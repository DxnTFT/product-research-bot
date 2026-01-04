"""
Product Research Bot - Web UI
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import os
import asyncio

# Page config
st.set_page_config(
    page_title="Product Research Bot",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-top: 0;
    }
    .score-high {
        background-color: #d4edda;
        padding: 5px 10px;
        border-radius: 5px;
        color: #155724;
        font-weight: bold;
    }
    .score-medium {
        background-color: #fff3cd;
        padding: 5px 10px;
        border-radius: 5px;
        color: #856404;
        font-weight: bold;
    }
    .score-low {
        background-color: #f8d7da;
        padding: 5px 10px;
        border-radius: 5px;
        color: #721c24;
        font-weight: bold;
    }
    .sentiment-positive { color: #28a745; font-weight: bold; }
    .sentiment-negative { color: #dc3545; font-weight: bold; }
    .sentiment-neutral { color: #6c757d; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None
if 'running' not in st.session_state:
    st.session_state.running = False


def get_sentiment_color(sentiment):
    """Get color based on sentiment value."""
    if sentiment > 0.05:
        return "🟢"
    elif sentiment < -0.05:
        return "🔴"
    return "🟡"


def get_score_badge(score):
    """Get badge based on score."""
    if score >= 70:
        return f"✅ {score:.1f}"
    elif score >= 50:
        return f"⚠️ {score:.1f}"
    return f"❌ {score:.1f}"


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
st.markdown('<p class="main-header">🔍 Product Research Bot</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Find trending products and validate with real user sentiment</p>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")

    research_mode = st.radio(
        "Research Mode",
        ["📝 Manual Products", "🔥 Amazon Trending"],
        help="Choose how to find products to research"
    )

    skip_trends = st.checkbox(
        "Skip Google Trends",
        value=True,
        help="Faster but less data. Uncheck to validate with Google Trends."
    )

    st.markdown("---")
    st.markdown("### 📊 Score Guide")
    st.markdown("- **70+** ✅ High opportunity")
    st.markdown("- **50-70** ⚠️ Moderate")
    st.markdown("- **<50** ❌ Low opportunity")

    st.markdown("---")
    st.markdown("### 💡 Tips")
    st.markdown("- Look for **positive sentiment** 🟢")
    st.markdown("- Avoid products with many **negative** reviews 🔴")
    st.markdown("- More Reddit posts = more confidence")

# Main content
if research_mode == "📝 Manual Products":
    st.header("📝 Research Specific Products")
    st.markdown("Enter product names to research (one per line)")

    products_input = st.text_area(
        "Products to research:",
        value="air fryer\nyoga mat\nresistance bands\nblender\nmassage gun",
        height=150,
        help="Enter one product per line"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        research_btn = st.button("🔍 Research", type="primary", use_container_width=True)

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
            st.success(f"✅ Researched {len(st.session_state.results)} products!")

else:  # Amazon Trending
    st.header("🔥 Amazon Trending Products")
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
        fetch_btn = st.button("🔥 Fetch & Research", type="primary", use_container_width=True)

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
                st.success(f"✅ Analyzed {len(results)} products!")

# Display results
if st.session_state.results:
    st.markdown("---")
    st.header("📊 Results")

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
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

            with col1:
                st.markdown(f"**{i+1}. {product['name'][:60]}**")
                if product.get('category'):
                    st.caption(f"Category: {product['category']}")

            with col2:
                score = product['opportunity_score']
                st.metric("Score", get_score_badge(score))

            with col3:
                sentiment = product['reddit_sentiment']
                emoji = get_sentiment_color(sentiment)
                st.metric("Sentiment", f"{emoji} {sentiment:.2f}")

            with col4:
                st.metric("Posts", product['reddit_posts'])

            # Expandable details
            with st.expander("View details"):
                detail_col1, detail_col2 = st.columns(2)

                with detail_col1:
                    st.markdown("**Reddit Analysis**")
                    st.write(f"- Total posts: {product['reddit_posts']}")
                    st.write(f"- Positive: {product['reddit_positive']}")
                    st.write(f"- Negative: {product['reddit_negative']}")
                    st.write(f"- Sentiment ratio: {product['sentiment_ratio']:.0%}")

                with detail_col2:
                    st.markdown("**Trend Data**")
                    st.write(f"- Trend direction: {product['trend_direction']}")
                    st.write(f"- Trend score: {product['trend_score']}")
                    if product.get('price'):
                        st.write(f"- Price: {product['price']}")
                    if product.get('url'):
                        st.markdown(f"[View on Amazon]({product['url']})")

            st.markdown("---")

    # Export section
    st.markdown("### 📥 Export Results")

    df = pd.DataFrame(filtered)

    col1, col2 = st.columns(2)

    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📄 Download CSV",
            data=csv,
            file_name=f"product_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        json_data = df.to_json(orient='records', indent=2)
        st.download_button(
            label="📋 Download JSON",
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
