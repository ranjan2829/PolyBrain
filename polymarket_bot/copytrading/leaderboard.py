import requests
import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class LeaderboardEntry:
    rank: int
    wallet_address: Optional[str]
    username: Optional[str]
    profit: float
    volume: float


class LeaderboardFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html',
            'Referer': 'https://polymarket.com/',
            'Origin': 'https://polymarket.com'
        })
        self.base_url = 'https://polymarket.com'
        self.data_api_url = 'https://data-api.polymarket.com'
    
    def _parse_profit(self, profit_str: str) -> float:
        profit_str = profit_str.replace('+', '').replace('$', '').replace(',', '').strip()
        try:
            return float(profit_str)
        except:
            return 0.0
    
    def _parse_volume(self, volume_str: str) -> float:
        volume_str = volume_str.replace('$', '').replace(',', '').strip()
        try:
            return float(volume_str)
        except:
            return 0.0
    
    def _extract_wallet_address(self, text: str) -> Optional[str]:
        eth_address_pattern = r'0x[a-fA-F0-9]{40}'
        match = re.search(eth_address_pattern, text)
        if match:
            return match.group(0).lower()
        return None
    
    def fetch_leaderboard_api(
        self,
        period: str = 'monthly',
        metric: str = 'profit',
        limit: int = 100,
        offset: int = 0
    ) -> List[LeaderboardEntry]:
        try:
            url = f'{self.data_api_url}/leaderboard'
            params = {
                'period': period,
                'metric': metric,
                'limit': limit,
                'offset': offset
            }
            
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                entries = []
                
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get('entries', []) or data.get('data', []) or []
                else:
                    return []
                
                for idx, item in enumerate(items, start=offset + 1):
                    wallet = item.get('address') or item.get('wallet') or item.get('user')
                    if not wallet:
                        wallet = self._extract_wallet_address(str(item))
                    
                    profit_str = item.get('profit', '') or item.get('profitLoss', '') or item.get('pnl', '') or '0'
                    volume_str = item.get('volume', '') or '0'
                    
                    entry = LeaderboardEntry(
                        rank=item.get('rank', idx),
                        wallet_address=wallet.lower() if wallet else None,
                        username=item.get('username') or item.get('name') or None,
                        profit=self._parse_profit(str(profit_str)),
                        volume=self._parse_volume(str(volume_str))
                    )
                    entries.append(entry)
                
                return entries
        except Exception as e:
            print(f"API fetch failed: {e}")
        
        return []
    
    def fetch_leaderboard_html(
        self,
        period: str = 'monthly',
        metric: str = 'profit'
    ) -> List[LeaderboardEntry]:
        try:
            url = f'{self.base_url}/leaderboard/overall/{period}/{metric}'
            resp = self.session.get(url, timeout=15)
            
            if resp.status_code == 200:
                html = resp.text
                entries = []
                
                wallet_pattern = r'0x[a-fA-F0-9]{40}'
                wallets = re.findall(wallet_pattern, html)
                unique_wallets = list(dict.fromkeys(wallets))
                
                profit_pattern = r'\+\$[\d,]+'
                profits = re.findall(profit_pattern, html)
                
                volume_pattern = r'\$[\d,]+'
                volumes = re.findall(volume_pattern, html)
                
                rank = 1
                for i, wallet in enumerate(unique_wallets[:100]):
                    profit = self._parse_profit(profits[i]) if i < len(profits) else 0.0
                    volume = self._parse_volume(volumes[i * 2 + 1]) if i * 2 + 1 < len(volumes) else 0.0
                    
                    entry = LeaderboardEntry(
                        rank=rank,
                        wallet_address=wallet.lower(),
                        username=None,
                        profit=profit,
                        volume=volume
                    )
                    entries.append(entry)
                    rank += 1
                
                return entries
        except Exception as e:
            print(f"HTML fetch failed: {e}")
        
        return []
    
    def fetch_leaderboard(
        self,
        period: str = 'monthly',
        metric: str = 'profit',
        limit: int = 100
    ) -> List[LeaderboardEntry]:
        entries = self.fetch_leaderboard_api(period, metric, limit)
        if not entries:
            entries = self.fetch_leaderboard_html(period, metric)
        return entries[:limit]
    
    def get_wallet_addresses(
        self,
        period: str = 'monthly',
        metric: str = 'profit',
        limit: int = 100,
        min_profit: float = 0.0
    ) -> List[str]:
        entries = self.fetch_leaderboard(period, metric, limit)
        wallets = []
        for entry in entries:
            if entry.wallet_address and entry.profit >= min_profit:
                wallets.append(entry.wallet_address)
        return wallets
    
    def get_top_wallets(
        self,
        top_n: int = 20,
        period: str = 'monthly',
        metric: str = 'profit'
    ) -> List[Dict]:
        entries = self.fetch_leaderboard(period, metric, top_n)
        result = []
        for entry in entries:
            if entry.wallet_address:
                result.append({
                    'rank': entry.rank,
                    'wallet': entry.wallet_address,
                    'username': entry.username,
                    'profit': entry.profit,
                    'volume': entry.volume
                })
        return result
    
    def fetch_crypto_leaderboard(
        self,
        category: str = 'CRYPTO',
        time_period: str = 'DAY',
        order_by: str = 'PNL',
        limit: int = 25
    ) -> List[Dict]:
        try:
            url = f'{self.data_api_url}/v1/leaderboard'
            params = {
                'category': category,
                'timePeriod': time_period,
                'orderBy': order_by,
                'limit': limit
            }
            
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get('data', []) or data.get('entries', []) or []
                
                return []
        except Exception as e:
            print(f"Crypto leaderboard fetch failed: {e}")
        
        return []
    
    def get_crypto_wallet_addresses(
        self,
        time_period: str = 'DAY',
        order_by: str = 'PNL',
        limit: int = 25
    ) -> List[str]:
        entries = self.fetch_crypto_leaderboard(
            category='CRYPTO',
            time_period=time_period,
            order_by=order_by,
            limit=limit
        )
        
        wallets = []
        for entry in entries:
            wallet = entry.get('user') or entry.get('address') or entry.get('wallet') or entry.get('taker')
            if wallet:
                wallets.append(wallet.lower() if isinstance(wallet, str) else str(wallet).lower())
        
        return wallets
