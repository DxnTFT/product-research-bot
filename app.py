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

# Custom CSS - Clean, professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 600;
        color: #212529;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #6c757d;
        margin-top: 0;
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
    """Get score badge with color."""
    if score >= 70:
        color = "#28a745"  # Green
        label = "HIGH"
    elif score >= 50:
        color = "#ffc107"  # Yellow
        label = "MODERATE"
    else:
        color = "#dc3545"  # Red
        label = "LOW"

    return f'<span style="background-color: {color}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">{score:.1f} - {label}</span>'


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


def discover_niches(categories, max_products, products_per_topic, progress_callback=None):
    """Discover product opportunities from trending topics."""
    from discovery.trends_to_products_finder import TrendsToProductsFinder
    finder = TrendsToProductsFinder()
    return finder.discover_opportunities(
        categories=categories,
        max_products=max_products,
        products_per_topic=products_per_topic,
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
st.markdown('<p class="main-header">Product Research Bot</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Find trending products and validate with real user sentiment</p>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("Settings")

    research_mode = st.radio(
        "Research Mode",
        ["Discover Hidden Niches", "Manual Products", "Amazon Trending"],
        help="Choose how to find products to research"
    )

    skip_trends = st.checkbox(
        "Skip Google Trends",
        value=True,
        help="Faster but less data. Uncheck to validate with Google Trends."
    )

    st.markdown("---")
    st.markdown("**Score Guide**")
    st.markdown("- **70-100:** High opportunity")
    st.markdown("- **50-69:** Moderate")
    st.markdown("- **0-49:** Low opportunity")

    st.markdown("---")
    st.markdown("**Tips**")
    st.markdown("- Look for positive sentiment")
    st.markdown("- Check marketplace links")
    st.markdown("- More Reddit posts = more confidence")

# Main content
if research_mode == "Discover Hidden Niches":
    st.header("Discover Hidden Niches")
    st.markdown("**Find products related to trending topics**")
    st.markdown("Gets trending topics from Google Trends, finds related products on Amazon, validates sentiment on Reddit")

    col1, col2 = st.columns(2)

    with col1:
        categories = st.multiselect(
            "Google Trends Categories:",
            ["fashion_beauty", "hobbies", "pets", "shopping", "technology"],
            default=["technology", "shopping"],
            help="Categories to scan on Google Trends (past 7 days)"
        )

    with col2:
        max_products = st.slider("Max products to return:", 10, 50, 20)

    products_per_topic = st.slider("Products per trending topic:", 1, 5, 3, help="How many products to find for each trending topic")

    st.markdown("---")
    st.markdown("**How it works:**")
    st.markdown("1. Gets trending topics from Google Trends (Fashion, Hobbies, Pets, Shopping, Technology)")
    st.markdown("2. Finds actual products on Amazon related to those topics")
    st.markdown("3. Extracts keywords and validates Reddit sentiment on specific products")
    st.markdown("4. Provides Amazon links and Shopify search URLs")

    col1, col2 = st.columns([1, 4])
    with col1:
        discover_btn = st.button("Discover Opportunities", type="primary", use_container_width=True)

    if discover_btn:
        if not categories:
            st.error("Please select at least one category")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(i, total, name):
                progress_bar.progress((i + 1) / total)
                status_text.text(f"Analyzing: {name[:40]}... ({i+1}/{total})")

            with st.spinner("Discovering opportunities from trending topics..."):
                st.session_state.results = discover_niches(
                    categories=categories,
                    max_products=max_products,
                    products_per_topic=products_per_topic,
                    progress_callback=update_progress
                )

            progress_bar.empty()
            status_text.empty()
            st.success(f"Discovered {len(st.session_state.results)} opportunities!")

elif research_mode == "Manual Products":
    st.header("Research Specific Products")
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
    st.header("Amazon Trending Products")
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
    st.header("Results")

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
    "<div style='text-align: center; color: #888;'>"
    "Product Research Bot • Built for E-commerce Product Discovery"
    "</div>",
    unsafe_allow_html=True
)
