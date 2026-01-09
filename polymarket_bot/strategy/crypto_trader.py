import os
from typing import Dict, List, Optional
from datetime import datetime, date
from dataclasses import dataclass

from ..markets import CryptoMarkets
from ..core.trader import PolymarketTrader
from ..config import WALLET_ADDRESS, MAX_POSITION_SIZE, ENABLE_TRADING


@dataclass
class TradeRecord:
    market_id: str
    symbol: str
    timeframe: str
    side: str
    outcome: str
    token_id: str
    size: float
    price: float
    timestamp: datetime
    order_id: Optional[str] = None


class CryptoTrader:
    MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', '20'))
    DEFAULT_SIZE = float(os.getenv('DEFAULT_TRADE_SIZE', '5.0'))
    
    def __init__(self):
        self.markets = CryptoMarkets()
        self.trader = PolymarketTrader()
        self.wallet = WALLET_ADDRESS
        self.max_position = MAX_POSITION_SIZE
        self.trading_enabled = ENABLE_TRADING
        self.daily_trades: List[TradeRecord] = []
        self.current_date: date = date.today()
    
    def _reset_daily_count(self):
        today = date.today()
        if self.current_date != today:
            self.daily_trades = []
            self.current_date = today
    
    def get_trades_today(self) -> int:
        self._reset_daily_count()
        return len(self.daily_trades)
    
    def can_trade(self) -> bool:
        self._reset_daily_count()
        return len(self.daily_trades) < self.MAX_DAILY_TRADES
    
    def get_remaining_trades(self) -> int:
        self._reset_daily_count()
        return max(0, self.MAX_DAILY_TRADES - len(self.daily_trades))
    
    def fetch_markets(self, timeframes: List[str] = None) -> Dict[str, List]:
        if timeframes is None:
            timeframes = ['15m', '1h']
        
        result = {}
        for tf in timeframes:
            if tf == '15m':
                result['15m'] = self.markets.get_15m()
            elif tf == '1h':
                result['1h'] = self.markets.get_1h()
            elif tf == '4h':
                result['4h'] = self.markets.get_4h()
        
        return result
    
    def place_trade(
        self,
        symbol: str,
        timeframe: str,
        outcome: str,
        size: float = None
    ) -> Optional[Dict]:
        if not self.can_trade():
            print(f"Daily trade limit reached ({self.MAX_DAILY_TRADES})")
            return None
        
        if not self.trading_enabled:
            print("Trading is disabled")
            return None
        
        market = self.markets.get_market(symbol, timeframe)
        if not market:
            print(f"Market not found: {symbol} {timeframe}")
            return None
        
        if outcome not in market.outcomes:
            print(f"Invalid outcome: {outcome}. Available: {market.outcomes}")
            return None
        
        outcome_idx = market.outcomes.index(outcome)
        if outcome_idx >= len(market.token_ids):
            print(f"Token ID not found for outcome: {outcome}")
            return None
        
        token_id = market.token_ids[outcome_idx]
        price = market.prices.get(outcome, 0.5)
        trade_size = size or self.DEFAULT_SIZE
        
        if trade_size > self.max_position:
            trade_size = self.max_position
            print(f"Size capped to max position: ${trade_size}")
        
        print(f"Placing trade: {symbol} {timeframe} | {outcome} @ ${price:.2f} | Size: ${trade_size}")
        
        result = self.trader.buy(token_id, trade_size, price)
        
        if result:
            record = TradeRecord(
                market_id=market.condition_id,
                symbol=symbol,
                timeframe=timeframe,
                side='BUY',
                outcome=outcome,
                token_id=token_id,
                size=trade_size,
                price=price,
                timestamp=datetime.now(),
                order_id=result.get('id')
            )
            self.daily_trades.append(record)
            print(f"Trade placed! Order ID: {result.get('id')} | Remaining: {self.get_remaining_trades()}")
        
        return result
    
    def buy_up(self, symbol: str, timeframe: str, size: float = None) -> Optional[Dict]:
        return self.place_trade(symbol, timeframe, 'Up', size)
    
    def buy_down(self, symbol: str, timeframe: str, size: float = None) -> Optional[Dict]:
        return self.place_trade(symbol, timeframe, 'Down', size)
    
    def scan_and_trade(self, strategy: str = 'momentum') -> List[Dict]:
        if not self.can_trade():
            print(f"Daily limit reached. Trades today: {self.get_trades_today()}/{self.MAX_DAILY_TRADES}")
            return []
        
        markets = self.fetch_markets(['15m', '1h'])
        trades = []
        
        for tf, mkts in markets.items():
            for m in mkts:
                if not self.can_trade():
                    break
                
                up_price = m.prices.get('Up', 0.5)
                down_price = m.prices.get('Down', 0.5)
                
                signal = None
                if strategy == 'momentum':
                    if up_price >= 0.55:
                        signal = 'Up'
                    elif down_price >= 0.55:
                        signal = 'Down'
                elif strategy == 'contrarian':
                    if up_price <= 0.45:
                        signal = 'Up'
                    elif down_price <= 0.45:
                        signal = 'Down'
                
                if signal:
                    result = self.place_trade(m.symbol, tf, signal)
                    if result:
                        trades.append({
                            'symbol': m.symbol,
                            'timeframe': tf,
                            'outcome': signal,
                            'price': m.prices.get(signal),
                            'order': result
                        })
        
        return trades
    
    def get_status(self) -> Dict:
        self._reset_daily_count()
        return {
            'trading_enabled': self.trading_enabled,
            'trades_today': len(self.daily_trades),
            'max_daily_trades': self.MAX_DAILY_TRADES,
            'remaining_trades': self.get_remaining_trades(),
            'default_size': self.DEFAULT_SIZE,
            'max_position': self.max_position,
            'recent_trades': [
                {
                    'symbol': t.symbol,
                    'timeframe': t.timeframe,
                    'outcome': t.outcome,
                    'price': t.price,
                    'size': t.size,
                    'time': t.timestamp.isoformat(),
                    'order_id': t.order_id
                }
                for t in self.daily_trades[-5:]
            ]
        }
    
    def print_markets(self, timeframes: List[str] = None):
        markets = self.fetch_markets(timeframes)
        
        print(f"\n{'='*60}")
        print(f"CRYPTO MARKETS | Trades: {self.get_trades_today()}/{self.MAX_DAILY_TRADES}")
        print(f"{'='*60}")
        
        for tf, mkts in markets.items():
            print(f"\n--- {tf.upper()} ---")
            for m in mkts:
                up = m.prices.get('Up', 0)
                down = m.prices.get('Down', 0)
                vol = m.volume
                print(f"{m.symbol}: Up ${up:.2f} | Down ${down:.2f} | Vol ${vol:,.0f}")
