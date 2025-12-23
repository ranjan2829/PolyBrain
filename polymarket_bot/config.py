import os
from dotenv import load_dotenv

load_dotenv()

PRICE_SPIKE_THRESHOLD = float(os.getenv('PRICE_SPIKE_THRESHOLD', '0.015'))
VOLUME_SPIKE_THRESHOLD = float(os.getenv('VOLUME_SPIKE_THRESHOLD', '1.5'))

POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '1'))
MARKET_LIMIT = int(os.getenv('MARKET_LIMIT', '50'))

ENABLE_PRICE_ALERTS = os.getenv('ENABLE_PRICE_ALERTS', 'true').lower() == 'true'
ENABLE_VOLUME_ALERTS = os.getenv('ENABLE_VOLUME_ALERTS', 'true').lower() == 'true'
MIN_MARKET_LIQUIDITY = float(os.getenv('MIN_MARKET_LIQUIDITY', '1000'))

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

POLYMARKET_API_URL = "https://clob.polymarket.com"
# Markets endpoint (REST); GraphQL not used for markets
POLYMARKET_GRAPHQL_URL = "https://gamma-api.polymarket.com/markets"
POLYMARKET_API_KEY = os.getenv('POLYMARKET_API_KEY', '')
POLYMARKET_API_SECRET = os.getenv('POLYMARKET_API_SECRET', '')
POLYMARKET_PASSPHRASE = os.getenv('POLYMARKET_PASSPHRASE', '')

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')

ENABLE_TRADING = os.getenv('ENABLE_TRADING', 'true').lower() == 'true'
PRIVATE_KEY = os.getenv('PRIVATE_KEY', '')
MNEMONIC = os.getenv('MNEMONIC', '')
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS', '')
PROXY_WALLET = os.getenv('PROXY_WALLET', '')
MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '100'))
MIN_PROFIT_PCT = float(os.getenv('MIN_PROFIT_PCT', '2.0'))
MAX_LOSS_PCT = float(os.getenv('MAX_LOSS_PCT', '-5.0'))
MAX_POSITIONS = int(os.getenv('MAX_POSITIONS', '5'))
POLYGON_RPC_URL = os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com')
USDC_CONTRACT = os.getenv('USDC_CONTRACT', '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174')

