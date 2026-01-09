import requests
from typing import List, Dict, Optional
from datetime import datetime, timezone
from .models import Timeframe, TimeframeConfig, CryptoPriceData, CryptoMarketData
from ..utils.market import generate_market_slug, get_interval_timestamps


class TimeframeRegistry:
    CONFIG: Dict[Timeframe, TimeframeConfig] = {
        Timeframe.FIFTEEN_MIN: TimeframeConfig(
            name='15m',
            duration_seconds=900,
            variant='fifteen',
            slug_format='timestamp'
        ),
        Timeframe.ONE_HOUR: TimeframeConfig(
            name='1h',
            duration_seconds=3600,
            variant='hour',
            slug_format='date'
        ),
        Timeframe.FOUR_HOUR: TimeframeConfig(
            name='4h',
            duration_seconds=14400,
            variant='four',
            slug_format='timestamp'
        )
    }
    
    @classmethod
    def get_config(cls, timeframe: Timeframe) -> TimeframeConfig:
        return cls.CONFIG[timeframe]
    
    @classmethod
    def get_variant(cls, timeframe: Timeframe) -> str:
        return cls.get_config(timeframe).variant


class CryptoFetcherBase:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Content-Type': 'application/json',
            'Referer': 'https://polymarket.com/',
            'Origin': 'https://polymarket.com'
        })
        self.gamma_base_url = 'https://gamma-api.polymarket.com'
        self.crypto_price_url = 'https://polymarket.com/api/crypto/crypto-price'
    
    def _fetch_market_by_slug(self, slug: str) -> Optional[Dict]:
        if not slug:
            return None
        
        try:
            resp = self.session.get(
                f'{self.gamma_base_url}/markets/slug/{slug}',
                timeout=10
            )
            if resp.status_code == 200:
                market = resp.json()
                if 'question' not in market or 'conditionId' not in market:
                    return None
                return market
            return None
        except Exception as e:
            print(f"Error fetching market by slug {slug}: {e}")
            return None
    
    def _fetch_price_data(
        self,
        interval_start_ts: int,
        symbol: str,
        variant: str
    ) -> Optional[Dict]:
        try:
            start_dt = datetime.fromtimestamp(interval_start_ts, tz=timezone.utc)
            duration_map = {'fifteen': 900, 'hour': 3600, 'four': 14400}
            duration = duration_map.get(variant, 900)
            end_dt = datetime.fromtimestamp(interval_start_ts + duration, tz=timezone.utc)
            
            resp = self.session.get(
                self.crypto_price_url,
                params={
                    'symbol': symbol,
                    'eventStartTime': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'variant': variant,
                    'endDate': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                },
                timeout=10
            )
            
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            print(f"Error fetching price data for {symbol} {variant}: {e}")
            return None


