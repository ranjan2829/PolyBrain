import requests
from typing import Dict, Optional, List
from .config import DUNE_API_KEY


class DuneClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or DUNE_API_KEY
        self.base_url = "https://api.dune.com/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def get_query_results(
        self,
        query_id: int,
        limit: int = 1000,
        offset: int = 0
    ) -> Optional[Dict]:
        try:
            url = f'{self.base_url}/query/{query_id}/results'
            params = {
                'limit': limit,
                'offset': offset,
                'api_key': self.api_key
            }
            
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Dune API error: {e}")
            return None
    
    def get_query_rows(
        self,
        query_id: int,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict]:
        result = self.get_query_results(query_id, limit, offset)
        if result and result.get('result'):
            return result['result'].get('rows', [])
        return []
    
    def get_polymarket_whales(self, limit: int = 1000) -> List[Dict]:
        query_id = 6493730
        return self.get_query_rows(query_id, limit=limit)
