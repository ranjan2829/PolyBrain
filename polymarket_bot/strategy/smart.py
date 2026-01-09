from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import date
import json

from ..markets import CryptoMarkets
from ..core.trader import PolymarketTrader
from ..api.gigabrain import GigaBrainClient


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
    BUY_MIN = 0.55
    BUY_MAX = 0.75
    
    def __init__(self):
        self.markets = CryptoMarkets()
        self.trader = PolymarketTrader()
        self.brain = GigaBrainClient()
        self.trades_today: List = []
        self.today: date = date.today()
    
    def _reset(self):
        if date.today() != self.today:
            self.trades_today = []
            self.today = date.today()
    
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
                    'in_sweet_spot': self.BUY_MIN <= dominant_price <= self.BUY_MAX and m.volume >= self.MIN_VOLUME
                }
                
                result['markets'].append(market_data)
                
                if market_data['in_sweet_spot']:
                    result['opportunities'].append(market_data)
        
        return result
    
    def ask_brain(self) -> Optional[Dict]:
        ctx = self.get_market_context()
        
        prompt = "Polymarket 15m/1h crypto bets:\n"
        for m in ctx['markets']:
            prompt += f"{m['symbol']} {m['timeframe']}: Up ${m['up_price']:.2f}, Down ${m['down_price']:.2f}, Vol ${m['volume']:,}\n"
        
        prompt += "\nRules: Buy at $0.55-0.75, pays $1 if wins. Which ONE bet? Reply SHORT: Symbol, Side, Price, Yes/No, 2-line reason with data."
        
        response = self.brain.chat(prompt)
        
        if 'error' in response:
            return {'error': response['error'], 'context': ctx}
        
        return {
            'ai_response': response.get('content', ''),
            'context': ctx,
            'credits': response.get('credits_remaining')
        }
    
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
    
    def buy(self, trade: Trade, size: float = 5.0) -> Optional[dict]:
        self._reset()
        
        if self.remaining() <= 0:
            return None
        
        market = self.markets.get_market(trade.symbol, trade.timeframe)
        if not market:
            return None
        
        idx = market.outcomes.index(trade.side)
        token_id = market.token_ids[idx]
        price = market.prices.get(trade.side)
        
        result = self.trader.buy(token_id, size, price)
        
        if result:
            self.trades_today.append(trade)
        
        return result
    
    def run(self, size: float = 5.0, max_trades: int = 3) -> List:
        trades = self.scan()
        results = []
        
        for t in trades[:max_trades]:
            if self.remaining() <= 0:
                break
            result = self.buy(t, size)
            if result:
                results.append({'trade': t, 'result': result})
        
        return results
    
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


def quick_scan() -> List[Trade]:
    return SmartStrategy().scan()


def quick_trade(size: float = 5.0) -> Optional[dict]:
    s = SmartStrategy()
    trades = s.scan()
    if trades:
        return s.buy(trades[0], size)
    return None


def market_status() -> dict:
    return SmartStrategy().status()


def ask_ai() -> Optional[Dict]:
    return SmartStrategy().ask_brain()
