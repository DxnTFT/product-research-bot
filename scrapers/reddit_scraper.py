"""
Reddit scraper using Reddit's JSON API (more reliable than HTML scraping).
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from .base_scraper import BaseScraper


class RedditScraper(BaseScraper):
    """Scraper for Reddit using JSON API."""

    BASE_URL = "https://www.reddit.com"

    def __init__(self, delay: float = 2.0):
        super().__init__(delay)
        self.session = requests.Session()

    def get_headers(self) -> Dict[str, str]:
        """Reddit JSON API requires a proper User-Agent."""
        return {
            "User-Agent": "ProductResearchBot/1.0 (Educational Project)",
            "Accept": "application/json",
        }

    def scrape(self, subreddit: str, sort: str = "hot", limit: int = 25, **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape posts from a subreddit using JSON API.

        Args:
            subreddit: Name of the subreddit (without r/)
            sort: Sort method - hot, new, top, rising
            limit: Number of posts to fetch

        Returns:
            List of post dictionaries
        """
        posts = []
        url = f"{self.BASE_URL}/r/{subreddit}/{sort}.json"
        params = {"limit": min(limit, 100)}

        try:
            self.rate_limit()
            response = self.session.get(url, headers=self.get_headers(), params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            children = data.get("data", {}).get("children", [])

            for child in children[:limit]:
                post_data = child.get("data", {})
                parsed = self._parse_post(post_data, subreddit)
                if parsed:
                    posts.append(parsed)

        except requests.RequestException as e:
            print(f"Error scraping r/{subreddit}: {e}")
        except ValueError as e:
            print(f"Error parsing JSON from r/{subreddit}: {e}")

        return posts

    def _parse_post(self, post_data: dict, subreddit: str) -> Optional[Dict[str, Any]]:
        """Parse a post from JSON data."""
        try:
            post_id = post_data.get("id", "")
            title = post_data.get("title", "")
            selftext = post_data.get("selftext", "")
            score = post_data.get("score", 0)
            num_comments = post_data.get("num_comments", 0)
            author = post_data.get("author", "[deleted]")
            permalink = post_data.get("permalink", "")
            created_utc = post_data.get("created_utc", 0)

            created_at = datetime.utcfromtimestamp(created_utc) if created_utc else datetime.utcnow()

            return {
                "platform_id": post_id,
                "source": "reddit",
                "subreddit": subreddit,
                "title": self.clean_text(title),
                "content": self.clean_text(selftext),
                "url": f"{self.BASE_URL}{permalink}" if permalink else "",
                "author": author,
                "upvotes": score,
                "comments_count": num_comments,
                "created_at": created_at,
                "is_post": True,
            }

        except Exception as e:
            print(f"Error parsing post: {e}")
            return None

    def scrape_comments(self, subreddit: str, post_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape comments from a specific post using JSON API.

        Args:
            subreddit: Name of the subreddit
            post_id: The post ID
            limit: Number of comments to fetch

        Returns:
            List of comment dictionaries
        """
        comments = []
        url = f"{self.BASE_URL}/r/{subreddit}/comments/{post_id}.json"
        params = {"limit": limit, "depth": 1}

        try:
            self.rate_limit()
            response = self.session.get(url, headers=self.get_headers(), params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            # Comments are in the second element of the response array
            if len(data) > 1:
                comment_data = data[1].get("data", {}).get("children", [])
                for child in comment_data[:limit]:
                    if child.get("kind") == "t1":  # t1 = comment
                        comment = self._parse_comment(child.get("data", {}), subreddit, post_id)
                        if comment:
                            comments.append(comment)

        except requests.RequestException as e:
            print(f"Error scraping comments for post {post_id}: {e}")
        except (ValueError, IndexError) as e:
            print(f"Error parsing comments JSON: {e}")

        return comments

    def _parse_comment(self, comment_data: dict, subreddit: str, post_id: str) -> Optional[Dict[str, Any]]:
        """Parse a comment from JSON data."""
        try:
            comment_id = comment_data.get("id", "")
            body = comment_data.get("body", "")
            score = comment_data.get("score", 0)
            author = comment_data.get("author", "[deleted]")
            created_utc = comment_data.get("created_utc", 0)

            created_at = datetime.utcfromtimestamp(created_utc) if created_utc else datetime.utcnow()

            return {
                "platform_id": comment_id,
                "source": "reddit",
                "subreddit": subreddit,
                "title": f"Comment on post {post_id}",
                "content": self.clean_text(body),
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
        Uses pattern matching and known brand detection.

        Args:
            content: Text content to analyze

        Returns:
            List of potential product names
        """
        products = []

        if not content:
            return products

        content_lower = content.lower()

        # Known brands/products to look for (expandable)
        known_brands = [
            # Fitness
            "rogue", "rep fitness", "titan", "bowflex", "peloton", "nordictrack",
            "garmin", "fitbit", "whoop", "apple watch", "nike", "adidas", "under armour",
            "lululemon", "gymshark", "reebok", "asics", "hoka", "brooks", "saucony",
            "concept2", "assault bike", "echo bike", "schwinn", "sole", "proform",
            "powerblock", "ironmaster", "adjustable dumbbells", "kettlebell", "barbell",
            "squat rack", "power rack", "pull up bar", "resistance bands", "foam roller",
            "theragun", "hypervolt", "massage gun", "yoga mat", "jump rope",
            # Kitchen
            "instant pot", "ninja", "cuisinart", "kitchenaid", "vitamix", "nutribullet",
            "air fryer", "cast iron", "lodge", "le creuset", "staub", "all-clad",
            "oxo", "pyrex", "corelle", "tupperware", "yeti", "hydroflask", "stanley",
            "keurig", "nespresso", "breville", "chemex", "aeropress",
            # Home
            "roomba", "dyson", "shark", "bissell", "eufy", "ecovacs", "roborock",
            "ring", "nest", "arlo", "wyze", "blink", "simplisafe",
            "casper", "purple", "tuft and needle", "nectar", "saatva",
            "ikea", "wayfair", "article", "west elm",
            # Tech/Gadgets
            "anker", "aukey", "belkin", "logitech", "razer", "steelseries",
            "bose", "sony", "sennheiser", "airpods", "jabra", "soundcore",
        ]

        # Check for known brands
        for brand in known_brands:
            if brand in content_lower:
                # Try to get more context (brand + model)
                pattern = rf"({re.escape(brand)}[\w\s\-]*?)(?:\.|,|\s+is|\s+are|\s+was|\s+for|\s+and|$)"
                matches = re.findall(pattern, content_lower, re.IGNORECASE)
                if matches:
                    for match in matches:
                        cleaned = match.strip().strip(".,").title()
                        if 3 < len(cleaned) < 50:
                            products.append(cleaned)
                else:
                    products.append(brand.title())

        # Pattern for "bought/got/recommend X" with product-like structure
        action_patterns = [
            r"(?:bought|got|purchased|recommend|love my|use|using)\s+(?:a|an|the|my)?\s*([A-Z][a-zA-Z0-9]+(?:\s+[A-Z]?[a-zA-Z0-9]+){0,3})",
        ]

        for pattern in action_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                cleaned = match.strip()
                # Filter out obvious non-products
                skip_words = [
                    "the", "this", "that", "these", "those", "i", "we", "you", "they",
                    "it", "my", "your", "new", "old", "good", "bad", "great", "lot",
                    "few", "some", "any", "all", "one", "two", "year", "month", "day",
                    "week", "time", "way", "thing", "stuff", "person", "people",
                    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep",
                    "oct", "nov", "dec", "monday", "tuesday", "wednesday", "thursday",
                    "friday", "saturday", "sunday", "http", "www", "reddit", "comment"
                ]
                if cleaned.lower() not in skip_words and 3 < len(cleaned) < 40:
                    # Check it looks like a product (has some structure)
                    if re.match(r'^[A-Z]', cleaned):
                        products.append(cleaned)

        # Deduplicate while preserving order
        seen = set()
        unique_products = []
        for p in products:
            p_lower = p.lower()
            if p_lower not in seen:
                seen.add(p_lower)
                unique_products.append(p)

        return unique_products

    def search_subreddit(self, subreddit: str, query: str, limit: int = 25, sort: str = "relevance", time_filter: str = "year") -> List[Dict[str, Any]]:
        """
        Search within a subreddit for specific terms using JSON API.

        Args:
            subreddit: Name of the subreddit
            query: Search query (product name)
            limit: Number of results
            sort: Sort by (relevance, hot, top, new, comments)
            time_filter: Time range (hour, day, week, month, year, all)

        Returns:
            List of matching posts
        """
        posts = []
        url = f"{self.BASE_URL}/r/{subreddit}/search.json"
        params = {
            "q": query,
            "restrict_sr": "on",
            "sort": sort,
            "t": time_filter,
            "limit": min(limit, 100),
        }

        try:
            self.rate_limit()
            response = self.session.get(url, headers=self.get_headers(), params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            children = data.get("data", {}).get("children", [])

            for child in children[:limit]:
                post_data = child.get("data", {})
                parsed = self._parse_post(post_data, subreddit)
                if parsed:
                    parsed["search_query"] = query
                    posts.append(parsed)

        except requests.RequestException as e:
            print(f"Error searching r/{subreddit}: {e}")
        except ValueError as e:
            print(f"Error parsing search JSON: {e}")

        return posts

    def search_product(self, product_name: str, subreddits: List[str] = None, limit_per_sub: int = 10) -> List[Dict[str, Any]]:
        """
        Search for a product across multiple relevant subreddits.

        Args:
            product_name: Product name to search for
            subreddits: List of subreddits to search (default: product review subs)
            limit_per_sub: Results per subreddit

        Returns:
            List of all matching posts with sentiment-relevant content
        """
        if subreddits is None:
            # Default subreddits for product discussions
            subreddits = [
                "BuyItForLife",
                "Fitness",
                "homegym",
                "Cooking",
                "Kitchen",
                "HomeImprovement",
                "frugal",
                "gadgets",
            ]

        all_results = []

        for subreddit in subreddits:
            results = self.search_subreddit(subreddit, product_name, limit=limit_per_sub)
            all_results.extend(results)

        return all_results

    def search_all_reddit(self, query: str, limit: int = 50, sort: str = "relevance") -> List[Dict[str, Any]]:
        """
        Search across all of Reddit for a product.

        Args:
            query: Search query
            limit: Number of results
            sort: Sort method

        Returns:
            List of matching posts from any subreddit
        """
        posts = []
        url = f"{self.BASE_URL}/search.json"
        params = {
            "q": query,
            "sort": sort,
            "t": "year",
            "limit": min(limit, 100),
        }

        try:
            self.rate_limit()
            response = self.session.get(url, headers=self.get_headers(), params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            children = data.get("data", {}).get("children", [])

            for child in children[:limit]:
                post_data = child.get("data", {})
                subreddit = post_data.get("subreddit", "")
                parsed = self._parse_post(post_data, subreddit)
                if parsed:
                    parsed["search_query"] = query
                    posts.append(parsed)

        except requests.RequestException as e:
            print(f"Error searching Reddit: {e}")
        except ValueError as e:
            print(f"Error parsing search JSON: {e}")

        return posts
