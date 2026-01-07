"""
Trends to Products Discovery
1. Get trending topics from Google Trends (past 7 days)
2. Find actual products on Amazon related to those topics (using Playwright)
3. Validate sentiment on Reddit AND Amazon reviews for those specific products

Updated to use rate-limited components that bypass blocking.
Now includes: accessories, alternatives, and complementary product discovery.

ASYNC VERSION: Parallel Reddit sentiment for 3-4x speedup.
"""

import re
import asyncio
import sys
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from scrapers.trends_rising_simple import TrendsRisingSimple
from scrapers.browser_scraper import BrowserScraper
from scrapers import RedditScraper
from analysis import SentimentAnalyzer
from database import Database

# Async components for parallel processing
from scrapers.async_worker_pool import AsyncWorkerPool
from scrapers.async_reddit_scraper import AsyncRedditScraper
from scrapers.async_browser_scraper import AsyncBrowserScraper


# Niche discovery patterns - what to search for each trending topic
NICHE_PATTERNS = {
    "accessories": [
        "{topic} case",
        "{topic} cover",
        "{topic} charger",
        "{topic} stand",
        "{topic} holder",
        "{topic} strap",
        "{topic} band",
        "{topic} screen protector",
        "{topic} mount",
        "{topic} bag",
    ],
    "alternatives": [
        "{topic} alternative",
        "budget {topic}",
        "cheap {topic}",
        "{topic} dupe",
        "like {topic}",
        "similar to {topic}",
    ],
    "complementary": [
        "{topic} bundle",
        "{topic} kit",
        "{topic} set",
        "{topic} starter",
        "best with {topic}",
        "{topic} compatible",
    ],
}

# Category-specific product suffixes
CATEGORY_NICHES = {
    "technology": {
        "accessories": ["case", "charger", "cable", "adapter", "stand", "dock", "screen protector"],
        "alternatives": ["alternative", "budget", "cheap", "clone"],
        "complementary": ["accessories", "bundle", "kit", "compatible"],
    },
    "fitness": {
        "accessories": ["bag", "mat", "gloves", "straps", "belt", "rack", "storage"],
        "alternatives": ["home", "budget", "beginner", "portable"],
        "complementary": ["workout", "training", "exercise", "gear"],
    },
    "health": {
        "accessories": ["case", "pouch", "organizer", "tracker", "monitor"],
        "alternatives": ["natural", "organic", "generic", "alternative"],
        "complementary": ["supplement", "vitamin", "wellness", "combo"],
    },
    "home": {
        "accessories": ["cover", "organizer", "storage", "replacement", "parts"],
        "alternatives": ["budget", "affordable", "diy", "compact"],
        "complementary": ["set", "bundle", "matching", "combo"],
    },
}


