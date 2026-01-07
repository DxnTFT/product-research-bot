# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Product Research Bot - Automated e-commerce product discovery that finds trending products, validates with market data, and scores opportunities based on competition and sentiment.

## Development Commands

```bash
# Setup
pip install -r requirements.txt
python -m playwright install chromium

# Web UI (recommended)
streamlit run app.py

# CLI - Discover hidden niches (PRIMARY)
python main.py --discover --seed-keywords technology fitness --max-products 10
python main.py -d --seed-keywords electronics --max-products 50 --slow  # Sequential mode

# CLI - Custom keywords (skip Google Trends)
python main.py -k "posture corrector" "led face mask" --max-products 10
python main.py -k "smart watch" --amazon-reviews  # Include Amazon review sentiment

# CLI - Research specific products
python main.py -p "air fryer" "yoga mat"
python main.py -f products_to_research.txt

# CLI - Quick check
python main.py --check "air fryer"

# CLI - Amazon trending
python main.py --categories kitchen fitness --limit 10 --skip-trends
```

No formal test suite exists. Manual testing via CLI and Web UI.

## Architecture

### Four Operating Modes

1. **Discover Hidden Niches (PRIMARY)** - `discovery/trends_to_products_finder.py`
   - Pipeline: Curated Keywords → Google Trends Rising Queries → Amazon Search → Reddit Sentiment → Score
   - Uses `TrendsRisingSimple` with category seed keywords (technology, fashion_beauty, hobbies, pets, shopping)
   - Fast mode (default): Parallel Reddit via `AsyncWorkerPool` (~3-4 mins)
   - Slow mode (`--slow`): Sequential processing (~5-10 mins)

2. **Custom Keywords Mode** - `main.py` with `-k` flag
   - Skip Google Trends, search Amazon directly with user keywords
   - Optional `--amazon-reviews` for deeper sentiment from product reviews

3. **Manual Product Research** - `main.py` with `-p` flag
   - User provides product names, gets validation and scoring

4. **Amazon Trending** - `main.py` with `--categories`
   - Scrapes Amazon Movers & Shakers (higher competition products)

### Core Pipeline Flow (Discovery Mode)

```
TrendsToProductsFinder.discover_opportunities_fast()
    │
    ├── TrendsRisingSimple.get_rising_topics()    # Google Trends
    │       └── pytrends interest_over_time()
    │
    ├── _generate_niche_keywords()                 # Create search queries
    │       └── NICHE_PATTERNS + CATEGORY_NICHES
    │
    ├── AsyncBrowserScraper.search_products_batch() # Amazon search
    │       └── Playwright browser (stealth mode)
    │
    └── _get_sentiment_parallel()                  # Reddit sentiment
            └── AsyncWorkerPool + AsyncRedditScraper
```

### Scraper Layer (`scrapers/`)

All scrapers inherit from `BaseScraper` (`base_scraper.py`) which provides user agent rotation, rate limiting with jitter, and text cleaning.

**Sync scrapers:**
| Scraper | Purpose |
|---------|---------|
| `browser_scraper.py` | Playwright-based Amazon scraping + review sentiment |
| `amazon_product_finder.py` | Amazon product search |
| `reddit_scraper.py` | Reddit search + comment scraping via requests |
| `trends_scraper.py` | Google Trends via pytrends |
| `trends_rising_simple.py` | Rising queries with curated category seeds |
| `shopify_scraper.py` | Shopify store discovery |
| `competition_checker.py` | Market saturation analysis |

**Async scrapers (for parallel processing):**
| Scraper | Purpose |
|---------|---------|
| `async_browser_scraper.py` | Async Playwright with browser reuse |
| `async_reddit_scraper.py` | Async Reddit with sentiment analysis |
| `async_worker_pool.py` | Bounded concurrency worker pool (semaphore-based) |

**Supporting infrastructure:**
- `rate_limiter.py` - Exponential backoff, circuit breaker pattern
- `stealth_config.py` - User agent rotation, fingerprint evasion
- `logging_config.py` - Structured scraper logging

### Analysis Layer (`analysis/`)

- `sentiment.py` - VADER sentiment for social media text
- `scorer.py` - Multi-factor opportunity scoring

### Discovery Layer (`discovery/`)

- `TrendsToProductsFinder` - **PRIMARY** - Real Google Trends data, includes profit margin estimates, seasonality detection, sourcing URLs
- `NicheFinder` - Uses related queries
- `SimpleNicheFinder` - Lightweight variant

### Scoring Algorithm (0-100 scale)

```python
# TrendsToProductsFinder._calculate_opportunity_score()
base_score = 30              # Product from rising topic
competition_score = 0-25     # Based on Amazon review count
sentiment_score = 0-25       # Combined Reddit + Amazon sentiment
niche_bonus = 0-10           # Accessory=10, Alternative=8, Complementary=6
validation_bonus = 0-10      # Reddit posts + Amazon reviews analyzed + rating
```

**Bonuses/Penalties:**
- +5 for >75% positive sentiment ratio
- -15 for more negative than positive reviews

**Interpretation:** 70-100 = High opportunity, 50-69 = Moderate, 0-49 = Low

### Key Entry Points

- `app.py` - Streamlit web UI
- `main.py` - CLI with argparse
- `config/settings.py` - All settings (subreddits, keywords, rate limits, stealth)
- `reports/generator.py` - CSV/JSON export

## Code Conventions

### New Scrapers
1. Inherit from `BaseScraper`
2. Implement `scrape()` and `extract_products()` abstract methods
3. Use `self.rate_limit()` between requests (adds jitter, logs progress)
4. Use `self.get_headers()` for stealth headers
5. Return `List[Dict]` format

### New Discovery Methods
1. Create class in `discovery/`
2. Implement `discover_opportunities()` method (sync) or `discover_opportunities_async()` (async)
3. Return `List[Dict]` with keys: `name`, `opportunity_score`, `reddit_sentiment`, `trend_direction`
4. For async methods, add a sync wrapper using `asyncio.run()` (see `discover_opportunities_fast()`)
5. Export from `discovery/__init__.py`

### Rate Limiting

Configured in `config/settings.py` under `RATE_LIMIT_SETTINGS`:
- Base delay: 15s (minimum 8s)
- Amazon: 15s delay, max 4 req/min
- Google Trends: 25s delay, max 2 req/min
- Circuit breaker: 3 failures → 10 min cooldown
- Backoff: 60s → 120s → 300s

## Platform Notes

**Windows asyncio fix** (required in `app.py` for Streamlit):
```python
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

**Playwright on Windows**: Uses default `ProactorEventLoop` for compatibility. The async discovery (`discover_opportunities_fast()`) handles this automatically.

## Data Storage

- Reports export to `reports/opportunities_TIMESTAMP.{csv,json}`
- Database models in `database/` exist but are unused - app is stateless

## Limitations

- **Google Trends**: 429 errors with heavy use. Discovery takes 3-10 mins.
- **Amazon**: Can trigger CAPTCHA. Stealth config helps but don't scale.
- **Reddit**: Public scraping has limits.
- **VADER**: May misinterpret sarcasm.
