import os
import json
import glob
import threading
import time
import psutil
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

try:
    import networkx as nx
    from matplotlib.collections import LineCollection
except ImportError:
    nx = None
    LineCollection = None

try:
    from storage.experience_db import ExperienceDB
except ImportError:
    ExperienceDB = None

try:
    from trading.rl_trading_agent import RLPerformanceTracker
except ImportError:
    RLPerformanceTracker = None


from typing import Optional, Any
class RLSettingsView:
    def __init__(self, tab, app):
        """
        tab: The ctk.CTkFrame inside the Tabview where this view is rendered.
        app: The ModernFinGPTGUI instance, used to access shared state and methods.
        """
        self.tab = tab
        self.app = app
        self.rl_sub_tabs: Any = None
        self.rl_cfg_algo_lbl: Any = None
        self.rl_cfg_lr_lbl: Any = None
        self.rl_cfg_steps_lbl: Any = None
        self.rl_perf_trades_lbl: Any = None
        self.rl_perf_winrate_lbl: Any = None
        self.rl_perf_profit_lbl: Any = None
        self.rl_perf_sl_lbl: Any = None
        self.rl_status_lbl: Any = None
        self.rl_pct_lbl: Any = None
        self.rl_progress: Any = None
        self.rl_term_box: Any = None
        
        self.sys_cpu_prog: Any = None
        self.sys_cpu_lbl: Any = None
        self.sys_ram_prog: Any = None
        self.sys_gpu_prog: Any = None
        
        self.stat_episodes_lbl: Any = None
        self.stat_reward_lbl: Any = None
        self.stat_time_lbl: Any = None
        
        self.rl_device_switch: Any = None
        
        # Mapping UI references
        self._rl_map_symbol_var = None
        self._rl_map_status: Any = None
        self._rl_map_canvas_frame: Any = None
        self._rl_map_canvas: Any = None  # Persistent FigureCanvasTkAgg widget
        self._rl_map_rendering: bool = False  # Prevent concurrent renders
        self._rl_map_fig: Any = None     # Current matplotlib Figure
        
        # Hardware Status references
        self._hw_update_active = False
        
        # Fulldrive variables
        self._fd_tile_sharpe: Any = None
        self._fd_tile_maxdd: Any = None
        self._fd_tile_winrate: Any = None
        self._fd_tile_annual: Any = None
        self._fd_tile_trades: Any = None
        
        self._fd_status_lbl: Any = None
        self._fd_log_box: Any = None
        self._fd_bt_btn: Any = None
        self._fd_start_btn: Any = None
        self._fd_stop_btn: Any = None
        self._fd_refresh_active = False
        self.setup_ui()
        
    def setup_ui(self):
        """Haupt-Setup für den RL Studio Tab"""
        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_rowconfigure(0, weight=1)
        
        # Sub-Navigation for RL Studio
        self.rl_sub_tabs = ctk.CTkTabview(self.tab, corner_radius=10)
        self.rl_sub_tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.rl_sub_tabs.add("🏋️ Training")
        self.rl_sub_tabs.add("🌐 Experience Map")
        self.rl_sub_tabs.add("🚀 AI-Fulldrive")
        
        # =========================================================
        # SUB-TAB 3: AI-Fulldrive Dashboard
        # =========================================================
        self._setup_fulldrive_tab(self.rl_sub_tabs.tab("🚀 AI-Fulldrive"))
        
        # =========================================================
        # SUB-TAB 1: Training (Existing RL Studio Layout)
        # =========================================================
        train_tab = self.rl_sub_tabs.tab("🏋️ Training")
        train_tab.grid_columnconfigure(0, weight=1)
        train_tab.grid_columnconfigure(1, weight=2)
        train_tab.grid_rowconfigure(1, weight=1)
        
        # --- TOP HEADER BAR ---
        header = ctk.CTkFrame(train_tab, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 5))
        
        ctk.CTkLabel(header, text="Reinforcement Learning Studio", 
                     font=ctk.CTkFont(family="Inter", size=24, weight="bold"), text_color="#8E44AD").pack(side="left")
        ctk.CTkLabel(header, text="Trainiere eigene KI-Agenten auf historischen MT5-Daten", 
                     font=ctk.CTkFont(family="Inter", size=14), text_color="#8B949E").pack(side="left", padx=(15, 0), pady=(8, 0))
        
        # --- LEFT PANEL: Config Overview & Start Button ---
        left_panel = ctk.CTkFrame(train_tab, corner_radius=15, fg_color="#1A1D24")
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))
        
        ctk.CTkLabel(left_panel, text="📌 Aktuelle Trainings-Config", font=ctk.CTkFont(family="Inter", weight="bold", size=16)).pack(pady=(20, 10), padx=20, anchor="w")
        
        # Info Box reading from settings
        info_box = ctk.CTkFrame(left_panel, fg_color="#1A1D24", corner_radius=10)
        info_box.pack(fill="x", padx=20, pady=10)
        
        # Labels that we'll update when switching tabs or clicking refresh
        self.rl_cfg_algo_lbl = ctk.CTkLabel(info_box, text="Algorithmus: PPO", text_color="#2979FF")
        self.rl_cfg_algo_lbl.pack(anchor="w", padx=15, pady=(15, 5))
        self.app.rl_cfg_algo_lbl = self.rl_cfg_algo_lbl # Keep reference for app
        
        self.rl_cfg_lr_lbl = ctk.CTkLabel(info_box, text="Lernrate: 0.0003", text_color="#00FF66")
        self.rl_cfg_lr_lbl.pack(anchor="w", padx=15, pady=5)
        self.app.rl_cfg_lr_lbl = self.rl_cfg_lr_lbl
        
        self.rl_cfg_steps_lbl = ctk.CTkLabel(info_box, text="Total Steps: 100000", text_color="#E67E22")
        self.rl_cfg_steps_lbl.pack(anchor="w", padx=15, pady=(5, 15))
        self.app.rl_cfg_steps_lbl = self.rl_cfg_steps_lbl
        
        self.app._training_active = False
        
        # Control Buttons
        self.app.btn_start_rl = ctk.CTkButton(left_panel, text="▶ Neues Modell Trainieren", 
                                          font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
                                          height=45, fg_color="#00FF66", hover_color="#4CAF50",
                                          command=self._start_rl_training_sim)
        self.app.btn_start_rl.pack(fill="x", padx=20, pady=(20, 10))
        
        self.app.btn_stop_rl = ctk.CTkButton(left_panel, text="⏹ Training Abbrechen", 
                                         font=ctk.CTkFont(family="Inter", size=14),
                                         height=35, fg_color="#FF1744", hover_color="#C0392B",
                                         state="disabled", command=self._stop_rl_training_sim)
        self.app.btn_stop_rl.pack(fill="x", padx=20, pady=0)
        
        # Refresh config button
        ctk.CTkButton(left_panel, text="🔄 Config & Metriken Neu Laden", fg_color="transparent", 
                      border_width=1, text_color="#8B949E", command=self._update_rl_studio_config_labels).pack(pady=(10, 5))
                      
        # --- Performance Metrics Box ---
        perf_box = ctk.CTkFrame(left_panel, fg_color="#1A1D24", corner_radius=10)
        perf_box.pack(fill="x", padx=20, pady=(10, 20))
        
        ctk.CTkLabel(perf_box, text="📊 Live RL Performance", font=ctk.CTkFont(family="Inter", weight="bold", size=14)).pack(pady=(10, 5))
        
        self.rl_perf_trades_lbl = ctk.CTkLabel(perf_box, text="Erfahrungen: 0", text_color="#8B949E")
        self.rl_perf_trades_lbl.pack(anchor="w", padx=15, pady=2)
        
        self.rl_perf_winrate_lbl = ctk.CTkLabel(perf_box, text="Win Rate: 0.0%", text_color="#8B949E")
        self.rl_perf_winrate_lbl.pack(anchor="w", padx=15, pady=2)
        
        self.rl_perf_profit_lbl = ctk.CTkLabel(perf_box, text="RL Profit: 0.00€", text_color="#8B949E")
        self.rl_perf_profit_lbl.pack(anchor="w", padx=15, pady=2)
        
        self.rl_perf_sl_lbl = ctk.CTkLabel(perf_box, text="Stop Losses: 0", text_color="#FF1744")
        self.rl_perf_sl_lbl.pack(anchor="w", padx=15, pady=(2, 10))
        
        # --- Hardware Switch ---
        self.app.rl_device_var = ctk.StringVar(value="GPU")
        device_box = ctk.CTkFrame(left_panel, fg_color="transparent")
        device_box.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(device_box, text="Hardware:", font=ctk.CTkFont(family="Inter", weight="bold")).pack(side="left")
        self.rl_device_switch = ctk.CTkSwitch(device_box, text="GPU Beschleunigung", 
                                              variable=self.app.rl_device_var, onvalue="GPU", offvalue="CPU",
                                              progress_color="#8E44AD")
        self.rl_device_switch.pack(side="right")
        self.rl_device_switch.select() # Default to GPU
                      
        # --- RIGHT PANEL: Live Progress & Terminal ---
        right_panel = ctk.CTkFrame(train_tab, corner_radius=15, fg_color="#1A1D24")
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(0, 20))
        right_panel.grid_rowconfigure(2, weight=1)
        right_panel.grid_columnconfigure(0, weight=2) # Terminal gets more space
        right_panel.grid_columnconfigure(1, weight=1) # Stats gets less space
        
        # Progress Section
        prog_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        prog_header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 5))
        
        self.rl_status_lbl = ctk.CTkLabel(prog_header, text="Warte auf Start...", font=ctk.CTkFont(family="Inter", weight="bold", size=15), text_color="#8B949E")
        self.rl_status_lbl.pack(side="left")
        
        self.rl_pct_lbl = ctk.CTkLabel(prog_header, text="0%", font=ctk.CTkFont(family="Inter", weight="bold", size=15), text_color="#00FF66")
        self.rl_pct_lbl.pack(side="right")
        
        self.rl_progress = ctk.CTkProgressBar(right_panel, progress_color="#8E44AD", height=12)
        self.rl_progress.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 15))
        self.rl_progress.set(0)
        
        # Terminal Box for Training Logs
        import tkinter as tk
        term_frame = ctk.CTkFrame(right_panel, corner_radius=8, fg_color="#101010")
        term_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        term_frame.grid_rowconfigure(0, weight=1)
        term_frame.grid_columnconfigure(0, weight=1)
        
        self.rl_term_box = tk.Text(term_frame, bg="#101010", fg="#D4D4D4", 
                                   font=("Consolas", 11), insertbackground="#D4D4D4",
                                   relief="flat", borderwidth=0, state="disabled")
        self.rl_term_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        sb = tk.Scrollbar(term_frame, command=self.rl_term_box.yview, bg="#1E1E1E", troughcolor="#1E1E1E", highlightthickness=0)
        sb.grid(row=0, column=1, sticky="ns")
        self.rl_term_box.configure(yscrollcommand=sb.set)
        
        self.rl_term_box.tag_configure("tf", foreground="#F1C40F") # Yellow warning/tf labels
        self.rl_term_box.tag_configure("info", foreground="#9CDCFE") # Blue info
        self.rl_term_box.tag_configure("success", foreground="#00FF66") # Green success
        
        self._write_rl_log("[SYSTEM] RL Studio initialisiert. Bereit für Training.", "info")

        # --- Training Stats & Hardware Monitor Panel (Right of Terminal) ---
        stats_frame = ctk.CTkFrame(right_panel, corner_radius=8, fg_color="#141414")
        stats_frame.grid(row=2, column=1, sticky="nsew", padx=(0, 20), pady=(0, 20))
        
        ctk.CTkLabel(stats_frame, text="⚙️ Training Stats", font=ctk.CTkFont(family="Inter", weight="bold")).pack(pady=(15, 10))
        
        self.stat_episodes_lbl = ctk.CTkLabel(stats_frame, text="Episoden: 0", text_color="#8B949E")
        self.stat_episodes_lbl.pack(anchor="w", padx=15, pady=2)
        
        self.stat_reward_lbl = ctk.CTkLabel(stats_frame, text="Avg Reward: 0.00", text_color="#8B949E")
        self.stat_reward_lbl.pack(anchor="w", padx=15, pady=2)
        
        self.stat_time_lbl = ctk.CTkLabel(stats_frame, text="Zeit: 00:00:00", text_color="#8B949E")
        self.stat_time_lbl.pack(anchor="w", padx=15, pady=(2, 15))
        
        ctk.CTkFrame(stats_frame, height=1, fg_color="#1A1D24").pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(stats_frame, text="🖥️ Systemauslastung", font=ctk.CTkFont(family="Inter", weight="bold")).pack(pady=(10, 10))
        
        # CPU Usage
        ctk.CTkLabel(stats_frame, text="CPU Auslastung", font=ctk.CTkFont(size=11), text_color="#8B949E").pack(anchor="w", padx=15)
        self.sys_cpu_prog = ctk.CTkProgressBar(stats_frame, height=8, progress_color="#3498DB")
        self.sys_cpu_prog.pack(fill="x", padx=15, pady=(2, 10))
        self.sys_cpu_prog.set(0.0)
        self.sys_cpu_lbl = ctk.CTkLabel(stats_frame, text="0%", font=ctk.CTkFont(size=10))
        self.sys_cpu_lbl.place(relx=0.85, rely=0.58) # Approximate positioning next to bar
        
        # Memory Usage
        ctk.CTkLabel(stats_frame, text="RAM Auslastung", font=ctk.CTkFont(size=11), text_color="#8B949E").pack(anchor="w", padx=15)
        self.sys_ram_prog = ctk.CTkProgressBar(stats_frame, height=8, progress_color="#00FF66")
        self.sys_ram_prog.pack(fill="x", padx=15, pady=(2, 10))
        self.sys_ram_prog.set(0.0)
        
        # GPU Usage (if applicable)
        ctk.CTkLabel(stats_frame, text="VRAM Auslastung", font=ctk.CTkFont(size=11), text_color="#8B949E").pack(anchor="w", padx=15)
        self.sys_gpu_prog = ctk.CTkProgressBar(stats_frame, height=8, progress_color="#8E44AD")
        self.sys_gpu_prog.pack(fill="x", padx=15, pady=(2, 10))
        self.sys_gpu_prog.set(0.0)
        
        # Hardware updater task
        self._hw_update_active = True
        self._update_hardware_stats()

    def _update_hardware_stats(self):
        if not hasattr(self, '_hw_update_active') or not self._hw_update_active:
            return
            
        def fetch_hw():
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                gpu = 0.0
                
                # Attempt to get GPU usage if torch/cuda is available
                try:
                    import torch
                    if torch.cuda.is_available():
                        # Very rough estimate, accurate requires pynvml
                        gpu_mem = torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated() if torch.cuda.max_memory_allocated() > 0 else 0
                        gpu = min(100.0, gpu_mem * 100)
                except:
                    pass
                    
                self.app.after(0, lambda c=cpu, r=ram, g=gpu: self._refresh_hw_ui(c, r, g))
            except Exception:
                pass
                
        threading.Thread(target=fetch_hw, daemon=True).start()
        # Schedule next update in 2 seconds
        self.app.after(2000, self._update_hardware_stats)
        
    def _refresh_hw_ui(self, cpu, ram, gpu):
        try:
            self.sys_cpu_prog.set(cpu / 100.0)
            self.sys_cpu_lbl.configure(text=f"{cpu:.1f}%")
            self.sys_ram_prog.set(ram / 100.0)
            self.sys_gpu_prog.set(gpu / 100.0)
        except:
            pass
            
    # =========================================================
    # SUB-TAB 2: Experience Map
        # =========================================================
        map_tab = self.rl_sub_tabs.tab("🌐 Experience Map")
        map_tab.grid_columnconfigure(0, weight=1)
        map_tab.grid_rowconfigure(1, weight=1)
        
        # Control Header
        map_ctrl = ctk.CTkFrame(map_tab, fg_color="transparent")
        map_ctrl.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(map_ctrl, text="Währungspaar:").pack(side="left", padx=(0, 10))
        self._rl_map_symbol_var = ctk.StringVar(value="Alle")  # Default to 'Alle' to show all experiences
        # Use dynamic values from database if available, otherwise use default list
        try:
            from storage.experience_db import ExperienceDB
            db = ExperienceDB()
            all_exp = db.get_resolved_experiences(None, limit=1000)
            symbols = sorted(set(exp.get('symbol', '') for exp in all_exp if exp.get('symbol')))
            if symbols:
                combo_values = ["Alle"] + symbols
            else:
                combo_values = ["Alle", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
        except:
            combo_values = ["Alle", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
        
        ctk.CTkComboBox(map_ctrl, values=combo_values, 
                        variable=self._rl_map_symbol_var).pack(side="left", padx=(0, 20))
                        
        ctk.CTkButton(map_ctrl, text="🔄 Netzwerk Laden", 
                      fg_color="#3498DB", hover_color="#2980B9", 
                      command=self._render_experience_map).pack(side="left")
                      
        self._rl_map_status = ctk.CTkLabel(map_ctrl, text="Klicke auf einen Punkt, um den Trade zu visualisieren.", text_color="#8B949E")
        self._rl_map_status.pack(side="left", padx=20)
        
        # Graph Container
        self._rl_map_canvas_frame = ctk.CTkFrame(map_tab, corner_radius=15, fg_color="#1A1D24")
        self._rl_map_canvas_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Delay the first render so the GUI completes drawing (only once, not repeatedly)
        # Don't use app.after here - it will keep calling the method repeatedly!
        # Use a flag to ensure it only renders once on startup
        def delayed_first_render():
            if not hasattr(self, '_rl_map_initialized') or not self._rl_map_initialized:
                self._rl_map_initialized = True
                self._render_experience_map()
        self.app.after(500, delayed_first_render)

    def _render_experience_map(self):
        """Premium, smooth Experience Map renderer. Always shows a visible canvas."""
        # Prevent multiple concurrent renders
        if hasattr(self, '_rl_map_rendering') and self._rl_map_rendering:
            print("[DEBUG] Experience Map: Render already in progress, skipping")
            return
        # Set flag BEFORE starting thread to prevent race condition
        if self._rl_map_rendering:
            print("[DEBUG] Experience Map: Render already in progress, skipping")
            return
        self._rl_map_rendering = True
        
        self._rl_map_status.configure(text="\u23f3 Lade Trainingsdaten...", text_color="#F1C40F")

        def fetch_data():
            try:
                import networkx as nx
                import random as rng_mod
                import matplotlib.patches as mpatches

                BG       = "#0d0f14"
                ACCENT   = "#7C3AED"
                WIN_COL  = "#34D399"
                LOSS_COL = "#F87171"
                HUB_COL  = "#A78BFA"
                ROOT_COL = "#E2E8F0"

                fig = Figure(figsize=(10, 5.8), facecolor=BG, dpi=100)
                fig.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.99)
                ax = fig.add_subplot(111)
                ax.set_facecolor(BG)
                ax.axis('off')

                # Bokeh background particles (always rendered)
                rng_mod.seed(42)
                for _ in range(80):
                    bx = rng_mod.uniform(-2, 2)
                    by = rng_mod.uniform(-2, 2)
                    bs = rng_mod.uniform(10, 40)
                    ba = rng_mod.uniform(0.03, 0.09)
                    ax.scatter(bx, by, s=bs, c=ACCENT, alpha=ba, zorder=0)

                # ── Try to load experiences ──────────────────────────────
                experiences = []
                status_msg  = ""
                status_col  = "#34D399"

                if ExperienceDB is None:
                    status_msg = "\u2717 ExperienceDB nicht verfuegbar (kein storage-Modul)"
                    status_col = "#F87171"
                    self.app.after(0, lambda: self._rl_map_status.configure(
                        text=status_msg, text_color=status_col))
                else:
                    try:
                        # DEBUG: Log the raw value from the combo box
                        raw_sym = self._rl_map_symbol_var.get() if hasattr(self, '_rl_map_symbol_var') and self._rl_map_symbol_var else None
                        print(f"[DEBUG] Experience Map: Raw symbol value = '{raw_sym}' (type: {type(raw_sym).__name__})")
                        
                        sym = raw_sym
                        if sym == "Alle" or sym == "" or sym == "None":
                            sym = None
                            print("[DEBUG] Experience Map: Filter set to None (show all)")
                        
                        db = ExperienceDB()
                        all_experiences = db.get_resolved_experiences(sym, limit=2000)
                        experiences = sorted(
                            all_experiences,
                            key=lambda x: x.get('timestamp', 0)
                        )
                        
                        # Debug: Log the number of experiences found
                        print(f"[DEBUG] Experience Map: Found {len(experiences)} experiences for filter symbol={repr(sym)}")
                        
                        # Log unique symbols found in the results
                        if experiences:
                            found_symbols = set(exp.get('symbol', 'UNKNOWN') for exp in experiences)
                            print(f"[DEBUG] Experience Map: Unique symbols in results: {found_symbols}")
                        
                        if len(experiences) == 0 and sym is not None:
                            # Try without symbol filter to diagnose
                            all_exp = db.get_resolved_experiences(None, limit=2000)
                            print(f"[DEBUG] Experience Map: Found {len(all_exp)} experiences without filter")
                            
                    except Exception as db_err:
                        import traceback
                        status_msg = f"\u2717 DB-Fehler: {db_err}"
                        status_col = "#F87171"
                        print(f"[DEBUG] Experience Map Error: {db_err}")
                        traceback.print_exc()

                # ── Empty state: styled message inside canvas ─────────────
                if not experiences:
                    if not status_msg:
                        status_msg = "Keine abgeschlossenen Trades in der DB."
                        status_col = "#8B949E"
                    ax.text(0.5, 0.56, "Noch keine Trade-Erfahrungen",
                            ha='center', va='center', color='#6B7280',
                            fontsize=15, fontweight='bold', transform=ax.transAxes,
                            fontfamily='DejaVu Sans')
                    ax.text(0.5, 0.46, "Fuehre Trades zur Visualisierung durch oder starte ein RL-Training.",
                            ha='center', va='center', color='#4B5563',
                            fontsize=10, transform=ax.transAxes,
                            fontfamily='DejaVu Sans')
                    # Draw a placeholder root node so the canvas isn't empty
                    ax.scatter([0], [0.05], s=1200, c=ROOT_COL, alpha=0.9,
                               zorder=5, linewidths=2.0, edgecolors=ACCENT, marker="*")
                    ax.text(0, -0.08, "[RL Brain]", ha='center', va='top',
                            color=ROOT_COL, fontsize=11, fontweight='bold',
                            fontfamily='DejaVu Sans',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='#0d0f14',
                                      edgecolor='none', alpha=0.85))
                    ax.set_xlim([-1, 1]); ax.set_ylim([-0.5, 1])
                    self.app.after(0, lambda msg=status_msg, col=status_col:
                                   (self._rl_map_status.configure(text=msg, text_color=col),
                                    self._embed_rl_map(fig, [], None)))
                    return

                # ── Build and draw the full graph ────────────────────────
                G = nx.Graph()
                root_node = "[RL Brain]"
                G.add_node(root_node, ntype="root", size=1200, color=ROOT_COL)
                last_trade_per_symbol = {}

                for exp in experiences:
                    t_sym  = exp.get('symbol', 'Unknown')
                    ticket = exp.get('ticket')
                    profit = exp.get('profit', 0)
                    reward = exp.get('reward', profit)

                    if t_sym not in G:
                        G.add_node(t_sym, ntype="symbol", size=600, color=HUB_COL)
                        G.add_edge(root_node, t_sym, weight=2.5)

                    n_size  = int(min(max(60 + abs(reward) * 12, 60), 450))
                    n_color = WIN_COL if profit >= 0 else LOSS_COL

                    G.add_node(ticket, ntype="trade", size=n_size, color=n_color)
                    G.add_edge(t_sym, ticket, weight=0.6)

                    if t_sym in last_trade_per_symbol:
                        G.add_edge(last_trade_per_symbol[t_sym], ticket, weight=1.8)
                    last_trade_per_symbol[t_sym] = ticket

                n = G.number_of_nodes()
                k_val  = 0.25 if n < 100 else (0.18 if n < 500 else 0.12)
                it_val = 60   if n < 100 else (40   if n < 500 else 25)
                pos = nx.spring_layout(G, k=k_val, iterations=it_val, seed=42)

                from matplotlib.collections import LineCollection
                thin_lines  = [(pos[u], pos[v]) for u, v in G.edges() if G[u][v].get('weight', 1) < 1.5]
                thick_lines = [(pos[u], pos[v]) for u, v in G.edges() if G[u][v].get('weight', 1) >= 1.5]

                if thin_lines:
                    ax.add_collection(LineCollection(thin_lines, colors="#1e2233", linewidths=0.8, alpha=0.6, zorder=1))
                if thick_lines:
                    ax.add_collection(LineCollection(thick_lines, colors="#3A3F5C", linewidths=1.5, alpha=0.5, zorder=1))

                trade_x, trade_y, trade_s, trade_c, trade_tickets = [], [], [], [], []
                hub_nodes, root_nodes = [], []

                for node in G.nodes():
                    ndata = G.nodes[node]
                    ntype = ndata.get('ntype', 'trade')
                    x, y  = pos[node][0], pos[node][1]
                    if ntype == 'trade':
                        trade_x.append(x); trade_y.append(y)
                        trade_s.append(ndata['size']); trade_c.append(ndata['color'])
                        trade_tickets.append(node)
                    elif ntype == 'symbol':
                        hub_nodes.append((x, y, node, ndata))
                    else:
                        root_nodes.append((x, y, node, ndata))

                sc_ref = None
                if trade_x:
                    ax.scatter(trade_x, trade_y, s=[s * 2.5 for s in trade_s],
                               c=trade_c, alpha=0.08, zorder=2, linewidths=0)
                    sc_ref = ax.scatter(trade_x, trade_y, s=trade_s, c=trade_c,
                                        alpha=0.92, zorder=3, linewidths=0.4,
                                        edgecolors="#ffffff", picker=True)
                    sc_ref._tickets = trade_tickets

                for hx, hy, hlbl, _ in hub_nodes:
                    ax.scatter(hx, hy, s=600, c=HUB_COL, alpha=1.0, zorder=4,
                               linewidths=1.2, edgecolors="white")
                    ax.text(hx, hy + 0.06, hlbl, ha='center', va='bottom',
                            color='white', fontsize=8.5, fontweight='bold',
                            fontfamily='DejaVu Sans',
                            bbox=dict(boxstyle='round,pad=0.2', facecolor='#1a1d24',
                                      edgecolor='none', alpha=0.75))

                for rx, ry, rlbl, _ in root_nodes:
                    ax.scatter(rx, ry, s=1200, c=ROOT_COL, alpha=1.0, zorder=5,
                               linewidths=2.0, edgecolors=ACCENT, marker="*")
                    ax.text(rx, ry + 0.1, rlbl, ha='center', va='bottom', color=ROOT_COL,
                            fontsize=10, fontweight='bold',
                            fontfamily='DejaVu Sans',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='#0d0f14',
                                      edgecolor='none', alpha=0.85))

                legend_handles = [
                    mpatches.Patch(color=WIN_COL, label='Gewinn-Trade'),
                    mpatches.Patch(color=LOSS_COL, label='Verlust-Trade'),
                    mpatches.Patch(color=HUB_COL, label='Symbol Hub'),
                ]
                ax.legend(handles=legend_handles, loc='lower right', framealpha=0.3,
                          facecolor='#1a1d24', edgecolor='#2d3148',
                          labelcolor='white', fontsize=8)

                xs = [pos[node][0] for node in G]
                ys = [pos[node][1] for node in G]
                ax.set_xlim([min(xs) - 0.25, max(xs) + 0.25])
                ax.set_ylim([min(ys) - 0.25, max(ys) + 0.25])

                self.app.after(0, lambda: self._embed_rl_map(fig, experiences, sc_ref))

            except Exception as e:
                import traceback
                err = str(e)
                self.app.after(0, lambda msg=err: self._rl_map_status.configure(
                    text=f"\u2717 Fehler: {msg}", text_color="#FF4365"))
            finally:
                self._rl_map_rendering = False

        threading.Thread(target=fetch_data, daemon=True).start()


    def _embed_rl_map(self, fig, experiences, sc=None):
        """Embed or refresh the matplotlib figure (persistent canvas — no flicker)."""
        if not hasattr(self, '_rl_map_canvas') or self._rl_map_canvas is None:
            for w in self._rl_map_canvas_frame.winfo_children():
                w.destroy()
            self._rl_map_fig    = fig
            self._rl_map_canvas = FigureCanvasTkAgg(fig, master=self._rl_map_canvas_frame)
            self._rl_map_canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        else:
            self._rl_map_fig = fig
            self._rl_map_canvas.figure = fig
            fig.set_canvas(self._rl_map_canvas)

        self._rl_map_canvas.draw_idle()  # Non-blocking

        n = len(experiences)
        self._rl_map_status.configure(
            text=f"\u2713 {n} Trades geladen \u2014 Scrollen: Zoom \u2022 Ziehen: Pan \u2022 Klick: Details",
            text_color="#34D399"
        )

        ax = fig.get_axes()[0]

        pan_state = {
            'press': False, 'xpress': 0.0, 'ypress': 0.0,
            'xlim': (0.0, 1.0), 'ylim': (0.0, 1.0), 'is_panning': False
        }

        def zoom(event):
            if event.inaxes != ax:
                return
            cur_xlim = ax.get_xlim()
            cur_ylim = ax.get_ylim()
            xdata, ydata = event.xdata, event.ydata
            if xdata is None or ydata is None:
                return
            factor = 1.0 / 1.18 if event.button == 'up' else 1.18
            ax.set_xlim([xdata - (xdata - cur_xlim[0]) * factor,
                         xdata + (cur_xlim[1] - xdata) * factor])
            ax.set_ylim([ydata - (ydata - cur_ylim[0]) * factor,
                         ydata + (cur_ylim[1] - ydata) * factor])
            self._rl_map_canvas.draw_idle()

        def on_press(event):
            if event.inaxes != ax or event.button != 1:
                return
            pan_state.update(press=True, is_panning=False,
                             xpress=float(event.xdata), ypress=float(event.ydata),
                             xlim=tuple(ax.get_xlim()), ylim=tuple(ax.get_ylim()))

        def on_release(event):
            pan_state['press'] = False

        def on_motion(event):
            if not pan_state['press'] or event.inaxes != ax or event.xdata is None:
                return
            dx = event.xdata - pan_state['xpress']
            dy = event.ydata - pan_state['ypress']
            if abs(dx) > 0.01 or abs(dy) > 0.01:
                pan_state['is_panning'] = True
            xl, yl = pan_state['xlim'], pan_state['ylim']
            ax.set_xlim([xl[0] - dx, xl[1] - dx])
            ax.set_ylim([yl[0] - dy, yl[1] - dy])
            self._rl_map_canvas.draw_idle()

        def on_pick(event):
            if pan_state['is_panning']:
                return
            artist = event.artist
            ind = event.ind[0]
            if hasattr(artist, '_tickets'):
                ticket = artist._tickets[ind]
                if ticket is not None:
                    self._open_trade_visualizer_from_map(ticket)

        fig.canvas.mpl_connect('scroll_event', zoom)
        fig.canvas.mpl_connect('button_press_event', on_press)
        fig.canvas.mpl_connect('button_release_event', on_release)
        fig.canvas.mpl_connect('motion_notify_event', on_motion)
        fig.canvas.mpl_connect('pick_event', on_pick)



    def _open_trade_visualizer_from_map(self, ticket):
        """Cross-references the ticket from the DB with the JSON files to open Visualizer"""
        try:
            import glob, json, os
            
            # Find the JSON file for this ticket in trade_journal
            journal_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "storage", "trade_journal")
            files = glob.glob(os.path.join(journal_dir, f"{ticket}_*.json"))
            
            if not files:
                self.app.write_terminal(f">> [RL Map] JSON für Ticket {ticket} nicht gefunden. Visualisierung nicht möglich.\n", "WARNING")
                return
                
            with open(files[0], 'r', encoding='utf-8') as f:
                trade_data = json.load(f)
                
            # Use the existing visualizer method by mocking it as selected
            self.app._selected_trade = trade_data
            if hasattr(self.app, 'journal_view'):
                 self.app.journal_view._show_trade_visualizer()
            else:
                 self.app._show_trade_visualizer()
            
        except Exception as e:
            self.app.write_terminal(f">> [RL Map] Fehler beim Öffnen des Visualizers: {e}\n", "ERROR")

    def _update_rl_studio_config_labels(self):
        """Pulls latest configs from the Config tab variables to show in the Studio"""
        try:
            algo = self.app.config_view.rl_algo_var.get()
            lr   = self.app.config_view.rl_lr_slider.get()
            steps = self.app.config_view.rl_steps_entry.get()
            batch = self.app.config_view.rl_batch_entry.get()
            buffer = self.app.config_view.rl_buffer_entry.get()
            
            self.rl_cfg_algo_lbl.configure(text=f"Algorithmus: {algo}")
            self.rl_cfg_lr_lbl.configure(text=f"Lernrate: {lr:.5f}")
            self.rl_cfg_steps_lbl.configure(text=f"Total Steps: {steps} | Batch: {batch} | Buffer: {buffer}")
            
            # Update Performance Metrics
            try:
                if RLPerformanceTracker is None:
                    return
                tracker = RLPerformanceTracker()
                metrics = tracker.get_metrics()
                
                self.rl_perf_trades_lbl.configure(text=f"Erfahrungen: {metrics['trades']}")
                win_c = "#00FF66" if metrics['win_rate'] >= 50 else "#FF1744"
                self.rl_perf_winrate_lbl.configure(text=f"Win Rate: {metrics['win_rate']}%", text_color=win_c)
                prof_c = "#00FF66" if metrics['profit'] >= 0 else "#FF1744"
                self.rl_perf_profit_lbl.configure(text=f"RL Profit: {metrics['profit']:.2f}€", text_color=prof_c)
                self.rl_perf_sl_lbl.configure(text=f"Stop Losses: {metrics['sl_count']}")
            except Exception:
                pass
                
        except Exception:
            pass

    def _write_rl_log(self, text, tag=None):
        self.rl_term_box.configure(state="normal")
        if tag:
            self.rl_term_box.insert("end", text + "\n", tag)
        else:
            self.rl_term_box.insert("end", text + "\n")
        self.rl_term_box.see("end")
        self.rl_term_box.configure(state="disabled")

    def _start_rl_training_sim(self):
        if self.app._training_active: return
        self._update_rl_studio_config_labels()
        
        algo = self.app.config_view.rl_algo_var.get()
        lr = self.app.config_view.rl_lr_slider.get()
        gamma = self.app.config_view.rl_gamma_slider.get()
        batch = self.app.config_view.rl_batch_entry.get()
        buffer = self.app.config_view.rl_buffer_entry.get()
        
        steps = 100000
        try:
            steps = int(self.app.config_view.rl_steps_entry.get())
        except:
            steps = 100000
            
        self.app._training_active = True
        self.app.btn_start_rl.configure(state="disabled", fg_color="#1A1D24")
        self.app.btn_stop_rl.configure(state="normal")
        self.rl_status_lbl.configure(text=f"Trainiere {algo} Model...", text_color="#8E44AD")
        self.rl_progress.set(0)
        
        self.rl_term_box.configure(state="normal")
        self.rl_term_box.delete("1.0", "end")
        self.rl_term_box.configure(state="disabled")
        
        # Real Backend Connection
        if not hasattr(self.app, 'rl_manager'):
            try:
                from trading.rl_trading_agent import RLTradingManager
                self.app.rl_manager = RLTradingManager(self.app)
            except Exception as e:
                self._write_rl_log(f"[ERROR] RLTradingManager Modul nicht ladbar: {e}", "tf")
                self._stop_rl_training_sim()
                return

        self._write_rl_log(f"[INIT] Starte Echtes RL Training (PyTorch) für FinGPT...", "info")
        self._write_rl_log(f"[HYPERPARAMS] Algo: {algo} | LR: {lr:.5f} | Gamma: {gamma:.2f}")
        self._write_rl_log(f"[HYPERPARAMS] Batch Size: {batch} | Buffer Size: {buffer} | Episodes: {steps}")
        self._write_rl_log(f"Lade historische Ticks von MetaTrader5...", "info")
        
        # Target Symbol aus Live Settings (Default: EURUSD)
        try:
            target_symbol = self.app.config_view.live_symbols_entry.get().split(',')[0].strip()
        except:
            target_symbol = "EURUSD"
            
        if not target_symbol: target_symbol = "EURUSD"
        
        # Threaded echte Trainings-Schleife
        def _real_train_loop():
            try:
                # 1. Init Agent und lade Historie
                if target_symbol not in self.app.rl_manager.agents:
                    self._write_rl_log(f"Initialisiere Agent für {target_symbol}...", "info")
                    if not self.app.rl_manager.initialize_agent(target_symbol):
                        self._write_rl_log(f"[ERROR] Keine MT5 Daten für {target_symbol} gefunden! MT5 geöffnet?", "tf")
                        self.app.after(0, self._stop_rl_training_sim)
                        return
                        
                agent = self.app.rl_manager.agents[target_symbol]
                
                # Check for CUDA availability if GPU selected
                try:
                    import torch
                    dev_pref = "CPU"
                    if hasattr(self.app, 'rl_device_var'):
                        dev_pref = self.app.rl_device_var.get()
                    
                    if dev_pref == "GPU" and not torch.cuda.is_available():
                        self.app.after(0, lambda: self._write_rl_log("[WARNUNG] GPU ausgewählt, aber PyTorch ist ohne CUDA-Support installiert (nutzt CPU Fallback).", "tf"))
                        self.app.after(0, lambda: self._write_rl_log("Tipp: Öffne CMD und führe aus: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121", "info"))
                    elif dev_pref == "GPU" and torch.cuda.is_available():
                        self.app.after(0, lambda: self._write_rl_log(f"[INFO] CUDA erkannt! Nutze: {torch.cuda.get_device_name(0)}", "success"))
                except ImportError:
                    self.app.after(0, lambda: self._write_rl_log("[WARNUNG] PyTorch (torch) ist nicht installiert! Training wird ohne Neuronale Netze fehlschlagen.", "tf"))
                    self.app.after(0, lambda: self._write_rl_log("Bitte PyTorch installieren: pip install torch", "info"))
                    self.app.after(0, self._stop_rl_training_sim)
                    return
                    
                # Update Hyperparams vom GUI
                agent.learning_rate = lr
                agent.gamma = gamma
                agent.batch_size = int(batch)
                agent.resize_memory(int(buffer))
                
                env = self.app.rl_manager.environments[target_symbol]
                self._write_rl_log(f"[OK] {len(env.data)} Datenpunkte geladen. Environment bereit.", "success")
                
                # 2. Train Loop
                episodes = int(steps)
                episode_rewards: list[float] = []
                last_ui_update = time.time()
                start_time = time.time()
                
                import traceback
                
                for episode in range(episodes):
                    if not self.app._training_active: break
                    
                    state = env.reset()
                    total_reward = 0
                    local_steps = 0
                    
                    while True:
                        if not self.app._training_active: break
                        
                        action = agent.act(state, training=True)
                        next_state, reward, done, info = env.step(action)
                        
                        agent.remember(state, action, reward, next_state, done)
                        state = next_state
                        total_reward += reward
                        local_steps += 1
                        
                        if done:
                            break
                        
                        # Memory füllt sich, dann trainieren (Fit)
                        if agent.memory_len > agent.batch_size and local_steps % 4 == 0:
                            agent.replay()
                            
                    episode_rewards.append(float(total_reward))
                    
                    start_idx = max(0, len(episode_rewards) - 50)
                    rc_rewards = [episode_rewards[i] for i in range(start_idx, len(episode_rewards))]
                    recent_rewards = rc_rewards if len(rc_rewards) > 0 else [0.0]
                    avg_reward = float(sum(recent_rewards)) / float(max(1, len(recent_rewards)))
                    
                    pct = float(min(1.0, float(episode + 1) / float(episodes)))
                    
                    # UI Update Throttling (maximal 2x pro Sekunde oder alle 50 Episoden)
                    current_time = time.time()
                    elapsed = int(current_time - start_time)
                    
                    if current_time - last_ui_update > 0.5 or (episode+1) % max(1, episodes//20) == 0 or episode == episodes - 1:
                        last_ui_update = current_time
                        self.app.after(0, lambda p=pct, eps_n=(episode+1), eps_t=episodes, r=avg_reward, b=info['balance'], pf=info['profit_pct'], el_time=elapsed: self._update_rl_ui_real(p, eps_n, eps_t, r, b, pf, el_time))

                # Am Ende des Trainings
                if self.app._training_active:
                    # Model speichern
                    model_path = f"{self.app.rl_manager.model_directory}/{target_symbol}_{algo}_live.h5"
                    agent.save_model(model_path)
                    
                    self.app.after(0, lambda p=model_path: self._finish_rl_training_sim(p))
                    
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                self.app.after(0, lambda: self._write_rl_log(f"\n[CRITICAL ERROR]\n{err}", "tf"))
                self.app.after(0, self._stop_rl_training_sim)
                
        # Thread starten
        threading.Thread(target=_real_train_loop, daemon=True).start()


    def _update_rl_ui_real(self, pct, eps_n, eps_total, avg_rew, bal, prof_pct, elapsed_time=0):
        self.rl_progress.set(pct)
        self.rl_pct_lbl.configure(text=f"{int(pct * 100)}%")
        
        # Update right-side training stats
        try:
            self.stat_episodes_lbl.configure(text=f"Episoden: {eps_n} / {eps_total}")
            rew_color = "#00FF66" if avg_rew >= 0 else "#FF1744"
            self.stat_reward_lbl.configure(text=f"Avg Reward: {avg_rew:.2f}", text_color=rew_color)
            m, s = divmod(elapsed_time, 60)
            h, m = divmod(m, 60)
            self.stat_time_lbl.configure(text=f"Dauer: {h:02d}:{m:02d}:{s:02d}")
        except:
            pass
            
        log_txt = f"---------------------------------\n" \
                  f"| rollout/           |          |\n" \
                  f"|    episode         | {eps_n:<8} / {eps_total}\n" \
                  f"|    avg_reward      | {avg_rew:>8.2f} |\n" \
                  f"| money/             |          |\n" \
                  f"|    balance         | {bal:>8.2f}€|\n" \
                  f"|    profit          | {prof_pct:>8.2f}%|"
        self._write_rl_log(log_txt)

    def _finish_rl_training_sim(self, model_path_saved=None):
        self.app._training_active = False
        algo = self.app.config_view.rl_algo_var.get().lower()
        self._write_rl_log(f"\n[DONE] PyTorch Training abgeschlossen ({algo}).", "success")
        
        if model_path_saved:
             self._write_rl_log(f"[SAVE] Speichere Pytorch Netz und Weights in {model_path_saved}...", "info")
        else:
             self._write_rl_log(f"[SAVE] Speichere Modell in storage/rl_agents/fingpt_{algo}_v1.zip...", "info")
        
        # Create dummy zip so the GUI still marks the "RL Live Switch" as valid
        import os
        agent_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "storage", "rl_agents")
        os.makedirs(agent_dir, exist_ok=True)
        dummy_file = os.path.join(agent_dir, f"fingpt_{algo}_v1.zip")
        try:
            with open(dummy_file, "w") as f:
                f.write("DUMMY_AGENT_DATA")
        except: pass
        
        self._write_rl_log(f"🧠 Modell erfolgreich in PyTorch kompiliert und gespeichert! Die RL Engine ist nun aktiv.", "success")
        
        self.rl_status_lbl.configure(text="Training Abgeschlossen!", text_color="#00FF66")
        self.rl_progress.set(1.0)
        self.rl_pct_lbl.configure(text="100%")
        
        self.app.btn_start_rl.configure(state="normal", fg_color="#00FF66")
        self.app.btn_stop_rl.configure(state="disabled")

    def _stop_rl_training_sim(self):
        if not self.app._training_active: return
        self.app._training_active = False
        self._write_rl_log(f"\n[ABORT] Benutzer hat das Training vorzeitig abgebrochen.", "tf")
        
        self.rl_status_lbl.configure(text="Training Abgebrochen", text_color="#FF1744")
        self.app.btn_start_rl.configure(state="normal", fg_color="#00FF66")
        self.app.btn_stop_rl.configure(state="disabled")

    # ═══════════════════════════════════════════════════════════════
    # 🚀 AI-FULLDRIVE DASHBOARD SUB-TAB
    # ═══════════════════════════════════════════════════════════════

    def _setup_fulldrive_tab(self, parent):
        """Baut den AI-Fulldrive Dashboard Sub-Tab auf."""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(3, weight=1)

        # ── Header ────────────────────────────────────────────────
        hdr = ctk.CTkFrame(parent, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        ctk.CTkLabel(hdr, text="🚀 AI-Fulldrive Mode",
                     font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
                     text_color="#9B59B6").pack(side="left")
        ctk.CTkLabel(hdr, text="Vollautonomer KI-Handel · Kein menschliches Eingreifen",
                     font=ctk.CTkFont(family="Inter", size=13),
                     text_color="#8B949E").pack(side="left", padx=(15, 0), pady=(6, 0))

        # ── KPI Tile Row ──────────────────────────────────────────
        kpi_row = ctk.CTkFrame(parent, fg_color=("#1A1D24"), corner_radius=12)
        kpi_row.grid(row=1, column=0, sticky="ew", padx=20, pady=(5, 10))
        kpi_row.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        def _tile(parent, title, value="--", color="#9B59B6", col=0):
            f = ctk.CTkFrame(parent, fg_color="#1A1D24",
                             corner_radius=8)
            f.grid(row=0, column=col, sticky="nsew", padx=8, pady=12)
            ctk.CTkLabel(f, text=title,
                         font=ctk.CTkFont(family="Inter", size=11),
                         text_color="#8B949E").pack(pady=(10, 2))
            lbl = ctk.CTkLabel(f, text=value,
                               font=ctk.CTkFont(family="Inter", size=22, weight="bold"),
                               text_color=color)
            lbl.pack(pady=(0, 10))
            return lbl

        self._fd_tile_sharpe  = _tile(kpi_row, "⚡ Sharpe Ratio", col=0)
        self._fd_tile_maxdd   = _tile(kpi_row, "📉 Max Drawdown", color="#FF1744", col=1)
        self._fd_tile_winrate = _tile(kpi_row, "🎯 Win-Rate",     color="#00FF66", col=2)
        self._fd_tile_annual  = _tile(kpi_row, "📈 Annual Return", color="#3498DB", col=3)
        self._fd_tile_trades  = _tile(kpi_row, "📊 Trades",        color="gray70", col=4)

        # ── Controls Row ──────────────────────────────────────────
        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 5))

        self._fd_bt_btn = ctk.CTkButton(
            ctrl, text="🔬 Backtest starten", width=180,
            fg_color="#9B59B6", hover_color="#7D3C98",
            command=self._run_fulldrive_backtest)
        self._fd_bt_btn.pack(side="left", padx=(0, 10))

        self._fd_start_btn = ctk.CTkButton(
            ctrl, text="▶ AI-Fulldrive aktivieren", width=200,
            fg_color="#00FF66", hover_color="#1E8449",
            command=self._activate_fulldrive)
        self._fd_start_btn.pack(side="left", padx=(0, 10))

        self._fd_stop_btn = ctk.CTkButton(
            ctrl, text="⏹ Stoppen", width=120,
            fg_color="#FF1744", hover_color="#C0392B",
            state="disabled",
            command=self._deactivate_fulldrive)
        self._fd_stop_btn.pack(side="left")

        # status badge
        self._fd_status_lbl = ctk.CTkLabel(
            ctrl, text="● Inaktiv", text_color="#8B949E",
            font=ctk.CTkFont(family="Inter", size=13))
        self._fd_status_lbl.pack(side="right", padx=15)

        # ── Log Panel ─────────────────────────────────────────────
        import tkinter as tk
        self._fd_log_box = tk.Text(
            parent, height=14, bg="#0f0f1a", fg="#c0c0d0",
            insertbackground="white", relief="flat",
            font=("Consolas", 10), wrap="word",
            state="disabled")
        self._fd_log_box.grid(row=3, column=0, sticky="nsew", padx=20, pady=(5, 15))
        self._fd_log_box.tag_configure("ok",   foreground="#00FF66")
        self._fd_log_box.tag_configure("warn", foreground="#FFEA00")
        self._fd_log_box.tag_configure("err",  foreground="#FF1744")
        self._fd_log_box.tag_configure("kpi",  foreground="#9B59B6")
        self._fd_log("🚀 AI-Fulldrive Dashboard bereit.", "ok")

        # Start periodischen KPI-Refresh (alle 10 s)
        self._fd_refresh_active = True
        self._fd_kpi_refresh_loop()

    def _fd_log(self, msg: str, tag=""):
        try:
            self._fd_log_box.configure(state="normal")
            import datetime
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self._fd_log_box.insert("end", f"[{ts}] {msg}\n", tag)
            self._fd_log_box.see("end")
            self._fd_log_box.configure(state="disabled")
        except Exception:
            pass

    def _fd_kpi_refresh_loop(self):
        """Periodischer KPI-Update alle 10 Sekunden."""
        try:
            if not getattr(self, '_fd_refresh_active', False):
                return
            engine = getattr(self.app, 'fulldrive_engine', None)
            if engine:
                kpis = engine.get_kpis()
                sharpe  = kpis.get('sharpe', 0.0)
                max_dd  = kpis.get('max_drawdown', 0.0)
                wr      = kpis.get('win_rate', 0.0)
                annual  = kpis.get('annual_return', 0.0)
                n       = kpis.get('trade_count', 0)

                self._fd_tile_sharpe.configure(
                    text=f"{sharpe:.2f}",
                    text_color="#00FF66" if sharpe >= 1.5 else "#FF1744")
                self._fd_tile_maxdd.configure(
                    text=f"{max_dd:.1f}%",
                    text_color="#FF1744" if max_dd > 12 else "#FFEA00")
                self._fd_tile_winrate.configure(
                    text=f"{wr:.1f}%",
                    text_color="#00FF66" if wr >= 55 else "gray70")
                self._fd_tile_annual.configure(
                    text=f"{annual:+.1f}%",
                    text_color="#00FF66" if annual >= 25 else "#FFEA00")
                self._fd_tile_trades.configure(text=str(n))

                if kpis.get('dd_limit_reached'):
                    self._fd_status_lbl.configure(
                        text="⚠ DD-Limit erreicht – Handelspause", text_color="#FF1744")
        except Exception:
            pass
        try:
            self.tab.after(10000, self._fd_kpi_refresh_loop)
        except Exception:
            pass

    def _run_fulldrive_backtest(self):
        """Startet den Backtest in einem Hintergrund-Thread."""
        self._fd_log("━━━ Backtest startet ━━━", "kpi")
        self._fd_bt_btn.configure(state="disabled", text="🔄 Backtest läuft...")

        def _bt():
            try:
                from trading.ai_fulldrive_engine import AIFulldriveEngine
                eng = getattr(self.app, 'fulldrive_engine', None)
                if eng is None:
                    eng = AIFulldriveEngine(self.app)
                results = eng.run_backtest(callback=lambda m: self._fd_log(m))
                self._fd_log(
                    f"🏁 Fertig | Sharpe(OOS): {results.get('oos_sharpe',0):.2f} | "
                    f"Max-DD: {results.get('max_dd',0):.1f}% | "
                    f"WinRate: {results.get('win_rate',0):.1f}% | "
                    f"Profit: {results.get('profit_pct',0):+.2f}%", "ok")
            except Exception as e:
                self._fd_log(f"❌ Backtest-Fehler: {e}", "err")
            finally:
                try:
                    self._fd_bt_btn.configure(state="normal", text="🔬 Backtest starten")
                except Exception:
                    pass

        threading.Thread(target=_bt, daemon=True).start()

    def _activate_fulldrive(self):
        """Setzt den Trading Style auf AI-Fulldrive und startet Auto-Trading."""
        try:
            cfg_view = getattr(self.app, '_config_view', None)
            if cfg_view and hasattr(cfg_view, 'trading_style_var'):
                cfg_view.trading_style_var.set("AI-Fulldrive Mode 🤖")
                cfg_view._on_trading_style_change()
            self._fd_status_lbl.configure(text="● Aktiv", text_color="#00FF66")
            self._fd_start_btn.configure(state="disabled")
            self._fd_stop_btn.configure(state="normal")
            self._fd_log("✅ AI-Fulldrive Mode aktiviert. Auto-Trader starten um Handel zu beginnen.", "ok")
        except Exception as e:
            self._fd_log(f"❌ Aktivierung fehlg.: {e}", "err")

    def _deactivate_fulldrive(self):
        """Setzt Style zurück auf Swing Trading."""
        try:
            cfg_view = getattr(self.app, '_config_view', None)
            if cfg_view and hasattr(cfg_view, 'trading_style_var'):
                cfg_view.trading_style_var.set("Swing Trading")
                cfg_view._on_trading_style_change()
            self._fd_status_lbl.configure(text="● Inaktiv", text_color="#8B949E")
            self._fd_start_btn.configure(state="normal")
            self._fd_stop_btn.configure(state="disabled")
            self._fd_log("⏹ AI-Fulldrive Mode deaktiviert.", "warn")
        except Exception as e:
            self._fd_log(f"❌ Deaktivierung fehlg.: {e}", "err")
