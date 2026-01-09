from polymarket_bot.copytrading import CopyTradingService, HourlyScheduler
import time

if __name__ == "__main__":
    service = CopyTradingService()
    
    print("Starting copytrading service...")
    print("Fetching top 20 whales and their trades...")
    
    whales = service.run_hourly_sync(top_n=20)
    
    print(f"\nFound {len(whales)} whales:")
    for whale in whales:
        wallet = whale.get('wallet', 'Unknown')
        profit = whale.get('profit', 0)
        trade_count = whale.get('trade_count', 0)
        print(f"{wallet} | Profit: ${profit:,.2f} | Trades: {trade_count}")
    
    def sync_task():
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running hourly sync...")
        service.run_hourly_sync(top_n=20)
        print("Sync completed.")
    
    scheduler = HourlyScheduler(sync_task, interval_seconds=3600)
    scheduler.start()
    
    print("\nScheduler started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()
