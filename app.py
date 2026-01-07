"""
Product Research Bot - Web UI
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import os
import asyncio
import sys

# Fix for Windows Playwright asyncio issue
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Page config
st.set_page_config(
    page_title="Product Research Bot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Google Fonts + RPG Theme CSS
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=Crimson+Pro:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>
    /* RPG Color Variables */
    :root {
        --parchment: #f4e4bc;
        --parchment-dark: #e8d5a3;
        --ink: #2c1810;
        --gold: #c9a227;
        --gold-light: #e8c547;
        --leather: #8b4513;
        --leather-dark: #5c2e0a;
        --blood: #8b0000;
        --emerald: #2e5a3a;
    }

    /* Parchment background texture */
    .stApp {
        background:
            linear-gradient(135deg, rgba(244,228,188,0.9) 0%, rgba(232,213,163,0.9) 100%),
            repeating-linear-gradient(
                45deg,
                transparent,
                transparent 2px,
                rgba(139,69,19,0.03) 2px,
                rgba(139,69,19,0.03) 4px
            );
    }

    /* Main header - ornate medieval */
    .main-header {
        font-family: 'Cinzel', serif;
        font-size: 2.8rem;
        font-weight: 900;
        color: var(--ink);
        margin-bottom: 0.25rem;
        letter-spacing: 0.05em;
        text-shadow: 2px 2px 0 var(--gold);
    }
    .sub-header {
        font-family: 'Crimson Pro', serif;
        font-size: 1.15rem;
        font-weight: 400;
        font-style: italic;
        color: var(--leather);
        margin-top: 0;
    }

    /* Ornate section headers */
    h3 {
        font-family: 'Cinzel', serif !important;
        font-weight: 700 !important;
        color: var(--ink) !important;
        letter-spacing: 0.03em !important;
        border-bottom: 2px solid var(--gold) !important;
        padding-bottom: 0.5rem !important;
    }

    /* Medieval buttons */
    .stButton > button {
        font-family: 'Cinzel', serif;
        background: linear-gradient(180deg, var(--leather) 0%, var(--leather-dark) 100%);
        color: var(--parchment);
        border: 2px solid var(--gold);
        border-radius: 2px;
        padding: 0.7rem 1.5rem;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        transition: all 0.2s ease;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.2),
            0 4px 8px rgba(0,0,0,0.3);
    }
    .stButton > button:hover {
        background: linear-gradient(180deg, var(--gold) 0%, var(--leather) 100%);
        color: var(--ink);
        transform: translateY(-2px);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.3),
            0 6px 12px rgba(0,0,0,0.4);
    }

    /* Score badges - treasure ratings */
    .score-high {
        font-family: 'Cinzel', serif;
        background: linear-gradient(180deg, var(--gold) 0%, #a08020 100%);
        color: var(--ink);
        padding: 8px 16px;
        border: 2px solid var(--leather);
        border-radius: 2px;
        font-weight: 700;
        font-size: 0.8rem;
        letter-spacing: 0.05em;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .score-medium {
        font-family: 'Cinzel', serif;
        background: linear-gradient(180deg, #c0c0c0 0%, #808080 100%);
        color: var(--ink);
        padding: 8px 16px;
        border: 2px solid var(--leather);
        border-radius: 2px;
        font-weight: 700;
        font-size: 0.8rem;
        letter-spacing: 0.05em;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .score-low {
        font-family: 'Cinzel', serif;
        background: linear-gradient(180deg, #cd7f32 0%, #8b4513 100%);
        color: var(--parchment);
        padding: 8px 16px;
        border: 2px solid var(--leather-dark);
        border-radius: 2px;
        font-weight: 700;
        font-size: 0.8rem;
        letter-spacing: 0.05em;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }

    /* Progress bar - gold fill */
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--gold) 0%, var(--gold-light) 100%);
    }

    /* Links styled as scrolls */
    .stLinkButton > a {
        font-family: 'Cinzel', serif;
        background: var(--parchment);
        border: 2px solid var(--leather);
        color: var(--ink);
        border-radius: 2px;
        font-weight: 700;
        letter-spacing: 0.05em;
        transition: all 0.2s ease;
    }
    .stLinkButton > a:hover {
        background: var(--gold);
        border-color: var(--leather-dark);
    }

    /* Sidebar - darker parchment */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--parchment-dark) 0%, #d4c090 100%);
        border-right: 3px solid var(--leather);
    }

    /* Text inputs */
    .stTextArea textarea, .stTextInput input {
        font-family: 'Crimson Pro', serif;
        background: var(--parchment);
        border: 2px solid var(--leather);
        border-radius: 2px;
        color: var(--ink);
    }

    /* Selectbox */
    .stSelectbox > div > div {
        font-family: 'Crimson Pro', serif;
        background: var(--parchment);
        border: 2px solid var(--leather);
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-family: 'Cinzel', serif;
        color: var(--ink);
    }

    /* Expander */
    .streamlit-expanderHeader {
        font-family: 'Cinzel', serif;
        background: var(--parchment-dark);
        border: 1px solid var(--leather);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None
if 'running' not in st.session_state:
    st.session_state.running = False


def get_sentiment_badge(sentiment):
    """Get sentiment badge with color."""
    if sentiment > 0.05:
        return f'<span style="color: #28a745; font-weight: bold;">+{sentiment:.2f}</span>'
    elif sentiment < -0.05:
        return f'<span style="color: #dc3545; font-weight: bold;">{sentiment:.2f}</span>'
    return f'<span style="color: #6c757d;">{sentiment:.2f}</span>'


def get_score_badge(score):
    """Get score badge with RPG treasure rating."""
    if score >= 70:
        css_class = "score-high"
        label = "GOLD"
    elif score >= 50:
        css_class = "score-medium"
        label = "SILVER"
    else:
        css_class = "score-low"
        label = "BRONZE"

    return f'<span class="{css_class}">{score:.1f} - {label}</span>'


@st.cache_resource
def load_scrapers():
    """Load scrapers (cached)."""
    from scrapers import RedditScraper, TrendsScraper
    from scrapers.browser_scraper import BrowserScraper
    from analysis import SentimentAnalyzer
    return {
        'reddit': RedditScraper(delay=2.0),
        'trends': TrendsScraper(delay=2.0),
        'browser': BrowserScraper(),
        'sentiment': SentimentAnalyzer()
    }


def discover_niches(categories, max_products, niche_types=None, include_amazon_sentiment=True, progress_callback=None):
    """Discover product opportunities from real Google Trends data."""
    from discovery.trends_to_products_finder import TrendsToProductsFinder
    finder = TrendsToProductsFinder()

    if niche_types is None:
        niche_types = ["accessories", "alternatives", "complementary"]

    return finder.discover_opportunities(
        categories=categories,
        max_products=max_products,
        products_per_topic=3,
        niche_types=niche_types,
        include_amazon_sentiment=include_amazon_sentiment,
        progress_callback=progress_callback
    )


def research_products(products, skip_trends=True, progress_callback=None):
    """Research a list of products."""
    tools = load_scrapers()
    results = []

    for i, product_name in enumerate(products):
        if progress_callback:
            progress_callback(i, len(products), product_name)

        result = {
            'name': product_name,
            'category': 'manual',
            'trend_score': 50,
            'trend_direction': 'unknown',
            'reddit_posts': 0,
            'reddit_sentiment': 0,
            'reddit_positive': 0,
            'reddit_negative': 0,
            'sentiment_ratio': 0.5,
            'opportunity_score': 0
        }

        # Google Trends (optional)
        if not skip_trends:
            try:
                trend_data = tools['trends'].check_trend(product_name)
                result['trend_score'] = trend_data.get('trend_score', 50)
                result['trend_direction'] = trend_data.get('trend_direction', 'unknown')
            except:
                pass

        # Reddit sentiment
        try:
            posts = tools['reddit'].search_all_reddit(product_name, limit=20)
            if posts:
                sentiments = []
                for post in posts:
                    text = f"{post.get('title', '')} {post.get('content', '')}"
                    label, score = tools['sentiment'].get_sentiment_label(text)
                    sentiments.append({
                        'label': label,
                        'score': score,
                        'upvotes': post.get('upvotes', 0)
                    })

                total_weight = sum(max(s['upvotes'], 1) for s in sentiments)
                weighted_sentiment = sum(
                    s['score'] * max(s['upvotes'], 1) for s in sentiments
                ) / total_weight if total_weight > 0 else 0

                positive_count = sum(1 for s in sentiments if s['label'] == 'positive')
                negative_count = sum(1 for s in sentiments if s['label'] == 'negative')

                result['reddit_posts'] = len(posts)
                result['reddit_sentiment'] = round(weighted_sentiment, 3)
                result['reddit_positive'] = positive_count
                result['reddit_negative'] = negative_count
                result['sentiment_ratio'] = round(
                    positive_count / max(positive_count + negative_count, 1), 2
                )
        except Exception as e:
            st.warning(f"Error searching Reddit for {product_name}: {e}")

        # Calculate score
        import math
        base_score = 30
        trend_component = (result['trend_score'] / 100) * 25
        sentiment_component = ((result['reddit_sentiment'] + 1) / 2) * 25
        volume_component = min(20, math.log10(result['reddit_posts'] + 1) * 10)

        final_score = base_score + trend_component + sentiment_component + volume_component

        if result['sentiment_ratio'] > 0.7:
            final_score += 5
        if result['reddit_negative'] > result['reddit_positive']:
            final_score -= 10

        result['opportunity_score'] = round(min(100, max(0, final_score)), 1)
        results.append(result)

    return results


def fetch_amazon_trending(categories, limit_per_category, progress_callback=None):
    """Fetch trending products from Amazon."""
    from scrapers.browser_scraper import get_amazon_trending
    return get_amazon_trending(categories, limit_per_category)


# Header
st.markdown('<p class="main-header">The Merchant\'s Ledger</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Seek treasures of the marketplace, divine their worth through the wisdom of the realm</p>', unsafe_allow_html=True)
st.markdown("")

# Sidebar
with st.sidebar:
    st.markdown("### Settings")

    research_mode = st.radio(
        "Research Mode",
        ["Discover Trends", "Manual Products", "Amazon Trending"],
        help="Choose how to find products to research"
    )

    # Map display names to internal names
    mode_map = {
        "Discover Trends": "Discover Hidden Niches",
        "Manual Products": "Manual Products",
        "Amazon Trending": "Amazon Trending"
    }
    internal_mode = mode_map[research_mode]

    skip_trends = st.checkbox(
        "Skip Google Trends validation",
        value=True,
        help="Faster but less data. Uncheck to validate with Google Trends."
    )

    st.markdown("---")
    st.markdown("### Treasure Rating")
    st.markdown("""
    <div style='font-family: Cinzel, serif; background: linear-gradient(180deg, #c9a227 0%, #a08020 100%); color: #2c1810; padding: 8px 12px; border: 2px solid #8b4513; margin-bottom: 8px;'>
        <strong>GOLD (70-100)</strong><br/>Legendary find
    </div>
    <div style='font-family: Cinzel, serif; background: linear-gradient(180deg, #c0c0c0 0%, #808080 100%); color: #2c1810; padding: 8px 12px; border: 2px solid #8b4513; margin-bottom: 8px;'>
        <strong>SILVER (50-69)</strong><br/>Worthy pursuit
    </div>
    <div style='font-family: Cinzel, serif; background: linear-gradient(180deg, #cd7f32 0%, #8b4513 100%); color: #f4e4bc; padding: 8px 12px; border: 2px solid #5c2e0a;'>
        <strong>BRONZE (0-49)</strong><br/>Common goods
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Scout's Wisdom")
    st.markdown("*Seek positive sentiment*")
    st.markdown("*Verify at the marketplace*")
    st.markdown("*Many voices speak truth*")

