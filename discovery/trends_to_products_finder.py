"""
Trends to Products Discovery
1. Get trending topics from Google Trends (past 7 days)
2. Find actual products on Amazon related to those topics
3. Validate sentiment on Reddit for those specific products
"""

import re
from typing import List, Dict, Any
from scrapers.google_trends_trending import GoogleTrendsTrending, get_trending_fallback
from scrapers.amazon_product_finder import AmazonProductFinder
from scrapers import RedditScraper
from analysis import SentimentAnalyzer


class TrendsToProductsFinder:
    """
    Find product opportunities from trending topics.

    Flow:
    1. Google Trends → Get trending topics (e.g., "iPhone 16")
    2. Amazon → Find products related to that topic (e.g., "MagSafe charger")
    3. Reddit → Validate sentiment on specific products
    4. Score and rank
    """

    def __init__(self):
        self.trends = GoogleTrendsTrending(delay=2.0)
        self.amazon = AmazonProductFinder(delay=2.0)
        self.reddit = RedditScraper(delay=2.0)
        self.sentiment = SentimentAnalyzer()

    def discover_opportunities(
        self,
        categories: List[str] = None,
        max_products: int = 30,
        products_per_topic: int = 3,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Discover product opportunities from trending topics.

        Args:
            categories: Google Trends categories (e.g., ["technology", "fashion_beauty"])
            max_products: Max products to return
            products_per_topic: Products to find per trending topic
            progress_callback: Progress update function

        Returns:
            List of product opportunities
        """
        print("\n" + "=" * 70)
        print("TRENDS TO PRODUCTS DISCOVERY")
        print("=" * 70)

        # STEP 1: Get trending topics from Google Trends
        print("\n[STEP 1] Getting trending topics from Google Trends...")
        print("-" * 50)

        trending_topics = self.trends.get_trending_topics(categories=categories, hours=168)

        # Fallback if scraping fails
        if not trending_topics:
            print("  Scraping failed, using fallback method...")
            trending_topics = get_trending_fallback()

        if not trending_topics:
            print("  No trending topics found")
            return []

        print(f"\nFound {len(trending_topics)} trending topics")

        # STEP 2: Find products on Amazon related to those topics
        print("\n[STEP 2] Finding products on Amazon...")
        print("-" * 50)

        topic_names = [t['title'] for t in trending_topics[:15]]  # Top 15 topics

        products = self.amazon.find_products_batch(
            topics=topic_names,
            products_per_topic=products_per_topic
        )

        if not products:
            print("  No products found")
            return []

        print(f"\nFound {len(products)} products")

        # STEP 3: Analyze Reddit sentiment for each product
        print("\n[STEP 3] Analyzing Reddit sentiment...")
        print("-" * 50)

        results = []

        for i, product in enumerate(products[:max_products]):
            if progress_callback:
                progress_callback(i, min(len(products), max_products), product['name'])

            print(f"\n  [{i+1}/{min(len(products), max_products)}] {product['name'][:60]}")

            # Extract keywords for Reddit search
            keywords = self._extract_keywords(product['name'])
            print(f"    Keywords: {', '.join(keywords)}")

            # Reddit sentiment
            print(f"    Searching Reddit...", end=" ")
            reddit_data = self._get_reddit_sentiment(keywords, product['name'])

            if reddit_data["reddit_posts"] > 0:
                sent = reddit_data["reddit_sentiment"]
                label = "positive" if sent > 0.05 else "negative" if sent < -0.05 else "neutral"
                print(f"{reddit_data['reddit_posts']} posts, {label} ({sent:.2f})")
            else:
                print("no posts")

            # Build result
            result = {
                "name": product['name'],
                "related_topic": product.get('related_topic', ''),
                "amazon_url": product.get('url', ''),
                "price": product.get('price', 'N/A'),
                "amazon_rating": product.get('rating', 0),
                "amazon_reviews": product.get('reviews', 0),
                "shopify_search_url": self._get_shopify_search_url(product['name']),
                "keywords": keywords,
            }

            result.update(reddit_data)

            # Trend data (it's trending because it came from Trends)
            result["trend_score"] = 80
            result["trend_direction"] = "rising"

            # Calculate opportunity score
            result["opportunity_score"] = self._calculate_opportunity_score(result)
            print(f"    Opportunity Score: {result['opportunity_score']:.1f}/100")

            results.append(result)

        # Sort by score
        results.sort(key=lambda x: x["opportunity_score"], reverse=True)

        return results

    def _extract_keywords(self, product_name: str) -> List[str]:
        """Extract meaningful keywords from product name."""
        # Clean the product name
        clean_name = product_name.lower()

        # Remove brand names, sizes, colors, etc.
        clean_name = re.sub(r'\d+\s*(oz|ml|inch|pack|count|lb|kg|piece|set|mm|cm|ft)\b', '', clean_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'\([^)]*\)', '', clean_name)  # Remove parentheses
        clean_name = re.sub(r'\[[^\]]*\]', '', clean_name)  # Remove brackets

        # Stop words
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
            'that', 'the', 'to', 'was', 'will', 'with', 'pack', 'set',
            'new', 'best', 'top', 'premium', 'professional'
        }

        # Split and filter
        words = re.findall(r'\w+', clean_name)
        keywords = [
            word for word in words
            if word not in stop_words and len(word) > 2
        ]

        # Return top 3 most meaningful
        return keywords[:3]

    def _get_shopify_search_url(self, product_name: str) -> str:
        """Generate Google search URL for Shopify stores."""
        query = f'site:myshopify.com "{product_name}"'
        return f"https://www.google.com/search?q={query.replace(' ', '+')}"

    def _get_reddit_sentiment(self, keywords: List[str], full_name: str) -> Dict[str, Any]:
        """
        Search Reddit using keywords and analyze sentiment.

        Args:
            keywords: Keywords to search for
            full_name: Full product name for fallback

        Returns:
            Reddit sentiment data
        """
        # Try with keywords first
        query = ' '.join(keywords)
        posts = self.reddit.search_all_reddit(query, limit=20)

        # If not enough posts, try with full name
        if len(posts) < 5:
            posts = self.reddit.search_all_reddit(full_name, limit=20)

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

        Factors:
        - Trending topic (base 40 pts)
        - Low Amazon competition (0-30 pts based on reviews)
        - Reddit sentiment (0-30 pts)
        """
        # Base score for being related to a trending topic
        base_score = 40

        # Amazon competition (0-30 pts)
        # Fewer reviews = less saturated = higher score
        reviews = product.get("amazon_reviews", 0)

        if reviews == 0:
            competition_score = 30
        elif reviews < 100:
            competition_score = 25
        elif reviews < 500:
            competition_score = 20
        elif reviews < 2000:
            competition_score = 15
        elif reviews < 5000:
            competition_score = 10
        else:
            competition_score = 5

        # Reddit sentiment (0-30 pts)
        sentiment = product.get("reddit_sentiment", 0)
        posts = product.get("reddit_posts", 0)

        sentiment_component = ((sentiment + 1) / 2) * 25

        # Discussion bonus
        import math
        discussion_bonus = min(5, math.log10(posts + 1) * 2.5)

        final_score = base_score + competition_score + sentiment_component + discussion_bonus

        # Bonuses
        if product.get("sentiment_ratio", 0) > 0.7:
            final_score += 5

        # Penalties
        if product.get("reddit_negative", 0) > product.get("reddit_positive", 0):
            final_score -= 10

        return round(min(100, max(0, final_score)), 1)
