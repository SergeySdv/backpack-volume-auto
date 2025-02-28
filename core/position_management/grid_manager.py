import asyncio
from typing import Dict, List, Optional

from core.backpack_trade import BackpackTrade
from core.utils import logger
from core.position_management.bot_worker import BotWorker


class GridManager:
    """
    Manages multiple grid trading bots across different trading pairs
    """
    
    def __init__(self):
        self.active_bots: Dict[str, BotWorker] = {}  # symbol -> BotWorker
    
    async def start_grid_bot(self, backpack: BackpackTrade, symbol: str, 
                             grid_levels: int = 5, grid_spread: float = 0.01, 
                             order_size: float = None, take_profit_percentage: float = 3.0) -> bool:
        """
        Start a grid trading bot for a specific symbol
        
        Args:
            backpack: BackpackTrade instance with API connection
            symbol: Trading pair (e.g. "SOL_USDC")
            grid_levels: Number of grid levels to create
            grid_spread: Price difference between grid levels (percentage)
            order_size: Size of each grid order (if None, calculated from balance)
            take_profit_percentage: Percentage profit target for take-profit orders
            
        Returns:
            bool: True if bot started successfully, False otherwise
        """
        if symbol in self.active_bots:
            logger.warning(f"Grid bot for {symbol} is already running")
            return False
        
        try:
            bot = BotWorker(
                backpack=backpack,
                symbol=symbol,
                grid_levels=grid_levels, 
                grid_spread=grid_spread,
                order_size=order_size,
                take_profit_percentage=take_profit_percentage
            )
            
            # Store the bot instance
            self.active_bots[symbol] = bot
            
            # Start the bot as a background task
            asyncio.create_task(bot.start_grid())
            
            logger.info(f"Started grid bot for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start grid bot for {symbol}: {e}")
            return False
    
    async def stop_grid_bot(self, symbol: str) -> bool:
        """
        Stop a grid trading bot for a specific symbol
        
        Args:
            symbol: Trading pair (e.g. "SOL_USDC")
            
        Returns:
            bool: True if bot stopped successfully, False otherwise
        """
        if symbol not in self.active_bots:
            logger.warning(f"No grid bot running for {symbol}")
            return False
        
        try:
            bot = self.active_bots[symbol]
            await bot.stop_grid()
            
            # Remove bot from active bots
            self.active_bots.pop(symbol)
            
            logger.info(f"Stopped grid bot for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop grid bot for {symbol}: {e}")
            return False
    
    async def stop_all_bots(self):
        """Stop all running grid bots"""
        if not self.active_bots:
            return
        
        logger.info(f"Stopping all grid bots ({len(self.active_bots)} running)")
        
        for symbol in list(self.active_bots.keys()):
            await self.stop_grid_bot(symbol)
    
    def get_active_bots(self) -> List[str]:
        """Get list of symbols with active grid bots"""
        return list(self.active_bots.keys())
    
    def get_bot_status(self, symbol: str) -> Optional[dict]:
        """
        Get status details for a specific grid bot
        
        Args:
            symbol: Trading pair (e.g. "SOL_USDC")
            
        Returns:
            dict: Bot status information or None if bot not found
        """
        if symbol not in self.active_bots:
            return None
        
        bot = self.active_bots[symbol]
        
        status = {
            "symbol": symbol,
            "is_running": bot.is_running,
            "grid_levels": bot.grid_levels,
            "grid_spread": bot.grid_spread,
            "order_size": bot.order_size,
            "last_price": bot.last_price,
            "active_orders": len(bot.active_orders),
            "take_profit_percentage": bot.take_profit_percentage
        }
        
        # Add position information if available
        if bot.current_position:
            status["position"] = {
                "entry_price": bot.current_position["entry_price"],
                "size": bot.current_position["size"],
                "value_usd": bot.current_position["size"] * bot.last_price if bot.last_price else None,
                "take_profit_price": bot.get_take_profit_price()
            }
        else:
            status["position"] = None
            
        return status