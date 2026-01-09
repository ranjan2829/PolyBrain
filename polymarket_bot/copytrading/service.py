import time
from typing import List, Dict, Optional
from datetime import datetime
from .leaderboard import LeaderboardFetcher
from .redis_cache import RedisCache
from ..polymarket_client import PolymarketClient


class CopyTradingService:
    def __init__(self):
        self.leaderboard_fetcher = LeaderboardFetcher()
        self.polymarket_client = PolymarketClient()
        self.redis_cache = RedisCache()
        self.cache_ttl = 3600
    
    def fetch_whale_trades(self, wallet: str, limit: int = 100) -> List[Dict]:
        cached = self.redis_cache.get_whale_trades(wallet)
        if cached:
            return cached
        
        try:
            trades = self.polymarket_client.get_user_trades(wallet, limit=limit)
            self.redis_cache.cache_whale_trades(wallet, trades, self.cache_ttl)
            return trades
        except Exception as e:
            print(f"Error fetching trades for {wallet}: {e}")
            return []
    
    def fetch_whale_data(self, wallet: str) -> Optional[Dict]:
        cached = self.redis_cache.get_whale(wallet)
        if cached:
            return cached
        
        trades = self.fetch_whale_trades(wallet)
        positions = self.polymarket_client.get_user_positions(wallet)
        
        whale_data = {
            'wallet': wallet,
            'trades': trades,
            'positions': positions,
            'trade_count': len(trades),
            'position_count': len(positions),
            'updated_at': datetime.now().isoformat()
        }
        
        self.redis_cache.cache_whale(wallet, whale_data, self.cache_ttl)
        return whale_data
    
    def fetch_top_whales(self, top_n: int = 20) -> List[Dict]:
        cached = self.redis_cache.get_top_whales()
        if cached:
            return cached
        
        whales = self.leaderboard_fetcher.get_top_wallets(
            top_n=top_n,
            period='monthly',
            metric='profit'
        )
        
        self.redis_cache.cache_top_whales(whales, self.cache_ttl)
        return whales
    
    def update_whale_data(self, wallet: str):
        return self.fetch_whale_data(wallet)
    
    def sync_top_whales(self, top_n: int = 20, fetch_trades: bool = True):
        print(f"Syncing top {top_n} whales...")
        
        whales = self.fetch_top_whales(top_n)
        
        if not fetch_trades:
            return whales
        
        updated_whales = []
        for whale in whales:
            wallet = whale.get('wallet')
            if not wallet:
                continue
            
            print(f"Fetching data for {wallet}...")
            whale_data = self.update_whale_data(wallet)
            
            if whale_data:
                whale['trades'] = whale_data.get('trades', [])
                whale['positions'] = whale_data.get('positions', [])
                whale['trade_count'] = whale_data.get('trade_count', 0)
                whale['position_count'] = whale_data.get('position_count', 0)
            
            updated_whales.append(whale)
            time.sleep(0.5)
        
        return updated_whales
    
    def should_refresh(self) -> bool:
        last_update = self.redis_cache.get_last_update_time()
        if not last_update:
            return True
        
        try:
            last_time = datetime.fromisoformat(last_update)
            elapsed = (datetime.now() - last_time).total_seconds()
            return elapsed >= self.cache_ttl
        except:
            return True
    
    def get_cached_whales_with_trades(self) -> List[Dict]:
        whales = self.redis_cache.get_top_whales()
        if not whales:
            return []
        
        result = []
        for whale in whales:
            wallet = whale.get('wallet')
            if not wallet:
                continue
            
            cached_trades = self.redis_cache.get_whale_trades(wallet)
            whale_data = {
                **whale,
                'trades': cached_trades or [],
                'cached': True
            }
            result.append(whale_data)
        
        return result
    
    def get_all_whale_wallets(self) -> List[str]:
        whales = self.get_cached_whales_with_trades()
        return [w.get('wallet') for w in whales if w.get('wallet')]
    
    def run_hourly_sync(self, top_n: int = 20):
        if not self.should_refresh():
            print("Cache is fresh, skipping sync")
            return self.get_cached_whales_with_trades()
        
        return self.sync_top_whales(top_n=top_n, fetch_trades=True)