class TrendsToProductsFinder:
    """
    Find product opportunities from trending topics.

    Flow:
    1. Google Trends → Get rising queries for category keywords (with rate limiting)
    2. Amazon → Find products via Playwright browser (bypasses blocking)
    3. Reddit + Amazon Reviews → Validate sentiment from both sources
    4. Score and rank based on competition + sentiment
    """

    def __init__(self):
        # Use rate-limited trends scraper (25s delay between requests)
        self.trends = TrendsRisingSimple(delay=25.0)

        # Use Playwright-based Amazon scraper (bypasses bot detection)
        self.amazon = BrowserScraper(delay=30.0)

        # Reddit scraper
        self.reddit = RedditScraper(delay=2.0)

        self.sentiment = SentimentAnalyzer()
        self.db = Database()

    def _save_to_history(
        self,
        results: List[Dict[str, Any]],
        mode: str,
        categories: List[str],
        settings: dict,
        start_time: datetime
    ) -> int:
        """
        Save discovery results to database for historical tracking.

        Args:
            results: List of product opportunities
            mode: Discovery mode (discover, custom_keywords, etc.)
            categories: Categories used for discovery
            settings: Settings dict (max_products, niche_types, etc.)
            start_time: When the discovery started

        Returns:
            Run ID of the saved discovery run
        """
        try:
            duration = int((datetime.utcnow() - start_time).total_seconds())
            avg_score = sum(r.get('opportunity_score', 0) for r in results) / len(results) if results else 0

            # Create discovery run
            run = self.db.create_discovery_run(
                mode=mode,
                categories=categories,
                settings=settings
            )

            # Save all product snapshots
            saved_count = self.db.bulk_save_snapshots(run.id, results)

            # Complete the run with stats
            self.db.complete_discovery_run(
                run.id,
                products_found=saved_count,
                avg_score=avg_score,
                duration_seconds=duration
            )

            print(f"\n[HISTORY] Saved run #{run.id} with {saved_count} products to database")
            return run.id

        except Exception as e:
            print(f"\n[HISTORY] Warning: Could not save to history: {e}")
            return -1

    def discover_opportunities(
        self,
        categories: List[str] = None,
        max_products: int = 30,
        products_per_topic: int = 3,
        niche_types: List[str] = None,
        include_amazon_sentiment: bool = True,
        min_price: float = 0.0,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Discover product opportunities from trending topics.

        Args:
            categories: Google Trends categories (e.g., ["technology", "fitness"])
            max_products: Max products to return
            products_per_topic: Products to find per trending topic
            niche_types: Types of niches to find ("accessories", "alternatives", "complementary")
            include_amazon_sentiment: Whether to scrape Amazon reviews for sentiment
            min_price: Minimum price filter (default 0 = no filter)
            progress_callback: Callback function(step, total_steps, current_item, message)

        Returns:
            List of product opportunities with sentiment data
        """
        if niche_types is None:
            niche_types = ["accessories", "alternatives", "complementary"]

        # Track start time for history
        start_time = datetime.utcnow()

        def update_progress(step: int, total: int, item: str = "", message: str = ""):
            if progress_callback:
                progress_callback(step, total, item, message)
            print(f"  [{step}/{total}] {message} {item[:50] if item else ''}")

        print("\n" + "=" * 70)
        print("TRENDS TO PRODUCTS DISCOVERY (Enhanced)")
        print(f"Niche types: {', '.join(niche_types)}")
        print("=" * 70)

        # STEP 1: Get rising queries from Google Trends
        print("\n[STEP 1] Getting rising queries from Google Trends...")
        print("-" * 50)

        if progress_callback:
            progress_callback(1, 4, "", "Fetching Google Trends data...")

        rising_topics = self.trends.get_rising_topics(categories=categories, max_per_seed=5)

        if not rising_topics:
            print("  No rising topics found")
            return []

        print(f"\nFound {len(rising_topics)} rising queries:")
        for topic in rising_topics[:5]:
            print(f"  - {topic['title']} ({topic.get('category', 'general')})")

        # STEP 2: Generate niche search keywords
        print("\n[STEP 2] Generating niche product searches...")
        print("-" * 50)

        if progress_callback:
            progress_callback(2, 4, "", "Generating niche keywords...")

        search_keywords = self._generate_niche_keywords(
            rising_topics[:8],  # Top 8 topics to limit API calls
            niche_types=niche_types,
            max_keywords_per_topic=4
        )

        print(f"  Generated {len(search_keywords)} search queries across {len(niche_types)} niche types")

        # STEP 3: Find products on Amazon
        print("\n[STEP 3] Searching Amazon for niche products...")
        if min_price > 0:
            print(f"  (filtering for products >= ${min_price:.0f})")
        print("-" * 50)

        if progress_callback:
            progress_callback(3, 4, "", "Searching Amazon...")

        products = self.amazon.search_products_batch(
            keywords=search_keywords,
            products_per_keyword=products_per_topic,
            min_price=min_price,
            progress_callback=lambda i, t, k: update_progress(i, t, k, "Searching:")
        )

        if not products:
            print("  No products found on Amazon")
            return []

        print(f"\nFound {len(products)} unique products on Amazon")

        # STEP 4: Analyze sentiment (Reddit + Amazon reviews)
        print("\n[STEP 4] Analyzing sentiment (Reddit + Amazon reviews)...")
        print("-" * 50)

        results = []
        total_products = min(len(products), max_products)

        for i, product in enumerate(products[:max_products]):
            if progress_callback:
                progress_callback(i + 1, total_products, product['name'][:40], "Analyzing:")

            print(f"\n  [{i+1}/{total_products}] {product['name'][:60]}")

            # Extract keywords for Reddit search
            keywords = self._extract_keywords(product['name'])

            # Reddit sentiment
            print(f"    Reddit...", end=" ")
            reddit_data = self._get_reddit_sentiment(keywords, product['name'])

            if reddit_data["reddit_posts"] > 0:
                sent = reddit_data["reddit_sentiment"]
                label = "positive" if sent > 0.05 else "negative" if sent < -0.05 else "neutral"
                print(f"{reddit_data['reddit_posts']} posts ({label})")
            else:
                print("no posts")

            # Amazon review sentiment (optional, adds time)
            amazon_sentiment_data = {}
            if include_amazon_sentiment and product.get('asin'):
                print(f"    Amazon reviews...", end=" ")
                amazon_sentiment_data = self.amazon.get_product_sentiment(
                    product['asin'],
                    self.sentiment,
                    max_reviews=10
                )
                if amazon_sentiment_data["amazon_reviews_analyzed"] > 0:
                    sent = amazon_sentiment_data["amazon_sentiment"]
                    label = "positive" if sent > 0.05 else "negative" if sent < -0.05 else "neutral"
                    print(f"{amazon_sentiment_data['amazon_reviews_analyzed']} reviews ({label})")
                else:
                    print("no reviews")

            # Build result
            result = {
                "name": product['name'],
                "niche_type": self._detect_niche_type(product.get('search_keyword', '')),
                "related_topic": product.get('search_keyword', ''),
                "amazon_url": product.get('url', ''),
                "amazon_asin": product.get('asin', ''),
                "price": product.get('price', 'N/A'),
                "amazon_rating": product.get('rating', 0),
                "amazon_review_count": product.get('reviews', 0),
                "shopify_search_url": self._get_shopify_search_url(product['name']),
                "keywords": keywords,
            }

            # Add Reddit data
            result.update(reddit_data)

            # Add Amazon sentiment data
            result.update(amazon_sentiment_data)

            # Combined sentiment score (average of both if available)
            result["combined_sentiment"] = self._calculate_combined_sentiment(
                reddit_data, amazon_sentiment_data
            )

            # Trend data
            result["trend_score"] = 80
            result["trend_direction"] = "rising"

            # Calculate opportunity score
            result["opportunity_score"] = self._calculate_opportunity_score(result)
            print(f"    Score: {result['opportunity_score']:.1f}/100")

            results.append(result)

        # Sort by score
        results.sort(key=lambda x: x["opportunity_score"], reverse=True)

        print("\n" + "=" * 70)
        print(f"Discovery complete! Found {len(results)} opportunities")
        print("=" * 70)

        # Save to history database
        self._save_to_history(
            results=results,
            mode="discover",
            categories=categories or [],
            settings={
                "max_products": max_products,
                "niche_types": niche_types,
                "include_amazon_sentiment": include_amazon_sentiment,
                "min_price": min_price
            },
            start_time=start_time
        )

        return results

    def _generate_niche_keywords(
        self,
        topics: List[Dict],
        niche_types: List[str],
        max_keywords_per_topic: int = 4
    ) -> List[str]:
        """
        Generate search keywords for finding niche products.

        Args:
            topics: List of trending topics
            niche_types: Types of niches to search for
            max_keywords_per_topic: Max keywords per topic

        Returns:
            List of search keywords
        """
        keywords = []

        for topic in topics:
            topic_name = topic['title']
            topic_category = topic.get('category', 'general').lower()

            for niche_type in niche_types:
                # Get patterns for this niche type
                patterns = NICHE_PATTERNS.get(niche_type, [])

                # Also get category-specific suffixes if available
                category_suffixes = []
                if topic_category in CATEGORY_NICHES:
                    category_suffixes = CATEGORY_NICHES[topic_category].get(niche_type, [])

                # Generate keywords from patterns
                for pattern in patterns[:2]:  # Limit patterns per type
                    keyword = pattern.format(topic=topic_name)
                    if keyword not in keywords:
                        keywords.append(keyword)

                # Generate keywords from category-specific suffixes
                for suffix in category_suffixes[:2]:
                    keyword = f"{topic_name} {suffix}"
                    if keyword not in keywords:
                        keywords.append(keyword)

                # Limit per topic
                if len(keywords) >= max_keywords_per_topic * len(topics):
                    break

        return keywords

    def _detect_niche_type(self, search_keyword: str) -> str:
        """Detect what type of niche a product belongs to based on search keyword."""
        keyword_lower = search_keyword.lower()

        accessory_words = ["case", "cover", "charger", "stand", "holder", "strap", "band", "mount", "bag", "screen protector"]
        alternative_words = ["alternative", "budget", "cheap", "dupe", "like", "similar"]
        complementary_words = ["bundle", "kit", "set", "starter", "compatible", "combo"]

        if any(word in keyword_lower for word in accessory_words):
            return "accessory"
        elif any(word in keyword_lower for word in alternative_words):
            return "alternative"
        elif any(word in keyword_lower for word in complementary_words):
            return "complementary"
        else:
            return "related"

    def _calculate_combined_sentiment(
        self,
        reddit_data: Dict[str, Any],
        amazon_data: Dict[str, Any]
    ) -> float:
        """
        Calculate combined sentiment from Reddit and Amazon.

        Weights Amazon reviews higher since they're more product-specific.
        """
        reddit_sentiment = reddit_data.get("reddit_sentiment", 0)
        reddit_posts = reddit_data.get("reddit_posts", 0)

        amazon_sentiment = amazon_data.get("amazon_sentiment", 0)
        amazon_reviews = amazon_data.get("amazon_reviews_analyzed", 0)

        # If we have both, weight Amazon higher (70/30)
        if amazon_reviews > 0 and reddit_posts > 0:
            return round(amazon_sentiment * 0.7 + reddit_sentiment * 0.3, 3)
        elif amazon_reviews > 0:
            return amazon_sentiment
        elif reddit_posts > 0:
            return reddit_sentiment
        else:
            return 0

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
        Search Reddit for product-specific discussions and analyze sentiment.

        IMPORTANT: Searches by full product name first to get relevant results.
        Only falls back to keywords if no results found.

        Args:
            keywords: Keywords to search for (fallback only)
            full_name: Full product name (primary search)

        Returns:
            Reddit sentiment data
        """
        # Extract brand + product type for more specific search
        # e.g., "Ninja Fit Compact Personal Blender..." -> "Ninja Blender"
        brand_product = self._extract_brand_and_type(full_name)

        # STEP 1: Search with brand + product type (most relevant)
        posts = self.reddit.search_all_reddit(brand_product, limit=25)

        # Filter to posts that actually mention the product
        relevant_posts = [
            p for p in posts
            if any(kw.lower() in (p.get('title', '') + ' ' + p.get('content', '')).lower()
                   for kw in keywords[:2])  # Must contain at least one keyword
        ]

        # STEP 2: If not enough relevant posts, try broader keyword search
        if len(relevant_posts) < 3:
            query = ' '.join(keywords[:2])  # Use top 2 keywords only
            posts = self.reddit.search_all_reddit(query, limit=25)
            relevant_posts = [
                p for p in posts
                if any(kw.lower() in (p.get('title', '') + ' ' + p.get('content', '')).lower()
                       for kw in keywords[:2])
            ]

        if not relevant_posts:
            return {
                "reddit_posts": 0,
                "reddit_sentiment": 0,
                "reddit_positive": 0,
                "reddit_negative": 0,
                "sentiment_ratio": 0.5,
            }

        # Analyze sentiment on RELEVANT posts AND their comments
        sentiments = []
        total_comments_analyzed = 0

        # Analyze top posts and fetch their comments
        for post in relevant_posts[:10]:  # Limit to top 10 posts for comments
            # Analyze post title + body
            post_text = f"{post.get('title', '')} {post.get('content', '')}"
            label, score = self.sentiment.get_sentiment_label(post_text)
            sentiments.append({
                "label": label,
                "score": score,
                "upvotes": post.get("upvotes", 0),
                "type": "post",
            })

            # Fetch and analyze comments from this post
            post_id = post.get("platform_id", "")
            subreddit = post.get("subreddit", "")

            if post_id and subreddit:
                comments = self.reddit.scrape_comments(subreddit, post_id, limit=15)
                for comment in comments:
                    comment_text = comment.get("content", "")
                    if comment_text and len(comment_text) > 10:
                        c_label, c_score = self.sentiment.get_sentiment_label(comment_text)
                        sentiments.append({
                            "label": c_label,
                            "score": c_score,
                            "upvotes": comment.get("upvotes", 0),
                            "type": "comment",
                        })
                        total_comments_analyzed += 1

        # Weighted sentiment (comments weighted slightly less than posts)
        total_weight = 0
        weighted_sum = 0
        for s in sentiments:
            weight = max(s["upvotes"], 1)
            # Posts get full weight, comments get 0.8x weight
            if s["type"] == "comment":
                weight *= 0.8
            total_weight += weight
            weighted_sum += s["score"] * weight

        weighted_sentiment = weighted_sum / total_weight if total_weight > 0 else 0

        positive_count = sum(1 for s in sentiments if s["label"] == "positive")
        negative_count = sum(1 for s in sentiments if s["label"] == "negative")

        return {
            "reddit_posts": len(relevant_posts),
            "reddit_comments": total_comments_analyzed,
            "reddit_sentiment": round(weighted_sentiment, 3),
            "reddit_positive": positive_count,
            "reddit_negative": negative_count,
            "sentiment_ratio": round(
                positive_count / max(positive_count + negative_count, 1), 2
            ),
        }

    def _detect_seasonality(self, product_name: str) -> Dict[str, Any]:
        """
        Detect if a product is seasonal based on keywords.

        Returns:
            Dictionary with is_seasonal, season_type, and warning
        """
        name_lower = product_name.lower()

        # Seasonal keyword patterns
        seasonal_patterns = {
            "christmas": ["christmas", "xmas", "santa", "reindeer", "snowman", "ornament", "stocking"],
            "halloween": ["halloween", "costume", "spooky", "pumpkin", "witch", "ghost", "skeleton"],
            "valentines": ["valentine", "heart shaped", "romantic", "cupid"],
            "easter": ["easter", "bunny", "egg hunt"],
            "thanksgiving": ["thanksgiving", "turkey", "pilgrim"],
            "summer": ["beach", "pool float", "sunscreen", "swimsuit", "bikini", "surfboard", "patio"],
            "winter": ["snow blower", "ice scraper", "heated blanket", "space heater", "snow shovel"],
            "back_to_school": ["backpack", "school supplies", "lunchbox", "pencil case", "binder"],
            "new_years": ["new year", "party supplies", "champagne", "countdown"],
            "mothers_day": ["mothers day", "mom gift"],
            "fathers_day": ["fathers day", "dad gift"],
            "black_friday": ["black friday", "cyber monday"],
        }

        # Check for matches
        for season, keywords in seasonal_patterns.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return {
                        "is_seasonal": True,
                        "season_type": season.replace("_", " ").title(),
                        "seasonality_warning": f"⚠️ Seasonal product ({season.replace('_', ' ')})",
                    }

        # Check for general holiday/event patterns
        holiday_words = ["holiday", "festive", "celebration", "party"]
        for word in holiday_words:
            if word in name_lower:
                return {
                    "is_seasonal": True,
                    "season_type": "Holiday/Event",
                    "seasonality_warning": "⚠️ Possible seasonal product",
                }

        return {
            "is_seasonal": False,
            "season_type": "Year-round",
            "seasonality_warning": "",
        }

    def _get_sourcing_data(self, product_name: str, selling_price: float) -> Dict[str, Any]:
        """
        Generate sourcing information for a product.

        Provides:
        - Alibaba/AliExpress search URLs for manual lookup
        - Estimated supplier price based on industry ratios
        - Sourcing recommendations

        Args:
            product_name: Product name for search
            selling_price: Amazon selling price

        Returns:
            Dictionary with sourcing data
        """
        import urllib.parse

        # Extract key search terms (remove brand names, focus on product type)
        search_terms = self._extract_sourcing_keywords(product_name)
        encoded_query = urllib.parse.quote(search_terms)

        # Generate search URLs
        alibaba_url = f"https://www.alibaba.com/trade/search?SearchText={encoded_query}"
        aliexpress_url = f"https://www.aliexpress.com/wholesale?SearchText={encoded_query}"
        made_in_china_url = f"https://www.made-in-china.com/products-search/hot-china-products/{encoded_query}.html"

        # Estimate supplier prices based on typical markup ratios
        # Amazon products typically have 3-5x markup from Alibaba
        # Higher priced items tend to have lower multipliers
        if selling_price < 20:
            markup_ratio = 4.0  # Small items: 4x markup
            estimated_supplier_price = selling_price / markup_ratio
        elif selling_price < 50:
            markup_ratio = 3.5  # Medium items: 3.5x markup
            estimated_supplier_price = selling_price / markup_ratio
        elif selling_price < 100:
            markup_ratio = 3.0  # Standard items: 3x markup
            estimated_supplier_price = selling_price / markup_ratio
        else:
            markup_ratio = 2.5  # Higher value items: 2.5x markup
            estimated_supplier_price = selling_price / markup_ratio

        # Sourcing recommendation
        if estimated_supplier_price < 5:
            sourcing_rec = "Good for bulk orders (MOQ 100+)"
        elif estimated_supplier_price < 15:
            sourcing_rec = "Standard sourcing, negotiate MOQ"
        elif estimated_supplier_price < 30:
            sourcing_rec = "Consider private label"
        else:
            sourcing_rec = "High value - verify quality first"

        return {
            "alibaba_url": alibaba_url,
            "aliexpress_url": aliexpress_url,
            "estimated_supplier_price": round(estimated_supplier_price, 2),
            "typical_markup": f"{markup_ratio}x",
            "sourcing_recommendation": sourcing_rec,
        }

    def _extract_sourcing_keywords(self, product_name: str) -> str:
        """
        Extract clean search terms for supplier search.

        Removes brand names and focuses on product type.
        """
        # Common brand prefixes to remove
        brand_indicators = [
            "amazon", "ninja", "cuisinart", "instant", "keurig", "dyson",
            "shark", "bissell", "hoover", "breville", "kitchenaid", "hamilton",
            "black+decker", "oster", "sunbeam", "fit geno", "upright go",
        ]

        name_lower = product_name.lower()

        # Remove brand names
        for brand in brand_indicators:
            name_lower = name_lower.replace(brand, "")

        # Remove common filler words
        filler_words = [
            "premium", "deluxe", "professional", "advanced", "ultimate",
            "best", "top", "rated", "new", "upgraded", "improved", "2024", "2025",
            "for women", "for men", "for women and men", "unisex",
        ]

        for filler in filler_words:
            name_lower = name_lower.replace(filler, "")

        # Clean up and take first 5 words
        import re
        words = re.findall(r'\b[a-z]+\b', name_lower)
        # Filter out very short words
        words = [w for w in words if len(w) > 2]
        return ' '.join(words[:5])

    def _calculate_competition_score(self, review_count: int, rating: float) -> Dict[str, Any]:
        """
        Calculate competition score based on market indicators.

        Lower score = less competition = better opportunity

        Args:
            review_count: Number of Amazon reviews
            rating: Amazon star rating (0-5)

        Returns:
            Dictionary with competition metrics
        """
        # Competition level based on review count
        if review_count == 0:
            competition_level = "Unknown"
            competition_score = 50  # Neutral - no data
        elif review_count < 100:
            competition_level = "Very Low"
            competition_score = 10  # Great opportunity
        elif review_count < 500:
            competition_level = "Low"
            competition_score = 25
        elif review_count < 1000:
            competition_level = "Low-Medium"
            competition_score = 40
        elif review_count < 2500:
            competition_level = "Medium"
            competition_score = 55
        elif review_count < 5000:
            competition_level = "Medium-High"
            competition_score = 70
        elif review_count < 10000:
            competition_level = "High"
            competition_score = 85
        else:
            competition_level = "Very High"
            competition_score = 95  # Saturated market

        # Adjust for rating (high rating = established competition)
        if rating >= 4.5 and review_count > 1000:
            competition_score = min(100, competition_score + 5)
            competition_level += " (Strong incumbent)"

        # Market entry difficulty
        if competition_score < 30:
            entry_difficulty = "Easy"
        elif competition_score < 50:
            entry_difficulty = "Moderate"
        elif competition_score < 70:
            entry_difficulty = "Challenging"
        else:
            entry_difficulty = "Difficult"

        return {
            "competition_score": competition_score,
            "competition_level": competition_level,
            "entry_difficulty": entry_difficulty,
        }

    def _estimate_profit_margin(self, price_str: str, cogs_percent: float = 0.30) -> Dict[str, Any]:
        """
        Estimate profit margin for a product.

        Assumptions:
        - Amazon Referral Fee: 15% (typical for most categories)
        - FBA Fee: estimated based on price tier
        - COGS: 30% of selling price by default (3.3x markup from supplier)

        Args:
            price_str: Price string like "$49.99"
            cogs_percent: Cost of goods as percent of selling price (default 30%)

        Returns:
            Dictionary with margin estimates
        """
        # Parse price
        price = 0.0
        if price_str and price_str != "N/A":
            try:
                import re
                clean = re.sub(r'[^\d.]', '', price_str)
                price = float(clean) if clean else 0.0
            except (ValueError, TypeError):
                price = 0.0

        if price == 0:
            return {
                "selling_price": 0,
                "estimated_cogs": 0,
                "amazon_referral_fee": 0,
                "amazon_fba_fee": 0,
                "estimated_profit": 0,
                "profit_margin_pct": 0,
            }

        # Amazon Referral Fee: ~15%
        referral_fee = price * 0.15

        # FBA Fee estimate (simplified tiers based on price/size)
        if price < 20:
            fba_fee = 3.50  # Small, low-price items
        elif price < 50:
            fba_fee = 4.50  # Medium items
        elif price < 100:
            fba_fee = 5.50  # Standard items
        else:
            fba_fee = 7.00  # Larger/heavier items

        # Cost of Goods Sold (sourcing from supplier)
        cogs = price * cogs_percent

        # Profit calculation
        total_fees = referral_fee + fba_fee
        profit = price - cogs - total_fees
        margin_pct = (profit / price * 100) if price > 0 else 0

        return {
            "selling_price": round(price, 2),
            "estimated_cogs": round(cogs, 2),
            "amazon_referral_fee": round(referral_fee, 2),
            "amazon_fba_fee": round(fba_fee, 2),
            "estimated_profit": round(profit, 2),
            "profit_margin_pct": round(margin_pct, 1),
        }

    def _extract_brand_and_type(self, product_name: str) -> str:
        """
        Extract brand name and product type from full product name.

        E.g., "Ninja Fit Compact Personal Blender, Portable..." -> "Ninja Blender"
             "AMZCHEF Portable Blender, Strong..." -> "AMZCHEF Blender"
             "Fit Geno Back Brace Posture Corrector..." -> "Fit Geno Posture Corrector"
        """
        # Common product types to look for
        product_types = [
            "blender", "massager", "posture corrector", "back brace",
            "air fryer", "watch", "earbuds", "headphones", "speaker",
            "vacuum", "charger", "case", "stand", "mat", "band",
            "tracker", "scale", "monitor", "lamp", "fan", "heater",
            "humidifier", "purifier", "cooker", "grill", "toaster",
            "mixer", "juicer", "processor", "maker", "kettle",
        ]

        name_lower = product_name.lower()

        # Find product type
        found_type = None
        for ptype in product_types:
            if ptype in name_lower:
                found_type = ptype.title()
                break

        # Get first word as brand (usually capitalized brand names)
        words = product_name.split()
        brand = words[0] if words else ""

        # Build search query
        if found_type:
            return f"{brand} {found_type}"
        else:
            # Return first 3 words as fallback
            return ' '.join(words[:3])

    def _calculate_opportunity_score(self, product: Dict[str, Any]) -> float:
        """
        Calculate opportunity score (0-100).

        Factors:
        - Trending topic (base 30 pts)
        - Low Amazon competition (0-25 pts based on review count)
        - Combined sentiment (0-25 pts from Reddit + Amazon reviews)
        - Niche type bonus (0-10 pts for accessories/alternatives)
        - Discussion/validation bonus (0-10 pts)
        """
        import math

        # Base score for being related to a trending topic
        base_score = 30

        # Amazon competition (0-25 pts)
        # Fewer reviews = less saturated = higher score
        reviews = product.get("amazon_review_count", product.get("amazon_reviews", 0))

        if reviews == 0:
            competition_score = 25  # Unknown competition, assume opportunity
        elif reviews < 50:
            competition_score = 25  # Very low competition
        elif reviews < 200:
            competition_score = 20  # Low competition
        elif reviews < 1000:
            competition_score = 15  # Moderate competition
        elif reviews < 5000:
            competition_score = 10  # High competition
        else:
            competition_score = 5   # Very saturated

        # Combined sentiment (0-25 pts)
        # Use combined_sentiment if available, else fall back to reddit or amazon
        sentiment = product.get("combined_sentiment", 0)
        if sentiment == 0:
            sentiment = product.get("amazon_sentiment", product.get("reddit_sentiment", 0))

        # Convert -1 to 1 range to 0-25 points
        sentiment_score = ((sentiment + 1) / 2) * 25

        # Niche type bonus (0-10 pts)
        # Accessories and alternatives often have better margins
        niche_type = product.get("niche_type", "")
        niche_bonus = 0
        if niche_type == "accessory":
            niche_bonus = 10  # Accessories often have high margins
        elif niche_type == "alternative":
            niche_bonus = 8   # Budget alternatives can capture value-conscious buyers
        elif niche_type == "complementary":
            niche_bonus = 6   # Bundles/kits can differentiate

        # Validation bonus (0-10 pts)
        # More data sources = higher confidence
        validation_bonus = 0

        reddit_posts = product.get("reddit_posts", 0)
        amazon_reviews_analyzed = product.get("amazon_reviews_analyzed", 0)

        # Bonus for having Reddit discussion
        if reddit_posts > 0:
            validation_bonus += min(3, math.log10(reddit_posts + 1) * 2)

        # Bonus for having analyzed Amazon reviews
        if amazon_reviews_analyzed > 0:
            validation_bonus += min(4, amazon_reviews_analyzed / 3)

        # Bonus for high Amazon product rating
        rating = product.get("amazon_rating", 0)
        if rating >= 4.5:
            validation_bonus += 3
        elif rating >= 4.0:
            validation_bonus += 2
        elif rating >= 3.5:
            validation_bonus += 1

        # Calculate final score
        final_score = base_score + competition_score + sentiment_score + niche_bonus + validation_bonus

        # Bonuses for strong positive signals
        reddit_ratio = product.get("sentiment_ratio", 0.5)
        amazon_ratio = product.get("amazon_sentiment_ratio", 0.5)
        combined_ratio = (reddit_ratio + amazon_ratio) / 2 if amazon_ratio != 0.5 else reddit_ratio

        if combined_ratio > 0.75:
            final_score += 5  # Strong positive sentiment

        # Penalties for negative signals
        reddit_negative = product.get("reddit_negative", 0)
        reddit_positive = product.get("reddit_positive", 0)
        amazon_negative = product.get("amazon_negative", 0)
        amazon_positive = product.get("amazon_positive", 0)

        total_negative = reddit_negative + amazon_negative
        total_positive = reddit_positive + amazon_positive

        if total_negative > total_positive and total_negative > 2:
            final_score -= 15  # Strong negative signal

        return round(min(100, max(0, final_score)), 1)

    # =========================================================================
    # ASYNC VERSION - Parallel Reddit sentiment for 3-4x speedup
    # =========================================================================

    async def discover_opportunities_async(
        self,
        categories: List[str] = None,
        max_products: int = 10,
        products_per_topic: int = 3,
        niche_types: List[str] = None,
        min_price: float = 0.0,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Async version of discover_opportunities with parallel Reddit sentiment.

        Key improvements:
        - Browser reuse for Amazon searches (saves ~40s)
        - Parallel Reddit sentiment (3 concurrent, saves ~60%)
        - Product-specific Reddit search (full product name, not keywords)

        Args:
            categories: Google Trends categories
            max_products: Max products to return (default 10)
            products_per_topic: Products per trending topic
            niche_types: Types of niches to find
            min_price: Minimum price filter (default 0 = no filter)
            progress_callback: Optional callback(step, total, item, message)

        Returns:
            List of top opportunities sorted by score
        """
        if niche_types is None:
            niche_types = ["accessories", "alternatives", "complementary"]

        # Track start time for history
        start_time = datetime.utcnow()

        def update_progress(step: int, total: int, item: str = "", message: str = ""):
            if progress_callback:
                progress_callback(step, total, item, message)
            print(f"  [{step}/{total}] {message} {item[:50] if item else ''}")

        print("\n" + "=" * 70)
        print("ASYNC DISCOVERY (Parallel Reddit Sentiment)")
        print(f"Target: {max_products} products | Niche types: {', '.join(niche_types)}")
        print("=" * 70)

        # STEP 1: Get rising topics from Google Trends (sync - single call)
        print("\n[STEP 1] Getting rising queries from Google Trends...")
        if progress_callback:
            progress_callback(1, 4, "", "Fetching Google Trends data...")

        rising_topics = self.trends.get_rising_topics(categories=categories, max_per_seed=5)

        if not rising_topics:
            print("  No rising topics found")
            return []

        print(f"  Found {len(rising_topics)} rising queries")
        for topic in rising_topics[:5]:
            print(f"    - {topic['title']}")

        # STEP 2: Generate niche search keywords
        print("\n[STEP 2] Generating niche product searches...")
        if progress_callback:
            progress_callback(2, 4, "", "Generating keywords...")

        search_keywords = self._generate_niche_keywords(
            rising_topics[:8],
            niche_types=niche_types,
            max_keywords_per_topic=4
        )
        print(f"  Generated {len(search_keywords)} search queries")

        # STEP 3: Search Amazon (async with browser reuse)
        print("\n[STEP 3] Searching Amazon (browser reuse optimization)...")
        if min_price > 0:
            print(f"  (filtering for products >= ${min_price:.0f})")
        if progress_callback:
            progress_callback(3, 4, "", "Searching Amazon...")

        async with AsyncBrowserScraper(delay=15.0) as browser:
            products = await browser.search_products_batch(
                keywords=search_keywords,
                products_per_keyword=products_per_topic,
                min_price=min_price,
                progress_callback=lambda i, t, k: update_progress(i, t, k, "Searching:")
            )

        if not products:
            print("  No products found on Amazon")
            return []

        print(f"\n  Found {len(products)} unique products")

        # Limit to max_products for sentiment analysis
        products_to_analyze = products[:max_products]

        # STEP 4: Parallel Reddit sentiment (KEY SPEEDUP)
        print(f"\n[STEP 4] Analyzing Reddit sentiment (parallel, {len(products_to_analyze)} products)...")
        if progress_callback:
            progress_callback(4, 4, "", "Analyzing sentiment...")

        products_with_sentiment = await self._get_sentiment_parallel(
            products_to_analyze,
            progress_callback=progress_callback
        )

        # Score and sort
        results = []
        for product in products_with_sentiment:
            # Add additional fields
            product["niche_type"] = self._detect_niche_type(product.get('search_keyword', ''))
            product["related_topic"] = product.get('search_keyword', '')
            product["amazon_url"] = product.get('url', '')
            product["amazon_asin"] = product.get('asin', '')
            product["amazon_rating"] = product.get('rating', 0)
            product["amazon_review_count"] = product.get('reviews', 0)
            product["shopify_search_url"] = self._get_shopify_search_url(product['name'])
            product["keywords"] = self._extract_keywords(product['name'])

            # Trend data (from Google Trends - all products are from rising topics)
            product["trend_score"] = 80
            product["trend_direction"] = "rising"

            # Combined sentiment (Reddit only in fast mode)
            product["combined_sentiment"] = product.get("reddit_sentiment", 0)

            # Calculate opportunity score
            product["opportunity_score"] = self._calculate_opportunity_score(product)

            results.append(product)

        # Sort by score and return top results
        results.sort(key=lambda x: x["opportunity_score"], reverse=True)
        final_results = results[:max_products]

        print("\n" + "=" * 70)
        print(f"Discovery complete! Top {len(final_results)} opportunities:")
        for i, r in enumerate(final_results[:5]):
            print(f"  {i+1}. {r['name'][:50]} | Score: {r['opportunity_score']:.0f}")
        print("=" * 70)

        # Save to history database
        self._save_to_history(
            results=final_results,
            mode="discover_async",
            categories=categories or [],
            settings={
                "max_products": max_products,
                "niche_types": niche_types,
                "min_price": min_price
            },
            start_time=start_time
        )

        return final_results

    async def _get_sentiment_parallel(
        self,
        products: List[Dict[str, Any]],
        max_workers: int = 3,
        delay: float = 10.0,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Get Reddit sentiment for products in parallel.

        Uses AsyncWorkerPool for bounded concurrency.
        Key change: Searches by FULL PRODUCT NAME, not keywords.

        Args:
            products: List of products to analyze
            max_workers: Concurrent Reddit requests (default 3)
            delay: Delay between requests (default 10s)
            progress_callback: Optional progress callback

        Returns:
            Products with sentiment data added
        """
        async_reddit = AsyncRedditScraper(delay=delay)
        worker_pool = AsyncWorkerPool(max_workers=max_workers, delay_between_tasks=delay)

        async def analyze_single(product: Dict[str, Any]) -> Dict[str, Any]:
            """Analyze sentiment for a single product."""
            product_name = product['name']
            print(f"    Reddit: {product_name[:40]}...", end=" ")

            sentiment_data = await async_reddit.search_product_sentiment(
                product_name,  # FULL product name, not keywords
                limit=20
            )

            if sentiment_data["reddit_posts"] > 0:
                label = "+" if sentiment_data["reddit_sentiment"] > 0.05 else "-" if sentiment_data["reddit_sentiment"] < -0.05 else "~"
                print(f"{sentiment_data['reddit_posts']} posts ({label})")
            else:
                print("no posts")

            return {**product, **sentiment_data}

        # Create coroutines for all products
        coroutines = [analyze_single(p) for p in products]

        # Execute in parallel with bounded concurrency
        results = await worker_pool.execute_batch(
            coroutines,
            progress_callback=lambda done, total, msg: (
                progress_callback(done, total, "", f"Sentiment: {done}/{total}") if progress_callback else None
            )
        )

        # Filter out any errors
        return [r for r in results if not isinstance(r, dict) or "error" not in r]

    def discover_opportunities_fast(
        self,
        categories: List[str] = None,
        max_products: int = 10,
        products_per_topic: int = 3,
        niche_types: List[str] = None,
        min_price: float = 0.0,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Fast synchronous wrapper for async discovery.

        Use this for CLI/scripts.
        Note: On Windows, uses ProactorEventLoop (default) for Playwright compatibility.
        """
        return asyncio.run(self.discover_opportunities_async(
            categories=categories,
            max_products=max_products,
            products_per_topic=products_per_topic,
            niche_types=niche_types,
            min_price=min_price,
            progress_callback=progress_callback
        ))

    def search_custom_keywords(
        self,
        keywords: List[str],
        max_products: int = 30,
        min_price: float = 0.0,
        products_per_keyword: int = 5,
        include_amazon_reviews: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for products using custom keywords (skips Google Trends).

        Use this when you have your own product ideas from TikTok, Kalodata,
        or other research sources.

        Args:
            keywords: List of product keywords to search
            max_products: Max total products to analyze
            min_price: Minimum price filter
            products_per_keyword: Products to fetch per keyword
            include_amazon_reviews: Whether to scrape Amazon reviews for sentiment (slower but more accurate)

        Returns:
            List of products with sentiment data and scores
        """
        # Track start time for history
        start_time = datetime.utcnow()

        print("\n" + "=" * 70)
        print("CUSTOM KEYWORD SEARCH")
        print(f"Keywords: {len(keywords)} | Min price: ${min_price:.0f}")
        if include_amazon_reviews:
            print("Amazon review sentiment: ENABLED (slower)")
        print("=" * 70)

        # STEP 1: Search Amazon for each keyword
        print("\n[STEP 1] Searching Amazon...")
        if min_price > 0:
            print(f"  (filtering for products >= ${min_price:.0f})")
        print("-" * 50)

        products = self.amazon.search_products_batch(
            keywords=keywords,
            products_per_keyword=products_per_keyword,
            min_price=min_price,
            progress_callback=lambda i, t, k: print(f"  [{i+1}/{t}] Searching: {k[:40]}...")
        )

        if not products:
            print("  No products found on Amazon")
            return []

        print(f"\n  Found {len(products)} products")

        # Limit to max_products
        products_to_analyze = products[:max_products]

        # STEP 2: Get Reddit sentiment
        print(f"\n[STEP 2] Getting Reddit sentiment ({len(products_to_analyze)} products)...")
        print("-" * 50)

        results = []
        for i, product in enumerate(products_to_analyze):
            name = product['name']
            asin = product.get('asin', '')
            print(f"  [{i+1}/{len(products_to_analyze)}] {name[:50]}...")

            # Get Reddit sentiment
            print(f"    Reddit...", end=" ")
            keywords_extracted = self._extract_keywords(name)
            reddit_data = self._get_reddit_sentiment(keywords_extracted, name)

            if reddit_data["reddit_posts"] > 0:
                sent = reddit_data["reddit_sentiment"]
                label = "+" if sent > 0.05 else "-" if sent < -0.05 else "~"
                comments = reddit_data.get("reddit_comments", 0)
                print(f"{reddit_data['reddit_posts']} posts, {comments} comments ({label})")
            else:
                print("no posts")

            # Get Amazon review sentiment (optional - slower but more accurate)
            amazon_sentiment_data = {}
            if include_amazon_reviews and asin:
                print(f"    Amazon reviews...", end=" ")
                amazon_sentiment_data = self.amazon.get_product_sentiment(
                    asin,
                    self.sentiment,
                    max_reviews=15
                )
                if amazon_sentiment_data.get("amazon_reviews_analyzed", 0) > 0:
                    sent = amazon_sentiment_data["amazon_sentiment"]
                    label = "+" if sent > 0.05 else "-" if sent < -0.05 else "~"
                    print(f"{amazon_sentiment_data['amazon_reviews_analyzed']} reviews ({label})")
                else:
                    print("no reviews")

            # Build result
            result = {
                "name": name,
                "niche_type": product.get('search_keyword', '')[:20],  # Short keyword
                "search_keyword": product.get('search_keyword', ''),
                "amazon_url": product.get('url', ''),
                "amazon_asin": asin,
                "price": product.get('price', 'N/A'),
                "amazon_rating": product.get('rating', 0),
                "amazon_review_count": product.get('reviews', 0),
                "keywords": keywords_extracted,
                "trend_score": 70,  # Default for custom keywords
                "trend_direction": "custom",
            }

            # Add Reddit data
            result.update(reddit_data)

            # Add Amazon sentiment data if available
            if amazon_sentiment_data:
                result.update(amazon_sentiment_data)

            # Combined sentiment (weight Amazon higher if available)
            reddit_sent = reddit_data.get("reddit_sentiment", 0)
            amazon_sent = amazon_sentiment_data.get("amazon_sentiment", 0)
            if amazon_sent != 0 and reddit_sent != 0:
                # 60% Amazon (product-specific), 40% Reddit (community)
                result["combined_sentiment"] = amazon_sent * 0.6 + reddit_sent * 0.4
            elif amazon_sent != 0:
                result["combined_sentiment"] = amazon_sent
            else:
                result["combined_sentiment"] = reddit_sent

            # Calculate profit margin estimate
            profit_data = self._estimate_profit_margin(result.get("price", "0"))
            result.update(profit_data)

            # Detect seasonality
            seasonality_data = self._detect_seasonality(name)
            result.update(seasonality_data)

            # Calculate competition score
            competition_data = self._calculate_competition_score(
                result.get("amazon_review_count", 0),
                result.get("amazon_rating", 0)
            )
            result.update(competition_data)

            # Get sourcing data (Alibaba/AliExpress URLs + estimated supplier price)
            sourcing_data = self._get_sourcing_data(
                name,
                profit_data.get("selling_price", 0)
            )
            result.update(sourcing_data)

            # Calculate score
            result["opportunity_score"] = self._calculate_opportunity_score(result)

            results.append(result)

        # Sort by score
        results.sort(key=lambda x: x["opportunity_score"], reverse=True)

        print("\n" + "=" * 70)
        print(f"Found {len(results)} products")
        print("=" * 70)

        # Save to history database
        self._save_to_history(
            results=results,
            mode="custom_keywords",
            categories=[],  # No categories for custom keywords
            settings={
                "keywords": keywords,
                "max_products": max_products,
                "min_price": min_price,
                "include_amazon_reviews": include_amazon_reviews
            },
            start_time=start_time
        )

        return results
