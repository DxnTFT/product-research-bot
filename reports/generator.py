"""
Report generation for product research results.
"""

import os
import json
import csv
from datetime import datetime
from typing import List, Dict, Optional
from tabulate import tabulate


class ReportGenerator:
    """Generate reports from product research data."""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_summary(self, products: List[Dict], top_n: int = 20) -> str:
        """
        Generate a text summary of top products.

        Args:
            products: List of product dictionaries with scores
            top_n: Number of top products to show

        Returns:
            Formatted string report
        """
        if not products:
            return "No products found."

        # Sort by opportunity score
        sorted_products = sorted(
            products,
            key=lambda x: x.get("opportunity_score", 0),
            reverse=True
        )[:top_n]

        # Build report
        lines = [
            "=" * 60,
            "PRODUCT OPPORTUNITY REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            ""
        ]

        # Table data
        table_data = []
        for i, product in enumerate(sorted_products, 1):
            table_data.append([
                i,
                product.get("name", "Unknown")[:30],
                f"{product.get('opportunity_score', 0):.1f}",
                product.get("total_mentions", 0),
                f"{product.get('avg_sentiment', 0):.2f}",
                product.get("category", "N/A")
            ])

        headers = ["#", "Product", "Score", "Mentions", "Sentiment", "Category"]
        table = tabulate(table_data, headers=headers, tablefmt="grid")
        lines.append(table)

        # Summary stats
        lines.extend([
            "",
            "-" * 60,
            "SUMMARY STATISTICS",
            "-" * 60,
            f"Total products analyzed: {len(products)}",
            f"Average opportunity score: {sum(p.get('opportunity_score', 0) for p in products) / len(products):.1f}",
            f"Products with positive sentiment: {sum(1 for p in products if p.get('avg_sentiment', 0) > 0)}",
            f"Products with negative sentiment: {sum(1 for p in products if p.get('avg_sentiment', 0) < 0)}",
            ""
        ])

        return "\n".join(lines)

    def export_csv(self, products: List[Dict], filename: str = None) -> str:
        """
        Export products to CSV file with all relevant columns.

        Args:
            products: List of product dictionaries
            filename: Output filename (without extension)

        Returns:
            Path to created file
        """
        if not filename:
            filename = f"opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        filepath = os.path.join(self.output_dir, f"{filename}.csv")

        if not products:
            return filepath

        # Streamlined fields for product research export
        fields = [
            # Core info
            "name",
            "price",
            "niche_type",  # Short keyword
            "opportunity_score",
            # Profit margin estimates
            "estimated_profit",
            "profit_margin_pct",
            "estimated_cogs",
            # Sourcing
            "estimated_supplier_price",
            "alibaba_url",
            "aliexpress_url",
            "sourcing_recommendation",
            # Competition analysis
            "competition_score",
            "competition_level",
            "entry_difficulty",
            # Seasonality
            "is_seasonal",
            "season_type",
            # Amazon product data
            "amazon_url",
            "amazon_rating",
            "amazon_review_count",
            # Reddit sentiment
            "reddit_sentiment",
            "reddit_posts",
            "reddit_comments",
            # Combined
            "combined_sentiment",
            "sentiment_ratio",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()

            for product in products:
                # Convert list fields to strings
                row = product.copy()
                if isinstance(row.get('keywords'), list):
                    row['keywords'] = ', '.join(row['keywords'])
                writer.writerow(row)

        print(f"CSV exported to: {filepath}")
        return filepath

    def export_json(self, products: List[Dict], filename: str = None) -> str:
        """
        Export products to JSON file.

        Args:
            products: List of product dictionaries
            filename: Output filename (without extension)

        Returns:
            Path to created file
        """
        if not filename:
            filename = f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        filepath = os.path.join(self.output_dir, f"{filename}.json")

        def serialize(obj):
            """Recursively convert datetime objects to strings."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize(item) for item in obj]
            return obj

        serializable = serialize(products)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)

        print(f"JSON exported to: {filepath}")
        return filepath

    def generate_detailed_report(self, product: Dict, mentions: List[Dict]) -> str:
        """
        Generate detailed report for a single product.

        Args:
            product: Product dictionary
            mentions: List of mentions for this product

        Returns:
            Formatted detailed report string
        """
        lines = [
            "=" * 60,
            f"DETAILED REPORT: {product.get('name', 'Unknown')}",
            "=" * 60,
            "",
            f"Category: {product.get('category', 'N/A')}",
            f"Opportunity Score: {product.get('opportunity_score', 0):.1f}/100",
            f"Total Mentions: {product.get('total_mentions', 0)}",
            f"Average Sentiment: {product.get('avg_sentiment', 0):.2f}",
            f"First Seen: {product.get('first_seen', 'N/A')}",
            f"Last Seen: {product.get('last_seen', 'N/A')}",
            "",
            "-" * 60,
            "MENTION BREAKDOWN BY SOURCE",
            "-" * 60,
        ]

        # Group mentions by subreddit
        by_subreddit = {}
        for mention in mentions:
            sub = mention.get("subreddit", "Unknown")
            if sub not in by_subreddit:
                by_subreddit[sub] = []
            by_subreddit[sub].append(mention)

        for subreddit, sub_mentions in by_subreddit.items():
            avg_sent = sum(m.get("sentiment_score", 0) for m in sub_mentions) / len(sub_mentions)
            lines.append(f"  r/{subreddit}: {len(sub_mentions)} mentions (avg sentiment: {avg_sent:.2f})")

        # Top mentions
        lines.extend([
            "",
            "-" * 60,
            "TOP MENTIONS (by engagement)",
            "-" * 60,
        ])

        top_mentions = sorted(mentions, key=lambda x: x.get("upvotes", 0), reverse=True)[:5]
        for i, mention in enumerate(top_mentions, 1):
            lines.extend([
                f"\n{i}. [{mention.get('sentiment_label', 'N/A')}] {mention.get('title', 'No title')[:50]}",
                f"   Upvotes: {mention.get('upvotes', 0)} | Subreddit: r/{mention.get('subreddit', 'N/A')}",
                f"   URL: {mention.get('url', 'N/A')}"
            ])

        return "\n".join(lines)

    def print_live_update(self, message: str, product: Optional[Dict] = None):
        """Print a live update during scraping."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        if product:
            print(f"[{timestamp}] {message} - {product.get('name', 'Unknown')} (Score: {product.get('opportunity_score', 0):.1f})")
        else:
            print(f"[{timestamp}] {message}")
