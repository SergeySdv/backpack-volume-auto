#!/usr/bin/env python
"""
Standalone script to close all open orders for a specific trading pair or all pairs.
Usage:
    python close_all_orders.py [trading_pair]

Example:
    python close_all_orders.py SOL_USDC  # Close orders for SOL_USDC
    python close_all_orders.py           # Close orders for all pairs
"""

import os
import sys
import json
import asyncio
from backpack import Backpack
from better_proxy import Proxy

from core.utils import logger
from inputs.config import ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH, GRID_TRADING_PAIRS


async def get_accounts(accounts_path, proxies_path=None):
    """Get accounts and proxies from files"""
    accounts = []
    proxies = []
    
    # Read accounts
    if os.path.exists(accounts_path):
        with open(accounts_path, 'r') as f:
            accounts = [line.strip() for line in f.readlines() if line.strip()]
    else:
        logger.error(f"Accounts file not found: {accounts_path}")
        return [], []
    
    # Read proxies
    if proxies_path and os.path.exists(proxies_path):
        with open(proxies_path, 'r') as f:
            proxies = [line.strip() for line in f.readlines() if line.strip()]
    
    # If not enough proxies, fill with None
    while len(proxies) < len(accounts):
        proxies.append(None)
    
    logger.info(f"Successfully loaded {len(accounts)} accounts")
    return accounts, proxies


async def close_all_orders(api_key, api_secret, proxy, symbol=None):
    """
    Close all open orders for a specific account and symbol.
    If symbol is None, close orders for all pairs.
    """
    # Initialize Backpack client
    client = None
    try:
        client = Backpack(
            api_key=api_key,
            api_secret=api_secret,
            proxy=proxy and Proxy.from_str(proxy.strip()).as_url
        )
        
        # Get open orders
        if symbol:
            # Get open orders for specific symbol
            response = await client.get_open_orders(symbol)
            resp_json = await response.json()
            
            if response.status != 200:
                logger.error(f"Failed to get open orders for {symbol}: {resp_json}")
                return False
            
            # Cancel each order
            for order in resp_json:
                order_id = order.get("id")
                if order_id:
                    logger.info(f"Cancelling order {order_id} for {symbol}")
                    cancel_resp = await client.cancel_order_by_id(symbol, order_id)
                    
                    if cancel_resp.status == 200:
                        logger.info(f"Successfully cancelled order {order_id}")
                    else:
                        logger.warning(f"Failed to cancel order {order_id}: {await cancel_resp.text()}")
        else:
            # Get open orders for each trading pair from config
            from inputs.config import ALLOWED_ASSETS
            
            # Use allowed assets from config as default trading pairs
            trading_pairs = ALLOWED_ASSETS
            logger.info(f"Checking {len(trading_pairs)} trading pairs for open orders")
            
            # Process each trading pair
            for pair in trading_pairs:
                try:
                    # Get open orders for this pair
                    response = await client.get_open_orders(pair)
                    resp_json = await response.json()
                    
                    if response.status != 200:
                        logger.warning(f"Failed to get open orders for {pair}: {resp_json}")
                        continue
                    
                    # Skip if no orders
                    if not resp_json:
                        continue
                        
                    logger.info(f"Found {len(resp_json)} open orders for {pair}")
                    
                    # Cancel each order
                    for order in resp_json:
                        order_id = order.get("id")
                        if order_id:
                            logger.info(f"Cancelling order {order_id} for {pair}")
                            cancel_resp = await client.cancel_order_by_id(pair, order_id)
                            
                            if cancel_resp.status == 200:
                                logger.info(f"Successfully cancelled order {order_id}")
                            else:
                                logger.warning(f"Failed to cancel order {order_id}: {await cancel_resp.text()}")
                
                except Exception as e:
                    logger.error(f"Error processing {pair}: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error closing orders: {e}")
        return False
    finally:
        # Always close the client to prevent unclosed session warnings
        if client:
            try:
                await client.close()
            except Exception as e:
                logger.error(f"Error closing client: {e}")


async def main():
    """Main function"""
    # Determine target symbol from command line argument
    target_symbol = None
    if len(sys.argv) > 1:
        target_symbol = sys.argv[1].upper()
        logger.info(f"Closing orders for {target_symbol}")
    else:
        logger.info("Closing orders for all trading pairs")
    
    # Get accounts and proxies
    accounts, proxies = await get_accounts(ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH)
    
    if not accounts:
        logger.error("No accounts found")
        return
    
    # Close orders for each account
    for i, account in enumerate(accounts):
        try:
            api_key, api_secret = account.split(":")
            proxy = proxies[i] if i < len(proxies) else None
            
            logger.info(f"Processing account {api_key[:8]}...")
            
            # Close orders
            await close_all_orders(api_key, api_secret, proxy, target_symbol)
            
        except Exception as e:
            logger.error(f"Error processing account {i+1}: {e}")
    
    logger.info("Done!")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())