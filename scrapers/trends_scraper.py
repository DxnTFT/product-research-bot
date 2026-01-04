"""
Google Trends integration for validating product interest.
Uses pytrends library for free access to Google Trends data.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time


class TrendsScraper:
    """
    Check Google Trends data for products.
    Validates if a product has rising search interest.
    """

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.pytrends = None
        self._init_pytrends()

    def _init_pytrends(self):
        """Initialize pytrends connection."""
        try:
            from pytrends.request import TrendReq
            self.pytrends = TrendReq(hl='en-US', tz=360)
        except ImportError:
            print("pytrends not installed. Run: pip install pytrends")
            self.pytrends = None

    def check_trend(self, keyword: str, timeframe: str = "today 3-m") -> Dict[str, Any]:
        """
        Check Google Trends for a keyword.

        Args:
            keyword: Product name or search term
            timeframe: Time range (e.g., "today 3-m", "today 12-m")

        Returns:
            Dictionary with trend data
        """
        if not self.pytrends:
            return {"error": "pytrends not available", "keyword": keyword}

        try:
            time.sleep(self.delay)  # Rate limiting

            # Build payload
            self.pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo='US')

            # Get interest over time
            interest_df = self.pytrends.interest_over_time()

            if interest_df.empty:
                return {
                    "keyword": keyword,
                    "trend_score": 0,
                    "trend_direction": "unknown",
                    "avg_interest": 0,
                    "recent_interest": 0,
                    "data_points": 0,
                }

            # Calculate trend metrics
            values = interest_df[keyword].tolist()
            avg_interest = sum(values) / len(values)

            # Compare recent vs earlier period
            mid_point = len(values) // 2
            early_avg = sum(values[:mid_point]) / mid_point if mid_point > 0 else 0
            recent_avg = sum(values[mid_point:]) / (len(values) - mid_point) if len(values) > mid_point else 0

            # Determine trend direction
            if recent_avg > early_avg * 1.2:
                trend_direction = "rising"
                trend_score = min(100, int((recent_avg / max(early_avg, 1)) * 50))
            elif recent_avg < early_avg * 0.8:
                trend_direction = "falling"
                trend_score = max(0, int((recent_avg / max(early_avg, 1)) * 50))
            else:
                trend_direction = "stable"
                trend_score = 50

            return {
                "keyword": keyword,
                "trend_score": trend_score,
                "trend_direction": trend_direction,
                "avg_interest": round(avg_interest, 1),
                "recent_interest": round(recent_avg, 1),
                "early_interest": round(early_avg, 1),
                "data_points": len(values),
                "peak_interest": max(values),
                "checked_at": datetime.utcnow(),
            }

        except Exception as e:
            return {
                "keyword": keyword,
                "error": str(e),
                "trend_score": 0,
                "trend_direction": "unknown",
            }

    def check_multiple(self, keywords: List[str], timeframe: str = "today 3-m") -> List[Dict[str, Any]]:
        """
        Check trends for multiple keywords.

        Args:
            keywords: List of product names
            timeframe: Time range

        Returns:
            List of trend results
        """
        results = []

        for keyword in keywords:
            # Clean up keyword for better search
            clean_keyword = self._clean_keyword(keyword)
            if len(clean_keyword) < 3:
                continue

            print(f"    Checking trend: {clean_keyword[:30]}...", end=" ")
            result = self.check_trend(clean_keyword, timeframe)
            results.append(result)

            direction = result.get("trend_direction", "unknown")
            score = result.get("trend_score", 0)
            print(f"{direction} ({score})")

        return results

    def _clean_keyword(self, keyword: str) -> str:
        """Clean product name for Google Trends search."""
        # Remove common suffixes and clean up
        keyword = keyword.strip()

        # Remove size/color variations
        import re
        keyword = re.sub(r'\d+\s*(oz|ml|inch|pack|count|lb|kg)\b', '', keyword, flags=re.IGNORECASE)
        keyword = re.sub(r'\([^)]*\)', '', keyword)  # Remove parentheses content
        keyword = re.sub(r'\s+', ' ', keyword).strip()

        # Truncate to reasonable length for search
        words = keyword.split()[:5]  # Max 5 words
        return ' '.join(words)

    def get_related_queries(self, keyword: str) -> Dict[str, Any]:
        """
        Get related queries for a keyword.
        Useful for finding related products.

        Args:
            keyword: Search term

        Returns:
            Dictionary with related queries
        """
        if not self.pytrends:
            return {"error": "pytrends not available"}

        try:
            time.sleep(self.delay)

            self.pytrends.build_payload([keyword], cat=0, timeframe='today 3-m', geo='US')
            related = self.pytrends.related_queries()

            result = {
                "keyword": keyword,
                "rising": [],
                "top": [],
            }

            if keyword in related:
                # Rising queries (gaining popularity)
                rising_df = related[keyword].get("rising")
                if rising_df is not None and not rising_df.empty:
                    result["rising"] = rising_df.head(10).to_dict("records")

                # Top queries (most popular)
                top_df = related[keyword].get("top")
                if top_df is not None and not top_df.empty:
                    result["top"] = top_df.head(10).to_dict("records")

            return result

        except Exception as e:
            return {"keyword": keyword, "error": str(e)}

    def compare_products(self, products: List[str]) -> Dict[str, Any]:
        """
        Compare search interest between multiple products.

        Args:
            products: List of product names (max 5)

        Returns:
            Comparison data
        """
        if not self.pytrends:
            return {"error": "pytrends not available"}

        products = products[:5]  # Google Trends limit

        try:
            time.sleep(self.delay)

            clean_products = [self._clean_keyword(p) for p in products]
            self.pytrends.build_payload(clean_products, cat=0, timeframe='today 3-m', geo='US')

            interest_df = self.pytrends.interest_over_time()

            if interest_df.empty:
                return {"products": products, "comparison": "no data"}

            # Calculate average interest for each
            comparison = {}
            for product in clean_products:
                if product in interest_df.columns:
                    values = interest_df[product].tolist()
                    comparison[product] = {
                        "avg_interest": round(sum(values) / len(values), 1),
                        "peak_interest": max(values),
                        "recent": round(sum(values[-4:]) / 4, 1) if len(values) >= 4 else 0,
                    }

            # Rank by recent interest
            ranked = sorted(comparison.items(), key=lambda x: x[1]["recent"], reverse=True)

            return {
                "products": products,
                "comparison": comparison,
                "ranking": [p[0] for p in ranked],
            }

        except Exception as e:
            return {"products": products, "error": str(e)}
