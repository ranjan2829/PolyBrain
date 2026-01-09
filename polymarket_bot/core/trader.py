import requests
import time
import json
import hmac
import hashlib
import base64
from typing import Dict, Optional, List
from ..config import POLYMARKET_API_URL, POLYMARKET_API_KEY, POLYMARKET_API_SECRET, POLYMARKET_PASSPHRASE, WALLET_ADDRESS


class PolymarketTrader:
    def __init__(self):
        self.api_url = POLYMARKET_API_URL
        self.api_key = POLYMARKET_API_KEY
        self.api_secret = POLYMARKET_API_SECRET
        self.passphrase = POLYMARKET_PASSPHRASE
        self.wallet_address = WALLET_ADDRESS
        self.session = requests.Session()
        self.chain_id = 137
    
    def _generate_signature(self, timestamp: str, method: str, path: str, body: str = '') -> str:
        if not self.api_secret:
            return ''
        
        message = timestamp + method + path + body
        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_headers(self, method: str, path: str, body: str = '') -> Dict:
        timestamp = str(int(time.time()))
        signature = self._generate_signature(timestamp, method, path, body)
        
        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': self.api_key,
            'X-TIMESTAMP': timestamp,
            'X-SIGNATURE': signature,
        }
        if self.passphrase:
            headers['X-PASSPHRASE'] = self.passphrase
        
        return headers
    
    def place_order(
        self,
        token_id: str,
        side: str,
        size: float,
        price: float,
        order_type: str = 'LIMIT'
    ) -> Optional[Dict]:
        if not self.api_key:
            print("API key not configured")
            return None
        
        if not self.wallet_address:
            print("Wallet address not configured")
            return None
        
        try:
            path = '/orders'
            order_data = {
                'tokenID': token_id,
                'side': side.upper(),
                'size': str(size),
                'price': str(price),
                'orderType': order_type.upper(),
                'chainID': self.chain_id,
            }
            
            body = json.dumps(order_data)
            headers = self._get_headers('POST', path, body)
            
            resp = self.session.post(
                f'{self.api_url}{path}',
                json=order_data,
                headers=headers,
                timeout=30
            )
            
            if resp.status_code in [200, 201]:
                return resp.json()
            else:
                print(f"Order failed: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            print(f"Error placing order: {e}")
            return None
    
    def buy(self, token_id: str, size: float, price: float, order_type: str = 'LIMIT') -> Optional[Dict]:
        return self.place_order(token_id, 'BUY', size, price, order_type)
    
    def sell(self, token_id: str, size: float, price: float, order_type: str = 'LIMIT') -> Optional[Dict]:
        return self.place_order(token_id, 'SELL', size, price, order_type)
    
    def cancel_order(self, order_id: str) -> bool:
        if not self.api_key:
            return False
        
        try:
            path = f'/orders/{order_id}'
            headers = self._get_headers('DELETE', path)
            
            resp = self.session.delete(
                f'{self.api_url}{path}',
                headers=headers,
                timeout=10
            )
            
            return resp.status_code in [200, 204]
        except Exception as e:
            print(f"Error canceling order: {e}")
            return False
    
    def get_orders(self, status: str = 'OPEN') -> List[Dict]:
        if not self.api_key:
            return []
        
        try:
            path = '/orders'
            params = {'status': status}
            headers = self._get_headers('GET', path)
            
            resp = self.session.get(
                f'{self.api_url}{path}',
                params=params,
                headers=headers,
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else []
            return []
        except Exception as e:
            print(f"Error fetching orders: {e}")
            return []
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        if not self.api_key:
            return None
        
        try:
            path = f'/orders/{order_id}'
            headers = self._get_headers('GET', path)
            
            resp = self.session.get(
                f'{self.api_url}{path}',
                headers=headers,
                timeout=10
            )
            
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            print(f"Error fetching order status: {e}")
            return None
