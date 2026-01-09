import subprocess
import json
from typing import Dict, Optional, List
from ..config import GIGABRAIN_API_KEY, GIGABRAIN_BASE_URL


class GigaBrainClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or GIGABRAIN_API_KEY
        self.base_url = (base_url or GIGABRAIN_BASE_URL or 'https://api.gigabrain.gg').rstrip('/')
    
    def chat(self, message: str) -> Dict:
        try:
            cmd = [
                'curl', '-s', '-X', 'POST',
                f'{self.base_url}/v1/chat',
                '-H', f'Authorization: Bearer {self.api_key}',
                '-H', 'Content-Type: application/json',
                '-d', json.dumps({'message': message, 'stream': False}),
                '--max-time', '90'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=100)
            
            if result.returncode != 0:
                return {'error': 'curl failed', 'success': False}
            
            if not result.stdout.strip():
                return {'error': 'empty response', 'success': False}
            
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            return {'error': 'timeout', 'success': False}
        except Exception as e:
            return {'error': str(e), 'success': False}
    
    def get_sessions(self, limit: int = 10) -> List[Dict]:
        try:
            cmd = [
                'curl', '-s',
                f'{self.base_url}/v1/sessions?limit={limit}',
                '-H', f'Authorization: Bearer {self.api_key}',
                '--max-time', '10'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.stdout:
                return json.loads(result.stdout)
            return []
        except Exception:
            return []
