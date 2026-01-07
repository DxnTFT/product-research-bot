"""
LLM Analysis Prompts for Product Research Bot

Optimized using recursive meta-prompt framework.
Each prompt follows: ROLE → CONTEXT → INSTRUCTIONS → OUTPUT FORMAT → CONSTRAINTS
"""

# =============================================================================
# SENTIMENT ANALYSIS PROMPT
# =============================================================================

SENTIMENT_ANALYSIS_PROMPT = """
**ROLE**
You are a sentiment classifier for e-commerce product discussions.

**CONTEXT**
- Input: Reddit post or comment about a product
- Task: Classify sentiment and extract purchase signals
- Domain: Consumer product discussions

**INSTRUCTIONS**
1. Read the text.
2. Identify sentiment polarity: POSITIVE, NEGATIVE, or NEUTRAL.
3. Calculate confidence score: 0.0 to 1.0.
4. Extract purchase intent signals if present.
5. Identify specific praise or complaints.

**INPUT**
Product: {product_name}
Text: {text}

**OUTPUT FORMAT**
Return JSON only:
{{
    "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
    "confidence": 0.0-1.0,
    "score": -1.0 to 1.0,
    "purchase_intent": true | false,
    "key_points": ["point1", "point2"],
    "reasoning": "one sentence"
}}

**CONSTRAINTS**
- Output JSON only. No other text.
- Score: -1.0 (negative) to 1.0 (positive)
- Confidence: how certain you are in classification
- Max 3 key points
"""

# =============================================================================
# PRODUCT EXTRACTION PROMPT
# =============================================================================

PRODUCT_EXTRACTION_PROMPT = """
**ROLE**
You are a product mention extractor for e-commerce research.

**CONTEXT**
- Input: Reddit post discussing products
- Task: Extract specific product names, brands, and categories
- Purpose: Identify products being discussed, recommended, or criticized

**INSTRUCTIONS**
1. Scan text for product mentions.
2. Distinguish between:
   - Specific products (brand + model): "Ninja AF101 Air Fryer"
   - Brand mentions: "Ninja"
   - Category mentions: "air fryer"
3. Identify context: recommendation, complaint, question, comparison.
4. Extract price mentions if present.

**INPUT**
Text: {text}
Subreddit: {subreddit}

**OUTPUT FORMAT**
Return JSON only:
{{
    "products": [
        {{
            "name": "full product name",
            "brand": "brand name or null",
            "category": "product category",
            "context": "recommendation" | "complaint" | "question" | "comparison" | "mention",
            "sentiment": "positive" | "negative" | "neutral",
            "price_mentioned": "$XX.XX or null"
        }}
    ],
    "product_count": integer
}}

**CONSTRAINTS**
- Output JSON only.
- Extract maximum 5 products per post.
- Use null for unknown fields, not empty strings.
- Category must be a generic term (e.g., "air fryer" not "Ninja AF101").
"""

# =============================================================================
# OPPORTUNITY SCORING PROMPT
# =============================================================================

OPPORTUNITY_SCORING_PROMPT = """
**ROLE**
You are an e-commerce opportunity analyst.

**CONTEXT**
- Input: Product data with market metrics
- Task: Score opportunity from 0-100
- Purpose: Identify high-potential products for e-commerce sellers

**SCORING FACTORS**
1. Competition (25 pts max): Fewer reviews = less saturated
   - 0-50 reviews: 25 pts
   - 51-200: 20 pts
   - 201-1000: 15 pts
   - 1001-5000: 10 pts
   - 5000+: 5 pts

2. Sentiment (25 pts max): Positive sentiment = demand signal
   - Convert -1 to +1 range to 0-25 pts

3. Trend (25 pts max): Rising trends = growing demand
   - Rising: 25 pts
   - Stable: 15 pts
   - Falling: 5 pts

4. Discussion Volume (25 pts max): More discussion = validated interest
   - 50+ posts: 25 pts
   - 20-49: 20 pts
   - 10-19: 15 pts
   - 5-9: 10 pts
   - 1-4: 5 pts

**INPUT**
{{
    "product_name": "{product_name}",
    "amazon_reviews": {amazon_reviews},
    "amazon_rating": {amazon_rating},
    "reddit_posts": {reddit_posts},
    "reddit_sentiment": {reddit_sentiment},
    "trend_direction": "{trend_direction}",
    "price": "{price}"
}}

**OUTPUT FORMAT**
Return JSON only:
{{
    "opportunity_score": 0-100,
    "competition_score": 0-25,
    "sentiment_score": 0-25,
    "trend_score": 0-25,
    "volume_score": 0-25,
    "recommendation": "HIGH_OPPORTUNITY" | "MODERATE" | "LOW_OPPORTUNITY" | "AVOID",
    "reasoning": "2-3 sentences explaining the score",
    "risks": ["risk1", "risk2"],
    "advantages": ["advantage1", "advantage2"]
}}

**CONSTRAINTS**
- Output JSON only.
- opportunity_score = competition_score + sentiment_score + trend_score + volume_score
- Maximum 3 risks and 3 advantages.
- Recommendation thresholds: HIGH ≥70, MODERATE 50-69, LOW 25-49, AVOID <25
"""

