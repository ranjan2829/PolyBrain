from polymarket_bot.copytrading import LeaderboardFetcher

if __name__ == "__main__":
    fetcher = LeaderboardFetcher()
    
    print("Fetching top whales from Polymarket leaderboard...")
    wallets = fetcher.get_wallet_addresses(period='monthly', metric='profit', limit=100)
    
    print(f"\nFound {len(wallets)} wallet addresses:")
    for i, wallet in enumerate(wallets, 1):
        print(f"{i}. {wallet}")
    
    print("\nTop 20 wallets with details:")
    top_wallets = fetcher.get_top_wallets(top_n=20, period='monthly', metric='profit')
    for wallet_data in top_wallets:
        print(f"Rank {wallet_data['rank']}: {wallet_data['wallet']} | Profit: ${wallet_data['profit']:,.2f} | Volume: ${wallet_data['volume']:,.2f}")
