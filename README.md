# Product Research Bot

**Professional product discovery tool for e-commerce entrepreneurs and businesses**

Find untapped product opportunities by combining Google Trends, marketplace competition analysis, and real user sentiment validation.

## Why This Tool?

Traditional product research requires:
- 10+ hours manually browsing Google Trends
- Checking Amazon competition for each product
- Searching Shopify stores to gauge saturation
- Reading Reddit threads for sentiment

**This tool does it all automatically in minutes.**

## Features

### 🔍 Hidden Niche Discovery (PRIMARY)
Automatically finds rising products with low competition:
- Discovers trending products from Google Trends
- Analyzes Amazon marketplace saturation
- Checks Shopify store competition
- Validates real user sentiment from Reddit
- Scores opportunities 0-100

**Perfect for:** Finding products BEFORE they become saturated

### 📝 Manual Product Research
Validate specific product ideas:
- Enter products you want to research
- Get competition analysis across Amazon + Shopify
- Reddit sentiment validation
- Opportunity scoring

**Perfect for:** Validating products you already have in mind

### 🔥 Amazon Trending (Optional)
Quick analysis of Amazon Movers & Shakers:
- Fetch currently trending products
- Analyze Reddit sentiment
- Good for market awareness

**Note:** These products are already trending = higher competition

## Installation

```bash
# Clone the repo
git clone https://github.com/DxnTFT/product-research-bot.git
cd product-research-bot

# Install dependencies
pip install -r requirements.txt

# Install browser for scraping
python -m playwright install chromium
```

## Usage

### Web UI (Recommended for Teams)

```bash
streamlit run app.py
```

Opens in browser with:
- **Discover Hidden Niches** - Automated discovery mode
- **Manual Products** - Validate specific ideas
- **Amazon Trending** - Quick market analysis
- Export results to CSV/JSON

### Command Line

#### Discover Hidden Niches
```bash
# Discover opportunities in specific categories
python main.py --discover --seed-keywords kitchen fitness home

# Analyze more products
python main.py -d --seed-keywords electronics --max-products 50
```

#### Research Specific Products
```bash
# Validate your product ideas
python main.py -p "air fryer" "yoga mat" "resistance bands"

# From a file
python main.py -f my_product_ideas.txt
```

#### Quick Product Check
```bash
python main.py --check "air fryer"
```

## How Scoring Works

### Opportunity Score (0-100)

**Rising Trend (0-25 pts)**
- Google Trends growth rate
- Bonus for "rising" direction

**Amazon Competition (0-25 pts)**
- Search result count
- Average review counts
- Very High saturation: 10 pts
- Very Low saturation: 90 pts

**Shopify Competition (0-25 pts)**
- Number of stores selling product
- <10 stores: 90 pts (excellent)
- >300 stores: 10 pts (saturated)

**Reddit Sentiment (0-25 pts)**
- User opinion analysis (-1 to +1)
- Discussion volume (more = better)
- Positive/negative ratio

**Bonuses & Penalties:**
- +5: Strong positive sentiment (>70% positive)
- -10: More negative than positive reviews
- -5: Very high Amazon/Shopify saturation

### Score Interpretation

| Score | Opportunity | Action |
|-------|------------|--------|
| **70-100** | High | Research further, likely good opportunity |
| **50-69** | Moderate | Proceed with caution, validate more |
| **0-49** | Low | High competition or negative sentiment |

## Output

Results saved to `reports/`:
- `opportunities_TIMESTAMP.csv` - Spreadsheet format
- `opportunities_TIMESTAMP.json` - For programmatic use

### Data Columns

| Column | Description |
|--------|-------------|
| `name` | Product name |
| `opportunity_score` | 0-100 score (higher = better) |
| `trend_direction` | rising/stable/falling |
| `trend_score` | Google Trends score |
| `amazon_saturation` | very_low/low/medium/high/very_high |
| `amazon_avg_reviews` | Avg reviews of top products |
| `shopify_saturation` | very_low/low/medium/high/very_high |
| `shopify_stores` | # of Shopify stores selling it |
| `reddit_sentiment` | -1 to +1 (positive = good) |
| `reddit_posts` | # of Reddit discussions |
| `sentiment_ratio` | % positive vs negative |

## Example Workflow

### For E-commerce Store Owners

1. **Discover Mode**: Find 20-30 rising opportunities
   ```bash
   python main.py -d --seed-keywords kitchen home fitness
   ```

2. **Review Results**: Look for score 70+, low saturation

3. **Validate Top Picks**: Read Reddit posts manually for final validation

4. **Research Suppliers**: Find products on Alibaba/AliExpress

5. **Test**: Order samples or start with dropshipping

### For Market Research

1. **Discover niches** in your target categories
2. **Export CSV** for team review
3. **Compare trends** over time (run weekly)
4. **Identify patterns** in rising categories

## Tech Stack

- **Python 3.8+**
- **Streamlit** - Web UI
- **Playwright** - Browser automation for Amazon
- **BeautifulSoup** - HTML parsing
- **pytrends** - Google Trends API
- **VADER Sentiment** - Social media sentiment analysis
- **Pandas** - Data processing

## SaaS Potential

This tool is designed for:
- E-commerce entrepreneurs
- Dropshipping businesses
- Product sourcing companies
- Market research teams

**Key Value Props:**
- Saves 10+ hours per week on research
- Finds opportunities competitors miss
- Data-driven decisions (not guesswork)
- Validates before inventory investment

## Roadmap

- [ ] Historical trend tracking
- [ ] Email alerts for new opportunities
- [ ] Multi-user team accounts
- [ ] TikTok/Instagram trend integration
- [ ] Supplier integration (Alibaba API)
- [ ] Competition price tracking

## Notes

- **Rate Limits**: Google Trends may throttle with heavy use (built-in delays help)
- **Accuracy**: Reddit sentiment based on available posts (more posts = more reliable)
- **Competition**: Metrics are snapshots; verify before major investment
- **Browser Required**: Playwright needs Chromium for Amazon scraping

## License

MIT

## Contributing

Built for the e-commerce community. Feedback and contributions welcome!

---

**Built to find hidden opportunities in competitive markets.**
