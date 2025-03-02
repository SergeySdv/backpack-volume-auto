CONVERT_ALL_TO_USDC = True  # convert all balances to USDC only

THREADS = 1  # Enter amount of threads
DELAY_BETWEEN_TRADE = (1, 2)  # Execute delay between every trade (Buy -> Delay -> Sell -> Buy -> Delay ...)
DELAY_BETWEEN_DEAL = (0, 0)  # Execute delay between full trade (Buy -> Sell -> Delay -> Buy -> Sell -> Delay ...)

NEEDED_TRADE_VOLUME = 0  # volume to trade, if 0 it will never stop
MIN_BALANCE_TO_LEFT = 0  # min amount to left on the balance, if 0, it is traded until the balance is equal to 0.

TRADE_AMOUNT = [0, 0]  # (works nearly from +-20%), minimum (5$) and maximum amount to trade in USD, if 0 it will trade on FULL balance
ALLOWED_ASSETS = ["SOL_USDC", "PYTH_USDC", "JTO_USDC", "HNT_USDC", "MOBILE_USDC", "BONK_USDC", "WIF_USDC", "JUP_USDC",
                  "RENDER_USDC", "WEN_USDC", "BTC_USDC", "W_USDC", "TNSR_USDC", "PRCL_USDC", "SHFL_USDC"]

# Volatility moment
# DEPTH of limit order to trade as market order
DEPTH = 3  # 1-20, optimal - 3-5, recommend up to 10, bigger depth = better market order but more slippage

# Position Management - Grid Trading Settings
ENABLE_GRID_TRADING = False  # Set to True to enable grid trading mode
GRID_TRADING_PAIRS = ["SOL_USDC"]  # Trading pairs to use for grid trading
GRID_LEVELS = 5  # Number of grid levels to create on each side (buy/sell)
GRID_SPREAD = 0.01  # Price difference between grid levels (1% = 0.01)
GRID_ORDER_SIZE = None  # Size of each grid order in base asset, None for auto-calculation
TAKE_PROFIT_PERCENTAGE = 3.0  # Take profit percentage for sell orders

# Market Order Price Adjustment
MARKET_PRICE_ADJUSTMENT = 0.0  # Percentage adjustment from market price (-0.01 = 1% lower, 0.01 = 1% higher)








###################################### left empty
ACCOUNTS_FILE_PATH = "inputs/accounts.txt"
PROXIES_FILE_PATH = "inputs/proxies.txt"