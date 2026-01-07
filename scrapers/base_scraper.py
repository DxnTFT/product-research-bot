"""
Base scraper class that all platform-specific scrapers inherit from.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import time
import random
from fake_useragent import UserAgent


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    def __init__(self, delay: float = 25.0):  # Increased from 2.0 to 25.0
        self.delay = delay
        self.session_count = 0

        # Initialize stealth and rate limiting components
        try:
            from .stealth_config import UserAgentRotator, HeaderGenerator
            from .rate_limiter import RateLimiter

            self.ua_rotator = UserAgentRotator()
            self.header_gen = HeaderGenerator()
            self.rate_limiter = RateLimiter(base_delay=delay)
        except ImportError:
            # Fallback if new modules not available yet
            self.ua_rotator = None
            self.ua = UserAgent()
            self.header_gen = None
            self.rate_limiter = None

    def get_headers(self) -> Dict[str, str]:
        """Get randomized headers to avoid detection."""
        if self.ua_rotator and self.header_gen:
            # Use new header generator
            ua = self.ua_rotator.get_next()
            return self.header_gen.get_realistic_headers(ua)
        else:
            # Fallback to simple headers
            return {
                "User-Agent": self.ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

    def rate_limit(self):
        """Apply rate limiting between requests with jitter."""
        # Add jitter to avoid patterns
        jitter = random.uniform(-2.0, 2.0)
        sleep_time = max(15.0, self.delay + jitter)  # Minimum 15 seconds
        time.sleep(sleep_time)
        self.session_count += 1

        # Log every 10 requests for monitoring
        if self.session_count % 10 == 0:
            print(f"    [{self.session_count} requests completed]")

    @abstractmethod
    def scrape(self, target: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Main scraping method to be implemented by subclasses.

        Args:
            target: The target to scrape (e.g., subreddit name, URL)
            **kwargs: Additional scraping parameters

        Returns:
            List of scraped items as dictionaries
        """
        pass

    @abstractmethod
    def extract_products(self, content: str) -> List[str]:
        """
        Extract product names/mentions from content.

        Args:
            content: The text content to analyze

        Returns:
            List of product names found
        """
        pass

    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        # Remove extra whitespace
        text = " ".join(text.split())
        # Remove common Reddit artifacts
        text = text.replace("&#x200B;", "")  # Zero-width space
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        return text.strip()
