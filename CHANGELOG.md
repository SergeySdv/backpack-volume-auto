# Backpack Trading Bot - Changelog

## v1.4.0 (2025-03-04)
### Added
- Configurable retry parameters in config.py
- New configuration options for retry attempts and delay times
- MAX_BUY_RETRIES, MAX_SELL_RETRIES, MAX_BALANCE_RETRIES settings
- MAX_MARKET_PRICE_RETRIES setting for API calls
- RETRY_DELAY_MIN and RETRY_DELAY_MAX for customizing retry wait times
- Unit tests for retry configuration validation
- Updated documentation for retry configuration
- Enhanced stability for intermittent connection issues

## v1.3.0 (2025-03-03)
### Added
- Auto-buy trigger when asset value is less than $5
- Skips actual sell operations for small balances to improve efficiency
- Assumes assets have been sold when value is negligible
- Enhanced recovery from dust balance situations
- Unit tests for small balance detection feature

## v1.2.0 (2025-03-02)
### Added
- Market price adjustment feature to control order pricing
- New `MARKET_PRICE_ADJUSTMENT` configuration option
- Support for placing orders higher or lower than market price
- Percentage-based price adjustments with configurable values
- Comprehensive unit tests for market price adjustment feature
- Updated documentation with examples

## v1.1.0 (Unreleased)
### Added
- Proxy validation tool for checking proxy health
- Command line option for automatic proxy validation
- Windows batch file for running proxy checker
- Integration of proxy validation with main bot
- Better proxy error handling and feedback
- Failed sell order retry system to prevent stuck positions
- Improved error handling for trade failures
- More robust trade cycle with better recovery mechanisms

## Feature Branch: Position Management

This feature branch significantly enhances the original volume generation bot with grid trading, position management, and utility tools.

### Grid Trading System

A complete grid trading implementation has been added:

- **Grid Order Placement**: Automatically places buy orders below current price and sell orders above
- **Position Tracking**: Calculates weighted average entry price and total position size
- **Take Profit Logic**: Sets sell orders at profitable levels based on average entry
- **Dynamic Grid Adjustment**: Repositions grid when price moves outside the range
- **Minimum Order Size**: Enforces exchange minimum requirements
- **Auto-Sizing**: Calculates appropriate order sizes based on available balance
- **Insufficient Funds Handling**: Gracefully handles low balance conditions

### Utility Scripts

New utility scripts make account management easier:

- **check_balances.py**: Show balances for all accounts in a table format
- **close_all_orders.py**: Cancel open orders for specific or all trading pairs
- **Windows Batch Files**: Easy-to-use .bat files for all utilities

### Error Handling Improvements

Enhanced error handling throughout the codebase:

- **Session Management**: Proper cleanup of API connections
- **Detailed Logging**: More informative logs with emojis and clear formatting
- **Balance Requirements**: Clear feedback on minimum balance requirements
- **Status Reporting**: Better reporting of order status and execution

### Testing Framework

A comprehensive test suite has been added:

- **Unit Tests**: Cover core grid trading functionality
- **Async Tests**: Test network operations with mock clients
- **Test Runner**: Simple script to run tests with configurable options

### Configuration Options

The config.py file has been extended with new options:

```python
# Grid Trading Configuration
ENABLE_GRID_TRADING = False  # Set to True to enable grid trading mode
GRID_TRADING_PAIRS = ["SOL_USDC"]  # Trading pairs for grid trading
GRID_LEVELS = 5  # Number of grid levels on each side (buy/sell)
GRID_SPREAD = 0.01  # Price difference between grid levels (1% = 0.01)
GRID_ORDER_SIZE = None  # Order size (None = auto-calculate)
TAKE_PROFIT_PERCENTAGE = 3.0  # Take profit target for sell orders
```

### Documentation Updates

- Comprehensive README updates with feature explanations
- Detailed instructions for each feature
- New section on utility scripts
- Complete development summary

### Backward Compatibility

All new features maintain compatibility with the original functionality:
- Original volume generation still works as before
- Can run in either grid mode or volume mode
- Existing config options still function as expected

## How to Start Using These Features

1. Switch to the feature branch: `git checkout feature/position-management`
2. Review configuration options in `inputs/config.py`
3. To enable grid trading, set `ENABLE_GRID_TRADING = True`
4. Configure your preferred trading pairs in `GRID_TRADING_PAIRS`
5. Run with `python main.py` or `START.bat`

## Utility Tools Usage

### Balance Checking
```bash
# Check balances for all accounts
python check_balances.py
```

### Order Cancellation
```bash
# Cancel all orders
python close_all_orders.py

# Cancel orders for specific pair
python close_all_orders.py SOL_USDC
```