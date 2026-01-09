from polymarket_bot import create_server

if __name__ == "__main__":
    print("Starting PolyBrain Server...")
    server = create_server()
    
    status = server.get_status()
    print(f"\nServer Status:")
    print(f"  Connected: {status['connected']}")
    print(f"  Wallet: {status.get('wallet', 'Not configured')}")
    print(f"  Trading: {'Enabled' if status['trading_enabled'] else 'Disabled'}")
    
    print(f"\nServices:")
    for service, enabled in status['services'].items():
        print(f"  {service}: {'✓' if enabled else '✗'}")
    
    if status['connected']:
        account = status.get('account_info', {})
        print(f"\nAccount:")
        print(f"  Positions: {account.get('positions_count', 0)}")
        print(f"  Recent Trades: {account.get('recent_trades', 0)}")
    
    print("\nServer ready.")
