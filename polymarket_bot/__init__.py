from .config import *
from .polymarket_client import PolymarketClient
from .redis_storage import RedisStorage
from .spike_detector import SpikeDetector, MarketSnapshot
from .trader import PolymarketTrader
from .position_manager import PositionManager
from .notifier import Notifier

__version__ = "1.0.0"

