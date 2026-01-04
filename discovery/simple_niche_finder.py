"""
Simplified Niche Discovery
No browser automation - uses HTTP requests and search URLs
"""

import re
import requests
from typing import List, Dict, Any
from scrapers.trends_discovery import TrendsDiscovery
from scrapers import RedditScraper
from analysis import SentimentAnalyzer


class SimpleNicheFinder:
    """
    Simplified niche discovery without browser automation.

    Flow:
    1. Get trending searches from Google Trends
    2. For each product, generate Amazon/Shopify search URLs
    3. Extract keywords for Reddit sentiment search
    4. Score opportunities
    """

    def __init__(self):
        self.trends = TrendsDiscovery(delay=2.0)
        self.reddit = RedditScraper(delay=2.0)
        self.sentiment = SentimentAnalyzer()

    def discover_niches(
        self,
        seed_keywords: List[str],
        max_products: int = 30,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Discover product niches.

        Args:
            seed_keywords: Category keywords to explore
            max_products: Max products to analyze
            progress_callback: Progress update function

        Returns:
            List of opportunities with scores
        """
        print("\n" + "=" * 70)
        print("NICHE DISCOVERY - Finding Trending Products")
        print("=" * 70)

        # STEP 1: Get trending product searches
        print("\n[STEP 1] Finding trending product searches from Google Trends...")
        print("-" * 50)

        trending_products = self.trends.discover_trending_products(
            seed_keywords,
            max_per_category=max_products // len(seed_keywords) if seed_keywords else 10
        )

        if not trending_products:
            print("No trending products found")
            return []

        print(f"\nFound {len(trending_products)} trending product searches")

        # STEP 2: Analyze each product
        print("\n[STEP 2] Analyzing products...")
        print("-" * 50)

        results = []

        for i, product_name in enumerate(trending_products[:max_products]):
            if progress_callback:
                progress_callback(i, len(trending_products[:max_products]), product_name)

            print(f"\n  [{i+1}/{min(len(trending_products), max_products)}] {product_name}")

            result = {
                "name": product_name,
                "source": "google_trends"
            }

            # Generate marketplace URLs
            result["amazon_url"] = self._get_amazon_search_url(product_name)
            result["shopify_search_url"] = self._get_shopify_search_url(product_name)

            # Extract keywords for Reddit search
            keywords = self._extract_keywords(product_name)
            result["keywords"] = keywords

            print(f"    Keywords: {', '.join(keywords)}")

            # Reddit sentiment using keywords
            print(f"    Searching Reddit...", end=" ")
            reddit_data = self._get_reddit_sentiment(keywords)
            result.update(reddit_data)

            if reddit_data["reddit_posts"] > 0:
                sent = reddit_data["reddit_sentiment"]
                label = "positive" if sent > 0.05 else "negative" if sent < -0.05 else "neutral"
                print(f"{reddit_data['reddit_posts']} posts, {label} ({sent:.2f})")
            else:
                print("no posts")

            # Simple trend score (it's trending if it showed up)
            result["trend_score"] = 75
            result["trend_direction"] = "rising"

            # Calculate opportunity score
            result["opportunity_score"] = self._calculate_opportunity_score(result)
            print(f"    Opportunity Score: {result['opportunity_score']:.1f}/100")

            results.append(result)

        # Sort by score
        results.sort(key=lambda x: x["opportunity_score"], reverse=True)

        return results

    def _get_amazon_search_url(self, product_name: str) -> str:
        """Generate Amazon search URL."""
        query = product_name.replace(' ', '+')
        return f"https://www.amazon.com/s?k={query}"

    def _get_shopify_search_url(self, product_name: str) -> str:
        """Generate Google search URL for Shopify stores."""
        query = f'site:myshopify.com "{product_name}"'
        return f"https://www.google.com/search?q={query.replace(' ', '+')}"

    def _extract_keywords(self, product_name: str) -> List[str]:
        """
        Extract meaningful keywords from product name.

        Used for Reddit sentiment search.
        """
        # Clean the product name
        clean_name = product_name.lower()

        # Remove common words
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
            'that', 'the', 'to', 'was', 'will', 'with'
        }

        # Split into words
        words = re.findall(r'\w+', clean_name)

        # Filter out stop words and short words
        keywords = [
            word for word in words
            if word not in stop_words and len(word) > 2
        ]

        # Return top 3 most meaningful keywords
        return keywords[:3]

    def _get_reddit_sentiment(self, keywords: List[str]) -> Dict[str, Any]:
        """
        Search Reddit using keywords and analyze sentiment.

        Args:
            keywords: List of keywords to search for

        Returns:
            Dict with Reddit metrics
        """
        # Create search query from keywords
        query = ' '.join(keywords)

        # Search Reddit
        posts = self.reddit.search_all_reddit(query, limit=20)

        if not posts:
            return {
                "reddit_posts": 0,
                "reddit_sentiment": 0,
                "reddit_positive": 0,
                "reddit_negative": 0,
                "sentiment_ratio": 0.5,
            }

        # Analyze sentiment
        sentiments = []
        for post in posts:
            text = f"{post.get('title', '')} {post.get('content', '')}"
            label, score = self.sentiment.get_sentiment_label(text)
            sentiments.append({
                "label": label,
                "score": score,
                "upvotes": post.get("upvotes", 0),
            })

        # Weighted sentiment
        total_weight = sum(max(s["upvotes"], 1) for s in sentiments)
        weighted_sentiment = sum(
            s["score"] * max(s["upvotes"], 1) for s in sentiments
        ) / total_weight if total_weight > 0 else 0

        positive_count = sum(1 for s in sentiments if s["label"] == "positive")
        negative_count = sum(1 for s in sentiments if s["label"] == "negative")

        return {
            "reddit_posts": len(posts),
            "reddit_sentiment": round(weighted_sentiment, 3),
            "reddit_positive": positive_count,
            "reddit_negative": negative_count,
            "sentiment_ratio": round(
                positive_count / max(positive_count + negative_count, 1), 2
            ),
        }

    def _calculate_opportunity_score(self, product: Dict[str, Any]) -> float:
        """
        Calculate opportunity score (0-100).

        Since we can't check competition automatically, we focus on:
        - It's trending (base 50 pts)
        - Reddit sentiment (0-50 pts)
        """
        # Base score for being trending
        base_score = 50

        # Reddit sentiment component (0-50 pts)
        sentiment = product.get("reddit_sentiment", 0)
        posts = product.get("reddit_posts", 0)

        # Sentiment contribution (0-40 pts)
        sentiment_component = ((sentiment + 1) / 2) * 40

        # Discussion volume bonus (0-10 pts)
        import math
        volume_bonus = min(10, math.log10(posts + 1) * 5)

        final_score = base_score + sentiment_component + volume_bonus

        # Bonuses
        if product.get("sentiment_ratio", 0) > 0.7:
            final_score += 10  # Strong positive sentiment

        # Penalties
        if product.get("reddit_negative", 0) > product.get("reddit_positive", 0):
            final_score -= 15  # More negative than positive

        return round(min(100, max(0, final_score)), 1)
