"""
Async Reddit Scraper with Product-Specific Search

Wraps the existing RedditScraper with async interface for parallel execution.
Key change: Searches for FULL PRODUCT NAMES, not extracted keywords.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional

from .reddit_scraper import RedditScraper
from analysis import SentimentAnalyzer


class AsyncRedditScraper:
    """
    Async wrapper for Reddit scraping with product-specific search.

    Key improvement: Searches Reddit using full product names
    (e.g., "Ninja AF101 Air Fryer") instead of extracted keywords
    (e.g., "ninja air fryer").

    Usage:
        scraper = AsyncRedditScraper(delay=10.0)
        sentiment = await scraper.search_product_sentiment("Ninja AF101 Air Fryer")
    """

    def __init__(self, delay: float = 10.0, min_delay: float = 5.0):
        """
        Initialize async Reddit scraper.

        Args:
            delay: Seconds between requests (default 10)
            min_delay: Minimum delay floor (default 5)
        """
        # Sync scraper with no internal delay (we handle it async)
        self.sync_scraper = RedditScraper(delay=0)
        self.sentiment_analyzer = SentimentAnalyzer()

        self.delay = delay
        self.min_delay = min_delay
        self.lock = asyncio.Lock()
        self.last_request_time = 0

        # Stats
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0

    async def search_product_sentiment(
        self,
        product_name: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search Reddit for a SPECIFIC PRODUCT and analyze sentiment.

        This is the key change: searches full product name, not keywords.

        Args:
            product_name: Full product name (e.g., "Ninja AF101 Air Fryer")
            limit: Max posts to analyze

        Returns:
            Dict with sentiment data:
            - reddit_posts: int
            - reddit_sentiment: float (-1 to 1)
            - reddit_positive: int
            - reddit_negative: int
            - sentiment_ratio: float (0 to 1)
        """
        # Apply async rate limiting
        await self._async_delay()

        try:
            # Search using FULL product name (key change)
            posts = await asyncio.to_thread(
                self.sync_scraper.search_all_reddit,
                product_name,
                limit
            )

            # Fallback: if too few results, try brand + category
            if len(posts) < 3:
                fallback_query = self._extract_brand_category(product_name)
                if fallback_query != product_name:
                    await self._async_delay()
                    fallback_posts = await asyncio.to_thread(
                        self.sync_scraper.search_all_reddit,
                        fallback_query,
                        limit
                    )
                    posts.extend(fallback_posts)

            self.success_count += 1
            return self._analyze_sentiment(posts, product_name)

        except Exception as e:
            self.error_count += 1
            print(f"    Reddit search failed for '{product_name[:30]}': {str(e)[:50]}")
            return self._empty_sentiment_result()

    async def search_multiple_products(
        self,
        product_names: List[str],
        limit_per_product: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search Reddit for multiple products (sequentially with rate limiting).

        For parallel execution, use AsyncWorkerPool instead.

        Args:
            product_names: List of product names
            limit_per_product: Posts per product

        Returns:
            List of sentiment dicts
        """
        results = []
        for name in product_names:
            sentiment = await self.search_product_sentiment(name, limit_per_product)
            results.append({"product_name": name, **sentiment})
        return results

    def _extract_brand_category(self, product_name: str) -> str:
        """
        Extract brand + category for fallback search.

        "Ninja AF101 Air Fryer 4 Quart" -> "Ninja Air Fryer"
        "COSORI Pro II Air Fryer" -> "COSORI Air Fryer"
        """
        import re

        # Common brands to detect
        brands = [
            "Ninja", "COSORI", "Instant Pot", "Cuisinart", "KitchenAid",
            "Dyson", "Shark", "Bissell", "iRobot", "Roomba",
            "Apple", "Samsung", "Sony", "Bose", "JBL",
            "Nike", "Adidas", "Under Armour", "Lululemon",
            "Anker", "Logitech", "Razer", "SteelSeries",
            "Philips", "Braun", "Oral-B", "Waterpik",
            "Lodge", "Le Creuset", "Staub", "All-Clad",
            "Theragun", "Hyperice", "Fitbit", "Garmin", "Whoop",
        ]

        # Common product categories
        categories = [
            "air fryer", "blender", "mixer", "toaster", "coffee maker",
            "vacuum", "robot vacuum", "mop", "steam cleaner",
            "headphones", "earbuds", "speaker", "soundbar",
            "watch", "fitness tracker", "scale",
            "keyboard", "mouse", "monitor", "webcam",
            "pan", "pot", "skillet", "dutch oven",
            "massage gun", "foam roller", "yoga mat",
            "shoes", "sneakers", "running shoes",
        ]

        name_lower = product_name.lower()

        # Find brand
        detected_brand = None
        for brand in brands:
            if brand.lower() in name_lower:
                detected_brand = brand
                break

        # Find category
        detected_category = None
        for category in categories:
            if category in name_lower:
                detected_category = category
                break

        # Build fallback query
        if detected_brand and detected_category:
            return f"{detected_brand} {detected_category}"
        elif detected_brand:
            # Remove model numbers, keep brand + main words
            clean = re.sub(r'[A-Z]{1,3}\d+[A-Z]?\d*', '', product_name)
            clean = re.sub(r'\d+\s*(oz|ml|qt|quart|inch|pack|count|lb|kg|piece|set)\b', '', clean, flags=re.IGNORECASE)
            words = clean.split()[:4]
            return ' '.join(words).strip()
        else:
            return product_name

    def _analyze_sentiment(
        self,
        posts: List[Dict[str, Any]],
        product_name: str
    ) -> Dict[str, Any]:
        """
        Analyze sentiment from Reddit posts using VADER.

        Weights sentiment by upvotes (popular posts matter more).
        """
        if not posts:
            return self._empty_sentiment_result()

        sentiments = []
        for post in posts:
            text = f"{post.get('title', '')} {post.get('content', '')}"
            if not text.strip():
                continue

            label, score = self.sentiment_analyzer.get_sentiment_label(text)
            sentiments.append({
                "label": label,
                "score": score,
                "upvotes": max(post.get("upvotes", 0), 1),
            })

        if not sentiments:
            return self._empty_sentiment_result()

        # Weighted sentiment by upvotes
        total_weight = sum(s["upvotes"] for s in sentiments)
        weighted_sentiment = sum(
            s["score"] * s["upvotes"] for s in sentiments
        ) / total_weight if total_weight > 0 else 0

        positive_count = sum(1 for s in sentiments if s["label"] == "positive")
        negative_count = sum(1 for s in sentiments if s["label"] == "negative")
        neutral_count = sum(1 for s in sentiments if s["label"] == "neutral")

        return {
            "reddit_posts": len(posts),
            "reddit_sentiment": round(weighted_sentiment, 3),
            "reddit_positive": positive_count,
            "reddit_negative": negative_count,
            "reddit_neutral": neutral_count,
            "sentiment_ratio": round(
                positive_count / max(positive_count + negative_count, 1), 2
            ),
        }

    def _empty_sentiment_result(self) -> Dict[str, Any]:
        """Return empty sentiment result for failed searches."""
        return {
            "reddit_posts": 0,
            "reddit_sentiment": 0,
            "reddit_positive": 0,
            "reddit_negative": 0,
            "reddit_neutral": 0,
            "sentiment_ratio": 0.5,
        }

    async def _async_delay(self):
        """Apply async-compatible rate limiting."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time

            if self.last_request_time > 0 and elapsed < self.delay:
                wait_time = max(self.min_delay, self.delay - elapsed)
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()
            self.request_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get scraper statistics."""
        return {
            "requests": self.request_count,
            "successes": self.success_count,
            "errors": self.error_count,
            "success_rate": self.success_count / max(self.request_count, 1),
        }
