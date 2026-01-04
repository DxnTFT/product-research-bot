"""
Amazon scraper for finding trending/rising products.
Targets Movers & Shakers and Best Sellers pages.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import time
import random

from .base_scraper import BaseScraper


class AmazonScraper(BaseScraper):
    """Scraper for Amazon trending products."""

    BASE_URL = "https://www.amazon.com"

    # Category URLs for Movers & Shakers (products gaining sales rank)
    MOVERS_SHAKERS = {
        "kitchen": "/gp/movers-and-shakers/kitchen/ref=zg_bsms_nav_kitchen_0",
        "home": "/gp/movers-and-shakers/home-garden/ref=zg_bsms_nav_home-garden_0",
        "sports": "/gp/movers-and-shakers/sporting-goods/ref=zg_bsms_nav_sporting-goods_0",
        "fitness": "/gp/movers-and-shakers/exercise-and-fitness/ref=zg_bsms_nav_exercise-and-fitness_0",
        "electronics": "/gp/movers-and-shakers/electronics/ref=zg_bsms_nav_electronics_0",
        "beauty": "/gp/movers-and-shakers/beauty/ref=zg_bsms_nav_beauty_0",
    }

    # Best Sellers pages
    BEST_SELLERS = {
        "kitchen": "/Best-Sellers-Kitchen-Dining/zgbs/kitchen/ref=zg_bs_nav_kitchen_0",
        "home": "/Best-Sellers-Home-Kitchen/zgbs/home-garden/ref=zg_bs_nav_home-garden_0",
        "sports": "/Best-Sellers-Sports-Outdoors/zgbs/sporting-goods/ref=zg_bs_nav_sporting-goods_0",
        "fitness": "/Best-Sellers-Sports-Fitness/zgbs/exercise-and-fitness/ref=zg_bs_nav_exercise-and-fitness_0",
    }

    def __init__(self, delay: float = 3.0):
        super().__init__(delay)
        self.session = requests.Session()

    def get_headers(self) -> Dict[str, str]:
        """Get headers that look like a real browser."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def scrape_movers_shakers(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape Amazon Movers & Shakers page for a category.
        These are products with biggest sales rank gains in last 24 hours.

        Args:
            category: Category key (kitchen, home, sports, fitness, etc.)
            limit: Number of products to return

        Returns:
            List of trending product dictionaries
        """
        if category not in self.MOVERS_SHAKERS:
            print(f"Unknown category: {category}. Available: {list(self.MOVERS_SHAKERS.keys())}")
            return []

        url = f"{self.BASE_URL}{self.MOVERS_SHAKERS[category]}"
        return self._scrape_product_list(url, category, limit, "movers_shakers")

    def scrape_best_sellers(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape Amazon Best Sellers page for a category.

        Args:
            category: Category key
            limit: Number of products to return

        Returns:
            List of best-selling product dictionaries
        """
        if category not in self.BEST_SELLERS:
            print(f"Unknown category: {category}. Available: {list(self.BEST_SELLERS.keys())}")
            return []

        url = f"{self.BASE_URL}{self.BEST_SELLERS[category]}"
        return self._scrape_product_list(url, category, limit, "best_sellers")

    def _scrape_product_list(self, url: str, category: str, limit: int, list_type: str) -> List[Dict[str, Any]]:
        """Scrape a product list page."""
        products = []

        try:
            self.rate_limit()
            response = self.session.get(url, headers=self.get_headers(), timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find product containers (Amazon's structure varies)
            product_containers = soup.find_all("div", {"data-asin": True})

            if not product_containers:
                # Try alternative selectors
                product_containers = soup.find_all("div", class_=re.compile(r"zg-grid-general-faceout"))

            for container in product_containers[:limit]:
                product = self._parse_product(container, category, list_type)
                if product:
                    products.append(product)

        except requests.RequestException as e:
            print(f"Error scraping Amazon {list_type}: {e}")
        except Exception as e:
            print(f"Error parsing Amazon page: {e}")

        return products

    def _parse_product(self, container, category: str, list_type: str) -> Optional[Dict[str, Any]]:
        """Parse a single product container."""
        try:
            # Get ASIN (Amazon product ID)
            asin = container.get("data-asin", "")
            if not asin:
                return None

            # Get product name
            name_el = container.find("span", class_=re.compile(r"zg-text-center-align")) or \
                      container.find("a", class_=re.compile(r"a-link-normal")) or \
                      container.find("div", class_=re.compile(r"p13n-sc-truncate"))

            name = ""
            if name_el:
                name = name_el.get_text(strip=True)

            if not name:
                # Try to find any text that looks like a product name
                link = container.find("a", href=re.compile(r"/dp/"))
                if link:
                    name = link.get_text(strip=True) or link.get("title", "")

            if not name or len(name) < 5:
                return None

            # Get price
            price = ""
            price_el = container.find("span", class_=re.compile(r"price|a-color-price"))
            if price_el:
                price = price_el.get_text(strip=True)

            # Get rating
            rating = 0.0
            rating_el = container.find("span", class_=re.compile(r"a-icon-alt"))
            if rating_el:
                rating_text = rating_el.get_text()
                rating_match = re.search(r"([\d.]+)", rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))

            # Get review count
            review_count = 0
            review_el = container.find("span", class_=re.compile(r"a-size-small"))
            if review_el:
                review_text = review_el.get_text().replace(",", "")
                review_match = re.search(r"(\d+)", review_text)
                if review_match:
                    review_count = int(review_match.group(1))

            # Get rank change (for movers & shakers)
            rank_change = ""
            rank_el = container.find("span", class_=re.compile(r"zg-percent-change"))
            if rank_el:
                rank_change = rank_el.get_text(strip=True)

            # Get product URL
            link = container.find("a", href=re.compile(r"/dp/"))
            product_url = ""
            if link:
                href = link.get("href", "")
                if href.startswith("/"):
                    product_url = f"{self.BASE_URL}{href}"
                else:
                    product_url = href

            return {
                "asin": asin,
                "name": self._clean_product_name(name),
                "category": category,
                "price": price,
                "rating": rating,
                "review_count": review_count,
                "rank_change": rank_change,
                "url": product_url,
                "source": f"amazon_{list_type}",
                "scraped_at": datetime.utcnow(),
            }

        except Exception as e:
            return None

    def _clean_product_name(self, name: str) -> str:
        """Clean up product name for better searching."""
        # Remove excessive details, keep brand + product type
        name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
        name = name[:100]  # Truncate long names
        return name.strip()

    def scrape(self, target: str, **kwargs) -> List[Dict[str, Any]]:
        """Generic scrape method for compatibility."""
        category = kwargs.get("category", "kitchen")
        limit = kwargs.get("limit", 20)
        list_type = kwargs.get("list_type", "movers_shakers")

        if list_type == "best_sellers":
            return self.scrape_best_sellers(category, limit)
        return self.scrape_movers_shakers(category, limit)

    def extract_products(self, content: str) -> List[str]:
        """Not used for Amazon scraper - we get structured data."""
        return []

    def get_all_trending(self, categories: List[str] = None, limit_per_category: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending products across multiple categories.

        Args:
            categories: List of categories to scan (default: all)
            limit_per_category: Products per category

        Returns:
            Combined list of trending products
        """
        if categories is None:
            categories = list(self.MOVERS_SHAKERS.keys())

        all_products = []

        for category in categories:
            print(f"  Scanning Amazon {category}...", end=" ")
            products = self.scrape_movers_shakers(category, limit_per_category)
            all_products.extend(products)
            print(f"Found {len(products)} products")

        return all_products
