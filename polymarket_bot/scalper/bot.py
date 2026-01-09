import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from ..markets import CryptoMarkets
from ..core import PolymarketTrader
from ..config import ENABLE_TRADING, MAX_POSITION_SIZE


@dataclass
class Position:
    market_slug: str
    symbol: str
    timeframe: str
    side: str
    token_id: str
    entry_price: float
    size: float
    target_price: float
    stop_price: float
    opened_at: datetime


class ScalperBot:
    def __init__(self):
        self.markets = CryptoMarkets()
        self.trader = PolymarketTrader()
        self.positions: Dict[str, Position] = {}
        self.take_profit_pct = 0.05  # 5% profit target
        self.stop_loss_pct = 0.10    # 10% stop loss
        self.max_positions = 3
        self.min_edge = 0.02         # Min 2% edge to enter
        self.running = False
    
    def find_opportunity(self, market) -> Optional[Dict]:
        up_price = market.prices.get('Up', 0.5)
        down_price = market.prices.get('Down', 0.5)
        
        # Look for mispriced markets (deviation from 50/50)
        if up_price < 0.48:  # Up is underpriced
            return {
                'side': 'Up',
                'price': up_price,
                'edge': 0.50 - up_price,
                'token_id': market.token_ids[0] if market.token_ids else None
            }
        elif down_price < 0.48:  # Down is underpriced
            return {
                'side': 'Down',
                'price': down_price,
                'edge': 0.50 - down_price,
                'token_id': market.token_ids[1] if len(market.token_ids) > 1 else None
            }
        
        return None
    
    def calculate_size(self, edge: float) -> float:
        # Kelly-inspired sizing: bet more when edge is higher
        base_size = 10.0
        size = base_size * (1 + edge * 10)
        return min(size, MAX_POSITION_SIZE)
    
    def open_position(self, market, opportunity: Dict) -> Optional[Position]:
        if len(self.positions) >= self.max_positions:
            return None
        
        if market.slug in self.positions:
            return None
        
        token_id = opportunity['token_id']
        if not token_id:
            return None
        
        entry_price = opportunity['price']
        size = self.calculate_size(opportunity['edge'])
        target = entry_price * (1 + self.take_profit_pct)
        stop = entry_price * (1 - self.stop_loss_pct)
        
        if ENABLE_TRADING:
            result = self.trader.buy(token_id, size, entry_price)
            if not result:
                print(f"Failed to open position on {market.symbol}")
                return None
        
        position = Position(
            market_slug=market.slug,
            symbol=market.symbol,
            timeframe=market.timeframe,
            side=opportunity['side'],
            token_id=token_id,
            entry_price=entry_price,
            size=size,
            target_price=target,
            stop_price=stop,
            opened_at=datetime.now()
        )
        
        self.positions[market.slug] = position
        print(f"OPEN: {market.symbol} {opportunity['side']} @ ${entry_price:.3f} | Size: ${size:.2f} | Target: ${target:.3f}")
        return position
    
    def check_exit(self, position: Position, current_price: float) -> bool:
        # Take profit
        if current_price >= position.target_price:
            pnl = (current_price - position.entry_price) * position.size
            print(f"TAKE PROFIT: {position.symbol} | Entry: ${position.entry_price:.3f} -> ${current_price:.3f} | PnL: ${pnl:.2f}")
            return True
        
        # Stop loss
        if current_price <= position.stop_price:
            pnl = (current_price - position.entry_price) * position.size
            print(f"STOP LOSS: {position.symbol} | Entry: ${position.entry_price:.3f} -> ${current_price:.3f} | PnL: ${pnl:.2f}")
            return True
        
        return False
    
    def close_position(self, position: Position, current_price: float):
        if ENABLE_TRADING:
            self.trader.sell(position.token_id, position.size, current_price)
        
        del self.positions[position.market_slug]
    
    def scan_markets(self):
        for timeframe in ['15m', '1h']:
            markets = self.markets._get_timeframe(timeframe)
            
            for market in markets:
                # Check existing position
                if market.slug in self.positions:
                    pos = self.positions[market.slug]
                    current = market.prices.get(pos.side, pos.entry_price)
                    if self.check_exit(pos, current):
                        self.close_position(pos, current)
                    continue
                
                # Look for new opportunity
                opp = self.find_opportunity(market)
                if opp and opp['edge'] >= self.min_edge:
                    self.open_position(market, opp)
    
    def run(self, interval: int = 30):
        print(f"ScalperBot started | TP: {self.take_profit_pct*100}% | SL: {self.stop_loss_pct*100}%")
        self.running = True
        
        while self.running:
            try:
                self.scan_markets()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Positions: {len(self.positions)}/{self.max_positions}")
                time.sleep(interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)
        
        print("ScalperBot stopped")
    
    def stop(self):
        self.running = False
    
    def get_status(self) -> Dict:
        return {
            'running': self.running,
            'positions': len(self.positions),
            'max_positions': self.max_positions,
            'take_profit': self.take_profit_pct,
            'stop_loss': self.stop_loss_pct
        }
