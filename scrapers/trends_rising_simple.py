"""
Simple Google Trends Rising Queries
Uses pytrends to get rising queries for category seed keywords.
Falls back to Playwright browser scraping if pytrends is rate-limited.
"""

from typing import List, Dict, Any
import time

from .rate_limiter import RateLimiter, CircuitBreaker


class TrendsRisingSimple:
    """Get rising queries using pytrends with browser fallback."""

    # Seed keywords for each category
    CATEGORY_SEEDS = {
        "technology": ["smartphone", "laptop", "headphones", "smartwatch", "tablet"],
        "fashion_beauty": ["makeup", "skincare", "fashion", "shoes", "clothing"],
        "hobbies": ["gaming", "photography", "crafts", "art supplies", "hobby"],
        "pets": ["dog food", "cat toys", "pet supplies", "aquarium", "bird cage"],
        "shopping": ["deals", "online shopping", "gift ideas", "home decor", "kitchen gadgets"],
    }

    def __init__(self, delay: float = 25.0, use_browser: bool = False):
        self.delay = delay
        self.use_browser = use_browser
        self.pytrends = None
        self.browser_scraper = None

        if not use_browser:
            self._init_pytrends()

        # Rate limiter for Google Trends (very aggressive limits)
        self.rate_limiter = RateLimiter(
            domain="trends.google.com",
            base_delay=delay,
            max_retries=3,
            jitter=5.0
        )

    def _init_pytrends(self):
        """Initialize pytrends with retry logic."""
        try:
            from pytrends.request import TrendReq
            self.pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 30))
        except ImportError:
            print("pytrends not installed. Run: pip install pytrends")
            self.pytrends = None

    def _init_browser_scraper(self):
        """Initialize browser-based scraper as fallback."""
        if self.browser_scraper is None:
            try:
                from .trends_browser_scraper import TrendsBrowserScraper
                self.browser_scraper = TrendsBrowserScraper(delay=10.0)
                return True
            except Exception as e:
                print(f"  Browser scraper init failed: {e}")
                return False
        return True

    def _use_browser_fallback(self, categories: List[str], max_per_seed: int) -> List[Dict[str, Any]]:
        """Use browser-based scraping when pytrends fails."""
        print("\n  Switching to browser-based scraping (bypasses rate limits)...")

        if not self._init_browser_scraper():
            return []

        return self.browser_scraper.get_rising_topics(
            categories=categories,
            max_per_seed=max_per_seed
        )

    def get_rising_topics(self, categories: List[str] = None, max_per_seed: int = 10) -> List[Dict[str, Any]]:
        """
        Get rising search queries for categories with rate limiting.
        Automatically falls back to browser scraping if pytrends is rate-limited.

        Args:
            categories: List of category names
            max_per_seed: Max rising queries per seed keyword

        Returns:
            List of rising topics
        """
        if categories is None:
            categories = list(self.CATEGORY_SEEDS.keys())

        # If use_browser flag is set, skip pytrends entirely
        if self.use_browser:
            print("  Using browser-based scraping (pytrends bypassed)...")
            return self._use_browser_fallback(categories, max_per_seed)

        # Check if pytrends is available
        if self.pytrends is None:
            print("  pytrends not available, using browser fallback...")
            return self._use_browser_fallback(categories, max_per_seed)

        all_topics = []
        seen = set()
        pytrends_failed = False

        for category in categories:
            if category not in self.CATEGORY_SEEDS:
                continue

            print(f"\n  Exploring {category.replace('_', ' ').title()}...")

            seeds = self.CATEGORY_SEEDS[category]

            for seed in seeds:
                # Check circuit breaker before making request
                if not self.rate_limiter.check_circuit_breaker():
                    print(f"    Circuit breaker OPEN - switching to browser fallback")
                    pytrends_failed = True
                    break

                print(f"    Checking rising queries for '{seed}'...", end=" ")

                try:
                    # Use rate limiter's execute_with_retry for automatic backoff
                    def fetch_rising():
                        self.pytrends.build_payload([seed], cat=0, timeframe='today 1-m', geo='US')
                        return self.pytrends.related_queries()

                    related = self.rate_limiter.execute_with_retry(fetch_rising)

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
                    error_msg = str(e)
                    if "429" in error_msg or "rate" in error_msg.lower():
                        print(f"rate limited - will try browser fallback")
                        self.rate_limiter.track_failure(error_msg)
                        pytrends_failed = True
                    else:
                        print(f"error: {error_msg[:50]}")
                    continue

            # If circuit breaker opened, stop trying pytrends
            if pytrends_failed:
                break

        # Print stats
        stats = self.rate_limiter.get_stats()
        print(f"\n  Rate limiter stats: {stats['successes']} successes, {stats['failures']} failures")

        # If pytrends failed or returned nothing, try browser fallback
        if pytrends_failed or len(all_topics) == 0:
            browser_topics = self._use_browser_fallback(categories, max_per_seed)
            # Merge results, avoiding duplicates
            for topic in browser_topics:
                if topic["title"].lower() not in seen:
                    all_topics.append(topic)
                    seen.add(topic["title"].lower())

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
