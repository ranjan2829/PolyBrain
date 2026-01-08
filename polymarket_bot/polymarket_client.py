import requests
from typing import List, Dict, Optional
from datetime import datetime, timezone
from .config import POLYMARKET_API_URL
from .market_utils import generate_market_slug, get_interval_timestamps, normalize_market, parse_json_fields
from .filters import filter_financial_markets


class PolymarketClient:
    def __init__(self):
        self.api_url = POLYMARKET_API_URL
        self.gamma_base_url = 'https://gamma-api.polymarket.com'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Content-Type': 'application/json',
            'Referer': 'https://polymarket.com/',
            'Origin': 'https://polymarket.com'
        })
    
    def get_markets(self, limit: int = 50, active: bool = True, 
                   filter_crypto_timeframes: bool = True,
                   filter_financial: bool = True,
                   min_volume: float = 50000) -> List[Dict]:
        try:
            all_markets = []
            seen_condition_ids = set()
            
            if filter_crypto_timeframes:
                for timeframe in ['15m', '1h', '4h']:
                    for m in self.find_active_crypto_timeframe_markets(timeframe):
                        cid = m.get('conditionId')
                        if cid and cid not in seen_condition_ids:
                            seen_condition_ids.add(cid)
                            all_markets.append(m)
            
            if filter_financial:
                try:
                    resp = self.session.get(f"{self.gamma_base_url}/markets", 
                                           params={"limit": 1000, "active": str(active).lower(), "closed": "false"}, 
                                           timeout=15)
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, list):
                            for m in filter_financial_markets(data, min_volume):
                                cid = m.get('conditionId') or m.get('condition_id')
                                if cid and cid not in seen_condition_ids:
                                    seen_condition_ids.add(cid)
                                    all_markets.append(m)
                except Exception:
                    pass
            
            valid_markets = [normalize_market(m) for m in all_markets if normalize_market(m)]
            valid_markets.sort(key=lambda x: x.get('volume', 0), reverse=True)
            return valid_markets[:limit]
        except Exception as e:
            print(f"Error fetching markets: {e}")
            return []
    
    def get_realtime_15m_markets(self) -> List[Dict]:
        try:
            realtime_markets = []
            seen = set()
            
            for timeframe in ['15m', '1h', '4h']:
                for m in self.find_active_crypto_timeframe_markets(timeframe):
                    cid = m.get('conditionId')
                    if cid and cid not in seen:
                        seen.add(cid)
                        realtime_markets.append(m)
            
            return realtime_markets
        except Exception as e:
            print(f"Error fetching realtime markets: {e}")
            return []
    
    def get_orderbook(self, token_id: str) -> Optional[Dict]:
        try:
            resp = self.session.get(f"{self.api_url}/book", params={"token_id": token_id}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return {'bids': data.get('bids', []), 'asks': data.get('asks', []), 'token_id': token_id}
            return None
        except Exception:
            return None
    
    def _fetch_user_data(self, endpoint: str, params: Dict) -> List[Dict]:
        try:
            resp = self.session.get(f"https://data-api.polymarket.com/{endpoint}", params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else []
            return []
        except Exception:
            return []
    
    def get_user_trades(self, wallet_address: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        return self._fetch_user_data('trades', {"user": wallet_address.lower(), "limit": limit, "offset": offset})
    
    def get_user_positions(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        return self._fetch_user_data('positions', {"user": wallet_address.lower(), "limit": limit})
    
    def get_user_activity(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        return self._fetch_user_data('activity', {
            "user": wallet_address.lower(),
            "limit": limit,
            "sortBy": "TIMESTAMP",
            "sortDirection": "DESC"
        })
    
    def find_active_crypto_timeframe_markets(self, timeframe: str = '15m', symbols: List[str] = None) -> List[Dict]:
        if symbols is None:
            symbols = ['BTC', 'ETH', 'SOL', 'XRP']
        
        active_markets = []
        seen_slugs = set()
        
        try:
            intervals = get_interval_timestamps(timeframe)
            
            for symbol in symbols:
                for interval_ts in intervals:
                    slug = generate_market_slug(interval_ts, symbol, timeframe)
                    if slug in seen_slugs:
                        continue
                    seen_slugs.add(slug)
                    
                    market = self.get_market_by_slug(slug)
                    if market:
                        market['conditionId'] = market.get('conditionId', '')
                        market['startDate'] = str(interval_ts)
                        market['symbol'] = symbol
                        active_markets.append(market)
        except Exception as e:
            print(f"Error finding {timeframe} markets: {e}")
        
        if active_markets:
            active_markets.sort(key=lambda x: x.get('startDate', ''), reverse=True)
            symbols_found = ', '.join(set([m.get('symbol', 'Unknown') for m in active_markets]))
            print(f"Found {len(active_markets)} active {timeframe} crypto markets ({symbols_found})")
        
        return active_markets
    
    def get_market_by_slug(self, slug: str) -> Optional[Dict]:
        if not slug:
            return None
        
        try:
            resp = self.session.get(f'{self.gamma_base_url}/markets/slug/{slug}', timeout=10)
            if resp.status_code == 200:
                market = resp.json()
                if 'question' not in market or 'conditionId' not in market:
                    return None
                return parse_json_fields(market)
            return None
        except Exception:
            return None
    
    def get_market_prices(self, interval_start_ts: int, symbol: str = 'BTC', variant: str = 'fifteen') -> Optional[Dict]:
        try:
            start_dt = datetime.fromtimestamp(interval_start_ts, tz=timezone.utc)
            duration = {'fifteen': 900, 'hour': 3600, 'four': 14400}.get(variant, 900)
            end_dt = datetime.fromtimestamp(interval_start_ts + duration, tz=timezone.utc)
            
            resp = self.session.get('https://polymarket.com/api/crypto/crypto-price', params={
                'symbol': symbol,
                'eventStartTime': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'variant': variant,
                'endDate': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            }, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'openPrice': float(data.get('openPrice')) if data.get('openPrice') else None,
                    'closePrice': float(data.get('closePrice')) if data.get('closePrice') else None,
                    'completed': data.get('completed', False) or data.get('cached', False),
                    'timestamp': data.get('timestamp'),
                    'incomplete': data.get('incomplete', False)
                }
            return None
        except Exception:
            return None
    
    def get_market_close_price(self, interval_start_ts: int, symbol: str = 'BTC', variant: str = 'fifteen') -> Optional[float]:
        prices = self.get_market_prices(interval_start_ts, symbol, variant)
        return prices.get('closePrice') if prices else None
