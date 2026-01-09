import time
from polymarket_bot import create_server

if __name__ == "__main__":
    server = create_server()
    server.start(enable_agent=True, agent_interval=60)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
