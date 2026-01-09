import re
import requests
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import date

from ..markets import CryptoMarkets
from ..core.trader import PolymarketTrader
from ..api.gigabrain import GigaBrainClient
from ..db.postgres import Database
from ..db.repository import TradeRepository


@dataclass 
class Trade:
    symbol: str
    timeframe: str
    side: str
    price: float
    potential_gain: float
    volume: float


class SmartStrategy:
    MAX_TRADES = 20
    MIN_VOLUME = 5000
    BUY_MIN = 0.30
    BUY_MAX = 0.80
    
    def __init__(self):
        self.markets = CryptoMarkets()
        self.trader = PolymarketTrader()
        self.brain = GigaBrainClient()
        self.db = None
        self.repo = None
        self.trades_today: List = []
        self.today: date = date.today()
        self._connect_db()
    
    def _connect_db(self):
        try:
            self.db = Database()
            self.db.connect()
            self.db.init_tables()
            self.repo = TradeRepository(self.db)
        except Exception as e:
            print(f"DB not connected: {e}")
            self.db = None
            self.repo = None
    
    def _reset(self):
        if date.today() != self.today:
            self.trades_today = []
            self.today = date.today()
    
    def _get_crypto_prices(self) -> Dict[str, float]:
        try:
            resp = requests.get(
                'https://api.binance.com/api/v3/ticker/price',
                params={'symbols': '["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT"]'},
                timeout=5
            )
            data = resp.json()
            return {
                'BTC': float(next((x['price'] for x in data if x['symbol'] == 'BTCUSDT'), 0)),
                'ETH': float(next((x['price'] for x in data if x['symbol'] == 'ETHUSDT'), 0)),
                'SOL': float(next((x['price'] for x in data if x['symbol'] == 'SOLUSDT'), 0)),
                'XRP': float(next((x['price'] for x in data if x['symbol'] == 'XRPUSDT'), 0))
            }
        except Exception:
            return {'BTC': 0, 'ETH': 0, 'SOL': 0, 'XRP': 0}
    
    def remaining(self) -> int:
        self._reset()
        return self.MAX_TRADES - len(self.trades_today)
    
    def get_market_context(self) -> Dict:
        result = {'markets': [], 'opportunities': []}
        
        for tf in ['15m', '1h']:
            mkts = self.markets.get_15m() if tf == '15m' else self.markets.get_1h()
            
            for m in mkts:
                up = m.prices.get('Up', 0.5)
                down = m.prices.get('Down', 0.5)
                dominant_side = 'Up' if up > down else 'Down'
                dominant_price = up if up > down else down
                
                market_data = {
                    'symbol': m.symbol,
                    'timeframe': tf,
                    'up_price': round(up, 2),
                    'down_price': round(down, 2),
                    'dominant_side': dominant_side,
                    'dominant_price': round(dominant_price, 2),
                    'volume': round(m.volume),
                    'potential_gain': round(((1/dominant_price) - 1) * 100, 1) if dominant_price > 0 else 0,
                    'in_sweet_spot': self.BUY_MIN <= dominant_price <= self.BUY_MAX and m.volume >= self.MIN_VOLUME,
                    'token_ids': m.token_ids,
                    'outcomes': m.outcomes
                }
                
                result['markets'].append(market_data)
                
                if market_data['in_sweet_spot']:
                    result['opportunities'].append(market_data)
        
        return result
    
    def _parse_ai_response(self, response: str) -> Dict:
        result = {'symbol': None, 'side': None, 'price': None, 'decision': None, 'reason': response}
        
        symbols = ['BTC', 'ETH', 'SOL', 'XRP']
        for sym in symbols:
            if sym in response.upper():
                result['symbol'] = sym
                break
        
        if 'Up' in response or 'UP' in response:
            result['side'] = 'Up'
        elif 'Down' in response or 'DOWN' in response:
            result['side'] = 'Down'
        
        prices = re.findall(r'\$?(0\.\d+)', response)
        if prices:
            result['price'] = float(prices[0])
        
        if '**Yes' in response or ', Yes' in response or 'Yes,' in response:
            result['decision'] = 'YES'
        elif '**No' in response or ', No' in response or 'No,' in response:
            result['decision'] = 'NO'
        
        return result
    
    def ask_brain_and_trade(self, size: float = 5.0) -> Dict:
        self._reset()
        ctx = self.get_market_context()
        crypto_prices = self._get_crypto_prices()
        
        prompt = "POLYMARKET CRYPTO BETS - REAL-TIME:\n\n"
        
        prompt += "HOW IT WORKS: Each market has a 'price to beat' (crypto price at interval START).\n"
        prompt += "- 'Up' wins if price at END >= price at START\n"
        prompt += "- 'Down' wins if price at END < price at START\n\n"
        
        prompt += "CURRENT CRYPTO PRICES (Binance):\n"
        for sym, price in crypto_prices.items():
            prompt += f"  {sym}: ${price:,.2f}\n"
        
        prompt += "\nMARKET ODDS (what bettors think):\n"
        for m in ctx['markets']:
            up_pct = int(m['up_price'] * 100)
            down_pct = int(m['down_price'] * 100)
            up_gain = round(((1/m['up_price']) - 1) * 100, 1) if m['up_price'] > 0 else 0
            down_gain = round(((1/m['down_price']) - 1) * 100, 1) if m['down_price'] > 0 else 0
            sweet = "✓" if m['in_sweet_spot'] else "✗"
            prompt += f"  {sweet} {m['symbol']} {m['timeframe']}: Up {up_pct}% (+{up_gain}% gain) | Down {down_pct}% (+{down_gain}% gain) | Vol ${m['volume']:,}\n"
        
        if ctx['opportunities']:
            prompt += "\nBEST BETS (dominant side, $0.30-$0.80):\n"
            for m in ctx['opportunities']:
                gain = round(((1/m['dominant_price']) - 1) * 100, 1)
                prompt += f"  → {m['symbol']} {m['timeframe']} {m['dominant_side']} @ {int(m['dominant_price']*100)}% odds = +{gain}% if wins\n"
        else:
            prompt += "\nNO GOOD BETS (prices outside $0.30-$0.80 or low volume)\n"
        
        prompt += """
STRATEGY:
- Bet WITH the market (dominant side = higher odds)
- Only bet if odds are $0.30-$0.80 (30%-80%)
- Higher volume = more reliable signal

Pick ONE bet. Reply: Symbol, Timeframe, Side, Price, Yes/No, reason (include price prediction)."""
        
        response = self.brain.chat(prompt)
        
        if 'error' in response:
            return {'success': False, 'error': response['error']}
        
        ai_text = response.get('content', '')
        parsed = self._parse_ai_response(ai_text)
        
        result = {
            'ai_response': ai_text,
            'parsed': parsed,
            'context': ctx,
            'trade_placed': False,
            'order': None,
            'db_id': None
        }
        
        market_info = None
        for m in ctx['markets']:
            if m['symbol'] == parsed['symbol']:
                market_info = m
                break
        
        volume = market_info['volume'] if market_info else 0
        entry_price = parsed['price'] or (market_info['dominant_price'] if market_info else 0)
        
        if parsed['decision'] == 'YES' and parsed['symbol'] and parsed['side']:
            if self.remaining() <= 0:
                result['error'] = 'Daily limit reached'
            else:
                market = self.markets.get_market(parsed['symbol'], '15m')
                if not market:
                    market = self.markets.get_market(parsed['symbol'], '1h')
                
                if market:
                    try:
                        idx = market.outcomes.index(parsed['side'])
                        token_id = market.token_ids[idx]
                        price = market.prices.get(parsed['side'])
                        
                        order = self.trader.buy(token_id, size, price)
                        
                        order_status = 'placed' if order else 'failed'
                        order_id = str(order.get('orderID', '')) if order else None
                        
                        if order:
                            result['trade_placed'] = True
                            result['order'] = order
                            self.trades_today.append(parsed)
                        else:
                            result['error'] = 'Order failed (no balance?)'
                        
                        if self.repo:
                            db_id = self.repo.save_brain_bet(
                                symbol=parsed['symbol'],
                                timeframe=market.timeframe,
                                side=parsed['side'],
                                entry_price=price,
                                volume=volume,
                                brain_reason=ai_text,
                                brain_decision='YES',
                                order_id=order_id,
                                size=size,
                                status=order_status
                            )
                            result['db_id'] = db_id
                    except Exception as e:
                        result['error'] = str(e)
                        if self.repo:
                            db_id = self.repo.save_brain_bet(
                                symbol=parsed['symbol'],
                                timeframe='15m',
                                side=parsed['side'],
                                entry_price=entry_price,
                                volume=volume,
                                brain_reason=ai_text,
                                brain_decision='YES',
                                status='error'
                            )
                            result['db_id'] = db_id
                else:
                    result['error'] = 'Market not found'
        else:
            if self.repo and parsed['symbol'] and parsed['side']:
                db_id = self.repo.save_brain_bet(
                    symbol=parsed['symbol'],
                    timeframe='15m',
                    side=parsed['side'],
                    entry_price=entry_price,
                    volume=volume,
                    brain_reason=ai_text,
                    brain_decision='NO',
                    status='skipped'
                )
                result['db_id'] = db_id
        
        return result
    
    def update_bet_pnl(self, bet_id: int) -> Dict:
        if not self.repo:
            return {'error': 'No DB connection'}
        
        bets = self.repo.get_brain_bets()
        bet = next((b for b in bets if b['id'] == bet_id), None)
        
        if not bet:
            return {'error': 'Bet not found'}
        
        market = self.markets.get_market(bet['symbol'], bet['timeframe'])
        if not market:
            return {'error': 'Market not found'}
        
        current_price = market.prices.get(bet['side'], 0)
        entry_price = float(bet['entry_price'])
        
        if current_price >= 0.99:
            pnl = ((1.0 / entry_price) - 1) * 100
            status = 'won'
        elif current_price <= 0.01:
            pnl = -100
            status = 'lost'
        else:
            pnl = ((current_price - entry_price) / entry_price) * 100
            status = 'open'
        
        if status in ['won', 'lost']:
            self.repo.update_brain_bet(bet_id, current_price, pnl, status)
        
        return {
            'bet_id': bet_id,
            'symbol': bet['symbol'],
            'side': bet['side'],
            'entry_price': entry_price,
            'current_price': current_price,
            'pnl': round(pnl, 2),
            'status': status
        }
    
    def get_bets(self, status: str = None) -> List[Dict]:
        if not self.repo:
            return []
        return self.repo.get_brain_bets(status)
    
    def get_pnl(self) -> Dict:
        if not self.repo:
            return {}
        return self.repo.get_brain_pnl()
    
    def scan(self) -> List[Trade]:
        trades = []
        
        for tf in ['15m', '1h']:
            mkts = self.markets.get_15m() if tf == '15m' else self.markets.get_1h()
            
            for m in mkts:
                if m.volume < self.MIN_VOLUME:
                    continue
                
                up = m.prices.get('Up', 0.5)
                down = m.prices.get('Down', 0.5)
                
                if up > down:
                    if self.BUY_MIN <= up <= self.BUY_MAX:
                        gain = ((1.0 / up) - 1) * 100
                        trades.append(Trade(
                            symbol=m.symbol,
                            timeframe=tf,
                            side='Up',
                            price=up,
                            potential_gain=gain,
                            volume=m.volume
                        ))
                else:
                    if self.BUY_MIN <= down <= self.BUY_MAX:
                        gain = ((1.0 / down) - 1) * 100
                        trades.append(Trade(
                            symbol=m.symbol,
                            timeframe=tf,
                            side='Down',
                            price=down,
                            potential_gain=gain,
                            volume=m.volume
                        ))
        
        trades.sort(key=lambda x: x.volume, reverse=True)
        return trades
    
    def status(self) -> dict:
        trades = self.scan()
        return {
            'remaining': self.remaining(),
            'opportunities': len(trades),
            'trades': [
                {
                    'symbol': t.symbol,
                    'timeframe': t.timeframe,
                    'side': t.side,
                    'price': t.price,
                    'gain': round(t.potential_gain, 1),
                    'volume': round(t.volume)
                }
                for t in trades
            ]
        }


_strategy = SmartStrategy()


def ask_ai() -> Dict:
    return _strategy.ask_brain_and_trade()


def market_status() -> dict:
    return _strategy.status()


def get_bets(status: str = None) -> List[Dict]:
    return _strategy.get_bets(status)


def get_pnl() -> Dict:
    return _strategy.get_pnl()