class CryptoTimeframeFetcher(CryptoFetcherBase):
    def __init__(self, timeframe: Timeframe):
        super().__init__()
        self.timeframe = timeframe
        self.config = TimeframeRegistry.get_config(timeframe)
    
    def get_price_data(
        self,
        interval_start_ts: int,
        symbol: str = 'BTC'
    ) -> Optional[CryptoPriceData]:
        raw_data = self._fetch_price_data(
            interval_start_ts,
            symbol,
            self.config.variant
        )
        
        if not raw_data:
            return None
        
        return CryptoPriceData(
            symbol=symbol,
            timeframe=self.config.name,
            timestamp=interval_start_ts,
            open_price=float(raw_data.get('openPrice')) if raw_data.get('openPrice') else None,
            close_price=float(raw_data.get('closePrice')) if raw_data.get('closePrice') else None,
            completed=raw_data.get('completed', False) or raw_data.get('cached', False),
            incomplete=raw_data.get('incomplete', False)
        )
    
    def get_market_data(
        self,
        interval_start_ts: int,
        symbol: str = 'BTC'
    ) -> Optional[CryptoMarketData]:
        slug = generate_market_slug(interval_start_ts, symbol, self.config.name)
        market = self._fetch_market_by_slug(slug)
        
        if not market:
            return None
        
        return CryptoMarketData(
            condition_id=market.get('conditionId', ''),
            symbol=symbol,
            timeframe=self.config.name,
            slug=slug,
            question=market.get('question', ''),
            start_date=interval_start_ts,
            volume=float(market.get('volume', 0) or 0),
            liquidity=float(market.get('liquidity', 0) or 0),
            active=market.get('active', False),
            closed=market.get('closed', False),
            outcomes=market.get('outcomes', [])
        )
    
    def get_active_markets(
        self,
        symbols: List[str] = None
    ) -> List[CryptoMarketData]:
        if symbols is None:
            symbols = ['BTC', 'ETH', 'SOL', 'XRP']
        
        active_markets = []
        seen_slugs = set()
        
        try:
            intervals = get_interval_timestamps(self.config.name)
            
            for symbol in symbols:
                for interval_ts in intervals:
                    slug = generate_market_slug(interval_ts, symbol, self.config.name)
                    
                    if slug in seen_slugs:
                        continue
                    seen_slugs.add(slug)
                    
                    market_data = self.get_market_data(interval_ts, symbol)
                    if market_data and market_data.active and not market_data.closed:
                        active_markets.append(market_data)
        except Exception as e:
            print(f"Error fetching active {self.config.name} markets: {e}")
        
        active_markets.sort(key=lambda x: x.start_date, reverse=True)
        return active_markets
    
    def get_current_interval_prices(
        self,
        symbols: List[str] = None
    ) -> List[CryptoPriceData]:
        if symbols is None:
            symbols = ['BTC', 'ETH', 'SOL', 'XRP']
        
        prices = []
        intervals = get_interval_timestamps(self.config.name)
        current_interval = intervals[0] if intervals else None
        
        if not current_interval:
            return prices
        
        for symbol in symbols:
            price_data = self.get_price_data(current_interval, symbol)
            if price_data:
                prices.append(price_data)
        
        return prices


class CryptoFetcherManager(CryptoFetcherBase):
    def __init__(self):
        super().__init__()
        self._fetchers = {
            Timeframe.FIFTEEN_MIN: CryptoTimeframeFetcher(Timeframe.FIFTEEN_MIN),
            Timeframe.ONE_HOUR: CryptoTimeframeFetcher(Timeframe.ONE_HOUR),
            Timeframe.FOUR_HOUR: CryptoTimeframeFetcher(Timeframe.FOUR_HOUR),
        }
    
    def get_fetcher(self, timeframe: Timeframe) -> CryptoTimeframeFetcher:
        return self._fetchers[timeframe]
    
    def get_fifteen_minute_fetcher(self) -> CryptoTimeframeFetcher:
        return self.get_fetcher(Timeframe.FIFTEEN_MIN)
    
    def get_one_hour_fetcher(self) -> CryptoTimeframeFetcher:
        return self.get_fetcher(Timeframe.ONE_HOUR)
    
    def get_four_hour_fetcher(self) -> CryptoTimeframeFetcher:
        return self.get_fetcher(Timeframe.FOUR_HOUR)
    
    def get_all_active_markets(
        self,
        symbols: List[str] = None,
        timeframes: List[Timeframe] = None
    ) -> Dict[str, List[CryptoMarketData]]:
        if timeframes is None:
            timeframes = list(Timeframe)
        
        result = {}
        for timeframe in timeframes:
            fetcher = self.get_fetcher(timeframe)
            markets = fetcher.get_active_markets(symbols)
            result[fetcher.config.name] = markets
        
        return result
    
    def get_all_current_prices(
        self,
        symbols: List[str] = None,
        timeframes: List[Timeframe] = None
    ) -> Dict[str, List[CryptoPriceData]]:
        if timeframes is None:
            timeframes = list(Timeframe)
        
        result = {}
        for timeframe in timeframes:
            fetcher = self.get_fetcher(timeframe)
            prices = fetcher.get_current_interval_prices(symbols)
            result[fetcher.config.name] = prices
        
        return result


def get_crypto_fetcher_manager() -> CryptoFetcherManager:
    return CryptoFetcherManager()


def get_15m_fetcher() -> CryptoTimeframeFetcher:
    return CryptoTimeframeFetcher(Timeframe.FIFTEEN_MIN)


def get_1h_fetcher() -> CryptoTimeframeFetcher:
    return CryptoTimeframeFetcher(Timeframe.ONE_HOUR)


def get_4h_fetcher() -> CryptoTimeframeFetcher:
    return CryptoTimeframeFetcher(Timeframe.FOUR_HOUR)
