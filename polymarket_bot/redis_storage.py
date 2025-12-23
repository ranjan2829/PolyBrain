import json
import redis
from typing import Dict, List, Optional
from datetime import datetime
from .config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD


class RedisStorage:
    def __init__(self):
        try:
            self.client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD if REDIS_PASSWORD else None,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.client.ping()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")
    
    def store_market_snapshot(self, market_id: str, snapshot_data: Dict):
        key = f"market:{market_id}:snapshot"
        snapshot_data['stored_at'] = datetime.now().isoformat()
        self.client.setex(key, 3600, json.dumps(snapshot_data))
        
        history_key = f"market:{market_id}:history"
        self.client.lpush(history_key, json.dumps(snapshot_data))
        self.client.ltrim(history_key, 0, 9)
        self.client.expire(history_key, 3600)
    
    def get_latest_snapshot(self, market_id: str) -> Optional[Dict]:
        key = f"market:{market_id}:snapshot"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def get_previous_snapshot(self, market_id: str) -> Optional[Dict]:
        history_key = f"market:{market_id}:history"
        data = self.client.lindex(history_key, 1)
        if data:
            return json.loads(data)
        return None
    
    def store_position(self, position_id: str, position_data: Dict):
        key = f"position:{position_id}"
        position_data['updated_at'] = datetime.now().isoformat()
        self.client.setex(key, 86400 * 7, json.dumps(position_data))
        self.client.sadd("active_positions", position_id)
    
    def get_position(self, position_id: str) -> Optional[Dict]:
        key = f"position:{position_id}"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def get_all_active_positions(self) -> List[Dict]:
        position_ids = self.client.smembers("active_positions")
        positions = []
        for pos_id in position_ids:
            pos_data = self.get_position(pos_id)
            if pos_data:
                positions.append(pos_data)
        return positions
    
    def close_position(self, position_id: str):
        self.client.srem("active_positions", position_id)
        self.client.sadd("closed_positions", position_id)
    
    def update_position_profit(self, position_id: str, current_price: float, profit_pct: float):
        position = self.get_position(position_id)
        if position:
            position['current_price'] = current_price
            position['profit_pct'] = profit_pct
            position['profit_amount'] = position.get('investment', 0) * (profit_pct / 100)
            position['updated_at'] = datetime.now().isoformat()
            self.store_position(position_id, position)

