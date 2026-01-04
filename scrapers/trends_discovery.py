"""
Google Trends Discovery - Find trending product searches
"""

from typing import List, Dict, Any
from pytrends.request import TrendReq
import time


class TrendsDiscovery:
    """Discover trending product searches from Google Trends."""

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.pytrends = TrendReq(hl='en-US', tz=360)

    def discover_trending_products(self, categories: List[str], max_per_category: int = 20) -> List[str]:
        """
        Find trending product searches across categories.

        Args:
            categories: Category keywords to explore (e.g., ["kitchen", "fitness"])
            max_per_category: Max trending items per category

        Returns:
            List of trending product search terms
        """
        all_trending = []
        seen = set()

        for category in categories:
            print(f"  Discovering trending in '{category}'...")

            # Get trending searches for this category
            trending = self._get_trending_searches(category)

            # Filter for product-like searches
            for term in trending[:max_per_category]:
                clean_term = term.lower().strip()

                if clean_term in seen:
                    continue

                if self._is_product_search(term):
                    all_trending.append(term)
                    seen.add(clean_term)
                    print(f"    + {term}")

            time.sleep(self.delay)

        return all_trending

    def _get_trending_searches(self, keyword: str) -> List[str]:
        """Get trending/rising searches related to a keyword."""
        try:
            time.sleep(self.delay)

            # Build payload for the base keyword
            self.pytrends.build_payload([keyword], cat=0, timeframe='today 3-m', geo='US')

            # Get related queries
            related = self.pytrends.related_queries()

            trending_terms = []

            if keyword in related:
                # Rising queries (gaining momentum)
                rising_df = related[keyword].get("rising")

                if rising_df is not None and not rising_df.empty:
                    # Get the query column
                    queries = rising_df['query'].tolist()
                    trending_terms.extend(queries)

                # Also get top queries
                top_df = related[keyword].get("top")
                if top_df is not None and not top_df.empty:
                    top_queries = top_df['query'].tolist()
                    # Add top queries that aren't in rising
                    for q in top_queries:
                        if q not in trending_terms:
                            trending_terms.append(q)

            return trending_terms

        except Exception as e:
            print(f"    Error getting trends for '{keyword}': {e}")
            return []

    def _is_product_search(self, query: str) -> bool:
        """
        Determine if a search query is likely a product search.

        Filters out:
        - Questions (how to, what is, why)
        - Informational searches
        - Store/location searches
        """
        query_lower = query.lower()

        # Skip informational queries
        skip_phrases = [
            "how to", "what is", "what are", "why", "when", "where",
            "tutorial", "guide", "tips", "best way to", "diy",
            "vs", "versus", "comparison", "vs.", "or",
            "near me", "store", "buy online", "shop",
            "recipe", "ideas", "meaning", "definition"
        ]

        for phrase in skip_phrases:
            if phrase in query_lower:
                return False

        # Must be reasonable length (not too short, not too long)
        words = query.split()
        if len(words) < 2 or len(words) > 6:
            return False

        # Skip if it's just a brand or company name (usually 1 word)
        if len(words) == 1:
            return False

        return True

    def get_trending_now(self, geo: str = 'US') -> List[str]:
        """
        Get currently trending searches in a region.

        Args:
            geo: Country code (US, UK, etc.)

        Returns:
            List of trending search terms
        """
        try:
            # Get trending searches
            trending_df = self.pytrends.trending_searches(pn=geo.lower())

            if trending_df is not None and not trending_df.empty:
                # Filter for product searches
                all_terms = trending_df[0].tolist()
                product_terms = [
                    term for term in all_terms
                    if self._is_product_search(term)
                ]
                return product_terms[:20]  # Top 20

            return []

        except Exception as e:
            print(f"Error getting trending searches: {e}")
            return []
