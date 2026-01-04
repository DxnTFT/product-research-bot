"""
Amazon Competition Checker
Analyzes market saturation on Amazon for a product
"""

import asyncio
from typing import Dict, Any
from playwright.async_api import async_playwright
import re


class AmazonCompetitionChecker:
    """Check Amazon competition levels for products."""

    async def check_competition(self, product_name: str) -> Dict[str, Any]:
        """
        Check Amazon competition for a product.

        Args:
            product_name: Product to search for

        Returns:
            Dict with competition metrics
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Search Amazon
                search_url = f"https://www.amazon.com/s?k={product_name.replace(' ', '+')}"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

                # Wait for results
                await page.wait_for_selector('[data-component-type="s-search-result"]', timeout=10000)

                # Extract metrics
                results = await page.query_selector_all('[data-component-type="s-search-result"]')
                result_count = len(results)

                # Get top products' review counts
                review_counts = []
                prices = []

                for i, result in enumerate(results[:10]):  # Top 10 products
                    # Reviews
                    review_elem = await result.query_selector('span[aria-label*="stars"]')
                    if review_elem:
                        aria_label = await review_elem.get_attribute('aria-label')
                        # Extract review count from "4.5 out of 5 stars 1,234"
                        match = re.search(r'([\d,]+)$', aria_label)
                        if match:
                            count = int(match.group(1).replace(',', ''))
                            review_counts.append(count)

                    # Price
                    price_elem = await result.query_selector('.a-price-whole')
                    if price_elem:
                        price_text = await price_elem.inner_text()
                        try:
                            price = float(price_text.replace(',', '').replace('$', ''))
                            prices.append(price)
                        except:
                            pass

                await browser.close()

                # Calculate competition metrics
                avg_reviews = sum(review_counts) / len(review_counts) if review_counts else 0
                max_reviews = max(review_counts) if review_counts else 0
                avg_price = sum(prices) / len(prices) if prices else 0

                # Determine saturation
                # High reviews = established competition
                if max_reviews > 10000 or avg_reviews > 3000:
                    saturation = "very_high"
                    score = 10
                elif max_reviews > 5000 or avg_reviews > 1500:
                    saturation = "high"
                    score = 30
                elif max_reviews > 1000 or avg_reviews > 500:
                    saturation = "medium"
                    score = 50
                elif max_reviews > 200 or avg_reviews > 100:
                    saturation = "low"
                    score = 70
                else:
                    saturation = "very_low"
                    score = 90

                return {
                    "amazon_results": result_count,
                    "amazon_avg_reviews": int(avg_reviews),
                    "amazon_max_reviews": max_reviews,
                    "amazon_avg_price": round(avg_price, 2) if avg_price else 0,
                    "amazon_saturation": saturation,
                    "amazon_score": score,
                }

        except Exception as e:
            print(f"Error checking Amazon competition: {e}")
            return {
                "amazon_results": 0,
                "amazon_avg_reviews": 0,
                "amazon_max_reviews": 0,
                "amazon_avg_price": 0,
                "amazon_saturation": "unknown",
                "amazon_score": 50,
                "error": str(e)
            }


def check_amazon_competition(product_name: str) -> Dict[str, Any]:
    """Synchronous wrapper for async competition check."""
    checker = AmazonCompetitionChecker()
    return asyncio.run(checker.check_competition(product_name))
