"""
Reddit scraper using old.reddit.com for easier parsing.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from .base_scraper import BaseScraper


class RedditScraper(BaseScraper):
    """Scraper for Reddit using old.reddit.com interface."""

    BASE_URL = "https://old.reddit.com"

    def __init__(self, delay: float = 2.0):
        super().__init__(delay)
        self.session = requests.Session()

    def scrape(self, subreddit: str, sort: str = "hot", limit: int = 25, **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape posts from a subreddit.

        Args:
            subreddit: Name of the subreddit (without r/)
            sort: Sort method - hot, new, top, rising
            limit: Number of posts to fetch

        Returns:
            List of post dictionaries
        """
        posts = []
        url = f"{self.BASE_URL}/r/{subreddit}/{sort}"

        try:
            self.rate_limit()
            response = self.session.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            post_elements = soup.find_all("div", class_="thing", attrs={"data-fullname": True})

            for post_el in post_elements[:limit]:
                post_data = self._parse_post(post_el, subreddit)
                if post_data:
                    posts.append(post_data)

        except requests.RequestException as e:
            print(f"Error scraping r/{subreddit}: {e}")

        return posts

    def _parse_post(self, post_element, subreddit: str) -> Optional[Dict[str, Any]]:
        """Parse a single post element."""
        try:
            # Get post ID
            post_id = post_element.get("data-fullname", "").replace("t3_", "")

            # Get title
            title_el = post_element.find("a", class_="title")
            title = title_el.get_text(strip=True) if title_el else ""

            # Get URL
            url = title_el.get("href", "") if title_el else ""
            if url.startswith("/"):
                url = f"{self.BASE_URL}{url}"

            # Get score (upvotes)
            score_el = post_element.find("div", class_="score")
            score_text = score_el.get("title", "0") if score_el else "0"
            try:
                score = int(score_text)
            except ValueError:
                score = 0

            # Get comment count
            comments_el = post_element.find("a", class_="comments")
            comments_text = comments_el.get_text(strip=True) if comments_el else "0"
            comments_match = re.search(r"(\d+)", comments_text)
            comments_count = int(comments_match.group(1)) if comments_match else 0

            # Get author
            author_el = post_element.find("a", class_="author")
            author = author_el.get_text(strip=True) if author_el else "[deleted]"

            # Get post time
            time_el = post_element.find("time")
            created_at = None
            if time_el and time_el.get("datetime"):
                try:
                    created_at = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
                except ValueError:
                    created_at = datetime.utcnow()

            # Get selftext preview if available
            selftext = ""
            expando = post_element.find("div", class_="expando")
            if expando:
                selftext_el = expando.find("div", class_="md")
                if selftext_el:
                    selftext = self.clean_text(selftext_el.get_text())

            return {
                "platform_id": post_id,
                "source": "reddit",
                "subreddit": subreddit,
                "title": self.clean_text(title),
                "content": selftext,
                "url": url,
                "author": author,
                "upvotes": score,
                "comments_count": comments_count,
                "created_at": created_at,
                "is_post": True,
            }

        except Exception as e:
            print(f"Error parsing post: {e}")
            return None

    def scrape_comments(self, subreddit: str, post_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape comments from a specific post.

        Args:
            subreddit: Name of the subreddit
            post_id: The post ID
            limit: Number of comments to fetch

        Returns:
            List of comment dictionaries
        """
        comments = []
        url = f"{self.BASE_URL}/r/{subreddit}/comments/{post_id}"

        try:
            self.rate_limit()
            response = self.session.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find comment area
            comment_area = soup.find("div", class_="commentarea")
            if not comment_area:
                return comments

            comment_elements = comment_area.find_all("div", class_="comment", attrs={"data-fullname": True})

            for comment_el in comment_elements[:limit]:
                comment_data = self._parse_comment(comment_el, subreddit, post_id)
                if comment_data:
                    comments.append(comment_data)

        except requests.RequestException as e:
            print(f"Error scraping comments for post {post_id}: {e}")

        return comments

    def _parse_comment(self, comment_element, subreddit: str, post_id: str) -> Optional[Dict[str, Any]]:
        """Parse a single comment element."""
        try:
            # Get comment ID
            comment_id = comment_element.get("data-fullname", "").replace("t1_", "")

            # Get author
            author_el = comment_element.find("a", class_="author")
            author = author_el.get_text(strip=True) if author_el else "[deleted]"

            # Get content
            content_el = comment_element.find("div", class_="md")
            content = self.clean_text(content_el.get_text()) if content_el else ""

            # Get score
            score_el = comment_element.find("span", class_="score")
            score_text = score_el.get("title", "1") if score_el else "1"
            try:
                score = int(score_text.split()[0])
            except (ValueError, IndexError):
                score = 1

            # Get time
            time_el = comment_element.find("time")
            created_at = None
            if time_el and time_el.get("datetime"):
                try:
                    created_at = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
                except ValueError:
                    created_at = datetime.utcnow()

            return {
                "platform_id": comment_id,
                "source": "reddit",
                "subreddit": subreddit,
                "title": f"Comment on post {post_id}",
                "content": content,
                "url": f"{self.BASE_URL}/r/{subreddit}/comments/{post_id}/_/{comment_id}",
                "author": author,
                "upvotes": score,
                "comments_count": 0,
                "created_at": created_at,
                "is_post": False,
            }

        except Exception as e:
            print(f"Error parsing comment: {e}")
            return None

    def extract_products(self, content: str) -> List[str]:
        """
        Extract potential product names from content.
        Uses pattern matching to find product mentions.

        Args:
            content: Text content to analyze

        Returns:
            List of potential product names
        """
        products = []

        if not content:
            return products

        # Patterns that often indicate product names
        patterns = [
            # "I bought/got/use [Product]"
            r"(?:bought|got|purchased|ordered|received|use|using|tried|recommend)\s+(?:a|an|the|my)?\s*([A-Z][A-Za-z0-9\s\-]+)",
            # "[Product] is/was amazing/great"
            r"([A-Z][A-Za-z0-9\s\-]+)\s+(?:is|was|are|were)\s+(?:amazing|great|awesome|excellent|perfect|terrible|garbage)",
            # "the [Product] from [Brand]"
            r"the\s+([A-Z][A-Za-z0-9\s\-]+)\s+from\s+[A-Z]",
            # Brand names followed by product
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+[A-Z0-9][A-Za-z0-9\s\-]*)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Clean up the match
                product = match.strip()
                # Filter out common false positives
                if len(product) > 3 and len(product) < 50:
                    if not any(word in product.lower() for word in ["http", "www", "reddit", "subreddit"]):
                        products.append(product)

        return list(set(products))  # Remove duplicates

    def search_subreddit(self, subreddit: str, query: str, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Search within a subreddit for specific terms.

        Args:
            subreddit: Name of the subreddit
            query: Search query
            limit: Number of results

        Returns:
            List of matching posts
        """
        posts = []
        url = f"{self.BASE_URL}/r/{subreddit}/search"
        params = {
            "q": query,
            "restrict_sr": "on",
            "sort": "relevance",
            "t": "all"
        }

        try:
            self.rate_limit()
            response = self.session.get(url, params=params, headers=self.get_headers(), timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            post_elements = soup.find_all("div", class_="thing", attrs={"data-fullname": True})

            for post_el in post_elements[:limit]:
                post_data = self._parse_post(post_el, subreddit)
                if post_data:
                    posts.append(post_data)

        except requests.RequestException as e:
            print(f"Error searching r/{subreddit}: {e}")

        return posts
