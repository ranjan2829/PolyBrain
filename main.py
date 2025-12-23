#!/usr/bin/env python3
import time
import signal
import sys
from datetime import datetime
from colorama import Fore, Style, init
from polymarket_bot import (
    PolymarketClient,
    SpikeDetector,
    Notifier,
    RedisStorage,
    PolymarketTrader,
    PositionManager,
    POLL_INTERVAL,
    MARKET_LIMIT,
    ENABLE_TRADING,
    PRICE_SPIKE_THRESHOLD
)

init(autoreset=True)

running = True


def signal_handler(sig, frame):
    global running
    print(f"\n{Fore.YELLOW}Shutting down gracefully...{Style.RESET_ALL}")
    running = False
    sys.exit(0)


def main():
    global running
    sample_bet_done = False
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        print(f"{Fore.CYAN}Connecting to Redis...{Style.RESET_ALL}")
        redis_storage = RedisStorage()
        print(f"{Fore.GREEN}Redis connected{Style.RESET_ALL}\n")
    except Exception as e:
        print(f"{Fore.RED}Failed to connect to Redis: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Please ensure Redis is running and configured correctly.{Style.RESET_ALL}")
        sys.exit(1)
    
    client = PolymarketClient()
    detector = SpikeDetector(redis_storage)
    notifier = Notifier()
    trader = PolymarketTrader(redis_storage)
    position_manager = PositionManager(redis_storage, trader, client)
    
    print(f"{Fore.GREEN}{'='*80}")
    print(f"{Fore.GREEN}Polymarket Spike Trading Bot")
    print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Polling interval: {POLL_INTERVAL} seconds")
    print(f"{Fore.CYAN}Monitoring up to {MARKET_LIMIT} markets")
    print(f"{Fore.CYAN}Spike threshold: {PRICE_SPIKE_THRESHOLD*100:.2f}%")
    print(f"{Fore.CYAN}Trading enabled: {ENABLE_TRADING}")
    
    if ENABLE_TRADING and trader.can_trade():
        print(f"{Fore.GREEN}Trading configured and ready{Style.RESET_ALL}")
    elif ENABLE_TRADING:
        print(f"{Fore.YELLOW}Trading enabled but not configured (check PRIVATE_KEY in .env){Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}Trading disabled (set ENABLE_TRADING=true to enable){Style.RESET_ALL}")
    
    print(f"{Fore.CYAN}Starting monitoring...{Style.RESET_ALL}\n")
    
    iteration = 0
    
    while running:
        try:
            iteration += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{Fore.BLUE}[{current_time}] Iteration #{iteration} - Fetching markets...{Style.RESET_ALL}")
            
            if ENABLE_TRADING and trader.can_trade():
                position_manager.monitor_positions()
                
                if iteration % 10 == 0:
                    portfolio = position_manager.get_portfolio_summary()
                    print(f"\n{Fore.MAGENTA}{'='*80}")
                    print(f"{Fore.MAGENTA}Portfolio Summary")
                    print(f"{Fore.MAGENTA}{'='*80}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Active Positions: {portfolio['active_positions']}")
                    print(f"{Fore.CYAN}Total Investment: ${portfolio['total_investment']:.2f}")
                    profit_color = Fore.GREEN if portfolio['total_profit'] >= 0 else Fore.RED
                    print(f"{profit_color}Total Profit: ${portfolio['total_profit']:.2f} ({portfolio['total_profit_pct']:.2f}%)")
                    print(f"{Fore.MAGENTA}{'='*80}\n{Style.RESET_ALL}")
            
            markets = client.get_markets(limit=MARKET_LIMIT, active=True)
            
            # Sort markets by volume/liquidity (descending) as a proxy for rising interest
            def _metric(m):
                vol = float(m.get("volume", 0) or 0)
                liq = float(m.get("liquidity", 0) or 0)
                return (vol, liq)
            
            markets = sorted(markets, key=_metric, reverse=True)
            
            print(f"{Fore.CYAN}Scanning {len(markets)} markets (sorted by volume/liquidity){Style.RESET_ALL}")
            
            # Attempt one sample bet (once) using first market with an orderbook ask
            if ENABLE_TRADING and trader.can_trade() and not sample_bet_done:
                for m in markets:
                    cid = m.get("conditionId") or m.get("id")
                    if not cid:
                        continue
                    ob = client.get_orderbook(cid)
                    if not ob:
                        continue
                    asks = ob.get("asks", [])
                    if not asks:
                        continue
                    best_ask = asks[0]
                    token_id = best_ask.get("token_id") or cid
                    price = str(best_ask.get("price") or best_ask.get("px") or best_ask.get("p") or "0.01")
                    size = "0.01"
                    print(f"{Fore.MAGENTA}Placing sample buy on {cid[:8]}... price={price} size={size}{Style.RESET_ALL}")
                    trader._place_order(token_id, "buy", size=size, price=price)
                    sample_bet_done = True
                    break
            
            if not markets:
                print(f"{Fore.YELLOW}No markets found. Retrying in {POLL_INTERVAL} seconds...{Style.RESET_ALL}")
                time.sleep(POLL_INTERVAL)
                continue
            
            print(f"{Fore.GREEN}Found {len(markets)} markets. Analyzing for spikes...{Style.RESET_ALL}")
            
            spike_count = 0
            trades_executed = 0
            
            for market in markets:
                if not running:
                    break
                
                detector.add_snapshot(market)
                spike_data = detector.detect_spikes(market)
                
                if spike_data:
                    spike_count += 1
                    notifier.send_alert(spike_data)
                    
                    if ENABLE_TRADING and trader.can_trade():
                        position = position_manager.open_position_on_spike(spike_data)
                        if position:
                            trades_executed += 1
                            print(f"{Fore.GREEN}Position opened: {position['position_id'][:8]}...{Style.RESET_ALL}")
            
            if spike_count == 0:
                print(f"{Fore.GREEN}No spikes detected. Monitoring continues...{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Detected {spike_count} spike(s)!")
                if ENABLE_TRADING and trader.can_trade():
                    print(f"{Fore.CYAN}Executed {trades_executed} trade(s){Style.RESET_ALL}")
            
            print(f"{Fore.CYAN}Waiting {POLL_INTERVAL} seconds until next check...\n{Style.RESET_ALL}")
            
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"{Fore.RED}Error in main loop: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
            print(f"{Fore.YELLOW}Retrying in {POLL_INTERVAL} seconds...{Style.RESET_ALL}")
            time.sleep(POLL_INTERVAL)
    
    if ENABLE_TRADING and trader.can_trade():
        print(f"\n{Fore.MAGENTA}{'='*80}")
        print(f"{Fore.MAGENTA}Final Portfolio Summary")
        print(f"{Fore.MAGENTA}{'='*80}{Style.RESET_ALL}")
        portfolio = position_manager.get_portfolio_summary()
        print(f"{Fore.CYAN}Active Positions: {portfolio['active_positions']}")
        print(f"{Fore.CYAN}Total Investment: ${portfolio['total_investment']:.2f}")
        profit_color = Fore.GREEN if portfolio['total_profit'] >= 0 else Fore.RED
        print(f"{profit_color}Total Profit: ${portfolio['total_profit']:.2f} ({portfolio['total_profit_pct']:.2f}%)")
        print(f"{Fore.MAGENTA}{'='*80}{Style.RESET_ALL}")
    
    print(f"{Fore.YELLOW}Bot stopped.{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
