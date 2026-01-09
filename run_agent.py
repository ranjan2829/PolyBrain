from polymarket_bot import CopyTradeAgent

if __name__ == "__main__":
    print("Starting CopyTrade Agent...")
    
    agent = CopyTradeAgent()
    agent.connect()
    
    try:
        agent.monitor_whales(top_n=20, interval=60)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        agent.close()
        print("Agent stopped.")
