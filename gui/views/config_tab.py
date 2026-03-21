import customtkinter as ctk
import threading
import requests
import MetaTrader5 as mt5
import tkinter.messagebox as messagebox
import tkinter as tk

class ConfigView:
    def __init__(self, master_tab, app):
        self.tab = master_tab
        self.app = app
        self._pair_presets = {
            "🏆 Majors (6 Paare)":
                "EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD",
            "🥈 Majors + Minors (14 Paare)":
                "EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, "
                "EURGBP, EURJPY, GBPJPY, AUDNZD, CADJPY, AUDCAD, NZDJPY",
            "🔀 Crosses (EUR/GBP/JPY Cross)":
                "EURGBP, EURJPY, EURCAD, EURAUD, EURNZD, EURCHF, "
                "GBPJPY, GBPCAD, GBPAUD, GBPNZD, GBPCHF",
            "💎 Exotics":
                "USDTRY, USDZAR, USDMXN, USDHKD, USDSGD, EURTRY, "
                "GBPTRY, XAUUSD, XAGUSD",
            "🌐 Alle Paare (Majors + Minors + Crosses)":
                "EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, "
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
        self.sidebar_frame = ctk.CTkFrame(self.tab, fg_color="#1A1D24", corner_radius=10, border_width=1, border_color="#2A2D34")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        ctk.CTkLabel(self.sidebar_frame, text="Einstellungen", font=ctk.CTkFont(family="Inter", size=18, weight="bold"), text_color="#FFFFFF").grid(row=0, column=0, padx=20, pady=(20, 15), sticky="w")
        ctk.CTkFrame(self.sidebar_frame, height=1, fg_color="#333").grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))

        self.categories = [
            ("🤖 KI & Ollama", self._build_ki_tab),
            ("🎨 Appearance", self._build_app_tab),
            ("📊 Trading Style", self._build_style_tab),
            ("🧠 RL Studio", self._build_rl_tab),
            ("⚙️ MT5 & System", self._build_mt5_tab),
            ("🔕 Benachrichtigungen", self._build_notif_tab)
        ]

        self.sidebar_buttons = {}
        row_idx = 2
        for name, _ in self.categories:
            btn = ctk.CTkButton(self.sidebar_frame, text=name, anchor="w", fg_color="transparent", text_color="#8B949E", 
                                font=ctk.CTkFont(family="Inter", size=14, weight="bold"), hover_color="#2A2D34", corner_radius=6, height=35,
                                command=lambda n=name: self._switch_category(n))
            btn.grid(row=row_idx, column=0, sticky="ew", padx=10, pady=2)
            self.sidebar_buttons[name] = btn
            row_idx += 1

        self.autosave_hint = ctk.CTkLabel(self.sidebar_frame, text="✅ Auto-Save", text_color="#00FF66", font=ctk.CTkFont(family="Inter", size=12, weight="bold"))
        self.autosave_hint.grid(row=11, column=0, sticky="ew", padx=20, pady=20)

        # Build Main Content Area
        self.content_container = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

        self.content_frames = {}
        for name, build_func in self.categories:
            frame = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")
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
        card = ctk.CTkFrame(parent, fg_color="#1A1D24", corner_radius=10, border_width=1, border_color="#2A2D34")
        card.pack(fill="x", padx=10, pady=10)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(family="Inter", size=15, weight="bold"), text_color=title_color).pack(side="left")
        ctk.CTkFrame(card, height=1, fg_color="#333").pack(fill="x", padx=15, pady=(0, 10))
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=(0, 15))
        content.grid_columnconfigure(1, weight=1)
        return card, content


    def _build_ki_tab(self, parent):
        _, c1 = self._create_card(parent, "API Einstellungen", "#2979FF")
        ctk.CTkLabel(c1, text="KI Provider:").grid(row=0, column=0, sticky="w", pady=5)
        self.ki_provider_var = ctk.StringVar(value="Ollama (Lokal)")
        self.ki_provider_combo = ctk.CTkComboBox(c1, values=["Ollama (Lokal)", "OpenAI (ChatGPT)", "Anthropic (Claude)", "DeepSeek"], variable=self.ki_provider_var, width=300, command=self._on_provider_change)
        self.ki_provider_combo.grid(row=0, column=1, sticky="w", pady=5, padx=10)
        
        self.url_lbl = ctk.CTkLabel(c1, text="Ollama URL:")
        self.url_lbl.grid(row=1, column=0, sticky="w", pady=5)
        self.url_entry = ctk.CTkEntry(c1, placeholder_text="http://localhost:11434", width=300)
        self.url_entry.insert(0, "http://localhost:11434")
        self.url_entry.grid(row=1, column=1, sticky="w", pady=5, padx=10)
        self.test_ollama_btn = ctk.CTkButton(c1, text="Test", width=60, height=28, fg_color="transparent", border_width=1, text_color="#8B949E", command=lambda: threading.Thread(target=self._test_ollama_click, daemon=True).start())
        self.test_ollama_btn.grid(row=1, column=2, padx=(0, 10))

        self.api_key_lbl = ctk.CTkLabel(c1, text="API Key:")
        self.api_key_lbl.grid(row=2, column=0, sticky="w", pady=5)
        self.api_key_entry = ctk.CTkEntry(c1, placeholder_text="sk-...", width=300, show="*")
        self.api_key_entry.grid(row=2, column=1, sticky="w", pady=5, padx=10)

        ctk.CTkLabel(c1, text="LLM Modell:").grid(row=3, column=0, sticky="w", pady=5)
        self.model_combo = ctk.CTkComboBox(c1, values=["Lade Modelle..."], width=300)
        self.model_combo.grid(row=3, column=1, sticky="w", pady=5, padx=10)

        _, c2 = self._create_card(parent, "System Parameter", "#00FF66")
        ctk.CTkLabel(c2, text="Auto-Trading Intervall (sek):").grid(row=0, column=0, sticky="w", pady=5)
        self.interval_slider = ctk.CTkSlider(c2, from_=1, to=30, number_of_steps=29)
        self.interval_slider.set(5)
        self.interval_slider.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        self.interval_lbl = ctk.CTkLabel(c2, text="5s")
        self.interval_lbl.grid(row=0, column=2)
        self.interval_slider.configure(command=lambda val: self.interval_lbl.configure(text=f"{int(val)}s"))

        ctk.CTkLabel(c2, text="KI Temperatur:").grid(row=1, column=0, sticky="w", pady=5)
        self.ai_temp_slider = ctk.CTkSlider(c2, from_=0.0, to=1.0, number_of_steps=10)
        self.ai_temp_slider.set(0.3)
        self.ai_temp_slider.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        self.ai_temp_lbl = ctk.CTkLabel(c2, text="0.3")
        self.ai_temp_lbl.grid(row=1, column=2)
        self.ai_temp_slider.configure(command=lambda val: self.ai_temp_lbl.configure(text=f"{val:.1f}"))

        ctk.CTkLabel(c2, text="Max Tokens:").grid(row=2, column=0, sticky="w", pady=5)
        self.max_tokens_slider = ctk.CTkSlider(c2, from_=100, to=4096, number_of_steps=39)
        self.max_tokens_slider.set(500)
        self.max_tokens_slider.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        self.max_tokens_lbl = ctk.CTkLabel(c2, text="500")
        self.max_tokens_lbl.grid(row=2, column=2)
        self.max_tokens_slider.configure(command=lambda val: (self.max_tokens_lbl.configure(text=f"{int(val)}"), self.app._trigger_autosave()))

        ctk.CTkLabel(c2, text="Min. Confidence (0-100%):").grid(row=3, column=0, sticky="w", pady=5)
        self.confidence_slider = ctk.CTkSlider(c2, from_=50, to=100, number_of_steps=50)
        self.confidence_slider.set(75)
        self.confidence_slider.grid(row=3, column=1, sticky="ew", padx=10, pady=5)
        self.confidence_lbl = ctk.CTkLabel(c2, text="75%")
        self.confidence_lbl.grid(row=3, column=2)
        self.confidence_slider.configure(command=lambda val: (self.confidence_lbl.configure(text=f"{int(val)}%"), self.app._trigger_autosave()))

        _, c3 = self._create_card(parent, "Prompts", "#9B59B6")
        ctk.CTkLabel(c3, text="Prompt-Sprache:").grid(row=0, column=0, sticky="w", pady=5)
        self.prompt_lang_var = ctk.StringVar(value="Deutsch")
        ctk.CTkComboBox(c3, values=["Deutsch", "Englisch", "Gemischt"], variable=self.prompt_lang_var).grid(row=0, column=1, sticky="w", pady=5, padx=10)

        ctk.CTkLabel(c3, text="System Prompt:").grid(row=1, column=0, sticky="nw", pady=5)
        self.system_prompt_text = ctk.CTkTextbox(c3, width=400, height=80, fg_color="#1A1D24", border_width=1, border_color="#2A2D34")
        self.system_prompt_text.insert("0.0", "Du bist ein professioneller Trading-Analyst. Bewerte den Markt objektiv basierend auf der technischen Ausgangslage und nutze eine klare, sachliche Sprache.")
        self.system_prompt_text.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.system_prompt_text.grid(row=1, column=1, sticky="w", pady=5, padx=10)

    def _build_app_tab(self, parent):
        _, c1 = self._create_card(parent, "UI Layout & Theming", "#F1C40F")
        ctk.CTkLabel(c1, text="Farb-Darstellung:").grid(row=0, column=0, sticky="w", pady=10)
        self.appearance_var = ctk.StringVar(value="Dark")
        app_combo = ctk.CTkComboBox(c1, values=["Dark", "Gedimmt", "System"], variable=self.appearance_var, width=300, command=self._on_appearance_change)
        app_combo.grid(row=0, column=1, sticky="w", pady=10, padx=20)
        
        ctk.CTkLabel(c1, text="Akzentfarbe:").grid(row=1, column=0, sticky="w", pady=10)
        self.theme_var = ctk.StringVar(value="green")
        theme_combo = ctk.CTkComboBox(c1, values=["blue", "green", "dark-blue"], variable=self.theme_var, width=300, command=lambda choice: (ctk.set_default_color_theme(choice), self.app._trigger_autosave()))
        theme_combo.grid(row=1, column=1, sticky="w", pady=10, padx=20)
        
        self.mica_switch = ctk.CTkSwitch(c1, text="Windows 11 Mica-Effekt (Glassmorphismus)", progress_color="#8E44AD", command=self.app._trigger_autosave)
        self.mica_switch.grid(row=2, column=0, columnspan=2, sticky="w", pady=15)

    def _build_style_tab(self, parent):
        _, c1 = self._create_card(parent, "Trading Strategie & Stil", "#E67E22")
        self.trading_active_switch = ctk.CTkSwitch(c1, text="Auto-Trading Global Erlauben", progress_color="#00FF66", command=self.app._trigger_autosave)
        self.trading_active_switch.select()
        self.trading_active_switch.grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
        
        ctk.CTkLabel(c1, text="Trading Style:").grid(row=1, column=0, sticky="w", pady=5)
        self.trading_style_var = ctk.StringVar(value="Swing Trading")
        self._style_combo = ctk.CTkComboBox(c1, values=["Scalping", "Day Trading", "Swing Trading", "Position Trading", "Price Action", "Breakout-Trading", "Mean Reversion", "AI-Fulldrive Mode 🤖"], variable=self.trading_style_var, width=260, command=self._on_trading_style_change)
        self._style_combo.grid(row=1, column=1, sticky="w", pady=5, padx=10)

        ctk.CTkLabel(c1, text="Signal-Strategie:").grid(row=2, column=0, sticky="w", pady=5)
        self.signal_strategy_var = ctk.StringVar(value="KI-gesteuert (Ollama)")
        ctk.CTkComboBox(c1, values=["KI-gesteuert (Ollama)", "Technische Indikatoren", "Hybrid (KI + Indikatoren)"], variable=self.signal_strategy_var, width=280, command=self.app._trigger_autosave).grid(row=2, column=1, sticky="w", pady=5, padx=10)

        ctk.CTkLabel(c1, text="Risikoprofil:").grid(row=3, column=0, sticky="w", pady=5)
        self.risk_profile_var = ctk.StringVar(value="Moderat")
        ctk.CTkComboBox(c1, values=["Konservativ", "Moderat", "Aggressiv"], variable=self.risk_profile_var, width=200, command=self.app._trigger_autosave).grid(row=3, column=1, sticky="w", pady=5, padx=10)

        _, c2 = self._create_card(parent, "Risk Manager", "#FF1744")
        ctk.CTkLabel(c2, text="Max Risiko pro Trade (%):").grid(row=0, column=0, sticky="w", pady=5)
        self.risk_trade_entry = ctk.CTkEntry(c2, width=80)
        self.risk_trade_entry.insert(0, "1.0")
        self.risk_trade_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.risk_trade_entry.grid(row=0, column=1, sticky="w", pady=5, padx=10)
        
        ctk.CTkLabel(c2, text="Max Daily Loss (%):").grid(row=1, column=0, sticky="w", pady=5)
        self.risk_daily_entry = ctk.CTkEntry(c2, width=80)
        self.risk_daily_entry.insert(0, "3.0")
        self.risk_daily_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.risk_daily_entry.grid(row=1, column=1, sticky="w", pady=5, padx=10)

        ctk.CTkLabel(c2, text="Max. Tagesverlust (€):").grid(row=2, column=0, sticky="w", pady=5)
        self.rm_daily_loss_entry = ctk.CTkEntry(c2, width=80)
        self.rm_daily_loss_entry.insert(0, "500")
        self.rm_daily_loss_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.rm_daily_loss_entry.grid(row=2, column=1, sticky="w", pady=5, padx=10)

        ctk.CTkLabel(c2, text="Max. Wochenverlust (€):").grid(row=3, column=0, sticky="w", pady=5)
        self.rm_weekly_loss_entry = ctk.CTkEntry(c2, width=80)
        self.rm_weekly_loss_entry.insert(0, "1500")
        self.rm_weekly_loss_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.rm_weekly_loss_entry.grid(row=3, column=1, sticky="w", pady=5, padx=10)

        ctk.CTkLabel(c2, text="Min. Zeit zwischen Trades (sek):").grid(row=4, column=0, sticky="w", pady=5)
        self.rm_cooldown_slider = ctk.CTkSlider(c2, from_=60, to=600, number_of_steps=54, width=180)
        self.rm_cooldown_slider.set(300)
        self.rm_cooldown_slider.grid(row=4, column=1, sticky="w", pady=5, padx=10)
        self.rm_cooldown_lbl = ctk.CTkLabel(c2, text="300 sek")
        self.rm_cooldown_lbl.grid(row=4, column=2)
        self.rm_cooldown_slider.configure(command=lambda v: (self.rm_cooldown_lbl.configure(text=f"{int(v)} sek"), self.app._trigger_autosave()))

        ctk.CTkLabel(c2, text="Max. Trades pro Tag:").grid(row=5, column=0, sticky="w", pady=5)
        self.rm_max_trades_entry = ctk.CTkEntry(c2, width=80)
        self.rm_max_trades_entry.insert(0, "10")
        self.rm_max_trades_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.rm_max_trades_entry.grid(row=5, column=1, sticky="w", pady=5, padx=10)

        ctk.CTkLabel(c2, text="Max Offene Positionen:").grid(row=6, column=0, sticky="w", pady=5)
        self.max_pos_entry = ctk.CTkEntry(c2, width=80)
        self.max_pos_entry.insert(0, "3")
        self.max_pos_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.max_pos_entry.grid(row=6, column=1, sticky="w", pady=5, padx=10)

        _, c3 = self._create_card(parent, "Stops & Protections", "#F1C40F")
        self.trailing_stop_switch = ctk.CTkSwitch(c3, text="Trailt Stops auf Gewinne automatisch", progress_color="#F1C40F", command=self.app._trigger_autosave)
        self.trailing_stop_switch.select()
        self.trailing_stop_switch.grid(row=0, column=0, sticky="w", pady=5)
        ctk.CTkLabel(c3, text="Trailing Abstand (Pips):").grid(row=0, column=1, sticky="e", pady=5)
        self.ts_dist_entry = ctk.CTkEntry(c3, width=80)
        self.ts_dist_entry.insert(0, "15")
        self.ts_dist_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.ts_dist_entry.grid(row=0, column=2, sticky="w", pady=5, padx=10)

        self.break_even_switch = ctk.CTkSwitch(c3, text="SL auf Einstieg nach X Pips", progress_color="#F1C40F", command=self.app._trigger_autosave)
        self.break_even_switch.grid(row=1, column=0, sticky="w", pady=5)
        ctk.CTkLabel(c3, text="BE Abstand (Pips):").grid(row=1, column=1, sticky="e", pady=5)
        self.be_dist_entry = ctk.CTkEntry(c3, width=80)
        self.be_dist_entry.insert(0, "10")
        self.be_dist_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.be_dist_entry.grid(row=1, column=2, sticky="w", pady=5, padx=10)

        self.weekend_exit_switch = ctk.CTkSwitch(c3, text="Wochenend-Schutz (Trades Freitags schließen)", progress_color="#FF1744", command=self.app._trigger_autosave)
        self.weekend_exit_switch.grid(row=2, column=0, columnspan=2, sticky="w", pady=10)
        
        _, c4 = self._create_card(parent, "Ausführungsqualität", "#00FF66")
        ctk.CTkLabel(c4, text="Max. Spread (Pips):").grid(row=0, column=0, sticky="w", pady=5)
        self.max_spread_slider = ctk.CTkSlider(c4, from_=1, to=20, number_of_steps=19, width=180)
        self.max_spread_slider.set(3)
        self.max_spread_slider.grid(row=0, column=1, sticky="w", pady=5, padx=10)
        self.max_spread_lbl = ctk.CTkLabel(c4, text="3 pips")
        self.max_spread_lbl.grid(row=0, column=2)
        self.max_spread_slider.configure(command=lambda v: (self.max_spread_lbl.configure(text=f"{int(v)} pips"), self.app._trigger_autosave()))

        ctk.CTkLabel(c4, text="Max. Slippage (Pips):").grid(row=1, column=0, sticky="w", pady=5)
        self.max_slippage_slider = ctk.CTkSlider(c4, from_=1, to=10, number_of_steps=9, width=180)
        self.max_slippage_slider.set(2)
        self.max_slippage_slider.grid(row=1, column=1, sticky="w", pady=5, padx=10)
        self.max_slippage_lbl = ctk.CTkLabel(c4, text="2 pips")
        self.max_slippage_lbl.grid(row=1, column=2)
        self.max_slippage_slider.configure(command=lambda v: (self.max_slippage_lbl.configure(text=f"{int(v)} pips"), self.app._trigger_autosave()))
        self.spread_check_switch = ctk.CTkSwitch(c4, text="Trade ablehnen wenn Spread zu hoch", progress_color="#00FF66", command=self.app._trigger_autosave)
        self.spread_check_switch.select()
        self.spread_check_switch.grid(row=2, column=0, columnspan=2, sticky="w", pady=5)


        # Fulldrive Widget references
        _, self.fd_card = self._create_card(parent, "🚀 AI-Fulldrive Mode Einstellungen", "#9B59B6")
        
        self._fd_conf_lbl_l = ctk.CTkLabel(self.fd_card, text="Min. Konfidenz (%):", text_color="#8B949E")
        self._fd_conf_lbl_l.grid(row=0, column=0, sticky="w", pady=5)
        self.fd_confidence_slider = ctk.CTkSlider(self.fd_card, from_=50, to=95, number_of_steps=45, width=180, progress_color="#9B59B6")
        self.fd_confidence_slider.set(70)
        self.fd_confidence_slider.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        self._fd_conf_val_lbl = ctk.CTkLabel(self.fd_card, text="70%")
        self._fd_conf_val_lbl.grid(row=0, column=2, sticky="w")
        self.fd_confidence_slider.configure(command=lambda v: (self._fd_conf_val_lbl.configure(text=f"{int(v)}%"), self.app._trigger_autosave()))

        self._fd_sharpe_lbl = ctk.CTkLabel(self.fd_card, text="Sharpe Ratio Ziel:", text_color="#8B949E")
        self._fd_sharpe_lbl.grid(row=1, column=0, sticky="w", pady=5)
        self.fd_sharpe_entry = ctk.CTkEntry(self.fd_card, width=90)
        self.fd_sharpe_entry.insert(0, "1.5")
        self.fd_sharpe_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.fd_sharpe_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        self._fd_dd_lbl = ctk.CTkLabel(self.fd_card, text="Max. Drawdown Limit (%):", text_color="#8B949E")
        self._fd_dd_lbl.grid(row=2, column=0, sticky="w", pady=5)
        self.fd_maxdd_entry = ctk.CTkEntry(self.fd_card, width=90)
        self.fd_maxdd_entry.insert(0, "15")
        self.fd_maxdd_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.fd_maxdd_entry.grid(row=2, column=1, sticky="w", padx=10, pady=5)

        self._fd_kpi_frame = ctk.CTkFrame(self.fd_card, fg_color="transparent")
        self._fd_kpi_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=10)
        self._fd_kpi_sharpe_lbl = ctk.CTkLabel(self._fd_kpi_frame, text="Sharpe: --")
        self._fd_kpi_sharpe_lbl.pack(side="left", padx=10)
        self._fd_kpi_dd_lbl = ctk.CTkLabel(self._fd_kpi_frame, text="Max-DD: --")
        self._fd_kpi_dd_lbl.pack(side="left", padx=10)
        self._fd_kpi_winrate_lbl = ctk.CTkLabel(self._fd_kpi_frame, text="Win-Rate: --")
        self._fd_kpi_winrate_lbl.pack(side="left", padx=10)
        self._fd_kpi_annual_lbl = ctk.CTkLabel(self._fd_kpi_frame, text="Annual: --")
        self._fd_kpi_annual_lbl.pack(side="left", padx=10)

        self._fd_selfopt_lbl = ctk.CTkLabel(self.fd_card, text="Selbst-Optimierung:", text_color="#8B949E")
        self._fd_selfopt_lbl.grid(row=4, column=0, sticky="w", pady=5)
        self.fd_selfopt_switch = ctk.CTkSwitch(self.fd_card, text="Auto-Retraining alle 50 Trades", progress_color="#9B59B6", command=self.app._trigger_autosave)
        self.fd_selfopt_switch.select()
        self.fd_selfopt_switch.grid(row=4, column=1, columnspan=2, sticky="w", padx=10, pady=5)
        
        self._fulldrive_widgets = [ self._fd_conf_lbl_l, self.fd_confidence_slider, self._fd_conf_val_lbl, self._fd_sharpe_lbl, self.fd_sharpe_entry, self._fd_dd_lbl, self.fd_maxdd_entry, self._fd_kpi_frame, self._fd_selfopt_lbl, self.fd_selfopt_switch ]
        self._set_fulldrive_visible(False)
        self.fd_card.master.pack_forget() # hide the card wrapper initially

    def _build_rl_tab(self, parent):
        _, c1 = self._create_card(parent, "Reinforcement Learning Parameter", "#8E44AD")
        ctk.CTkLabel(c1, text="RL Algorithmus:").grid(row=0, column=0, sticky="w", pady=5)
        self.rl_algo_var = ctk.StringVar(value="PPO")
        ctk.CTkComboBox(c1, values=["PPO", "DQN", "A2C", "SAC"], variable=self.rl_algo_var, width=180, command=self.app._trigger_autosave).grid(row=0, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c1, text="Lernrate:").grid(row=1, column=0, sticky="w", pady=5)
        self.rl_lr_slider = ctk.CTkSlider(c1, from_=0.0001, to=0.01, number_of_steps=99)
        self.rl_lr_slider.set(0.0003)
        self.rl_lr_slider.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        self.rl_lr_lbl = ctk.CTkLabel(c1, text="0.0003")
        self.rl_lr_lbl.grid(row=1, column=2)
        self.rl_lr_slider.configure(command=lambda val: (self.rl_lr_lbl.configure(text=f"{val:.4f}"), self.app._trigger_autosave()))

        ctk.CTkLabel(c1, text="Gamma (Discount):").grid(row=2, column=0, sticky="w", pady=5)
        self.rl_gamma_slider = ctk.CTkSlider(c1, from_=0.8, to=1.0, number_of_steps=20)
        self.rl_gamma_slider.set(0.99)
        self.rl_gamma_slider.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        self.rl_gamma_lbl = ctk.CTkLabel(c1, text="0.99")
        self.rl_gamma_lbl.grid(row=2, column=2)
        self.rl_gamma_slider.configure(command=lambda val: (self.rl_gamma_lbl.configure(text=f"{val:.2f}"), self.app._trigger_autosave()))

        ctk.CTkLabel(c1, text="Training Steps:").grid(row=3, column=0, sticky="w", pady=5)
        self.rl_steps_entry = ctk.CTkEntry(c1, width=120)
        self.rl_steps_entry.insert(0, "100000")
        self.rl_steps_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.rl_steps_entry.grid(row=3, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c1, text="Belohnungsfunktion:").grid(row=4, column=0, sticky="w", pady=5)
        self.rl_reward_var = ctk.StringVar(value="Profit + Sharpe Ratio")
        ctk.CTkComboBox(c1, values=["Profit + Sharpe Ratio", "Reiner Profit", "Sortino Ratio", "Custom"], variable=self.rl_reward_var, width=250, command=self.app._trigger_autosave).grid(row=4, column=1, sticky="w", padx=10, pady=5)

        _, c2 = self._create_card(parent, "Advanced RL Parameters", "#F39C12")
        ctk.CTkLabel(c2, text="Replay Buffer Size:").grid(row=0, column=0, sticky="w", pady=5)
        self.rl_buffer_entry = ctk.CTkEntry(c2, width=100)
        self.rl_buffer_entry.insert(0, "10000")
        self.rl_buffer_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.rl_buffer_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c2, text="Batch Size:").grid(row=0, column=2, sticky="w", pady=5)
        self.rl_batch_entry = ctk.CTkEntry(c2, width=100)
        self.rl_batch_entry.insert(0, "64")
        self.rl_batch_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.rl_batch_entry.grid(row=0, column=3, sticky="w", padx=10, pady=5)
        
        ctk.CTkLabel(c2, text="Epochs (PPO):").grid(row=1, column=0, sticky="w", pady=5)
        self.rl_epochs_entry = ctk.CTkEntry(c2, width=100)
        self.rl_epochs_entry.insert(0, "10")
        self.rl_epochs_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.rl_epochs_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c2, text="Target Update (DQN):").grid(row=1, column=2, sticky="w", pady=5)
        self.rl_target_update_entry = ctk.CTkEntry(c2, width=100)
        self.rl_target_update_entry.insert(0, "1000")
        self.rl_target_update_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.rl_target_update_entry.grid(row=1, column=3, sticky="w", padx=10, pady=5)
        
        _, c3 = self._create_card(parent, "Neural Network & Model", "#9B59B6")
        ctk.CTkLabel(c3, text="Netzwerk-Architektur:").grid(row=0, column=0, sticky="w", pady=5)
        self.rl_nn_arch_var = ctk.StringVar(value="Mittel (128-128)")
        ctk.CTkComboBox(c3, values=["Klein (64-64)", "Mittel (128-128)", "Groß (256-256)"], variable=self.rl_nn_arch_var, width=200, command=lambda v: self.app._trigger_autosave()).grid(row=0, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(c3, text="Checkpoint Pfad:").grid(row=1, column=0, sticky="w", pady=5)
        self.rl_checkpoint_entry = ctk.CTkEntry(c3, placeholder_text="storage/rl_agents/model.zip", width=300)
        self.rl_checkpoint_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.rl_checkpoint_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        self.rl_live_switch = ctk.CTkSwitch(c3, text="RL Agent für Live-Trading aktivieren (Experimentell)", progress_color="#8E44AD", command=self.app._trigger_autosave)
        self.rl_live_switch.grid(row=2, column=0, columnspan=2, sticky="w", pady=15)

    def _build_mt5_tab(self, parent):
        _, c1 = self._create_card(parent, "MetaTrader 5 & System", "#FF1744")
        ctk.CTkButton(c1, text="MT5 Manuell Neuverbinden", command=self.test_mt5_connection, fg_color="transparent", border_width=1, text_color="#8B949E").grid(row=0, column=0, sticky="w", pady=5)
        
        ctk.CTkLabel(c1, text="Konto:").grid(row=1, column=0, sticky="w", pady=5)
        self.account_combo_var = ctk.StringVar(value="🔍 Wird ermittelt...")
        self.account_combo = ctk.CTkComboBox(c1, variable=self.account_combo_var, values=["Wird geladen..."], width=350, command=self._on_account_switch)
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
        pairs_preset_combo = ctk.CTkComboBox(c2, values=list(self._pair_presets.keys()), variable=self._pairs_preset_var, width=350, command=self._on_pairs_preset_change)
        pairs_preset_combo.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        ctk.CTkLabel(c2, text="Aktive Paare:").grid(row=1, column=0, sticky="nw", pady=5)
        self.pairs_entry = ctk.CTkEntry(c2, width=350)
        self.pairs_entry.insert(0, self._pair_presets["🏆 Majors (6 Paare)"])
        self.pairs_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.pairs_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        self.debug_mode_switch = ctk.CTkSwitch(c2, text="Debug-Modus (mehr Terminal-Output)", progress_color="#FF1744", command=self.app._trigger_autosave)
        self.debug_mode_switch.grid(row=2, column=0, columnspan=2, sticky="w", pady=15)

    def _build_notif_tab(self, parent):
        _, c1 = self._create_card(parent, "Discord & Telegram Integrations", "#F1C40F")
        ctk.CTkLabel(c1, text="Discord Webhook URL:").grid(row=0, column=0, sticky="w", pady=5)
        self.discord_webhook_entry = ctk.CTkEntry(c1, width=350, placeholder_text="https://discord.com/api/webhooks/...")
        self.discord_webhook_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.discord_webhook_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        ctk.CTkLabel(c1, text="Telegram Bot Token:").grid(row=1, column=0, sticky="w", pady=5)
        self.tg_token_entry = ctk.CTkEntry(c1, width=350, placeholder_text="123456:ABC-DEF...")
        self.tg_token_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.tg_token_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        ctk.CTkLabel(c1, text="Telegram Chat ID:").grid(row=2, column=0, sticky="w", pady=5)
        self.tg_chat_id_entry = ctk.CTkEntry(c1, width=200, placeholder_text="-100123...")
        self.tg_chat_id_entry.bind("<KeyRelease>", lambda e: self.app._trigger_autosave())
        self.tg_chat_id_entry.grid(row=2, column=1, sticky="w", padx=10, pady=5)
        
        self.tg_test_btn = ctk.CTkButton(c1, text="📤 Test-Nachricht", width=200, fg_color="#2979FF", command=lambda: threading.Thread(target=self._send_telegram_test, daemon=True).start())
        self.tg_test_btn.grid(row=3, column=0, columnspan=2, sticky="w", pady=15)

        _, c2 = self._create_card(parent, "Benachrichtigungsfilter", "#00FF66")
        self.notif_sl_hit = ctk.CTkCheckBox(c2, text="SL Hit", command=self.app._trigger_autosave)
        self.notif_sl_hit.select(); self.notif_sl_hit.grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.notif_tp_hit = ctk.CTkCheckBox(c2, text="TP Hit", command=self.app._trigger_autosave)
        self.notif_tp_hit.select(); self.notif_tp_hit.grid(row=0, column=1, sticky="w", pady=5, padx=5)
        
        self.notif_new_trade = ctk.CTkCheckBox(c2, text="Neuer Trade", command=self.app._trigger_autosave)
        self.notif_new_trade.select(); self.notif_new_trade.grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.notif_error = ctk.CTkCheckBox(c2, text="Fehler & Kritisch", command=self.app._trigger_autosave)
        self.notif_error.select(); self.notif_error.grid(row=1, column=1, sticky="w", pady=5, padx=5)

        self.sound_alerts_switch = ctk.CTkSwitch(c2, text="Trade-Sounds abspielen (Öffnen/Schließen)", progress_color="#F1C40F", command=self.app._trigger_autosave)
        self.sound_alerts_switch.grid(row=2, column=0, columnspan=2, sticky="w", pady=15)

    def _on_appearance_change(self, choice):
        """Handles appearance mode changes. 'Gedimmt' = soft dark gray."""
        if choice == "Gedimmt":
            # Force CTk into Dark mode, then tint the root window lighter
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
        """Zeige/verstecke den AI-Fulldrive Einstellungsbereich."""
        try:
            for widget in self._fulldrive_widgets:
                if visible:
                    widget.grid()
                else:
                    widget.grid_remove()
        except Exception:
            pass

    def _on_trading_style_change(self, choice=None):
        """Callback wenn Trading Style geändert wird."""
        if choice is None:
            choice = self.trading_style_var.get()
        is_fulldrive = ("AI-Fulldrive" in choice)
        self._set_fulldrive_visible(is_fulldrive)
        self.app._trigger_autosave()
        # KPI-Labels aktualisieren wenn Engine bereits läuft
        if is_fulldrive:
            self._refresh_fulldrive_kpis()

    def _refresh_fulldrive_kpis(self):
        """Holt aktuelle KPIs von der AIFulldriveEngine und aktualisiert Labels."""
        try:
            engine = getattr(self.app, 'fulldrive_engine', None)
            if engine is None:
                return
            kpis = engine.get_kpis()
            self._fd_kpi_sharpe_lbl.configure(
                text=f"Sharpe: {kpis.get('sharpe', 0):.2f}",
                text_color="#00FF66" if kpis.get('sharpe', 0) >= 1.5 else "#FF1744")
            self._fd_kpi_dd_lbl.configure(
                text=f"Max-DD: {kpis.get('max_drawdown', 0):.1f}%",
                text_color="#FF1744" if kpis.get('max_drawdown', 0) > 12 else "gray70")
            self._fd_kpi_winrate_lbl.configure(
                text=f"Win-Rate: {kpis.get('win_rate', 0):.1f}%")
            self._fd_kpi_annual_lbl.configure(
                text=f"Annual: {kpis.get('annual_return', 0):+.1f}%",
                text_color="#00FF66" if kpis.get('annual_return', 0) >= 25 else "gray70")
        except Exception:
            pass

    def _on_provider_change(self, choice=None):
        if choice is None:
            choice = self.ki_provider_var.get()
            
        if "Ollama" in choice:
            self.url_lbl.configure(text="Ollama URL:")
            self.api_key_entry.configure(state="normal") 
            self.api_key_entry.configure(fg_color="#1A1D24")
            threading.Thread(target=self.fetch_ollama_models_silently, daemon=True).start()
        elif "OpenAI" in choice:
            self.url_lbl.configure(text="Base URL (opt):")
            self.api_key_entry.configure(state="normal", fg_color="#1A1D24")
            self.model_combo.configure(values=["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"])
            if self.model_combo.get() not in ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]:
                self.model_combo.set("gpt-4o")
        elif "Anthropic" in choice:
            self.url_lbl.configure(text="Base URL (opt):")
            self.api_key_entry.configure(state="normal", fg_color="#1A1D24")
            self.model_combo.configure(values=["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"])
            if self.model_combo.get() not in ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"]:
                self.model_combo.set("claude-3-5-sonnet-20241022")
        elif "DeepSeek" in choice:
            self.url_lbl.configure(text="Base URL (opt):")
            self.api_key_entry.configure(state="normal", fg_color="#1A1D24")
            self.model_combo.configure(values=["deepseek-chat", "deepseek-coder"])
            if self.model_combo.get() not in ["deepseek-chat", "deepseek-coder"]:
                self.model_combo.set("deepseek-chat")
            
        self.app._trigger_autosave()

    def fetch_ollama_models_silently(self):
        try:
            url = self.url_entry.get().strip()
            response = requests.get(f"{url}/api/tags", timeout=3)
            if response.status_code == 200:
                models = [model['name'] for model in response.json().get('models', [])]
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

    def test_ollama_connection(self):
        try:
            url = self.url_entry.get().strip()
            response = requests.get(f"{url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = [model['name'] for model in response.json().get('models', [])]
                if models:
                    self.model_combo.configure(values=models)
                    self.model_combo.set(models[0])
                    messagebox.showinfo("Erfolg", f"Ollama verbunden! {len(models)} Modelle gefunden.")
                    self.app.write_terminal(f">> Ollama Connection OK. Models: {', '.join(models)}\n")
                else:
                    self.model_combo.configure(values=["Keine Modelle gefunden"])
                    messagebox.showwarning("Warnung", "Ollama ist erreichbar, aber es sind keine Modelle installiert.")
            else:
                messagebox.showerror("Fehler", f"Server antwortete mit Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Verbindungsfehler", f"Ollama Daemon konnte nicht erreicht werden:\n{e}")

    def _on_pairs_preset_change(self, choice):
        pairs = self._pair_presets.get(choice, "")
        self.pairs_entry.delete(0, "end")
        if pairs:
            self.pairs_entry.insert(0, pairs)
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
                    self.app.write_terminal(f">> ❌ Fehler beim Kontowechsel. MT5 Fehlercode: {mt5.last_error()}\n", "ERROR")
                    messagebox.showwarning("Login fehlgeschlagen", "MT5 benötigt eventuell Passwort/Server.")
        except Exception as e:
            self.app.write_terminal(f">> ❌ Fehler beim Parsen des Kontos: {e}\n", "ERROR")

    def _update_broker_labels(self):
        info = mt5.account_info()
        if info is not None:
            trade_mode = getattr(info, 'trade_mode', None)
            type_map = {
                0: ("🟡 Demo",    "#F1C40F"),
                2: ("🔴 Live",    "#FF1744"),
                1: ("🟠 Contest", "#E67E22"),
            }
            text, color = type_map.get(trade_mode, (f"Unbekannt ({trade_mode})", "gray60"))
            
            currency = getattr(info, 'currency', '')
            if 'CENT' in currency.upper():
                text, color = "🪙 Cent", "#8E44AD"
                
            self._account_type_lbl.configure(text=f"Typ: {text}", text_color=color)
            
            company = getattr(info, 'company', 'Unbekannt')
            server = getattr(info, 'server', 'Unbekannt')
            self._broker_name_lbl.configure(text=f"Broker: {company}", text_color="#8B949E")
            
            company_upper = company.upper()
            server_upper = server.upper()
            prop_keywords = ["FTMO", "FUNDED", "TFF", "EIGHTCAP", "TRUEFOREX", "MYFOREX", "MFF", "ALPHA", "SURGE", "BESPOKE", "FUNDING"]
            is_prop = any(hint in company_upper or hint in server_upper for hint in prop_keywords)
            
            if is_prop:
                self._prop_firm_lbl.configure(text="Prop Firm: ✅ Ja", text_color="#00FF66")
            else:
                self._prop_firm_lbl.configure(text="Prop Firm: ❌ Nein", text_color="#8B949E")
        else:
            self._account_type_lbl.configure(text="Typ: ⚠️ Không verbunden", text_color="#8B949E")
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
            self.app.write_terminal(f">> ❌ Fehler beim Lesen der Konten: {e}\n", "ERROR")
            
        self.account_combo_var.set("⚠️ Nicht verbunden")
        self._update_broker_labels()

    def test_mt5_connection(self):
        if mt5.initialize():
            messagebox.showinfo("Erfolg", "MetaTrader 5 erfolgreich verbunden!")
            self.app.write_terminal(">> MT5 Connection re-initialized successfully.\n")
            self._detect_account_type()
        else:
            messagebox.showerror("Fehler", "MT5 Terminal konnte nicht gefunden oder verbunden werden.")

    def _test_ollama_click(self):
        """Test Ollama connection and show a popup result. Runs in a background thread."""
        url = self.url_entry.get().strip() or "http://localhost:11434"
        try:
            resp = requests.get(f"{url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m['name'] for m in resp.json().get('models', [])]
                msg = f"✅ Ollama verbunden!\n{len(models)} Modelle gefunden:\n" + "\n".join(models[:8])
                self.app.after(0, lambda: messagebox.showinfo("Ollama Test", msg))
                if models:
                    self.app.after(0, lambda: (self.model_combo.configure(values=models), self.model_combo.set(models[0])))
            else:
                self.app.after(0, lambda: messagebox.showerror("Ollama Test", f"Status {resp.status_code}"))
        except Exception as e:
            self.app.after(0, lambda err=str(e): messagebox.showerror("Ollama Test", f"Verbindung fehlgeschlagen:\n{err}"))

    def _send_telegram_test(self):
        """Send a test message via Telegram Bot API. Runs in a background thread."""
        token   = self.tg_token_entry.get().strip()
        chat_id = self.tg_chat_id_entry.get().strip()
        if not token or not chat_id:
            self.app.after(0, lambda: messagebox.showwarning(
                "Telegram Test", "Bitte Token und Chat-ID eingeben."))
            return
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": "✅ FinGPT Test-Nachricht erfolgreich empfangen!"},
                timeout=10
            )
            if resp.status_code == 200:
                self.app.after(0, lambda: messagebox.showinfo("Telegram Test", "✅ Nachricht erfolgreich gesendet!"))
            else:
                self.app.after(0, lambda r=resp: messagebox.showerror("Telegram Test", f"Fehler {r.status_code}:\n{r.text[:200]}"))
        except Exception as e:
            self.app.after(0, lambda err=str(e): messagebox.showerror("Telegram Test", f"Fehler:\n{err}"))

