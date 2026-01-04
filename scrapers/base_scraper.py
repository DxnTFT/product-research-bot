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

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.ua = UserAgent()
        self.session_count = 0

    def get_headers(self) -> Dict[str, str]:
        """Get randomized headers to avoid detection."""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def rate_limit(self):
        """Apply rate limiting between requests."""
        # Add some randomness to avoid patterns
        sleep_time = self.delay + random.uniform(0.5, 1.5)
        time.sleep(sleep_time)
        self.session_count += 1

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
