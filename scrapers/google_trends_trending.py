"""
Google Trends Trending Now Scraper
Gets actually trending topics from Google Trends (past 7 days)
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import time


class GoogleTrendsTrending:
    """Scrape Google Trends trending topics."""

    CATEGORIES = {
        "fashion_beauty": 2,
        "hobbies": 8,
        "pets": 13,
        "shopping": 16,
        "technology": 18,
    }

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.base_url = "https://trends.google.com/trending"

    def get_trending_topics(self, categories: List[str] = None, hours: int = 168) -> List[Dict[str, Any]]:
        """
        Get trending topics from Google Trends.

        Args:
            categories: List of category names (e.g., ["fashion_beauty", "technology"])
            hours: Time window in hours (168 = 7 days)

        Returns:
            List of trending topics with metadata
        """
        if categories is None:
            categories = list(self.CATEGORIES.keys())

        all_topics = []

        for category_name in categories:
            if category_name not in self.CATEGORIES:
                print(f"Unknown category: {category_name}")
                continue

            category_id = self.CATEGORIES[category_name]

            print(f"  Fetching trending topics from {category_name.replace('_', ' ').title()}...")

            topics = self._scrape_category(category_id, hours)

            for topic in topics:
                topic['category'] = category_name
                all_topics.append(topic)
                print(f"    + {topic['title']}")

            time.sleep(self.delay)

        return all_topics

    def _scrape_category(self, category_id: int, hours: int) -> List[Dict[str, Any]]:
        """
        Scrape trending topics from a specific category.

        Args:
            category_id: Google Trends category ID
            hours: Time window

        Returns:
            List of trending topics
        """
        try:
            url = f"{self.base_url}?geo=US&hl=en-US&sort=search-volume&hours={hours}"
            if category_id:
                url += f"&category={category_id}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            # Parse JSON data from the page
            # Google Trends embeds data in script tags
            import json
            import re

            # Look for the trending data in the page
            # It's usually in a script tag with window.data or similar
            soup = BeautifulSoup(response.text, 'html.parser')

            topics = []

            # Try to find script tag with trending data
            scripts = soup.find_all('script')

            for script in scripts:
                if script.string and 'trending' in script.string.lower():
                    # Extract JSON data
                    try:
                        # Look for patterns like ["Title", "12345", ...]
                        matches = re.findall(r'\["([^"]+)",\s*"(\d+)"', script.string)

                        for title, volume in matches[:20]:  # Top 20
                            # Filter out non-product looking terms
                            if self._looks_like_product_topic(title):
                                topics.append({
                                    "title": title,
                                    "search_volume": volume,
                                })

                    except Exception as e:
                        continue

            # Fallback: If we can't parse JSON, try RSS feed
            if not topics:
                topics = self._try_rss_feed(category_id, hours)

            return topics[:20]  # Top 20

        except Exception as e:
            print(f"    Error scraping category {category_id}: {e}")
            return []

    def _try_rss_feed(self, category_id: int, hours: int) -> List[Dict[str, Any]]:
        """Try getting trending topics from RSS feed."""
        try:
            rss_url = f"{self.base_url}/rss?geo=US"
            if category_id:
                rss_url += f"&cat={category_id}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(rss_url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item')

            topics = []

            for item in items[:20]:
                title_tag = item.find('title')
                if title_tag:
                    title = title_tag.text.strip()

                    if self._looks_like_product_topic(title):
                        topics.append({
                            "title": title,
                            "search_volume": "unknown",
                        })

            return topics

        except Exception as e:
            print(f"    RSS feed error: {e}")
            return []

    def _looks_like_product_topic(self, title: str) -> bool:
        """
        Check if a trending topic looks like it could be related to products.

        Filters out:
        - News/politics
        - People/celebrities (unless product related)
        - Events
        """
        title_lower = title.lower()

        # Skip obvious non-product topics
        skip_words = [
            "election", "vote", "president", "senator", "congress",
            "died", "death", "killed", "arrested", "trial", "lawsuit",
            "hurricane", "earthquake", "fire", "flood",
            "game score", "vs", "football", "basketball", "baseball",
            "news", "breaking"
        ]

        for word in skip_words:
            if word in title_lower:
                return False

        # Keep product-related terms
        product_words = [
            "phone", "iphone", "ipad", "laptop", "computer", "watch",
            "headphones", "earbuds", "speaker", "camera",
            "shoes", "clothing", "fashion", "beauty", "makeup",
            "toy", "game", "console", "ps5", "xbox",
            "gadget", "device", "tech", "app",
            "wireless", "bluetooth", "usb", "charger",
            "case", "cover", "accessories",
            "pet", "dog", "cat", "food"
        ]

        for word in product_words:
            if word in title_lower:
                return True

        # If it's short and looks like a product name, keep it
        words = title.split()
        if len(words) <= 4:
            return True

        return False


# Fallback: Use pytrends for trending searches
def get_trending_fallback() -> List[Dict[str, Any]]:
    """Fallback method using pytrends."""
    try:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl='en-US', tz=360)

        # Get trending searches
        trending_df = pytrends.trending_searches(pn='united_states')

        if trending_df is not None and not trending_df.empty:
            topics = []

            for term in trending_df[0].tolist()[:30]:
                topics.append({
                    "title": term,
                    "search_volume": "trending",
                    "category": "general"
                })

            return topics

        return []

    except Exception as e:
        print(f"Fallback error: {e}")
        return []
