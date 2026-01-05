"""
Simple Google Trends Rising Queries
Uses pytrends to get rising queries for category seed keywords
"""

from typing import List, Dict, Any
from pytrends.request import TrendReq
import time


class TrendsRisingSimple:
    """Get rising queries using pytrends (reliable method)."""

    # Seed keywords for each category
    CATEGORY_SEEDS = {
        "technology": ["smartphone", "laptop", "headphones", "smartwatch", "tablet"],
        "fashion_beauty": ["makeup", "skincare", "fashion", "shoes", "clothing"],
        "hobbies": ["gaming", "photography", "crafts", "art supplies", "hobby"],
        "pets": ["dog food", "cat toys", "pet supplies", "aquarium", "bird cage"],
        "shopping": ["deals", "online shopping", "gift ideas", "home decor", "kitchen gadgets"],
    }

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))

    def get_rising_topics(self, categories: List[str] = None, max_per_seed: int = 10) -> List[Dict[str, Any]]:
        """
        Get rising search queries for categories.

        Args:
            categories: List of category names
            max_per_seed: Max rising queries per seed keyword

        Returns:
            List of rising topics
        """
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
                print(f"    Checking rising queries for '{seed}'...", end=" ")

                try:
                    time.sleep(self.delay)

                    # Build payload
                    self.pytrends.build_payload([seed], cat=0, timeframe='today 1-m', geo='US')

                    # Get related rising queries
                    related = self.pytrends.related_queries()

                    if seed in related:
                        rising_df = related[seed].get("rising")

                        if rising_df is not None and not rising_df.empty:
                            queries = rising_df['query'].tolist()[:max_per_seed]

                            count = 0
                            for query in queries:
                                query_lower = query.lower()

                                # Skip duplicates
                                if query_lower in seen:
                                    continue

                                # Filter for product-like queries
                                if self._is_product_query(query):
                                    all_topics.append({
                                        "title": query,
                                        "category": category,
                                        "seed_keyword": seed,
                                        "search_volume": "rising"
                                    })
                                    seen.add(query_lower)
                                    count += 1

                            print(f"found {count} rising queries")
                        else:
                            print("no rising data")
                    else:
                        print("no data")

                except Exception as e:
                    print(f"error: {str(e)[:50]}")
                    continue

        return all_topics

    def _is_product_query(self, query: str) -> bool:
        """Check if query looks like a product search."""
        query_lower = query.lower()

        # Skip informational queries
        skip_words = [
            "how to", "what is", "what are", "why", "when", "where",
            "tutorial", "guide", "tips", "best way", "diy",
            "near me", "store", "open", "hours",
            "recipe", "meaning", "definition", "wikipedia"
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
        if len(words) < 2 or len(words) > 6:
            return False

        return True
