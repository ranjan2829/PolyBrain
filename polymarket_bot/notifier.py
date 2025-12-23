import requests
from typing import Dict
from datetime import datetime
from colorama import Fore, Style, init
from .config import DISCORD_WEBHOOK_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

init(autoreset=True)


class Notifier:
    def __init__(self):
        self.discord_webhook = DISCORD_WEBHOOK_URL
        self.telegram_token = TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = TELEGRAM_CHAT_ID
    
    def send_alert(self, spike_data: Dict):
        self._console_alert(spike_data)
        
        if self.discord_webhook:
            self._discord_alert(spike_data)
        
        if self.telegram_token and self.telegram_chat_id:
            self._telegram_alert(spike_data)
    
    def _console_alert(self, spike_data: Dict):
        print(f"\n{Fore.YELLOW}{'='*80}")
        print(f"{Fore.RED}SPIKE DETECTED{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'='*80}{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}Market: {Fore.WHITE}{spike_data['question']}")
        print(f"{Fore.CYAN}Market ID: {Fore.WHITE}{spike_data['market_id']}")
        print(f"{Fore.CYAN}Liquidity: {Fore.WHITE}${spike_data['current_liquidity']:,.2f}")
        print(f"{Fore.CYAN}Volume: {Fore.WHITE}${spike_data['current_volume']:,.2f}")
        
        for spike in spike_data['spikes']:
            if spike['type'] == 'price':
                print(f"\n{Fore.GREEN}PRICE SPIKE: {spike['direction'].upper()}")
                print(f"  Change: {Fore.YELLOW}{spike['change_percent']:.2f}%")
                if 'outcome' in spike:
                    print(f"  Outcome: {spike['outcome']}")
                print(f"  Previous Price: {spike['previous_price']:.4f}")
                print(f"  Current Price: {spike['current_price']:.4f}")
            elif spike['type'] == 'volume':
                print(f"\n{Fore.MAGENTA}VOLUME SPIKE")
                print(f"  Volume Ratio: {Fore.YELLOW}{spike['change_ratio']:.2f}x")
                print(f"  Previous Volume: ${spike['previous_volume']:,.2f}")
                print(f"  Current Volume: ${spike['current_volume']:,.2f}")
                print(f"  Volume Increase: ${spike['volume_increase']:,.2f}")
        
        market_url = f"https://polymarket.com/event/{spike_data.get('slug', spike_data['market_id'])}"
        print(f"\n{Fore.CYAN}Market URL: {Fore.BLUE}{market_url}")
        print(f"{Fore.YELLOW}{'='*80}\n{Style.RESET_ALL}")
    
    def _discord_alert(self, spike_data: Dict):
        try:
            embed = {
                "title": "Polymarket Spike Detected",
                "description": spike_data['question'],
                "color": 0xff0000,
                "fields": [],
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "Polymarket Spike Bot"}
            }
            
            for spike in spike_data['spikes']:
                if spike['type'] == 'price':
                    embed['fields'].append({
                        "name": f"Price Spike ({spike['direction'].upper()})",
                        "value": f"Change: {spike['change_percent']:.2f}%\n"
                                f"Previous: {spike['previous_price']:.4f}\n"
                                f"Current: {spike['current_price']:.4f}",
                        "inline": True
                    })
                elif spike['type'] == 'volume':
                    embed['fields'].append({
                        "name": "Volume Spike",
                        "value": f"Ratio: {spike['change_ratio']:.2f}x\n"
                                f"Previous: ${spike['previous_volume']:,.2f}\n"
                                f"Current: ${spike['current_volume']:,.2f}",
                        "inline": True
                    })
            
            embed['fields'].append({
                "name": "Market Info",
                "value": f"Liquidity: ${spike_data['current_liquidity']:,.2f}\n"
                        f"Volume: ${spike_data['current_volume']:,.2f}",
                "inline": False
            })
            
            market_url = f"https://polymarket.com/event/{spike_data.get('slug', spike_data['market_id'])}"
            embed['url'] = market_url
            
            payload = {"embeds": [embed]}
            response = requests.post(self.discord_webhook, json=payload, timeout=5)
            response.raise_for_status()
        except Exception as e:
            print(f"{Fore.RED}Error sending Discord notification: {e}{Style.RESET_ALL}")
    
    def _telegram_alert(self, spike_data: Dict):
        try:
            message = f"*Polymarket Spike Detected*\n\n"
            message += f"*Market:* {spike_data['question']}\n\n"
            
            for spike in spike_data['spikes']:
                if spike['type'] == 'price':
                    message += f"*Price Spike ({spike['direction'].upper()})*\n"
                    message += f"Change: {spike['change_percent']:.2f}%\n"
                    message += f"Previous: {spike['previous_price']:.4f}\n"
                    message += f"Current: {spike['current_price']:.4f}\n\n"
                elif spike['type'] == 'volume':
                    message += f"*Volume Spike*\n"
                    message += f"Ratio: {spike['change_ratio']:.2f}x\n"
                    message += f"Previous: ${spike['previous_volume']:,.2f}\n"
                    message += f"Current: ${spike['current_volume']:,.2f}\n\n"
            
            message += f"Liquidity: ${spike_data['current_liquidity']:,.2f}\n"
            message += f"Volume: ${spike_data['current_volume']:,.2f}\n\n"
            
            market_url = f"https://polymarket.com/event/{spike_data.get('slug', spike_data['market_id'])}"
            message += f"[View Market]({market_url})"
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False
            }
            
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
        except Exception as e:
            print(f"{Fore.RED}Error sending Telegram notification: {e}{Style.RESET_ALL}")

