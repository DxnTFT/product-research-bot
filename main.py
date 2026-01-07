"""
Product Research Bot - NEW PIPELINE
1. Find trending products on Amazon
2. Validate with Google Trends
3. Search Reddit for sentiment
4. Score and rank opportunities
"""

import argparse
from datetime import datetime
from typing import List, Dict, Any

from scrapers import AmazonScraper, TrendsScraper, RedditScraper, get_amazon_trending
from analysis import SentimentAnalyzer, ProductScorer
from reports import ReportGenerator
from discovery import TrendsToProductsFinder
from database import Database
import json


class ProductResearchBot:
    """
    Main bot class - NEW FLOW:
    Amazon Trending → Google Trends → Reddit Sentiment → Score
    """

    def __init__(self):
        self.amazon = AmazonScraper(delay=3.0)
        self.trends = TrendsScraper(delay=2.0)
        self.reddit = RedditScraper(delay=2.0)
        self.sentiment = SentimentAnalyzer()
        self.scorer = ProductScorer()
        self.reporter = ReportGenerator()
        self.use_browser = True  # Use browser-based scraper for Amazon

    def run(self, categories: List[str] = None, limit: int = 10, skip_trends: bool = False):
        """
        Run the full product research pipeline.

        Args:
            categories: Amazon categories to scan (kitchen, home, fitness, etc.)
            limit: Products per category
            skip_trends: Skip Google Trends check (faster but less data)
        """
        print("\n" + "=" * 70)
        print("PRODUCT RESEARCH BOT - Starting Pipeline")
        print("=" * 70)

        if categories is None:
            categories = ["kitchen", "fitness", "home"]

        # STEP 1: Find trending products on Amazon (using browser automation)
        print("\n[STEP 1] Finding trending products on Amazon...")
        print("-" * 50)
        print("  Using browser automation (Playwright)...")

        trending_products = get_amazon_trending(categories, limit_per_category=limit)

        if not trending_products:
            print("\n[ERROR] Could not fetch Amazon products.")
            print("Make sure Playwright is installed: python -m playwright install chromium")
            return

        print(f"\n  Total trending products found: {len(trending_products)}")

        # STEP 2: Validate with Google Trends (optional)
        if not skip_trends:
            print("\n[STEP 2] Validating with Google Trends...")
            print("-" * 50)
            trending_products = self._check_trends(trending_products)
        else:
            print("\n[STEP 2] Skipping Google Trends (--skip-trends flag)")
            for p in trending_products:
                p["trend_score"] = 50  # Default neutral score
                p["trend_direction"] = "unknown"

        # STEP 3: Search Reddit for sentiment
        print("\n[STEP 3] Searching Reddit for sentiment...")
        print("-" * 50)
        trending_products = self._get_reddit_sentiment(trending_products)

        # STEP 4: Calculate final scores
        print("\n[STEP 4] Calculating opportunity scores...")
        print("-" * 50)
        scored_products = self._calculate_scores(trending_products)

        # Generate report
        print("\n[STEP 5] Generating report...")
        print("-" * 50)
        self._generate_report(scored_products)

        print("\n" + "=" * 70)
        print("PIPELINE COMPLETE")
        print("=" * 70 + "\n")

    def _check_trends(self, products: List[Dict]) -> List[Dict]:
        """Check Google Trends for each product."""
        for i, product in enumerate(products):
            name = product.get("name", "")[:50]
            print(f"  [{i+1}/{len(products)}] Checking: {name}...", end=" ")

            trend_data = self.trends.check_trend(name)
            product["trend_score"] = trend_data.get("trend_score", 50)
            product["trend_direction"] = trend_data.get("trend_direction", "unknown")
            product["trend_recent"] = trend_data.get("recent_interest", 0)

            print(f"{product['trend_direction']} ({product['trend_score']})")

        return products

    def _get_reddit_sentiment(self, products: List[Dict]) -> List[Dict]:
        """Search Reddit for each product and analyze sentiment."""
        for i, product in enumerate(products):
            name = product.get("name", "")
            # Use shorter search query
            search_query = self._make_search_query(name)

            print(f"  [{i+1}/{len(products)}] Searching: {search_query[:40]}...", end=" ")

            # Search Reddit
            posts = self.reddit.search_all_reddit(search_query, limit=20)

            if posts:
                # Analyze sentiment of all posts
                sentiments = []
                for post in posts:
                    text = f"{post.get('title', '')} {post.get('content', '')}"
                    label, score = self.sentiment.get_sentiment_label(text)
                    sentiments.append({
                        "label": label,
                        "score": score,
                        "upvotes": post.get("upvotes", 0),
                    })

                # Calculate weighted sentiment (upvotes matter)
                total_weight = sum(max(s["upvotes"], 1) for s in sentiments)
                weighted_sentiment = sum(
                    s["score"] * max(s["upvotes"], 1) for s in sentiments
                ) / total_weight if total_weight > 0 else 0

                positive_count = sum(1 for s in sentiments if s["label"] == "positive")
                negative_count = sum(1 for s in sentiments if s["label"] == "negative")

                product["reddit_posts"] = len(posts)
                product["reddit_sentiment"] = round(weighted_sentiment, 3)
                product["reddit_positive"] = positive_count
                product["reddit_negative"] = negative_count
                product["sentiment_ratio"] = round(
                    positive_count / max(positive_count + negative_count, 1), 2
                )

                sentiment_label = "positive" if weighted_sentiment > 0.05 else "negative" if weighted_sentiment < -0.05 else "neutral"
                print(f"{len(posts)} posts, {sentiment_label} ({weighted_sentiment:.2f})")
            else:
                product["reddit_posts"] = 0
                product["reddit_sentiment"] = 0
                product["reddit_positive"] = 0
                product["reddit_negative"] = 0
                product["sentiment_ratio"] = 0.5
                print("no posts found")

        return products

    def _make_search_query(self, product_name: str) -> str:
        """Create a good search query from product name."""
        import re
        # Remove size/quantity info
        query = re.sub(r'\d+\s*(oz|ml|inch|pack|count|lb|kg|piece|set)\b', '', product_name, flags=re.IGNORECASE)
        # Remove parentheses content
        query = re.sub(r'\([^)]*\)', '', query)
        # Clean up
        query = re.sub(r'\s+', ' ', query).strip()
        # Take first few meaningful words
        words = query.split()[:4]
        return ' '.join(words)

    def _calculate_scores(self, products: List[Dict]) -> List[Dict]:
        """Calculate final opportunity score for each product."""
        for product in products:
            # Components of the score:
            # 1. Amazon trend (it's on Movers & Shakers) = base 30 points
            # 2. Google Trends score (0-100) = up to 25 points
            # 3. Reddit sentiment (-1 to 1) = up to 25 points
            # 4. Reddit discussion volume = up to 20 points

            base_score = 30  # On Amazon trending = good sign

            # Google Trends component
            trend_score = product.get("trend_score", 50)
            trend_component = (trend_score / 100) * 25

            # Reddit sentiment component
            reddit_sentiment = product.get("reddit_sentiment", 0)
            # Convert -1 to 1 range to 0 to 25
            sentiment_component = ((reddit_sentiment + 1) / 2) * 25

            # Reddit volume component (log scale)
            reddit_posts = product.get("reddit_posts", 0)
            import math
            volume_component = min(20, math.log10(reddit_posts + 1) * 10)

            # Final score
            final_score = base_score + trend_component + sentiment_component + volume_component

            # Bonus for positive sentiment ratio
            if product.get("sentiment_ratio", 0.5) > 0.7:
                final_score += 5

            # Penalty for negative sentiment
            if product.get("reddit_negative", 0) > product.get("reddit_positive", 0):
                final_score -= 10

            product["opportunity_score"] = round(min(100, max(0, final_score)), 1)

        # Sort by score
        products.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)

        return products

    def _generate_report(self, products: List[Dict]):
        """Generate and display the final report."""
        print("\n" + "=" * 70)
        print("TOP PRODUCT OPPORTUNITIES")
        print("=" * 70)

        # Display top 20
        for i, product in enumerate(products[:20], 1):
            name = product.get("name", "Unknown")[:45]
            score = product.get("opportunity_score", 0)
            trend = product.get("trend_direction", "?")[0].upper()
            sentiment = product.get("reddit_sentiment", 0)
            posts = product.get("reddit_posts", 0)
            category = product.get("category", "")

            sent_emoji = "+" if sentiment > 0.05 else "-" if sentiment < -0.05 else "~"

            print(f"{i:2}. [{score:5.1f}] {name:45} | {category:8} | T:{trend} S:{sent_emoji} R:{posts:2}")

        print("\nLegend: T=Trend(R/S/F/U), S=Sentiment(+/-/~), R=Reddit posts")

        # Summary
        print("\n" + "-" * 70)
        print("SUMMARY")
        print("-" * 70)
        print(f"Total products analyzed: {len(products)}")
        avg_score = sum(p.get("opportunity_score", 0) for p in products) / len(products) if products else 0
        print(f"Average opportunity score: {avg_score:.1f}")

        high_opportunity = [p for p in products if p.get("opportunity_score", 0) >= 70]
        print(f"High opportunity (70+): {len(high_opportunity)} products")

        # Export
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Prepare export data - map to CSV field names
        export_data = []
        for p in products:
            export_data.append({
                "name": p.get("name", ""),
                "price": p.get("price", ""),
                "niche_type": p.get("niche_type", "") or p.get("search_keyword", "")[:15],
                "opportunity_score": p.get("opportunity_score", 0),
                # Profit margin estimates
                "estimated_profit": p.get("estimated_profit", 0),
                "profit_margin_pct": p.get("profit_margin_pct", 0),
                "estimated_cogs": p.get("estimated_cogs", 0),
                # Sourcing
                "estimated_supplier_price": p.get("estimated_supplier_price", 0),
                "alibaba_url": p.get("alibaba_url", ""),
                "aliexpress_url": p.get("aliexpress_url", ""),
                "sourcing_recommendation": p.get("sourcing_recommendation", ""),
                # Competition analysis
                "competition_score": p.get("competition_score", 0),
                "competition_level": p.get("competition_level", ""),
                "entry_difficulty": p.get("entry_difficulty", ""),
                # Seasonality
                "is_seasonal": p.get("is_seasonal", False),
                "season_type": p.get("season_type", ""),
                # Amazon product data
                "amazon_url": p.get("amazon_url", "") or p.get("url", ""),
                "amazon_rating": p.get("amazon_rating", 0) or p.get("rating", 0),
                "amazon_review_count": p.get("amazon_review_count", 0) or p.get("reviews", 0),
                # Reddit sentiment
                "reddit_sentiment": p.get("reddit_sentiment", 0),
                "reddit_posts": p.get("reddit_posts", 0),
                "reddit_comments": p.get("reddit_comments", 0),
                # Combined
                "combined_sentiment": p.get("combined_sentiment", 0),
                "sentiment_ratio": p.get("sentiment_ratio", 0),
            })

        csv_path = self.reporter.export_csv(export_data, f"opportunities_{timestamp}")
        json_path = self.reporter.export_json(export_data, f"opportunities_{timestamp}")

        print(f"\nExported to:")
        print(f"  - {csv_path}")
        print(f"  - {json_path}")

    def quick_check(self, product_name: str):
        """
        Quick check for a single product.
        Useful for validating a product idea.
        """
        print(f"\n[QUICK CHECK] {product_name}")
        print("=" * 50)

        # Google Trends
        print("\n1. Google Trends...")
        trend_data = self.trends.check_trend(product_name)
        print(f"   Direction: {trend_data.get('trend_direction', 'unknown')}")
        print(f"   Score: {trend_data.get('trend_score', 0)}")
        print(f"   Recent Interest: {trend_data.get('recent_interest', 0)}")

        # Reddit
        print("\n2. Reddit Sentiment...")
        posts = self.reddit.search_all_reddit(product_name, limit=30)
        print(f"   Posts found: {len(posts)}")

        if posts:
            sentiments = []
            for post in posts:
                text = f"{post.get('title', '')} {post.get('content', '')}"
                label, score = self.sentiment.get_sentiment_label(text)
                sentiments.append({"label": label, "score": score})

            avg_sentiment = sum(s["score"] for s in sentiments) / len(sentiments)
            positive = sum(1 for s in sentiments if s["label"] == "positive")
            negative = sum(1 for s in sentiments if s["label"] == "negative")

            print(f"   Avg Sentiment: {avg_sentiment:.2f}")
            print(f"   Positive: {positive}, Negative: {negative}")

            print("\n   Sample posts:")
            for post in posts[:3]:
                title = post.get("title", "")[:60]
                sub = post.get("subreddit", "")
                print(f"   - r/{sub}: {title}...")

        print("\n" + "=" * 50)

    def research_products(self, products: List[str], skip_trends: bool = False):
        """
        Research a list of products provided by user.

        Args:
            products: List of product names to research
            skip_trends: Skip Google Trends check
        """
        print("\n" + "=" * 70)
        print("PRODUCT RESEARCH BOT - Manual Product Research")
        print("=" * 70)
        print(f"\nResearching {len(products)} products...")

        # Convert to dict format
        product_list = [
            {"name": p, "category": "manual", "source": "user_input"}
            for p in products
        ]

        # STEP 1: Google Trends (optional)
        if not skip_trends:
            print("\n[STEP 1] Checking Google Trends...")
            print("-" * 50)
            product_list = self._check_trends(product_list)
        else:
            print("\n[STEP 1] Skipping Google Trends")
            for p in product_list:
                p["trend_score"] = 50
                p["trend_direction"] = "unknown"

        # STEP 2: Reddit sentiment
        print("\n[STEP 2] Searching Reddit for sentiment...")
        print("-" * 50)
        product_list = self._get_reddit_sentiment(product_list)

        # STEP 3: Calculate scores
        print("\n[STEP 3] Calculating scores...")
        print("-" * 50)
        scored = self._calculate_scores(product_list)

        # Generate report
        print("\n[STEP 4] Generating report...")
        self._generate_report(scored)

        print("\n" + "=" * 70)
        print("RESEARCH COMPLETE")
        print("=" * 70 + "\n")

    def research_from_file(self, filepath: str, skip_trends: bool = False):
        """
        Research products from a text file.

        Args:
            filepath: Path to text file (one product per line)
            skip_trends: Skip Google Trends check
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Filter out comments and empty lines
                products = [
                    line.strip() for line in f
                    if line.strip() and not line.strip().startswith('#')
                ]

            if not products:
                print(f"No products found in {filepath}")
                return

            print(f"Loaded {len(products)} products from {filepath}")
            self.research_products(products, skip_trends=skip_trends)

        except FileNotFoundError:
            print(f"File not found: {filepath}")
        except Exception as e:
            print(f"Error reading file: {e}")


# =========================================================================
# History CLI Functions
# =========================================================================

def show_recent_runs(limit: int = 20):
    """Display recent discovery runs."""
    db = Database()
    runs = db.get_recent_runs(limit=limit)

    if not runs:
        print("\nNo discovery runs found in history.")
        print("Run a discovery first: python main.py --discover")
        return

    print("\n" + "=" * 80)
    print("RECENT DISCOVERY RUNS")
    print("=" * 80)
    print(f"{'ID':<6} {'Timestamp':<20} {'Mode':<18} {'Products':<10} {'Avg Score':<10} {'Duration'}")
    print("-" * 80)

    for run in runs:
        timestamp = run.run_timestamp.strftime("%Y-%m-%d %H:%M") if run.run_timestamp else "N/A"
        duration = f"{run.duration_seconds}s" if run.duration_seconds else "N/A"
        print(f"{run.id:<6} {timestamp:<20} {run.mode:<18} {run.products_found:<10} {run.avg_score:<10.1f} {duration}")

    print("-" * 80)
    print(f"Total: {len(runs)} runs")
    print("\nTip: Use --run-details <ID> to see products from a specific run")


def show_product_history(query: str):
    """Show history for products matching a query."""
    db = Database()
    products = db.search_products(query, limit=10)

    if not products:
        print(f"\nNo products found matching '{query}'")
        return

    print("\n" + "=" * 80)
    print(f"PRODUCT HISTORY: '{query}'")
    print("=" * 80)

    for product in products:
        print(f"\n{'-' * 70}")
        print(f"Product: {product.name[:60]}")
        print(f"{'-' * 70}")
        print(f"  Times Seen: {product.times_seen}")
        print(f"  First Seen: {product.first_seen.strftime('%Y-%m-%d') if product.first_seen else 'N/A'}")
        print(f"  Last Seen:  {product.last_seen.strftime('%Y-%m-%d') if product.last_seen else 'N/A'}")
        print(f"  Score Range: {product.lowest_score:.1f} - {product.highest_score:.1f}")
        print(f"  Current Score: {product.opportunity_score:.1f}")

        # Get recent snapshots
        history = db.get_product_history(product.id, limit=5)
        if history:
            print(f"\n  Recent History:")
            for snap in history:
                run_date = snap.discovery_run.run_timestamp.strftime("%m/%d") if snap.discovery_run else "?"
                print(f"    [{run_date}] Score: {snap.opportunity_score:.1f} | Sentiment: {snap.reddit_sentiment:.2f}")


def show_run_details(run_id: int):
    """Show details of a specific discovery run."""
    db = Database()
    run = db.get_run_by_id(run_id)

    if not run:
        print(f"\nRun #{run_id} not found")
        return

    print("\n" + "=" * 80)
    print(f"DISCOVERY RUN #{run_id}")
    print("=" * 80)
    print(f"Timestamp: {run.run_timestamp.strftime('%Y-%m-%d %H:%M:%S') if run.run_timestamp else 'N/A'}")
    print(f"Mode: {run.mode}")
    print(f"Categories: {run.categories}")
    print(f"Settings: {run.settings}")
    print(f"Products Found: {run.products_found}")
    print(f"Average Score: {run.avg_score:.1f}")
    print(f"Duration: {run.duration_seconds}s" if run.duration_seconds else "Duration: N/A")

    # Get products from this run
    snapshots = db.get_run_products(run_id)

    if snapshots:
        print(f"\n{'-' * 80}")
        print("PRODUCTS IN THIS RUN (sorted by score)")
        print(f"{'-' * 80}")
        print(f"{'#':<4} {'Score':<8} {'Sentiment':<12} {'Product Name'}")
        print("-" * 80)

        for i, snap in enumerate(snapshots[:30], 1):
            sent_label = "+" if snap.reddit_sentiment > 0.05 else "-" if snap.reddit_sentiment < -0.05 else "~"
            print(f"{i:<4} {snap.opportunity_score:<8.1f} {sent_label}{abs(snap.reddit_sentiment):<10.2f} {snap.product.name[:55]}")


def compare_discovery_runs(run_id_1: int, run_id_2: int):
    """Compare two discovery runs."""
    db = Database()

    run1 = db.get_run_by_id(run_id_1)
    run2 = db.get_run_by_id(run_id_2)

    if not run1:
        print(f"\nRun #{run_id_1} not found")
        return
    if not run2:
        print(f"\nRun #{run_id_2} not found")
        return

    comparison = db.compare_runs(run_id_1, run_id_2)

    print("\n" + "=" * 80)
    print(f"COMPARING RUN #{run_id_1} vs RUN #{run_id_2}")
    print("=" * 80)

    date1 = run1.run_timestamp.strftime("%Y-%m-%d %H:%M") if run1.run_timestamp else "N/A"
    date2 = run2.run_timestamp.strftime("%Y-%m-%d %H:%M") if run2.run_timestamp else "N/A"

    print(f"\nRun #{run_id_1}: {date1} | {run1.products_found} products | Avg: {run1.avg_score:.1f}")
    print(f"Run #{run_id_2}: {date2} | {run2.products_found} products | Avg: {run2.avg_score:.1f}")

    summary = comparison['summary']
    print(f"\n{'-' * 60}")
    print(f"New Products: {summary['new_count']} | Recurring: {summary['recurring_count']} | Dropped: {summary['dropped_count']}")
    print(f"{'-' * 60}")

    # Show new products
    if comparison['new_products']:
        print(f"\nNEW PRODUCTS (in Run #{run_id_2}):")
        for p in comparison['new_products'][:10]:
            print(f"  + {p['name'][:50]} (Score: {p['score']:.1f})")

    # Show dropped products
    if comparison['dropped_products']:
        print(f"\nDROPPED PRODUCTS (not in Run #{run_id_2}):")
        for p in comparison['dropped_products'][:10]:
            print(f"  - {p['name'][:50]} (Was: {p['score']:.1f})")

    # Show recurring products with score changes
    if comparison['recurring_products']:
        print(f"\nRECURRING PRODUCTS (score changes):")
        for p in comparison['recurring_products'][:10]:
            change = p['score_change']
            arrow = "^" if change > 0 else "v" if change < 0 else "="
            print(f"  {arrow} {p['name'][:45]} ({p['score_old']:.1f} -> {p['score_new']:.1f}, {change:+.1f})")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Product Research Bot - Find trending products with good sentiment"
    )
    parser.add_argument(
        "--categories", "-c", nargs="+",
        default=["kitchen", "fitness", "home"],
        help="Amazon categories to scan (kitchen, home, fitness, sports, electronics, beauty)"
    )
    parser.add_argument(
        "--limit", "-l", type=int, default=10,
        help="Products per category (default: 10)"
    )
    parser.add_argument(
        "--skip-trends", action="store_true",
        help="Skip Google Trends check (faster)"
    )
    parser.add_argument(
        "--check", type=str,
        help="Quick check a single product (e.g., --check 'air fryer')"
    )
    parser.add_argument(
        "--products", "-p", nargs="+",
        help="Manually specify products to research (e.g., -p 'air fryer' 'yoga mat' 'blender')"
    )
    parser.add_argument(
        "--file", "-f", type=str,
        help="Load products from a text file (one product per line)"
    )
    parser.add_argument(
        "--discover", "-d", action="store_true",
        help="Discover hidden niches (rising trends + low competition)"
    )
    parser.add_argument(
        "--seed-keywords", nargs="+",
        default=["kitchen", "fitness", "home"],
        help="Seed keywords for niche discovery (default: kitchen fitness home)"
    )
    parser.add_argument(
        "--max-products", type=int, default=10,
        help="Max products to analyze in discovery mode (default: 10)"
    )
    parser.add_argument(
        "--fast", action="store_true", default=True,
        help="Use fast async mode with parallel Reddit (default: True)"
    )
    parser.add_argument(
        "--slow", action="store_true",
        help="Use original slow sequential mode"
    )
    parser.add_argument(
        "--min-price", type=float, default=0.0,
        help="Minimum product price filter (default: 0 = no filter)"
    )
    parser.add_argument(
        "--keywords", "-k", nargs="+",
        help="Custom product keywords to search (skips Google Trends). Example: -k 'posture corrector' 'led face mask'"
    )
    parser.add_argument(
        "--amazon-reviews", action="store_true",
        help="Include Amazon review sentiment analysis (slower but more accurate)"
    )

    # History commands
    parser.add_argument(
        "--list-runs", action="store_true",
        help="List recent discovery runs from history"
    )
    parser.add_argument(
        "--history", type=str,
        help="Show history for a product (e.g., --history 'air fryer')"
    )
    parser.add_argument(
        "--compare", nargs=2, type=int, metavar=("RUN1", "RUN2"),
        help="Compare two discovery runs (e.g., --compare 1 2)"
    )
    parser.add_argument(
        "--run-details", type=int, metavar="RUN_ID",
        help="Show details of a specific discovery run"
    )

    args = parser.parse_args()

    # Handle history commands first
    if args.list_runs:
        show_recent_runs()
        return
    elif args.history:
        show_product_history(args.history)
        return
    elif args.compare:
        compare_discovery_runs(args.compare[0], args.compare[1])
        return
    elif args.run_details:
        show_run_details(args.run_details)
        return

    if args.discover or args.keywords:
        finder = TrendsToProductsFinder()

        # Check if using custom keywords (skip Google Trends)
        if args.keywords:
            print("\n" + "=" * 70)
            print("CUSTOM KEYWORDS MODE - Skipping Google Trends")
            print("=" * 70)
            print(f"Keywords: {', '.join(args.keywords)}")
            if args.min_price > 0:
                print(f"Filtering for products >= ${args.min_price:.0f}")

            print("\nSearching Amazon + Reddit sentiment...")
            opportunities = finder.search_custom_keywords(
                keywords=args.keywords,
                max_products=args.max_products,
                min_price=args.min_price,
                include_amazon_reviews=args.amazon_reviews
            )
        else:
            # Discover hidden niches mode - uses real Google Trends data
            print("\n" + "=" * 70)
            print("DISCOVER MODE - Finding products from real Google Trends data")
            print("=" * 70)

            # Map seed keywords to Google Trends categories
            category_map = {
                "kitchen": "shopping",
                "fitness": "shopping",
                "home": "shopping",
                "tech": "technology",
                "technology": "technology",
                "beauty": "fashion_beauty",
                "fashion": "fashion_beauty",
                "pets": "pets",
                "hobbies": "hobbies",
            }

            # Convert seed keywords to categories
            categories = []
            for kw in args.seed_keywords:
                cat = category_map.get(kw.lower(), "shopping")
                if cat not in categories:
                    categories.append(cat)

            # Use fast async mode by default, unless --slow is specified
            if args.min_price > 0:
                print(f"Filtering for products >= ${args.min_price:.0f}")

            if args.slow:
                print("Using SLOW sequential mode...")
                print("This will take 5-10 minutes due to rate limiting...")
                opportunities = finder.discover_opportunities(
                    categories=categories,
                    max_products=args.max_products,
                    products_per_topic=3,
                    min_price=args.min_price
                )
            else:
                print("Using FAST async mode with parallel Reddit sentiment...")
                print("Expected time: 3-4 minutes")
                opportunities = finder.discover_opportunities_fast(
                    categories=categories,
                    max_products=args.max_products,
                    products_per_topic=3,
                    min_price=args.min_price
                )

        # Generate report
        if opportunities:
            bot = ProductResearchBot()
            bot._generate_report(opportunities)
        else:
            print("\nNo opportunities found. Try different keywords or check rate limits.")
    else:
        bot = ProductResearchBot()

        if args.check:
            bot.quick_check(args.check)
        elif args.products:
            bot.research_products(args.products, skip_trends=args.skip_trends)
        elif args.file:
            bot.research_from_file(args.file, skip_trends=args.skip_trends)
        else:
            bot.run(
                categories=args.categories,
                limit=args.limit,
                skip_trends=args.skip_trends
            )


if __name__ == "__main__":
    main()
