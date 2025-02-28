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
            logger.info(f"Checking {symbol} for open orders...")
            response = await client.get_open_orders(symbol)
            resp_json = await response.json()
            
            if response.status != 200:
                logger.error(f"Failed to get open orders for {symbol}: {resp_json}")
                return False
                
            # Handle no orders case
            if not resp_json:
                logger.info(f"No open orders found for {symbol}")
                return True
                
            # Count orders
            orders_count = len(resp_json)
            logger.info(f"Found {orders_count} open orders for {symbol}")
            
            # Cancel each order
            cancelled_count = 0
            for order in resp_json:
                order_id = order.get("id")
                order_side = order.get("side", "unknown")
                order_price = order.get("price", "unknown")
                order_quantity = order.get("quantity", "unknown")
                
                if order_id:
                    logger.info(f"Cancelling {order_side} order {order_id} for {symbol}: {order_quantity} @ {order_price}")
                    cancel_resp = await client.cancel_order_by_id(symbol, order_id)
                    
                    if cancel_resp.status == 200:
                        cancelled_count += 1
                        logger.info(f"✅ Successfully cancelled order {order_id}")
                    else:
                        logger.warning(f"❌ Failed to cancel order {order_id}: {await cancel_resp.text()}")
            
            # Summary
            if cancelled_count == orders_count:
                logger.info(f"✅ Successfully cancelled all {cancelled_count} orders for {symbol}")
            else:
                logger.info(f"⚠️ Cancelled {cancelled_count}/{orders_count} orders for {symbol}")
            
            return cancelled_count > 0
        else:
            # Get open orders for each trading pair from config
            from inputs.config import ALLOWED_ASSETS
            
            # Use allowed assets from config as default trading pairs
            trading_pairs = ALLOWED_ASSETS
            logger.info(f"Checking {len(trading_pairs)} trading pairs for open orders")
            
            # Track total orders found and cancelled
            total_orders_found = 0
            total_orders_cancelled = 0
            processed_pairs = 0
            
            # Process each trading pair
            for pair in trading_pairs:
                try:
                    processed_pairs += 1
                    logger.info(f"[{processed_pairs}/{len(trading_pairs)}] Checking {pair} for open orders...")
                    
                    # Get open orders for this pair
                    response = await client.get_open_orders(pair)
                    resp_json = await response.json()
                    
                    if response.status != 200:
                        logger.warning(f"Failed to get open orders for {pair}: {resp_json}")
                        continue
                    
                    # Skip if no orders
                    if not resp_json:
                        logger.info(f"No open orders found for {pair}")
                        continue
                    
                    # Count orders    
                    orders_count = len(resp_json)
                    total_orders_found += orders_count
                    logger.info(f"Found {orders_count} open orders for {pair}")
                    
                    # Cancel each order
                    cancelled_for_pair = 0
                    for order in resp_json:
                        order_id = order.get("id")
                        order_side = order.get("side", "unknown")
                        order_price = order.get("price", "unknown")
                        order_quantity = order.get("quantity", "unknown")
                        
                        if order_id:
                            logger.info(f"Cancelling {order_side} order {order_id} for {pair}: {order_quantity} @ {order_price}")
                            cancel_resp = await client.cancel_order_by_id(pair, order_id)
                            
                            if cancel_resp.status == 200:
                                cancelled_for_pair += 1
                                total_orders_cancelled += 1
                                logger.info(f"✅ Successfully cancelled order {order_id}")
                            else:
                                logger.warning(f"❌ Failed to cancel order {order_id}: {await cancel_resp.text()}")
                    
                    logger.info(f"Cancelled {cancelled_for_pair}/{orders_count} orders for {pair}")
                
                except Exception as e:
                    logger.error(f"Error processing {pair}: {e}")
            
            # Summary
            if total_orders_found == 0:
                logger.info(f"No open orders found across any of the {len(trading_pairs)} trading pairs")
            else:
                logger.info(f"Summary: Found {total_orders_found} orders, successfully cancelled {total_orders_cancelled} orders")
        
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
    # Show script banner
    print("\n" + "=" * 60)
    print("  BACKPACK ORDER CANCELLATION TOOL")
    print("=" * 60 + "\n")
    
    # Determine target symbol from command line argument
    target_symbol = None
    if len(sys.argv) > 1:
        target_symbol = sys.argv[1].upper()
        logger.info(f"🎯 Target: Closing orders for specific pair: {target_symbol}")
    else:
        logger.info("🎯 Target: Closing orders for all trading pairs")
    
    # Get accounts and proxies
    accounts, proxies = await get_accounts(ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH)
    
    if not accounts:
        logger.error("❌ No accounts found in accounts.txt. Please add your API keys.")
        return
    
    logger.info(f"🔑 Found {len(accounts)} accounts to process")
    
    # Track success/failure
    success_count = 0
    failure_count = 0
    
    # Close orders for each account
    for i, account in enumerate(accounts):
        try:
            api_key, api_secret = account.split(":")
            proxy = proxies[i] if i < len(proxies) else None
            
            logger.info(f"\n📊 Processing account {i+1}/{len(accounts)}: {api_key[:8]}...")
            
            # Close orders
            result = await close_all_orders(api_key, api_secret, proxy, target_symbol)
            
            if result:
                success_count += 1
            else:
                failure_count += 1
                
        except Exception as e:
            logger.error(f"❌ Error processing account {i+1}: {e}")
            failure_count += 1
    
    # Final summary
    print("\n" + "=" * 60)
    if success_count > 0 and failure_count == 0:
        logger.info(f"✅ Successfully processed all {success_count} accounts")
    elif success_count > 0 and failure_count > 0:
        logger.info(f"⚠️ Processed {success_count} accounts successfully, {failure_count} accounts had errors")
    else:
        logger.error(f"❌ Failed to process any accounts successfully")
    print("=" * 60 + "\n")
    
    logger.info("Done!")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())