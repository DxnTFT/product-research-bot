"""
Browser-based scraper using Playwright for sites with strong anti-bot measures.
This actually controls a real browser, so it bypasses most blocking.
Includes stealth configuration to avoid detection.
"""

import asyncio
import re
import random
import time
from typing import List, Dict, Any
from datetime import datetime

from .stealth_config import UserAgentRotator, StealthConfig
from .rate_limiter import RateLimiter


def parse_price(price_str: str) -> float:
    """
    Parse a price string like '$29.99' or '$1,234.56' to a float.
    Returns 0.0 if parsing fails.
    """
    if not price_str or price_str == "N/A":
        return 0.0
    try:
        # Remove currency symbols and commas
        clean = re.sub(r'[^\d.]', '', price_str)
        return float(clean) if clean else 0.0
    except (ValueError, TypeError):
        return 0.0


class BrowserScraper:
    """
    Playwright-based scraper for Amazon and other protected sites.
    Requires: pip install playwright && playwright install chromium
    """

    def __init__(self, delay: float = 15.0):
        self.browser = None
        self.context = None
        self.page = None
        self.delay = delay

        # Stealth configuration
        self.ua_rotator = UserAgentRotator()
        self.stealth_config = StealthConfig()

        # Rate limiter for Amazon
        self.rate_limiter = RateLimiter(
            domain="amazon.com",
            base_delay=delay,
            max_retries=2,
            jitter=5.0
        )

    async def _init_browser(self):
        """Initialize the browser with stealth settings."""
        try:
            from playwright.async_api import async_playwright

            # Get stealth settings
            viewport = self.stealth_config.get_random_viewport()
            user_agent = self.ua_rotator.get_next()
            timezone = self.stealth_config.get_random_timezone()
            locale = self.stealth_config.get_random_locale()

            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            self.context = await self.browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                locale=locale,
                timezone_id=timezone,
            )

            # Add stealth scripts to evade detection
            await self.context.add_init_script("""
                // Override webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)

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

    async def search_amazon_products(self, keyword: str, max_products: int = 5) -> List[Dict[str, Any]]:
        """
        Search Amazon for products by keyword using a real browser.

        Args:
            keyword: Search term (e.g., "S26 Ultra case", "wireless earbuds")
            max_products: Maximum products to return

        Returns:
            List of product dictionaries
        """
        if not await self._init_browser():
            return []

        products = []

        try:
            # Build search URL
            search_query = keyword.replace(' ', '+')
            url = f"https://www.amazon.com/s?k={search_query}"

            print(f"    Searching Amazon for: {keyword}...", end=" ")

            # Add random delay to seem more human
            await asyncio.sleep(random.uniform(2, 5))

            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Wait for search results
            try:
                await self.page.wait_for_selector('[data-component-type="s-search-result"]', timeout=15000)
            except:
                # Try alternative selector
                await self.page.wait_for_selector('[data-asin]', timeout=10000)

            # Get search result elements
            result_elements = await self.page.query_selector_all('[data-component-type="s-search-result"]')

            if not result_elements:
                # Fallback selector
                result_elements = await self.page.query_selector_all('[data-asin]:not([data-asin=""])')

            for elem in result_elements[:max_products]:
                try:
                    asin = await elem.get_attribute('data-asin')
                    if not asin:
                        continue

                    # Product title - try multiple selectors
                    name = ""
                    title_selectors = [
                        'h2 a.a-link-normal span.a-text-normal',
                        'span.a-size-medium.a-color-base.a-text-normal',
                        'span.a-size-base-plus.a-color-base.a-text-normal',
                        'h2 a span',
                        'h2 span',
                        '.a-size-medium',
                        '.a-size-base-plus',
                    ]

                    for selector in title_selectors:
                        name_elem = await elem.query_selector(selector)
                        if name_elem:
                            candidate = await name_elem.inner_text()
                            candidate = candidate.strip() if candidate else ""
                            # Skip badges, short names, and generic labels
                            skip_patterns = [
                                "amazon's choice",
                                "overall pick",
                                "best seller",
                                "limited time deal",
                                "climate pledge",
                            ]
                            if candidate and len(candidate) > 10:
                                if not any(p in candidate.lower() for p in skip_patterns):
                                    name = candidate
                                    break

                    # Fallback: get from link title attribute
                    if not name or len(name) < 10:
                        link = await elem.query_selector('a[href*="/dp/"]')
                        if link:
                            title_attr = await link.get_attribute('title')
                            if title_attr and len(title_attr) > 10:
                                name = title_attr

                    if not name or len(name) < 5:
                        continue

                    # Price
                    price = "N/A"
                    price_selectors = [
                        '.a-price .a-offscreen',
                        '.a-price-whole',
                        'span.a-price span',
                    ]

                    for selector in price_selectors:
                        price_elem = await elem.query_selector(selector)
                        if price_elem:
                            price_text = await price_elem.inner_text()
                            if price_text:
                                price = price_text.strip()
                                if not price.startswith('$'):
                                    price = f"${price}"
                                break

                    # Rating
                    rating = 0.0
                    rating_elem = await elem.query_selector('.a-icon-alt')
                    if rating_elem:
                        rating_text = await rating_elem.inner_text()
                        match = re.search(r'([\d.]+)', rating_text)
                        if match:
                            rating = float(match.group(1))

                    # Review count - try multiple approaches
                    reviews = 0

                    # Method 1: aria-label on the reviews link (most reliable)
                    reviews_link = await elem.query_selector('a[href*="customerReviews"], a[href*="#reviews"]')
                    if reviews_link:
                        aria_label = await reviews_link.get_attribute('aria-label')
                        if aria_label:
                            # Format: "4,532 ratings" or "See 4532 customer reviews"
                            match = re.search(r'([\d,]+)\s*(?:ratings?|reviews?|customer)', aria_label, re.IGNORECASE)
                            if match:
                                reviews = int(match.group(1).replace(',', ''))

                    # Method 2: Text content of review count span
                    if reviews == 0:
                        reviews_selectors = [
                            'span.a-size-base.s-underline-text',
                            'span[data-csa-c-type="Rating"]',
                            '.a-size-base.s-underline-text',
                            'a.s-underline-text span',
                            '[data-component-type="s-product-reviews"] span',
                        ]

                        for selector in reviews_selectors:
                            reviews_elem = await elem.query_selector(selector)
                            if reviews_elem:
                                reviews_text = await reviews_elem.inner_text()
                                # Clean and extract number: "4,532" or "(4,532)" or "4.5K"
                                reviews_text = reviews_text.strip()

                                # Handle "4.5K" format
                                k_match = re.search(r'([\d.]+)K', reviews_text, re.IGNORECASE)
                                if k_match:
                                    reviews = int(float(k_match.group(1)) * 1000)
                                    break

                                # Handle regular number format
                                reviews_text = reviews_text.replace(',', '').replace('(', '').replace(')', '')
                                match = re.search(r'(\d+)', reviews_text)
                                if match:
                                    reviews = int(match.group(1))
                                    break

                    # Method 3: Look for the rating row and get adjacent text
                    if reviews == 0:
                        rating_row = await elem.query_selector('[data-cy="reviews-block"], .a-row.a-size-small')
                        if rating_row:
                            row_text = await rating_row.inner_text()
                            # Extract number from text like "4.5 out of 5 stars 4,532"
                            numbers = re.findall(r'(?<!\.)(\d[\d,]*)', row_text)
                            for num_str in numbers:
                                num = int(num_str.replace(',', ''))
                                if num > 10:  # Likely review count, not rating
                                    reviews = num
                                    break

                    # Product URL
                    product_url = ""
                    link = await elem.query_selector('a[href*="/dp/"]')
                    if link:
                        href = await link.get_attribute('href')
                        if href:
                            if href.startswith('/'):
                                product_url = f"https://www.amazon.com{href}"
                            else:
                                product_url = href

                    products.append({
                        "asin": asin,
                        "name": name.strip()[:150],
                        "price": price,
                        "rating": rating,
                        "reviews": reviews,
                        "url": product_url,
                        "search_keyword": keyword,
                        "source": "amazon_search",
                        "scraped_at": datetime.utcnow(),
                    })

                except Exception as e:
                    continue

            print(f"found {len(products)}")

        except Exception as e:
            print(f"error: {str(e)[:50]}")

        finally:
            await self._close_browser()

        return products

    def search_amazon_sync(self, keyword: str, max_products: int = 5) -> List[Dict[str, Any]]:
        """
        Synchronous wrapper for Amazon search.
        Use this from non-async code.
        """
        return asyncio.run(self.search_amazon_products(keyword, max_products))

    async def scrape_product_reviews(self, asin: str, max_reviews: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape reviews from an Amazon product page.

        Args:
            asin: Amazon product ASIN
            max_reviews: Maximum reviews to scrape

        Returns:
            List of review dictionaries with text, rating, helpful_votes
        """
        if not await self._init_browser():
            return []

        reviews = []

        try:
            # Try different review URL formats
            urls_to_try = [
                f"https://www.amazon.com/dp/{asin}#customerReviews",
                f"https://www.amazon.com/product-reviews/{asin}",
                f"https://www.amazon.com/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm?reviewerType=all_reviews",
            ]

            print(f"    Scraping reviews for ASIN {asin}...", end=" ")

            review_elements = []
            for url in urls_to_try:
                await asyncio.sleep(random.uniform(2, 4))
                await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # Wait for reviews to load - try multiple selectors
                review_selectors = [
                    '[data-hook="review"]',
                    '.review',
                    '[data-hook="review-body"]',
                    '.a-section.review',
                    '#cm_cr-review_list .a-section',
                ]

                for selector in review_selectors:
                    try:
                        await self.page.wait_for_selector(selector, timeout=8000)
                        review_elements = await self.page.query_selector_all(selector)
                        if review_elements:
                            break
                    except:
                        continue

                if review_elements:
                    break

            if not review_elements:
                print("no reviews found")
                return []

            for elem in review_elements[:max_reviews]:
                try:
                    # Review text
                    text_elem = await elem.query_selector('[data-hook="review-body"] span')
                    review_text = await text_elem.inner_text() if text_elem else ""

                    # Rating (1-5 stars)
                    rating = 0
                    rating_elem = await elem.query_selector('[data-hook="review-star-rating"] span, [data-hook="cmps-review-star-rating"] span')
                    if rating_elem:
                        rating_text = await rating_elem.inner_text()
                        match = re.search(r'([\d.]+)', rating_text)
                        if match:
                            rating = float(match.group(1))

                    # Review title
                    title_elem = await elem.query_selector('[data-hook="review-title"] span:not(.a-icon-alt)')
                    title = await title_elem.inner_text() if title_elem else ""

                    # Helpful votes
                    helpful = 0
                    helpful_elem = await elem.query_selector('[data-hook="helpful-vote-statement"]')
                    if helpful_elem:
                        helpful_text = await helpful_elem.inner_text()
                        match = re.search(r'(\d+)', helpful_text)
                        if match:
                            helpful = int(match.group(1))

                    # Verified purchase
                    verified_elem = await elem.query_selector('[data-hook="avp-badge"]')
                    verified = verified_elem is not None

                    if review_text or title:
                        reviews.append({
                            "asin": asin,
                            "title": title.strip() if title else "",
                            "text": review_text.strip() if review_text else "",
                            "rating": rating,
                            "helpful_votes": helpful,
                            "verified_purchase": verified,
                        })

                except Exception as e:
                    continue

            print(f"found {len(reviews)}")

        except Exception as e:
            print(f"error: {str(e)[:50]}")

        finally:
            await self._close_browser()

        return reviews

    def scrape_reviews_sync(self, asin: str, max_reviews: int = 20) -> List[Dict[str, Any]]:
        """
        Synchronous wrapper for review scraping.
        """
        return asyncio.run(self.scrape_product_reviews(asin, max_reviews))

    def get_product_sentiment(self, asin: str, sentiment_analyzer, max_reviews: int = 15) -> Dict[str, Any]:
        """
        Get sentiment analysis from Amazon reviews for a product.

        Args:
            asin: Amazon product ASIN
            sentiment_analyzer: SentimentAnalyzer instance
            max_reviews: Max reviews to analyze

        Returns:
            Dictionary with amazon_sentiment, amazon_reviews_analyzed, etc.
        """
        reviews = self.scrape_reviews_sync(asin, max_reviews)

        if not reviews:
            return {
                "amazon_sentiment": 0,
                "amazon_reviews_analyzed": 0,
                "amazon_positive": 0,
                "amazon_negative": 0,
                "amazon_avg_rating": 0,
                "amazon_sentiment_ratio": 0.5,
            }

        # Analyze sentiment for each review
        sentiments = []
        total_rating = 0

        for review in reviews:
            # Combine title and text for better analysis
            full_text = f"{review.get('title', '')} {review.get('text', '')}"
            label, score = sentiment_analyzer.get_sentiment_label(full_text)

            # Weight by helpful votes (more helpful = more reliable)
            weight = max(review.get('helpful_votes', 0), 1)

            sentiments.append({
                "label": label,
                "score": score,
                "weight": weight,
                "rating": review.get('rating', 0),
            })

            total_rating += review.get('rating', 0)

        # Calculate weighted sentiment
        total_weight = sum(s["weight"] for s in sentiments)
        weighted_sentiment = sum(
            s["score"] * s["weight"] for s in sentiments
        ) / total_weight if total_weight > 0 else 0

        positive_count = sum(1 for s in sentiments if s["label"] == "positive")
        negative_count = sum(1 for s in sentiments if s["label"] == "negative")

        return {
            "amazon_sentiment": round(weighted_sentiment, 3),
            "amazon_reviews_analyzed": len(reviews),
            "amazon_positive": positive_count,
            "amazon_negative": negative_count,
            "amazon_avg_rating": round(total_rating / len(reviews), 2) if reviews else 0,
            "amazon_sentiment_ratio": round(
                positive_count / max(positive_count + negative_count, 1), 2
            ),
        }

    def search_products_batch(
        self,
        keywords: List[str],
        products_per_keyword: int = 3,
        min_price: float = 0.0,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Search Amazon for multiple keywords.

        Args:
            keywords: List of search terms
            products_per_keyword: Max products per keyword
            min_price: Minimum price filter (default 0 = no filter)
            progress_callback: Optional progress callback

        Returns:
            List of all products found (deduplicated, filtered by min_price)
        """
        all_products = []
        seen_asins = set()
        skipped_low_price = 0

        for i, keyword in enumerate(keywords):
            if progress_callback:
                progress_callback(i, len(keywords), keyword)

            # Check circuit breaker
            if not self.rate_limiter.check_circuit_breaker():
                print(f"  Circuit breaker OPEN - stopping searches")
                break

            # Rate limiting delay
            if i > 0:
                delay = self.delay + random.uniform(-5, 5)
                print(f"    Waiting {delay:.0f}s before next search...")
                time.sleep(max(15, delay))

            # Search
            products = self.search_amazon_sync(keyword, products_per_keyword)

            # Deduplicate by ASIN and filter by price
            for product in products:
                if product['asin'] not in seen_asins:
                    # Apply min_price filter
                    if min_price > 0:
                        price = parse_price(product.get('price', ''))
                        if price < min_price:
                            skipped_low_price += 1
                            continue
                    all_products.append(product)
                    seen_asins.add(product['asin'])

            # Track success/failure
            if products:
                self.rate_limiter.track_success()
            else:
                self.rate_limiter.track_failure("No products found")

        if min_price > 0 and skipped_low_price > 0:
            print(f"  Filtered out {skipped_low_price} products below ${min_price:.0f}")

        return all_products


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
