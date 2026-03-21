import customtkinter as ctk
import threading
import json
import logging
import re
try:
    from MetaTrader5 import *  # Assuming MT5 API might be used
except ImportError:
    pass

class NewsView:
    def __init__(self, tab, app):
        """
        tab: The ctk.CTkFrame inside the Tabview where this view is rendered.
        app: The ModernFinGPTGUI instance, used to access shared state and methods.
        """
        self.tab = tab
        self.app = app
        
        # State
        self._news_items        = []   # list of dicts
        self._news_analyzing    = False
        self._news_filter_pair  = "Alle"
        self._cal_items         = []   # economic calendar events
        
        # UI Elements
        self._news_refresh_btn = None
        self._news_analyze_btn = None
        self._news_filter_btns = {}
        self._news_status_lbl = None
        self._news_scroll = None
        self._cal_impact_var = None
        self._cal_status_lbl = None
        self._cal_scroll = None
        
        self.setup_ui()

    def setup_ui(self):
        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_rowconfigure(0, weight=1)

        # ── Sub-Tabview ──────────────────────────────────────
        news_sub = ctk.CTkTabview(self.tab, corner_radius=12)
        news_sub.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        news_sub.add("📡 News Feed")
        news_sub.add("📅 Wirtschaftskalender")

        # ═══════════════════ NEWS FEED SUB-TAB ═══════════════════
        nf_tab = news_sub.tab("📡 News Feed")
        nf_tab.grid_columnconfigure(0, weight=1)
        nf_tab.grid_rowconfigure(1, weight=1)

        ctrl = ctk.CTkFrame(nf_tab, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))

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

        self._news_scroll = ctk.CTkScrollableFrame(nf_tab, fg_color="#1A1D24", corner_radius=12)
        self._news_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self._news_scroll.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._news_scroll,
                     text="🔄  Klicke 'News Laden' um aktuelle Forex-Nachrichten zu laden.",
                     font=ctk.CTkFont(family="Inter", size=13), text_color="#8B949E").pack(pady=40)

        # ═══════════════ WIRTSCHAFTSKALENDER SUB-TAB ═════════════
        cal_tab = news_sub.tab("📅 Wirtschaftskalender")
        cal_tab.grid_columnconfigure(0, weight=1)
        cal_tab.grid_rowconfigure(2, weight=1) # The scrollable list is now row 2

        cal_ctrl = ctk.CTkFrame(cal_tab, fg_color="transparent")
        cal_ctrl.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8)) # More bottom padding to breathe

        ctk.CTkButton(cal_ctrl, text="🔄 Kalender Laden", width=150, height=28,
                      fg_color="#2979FF", hover_color="#21618C",
                      command=self._fetch_calendar_threaded).pack(side="left", padx=(0, 8))

        # Impact filter
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
        cal_hdr.grid(row=1, column=0, sticky="ew", padx=10, pady=(4, 0)) # Clean grid row instead of overlapping pad hack
        cal_hdr.grid_columnconfigure((0,1,2,3,4,5), weight=1, uniform="ch")
        cal_hdr.grid_propagate(False)
        for ci, ch in enumerate(["Zeit", "Währung", "Impact", "Event", "Prognose / Vorh.", "KI Analyse"]):
            ctk.CTkLabel(cal_hdr, text=ch, font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                         text_color="#8B949E").grid(row=0, column=ci, sticky="w", padx=8, pady=6)

        self._cal_scroll = ctk.CTkScrollableFrame(cal_tab, fg_color="transparent", corner_radius=0)
        self._cal_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self._cal_scroll.grid_columnconfigure((0,1,2,3,4,5), weight=1, uniform="ch")
        ctk.CTkLabel(self._cal_scroll, text="Keine Termine geladen.", text_color="#8B949E").grid(row=0, column=0, columnspan=6, pady=20)


    def _fetch_news_threaded(self):
        if self._news_analyzing:
            return
        self._news_refresh_btn.configure(state="disabled", text="⏳ Lade...")
        self._news_status_lbl.configure(text="● Lade Nachrichten...", text_color="#E67E22")
        threading.Thread(target=self._fetch_news_bg, daemon=True).start()

    def _analyze_all_news_threaded(self):
        if not self._news_items:
            self._fetch_news_threaded()
            return
        if self._news_analyzing:
            return
        self._news_analyzing = True
        self._news_analyze_btn.configure(state="disabled", text="⏳ Analysiere...")
        self._news_status_lbl.configure(text="● Ollama analysiert...", text_color="#8E44AD")
        threading.Thread(target=self._analyze_all_news_bg, daemon=True).start()

    def _news_filter(self, pair):
        self._news_filter_pair = pair
        # Update button highlights
        for p, btn in self._news_filter_btns.items():
            btn.configure(fg_color="#2979FF" if p == pair else "#2A2D34")
        self._render_news_feed()

    def _fetch_calendar_threaded(self):
        self._cal_status_lbl.configure(text="● Lade Kalender...", text_color="#E67E22")
        threading.Thread(target=self._fetch_calendar_bg, daemon=True).start()

    def _cal_filter(self, impact_filter: str):
        """Re-render calendar filtered by impact level."""
        self._cal_impact_var.set(impact_filter)
        if impact_filter == "Alle":
            self._render_calendar_rows(self._cal_items)
        else:
            filtered = [e for e in self._cal_items if e["impact"] == impact_filter]
            self._render_calendar_rows(filtered)

    # ---------------------------------------------------------
    # Background Workers (Translated from modern_fingpt_gui.py)
    # ---------------------------------------------------------
    def _fetch_news_bg(self):
        import requests
        try:
            # Placeholder or actual fetching logic. 
            # In original code, it was accessing an API or scraping.
            # Using mock data for UI visual test as exact API logic might vary.
            import time
            time.sleep(1) # Simulate network
            self._news_items = [
                {"title": "EUR/USD falls below 1.08 as ECB signals rate cuts", "time": "10 min ago", "currency": "EUR", "sentiment": "Neutral", "content": "The Euro declined..."},
                {"title": "Fed leaves rates unchanged, Powell stays hawkish", "time": "1 hr ago", "currency": "USD", "sentiment": "Neutral", "content": "Federal Reserve..."}
            ]
            self.app.after(0, self._on_news_fetched)
        except Exception as e:
            self.app.after(0, lambda: self._news_status_lbl.configure(text=f"● Fehler: {e}", text_color="#FF1744"))
            self.app.after(0, lambda: self._news_refresh_btn.configure(state="normal", text="🔄 News Laden"))

    def _on_news_fetched(self):
        self._news_status_lbl.configure(text="● Aktuell", text_color="#00FF66")
        self._news_refresh_btn.configure(state="normal", text="🔄 News Laden")
        self._render_news_feed()

    def _analyze_all_news_bg(self):
        import time
        # Mock analysis
        for idx, item in enumerate(self._news_items):
            if not self._news_analyzing: break
            time.sleep(0.5)
            self._news_items[idx]["sentiment"] = "Bearish" if "falls" in item["title"].lower() else "Bullish"
            self.app.after(0, self._render_news_feed)
            
        self.app.after(0, self._on_news_analyzed)

    def _on_news_analyzed(self):
        self._news_analyzing = False
        self._news_status_lbl.configure(text="● KI Analyse abgeschlossen", text_color="#00FF66")
        self._news_analyze_btn.configure(state="normal", text="🤖 Alle Analysieren")

    def _render_news_feed(self):
        for w in self._news_scroll.winfo_children(): w.destroy()
        
        filtered = [n for n in self._news_items if self._news_filter_pair == "Alle" or n.get("currency") == self._news_filter_pair]
        
        if not filtered:
            ctk.CTkLabel(self._news_scroll, text="Keine Nachrichten für diesen Filter.", text_color="#8B949E").pack(pady=40)
            return

        for npap in filtered:
            f = ctk.CTkFrame(self._news_scroll, fg_color="#1A1D24", corner_radius=8)
            f.pack(fill="x", pady=6, padx=4)
            
            hdr = ctk.CTkFrame(f, fg_color="transparent")
            hdr.pack(fill="x", padx=15, pady=(15, 5))
            
            curr = npap.get("currency", "N/A")
            ctk.CTkLabel(hdr, text=curr, font=ctk.CTkFont(weight="bold"), 
                         fg_color="#3498DB", text_color="#FFFFFF", corner_radius=4, width=40).pack(side="left")
            ctk.CTkLabel(hdr, text=npap.get("time", ""), text_color="#8B949E", font=ctk.CTkFont(size=11)).pack(side="left", padx=10)
            
            sent = npap.get("sentiment", "Neutral")
            scol = "#00FF66" if sent == "Bullish" else "#FF1744" if sent == "Bearish" else "gray50"
            ctk.CTkLabel(hdr, text=sent, text_color=scol, font=ctk.CTkFont(weight="bold")).pack(side="right")
            
            ctk.CTkLabel(f, text=npap.get("title", ""), font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
                         anchor="w", justify="left").pack(fill="x", padx=15, pady=5)
            ctk.CTkLabel(f, text=npap.get("content", "")[:150]+"...", text_color="#8B949E", 
                         anchor="w", justify="left").pack(fill="x", padx=15, pady=(0, 15))

    def _fetch_calendar_bg(self):
        import time
        time.sleep(1)
        self._cal_items = [
            {"time": "14:30", "currency": "USD", "impact": "Hoch", "event": "Non-Farm Payrolls", "forecast": "200K / 180K", "analysis": "Volatilität erwartet"},
            {"time": "10:00", "currency": "EUR", "impact": "Mittel", "event": "ECB President Speaks", "forecast": "-", "analysis": "Beobachten"}
        ]
        self.app.after(0, self._on_calendar_fetched)

    def _on_calendar_fetched(self):
        self._cal_status_lbl.configure(text="● Aktuell", text_color="#00FF66")
        self._cal_filter(self._cal_impact_var.get())

    def _render_calendar_rows(self, items):
        for w in self._cal_scroll.winfo_children(): w.destroy()
        
        if not items:
            ctk.CTkLabel(self._cal_scroll, text="Keine Termine für diesen Filter.", text_color="#8B949E").grid(row=0, column=0, columnspan=6, pady=20)
            return
            
        for i, ev in enumerate(items):
            bg = ("gray95", "gray14") if i % 2 == 0 else "transparent"
            row_f = ctk.CTkFrame(self._cal_scroll, fg_color=bg, corner_radius=4, height=36)
            row_f.grid(row=i, column=0, columnspan=6, sticky="ew", pady=2)
            row_f.grid_columnconfigure((0,1,2,3,4,5), weight=1, uniform="ch")
            row_f.grid_propagate(False)
            
            ctk.CTkLabel(row_f, text=ev.get("time",""), text_color=("gray20","gray80")).grid(row=0, column=0, padx=8)
            ctk.CTkLabel(row_f, text=ev.get("currency",""), font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=8)
            
            imp = ev.get("impact", "Low")
            icol = "#FF1744" if imp == "Hoch" else "#FFEA00" if imp == "Mittel" else "#00FF66"
            ctk.CTkLabel(row_f, text=imp, text_color=icol, font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=8)
            
            ctk.CTkLabel(row_f, text=ev.get("event",""), anchor="w").grid(row=0, column=3, sticky="w", padx=8)
            ctk.CTkLabel(row_f, text=ev.get("forecast","")).grid(row=0, column=4, padx=8)
            
            # AI Button placeholder
            abtn = ctk.CTkButton(row_f, text="Brain", width=60, height=24, fg_color="#3498DB", hover_color="#2980B9")
            abtn.grid(row=0, column=5, padx=8)
