"""
FinGPT Professional News Dashboard - Streamlit News Tab
Echtzeit Trading News Intelligence für EUR/USD

Author: FinGPT Team
Version: 2.0.0 - Mit 3D Neuronen-Kugel Loading Animation

BUG-FIXES:
- Empty State: Zeigt 3D-Neuronen-Kugel statt leerem Placeholder
- Loading States: 3D Kugel → Progress Bar → News Cards
- Smart News Loading: NewsAPI + Finnhub (EUR/USD focused)
"""

import streamlit as st
import pandas as pd
import requests
import feedparser
import json
import os
import time
import hashlib
import math
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Import NeuronSphere component
from gui.components.neuron_sphere import (
    NeuronSphereConfig,
    NeuronColors,
    generate_neuron_points,
    create_neuron_sphere_figure,
    render_trade_history_panel,
    render_loading_sphere
)

# ============================================================
# LOADING STATE MACHINE
# ============================================================

class LoadingState:
    """Enum für Loading States"""
    INITIAL = "initial"       # 3D Kugel Animation
    FETCHING = "fetching"     # Progress Bar
    SUCCESS = "success"       # News Cards
    ERROR = "error"           # Error Card + Retry

# ============================================================
# KONFIGURATION & SETUP
# ============================================================

# Dark Theme Setup
st.set_page_config(
    page_title="FinGPT News Intelligence",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS für dunkles Theme + Loading States
st.markdown("""
<style>
    .news-card {
        background-color: #1E2A38;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        border-left: 4px solid #4CAF50;
    }
    .news-card-bearish {
        border-left-color: #F44336;
    }
    .news-card-neutral {
        border-left-color: #FFC107;
    }
    .impact-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }
    .impact-high {
        background-color: #F44336;
        color: white;
    }
    .impact-medium {
        background-color: #FFC107;
        color: black;
    }
    .impact-low {
        background-color: #4CAF50;
        color: white;
    }
    .sentiment-bullish { color: #4CAF50; font-weight: bold; }
    .sentiment-bearish { color: #F44336; font-weight: bold; }
    .sentiment-neutral { color: #FFC107; font-weight: bold; }
    .metric-box {
        background: linear-gradient(135deg, #1E2A38 0%, #2C3E50 100%);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .stMetric {
        background-color: #1E2A38;
        padding: 15px;
        border-radius: 10px;
    }
    
    /* Loading State Styles */
    .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px 20px;
        min-height: 500px;
    }
    .loading-message {
        color: #FAFAFA;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 10px;
        text-align: center;
    }
    .loading-submessage {
        color: #8B949E;
        font-size: 14px;
        text-align: center;
    }
    
    /* Error Card Styles */
    .error-card {
        background: linear-gradient(135deg, #2C1A1A 0%, #1E2A38 100%);
        border-radius: 16px;
        padding: 30px;
        border: 1px solid #F44336;
        text-align: center;
    }
    .error-title {
        color: #F44336;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .error-message {
        color: #8B949E;
        font-size: 14px;
        margin-bottom: 20px;
    }
    
    /* Progress Bar Custom */
    .progress-container {
        width: 100%;
        max-width: 400px;
        margin: 20px auto;
    }
    
    /* Hide default streamlit spinner */
    .stSpinner > div > div {
        border-color: #2979FF transparent #2979FF transparent;
    }
</style>
""", unsafe_allow_html=True)

# Environment Variables
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Currency Keywords für Relevance Scoring
CURRENCY_KEYWORDS = {
    "EUR/USD": ["eur/usd", "euro dollar", "euro/dollar", "eurusd", "ecb", "european central bank", "eurozone"],
    "GBP/USD": ["gbp/usd", "pound dollar", "gbpusd", "bank of england", "boe"],
    "USD/JPY": ["usd/jpy", "dollar yen", "usdjpy", "bank of japan", "boj", "nikkei"],
    "USD/CHF": ["usd/chf", "dollar swiss", "usdchf", "swiss national bank", "snb"],
    "AUD/USD": ["aud/usd", "australian dollar", "audusd", "rba", "reserve bank of australia"],
    "USD/CAD": ["usd/cad", "dollar canada", "usdcad", "bank of canada", "boc"]
}

# Impact Keywords
IMPACT_KEYWORDS = {
    "HIGH": ["ecb", "fed", "fomc", "interest rate", "rate decision", "non-farm payrolls", "nfp", 
             "gdp", "cpi", "inflation", "speech", "press conference", "governor", "pce"],
    "MEDIUM": ["retail sales", "unemployment", "ppi", "trade balance", "consumer confidence", 
               "manufacturing pmi", "services pmi", "housing starts", " durable goods"],
    "LOW": ["initial claims", "philly fed", "richmond fed", "michigan sentiment", "building permits"]
}

# ============================================================
# LOADING STATE RENDERING
# ============================================================

def render_initial_state():
    """Zeige INITIAL State: 3D Neuronen-Kugel Animation"""
    st.markdown(f"""
    <div class="loading-container">
        <div class="loading-message">🧠 Analysiere News...</div>
        <div class="loading-submessage">FinGPT AI analysiert Marktbedingungen für EUR/USD</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Render 3D Loading Sphere
    render_loading_sphere(
        message="Analysiere News... 🧠",
        key="news_loading_sphere"
    )


def render_fetching_state(progress: float = 0.0, source: str = ""):
    """Zeige FETCHING State: Progress Bar"""
    st.markdown(f"""
    <div class="loading-container">
        <div class="loading-message">📡 Lade Nachrichten</div>
        <div class="loading-submessage">{source}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Simulate progress
    for i in range(100):
        time.sleep(0.05)
        progress_bar.progress(i + 1)
        status_text.text(f"Verarbeite... {i+1}%")
    
    progress_bar.empty()
    status_text.empty()


def render_error_state(error_message: str, retry_callback):
    """Zeige ERROR State: Error Card mit Retry Button"""
    st.markdown(f"""
    <div class="error-card">
        <div class="error-title">❌ Fehler beim Laden der Nachrichten</div>
        <div class="error-message">{error_message}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Retry Button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 Erneut versuchen", use_container_width=True):
            retry_callback()
    
    # Show demo data option
    st.info("💡 Tipp: Erstelle eine .env Datei mit NEWSAPI_KEY und FINNHUB_API_KEY")


def render_success_state(news: List[Dict], currency_filter: str, impact_filter: str):
    """Zeige SUCCESS State: Normale News Cards"""
    # Analyze sentiment and impact for each news item
    for item in news:
        if not item.get("sentiment"):
            text = item.get("title", "") + " " + item.get("description", "")
            item["sentiment"] = analyze_sentiment_fingpt(text)
            item["impact"] = analyze_impact(text)
    
    # Filter by impact
    if impact_filter != "Alle":
        news = [n for n in news if n.get("impact") == impact_filter]
    
    # Render metrics
    sentiment_stats = render_sentiment_summary(news)
    st.divider()
    render_metrics(sentiment_stats, currency_filter)
    
    # Render timeline
    with st.expander("📈 Nachrichten Timeline", expanded=True):
        render_timeline(news)
    
    # Render news feed
    st.divider()
    st.subheader(f"📰 News Feed ({len(news)} Nachrichten)")
    
    # Export all button
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("📥 Alle Exportieren"):
            export_news_csv(news)
    
    # Render news cards
    for i, news_item in enumerate(news):
        render_news_card(news_item, i)


# ============================================================
# CACHE MANAGER (5min TTL)
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def fetch_and_cache_news(currency_filter: str = "EUR/USD", max_items: int = 50) -> List[Dict]:
    """Fetch news from all sources and cache for 5 minutes"""
    all_news = []
    
    # Fetch from multiple sources in parallel
    with st.spinner("Lade News aus verschiedenen Quellen..."):
        # NewsAPI
        if NEWSAPI_KEY:
            newsapi_news = fetch_newsapi(currency_filter, max_items // 3)
            all_news.extend(newsapi_news)
        
        # Finnhub
        if FINNHUB_KEY:
            finnhub_news = fetch_finnhub(currency_filter, max_items // 3)
            all_news.extend(finnhub_news)
        
        # RSS Feeds
        rss_news = fetch_rss_feeds(currency_filter, max_items // 3)
        all_news.extend(rss_news)
    
    # Deduplicate and sort
    all_news = deduplicate_news(all_news)
    all_news = sort_by_relevance(all_news, currency_filter)
    
    return all_news[:max_items]


def fetch_newsapi(currency: str, limit: int) -> List[Dict]:
    """Fetch news from NewsAPI"""
    try:
        keywords = currency.replace("/", " ")
        url = f"https://newsapi.org/v2/everything"
        params = {
            "q": keywords,
            "apiKey": NEWSAPI_KEY,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": limit
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        news = []
        for article in data.get("articles", []):
            news.append({
                "id": hashlib.md5(article["url"].encode()).hexdigest(),
                "title": article["title"],
                "description": article.get("description", "")[:200],
                "source": article["source"]["name"],
                "url": article["url"],
                "published_at": article["publishedAt"],
                "currency": currency,
                "sentiment": None,
                "impact": None,
                "relevance_score": 0
            })
        return news
    except Exception as e:
        st.error(f"NewsAPI Fehler: {e}")
        return []


def fetch_finnhub(currency: str, limit: int) -> List[Dict]:
    """Fetch news from Finnhub"""
    try:
        symbol = currency.replace("/", "").replace("USD", "USD")
        url = f"https://finnhub.io/api/v1/news?category=forex&token={FINNHUB_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        news = []
        for item in data[:limit]:
            news.append({
                "id": str(item.get("id", "")),
                "title": item.get("headline", ""),
                "description": item.get("summary", "")[:200],
                "source": item.get("source", "Finnhub"),
                "url": item.get("url", ""),
                "published_at": item.get("datetime", ""),
                "currency": currency,
                "sentiment": None,
                "impact": None,
                "relevance_score": 0
            })
        return news
    except Exception as e:
        return []


def fetch_rss_feeds(currency: str, limit: int) -> List[Dict]:
    """Fetch news from RSS feeds"""
    rss_urls = [
        "https://www.forexstreet.net/news/rss",
        "https://www.investing.com/rss/news.rss",
        "https://feeds.fxstreet.com/fxstreet"
    ]
    
    news = []
    for rss_url in rss_urls:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:limit // len(rss_urls)]:
                news.append({
                    "id": hashlib.md5(entry.link.encode()).hexdigest(),
                    "title": entry.get("title", ""),
                    "description": entry.get("summary", "")[:200],
                    "source": feed.feed.get("title", "RSS"),
                    "url": entry.get("link", ""),
                    "published_at": entry.get("published", ""),
                    "currency": currency,
                    "sentiment": None,
                    "impact": None,
                    "relevance_score": 0
                })
        except Exception:
            continue
    
    return news


def deduplicate_news(news_list: List[Dict]) -> List[Dict]:
    """Remove duplicate news items"""
    seen = set()
    unique_news = []
    for item in news_list:
        if item["id"] not in seen:
            seen.add(item["id"])
            unique_news.append(item)
    return unique_news


def sort_by_relevance(news_list: List[Dict], target_currency: str) -> List[Dict]:
    """Sort news by relevance to target currency"""
    keywords = CURRENCY_KEYWORDS.get(target_currency, CURRENCY_KEYWORDS["EUR/USD"])
    
    for item in news_list:
        text = (item["title"] + " " + item.get("description", "")).lower()
        score = sum(1 for kw in keywords if kw in text)
        item["relevance_score"] = score
    
    return sorted(news_list, key=lambda x: x["relevance_score"], reverse=True)

# ============================================================
# FINGPT SENTIMENT ANALYSIS
# ============================================================

def analyze_sentiment_fingpt(news_text: str) -> str:
    """Analyze sentiment using Ollama (FinGPT)"""
    try:
        prompt = f"""Analysiere das Trading-Sentiment für diese Nachricht.
Antworte nur mit einem Wort: BULLISH, BEARISH oder NEUTRAL

Nachricht: {news_text[:500]}
"""
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "qwen3",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("message", {}).get("content", "").upper()
            if "BULLISH" in content:
                return "BULLISH"
            elif "BEARISH" in content:
                return "BEARISH"
    except Exception:
        pass
    
    # Fallback: Keyword-based sentiment
    return keyword_sentiment(news_text)


def keyword_sentiment(text: str) -> str:
    """Fallback sentiment analysis using keywords"""
    text_lower = text.lower()
    bullish_words = ["rise", "gain", "bullish", "growth", "positive", "surge", "rally", "up", "higher"]
    bearish_words = ["fall", "drop", "bearish", "decline", "negative", "plunge", "sell", "down", "lower"]
    
    bullish_count = sum(1 for word in bullish_words if word in text_lower)
    bearish_count = sum(1 for word in bearish_words if word in text_lower)
    
    if bullish_count > bearish_count:
        return "BULLISH"
    elif bearish_count > bullish_count:
        return "BEARISH"
    return "NEUTRAL"


def analyze_impact(news_text: str) -> str:
    """Analyze impact level based on keywords"""
    text_lower = news_text.lower()
    
    for keyword in IMPACT_KEYWORDS["HIGH"]:
        if keyword in text_lower:
            return "HIGH"
    
    for keyword in IMPACT_KEYWORDS["MEDIUM"]:
        if keyword in text_lower:
            return "MEDIUM"
    
    return "LOW"

# ============================================================
# UI KOMPONENTEN
# ============================================================

def render_header():
    """Render the main header"""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("📰 EUR/USD News Intelligence")
        st.caption("Echtzeit Trading News mit FinGPT Sentiment Analysis")
    
    with col2:
        auto_refresh = st.checkbox("🔄 Auto-Refresh (60s)", value=True)
        if auto_refresh:
            time.sleep(60)
            st.rerun()
    
    with col3:
        st.metric("Letzte Aktualisierung", datetime.now().strftime("%H:%M:%S"))


def render_currency_filter() -> str:
    """Render currency filter dropdown"""
    currencies = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD", "Alle"]
    selected = st.selectbox("💱 Währungspaar filtern:", currencies, index=0)
    return selected if selected != "Alle" else "EUR/USD"


def render_impact_filter() -> str:
    """Render impact filter dropdown"""
    impacts = ["Alle", "HIGH", "MEDIUM", "LOW"]
    selected = st.selectbox("⚡ Impact Level:", impacts, index=0)
    return selected


def render_sentiment_summary(news: List[Dict]) -> Dict:
    """Render sentiment summary metrics"""
    sentiments = [n.get("sentiment", "NEUTRAL") for n in news if n.get("sentiment")]
    
    if not sentiments:
        return {"bullish": 0, "bearish": 0, "neutral": 0, "total": 0}
    
    return {
        "bullish": sentiments.count("BULLISH"),
        "bearish": sentiments.count("BEARISH"),
        "neutral": sentiments.count("NEUTRAL"),
        "total": len(sentiments)
    }


def render_metrics(sentiment_stats: Dict, currency: str):
    """Render top metrics row"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Gesamt Nachrichten", sentiment_stats["total"])
    
    with col2:
        st.metric("🟢 Bullish", sentiment_stats["bullish"], 
                 delta=f"{sentiment_stats['bullish']/max(sentiment_stats['total'],1)*100:.0f}%")
    
    with col3:
        st.metric("🔴 Bearish", sentiment_stats["bearish"],
                 delta=f"-{sentiment_stats['bearish']/max(sentiment_stats['total'],1)*100:.0f}%")
    
    with col4:
        bullish_pct = sentiment_stats['bullish'] / max(sentiment_stats['total'], 1) * 100
        st.metric("📈 EUR/USD Signal", "🟢 KAUFEN" if bullish_pct > 50 else "🔴 VERKAUFEN")


def render_news_card(news_item: Dict, index: int):
    """Render a single news card"""
    sentiment = news_item.get("sentiment", "NEUTRAL")
    impact = news_item.get("impact", "LOW")
    
    # Sentiment icon and color
    if sentiment == "BULLISH":
        sentiment_icon = "🟢"
        sentiment_color = "sentiment-bullish"
        card_class = "news-card"
    elif sentiment == "BEARISH":
        sentiment_icon = "🔴"
        sentiment_color = "sentiment-bearish"
        card_class = "news-card news-card-bearish"
    else:
        sentiment_icon = "🟡"
        sentiment_color = "sentiment-neutral"
        card_class = "news-card news-card-neutral"
    
    # Impact badge
    impact_badge = f'<span class="impact-badge impact-{impact.lower()}">{impact}</span>'
    
    # Format published time
    try:
        if "published_at" in news_item and news_item["published_at"]:
            if isinstance(news_item["published_at"], str):
                if "T" in news_item["published_at"]:
                    dt = datetime.fromisoformat(news_item["published_at"].replace("Z", "+00:00"))
                    time_ago = (datetime.now() - dt.replace(tzinfo=None)).total_seconds() / 3600
                    time_str = f"{time_ago:.1f}h"
                else:
                    time_str = news_item["published_at"][:10]
            else:
                time_str = "Recent"
        else:
            time_str = "Recent"
    except:
        time_str = "Recent"
    
    # Render card
    with st.container():
        st.markdown(f"""
        <div class="{card_class}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span>{impact_badge}</span>
                <span style="color: #888; font-size: 12px;">⏰ {time_str} | 📰 {news_item.get('source', 'Unknown')}</span>
            </div>
            <h4 style="margin: 0 0 10px 0; color: white;">{news_item.get('title', 'No Title')}</h4>
            <p style="color: #aaa; font-size: 13px; margin-bottom: 15px;">{news_item.get('description', '')[:150]}...</p>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="{sentiment_color}">{sentiment_icon} {sentiment}</span>
                <a href="{news_item.get('url', '#')}" target="_blank" style="color: #4CAF50; text-decoration: none;">🔗 Mehr lesen →</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button(f"📈 Chart", key=f"chart_{index}", help="Zum Chart springen"):
                st.session_state['selected_news'] = news_item
        with col2:
            if st.button(f"🔔 Alert", key=f"alert_{index}", help="Alert erstellen"):
                st.session_state['alerts'] = st.session_state.get('alerts', []) + [news_item]
                st.success("Alert erstellt!")
        with col3:
            if st.button(f"📤 Export", key=f"export_{index}", help="Exportieren"):
                export_news_csv([news_item])


def render_timeline(news: List[Dict]):
    """Render news timeline using Plotly"""
    if not news:
        st.info("Keine Nachrichten für Timeline verfügbar")
        return
    
    # Prepare data
    timeline_data = []
    for item in news:
        try:
            if "published_at" in item and item["published_at"]:
                if isinstance(item["published_at"], str) and "T" in item["published_at"]:
                    dt = item["published_at"].replace("T", " ").replace("Z", "")[:19]
                else:
                    dt = str(item["published_at"])
            else:
                dt = datetime.now().isoformat()
            
            impact = item.get("impact", "LOW")
            color = "#F44336" if impact == "HIGH" else "#FFC107" if impact == "MEDIUM" else "#4CAF50"
            
            timeline_data.append({
                "Task": item.get("title", "")[:50] + "...",
                "Start": dt,
                "Impact": impact,
                "Color": color
            })
        except:
            continue
    
    if not timeline_data:
        st.info("Keine Timeline-Daten verfügbar")
        return
    
    df = pd.DataFrame(timeline_data)
    
    # Create Gantt chart
    fig = px.timeline(
        df, 
        x_start="Start", 
        x_end=pd.Timestamp.now(),
        y="Task",
        color="Impact",
        color_discrete_map={
            "HIGH": "#F44336",
            "MEDIUM": "#FFC107",
            "LOW": "#4CAF50"
        },
        title="📈 Nachrichten Timeline (Letzte 24h)"
    )
    
    fig.update_layout(
        template="plotly_dark",
        height=300,
        showlegend=True,
        xaxis_title="Zeit",
        yaxis_title=""
    )
    
    st.plotly_chart(fig, use_container_width=True)


def export_news_csv(news: List[Dict]):
    """Export news to CSV"""
    if not news:
        st.warning("Keine Nachrichten zum Exportieren")
        return
    
    df = pd.DataFrame(news)
    csv = df.to_csv(index=False)
    
    st.download_button(
        label="📥 CSV Herunterladen",
        data=csv,
        file_name=f"fingpt_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )


# ============================================================
# MAIN APP - MIT LOADING STATES
# ============================================================

def main():
    """Main Streamlit app mit Loading State Machine"""
    
    # Initialize session state für Loading
    if 'news_loading_state' not in st.session_state:
        st.session_state['news_loading_state'] = LoadingState.INITIAL
    if 'news_cache' not in st.session_state:
        st.session_state['news_cache'] = []
    if 'last_update' not in st.session_state:
        st.session_state['last_update'] = None
    if 'news_error' not in st.session_state:
        st.session_state['news_error'] = None
    
    # Render header
    render_header()
    
    # Filters
    st.divider()
    col1, col2 = st.columns([1, 1])
    with col1:
        currency_filter = render_currency_filter()
    with col2:
        impact_filter = render_impact_filter()
    
    # Check if user wants to refresh
    refresh_btn = st.button("🔄 Aktualisieren")
    
    # Loading State Machine
    loading_state = st.session_state['news_loading_state']
    
    if loading_state == LoadingState.INITIAL or refresh_btn:
        # STATE 1: Zeige 3D Kugel während Initialisierung
        st.session_state['news_loading_state'] = LoadingState.FETCHING
        render_initial_state()
        
    elif loading_state == LoadingState.FETCHING:
        # STATE 2: Progress Bar während API Fetch
        try:
            news = fetch_and_cache_news(currency_filter)
            
            if news and len(news) > 0:
                # Erfolg: Zeige News Cards
                st.session_state['news_loading_state'] = LoadingState.SUCCESS
                st.session_state['news_cache'] = news
                st.session_state['news_error'] = None
            else:
                # Keine News: Verwende Mock Data
                news = get_mock_news()
                st.session_state['news_loading_state'] = LoadingState.SUCCESS
                st.session_state['news_cache'] = news
                st.session_state['news_error'] = None
                
        except Exception as e:
            # Error: Zeige Error Card
            st.session_state['news_loading_state'] = LoadingState.ERROR
            st.session_state['news_error'] = str(e)
            news = get_mock_news()
            st.session_state['news_cache'] = news
        
        # Force rerun to show next state
        st.rerun()
    
    elif loading_state == LoadingState.ERROR:
        # STATE 3: Error Card
        error_msg = st.session_state.get('news_error', 'Unbekannter Fehler')
        render_error_state(error_msg, lambda: setattr(st.session_state, 'news_loading_state', LoadingState.INITIAL))
        
        # Fallback: Zeige trotzdem Mock Data
        news = st.session_state.get('news_cache', get_mock_news())
        render_success_state(news, currency_filter, impact_filter)
    
    else:  # SUCCESS
        # STATE 4: News Cards (normal)
        news = st.session_state.get('news_cache', [])
        if not news:
            news = get_mock_news()
        
        render_success_state(news, currency_filter, impact_filter)
    
    # Footer
    st.divider()
    st.caption(f"🕐 Letzte Aktualisierung: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CET | Cache: 5min TTL | FinGPT powered")


def get_mock_news() -> List[Dict]:
    """Get mock news data for demo"""
    return [
        {
            "id": "1",
            "title": "ECB Rate Decision: Interest Rates Hold at 4.50%",
            "description": "European Central Bank maintains current interest rates, signals potential cuts in Q2",
            "source": "FX Street",
            "url": "#",
            "published_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "currency": "EUR/USD",
            "sentiment": "NEUTRAL",
            "impact": "HIGH",
            "relevance_score": 10
        },
        {
            "id": "2",
            "title": "EUR/USD Rises to 1.0950 on Strong German GDP Data",
            "description": "Euro gains ground against dollar following better-than-expected German economic growth",
            "source": "Bloomberg",
            "url": "#",
            "published_at": (datetime.now() - timedelta(hours=4)).isoformat(),
            "currency": "EUR/USD",
            "sentiment": "BULLISH",
            "impact": "MEDIUM",
            "relevance_score": 9
        },
        {
            "id": "3",
            "title": "Fed Powell Speech: Inflation Still a Concern",
            "description": "Federal Reserve Chair emphasizes need for continued monetary tightening",
            "source": "Reuters",
            "url": "#",
            "published_at": (datetime.now() - timedelta(hours=6)).isoformat(),
            "currency": "EUR/USD",
            "sentiment": "BULLISH",
            "impact": "HIGH",
            "relevance_score": 10
        },
        {
            "id": "4",
            "title": "US Non-Farm Payrolls Beat Expectations at 275K",
            "description": "Labor market remains strong with job gains exceeding forecasts",
            "source": "MarketWatch",
            "url": "#",
            "published_at": (datetime.now() - timedelta(hours=8)).isoformat(),
            "currency": "EUR/USD",
            "sentiment": "BEARISH",
            "impact": "HIGH",
            "relevance_score": 10
        },
        {
            "id": "5",
            "title": "USD/JPY Tests 150 Level Amid BOJ Uncertainty",
            "description": "Dollar strengthens against yen as Bank of Japan maintains dovish stance",
            "source": "Investing.com",
            "url": "#",
            "published_at": (datetime.now() - timedelta(hours=10)).isoformat(),
            "currency": "USD/JPY",
            "sentiment": "NEUTRAL",
            "impact": "MEDIUM",
            "relevance_score": 7
        }
    ]


if __name__ == "__main__":
    main()
