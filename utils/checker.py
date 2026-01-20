import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
from typing import Tuple, Optional
from config import TEST_URLS, TIMEOUT


async def check_proxy(proxy: str, protocol: str, semaphore: asyncio.Semaphore) -> Tuple[str, bool]:
    """
    Checks if a proxy is alive.
    For HTTP/HTTPS: uses aiohttp with proxy parameter.
    For SOCKS4/5: uses aiohttp_socks ProxyConnector.
    """
    async with semaphore:
        for test_url in TEST_URLS:
            try:
                # Prepare arguments for request
                session_kwargs = {}
                request_kwargs = {
                    'timeout': aiohttp.ClientTimeout(total=TIMEOUT),
                }

                if protocol in ('http', 'https'):
                    request_kwargs['proxy'] = f'http://{proxy}'
                    request_kwargs['ssl'] = False if protocol == 'https' else None
                elif protocol in ('socks4', 'socks5'):
                    connector = ProxyConnector.from_url(f'{protocol}://{proxy}')
                    session_kwargs['connector'] = connector
                else:
                    return proxy, False

                async with aiohttp.ClientSession(**session_kwargs) as session:
                    async with session.get(test_url, **request_kwargs) as response:
                        if response.status == 200:
                            return proxy, True

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                OSError,
                Exception
            ):
                continue
        
        return proxy, False

async def batch_geolocate_proxies(proxies: list[str]) -> dict[str, dict]:
    """
    Geolocates a list of proxies using ip-api.com batch endpoint.
    Returns: {proxy_ip: {'country': 'US', 'countryCode': 'US', ...}}
    """
    api_url = "http://ip-api.com/batch"
    results = {}
    
    # Extract IPs from proxies (remove ports)
    ips = [p.split(':')[0] for p in proxies]
    
    # Process in chunks of 100 (API limit)
    chunk_size = 100
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(ips), chunk_size):
            chunk = ips[i:i + chunk_size]
            try:
                async with session.post(api_url, json=chunk, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        for ip, info in zip(chunk, data):
                            if info.get('status') == 'success':
                                results[ip] = {
                                    'country': info.get('country', 'Unknown'),
                                    'countryCode': info.get('countryCode', '??'),
                                    'city': info.get('city', 'Unknown')
                                }
            except Exception:
                continue
                
    return results
