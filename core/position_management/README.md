# Position Management - Grid Trading

This module provides grid trading functionality for Backpack Exchange. Grid trading is a strategy that places multiple buy and sell orders at regular price intervals (a grid) above and below the current market price.

## Key Features

- **Automated Grid Creation**: Sets up buy orders below current price and sell orders above
- **Dynamic Grid Adjustment**: Automatically repositions grid when price moves significantly
- **Order Management**: Tracks active orders and creates counter orders when orders are filled
- **Multiple Pair Support**: Run grid bots on multiple trading pairs simultaneously

## How Grid Trading Works

1. The system creates a grid of limit orders at specified intervals around the current price
2. As market price moves, some orders get filled automatically
3. When a buy order is filled, a corresponding sell order is placed at a higher price
4. When a sell order is filled, a corresponding buy order is placed at a lower price
5. This creates a constant buying low and selling high pattern
6. If price moves significantly away from the grid, orders are canceled and repositioned

## Configuration

Configure grid trading in `inputs/config.py`:

```python
# Position Management - Grid Trading Settings
ENABLE_GRID_TRADING = True  # Set to True to enable grid trading mode
GRID_TRADING_PAIRS = ["SOL_USDC"]  # Trading pairs to use for grid trading
GRID_LEVELS = 5  # Number of grid levels to create on each side (buy/sell)
GRID_SPREAD = 0.01  # Price difference between grid levels (1% = 0.01)
GRID_ORDER_SIZE = None  # Size of each grid order in base asset, None for auto-calculation
```

## Usage

1. Set `ENABLE_GRID_TRADING = True` in the config file
2. Configure the desired trading pairs and parameters
3. Run the bot normally with `python main.py`
4. The system will start grid trading instead of the regular volume generation trading
5. Press Ctrl+C to stop grid trading

## Customization

- Adjust `GRID_LEVELS` to control how many orders are placed (higher number = more orders)
- Modify `GRID_SPREAD` to set the price difference between orders (smaller = tighter grid)
- Set `GRID_ORDER_SIZE` to control the size of each order or leave as `None` for auto-sizing

## Implementation Details

- `BotWorker`: Core grid trading logic for a single trading pair
- `GridManager`: Manages multiple grid trading bots across different pairs
- Order status is continuously monitored to detect fills and create counter orders
- Price deviations from the grid center trigger grid repositioning