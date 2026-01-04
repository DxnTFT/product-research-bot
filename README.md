# Product Research Bot

Automated product research tool that finds trending products and validates them with real user sentiment from Reddit.

## What It Does

```
Amazon Movers & Shakers → Google Trends → Reddit Sentiment → Opportunity Score
```

1. **Finds trending products** from Amazon's Movers & Shakers (products gaining sales rank)
2. **Validates search interest** with Google Trends (optional)
3. **Analyzes real user sentiment** by searching Reddit discussions
4. **Scores opportunities** and exports to CSV/JSON

## Installation

```bash
# Clone the repo
git clone https://github.com/DxnTFT/product-research-bot.git
cd product-research-bot

# Install dependencies
pip install -r requirements.txt

# Install browser for Amazon scraping
python -m playwright install chromium
```

## Usage

### Full Automated Pipeline
```bash
# Scan Amazon trending → Reddit sentiment (kitchen, fitness, home)
python main.py

# Specific categories
python main.py --categories kitchen fitness

# More products per category
python main.py --categories kitchen --limit 20

# Skip Google Trends (faster)
python main.py --skip-trends
```

### Manual Product Research
```bash
# Research specific products you're interested in
python main.py -p "air fryer" "yoga mat" "resistance bands"

# From a file (one product per line)
python main.py -f products_to_research.txt
```

### Quick Check Single Product
```bash
python main.py --check "air fryer"
```

## Output

Results are saved to the `reports/` folder:
- `opportunities_TIMESTAMP.csv` - Open in Excel/Google Sheets
- `opportunities_TIMESTAMP.json` - For programmatic use

### Columns Explained

| Column | Description |
|--------|-------------|
| `name` | Product name |
| `opportunity_score` | 0-100 score (higher = better opportunity) |
| `reddit_sentiment` | -1 to +1 (positive = people like it) |
| `reddit_posts` | Number of Reddit discussions found |
| `sentiment_ratio` | % of positive vs negative posts |
| `trend_direction` | rising/falling/stable (from Google Trends) |

## Available Categories

- `kitchen` - Kitchen & Dining
- `home` - Home & Garden
- `fitness` - Exercise & Fitness
- `sports` - Sports & Outdoors
- `electronics` - Electronics
- `beauty` - Beauty & Personal Care
- `baby` - Baby Products
- `pets` - Pet Supplies
- `garden` - Lawn & Garden
- `tools` - Tools & Home Improvement

## How Scoring Works

```
Base Score (30 pts) - Product is trending on Amazon
+ Google Trends (0-25 pts) - Rising search interest
+ Reddit Sentiment (0-25 pts) - Positive user opinions
+ Reddit Volume (0-20 pts) - Amount of discussion
+ Bonus (+5 pts) - Strong positive sentiment ratio
- Penalty (-10 pts) - More negative than positive posts
= Opportunity Score (0-100)
```

**70+ = High opportunity** - Consider researching further
**50-70 = Moderate** - Proceed with caution
**<50 = Low opportunity** - May have issues

## Example Output

```
TOP PRODUCT OPPORTUNITIES
======================================================================
 1. [ 83.5] Ello Duraglass Meal Prep Sets              | kitchen  | S:+ R:16
 2. [ 80.9] Ello Pop & Fill Water Bottle               | kitchen  | S:+ R:20
 3. [ 77.6] Kitchen Genie Manual Chopper               | kitchen  | S:+ R:20
 4. [ 74.1] Ukeetap Chicken Shredder Tool              | kitchen  | S:+ R:20
 5. [ 64.2] Generic Yoga Mat                           | fitness  | S:- R:20
```

Note: Product #5 has negative sentiment (S:-) which lowers its score.

## Tech Stack

- **Python 3.8+**
- **Playwright** - Browser automation for Amazon
- **BeautifulSoup** - HTML parsing
- **VADER Sentiment** - Social media sentiment analysis
- **pytrends** - Google Trends API
- **SQLAlchemy** - Database (optional)

## Notes

- Amazon scraping uses browser automation (Playwright) to avoid blocking
- Reddit uses their JSON API (no auth required)
- Google Trends may rate limit with heavy use
- Run with `--skip-trends` for faster results

## License

MIT
