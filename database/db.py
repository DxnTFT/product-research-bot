"""
Database operations and session management.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime, timedelta
from typing import Optional, List

from .models import Base, Product, Mention, ScrapingLog, TrendSnapshot, DiscoveryRun, ProductSnapshot
import json
import re


class Database:
    """Handle all database operations."""

    def __init__(self, db_path: str = "data/products.db"):
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)

        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)

    def get_session(self):
        """Get a new database session."""
        return self.Session()

    def close(self):
        """Close all sessions."""
        self.Session.remove()

    # Product operations
    def get_or_create_product(self, name: str, category: str = None) -> Product:
        """Get existing product or create new one."""
        session = self.get_session()

        # Normalize product name
        normalized_name = name.lower().strip()

        product = session.query(Product).filter(
            Product.name.ilike(f"%{normalized_name}%")
        ).first()

        if not product:
            product = Product(
                name=normalized_name,
                category=category,
                total_mentions=0
            )
            session.add(product)
            session.commit()

        return product

    def update_product_stats(self, product_id: int):
        """Recalculate product statistics from mentions."""
        session = self.get_session()
        product = session.query(Product).get(product_id)

        if product:
            mentions = session.query(Mention).filter(
                Mention.product_id == product_id
            ).all()

            product.total_mentions = len(mentions)
            if mentions:
                product.avg_sentiment = sum(m.sentiment_score or 0 for m in mentions) / len(mentions)
            product.last_seen = datetime.utcnow()

            session.commit()

        return product

    # Mention operations
    def add_mention(self, product_id: int, mention_data: dict) -> Mention:
        """Add a new mention to the database."""
        session = self.get_session()

        # Check if mention already exists
        existing = session.query(Mention).filter(
            Mention.platform_id == mention_data.get("platform_id"),
            Mention.source == mention_data.get("source")
        ).first()

        if existing:
            return existing

        mention = Mention(
            product_id=product_id,
            **mention_data
        )
        session.add(mention)
        session.commit()

        # Update product stats
        self.update_product_stats(product_id)

        return mention

    # Logging operations
    def create_scraping_log(self, source: str, subreddit: str = None) -> ScrapingLog:
        """Create a new scraping log entry."""
        session = self.get_session()
        log = ScrapingLog(source=source, subreddit=subreddit)
        session.add(log)
        session.commit()
        return log

    def complete_scraping_log(self, log_id: int, posts: int, comments: int, products: int, errors: str = None):
        """Complete a scraping log entry."""
        session = self.get_session()
        log = session.query(ScrapingLog).get(log_id)
        if log:
            log.posts_scraped = posts
            log.comments_scraped = comments
            log.products_found = products
            log.errors = errors
            log.completed_at = datetime.utcnow()
            session.commit()

    # Query operations
    def get_top_products(self, limit: int = 20, category: str = None) -> List[Product]:
        """Get top products by opportunity score."""
        session = self.get_session()
        query = session.query(Product).order_by(Product.opportunity_score.desc())

        if category:
            query = query.filter(Product.category == category)

        return query.limit(limit).all()

    def get_trending_products(self, days: int = 7, limit: int = 20) -> List[Product]:
        """Get products with increasing mention velocity."""
        session = self.get_session()
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get products with recent mentions
        products = session.query(Product).join(Mention).filter(
            Mention.scraped_at >= cutoff
        ).order_by(Product.total_mentions.desc()).limit(limit).all()

        return products

    def get_product_mentions(self, product_id: int, limit: int = 50) -> List[Mention]:
        """Get mentions for a specific product."""
        session = self.get_session()
        return session.query(Mention).filter(
            Mention.product_id == product_id
        ).order_by(Mention.scraped_at.desc()).limit(limit).all()

    def get_mentions_by_subreddit(self, subreddit: str, limit: int = 100) -> List[Mention]:
        """Get all mentions from a specific subreddit."""
        session = self.get_session()
        return session.query(Mention).filter(
            Mention.subreddit == subreddit
        ).order_by(Mention.scraped_at.desc()).limit(limit).all()

    def get_sentiment_summary(self, product_id: int = None) -> dict:
        """Get sentiment summary for a product or overall."""
        session = self.get_session()
        query = session.query(Mention)

        if product_id:
            query = query.filter(Mention.product_id == product_id)

        mentions = query.all()

        if not mentions:
            return {"positive": 0, "negative": 0, "neutral": 0, "total": 0}

        summary = {
            "positive": sum(1 for m in mentions if m.sentiment_label == "positive"),
            "negative": sum(1 for m in mentions if m.sentiment_label == "negative"),
            "neutral": sum(1 for m in mentions if m.sentiment_label == "neutral"),
            "total": len(mentions),
            "avg_score": sum(m.sentiment_score or 0 for m in mentions) / len(mentions)
        }

        return summary

    # =========================================================================
    # Discovery Run Management (Historical Tracking)
    # =========================================================================

    def normalize_product_name(self, name: str) -> str:
        """Create a normalized version of product name for matching across runs."""
        name = name.lower().strip()
        # Remove size/quantity info
        name = re.sub(r'\d+\s*(oz|ml|inch|pack|count|lb|kg|piece|set|mm|cm)\b', '', name, flags=re.IGNORECASE)
        # Remove parentheses content
        name = re.sub(r'\([^)]*\)', '', name)
        # Remove brackets content
        name = re.sub(r'\[[^\]]*\]', '', name)
        # Remove special characters
        name = re.sub(r'[^\w\s]', '', name)
        # Clean whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        # Take first 5 words for matching
        words = name.split()[:5]
        return ' '.join(words)

    def create_discovery_run(self, mode: str, categories: List[str] = None, settings: dict = None) -> DiscoveryRun:
        """Create a new discovery run record."""
        session = self.get_session()
        run = DiscoveryRun(
            mode=mode,
            categories=json.dumps(categories or []),
            settings=json.dumps(settings or {})
        )
        session.add(run)
        session.commit()
        return run

    def complete_discovery_run(self, run_id: int, products_found: int, avg_score: float, duration_seconds: int):
        """Mark a discovery run as complete with stats."""
        session = self.get_session()
        run = session.query(DiscoveryRun).get(run_id)
        if run:
            run.products_found = products_found
            run.avg_score = avg_score
            run.duration_seconds = duration_seconds
            session.commit()

    def get_recent_runs(self, limit: int = 10) -> List[DiscoveryRun]:
        """Get most recent discovery runs."""
        session = self.get_session()
        return session.query(DiscoveryRun).order_by(
            DiscoveryRun.run_timestamp.desc()
        ).limit(limit).all()

    def get_run_by_id(self, run_id: int) -> Optional[DiscoveryRun]:
        """Get a specific run by ID."""
        session = self.get_session()
        return session.query(DiscoveryRun).get(run_id)

    def get_run_products(self, run_id: int) -> List[ProductSnapshot]:
        """Get all product snapshots for a specific run."""
        session = self.get_session()
        return session.query(ProductSnapshot).filter(
            ProductSnapshot.discovery_run_id == run_id
        ).order_by(ProductSnapshot.opportunity_score.desc()).all()

    # =========================================================================
    # Product Tracking
    # =========================================================================

    def get_or_create_product_by_name(self, name: str, category: str = None) -> Product:
        """Find product by normalized name or create new one."""
        session = self.get_session()
        normalized = self.normalize_product_name(name)

        product = session.query(Product).filter(
            Product.normalized_name == normalized
        ).first()

        if not product:
            product = Product(
                name=name,
                normalized_name=normalized,
                category=category,
                times_seen=0,
                highest_score=0.0,
                lowest_score=100.0
            )
            session.add(product)
            session.commit()

        return product

    def save_product_snapshot(self, run_id: int, product_data: dict) -> ProductSnapshot:
        """Save a product snapshot for a discovery run."""
        session = self.get_session()

        # Get or create the Product record
        product = self.get_or_create_product_by_name(
            product_data.get('name', ''),
            product_data.get('category')
        )

        score = product_data.get('opportunity_score', 0)

        # Update Product tracking fields
        product.times_seen += 1
        product.last_seen = datetime.utcnow()
        product.opportunity_score = score
        product.avg_sentiment = product_data.get('reddit_sentiment', 0)

        if score > product.highest_score:
            product.highest_score = score
        if score < product.lowest_score:
            product.lowest_score = score

        # Create snapshot
        snapshot = ProductSnapshot(
            discovery_run_id=run_id,
            product_id=product.id,
            opportunity_score=score,
            reddit_sentiment=product_data.get('reddit_sentiment', 0),
            sentiment_ratio=product_data.get('sentiment_ratio', 0),
            reddit_posts=product_data.get('reddit_posts', 0),
            amazon_review_count=product_data.get('amazon_review_count', 0),
            price=str(product_data.get('price', '')),
            niche_type=product_data.get('niche_type', ''),
            trend_direction=product_data.get('trend_direction', ''),
            combined_sentiment=product_data.get('combined_sentiment', 0)
        )
        session.add(snapshot)
        session.commit()

        return snapshot

    def bulk_save_snapshots(self, run_id: int, products: List[dict]) -> int:
        """Save multiple product snapshots efficiently."""
        count = 0
        for product_data in products:
            try:
                self.save_product_snapshot(run_id, product_data)
                count += 1
            except Exception as e:
                print(f"Error saving snapshot for {product_data.get('name', 'unknown')}: {e}")
        return count

    # =========================================================================
    # Historical Analysis
    # =========================================================================

    def get_product_history(self, product_id: int, limit: int = 30) -> List[ProductSnapshot]:
        """Get score history for a product across runs."""
        session = self.get_session()
        return session.query(ProductSnapshot).filter(
            ProductSnapshot.product_id == product_id
        ).order_by(ProductSnapshot.id.desc()).limit(limit).all()

    def search_products(self, query: str, limit: int = 20) -> List[Product]:
        """Search products by name."""
        session = self.get_session()
        return session.query(Product).filter(
            Product.name.ilike(f"%{query}%")
        ).order_by(Product.times_seen.desc()).limit(limit).all()

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Get a product by ID."""
        session = self.get_session()
        return session.query(Product).get(product_id)

    def compare_runs(self, run_id_1: int, run_id_2: int) -> dict:
        """Compare two discovery runs."""
        session = self.get_session()

        # Get snapshots for both runs
        snapshots_1 = {
            s.product.normalized_name: s
            for s in session.query(ProductSnapshot).filter(
                ProductSnapshot.discovery_run_id == run_id_1
            ).all()
        }
        snapshots_2 = {
            s.product.normalized_name: s
            for s in session.query(ProductSnapshot).filter(
                ProductSnapshot.discovery_run_id == run_id_2
            ).all()
        }

        names_1 = set(snapshots_1.keys())
        names_2 = set(snapshots_2.keys())

        # Find new, recurring, dropped
        new_names = names_2 - names_1
        dropped_names = names_1 - names_2
        recurring_names = names_1 & names_2

        # Build results
        new_products = [
            {
                'name': snapshots_2[n].product.name,
                'score': snapshots_2[n].opportunity_score,
                'product_id': snapshots_2[n].product_id
            }
            for n in new_names
        ]

        dropped_products = [
            {
                'name': snapshots_1[n].product.name,
                'score': snapshots_1[n].opportunity_score,
                'product_id': snapshots_1[n].product_id
            }
            for n in dropped_names
        ]

        recurring_products = [
            {
                'name': snapshots_2[n].product.name,
                'score_old': snapshots_1[n].opportunity_score,
                'score_new': snapshots_2[n].opportunity_score,
                'score_change': snapshots_2[n].opportunity_score - snapshots_1[n].opportunity_score,
                'product_id': snapshots_2[n].product_id
            }
            for n in recurring_names
        ]

        # Sort by score/change
        new_products.sort(key=lambda x: x['score'], reverse=True)
        dropped_products.sort(key=lambda x: x['score'], reverse=True)
        recurring_products.sort(key=lambda x: x['score_change'], reverse=True)

        return {
            'new_products': new_products,
            'dropped_products': dropped_products,
            'recurring_products': recurring_products,
            'summary': {
                'new_count': len(new_products),
                'dropped_count': len(dropped_products),
                'recurring_count': len(recurring_products)
            }
        }

    def get_recurring_products(self, min_appearances: int = 3, days: int = 30) -> List[Product]:
        """Get products that appear frequently (good signals)."""
        session = self.get_session()
        cutoff = datetime.utcnow() - timedelta(days=days)

        return session.query(Product).filter(
            Product.times_seen >= min_appearances,
            Product.last_seen >= cutoff
        ).order_by(Product.times_seen.desc()).all()

    def get_all_products(self, limit: int = 100) -> List[Product]:
        """Get all tracked products."""
        session = self.get_session()
        return session.query(Product).filter(
            Product.times_seen > 0
        ).order_by(Product.times_seen.desc()).limit(limit).all()
