import requests
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta


@dataclass
class Market:
    symbol: str
    timeframe: str
    slug: str
    condition_id: str
    question: str
    volume: float
    liquidity: float
    active: bool
    outcomes: List[str]
    token_ids: List[str]
    prices: Dict[str, float]


class CryptoMarkets:
    SYMBOLS = ['BTC', 'ETH', 'SOL', 'XRP']
    TIMEFRAMES = ['15m', '1h', '4h']
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/json',
            'Referer': 'https://polymarket.com/',
            'Origin': 'https://polymarket.com'
        })
        self.gamma_url = 'https://gamma-api.polymarket.com'
        self.price_url = 'https://polymarket.com/api/crypto/crypto-price'
    
    def _get_slug(self, timestamp: int, symbol: str, timeframe: str) -> str:
        symbol_lower = symbol.lower()
        name = {'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'XRP': 'xrp'}.get(symbol, symbol_lower)
        
        if timeframe in ['1h', '4h']:
            et = timezone(timedelta(hours=-5))
            dt = datetime.fromtimestamp(timestamp, tz=et)
            month = dt.strftime('%B').lower()
            day = dt.day
            hour = dt.strftime('%I').lstrip('0') or '12'
            ampm = dt.strftime('%p').lower()
            return f"{name}-up-or-down-{month}-{day}-{hour}{ampm}-et"
        
        return f"{symbol_lower}-updown-{timeframe}-{timestamp}"
    
    def _get_intervals(self, timeframe: str) -> List[int]:
        durations = {'15m': 900, '1h': 3600, '4h': 14400}
        duration = durations.get(timeframe, 900)
        
        et = timezone(timedelta(hours=-5))
        now = int(datetime.now(et).timestamp())
        current = (now // duration) * duration
        
        # Check current + next 5 intervals to find active markets
        intervals = []
        for i in range(6):
            intervals.append(current + (i * duration))
        
        return intervals
    
    def _fetch_market(self, slug: str) -> Optional[Dict]:
        try:
            resp = self.session.get(f'{self.gamma_url}/markets/slug/{slug}', timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if 'conditionId' in data:
                    return data
        except Exception:
            pass
        return None
    
    def _parse_json(self, market: Dict, field: str) -> List:
        import json
        val = market.get(field, [])
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return []
        return val or []
    
    def get_market(self, symbol: str, timeframe: str) -> Optional[Market]:
        intervals = self._get_intervals(timeframe)
        
        for ts in intervals:
            slug = self._get_slug(ts, symbol, timeframe)
            data = self._fetch_market(slug)
            
            if data and data.get('active') and not data.get('closed'):
                outcomes = self._parse_json(data, 'outcomes')
                token_ids = self._parse_json(data, 'clobTokenIds')
                outcome_prices = self._parse_json(data, 'outcomePrices')
                
                prices = {}
                for i, outcome in enumerate(outcomes):
                    if i < len(outcome_prices):
                        prices[outcome] = float(outcome_prices[i])
                
                return Market(
                    symbol=symbol,
                    timeframe=timeframe,
                    slug=slug,
                    condition_id=data.get('conditionId', ''),
                    question=data.get('question', ''),
                    volume=float(data.get('volume', 0) or 0),
                    liquidity=float(data.get('liquidity', 0) or 0),
                    active=True,
                    outcomes=outcomes,
                    token_ids=token_ids,
                    prices=prices
                )
        
        return None
    
    def get_15m(self, symbols: List[str] = None) -> List[Market]:
        return self._get_timeframe('15m', symbols)
    
    def get_1h(self, symbols: List[str] = None) -> List[Market]:
        return self._get_timeframe('1h', symbols)
    
    def get_4h(self, symbols: List[str] = None) -> List[Market]:
        return self._get_timeframe('4h', symbols)
    
    def _get_timeframe(self, timeframe: str, symbols: List[str] = None) -> List[Market]:
        if symbols is None:
            symbols = self.SYMBOLS
        
        markets = []
        for symbol in symbols:
            market = self.get_market(symbol, timeframe)
            if market:
                markets.append(market)
        
        return markets
    
    def get_all(self, symbols: List[str] = None) -> Dict[str, List[Market]]:
        return {
            '15m': self.get_15m(symbols),
            '1h': self.get_1h(symbols),
            '4h': self.get_4h(symbols)
        }
    
    def to_dict(self, markets: List[Market]) -> List[Dict]:
        return [asdict(m) for m in markets]
    
    def print_markets(self, markets: List[Market]):
        for m in markets:
            print(f"{m.symbol} {m.timeframe}: {m.question}")
            for outcome, price in m.prices.items():
                print(f"  {outcome}: ${price:.2f}")
