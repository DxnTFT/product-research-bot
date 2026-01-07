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
    normalized_name = Column(String(255), index=True, unique=True)  # For matching across runs
    category = Column(String(100), index=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_mentions = Column(Integer, default=0)
    avg_sentiment = Column(Float, default=0.0)
    opportunity_score = Column(Float, default=0.0)

    # Tracking fields for historical analysis
    times_seen = Column(Integer, default=1)  # How many discovery runs it appeared in
    highest_score = Column(Float, default=0.0)
    lowest_score = Column(Float, default=100.0)

    mentions = relationship("Mention", back_populates="product")
    snapshots = relationship("ProductSnapshot", back_populates="product")

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


class DiscoveryRun(Base):
    """Track each discovery session for historical comparison."""
    __tablename__ = "discovery_runs"

    id = Column(Integer, primary_key=True)
    run_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    mode = Column(String(50))  # "discover", "custom_keywords", "manual", "amazon_trending"
    categories = Column(Text)  # JSON list of categories used
    settings = Column(Text)  # JSON of settings (max_products, niche_types, etc.)
    products_found = Column(Integer, default=0)
    avg_score = Column(Float, default=0.0)
    duration_seconds = Column(Integer)  # How long the run took

    # Relationship to products found in this run
    snapshots = relationship("ProductSnapshot", back_populates="discovery_run")

    def __repr__(self):
        return f"<DiscoveryRun(id={self.id}, timestamp='{self.run_timestamp}', products={self.products_found})>"


class ProductSnapshot(Base):
    """Snapshot of product state at each discovery run."""
    __tablename__ = "product_snapshots"

    id = Column(Integer, primary_key=True)
    discovery_run_id = Column(Integer, ForeignKey("discovery_runs.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)

    # Snapshot data (captured at this point in time)
    opportunity_score = Column(Float)
    reddit_sentiment = Column(Float)
    sentiment_ratio = Column(Float)
    reddit_posts = Column(Integer)
    amazon_review_count = Column(Integer)
    price = Column(String(50))
    niche_type = Column(String(50))
    trend_direction = Column(String(20))
    combined_sentiment = Column(Float)

    # Relationships
    discovery_run = relationship("DiscoveryRun", back_populates="snapshots")
    product = relationship("Product", back_populates="snapshots")

    def __repr__(self):
        return f"<ProductSnapshot(product_id={self.product_id}, score={self.opportunity_score})>"
