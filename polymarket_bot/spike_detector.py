from typing import Dict, Optional
from datetime import datetime
from .redis_storage import RedisStorage
from .config import (
    PRICE_SPIKE_THRESHOLD,
    VOLUME_SPIKE_THRESHOLD,
    ENABLE_PRICE_ALERTS,
    ENABLE_VOLUME_ALERTS,
    MIN_MARKET_LIQUIDITY
)


class MarketSnapshot:
    def __init__(self, market: Dict, timestamp: float):
        self.market_id = market.get('id')
        self.condition_id = market.get('conditionId')
        self.question = market.get('question', 'Unknown Market')
        self.volume = float(market.get('volume', 0))
        self.liquidity = float(market.get('liquidity', 0))
        self.prices = {}
        self.timestamp = timestamp
        
        if 'prices' in market and market['prices']:
            for price_data in market['prices']:
                outcome = price_data.get('outcome')
                price = float(price_data.get('price', 0))
                self.prices[outcome] = price
    
    def to_dict(self) -> Dict:
        return {
            'market_id': self.market_id,
            'condition_id': self.condition_id,
            'question': self.question,
            'volume': self.volume,
            'liquidity': self.liquidity,
            'prices': self.prices,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        snapshot = cls({}, data.get('timestamp', datetime.now().timestamp()))
        snapshot.market_id = data.get('market_id')
        snapshot.condition_id = data.get('condition_id')
        snapshot.question = data.get('question', 'Unknown Market')
        snapshot.volume = float(data.get('volume', 0))
        snapshot.liquidity = float(data.get('liquidity', 0))
        snapshot.prices = data.get('prices', {})
        snapshot.timestamp = data.get('timestamp', datetime.now().timestamp())
        return snapshot
    
    def get_avg_price(self) -> float:
        if not self.prices:
            return 0.0
        return sum(self.prices.values()) / len(self.prices)
    
    def get_max_price(self) -> float:
        if not self.prices:
            return 0.0
        return max(self.prices.values())
    
    def get_min_price(self) -> float:
        if not self.prices:
            return 0.0
        return min(self.prices.values())
    
    def get_best_outcome_price(self) -> tuple:
        if not self.prices:
            return None, 0.0
        best_outcome = min(self.prices.items(), key=lambda x: x[1])
        return best_outcome[0], best_outcome[1]


class SpikeDetector:
    def __init__(self, redis_storage: RedisStorage):
        self.redis = redis_storage
    
    def add_snapshot(self, market: Dict):
        snapshot = MarketSnapshot(market, datetime.now().timestamp())
        self.redis.store_market_snapshot(snapshot.market_id, snapshot.to_dict())
    
    def detect_spikes(self, market: Dict, orderbook_data: Optional[Dict] = None) -> Optional[Dict]:
        snapshot = MarketSnapshot(market, datetime.now().timestamp())
        market_id = snapshot.market_id
        condition_id = snapshot.condition_id
        
        if snapshot.liquidity < MIN_MARKET_LIQUIDITY:
            return None
        
        previous_data = self.redis.get_previous_snapshot(market_id)
        if not previous_data:
            self.redis.store_market_snapshot(market_id, snapshot.to_dict())
            return None
        
        previous_snapshot = MarketSnapshot.from_dict(previous_data)
        spikes = []
        
        if orderbook_data and isinstance(orderbook_data, dict):
            current_prices = {}
            for outcome_name, ob in orderbook_data.items():
                if not isinstance(ob, dict):
                    continue
                asks = ob.get('asks', [])
                bids = ob.get('bids', [])
                price = 0.0
                if asks and len(asks) > 0:
                    best_ask = asks[0]
                    price = float(best_ask.get('price') or best_ask.get('px') or best_ask.get('p') or 0)
                elif bids and len(bids) > 0:
                    best_bid = bids[0]
                    price = float(best_bid.get('price') or best_bid.get('px') or best_bid.get('p') or 0)
                
                if price > 0:
                    current_prices[outcome_name] = price
            
            if current_prices:
                snapshot.prices = current_prices
        
        if ENABLE_PRICE_ALERTS:
            price_spike = self._detect_price_spike(previous_snapshot, snapshot)
            if price_spike:
                spikes.append(price_spike)
        
        if ENABLE_VOLUME_ALERTS:
            volume_spike = self._detect_volume_spike(previous_snapshot, snapshot)
            if volume_spike:
                spikes.append(volume_spike)
        
        if spikes:
            return {
                'market_id': market_id,
                'question': snapshot.question,
                'slug': market.get('slug', ''),
                'condition_id': snapshot.condition_id,
                'spikes': spikes,
                'current_volume': snapshot.volume,
                'current_liquidity': snapshot.liquidity,
                'current_prices': snapshot.prices,
                'timestamp': snapshot.timestamp,
                'snapshot': snapshot
            }
        
        return None
    
    def _detect_price_spike(self, previous: MarketSnapshot, current: MarketSnapshot) -> Optional[Dict]:
        best_spike = None
        best_change = 0
        
        for outcome in ['Yes', 'No']:
            if outcome not in current.prices or outcome not in previous.prices:
                continue
            
            curr_price = current.prices[outcome]
            prev_price = previous.prices[outcome]
            
            if prev_price <= 0 or curr_price <= 0:
                continue
            
            outcome_change = (curr_price - prev_price) / prev_price
            abs_change = abs(outcome_change)
            
            if abs_change >= PRICE_SPIKE_THRESHOLD and abs_change > best_change:
                best_change = abs_change
                best_spike = {
                    'type': 'price',
                    'direction': 'up' if outcome_change > 0 else 'down',
                    'change_percent': abs_change * 100,
                    'previous_price': prev_price,
                    'current_price': curr_price,
                    'outcome': outcome,
                    'threshold': PRICE_SPIKE_THRESHOLD * 100
                }
        
        return best_spike
    
    def _detect_volume_spike(self, previous: MarketSnapshot, current: MarketSnapshot) -> Optional[Dict]:
        if previous.volume == 0:
            return None
        
        volume_ratio = current.volume / previous.volume if previous.volume > 0 else 0
        
        if volume_ratio >= VOLUME_SPIKE_THRESHOLD:
            return {
                'type': 'volume',
                'change_ratio': volume_ratio,
                'previous_volume': previous.volume,
                'current_volume': current.volume,
                'volume_increase': current.volume - previous.volume,
                'threshold': VOLUME_SPIKE_THRESHOLD
            }
        
        return None

