"""
Browser-based scraper using Playwright for sites with strong anti-bot measures.
This actually controls a real browser, so it bypasses most blocking.
"""

import asyncio
import re
from typing import List, Dict, Any
from datetime import datetime


class BrowserScraper:
    """
    Playwright-based scraper for Amazon and other protected sites.
    Requires: pip install playwright && playwright install chromium
    """

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def _init_browser(self):
        """Initialize the browser."""
        try:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Set to False to see the browser
            )
            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()
        except ImportError:
            print("Playwright not installed. Run:")
            print("  pip install playwright")
            print("  playwright install chromium")
            return False
        return True

    async def _close_browser(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def scrape_amazon_movers_shakers(self, category: str = "kitchen", limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape Amazon Movers & Shakers using a real browser.

        Args:
            category: Category to scrape
            limit: Number of products

        Returns:
            List of product dictionaries
        """
        categories = {
            "kitchen": "kitchen",
            "home": "home-garden",
            "fitness": "exercise-and-fitness",
            "sports": "sporting-goods",
            "electronics": "electronics",
            "beauty": "beauty",
            "baby": "baby-products",
            "pets": "pet-supplies",
            "garden": "lawn-garden",
            "tools": "hi",
        }

        if category not in categories:
            print(f"Unknown category: {category}")
            return []

        url = f"https://www.amazon.com/gp/movers-and-shakers/{categories[category]}"

        if not await self._init_browser():
            return []

        products = []

        try:
            print(f"  Loading Amazon Movers & Shakers ({category})...")
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Wait for products to load
            await self.page.wait_for_selector('[data-asin]', timeout=15000)

            # Get all product elements
            product_elements = await self.page.query_selector_all('[data-asin]:not([data-asin=""])')

            for elem in product_elements[:limit]:
                try:
                    asin = await elem.get_attribute('data-asin')
                    if not asin:
                        continue

                    # Get product name
                    name_elem = await elem.query_selector('a.a-link-normal span, .p13n-sc-truncate, ._cDEzb_p13n-sc-css-line-clamp-1_1Fn1y')
                    name = await name_elem.inner_text() if name_elem else ""

                    if not name or len(name) < 5:
                        # Try alternative selector
                        link = await elem.query_selector('a[href*="/dp/"]')
                        if link:
                            name = await link.get_attribute('title') or await link.inner_text()

                    if not name or len(name) < 5:
                        continue

                    # Get price
                    price_elem = await elem.query_selector('.a-price .a-offscreen, .p13n-sc-price')
                    price = await price_elem.inner_text() if price_elem else ""

                    # Get rating
                    rating = 0.0
                    rating_elem = await elem.query_selector('.a-icon-alt')
                    if rating_elem:
                        rating_text = await rating_elem.inner_text()
                        match = re.search(r'([\d.]+)', rating_text)
                        if match:
                            rating = float(match.group(1))

                    # Get rank change percentage
                    rank_elem = await elem.query_selector('.zg-bdg-text, .zg-percent-change')
                    rank_change = await rank_elem.inner_text() if rank_elem else ""

                    # Get product URL
                    link = await elem.query_selector('a[href*="/dp/"]')
                    product_url = ""
                    if link:
                        href = await link.get_attribute('href')
                        if href:
                            if href.startswith('/'):
                                product_url = f"https://www.amazon.com{href}"
                            else:
                                product_url = href

                    products.append({
                        "asin": asin,
                        "name": name.strip()[:100],
                        "category": category,
                        "price": price,
                        "rating": rating,
                        "rank_change": rank_change,
                        "url": product_url,
                        "source": "amazon_movers_shakers",
                        "scraped_at": datetime.utcnow(),
                    })

                except Exception as e:
                    continue

            print(f"  Found {len(products)} products")

        except Exception as e:
            print(f"  Error: {e}")

        finally:
            await self._close_browser()

        return products

    def scrape_amazon_sync(self, category: str = "kitchen", limit: int = 20) -> List[Dict[str, Any]]:
        """
        Synchronous wrapper for async scraping.
        Use this from non-async code.
        """
        return asyncio.run(self.scrape_amazon_movers_shakers(category, limit))


def get_amazon_trending(categories: List[str] = None, limit_per_category: int = 10) -> List[Dict[str, Any]]:
    """
    Get trending products from Amazon across multiple categories.

    Args:
        categories: List of categories (default: kitchen, fitness, home)
        limit_per_category: Products per category

    Returns:
        Combined list of trending products
    """
    if categories is None:
        categories = ["kitchen", "fitness", "home"]

    scraper = BrowserScraper()
    all_products = []

    for category in categories:
        products = scraper.scrape_amazon_sync(category, limit_per_category)
        all_products.extend(products)

    return all_products


# Quick test
if __name__ == "__main__":
    print("Testing browser-based Amazon scraper...")
    products = get_amazon_trending(["kitchen"], limit_per_category=5)
    for p in products:
        print(f"  - {p['name'][:50]} | {p['price']} | {p['rank_change']}")
