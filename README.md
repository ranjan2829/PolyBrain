# Polymarket Spike Trading Bot

Automated trading bot for Polymarket that detects price spikes (1-2%), executes trades, and manages positions with profit monitoring.

## Features

- Real-time market monitoring with Redis storage
- Price spike detection (1-2% threshold)
- Automated buy/sell execution
- Position tracking and profit monitoring
- Automatic take-profit and stop-loss
- Discord and Telegram notifications

## Requirements

- Python 3.7+
- Redis server
- Wallet with USDC on Polygon network

## Installation

```bash
pip install -r requirements.txt
```

Or with Python 3:
```bash
pip3 install -r requirements.txt
```

## Configuration

Create a `.env` file:

```env
REDIS_HOST=localhost
REDIS_PORT=6379

WALLET_ADDRESS=0xYOUR_WALLET_ADDRESS
MNEMONIC=your twelve word mnemonic phrase here
POLYMARKET_API_KEY=your_api_key_from_polymarket_settings
ENABLE_TRADING=true

MAX_POSITION_SIZE=100
MIN_PROFIT_PCT=2.0
MAX_LOSS_PCT=-5.0
MAX_POSITIONS=5

PRICE_SPIKE_THRESHOLD=0.015
POLL_INTERVAL=30
MARKET_LIMIT=50
```

**CRITICAL SECURITY:**
- Never commit your `.env` file to git
- Never share your mnemonic phrase or private key
- Use either `MNEMONIC` (seed phrase) or `PRIVATE_KEY` - never both
- The `.env` file is already in `.gitignore` for your protection

## Usage

**First, test your wallet connection:**
```bash
python test_wallet.py
```

This will verify:
- Your mnemonic/private key is valid
- Wallet address matches
- Polygon network connection
- Wallet balance

**Then start Redis:**
```bash
redis-server
```

**Run the bot:**
```bash
python main.py
```

## Module Structure

```
polymarket_bot/
├── __init__.py
├── config.py
├── polymarket_client.py
├── redis_storage.py
├── spike_detector.py
├── trader.py
├── position_manager.py
└── notifier.py
```

## How It Works

1. Fetches market data from Polymarket API
2. Stores snapshots in Redis
3. Detects price spikes by comparing current vs previous snapshots
4. Automatically buys on upward spikes
5. Monitors positions for profit/loss
6. Automatically sells when profit targets or stop-losses are hit

## Security

- Never commit `.env` file
- Use a dedicated trading wallet
- Only use funds you can afford to lose
- Keep private keys secure

## License

Provided as-is for educational purposes. Use at your own risk.