# Main content
if internal_mode == "Discover Hidden Niches":
    st.markdown("### Discover Hidden Niches")
    st.markdown("**Find products related to what's actually trending right now**")
    st.markdown("Queries Google Trends for rising topics, searches Amazon for related products, validates sentiment on Reddit + Amazon reviews")

    col1, col2 = st.columns(2)

    with col1:
        categories = st.multiselect(
            "Google Trends Categories:",
            ["fashion_beauty", "hobbies", "pets", "shopping", "technology", "health", "home"],
            default=["technology"],
            help="Categories to scan on Google Trends for rising queries"
        )

    with col2:
        max_products = st.slider("Max products to analyze:", 5, 30, 10)

    col1, col2 = st.columns(2)

    with col1:
        niche_types = st.multiselect(
            "Niche Types to Find:",
            ["accessories", "alternatives", "complementary"],
            default=["accessories", "alternatives", "complementary"],
            help="Types of niche products to discover for each trending topic"
        )

    with col2:
        include_amazon_sentiment = st.checkbox(
            "Analyze Amazon Reviews",
            value=True,
            help="Scrape and analyze Amazon reviews for sentiment (slower but more accurate)"
        )

    st.markdown("---")
    st.markdown("**How it works:**")
    st.markdown("1. Queries Google Trends API for **real rising topics** (past 30 days)")
    st.markdown("2. Generates niche product searches (accessories, alternatives, complementary)")
    st.markdown("3. Searches Amazon via browser automation for related products")
    st.markdown("4. Analyzes sentiment from **Reddit + Amazon reviews**")
    st.markdown("5. Scores based on competition, sentiment, and niche type")
    st.markdown("")
    st.warning("**Note:** This uses rate-limited APIs. Discovery takes 3-8 minutes depending on settings.")

    col1, col2 = st.columns([1, 4])
    with col1:
        discover_btn = st.button("Discover Opportunities", type="primary", use_container_width=True)

    if discover_btn:
        if not categories:
            st.error("Please select at least one category")
        elif not niche_types:
            st.error("Please select at least one niche type")
        else:
            # Progress tracking with detailed status
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                detail_text = st.empty()
                live_results = st.empty()

            discovered_products = []

            def update_progress(step, total, item="", message=""):
                if total > 0:
                    progress_bar.progress(min(step / total, 1.0))
                status_text.text(f"{message} {item[:50] if item else ''}")
                detail_text.text(f"Step {step}/{total}")

                # Show live results count
                if discovered_products:
                    live_results.info(f"Found {len(discovered_products)} products so far...")

            with st.spinner("Discovering trends and searching Amazon..."):
                st.session_state.results = discover_niches(
                    categories=categories,
                    max_products=max_products,
                    niche_types=niche_types,
                    include_amazon_sentiment=include_amazon_sentiment,
                    progress_callback=update_progress
                )

            progress_bar.empty()
            status_text.empty()
            detail_text.empty()
            live_results.empty()
            st.success(f"Discovered {len(st.session_state.results)} opportunities!")

