import customtkinter as ctk
import threading
import requests
import MetaTrader5 as mt5
import tkinter.messagebox as messagebox
import tkinter as tk

from core.app_config import app_config_manager


class ConfigView:
    def __init__(self, master_tab, app):
        self.tab = master_tab
        self.app = app
        self._pair_presets = {
            "🏆 Majors (6 Paare)": "EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD",
            "🥈 Majors + Minors (14 Paare)": "EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, "
            "EURGBP, EURJPY, GBPJPY, AUDNZD, CADJPY, AUDCAD, NZDJPY",
            "🔀 Crosses (EUR/GBP/JPY Cross)": "EURGBP, EURJPY, EURCAD, EURAUD, EURNZD, EURCHF, "
            "GBPJPY, GBPCAD, GBPAUD, GBPNZD, GBPCHF",
            "💎 Exotics": "USDTRY, USDZAR, USDMXN, USDHKD, USDSGD, EURTRY, "
            "GBPTRY, XAUUSD, XAGUSD",
            "₿ Crypto Top 10": "BTCUSD, ETHUSD, SOLUSD, BNBUSD, XRPUSD, ADAUSD, DOGEUSD, AVAXUSD, DOTUSD, LINKUSD",
            "📈 Bekannte Aktien (US Tech & Co)": "AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA, NFLX, AMD, INTC",
            "🌐 Alle Paare (Majors + Minors + Crosses)": "EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, "
            "EURGBP, EURJPY, EURCAD, EURAUD, EURNZD, EURCHF, "
            "GBPJPY, GBPCAD, GBPAUD, GBPNZD, GBPCHF, "
            "AUDNZD, AUDCAD, CADJPY, NZDJPY, CHFJPY",
            "✏️ Custom (Manuell eingeben)": "",
        }
        self.setup_ui()

    def setup_ui(self):
        self.tab.grid_columnconfigure(0, weight=0)
        self.tab.grid_columnconfigure(1, weight=1)
        self.tab.grid_rowconfigure(0, weight=1)

        # Build Sidebar
        self.sidebar_frame = ctk.CTkFrame(
            self.tab,
            fg_color="#1A1D24",
            corner_radius=10,
            border_width=1,
            border_color="#2A2D34",
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        ctk.CTkLabel(
            self.sidebar_frame,
            text="Einstellungen",
            font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
            text_color="#FFFFFF",
        ).grid(row=0, column=0, padx=20, pady=(20, 15), sticky="w")
        ctk.CTkFrame(self.sidebar_frame, height=1, fg_color="#333").grid(
            row=1, column=0, sticky="ew", padx=15, pady=(0, 15)
        )

        self.categories = [
            ("🤖 KI & Ollama", self._build_ki_tab),
            ("🎨 Appearance", self._build_app_tab),
            ("📊 Trading Style", self._build_style_tab),
            ("🧠 RL Studio", self._build_rl_tab),
            ("⚙️ MT5 & System", self._build_mt5_tab),
            ("🔕 Benachrichtigungen", self._build_notif_tab),
            ("🔌 MCP Server", self._build_mcp_tab),
        ]

        self.sidebar_buttons = {}
        row_idx = 2
        for name, _ in self.categories:
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=name,
                anchor="w",
                fg_color="transparent",
                text_color="#8B949E",
                font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                hover_color="#2A2D34",
                corner_radius=6,
                height=35,
                command=lambda n=name: self._switch_category(n),
            )
            btn.grid(row=row_idx, column=0, sticky="ew", padx=10, pady=2)
            self.sidebar_buttons[name] = btn
            row_idx += 1

        self.autosave_hint = ctk.CTkLabel(
            self.sidebar_frame,
            text="✅ Auto-Save",
            text_color="#00FF66",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
        )
        self.autosave_hint.grid(row=11, column=0, sticky="ew", padx=20, pady=20)

        # Build Main Content Area
        self.content_container = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.content_container.grid(
            row=0, column=1, sticky="nsew", padx=(5, 10), pady=10
        )
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

        self.content_frames = {}
        for name, build_func in self.categories:
            frame = ctk.CTkScrollableFrame(
                self.content_container, fg_color="transparent"
            )
            frame.grid(row=0, column=0, sticky="nsew")
            build_func(frame)
            self.content_frames[name] = frame

        # Select first tab
        self._switch_category(self.categories[0][0])

        # Async tasks running in the original code
        self.app.after(800, self._detect_account_type)
        self.app.after(500, self.fetch_ollama_models_silently)

    def _switch_category(self, name):
        for btn_name, btn in self.sidebar_buttons.items():
            if btn_name == name:
                btn.configure(fg_color="#2A2D34", text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color="#8B949E")

        for frame in self.content_frames.values():
            frame.grid_remove()

        self.content_frames[name].grid(row=0, column=0, sticky="nsew")

    def _create_card(self, parent, title, title_color="#FFFFFF"):
        card = ctk.CTkFrame(
            parent,
            fg_color="#1A1D24",
            corner_radius=10,
            border_width=1,
            border_color="#2A2D34",
        )
        card.pack(fill="x", padx=10, pady=10)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            text_color=title_color,
        ).pack(side="left")
        ctk.CTkFrame(card, height=1, fg_color="#333").pack(
            fill="x", padx=15, pady=(0, 10)
        )
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=(0, 15))
        content.grid_columnconfigure(1, weight=1)
        return card, content

    def _build_ki_tab(self, parent):
        _, c1 = self._create_card(parent, "API Einstellungen", "#2979FF")
        ctk.CTkLabel(c1, text="KI Provider:").grid(row=0, column=0, sticky="w", pady=5)
        self.ki_provider_var = ctk.StringVar(value="Ollama (Lokal)")
        self.ki_provider_combo = ctk.CTkComboBox(
            c1,
            values=[
                "Ollama (Lokal)",
                "OpenAI (ChatGPT)",
                "Anthropic (Claude)",
                "DeepSeek",
                "OpenRouter",
            ],
            variable=self.ki_provider_var,
            width=300,
            command=self._on_provider_change,
        )
        self.ki_provider_combo.grid(row=0, column=1, sticky="w", pady=5, padx=10)

        self.url_lbl = ctk.CTkLabel(c1, text="Ollama URL:")
        self.url_lbl.grid(row=1, column=0, sticky="w", pady=5)
        self.url_entry = ctk.CTkEntry(
            c1, placeholder_text="http://localhost:11434", width=300
        )
        self.url_entry.insert(0, "http://localhost:11434")
        self.url_entry.grid(row=1, column=1, sticky="w", pady=5, padx=10)
        self.test_ollama_btn = ctk.CTkButton(
            c1,
            text="Test",
            width=60,
            height=28,
            fg_color="transparent",
            border_width=1,
            text_color="#8B949E",
            command=lambda: threading.Thread(
                target=self._test_ollama_click, daemon=True
            ).start(),
        )
        self.test_ollama_btn.grid(row=1, column=2, padx=(0, 10))

        self.api_key_lbl = ctk.CTkLabel(c1, text="API Key:")
        self.api_key_lbl.grid(row=2, column=0, sticky="w", pady=5)
        self.api_key_entry = ctk.CTkEntry(
            c1, placeholder_text="sk-...", width=300, show="*"
        )
        self.api_key_entry.grid(row=2, column=1, sticky="w", pady=5, padx=10)

        ctk.CTkLabel(c1, text="LLM Modell:").grid(row=3, column=0, sticky="w", pady=5)
        self.model_combo = ctk.CTkComboBox(c1, values=["Lade Modelle..."], width=300)
        self.model_combo.grid(row=3, column=1, sticky="w", pady=5, padx=10)

        _, c2 = self._create_card(parent, "System Parameter", "#00FF66")
        ctk.CTkLabel(c2, text="Auto-Trading Intervall (sek):").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.interval_slider = ctk.CTkSlider(c2, from_=1, to=30, number_of_steps=29)
        self.interval_slider.set(5)
        self.interval_slider.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        self.interval_lbl = ctk.CTkLabel(c2, text="5s")
        self.interval_lbl.grid(row=0, column=2)
        self.interval_slider.configure(
            command=lambda val: self.interval_lbl.configure(text=f"{int(val)}s")
        )

        ctk.CTkLabel(c2, text="KI Temperatur:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.ai_temp_slider = ctk.CTkSlider(c2, from_=0.0, to=1.0, number_of_steps=10)
        self.ai_temp_slider.set(0.3)
        self.ai_temp_slider.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        self.ai_temp_lbl = ctk.CTkLabel(c2, text="0.3")
        self.ai_temp_lbl.grid(row=1, column=2)
        self.ai_temp_slider.configure(
            command=lambda val: self.ai_temp_lbl.configure(text=f"{val:.1f}")
        )

        ctk.CTkLabel(c2, text="Max Tokens:").grid(row=2, column=0, sticky="w", pady=5)
        self.max_tokens_slider = ctk.CTkSlider(
            c2, from_=100, to=4096, number_of_steps=39
        )
        self.max_tokens_slider.set(500)
        self.max_tokens_slider.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        self.max_tokens_lbl = ctk.CTkLabel(c2, text="500")
        self.max_tokens_lbl.grid(row=2, column=2)
        self.max_tokens_slider.configure(
            command=lambda val: (
                self.max_tokens_lbl.configure(text=f"{int(val)}"),
                self.app._trigger_autosave(),
            )
        )

        ctk.CTkLabel(c2, text="Min. Confidence (0-100%):").grid(
            row=3, column=0, sticky="w", pady=5
        )
        self.confidence_slider = ctk.CTkSlider(c2, from_=50, to=100, number_of_steps=50)
        self.confidence_slider.set(75)
        self.confidence_slider.grid(row=3, column=1, sticky="ew", padx=10, pady=5)
        self.confidence_lbl = ctk.CTkLabel(c2, text="75%")
        self.confidence_lbl.grid(row=3, column=2)
        self.confidence_slider.configure(
            command=lambda val: (
                self.confidence_lbl.configure(text=f"{int(val)}%"),
                self.app._trigger_autosave(),
            )
        )

        _, c3 = self._create_card(parent, "Prompts", "#9B59B6")
        ctk.CTkLabel(c3, text="Prompt-Sprache:").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.prompt_lang_var = ctk.StringVar(value="Deutsch")
        ctk.CTkComboBox(
            c3,
            values=["Deutsch", "Englisch", "Gemischt"],
            variable=self.prompt_lang_var,
        ).grid(row=0, column=1, sticky="w", pady=5, padx=10)

        ctk.CTkLabel(c3, text="System Prompt:").grid(
            row=1, column=0, sticky="nw", pady=5
        )
        self.system_prompt_text = ctk.CTkTextbox(
            c3,
            width=400,
            height=80,
            fg_color="#1A1D24",
            border_width=1,
            border_color="#2A2D34",
        )
        self.system_prompt_text.insert(
            "0.0",
            "Du bist ein professioneller Trading-Analyst. Bewerte den Markt objektiv basierend auf der technischen Ausgangslage und nutze eine klare, sachliche Sprache.",
        )
        self.system_prompt_text.bind(
            "<KeyRelease>", lambda e: self.app._trigger_autosave()
        )
        self.system_prompt_text.grid(row=1, column=1, sticky="w", pady=5, padx=10)

    def _build_app_tab(self, parent):
        _, c1 = self._create_card(parent, "UI Layout & Theming", "#F1C40F")
        ctk.CTkLabel(c1, text="Farb-Darstellung:").grid(
            row=0, column=0, sticky="w", pady=10
        )
        self.appearance_var = ctk.StringVar(value="Dark")
        app_combo = ctk.CTkComboBox(
            c1,
            values=["Dark", "Gedimmt", "White", "System"],
            variable=self.appearance_var,
            width=300,
            command=self._on_appearance_change,
        )
        app_combo.grid(row=0, column=1, sticky="w", pady=10, padx=20)

        ctk.CTkLabel(c1, text="Akzentfarbe:").grid(row=1, column=0, sticky="w", pady=10)
        self.theme_var = ctk.StringVar(value="green")
        theme_combo = ctk.CTkComboBox(
            c1,
            values=["blue", "green", "dark-blue"],
            variable=self.theme_var,
            width=300,
            command=lambda choice: (
                ctk.set_default_color_theme(choice),
                self.app._trigger_autosave(),
            ),
        )
        theme_combo.grid(row=1, column=1, sticky="w", pady=10, padx=20)

    def _build_style_tab(self, parent):
        # 1. Automatisierung & Stil
        _, c_style = self._create_card(parent, "⚙️ Automatisierung & Stil", "#3498DB")
        
        # Global Switch
        self.trading_active_switch = ctk.CTkSwitch(c_style, text="Auto-Trading Global Erlauben", progress_color="#00FF66", font=ctk.CTkFont(weight="bold"), command=self.app._trigger_autosave)
        self.trading_active_switch.select()
        self.trading_active_switch.pack(anchor="w", pady=(0, 15), padx=15)
        
        style_grid = ctk.CTkFrame(c_style, fg_color="transparent")
        style_grid.pack(fill="x", padx=15)
        
        ctk.CTkLabel(style_grid, text="Trading Style:").grid(row=0, column=0, sticky="w", pady=8, padx=(0,10))
        self.trading_style_var = ctk.StringVar(value="Swing Trading")
        self._style_combo = ctk.CTkComboBox(
            style_grid,
            values=[
                "Scalping", "Day Trading", "Swing Trading", "Position Trading",
                "Price Action", "Breakout-Trading", "Mean Reversion", "Structure Trading",
                "Pattern Trading", "Market Profile", "ICT Orderblock", "AI-Fulldrive Mode 🤖"
            ],
            variable=self.trading_style_var,
            width=200,
            command=self._on_trading_style_change,
        )
        self._style_combo.grid(row=0, column=1, sticky="w", pady=8)
        
        ctk.CTkLabel(style_grid, text="Signal-Strategie:").grid(row=0, column=2, sticky="w", pady=8, padx=(30,10))
        self.signal_strategy_var = ctk.StringVar(value="KI-gesteuert (Ollama)")
        ctk.CTkComboBox(
            style_grid,
            values=["KI-gesteuert (Ollama)", "Technische Indikatoren", "Hybrid (KI + Indikatoren)"],
            variable=self.signal_strategy_var,
            width=200,
            command=self.app._trigger_autosave
        ).grid(row=0, column=3, sticky="w", pady=8)

        ctk.CTkLabel(style_grid, text="Risikoprofil:").grid(row=1, column=0, sticky="w", pady=8, padx=(0,10))
        self.risk_profile_var = ctk.StringVar(value="Moderat")
        ctk.CTkComboBox(
            style_grid,
            values=["Konservativ", "Moderat", "Aggressiv"],
            variable=self.risk_profile_var,
            width=200,
            command=self.app._trigger_autosave
        ).grid(row=1, column=1, sticky="w", pady=8)

        # 2. Strategie-Parameter (Dynamisch)
        self.dyn_card, self.dyn_content = self._create_card(parent, "🎯 Strategie-Spezifische Parameter", "#E67E22")
        
        # -- Frame für "Fast" (Scalping / Day Trading)
        self.fast_frame = ctk.CTkFrame(self.dyn_content, fg_color="transparent")
        
        ctk.CTkLabel(self.fast_frame, text="Min. Zeit zwischen Trades (sek):").grid(row=0, column=0, sticky="w", pady=5)
        self.rm_cooldown_slider = ctk.CTkSlider(self.fast_frame, from_=10, to=900, number_of_steps=89, width=180)
        self.rm_cooldown_slider.set(300)
        self.rm_cooldown_slider.grid(row=0, column=1, sticky="w", pady=5, padx=10)
        self.rm_cooldown_lbl = ctk.CTkLabel(self.fast_frame, text="300 sek")
        self.rm_cooldown_lbl.grid(row=0, column=2, sticky="w")
        self.rm_cooldown_slider.configure(command=lambda v: (self.rm_cooldown_lbl.configure(text=f"{int(v)} sek"), self._validate_risk_settings(), self.app._trigger_autosave()))

        ctk.CTkLabel(self.fast_frame, text="Max. Spread (Pips):").grid(row=1, column=0, sticky="w", pady=5)
        self.max_spread_slider = ctk.CTkSlider(self.fast_frame, from_=1, to=20, number_of_steps=19, width=180)
        self.max_spread_slider.set(3)
        self.max_spread_slider.grid(row=1, column=1, sticky="w", pady=5, padx=10)
        self.max_spread_lbl = ctk.CTkLabel(self.fast_frame, text="3 pips")
        self.max_spread_lbl.grid(row=1, column=2, sticky="w")
        self.max_spread_slider.configure(command=lambda v: (self.max_spread_lbl.configure(text=f"{int(v)} pips"), self.app._trigger_autosave()))

        ctk.CTkLabel(self.fast_frame, text="Max. Slippage (Pips):").grid(row=2, column=0, sticky="w", pady=5)
        self.max_slippage_slider = ctk.CTkSlider(self.fast_frame, from_=1, to=10, number_of_steps=9, width=180)
        self.max_slippage_slider.set(2)
        self.max_slippage_slider.grid(row=2, column=1, sticky="w", pady=5, padx=10)
        self.max_slippage_lbl = ctk.CTkLabel(self.fast_frame, text="2 pips")
        self.max_slippage_lbl.grid(row=2, column=2, sticky="w")
        self.max_slippage_slider.configure(command=lambda v: (self.max_slippage_lbl.configure(text=f"{int(v)} pips"), self.app._trigger_autosave()))

        self.spread_check_switch = ctk.CTkSwitch(self.fast_frame, text="Trade ablehnen wenn Spread zu hoch", progress_color="#00FF66", command=self.app._trigger_autosave)
        self.spread_check_switch.select()
        self.spread_check_switch.grid(row=3, column=0, columnspan=3, sticky="w", pady=10)

        # -- Frame für "Fulldrive"
        self.fd_frame = ctk.CTkFrame(self.dyn_content, fg_color="transparent")
        
        self._fd_conf_lbl_l = ctk.CTkLabel(self.fd_frame, text="Min. Konfidenz (%):", text_color="#8B949E")
        self._fd_conf_lbl_l.grid(row=0, column=0, sticky="w", pady=5)
        self.fd_confidence_slider = ctk.CTkSlider(self.fd_frame, from_=50, to=95, number_of_steps=45, width=180, progress_color="#9B59B6")
        self.fd_confidence_slider.set(70)
        self.fd_confidence_slider.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        self._fd_conf_val_lbl = ctk.CTkLabel(self.fd_frame, text="70%")
        self._fd_conf_val_lbl.grid(row=0, column=2, sticky="w")
        self.fd_confidence_slider.configure(command=lambda v: (self._fd_conf_val_lbl.configure(text=f"{int(v)}%"), self.app._trigger_autosave()))

        self._fd_sharpe_lbl = ctk.CTkLabel(self.fd_frame, text="Sharpe Ratio Ziel:", text_color="#8B949E")
        self._fd_sharpe_lbl.grid(row=1, column=0, sticky="w", pady=5)
        self.fd_sharpe_entry = ctk.CTkEntry(self.fd_frame, width=90)
        self.fd_sharpe_entry.insert(0, "1.5")
        self.fd_sharpe_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        self.fd_sharpe_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())

        self._fd_dd_lbl = ctk.CTkLabel(self.fd_frame, text="Max. Drawdown Limit (%):", text_color="#8B949E")
        self._fd_dd_lbl.grid(row=2, column=0, sticky="w", pady=5)
        self.fd_maxdd_entry = ctk.CTkEntry(self.fd_frame, width=90)
        self.fd_maxdd_entry.insert(0, "15")
        self.fd_maxdd_entry.grid(row=2, column=1, sticky="w", padx=10, pady=5)
        self.fd_maxdd_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())

        self.fd_selfopt_switch = ctk.CTkSwitch(self.fd_frame, text="Auto-Retraining alle 50 Trades", progress_color="#9B59B6", command=self.app._trigger_autosave)
        self.fd_selfopt_switch.select()
        self.fd_selfopt_switch.grid(row=3, column=0, columnspan=3, sticky="w", pady=10)

        self._fd_kpi_frame = ctk.CTkFrame(self.fd_frame, fg_color="#21252D", corner_radius=6)
        self._fd_kpi_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=5)
        self._fd_kpi_sharpe_lbl = ctk.CTkLabel(self._fd_kpi_frame, text="Sharpe: --")
        self._fd_kpi_sharpe_lbl.pack(side="left", padx=15, pady=8)
        self._fd_kpi_dd_lbl = ctk.CTkLabel(self._fd_kpi_frame, text="Max-DD: --")
        self._fd_kpi_dd_lbl.pack(side="left", padx=15, pady=8)
        self._fd_kpi_winrate_lbl = ctk.CTkLabel(self._fd_kpi_frame, text="Win-Rate: --")
        self._fd_kpi_winrate_lbl.pack(side="left", padx=15, pady=8)

        # -- Frame für "Default / Other"
        self.default_frame = ctk.CTkFrame(self.dyn_content, fg_color="transparent")
        ctk.CTkLabel(self.default_frame, text="Für diesen Trading Style gelten die globalen Limits und Regeln.\\nKeine zusätzlichen Strategie-Parameter erforderlich.", text_color="#8B949E", justify="left").pack(pady=20, anchor="w", padx=5)

        # 3. Risiko-Management (Allgemein)
        _, c_risk = self._create_card(parent, "🛡️ Risiko-Management", "#FF1744")
        
        self.risk_summary_lbl = ctk.CTkLabel(c_risk, text="✅ Settings validiert", text_color="#00FF66", font=ctk.CTkFont(size=12, weight="bold"))
        self.risk_summary_lbl.pack(anchor="w", pady=(0, 10), padx=15)

        risk_grid = ctk.CTkFrame(c_risk, fg_color="transparent")
        risk_grid.pack(fill="x", padx=15)
        
        ctk.CTkLabel(risk_grid, text="Risiko pro Trade (%):").grid(row=0, column=0, sticky="w", pady=8, padx=5)
        self.risk_trade_entry = ctk.CTkEntry(risk_grid, width=80)
        self.risk_trade_entry.insert(0, "1.0")
        self.risk_trade_entry.grid(row=0, column=1, sticky="w", pady=8, padx=5)
        self.risk_trade_entry.bind("<KeyRelease>", lambda e: self._validate_risk_settings())
        
        ctk.CTkLabel(risk_grid, text="Max. Offene Pos:").grid(row=0, column=2, sticky="w", pady=8, padx=(30, 5))
        self.max_pos_entry = ctk.CTkEntry(risk_grid, width=80)
        self.max_pos_entry.insert(0, "3")
        self.max_pos_entry.grid(row=0, column=3, sticky="w", pady=8, padx=5)
        self.max_pos_entry.bind("<KeyRelease>", lambda e: self._validate_risk_settings())

        ctk.CTkLabel(risk_grid, text="Daily Loss Limit (%):").grid(row=1, column=0, sticky="w", pady=8, padx=5)
        self.risk_daily_entry = ctk.CTkEntry(risk_grid, width=80)
        self.risk_daily_entry.insert(0, "3.0")
        self.risk_daily_entry.grid(row=1, column=1, sticky="w", pady=8, padx=5)
        self.risk_daily_entry.bind("<KeyRelease>", lambda e: self._validate_risk_settings())
        
        ctk.CTkLabel(risk_grid, text="Tagesverlust max (€):").grid(row=1, column=2, sticky="w", pady=8, padx=(30, 5))
        self.rm_daily_loss_entry = ctk.CTkEntry(risk_grid, width=80)
        self.rm_daily_loss_entry.insert(0, "500")
        self.rm_daily_loss_entry.grid(row=1, column=3, sticky="w", pady=8, padx=5)
        self.rm_daily_loss_entry.bind("<KeyRelease>", lambda e: self._validate_risk_settings())

        ctk.CTkLabel(risk_grid, text="Wochenverlust max (€):").grid(row=2, column=0, sticky="w", pady=8, padx=5)
        self.rm_weekly_loss_entry = ctk.CTkEntry(risk_grid, width=80)
        self.rm_weekly_loss_entry.insert(0, "1500")
        self.rm_weekly_loss_entry.grid(row=2, column=1, sticky="w", pady=8, padx=5)
        self.rm_weekly_loss_entry.bind("<KeyRelease>", lambda e: self._validate_risk_settings())
        
        ctk.CTkLabel(risk_grid, text="Monatsziel (%):").grid(row=2, column=2, sticky="w", pady=8, padx=(30, 5))
        self.monthly_target_entry = ctk.CTkEntry(risk_grid, width=80)
        self.monthly_target_entry.insert(0, "10")
        self.monthly_target_entry.grid(row=2, column=3, sticky="w", pady=8, padx=5)
        self.monthly_target_entry.bind("<KeyRelease>", lambda e: self._validate_risk_settings())

        # 4. Exit-Regeln & Protections
        _, c_exit = self._create_card(parent, "🛑 Exit-Regeln & Protections", "#F1C40F")

        # Stop-Loss Row
        sl_row = ctk.CTkFrame(c_exit, fg_color="#21252D", corner_radius=6)
        sl_row.pack(fill="x", pady=4, padx=10)
        ctk.CTkLabel(sl_row, text="Stop-Loss (Pips)", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15, pady=12)
        self.sl_dist_entry = ctk.CTkEntry(sl_row, width=70)
        self.sl_dist_entry.insert(0, "20")
        self.sl_dist_entry.pack(side="left", padx=5)
        self.sl_dist_entry.bind("<KeyRelease>", lambda e: self._validate_risk_settings())
        ctk.CTkLabel(sl_row, text="Absolutes Limit für Verluste pro Trade", text_color="#8B949E", font=ctk.CTkFont(size=11)).pack(side="left", padx=15)

        # Trailing Stop Row
        ts_row = ctk.CTkFrame(c_exit, fg_color="#21252D", corner_radius=6)
        ts_row.pack(fill="x", pady=4, padx=10)
        ts_header = ctk.CTkFrame(ts_row, fg_color="transparent")
        ts_header.pack(fill="x", padx=10, pady=(10, 2))
        self.trailing_stop_switch = ctk.CTkSwitch(ts_header, text="Trailing Stop", font=ctk.CTkFont(weight="bold"), progress_color="#F1C40F", command=self._validate_risk_settings)
        self.trailing_stop_switch.select()
        self.trailing_stop_switch.pack(side="left", padx=5)
        ctk.CTkLabel(ts_header, text="Trailt den Stop automatisch nach, um Gewinne abzusichern", text_color="#8B949E", font=ctk.CTkFont(size=11)).pack(side="left", padx=15)
        ts_body = ctk.CTkFrame(ts_row, fg_color="transparent")
        ts_body.pack(fill="x", padx=10, pady=(2, 10))
        ctk.CTkLabel(ts_body, text="Abstand (Pips):").pack(side="left", padx=(30, 5))
        self.ts_dist_entry = ctk.CTkEntry(ts_body, width=70)
        self.ts_dist_entry.insert(0, "15")
        self.ts_dist_entry.pack(side="left")
        self.ts_dist_entry.bind("<KeyRelease>", lambda e: self._validate_risk_settings())

        # Break-Even Row
        be_row = ctk.CTkFrame(c_exit, fg_color="#21252D", corner_radius=6)
        be_row.pack(fill="x", pady=4, padx=10)
        be_header = ctk.CTkFrame(be_row, fg_color="transparent")
        be_header.pack(fill="x", padx=10, pady=(10, 2))
        self.break_even_switch = ctk.CTkSwitch(be_header, text="Break-Even", font=ctk.CTkFont(weight="bold"), progress_color="#F1C40F", command=self._validate_risk_settings)
        self.break_even_switch.pack(side="left", padx=5)
        ctk.CTkLabel(be_header, text="Sichert den Trade frühzeitig auf den Einstiegspreis ab", text_color="#8B949E", font=ctk.CTkFont(size=11)).pack(side="left", padx=15)
        be_body = ctk.CTkFrame(be_row, fg_color="transparent")
        be_body.pack(fill="x", padx=10, pady=(2, 10))
        ctk.CTkLabel(be_body, text="Aktivierung ab (Pips):").pack(side="left", padx=(30, 5))
        self.be_dist_entry = ctk.CTkEntry(be_body, width=70)
        self.be_dist_entry.insert(0, "10")
        self.be_dist_entry.pack(side="left")
        self.be_dist_entry.bind("<KeyRelease>", lambda e: self._validate_risk_settings())

        # Weekend Row
        we_row = ctk.CTkFrame(c_exit, fg_color="#21252D", corner_radius=6)
        we_row.pack(fill="x", pady=4, padx=10)
        self.weekend_exit_switch = ctk.CTkSwitch(we_row, text="Wochenend-Schutz (Trades Freitags schließen)", font=ctk.CTkFont(weight="bold"), progress_color="#FF1744", command=self.app._trigger_autosave)
        self.weekend_exit_switch.pack(side="left", padx=15, pady=12)
        ctk.CTkLabel(we_row, text="Vermeidet Gaps über das Wochenende", text_color="#8B949E", font=ctk.CTkFont(size=11)).pack(side="left", padx=15)


        # 5. Handelslimits & Zeiten
        _, c_time = self._create_card(parent, "🗓️ Handelslimits & Zeiten", "#9B59B6")
        
        limit_grid = ctk.CTkFrame(c_time, fg_color="transparent")
        limit_grid.pack(fill="x", pady=(0, 10), padx=15)
        
        ctk.CTkLabel(limit_grid, text="Max. Trades pro Tag:").grid(row=0, column=0, sticky="w", pady=5)
        self.rm_max_trades_entry = ctk.CTkEntry(limit_grid, width=80)
        self.rm_max_trades_entry.insert(0, "10")
        self.rm_max_trades_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        self.rm_max_trades_entry.bind("<KeyRelease>", lambda e: self._validate_risk_settings())

        ctk.CTkLabel(c_time, text="Aktive Handelstage:", text_color="#FFFFFF").pack(anchor="w", pady=(10, 5), padx=15)
        
        days_frame = ctk.CTkFrame(c_time, fg_color="transparent")
        days_frame.pack(fill="x", pady=5, padx=15)
        days_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1, uniform="day")

        self._day_buttons = {}
        self._day_vars = {}
        days = [("day_mon", "Mo", 0), ("day_tue", "Di", 1), ("day_wed", "Mi", 2),
                ("day_thu", "Do", 3), ("day_fri", "Fr", 4), ("day_sat", "Sa", 5), ("day_sun", "So", 6)]
        
        active_color = "#00FF66"
        inactive_color = "#4A4A4A"

        def _on_day_click(day_id):
            var = self._day_vars[day_id]
            btn_data = self._day_buttons[day_id]
            new_state = not var.get()
            var.set(new_state)
            if new_state:
                btn_data["frame"].configure(fg_color=active_color)
                btn_data["label"].configure(text_color="#000000")
            else:
                btn_data["frame"].configure(fg_color=inactive_color)
                btn_data["label"].configure(text_color="#AAAAAA")
            self.app._trigger_autosave()

        for day_id, day_name, col in days:
            var = ctk.BooleanVar(value=day_id in ["day_mon", "day_tue", "day_wed", "day_thu", "day_fri"])
            self._day_vars[day_id] = var
            btn_frame = ctk.CTkFrame(days_frame, fg_color=active_color if var.get() else inactive_color, corner_radius=8)
            btn_frame.grid(row=0, column=col, padx=4, pady=0, sticky="ew")
            lbl = ctk.CTkLabel(btn_frame, text=day_name, font=ctk.CTkFont(size=14, weight="bold"), text_color="#000000" if var.get() else "#AAAAAA")
            lbl.pack(padx=10, pady=8)
            self._day_buttons[day_id] = {"frame": btn_frame, "label": lbl, "var": var}
            btn_frame.bind("<Button-1>", lambda e, did=day_id: _on_day_click(did))
            lbl.bind("<Button-1>", lambda e, did=day_id: _on_day_click(did))

        # Backwards comp.
        self.day_mon = ctk.CTkCheckBox(c_time, text="", variable=self._day_vars["day_mon"]); self.day_mon.grid_forget()
        self.day_tue = ctk.CTkCheckBox(c_time, text="", variable=self._day_vars["day_tue"]); self.day_tue.grid_forget()
        self.day_wed = ctk.CTkCheckBox(c_time, text="", variable=self._day_vars["day_wed"]); self.day_wed.grid_forget()
        self.day_thu = ctk.CTkCheckBox(c_time, text="", variable=self._day_vars["day_thu"]); self.day_thu.grid_forget()
        self.day_fri = ctk.CTkCheckBox(c_time, text="", variable=self._day_vars["day_fri"]); self.day_fri.grid_forget()
        self.day_sat = ctk.CTkCheckBox(c_time, text="", variable=self._day_vars["day_sat"]); self.day_sat.grid_forget()
        self.day_sun = ctk.CTkCheckBox(c_time, text="", variable=self._day_vars["day_sun"]); self.day_sun.grid_forget()

        ctk.CTkLabel(c_time, text="Handelszeitraum:", text_color="#FFFFFF").pack(anchor="w", pady=(20, 5), padx=15)
        self.time_filter_switch = ctk.CTkSwitch(c_time, text="Zeitfilter aktivieren", progress_color="#3498DB", command=self.app._trigger_autosave)
        self.time_filter_switch.select()
        self.time_filter_switch.pack(anchor="w", pady=5, padx=15)
        
        time_frame = ctk.CTkFrame(c_time, fg_color="transparent")
        time_frame.pack(fill="x", pady=(5, 10), padx=15)
        ctk.CTkLabel(time_frame, text="Von:", text_color="#8B949E").pack(side="left", padx=(0,5))
        self.trade_time_from = ctk.CTkEntry(time_frame, width=80)
        self.trade_time_from.insert(0, "08:00")
        self.trade_time_from.pack(side="left", padx=5)
        self.trade_time_from.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        ctk.CTkLabel(time_frame, text="Bis:", text_color="#8B949E").pack(side="left", padx=(15,5))
        self.trade_time_to = ctk.CTkEntry(time_frame, width=80)
        self.trade_time_to.insert(0, "20:00")
        self.trade_time_to.pack(side="left", padx=5)
        self.trade_time_to.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        ctk.CTkLabel(time_frame, text="(24h Format: z.B. 08:00 - 20:00)", text_color="#666666", font=ctk.CTkFont(size=11)).pack(side="left", padx=15)
        
        # Trigger initial state
        self._on_trading_style_change(self.trading_style_var.get())

    def _build_rl_tab(self, parent):
        _, c1 = self._create_card(parent, "Reinforcement Learning Parameter", "#8E44AD")
        ctk.CTkLabel(c1, text="RL Algorithmus:").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.rl_algo_var = ctk.StringVar(value="PPO")
        ctk.CTkComboBox(
            c1,
            values=["PPO", "DQN", "A2C", "SAC"],
            variable=self.rl_algo_var,
            width=180,
            command=self.app._trigger_autosave,
        ).grid(row=0, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c1, text="Lernrate:").grid(row=1, column=0, sticky="w", pady=5)
        self.rl_lr_slider = ctk.CTkSlider(c1, from_=0.0001, to=0.01, number_of_steps=99)
        self.rl_lr_slider.set(0.0003)
        self.rl_lr_slider.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        self.rl_lr_lbl = ctk.CTkLabel(c1, text="0.0003")
        self.rl_lr_lbl.grid(row=1, column=2)
        self.rl_lr_slider.configure(
            command=lambda val: (
                self.rl_lr_lbl.configure(text=f"{val:.4f}"),
                self.app._trigger_autosave(),
            )
        )

        ctk.CTkLabel(c1, text="Gamma (Discount):").grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.rl_gamma_slider = ctk.CTkSlider(c1, from_=0.8, to=1.0, number_of_steps=20)
        self.rl_gamma_slider.set(0.99)
        self.rl_gamma_slider.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        self.rl_gamma_lbl = ctk.CTkLabel(c1, text="0.99")
        self.rl_gamma_lbl.grid(row=2, column=2)
        self.rl_gamma_slider.configure(
            command=lambda val: (
                self.rl_gamma_lbl.configure(text=f"{val:.2f}"),
                self.app._trigger_autosave(),
            )
        )

        ctk.CTkLabel(c1, text="Training Steps:").grid(
            row=3, column=0, sticky="w", pady=5
        )
        self.rl_steps_entry = ctk.CTkEntry(c1, width=120)
        self.rl_steps_entry.insert(0, "100000")
        self.rl_steps_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.rl_steps_entry.grid(row=3, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c1, text="Belohnungsfunktion:").grid(
            row=4, column=0, sticky="w", pady=5
        )
        self.rl_reward_var = ctk.StringVar(value="Profit + Sharpe Ratio")
        ctk.CTkComboBox(
            c1,
            values=[
                "Profit + Sharpe Ratio",
                "Reiner Profit",
                "Sortino Ratio",
                "Custom",
            ],
            variable=self.rl_reward_var,
            width=250,
            command=self.app._trigger_autosave,
        ).grid(row=4, column=1, sticky="w", padx=10, pady=5)

        _, c2 = self._create_card(parent, "Advanced RL Parameters", "#F39C12")
        ctk.CTkLabel(c2, text="Replay Buffer Size:").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.rl_buffer_entry = ctk.CTkEntry(c2, width=100)
        self.rl_buffer_entry.insert(0, "10000")
        self.rl_buffer_entry.bind(
            "<KeyRelease>", lambda e: self.app._trigger_autosave()
        )
        self.rl_buffer_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c2, text="Batch Size:").grid(row=0, column=2, sticky="w", pady=5)
        self.rl_batch_entry = ctk.CTkEntry(c2, width=100)
        self.rl_batch_entry.insert(0, "64")
        self.rl_batch_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.rl_batch_entry.grid(row=0, column=3, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c2, text="Epochs (PPO):").grid(row=1, column=0, sticky="w", pady=5)
        self.rl_epochs_entry = ctk.CTkEntry(c2, width=100)
        self.rl_epochs_entry.insert(0, "10")
        self.rl_epochs_entry.bind(
            "<KeyRelease>", lambda e: self.app._trigger_autosave()
        )
        self.rl_epochs_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c2, text="Target Update (DQN):").grid(
            row=1, column=2, sticky="w", pady=5
        )
        self.rl_target_update_entry = ctk.CTkEntry(c2, width=100)
        self.rl_target_update_entry.insert(0, "1000")
        self.rl_target_update_entry.bind(
            "<KeyRelease>", lambda e: self.app._trigger_autosave()
        )
        self.rl_target_update_entry.grid(row=1, column=3, sticky="w", padx=10, pady=5)

        _, c3 = self._create_card(parent, "Neural Network & Model", "#9B59B6")
        ctk.CTkLabel(c3, text="Netzwerk-Architektur:").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.rl_nn_arch_var = ctk.StringVar(value="Mittel (128-128)")
        ctk.CTkComboBox(
            c3,
            values=["Klein (64-64)", "Mittel (128-128)", "Groß (256-256)"],
            variable=self.rl_nn_arch_var,
            width=200,
            command=lambda v: self.app._trigger_autosave(),
        ).grid(row=0, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c3, text="Checkpoint Pfad:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.rl_checkpoint_entry = ctk.CTkEntry(
            c3, placeholder_text="storage/rl_agents/model.zip", width=300
        )
        self.rl_checkpoint_entry.bind(
            "<KeyRelease>", lambda e: self.app._trigger_autosave()
        )
        self.rl_checkpoint_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        self.rl_live_switch = ctk.CTkSwitch(
            c3,
            text="RL Agent für Live-Trading aktivieren (Experimentell)",
            progress_color="#8E44AD",
            command=self.app._trigger_autosave,
        )
        self.rl_live_switch.grid(row=2, column=0, columnspan=2, sticky="w", pady=15)

    def _build_mt5_tab(self, parent):
        _, c1 = self._create_card(parent, "MetaTrader 5 & System", "#FF1744")
        ctk.CTkButton(
            c1,
            text="MT5 Manuell Neuverbinden",
            command=self.test_mt5_connection,
            fg_color="transparent",
            border_width=1,
            text_color="#8B949E",
        ).grid(row=0, column=0, sticky="w", pady=5)

        ctk.CTkLabel(c1, text="Konto:").grid(row=1, column=0, sticky="w", pady=5)
        self.account_combo_var = ctk.StringVar(value="🔍 Wird ermittelt...")
        self.account_combo = ctk.CTkComboBox(
            c1,
            variable=self.account_combo_var,
            values=["Wird geladen..."],
            width=350,
            command=self._on_account_switch,
        )
        self.account_combo.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        broker_info_frame = ctk.CTkFrame(c1, fg_color="transparent")
        broker_info_frame.grid(row=2, column=1, sticky="w", padx=10, pady=5)
        self._account_type_lbl = ctk.CTkLabel(broker_info_frame, text="Typ: --")
        self._account_type_lbl.pack(side="left", padx=5)
        self._broker_name_lbl = ctk.CTkLabel(broker_info_frame, text="Broker: --")
        self._broker_name_lbl.pack(side="left", padx=5)
        self._prop_firm_lbl = ctk.CTkLabel(broker_info_frame, text="Prop: --")
        self._prop_firm_lbl.pack(side="left", padx=5)

        _, c2 = self._create_card(parent, "Trading Paare", "#E67E22")
        ctk.CTkLabel(c2, text="Presets:").grid(row=0, column=0, sticky="w", pady=5)
        self._pairs_preset_var = ctk.StringVar(value="🏆 Majors (6 Paare)")
        pairs_preset_combo = ctk.CTkComboBox(
            c2,
            values=list(self._pair_presets.keys()),
            variable=self._pairs_preset_var,
            width=350,
            command=self._on_pairs_preset_change,
        )
        pairs_preset_combo.grid(row=0, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c2, text="Aktive Paare:").grid(
            row=1, column=0, sticky="nw", pady=5
        )
        self.pairs_entry = ctk.CTkEntry(c2, width=350)
        self.pairs_entry.insert(0, self._pair_presets["🏆 Majors (6 Paare)"])
        self.pairs_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.pairs_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        self.debug_mode_switch = ctk.CTkSwitch(
            c2,
            text="Debug-Modus (mehr Terminal-Output)",
            progress_color="#FF1744",
            command=self.app._trigger_autosave,
        )
        self.debug_mode_switch.grid(row=2, column=0, columnspan=2, sticky="w", pady=15)

    def _build_notif_tab(self, parent):
        _, c1 = self._create_card(parent, "Discord & Telegram Integrations", "#F1C40F")
        ctk.CTkLabel(c1, text="Discord Webhook URL:").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.discord_webhook_entry = ctk.CTkEntry(
            c1, width=350, placeholder_text="https://discord.com/api/webhooks/..."
        )
        self.discord_webhook_entry.bind(
            "<KeyRelease>", lambda e: self.app._trigger_autosave()
        )
        self.discord_webhook_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c1, text="Telegram Bot Token:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.tg_token_entry = ctk.CTkEntry(
            c1, width=350, placeholder_text="123456:ABC-DEF..."
        )
        self.tg_token_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.tg_token_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c1, text="Telegram Chat ID:").grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.tg_chat_id_entry = ctk.CTkEntry(
            c1, width=200, placeholder_text="-100123..."
        )
        self.tg_chat_id_entry.bind(
            "<KeyRelease>", lambda e: self.app._trigger_autosave()
        )
        self.tg_chat_id_entry.grid(row=2, column=1, sticky="w", padx=10, pady=5)

        self.tg_test_btn = ctk.CTkButton(
            c1,
            text="📤 Test-Nachricht",
            width=200,
            fg_color="#2979FF",
            command=lambda: threading.Thread(
                target=self._send_telegram_test, daemon=True
            ).start(),
        )
        self.tg_test_btn.grid(row=3, column=0, columnspan=2, sticky="w", pady=15)

        _, c2 = self._create_card(parent, "Benachrichtigungsfilter", "#00FF66")
        self.notif_sl_hit = ctk.CTkCheckBox(
            c2, text="SL Hit", command=self.app._trigger_autosave
        )
        self.notif_sl_hit.select()
        self.notif_sl_hit.grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.notif_tp_hit = ctk.CTkCheckBox(
            c2, text="TP Hit", command=self.app._trigger_autosave
        )
        self.notif_tp_hit.select()
        self.notif_tp_hit.grid(row=0, column=1, sticky="w", pady=5, padx=5)

        self.notif_new_trade = ctk.CTkCheckBox(
            c2, text="Neuer Trade", command=self.app._trigger_autosave
        )
        self.notif_new_trade.select()
        self.notif_new_trade.grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.notif_error = ctk.CTkCheckBox(
            c2, text="Fehler & Kritisch", command=self.app._trigger_autosave
        )
        self.notif_error.select()
        self.notif_error.grid(row=1, column=1, sticky="w", pady=5, padx=5)

        self.sound_alerts_switch = ctk.CTkSwitch(
            c2,
            text="Trade-Sounds abspielen (Öffnen/Schließen)",
            progress_color="#F1C40F",
            command=self.app._trigger_autosave,
        )
        self.sound_alerts_switch.grid(
            row=2, column=0, columnspan=2, sticky="w", pady=15
        )

    def _on_appearance_change(self, choice):
        """Handles appearance mode changes."""
        if choice == "Gedimmt":
            # Force CTk into Light mode (or slightly modified dark mode), then tint the root window lighter
            ctk.set_appearance_mode("Dark")
            try:
                root = self.app
                # Soft dark: #2b2d3a – much lighter than full dark but not blinding like Light
                _DIMMED_BG = "#2b2d3a"
                root.configure(fg_color=_DIMMED_BG)
                root.main_container.configure(fg_color=_DIMMED_BG)
                root.content_frame.configure(fg_color=_DIMMED_BG)
                root.title_bar.configure(fg_color=_DIMMED_BG)
                # Also update the tabview bg
                root.tabview.configure(fg_color="#343748")
                root.status_bar.configure(fg_color="#343748")
            except Exception:
                pass
        elif choice == "White":
            ctk.set_appearance_mode("Light")
            try:
                root = self.app
                _WHITE_BG = "#FFFFFF"
                root.configure(fg_color=_WHITE_BG)
                root.main_container.configure(fg_color=_WHITE_BG)
                root.content_frame.configure(fg_color=_WHITE_BG)
                root.title_bar.configure(fg_color=_WHITE_BG)
                root.tabview.configure(fg_color="#F0F0F0")
                root.status_bar.configure(fg_color="#F0F0F0")
            except Exception:
                pass
        elif choice == "Dark":
            ctk.set_appearance_mode("Dark")
            try:
                root = self.app
                _DARK_BG = "#1a1a2e"
                root.configure(fg_color=_DARK_BG)
                root.main_container.configure(fg_color=_DARK_BG)
                root.content_frame.configure(fg_color=_DARK_BG)
                root.title_bar.configure(fg_color=_DARK_BG)
                root.tabview.configure(fg_color="#212135")
                root.status_bar.configure(fg_color="#212135")
            except Exception:
                pass
        else:  # System
            ctk.set_appearance_mode("System")
        self.app._trigger_autosave()

    def _set_fulldrive_visible(self, visible: bool):
        pass  # Obsolet, Logik in _on_trading_style_change

    def update_day_buttons_from_config(self):
        """Aktualisiert die visuellen Wochentag-Buttons basierend auf den geladenen Konfigurationswerten."""
        if not hasattr(self, "_day_buttons"):
            return

        active_color = "#00FF66"
        inactive_color = "#4A4A4A"

        # Mapping von Checkbox zu Button-ID
        day_mapping = {
            "day_mon": "day_mon",
            "day_tue": "day_tue",
            "day_wed": "day_wed",
            "day_thu": "day_thu",
            "day_fri": "day_fri",
            "day_sat": "day_sat",
            "day_sun": "day_sun",
        }

        for cb_name, btn_id in day_mapping.items():
            if hasattr(self, cb_name) and btn_id in self._day_buttons:
                is_active = bool(getattr(self, cb_name).get())
                btn_data = self._day_buttons[btn_id]

                # Variable aktualisieren
                btn_data["var"].set(is_active)

                # Visuelles Update
                if is_active:
                    btn_data["frame"].configure(fg_color=active_color)
                    btn_data["label"].configure(text_color="#000000")
                else:
                    btn_data["frame"].configure(fg_color=inactive_color)
                    btn_data["label"].configure(text_color="#AAAAAA")

    def _on_trading_style_change(self, choice=None):
        """Callback wenn Trading Style geändert wird."""
        if choice is None:
            choice = self.trading_style_var.get()
            
        self.fast_frame.pack_forget()
        self.fd_frame.pack_forget()
        self.default_frame.pack_forget()
        
        if "Scalping" in choice or "Day Trading" in choice:
            self.fast_frame.pack(fill="x", pady=5, padx=15)
        elif "AI-Fulldrive" in choice:
            self.fd_frame.pack(fill="x", pady=5, padx=15)
            self._refresh_fulldrive_kpis()
        else:
            self.default_frame.pack(fill="x", pady=5, padx=15)
            
        self._validate_risk_settings()
        self.app._trigger_autosave()

    def _validate_risk_settings(self, event=None):
        """Intelligente Live-Validierung der Risk-Manager Einstellungen (gemäß UX Vorgaben)."""
        is_valid = True
        warnings = []
        errors = []

        # Helfer zum Resetten
        fields = [
            self.risk_trade_entry,
            self.risk_daily_entry,
            self.rm_daily_loss_entry,
            self.rm_weekly_loss_entry,
            self.rm_max_trades_entry,
            self.max_pos_entry,
            self.monthly_target_entry,
            self.sl_dist_entry,
            self.ts_dist_entry,
            self.be_dist_entry,
        ]

        for f in fields:
            if f.winfo_exists():
                f.configure(border_color="#2A2D34")  # design-system background idle

        def mark_invalid(field, msg):
            nonlocal is_valid
            is_valid = False
            field.configure(border_color="#FF1744")
            if msg and msg not in errors:
                errors.append(msg)

        def mark_warning(field, msg):
            field.configure(border_color="#F39C12")  # Orange
            if msg and msg not in warnings:
                warnings.append(msg)

        try:
            # 1. Parsing
            max_trades = int(self.rm_max_trades_entry.get() or 0)
            max_pos = int(self.max_pos_entry.get() or 0)
            sl_dist = float(self.sl_dist_entry.get() or 0)
            be_dist = float(self.be_dist_entry.get() or 0)
            ts_dist = float(self.ts_dist_entry.get() or 0)
            risk_trade = float(self.risk_trade_entry.get() or 0)
            risk_daily = float(self.risk_daily_entry.get() or 0)
            monthly_target = float(self.monthly_target_entry.get() or 0)

            # --- RULES ---

            # Regel 1: Max Trades >= Max Offene Positionen
            if max_trades < max_pos:
                mark_invalid(
                    self.rm_max_trades_entry, "Max Trades müssen ≥ Max Positionen sein"
                )
                mark_invalid(self.max_pos_entry, "")

            # Regel 2: SL >= BE >= TS
            if (
                getattr(self, "break_even_switch", None)
                and self.break_even_switch.get()
            ):
                if sl_dist < be_dist:
                    mark_invalid(
                        self.sl_dist_entry, "Stop-Loss muss ≥ Break-Even Offset sein"
                    )
                    mark_invalid(self.be_dist_entry, "")

            if getattr(self, "trailing_stop_switch", None) and getattr(
                self, "break_even_switch", None
            ):
                if self.trailing_stop_switch.get() and self.break_even_switch.get():
                    if be_dist < ts_dist:
                        mark_invalid(
                            self.be_dist_entry,
                            "Break-Even muss ≥ Trailing Distanz sein",
                        )
                        mark_invalid(self.ts_dist_entry, "")

            # Regel 3: Risk per Trade * Positionen <= Max Daily Loss * 0.8
            max_exposure = risk_trade * max_pos
            if max_exposure > (risk_daily * 0.8):
                mark_warning(
                    self.risk_trade_entry,
                    f"Zu aggressiv! Risiko/Trade * Pos ({max_exposure}%) > 80% vom Daily Loss ({risk_daily}%)",
                )
                mark_warning(self.max_pos_entry, "")

            # Regel 4: Min Zeit dynamisch anpassen
            trading_style = (
                self.trading_style_var.get().lower()
                if getattr(self, "trading_style_var", None)
                else ""
            )
            current_cooldown = (
                self.rm_cooldown_slider.get()
                if getattr(self, "rm_cooldown_slider", None)
                else 300
            )

            if "scalping" in trading_style:
                if current_cooldown < 30:
                    self.rm_cooldown_slider.set(30)
                    self.rm_cooldown_lbl.configure(text="30 sek (Auto-Fix)")
            elif "swing" in trading_style:
                if current_cooldown < 900:  # 15 min
                    self.rm_cooldown_slider.set(900)
                    self.rm_cooldown_lbl.configure(text="900 sek (Auto-Fix)")

            # Regel 5: Broker-Realismus
            if sl_dist < 5:
                mark_invalid(self.sl_dist_entry, "Stop-Loss min. 5 Pips")
            if risk_trade > 5:
                mark_invalid(
                    self.risk_trade_entry,
                    "Risiko/Trade darf max. 5% sein (Retail Limit)",
                )
            if monthly_target > 20:
                mark_warning(
                    self.monthly_target_entry, "Monatsziel >20% ist unrealistisch"
                )

        except ValueError:
            is_valid = False
            errors.append("Formatfehler: Bitte nur Zahlen eingeben")

        # Summary Update
        if (
            getattr(self, "risk_summary_lbl", None)
            and self.risk_summary_lbl.winfo_exists()
        ):
            if not is_valid:
                if len(errors) > 0:
                    self.risk_summary_lbl.configure(
                        text="❌ " + errors[0], text_color="#FF1744"
                    )
            elif len(warnings) > 0:
                self.risk_summary_lbl.configure(
                    text="⚠️ " + warnings[0], text_color="#F39C12"
                )
            else:
                self.risk_summary_lbl.configure(
                    text="✅ Settings validiert & gespeichert", text_color="#00FF66"
                )

        # Nur speichern wenn valid
        if is_valid:
            self.app._trigger_autosave()

    def _refresh_fulldrive_kpis(self):
        """Holt aktuelle KPIs von der AIFulldriveEngine und aktualisiert Labels."""
        try:
            engine = getattr(self.app, "fulldrive_engine", None)
            if engine is None:
                return
            kpis = engine.get_kpis()
            self._fd_kpi_sharpe_lbl.configure(
                text=f"Sharpe: {kpis.get('sharpe', 0):.2f}",
                text_color="#00FF66" if kpis.get("sharpe", 0) >= 1.5 else "#FF1744",
            )
            self._fd_kpi_dd_lbl.configure(
                text=f"Max-DD: {kpis.get('max_drawdown', 0):.1f}%",
                text_color="#FF1744" if kpis.get("max_drawdown", 0) > 12 else "gray70",
            )
            self._fd_kpi_winrate_lbl.configure(
                text=f"Win-Rate: {kpis.get('win_rate', 0):.1f}%"
            )
            self._fd_kpi_annual_lbl.configure(
                text=f"Annual: {kpis.get('annual_return', 0):+.1f}%",
                text_color="#00FF66"
                if kpis.get("annual_return", 0) >= 25
                else "gray70",
            )
        except Exception:
            pass

    def _on_provider_change(self, choice=None):
        if choice is None:
            choice = self.ki_provider_var.get()

        cfg = getattr(self.app, "app_config", None)

        if "Ollama" in choice:
            self.url_lbl.configure(text="Ollama URL:")
            self.api_key_entry.configure(state="normal")
            self.api_key_entry.configure(fg_color="#1A1D24")
            self.api_key_entry.delete(0, "end")
            threading.Thread(
                target=self.fetch_ollama_models_silently, daemon=True
            ).start()

        elif "OpenAI" in choice:
            self.url_lbl.configure(text="Base URL (opt):")
            self.api_key_entry.configure(state="normal", fg_color="#1A1D24")
            self.api_key_entry.delete(0, "end")
            if cfg:
                self.api_key_entry.insert(
                    0, getattr(cfg, "api_key_openai", cfg.api_key)
                )
            self.model_combo.configure(
                values=["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
            )
            if self.model_combo.get() not in ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]:
                self.model_combo.set("gpt-4o")

        elif "Anthropic" in choice:
            self.url_lbl.configure(text="Base URL (opt):")
            self.api_key_entry.configure(state="normal", fg_color="#1A1D24")
            self.api_key_entry.delete(0, "end")
            if cfg:
                self.api_key_entry.insert(
                    0, getattr(cfg, "api_key_anthropic", cfg.api_key)
                )
            self.model_combo.configure(
                values=[
                    "claude-3-5-sonnet-20241022",
                    "claude-3-opus-20240229",
                    "claude-3-haiku-20240307",
                ]
            )
            if self.model_combo.get() not in [
                "claude-3-5-sonnet-20241022",
                "claude-3-opus-20240229",
                "claude-3-haiku-20240307",
            ]:
                self.model_combo.set("claude-3-5-sonnet-20241022")

        elif "DeepSeek" in choice:
            self.url_lbl.configure(text="Base URL (opt):")
            self.api_key_entry.configure(state="normal", fg_color="#1A1D24")
            self.api_key_entry.delete(0, "end")
            if cfg:
                self.api_key_entry.insert(
                    0, getattr(cfg, "api_key_deepseek", cfg.api_key)
                )
            self.model_combo.configure(values=["deepseek-chat", "deepseek-coder"])
            if self.model_combo.get() not in ["deepseek-chat", "deepseek-coder"]:
                self.model_combo.set("deepseek-chat")

        elif "OpenRouter" in choice:
            self.url_lbl.configure(text="Base URL (opt):")
            self.api_key_entry.configure(state="normal", fg_color="#1A1D24")
            self.api_key_entry.delete(0, "end")
            if cfg:
                self.api_key_entry.insert(
                    0, getattr(cfg, "api_key_openrouter", cfg.api_key)
                )
            self.model_combo.configure(values=["Lade Modelle..."])
            self.model_combo.set("Lade Modelle...")
            threading.Thread(
                target=self.fetch_openrouter_models_silently, daemon=True
            ).start()

        self.app._trigger_autosave()

    def fetch_ollama_models_silently(self):
        try:
            url = self.url_entry.get().strip()
            response = requests.get(f"{url}/api/tags", timeout=3)
            if response.status_code == 200:
                models = [model["name"] for model in response.json().get("models", [])]
                if models:
                    self.model_combo.configure(values=models)
                    self.model_combo.set(models[0])
                else:
                    self.model_combo.configure(values=["Keine Modelle gefunden"])
                    self.model_combo.set("Keine Modelle gefunden")
            else:
                self.model_combo.configure(values=["Verbindung fehlgeschlagen"])
                self.model_combo.set("Verbindung fehlgeschlagen")
        except Exception:
            self.model_combo.configure(values=["Verbindung fehlgeschlagen"])
            self.model_combo.set("Verbindung fehlgeschlagen")

    def fetch_openrouter_models_silently(self):
        try:
            url = "https://openrouter.ai/api/v1/models"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json().get("data", [])
                free_models = []
                for model in data:
                    pricing = model.get("pricing", {})
                    if pricing:
                        try:
                            prompt_price = float(pricing.get("prompt", -1))
                            comp_price = float(pricing.get("completion", -1))
                            if prompt_price == 0 and comp_price == 0:
                                free_models.append(model.get("id", ""))
                        except (ValueError, TypeError):
                            pass

                paid_models = [
                    "google/gemini-2.5-pro",
                    "anthropic/claude-3.5-sonnet",
                    "meta-llama/llama-3.3-70b-instruct",
                    "deepseek/deepseek-chat",
                ]

                all_models = paid_models + [
                    m for m in free_models if m not in paid_models
                ]

                current_val = self.model_combo.get()
                if (
                    current_val
                    and current_val not in all_models
                    and "Lade Modelle..." not in current_val
                ):
                    all_models.insert(0, current_val)

                if all_models:
                    self.model_combo.configure(values=all_models)
                    if self.model_combo.get() not in all_models:
                        self.model_combo.set(all_models[0])
                else:
                    self.model_combo.configure(values=paid_models)
                    if (
                        current_val
                        and current_val not in paid_models
                        and "Lade Modelle..." not in current_val
                    ):
                        self.model_combo.set(current_val)
                    else:
                        self.model_combo.set(paid_models[0])
            else:
                paid_models = [
                    "google/gemini-2.5-pro",
                    "anthropic/claude-3.5-sonnet",
                    "meta-llama/llama-3.3-70b-instruct",
                    "deepseek/deepseek-chat",
                ]
                self.model_combo.configure(values=paid_models)
                current_val = self.model_combo.get()
                if (
                    current_val
                    and current_val not in paid_models
                    and "Lade Modelle..." not in current_val
                ):
                    self.model_combo.set(current_val)
                else:
                    self.model_combo.set(paid_models[0])
        except Exception:
            paid_models = [
                "google/gemini-2.5-pro",
                "anthropic/claude-3.5-sonnet",
                "meta-llama/llama-3.3-70b-instruct",
                "deepseek/deepseek-chat",
            ]
            self.model_combo.configure(values=paid_models)
            current_val = self.model_combo.get()
            if (
                current_val
                and current_val not in paid_models
                and "Lade Modelle..." not in current_val
            ):
                self.model_combo.set(current_val)
            else:
                self.model_combo.set(paid_models[0])

    def test_ollama_connection(self):
        try:
            url = self.url_entry.get().strip()
            response = requests.get(f"{url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = [model["name"] for model in response.json().get("models", [])]
                if models:
                    self.model_combo.configure(values=models)
                    self.model_combo.set(models[0])
                    messagebox.showinfo(
                        "Erfolg", f"Ollama verbunden! {len(models)} Modelle gefunden."
                    )
                    self.app.write_terminal(
                        f">> Ollama Connection OK. Models: {', '.join(models)}\n"
                    )
                else:
                    self.model_combo.configure(values=["Keine Modelle gefunden"])
                    messagebox.showwarning(
                        "Warnung",
                        "Ollama ist erreichbar, aber es sind keine Modelle installiert.",
                    )
            else:
                messagebox.showerror(
                    "Fehler", f"Server antwortete mit Status: {response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            messagebox.showerror(
                "Verbindungsfehler", f"Ollama Daemon konnte nicht erreicht werden:\n{e}"
            )

    def _on_pairs_preset_change(self, choice):
        pairs_str = self._pair_presets.get(choice, "")
        if "Custom" in choice:
            self.pairs_entry.delete(0, "end")
            return

        validated_pairs = []
        if pairs_str:
            if mt5.initialize():
                symbols_info = mt5.symbols_get()
                all_symbols = [s.name for s in symbols_info] if symbols_info else []
                raw_pairs = [p.strip() for p in pairs_str.split(",")]

                for p in raw_pairs:
                    # 1. Direkter Match
                    if mt5.symbol_info(p):
                        validated_pairs.append(p)
                        continue

                    # 2. Suffix Match (z.B. EURUSD.p, AAPL_m)
                    if all_symbols:
                        matches = [
                            s
                            for s in all_symbols
                            if s.startswith(p) and len(s) <= len(p) + 4
                        ]
                        if matches:
                            # Bevorzuge kürzeres Suffix
                            matches.sort(key=len)
                            validated_pairs.append(matches[0])

                if not validated_pairs:
                    company = (
                        mt5.account_info().company
                        if mt5.account_info()
                        else "Unbekannt"
                    )
                    messagebox.showwarning(
                        "Fehlende Symbole",
                        f"Keines der Symbole aus dem Preset '{choice}' konnte bei deinem aktuellen Broker ({company}) gefunden werden.\n\n"
                        "Möglicherweise verwendet dein Broker andere Ticker-Bezeichnungen.",
                    )
            else:
                validated_pairs = [p.strip() for p in pairs_str.split(",")]

        self.pairs_entry.delete(0, "end")
        if validated_pairs:
            final_str = ", ".join(validated_pairs)
            self.pairs_entry.insert(0, final_str)
            self.app._trigger_autosave()

    def _on_account_switch(self, selected_account_str):
        self.app.write_terminal(f">> Wechsel zu Konto: {selected_account_str}...\n")
        try:
            login = int(selected_account_str.split(" - ")[0].strip())
            if mt5.initialize():
                result = mt5.login(login)
                if result:
                    self.app.write_terminal(">> ✅ Konto erfolgreich gewechselt.\n")
                    self._update_broker_labels()
                    self.app.dashboard_view.update_dashboard_data()
                else:
                    self.app.write_terminal(
                        f">> ❌ Fehler beim Kontowechsel. MT5 Fehlercode: {mt5.last_error()}\n",
                        "ERROR",
                    )
                    messagebox.showwarning(
                        "Login fehlgeschlagen",
                        "MT5 benötigt eventuell Passwort/Server.",
                    )
        except Exception as e:
            self.app.write_terminal(
                f">> ❌ Fehler beim Parsen des Kontos: {e}\n", "ERROR"
            )

    def _update_broker_labels(self):
        info = mt5.account_info()
        if info is not None:
            trade_mode = getattr(info, "trade_mode", None)
            type_map = {
                0: ("🟡 Demo", "#F1C40F"),
                2: ("🔴 Live", "#FF1744"),
                1: ("🟠 Contest", "#E67E22"),
            }
            text, color = type_map.get(
                trade_mode, (f"Unbekannt ({trade_mode})", "gray60")
            )

            currency = getattr(info, "currency", "")
            if "CENT" in currency.upper():
                text, color = "🪙 Cent", "#8E44AD"

            self._account_type_lbl.configure(text=f"Typ: {text}", text_color=color)

            company = getattr(info, "company", "Unbekannt")
            server = getattr(info, "server", "Unbekannt")
            self._broker_name_lbl.configure(
                text=f"Broker: {company}", text_color="#8B949E"
            )

            company_upper = company.upper()
            server_upper = server.upper()
            prop_keywords = [
                "FTMO",
                "FUNDED",
                "TFF",
                "EIGHTCAP",
                "TRUEFOREX",
                "MYFOREX",
                "MFF",
                "ALPHA",
                "SURGE",
                "BESPOKE",
                "FUNDING",
            ]
            is_prop = any(
                hint in company_upper or hint in server_upper for hint in prop_keywords
            )

            if is_prop:
                self._prop_firm_lbl.configure(
                    text="Prop Firm: ✅ Ja", text_color="#00FF66"
                )
            else:
                self._prop_firm_lbl.configure(
                    text="Prop Firm: ❌ Nein", text_color="#8B949E"
                )
        else:
            self._account_type_lbl.configure(
                text="Typ: ⚠️ Không verbunden", text_color="#8B949E"
            )
            self._broker_name_lbl.configure(text="Broker: --", text_color="#8B949E")
            self._prop_firm_lbl.configure(text="Prop Firm: --", text_color="#8B949E")

    def _detect_account_type(self):
        try:
            if mt5.initialize():
                self._update_broker_labels()
                current_info = mt5.account_info()
                if current_info:
                    current_str = f"{current_info.login} - {current_info.company}"
                    self.account_combo.configure(values=[current_str])
                    self.account_combo_var.set(current_str)
                return
        except Exception as e:
            self.app.write_terminal(
                f">> ❌ Fehler beim Lesen der Konten: {e}\n", "ERROR"
            )

        self.account_combo_var.set("⚠️ Nicht verbunden")
        self._update_broker_labels()

    def test_mt5_connection(self):
        if mt5.initialize():
            messagebox.showinfo("Erfolg", "MetaTrader 5 erfolgreich verbunden!")
            self.app.write_terminal(">> MT5 Connection re-initialized successfully.\n")
            self._detect_account_type()
        else:
            messagebox.showerror(
                "Fehler", "MT5 Terminal konnte nicht gefunden oder verbunden werden."
            )

    def _test_ollama_click(self):
        """Test Ollama connection and show a popup result. Runs in a background thread."""
        url = self.url_entry.get().strip() or "http://localhost:11434"
        try:
            resp = requests.get(f"{url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                msg = (
                    f"✅ Ollama verbunden!\n{len(models)} Modelle gefunden:\n"
                    + "\n".join(models[:8])
                )
                self.app.after(0, lambda: messagebox.showinfo("Ollama Test", msg))
                if models:
                    self.app.after(
                        0,
                        lambda: (
                            self.model_combo.configure(values=models),
                            self.model_combo.set(models[0]),
                        ),
                    )
            else:
                self.app.after(
                    0,
                    lambda: messagebox.showerror(
                        "Ollama Test", f"Status {resp.status_code}"
                    ),
                )
        except Exception as e:
            self.app.after(
                0,
                lambda err=str(e): messagebox.showerror(
                    "Ollama Test", f"Verbindung fehlgeschlagen:\n{err}"
                ),
            )

    def _send_telegram_test(self):
        """Send a test message via Telegram Bot API. Runs in a background thread."""
        token = self.tg_token_entry.get().strip()
        chat_id = self.tg_chat_id_entry.get().strip()
        if not token or not chat_id:
            self.app.after(
                0,
                lambda: messagebox.showwarning(
                    "Telegram Test", "Bitte Token und Chat-ID eingeben."
                ),
            )
            return
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "✅ FinGPT Test-Nachricht erfolgreich empfangen!",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                self.app.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Telegram Test", "✅ Nachricht erfolgreich gesendet!"
                    ),
                )
            else:
                self.app.after(
                    0,
                    lambda r=resp: messagebox.showerror(
                        "Telegram Test", f"Fehler {r.status_code}:\n{r.text[:200]}"
                    ),
                )
        except Exception as e:
            self.app.after(
                0,
                lambda err=str(e): messagebox.showerror(
                    "Telegram Test", f"Fehler:\n{err}"
                ),
            )

    def _build_mcp_tab(self, parent):
        """Build MCP Server configuration tab"""
        _, c1 = self._create_card(parent, "MCP Server Status", "#9C27B0")

        ctk.CTkLabel(
            c1,
            text="MCP Integration:",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=10, columnspan=2)

        self.mcp_enabled_switch = ctk.CTkSwitch(
            c1,
            text="MCP Server aktivieren",
            progress_color="#9C27B0",
            command=self._on_mcp_enabled_change,
        )
        self.mcp_enabled_switch.grid(row=1, column=0, sticky="w", pady=5, columnspan=2)

        ctk.CTkLabel(c1, text="TradingView MCP:", text_color="#4CAF50").grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.tradingview_status = ctk.CTkLabel(
            c1, text="❌ Nicht gestartet", text_color="#F44336"
        )
        self.tradingview_status.grid(row=2, column=1, sticky="w", pady=5, padx=10)

        ctk.CTkLabel(c1, text="Hive Intelligence MCP:", text_color="#FF9800").grid(
            row=3, column=0, sticky="w", pady=5
        )
        self.hive_status = ctk.CTkLabel(
            c1, text="❌ Nicht gestartet", text_color="#F44336"
        )
        self.hive_status.grid(row=3, column=1, sticky="w", pady=5, padx=10)

        _, c2 = self._create_card(parent, "Nutzung", "#2196F3")

        ctk.CTkLabel(
            c2,
            text="TradingView MCP bietet:",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=5)
        tv_features = [
            "• Stock Screening (USA Aktien)",
            "• Crypto Screening",
            "• Forex Screening",
            "• Technische Filter (RSI, MACD, etc.)",
            "• Preset Strategien",
        ]
        for i, feat in enumerate(tv_features, 1):
            ctk.CTkLabel(c2, text=feat).grid(
                row=i, column=0, sticky="w", padx=20, pady=2
            )

        ctk.CTkLabel(
            c2,
            text="Hive Intelligence bietet:",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
        ).grid(row=len(tv_features) + 1, column=0, sticky="w", pady=5)
        hive_features = [
            "• Crypto Preise & Sentiment",
            "• Forex Kurse",
            "• Aktienkurse",
            "• Markt-Zusammenfassung",
            "• DeFi TVL Daten",
        ]
        start_row = len(tv_features) + 2
        for i, feat in enumerate(hive_features, start_row):
            ctk.CTkLabel(c2, text=feat).grid(
                row=i, column=0, sticky="w", padx=20, pady=2
            )

        self.mcp_test_btn = ctk.CTkButton(
            c2,
            text="MCP Server manuell starten",
            fg_color="#9C27B0",
            hover_color="#7B1FA2",
            command=self._start_mcp_servers,
        )
        self.mcp_test_btn.grid(
            row=start_row + len(hive_features) + 1, column=0, sticky="w", pady=15
        )

    def _on_mcp_enabled_change(self):
        """Handle MCP enabled toggle"""
        enabled = self.mcp_enabled_switch.get() == 1
        cfg = getattr(self.app, "app_config", None)
        if cfg:
            cfg.mcp_enabled = enabled
            app_config_manager.save()

        if hasattr(self.app, "trading_controller") and self.app.trading_controller:
            tc = self.app.trading_controller
            if enabled and tc.mcp_engine:
                try:
                    tc.mcp_engine.start()
                    self.tradingview_status.configure(
                        text="✅ Aktiv", text_color="#4CAF50"
                    )
                    self.hive_status.configure(text="✅ Aktiv", text_color="#4CAF50")
                except Exception as e:
                    self.tradingview_status.configure(
                        text=f"❌ Fehler: {e}", text_color="#F44336"
                    )
            elif not enabled and tc.mcp_engine:
                try:
                    tc.mcp_engine.stop()
                    self.tradingview_status.configure(
                        text="❌ Gestoppt", text_color="#F44336"
                    )
                    self.hive_status.configure(text="❌ Gestoppt", text_color="#F44336")
                except Exception:
                    pass

        self.app._trigger_autosave()

    def _start_mcp_servers(self):
        """Startet MCP Server manuell – funktioniert auch ohne aktiven Live-Stream.
        
        Warum: Der trading_controller wird normalerweise erst beim Live-Stream-Start
        erstellt. Um den MCP-Test-Button unabhängig davon nutzbar zu machen,
        erstellen wir ihn hier on-demand, falls er noch nicht existiert.
        """
        # Stelle sicher dass trading_controller existiert
        if not hasattr(self.app, "trading_controller") or not self.app.trading_controller:
            try:
                from core.trading_controller import TradingController
                self.app.trading_controller = TradingController(self.app)
            except Exception as e:
                messagebox.showerror(
                    "MCP", f"Trading Controller konnte nicht erstellt werden:\n{e}"
                )
                return

        tc = self.app.trading_controller

        # Initialisiere MCP Engine falls nicht vorhanden
        if tc.mcp_engine is None:
            try:
                from core.mcp_integration import create_mcp_integration
                tc.mcp_engine = create_mcp_integration(self.app, None)
            except Exception as e:
                messagebox.showerror(
                    "MCP", f"MCP Engine konnte nicht erstellt werden:\n{e}"
                )
                return

        if tc.mcp_engine:
            try:
                tc.mcp_engine.start()
                self.tradingview_status.configure(
                    text="✅ Aktiv", text_color="#4CAF50"
                )
                self.hive_status.configure(text="✅ Aktiv", text_color="#4CAF50")
                messagebox.showinfo("MCP", "MCP Server erfolgreich gestartet!")
            except Exception as e:
                self.tradingview_status.configure(
                    text=f"❌ Fehler: {e}", text_color="#F44336"
                )
                self.hive_status.configure(
                    text=f"❌ Fehler: {e}", text_color="#F44336"
                )
                messagebox.showerror("MCP", f"Fehler beim Starten:\n{e}")
        else:
            messagebox.showwarning(
                "MCP", "MCP Engine konnte nicht erstellt werden."
            )
