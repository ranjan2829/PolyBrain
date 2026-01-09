import time
import json
from typing import List, Dict, Optional
from datetime import datetime
from ..core import PolymarketClient, PolymarketTrader
from ..api import GigaBrainClient
from ..db import Database, TradeRepository
from ..copytrading import CopyTradingService
from ..config import (
    WALLET_ADDRESS,
    MAX_POSITION_SIZE,
    ENABLE_TRADING
)


class CopyTradeAgent:
    def __init__(self):
        self.client = PolymarketClient()
        self.trader = PolymarketTrader()
        self.gigabrain = GigaBrainClient()
        self.copytrading = CopyTradingService()
        self.db = Database()
        self.repo = None
        self.wallet = WALLET_ADDRESS
        self.max_position = MAX_POSITION_SIZE
        self.min_confidence = 0.6
        self.seen_moves = set()
    
    def connect(self):
        self.db.connect()
        self.db.init_tables()
        self.repo = TradeRepository(self.db)
        print("CopyTradeAgent connected to database")
        return self
    
    def close(self):
        self.db.close()
    
    def get_account_value(self) -> float:
        try:
            positions = self.client.get_user_positions(self.wallet)
            total = sum(float(p.get('value', 0) or 0) for p in positions)
            return max(total, 100.0)
        except Exception:
            return 100.0
    
    def calculate_position_size(self, whale_size: float, whale_profit: float) -> float:
        account_value = self.get_account_value()
        base_ratio = min(account_value / 10000, 1.0)
        confidence_multiplier = min(whale_profit / 50000, 2.0) if whale_profit > 0 else 0.5
        position = whale_size * base_ratio * confidence_multiplier
        return min(position, self.max_position)
    
    def analyze_trade(self, whale: Dict, activity: Dict) -> Dict:
        market_question = activity.get('title', activity.get('marketTitle', 'Unknown'))
        side = activity.get('side', 'BUY')
        size = float(activity.get('size', 0) or activity.get('amount', 0) or 0)
        price = float(activity.get('price', 0.5) or 0.5)
        
        prompt = f"""Analyze this whale trade on Polymarket:

Whale: {whale.get('wallet', 'Unknown')}
Whale Profit: ${whale.get('profit', 0):,.2f}
Market: {market_question}
Side: {side}
Size: ${size:,.2f}
Price: {price}

Should we copy this trade? Consider:
1. Whale's track record (profit)
2. Market liquidity and volume
3. Current price vs fair value
4. Risk/reward ratio

Respond with JSON:
{{"copy": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

        try:
            response = self.gigabrain.chat(prompt)
            content = response.get('response', response.get('message', '{}'))
            
            if isinstance(content, str):
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    content = content[start:end]
                analysis = json.loads(content)
            else:
                analysis = content
            
            return {
                'copy': analysis.get('copy', False),
                'confidence': float(analysis.get('confidence', 0.5)),
                'reasoning': analysis.get('reasoning', 'No reasoning provided')
            }
        except Exception as e:
            return {
                'copy': whale.get('profit', 0) > 10000,
                'confidence': 0.5,
                'reasoning': f'Fallback: Based on whale profit. Error: {str(e)}'
            }
    
    def process_whale_activity(self, whale: Dict, activity: Dict) -> Optional[int]:
        move_id = f"{whale.get('wallet')}_{activity.get('id', activity.get('timestamp', ''))}"
        if move_id in self.seen_moves:
            return None
        self.seen_moves.add(move_id)
        
        market_id = activity.get('conditionId', activity.get('marketId', ''))
        market_question = activity.get('title', activity.get('marketTitle', 'Unknown'))
        side = activity.get('side', 'BUY').upper()
        size = float(activity.get('size', 0) or activity.get('amount', 0) or 0)
        price = float(activity.get('price', 0.5) or 0.5)
        
        if size < 10:
            return None
        
        whale_move_id = self.repo.save_whale_move(
            wallet=whale.get('wallet', ''),
            market_id=market_id,
            market_question=market_question,
            side=side,
            size=size,
            price=price
        )
        
        analysis = self.analyze_trade(whale, activity)
        
        if not analysis['copy'] or analysis['confidence'] < self.min_confidence:
            self.repo.mark_move_processed(whale_move_id)
            print(f"Skipping trade: {analysis['reasoning']}")
            return None
        
        our_size = self.calculate_position_size(size, whale.get('profit', 0))
        
        trade_id = self.repo.save_trade(
            whale_wallet=whale.get('wallet', ''),
            market_id=market_id,
            market_question=market_question,
            whale_side=side,
            whale_size=size,
            whale_price=price,
            our_side=side,
            our_size=our_size,
            our_price=price,
            reasoning=analysis['reasoning'],
            confidence=analysis['confidence'],
            status='pending'
        )
        
        if ENABLE_TRADING:
            token_id = activity.get('tokenId', activity.get('token_id', ''))
            if token_id:
                result = None
                if side == 'BUY':
                    result = self.trader.buy(token_id, our_size, price)
                else:
                    result = self.trader.sell(token_id, our_size, price)
                
                if result:
                    self.repo.update_trade_status(trade_id, 'executed', datetime.now())
                    print(f"Trade executed: {side} ${our_size:.2f} @ {price}")
                else:
                    self.repo.update_trade_status(trade_id, 'failed')
                    print(f"Trade failed: {side} ${our_size:.2f}")
            else:
                self.repo.update_trade_status(trade_id, 'no_token_id')
        else:
            print(f"Trade logged (trading disabled): {side} ${our_size:.2f} @ {price}")
        
        self.repo.mark_move_processed(whale_move_id)
        return trade_id
    
    def monitor_whales(self, top_n: int = 20, interval: int = 60):
        print(f"Monitoring top {top_n} whales every {interval}s...")
        
        while True:
            try:
                whales = self.copytrading.fetch_top_whales(top_n)
                
                for whale in whales[:10]:
                    wallet = whale.get('wallet')
                    if not wallet:
                        continue
                    
                    activities = self.client.get_user_activity(wallet, limit=5)
                    
                    for activity in activities:
                        if activity.get('type') in ['TRADE', 'BUY', 'SELL']:
                            self.process_whale_activity(whale, activity)
                    
                    time.sleep(0.5)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Scan complete. Waiting {interval}s...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\nStopping whale monitor...")
                break
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(10)
    
    def get_stats(self) -> Dict:
        return self.repo.get_pnl_summary()
    
    def get_recent_trades(self, limit: int = 20) -> List[Dict]:
        return self.repo.get_trade_history(limit)
