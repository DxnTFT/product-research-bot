"""
Async Browser Scraper with Browser Reuse

Uses thread pool to run Playwright (avoids Windows asyncio subprocess issues).
Key optimization: Keeps browser instance open across multiple searches.

Usage:
    async with AsyncBrowserScraper() as scraper:
        products = await scraper.search_products_batch(keywords)
"""

import asyncio
import random
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from .browser_scraper import BrowserScraper, parse_price
from .rate_limiter import RateLimiter


class AsyncBrowserScraper:
    """
    Async Amazon scraper that wraps sync BrowserScraper.

    Uses ThreadPoolExecutor to avoid Windows asyncio + Playwright conflicts.
    The sync BrowserScraper handles browser lifecycle internally.

    Usage:
        async with AsyncBrowserScraper(delay=30.0) as scraper:
            products = await scraper.search_products_batch(
                keywords=["air fryer case", "yoga mat"],
                products_per_keyword=3
            )
    """

    def __init__(self, delay: float = 15.0, min_delay: float = 8.0):
        """
        Initialize async browser scraper.

        Args:
            delay: Seconds between requests (default 30)
            min_delay: Minimum delay floor (default 15)
        """
        self.delay = delay
        self.min_delay = min_delay

        # Sync browser scraper (handles Playwright internally)
        self.sync_scraper = BrowserScraper(delay=delay)

        # Rate limiter
        self.rate_limiter = RateLimiter(
            domain="amazon.com",
            base_delay=delay,
            max_retries=2,
            jitter=5.0
        )

        # Thread pool for running sync code
        self.executor = ThreadPoolExecutor(max_workers=1)

        # Timing
        self.last_request_time = 0
        self.lock = asyncio.Lock()

        # Stats
        self.search_count = 0
        self.success_count = 0
        self.error_count = 0

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup executor."""
        self.executor.shutdown(wait=False)

    async def search_products(
        self,
        keyword: str,
        max_products: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search Amazon for products by keyword.

        Runs sync BrowserScraper in thread pool.

        Args:
            keyword: Search term
            max_products: Max products to return

        Returns:
            List of product dicts
        """
        try:
            # Run sync scraper in thread pool (avoids asyncio conflicts)
            loop = asyncio.get_event_loop()
            products = await loop.run_in_executor(
                self.executor,
                lambda: self.sync_scraper.search_amazon_sync(keyword, max_products)
            )

            if products:
                self.success_count += 1
            else:
                self.error_count += 1

            self.search_count += 1
            return products or []

        except Exception as e:
            print(f"    Search error: {str(e)[:50]}")
            self.error_count += 1
            self.search_count += 1
            return []

    async def search_products_batch(
        self,
        keywords: List[str],
        products_per_keyword: int = 3,
        min_price: float = 0.0,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Search Amazon for multiple keywords.

        Runs sequentially with rate limiting (Amazon is sensitive).

        Args:
            keywords: List of search terms
            products_per_keyword: Max products per keyword
            min_price: Minimum price filter (default 0 = no filter)
            progress_callback: Optional callback(current, total, keyword)

        Returns:
            List of all products found (deduplicated by ASIN, filtered by min_price)
        """
        all_products = []
        seen_asins = set()
        skipped_low_price = 0

        for i, keyword in enumerate(keywords):
            if progress_callback:
                progress_callback(i + 1, len(keywords), keyword)

            # Check circuit breaker
            if not self.rate_limiter.check_circuit_breaker():
                print(f"  Circuit breaker OPEN - stopping searches")
                break

            # Rate limiting (skip first)
            if i > 0:
                await self._async_delay()

            # Search
            products = await self.search_products(keyword, products_per_keyword)

            # Deduplicate by ASIN and filter by price
            for product in products:
                asin = product.get('asin')
                if asin and asin not in seen_asins:
                    # Apply min_price filter
                    if min_price > 0:
                        price = parse_price(product.get('price', ''))
                        if price < min_price:
                            skipped_low_price += 1
                            continue
                    all_products.append(product)
                    seen_asins.add(asin)

            # Track for circuit breaker
            if products:
                self.rate_limiter.track_success()
            else:
                self.rate_limiter.track_failure("No products found")

        if min_price > 0 and skipped_low_price > 0:
            print(f"  Filtered out {skipped_low_price} products below ${min_price:.0f}")

        return all_products

    async def _async_delay(self):
        """Apply async rate limiting between requests."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time

            if self.last_request_time > 0 and elapsed < self.delay:
                wait_time = max(self.min_delay, self.delay - elapsed)
                jitter = random.uniform(-3, 3)
                final_wait = max(self.min_delay, wait_time + jitter)
                print(f"    Waiting {final_wait:.0f}s...")
                await asyncio.sleep(final_wait)

            self.last_request_time = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """Get scraper statistics."""
        return {
            "searches": self.search_count,
            "successes": self.success_count,
            "errors": self.error_count,
            "success_rate": self.success_count / max(self.search_count, 1),
            "circuit_state": self.rate_limiter.circuit_breaker.get_state(),
        }


async def search_amazon_async(
    keywords: List[str],
    products_per_keyword: int = 3,
    delay: float = 30.0
) -> List[Dict[str, Any]]:
    """
    Convenience function for async Amazon search.

    Usage:
        products = await search_amazon_async(
            keywords=["air fryer", "yoga mat"],
            products_per_keyword=3
        )
    """
    async with AsyncBrowserScraper(delay=delay) as scraper:
        return await scraper.search_products_batch(
            keywords=keywords,
            products_per_keyword=products_per_keyword
        )
