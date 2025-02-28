import asyncio
import sys
from art import text2art
from termcolor import colored, cprint

from inputs.config import PROXIES_FILE_PATH
from core.utils.logger import logger
from core.utils.proxy_checker import ProxyChecker
from core.utils.file_manager import str_to_file

async def main():
    cprint(text2art("PROXY CHECKER"), 'cyan')
    print(
        f"{colored('Backpack Volume Auto - Proxy Validation Tool', color='light_yellow')}\n"
    )
    
    # Validate all proxies in the file
    working_proxies, failed_proxies = await ProxyChecker.validate_proxies_from_file(PROXIES_FILE_PATH)
    
    total = len(working_proxies) + len(failed_proxies)
    
    if total == 0:
        logger.warning(f"No proxies found in {PROXIES_FILE_PATH}. Add some proxies to use this tool.")
        return
    
    success_ratio = len(working_proxies) / total * 100 if total > 0 else 0
    
    print()
    logger.info(f"Results Summary:")
    logger.info(f"  Total Proxies: {total}")
    logger.info(f"  Working: {len(working_proxies)} ({success_ratio:.1f}%)")
    logger.info(f"  Failed: {len(failed_proxies)}")
    
    # Ask if the user wants to save only working proxies
    if working_proxies and failed_proxies:
        print()
        response = input(colored("Would you like to update proxies.txt to contain only working proxies? (y/n): ", "yellow"))
        
        if response.lower() == 'y':
            # Backup the original file
            backup_path = f"{PROXIES_FILE_PATH}.bak"
            with open(PROXIES_FILE_PATH, 'r') as source:
                with open(backup_path, 'w') as backup:
                    backup.write(source.read())
            
            # Replace with only working proxies
            with open(PROXIES_FILE_PATH, 'w') as f:
                for proxy in working_proxies:
                    f.write(f"{proxy}\n")
            
            logger.info(f"Updated {PROXIES_FILE_PATH} with {len(working_proxies)} working proxies.")
            logger.info(f"Original file backed up to {backup_path}")
    
    # Inform about next steps
    print()
    logger.info(f"You can now run the main bot with confidence in your proxy configuration!")
    logger.info(f"Run the bot: python main.py")

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())