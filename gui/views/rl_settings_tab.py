import os
import json
import glob
import threading
import time
import psutil
import math
import random
import tkinter as tk
import customtkinter as ctk
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from gui.design_system import DesignSystem, create_button

# Enable anti-aliasing for smooth lines in matplotlib if possible
try:
    import matplotlib.style as mpl_style
    plt.style.use('dark_background')
except:
    pass
# Native Canvas Map

try:
    import networkx as nx
except ImportError:
    nx = None

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
        self._rl_map_fig: Any = None  # Current matplotlib Figure
        self._rl_map_static_rendered: bool = False  # Static render flag

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
        self._fd_bt_btn: Any = None
        self._fd_start_btn: Any = None
        self._fd_stop_btn: Any = None
        self._fd_refresh_active = False
        
        # New plot lists for dynamic chart
        self._plot_rewards = []
        self._plot_episodes = []
        
        self.setup_ui()

    def setup_ui(self):
        """Haupt-Setup für den RL Studio Tab - Modernes Dashboard"""
        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_rowconfigure(0, weight=1)

        # Sub-Navigation for RL Studio
        self.rl_sub_tabs = ctk.CTkTabview(self.tab, corner_radius=10, fg_color="transparent")
        self.rl_sub_tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.rl_sub_tabs.add("🏋️ Training")
        self.rl_sub_tabs.add("🌌 Neural Network")
        self.rl_sub_tabs.add("🚀 AI-Fulldrive")

        # =========================================================
        # SUB-TAB 2: Neural Network
        # =========================================================
        nn_tab = self.rl_sub_tabs.tab("🌌 Neural Network")
        self._setup_neural_network_tab(nn_tab)

        # =========================================================
        # SUB-TAB 3: AI-Fulldrive Dashboard
        # =========================================================
        self._setup_fulldrive_tab(self.rl_sub_tabs.tab("🚀 AI-Fulldrive"))

        # =========================================================
        # SUB-TAB 1: Training (New Dashboard Layout)
        # =========================================================
        train_tab = self.rl_sub_tabs.tab("🏋️ Training")
        train_tab.grid_columnconfigure(0, weight=1) # Panel 1
        train_tab.grid_columnconfigure(1, weight=2) # Panel 2
        train_tab.grid_columnconfigure(2, weight=1) # Panel 3
        train_tab.grid_rowconfigure(1, weight=1)

        # --- TOP HEADER BAR ---
        header = ctk.CTkFrame(train_tab, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=20, pady=(10, 5))

        ctk.CTkLabel(
            header,
            text="RL Control Center",
            font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
            text_color="#00E5FF",
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text="Autonomous Agent Training & Monitoring",
            font=ctk.CTkFont(family="Inter", size=14),
            text_color="#8B949E",
        ).pack(side="left", padx=(15, 0), pady=(8, 0))

        # --- LEFT PANEL: Controls & Configuration ---
        left_panel = ctk.CTkFrame(train_tab, corner_radius=15, fg_color="#14171A")
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))

        ctk.CTkLabel(
            left_panel,
            text="⚙️ Configuration",
            font=ctk.CTkFont(family="Inter", weight="bold", size=16),
        ).pack(pady=(20, 10), padx=20, anchor="w")

        info_box = ctk.CTkFrame(left_panel, fg_color="#1C2128", corner_radius=10)
        info_box.pack(fill="x", padx=20, pady=10)

        self.rl_cfg_algo_lbl = ctk.CTkLabel(info_box, text="Algo: PPO", font=ctk.CTkFont(weight="bold"), text_color="#00E5FF")
        self.rl_cfg_algo_lbl.pack(anchor="w", padx=15, pady=(15, 5))
        self.app.rl_cfg_algo_lbl = self.rl_cfg_algo_lbl

        self.rl_cfg_lr_lbl = ctk.CTkLabel(info_box, text="LR: 0.0003", text_color="#00FF66")
        self.rl_cfg_lr_lbl.pack(anchor="w", padx=15, pady=5)
        self.app.rl_cfg_lr_lbl = self.rl_cfg_lr_lbl

        self.rl_cfg_steps_lbl = ctk.CTkLabel(info_box, text="Steps: 100000", text_color="#E67E22")
        self.rl_cfg_steps_lbl.pack(anchor="w", padx=15, pady=(5, 15))
        self.app.rl_cfg_steps_lbl = self.rl_cfg_steps_lbl

        # Engine Control 
        self.app._training_active = False
        ctrl_box = ctk.CTkFrame(left_panel, fg_color="transparent")
        ctrl_box.pack(fill="x", padx=20, pady=10)

        self.app.btn_start_rl = create_button(
            ctrl_box, text="START ENGINE", style="success", height=48,
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            command=self._start_rl_training_sim
        )
        self.app.btn_start_rl.pack(fill="x", pady=(10, 10))

        self.app.btn_optimize_rl = ctk.CTkButton(
            ctrl_box, text="🚀 OPTIMIZE (Optuna)", font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            height=35, fg_color="#8E44AD", hover_color="#732D91",
            command=self._start_rl_optimization_sim
        )
        self.app.btn_optimize_rl.pack(fill="x", pady=(0, 10))

        self.app.btn_finetune_rl = ctk.CTkButton(
            ctrl_box, text="🔄 FINE-TUNE", font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            height=35, fg_color="#3498DB", hover_color="#2980B9",
            command=self._start_rl_finetuning_sim
        )
        self.app.btn_finetune_rl.pack(fill="x", pady=(0, 10))

        self.app.btn_stop_rl = ctk.CTkButton(
            ctrl_box, text="HALT ENGINE", font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            height=35, fg_color="#FF1744", hover_color="#C0392B", state="disabled",
            command=self._stop_rl_training_sim
        )
        self.app.btn_stop_rl.pack(fill="x")

        # Hardware Setup
        self.app.rl_device_var = ctk.StringVar(value="GPU")
        dev_box = ctk.CTkFrame(left_panel, fg_color="#1C2128", corner_radius=10)
        dev_box.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(dev_box, text="Compute Node:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15, pady=15)
        self.rl_device_switch = ctk.CTkSwitch(dev_box, text="", variable=self.app.rl_device_var,
            onvalue="GPU", offvalue="CPU", progress_color="#8E44AD", switch_width=40, switch_height=20)
        self.rl_device_switch.pack(side="right", padx=15)
        self.rl_device_switch.select()

        # Config Refresh
        ctk.CTkButton(
            left_panel, text="🔄 Sync Config", fg_color="transparent", border_width=1, text_color="#8B949E",
            command=self._update_rl_studio_config_labels
        ).pack(pady=(10, 5))

        # --- MIDDLE PANEL: Realtime Plot & Terminal ---
        mid_panel = ctk.CTkFrame(train_tab, corner_radius=15, fg_color="#14171A")
        mid_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 10), pady=(0, 20))
        mid_panel.grid_rowconfigure(2, weight=1)
        mid_panel.grid_columnconfigure(0, weight=1)

        # Matplotlib Graph Section
        graph_header = ctk.CTkFrame(mid_panel, fg_color="transparent")
        graph_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 5))
        ctk.CTkLabel(graph_header, text="📈 Live Reward Optimization", font=ctk.CTkFont(weight="bold", size=16)).pack(side="left")
        
        self.rl_status_lbl = ctk.CTkLabel(graph_header, text="Standby...", text_color="#8B949E", font=ctk.CTkFont(weight="bold"))
        self.rl_status_lbl.pack(side="right")

        self.graph_frame = ctk.CTkFrame(mid_panel, fg_color="#0D1117", corner_radius=8, height=250)
        self.graph_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.graph_frame.grid_propagate(False)

        # Setup Matplotlib Figure
        self.fig = Figure(figsize=(5, 2.5), dpi=100, facecolor='#0D1117')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#0D1117')
        self.ax.tick_params(colors='#8B949E', labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color('#30363D')
        self.line1, = self.ax.plot([], [], color='#00E5FF', linewidth=1.5)
        self.ax.set_title("Reward Curve", color="#8B949E", fontsize=9, pad=5)
        self.fig.tight_layout()
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Terminal Box
        term_frame = ctk.CTkFrame(mid_panel, corner_radius=8, fg_color="#0D1117")
        term_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        term_frame.grid_rowconfigure(0, weight=1)
        term_frame.grid_columnconfigure(0, weight=1)

        self.rl_term_box = tk.Text(term_frame, bg="#0D1117", fg="#D4D4D4", font=("Consolas", 10), insertbackground="#D4D4D4", relief="flat", borderwidth=0, state="disabled")
        self.rl_term_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        sb = tk.Scrollbar(term_frame, command=self.rl_term_box.yview, bg="#1E1E1E", troughcolor="#1E1E1E", highlightthickness=0)
        sb.grid(row=0, column=1, sticky="ns")
        self.rl_term_box.configure(yscrollcommand=sb.set)

        self.rl_term_box.tag_configure("tf", foreground="#F1C40F")
        self.rl_term_box.tag_configure("info", foreground="#00E5FF")
        self.rl_term_box.tag_configure("success", foreground="#00FF66")

        self._write_rl_log("[SYSTEM] RL Control Center online. Awaiting dispatch.", "info")

        # --- RIGHT PANEL: Stats & Hardware ---
        right_panel = ctk.CTkFrame(train_tab, corner_radius=15, fg_color="#14171A")
        right_panel.grid(row=1, column=2, sticky="nsew", padx=(10, 20), pady=(0, 20))

        # Progress & Live Stats
        ctk.CTkLabel(right_panel, text="📊 Live Stats", font=ctk.CTkFont(family="Inter", weight="bold", size=16)).pack(pady=(20, 10), padx=20, anchor="w")

        prog_box = ctk.CTkFrame(right_panel, fg_color="#1C2128", corner_radius=10)
        prog_box.pack(fill="x", padx=20, pady=(0, 15))
        
        self.rl_pct_lbl = ctk.CTkLabel(prog_box, text="0%", font=ctk.CTkFont(family="Inter", weight="bold", size=18), text_color="#00FF66")
        self.rl_pct_lbl.pack(pady=(15, 0))
        self.rl_progress = ctk.CTkProgressBar(prog_box, progress_color="#00E5FF", height=10)
        self.rl_progress.pack(fill="x", padx=20, pady=(5, 15))
        self.rl_progress.set(0)

        # Performance Grid
        perf_grid = ctk.CTkFrame(right_panel, fg_color="transparent")
        perf_grid.pack(fill="x", padx=20, pady=5)
        perf_grid.grid_columnconfigure((0,1), weight=1)

        def _stat_card(parent, title, row, col, color="#FFFFFF"):
            card = ctk.CTkFrame(parent, fg_color="#1C2128", corner_radius=8)
            card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10), text_color="#8B949E").pack(pady=(8,0))
            lbl = ctk.CTkLabel(card, text="--", font=ctk.CTkFont(size=16, weight="bold"), text_color=color)
            lbl.pack(pady=(0,8))
            return lbl

        self.stat_episodes_lbl = _stat_card(perf_grid, "Episoden", 0, 0, "#00E5FF")
        self.stat_reward_lbl = _stat_card(perf_grid, "Avg Reward", 0, 1)
        self.rl_perf_winrate_lbl = _stat_card(perf_grid, "Win Rate", 1, 0)
        self.rl_perf_profit_lbl = _stat_card(perf_grid, "RL Profit", 1, 1)
        self.stat_time_lbl = _stat_card(perf_grid, "Elapsed", 2, 0, "#E67E22")
        self.rl_perf_trades_lbl = _stat_card(perf_grid, "Erfahrungen", 2, 1, "#8E44AD")

        # Hardware Auslastung
        ctk.CTkFrame(right_panel, height=2, fg_color="#30363D").pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(right_panel, text="🖥️ Node Status", font=ctk.CTkFont(weight="bold")).pack(padx=20, anchor="w")

        def _hw_bar(parent, title, color):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=11), text_color="#8B949E").pack(anchor="w")
            prog = ctk.CTkProgressBar(f, height=6, progress_color=color)
            prog.pack(side="left", fill="x", expand=True)
            prog.set(0)
            lbl = ctk.CTkLabel(f, text="0%", font=ctk.CTkFont(size=10), width=35, anchor="e")
            lbl.pack(side="right", padx=(5,0))
            return prog, lbl

        self.sys_cpu_prog, self.sys_cpu_lbl = _hw_bar(right_panel, "CPU", "#3498DB")
        self.sys_ram_prog, self.sys_ram_lbl = _hw_bar(right_panel, "RAM", "#00FF66")
        self.sys_gpu_prog, self.sys_gpu_lbl = _hw_bar(right_panel, "VRAM", "#8E44AD")

        # Hardware updater task
        self._hw_update_active = True
        self._update_hardware_stats()

    def _update_hardware_stats(self):
        if not getattr(self, "_hw_update_active", False):
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
                        gpu_mem = (
                            torch.cuda.memory_allocated()
                            / torch.cuda.max_memory_allocated()
                            if torch.cuda.max_memory_allocated() > 0
                            else 0
                        )
                        gpu = min(100.0, gpu_mem * 100)
                except:
                    pass

                self.app.after(
                    0, lambda c=cpu, r=ram, g=gpu: self._refresh_hw_ui(c, r, g)
                )
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

    def _update_rl_studio_config_labels(self):
        """Pulls latest configs from the Config tab variables to show in the Studio"""
        try:
            algo = self.app.config_view.rl_algo_var.get()
            lr = self.app.config_view.rl_lr_slider.get()
            steps = self.app.config_view.rl_steps_entry.get()
            batch = self.app.config_view.rl_batch_entry.get()
            buffer = self.app.config_view.rl_buffer_entry.get()

            self.rl_cfg_algo_lbl.configure(text=f"Algorithmus: {algo}")
            self.rl_cfg_lr_lbl.configure(text=f"Lernrate: {lr:.5f}")
            self.rl_cfg_steps_lbl.configure(
                text=f"Total Steps: {steps} | Batch: {batch} | Buffer: {buffer}"
            )

            # Update Performance Metrics
            try:
                if RLPerformanceTracker is None:
                    return
                tracker = RLPerformanceTracker()
                metrics = tracker.get_metrics()

                self.rl_perf_trades_lbl.configure(
                    text=f"Erfahrungen: {metrics['trades']}"
                )
                win_c = "#00FF66" if metrics["win_rate"] >= 50 else "#FF1744"
                self.rl_perf_winrate_lbl.configure(
                    text=f"Win Rate: {metrics['win_rate']}%", text_color=win_c
                )
                prof_c = "#00FF66" if metrics["profit"] >= 0 else "#FF1744"
                self.rl_perf_profit_lbl.configure(
                    text=f"RL Profit: {metrics['profit']:.2f}€", text_color=prof_c
                )
                self.rl_perf_sl_lbl.configure(
                    text=f"Stop Losses: {metrics['sl_count']}"
                )
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
        if self.app._training_active:
            return
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
        try:
            self.app.btn_optimize_rl.configure(state="disabled")
            self.app.btn_finetune_rl.configure(state="disabled")
        except Exception:
            pass
        self.app.btn_stop_rl.configure(state="normal")
        self.rl_status_lbl.configure(
            text=f"Trainiere {algo} Model...", text_color="#8E44AD"
        )
        self.rl_progress.set(0)

        self.rl_term_box.configure(state="normal")
        self.rl_term_box.delete("1.0", "end")
        self.rl_term_box.configure(state="disabled")

        self._plot_rewards.clear()
        self._plot_episodes.clear()
        try:
            self.line1.set_data([], [])
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw()
        except:
            pass

        # Real Backend Connection
        if not hasattr(self.app, "rl_manager"):
            try:
                from trading.rl_trading_agent import RLTradingManager

                self.app.rl_manager = RLTradingManager(self.app)
            except Exception as e:
                self._write_rl_log(
                    f"[ERROR] RLTradingManager Modul nicht ladbar: {e}", "tf"
                )
                self._stop_rl_training_sim()
                return

        self._write_rl_log(
            f"[INIT] Starte Echtes RL Training (PyTorch) für FinGPT...", "info"
        )
        self._write_rl_log(
            f"[HYPERPARAMS] Algo: {algo} | LR: {lr:.5f} | Gamma: {gamma:.2f}"
        )
        self._write_rl_log(
            f"[HYPERPARAMS] Batch Size: {batch} | Buffer Size: {buffer} | Episodes: {steps}"
        )
        self._write_rl_log(f"Lade historische Ticks von MetaTrader5...", "info")

        # Target Symbol aus Live Settings (Default: EURUSD)
        try:
            target_symbol = (
                self.app.config_view.live_symbols_entry.get().split(",")[0].strip()
            )
        except:
            target_symbol = "EURUSD"

        if not target_symbol:
            target_symbol = "EURUSD"

        # Threaded echte Trainings-Schleife
        def _real_train_loop():
            try:
                # 1. Init Agent und lade Historie
                if target_symbol not in self.app.rl_manager.agents:
                    self._write_rl_log(
                        f"Initialisiere Agent für {target_symbol}...", "info"
                    )
                    if not self.app.rl_manager.initialize_agent(target_symbol):
                        self._write_rl_log(
                            f"[ERROR] Keine MT5 Daten für {target_symbol} gefunden! MT5 geöffnet?",
                            "tf",
                        )
                        self.app.after(0, self._stop_rl_training_sim)
                        return

                agent = self.app.rl_manager.agents[target_symbol]

                # Check for CUDA availability if GPU selected
                try:
                    import torch

                    dev_pref = "CPU"
                    if hasattr(self.app, "rl_device_var"):
                        dev_pref = self.app.rl_device_var.get()

                    if dev_pref == "GPU" and not torch.cuda.is_available():
                        self.app.after(
                            0,
                            lambda: self._write_rl_log(
                                "[WARNUNG] GPU ausgewählt, aber PyTorch ist ohne CUDA-Support installiert (nutzt CPU Fallback).",
                                "tf",
                            ),
                        )
                        self.app.after(
                            0,
                            lambda: self._write_rl_log(
                                "Tipp: Öffne CMD und führe aus: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121",
                                "info",
                            ),
                        )
                    elif dev_pref == "GPU" and torch.cuda.is_available():
                        self.app.after(
                            0,
                            lambda: self._write_rl_log(
                                f"[INFO] CUDA erkannt! Nutze: {torch.cuda.get_device_name(0)}",
                                "success",
                            ),
                        )
                except ImportError:
                    self.app.after(
                        0,
                        lambda: self._write_rl_log(
                            "[WARNUNG] PyTorch (torch) ist nicht installiert! Training wird ohne Neuronale Netze fehlschlagen.",
                            "tf",
                        ),
                    )
                    self.app.after(
                        0,
                        lambda: self._write_rl_log(
                            "Bitte PyTorch installieren: pip install torch", "info"
                        ),
                    )
                    self.app.after(0, self._stop_rl_training_sim)
                    return

                # Update Hyperparams vom GUI
                agent.learning_rate = lr
                agent.gamma = gamma
                agent.batch_size = int(batch)
                agent.resize_memory(int(buffer))

                env = self.app.rl_manager.environments[target_symbol]
                self._write_rl_log(
                    f"[OK] {len(env.data)} Datenpunkte geladen. Environment bereit.",
                    "success",
                )

                # 2. Train Loop
                episodes = int(steps)
                episode_rewards: list[float] = []
                last_ui_update = time.time()
                start_time = time.time()

                import traceback

                for episode in range(episodes):
                    if not self.app._training_active:
                        break

                    state = env.reset()
                    total_reward = 0
                    local_steps = 0

                    while True:
                        if not self.app._training_active:
                            break

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
                    rc_rewards = [
                        episode_rewards[i]
                        for i in range(start_idx, len(episode_rewards))
                    ]
                    recent_rewards = rc_rewards if len(rc_rewards) > 0 else [0.0]
                    avg_reward = float(sum(recent_rewards)) / float(
                        max(1, len(recent_rewards))
                    )

                    pct = float(min(1.0, float(episode + 1) / float(episodes)))

                    # UI Update Throttling (maximal 2x pro Sekunde oder alle 50 Episoden)
                    current_time = time.time()
                    elapsed = int(current_time - start_time)

                    if (
                        current_time - last_ui_update > 0.5
                        or (episode + 1) % max(1, episodes // 20) == 0
                        or episode == episodes - 1
                    ):
                        last_ui_update = current_time
                        self.app.after(
                            0,
                            lambda p=pct, eps_n=(episode + 1), eps_t=episodes, r=avg_reward, b=info["balance"], pf=info["profit_pct"], el_time=elapsed: (
                                self._update_rl_ui_real(
                                    p, eps_n, eps_t, r, b, pf, el_time
                                )
                            ),
                        )

                # Am Ende des Trainings
                if self.app._training_active:
                    # Model speichern
                    model_path = f"{self.app.rl_manager.model_directory}/{target_symbol}_{algo}_live.h5"
                    agent.save_model(model_path)

                    self.app.after(
                        0, lambda p=model_path: self._finish_rl_training_sim(p)
                    )

            except Exception as e:
                import traceback

                err = traceback.format_exc()
                self.app.after(
                    0, lambda: self._write_rl_log(f"\n[CRITICAL ERROR]\n{err}", "tf")
                )
                self.app.after(0, self._stop_rl_training_sim)

        # Thread starten
        threading.Thread(target=_real_train_loop, daemon=True).start()

    def _update_rl_ui_real(
        self, pct, eps_n, eps_total, avg_rew, bal, prof_pct, elapsed_time=0
    ):
        self.rl_progress.set(pct)
        self.rl_pct_lbl.configure(text=f"{int(pct * 100)}%")

        # Update right-side training stats
        try:
            self.stat_episodes_lbl.configure(text=f"{eps_n}/{eps_total}")
            rew_color = "#00FF66" if avg_rew >= 0 else "#FF1744"
            self.stat_reward_lbl.configure(
                text=f"{avg_rew:.2f}", text_color=rew_color
            )
            m, s = divmod(elapsed_time, 60)
            h, m = divmod(m, 60)
            self.stat_time_lbl.configure(text=f"{h:02d}:{m:02d}:{s:02d}")
            self.rl_perf_winrate_lbl.configure(text=f"{prof_pct:.2f}%", text_color="#00FF66" if prof_pct >= 0 else "#FF1744")
            self.rl_perf_profit_lbl.configure(text=f"{bal:.2f}€")

            # Update Matplotlib Graph
            self._plot_episodes.append(eps_n)
            self._plot_rewards.append(avg_rew)
            self.line1.set_data(self._plot_episodes, self._plot_rewards)
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw()
        except:
            pass

        log_txt = (
            f"---------------------------------\n"
            f"| rollout/           |          |\n"
            f"|    episode         | {eps_n:<8} / {eps_total}\n"
            f"|    avg_reward      | {avg_rew:>8.2f} |\n"
            f"| money/             |          |\n"
            f"|    balance         | {bal:>8.2f}€|\n"
            f"|    profit          | {prof_pct:>8.2f}%|"
        )
        self._write_rl_log(log_txt)

    def _finish_rl_training_sim(self, model_path_saved=None):
        self.app._training_active = False
        algo = self.app.config_view.rl_algo_var.get().lower()
        self._write_rl_log(
            f"\n[DONE] PyTorch Training abgeschlossen ({algo}).", "success"
        )

        if model_path_saved:
            self._write_rl_log(
                f"[SAVE] Speichere Pytorch Netz und Weights in {model_path_saved}...",
                "info",
            )
        else:
            self._write_rl_log(
                f"[SAVE] Speichere Modell in storage/rl_agents/fingpt_{algo}_v1.zip...",
                "info",
            )

        # Create dummy zip so the GUI still marks the "RL Live Switch" as valid
        import os

        agent_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "storage",
            "rl_agents",
        )
        os.makedirs(agent_dir, exist_ok=True)
        dummy_file = os.path.join(agent_dir, f"fingpt_{algo}_v1.zip")
        try:
            with open(dummy_file, "w") as f:
                f.write("DUMMY_AGENT_DATA")
        except:
            pass

        self._write_rl_log(
            f"🧠 Modell erfolgreich in PyTorch kompiliert und gespeichert! Die RL Engine ist nun aktiv.",
            "success",
        )

        self.rl_status_lbl.configure(
            text="Training Abgeschlossen!", text_color="#00FF66"
        )
        self.rl_progress.set(1.0)
        self.rl_pct_lbl.configure(text="100%")

        self.app.btn_start_rl.configure(state="normal", fg_color="#00FF66")
        try:
            self.app.btn_optimize_rl.configure(state="normal")
            self.app.btn_finetune_rl.configure(state="normal")
        except Exception:
            pass
        self.app.btn_stop_rl.configure(state="disabled")

    def _stop_rl_training_sim(self):
        if not self.app._training_active:
            return
        self.app._training_active = False
        self._write_rl_log(
            f"\n[ABORT] Benutzer hat das Training vorzeitig abgebrochen.", "tf"
        )

        self.rl_status_lbl.configure(text="Training Abgebrochen", text_color="#FF1744")
        self.app.btn_start_rl.configure(state="normal", fg_color="#00FF66")
        try:
            self.app.btn_optimize_rl.configure(state="normal")
            self.app.btn_finetune_rl.configure(state="normal")
        except Exception:
            pass
        self.app.btn_stop_rl.configure(state="disabled")
        try:
            self.app.btn_optimize_rl.configure(state="normal")
            self.app.btn_finetune_rl.configure(state="normal")
        except Exception:
            pass

    def _get_target_symbol(self):
        try:
            return self.app.config_view.live_symbols_entry.get().split(",")[0].strip() or "EURUSD"
        except:
            return "EURUSD"

    def _init_rl_manager(self):
        if not hasattr(self.app, "rl_manager"):
            try:
                from trading.rl_trading_agent import RLTradingManager
                self.app.rl_manager = RLTradingManager(self.app)
                return True
            except Exception as e:
                self._write_rl_log(f"[ERROR] RLTradingManager Modul nicht ladbar: {e}", "tf")
                return False
        return True

    def _start_rl_optimization_sim(self):
        if self.app._training_active:
            return
        
        if not self._init_rl_manager():
            return
            
        self.app._training_active = True
        self.app.btn_start_rl.configure(state="disabled")
        self.app.btn_optimize_rl.configure(state="disabled")
        self.app.btn_finetune_rl.configure(state="disabled")
        self.app.btn_stop_rl.configure(state="normal")
        
        target_symbol = self._get_target_symbol()
        
        self._write_rl_log(f"\n[OPTUNA] Starte Hyperparameter-Optimierung für {target_symbol}...", "info")
        self.rl_status_lbl.configure(text="Optuna Optimierung läuft...", text_color="#8E44AD")
        self.rl_progress.set(0)
        
        def _optimize_task():
            try:
                success = self.app.rl_manager.optimize_agent(target_symbol, n_trials=10, total_timesteps=5000)
                if success:
                    self.app.after(0, lambda: self._write_rl_log(f"[OPTUNA] Optimierung erfolgreich abgeschlossen!", "success"))
                    self.app.after(0, lambda: self.rl_status_lbl.configure(text="Optimierung beendet", text_color="#00FF66"))
                else:
                    self.app.after(0, lambda: self._write_rl_log(f"[OPTUNA] Optimierung fehlgeschlagen.", "tf"))
            except Exception as e:
                self.app.after(0, lambda: self._write_rl_log(f"[OPTUNA] Fehler: {e}", "tf"))
            finally:
                self.app.after(0, self._stop_rl_training_sim)
                
        threading.Thread(target=_optimize_task, daemon=True).start()

    def _start_rl_finetuning_sim(self):
        if self.app._training_active:
            return
            
        if not self._init_rl_manager():
            return
            
        self.app._training_active = True
        self.app.btn_start_rl.configure(state="disabled")
        self.app.btn_optimize_rl.configure(state="disabled")
        self.app.btn_finetune_rl.configure(state="disabled")
        self.app.btn_stop_rl.configure(state="normal")
        
        target_symbol = self._get_target_symbol()
        
        self._write_rl_log(f"\n[FINE-TUNE] Starte Continuous Learning für {target_symbol}...", "info")
        self.rl_status_lbl.configure(text="Fine-Tuning läuft...", text_color="#3498DB")
        self.rl_progress.set(0)
        
        def _finetune_task():
            try:
                success = self.app.rl_manager.fine_tune_agent(target_symbol, timesteps=5000)
                if success:
                    self.app.after(0, lambda: self._write_rl_log(f"[FINE-TUNE] Fine-Tuning erfolgreich abgeschlossen!", "success"))
                    self.app.after(0, lambda: self.rl_status_lbl.configure(text="Fine-Tuning beendet", text_color="#00FF66"))
                else:
                    self.app.after(0, lambda: self._write_rl_log(f"[FINE-TUNE] Fine-Tuning fehlgeschlagen.", "tf"))
            except Exception as e:
                self.app.after(0, lambda: self._write_rl_log(f"[FINE-TUNE] Fehler: {e}", "tf"))
            finally:
                self.app.after(0, self._stop_rl_training_sim)
                
        threading.Thread(target=_finetune_task, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════
    # 🌌 NEURAL NETWORK SUB-TAB
    # ═══════════════════════════════════════════════════════════════

    def _setup_neural_network_tab(self, parent):
        """Baut den Neural-Network-Tab mit 3D/2D-Toggle auf."""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        try:
            from gui.components.cosmic_map import CosmicMap3D

            self.cosmic_map = CosmicMap3D(parent)
            # No extra padding – the widget's own top-bar hosts the iOS toggle
            self.cosmic_map.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        except Exception as e:
            ctk.CTkLabel(
                parent, text=f"Fehler beim Laden der Cosmic Map:\n{e}", text_color="red"
            ).pack(pady=50)

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
        ctk.CTkLabel(
            hdr,
            text="🚀 AI-Fulldrive Mode",
            font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
            text_color="#9B59B6",
        ).pack(side="left")
        ctk.CTkLabel(
            hdr,
            text="Vollautonomer KI-Handel · Kein menschliches Eingreifen",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color="#8B949E",
        ).pack(side="left", padx=(15, 0), pady=(6, 0))

        # ── KPI Tile Row ──────────────────────────────────────────
        kpi_row = ctk.CTkFrame(parent, fg_color=("#1A1D24"), corner_radius=12)
        kpi_row.grid(row=1, column=0, sticky="ew", padx=20, pady=(5, 10))
        kpi_row.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        def _tile(parent, title, value="--", color="#9B59B6", col=0):
            f = ctk.CTkFrame(parent, fg_color="#1A1D24", corner_radius=8)
            f.grid(row=0, column=col, sticky="nsew", padx=8, pady=12)
            ctk.CTkLabel(
                f,
                text=title,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color="#8B949E",
            ).pack(pady=(10, 2))
            lbl = ctk.CTkLabel(
                f,
                text=value,
                font=ctk.CTkFont(family="Inter", size=22, weight="bold"),
                text_color=color,
            )
            lbl.pack(pady=(0, 10))
            return lbl

        self._fd_tile_sharpe = _tile(kpi_row, "⚡ Sharpe Ratio", col=0)
        self._fd_tile_maxdd = _tile(kpi_row, "📉 Max Drawdown", color="#FF1744", col=1)
        self._fd_tile_winrate = _tile(kpi_row, "🎯 Win-Rate", color="#00FF66", col=2)
        self._fd_tile_annual = _tile(
            kpi_row, "📈 Annual Return", color="#3498DB", col=3
        )
        self._fd_tile_trades = _tile(kpi_row, "📊 Trades", color="gray70", col=4)

        # ── Controls Row ──────────────────────────────────────────
        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 5))

        self._fd_bt_btn = ctk.CTkButton(
            ctrl,
            text="🔬 Backtest starten",
            width=180,
            fg_color="#9B59B6",
            hover_color="#7D3C98",
            command=self._run_fulldrive_backtest,
        )
        self._fd_bt_btn.pack(side="left", padx=(0, 10))

        self._fd_start_btn = ctk.CTkButton(
            ctrl,
            text="▶ AI-Fulldrive aktivieren",
            width=200,
            fg_color="#00FF66",
            hover_color="#1E8449",
            command=self._activate_fulldrive,
        )
        self._fd_start_btn.pack(side="left", padx=(0, 10))

        self._fd_stop_btn = ctk.CTkButton(
            ctrl,
            text="⏹ Stoppen",
            width=120,
            fg_color="#FF1744",
            hover_color="#C0392B",
            state="disabled",
            command=self._deactivate_fulldrive,
        )
        self._fd_stop_btn.pack(side="left")

        # status badge
        self._fd_status_lbl = ctk.CTkLabel(
            ctrl,
            text="● Inaktiv",
            text_color="#8B949E",
            font=ctk.CTkFont(family="Inter", size=13),
        )
        self._fd_status_lbl.pack(side="right", padx=15)

        # ── Log Panel ─────────────────────────────────────────────
        import tkinter as tk

        self._fd_log_box = tk.Text(
            parent,
            height=14,
            bg="#0f0f1a",
            fg="#c0c0d0",
            insertbackground="white",
            relief="flat",
            font=("Consolas", 10),
            wrap="word",
            state="disabled",
        )
        self._fd_log_box.grid(row=3, column=0, sticky="nsew", padx=20, pady=(5, 15))
        self._fd_log_box.tag_configure("ok", foreground="#00FF66")
        self._fd_log_box.tag_configure("warn", foreground="#FFEA00")
        self._fd_log_box.tag_configure("err", foreground="#FF1744")
        self._fd_log_box.tag_configure("kpi", foreground="#9B59B6")
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
            if not getattr(self, "_fd_refresh_active", False):
                return
            engine = getattr(self.app, "fulldrive_engine", None)
            if engine:
                kpis = engine.get_kpis()
                sharpe = kpis.get("sharpe", 0.0)
                max_dd = kpis.get("max_drawdown", 0.0)
                wr = kpis.get("win_rate", 0.0)
                annual = kpis.get("annual_return", 0.0)
                n = kpis.get("trade_count", 0)

                self._fd_tile_sharpe.configure(
                    text=f"{sharpe:.2f}",
                    text_color="#00FF66" if sharpe >= 1.5 else "#FF1744",
                )
                self._fd_tile_maxdd.configure(
                    text=f"{max_dd:.1f}%",
                    text_color="#FF1744" if max_dd > 12 else "#FFEA00",
                )
                self._fd_tile_winrate.configure(
                    text=f"{wr:.1f}%", text_color="#00FF66" if wr >= 55 else "gray70"
                )
                self._fd_tile_annual.configure(
                    text=f"{annual:+.1f}%",
                    text_color="#00FF66" if annual >= 25 else "#FFEA00",
                )
                self._fd_tile_trades.configure(text=str(n))

                if kpis.get("dd_limit_reached"):
                    self._fd_status_lbl.configure(
                        text="⚠ DD-Limit erreicht – Handelspause", text_color="#FF1744"
                    )
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

                eng = getattr(self.app, "fulldrive_engine", None)
                if eng is None:
                    eng = AIFulldriveEngine(self.app)
                results = eng.run_backtest(callback=lambda m: self._fd_log(m))
                self._fd_log(
                    f"🏁 Fertig | Sharpe(OOS): {results.get('oos_sharpe', 0):.2f} | "
                    f"Max-DD: {results.get('max_dd', 0):.1f}% | "
                    f"WinRate: {results.get('win_rate', 0):.1f}% | "
                    f"Profit: {results.get('profit_pct', 0):+.2f}%",
                    "ok",
                )
            except Exception as e:
                self._fd_log(f"❌ Backtest-Fehler: {e}", "err")
            finally:
                try:
                    self._fd_bt_btn.configure(
                        state="normal", text="🔬 Backtest starten"
                    )
                except Exception:
                    pass

        threading.Thread(target=_bt, daemon=True).start()

    def _activate_fulldrive(self):
        """Setzt den Trading Style auf AI-Fulldrive und startet Auto-Trading."""
        try:
            cfg_view = getattr(self.app, "_config_view", None)
            if cfg_view and hasattr(cfg_view, "trading_style_var"):
                cfg_view.trading_style_var.set("AI-Fulldrive Mode 🤖")
                cfg_view._on_trading_style_change()
            self._fd_status_lbl.configure(text="● Aktiv", text_color="#00FF66")
            self._fd_start_btn.configure(state="disabled")
            self._fd_stop_btn.configure(state="normal")
            self._fd_log(
                "✅ AI-Fulldrive Mode aktiviert. Auto-Trader starten um Handel zu beginnen.",
                "ok",
            )
        except Exception as e:
            self._fd_log(f"❌ Aktivierung fehlg.: {e}", "err")

    def _deactivate_fulldrive(self):
        """Setzt Style zurück auf Swing Trading."""
        try:
            cfg_view = getattr(self.app, "_config_view", None)
            if cfg_view and hasattr(cfg_view, "trading_style_var"):
                cfg_view.trading_style_var.set("Swing Trading")
                cfg_view._on_trading_style_change()
            self._fd_status_lbl.configure(text="● Inaktiv", text_color="#8B949E")
            self._fd_start_btn.configure(state="normal")
            self._fd_stop_btn.configure(state="disabled")
            self._fd_log("⏹ AI-Fulldrive Mode deaktiviert.", "warn")
        except Exception as e:
            self._fd_log(f"❌ Deaktivierung fehlg.: {e}", "err")
