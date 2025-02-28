import asyncio
import ctypes
import sys

from core.autoreger import AutoReger
from core.backpack_trade import BackpackTrade
from core.position_management.grid_manager import GridManager

from art import text2art
from termcolor import colored, cprint

from core.utils import logger
from inputs.config import (ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH, THREADS, DELAY_BETWEEN_TRADE, DELAY_BETWEEN_DEAL,
                           ALLOWED_ASSETS, NEEDED_TRADE_VOLUME, MIN_BALANCE_TO_LEFT, TRADE_AMOUNT, CONVERT_ALL_TO_USDC,
                           ENABLE_GRID_TRADING, GRID_TRADING_PAIRS, GRID_LEVELS, GRID_SPREAD, GRID_ORDER_SIZE, 
                           TAKE_PROFIT_PERCENTAGE)


def bot_info(name: str = ""):
    cprint(text2art(name), 'green')

    if sys.platform == 'win32':
        ctypes.windll.kernel32.SetConsoleTitleW(f"{name}")

    print(
        f"{colored('EnJoYeR <crypto/> moves:', color='light_yellow')} "
        f"{colored('https://t.me/+tdC-PXRzhnczNDli', color='light_green')}"
    )
    print(
        f"{colored('To say thanks for work:', color='light_yellow')} "
        f"{colored('0x000007c73a94f8582ef95396918dcd04f806cdd8', color='light_green')}"
    )


async def worker_task(account: str, proxy: str):
    api_key, api_secret = account.split(":")

    try:
        backpack = BackpackTrade(api_key, api_secret, proxy, DELAY_BETWEEN_TRADE, DELAY_BETWEEN_DEAL,
                                 NEEDED_TRADE_VOLUME, MIN_BALANCE_TO_LEFT, TRADE_AMOUNT)
    except Exception as e:
        logger.error(f"WRONG API SECRET KEY !!!!!!!!!!!!!!!!!!!!!!!!: {e}")
        return False

    await backpack.show_balances()

    if CONVERT_ALL_TO_USDC:
        await backpack.sell_all()
    elif ENABLE_GRID_TRADING:
        # Start grid trading mode
        await run_grid_trading(backpack)
    else:
        # Regular trading mode
        await backpack.start_trading(pairs=ALLOWED_ASSETS)

    await backpack.show_balances()

    await backpack.close()

    return True


async def run_grid_trading(backpack: BackpackTrade):
    """Run grid trading with the provided backpack instance"""
    logger.info(colored("Starting grid trading mode", "green"))
    
    # Create a grid manager
    grid_manager = GridManager()
    
    # Start grid bots for each configured pair
    for pair in GRID_TRADING_PAIRS:
        if pair not in ALLOWED_ASSETS:
            logger.warning(f"Grid trading pair {pair} not in allowed assets. Skipping...")
            continue
            
        logger.info(f"Starting grid bot for {pair}...")
        success = await grid_manager.start_grid_bot(
            backpack=backpack,
            symbol=pair,
            grid_levels=GRID_LEVELS,
            grid_spread=GRID_SPREAD,
            order_size=GRID_ORDER_SIZE,
            take_profit_percentage=TAKE_PROFIT_PERCENTAGE
        )
        
        if success:
            logger.info(colored(f"Grid bot for {pair} started successfully", "green"))
        else:
            logger.error(f"Failed to start grid bot for {pair}")
    
    # Let grid bots run until user interrupts
    try:
        active_bots = grid_manager.get_active_bots()
        if not active_bots:
            logger.warning("No grid bots were started. Check configuration.")
            return
            
        logger.info(f"Running {len(active_bots)} grid bots: {', '.join(active_bots)}")
        logger.info("Press Ctrl+C to stop grid trading...")
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Grid trading interrupted by user")
    except Exception as e:
        logger.error(f"Error in grid trading: {e}")
    finally:
        # Ensure all bots are stopped
        logger.info("Stopping all grid bots...")
        await grid_manager.stop_all_bots()
        logger.info("All grid bots stopped")


async def main():
    bot_info("BACKPACK_AUTO")

    autoreger = AutoReger.get_accounts(ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH)
    await autoreger.start(worker_task, THREADS)


if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
