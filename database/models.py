"""
Database models for storing scraped data and analysis results.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Product(Base):
    """Tracked products/items mentioned across platforms."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), index=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_mentions = Column(Integer, default=0)
    avg_sentiment = Column(Float, default=0.0)
    opportunity_score = Column(Float, default=0.0)

    mentions = relationship("Mention", back_populates="product")

    def __repr__(self):
        return f"<Product(name='{self.name}', score={self.opportunity_score:.2f})>"


class Mention(Base):
    """Individual mentions of products in posts/comments."""
    __tablename__ = "mentions"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    source = Column(String(50))  # reddit, amazon, etc.
    platform_id = Column(String(100))  # Original post/comment ID
    subreddit = Column(String(100), index=True)
    title = Column(Text)
    content = Column(Text)
    url = Column(String(500))
    author = Column(String(100))
    upvotes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    sentiment_score = Column(Float)
    sentiment_label = Column(String(20))  # positive, negative, neutral
    is_post = Column(Boolean, default=True)  # True for post, False for comment
    created_at = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="mentions")

    def __repr__(self):
        return f"<Mention(source='{self.source}', sentiment={self.sentiment_label})>"


class ScrapingLog(Base):
    """Log of scraping sessions for tracking and debugging."""
    __tablename__ = "scraping_logs"

    id = Column(Integer, primary_key=True)
    source = Column(String(50))
    subreddit = Column(String(100))
    posts_scraped = Column(Integer, default=0)
    comments_scraped = Column(Integer, default=0)
    products_found = Column(Integer, default=0)
    errors = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    def __repr__(self):
        return f"<ScrapingLog(source='{self.source}', posts={self.posts_scraped})>"


class TrendSnapshot(Base):
    """Daily snapshots for tracking trends over time."""
    __tablename__ = "trend_snapshots"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    daily_mentions = Column(Integer, default=0)
    daily_sentiment = Column(Float)
    trending_score = Column(Float)  # Calculated based on growth

    def __repr__(self):
        return f"<TrendSnapshot(date='{self.date}', mentions={self.daily_mentions})>"
