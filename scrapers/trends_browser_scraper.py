"""
Playwright-based Google Trends scraper.
Uses real browser to bypass rate limits that block pytrends.
"""

import asyncio
import random
import re
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from .stealth_config import StealthConfig, UserAgentRotator
from .rate_limiter import RateLimiter


class TrendsBrowserScraper:
    """
    Scrape Google Trends using Playwright (real browser).

    This bypasses the rate limits that affect pytrends by acting
    like a real user browsing Google Trends.
    """

    # Seed keywords for each category (same as TrendsRisingSimple)
    CATEGORY_SEEDS = {
        "technology": ["smartphone", "laptop", "headphones", "smartwatch", "tablet"],
        "fashion_beauty": ["makeup", "skincare", "fashion", "shoes", "clothing"],
        "hobbies": ["gaming", "photography", "crafts", "art supplies", "hobby"],
        "pets": ["dog food", "cat toys", "pet supplies", "aquarium", "bird cage"],
        "shopping": ["deals", "online shopping", "gift ideas", "home decor", "kitchen gadgets"],
    }

    def __init__(self, delay: float = 10.0):
        self.browser = None
        self.context = None
        self.page = None
        self.delay = delay
        self.stealth = StealthConfig()
        self.user_agent_rotator = UserAgentRotator()

        self.rate_limiter = RateLimiter(
            domain="trends.google.com",
            base_delay=delay,
            max_retries=2,
            jitter=3.0
        )

    async def _init_browser(self) -> bool:
        """Initialize Playwright browser with stealth settings."""
        try:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()

            # Get stealth settings
            user_agent = self.user_agent_rotator.get_random()
            viewport = self.stealth.get_random_viewport()

            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )

            self.context = await self.browser.new_context(
                user_agent=user_agent,
                viewport=viewport,
                locale='en-US',
                timezone_id='America/New_York',
            )

            # Add stealth scripts
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """)

            self.page = await self.context.new_page()
            return True

        except Exception as e:
            print(f"    Browser init error: {str(e)[:50]}")
            return False

    async def _close_browser(self):
        """Close browser and cleanup."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except:
            pass
        finally:
            self.page = None
            self.context = None
            self.browser = None

    async def get_rising_queries(self, keyword: str, timeframe: str = "today 1-m") -> List[Dict[str, Any]]:
        """
        Get rising queries for a keyword from Google Trends.

        Args:
            keyword: Seed keyword to search
            timeframe: Time range (default: past month)

        Returns:
            List of rising queries with their data
        """
        rising_queries = []

        if not await self._init_browser():
            return []

        try:
            # Build Google Trends URL for related queries
            # Using explore page with the keyword
            url = f"https://trends.google.com/trends/explore?q={keyword}&geo=US&hl=en"

            print(f"    Fetching trends for '{keyword}'...", end=" ")

            # Random delay before request
            await asyncio.sleep(random.uniform(2, 4))

            # Navigate to trends page
            await self.page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for content to load
            await asyncio.sleep(random.uniform(3, 5))

            # Look for related queries section
            # Google Trends shows "Rising" and "Top" related queries

            # Try to find rising queries in the page
            try:
                # Wait for related queries widget
                await self.page.wait_for_selector('[class*="related-queries"]', timeout=10000)
            except:
                # Try alternate selector
                try:
                    await self.page.wait_for_selector('[class*="fe-related"]', timeout=5000)
                except:
                    pass

            # Extract rising queries from the page
            # Google Trends uses various class names, we'll try multiple approaches

            # Method 1: Look for Rising tab content
            rising_items = await self.page.query_selector_all('[class*="rising"] [class*="item"], [class*="feed-item"]')

            if not rising_items:
                # Method 2: Try broader selector
                rising_items = await self.page.query_selector_all('[class*="related"] a, [class*="query"] a')

            if not rising_items:
                # Method 3: Get all text that looks like queries
                content = await self.page.content()
                # Parse the page for query patterns
                rising_queries = self._parse_trends_page(content, keyword)
                if rising_queries:
                    print(f"found {len(rising_queries)} (parsed)")
                else:
                    print("no rising data found")
                return rising_queries

            for item in rising_items[:10]:  # Limit to 10 per keyword
                try:
                    text = await item.inner_text()
                    text = text.strip()

                    if text and len(text) > 2 and self._is_product_query(text):
                        rising_queries.append({
                            "title": text,
                            "category": "general",
                            "seed_keyword": keyword,
                            "search_volume": "rising"
                        })
                except:
                    continue

            if rising_queries:
                print(f"found {len(rising_queries)}")
            else:
                print("no rising data")

        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                print("timeout")
            else:
                print(f"error: {error_msg[:30]}")

        finally:
            await self._close_browser()

        return rising_queries

    def _parse_trends_page(self, html_content: str, seed_keyword: str) -> List[Dict[str, Any]]:
        """
        Parse Google Trends page HTML to extract related queries.
        Fallback method when selectors don't work.
        """
        queries = []

        # Look for patterns in the HTML that indicate related queries
        # Google Trends embeds data in various formats

        # Pattern 1: Look for query strings in JSON-like structures
        import re

        # Find potential query text (words that appear near "rising" or "related")
        patterns = [
            r'"query":"([^"]+)"',
            r'"title":"([^"]+)"',
            r'<span[^>]*>([A-Za-z][A-Za-z0-9\s]{3,30})</span>',
        ]

        seen = set()
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                match = match.strip()
                if (match and
                    len(match) > 3 and
                    match.lower() not in seen and
                    self._is_product_query(match) and
                    match.lower() != seed_keyword.lower()):

                    queries.append({
                        "title": match,
                        "category": "general",
                        "seed_keyword": seed_keyword,
                        "search_volume": "rising"
                    })
                    seen.add(match.lower())

                    if len(queries) >= 10:
                        break

            if len(queries) >= 10:
                break

        return queries

    def _is_product_query(self, query: str) -> bool:
        """Check if query looks like a product search."""
        query_lower = query.lower()

        # Skip informational queries
        skip_words = [
            "how to", "what is", "what are", "why", "when", "where",
            "tutorial", "guide", "tips", "best way", "diy",
            "near me", "store", "open", "hours",
            "recipe", "meaning", "definition", "wikipedia",
            "login", "sign in", "account", "password"
        ]

        for word in skip_words:
            if word in query_lower:
                return False

        # Skip news/events
        skip_patterns = [
            "died", "death", "arrested", "trial", "lawsuit",
            "election", "vote", "score", " vs ", "vs."
        ]

        for pattern in skip_patterns:
            if pattern in query_lower:
                return False

        # Reasonable length
        words = query.split()
        if len(words) < 1 or len(words) > 8:
            return False

        return True

    def get_rising_topics(
        self,
        categories: List[str] = None,
        max_per_seed: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get rising topics for multiple categories (sync wrapper).

        Args:
            categories: List of category names
            max_per_seed: Max queries per seed keyword

        Returns:
            List of all rising topics found
        """
        # Check if we're already in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, need to use a different approach
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self._get_rising_topics_async(categories, max_per_seed)
                )
                return future.result()
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            return asyncio.run(self._get_rising_topics_async(categories, max_per_seed))

    async def _get_rising_topics_async(
        self,
        categories: List[str] = None,
        max_per_seed: int = 10
    ) -> List[Dict[str, Any]]:
        """Async implementation of get_rising_topics."""

        if categories is None:
            categories = list(self.CATEGORY_SEEDS.keys())

        all_topics = []
        seen = set()

        for category in categories:
            if category not in self.CATEGORY_SEEDS:
                continue

            print(f"\n  Exploring {category.replace('_', ' ').title()}...")

            seeds = self.CATEGORY_SEEDS[category]

            for seed in seeds:
                # Rate limiting
                if not self.rate_limiter.check_circuit_breaker():
                    print(f"    Circuit breaker OPEN - skipping remaining seeds")
                    break

                # Delay between requests
                delay = self.delay + random.uniform(-2, 2)
                await asyncio.sleep(max(5, delay))

                # Get rising queries for this seed
                queries = await self.get_rising_queries(seed)

                # Track success/failure
                if queries:
                    self.rate_limiter.track_success()

                    for q in queries[:max_per_seed]:
                        q_lower = q["title"].lower()
                        if q_lower not in seen:
                            q["category"] = category
                            all_topics.append(q)
                            seen.add(q_lower)
                else:
                    self.rate_limiter.track_failure("No data returned")

        stats = self.rate_limiter.get_stats()
        print(f"\n  Browser scraper stats: {stats['successes']} successes, {stats['failures']} failures")

        return all_topics


# Convenience function
def get_trending_with_browser(
    categories: List[str] = None,
    max_per_seed: int = 10,
    delay: float = 10.0
) -> List[Dict[str, Any]]:
    """
    Get trending topics using browser-based scraping.

    Usage:
        topics = get_trending_with_browser(
            categories=["technology", "shopping"],
            max_per_seed=10
        )
    """
    scraper = TrendsBrowserScraper(delay=delay)
    return scraper.get_rising_topics(categories=categories, max_per_seed=max_per_seed)
