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
    "delay_between_requests": 4,  # Seconds between requests (be nice to Reddit)
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
