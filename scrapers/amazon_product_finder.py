"""
Amazon Product Finder
Finds actual products on Amazon related to trending topics
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import time
import re


class AmazonProductFinder:
    """Find products on Amazon related to trending keywords."""

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.base_url = "https://www.amazon.com"

    def find_products_for_topic(self, topic: str, max_products: int = 5) -> List[Dict[str, Any]]:
        """
        Find products on Amazon related to a trending topic.

        Args:
            topic: Trending topic/keyword
            max_products: Max products to return

        Returns:
            List of products with metadata
        """
        try:
            # Search Amazon
            search_url = f"{self.base_url}/s?k={topic.replace(' ', '+')}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }

            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            products = []

            # Find product cards
            product_cards = soup.find_all('div', {'data-component-type': 's-search-result'})

            for card in product_cards[:max_products]:
                try:
                    # Product title
                    title_elem = card.find('h2', {'class': 'a-size-mini'})
                    if not title_elem:
                        title_elem = card.find('h2')

                    if not title_elem:
                        continue

                    title_link = title_elem.find('a')
                    if not title_link:
                        continue

                    title = title_link.text.strip()

                    # Product URL
                    url_path = title_link.get('href', '')
                    product_url = f"{self.base_url}{url_path}" if url_path.startswith('/') else url_path

                    # Price
                    price = "N/A"
                    price_elem = card.find('span', {'class': 'a-price-whole'})
                    if price_elem:
                        price = f"${price_elem.text.strip()}"

                    # Rating
                    rating = 0
                    rating_elem = card.find('span', {'class': 'a-icon-alt'})
                    if rating_elem:
                        rating_text = rating_elem.text
                        match = re.search(r'(\d+\.?\d*)', rating_text)
                        if match:
                            rating = float(match.group(1))

                    # Reviews count
                    reviews = 0
                    reviews_elem = card.find('span', {'class': 'a-size-base'})
                    if reviews_elem:
                        reviews_text = reviews_elem.text
                        reviews_text = reviews_text.replace(',', '')
                        match = re.search(r'(\d+)', reviews_text)
                        if match:
                            reviews = int(match.group(1))

                    products.append({
                        "name": title,
                        "url": product_url,
                        "price": price,
                        "rating": rating,
                        "reviews": reviews,
                        "related_topic": topic
                    })

                except Exception as e:
                    continue

            time.sleep(self.delay)

            return products

        except Exception as e:
            print(f"    Error finding products for '{topic}': {e}")
            return []

    def find_products_batch(
        self,
        topics: List[str],
        products_per_topic: int = 3,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Find products for multiple trending topics.

        Args:
            topics: List of trending topics
            products_per_topic: Max products per topic
            progress_callback: Progress update function

        Returns:
            List of all products found
        """
        all_products = []
        seen_names = set()

        for i, topic in enumerate(topics):
            if progress_callback:
                progress_callback(i, len(topics), topic)

            print(f"\n  [{i+1}/{len(topics)}] Finding products for: {topic}")

            products = self.find_products_for_topic(topic, products_per_topic)

            # Deduplicate by product name
            for product in products:
                name_lower = product['name'].lower()

                # Check if we've seen this product
                if name_lower not in seen_names:
                    all_products.append(product)
                    seen_names.add(name_lower)
                    print(f"    + {product['name'][:60]}")

        return all_products
