"""Polymarket Bot - Data Fetching Client"""
from .polymarket_client import PolymarketClient
from .fetchers import (
    CryptoFetcherManager,
    CryptoTimeframeFetcher,
    get_crypto_fetcher_manager,
    get_15m_fetcher,
    get_1h_fetcher,
    get_4h_fetcher,
)
from .models import (
    CryptoPriceData,
    CryptoMarketData,
    Timeframe,
)
from .gigabrain_client import GigaBrainClient
from .config import *

__version__ = "2.0.0"
__all__ = [
    'PolymarketClient',
    'CryptoFetcherManager',
    'CryptoTimeframeFetcher',
    'CryptoPriceData',
    'CryptoMarketData',
    'Timeframe',
    'get_crypto_fetcher_manager',
    'get_15m_fetcher',
    'get_1h_fetcher',
    'get_4h_fetcher',
    'GigaBrainClient',
]
