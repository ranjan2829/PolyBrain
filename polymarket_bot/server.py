import threading
from typing import List, Dict, Optional
from datetime import datetime

from .core import PolymarketClient, PolymarketTrader
from .api import GigaBrainClient, DuneClient
from .data import Timeframe, CryptoFetcherManager
from .markets import CryptoMarkets
from .scalper import ScalperBot
from .strategy import CryptoTrader
from .copytrading import CopyTradingService, HourlyScheduler
from .db import Database, TradeRepository
from .agent import CopyTradeAgent
from .config import WALLET_ADDRESS, POLYMARKET_API_KEY, ENABLE_TRADING


class PolyBrainServer:
    def __init__(self):
        self.polymarket = PolymarketClient()
        self.gigabrain = GigaBrainClient()
        self.dune = DuneClient()
        self.trader = PolymarketTrader()
        self.copytrading = CopyTradingService()
        self.crypto_fetcher = CryptoFetcherManager()
        self.markets = CryptoMarkets()
        self.crypto_trader = CryptoTrader()
        self.wallet_address = WALLET_ADDRESS
        self.connected = False
        self.trading_enabled = ENABLE_TRADING
        
        self.db = None
        self.repo = None
        self.agent = None
        self.scalper = None
        self.scheduler = None
        self.agent_thread = None
        self.scalper_thread = None
        self.running = False
        
        if POLYMARKET_API_KEY:
            self.connected = True
    
    def connect(self) -> bool:
        if not self.wallet_address:
            print("No wallet address configured")
            return False
        
        try:
            _ = self.polymarket.get_user_positions(self.wallet_address, limit=1)
            self.connected = True
            print(f"Connected to Polymarket: {self.wallet_address}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def connect_db(self) -> bool:
        try:
            self.db = Database()
            self.db.connect()
            self.db.init_tables()
            self.repo = TradeRepository(self.db)
            print("Connected to PostgreSQL")
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
    
    def start_agent(self, top_n: int = 20, interval: int = 60):
        if self.agent_thread and self.agent_thread.is_alive():
            print("Agent already running")
            return
        
        self.agent = CopyTradeAgent()
        self.agent.connect()
        self.running = True
        
        def run():
            self.agent.monitor_whales(top_n=top_n, interval=interval)
        
        self.agent_thread = threading.Thread(target=run, daemon=True)
        self.agent_thread.start()
        print(f"CopyTradeAgent started (monitoring {top_n} whales)")
    
    def stop_agent(self):
        self.running = False
        if self.agent:
            self.agent.close()
        print("Agent stopped")
    
    def start_scalper(self, interval: int = 30):
        if self.scalper_thread and self.scalper_thread.is_alive():
            print("Scalper already running")
            return
        
        self.scalper = ScalperBot()
        
        def run():
            self.scalper.run(interval=interval)
        
        self.scalper_thread = threading.Thread(target=run, daemon=True)
        self.scalper_thread.start()
        print("ScalperBot started")
    
    def stop_scalper(self):
        if self.scalper:
            self.scalper.stop()
        print("Scalper stopped")
    
    def start(self, enable_agent: bool = True, agent_interval: int = 60):
        print("=" * 50)
        print("PolyBrain Server Starting...")
        print("=" * 50)
        
        self.connect()
        self.connect_db()
        
        if enable_agent and self.connected:
            self.start_agent(interval=agent_interval)
        
        self.scheduler = self.start_whale_monitoring()
        
        print("\nServer running. Services:")
        status = self.get_status()
        for service, active in status['services'].items():
            print(f"  {service}: {'✓' if active else '✗'}")
        
        return self
    
    def stop(self):
        print("\nShutting down...")
        self.stop_agent()
        self.stop_scalper()
        if self.scheduler:
            self.scheduler.stop()
        if self.db:
            self.db.close()
        print("Server stopped.")
    
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
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Syncing whales...")
            self.sync_whales(top_n)
        
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
    
    def get_15m_markets(self, symbols: List[str] = None) -> List[Dict]:
        return self.markets.to_dict(self.markets.get_15m(symbols))
    
    def get_1h_markets(self, symbols: List[str] = None) -> List[Dict]:
        return self.markets.to_dict(self.markets.get_1h(symbols))
    
    def get_4h_markets(self, symbols: List[str] = None) -> List[Dict]:
        return self.markets.to_dict(self.markets.get_4h(symbols))
    
    def get_all_markets(self, symbols: List[str] = None) -> Dict[str, List[Dict]]:
        all_markets = self.markets.get_all(symbols)
        return {tf: self.markets.to_dict(mkts) for tf, mkts in all_markets.items()}
    
    def trade_crypto(self, symbol: str, timeframe: str, outcome: str, size: float = None) -> Optional[Dict]:
        return self.crypto_trader.place_trade(symbol, timeframe, outcome, size)
    
    def buy_up(self, symbol: str, timeframe: str, size: float = None) -> Optional[Dict]:
        return self.crypto_trader.buy_up(symbol, timeframe, size)
    
    def buy_down(self, symbol: str, timeframe: str, size: float = None) -> Optional[Dict]:
        return self.crypto_trader.buy_down(symbol, timeframe, size)
    
    def auto_trade_crypto(self, strategy: str = 'momentum') -> List[Dict]:
        return self.crypto_trader.scan_and_trade(strategy)
    
    def get_trading_status(self) -> Dict:
        return self.crypto_trader.get_status()
    
    def place_buy_order(self, token_id: str, size: float, price: float) -> Optional[Dict]:
        if not self.trading_enabled:
            print("Trading disabled")
            return None
        return self.trader.buy(token_id, size, price)
    
    def place_sell_order(self, token_id: str, size: float, price: float) -> Optional[Dict]:
        if not self.trading_enabled:
            print("Trading disabled")
            return None
        return self.trader.sell(token_id, size, price)
    
    def cancel_order(self, order_id: str) -> bool:
        return self.trader.cancel_order(order_id)
    
    def get_open_orders(self) -> List[Dict]:
        return self.trader.get_orders(status='OPEN')
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        return self.trader.get_order_status(order_id)
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        if self.repo:
            return self.repo.get_trade_history(limit)
        return []
    
    def get_pnl_stats(self) -> Dict:
        if self.repo:
            return self.repo.get_pnl_summary()
        return {}
    
    def get_status(self) -> Dict:
        return {
            'connected': self.connected,
            'wallet': self.wallet_address,
            'trading_enabled': self.trading_enabled,
            'agent_running': self.agent_thread.is_alive() if self.agent_thread else False,
            'services': {
                'polymarket': self.connected,
                'gigabrain': bool(self.gigabrain.api_key),
                'dune': bool(self.dune.api_key),
                'database': self.db is not None,
                'copytrading': True,
                'crypto_fetcher': True,
                'trading': bool(self.trader.api_key and self.trader.api_secret),
                'agent': self.agent is not None,
                'scalper': self.scalper is not None
            }
        }


def create_server() -> PolyBrainServer:
    return PolyBrainServer()
