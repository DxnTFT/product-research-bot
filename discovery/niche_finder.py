"""
Hidden Niche Discovery Engine
Finds rising products with low competition and positive sentiment
"""

import math
from typing import List, Dict, Any
from scrapers import TrendsScraper, RedditScraper
from scrapers.shopify_scraper import ShopifyScraper
from scrapers.competition_checker import check_amazon_competition
from analysis import SentimentAnalyzer


class NicheFinder:
    """
    Discovers hidden product opportunities by finding:
    - Rising search interest (Google Trends)
    - Low competition (Amazon + Shopify)
    - Positive sentiment (Reddit)
    """

    def __init__(self):
        self.trends = TrendsScraper(delay=2.0)
        self.shopify = ShopifyScraper(delay=2.0)
        self.reddit = RedditScraper(delay=2.0)
        self.sentiment = SentimentAnalyzer()

    def discover_niches(
        self,
        seed_keywords: List[str],
        max_products: int = 50,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Discover hidden product niches.

        Args:
            seed_keywords: Starting categories/keywords (e.g., ["kitchen", "fitness"])
            max_products: Maximum products to analyze
            progress_callback: Optional callback for progress updates

        Returns:
            List of product opportunities sorted by score
        """
        print("\n" + "=" * 70)
        print("NICHE DISCOVERY - Finding Hidden Opportunities")
        print("=" * 70)

        # STEP 1: Find rising products from Google Trends
        print("\n[STEP 1] Finding rising products from Google Trends...")
        print("-" * 50)

        rising_products = self._discover_rising_products(seed_keywords, max_products)

        if not rising_products:
            print("No rising products found. Try different seed keywords.")
            return []

        print(f"Found {len(rising_products)} rising products to analyze")

        # STEP 2: Analyze each product
        print("\n[STEP 2] Analyzing competition and sentiment...")
        print("-" * 50)

        analyzed_products = []

        for i, product_name in enumerate(rising_products):
            if progress_callback:
                progress_callback(i, len(rising_products), product_name)

            print(f"\n  [{i+1}/{len(rising_products)}] {product_name[:50]}")

            result = {
                "name": product_name,
                "source": "google_trends_rising"
            }

            # 2a. Google Trends validation
            print(f"    → Trends...", end=" ")
            trend_data = self.trends.check_trend(product_name)
            result["trend_score"] = trend_data.get("trend_score", 50)
            result["trend_direction"] = trend_data.get("trend_direction", "unknown")
            result["recent_interest"] = trend_data.get("recent_interest", 0)
            print(f"{result['trend_direction']} ({result['trend_score']})")

            # 2b. Amazon competition
            print(f"    → Amazon...", end=" ")
            amazon_data = check_amazon_competition(product_name)
            result.update(amazon_data)
            print(f"{amazon_data.get('amazon_saturation', 'unknown')} (score: {amazon_data.get('amazon_score', 0)})")

            # 2c. Shopify competition
            print(f"    → Shopify...", end=" ")
            shopify_data = self.shopify.check_competition(product_name)
            result.update(shopify_data)
            print(f"{shopify_data.get('shopify_saturation', 'unknown')} ({shopify_data.get('shopify_stores', 0)} stores)")

            # 2d. Reddit sentiment
            print(f"    → Reddit...", end=" ")
            reddit_data = self._get_reddit_sentiment(product_name)
            result.update(reddit_data)

            if reddit_data["reddit_posts"] > 0:
                sent = reddit_data["reddit_sentiment"]
                label = "positive" if sent > 0.05 else "negative" if sent < -0.05 else "neutral"
                print(f"{reddit_data['reddit_posts']} posts, {label} ({sent:.2f})")
            else:
                print("no posts found")

            # Calculate opportunity score
            result["opportunity_score"] = self._calculate_opportunity_score(result)
            print(f"    ✓ Opportunity Score: {result['opportunity_score']:.1f}/100")

            analyzed_products.append(result)

        # STEP 3: Sort and return top opportunities
        print("\n[STEP 3] Ranking opportunities...")
        print("-" * 50)

        # Sort by opportunity score
        analyzed_products.sort(key=lambda x: x["opportunity_score"], reverse=True)

        return analyzed_products

    def _discover_rising_products(self, seed_keywords: List[str], max_products: int) -> List[str]:
        """
        Discover rising products from Google Trends.

        Args:
            seed_keywords: Categories to explore
            max_products: Max products to return

        Returns:
            List of product names
        """
        all_rising = []
        seen = set()

        for keyword in seed_keywords:
            print(f"  Exploring '{keyword}'...", end=" ")

            related = self.trends.get_related_queries(keyword)

            # Get rising queries (products gaining momentum)
            rising_queries = related.get("rising", [])

            if rising_queries:
                # Filter for product-like queries (not just informational)
                for item in rising_queries:
                    query = item.get("query", "")

                    # Skip if already seen
                    if query.lower() in seen:
                        continue

                    # Skip informational queries
                    if self._is_product_query(query):
                        all_rising.append(query)
                        seen.add(query.lower())

                print(f"found {len(rising_queries)} rising queries")
            else:
                print("no rising data")

            # Stop if we have enough
            if len(all_rising) >= max_products:
                break

        return all_rising[:max_products]

    def _is_product_query(self, query: str) -> bool:
        """
        Check if query looks like a product search (not informational).

        Args:
            query: Search query

        Returns:
            True if likely a product query
        """
        query_lower = query.lower()

        # Skip informational queries
        skip_words = [
            "how to", "what is", "why", "when", "where",
            "tutorial", "guide", "tips", "best way",
            "vs", "versus", "comparison", "review",
            "near me", "store", "buy online"
        ]

        for skip in skip_words:
            if skip in query_lower:
                return False

        # Must have some length
        if len(query.split()) > 8:  # Too long, probably not a product
            return False

        return True

    def _get_reddit_sentiment(self, product_name: str) -> Dict[str, Any]:
        """Get Reddit sentiment for a product."""
        # Search Reddit
        posts = self.reddit.search_all_reddit(product_name, limit=20)

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

        # Weighted sentiment (upvotes matter)
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

        Factors:
        - Rising trend (25 pts)
        - Low Amazon competition (25 pts)
        - Low Shopify competition (25 pts)
        - Positive sentiment (25 pts)
        """

        # 1. Trend component (0-25 pts)
        # Rising = higher score
        trend_score = product.get("trend_score", 50)
        if product.get("trend_direction") == "rising":
            trend_component = (trend_score / 100) * 25
        else:
            trend_component = (trend_score / 100) * 15  # Penalize non-rising

        # 2. Amazon competition (0-25 pts)
        # Lower competition = higher score
        amazon_score = product.get("amazon_score", 50)
        amazon_component = (amazon_score / 100) * 25

        # 3. Shopify competition (0-25 pts)
        # Fewer stores = higher score
        shopify_score = product.get("shopify_score", 50)
        shopify_component = (shopify_score / 100) * 25

        # 4. Reddit sentiment (0-25 pts)
        sentiment = product.get("reddit_sentiment", 0)
        posts = product.get("reddit_posts", 0)

        # Convert sentiment -1 to 1 → 0 to 25
        sentiment_component = ((sentiment + 1) / 2) * 20

        # Bonus for discussion volume
        volume_bonus = min(5, math.log10(posts + 1) * 2.5)

        sentiment_total = sentiment_component + volume_bonus

        # Final score
        final_score = (
            trend_component +
            amazon_component +
            shopify_component +
            sentiment_total
        )

        # Bonuses
        if product.get("sentiment_ratio", 0) > 0.7:
            final_score += 5  # Strong positive ratio

        # Penalties
        if product.get("reddit_negative", 0) > product.get("reddit_positive", 0):
            final_score -= 10  # More negative than positive

        if product.get("amazon_saturation") == "very_high":
            final_score -= 5  # Very saturated on Amazon

        if product.get("shopify_saturation") == "very_high":
            final_score -= 5  # Very saturated on Shopify

        return round(min(100, max(0, final_score)), 1)
