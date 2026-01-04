"""
Product opportunity scoring system.
Calculates a score based on multiple factors to identify promising products.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import math

from config.settings import SCORING_WEIGHTS, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS


class ProductScorer:
    """
    Score products based on their opportunity potential.
    Higher scores = better opportunity.
    """

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or SCORING_WEIGHTS

    def calculate_score(self, product_data: Dict) -> float:
        """
        Calculate opportunity score for a product.

        Args:
            product_data: Dictionary containing:
                - mentions: List of mention dictionaries
                - avg_sentiment: Average sentiment score
                - total_mentions: Total mention count

        Returns:
            Opportunity score (0-100)
        """
        mentions = product_data.get("mentions", [])

        if not mentions:
            return 0.0

        # Calculate individual scores
        mention_score = self._score_mention_frequency(mentions)
        sentiment_score = self._score_sentiment(product_data.get("avg_sentiment", 0))
        engagement_score = self._score_engagement(mentions)
        recency_score = self._score_recency(mentions)
        intent_score = self._score_purchase_intent(mentions)

        # Weighted combination
        total_score = (
            self.weights["mention_frequency"] * mention_score +
            self.weights["sentiment_score"] * sentiment_score +
            self.weights["engagement"] * engagement_score +
            self.weights["recency"] * recency_score +
            self.weights["purchase_intent"] * intent_score
        )

        # Normalize to 0-100
        return round(min(100, max(0, total_score * 100)), 2)

    def _score_mention_frequency(self, mentions: List[Dict]) -> float:
        """
        Score based on how often the product is mentioned.
        Uses logarithmic scaling to prevent runaway scores.
        """
        count = len(mentions)
        if count == 0:
            return 0.0

        # Log scale: 1 mention = 0.3, 10 mentions = 0.7, 100 mentions = 1.0
        return min(1.0, math.log10(count + 1) / 2)

    def _score_sentiment(self, avg_sentiment: float) -> float:
        """
        Score based on average sentiment.
        Sentiment ranges from -1 to 1, we convert to 0-1.
        """
        # Convert -1 to 1 range to 0 to 1
        return (avg_sentiment + 1) / 2

    def _score_engagement(self, mentions: List[Dict]) -> float:
        """
        Score based on upvotes and comments.
        High engagement = more interest.
        """
        if not mentions:
            return 0.0

        total_upvotes = sum(m.get("upvotes", 0) for m in mentions)
        total_comments = sum(m.get("comments_count", 0) for m in mentions)

        # Weighted engagement (comments worth more than upvotes)
        engagement = total_upvotes + (total_comments * 3)

        # Log scale normalization
        return min(1.0, math.log10(engagement + 1) / 4)

    def _score_recency(self, mentions: List[Dict]) -> float:
        """
        Score based on how recent the mentions are.
        More recent = higher score.
        """
        if not mentions:
            return 0.0

        now = datetime.utcnow()
        recency_scores = []

        for mention in mentions:
            created_at = mention.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at)
                    except ValueError:
                        continue

                days_old = (now - created_at).days
                # Decay: 0 days = 1.0, 30 days = 0.5, 90 days = 0.1
                score = math.exp(-days_old / 30)
                recency_scores.append(score)

        if not recency_scores:
            return 0.5  # Default if no dates

        return sum(recency_scores) / len(recency_scores)

    def _score_purchase_intent(self, mentions: List[Dict]) -> float:
        """
        Score based on purchase intent keywords.
        Looking for "should I buy", "recommend", "worth it", etc.
        """
        if not mentions:
            return 0.0

        intent_keywords = [
            "buy", "purchase", "recommend", "worth", "should i",
            "looking for", "need", "want", "best", "alternative"
        ]

        intent_count = 0
        negative_count = 0

        for mention in mentions:
            content = (mention.get("content", "") + " " + mention.get("title", "")).lower()

            # Check for purchase intent
            if any(kw in content for kw in intent_keywords):
                intent_count += 1

            # Check for warning signs
            if any(kw in content for kw in ["don't buy", "avoid", "scam", "waste"]):
                negative_count += 1

        if not mentions:
            return 0.0

        # Positive intent minus negative warnings
        intent_ratio = (intent_count - negative_count * 2) / len(mentions)
        return max(0, min(1, (intent_ratio + 0.5)))  # Normalize to 0-1

    def rank_products(self, products: List[Dict]) -> List[Dict]:
        """
        Rank multiple products by their opportunity score.

        Args:
            products: List of product data dictionaries

        Returns:
            Sorted list with scores added
        """
        scored_products = []

        for product in products:
            score = self.calculate_score(product)
            product["opportunity_score"] = score
            scored_products.append(product)

        # Sort by score descending
        return sorted(scored_products, key=lambda x: x["opportunity_score"], reverse=True)

    def get_score_breakdown(self, product_data: Dict) -> Dict[str, float]:
        """
        Get detailed breakdown of score components.
        Useful for understanding why a product scored high/low.
        """
        mentions = product_data.get("mentions", [])

        return {
            "mention_frequency": round(self._score_mention_frequency(mentions) * 100, 1),
            "sentiment": round(self._score_sentiment(product_data.get("avg_sentiment", 0)) * 100, 1),
            "engagement": round(self._score_engagement(mentions) * 100, 1),
            "recency": round(self._score_recency(mentions) * 100, 1),
            "purchase_intent": round(self._score_purchase_intent(mentions) * 100, 1),
        }
