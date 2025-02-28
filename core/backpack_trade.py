import decimal
import json
import random
import traceback
from asyncio import sleep
from typing import Optional
from math import floor

from prettytable import PrettyTable
from tenacity import stop_after_attempt, retry, wait_random, retry_if_not_exception_type, retry_if_exception_type

from backpack import Backpack
from better_proxy import Proxy
from termcolor import colored

from inputs.config import DEPTH
from .exceptions import TradeException, FokOrderException
from .utils import logger


def to_fixed(n: str | float, d: int = 0) -> str:
    d = int('1' + ('0' * d))
    result = str(floor(float(n) * d) / d)
    if result.endswith(".0"):
        result = result[:-2]
    return result


class BackpackTrade(Backpack):
    ASSETS_INFO = {
        "SOL": {
            'decimal': 2
        },
        "USDC": {
            'decimal': 2
        },
        "PYTH": {
            'decimal': 1
        },
        "JTO": {
            'decimal': 1
        },
        "HNT": {
            'decimal': 1
        },
        "MOBILE": {
            'decimal': 0
        },
        'BONK': {
            'decimal': 0,
        },
        "WIF": {
            'decimal': 1
        },
        "USDT": {
            'decimal': 0
        },
        "JUP": {
            'decimal': 2
        },
        "RENDER": {
            'decimal': 2
        },
        "WEN": {
            'decimal': 0
        },
        "BTC": {
            'decimal': 5
        },
        "W": {
            'decimal': 2
        },
        "TNSR": {
            'decimal': 2
        },
        "PRCL": {
            'decimal': 2
        },
        "SHFL": {
            'decimal': 2
        }
    }

    def __init__(self, api_key: str, api_secret: str, proxy: Optional[str] = None, *args):
        super().__init__(
            api_key=api_key,
            api_secret=api_secret,
            proxy=proxy and Proxy.from_str(proxy.strip()).as_url
        )

        self.api_id = api_key[:15] + '...'

        self.trade_delay, self.deal_delay, self.needed_volume, self.min_balance_to_left, self.trade_amount = args

        self.current_volume: float = 0
        self.amount_usd = 0
        self.min_balance_usd = 5

    async def start_trading(self, pairs: list[str]):
        try:
            # Track failed sells to retry them
            failed_sells = []
            
            while True:
                # First check if we have failed sells to retry
                if failed_sells:
                    # Try to sell any failed positions before continuing
                    logger.info(f"Attempting to retry {len(failed_sells)} failed sell orders")
                    
                    # Copy the list to avoid modifying during iteration
                    sells_to_retry = failed_sells.copy()
                    failed_sells.clear()
                    
                    for pair_to_retry in sells_to_retry:
                        try:
                            logger.info(f"Retrying sell for {pair_to_retry}")
                            await self.custom_delay(delays=self.trade_delay)
                            
                            # Attempt to sell again
                            sell_result = await self.sell(pair_to_retry, use_retry_parameters=True)
                            
                            if not sell_result:
                                # If still failed, add back to the queue
                                logger.warning(f"Sell retry failed for {pair_to_retry}, will try again later")
                                failed_sells.append(pair_to_retry)
                            else:
                                logger.success(f"Successfully sold {pair_to_retry} after retry")
                                
                        except Exception as e:
                            logger.error(f"Error retrying sell for {pair_to_retry}: {e}")
                            failed_sells.append(pair_to_retry)
                
                # Regular trading cycle
                pair = random.choice(pairs)
                
                try:
                    # Attempt normal trade cycle
                    buy_success = await self.trade_worker(pair)
                    
                    # If buy was successful but sell failed, add to retry list
                    if isinstance(buy_success, dict) and buy_success.get("sell_failed"):
                        logger.warning(f"Adding {pair} to sell retry queue after failed sell")
                        failed_sells.append(pair)
                    
                    # Check if we should exit
                    if buy_success is True:  # Only exit if explicit True is returned
                        break
                        
                except TradeException as e:
                    logger.warning(f"Trade exception during regular cycle: {e}")
                except Exception as e:
                    logger.error(f"Error in trade cycle: {e}")
                    logger.debug(f"{e} {traceback.format_exc()}")
                    
                # Exit early if volume target reached
                if self.needed_volume and self.current_volume > self.needed_volume:
                    break
                
        except TradeException as e:
            logger.warning(e)
        except Exception as e:
            logger.error(f"{e} / Check logs in logs/out.log")
            logger.debug(f"{e} {traceback.format_exc()}")

        # Final attempt to sell any remaining failed positions
        if failed_sells:
            logger.info(f"Final attempt to sell {len(failed_sells)} remaining positions")
            for pair_to_retry in failed_sells:
                try:
                    logger.info(f"Final sell attempt for {pair_to_retry}")
                    await self.custom_delay(delays=self.trade_delay)
                    await self.sell(pair_to_retry, use_retry_parameters=True)
                except Exception as e:
                    logger.error(f"Final sell attempt failed for {pair_to_retry}: {e}")

        logger.info(f"Finished! Traded volume ~ {self.current_volume:.2f}$")

    async def trade_worker(self, pair: str):
        print()

        await self.custom_delay(delays=self.trade_delay)
        
        # Attempt to buy
        try:
            await self.buy(pair)
        except Exception as e:
            logger.error(f"Buy failed for {pair}: {e}")
            return False

        await self.custom_delay(delays=self.trade_delay)
        
        # Attempt to sell
        try:
            sell_result = await self.sell(pair)
            if not sell_result:
                # Return a dict to indicate buy succeeded but sell failed
                return {"sell_failed": True, "pair": pair}
        except Exception as e:
            logger.error(f"Sell failed for {pair}: {e}")
            # Return a dict to indicate buy succeeded but sell failed
            return {"sell_failed": True, "pair": pair}

        await self.custom_delay(self.deal_delay)

        if self.needed_volume and self.current_volume > self.needed_volume:
            return True
            
        return False

    @retry(stop=stop_after_attempt(10), wait=wait_random(5, 7), reraise=True,
           retry=retry_if_exception_type(FokOrderException))
    async def buy(self, symbol: str):
        side = 'buy'
        token = symbol.split('_')[1]
        price, balance = await self.get_trade_info(symbol, side, token)

        amount = str(float(balance) / float(price))

        await self.trade(symbol, amount, side, price)

    @retry(stop=stop_after_attempt(10), wait=wait_random(5, 7), reraise=True,
           retry=retry_if_exception_type(FokOrderException))
    async def sell(self, symbol: str, use_global_options: bool = True, use_retry_parameters: bool = False):
        side = 'sell'
        token = symbol.split('_')[0]
        
        try:
            # For retry attempts, use different parameters to increase success chance
            if use_retry_parameters:
                logger.info(f"Using adjusted parameters for sell retry on {symbol}")
                
                # Get current price
                current_price = await self.get_market_price(symbol, side, 1)
                
                # Use simpler parameters for retry - just sell what we have at current price
                balances = await self.get_balance()
                token_balance = balances.get(token, {}).get('available', '0')
                
                if float(token_balance) <= 0:
                    logger.warning(f"No {token} balance available for retry sell")
                    return False
                
                decimal_point = BackpackTrade.ASSETS_INFO.get(token.upper(), {}).get('decimal', 0)
                amount = to_fixed(token_balance, decimal_point)
                
                # Calculate approximate USD value for logging
                amount_usd = float(token_balance) * float(current_price)
                logger.info(f"Retry selling {amount} {token} (approx. {amount_usd:.2f}$)")
                
                return await self.trade(symbol, amount, side, current_price)
            else:
                # Normal sell process
                price, amount = await self.get_trade_info(symbol, side, token, use_global_options)
                return await self.trade(symbol, amount, side, price)
                
        except TradeException as e:
            logger.warning(f"Sell operation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in sell operation: {e}")
            logger.debug(traceback.format_exc())
            return False

    @retry(stop=stop_after_attempt(7), wait=wait_random(2, 5),
           before_sleep=lambda e: logger.info(f"Get Balance. Retrying... | {e}"),
           reraise=True)
    async def get_balance(self):
        response = await self.get_balances()
        msg = await response.text()
        logger.debug(f"Balance response: {msg}")

        if response.status != 200:
            if msg == "Request has expired":
                msg = "Update your time on computer!"
            logger.info(f"Response: {colored(msg, 'yellow')} | Failed to get balance! Check logs for more info.")

        return await response.json()

    @retry(stop=stop_after_attempt(7), wait=wait_random(2, 5),
           before_sleep=lambda e: logger.info(f"Get price and amount. Retrying... | {e}"),
           retry=retry_if_not_exception_type(TradeException), reraise=True)
    async def get_trade_info(self, symbol: str, side: str, token: str, use_global_options: bool = True):
        # logger.info(f"Trying to {side.upper()} {symbol}...")
        price = await self.get_market_price(symbol, side, DEPTH)
        # logger.info(f"Market price: {price} | Side: {side} | Token: {token}")
        balances = await self.get_balance()
        # logger.info(f"Balances: {await response.text()} | Side: {side} | Token: {token}")

        if side == 'buy' and (balances.get(token) is None or float(balances[token]['available']) < self.min_balance_usd):
            raise TradeException(f"Top up your balance in USDC ({to_fixed(balances[token]['available'], 5)} $)!")

        amount = balances[token]['available']

        amount_usd = float(amount) * float(price) if side != 'buy' else float(amount)

        if use_global_options:
            if not self.trade_amount[0] and not self.trade_amount[1]:
                pass
            elif self.trade_amount[1] < 5:
                self.trade_amount[0] = 5
                self.trade_amount[1] = 5
            elif self.trade_amount[0] < 5:
                self.trade_amount[0] = 5

            if side == "buy":
                if self.min_balance_to_left > 0 and self.min_balance_to_left >= amount_usd:
                    raise TradeException(
                        f"Stopped by min balance parameter {self.min_balance_to_left}. Current balance ~ {amount_usd}$")

            if self.trade_amount[1] > 0:
                if self.trade_amount[0] * 0.8 > amount_usd:
                    raise TradeException(
                        f"Not enough funds to trade. Trade Stopped. Current balance ~ {amount_usd:.2f}$")

                if side == "buy":
                    if self.trade_amount[1] > amount_usd:
                        self.trade_amount[1] = amount_usd

                    amount_usd = random.uniform(*self.trade_amount)
                    amount = amount_usd
                elif side == "sell":
                    amount = amount_usd / float(price)

        self.amount_usd = amount_usd

        return price, amount

    @retry(stop=stop_after_attempt(9), wait=wait_random(2, 5), reraise=True,
           before_sleep=lambda e: logger.info(f"Execute Trade. Retrying... | {e}"),
           retry=retry_if_not_exception_type((TradeException, FokOrderException)))
    async def trade(self, symbol: str, amount: str, side: str, price: str):
        decimal_point = BackpackTrade.ASSETS_INFO.get(symbol.split('_')[0].upper(), {}).get('decimal', 0)

        fixed_amount = to_fixed(amount, decimal_point)
        readable_amount = str(decimal.Decimal(fixed_amount))

        if readable_amount == "0":
            raise TradeException("Not enough funds to trade!")

        logger.bind(end="").debug(f"Side: {side} | Price: {price} | Amount: {readable_amount}")

        # For retry sell attempts, try GTC (Good Till Canceled) instead of FOK
        if side == "sell" and hasattr(self, "_is_retry_attempt") and self._is_retry_attempt:
            time_in_force = "GTC"
            logger.info(f"Using GTC order type for retry sell")
        else:
            time_in_force = "FOK"  # Use FOK for regular orders

        response = await self.execute_order(symbol, side, order_type="limit", quantity=readable_amount, price=price,
                                            time_in_force=time_in_force)

        resp_text = await response.text()

        logger.opt(raw=True).debug(f" | Response: {resp_text} \n")

        if resp_text == "Fill or kill order would not complete fill immediately":
            logger.info(f"Order can't be executed. Re-creating order")
            raise FokOrderException(resp_text)

        if response.status != 200:
            logger.info(f"Failed to trade! Check logs for more info. Response: {resp_text}")
            return False

        result = await response.json()

        if result.get("createdAt"):
            # Calculate amount in USD for tracking
            try:
                # If we already have self.amount_usd set, use it
                if hasattr(self, "amount_usd") and self.amount_usd > 0:
                    amount_usd = self.amount_usd
                else:
                    # Calculate approximate USD value
                    amount_usd = float(readable_amount) * float(price)
                
                self.current_volume += amount_usd

                decorated_side = colored(f'X {side.capitalize()}', 'green' if side == 'buy' else 'red')

                logger.info(f"{decorated_side} {readable_amount} {symbol} ({to_fixed(amount_usd, 2)}$). "
                            f"Traded volume: {self.current_volume:.2f}$")
            except Exception as e:
                logger.error(f"Error calculating trade volume: {e}")
                # Still return True since the order executed successfully
                
            return True

        raise TradeException(f"Failed to trade! Check logs for more info. Response: {resp_text}")

    @retry(stop=stop_after_attempt(5), before_sleep=
           lambda e: logger.info(f"Get market price. Retrying... | {e.outcome}"),
           retry=retry_if_not_exception_type(TradeException),
           wait=wait_random(2, 5), reraise=True)
    async def get_market_price(self, symbol: str, side: str, depth: int = 1):
        response = await self.get_order_book_depth(symbol)
        orderbook = await response.json()

        if len(orderbook['asks']) < depth or len(orderbook['bids']) < depth:
            raise TradeException(f"Orderbook is empty! Check logs for more info. Response: {await response.text()}")

        return orderbook['asks'][depth][0] if side == 'buy' else orderbook['bids'][-depth][0]

    async def show_balances(self):
        balances = await self.get_balance()

        table = self.get_table_from_dict(balances)
        print(table)

        with open("logs/balances.csv", "a") as fp:
            fp.write(table.get_csv_string())

        balances['private_key'] = self.api_id
        with open("logs/balances.txt", "a") as fp:
            fp.write(str(balances) + "\n")

        return balances

    def get_table_from_dict(self, balances: dict):
        table_keys = list(balances.keys())
        table_keys.sort(key=lambda x: x.startswith('USDC'), reverse=True)
        table_headers = table_keys.copy()
        table_headers.insert(0, "Private key")
        table = PrettyTable(table_headers)
        values = [to_fixed(balances[header]['available'], 5) for header in table_keys]
        values.insert(0, self.api_id)
        table.add_row(values)

        return table

    async def sell_all(self):
        balances = await self.get_balance()
        failed_sells = []

        logger.info("Converting all balances to USDC...")
        
        # First attempt to sell everything
        for symbol in balances.keys():
            if symbol.startswith('USDC'):
                continue
                
            # Skip tokens with zero balance
            available = float(balances[symbol]['available'])
            if available <= 0:
                continue
                
            # Display token balance before selling
            logger.info(f"Selling {available} {symbol}")
                
            try:
                result = await self.sell(f"{symbol}_USDC", use_global_options=False)
                if not result:
                    logger.warning(f"Failed to sell {symbol}, will retry")
                    failed_sells.append(symbol)
            except Exception as e:
                logger.error(f"Error selling {symbol}: {e}")
                failed_sells.append(symbol)
        
        # If we have failed sells, try again with retry parameters
        if failed_sells:
            logger.info(f"Retrying {len(failed_sells)} failed conversions...")
            
            for symbol in failed_sells:
                logger.info(f"Final attempt to sell {symbol}")
                try:
                    await self.sell(f"{symbol}_USDC", use_global_options=False, use_retry_parameters=True)
                except Exception as e:
                    logger.error(f"Could not convert {symbol} to USDC: {e}")
        
        # Show final balances
        final_balances = await self.get_balance()
        usdc_balance = float(final_balances.get('USDC', {}).get('available', 0))
        
        logger.info(f"Conversion complete! Final USDC balance: {usdc_balance:.2f} USDC")

    @retry(stop=stop_after_attempt(5), wait=wait_random(2, 5),
           before_sleep=lambda e: logger.info(f"Get order status. Retrying... | {e}"),
           reraise=True)
    async def get_order_status(self, symbol: str, order_id: str):
        """Get status of a specific order"""
        response = await self.get_order(symbol, order_id)
        return response
        
    @retry(stop=stop_after_attempt(5), wait=wait_random(2, 5),
           before_sleep=lambda e: logger.info(f"Get order. Retrying... | {e}"),
           reraise=True)
    async def get_order(self, symbol: str, order_id: str):
        """Get order information - alias needed for grid trading compatibility"""
        # Looking at backpack-api source code, the correct endpoint is:
        endpoint = f"/api/v1/orders/{order_id}"
        
        # Use the client's built-in request method - this is provided by the backpack base class
        # The base class is imported as "from backpack import Backpack" at the top of this file
        # We're inheriting from it, so we have access to its methods
        response = await self.get_request(endpoint)
        return response
    
    @retry(stop=stop_after_attempt(5), wait=wait_random(2, 5),
           before_sleep=lambda e: logger.info(f"Cancel order. Retrying... | {e}"),
           reraise=True)
    async def cancel_order(self, symbol: str, order_id: str):
        """Cancel a specific order"""
        response = await self.cancel_order_by_id(symbol, order_id)
        return response
    
    @staticmethod
    async def custom_delay(delays: tuple):
        if delays[1] > 0:
            sleep_time = random.uniform(*delays)
            msg = f"Delaying for {to_fixed(sleep_time, 2)} seconds..."
            logger.info(colored(msg, 'grey'))
            await sleep(sleep_time)
