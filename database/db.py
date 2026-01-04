"""
Database operations and session management.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime, timedelta
from typing import Optional, List

from .models import Base, Product, Mention, ScrapingLog, TrendSnapshot


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
