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

# Import Design System für konsistente UI-Gestaltung
from gui.design_system import DesignSystem

try:
    import requests
    import feedparser
    NEWSAPI_AVAILABLE = True
except ImportError:
    NEWSAPI_AVAILABLE = False

# Design System Shortcuts für bessere Lesbarkeit
ds = DesignSystem
COLORS = ds.COLORS
SEMANTIC = ds.SEMANTIC
SPACING = ds.SPACING
RADIUS = ds.RADIUS

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
        
        # Trading News Filter UI Elements
        self.news_filter_switch = None
        self.news_high = None
        self.news_medium = None
        self.news_low = None
        self.news_before_slider = None
        self.news_before_lbl = None
        self.news_after_slider = None
        self.news_after_lbl = None
        
        # Metrics labels
        self._metric_bullish = None
        self._metric_bearish = None
        self._metric_neutral = None
        
        self.setup_ui()
        
        # Lade den Kalender initial beim Start (verzögert, um RuntimeError zu vermeiden)
        self.app.after(1000, self._fetch_calendar_threaded)

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
        nf_tab.grid_rowconfigure(0, weight=0)  # Metrics row - no expand
        nf_tab.grid_rowconfigure(1, weight=0)  # Controls row - compact
        nf_tab.grid_rowconfigure(2, weight=1)  # News scroll - expand!

        # ═══ METRICS ROW (GANZ OBEN - KOMPAKT) ═══
        metrics_frame = ctk.CTkFrame(
            nf_tab, 
            fg_color=SEMANTIC['surface'], 
            corner_radius=RADIUS['lg'], 
            height=36
        )
        metrics_frame.grid(row=0, column=0, sticky="ew", padx=SPACING['sm'], pady=(SPACING['xs'], 0))
        metrics_frame.grid_columnconfigure((0,1,2,3), weight=1, uniform="metric")
        metrics_frame.grid_propagate(False)
        
        # Sentiment Summary - Kompakt
        ctk.CTkLabel(
            metrics_frame, text="📊", 
            text_color=COLORS['neutral']['light'], 
            font=ds.get_font('xs')
        ).grid(row=0, column=0, padx=SPACING['xs'], pady=SPACING['xs'])
        
        self._metric_bullish = ctk.CTkLabel(
            metrics_frame, text="🟢0", 
            text_color=COLORS['success']['base'], 
            font=ds.get_font('sm', 'bold')
        )
        self._metric_bullish.grid(row=0, column=1, padx=SPACING['xs'])
        self._metric_bearish = ctk.CTkLabel(
            metrics_frame, text="🔴0", 
            text_color=COLORS['danger']['base'], 
            font=ds.get_font('sm', 'bold')
        )
        self._metric_bearish.grid(row=0, column=2, padx=SPACING['xs'])
        self._metric_neutral = ctk.CTkLabel(
            metrics_frame, text="🟡0", 
            text_color=COLORS['warning']['base'], 
            font=ds.get_font('sm', 'bold')
        )
        self._metric_neutral.grid(row=0, column=3, padx=SPACING['xs'])
        


        # ═══ CONTROLS ROW (GANZ OBEN - KOMPAKT) ═══
        ctrl = ctk.CTkFrame(nf_tab, fg_color="transparent")
        ctrl.grid(row=1, column=0, sticky="ew", padx=SPACING['sm'], pady=(SPACING['xs'], SPACING['xs']))

        # Kompakte Buttons - standardisierte Größen
        button_height = 28
        
        self._news_refresh_btn = ctk.CTkButton(
            ctrl, text="🔄 Laden", width=100, height=button_height,
            fg_color=COLORS['primary']['base'], hover_color=COLORS['primary']['hover'], 
            font=ds.get_font('sm'), corner_radius=RADIUS['md'],
            command=self._fetch_news_threaded)
        self._news_refresh_btn.pack(side="left", padx=(0, SPACING['xs']))

        self._news_analyze_btn = ctk.CTkButton(
            ctrl, text="🤖 KI", width=60, height=button_height,
            fg_color=COLORS['secondary']['base'], hover_color=COLORS['secondary']['hover'], 
            font=ds.get_font('sm'), corner_radius=RADIUS['md'],
            command=self._analyze_all_news_threaded)
        self._news_analyze_btn.pack(side="left", padx=(0, SPACING['xs']))

        # Auto-refresh toggle - kompakt
        self._auto_refresh_btn = ctk.CTkButton(
            ctrl, text="🔁 Auto", width=70, height=button_height,
            fg_color=SEMANTIC['surface'], hover_color=COLORS['primary']['hover'], 
            font=ds.get_font('sm'), corner_radius=RADIUS['md'],
            command=self._toggle_auto_refresh)
        self._auto_refresh_btn.pack(side="left", padx=(0, SPACING['xs']))

        # Filter-Buttons kompakt - standardisierte Größe
        ctk.CTkLabel(
            ctrl, text="Filter:", 
            text_color=COLORS['neutral']['light'], 
            font=ds.get_font('xs')
        ).pack(side="left", padx=(SPACING['xs'], SPACING['xs']))
        
        filter_btn_width = 50
        for pair in ["Alle", "EUR", "GBP", "USD", "JPY"]:
            btn = ctk.CTkButton(
                ctrl, text=pair, width=filter_btn_width, height=button_height - 4,
                fg_color=COLORS['primary']['base'] if pair == "Alle" else SEMANTIC['surface'],
                hover_color=COLORS['primary']['hover'], 
                font=ds.get_font('xs'),
                corner_radius=RADIUS['sm'],
                command=lambda p=pair: self._news_filter(p)
            )
            btn.pack(side="left", padx=1)
            self._news_filter_btns[pair] = btn

        # Status-Indicator kompakt - nach rechts verschoben
        self._news_status_lbl = ctk.CTkLabel(
            ctrl, text="● Bereit", 
            text_color=COLORS['success']['base'],
            font=ds.get_font('xs', 'bold')
        )
        self._news_status_lbl.pack(side="right", padx=SPACING['sm'])

        # ═══ NEWS SCROLL (MEHR PLATZ - ganz oben beginnend) ═══
        self._news_scroll = ctk.CTkScrollableFrame(
            nf_tab, 
            fg_color=SEMANTIC['surface'], 
            corner_radius=RADIUS['lg']
        )
        self._news_scroll.grid(row=2, column=0, sticky="nsew", padx=SPACING['sm'], pady=(SPACING['xs'], SPACING['sm']))
        self._news_scroll.grid_columnconfigure(0, weight=1)
        
        # Kompakte Empty State Nachricht
        ctk.CTkLabel(
            self._news_scroll,
            text="🔄 Klicke 'Laden' für Forex-News oder aktiviere 'Auto'",
            font=ds.get_font('sm'), 
            text_color=COLORS['neutral']['light']
        ).pack(pady=20)

        # ═══════════════ WIRTSCHAFTSKALENDER SUB-TAB ═════════════
        cal_tab = news_sub.tab("📅 Wirtschaftskalender")
        cal_tab.grid_columnconfigure(0, weight=1)
        cal_tab.grid_rowconfigure(3, weight=1)

        # --- TRADING NEWS FILTER ---
        filter_frame = ctk.CTkFrame(cal_tab, fg_color=SEMANTIC['surface'], corner_radius=RADIUS['lg'])
        filter_frame.grid(row=0, column=0, sticky="ew", padx=SPACING['lg'], pady=(SPACING['lg'], 0))
        
        # Header Row
        hdr_row = ctk.CTkFrame(filter_frame, fg_color="transparent")
        hdr_row.pack(fill="x", padx=SPACING['md'], pady=(SPACING['sm'], SPACING['xs']))
        
        ctk.CTkLabel(
            hdr_row, 
            text="🛡️ Trading News Filter", 
            font=ds.get_font('md', 'bold')
        ).pack(side="left")
        
        self.news_filter_switch = ctk.CTkSwitch(
            hdr_row, 
            text="Auto-Trading bei News pausieren", 
            progress_color=COLORS['primary']['base'],
            font=ds.get_font('sm', 'bold'),
            command=self.app._trigger_autosave
        )
        self.news_filter_switch.pack(side="right")
        
        ctk.CTkFrame(filter_frame, height=1, fg_color=COLORS['neutral']['dark']).pack(fill="x", padx=SPACING['md'], pady=SPACING['xs'])
        
        # Body Row
        body_row = ctk.CTkFrame(filter_frame, fg_color="transparent")
        body_row.pack(fill="x", padx=SPACING['md'], pady=(SPACING['xs'], SPACING['sm']))
        
        # Wichtigkeit
        imp_frame = ctk.CTkFrame(body_row, fg_color="transparent")
        imp_frame.pack(side="left", padx=(0, SPACING['lg']))
        ctk.CTkLabel(imp_frame, text="Relevanz filtern:", text_color=COLORS['neutral']['light'], font=ds.get_font('xs')).pack(anchor="w", pady=(0, 2))
        
        self.news_high = ctk.CTkCheckBox(imp_frame, text="Hoch", text_color=COLORS['danger']['base'], font=ds.get_font('sm', 'bold'), command=self.app._trigger_autosave)
        self.news_high.pack(side="left", padx=(0, SPACING['sm']))
        
        self.news_medium = ctk.CTkCheckBox(imp_frame, text="Mittel", text_color=COLORS['warning']['base'], font=ds.get_font('sm', 'bold'), command=self.app._trigger_autosave)
        self.news_medium.pack(side="left", padx=(0, SPACING['sm']))
        
        self.news_low = ctk.CTkCheckBox(imp_frame, text="Niedrig", text_color=COLORS['success']['base'], font=ds.get_font('sm', 'bold'), command=self.app._trigger_autosave)
        self.news_low.pack(side="left", padx=(0, 0))

        # Slider Before
        bef_frame = ctk.CTkFrame(body_row, fg_color="transparent")
        bef_frame.pack(side="left", padx=SPACING['lg'])
        ctk.CTkLabel(bef_frame, text="Sperrzeit Vorher (Min):", text_color=COLORS['neutral']['light'], font=ds.get_font('xs')).pack(anchor="w", pady=(0, 2))
        
        slider_bef_row = ctk.CTkFrame(bef_frame, fg_color="transparent")
        slider_bef_row.pack(fill="x")
        self.news_before_slider = ctk.CTkSlider(slider_bef_row, from_=0, to=120, number_of_steps=24, width=120)
        self.news_before_slider.pack(side="left")
        self.news_before_lbl = ctk.CTkLabel(slider_bef_row, text="30 Min", font=ds.get_font('sm'))
        self.news_before_lbl.pack(side="left", padx=(SPACING['sm'], 0))
        self.news_before_slider.configure(command=lambda v: (self.news_before_lbl.configure(text=f"{int(v)} Min"), self.app._trigger_autosave()))

        # Slider After
        aft_frame = ctk.CTkFrame(body_row, fg_color="transparent")
        aft_frame.pack(side="left", padx=SPACING['lg'])
        ctk.CTkLabel(aft_frame, text="Sperrzeit Nachher (Min):", text_color=COLORS['neutral']['light'], font=ds.get_font('xs')).pack(anchor="w", pady=(0, 2))
        
        slider_aft_row = ctk.CTkFrame(aft_frame, fg_color="transparent")
        slider_aft_row.pack(fill="x")
        self.news_after_slider = ctk.CTkSlider(slider_aft_row, from_=0, to=120, number_of_steps=24, width=120)
        self.news_after_slider.pack(side="left")
        self.news_after_lbl = ctk.CTkLabel(slider_aft_row, text="15 Min", font=ds.get_font('sm'))
        self.news_after_lbl.pack(side="left", padx=(SPACING['sm'], 0))
        self.news_after_slider.configure(command=lambda v: (self.news_after_lbl.configure(text=f"{int(v)} Min"), self.app._trigger_autosave()))

        cal_ctrl = ctk.CTkFrame(cal_tab, fg_color="transparent")
        cal_ctrl.grid(row=1, column=0, sticky="ew", padx=SPACING['lg'], pady=(SPACING['md'], SPACING['md']))

        ctk.CTkButton(
            cal_ctrl, 
            text="🔄 Kalender Laden", 
            width=150, 
            height=32,
            fg_color=COLORS['primary']['base'], 
            hover_color=COLORS['primary']['hover'],
            corner_radius=RADIUS['md'],
            font=ds.get_font('sm'),
            command=self._fetch_calendar_threaded
        ).pack(side="left", padx=(0, SPACING['sm']))

        ctk.CTkLabel(
            cal_ctrl, 
            text="Impact:", 
            text_color=COLORS['neutral']['light']
        ).pack(side="left", padx=(0, SPACING['xs']))
        
        self._cal_impact_var = ctk.StringVar(value="Alle")
        
        for impact in ["Alle", "Hoch", "Mittel", "Niedrig"]:
            ctk.CTkButton(
                cal_ctrl, 
                text=impact, 
                width=70, 
                height=30,
                fg_color=SEMANTIC['surface'], 
                hover_color=COLORS['primary']['hover'],
                corner_radius=RADIUS['md'],
                font=ds.get_font('sm'),
                command=lambda iv=impact: self._cal_filter(iv)
            ).pack(side="left", padx=2)

        self._cal_status_lbl = ctk.CTkLabel(
            cal_ctrl, 
            text="● Bereit", 
            text_color=COLORS['neutral']['light'],
            font=ds.get_font('sm')
        )
        self._cal_status_lbl.pack(side="right", padx=SPACING['lg'])

        # Table header
        cal_hdr = ctk.CTkFrame(
            cal_tab, 
            fg_color=SEMANTIC['surface'], 
            corner_radius=RADIUS['lg'], 
            height=36
        )
        cal_hdr.grid(row=2, column=0, sticky="ew", padx=SPACING['lg'], pady=(SPACING['xs'], 0))
        cal_hdr.grid_columnconfigure((0,1,2,3,4,5), weight=1, uniform="ch")
        cal_hdr.grid_propagate(False)
        
        for ci, ch in enumerate(["Zeit", "Währung", "Impact", "Event", "Prognose", "Sentiment"]):
            ctk.CTkLabel(
                cal_hdr, 
                text=ch, 
                font=ds.get_font('sm', 'bold'),
                text_color=COLORS['neutral']['light']
            ).grid(row=0, column=ci, sticky="w", padx=SPACING['sm'], pady=SPACING['sm'])

        self._cal_scroll = ctk.CTkScrollableFrame(
            cal_tab, 
            fg_color="transparent", 
            corner_radius=RADIUS['lg']
        )
        self._cal_scroll.grid(row=3, column=0, sticky="nsew", padx=SPACING['lg'], pady=(0, SPACING['lg']))
        self._cal_scroll.grid_columnconfigure((0,1,2,3,4,5), weight=1, uniform="ch")
        ctk.CTkLabel(
            self._cal_scroll, 
            text="Keine Termine geladen.", 
            text_color=COLORS['neutral']['light']
        ).grid(row=0, column=0, columnspan=6, pady=20)

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
        self._news_status_lbl.configure(text="⬤ Lade...", text_color="#E67E22")
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
                                "description": entry.get("summary", "")[:500],  # Mehr Kontext anzeigen
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
             "description": "European Central Bank maintains current rates. Die EZB hat die Zinsen unverändert belassen und signalisiert eine vorsichtige Haltung angesichts der Inflation.", "source": "FX Street",
             "url": "https://www.forexstreet.net/news/ecb-rate-decision", "published_at": (datetime.now() - timedelta(hours=2)).isoformat(),
             "currency": "EUR", "sentiment": "Neutral", "impact": "HIGH"},
            {"id": "2", "title": "EUR/USD Rises to 1.0950 on Strong German GDP", 
             "description": "Euro gains on better-than-expected growth. Das deutsche BIP-Wachstum übertraf die Erwartungen, was den Euro stärker machte.", "source": "Bloomberg",
             "url": "https://www.bloomberg.com/markets/eurrencies", "published_at": (datetime.now() - timedelta(hours=4)).isoformat(),
             "currency": "EUR", "sentiment": "Bullish", "impact": "MEDIUM"},
            {"id": "3", "title": "Fed Powell: Inflation Still a Concern", 
             "description": "Federal Reserve emphasizes tightening. Fed-Chairman Powell betonte, dass die Inflation weiterhin ein Hauptanliegen bleibt.", "source": "Reuters",
             "url": "https://www.reuters.com/markets/us", "published_at": (datetime.now() - timedelta(hours=6)).isoformat(),
             "currency": "USD", "sentiment": "Bearish", "impact": "HIGH"},
            {"id": "4", "title": "US Non-Farm Payrolls Beat at 275K", 
             "description": "Labor market remains strong. Die US-Arbeitsmarktdaten übertrafen die Erwartungen deutlich mit 275.000 neuen Stellen.", "source": "MarketWatch",
             "url": "https://www.marketwatch.com/investing/economy", "published_at": (datetime.now() - timedelta(hours=8)).isoformat(),
             "currency": "USD", "sentiment": "Bearish", "impact": "HIGH"},
            {"id": "5", "title": "USD/JPY Tests 150 Level", 
             "description": "Dollar strengthens on BOJ uncertainty. Die Unsicherheit über die Geldpolitik der Bank of Japan lässt den Yen schwächeln.", "source": "Investing",
             "url": "https://www.investing.com/currencies/usd-jpy", "published_at": (datetime.now() - timedelta(hours=10)).isoformat(),
             "currency": "JPY", "sentiment": "Neutral", "impact": "MEDIUM"}
        ]

    def _on_news_fetched(self):
        self._news_refresh_btn.configure(state="normal", text="🔄 Laden")
        if self._auto_refresh:
            self._news_status_lbl.configure(text=f"✓ Auto {datetime.now().strftime('%H:%M')}", text_color="#4CAF50")
        else:
            self._news_status_lbl.configure(text="✓ Bereit", text_color="#00FF66")
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
        self._news_analyze_btn.configure(state="disabled", text="⏳...")
        self._news_status_lbl.configure(text="⬤ KI...", text_color="#8E44AD")
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
        self._news_status_lbl.configure(text="✓ Fertig", text_color="#00FF66")
        self._news_analyze_btn.configure(state="normal", text="🤖 KI")
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
            ctk.CTkLabel(
                self._news_scroll, 
                text="Keine Nachrichten für diesen Filter.", 
                text_color=COLORS['neutral']['light'], 
                font=ds.get_font('sm')
            ).pack(pady=20)
            return

        for npap in filtered:
            # Kompakteres News Card Design
            f = ctk.CTkFrame(
                self._news_scroll, 
                fg_color=SEMANTIC['surface'], 
                corner_radius=RADIUS['md']
            )
            f.pack(fill="x", pady=SPACING['xs'], padx=2)
            
            # Kompakter Header
            hdr = ctk.CTkFrame(f, fg_color="transparent")
            hdr.pack(fill="x", padx=SPACING['sm'], pady=(SPACING['sm'], SPACING['xs']))
            
            # Currency & Time - kompakt
            curr = npap.get("currency", "N/A")
            ctk.CTkLabel(
                hdr, text=curr, 
                font=ds.get_font('xs', 'bold'), 
                fg_color=COLORS['primary']['base'], 
                text_color="#FFFFFF", 
                corner_radius=RADIUS['sm'], 
                width=36, height=20
            ).pack(side="left")
            
            # Impact Badge - kompakt
            impact = npap.get("impact", "LOW")
            icol = COLORS['danger']['base'] if impact == "HIGH" else COLORS['warning']['base'] if impact == "MEDIUM" else COLORS['success']['base']
            ctk.CTkLabel(
                hdr, 
                text=f"⚡{impact}", 
                text_color=icol, 
                font=ds.get_font('xs', 'bold')
            ).pack(side="left", padx=SPACING['xs'])
            
            # Time - kompakt
            try:
                if npap.get("published_at"):
                    dt = datetime.fromisoformat(npap["published_at"].replace("Z", "+00:00"))
                    time_ago = (datetime.now() - dt.replace(tzinfo=None)).total_seconds() / 3600
                    time_str = f"{time_ago:.1f}h"
                else:
                    time_str = "Neu"
            except:
                time_str = "Neu"
            
            ctk.CTkLabel(
                hdr, text=time_str, 
                text_color=COLORS['neutral']['light'], 
                font=ds.get_font('xs')
            ).pack(side="left", padx=SPACING['sm'])
            
            # Sentiment - kompakt
            sent = npap.get("sentiment", "Neutral")
            scol = COLORS['success']['base'] if sent == "Bullish" else COLORS['danger']['base'] if sent == "Bearish" else COLORS['warning']['base']
            sent_icon = "🟢" if sent == "Bullish" else "🔴" if sent == "Bearish" else "🟡"
            ctk.CTkLabel(
                hdr, 
                text=f"{sent_icon} {sent}", 
                text_color=scol, 
                font=ds.get_font('xs', 'bold')
            ).pack(side="right")
            
            # Title - kompakter
            ctk.CTkLabel(
                f, 
                text=npap.get("title", ""), 
                font=ds.get_font('sm', 'bold'),
                anchor="w", 
                justify="left"
            ).pack(fill="x", padx=SPACING['sm'], pady=(SPACING['xs'], SPACING['xs']))
            
            # Description - MEHR KONTEXT (größerer Text, mehr Platz)
            desc_text = npap.get("description", "")
            # Zeige mehr vom Description-Text
            ctk.CTkLabel(
                f, 
                text=desc_text, 
                text_color=COLORS['neutral']['light'], 
                anchor="w", 
                justify="left", 
                font=ds.get_font('sm'),  # Größere Schrift
                wraplength=700  # Mehr Platz für Textumbruch
            ).pack(fill="x", padx=SPACING['sm'], pady=(0, SPACING['xs']))
            
            # Quelle und Link zum Artikel
            source = npap.get("source", "Unbekannt")
            url = npap.get("url", "")
            
            footer = ctk.CTkFrame(f, fg_color="transparent")
            footer.pack(fill="x", padx=SPACING['sm'], pady=(0, SPACING['sm']))
            
            ctk.CTkLabel(
                footer, 
                text=f"📰 {source}", 
                text_color=COLORS['neutral']['light'], 
                font=ds.get_font('xs')
            ).pack(side="left")
            
            # Link-Button zum Artikel
            article_url = url  # Capture URL for lambda
            if article_url and article_url != "#":
                link_btn = ctk.CTkButton(
                    footer,
                    text="🔗 Artikel öffnen",
                    width=120,
                    height=24,
                    fg_color=COLORS['primary']['base'],
                    hover_color=COLORS['primary']['hover'],
                    font=ds.get_font('xs'),
                    corner_radius=RADIUS['sm'],
                    command=lambda u=article_url: self._open_article_url(u)
                )
                link_btn.pack(side="right")

    # ═══════════════════════════════════════════════════════════════
    # ARTICLE URL
    # ═══════════════════════════════════════════════════════════════
    
    def _open_article_url(self, url: str):
        """Öffnet den Artikel-Link im Standard-Browser"""
        import webbrowser
        try:
            logging.info(f"Öffne URL: {url}")
            if url and url.startswith("http"):
                webbrowser.open(url)
            elif url and url != "#":
                webbrowser.open("https://" + url)
            else:
                logging.warning(f"Ungültige URL: {url}")
                self._news_status_lbl.configure(text="● Keine URL verfügbar", text_color=COLORS['warning']['base'])
        except Exception as e:
            logging.error(f"Fehler beim Öffnen der URL: {e}")
            self._news_status_lbl.configure(text="● Fehler beim Öffnen", text_color=COLORS['danger']['base'])

    # ═══════════════════════════════════════════════════════
    # CALENDAR
    # ═══════════════════════════════════════════════════════
    
    def _fetch_calendar_threaded(self):
        self._cal_status_lbl.configure(text="● Lade Kalender...", text_color="#E67E22")
        threading.Thread(target=self._fetch_calendar_bg, daemon=True).start()

    def _fetch_calendar_bg(self):
        try:
            url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self._cal_items = []
                
                # Parse JSON data
                for item in data:
                    # Time formatting
                    try:
                        # "2026-04-05T05:15:00-04:00" -> Parse and extract time
                        dt = datetime.fromisoformat(item.get("date", "").replace("Z", "+00:00"))
                        time_str = dt.strftime("%H:%M")
                    except:
                        time_str = ""
                    
                    impact = item.get("impact", "Low").upper()
                    if impact not in ["HIGH", "MEDIUM", "LOW"]:
                        impact = "LOW"
                        
                    forecast = item.get("forecast", "")
                    previous = item.get("previous", "")
                    forecast_str = f"{forecast} / {previous}" if forecast and previous else forecast or previous
                    
                    self._cal_items.append({
                        "time": time_str,
                        "currency": item.get("country", ""),
                        "impact": impact,
                        "event": item.get("title", ""),
                        "forecast": forecast_str,
                        "sentiment": "Neutral"
                    })
            else:
                logging.error(f"Calendar API error: {response.status_code}")
                # Log to terminal UI if possible
                if hasattr(self, 'app') and hasattr(self.app, 'write_terminal'):
                    self.app.write_terminal(f">> [API ERROR] Kalender: HTTP {response.status_code}. Lade Fallback-Daten...\n", "ERROR")
                
                # Fallback mock data if API fails (z.B. wegen Rate Limit 429)
                self._cal_items = [
                    {"time": "14:30", "currency": "USD", "impact": "HIGH", "event": "Non-Farm Payrolls", "forecast": "200K / 180K", "sentiment": "Bearish"},
                    {"time": "14:30", "currency": "EUR", "impact": "HIGH", "event": "ECB Rate Decision", "forecast": "4.50%", "sentiment": "Neutral"},
                    {"time": "10:00", "currency": "EUR", "impact": "MEDIUM", "event": "German GDP", "forecast": "0.2%", "sentiment": "Bullish"},
                    {"time": "09:30", "currency": "GBP", "impact": "MEDIUM", "event": "Retail Sales", "forecast": "0.3%", "sentiment": "Neutral"},
                    {"time": "13:30", "currency": "USD", "impact": "MEDIUM", "event": "CPI Data", "forecast": "3.2%", "sentiment": "Bearish"},
                    {"time": "15:00", "currency": "USD", "impact": "LOW", "event": "Michigan Sentiment", "forecast": "72", "sentiment": "Neutral"}
                ]
        except Exception as e:
            logging.error(f"Calendar fetch error: {e}")
            if hasattr(self, 'app') and hasattr(self.app, 'write_terminal'):
                self.app.write_terminal(f">> [API ERROR] Kalender Fetch: {e}. Lade Fallback-Daten...\n", "ERROR")
            self._cal_items = [
                {"time": "14:30", "currency": "USD", "impact": "HIGH", "event": "Non-Farm Payrolls", "forecast": "200K / 180K", "sentiment": "Bearish"},
                {"time": "14:30", "currency": "EUR", "impact": "HIGH", "event": "ECB Rate Decision", "forecast": "4.50%", "sentiment": "Neutral"}
            ]
            
        # Speichere die Kalenderdaten in der App-Instanz für den TradingController
        self.app.calendar_events = self._cal_items
        
        try:
            self.app.after(0, self._on_calendar_fetched)
        except RuntimeError:
            pass

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
            ctk.CTkLabel(
                self._cal_scroll, 
                text="Keine Termine für diesen Filter.", 
                text_color=COLORS['neutral']['light']
            ).grid(row=0, column=0, columnspan=6, pady=20)
            return
            
        for i, ev in enumerate(items):
            bg = ("gray95", "gray14") if i % 2 == 0 else "transparent"
            row_f = ctk.CTkFrame(
                self._cal_scroll, 
                fg_color=bg, 
                corner_radius=RADIUS['sm'], 
                height=40
            )
            row_f.grid(row=i, column=0, columnspan=6, sticky="ew", pady=2)
            row_f.grid_columnconfigure((0,1,2,3,4,5), weight=1, uniform="ch")
            row_f.grid_propagate(False)
            
            ctk.CTkLabel(
                row_f, 
                text=ev.get("time",""), 
                text_color=("gray20","gray80")
            ).grid(row=0, column=0, padx=SPACING['sm'])
            ctk.CTkLabel(
                row_f, 
                text=ev.get("currency",""), 
                font=ds.get_font('sm', 'bold')
            ).grid(row=0, column=1, padx=SPACING['sm'])
            
            imp = ev.get("impact", "LOW")
            icol = COLORS['danger']['base'] if imp == "HIGH" else COLORS['warning']['base'] if imp == "MEDIUM" else COLORS['success']['base']
            
            display_map = {"HIGH": "Hoch", "MEDIUM": "Mittel", "LOW": "Niedrig"}
            display_imp = display_map.get(imp, imp)
            
            ctk.CTkLabel(
                row_f, 
                text=display_imp, 
                text_color=icol, 
                font=ds.get_font('sm', 'bold')
            ).grid(row=0, column=2, padx=SPACING['sm'])
            
            ctk.CTkLabel(
                row_f, 
                text=ev.get("event",""), 
                anchor="w"
            ).grid(row=0, column=3, sticky="w", padx=SPACING['sm'])
            ctk.CTkLabel(
                row_f, 
                text=ev.get("forecast","")
            ).grid(row=0, column=4, padx=SPACING['sm'])
            
            # Sentiment
            sent = ev.get("sentiment", "Neutral")
            scol = COLORS['success']['base'] if sent == "Bullish" else COLORS['danger']['base'] if sent == "Bearish" else COLORS['warning']['base']
            ctk.CTkLabel(
                row_f, 
                text=sent, 
                text_color=scol, 
                font=ds.get_font('sm', 'bold')
            ).grid(row=0, column=5, padx=SPACING['sm'])

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
            
            self._news_status_lbl.configure(text=f"● Export: {filename}", text_color=COLORS['success']['base'])
        except Exception as e:
            logging.error(f"Export error: {e}")
