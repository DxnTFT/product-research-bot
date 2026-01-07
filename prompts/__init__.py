"""
LLM Prompts Module

Optimized prompts for Claude API-powered analysis.
"""

from .analysis_prompts import (
    SENTIMENT_ANALYSIS_PROMPT,
    PRODUCT_EXTRACTION_PROMPT,
    OPPORTUNITY_SCORING_PROMPT,
    BATCH_SENTIMENT_PROMPT,
    PRODUCT_COMPARISON_PROMPT,
    format_sentiment_prompt,
    format_extraction_prompt,
    format_scoring_prompt,
    format_batch_sentiment_prompt,
)

__all__ = [
    "SENTIMENT_ANALYSIS_PROMPT",
    "PRODUCT_EXTRACTION_PROMPT",
    "OPPORTUNITY_SCORING_PROMPT",
    "BATCH_SENTIMENT_PROMPT",
    "PRODUCT_COMPARISON_PROMPT",
    "format_sentiment_prompt",
    "format_extraction_prompt",
    "format_scoring_prompt",
    "format_batch_sentiment_prompt",
]
