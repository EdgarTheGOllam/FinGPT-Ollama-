import customtkinter as ctk
import threading
import json
import logging
import re
import os
import time
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional

try:
    import requests
    import feedparser
    NEWSAPI_AVAILABLE = True
except ImportError:
    NEWSAPI_AVAILABLE = False

# ============================================================
# KONFIGURATION
# ============================================================

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

CURRENCY_KEYWORDS = {
    "EUR": ["eur/usd", "euro", "ecb", "european central bank", "eurozone", "eurusd"],
    "GBP": ["gbp/usd", "pound", "bank of england", "gbpusd"],
    "USD": ["usd", "dollar", "fed", "federal reserve"],
    "JPY": ["usd/jpy", "yen", "bank of japan", "nikkei", "usdjpy"],
    "CHF": ["usd/chf", "swiss", "snb"],
    "AUD": ["aud/usd", "australian", "rba"],
    "CAD": ["usd/cad", "canadian", "bank of canada"],
    "NZD": ["nzd/usd", "new zealand", "rbnz"]
}

IMPACT_KEYWORDS = {
    "HIGH": ["ecb", "fed", "fomc", "interest rate", "rate decision", "non-farm", "nfp", 
             "gdp", "cpi", "inflation", "speech", "press conference", "governor"],
    "MEDIUM": ["retail sales", "unemployment", "ppi", "trade balance", "consumer confidence", 
               "manufacturing pmi", "housing starts"],
    "LOW": ["initial claims", "philly fed", "michigan sentiment"]
}


