"""
Shopify Competition Scraper
Checks how many Shopify stores are selling a product
"""

import requests
import time
from typing import Dict, Any
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


class ShopifyScraper:
    """Check Shopify marketplace competition for products."""

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.ua = UserAgent()

    def check_competition(self, product_name: str) -> Dict[str, Any]:
        """
        Check how many Shopify stores sell this product.

        Args:
            product_name: Product to search for

        Returns:
            Dict with competition metrics
        """
        # Google search for Shopify stores selling this product
        query = f'site:myshopify.com "{product_name}"'

        try:
            # Use Google search
            url = "https://www.google.com/search"
            headers = {
                "User-Agent": self.ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
            }

            params = {
                "q": query,
                "num": 50,  # Get more results
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse results
            soup = BeautifulSoup(response.text, 'html.parser')

            # Count search results
            # Google shows "About X results" in the stats
            stats_text = soup.find("div", {"id": "result-stats"})

            result_count = 0
            if stats_text:
                text = stats_text.get_text()
                # Extract number from "About 123 results"
                import re
                match = re.search(r'About ([\d,]+) results', text)
                if match:
                    result_count = int(match.group(1).replace(',', ''))
                else:
                    # Alternative: just count visible results
                    result_count = len(soup.find_all("div", class_="g"))
            else:
                # Fallback: count search result divs
                result_count = len(soup.find_all("div", class_="g"))

            # Determine saturation level
            if result_count < 10:
                saturation = "very_low"
                score = 90
            elif result_count < 30:
                saturation = "low"
                score = 70
            elif result_count < 100:
                saturation = "medium"
                score = 50
            elif result_count < 300:
                saturation = "high"
                score = 30
            else:
                saturation = "very_high"
                score = 10

            time.sleep(self.delay)

            return {
                "shopify_stores": result_count,
                "shopify_saturation": saturation,
                "shopify_score": score,
            }

        except Exception as e:
            print(f"Error checking Shopify competition: {e}")
            return {
                "shopify_stores": 0,
                "shopify_saturation": "unknown",
                "shopify_score": 50,  # Neutral score if can't determine
                "error": str(e)
            }
