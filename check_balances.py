#!/usr/bin/env python
"""
Standalone script to check balances for all accounts in accounts.txt.
This script displays balances in a table format without starting any trading.

Usage:
    python check_balances.py

The script will show a table with balances for all accounts in accounts.txt.
"""

import os
import sys
import asyncio
import json
from decimal import Decimal
from prettytable import PrettyTable
from backpack import Backpack
from better_proxy import Proxy
from termcolor import colored

from core.utils import logger
from inputs.config import ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH
from core.backpack_trade import to_fixed


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


async def get_account_balances(api_key, api_secret, proxy=None):
    """
    Get balances for a specific account.
    Returns a dictionary of asset balances.
    """
    # Initialize Backpack client
    client = None
    try:
        client = Backpack(
            api_key=api_key,
            api_secret=api_secret,
            proxy=proxy and Proxy.from_str(proxy.strip()).as_url
        )
        
        # Get balances
        response = await client.get_balances()
        if response.status != 200:
            logger.error(f"Failed to get balances: {await response.text()}")
            return None
            
        balances = await response.json()
        return balances
        
    except Exception as e:
        logger.error(f"Error getting balances: {e}")
        return None
    finally:
        # Always close the client to prevent unclosed session warnings
        if client:
            try:
                await client.close()
            except Exception as e:
                logger.error(f"Error closing client: {e}")


def format_balance_table(all_balances):
    """
    Format balances for multiple accounts into a pretty table.
    Returns a PrettyTable object.
    """
    # Find all unique assets across all accounts
    all_assets = set()
    for balances in all_balances:
        if balances:
            all_assets.update(balances.keys())
    
    # Sort assets (USDC first, then alphabetically)
    sorted_assets = sorted(list(all_assets), key=lambda x: (0 if x.startswith('USDC') else 1, x))
    
    # Create table headers (Private key + all assets)
    headers = ["Private key"] + sorted_assets
    table = PrettyTable(headers)
    
    # Add rows for each account
    for i, balances in enumerate(all_balances):
        if not balances:
            continue
            
        # Get masked API key as identifier
        api_key = balances.get('private_key', f"Account {i+1}")
        
        # Create row with API key and all balances
        row = [api_key]
        
        for asset in sorted_assets:
            if asset in balances and asset != 'private_key':
                # Format the balance to 5 decimal places
                value = to_fixed(balances[asset]['available'], 5)
                row.append(value)
            else:
                row.append("-")
        
        table.add_row(row)
    
    return table


def calculate_total_usd_value(all_balances, price_map=None):
    """
    Calculate approximate USD value of all assets (if price_map provided)
    Returns a dictionary of account totals and an overall total.
    """
    # If no price map is provided, we can't calculate USD values
    if not price_map:
        return None
        
    account_totals = []
    overall_total = 0
    
    for balances in all_balances:
        if not balances:
            account_totals.append(0)
            continue
            
        account_total = 0
        for asset, bal in balances.items():
            if asset == 'private_key':
                continue
                
            if asset in price_map:
                asset_value = float(bal['available']) * price_map[asset]
                account_total += asset_value
        
        account_totals.append(account_total)
        overall_total += account_total
    
    return {
        'account_totals': account_totals,
        'overall_total': overall_total
    }


async def main():
    """Main function"""
    # Show script banner
    print("\n" + "=" * 60)
    print("  BACKPACK BALANCE CHECKER")
    print("=" * 60 + "\n")
    
    # Get accounts and proxies
    accounts, proxies = await get_accounts(ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH)
    
    if not accounts:
        logger.error("No accounts found in accounts.txt")
        return
    
    # Get balances for each account
    all_balances = []
    for i, account in enumerate(accounts):
        try:
            api_key, api_secret = account.split(":")
            proxy = proxies[i] if i < len(proxies) else None
            
            # Get masked API key for display
            masked_key = api_key[:8] + "..." if len(api_key) > 10 else api_key
            logger.info(f"Checking balances for account {i+1}/{len(accounts)}: {masked_key}")
            
            # Get balances
            balances = await get_account_balances(api_key, api_secret, proxy)
            
            if balances:
                # Add masked API key to balances
                balances['private_key'] = masked_key
                all_balances.append(balances)
            else:
                all_balances.append(None)
                
        except Exception as e:
            logger.error(f"Error processing account {i+1}: {e}")
            all_balances.append(None)
    
    # Format and display balances table
    if any(all_balances):
        table = format_balance_table(all_balances)
        print(table)
        
        # Save to file (optional)
        with open("logs/balances.csv", "a") as fp:
            fp.write(table.get_csv_string())
    else:
        logger.error("No balances found for any accounts")
    
    # Final summary
    print("\n" + "=" * 60)
    success_count = sum(1 for b in all_balances if b)
    logger.info(f"Checked balances for {success_count}/{len(accounts)} accounts successfully")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Run main function
    asyncio.run(main())