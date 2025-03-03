# Backpack Trading 🔹

Automated trading bot for creating volume and managing positions on the [Backpack exchange](https://backpack.exchange/).

Discover the latest `<crypto/>` moves in my Telegram Channel:

[![My Channel 🥰](https://img.shields.io/badge/Web3_Enjoyer_|_Subscribe_🥰-0A66C2?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/web3_enjoyer_club) 

![image](https://github.com/opensolmap/solmap/assets/58307006/2bb4c3a8-d009-4647-8c9a-50d2eaa53534)

## Features
- Volume trading with configurable parameters
- Grid trading system for automated market making
- Position management with entry tracking
- Take profit functionality
- Proxy support with validation and health checking
- Auto-sizing of orders based on available balance
- Smart handling of small balances (less than $5)
- Configurable retry mechanism for all network operations

## Quick Start 📚
1. Clone this repository to your local machine
2. To install dependencies on Windows click on `INSTALL.bat` (or run `pip install -r requirements.txt`)
3. Configure your settings in `inputs/config.py`
4. Add your API keys to `inputs/accounts.txt`
5. (Optional) Add proxies to `inputs/proxies.txt`
6. (Optional) Validate your proxies using `CHECK_PROXIES.bat` (or run `python check_proxies.py`)
7. To start the bot use `START.bat` (or run `python main.py`)
   - For auto proxy validation, use `START_WITH_PROXY_CHECK.bat` (or run `python main.py --check-proxies`)
8. To check account balances use `CHECK_BALANCES.bat` (or run `python check_balances.py`)
9. To close all open orders use `CLOSE_ORDERS.bat` (or run `python close_all_orders.py`)

## Configuration Guide 📧

All settings can be customized in `inputs/config.py`:

### General Settings
```python
CONVERT_ALL_TO_USDC = False  # When True, sells all assets to USDC instead of trading
THREADS = 1  # Number of parallel threads to run
DEPTH = 3  # Market depth for order execution (1-20, higher = more slippage)

# Retry Configuration
MAX_BUY_RETRIES = 10  # Number of retry attempts for buy operations
MAX_SELL_RETRIES = 10  # Number of retry attempts for sell operations
MAX_BALANCE_RETRIES = 7  # Number of retry attempts for balance operations
MAX_MARKET_PRICE_RETRIES = 5  # Number of retry attempts for market price operations
RETRY_DELAY_MIN = 2  # Minimum delay between retries (seconds)
RETRY_DELAY_MAX = 7  # Maximum delay between retries (seconds)
```

### Volume Trading Settings
```python
DELAY_BETWEEN_TRADE = (1, 2)  # Delay in seconds between buy and sell operations
DELAY_BETWEEN_DEAL = (0, 0)  # Delay in seconds between completed trade cycles
NEEDED_TRADE_VOLUME = 0  # Target trading volume in USD (0 = unlimited)
MIN_BALANCE_TO_LEFT = 0  # Minimum balance to maintain (in USD)
TRADE_AMOUNT = [0, 0]  # Min and max amount per trade in USD (0 = use full balance)
ALLOWED_ASSETS = ["SOL_USDC", "PYTH_USDC", ...]  # Trading pairs to use
MARKET_PRICE_ADJUSTMENT = 0.0  # Price adjustment: -0.01 = 1% lower, +0.01 = 1% higher
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
   - Validate your proxies with the proxy checker tool
   - Run `CHECK_PROXIES.bat` or `python check_proxies.py` to test proxy health
   
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

## Version Management and Releases

This project uses git tags to mark specific versions. If you're not familiar with coding but want to use a specific version:

### How to List All Available Versions
```bash
# List all tags (versions)
git tag -l

# Show tags with their creation dates
git for-each-ref --sort=-creatordate --format '%(refname:short) - %(creatordate:short)' refs/tags
```

### How to Check the Current Version
```bash
# Show current version
git describe --tags
```

### How to Switch to a Specific Version
```bash
# First, save any changes you've made to config files
# Then run:
git checkout v1.2.0  # Replace with the version you want
```

### How to Create a New Release Tag (for Developers)
```bash
# Create a new version tag
git tag -a v1.5.0 -m "Version 1.5.0 with XYZ feature"

# Push tag to remote repository
git push origin v1.5.0
```

### Available Versions
- **v1.4.0**: Latest version with configurable retry parameters
- **v1.3.0**: Version with small balance auto-buy feature
- **v1.2.0**: Version with market price adjustment feature
- Check CHANGELOG.md for detailed version information

### How to Get Back to Latest Version
```bash
git checkout master
```

## New Features Summary

Recent updates to the project have added significant new capabilities:

### 1. Grid Trading System
- Create a grid of buy/sell orders at regular price intervals
- Automatically "buy low, sell high" as price moves within the grid
- Dynamic grid adjustment when price moves outside the range
- Position tracking with weighted average entry price
- Take profit targets based on position entry price
- Automatic order resizing based on available balance
- Graceful handling of insufficient funds

### 2. Utility Scripts
The project now includes several utility scripts to help manage your trading:

### Proxy Validation

To check if your proxies are working correctly:

```bash
python check_proxies.py
```

On Windows, you can use the `CHECK_PROXIES.bat` file:
```
CHECK_PROXIES.bat
```

This will:
- Test every proxy in your proxies.txt file against the Backpack API
- Show response times for working proxies
- Provide detailed error information for failed proxies
- Option to update your proxies.txt file with only working proxies

You can also run the main bot with automatic proxy validation:
```bash
python main.py --check-proxies
```

Or on Windows:
```
START_WITH_PROXY_CHECK.bat
```

### Balance Checking

To check balances for all your accounts:

```bash
python check_balances.py
```

On Windows, you can use the `CHECK_BALANCES.bat` file:
```
CHECK_BALANCES.bat
```

This will show a table of all assets across all accounts in your accounts.txt file.

### Closing Orders

To close all open orders (useful for stopping grid trading, or in case of emergencies):

```bash
# Close all open orders on all pairs
python close_all_orders.py

# Close orders for a specific pair
python close_all_orders.py SOL_USDC
```

On Windows, you can use the `CLOSE_ORDERS.bat` file, optionally with a trading pair:
```
CLOSE_ORDERS.bat SOL_USDC
```

This will cancel all open orders for your account on Backpack Exchange.

### 3. Testing Framework

The project now includes a comprehensive test suite for verifying grid trading functionality:

```bash
# Run all tests
python run_tests.py

# Run specific tests
python run_tests.py tests/unit/test_bot_worker.py
```

The tests cover:
- Position tracking calculations
- Grid price calculations
- Order management
- Take profit logic
- Price deviation handling
- Multiple bot management

## Development Summary

This project has evolved from a simple volume generation bot to a comprehensive trading suite with position management capabilities.

### Key Features Added:
1. **Grid Trading System**
   - Fully automated market making strategy
   - Position tracking with weighted average entry
   - Take profit functionality based on entry price
   - Dynamic grid adjustment for changing market conditions
   - Smart order placement with minimum size enforcement
   - Auto-detection of small balances with buy trigger

2. **Utility Tools**
   - Balance checker for monitoring assets across accounts
   - Order cancellation tool for emergency management
   - Windows batch files for easy access to all features

3. **Enhanced Error Handling**
   - Graceful handling of insufficient funds
   - Better logging with detailed information
   - Proper session management and cleanup

4. **Order Price Control**
   - Adjustable market price orders (higher or lower than market)
   - Percentage-based price adjustments
   - Independent control for all trading operations

5. **Testing Framework**
   - Unit tests for core components
   - Async tests for network operations
   - Easy test runner script

### Configuration Options
The system now offers multiple trading modes:
- **Volume Mode**: Simple buy/sell cycling for exchange volume requirements
- **Grid Mode**: Automated market making for profit from price volatility
- **Mixed Mode**: Run different strategies on different pairs

All features maintain backward compatibility with the original volume generation functionality.