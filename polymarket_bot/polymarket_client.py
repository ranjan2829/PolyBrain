import requests
from typing import List, Dict, Optional
from .config import POLYMARKET_GRAPHQL_URL, POLYMARKET_API_URL


class PolymarketClient:
    def __init__(self):
        self.graphql_url = POLYMARKET_GRAPHQL_URL
        self.api_url = POLYMARKET_API_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Polymarket-Spike-Bot/1.0',
            'Content-Type': 'application/json'
        })
    
    def get_markets(self, limit: int = 50, active: bool = True) -> List[Dict]:
        # Use REST markets endpoint (avoids GraphQL 404)
        try:
            url = "https://gamma-api.polymarket.com/markets"
            params = {
                "limit": limit,
                "active": str(active).lower()
            }
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "markets" in data:
                return data["markets"]
            return []
        except Exception as e:
            print(f"Error fetching markets: {e}")
            return []
    
    def get_market_prices(self, condition_id: str) -> Optional[Dict]:
        try:
            url = f"{self.api_url}/book"
            params = {"token_id": condition_id}
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching prices for {condition_id}: {e}")
            return None
    
    def get_orderbook(self, condition_id: str) -> Optional[Dict]:
        """Fetch CLOB orderbook for a given condition_id/token_id."""
        try:
            url = f"{self.api_url}/book"
            params = {"token_id": condition_id}
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching orderbook for {condition_id}: {e}")
            return None
    
    def get_user_trades(self, wallet_address: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        try:
            url = "https://data-api.polymarket.com/trades"
            params = {
                "user": wallet_address.lower(),
                "limit": limit,
                "offset": offset
            }
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else []
            return []
        except Exception as e:
            print(f"Error fetching trades: {e}")
            return []
    
    def get_user_positions(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        try:
            url = "https://data-api.polymarket.com/positions"
            params = {
                "user": wallet_address.lower(),
                "limit": limit
            }
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else []
            return []
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []
    
    def get_user_activity(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        try:
            url = "https://data-api.polymarket.com/activity"
            params = {
                "user": wallet_address.lower(),
                "limit": limit,
                "sortBy": "TIMESTAMP",
                "sortDirection": "DESC"
            }
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else []
            return []
        except Exception as e:
            print(f"Error fetching activity: {e}")
            return []