class NewsView:
    def __init__(self, tab, app):
        """
        tab: The ctk.CTkFrame inside the Tabview where this view is rendered.
        app: The ModernFinGPTGUI instance, used to access shared state and methods.
        """
        self.tab = tab
        self.app = app
        
        # State
        self._news_items = []
        self._news_analyzing = False
        self._news_filter_pair = "Alle"
        self._cal_items = []
        self._auto_refresh = False
        self._auto_refresh_interval = 60  # seconds
        
        # UI Elements
        self._news_refresh_btn = None
        self._news_analyze_btn = None
        self._news_filter_btns = {}
        self._news_status_lbl = None
        self._news_scroll = None
        self._cal_impact_var = None
        self._cal_status_lbl = None
        self._cal_scroll = None
        self._sentiment_label = None
        self._signal_label = None
        self._auto_refresh_btn = None
        
        # Metrics labels
        self._metric_bullish = None
        self._metric_bearish = None
        self._metric_neutral = None
        
        self.setup_ui()

    def setup_ui(self):
        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_rowconfigure(0, weight=1)

        # ── Sub-Tabview ──────────────────────────────────────
        news_sub = ctk.CTkTabview(self.tab, corner_radius=12)
        news_sub.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        news_sub.add("📡 News Feed")
        news_sub.add("📅 Wirtschaftskalender")
        news_sub.add("📊 Analytics")

        # ═══════════════════ NEWS FEED SUB-TAB ═══════════════════
        nf_tab = news_sub.tab("📡 News Feed")
        nf_tab.grid_columnconfigure(0, weight=1)
        nf_tab.grid_rowconfigure(1, weight=1)
        nf_tab.grid_rowconfigure(2, weight=0)  # Metrics row

        # ═══ METRICS ROW ═══
        metrics_frame = ctk.CTkFrame(nf_tab, fg_color="#1A1D24", corner_radius=12)
        metrics_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        metrics_frame.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="metric")
        
        # Sentiment Summary
        ctk.CTkLabel(metrics_frame, text="📊 Gesamt", text_color="#8B949E").grid(row=0, column=0, padx=10, pady=10)
        self._metric_bullish = ctk.CTkLabel(metrics_frame, text="🟢 0", text_color="#4CAF50", font=ctk.CTkFont(size=16, weight="bold"))
        self._metric_bullish.grid(row=0, column=1, padx=10)
        self._metric_bearish = ctk.CTkLabel(metrics_frame, text="🔴 0", text_color="#F44336", font=ctk.CTkFont(size=16, weight="bold"))
        self._metric_bearish.grid(row=0, column=2, padx=10)
        self._metric_neutral = ctk.CTkLabel(metrics_frame, text="🟡 0", text_color="#FFC107", font=ctk.CTkFont(size=16, weight="bold"))
        self._metric_neutral.grid(row=0, column=3, padx=10)
        
        # EUR/USD Signal
        self._signal_label = ctk.CTkLabel(metrics_frame, text="📈 EUR/USD: --", text_color="#2979FF", font=ctk.CTkFont(size=16, weight="bold"))
        self._signal_label.grid(row=0, column=4, padx=10)

        # ═══ CONTROLS ROW ═══
        ctrl = ctk.CTkFrame(nf_tab, fg_color="transparent")
        ctrl.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 0))

        self._news_refresh_btn = ctk.CTkButton(
            ctrl, text="🔄 News Laden", width=130,
            fg_color="#2979FF", hover_color="#21618C",
            command=self._fetch_news_threaded)
        self._news_refresh_btn.pack(side="left", padx=(0, 8))

        self._news_analyze_btn = ctk.CTkButton(
            ctrl, text="🤖 Alle Analysieren", width=150,
            fg_color="#8E44AD", hover_color="#6C3483",
            command=self._analyze_all_news_threaded)
        self._news_analyze_btn.pack(side="left", padx=(0, 14))

        # Auto-refresh toggle
        self._auto_refresh_btn = ctk.CTkButton(
            ctrl, text="🔁 Auto (60s)", width=100,
            fg_color="#2A2D34", hover_color="#21618C",
            command=self._toggle_auto_refresh)
        self._auto_refresh_btn.pack(side="left", padx=(0, 8))

        # Export button
        ctk.CTkButton(
            ctrl, text="📥 Export CSV", width=100,
            fg_color="#4CAF50", hover_color="#388E3C",
            command=self._export_csv).pack(side="left", padx=(0, 14))

        ctk.CTkLabel(ctrl, text="Filter:", text_color="#8B949E").pack(side="left", padx=(0, 4))
        for pair in ["Alle", "EUR", "GBP", "USD", "JPY", "CHF", "AUD", "CAD", "NZD"]:
            btn = ctk.CTkButton(ctrl, text=pair, width=52, height=26,
                                fg_color="#2979FF" if pair == "Alle" else "#2A2D34",
                                hover_color="#21618C",
                                command=lambda p=pair: self._news_filter(p))
            btn.pack(side="left", padx=2)
            self._news_filter_btns[pair] = btn

        self._news_status_lbl = ctk.CTkLabel(ctrl, text="● Bereit", text_color="#8B949E",
                                              font=ctk.CTkFont(family="Inter", size=11))
        self._news_status_lbl.pack(side="right", padx=15)

        # ═══ NEWS SCROLL ═══
        self._news_scroll = ctk.CTkScrollableFrame(nf_tab, fg_color="#1A1D24", corner_radius=12)
        self._news_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self._news_scroll.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._news_scroll,
                     text="🔄  Klicke 'News Laden' um aktuelle Forex-Nachrichten zu laden.\n\nOder aktiviere 'Auto' für Live-Updates alle 60 Sekunden.",
                     font=ctk.CTkFont(family="Inter", size=13), text_color="#8B949E").pack(pady=40)

        # ═══════════════ WIRTSCHAFTSKALENDER SUB-TAB ═════════════
        cal_tab = news_sub.tab("📅 Wirtschaftskalender")
        cal_tab.grid_columnconfigure(0, weight=1)
        cal_tab.grid_rowconfigure(2, weight=1)

        cal_ctrl = ctk.CTkFrame(cal_tab, fg_color="transparent")
        cal_ctrl.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))

        ctk.CTkButton(cal_ctrl, text="🔄 Kalender Laden", width=150, height=28,
                      fg_color="#2979FF", hover_color="#21618C",
                      command=self._fetch_calendar_threaded).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(cal_ctrl, text="Impact:", text_color="#8B949E").pack(side="left", padx=(0, 4))
        self._cal_impact_var = ctk.StringVar(value="Alle")
        for impact in ["Alle", "Hoch", "Mittel", "Niedrig"]:
            ctk.CTkButton(cal_ctrl, text=impact, width=60, height=26,
                          fg_color="#2A2D34", hover_color="#21618C",
                          command=lambda iv=impact: self._cal_filter(iv)).pack(side="left", padx=2)

        self._cal_status_lbl = ctk.CTkLabel(cal_ctrl, text="● Bereit", text_color="#8B949E",
                                             font=ctk.CTkFont(family="Inter", size=11))
        self._cal_status_lbl.pack(side="right", padx=15)

        # Table header
        cal_hdr = ctk.CTkFrame(cal_tab, fg_color="#1A1D24", corner_radius=8, height=32)
        cal_hdr.grid(row=1, column=0, sticky="ew", padx=10, pady=(4, 0))
        cal_hdr.grid_columnconfigure((0,1,2,3,4,5), weight=1, uniform="ch")
        cal_hdr.grid_propagate(False)
        for ci, ch in enumerate(["Zeit", "Währung", "Impact", "Event", "Prognose", "Sentiment"]):
            ctk.CTkLabel(cal_hdr, text=ch, font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                         text_color="#8B949E").grid(row=0, column=ci, sticky="w", padx=8, pady=6)

        self._cal_scroll = ctk.CTkScrollableFrame(cal_tab, fg_color="transparent", corner_radius=0)
        self._cal_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self._cal_scroll.grid_columnconfigure((0,1,2,3,4,5), weight=1, uniform="ch")
        ctk.CTkLabel(self._cal_scroll, text="Keine Termine geladen.", text_color="#8B949E").grid(row=0, column=0, columnspan=6, pady=20)

        # ═══════════════ ANALYTICS SUB-TAB ═════════════
        analytics_tab = news_sub.tab("📊 Analytics")
        analytics_tab.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(analytics_tab, text="📈 Sentiment Verteilung", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        ctk.CTkLabel(analytics_tab, text="(Timeline Visualization Coming Soon)", text_color="#8B949E").pack()

    # ═══════════════════════════════════════════════════════
    # AUTO REFRESH
    # ═══════════════════════════════════════════════════════
    
    def _toggle_auto_refresh(self):
        """Toggle auto-refresh mode"""
        self._auto_refresh = not self._auto_refresh
        if self._auto_refresh:
            self._auto_refresh_btn.configure(fg_color="#4CAF50", text="⏹️ Stop")
            self._news_status_lbl.configure(text="● Auto-Refresh aktiv", text_color="#4CAF50")
            self._start_auto_refresh()
        else:
            self._auto_refresh_btn.configure(fg_color="#2A2D34", text="🔁 Auto (60s)")
            self._news_status_lbl.configure(text="● Bereit", text_color="#8B949E")

    def _start_auto_refresh(self):
        """Start auto-refresh loop"""
        if self._auto_refresh:
            self._fetch_news_threaded()
            # Schedule next refresh
            self.tab.after(self._auto_refresh_interval * 1000, self._start_auto_refresh)

    # ═══════════════════════════════════════════════════════
    # NEWS FETCHING
    # ═══════════════════════════════════════════════════════
    
    def _fetch_news_threaded(self):
        if self._news_analyzing:
            return
        self._news_refresh_btn.configure(state="disabled", text="⏳ Lade...")
        self._news_status_lbl.configure(text="● Lade Nachrichten...", text_color="#E67E22")
        threading.Thread(target=self._fetch_news_bg, daemon=True).start()

    def _fetch_news_bg(self):
        """Background news fetching with real API calls"""
        news_items = []
        
        try:
            # NewsAPI
            if NEWSAPI_KEY and NEWSAPI_AVAILABLE:
                try:
                    url = "https://newsapi.org/v2/everything"
                    params = {
                        "q": "forex OR currency OR EUR/USD OR trading",
                        "apiKey": NEWSAPI_KEY,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 20
                    }
                    response = requests.get(url, params=params, timeout=10)
                    data = response.json()
                    
                    for article in data.get("articles", []):
                        news_items.append({
                            "id": hashlib.md5(article["url"].encode()).hexdigest(),
                            "title": article["title"],
                            "description": article.get("description", "")[:200],
                            "source": article["source"]["name"],
                            "url": article["url"],
                            "published_at": article.get("publishedAt", ""),
                            "currency": self._detect_currency(article["title"] + " " + article.get("description", "")),
                            "sentiment": None,
                            "impact": None
                        })
                except Exception as e:
                    logging.warning(f"NewsAPI error: {e}")
            
            # Finnhub
            if FINNHUB_KEY and NEWSAPI_AVAILABLE:
                try:
                    url = f"https://finnhub.io/api/v1/news?category=forex&token={FINNHUB_KEY}"
                    response = requests.get(url, timeout=10)
                    data = response.json()
                    
                    for item in data[:15]:
                        news_items.append({
                            "id": str(item.get("id", "")),
                            "title": item.get("headline", ""),
                            "description": item.get("summary", "")[:200],
                            "source": item.get("source", "Finnhub"),
                            "url": item.get("url", ""),
                            "published_at": datetime.fromtimestamp(item.get("datetime", 0)).isoformat() if item.get("datetime") else "",
                            "currency": self._detect_currency(item.get("headline", "") + " " + item.get("summary", "")),
                            "sentiment": None,
                            "impact": None
                        })
                except Exception as e:
                    logging.warning(f"Finnhub error: {e}")
            
            # RSS Fallback
            if not news_items and NEWSAPI_AVAILABLE:
                rss_urls = [
                    "https://www.forexstreet.net/news/rss",
                    "https://www.investing.com/rss/news.rss"
                ]
                for rss_url in rss_urls:
                    try:
                        feed = feedparser.parse(rss_url)
                        for entry in feed.entries[:10]:
                            news_items.append({
                                "id": hashlib.md5(entry.link.encode()).hexdigest(),
                                "title": entry.get("title", ""),
                                "description": entry.get("summary", "")[:200],
                                "source": feed.feed.get("title", "RSS"),
                                "url": entry.get("link", ""),
                                "published_at": entry.get("published", ""),
                                "currency": self._detect_currency(entry.get("title", "") + " " + entry.get("summary", "")),
                                "sentiment": None,
                                "impact": None
                            })
                    except:
                        continue
            
        except Exception as e:
            logging.error(f"News fetch error: {e}")
        
        # Use mock data if no news fetched
        if not news_items:
            news_items = self._get_mock_news()
        
        # Deduplicate
        seen = set()
        unique_news = []
        for item in news_items:
            if item["id"] not in seen:
                seen.add(item["id"])
                unique_news.append(item)
        
        self._news_items = unique_news[:50]
        self.app.after(0, self._on_news_fetched)

    def _detect_currency(self, text: str) -> str:
        """Detect currency from text"""
        text_lower = text.lower()
        for currency, keywords in CURRENCY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return currency
        return "USD"

    def _get_mock_news(self) -> List[Dict]:
        """Get mock news for demo/offline"""
        return [
            {"id": "1", "title": "ECB Rate Decision: Interest Rates Hold at 4.50%", 
             "description": "European Central Bank maintains current rates", "source": "FX Street",
             "url": "#", "published_at": (datetime.now() - timedelta(hours=2)).isoformat(),
             "currency": "EUR", "sentiment": "Neutral", "impact": "HIGH"},
            {"id": "2", "title": "EUR/USD Rises to 1.0950 on Strong German GDP", 
             "description": "Euro gains on better-than-expected growth", "source": "Bloomberg",
             "url": "#", "published_at": (datetime.now() - timedelta(hours=4)).isoformat(),
             "currency": "EUR", "sentiment": "Bullish", "impact": "MEDIUM"},
            {"id": "3", "title": "Fed Powell: Inflation Still a Concern", 
             "description": "Federal Reserve emphasizes tightening", "source": "Reuters",
             "url": "#", "published_at": (datetime.now() - timedelta(hours=6)).isoformat(),
             "currency": "USD", "sentiment": "Bearish", "impact": "HIGH"},
            {"id": "4", "title": "US Non-Farm Payrolls Beat at 275K", 
             "description": "Labor market remains strong", "source": "MarketWatch",
             "url": "#", "published_at": (datetime.now() - timedelta(hours=8)).isoformat(),
             "currency": "USD", "sentiment": "Bearish", "impact": "HIGH"},
            {"id": "5", "title": "USD/JPY Tests 150 Level", 
             "description": "Dollar strengthens on BOJ uncertainty", "source": "Investing",
             "url": "#", "published_at": (datetime.now() - timedelta(hours=10)).isoformat(),
             "currency": "JPY", "sentiment": "Neutral", "impact": "MEDIUM"}
        ]

    def _on_news_fetched(self):
        self._news_refresh_btn.configure(state="normal", text="🔄 News Laden")
        if self._auto_refresh:
            self._news_status_lbl.configure(text=f"● Auto: {datetime.now().strftime('%H:%M:%S')}", text_color="#4CAF50")
        else:
            self._news_status_lbl.configure(text="● Aktuell", text_color="#00FF66")
        self._render_news_feed()
        self._update_sentiment_metrics()

    # ═══════════════════════════════════════════════════════
    # SENTIMENT ANALYSIS
    # ═══════════════════════════════════════════════════════
    
    def _analyze_all_news_threaded(self):
        if not self._news_items:
            self._fetch_news_threaded()
            return
        if self._news_analyzing:
            return
        self._news_analyzing = True
        self._news_analyze_btn.configure(state="disabled", text="⏳ Analysiere...")
        self._news_status_lbl.configure(text="● KI analysiert...", text_color="#8E44AD")
        threading.Thread(target=self._analyze_all_news_bg, daemon=True).start()

    def _analyze_all_news_bg(self):
        """Background sentiment analysis with Ollama"""
        for idx, item in enumerate(self._news_items):
            if not self._news_analyzing:
                break
            
            text = item.get("title", "") + " " + item.get("description", "")
            
            # Try Ollama first
            sentiment = self._analyze_sentiment_ollama(text)
            if not sentiment:
                sentiment = self._keyword_sentiment(text)
            
            impact = self._analyze_impact(text)
            
            self._news_items[idx]["sentiment"] = sentiment
            self._news_items[idx]["impact"] = impact
            
            self.app.after(0, self._render_news_feed)
            time.sleep(0.3)
        
        self.app.after(0, self._on_news_analyzed)

    def _analyze_sentiment_ollama(self, text: str) -> Optional[str]:
        """Analyze sentiment using Ollama"""
        try:
            prompt = f"""Analysiere das Trading-Sentiment.
Antworte nur: BULLISH, BEARISH oder NEUTRAL
            
Nachricht: {text[:300]}"""
            
            response = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": "qwen3", "messages": [{"role": "user", "content": prompt}], "stream": False},
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "").upper()
                if "BULLISH" in content:
                    return "Bullish"
                elif "BEARISH" in content:
                    return "Bearish"
        except:
            pass
        return None

    def _keyword_sentiment(self, text: str) -> str:
        """Fallback keyword-based sentiment"""
        text_lower = text.lower()
        bullish = sum(1 for w in ["rise", "gain", "bullish", "growth", "positive", "surge", "rally"] if w in text_lower)
        bearish = sum(1 for w in ["fall", "drop", "bearish", "decline", "negative", "plunge", "sell"] if w in text_lower)
        
        if bullish > bearish:
            return "Bullish"
        elif bearish > bullish:
            return "Bearish"
        return "Neutral"

    def _analyze_impact(self, text: str) -> str:
        """Analyze impact level"""
        text_lower = text.lower()
        for kw in IMPACT_KEYWORDS["HIGH"]:
            if kw in text_lower:
                return "HIGH"
        for kw in IMPACT_KEYWORDS["MEDIUM"]:
            if kw in text_lower:
                return "MEDIUM"
        return "LOW"

    def _on_news_analyzed(self):
        self._news_analyzing = False
        self._news_status_lbl.configure(text="● KI Analyse abgeschlossen", text_color="#00FF66")
        self._news_analyze_btn.configure(state="normal", text="🤖 Alle Analysieren")
        self._render_news_feed()
        self._update_sentiment_metrics()

    def _update_sentiment_metrics(self):
        """Update sentiment metrics display"""
        sentiments = [n.get("sentiment", "Neutral") for n in self._news_items if n.get("sentiment")]
        
        bullish = sentiments.count("Bullish")
        bearish = sentiments.count("Bearish")
        neutral = sentiments.count("Neutral")
        total = len(sentiments) if sentiments else 1
        
        self._metric_bullish.configure(text=f"🟢 {bullish}")
        self._metric_bearish.configure(text=f"🔴 {bearish}")
        self._metric_neutral.configure(text=f"🟡 {neutral}")
        
        # EUR/USD Signal
        if bullish > bearish:
            signal = "🟢 KAUFEN"
        elif bearish > bullish:
            signal = "🔴 VERKAUFEN"
        else:
            signal = "🟡 NEUTRAL"
        
        bullish_pct = bullish / total * 100
        self._signal_label.configure(text=f"📈 EUR/USD: {signal} ({bullish_pct:.0f}%)")

    # ═══════════════════════════════════════════════════════
    # UI RENDERING
    # ═══════════════════════════════════════════════════════
    
    def _news_filter(self, pair):
        self._news_filter_pair = pair
        for p, btn in self._news_filter_btns.items():
            btn.configure(fg_color="#2979FF" if p == pair else "#2A2D34")
        self._render_news_feed()

    def _render_news_feed(self):
        for w in self._news_scroll.winfo_children():
            w.destroy()
        
        filtered = [n for n in self._news_items if self._news_filter_pair == "Alle" or n.get("currency") == self._news_filter_pair]
        
        if not filtered:
            ctk.CTkLabel(self._news_scroll, text="Keine Nachrichten für diesen Filter.", 
                        text_color="#8B949E").pack(pady=40)
            return

        for npap in filtered:
            f = ctk.CTkFrame(self._news_scroll, fg_color="#1A1D24", corner_radius=8)
            f.pack(fill="x", pady=6, padx=4)
            
            # Header
            hdr = ctk.CTkFrame(f, fg_color="transparent")
            hdr.pack(fill="x", padx=15, pady=(15, 5))
            
            # Currency & Time
            curr = npap.get("currency", "N/A")
            ctk.CTkLabel(hdr, text=curr, font=ctk.CTkFont(weight="bold"), 
                        fg_color="#3498DB", text_color="#FFFFFF", corner_radius=4, width=40).pack(side="left")
            
            # Impact Badge
            impact = npap.get("impact", "LOW")
            icol = "#F44336" if impact == "HIGH" else "#FFC107" if impact == "MEDIUM" else "#4CAF50"
            ctk.CTkLabel(hdr, text=f"⚡{impact}", text_color=icol, font=ctk.CTkFont(weight="bold", size=11)).pack(side="left", padx=8)
            
            # Time
            try:
                if npap.get("published_at"):
                    dt = datetime.fromisoformat(npap["published_at"].replace("Z", "+00:00"))
                    time_ago = (datetime.now() - dt.replace(tzinfo=None)).total_seconds() / 3600
                    time_str = f"{time_ago:.1f}h"
                else:
                    time_str = "Recent"
            except:
                time_str = "Recent"
            
            ctk.CTkLabel(hdr, text=time_str, text_color="#8B949E", font=ctk.CTkFont(size=11)).pack(side="left", padx=10)
            
            # Sentiment
            sent = npap.get("sentiment", "Neutral")
            scol = "#4CAF50" if sent == "Bullish" else "#F44336" if sent == "Bearish" else "#FFC107"
            sent_icon = "🟢" if sent == "Bullish" else "🔴" if sent == "Bearish" else "🟡"
            ctk.CTkLabel(hdr, text=f"{sent_icon} {sent}", text_color=scol, font=ctk.CTkFont(weight="bold")).pack(side="right")
            
            # Title
            ctk.CTkLabel(f, text=npap.get("title", ""), font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                         anchor="w", justify="left").pack(fill="x", padx=15, pady=(5, 5))
            
            # Description
            ctk.CTkLabel(f, text=npap.get("description", "")[:150] + "...", text_color="#8B949E", 
                         anchor="w", justify="left").pack(fill="x", padx=15, pady=(0, 15))

    # ═══════════════════════════════════════════════════════
    # CALENDAR
    # ═══════════════════════════════════════════════════════
    
    def _fetch_calendar_threaded(self):
        self._cal_status_lbl.configure(text="● Lade Kalender...", text_color="#E67E22")
        threading.Thread(target=self._fetch_calendar_bg, daemon=True).start()

    def _fetch_calendar_bg(self):
        import time
        time.sleep(0.5)
        
        # Get economic events (mock data with real API structure)
        self._cal_items = [
            {"time": "14:30", "currency": "USD", "impact": "Hoch", "event": "Non-Farm Payrolls", "forecast": "200K / 180K", "sentiment": "Bearish"},
            {"time": "14:30", "currency": "EUR", "impact": "Hoch", "event": "ECB Rate Decision", "forecast": "4.50%", "sentiment": "Neutral"},
            {"time": "10:00", "currency": "EUR", "impact": "Mittel", "event": "German GDP", "forecast": "0.2%", "sentiment": "Bullish"},
            {"time": "09:30", "currency": "GBP", "impact": "Mittel", "event": "Retail Sales", "forecast": "0.3%", "sentiment": "Neutral"},
            {"time": "13:30", "currency": "USD", "impact": "Mittel", "event": "CPI Data", "forecast": "3.2%", "sentiment": "Bearish"},
            {"time": "15:00", "currency": "USD", "impact": "Niedrig", "event": "Michigan Sentiment", "forecast": "72", "sentiment": "Neutral"}
        ]
        self.app.after(0, self._on_calendar_fetched)

    def _on_calendar_fetched(self):
        self._cal_status_lbl.configure(text="● Aktuell", text_color="#00FF66")
        self._cal_filter(self._cal_impact_var.get())

    def _cal_filter(self, impact_filter: str):
        self._cal_impact_var.set(impact_filter)
        impact_map = {"Hoch": "HIGH", "Mittel": "MEDIUM", "Niedrig": "LOW"}
        
        if impact_filter == "Alle":
            self._render_calendar_rows(self._cal_items)
        else:
            mapped = impact_map.get(impact_filter, "LOW")
            filtered = [e for e in self._cal_items if e["impact"] == mapped]
            self._render_calendar_rows(filtered)

    def _render_calendar_rows(self, items):
        for w in self._cal_scroll.winfo_children():
            w.destroy()
        
        if not items:
            ctk.CTkLabel(self._cal_scroll, text="Keine Termine für diesen Filter.", 
                        text_color="#8B949E").grid(row=0, column=0, columnspan=6, pady=20)
            return
            
        for i, ev in enumerate(items):
            bg = ("gray95", "gray14") if i % 2 == 0 else "transparent"
            row_f = ctk.CTkFrame(self._cal_scroll, fg_color=bg, corner_radius=4, height=36)
            row_f.grid(row=i, column=0, columnspan=6, sticky="ew", pady=2)
            row_f.grid_columnconfigure((0,1,2,3,4,5), weight=1, uniform="ch")
            row_f.grid_propagate(False)
            
            ctk.CTkLabel(row_f, text=ev.get("time",""), text_color=("gray20","gray80")).grid(row=0, column=0, padx=8)
            ctk.CTkLabel(row_f, text=ev.get("currency",""), font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=8)
            
            imp = ev.get("impact", "LOW")
            icol = "#F44336" if imp == "HIGH" else "#FFC107" if imp == "MEDIUM" else "#4CAF50"
            ctk.CTkLabel(row_f, text=imp, text_color=icol, font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=8)
            
            ctk.CTkLabel(row_f, text=ev.get("event",""), anchor="w").grid(row=0, column=3, sticky="w", padx=8)
            ctk.CTkLabel(row_f, text=ev.get("forecast","")).grid(row=0, column=4, padx=8)
            
            # Sentiment
            sent = ev.get("sentiment", "Neutral")
            scol = "#4CAF50" if sent == "Bullish" else "#F44336" if sent == "Bearish" else "#FFC107"
            ctk.CTkLabel(row_f, text=sent, text_color=scol, font=ctk.CTkFont(weight="bold")).grid(row=0, column=5, padx=8)

    # ═══════════════════════════════════════════════════════
    # EXPORT
    # ═══════════════════════════════════════════════════════
    
    def _export_csv(self):
        """Export news to CSV"""
        if not self._news_items:
            return
        
        try:
            import csv
            from datetime import datetime
            
            filename = f"fingpt_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['title', 'source', 'currency', 'sentiment', 'impact', 'published_at'])
                writer.writeheader()
                
                for item in self._news_items:
                    writer.writerow({
                        'title': item.get('title', ''),
                        'source': item.get('source', ''),
                        'currency': item.get('currency', ''),
                        'sentiment': item.get('sentiment', ''),
                        'impact': item.get('impact', ''),
                        'published_at': item.get('published_at', '')
                    })
            
            self._news_status_lbl.configure(text=f"● Export: {filename}", text_color="#4CAF50")
        except Exception as e:
            logging.error(f"Export error: {e}")