elif internal_mode == "Manual Products":
    st.markdown("### Research Specific Products")
    st.markdown("Enter product names to research (one per line)")

    products_input = st.text_area(
        "Products to research:",
        value="air fryer\nyoga mat\nresistance bands\nblender\nmassage gun",
        height=150,
        help="Enter one product per line"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        research_btn = st.button("Research Products", type="primary", use_container_width=True)

    if research_btn:
        products = [p.strip() for p in products_input.split('\n') if p.strip()]

        if not products:
            st.error("Please enter at least one product")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(i, total, name):
                progress_bar.progress((i + 1) / total)
                status_text.text(f"Researching: {name} ({i+1}/{total})")

            with st.spinner("Researching products..."):
                st.session_state.results = research_products(
                    products,
                    skip_trends=skip_trends,
                    progress_callback=update_progress
                )

            progress_bar.empty()
            status_text.empty()
            st.success(f"Researched {len(st.session_state.results)} products!")

else:  # Amazon Trending
    st.markdown("### Amazon Trending Products")
    st.markdown("Automatically fetch products from Amazon Movers & Shakers")

    col1, col2 = st.columns(2)

    with col1:
        categories = st.multiselect(
            "Categories to scan:",
            ["kitchen", "fitness", "home", "sports", "electronics", "beauty", "baby", "pets", "garden", "tools"],
            default=["kitchen", "fitness"],
            help="Select Amazon categories"
        )

    with col2:
        limit = st.slider("Products per category:", 5, 20, 10)

    col1, col2 = st.columns([1, 4])
    with col1:
        fetch_btn = st.button("Fetch & Research", type="primary", use_container_width=True)

    if fetch_btn:
        if not categories:
            st.error("Please select at least one category")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Step 1: Fetch from Amazon
            status_text.text("Step 1/2: Fetching from Amazon (this may take a moment)...")

            with st.spinner("Opening browser and fetching Amazon data..."):
                amazon_products = fetch_amazon_trending(categories, limit)

            if not amazon_products:
                st.error("❌ Could not fetch Amazon products. Make sure Playwright is installed.")
                progress_bar.empty()
                status_text.empty()
            else:
                st.info(f"Found {len(amazon_products)} trending products from Amazon")

                # Step 2: Research sentiment
                status_text.text("Step 2/2: Analyzing Reddit sentiment...")

                product_names = [p['name'] for p in amazon_products]

                def update_progress(i, total, name):
                    progress_bar.progress((i + 1) / total)
                    status_text.text(f"Analyzing: {name[:40]}... ({i+1}/{total})")

                results = research_products(
                    product_names,
                    skip_trends=skip_trends,
                    progress_callback=update_progress
                )

                # Merge Amazon data with results
                for i, result in enumerate(results):
                    if i < len(amazon_products):
                        result['category'] = amazon_products[i].get('category', 'unknown')
                        result['price'] = amazon_products[i].get('price', '')
                        result['rank_change'] = amazon_products[i].get('rank_change', '')
                        result['url'] = amazon_products[i].get('url', '')

                st.session_state.results = results
                progress_bar.empty()
                status_text.empty()
                st.success(f"Analyzed {len(results)} products!")

# Display results
if st.session_state.results:
    st.markdown("---")
    st.markdown("### Results")

    results = st.session_state.results

    # Sort options
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        sort_by = st.selectbox(
            "Sort by:",
            ["Opportunity Score", "Reddit Sentiment", "Reddit Posts"],
            index=0
        )
    with col2:
        filter_score = st.slider("Min score:", 0, 100, 0)
    with col3:
        filter_sentiment = st.selectbox(
            "Sentiment filter:",
            ["All", "Positive only", "Negative only"],
            index=0
        )

    # Apply filters
    filtered = results.copy()
    filtered = [r for r in filtered if r['opportunity_score'] >= filter_score]

    if filter_sentiment == "Positive only":
        filtered = [r for r in filtered if r['reddit_sentiment'] > 0.05]
    elif filter_sentiment == "Negative only":
        filtered = [r for r in filtered if r['reddit_sentiment'] < -0.05]

    # Sort
    if sort_by == "Opportunity Score":
        filtered.sort(key=lambda x: x['opportunity_score'], reverse=True)
    elif sort_by == "Reddit Sentiment":
        filtered.sort(key=lambda x: x['reddit_sentiment'], reverse=True)
    else:
        filtered.sort(key=lambda x: x['reddit_posts'], reverse=True)

    # Display as cards
    st.markdown(f"**Showing {len(filtered)} products**")

    for i, product in enumerate(filtered):
        with st.container():
            # Header row
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"### {i+1}. {product['name'][:70]}")
                if product.get('related_topic'):
                    st.caption(f"Related to trending topic: **{product['related_topic']}**")
                if product.get('keywords'):
                    st.caption(f"Keywords: {', '.join(product['keywords'])}")
                elif product.get('category'):
                    st.caption(f"Category: {product['category']}")

            with col2:
                score = product['opportunity_score']
                st.markdown(get_score_badge(score), unsafe_allow_html=True)

            # Metrics row
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Reddit Posts", product['reddit_posts'])

            with col2:
                sentiment = product['reddit_sentiment']
                st.markdown(f"**Sentiment:** {get_sentiment_badge(sentiment)}", unsafe_allow_html=True)

            with col3:
                ratio = product.get('sentiment_ratio', 0.5)
                st.metric("Positive Ratio", f"{ratio:.0%}")

            # Marketplace links
            if product.get('amazon_url') or product.get('shopify_search_url'):
                link_col1, link_col2 = st.columns(2)

                with link_col1:
                    if product.get('amazon_url'):
                        st.link_button("Search on Amazon", product['amazon_url'], use_container_width=True)

                with link_col2:
                    if product.get('shopify_search_url'):
                        st.link_button("Search Shopify Stores", product['shopify_search_url'], use_container_width=True)

            # Expandable details
            with st.expander("View details"):
                detail_col1, detail_col2 = st.columns(2)

                with detail_col1:
                    st.markdown("**Reddit Analysis**")
                    st.write(f"- Total posts: {product['reddit_posts']}")
                    st.write(f"- Positive: {product['reddit_positive']}")
                    st.write(f"- Negative: {product['reddit_negative']}")
                    st.write(f"- Sentiment score: {product['reddit_sentiment']:.3f}")

                with detail_col2:
                    st.markdown("**Additional Info**")
                    st.write(f"- Trend direction: {product.get('trend_direction', 'unknown')}")
                    st.write(f"- Trend score: {product.get('trend_score', 0)}")
                    if product.get('price'):
                        st.write(f"- Price: {product['price']}")
                    if product.get('amazon_saturation'):
                        st.write(f"- Amazon saturation: {product['amazon_saturation']}")
                    if product.get('shopify_stores'):
                        st.write(f"- Shopify stores: {product['shopify_stores']}")

            st.markdown("---")

    # Export section
    st.markdown("### Export Results")

    df = pd.DataFrame(filtered)

    col1, col2 = st.columns(2)

    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"product_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        json_data = df.to_json(orient='records', indent=2)
        st.download_button(
            label="Download JSON",
            data=json_data,
            file_name=f"product_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; padding: 1.5rem 0; font-family: Cinzel, serif;'>
        <p style='color: #2c1810; font-weight: 700; margin-bottom: 0.25rem; letter-spacing: 0.1em;'>THE MERCHANT'S LEDGER</p>
        <p style='color: #8b4513; font-size: 0.85rem; font-family: Crimson Pro, serif; font-style: italic;'>Fortune favors the prepared trader</p>
    </div>
    """,
    unsafe_allow_html=True
)
