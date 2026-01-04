"""
Sentiment analysis module using VADER (optimized for social media).
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import Dict, Tuple
import re


class SentimentAnalyzer:
    """
    Analyze sentiment of text using VADER.
    VADER is specifically tuned for social media content.
    """

    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

        # Custom words relevant to product reviews
        self._add_custom_lexicon()

    def _add_custom_lexicon(self):
        """Add product-review specific words to VADER's lexicon."""
        custom_words = {
            # Positive product words
            "worth it": 2.5,
            "game changer": 3.0,
            "holy grail": 3.0,
            "must have": 2.5,
            "highly recommend": 3.0,
            "best purchase": 3.0,
            "exceeded expectations": 2.5,
            "well made": 2.0,
            "great quality": 2.5,
            "love it": 2.5,
            "perfect": 2.5,
            "durable": 1.5,
            "sturdy": 1.5,
            "reliable": 1.5,
            "bang for buck": 2.5,
            "value for money": 2.0,
            # Negative product words
            "waste of money": -3.0,
            "broke": -2.0,
            "cheaply made": -2.5,
            "fell apart": -2.5,
            "returned it": -2.0,
            "don't buy": -3.0,
            "avoid": -2.5,
            "scam": -3.5,
            "ripoff": -3.0,
            "rip off": -3.0,
            "overpriced": -2.0,
            "disappointing": -2.0,
            "flimsy": -2.0,
            "junk": -2.5,
            "garbage": -3.0,
            "buyer beware": -2.5,
        }

        for word, score in custom_words.items():
            self.analyzer.lexicon[word] = score

    def analyze(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment scores:
            - neg: Negative sentiment (0-1)
            - neu: Neutral sentiment (0-1)
            - pos: Positive sentiment (0-1)
            - compound: Overall sentiment (-1 to 1)
        """
        if not text:
            return {"neg": 0, "neu": 1, "pos": 0, "compound": 0}

        # Clean text
        text = self._preprocess(text)

        return self.analyzer.polarity_scores(text)

    def get_sentiment_label(self, text: str) -> Tuple[str, float]:
        """
        Get sentiment label and score.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (label, compound_score)
            Label is 'positive', 'negative', or 'neutral'
        """
        scores = self.analyze(text)
        compound = scores["compound"]

        # VADER recommended thresholds
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"

        return label, compound

    def _preprocess(self, text: str) -> str:
        """Preprocess text for better sentiment analysis."""
        # Convert to lowercase but preserve emoticons
        text = text.strip()

        # Remove URLs
        text = re.sub(r"http\S+|www\.\S+", "", text)

        # Remove Reddit-specific markdown
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # Links
        text = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", text)  # Bold/italic

        # Normalize whitespace
        text = " ".join(text.split())

        return text

    def analyze_batch(self, texts: list) -> list:
        """
        Analyze sentiment of multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            List of (label, score) tuples
        """
        return [self.get_sentiment_label(text) for text in texts]

    def get_summary_stats(self, texts: list) -> Dict[str, float]:
        """
        Get summary statistics for a batch of texts.

        Args:
            texts: List of texts to analyze

        Returns:
            Dictionary with summary stats
        """
        if not texts:
            return {
                "avg_compound": 0,
                "positive_pct": 0,
                "negative_pct": 0,
                "neutral_pct": 0,
                "total": 0
            }

        results = self.analyze_batch(texts)

        positive = sum(1 for label, _ in results if label == "positive")
        negative = sum(1 for label, _ in results if label == "negative")
        neutral = sum(1 for label, _ in results if label == "neutral")
        total = len(results)

        avg_compound = sum(score for _, score in results) / total

        return {
            "avg_compound": round(avg_compound, 3),
            "positive_pct": round(positive / total * 100, 1),
            "negative_pct": round(negative / total * 100, 1),
            "neutral_pct": round(neutral / total * 100, 1),
            "total": total
        }
