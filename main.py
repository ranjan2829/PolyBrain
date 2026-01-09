import time
from polymarket_bot.server import create_server


def main():
    print("=" * 60)
    print("PolyBrain Server - Unified Polymarket Trading Platform")
    print("=" * 60)
    
    server = create_server()
    
    status = server.get_status()
    print("\nServer Status:")
    print(f"  Connected: {status['connected']}")
    print(f"  Wallet: {status.get('wallet', 'Not configured')}")
    print(f"  Trading Enabled: {status['trading_enabled']}")
    print(f"\nServices:")
    for service, enabled in status['services'].items():
        print(f"  {service}: {'✓' if enabled else '✗'}")
    
    if status['connected']:
        account = server.get_account_info()
        print(f"\nAccount Info:")
        print(f"  Positions: {account.get('positions_count', 0)}")
        print(f"  Recent Trades: {account.get('recent_trades', 0)}")
    
    print("\n" + "=" * 60)
    print("Starting services...")
    print("=" * 60)
    
    scheduler = server.start_whale_monitoring(top_n=20, interval=3600)
    
    print("\nServer running. Press Ctrl+C to stop.")
    print("\nAvailable commands (in interactive mode):")
    print("  server.get_top_whales(20)")
    print("  server.get_crypto_prices()")
    print("  server.get_markets(50)")
    print("  server.get_status()")
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        scheduler.stop()
        print("Server stopped.")


if __name__ == "__main__":
    main()
