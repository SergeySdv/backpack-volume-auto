import asyncio
import time
from typing import List, Dict, Tuple, Optional

import aiohttp
from better_proxy import Proxy
from termcolor import colored

from core.utils.logger import logger

class ProxyChecker:
    """Utility for verifying proxy connections to Backpack API endpoints"""

    def __init__(self, test_url: str = "https://api.backpack.exchange/api/v1/markets"):
        """
        Initialize the ProxyChecker with a test URL
        
        Args:
            test_url: URL to test proxy connectivity against (defaults to Backpack markets API)
        """
        self.test_url = test_url
        self.timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout

    async def check_proxy(self, proxy_str: str) -> Tuple[bool, float, Optional[str]]:
        """
        Test if a proxy is working correctly
        
        Args:
            proxy_str: Proxy string in format "ip:port" or "ip:port:user:pass"
            
        Returns:
            Tuple of (success: bool, response_time: float, error_message: Optional[str])
        """
        if not proxy_str or not proxy_str.strip():
            return False, 0, "Empty proxy string"
            
        try:
            proxy_url = Proxy.from_str(proxy_str.strip()).as_url
            
            start_time = time.time()
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.test_url, proxy=proxy_url) as response:
                    elapsed = time.time() - start_time
                    
                    if response.status == 200:
                        return True, elapsed, None
                    else:
                        return False, elapsed, f"HTTP {response.status}: {await response.text()}"
                        
        except Exception as e:
            return False, 0, str(e)

    async def check_proxies(self, proxies: List[str]) -> Dict[str, Dict]:
        """
        Test multiple proxies and return their status
        
        Args:
            proxies: List of proxy strings
            
        Returns:
            Dictionary mapping proxy strings to their test results
        """
        results = {}
        tasks = []
        
        for proxy in proxies:
            task = asyncio.create_task(self.check_proxy(proxy))
            tasks.append((proxy, task))
            
        for proxy, task in tasks:
            success, response_time, error = await task
            results[proxy] = {
                "working": success,
                "response_time": response_time,
                "error": error
            }
            
        return results
        
    async def filter_working_proxies(self, proxies: List[str]) -> List[str]:
        """
        Filter and return only working proxies
        
        Args:
            proxies: List of proxy strings
            
        Returns:
            List of working proxy strings
        """
        results = await self.check_proxies(proxies)
        return [proxy for proxy, data in results.items() if data["working"]]
        
    @staticmethod
    async def validate_proxies_from_file(file_path: str) -> Tuple[List[str], List[str]]:
        """
        Validate proxies from a file and return working and non-working proxies
        
        Args:
            file_path: Path to file containing proxies (one per line)
            
        Returns:
            Tuple of (working_proxies: List[str], non_working_proxies: List[str])
        """
        from core.utils.file_manager import file_to_list
        
        logger.info(f"Validating proxies from {file_path}...")
        proxies = file_to_list(file_path)
        
        if not proxies:
            logger.warning(f"No proxies found in {file_path}")
            return [], []
            
        logger.info(f"Testing {len(proxies)} proxies...")
        
        checker = ProxyChecker()
        results = await checker.check_proxies(proxies)
        
        working = []
        non_working = []
        
        for proxy, data in results.items():
            if data["working"]:
                status = colored("✓", "green")
                time_str = colored(f"{data['response_time']:.2f}s", "green")
                working.append(proxy)
            else:
                status = colored("✗", "red")
                time_str = colored("Failed", "red")
                non_working.append(proxy)
                
            logger.info(f"Proxy {proxy}: {status} - Response Time: {time_str}")
            if not data["working"] and data["error"]:
                logger.debug(f"  Error: {data['error']}")
                
        logger.info(f"Proxy Check Summary: {len(working)} working, {len(non_working)} failed")
        
        return working, non_working