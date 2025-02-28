import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

import asyncio
import pytest

from core.position_management.bot_worker import BotWorker


class TestBotWorker(unittest.TestCase):
    """Unit tests for the BotWorker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.backpack_mock = AsyncMock()
        self.symbol = "SOL_USDC"
        self.bot = BotWorker(
            backpack=self.backpack_mock,
            symbol=self.symbol,
            grid_levels=3,
            grid_spread=0.02,
            order_size=1.0,
            take_profit_percentage=5.0
        )
        
    def test_initialization(self):
        """Test proper initialization of the BotWorker class"""
        self.assertEqual(self.bot.symbol, "SOL_USDC")
        self.assertEqual(self.bot.grid_levels, 3)
        self.assertEqual(self.bot.grid_spread, 0.02)
        self.assertEqual(self.bot.order_size, 1.0)
        self.assertEqual(self.bot.take_profit_percentage, 5.0)
        self.assertEqual(self.bot.base_asset, "SOL")
        self.assertEqual(self.bot.quote_asset, "USDC")
        self.assertFalse(self.bot.is_running)
        self.assertIsNone(self.bot.current_position)
        self.assertEqual(self.bot.filled_orders, [])
        
    def test_calculate_grid_prices(self):
        """Test the grid price calculation logic"""
        self.bot.last_price = 100.0
        grid_prices = self.bot._calculate_grid_prices()
        
        # Check buy grid (below current price)
        self.assertEqual(len(grid_prices["buy"]), 3)
        self.assertAlmostEqual(grid_prices["buy"][0], 98.0)  # 100 * (1 - 0.02)
        self.assertAlmostEqual(grid_prices["buy"][1], 96.0)  # 100 * (1 - 0.04)
        self.assertAlmostEqual(grid_prices["buy"][2], 94.0)  # 100 * (1 - 0.06)
        
        # Check sell grid (above current price)
        self.assertEqual(len(grid_prices["sell"]), 3)
        self.assertAlmostEqual(grid_prices["sell"][0], 102.0)  # 100 * (1 + 0.02)
        self.assertAlmostEqual(grid_prices["sell"][1], 104.0)  # 100 * (1 + 0.04)
        self.assertAlmostEqual(grid_prices["sell"][2], 106.0)  # 100 * (1 + 0.06)
        
    def test_update_position_buy_order(self):
        """Test position tracking when a buy order is filled"""
        # Simulate a buy order being filled
        filled_order = {
            "side": "buy",
            "price": 100.0,
            "amount": 2.0
        }
        
        self.bot.update_position(filled_order)
        
        # Check position tracking
        self.assertEqual(len(self.bot.filled_orders), 1)
        self.assertEqual(self.bot.filled_orders[0]["price"], 100.0)
        self.assertEqual(self.bot.filled_orders[0]["size"], 2.0)
        
        # Check current position
        self.assertIsNotNone(self.bot.current_position)
        self.assertEqual(self.bot.current_position["entry_price"], 100.0)
        self.assertEqual(self.bot.current_position["size"], 2.0)
        
    def test_update_position_multiple_buys(self):
        """Test position tracking with multiple buys at different prices"""
        # First buy
        self.bot.update_position({
            "side": "buy",
            "price": 100.0,
            "amount": 2.0
        })
        
        # Second buy at different price
        self.bot.update_position({
            "side": "buy",
            "price": 120.0,
            "amount": 1.0
        })
        
        # Check position tracking
        self.assertEqual(len(self.bot.filled_orders), 2)
        
        # Check current position with weighted average price
        # (100*2 + 120*1) / (2+1) = 320/3 = 106.67
        self.assertIsNotNone(self.bot.current_position)
        self.assertAlmostEqual(self.bot.current_position["entry_price"], 106.67, places=2)
        self.assertEqual(self.bot.current_position["size"], 3.0)
        
    def test_update_position_buy_then_sell(self):
        """Test position tracking when buying then selling"""
        # Buy first
        self.bot.update_position({
            "side": "buy",
            "price": 100.0,
            "amount": 2.0
        })
        
        # Then sell partial position
        self.bot.update_position({
            "side": "sell",
            "price": 110.0,
            "amount": 1.0
        })
        
        # Check position tracking
        self.assertEqual(len(self.bot.filled_orders), 1)  # One buy left
        self.assertEqual(self.bot.current_position["size"], 1.0)
        self.assertEqual(self.bot.current_position["entry_price"], 100.0)
        
    def test_update_position_full_exit(self):
        """Test position tracking when selling entire position"""
        # Buy first
        self.bot.update_position({
            "side": "buy",
            "price": 100.0,
            "amount": 2.0
        })
        
        # Then sell entire position
        self.bot.update_position({
            "side": "sell",
            "price": 110.0,
            "amount": 2.0
        })
        
        # Check position tracking
        self.assertEqual(len(self.bot.filled_orders), 0)  # No buys left
        self.assertIsNone(self.bot.current_position)  # Position is closed
        
    def test_get_take_profit_price(self):
        """Test take profit price calculation"""
        # Set up a position
        self.bot.current_position = {
            "entry_price": 100.0,
            "size": 1.0
        }
        self.bot.take_profit_percentage = 5.0
        
        take_profit_price = self.bot.get_take_profit_price()
        self.assertEqual(take_profit_price, 105.0)  # 100 * (1 + 5/100)
        
        # Test with no position
        self.bot.current_position = None
        take_profit_price = self.bot.get_take_profit_price()
        self.assertIsNone(take_profit_price)  # No take profit when no position


@pytest.mark.asyncio
class TestBotWorkerAsync:
    """Async tests for the BotWorker class"""
    
    @pytest.fixture
    async def bot_setup(self):
        """Set up test fixtures"""
        backpack_mock = AsyncMock()
        symbol = "SOL_USDC"
        bot = BotWorker(
            backpack=backpack_mock,
            symbol=symbol,
            grid_levels=3,
            grid_spread=0.02,
            order_size=1.0,
            take_profit_percentage=5.0
        )
        
        # Mock get_current_price to return a fixed value
        bot.get_current_price = AsyncMock(return_value=100.0)
        
        return bot, backpack_mock
    
    async def test_check_price_deviation(self, bot_setup):
        """Test price deviation handling"""
        bot, backpack_mock = bot_setup
        bot.last_price = 100.0
        bot.cancel_all_orders = AsyncMock()
        bot.setup_grid = AsyncMock()
        
        # Test with significant deviation
        await bot.check_price_deviation(110.0)
        
        # Should cancel orders and set up new grid
        bot.cancel_all_orders.assert_called_once()
        bot.setup_grid.assert_called_once()
        self.assertEqual(bot.last_price, 110.0)
        
    async def test_place_counter_order(self, bot_setup):
        """Test counter order placement logic"""
        bot, backpack_mock = bot_setup
        bot._place_grid_order = AsyncMock()
        
        # Set up a position
        bot.current_position = {
            "entry_price": 100.0,
            "size": 1.0
        }
        
        # Test sell counter order with take profit
        filled_buy_order = {
            "side": "buy",
            "price": 95.0,
            "amount": 1.0
        }
        
        await bot._place_counter_order(filled_buy_order)
        
        # Should place sell order at take profit price (105.0)
        bot._place_grid_order.assert_called_once()
        call_args = bot._place_grid_order.call_args[0]
        self.assertEqual(call_args[0], "sell")
        self.assertEqual(call_args[1], 105.0)  # Take profit price
        
        # Reset mock
        bot._place_grid_order.reset_mock()
        
        # Test buy counter order
        filled_sell_order = {
            "side": "sell",
            "price": 105.0,
            "amount": 0.5
        }
        
        await bot._place_counter_order(filled_sell_order)
        
        # Should place buy order at a lower price
        bot._place_grid_order.assert_called_once()
        call_args = bot._place_grid_order.call_args[0]
        self.assertEqual(call_args[0], "buy")
        self.assertAlmostEqual(call_args[1], 102.9, places=1)  # 105 * (1 - 0.02)


if __name__ == '__main__':
    unittest.main()