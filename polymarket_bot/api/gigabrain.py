import requests
from typing import Dict, Optional, List
from ..config import GIGABRAIN_API_KEY, GIGABRAIN_BASE_URL


class GigaBrainClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or GIGABRAIN_API_KEY
        self.base_url = (base_url or GIGABRAIN_BASE_URL).rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
    
    def chat(self, message: str, stream: bool = False) -> Dict:
        try:
            resp = self.session.post(
                f'{self.base_url}/v1/chat',
                json={'message': message, 'stream': stream},
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {'error': str(e), 'success': False}
    
    def get_sessions(self, limit: int = 10, offset: int = 0) -> List[Dict]:
        try:
            resp = self.session.get(
                f'{self.base_url}/v1/sessions',
                params={'limit': limit, 'offset': offset},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get('sessions', [])
        except Exception:
            return []
