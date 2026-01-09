from typing import Dict, Optional, List
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType
from ..config import (
    POLYMARKET_API_URL,
    POLYMARKET_API_KEY,
    POLYMARKET_API_SECRET,
    POLYMARKET_PASSPHRASE,
    WALLET_ADDRESS,
    PRIVATE_KEY,
    PROXY_WALLET
)


class PolymarketTrader:
    CHAIN_ID = 137
    SIGNATURE_TYPE = 2  # Polymarket proxy wallet
    
    def __init__(self):
        self.api_url = POLYMARKET_API_URL or 'https://clob.polymarket.com'
        self.api_key = POLYMARKET_API_KEY
        self.api_secret = POLYMARKET_API_SECRET
        self.passphrase = POLYMARKET_PASSPHRASE
        self.wallet_address = WALLET_ADDRESS
        self.proxy_wallet = PROXY_WALLET
        self.private_key = PRIVATE_KEY
        self.client = None
        self._init_client()
    
    def _init_client(self):
        if not self.private_key:
            print("Warning: PRIVATE_KEY not set. Trading will not work.")
            return
        
        try:
            self.client = ClobClient(
                self.api_url,
                key=self.private_key,
                chain_id=self.CHAIN_ID,
                signature_type=self.SIGNATURE_TYPE,
                funder=self.proxy_wallet,
                creds=ApiCreds(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    api_passphrase=self.passphrase
                ) if self.api_key else None
            )
        except Exception as e:
            print(f"Failed to initialize CLOB client: {e}")
            self.client = None
    
    def place_order(
        self,
        token_id: str,
        side: str,
        size: float,
        price: float,
        order_type: str = 'GTC'
    ) -> Optional[Dict]:
        if not self.client:
            print("Trading client not initialized")
            return None
        
        try:
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=side.upper(),
            )
            
            signed_order = self.client.create_order(order_args)
            result = self.client.post_order(signed_order, orderType=OrderType.GTC)
            
            print(f"Order placed: {side.upper()} {size} @ ${price}")
            return result
        except Exception as e:
            print(f"Error placing order: {e}")
            return None
    
    def buy(self, token_id: str, size: float, price: float, order_type: str = 'GTC') -> Optional[Dict]:
        return self.place_order(token_id, 'BUY', size, price, order_type)
    
    def sell(self, token_id: str, size: float, price: float, order_type: str = 'GTC') -> Optional[Dict]:
        return self.place_order(token_id, 'SELL', size, price, order_type)
    
    def cancel_order(self, order_id: str) -> bool:
        if not self.client:
            return False
        
        try:
            self.client.cancel(order_id)
            return True
        except Exception as e:
            print(f"Error canceling order: {e}")
            return False
    
    def cancel_all(self) -> bool:
        if not self.client:
            return False
        
        try:
            self.client.cancel_all()
            return True
        except Exception as e:
            print(f"Error canceling all orders: {e}")
            return False
    
    def get_orders(self, status: str = 'OPEN') -> List[Dict]:
        if not self.client:
            return []
        
        try:
            orders = self.client.get_orders()
            if status:
                return [o for o in orders if o.get('status') == status]
            return orders
        except Exception as e:
            print(f"Error fetching orders: {e}")
            return []
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        if not self.client:
            return None
        
        try:
            return self.client.get_order(order_id)
        except Exception as e:
            print(f"Error fetching order: {e}")
            return None
    
    def get_balance(self) -> float:
        if not self.client:
            return 0.0
        
        try:
            bal = self.client.get_balance_allowance()
            if bal and 'balance' in bal:
                return float(bal['balance'])
            return 0.0
        except Exception:
            return 0.0
    
    def is_ready(self) -> bool:
        return self.client is not None
