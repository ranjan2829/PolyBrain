from typing import List, Dict, Optional
from colorama import Fore, Style
from .redis_storage import RedisStorage
from .trader import PolymarketTrader
from .polymarket_client import PolymarketClient
from .config import MAX_POSITIONS, MAX_POSITION_SIZE


class PositionManager:
    def __init__(self, redis_storage: RedisStorage, trader: PolymarketTrader, client: PolymarketClient):
        self.redis = redis_storage
        self.trader = trader
        self.client = client
    
    def get_active_positions(self) -> List[Dict]:
        return self.redis.get_all_active_positions()
    
    def can_open_new_position(self) -> bool:
        active_positions = self.get_active_positions()
        return len(active_positions) < MAX_POSITIONS
    
    def monitor_positions(self):
        active_positions = self.get_active_positions()
        
        if not active_positions:
            return
        
        print(f"{Fore.CYAN}Monitoring {len(active_positions)} active position(s)...{Style.RESET_ALL}")
        
        for position in active_positions:
            try:
                condition_id = position.get('condition_id')
                if not condition_id:
                    continue
                
                market_id = position.get('market_id')
                latest_snapshot = self.redis.get_latest_snapshot(market_id)
                
                if not latest_snapshot:
                    markets = self.client.get_markets(limit=100, active=True)
                    current_market = next(
                        (m for m in markets if m.get('conditionId') == condition_id or m.get('id') == market_id),
                        None
                    )
                    
                    if not current_market:
                        continue
                    
                    outcome = position.get('outcome')
                    current_price = None
                    
                    if 'prices' in current_market and current_market['prices']:
                        for price_data in current_market['prices']:
                            if price_data.get('outcome') == outcome:
                                current_price = float(price_data.get('price', 0))
                                break
                    
                    if current_price is None or current_price == 0:
                        continue
                else:
                    outcome = position.get('outcome')
                    prices = latest_snapshot.get('prices', {})
                    current_price = prices.get(outcome, position.get('buy_price', 0))
                    
                    if current_price == 0:
                        continue
                
                profit_pct = self.trader.check_position_profit(position, current_price)
                
                self.redis.update_position_profit(
                    position['position_id'],
                    current_price,
                    profit_pct
                )
                
                should_sell, reason = self.trader.should_sell(position, current_price)
                
                if should_sell:
                    print(f"{Fore.YELLOW}{reason}{Style.RESET_ALL}")
                    self.trader.sell_position(position, current_price)
                else:
                    status_color = Fore.GREEN if profit_pct > 0 else Fore.RED
                    print(f"{Fore.CYAN}Position: {position['market_question'][:50]}...")
                    print(f"{status_color}Profit: {profit_pct:.2f}% | Price: ${current_price:.4f}{Style.RESET_ALL}")
                    
            except Exception as e:
                print(f"{Fore.RED}Error monitoring position {position.get('position_id', 'unknown')}: {e}{Style.RESET_ALL}")
    
    def open_position_on_spike(self, spike_data: Dict, investment_amount: Optional[float] = None) -> Optional[Dict]:
        if not self.can_open_new_position():
            print(f"{Fore.YELLOW}Maximum positions ({MAX_POSITIONS}) reached. Skipping trade.{Style.RESET_ALL}")
            return None
        
        if investment_amount is None:
            investment_amount = MAX_POSITION_SIZE
        
        price_spikes = [s for s in spike_data.get('spikes', []) if s.get('type') == 'price' and s.get('direction') == 'up']
        
        if not price_spikes:
            return None
        
        return self.trader.buy_on_spike(spike_data, investment_amount)
    
    def get_portfolio_summary(self) -> Dict:
        active_positions = self.get_active_positions()
        
        total_investment = sum(p.get('investment', 0) for p in active_positions)
        total_profit = 0.0
        total_profit_pct = 0.0
        
        for position in active_positions:
            current_price = position.get('current_price', position.get('buy_price', 0))
            profit_pct = self.trader.check_position_profit(position, current_price)
            profit = position.get('investment', 0) * (profit_pct / 100)
            total_profit += profit
        
        if total_investment > 0:
            total_profit_pct = (total_profit / total_investment) * 100
        
        return {
            'active_positions': len(active_positions),
            'total_investment': total_investment,
            'total_profit': total_profit,
            'total_profit_pct': total_profit_pct
        }

