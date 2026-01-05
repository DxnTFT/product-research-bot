"""
Amazon Direct Product Finder
Skip Google Trends entirely - just search Amazon for trending categories
"""

import re
from typing import List, Dict, Any
from scrapers.amazon_product_finder import AmazonProductFinder
from scrapers import RedditScraper
from analysis import SentimentAnalyzer


class AmazonDirectFinder:
    """
    Find products by searching Amazon directly for trending keywords.

    Since Google Trends APIs are unreliable/blocked, use curated trending
    keywords for each category and search Amazon directly.
    """

    # Curated trending keywords for each category
    # Update these monthly based on what's actually trending
    TRENDING_KEYWORDS = {
        "technology": [
            "samsung galaxy s26", "iphone 16 accessories", "wireless earbuds 2026",
            "gaming laptop", "mechanical keyboard", "webcam", "usb c hub",
            "portable monitor", "power bank", "phone gimbal"
        ],
        "fashion_beauty": [
            "oversized hoodie", "platform shoes", "minimalist jewelry",
            "korean skincare", "retinol serum", "makeup primer",
            "hair growth oil", "nail art kit", "lash serum"
        ],
        "hobbies": [
            "resin art kit", "embroidery supplies", "acrylic paint set",
            "photography backdrop", "vinyl cutter", "3d printing pen",
            "bullet journal", "watercolor brushes", "crochet hooks"
        ],
        "pets": [
            "automatic cat feeder", "dog training collar", "cat water fountain",
            "pet camera", "dog puzzle toy", "cat litter mat",
            "dog anxiety vest", "bird toys", "hamster cage"
        ],
        "shopping": [
            "air fryer", "stand mixer", "cordless vacuum", "coffee maker",
            "sous vide", "electric kettle", "rice cooker", "blender",
            "slow cooker", "food processor"
        ],
    }

    def __init__(self):
        self.amazon = AmazonProductFinder(delay=2.0)
        self.reddit = RedditScraper(delay=2.0)
        self.sentiment = SentimentAnalyzer()

    def discover_opportunities(
        self,
        categories: List[str] = None,
        max_products: int = 30,
        products_per_keyword: int = 3,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Discover product opportunities.

        Args:
            categories: Categories to search
            max_products: Max products to return
            products_per_keyword: Products to find per keyword
            progress_callback: Progress update function

        Returns:
            List of product opportunities
        """
        print("\n" + "=" * 70)
        print("PRODUCT DISCOVERY - Amazon Direct Search")
        print("=" * 70)

        if categories is None:
            categories = list(self.TRENDING_KEYWORDS.keys())

        # Get keywords for selected categories
        keywords = []
        for category in categories:
            if category in self.TRENDING_KEYWORDS:
                keywords.extend(self.TRENDING_KEYWORDS[category])

        print(f"\nSearching Amazon for {len(keywords)} trending keywords across {len(categories)} categories")

        # STEP 1: Find products on Amazon
        print("\n[STEP 1] Finding products on Amazon...")
        print("-" * 50)

        products = self.amazon.find_products_batch(
            topics=keywords,
            products_per_topic=products_per_keyword
        )

        if not products:
            print("  No products found")
            return []

        print(f"\nFound {len(products)} products")

        # STEP 2: Analyze Reddit sentiment
        print("\n[STEP 2] Analyzing Reddit sentiment...")
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
                "category": self._get_category_for_topic(product.get('related_topic', ''))
            }

            result.update(reddit_data)

            # Trend data (these are curated trending keywords)
            result["trend_score"] = 75
            result["trend_direction"] = "rising"

            # Calculate opportunity score
            result["opportunity_score"] = self._calculate_opportunity_score(result)
            print(f"    Opportunity Score: {result['opportunity_score']:.1f}/100")

            results.append(result)

        # Sort by score
        results.sort(key=lambda x: x["opportunity_score"], reverse=True)

        return results

    def _get_category_for_topic(self, topic: str) -> str:
        """Get category for a topic."""
        for category, keywords in self.TRENDING_KEYWORDS.items():
            if topic.lower() in [k.lower() for k in keywords]:
                return category
        return "general"

    def _extract_keywords(self, product_name: str) -> List[str]:
        """Extract meaningful keywords from product name."""
        clean_name = product_name.lower()

        # Remove sizes, quantities, etc.
        clean_name = re.sub(r'\d+\s*(oz|ml|inch|pack|count|lb|kg|piece|set|mm|cm|ft)\b', '', clean_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'\([^)]*\)', '', clean_name)
        clean_name = re.sub(r'\[[^\]]*\]', '', clean_name)

        # Stop words
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
            'that', 'the', 'to', 'was', 'will', 'with', 'pack', 'set',
            'new', 'best', 'top', 'premium', 'professional'
        }

        words = re.findall(r'\w+', clean_name)
        keywords = [
            word for word in words
            if word not in stop_words and len(word) > 2
        ]

        return keywords[:3]

    def _get_shopify_search_url(self, product_name: str) -> str:
        """Generate Google search URL for Shopify stores."""
        query = f'site:myshopify.com "{product_name}"'
        return f"https://www.google.com/search?q={query.replace(' ', '+')}"

    def _get_reddit_sentiment(self, keywords: List[str], full_name: str) -> Dict[str, Any]:
        """Search Reddit and analyze sentiment."""
        query = ' '.join(keywords)
        posts = self.reddit.search_all_reddit(query, limit=20)

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

        sentiments = []
        for post in posts:
            text = f"{post.get('title', '')} {post.get('content', '')}"
            label, score = self.sentiment.get_sentiment_label(text)
            sentiments.append({
                "label": label,
                "score": score,
                "upvotes": post.get("upvotes", 0),
            })

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
        """Calculate opportunity score (0-100)."""
        base_score = 40  # Curated trending keyword

        # Amazon competition (fewer reviews = less saturated)
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

        # Reddit sentiment
        sentiment = product.get("reddit_sentiment", 0)
        posts = product.get("reddit_posts", 0)

        sentiment_component = ((sentiment + 1) / 2) * 25

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
