# Backpack Trading 🔹

Automated trading bot for creating volume and managing positions on the [Backpack exchange](https://backpack.exchange/refer/binance).

Discover the latest `<crypto/>` moves in my Telegram Channel:

[![My Channel 🥰](https://img.shields.io/badge/Web3_Enjoyer_|_Subscribe_🥰-0A66C2?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/web3_enjoyer_club) 

![image](https://github.com/opensolmap/solmap/assets/58307006/2bb4c3a8-d009-4647-8c9a-50d2eaa53534)

## Features
- Volume trading with configurable parameters
- Grid trading system for automated market making
- Position management with entry tracking
- Take profit functionality
- Proxy support for multiple accounts
- Auto-sizing of orders based on available balance

## Quick Start 📚
1. Clone this repository to your local machine
2. To install dependencies on Windows click on `INSTALL.bat` (or run `pip install -r requirements.txt`)
3. Configure your settings in `inputs/config.py`
4. Add your API keys to `inputs/accounts.txt`
5. (Optional) Add proxies to `inputs/proxies.txt`
6. To start the bot use `START.bat` (or run `python main.py`)

## Configuration Guide 📧

All settings can be customized in `inputs/config.py`:

### General Settings
```python
CONVERT_ALL_TO_USDC = False  # When True, sells all assets to USDC instead of trading
THREADS = 1  # Number of parallel threads to run
DEPTH = 3  # Market depth for order execution (1-20, higher = more slippage)
```

### Volume Trading Settings
```python
DELAY_BETWEEN_TRADE = (1, 2)  # Delay in seconds between buy and sell operations
DELAY_BETWEEN_DEAL = (0, 0)  # Delay in seconds between completed trade cycles
NEEDED_TRADE_VOLUME = 0  # Target trading volume in USD (0 = unlimited)
MIN_BALANCE_TO_LEFT = 0  # Minimum balance to maintain (in USD)
TRADE_AMOUNT = [0, 0]  # Min and max amount per trade in USD (0 = use full balance)
ALLOWED_ASSETS = ["SOL_USDC", "PYTH_USDC", ...]  # Trading pairs to use
```

### Position Management & Grid Trading
```python
# Grid Trading Configuration
ENABLE_GRID_TRADING = False  # Set to True to enable grid trading mode
GRID_TRADING_PAIRS = ["SOL_USDC"]  # Trading pairs for grid trading
GRID_LEVELS = 5  # Number of grid levels on each side (buy/sell)
GRID_SPREAD = 0.01  # Price difference between grid levels (1% = 0.01)
GRID_ORDER_SIZE = None  # Order size (None = auto-calculate)
TAKE_PROFIT_PERCENTAGE = 3.0  # Take profit target for sell orders
```

### Account Setup
1. API Keys Configuration 🔒
   - Get your API keys from [Backpack Exchange](https://backpack.exchange/settings/api-keys)
   - Add them to `inputs/accounts.txt` in the format: `api_key:secret_key`
   
   ![image](https://github.com/MsLolita/pybackpack/assets/58307006/910e8383-c7cc-4336-8829-69ad5fe24996)

2. (Optional) Proxy Setup 🌐
   - Add your proxies to `inputs/proxies.txt`
   - Supports any format (socks, http/s, etc.)
   
   ![Proxy Configuration](https://github.com/MsLolita/VeloData/assets/58307006/a2c95484-52b6-497a-b89e-73b89d953d8c)

## Trading Modes

### Standard Volume Trading
The default mode generates trading volume by continuously buying and selling assets. This is useful for:
- Meeting volume requirements for rewards programs
- Maintaining activity on your account
- Simple trading automation

To use this mode, set `ENABLE_GRID_TRADING = False` in the config.

### Grid Trading
Grid trading places multiple buy and sell orders at regular intervals around the current market price, automatically profiting from price volatility.

Key benefits:
- Automated buying low and selling high
- Position tracking with weighted average entry price
- Take profit targets based on position entry
- Automatic order repositioning when market moves significantly

To use this mode:
1. Set `ENABLE_GRID_TRADING = True` in the config
2. Configure your desired pairs in `GRID_TRADING_PAIRS`
3. Adjust grid parameters (`GRID_LEVELS`, `GRID_SPREAD`, etc.)
4. Set your profit target with `TAKE_PROFIT_PERCENTAGE`

For detailed information on grid trading, see the [Grid Trading Documentation](core/position_management/README.md).
