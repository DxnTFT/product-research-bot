"""
Product Research Bot - Main Entry Point
Monitors Reddit for product opportunities and analyzes sentiment.
"""

import time
import argparse
from datetime import datetime
from typing import List, Dict

from config.settings import SUBREDDITS, SCRAPE_SETTINGS, PRODUCT_KEYWORDS
from database import Database, Product, Mention
from scrapers import RedditScraper
from analysis import SentimentAnalyzer, ProductScorer
from reports import ReportGenerator


class ProductResearchBot:
    """Main bot class that orchestrates scraping and analysis."""

    def __init__(self):
        self.db = Database()
        self.scraper = RedditScraper(delay=SCRAPE_SETTINGS["delay_between_requests"])
        self.sentiment = SentimentAnalyzer()
        self.scorer = ProductScorer()
        self.reporter = ReportGenerator()

    def run(self, categories: List[str] = None, limit_per_sub: int = None):
        """
        Run the product research bot.

        Args:
            categories: List of categories to scan (default: all)
            limit_per_sub: Override posts per subreddit limit
        """
        print("\n" + "=" * 60)
        print("PRODUCT RESEARCH BOT - Starting scan")
        print("=" * 60 + "\n")

        # Determine which subreddits to scan
        if categories:
            subreddits_to_scan = {}
            for cat in categories:
                if cat in SUBREDDITS:
                    subreddits_to_scan[cat] = SUBREDDITS[cat]
        else:
            subreddits_to_scan = SUBREDDITS

        limit = limit_per_sub or SCRAPE_SETTINGS["posts_per_subreddit"]
        total_products_found = 0

        # Scan each category
        for category, subreddit_list in subreddits_to_scan.items():
            print(f"\n[{category.upper()}] Scanning {len(subreddit_list)} subreddits...")

            for subreddit in subreddit_list:
                products_found = self._scan_subreddit(subreddit, category, limit)
                total_products_found += products_found

        # Generate report
        print("\n" + "=" * 60)
        print("Generating report...")
        print("=" * 60)

        self._generate_final_report()

        print(f"\n[COMPLETE] Found {total_products_found} product mentions")
        print("=" * 60 + "\n")

    def _scan_subreddit(self, subreddit: str, category: str, limit: int) -> int:
        """Scan a single subreddit for products."""
        print(f"  Scanning r/{subreddit}...", end=" ")

        # Create scraping log
        log = self.db.create_scraping_log("reddit", subreddit)

        try:
            # Scrape posts
            posts = self.scraper.scrape(subreddit, limit=limit)

            products_found = 0
            comments_scraped = 0

            for post in posts:
                # Analyze sentiment
                content = f"{post.get('title', '')} {post.get('content', '')}"
                label, score = self.sentiment.get_sentiment_label(content)
                post["sentiment_score"] = score
                post["sentiment_label"] = label

                # Extract product mentions
                products = self.scraper.extract_products(content)

                # Also check if title contains product keywords
                if any(kw in post.get("title", "").lower() for kw in PRODUCT_KEYWORDS):
                    # This is likely a product discussion post
                    pass

                # Store mentions
                for product_name in products:
                    product = self.db.get_or_create_product(product_name, category)
                    self.db.add_mention(product.id, post)
                    products_found += 1

                # Optionally scrape comments
                if SCRAPE_SETTINGS["include_comments"] and post.get("comments_count", 0) > 0:
                    post_id = post.get("platform_id")
                    if post_id:
                        comments = self.scraper.scrape_comments(
                            subreddit,
                            post_id,
                            limit=SCRAPE_SETTINGS["comments_per_post"]
                        )

                        for comment in comments:
                            label, score = self.sentiment.get_sentiment_label(comment.get("content", ""))
                            comment["sentiment_score"] = score
                            comment["sentiment_label"] = label

                            comment_products = self.scraper.extract_products(comment.get("content", ""))
                            for product_name in comment_products:
                                product = self.db.get_or_create_product(product_name, category)
                                self.db.add_mention(product.id, comment)
                                products_found += 1

                            comments_scraped += 1

            # Complete log
            self.db.complete_scraping_log(
                log.id,
                posts=len(posts),
                comments=comments_scraped,
                products=products_found
            )

            print(f"Found {len(posts)} posts, {products_found} product mentions")
            return products_found

        except Exception as e:
            self.db.complete_scraping_log(log.id, 0, 0, 0, str(e))
            print(f"Error: {e}")
            return 0

    def _generate_final_report(self):
        """Generate and display final report."""
        session = self.db.get_session()

        # Get all products with their mentions
        products = session.query(Product).all()

        product_data = []
        for product in products:
            mentions = self.db.get_product_mentions(product.id)
            mention_dicts = [
                {
                    "upvotes": m.upvotes,
                    "comments_count": m.comments_count,
                    "sentiment_score": m.sentiment_score,
                    "created_at": m.created_at,
                    "content": m.content,
                    "title": m.title
                }
                for m in mentions
            ]

            data = {
                "name": product.name,
                "category": product.category,
                "total_mentions": product.total_mentions,
                "avg_sentiment": product.avg_sentiment,
                "first_seen": product.first_seen,
                "last_seen": product.last_seen,
                "mentions": mention_dicts
            }

            # Calculate opportunity score
            score = self.scorer.calculate_score(data)
            data["opportunity_score"] = score

            # Update in database
            product.opportunity_score = score
            session.commit()

            product_data.append(data)

        # Generate summary
        summary = self.reporter.generate_summary(product_data)
        print(summary)

        # Export reports
        self.reporter.export_csv(product_data)
        self.reporter.export_json(product_data)

    def search_product(self, product_name: str):
        """Search for mentions of a specific product."""
        print(f"\nSearching for '{product_name}'...")

        all_mentions = []

        for category, subreddit_list in SUBREDDITS.items():
            for subreddit in subreddit_list:
                results = self.scraper.search_subreddit(subreddit, product_name, limit=10)
                for result in results:
                    label, score = self.sentiment.get_sentiment_label(
                        f"{result.get('title', '')} {result.get('content', '')}"
                    )
                    result["sentiment_score"] = score
                    result["sentiment_label"] = label
                    result["category"] = category
                    all_mentions.append(result)

        if all_mentions:
            print(f"\nFound {len(all_mentions)} mentions:")
            for mention in all_mentions[:10]:
                print(f"  [{mention['sentiment_label']}] r/{mention['subreddit']}: {mention['title'][:50]}...")
        else:
            print("No mentions found.")

        return all_mentions

    def show_top_products(self, limit: int = 20, category: str = None):
        """Display top products from database."""
        products = self.db.get_top_products(limit=limit, category=category)

        if not products:
            print("No products in database. Run a scan first.")
            return

        print(f"\nTop {limit} Products" + (f" in {category}" if category else ""))
        print("-" * 60)

        for i, product in enumerate(products, 1):
            sentiment_emoji = "+" if product.avg_sentiment > 0 else "-" if product.avg_sentiment < 0 else "~"
            print(f"{i:2}. [{sentiment_emoji}] {product.name[:30]:30} Score: {product.opportunity_score:5.1f} | Mentions: {product.total_mentions}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Product Research Bot")
    parser.add_argument("--categories", "-c", nargs="+", help="Categories to scan (e.g., fitness homegoods)")
    parser.add_argument("--limit", "-l", type=int, help="Posts per subreddit")
    parser.add_argument("--search", "-s", help="Search for a specific product")
    parser.add_argument("--top", "-t", type=int, help="Show top N products from database")

    args = parser.parse_args()

    bot = ProductResearchBot()

    if args.search:
        bot.search_product(args.search)
    elif args.top:
        bot.show_top_products(limit=args.top)
    else:
        bot.run(categories=args.categories, limit_per_sub=args.limit)


if __name__ == "__main__":
    main()
