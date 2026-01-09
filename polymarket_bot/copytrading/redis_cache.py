import json
import redis
from typing import Dict, List, Optional, Any
from datetime import datetime
from ..config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD


class RedisCache:
    def __init__(self):
        try:
            self.client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD if REDIS_PASSWORD else None,
                decode_responses=True
            )
            self.client.ping()
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.client = None
    
    def _key(self, prefix: str, identifier: str) -> str:
        return f"copytrading:{prefix}:{identifier}"
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        if not self.client:
            return False
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return self.client.setex(key, ttl, value)
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        if not self.client:
            return None
        try:
            value = self.client.get(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except:
                return value
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    def delete(self, key: str):
        if not self.client:
            return False
        try:
            return self.client.delete(key)
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        if not self.client:
            return False
        try:
            return self.client.exists(key) > 0
        except:
            return False
    
    def cache_whale(self, wallet: str, data: Dict, ttl: int = 3600):
        key = self._key("whale", wallet)
        return self.set(key, data, ttl)
    
    def get_whale(self, wallet: str) -> Optional[Dict]:
        key = self._key("whale", wallet)
        return self.get(key)
    
    def cache_whale_trades(self, wallet: str, trades: List[Dict], ttl: int = 3600):
        key = self._key("whale_trades", wallet)
        return self.set(key, trades, ttl)
    
    def get_whale_trades(self, wallet: str) -> Optional[List[Dict]]:
        key = self._key("whale_trades", wallet)
        return self.get(key)
    
    def cache_top_whales(self, whales: List[Dict], ttl: int = 3600):
        key = self._key("top", "whales")
        metadata = {
            'whales': whales,
            'updated_at': datetime.now().isoformat(),
            'count': len(whales)
        }
        return self.set(key, metadata, ttl)
    
    def get_top_whales(self) -> Optional[List[Dict]]:
        key = self._key("top", "whales")
        data = self.get(key)
        if data and isinstance(data, dict):
            return data.get('whales', [])
        return None
    
    def get_last_update_time(self) -> Optional[str]:
        key = self._key("top", "whales")
        data = self.get(key)
        if data and isinstance(data, dict):
            return data.get('updated_at')
        return None
