from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class Timeframe(Enum):
    FIFTEEN_MIN = '15m'
    ONE_HOUR = '1h'
    FOUR_HOUR = '4h'


@dataclass
class TimeframeConfig:
    name: str
    duration_seconds: int
    variant: str
    slug_format: str


@dataclass
class CryptoPriceData:
    symbol: str
    timeframe: str
    timestamp: int
    open_price: Optional[float]
    close_price: Optional[float]
    completed: bool
    incomplete: bool


@dataclass
class CryptoMarketData:
    condition_id: str
    symbol: str
    timeframe: str
    slug: str
    question: str
    start_date: int
    volume: float
    liquidity: float
    active: bool
    closed: bool
    outcomes: List[Dict]
