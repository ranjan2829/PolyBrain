from .core import PolymarketClient, PolymarketTrader
from .api import GigaBrainClient, DuneClient
from .data import (
    Timeframe,
    TimeframeConfig,
    CryptoPriceData,
    CryptoMarketData,
    CryptoFetcherManager,
    CryptoTimeframeFetcher,
    get_crypto_fetcher_manager,
    get_15m_fetcher,
    get_1h_fetcher,
    get_4h_fetcher,
)
from .copytrading import CopyTradingService, HourlyScheduler, LeaderboardFetcher, RedisCache
from .markets import CryptoMarkets
from .scalper import ScalperBot
from .strategy import SmartStrategy, quick_scan, quick_trade
from .db import Database, TradeRepository
from .agent import CopyTradeAgent
from .server import PolyBrainServer, create_server

__version__ = "2.0.0"
__all__ = [
    'PolymarketClient',
    'PolymarketTrader',
    'GigaBrainClient',
    'DuneClient',
    'Timeframe',
    'TimeframeConfig',
    'CryptoPriceData',
    'CryptoMarketData',
    'CryptoFetcherManager',
    'CryptoTimeframeFetcher',
    'get_crypto_fetcher_manager',
    'get_15m_fetcher',
    'get_1h_fetcher',
    'get_4h_fetcher',
    'CopyTradingService',
    'HourlyScheduler',
    'LeaderboardFetcher',
    'RedisCache',
    'CryptoMarkets',
    'ScalperBot',
    'SmartStrategy',
    'quick_scan',
    'quick_trade',
    'Database',
    'TradeRepository',
    'CopyTradeAgent',
    'PolyBrainServer',
    'create_server',
]
