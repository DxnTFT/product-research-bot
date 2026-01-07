"""
Configuration settings for the product research bot.
Add/remove subreddits and keywords based on your niche.
"""

# Subreddits to monitor - organized by category
SUBREDDITS = {
    "ecommerce": [
        "ecommerce",
        "dropship",
        "FulfillmentByAmazon",
        "Entrepreneur",
        "smallbusiness",
    ],
    "fitness": [
        "Fitness",
        "homegym",
        "GYM",
        "bodyweightfitness",
        "running",
    ],
    "homegoods": [
        "BuyItForLife",
        "homeowners",
        "HomeImprovement",
        "organization",
        "Cooking",
    ],
    "kitchenware": [
        "Cooking",
        "Kitchen",
        "cookware",
        "Baking",
        "MealPrepSunday",
    ],
    "fashion": [
        "fashion",
        "streetwear",
        "malefashionadvice",
        "femalefashionadvice",
        "frugalmalefashion",
    ],
}

# Keywords that indicate product discussion
PRODUCT_KEYWORDS = [
    "recommend",
    "best",
    "looking for",
    "anyone tried",
    "worth it",
    "review",
    "bought",
    "purchase",
    "alternative to",
    "cheaper",
    "upgrade",
    "holy grail",
    "game changer",
    "must have",
    "favorite",
    "suggestion",
]

# Keywords indicating negative sentiment about products
NEGATIVE_KEYWORDS = [
    "broke",
    "waste of money",
    "don't buy",
    "avoid",
    "terrible",
    "scam",
    "disappointing",
    "returned",
    "refund",
    "cheap quality",
]

# Keywords indicating positive sentiment
POSITIVE_KEYWORDS = [
    "love it",
    "amazing",
    "best purchase",
    "highly recommend",
    "worth every penny",
    "changed my life",
    "can't live without",
    "excellent quality",
    "perfect",
    "exceeded expectations",
]

# Scraping settings
SCRAPE_SETTINGS = {
    "posts_per_subreddit": 25,  # Number of posts to fetch per subreddit
    "min_upvotes": 10,  # Minimum upvotes to consider
    "min_comments": 5,  # Minimum comments to consider
    "include_comments": False,  # Disable comments for now (causes 403s)
    "comments_per_post": 10,  # Top comments to analyze per post
    "delay_between_requests": 25,  # Seconds between requests (increased from 4 to 25)
}

# Scoring weights for product opportunity
SCORING_WEIGHTS = {
    "mention_frequency": 0.25,  # How often product is mentioned
    "sentiment_score": 0.30,  # Overall sentiment
    "engagement": 0.20,  # Upvotes + comments
    "recency": 0.15,  # Newer mentions weighted higher
    "purchase_intent": 0.10,  # Keywords indicating buying interest
}

# Database settings
DATABASE_PATH = "data/products.db"

# Reporting settings
REPORT_SETTINGS = {
    "top_products": 20,  # Number of top products to show in reports
    "export_formats": ["csv", "json"],
}

# Anti-blocking and rate limiting settings
RATE_LIMIT_SETTINGS = {
    "base_delay": 15.0,  # Base delay between requests (seconds) - FASTER MODE
    "max_jitter": 2.0,  # Random jitter +/- seconds
    "min_delay": 8.0,  # Minimum delay (safety floor) - FASTER MODE

    # Exponential backoff settings
    "exponential_backoff": {
        "first_retry": 60,  # 1 minute
        "second_retry": 120,  # 2 minutes
        "third_retry": 300,  # 5 minutes
        "max_retries": 3,
        "backoff_factor": 2.0,  # Multiply by this each retry
    },

    # Circuit breaker settings
    "circuit_breaker": {
        "failure_threshold": 3,  # Consecutive failures before opening
        "recovery_timeout": 600,  # 10 minutes before trying again
        "half_open_requests": 1,  # Requests to try when half-open
    },

    # Domain-specific settings
    "domains": {
        "amazon.com": {
            "delay": 15.0,  # FASTER MODE
            "max_requests_per_minute": 4,  # FASTER MODE
        },
        "trends.google.com": {
            "delay": 25.0,
            "max_requests_per_minute": 2,
        },
    },
}

# Stealth settings for anti-bot detection evasion
STEALTH_SETTINGS = {
    "rotate_user_agent": True,
    "randomize_viewport": True,
    "randomize_timezone": True,
    "simulate_human_behavior": True,
    "use_fingerprint_evasion": True,

    # Playwright settings
    "playwright": {
        "headless": True,
        "slow_mo": 100,  # Slow down operations by 100ms
        "navigation_timeout": 60000,  # 60 seconds
    },
}
