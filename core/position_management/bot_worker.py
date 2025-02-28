
import asyncio
import decimal
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from tenacity import retry, stop_after_attempt, wait_random, retry_if_exception_type
from termcolor import colored

from core.backpack_trade import BackpackTrade, to_fixed
from core.exceptions import TradeException, FokOrderException
from core.utils import logger


class BotWorker:
    def __init__(self, backpack: BackpackTrade, symbol: str, 
                 grid_levels: int = 5, grid_spread: float = 0.01, 
                 order_size: float = None, take_profit_percentage: float = 3.0):
        """
        Grid trading implementation for Backpack exchange.
        
        Args:
            backpack: BackpackTrade instance with API connection
            symbol: Trading pair (e.g. "SOL_USDC")
            grid_levels: Number of grid levels to create
            grid_spread: Price difference between grid levels (percentage)
            order_size: Size of each grid order (if None, calculated from balance)
            take_profit_percentage: Percentage profit target for take-profit orders
        """
        self.backpack = backpack
        self.symbol = symbol
        self.grid_levels = grid_levels
        self.grid_spread = grid_spread
        self.order_size = order_size
        self.take_profit_percentage = take_profit_percentage
        
        self.base_asset, self.quote_asset = symbol.split("_")
        self.active_orders: Dict[str, dict] = {}  # order_id -> order_details
        self.last_price: Optional[float] = None
        self.is_running = False
        
        # Position tracking
        self.current_position = None
        self.filled_orders = []  # Track filled orders for position calculation
        
    async def start_grid(self):
        """Start the grid trading bot"""
        self.is_running = True
        
        # Get initial price
        self.last_price = await self.get_current_price()
        logger.info(f"Starting grid trading for {self.symbol} at price {self.last_price}")
        
        # Setup initial grid
        await self.setup_grid()
        
        # Check if we have any active orders
        if not self.active_orders:
            logger.warning(f"No active orders could be placed. Check balances and minimum order requirements.")
            logger.info(f"Grid trading for {self.symbol} stopped due to insufficient funds.")
            self.is_running = False
            return
        
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
                
                # If all orders are gone and we couldn't place new ones, stop the bot
                if not self.active_orders:
                    try:
                        # Try to setup grid again
                        await self.setup_grid()
                        # If still no orders, stop the bot
                        if not self.active_orders:
                            logger.warning(f"No active orders remaining and unable to place new ones.")
                            logger.info(f"Grid trading for {self.symbol} stopping due to insufficient funds.")
                            self.is_running = False
                            break
                    except Exception as e:
                        logger.error(f"Error trying to recreate grid: {e}")
                        # Continue the loop, we'll try again later
                
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
        
        # Get balances to check funds before placing orders
        balances = await self.backpack.get_balance()
        quote_balance = float(balances.get(self.quote_asset, {}).get('available', 0))
        base_balance = float(balances.get(self.base_asset, {}).get('available', 0))
        
        # Checking minimum requirements
        min_order_size = 0.01  # Most assets
        if self.base_asset.upper() == "BTC":
            min_order_size = 0.0001
        
        buy_enough_funds = quote_balance >= min_order_size * self.last_price
        sell_enough_funds = base_balance >= min_order_size
        
        if not buy_enough_funds and not sell_enough_funds:
            logger.warning(f"Insufficient funds for both buy and sell orders. " +
                          f"Need {min_order_size * self.last_price} {self.quote_asset} for buys or " +
                          f"{min_order_size} {self.base_asset} for sells.")
            return
        
        # Place buy orders below current price
        if buy_enough_funds:
            logger.info(f"Placing buy orders below {self.last_price}")
            for price in grid_prices["buy"]:
                await self._place_grid_order("buy", price)
        else:
            logger.warning(f"Skipping buy orders due to insufficient {self.quote_asset}")
        
        # Place sell orders above current price
        if sell_enough_funds:
            logger.info(f"Placing sell orders above {self.last_price}")
            for price in grid_prices["sell"]:
                await self._place_grid_order("sell", price)
        else:
            logger.warning(f"Skipping sell orders due to insufficient {self.base_asset}")
    
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
        
        logger.info(f"Available balances: {self.quote_asset}={quote_balance}, {self.base_asset}={base_balance}")
        
        # Calculate order size based on available balance
        # Use at most 80% of available balance split across grid levels
        if quote_balance > 0:
            # Calculate in quote currency, then convert to base
            quote_per_order = (quote_balance * 0.8) / (self.grid_levels * 2)  # Divide by 2 for buy/sell side
            self.order_size = quote_per_order / self.last_price
            logger.info(f"Calculated size from quote: {quote_per_order} {self.quote_asset} -> {self.order_size} {self.base_asset}")
        elif base_balance > 0:
            # Use base currency directly
            self.order_size = (base_balance * 0.8) / (self.grid_levels * 2)  # Divide by 2 for buy/sell side
            logger.info(f"Calculated size from base: {self.order_size} {self.base_asset}")
        else:
            raise TradeException(f"Insufficient balance for {self.base_asset} and {self.quote_asset}")
        
        # Set a minimum order size based on the asset
        min_sizes = {
            "SOL": 0.01,
            "BTC": 0.0001,
            "JUP": 0.1,
            "PRCL": 0.1,
            "WEN": 1.0,
            "W": 0.01
        }
        
        min_size = min_sizes.get(self.base_asset.upper(), 0.01)
        if self.order_size < min_size:
            logger.info(f"Increasing order size from {self.order_size} to minimum {min_size} {self.base_asset}")
            self.order_size = min_size
        
        decimal_point = BackpackTrade.ASSETS_INFO.get(self.base_asset.upper(), {}).get('decimal', 0)
        self.order_size = float(to_fixed(self.order_size, decimal_point))
        
        logger.info(f"Final order size: {self.order_size} {self.base_asset}")
    
    @retry(stop=stop_after_attempt(5), wait=wait_random(2, 5), 
           retry=retry_if_exception_type(FokOrderException))
    async def _place_grid_order(self, side: str, price: float):
        """Place a single grid order"""
        try:
            decimal_point = BackpackTrade.ASSETS_INFO.get(self.base_asset.upper(), {}).get('decimal', 0)
            price_str = to_fixed(price, decimal_point)
            
            # Adjust amount based on side
            if side == "buy":
                # For buy orders, we calculate amount based on price
                amount = self.order_size
            else:
                # For sell orders, we use the fixed amount
                amount = self.order_size
            
            # Check if amount is zero or too small
            if amount <= 0:
                logger.warning(f"Cannot place {side} order with zero or negative quantity")
                return
                
            amount_str = to_fixed(amount, decimal_point)
            
            # Double-check the formatted amount isn't zero
            if amount_str == "0" or float(amount_str) <= 0:
                logger.warning(f"Cannot place {side} order with zero quantity after formatting")
                return
                
            logger.info(f"Placing {side} order: {amount_str} {self.base_asset} @ {price_str}")
            
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
        
        current_price = await self.get_current_price()
        unfilled_orders_to_reposition = []
            
        for order_id in list(self.active_orders.keys()):
            try:
                response = await self.backpack.get_order_status(self.symbol, order_id)
                resp_json = await response.json()
                
                if response.status == 200:
                    status = resp_json.get("status")
                    order_details = self.active_orders[order_id]
                    
                    # Check if order is too far from market price and needs repositioning
                    order_price = float(order_details["price"])
                    price_diff_pct = abs(current_price - order_price) / current_price
                    
                    # If price has moved significantly and order is still open, add to reposition list
                    if status == "open" and price_diff_pct > (self.grid_spread * 3):
                        unfilled_orders_to_reposition.append(order_id)
                        continue
                    
                    if status == "filled":
                        logger.info(f"Order {order_id} filled")
                        order_details = self.active_orders.pop(order_id)
                        
                        # Update position tracking
                        self.update_position(order_details)
                        
                        # Place a counter order
                        await self._place_counter_order(order_details)
                    
                    elif status in ["cancelled", "expired", "rejected"]:
                        logger.info(f"Order {order_id} {status}")
                        self.active_orders.pop(order_id, None)
                        
            except Exception as e:
                logger.error(f"Error updating order {order_id} status: {e}")
        
        # Reposition orders that are too far from current price
        for order_id in unfilled_orders_to_reposition:
            try:
                order_details = self.active_orders[order_id]
                logger.info(f"Repositioning order {order_id} closer to current price")
                
                # Cancel the existing order
                await self.backpack.cancel_order(self.symbol, order_id)
                self.active_orders.pop(order_id, None)
                
                # Place a new order closer to current price
                side = order_details["side"]
                new_price = current_price * (1 - self.grid_spread) if side == "buy" else current_price * (1 + self.grid_spread)
                await self._place_grid_order(side, new_price)
                
            except Exception as e:
                logger.error(f"Error repositioning order {order_id}: {e}")
    
    def update_position(self, filled_order: dict):
        """Update position when an order is filled"""
        try:
            # Extract execution details
            executed_size = Decimal(str(filled_order['amount']))
            executed_price = Decimal(str(filled_order['price']))
            side = filled_order['side']
            
            if executed_size <= 0 or executed_price <= 0:
                logger.error(f"Invalid order execution data: size={executed_size}, price={executed_price}")
                return
                
            logger.info(f"Processing executed {side} order: size={executed_size}, price={executed_price}")
            
            # For sell orders, we're reducing position
            if side == "sell":
                # If we have a current position, reduce it
                if self.filled_orders:
                    # Find matching buy orders to reduce
                    remaining_size = executed_size
                    new_filled_orders = []
                    
                    for order in self.filled_orders:
                        if remaining_size <= 0:
                            new_filled_orders.append(order)
                            continue
                            
                        order_size = Decimal(str(order['size']))
                        if order_size <= remaining_size:
                            # This buy order is fully matched by the sell
                            remaining_size -= order_size
                        else:
                            # This buy order is partially matched
                            new_size = order_size - remaining_size
                            new_filled_orders.append({
                                'price': order['price'],
                                'size': float(new_size)
                            })
                            remaining_size = 0
                    
                    self.filled_orders = new_filled_orders
            else:
                # For buy orders, add to position
                self.filled_orders.append({
                    'price': float(executed_price),
                    'size': float(executed_size)
                })
            
            # Calculate total position
            if not self.filled_orders:
                self.current_position = None
                logger.info("Position fully closed")
                return
                
            total_size = sum(Decimal(str(order['size'])) for order in self.filled_orders)
            weighted_sum = sum(Decimal(str(order['price'])) * Decimal(str(order['size'])) for order in self.filled_orders)
            
            if total_size > 0:
                avg_price = weighted_sum / total_size
                self.current_position = {
                    'entry_price': float(avg_price),
                    'size': float(total_size)
                }
                logger.info(f"Updated position: entry_price={self.current_position['entry_price']}, size={self.current_position['size']}")
            else:
                self.current_position = None
                logger.info("Position closed (size = 0)")
                
        except Exception as e:
            logger.error(f"Error updating position: {e}")
    
    def get_take_profit_price(self):
        """Calculate take profit price based on average entry"""
        try:
            if not self.current_position:
                logger.warning("No position exists to calculate take-profit price")
                return None
                
            entry_price = Decimal(str(self.current_position['entry_price']))
            profit_mult = 1 + (Decimal(str(self.take_profit_percentage)) / 100)
            take_profit_price = float(entry_price * profit_mult)
            
            logger.info(f"Calculated take-profit price: {take_profit_price} (entry: {entry_price}, profit: {self.take_profit_percentage}%)")
            return take_profit_price
            
        except Exception as e:
            logger.error(f"Error calculating take-profit price: {e}")
            return None
    
    async def _place_counter_order(self, filled_order: dict):
        """Place a counter order when a grid order is filled"""
        counter_side = "sell" if filled_order["side"] == "buy" else "buy"
        
        # Different price calculation based on side
        if counter_side == "sell" and self.current_position:
            # For sell orders, we can use take profit calculation if it's available
            take_profit_price = self.get_take_profit_price()
            if take_profit_price:
                counter_price = take_profit_price
                logger.info(f"Using take-profit price for counter order: {counter_price}")
            else:
                # Fall back to grid spread if no take profit available
                counter_price = filled_order["price"] * (1 + self.grid_spread)
        else:
            # For buy orders, we use grid spread
            price_direction = 1 if counter_side == "sell" else -1
            counter_price = filled_order["price"] * (1 + (price_direction * self.grid_spread))
        
        # Use the same amount as the filled order
        amount = filled_order["amount"]
        
        # Place the counter order
        await self._place_grid_order(counter_side, counter_price)