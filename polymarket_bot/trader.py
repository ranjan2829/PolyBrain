import uuid
import requests
import json
import time
import hmac
import hashlib
import base64
from typing import Dict, Optional, List
from datetime import datetime
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from mnemonic import Mnemonic
from colorama import Fore, Style
from .config import (
    PRIVATE_KEY,
    MNEMONIC,
    WALLET_ADDRESS,
    PROXY_WALLET,
    MAX_POSITION_SIZE,
    POLYGON_RPC_URL,
    POLYMARKET_API_URL,
    POLYMARKET_API_KEY,
    POLYMARKET_API_SECRET,
    POLYMARKET_PASSPHRASE
)
from .redis_storage import RedisStorage


class PolymarketTrader:
    def __init__(self, redis_storage: RedisStorage):
        self.redis = redis_storage
        self.w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))
        
        if PRIVATE_KEY:
            self.account = Account.from_key(PRIVATE_KEY)
            self.wallet_address = self.account.address
        elif MNEMONIC:
            try:
                mnemo = Mnemonic("english")
                if not mnemo.check(MNEMONIC):
                    raise ValueError("Invalid mnemonic phrase")
                
                Account.enable_unaudited_hdwallet_features()
                self.account = Account.from_mnemonic(MNEMONIC, account_path="m/44'/60'/0'/0/0")
                self.wallet_address = self.account.address
            except Exception as e:
                print(f"{Fore.RED}Error deriving account from mnemonic: {e}{Style.RESET_ALL}")
                self.account = None
                self.wallet_address = WALLET_ADDRESS if WALLET_ADDRESS else None
        else:
            self.account = None
            self.wallet_address = WALLET_ADDRESS if WALLET_ADDRESS else None
        
        if self.account and WALLET_ADDRESS:
            derived_address = self.account.address.lower()
            expected_address = WALLET_ADDRESS.lower()
            
            if derived_address != expected_address:
                print(f"{Fore.YELLOW}Warning: Derived address ({derived_address}) does not match WALLET_ADDRESS ({expected_address}){Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}Wallet address verified: {self.wallet_address}{Style.RESET_ALL}")
        
        self.proxy_wallet = PROXY_WALLET
        self.api_url = POLYMARKET_API_URL
        self.api_key = POLYMARKET_API_KEY
        self.api_secret = POLYMARKET_API_SECRET
        self.passphrase = POLYMARKET_PASSPHRASE
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Polymarket-Spike-Bot/1.0'
        })
        
        if self.api_key and self.api_secret and self.passphrase:
            print(f"{Fore.GREEN}Polymarket API credentials loaded{Style.RESET_ALL}")
        elif self.api_key or self.api_secret or self.passphrase:
            print(f"{Fore.YELLOW}Warning: Some API credentials missing{Style.RESET_ALL}")
    
    def can_trade(self) -> bool:
        return self.account is not None and self.wallet_address is not None
    
    def get_balance(self, check_proxy: bool = True) -> Optional[Dict]:
        if not self.wallet_address:
            return None
        
        try:
            from web3 import Web3
            from .config import USDC_CONTRACT, POLYGON_RPC_URL
            
            w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))
            
            usdc_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function"
                }
            ]
            
            usdc_contract = w3.eth.contract(
                address=Web3.to_checksum_address(USDC_CONTRACT),
                abi=usdc_abi
            )
            
            decimals = usdc_contract.functions.decimals().call()
            
            addresses_to_check = [("main", self.wallet_address)]
            if check_proxy and self.proxy_wallet:
                addresses_to_check.append(("proxy", self.proxy_wallet))
            
            total_usdc = 0.0
            total_native = 0.0
            balances = {}
            
            for label, address in addresses_to_check:
                try:
                    balance_wei = usdc_contract.functions.balanceOf(
                        Web3.to_checksum_address(address)
                    ).call()
                    balance_usdc = balance_wei / (10 ** decimals)
                    total_usdc += balance_usdc
                    
                    native_balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
                    native_balance = w3.from_wei(native_balance_wei, 'ether')
                    total_native += float(native_balance)
                    
                    balances[label] = {
                        "address": address,
                        "usdc_balance": balance_usdc,
                        "native_balance": float(native_balance)
                    }
                except Exception as e:
                    print(f"{Fore.YELLOW}Warning: Could not fetch balance for {label} wallet {address}: {e}{Style.RESET_ALL}")
            
            return {
                "total_usdc_balance": total_usdc,
                "total_usdc_balance_formatted": f"{total_usdc:.2f} USDC",
                "total_native_balance": total_native,
                "total_native_balance_formatted": f"{total_native:.4f} POL",
                "wallet_address": self.wallet_address,
                "balances_by_wallet": balances
            }
        except Exception as e:
            print(f"{Fore.RED}Error fetching balance: {e}{Style.RESET_ALL}")
            return None
    
    def get_existing_positions(self) -> List[Dict]:
        if not self.wallet_address:
            return []
        
        try:
            from .polymarket_client import PolymarketClient
            client = PolymarketClient()
            positions = client.get_user_positions(self.wallet_address)
            return positions
        except Exception as e:
            print(f"{Fore.RED}Error fetching positions: {e}{Style.RESET_ALL}")
            return []
    
    def get_trade_history(self, limit: int = 100) -> List[Dict]:
        if not self.wallet_address:
            return []
        
        try:
            from .polymarket_client import PolymarketClient
            client = PolymarketClient()
            trades = client.get_user_trades(self.wallet_address, limit=limit)
            return trades
        except Exception as e:
            print(f"{Fore.RED}Error fetching trade history: {e}{Style.RESET_ALL}")
            return []
    
    def _sign_message(self, message: str) -> str:
        if not self.account:
            return ""
        message_hash = encode_defunct(text=message)
        signed = self.account.sign_message(message_hash)
        return signed.signature.hex()
    
    def _get_token_id(self, condition_id: str, outcome: str) -> Optional[str]:
        try:
            url = f"{self.api_url}/tokens"
            params = {"token_id": f"{condition_id}-{outcome}"}
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('token_id') or f"{condition_id}-{outcome}"
            return f"{condition_id}-{outcome}"
        except:
            return f"{condition_id}-{outcome}"
    
    def _get_auth_headers(self, method: str, path: str, body: str = "") -> Dict:
        if not (self.api_key and self.api_secret and self.passphrase):
            return {}
        
        try:
            timestamp = str(int(time.time() * 1000))
            message = timestamp + method + path + body
            
            secret_bytes = self.api_secret.encode('utf-8')
            if len(secret_bytes) % 4 != 0:
                secret_bytes += b'=' * (4 - len(secret_bytes) % 4)
            
            try:
                secret_decoded = base64.b64decode(secret_bytes)
            except:
                secret_decoded = self.api_secret.encode('utf-8')
            
            signature = hmac.new(
                secret_decoded,
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
            signature_b64 = base64.b64encode(signature).decode('utf-8')
            
            return {
                'X-API-KEY': self.api_key,
                'X-API-SIGNATURE': signature_b64,
                'X-API-TIMESTAMP': timestamp,
                'X-API-PASSPHRASE': self.passphrase
            }
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Auth header generation failed: {e}{Style.RESET_ALL}")
            return {}
    
    def _place_order(self, token_id: str, side: str, size: str, price: str) -> Optional[Dict]:
        if not self.account:
            return None
        
        timestamp = str(int(time.time() * 1000))
        order_data = {
            "token_id": token_id,
            "side": side,
            "size": size,
            "price": price,
            "expiration": str(int(time.time()) + 86400),
            "nonce": timestamp,
            "maker": self.wallet_address
        }
        
        message = json.dumps(order_data, sort_keys=True)
        signature = self._sign_message(message)
        order_data['signature'] = signature
        
        body = json.dumps(order_data)
        path = "/order"
        headers = self._get_auth_headers("POST", path, body)
        headers.update(self.session.headers)
        
        try:
            url = f"{self.api_url}{path}"
            response = requests.post(url, json=order_data, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                print(f"{Fore.GREEN}Order placed successfully!{Style.RESET_ALL}")
                return response.json()
            else:
                print(f"{Fore.RED}Order failed: {response.status_code} - {response.text[:200]}{Style.RESET_ALL}")
                return None
        except Exception as e:
            print(f"{Fore.RED}Error placing order: {e}{Style.RESET_ALL}")
            return None
    
    def buy_on_spike(self, spike_data: Dict, investment_amount: float) -> Optional[Dict]:
        if not self.can_trade():
            return None
        
        if investment_amount > MAX_POSITION_SIZE:
            investment_amount = MAX_POSITION_SIZE
        
        snapshot = spike_data.get('snapshot')
        if not snapshot:
            return None
        
        outcome, price = snapshot.get_best_outcome_price()
        if not outcome or price == 0:
            return None
        
        condition_id = spike_data.get('condition_id')
        if not condition_id:
            return None
        
        shares = investment_amount / price
        
        token_id = self._get_token_id(condition_id, outcome)
        if not token_id:
            return None
        
        price_str = str(int(price * 10000))
        size_str = str(int(shares * 1000000))
        
        print(f"{Fore.GREEN}Placing BUY order: {shares:.2f} shares @ ${price:.4f} = ${investment_amount:.2f}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Market: {spike_data['question']}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Outcome: {outcome}{Style.RESET_ALL}")
        
        order_result = self._place_order(token_id, "BUY", size_str, price_str)
        
        position_id = str(uuid.uuid4())
        position = {
            'position_id': position_id,
            'market_id': spike_data['market_id'],
            'market_question': spike_data['question'],
            'condition_id': condition_id,
            'outcome': outcome,
            'token_id': token_id,
            'buy_price': price,
            'shares': shares,
            'investment': investment_amount,
            'status': 'open',
            'buy_time': datetime.now().isoformat(),
            'spike_data': spike_data,
            'order_result': order_result
        }
        
        if order_result:
            print(f"{Fore.GREEN}Order placed successfully!{Style.RESET_ALL}")
            self.redis.store_position(position_id, position)
            return position
        else:
            print(f"{Fore.RED}Order placement failed - position not stored{Style.RESET_ALL}")
            return None
    
    def sell_position(self, position: Dict, current_price: float) -> Optional[Dict]:
        if not self.can_trade():
            return None
        
        position_id = position['position_id']
        shares = position['shares']
        token_id = position.get('token_id')
        condition_id = position.get('condition_id')
        outcome = position.get('outcome')
        
        if not token_id and condition_id and outcome:
            token_id = self._get_token_id(condition_id, outcome)
        
        sell_amount = shares * current_price
        profit = sell_amount - position['investment']
        profit_pct = (profit / position['investment']) * 100
        
        print(f"{Fore.YELLOW}Placing SELL order: {shares:.2f} shares @ ${current_price:.4f} = ${sell_amount:.2f}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Market: {position['market_question']}{Style.RESET_ALL}")
        
        if token_id:
            price_str = str(int(current_price * 10000))
            size_str = str(int(shares * 1000000))
            order_result = self._place_order(token_id, "SELL", size_str, price_str)
            
            if order_result:
                print(f"{Fore.GREEN}Sell order placed successfully!{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Warning: Sell order may have failed{Style.RESET_ALL}")
        
        position['sell_price'] = current_price
        position['sell_amount'] = sell_amount
        position['profit'] = profit
        position['profit_pct'] = profit_pct
        position['status'] = 'closed'
        position['sell_time'] = datetime.now().isoformat()
        
        self.redis.store_position(position_id, position)
        self.redis.close_position(position_id)
        
        print(f"{Fore.GREEN if profit > 0 else Fore.RED}Profit: ${profit:.2f} ({profit_pct:.2f}%){Style.RESET_ALL}")
        
        return position
    
    def check_position_profit(self, position: Dict, current_price: float) -> float:
        buy_price = position['buy_price']
        if buy_price == 0:
            return 0.0
        
        profit_pct = ((current_price - buy_price) / buy_price) * 100
        return profit_pct
    
    def should_sell(self, position: Dict, current_price: float):
        from .config import MIN_PROFIT_PCT, MAX_LOSS_PCT
        
        profit_pct = self.check_position_profit(position, current_price)
        
        if profit_pct >= MIN_PROFIT_PCT:
            return True, f"Take profit: {profit_pct:.2f}% >= {MIN_PROFIT_PCT}%"
        
        if profit_pct <= MAX_LOSS_PCT:
            return True, f"Stop loss: {profit_pct:.2f}% <= {MAX_LOSS_PCT}%"
        
        return False, ""