# =============================================================================
# BATCH ANALYSIS PROMPT (for efficiency)
# =============================================================================

BATCH_SENTIMENT_PROMPT = """
**ROLE**
You are a batch sentiment classifier for product discussions.

**CONTEXT**
- Input: Multiple Reddit posts about a product
- Task: Analyze all posts, return aggregate sentiment

**INSTRUCTIONS**
1. Analyze each post individually.
2. Weight by upvotes (higher upvotes = more weight).
3. Calculate aggregate sentiment.
4. Identify consensus and outliers.

**INPUT**
Product: {product_name}
Posts:
{posts_json}

**OUTPUT FORMAT**
Return JSON only:
{{
    "aggregate_sentiment": -1.0 to 1.0,
    "positive_count": integer,
    "negative_count": integer,
    "neutral_count": integer,
    "sentiment_ratio": 0.0 to 1.0,
    "confidence": 0.0 to 1.0,
    "top_praise": ["point1", "point2"],
    "top_complaints": ["point1", "point2"],
    "purchase_signals": integer,
    "consensus": "strong_positive" | "positive" | "mixed" | "negative" | "strong_negative"
}}

**CONSTRAINTS**
- Output JSON only.
- sentiment_ratio = positive_count / (positive_count + negative_count)
- Max 3 items each for top_praise and top_complaints.
- Weight sentiment by upvotes when calculating aggregate.
"""

# =============================================================================
# PRODUCT COMPARISON PROMPT
# =============================================================================

PRODUCT_COMPARISON_PROMPT = """
**ROLE**
You are a product comparison analyst.

**CONTEXT**
- Input: Multiple products with their metrics
- Task: Rank and compare opportunities

**INPUT**
Products:
{products_json}

**OUTPUT FORMAT**
Return JSON only:
{{
    "rankings": [
        {{
            "rank": 1,
            "product_name": "name",
            "score": 0-100,
            "verdict": "one sentence"
        }}
    ],
    "best_opportunity": "product name",
    "avoid": ["product1", "product2"],
    "market_insight": "2-3 sentences about the overall market"
}}

**CONSTRAINTS**
- Output JSON only.
- Rank all products, best first.
- Maximum 3 products in avoid list.
"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_sentiment_prompt(product_name: str, text: str) -> str:
    """Format sentiment analysis prompt with inputs."""
    return SENTIMENT_ANALYSIS_PROMPT.format(
        product_name=product_name,
        text=text
    )


def format_extraction_prompt(text: str, subreddit: str) -> str:
    """Format product extraction prompt with inputs."""
    return PRODUCT_EXTRACTION_PROMPT.format(
        text=text,
        subreddit=subreddit
    )


def format_scoring_prompt(
    product_name: str,
    amazon_reviews: int,
    amazon_rating: float,
    reddit_posts: int,
    reddit_sentiment: float,
    trend_direction: str,
    price: str
) -> str:
    """Format opportunity scoring prompt with inputs."""
    return OPPORTUNITY_SCORING_PROMPT.format(
        product_name=product_name,
        amazon_reviews=amazon_reviews,
        amazon_rating=amazon_rating,
        reddit_posts=reddit_posts,
        reddit_sentiment=reddit_sentiment,
        trend_direction=trend_direction,
        price=price
    )


def format_batch_sentiment_prompt(product_name: str, posts: list) -> str:
    """Format batch sentiment prompt with posts."""
    import json
    posts_formatted = json.dumps([
        {
            "title": p.get("title", ""),
            "content": p.get("content", "")[:500],  # Truncate for token limit
            "upvotes": p.get("upvotes", 0)
        }
        for p in posts
    ], indent=2)

    return BATCH_SENTIMENT_PROMPT.format(
        product_name=product_name,
        posts_json=posts_formatted
    )
