from typing import List, Dict, Optional
from datetime import datetime

from .polymarket_client import PolymarketClient
from .gigabrain_client import GigaBrainClient
from .dune_client import DuneClient
from .trader import PolymarketTrader
from .copytrading import CopyTradingService, HourlyScheduler
from .fetchers import CryptoFetcherManager
from .models import Timeframe
from .config import (
    WALLET_ADDRESS,
    POLYMARKET_API_KEY,
    ENABLE_TRADING
)


class PolyBrainServer:
    def __init__(self):
        self.polymarket = PolymarketClient()
        self.gigabrain = GigaBrainClient()
        self.dune = DuneClient()
        self.trader = PolymarketTrader()
        self.copytrading = CopyTradingService()
        self.crypto_fetcher = CryptoFetcherManager()
        self.wallet_address = WALLET_ADDRESS
        self.connected = False
        self.trading_enabled = ENABLE_TRADING
        
        if POLYMARKET_API_KEY:
            self.connected = True
    
    def connect(self) -> bool:
        if not self.wallet_address:
            print("No wallet address configured")
            return False
        
        try:
            _ = self.polymarket.get_user_positions(self.wallet_address, limit=1)
            self.connected = True
            print(f"Connected to Polymarket account: {self.wallet_address}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def get_account_info(self) -> Dict:
        if not self.connected:
            return {}
        
        try:
            positions = self.polymarket.get_user_positions(self.wallet_address)
            trades = self.polymarket.get_user_trades(self.wallet_address, limit=10)
            activity = self.polymarket.get_user_activity(self.wallet_address, limit=10)
            
            return {
                'wallet': self.wallet_address,
                'positions_count': len(positions),
                'recent_trades': len(trades),
                'recent_activity': len(activity),
                'connected': self.connected
            }
        except Exception as e:
            print(f"Error fetching account info: {e}")
            return {}
    
    def get_top_whales(self, top_n: int = 20) -> List[Dict]:
        return self.copytrading.fetch_top_whales(top_n)
    
    def get_whale_activity(self, wallet: str, limit: int = 100) -> List[Dict]:
        return self.polymarket.get_whale_activity(wallet, limit)
    
    def get_crypto_leaderboard(self, time_period: str = 'DAY', limit: int = 25) -> List[Dict]:
        return self.copytrading.leaderboard_fetcher.fetch_crypto_leaderboard(
            time_period=time_period,
            limit=limit
        )
    
    def get_crypto_prices(self, timeframe: Timeframe = Timeframe.FIFTEEN_MIN, symbols: List[str] = None) -> Dict:
        fetcher = self.crypto_fetcher.get_fetcher(timeframe)
        if symbols is None:
            symbols = ['BTC', 'ETH', 'SOL', 'XRP']
        prices = fetcher.get_current_interval_prices(symbols)
        return {p.symbol: {'open': p.open_price, 'close': p.close_price, 'completed': p.completed} for p in prices}
    
    def get_crypto_markets(self, timeframe: Timeframe = Timeframe.FIFTEEN_MIN, symbols: List[str] = None) -> List[Dict]:
        fetcher = self.crypto_fetcher.get_fetcher(timeframe)
        markets = fetcher.get_active_markets(symbols)
        return [{
            'symbol': m.symbol,
            'timeframe': m.timeframe,
            'slug': m.slug,
            'volume': m.volume,
            'liquidity': m.liquidity,
            'question': m.question
        } for m in markets]
    
    def get_dune_whales(self, limit: int = 1000) -> List[Dict]:
        return self.dune.get_polymarket_whales(limit)
    
    def sync_whales(self, top_n: int = 20):
        return self.copytrading.run_hourly_sync(top_n=top_n)
    
    def get_whale_trades(self, wallet: str, limit: int = 100) -> List[Dict]:
        return self.copytrading.fetch_whale_trades(wallet, limit)
    
    def start_whale_monitoring(self, top_n: int = 20, interval: int = 3600):
        def sync_task():
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Syncing whales...")
            self.sync_whales(top_n)
            print("Sync completed.")
        
        scheduler = HourlyScheduler(sync_task, interval_seconds=interval)
        scheduler.start()
        return scheduler
    
    def get_markets(self, limit: int = 50) -> List[Dict]:
        return self.polymarket.get_markets(limit=limit)
    
    def ask_gigabrain(self, message: str) -> Dict:
        return self.gigabrain.chat(message)
    
    def get_all_crypto_data(self) -> Dict:
        result = {}
        for timeframe in [Timeframe.FIFTEEN_MIN, Timeframe.ONE_HOUR, Timeframe.FOUR_HOUR]:
            result[timeframe.value] = {
                'prices': self.get_crypto_prices(timeframe),
                'markets': self.get_crypto_markets(timeframe)
            }
        return result
    
    def place_buy_order(self, token_id: str, size: float, price: float) -> Optional[Dict]:
        if not self.trading_enabled:
            print("Trading is disabled in config")
            return None
        return self.trader.buy(token_id, size, price)
    
    def place_sell_order(self, token_id: str, size: float, price: float) -> Optional[Dict]:
        if not self.trading_enabled:
            print("Trading is disabled in config")
            return None
        return self.trader.sell(token_id, size, price)
    
    def cancel_order(self, order_id: str) -> bool:
        return self.trader.cancel_order(order_id)
    
    def get_open_orders(self) -> List[Dict]:
        return self.trader.get_orders(status='OPEN')
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        return self.trader.get_order_status(order_id)
    
    def get_status(self) -> Dict:
        return {
            'connected': self.connected,
            'wallet': self.wallet_address,
            'trading_enabled': self.trading_enabled,
            'account_info': self.get_account_info() if self.connected else {},
            'services': {
                'polymarket': True,
                'gigabrain': bool(self.gigabrain.api_key),
                'dune': bool(self.dune.api_key),
                'copytrading': True,
                'crypto_fetcher': True,
                'trading': bool(self.trader.api_key and self.trader.api_secret)
            }
        }


def create_server() -> PolyBrainServer:
    server = PolyBrainServer()
    if WALLET_ADDRESS:
        server.connect()
    return server
