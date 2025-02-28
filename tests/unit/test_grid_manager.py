import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import pytest

from core.position_management.grid_manager import GridManager
from core.position_management.bot_worker import BotWorker


class TestGridManager(unittest.TestCase):
    """Unit tests for the GridManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.grid_manager = GridManager()
        
    def test_initialization(self):
        """Test proper initialization of the GridManager class"""
        self.assertEqual(self.grid_manager.active_bots, {})
        
    def test_get_active_bots(self):
        """Test getting list of active bots"""
        # Empty initially
        self.assertEqual(self.grid_manager.get_active_bots(), [])
        
        # Add mock bots
        self.grid_manager.active_bots = {
            "SOL_USDC": MagicMock(),
            "BTC_USDC": MagicMock()
        }
        
        # Check list
        active_bots = self.grid_manager.get_active_bots()
        self.assertEqual(len(active_bots), 2)
        self.assertIn("SOL_USDC", active_bots)
        self.assertIn("BTC_USDC", active_bots)
        
    def test_get_bot_status_nonexistent(self):
        """Test getting status of non-existent bot"""
        status = self.grid_manager.get_bot_status("NONEXISTENT")
        self.assertIsNone(status)
        
    def test_get_bot_status_with_position(self):
        """Test getting status of a bot with position"""
        # Create mock bot with position
        mock_bot = MagicMock()
        mock_bot.symbol = "SOL_USDC"
        mock_bot.is_running = True
        mock_bot.grid_levels = 5
        mock_bot.grid_spread = 0.01
        mock_bot.order_size = 1.0
        mock_bot.last_price = 100.0
        mock_bot.active_orders = {"order1": {}, "order2": {}}
        mock_bot.take_profit_percentage = 3.0
        mock_bot.current_position = {
            "entry_price": 95.0,
            "size": 2.0
        }
        mock_bot.get_take_profit_price.return_value = 97.85
        
        # Add mock bot to manager
        self.grid_manager.active_bots["SOL_USDC"] = mock_bot
        
        # Get status
        status = self.grid_manager.get_bot_status("SOL_USDC")
        
        # Check status details
        self.assertEqual(status["symbol"], "SOL_USDC")
        self.assertTrue(status["is_running"])
        self.assertEqual(status["grid_levels"], 5)
        self.assertEqual(status["grid_spread"], 0.01)
        self.assertEqual(status["order_size"], 1.0)
        self.assertEqual(status["last_price"], 100.0)
        self.assertEqual(status["active_orders"], 2)
        self.assertEqual(status["take_profit_percentage"], 3.0)
        
        # Check position details
        self.assertIsNotNone(status["position"])
        self.assertEqual(status["position"]["entry_price"], 95.0)
        self.assertEqual(status["position"]["size"], 2.0)
        self.assertEqual(status["position"]["value_usd"], 200.0)  # 2.0 * 100.0
        self.assertEqual(status["position"]["take_profit_price"], 97.85)
        
    def test_get_bot_status_no_position(self):
        """Test getting status of a bot without position"""
        # Create mock bot without position
        mock_bot = MagicMock()
        mock_bot.symbol = "BTC_USDC"
        mock_bot.is_running = True
        mock_bot.grid_levels = 3
        mock_bot.grid_spread = 0.02
        mock_bot.order_size = 0.1
        mock_bot.last_price = 50000.0
        mock_bot.active_orders = {"order1": {}}
        mock_bot.take_profit_percentage = 5.0
        mock_bot.current_position = None
        
        # Add mock bot to manager
        self.grid_manager.active_bots["BTC_USDC"] = mock_bot
        
        # Get status
        status = self.grid_manager.get_bot_status("BTC_USDC")
        
        # Check status details
        self.assertEqual(status["symbol"], "BTC_USDC")
        self.assertTrue(status["is_running"])
        self.assertEqual(status["grid_levels"], 3)
        self.assertEqual(status["grid_spread"], 0.02)
        self.assertEqual(status["order_size"], 0.1)
        self.assertEqual(status["last_price"], 50000.0)
        self.assertEqual(status["active_orders"], 1)
        self.assertEqual(status["take_profit_percentage"], 5.0)
        
        # Check position is None
        self.assertIsNone(status["position"])


@pytest.mark.asyncio
class TestGridManagerAsync:
    """Async tests for the GridManager class"""
    
    @pytest.fixture
    async def grid_manager_setup(self):
        """Set up test fixtures"""
        grid_manager = GridManager()
        backpack_mock = AsyncMock()
        
        return grid_manager, backpack_mock
    
    async def test_start_grid_bot(self, grid_manager_setup):
        """Test starting a grid bot"""
        grid_manager, backpack_mock = grid_manager_setup
        
        # Patch BotWorker to avoid actual instantiation
        with patch('core.position_management.grid_manager.BotWorker') as mock_bot_worker:
            # Configure mock bot worker
            mock_bot = AsyncMock()
            mock_bot_worker.return_value = mock_bot
            
            # Start grid bot
            result = await grid_manager.start_grid_bot(
                backpack=backpack_mock,
                symbol="SOL_USDC",
                grid_levels=5,
                grid_spread=0.01,
                order_size=1.0,
                take_profit_percentage=3.0
            )
            
            # Check result
            assert result is True
            
            # Check BotWorker was created with correct parameters
            mock_bot_worker.assert_called_once_with(
                backpack=backpack_mock,
                symbol="SOL_USDC",
                grid_levels=5, 
                grid_spread=0.01,
                order_size=1.0,
                take_profit_percentage=3.0
            )
            
            # Check bot was started
            assert "SOL_USDC" in grid_manager.active_bots
            assert mock_bot.start_grid.called
    
    async def test_start_duplicate_bot(self, grid_manager_setup):
        """Test starting a bot that's already running"""
        grid_manager, backpack_mock = grid_manager_setup
        
        # Add a mock bot to simulate it's already running
        grid_manager.active_bots["SOL_USDC"] = AsyncMock()
        
        # Try to start a bot with the same symbol
        result = await grid_manager.start_grid_bot(
            backpack=backpack_mock,
            symbol="SOL_USDC",
            grid_levels=5,
            grid_spread=0.01
        )
        
        # Check result is False (can't start duplicate)
        assert result is False
    
    async def test_stop_grid_bot(self, grid_manager_setup):
        """Test stopping a grid bot"""
        grid_manager, backpack_mock = grid_manager_setup
        
        # Add a mock bot
        mock_bot = AsyncMock()
        grid_manager.active_bots["SOL_USDC"] = mock_bot
        
        # Stop the bot
        result = await grid_manager.stop_grid_bot("SOL_USDC")
        
        # Check result
        assert result is True
        
        # Check bot was stopped and removed
        assert mock_bot.stop_grid.called
        assert "SOL_USDC" not in grid_manager.active_bots
    
    async def test_stop_nonexistent_bot(self, grid_manager_setup):
        """Test stopping a bot that doesn't exist"""
        grid_manager, backpack_mock = grid_manager_setup
        
        # Try to stop a non-existent bot
        result = await grid_manager.stop_grid_bot("NONEXISTENT")
        
        # Check result is False
        assert result is False
    
    async def test_stop_all_bots(self, grid_manager_setup):
        """Test stopping all bots"""
        grid_manager, backpack_mock = grid_manager_setup
        
        # Add multiple mock bots
        grid_manager.active_bots = {
            "SOL_USDC": AsyncMock(),
            "BTC_USDC": AsyncMock(),
            "ETH_USDC": AsyncMock()
        }
        
        # Stop all bots
        await grid_manager.stop_all_bots()
        
        # Check all bots were stopped
        for bot in grid_manager.active_bots.values():
            assert bot.stop_grid.called
        
        # Check all bots were removed
        assert len(grid_manager.active_bots) == 0


if __name__ == '__main__':
    unittest.main()