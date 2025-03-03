import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest
import json

from core.backpack_trade import BackpackTrade
from core.exceptions import TradeException


class TestBackpackTrade(unittest.TestCase):
    """Unit tests for BackpackTrade class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock api_key and api_secret
        self.api_key = "test_api_key"
        self.api_secret = "test_api_secret"
        
        # Create mock args for BackpackTrade
        self.trade_delay = (0.1, 0.2)
        self.deal_delay = (0.1, 0.2)
        self.needed_volume = 0
        self.min_balance_to_left = 0
        self.trade_amount = [0, 0]
        
        # Create a patched version of BackpackTrade
        with patch('core.backpack_trade.Backpack'):
            self.trade = BackpackTrade(
                self.api_key, 
                self.api_secret,
                None,
                self.trade_delay,
                self.deal_delay,
                self.needed_volume,
                self.min_balance_to_left,
                self.trade_amount
            )


@pytest.mark.asyncio
class TestBackpackTradeAsync:
    """Async tests for BackpackTrade class"""
    
    @pytest.fixture
    async def trade_setup(self):
        """Set up test fixtures"""
        # Create mock args for BackpackTrade
        trade_delay = (0.1, 0.2)
        deal_delay = (0.1, 0.2)
        needed_volume = 0
        min_balance_to_left = 0
        trade_amount = [0, 0]
        
        # Create a mock BackpackTrade class that avoids calling the real Backpack __init__
        with patch('core.backpack_trade.BackpackTrade.__init__', return_value=None):
            trade = BackpackTrade.__new__(BackpackTrade)
            
            # Set the necessary attributes directly
            trade.trade_delay = trade_delay
            trade.deal_delay = deal_delay
            trade.needed_volume = needed_volume
            trade.min_balance_to_left = min_balance_to_left
            trade.trade_amount = trade_amount
            trade.current_volume = 0
            trade.amount_usd = 0
            trade.min_balance_usd = 5
            trade.api_id = "test_api_key"
            
            # Make the get_order_book_depth method return a known response
            mock_response = AsyncMock()
            trade.get_order_book_depth = AsyncMock(return_value=mock_response)
            
            return trade, mock_response

    async def test_get_market_price_no_adjustment(self, trade_setup, monkeypatch):
        """Test get_market_price with no price adjustment"""
        trade, mock_response = trade_setup
        
        # Mock config MARKET_PRICE_ADJUSTMENT to 0
        monkeypatch.setattr('inputs.config.MARKET_PRICE_ADJUSTMENT', 0.0)
        
        # Create a sample orderbook response
        # For ask (buy), the function uses positive indexing: orderbook['asks'][depth][0]
        # For bid (sell), the function uses negative indexing: orderbook['bids'][-depth][0]
        orderbook = {
            'asks': [['dummy', '0'], ['100.0', '1.0'], ['101.0', '2.0'], ['102.0', '3.0']],
            'bids': [['dummy', '0'], ['99.0', '1.0'], ['98.0', '2.0'], ['97.0', '3.0']]
        }
        
        # Set the response JSON
        mock_response.json = AsyncMock(return_value=orderbook)
        
        # Test buy side, depth 1 (index 0 in the array)
        price = await trade.get_market_price('SOL_USDC', 'buy', 1)
        assert price == '100.0'
        
        # Test sell side, depth 1 (index -1 for negative indexing)
        price = await trade.get_market_price('SOL_USDC', 'sell', 1)
        assert price == '97.0'
        
        # Test buy side, depth 3 (index 2 in the array)
        price = await trade.get_market_price('SOL_USDC', 'buy', 3)
        assert price == '102.0'
        
        # Test sell side, depth 3 (index -3 for negative indexing)
        price = await trade.get_market_price('SOL_USDC', 'sell', 3)
        assert price == '99.0'

    async def test_get_market_price_with_positive_adjustment(self, trade_setup, monkeypatch):
        """Test get_market_price with positive price adjustment (higher)"""
        trade, mock_response = trade_setup
        
        # Mock config MARKET_PRICE_ADJUSTMENT to 0.01 (1% higher)
        monkeypatch.setattr('inputs.config.MARKET_PRICE_ADJUSTMENT', 0.01)
        
        # Create a sample orderbook response
        # For ask (buy), the function uses positive indexing: orderbook['asks'][depth][0]
        # For bid (sell), the function uses negative indexing: orderbook['bids'][-depth][0]
        orderbook = {
            'asks': [['dummy', '0'], ['100.0', '1.0'], ['101.0', '2.0'], ['102.0', '3.0']],
            'bids': [['dummy', '0'], ['99.0', '1.0'], ['98.0', '2.0'], ['97.0', '3.0']]
        }
        
        # Set the response JSON
        mock_response.json = AsyncMock(return_value=orderbook)
        
        # Test buy side, depth 1
        price = await trade.get_market_price('SOL_USDC', 'buy', 1)
        assert float(price) == pytest.approx(101.0, 0.0001)  # 100 + 1%
        
        # Test sell side, depth 1 (index -1 for negative indexing)
        price = await trade.get_market_price('SOL_USDC', 'sell', 1)
        assert float(price) == pytest.approx(97.97, 0.0001)  # 97 + 1%
        
        # Test buy side, depth 3
        price = await trade.get_market_price('SOL_USDC', 'buy', 3)
        assert float(price) == pytest.approx(103.02, 0.0001)  # 102 + 1%

    async def test_get_market_price_with_negative_adjustment(self, trade_setup, monkeypatch):
        """Test get_market_price with negative price adjustment (lower)"""
        trade, mock_response = trade_setup
        
        # Mock config MARKET_PRICE_ADJUSTMENT to -0.02 (2% lower)
        monkeypatch.setattr('inputs.config.MARKET_PRICE_ADJUSTMENT', -0.02)
        
        # Create a sample orderbook response
        # For ask (buy), the function uses positive indexing: orderbook['asks'][depth][0]
        # For bid (sell), the function uses negative indexing: orderbook['bids'][-depth][0]
        orderbook = {
            'asks': [['dummy', '0'], ['100.0', '1.0'], ['101.0', '2.0'], ['102.0', '3.0']],
            'bids': [['dummy', '0'], ['99.0', '1.0'], ['98.0', '2.0'], ['97.0', '3.0']]
        }
        
        # Set the response JSON
        mock_response.json = AsyncMock(return_value=orderbook)
        
        # Test buy side, depth 1
        price = await trade.get_market_price('SOL_USDC', 'buy', 1)
        assert float(price) == pytest.approx(98.0, 0.0001)  # 100 - 2%
        
        # Test sell side, depth 1 (index -1 for negative indexing)
        price = await trade.get_market_price('SOL_USDC', 'sell', 1)
        assert float(price) == pytest.approx(95.06, 0.0001)  # 97 - 2%
        
        # Test sell side, depth 3 (index -3 for negative indexing)
        price = await trade.get_market_price('SOL_USDC', 'sell', 3)
        assert float(price) == pytest.approx(97.02, 0.0001)  # 99 - 2%

    async def test_get_market_price_empty_orderbook(self, trade_setup):
        """Test get_market_price with empty orderbook"""
        trade, mock_response = trade_setup
        
        # Create an empty orderbook response
        orderbook = {
            'asks': [],
            'bids': []
        }
        
        # Set the response JSON
        mock_response.json = AsyncMock(return_value=orderbook)
        mock_response.text = AsyncMock(return_value="Empty orderbook")
        
        # Test that TradeException is raised
        with pytest.raises(TradeException) as excinfo:
            await trade.get_market_price('SOL_USDC', 'buy')
        
        assert "Orderbook is empty" in str(excinfo.value)

    async def test_sell_with_small_balance(self, trade_setup):
        """Test sell method with balance less than $5"""
        trade, mock_response = trade_setup
        
        # Mock get_market_price to return a known price
        trade.get_market_price = AsyncMock(return_value='10.0')
        
        # Mock get_balance to return a small balance (less than $5 when multiplied by price)
        mock_balance_response = {
            'SOL': {'available': '0.4'}  # 0.4 * 10 = $4 (less than $5)
        }
        trade.get_balance = AsyncMock(return_value=mock_balance_response)
        
        # Mock get_trade_info to return price and amount directly
        trade.get_trade_info = AsyncMock(return_value=('10.0', '0.4'))
        
        # Mock trade method
        trade.trade = AsyncMock()
        
        # Call sell method
        result = await trade.sell('SOL_USDC')
        
        # Check that the function returns True (considering it sold) without calling trade
        assert result is True
        
        # Verify that trade.trade wasn't called
        assert not trade.trade.called
        
    async def test_sell_retry_with_small_balance(self, trade_setup):
        """Test sell method with retry parameters and balance less than $5"""
        trade, mock_response = trade_setup
        
        # Mock get_market_price to return a known price
        trade.get_market_price = AsyncMock(return_value='10.0')
        
        # Mock get_balance to return a small balance (less than $5 when multiplied by price)
        mock_balance_response = {
            'SOL': {'available': '0.4'}  # 0.4 * 10 = $4 (less than $5)
        }
        trade.get_balance = AsyncMock(return_value=mock_balance_response)
        
        # Mock trade method
        trade.trade = AsyncMock()
        
        # Mock to_fixed function
        with patch('core.backpack_trade.to_fixed', return_value='0.4'):
            # Call sell method with retry parameters
            result = await trade.sell('SOL_USDC', use_retry_parameters=True)
            
        # Check that the function returns True (considering it sold) without calling trade
        assert result is True
        
        # Verify that trade.trade wasn't called
        assert not trade.trade.called
        
    async def test_sell_with_normal_balance(self, trade_setup):
        """Test sell method with normal balance (more than $5)"""
        trade, mock_response = trade_setup
        
        # Mock get_market_price to return a known price
        trade.get_market_price = AsyncMock(return_value='10.0')
        
        # Mock get_trade_info to return price and amount directly
        trade.get_trade_info = AsyncMock(return_value=('10.0', '1.0'))  # 1.0 * 10 = $10 (more than $5)
        
        # Mock trade method to return True
        trade.trade = AsyncMock(return_value=True)
        
        # Call sell method
        result = await trade.sell('SOL_USDC')
        
        # Check that the function returns the result of trade
        assert result is True
        
        # Verify that trade.trade was called with correct parameters
        trade.trade.assert_called_once_with('SOL_USDC', '1.0', 'sell', '10.0')


    async def test_trade_worker_with_small_balance(self, trade_setup):
        """Test trade_worker skips sell phase for small balances"""
        trade, mock_response = trade_setup
        
        # Mock custom_delay to avoid delays
        trade.custom_delay = AsyncMock()
        
        # Mock get_balance to return a small balance (less than $5)
        mock_balance_response = {
            'SOL': {'available': '0.3'},  # Small balance
            'USDC': {'available': '100.0'}  # Good USDC balance for buying
        }
        trade.get_balance = AsyncMock(return_value=mock_balance_response)
        
        # Mock get_market_price to return a price that makes SOL value < $5
        trade.get_market_price = AsyncMock(return_value='10.0')  # 0.3 * 10 = $3 (less than $5)
        
        # Mock buy method
        trade.buy = AsyncMock()
        
        # Mock sell method - we'll assert this is NOT called
        trade.sell = AsyncMock()
        
        # Call trade_worker
        result = await trade.trade_worker('SOL_USDC')
        
        # Verify buy was called but sell was NOT called
        trade.buy.assert_called_once()
        assert not trade.sell.called
        
        # Check debug logs (optional)
        # You could mock logger here to check it was called with the right message
        
    async def test_trade_worker_with_normal_balance(self, trade_setup):
        """Test trade_worker does normal sell-buy cycle for normal balances"""
        trade, mock_response = trade_setup
        
        # Mock custom_delay to avoid delays
        trade.custom_delay = AsyncMock()
        
        # Mock get_balance to return a normal balance (more than $5)
        mock_balance_response = {
            'SOL': {'available': '1.0'},  # Normal balance
            'USDC': {'available': '100.0'}  # Good USDC balance for buying
        }
        trade.get_balance = AsyncMock(return_value=mock_balance_response)
        
        # Mock get_market_price to return a price that makes SOL value > $5
        trade.get_market_price = AsyncMock(return_value='10.0')  # 1.0 * 10 = $10 (more than $5)
        
        # Mock buy and sell methods to both succeed
        trade.buy = AsyncMock()
        trade.sell = AsyncMock(return_value=True)
        
        # Call trade_worker
        result = await trade.trade_worker('SOL_USDC')
        
        # Verify both buy and sell were called
        trade.sell.assert_called_once()
        trade.buy.assert_called_once()
        
    async def test_price_decimal_error_handling(self, trade_setup):
        """Test that price decimal errors are properly handled in trade method"""
        trade, mock_response = trade_setup
        
        # Setup for the trade method test
        from core.exceptions import FokOrderException
        
        # Mock execute_order to simulate a decimal error response
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value='{"code": "INVALID_CLIENT_REQUEST", "message": "Price decimal too long"}')
        
        # Mock the execute_order method on the trade instance
        trade.execute_order = AsyncMock(return_value=mock_response)
        
        # Call the trade method and verify it raises the right exception
        with pytest.raises(FokOrderException) as excinfo:
            await trade.trade('SOL_USDC', '1.0', 'buy', '123.456789012345')  # Overly precise price
            
        # Verify the exception message
        assert "Price decimal error" in str(excinfo.value)

if __name__ == '__main__':
    unittest.main()