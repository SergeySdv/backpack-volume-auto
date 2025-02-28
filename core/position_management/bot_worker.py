
import asyncio
import decimal
from typing import Dict, List, Optional, Tuple

from tenacity import retry, stop_after_attempt, wait_random, retry_if_exception_type
from termcolor import colored

from core.backpack_trade import BackpackTrade
from core.exceptions import TradeException, FokOrderException
from core.utils import logger


class BotWorker:
    def __init__(self, backpack: BackpackTrade, symbol: str, 
                 grid_levels: int = 5, grid_spread: float = 0.01, 
                 order_size: float = None):
        """
        Grid trading implementation for Backpack exchange.
        
        Args:
            backpack: BackpackTrade instance with API connection
            symbol: Trading pair (e.g. "SOL_USDC")
            grid_levels: Number of grid levels to create
            grid_spread: Price difference between grid levels (percentage)
            order_size: Size of each grid order (if None, calculated from balance)
        """
        self.backpack = backpack
        self.symbol = symbol
        self.grid_levels = grid_levels
        self.grid_spread = grid_spread
        self.order_size = order_size
        
        self.base_asset, self.quote_asset = symbol.split("_")
        self.active_orders: Dict[str, dict] = {}  # order_id -> order_details
        self.last_price: Optional[float] = None
        self.is_running = False
        
    async def start_grid(self):
        """Start the grid trading bot"""
        self.is_running = True
        
        # Get initial price
        self.last_price = await self.get_current_price()
        logger.info(f"Starting grid trading for {self.symbol} at price {self.last_price}")
        
        # Setup initial grid
        await self.setup_grid()
        
        # Monitor grid
        while self.is_running:
            try:
                # Check for price deviation
                current_price = await self.get_current_price()
                deviation = abs(current_price - self.last_price) / self.last_price
                
                if deviation > self.grid_spread * 2:
                    logger.info(f"Price deviation detected: {deviation:.2%}")
                    await self.check_price_deviation(current_price)
                
                # Check order status
                await self.update_order_status()
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Grid trading error: {e}")
                await asyncio.sleep(30)  # Longer sleep on error
    
    async def stop_grid(self):
        """Stop the grid trading bot"""
        self.is_running = False
        await self.cancel_all_orders()
        logger.info(f"Grid trading stopped for {self.symbol}")
    
    async def get_current_price(self) -> float:
        """Get current market price"""
        price = await self.backpack.get_market_price(self.symbol, "buy", 1)
        return float(price)
    
    async def check_price_deviation(self, current_price: float):
        """
        Detects when price moves away from grid orders and repositions the grid
        
        Args:
            current_price: Current market price
        """
        # If price has moved significantly from our grid center
        if abs(current_price - self.last_price) / self.last_price > self.grid_spread * 2:
            logger.info(f"Price moved from {self.last_price} to {current_price}")
            
            # Cancel existing orders
            await self.cancel_all_orders()
            
            # Update last price and create new grid
            self.last_price = current_price
            await self.setup_grid()
    
    @retry(stop=stop_after_attempt(5), wait=wait_random(2, 5), 
           retry=retry_if_exception_type(FokOrderException))
    async def cancel_all_orders(self):
        """Cancels all unfilled grid orders"""
        if not self.active_orders:
            return
        
        logger.info(f"Cancelling {len(self.active_orders)} active orders")
        
        for order_id in list(self.active_orders.keys()):
            try:
                response = await self.backpack.cancel_order(self.symbol, order_id)
                resp_json = await response.json()
                
                if response.status == 200:
                    logger.info(f"Cancelled order {order_id}")
                    self.active_orders.pop(order_id, None)
                else:
                    logger.warning(f"Failed to cancel order {order_id}: {resp_json}")
            except Exception as e:
                logger.error(f"Error cancelling order {order_id}: {e}")
        
        self.active_orders = {}
    
    async def setup_grid(self):
        """Creates new grid orders closer to current market price"""
        # Calculate grid prices
        grid_prices = self._calculate_grid_prices()
        
        # Calculate order size if not provided
        if self.order_size is None:
            await self._calculate_order_size()
        
        logger.info(f"Setting up grid with {len(grid_prices)} levels around {self.last_price}")
        
        # Place buy orders below current price
        for price in grid_prices["buy"]:
            await self._place_grid_order("buy", price)
        
        # Place sell orders above current price
        for price in grid_prices["sell"]:
            await self._place_grid_order("sell", price)
    
    def _calculate_grid_prices(self) -> Dict[str, List[float]]:
        """Calculate grid prices based on current price and parameters"""
        result = {"buy": [], "sell": []}
        
        # Generate buy grid levels (below current price)
        for i in range(1, self.grid_levels + 1):
            price_factor = 1 - (i * self.grid_spread)
            buy_price = self.last_price * price_factor
            result["buy"].append(buy_price)
        
        # Generate sell grid levels (above current price)
        for i in range(1, self.grid_levels + 1):
            price_factor = 1 + (i * self.grid_spread)
            sell_price = self.last_price * price_factor
            result["sell"].append(sell_price)
        
        return result
    
    async def _calculate_order_size(self):
        """Calculate appropriate order size based on available balance"""
        balances = await self.backpack.get_balance()
        
        # For buy orders, we need quote currency (e.g., USDC)
        quote_balance = float(balances.get(self.quote_asset, {}).get('available', 0))
        
        # For sell orders, we need base currency (e.g., SOL)
        base_balance = float(balances.get(self.base_asset, {}).get('available', 0))
        
        # Calculate order size based on available balance
        # Use at most 80% of available balance split across grid levels
        if quote_balance > 0:
            # Calculate in quote currency, then convert to base
            quote_per_order = (quote_balance * 0.8) / self.grid_levels
            self.order_size = quote_per_order / self.last_price
        elif base_balance > 0:
            # Use base currency directly
            self.order_size = (base_balance * 0.8) / self.grid_levels
        else:
            raise TradeException(f"Insufficient balance for {self.base_asset} and {self.quote_asset}")
        
        decimal_point = BackpackTrade.ASSETS_INFO.get(self.base_asset.upper(), {}).get('decimal', 0)
        self.order_size = float(self.backpack.to_fixed(self.order_size, decimal_point))
        
        logger.info(f"Calculated order size: {self.order_size} {self.base_asset}")
    
    @retry(stop=stop_after_attempt(5), wait=wait_random(2, 5), 
           retry=retry_if_exception_type(FokOrderException))
    async def _place_grid_order(self, side: str, price: float):
        """Place a single grid order"""
        try:
            decimal_point = BackpackTrade.ASSETS_INFO.get(self.base_asset.upper(), {}).get('decimal', 0)
            price_str = self.backpack.to_fixed(price, decimal_point)
            
            # Adjust amount based on side
            if side == "buy":
                # For buy orders, we calculate amount based on price
                amount = self.order_size
            else:
                # For sell orders, we use the fixed amount
                amount = self.order_size
            
            amount_str = self.backpack.to_fixed(amount, decimal_point)
            
            # Place limit order with GTC (Good Till Cancelled)
            response = await self.backpack.execute_order(
                self.symbol, 
                side, 
                order_type="limit", 
                quantity=amount_str, 
                price=price_str,
                time_in_force="GTC"  # Change to GTC for grid orders
            )
            
            resp_text = await response.text()
            
            if response.status != 200:
                logger.warning(f"Failed to place {side} grid order: {resp_text}")
                return
            
            result = await response.json()
            order_id = result.get("id")
            
            if order_id:
                decorated_side = colored(f'Grid {side.capitalize()}', 'green' if side == 'buy' else 'red')
                logger.info(f"{decorated_side} {amount_str} {self.symbol} at {price_str}")
                
                # Track order
                self.active_orders[order_id] = {
                    "id": order_id,
                    "side": side,
                    "price": price,
                    "amount": amount,
                    "status": "open"
                }
            else:
                logger.warning(f"Failed to get order ID for {side} grid order: {result}")
                
        except Exception as e:
            logger.error(f"Error placing {side} grid order at {price}: {e}")
    
    async def update_order_status(self):
        """Update status of all active orders"""
        if not self.active_orders:
            return
            
        for order_id in list(self.active_orders.keys()):
            try:
                response = await self.backpack.get_order_status(self.symbol, order_id)
                resp_json = await response.json()
                
                if response.status == 200:
                    status = resp_json.get("status")
                    
                    if status == "filled":
                        logger.info(f"Order {order_id} filled")
                        order_details = self.active_orders.pop(order_id)
                        
                        # Place a counter order
                        await self._place_counter_order(order_details)
                    
                    elif status in ["cancelled", "expired", "rejected"]:
                        logger.info(f"Order {order_id} {status}")
                        self.active_orders.pop(order_id, None)
                        
            except Exception as e:
                logger.error(f"Error updating order {order_id} status: {e}")
    
    async def _place_counter_order(self, filled_order: dict):
        """Place a counter order when a grid order is filled"""
        counter_side = "sell" if filled_order["side"] == "buy" else "buy"
        
        # Calculate counter price: for buys we sell higher, for sells we buy lower
        price_direction = 1 if counter_side == "sell" else -1
        counter_price = filled_order["price"] * (1 + (price_direction * self.grid_spread))
        
        # Use the same amount as the filled order
        amount = filled_order["amount"]
        
        # Place the counter order
        await self._place_grid_order(counter_side, counter_price)