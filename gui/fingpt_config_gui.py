#!/usr/bin/env python3
"""
FinGPT Configuration GUI
Modernes Tkinter-Interface für die Konfiguration von FinGPT
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
from typing import Dict, Any, Optional, List
import json
from pathlib import Path

# Import der Geschäftslogik
from core.config_manager import ConfigManager, FinGPTConfig, FinGPTExtendedConfig


class FinGPTConfigGUI:
    """
    Haupt-GUI-Klasse für die FinGPT Konfiguration
    
    Diese Klasse implementiert:
    - Moderne Benutzeroberfläche mit Tkinter und ttk
    - Saubere Trennung zwischen GUI und Geschäftslogik
    - Validierung und Error-Handling
    - Visuelle Rückmeldung über den Konfigurationsstatus
    """
    
    def __init__(self):
        """Initialisiert die GUI"""
        self.root = tk.Tk()
        self.config_manager = ConfigManager()
        
        # GUI-Setup
        self.setup_window()
        self.create_widgets()
        self.load_current_config()
        
        # Status-Tracking
        self.config_changed = False
        self.validation_errors = []
        
    def setup_window(self):
        """Konfiguriert das Hauptfenster"""
        self.root.title("FinGPT Configuration Manager")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Icon setzen (falls vorhanden)
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # Style konfigurieren
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Farben definieren
        self.colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72',
            'success': '#F18F01',
            'warning': '#C73E1D',
            'background': '#F5F5F5',
            'text': '#333333'
        }
        
        # Style anpassen
        self.style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        self.style.configure('Section.TLabel', font=('Arial', 10, 'bold'))
        self.style.configure('Success.TLabel', foreground='green')
        self.style.configure('Error.TLabel', foreground='red')
        
    def create_widgets(self):
        """Erstellt alle GUI-Widgets"""
        # Haupt-Container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Grid-Konfiguration
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(1, weight=1)
        
        # Header
        self.create_header(main_container)
        
        # Notebook für Tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Tabs erstellen
        self.create_basic_tab()
        self.create_advanced_tab()
        self.create_extended_tab()
        
        # Status-Bar
        self.create_status_bar(main_container)
        
        # Button-Leiste
        self.create_button_bar(main_container)
        
    def create_header(self, parent):
        """Erstellt den Header-Bereich"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Titel
        title_label = ttk.Label(header_frame, text="FinGPT Configuration Manager", style='Title.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Status-Label
        self.status_label = ttk.Label(header_frame, text="Bereit", style='Success.TLabel')
        self.status_label.grid(row=0, column=1, sticky=tk.E)
        
        header_frame.columnconfigure(1, weight=1)
        
    def create_basic_tab(self):
        """Erstellt den Tab für grundlegende Einstellungen"""
        basic_frame = ttk.Frame(self.notebook)
        self.notebook.add(basic_frame, text="Grundlegende Einstellungen")
        
        # Scrollbar für langen Inhalt
        canvas = tk.Canvas(basic_frame)
        scrollbar = ttk.Scrollbar(basic_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Grundlegende Einstellungen
        row = 0
        ttk.Label(scrollable_frame, text="Allgemeine Einstellungen", style='Section.TLabel').grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(10, 5))
        row += 1
        
        # Ollama URL
        ttk.Label(scrollable_frame, text="Ollama URL:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.ollama_url_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.ollama_url_var, width=40).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(scrollable_frame, text="Testen", command=self.test_ollama_connection).grid(
            row=row, column=2, padx=5)
        row += 1
        
        # Modell-Auswahl
        ttk.Label(scrollable_frame, text="KI-Modell:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(scrollable_frame, textvariable=self.model_var, width=37)
        self.model_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(scrollable_frame, text="Aktualisieren", command=self.refresh_models).grid(
            row=row, column=2, padx=5)
        row += 1
        
        # Trading Einstellungen
        ttk.Label(scrollable_frame, text="Trading Einstellungen", style='Section.TLabel').grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(20, 5))
        row += 1
        
        # Trading aktivieren
        self.trading_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(scrollable_frame, text="Trading aktivieren", 
                       variable=self.trading_enabled_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5)
        row += 1
        
        # Default Lot Size
        ttk.Label(scrollable_frame, text="Default Lot Size:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.lot_size_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.lot_size_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        # Max Risk Percent
        ttk.Label(scrollable_frame, text="Max Risk (%):").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.max_risk_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.max_risk_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        # Auto Trading
        self.auto_trading_var = tk.BooleanVar()
        ttk.Checkbutton(scrollable_frame, text="Auto-Trading aktivieren", 
                       variable=self.auto_trading_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5)
        row += 1
        
        # Auto Trade Symbols
        ttk.Label(scrollable_frame, text="Auto-Trade Symbole:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.symbols_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.symbols_var, width=40).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        row += 1
        
        # Analysis Interval
        ttk.Label(scrollable_frame, text="Analyse-Intervall (s):").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.interval_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.interval_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        # Canvas und Scrollbar konfigurieren
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        basic_frame.columnconfigure(0, weight=1)
        basic_frame.rowconfigure(0, weight=1)
        scrollable_frame.columnconfigure(1, weight=1)
        
    def create_advanced_tab(self):
        """Erstellt den Tab für erweiterte Einstellungen"""
        advanced_frame = ttk.Frame(self.notebook)
        self.notebook.add(advanced_frame, text="Erweiterte Einstellungen")
        
        # Scrollbar für langen Inhalt
        canvas = tk.Canvas(advanced_frame)
        scrollbar = ttk.Scrollbar(advanced_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        row = 0
        
        # RSI Einstellungen
        ttk.Label(scrollable_frame, text="RSI Einstellungen", style='Section.TLabel').grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(10, 5))
        row += 1
        
        ttk.Label(scrollable_frame, text="RSI Periode:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.rsi_period_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.rsi_period_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        ttk.Label(scrollable_frame, text="RSI Overbought:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.rsi_overbought_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.rsi_overbought_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        ttk.Label(scrollable_frame, text="RSI Oversold:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.rsi_oversold_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.rsi_oversold_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        # MACD Einstellungen
        ttk.Label(scrollable_frame, text="MACD Einstellungen", style='Section.TLabel').grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(20, 5))
        row += 1
        
        ttk.Label(scrollable_frame, text="Fast Period:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.macd_fast_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.macd_fast_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        ttk.Label(scrollable_frame, text="Slow Period:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.macd_slow_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.macd_slow_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        ttk.Label(scrollable_frame, text="Signal Period:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.macd_signal_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.macd_signal_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        # Support/Resistance Einstellungen
        ttk.Label(scrollable_frame, text="Support/Resistance Einstellungen", style='Section.TLabel').grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(20, 5))
        row += 1
        
        ttk.Label(scrollable_frame, text="Lookback Period:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.sr_lookback_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.sr_lookback_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        ttk.Label(scrollable_frame, text="Min Touches:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.sr_touches_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.sr_touches_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        ttk.Label(scrollable_frame, text="Tolerance:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.sr_tolerance_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.sr_tolerance_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        # Canvas und Scrollbar konfigurieren
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        advanced_frame.columnconfigure(0, weight=1)
        advanced_frame.rowconfigure(0, weight=1)
        scrollable_frame.columnconfigure(1, weight=1)
        
    def create_extended_tab(self):
        """Erstellt den Tab für Extended-Einstellungen"""
        extended_frame = ttk.Frame(self.notebook)
        self.notebook.add(extended_frame, text="Extended Einstellungen")
        
        # Scrollbar für langen Inhalt
        canvas = tk.Canvas(extended_frame)
        scrollbar = ttk.Scrollbar(extended_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        row = 0
        
        # Menü-Konfiguration
        ttk.Label(scrollable_frame, text="Menü-Konfiguration", style='Section.TLabel').grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        row += 1
        
        self.show_original_var = tk.BooleanVar()
        ttk.Checkbutton(scrollable_frame, text="Original-Menü anzeigen", 
                       variable=self.show_original_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5)
        row += 1
        
        self.show_extended_var = tk.BooleanVar()
        ttk.Checkbutton(scrollable_frame, text="Erweitertes Menü anzeigen", 
                       variable=self.show_extended_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5)
        row += 1
        
        ttk.Label(scrollable_frame, text="Menü-Style:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.menu_style_var = tk.StringVar()
        menu_combo = ttk.Combobox(scrollable_frame, textvariable=self.menu_style_var, 
                                 values=["grouped", "original"], width=20)
        menu_combo.grid(row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        # Erweiterte Funktionen
        ttk.Label(scrollable_frame, text="Erweiterte Funktionen", style='Section.TLabel').grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(20, 5))
        row += 1
        
        self.enable_advanced_indicators_var = tk.BooleanVar()
        ttk.Checkbutton(scrollable_frame, text="Erweiterte Indikatoren aktivieren", 
                       variable=self.enable_advanced_indicators_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5)
        row += 1
        
        self.enable_enhanced_ai_var = tk.BooleanVar()
        ttk.Checkbutton(scrollable_frame, text="Enhanced KI-Analyse aktivieren", 
                       variable=self.enable_enhanced_ai_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5)
        row += 1
        
        self.enable_multi_scanner_var = tk.BooleanVar()
        ttk.Checkbutton(scrollable_frame, text="Multi-Indikator Scanner aktivieren", 
                       variable=self.enable_multi_scanner_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5)
        row += 1
        
        self.enable_comparison_var = tk.BooleanVar()
        ttk.Checkbutton(scrollable_frame, text="Indikator-Vergleich aktivieren", 
                       variable=self.enable_comparison_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5)
        row += 1
        
        # UI-Einstellungen
        ttk.Label(scrollable_frame, text="UI-Einstellungen", style='Section.TLabel').grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(20, 5))
        row += 1
        
        self.show_status_bar_var = tk.BooleanVar()
        ttk.Checkbutton(scrollable_frame, text="Status-Bar anzeigen", 
                       variable=self.show_status_bar_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5)
        row += 1
        
        ttk.Label(scrollable_frame, text="Farbschema:").grid(row=row, column=0, sticky=tk.W, padx=5)
        self.color_scheme_var = tk.StringVar()
        color_combo = ttk.Combobox(scrollable_frame, textvariable=self.color_scheme_var, 
                                  values=["default", "dark", "light"], width=20)
        color_combo.grid(row=row, column=1, sticky=tk.W, padx=5)
        row += 1
        
        # Canvas und Scrollbar konfigurieren
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        extended_frame.columnconfigure(0, weight=1)
        extended_frame.rowconfigure(0, weight=1)
        scrollable_frame.columnconfigure(1, weight=1)
        
    def create_status_bar(self, parent):
        """Erstellt die Status-Bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Status-Label
        self.config_status_label = ttk.Label(status_frame, text="Konfiguration geladen")
        self.config_status_label.grid(row=0, column=0, sticky=tk.W)
        
        # Änderungs-Label
        self.changes_label = ttk.Label(status_frame, text="", style='Warning.TLabel')
        self.changes_label.grid(row=0, column=1, sticky=tk.E)
        
        status_frame.columnconfigure(1, weight=1)
        
    def create_button_bar(self, parent):
        """Erstellt die Button-Leiste"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Buttons
        ttk.Button(button_frame, text="Speichern", command=self.save_config).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Zurücksetzen", command=self.reset_config).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Importieren", command=self.import_config).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="Exportieren", command=self.export_config).grid(row=0, column=3, padx=5)
        ttk.Button(button_frame, text="Validieren", command=self.validate_config).grid(row=0, column=4, padx=5)
        ttk.Button(button_frame, text="Beenden", command=self.quit_app).grid(row=0, column=5, padx=5)
        
        button_frame.columnconfigure(5, weight=1)
        
    def load_current_config(self):
        """Lädt die aktuelle Konfiguration in die GUI"""
        try:
            config = self.config_manager.fingpt_config
            extended_config = self.config_manager.fingpt_extended_config
            
            # Grundlegende Einstellungen
            self.ollama_url_var.set(config.ollama_url)
            self.model_var.set(config.selected_model or "")
            self.trading_enabled_var.set(config.trading_enabled)
            self.lot_size_var.set(str(config.default_lot_size))
            self.max_risk_var.set(str(config.max_risk_percent))
            self.auto_trading_var.set(config.auto_trading)
            self.symbols_var.set(", ".join(config.auto_trade_symbols))
            self.interval_var.set(str(config.analysis_interval))
            
            # Erweiterte Einstellungen
            self.rsi_period_var.set(str(config.rsi_period))
            self.rsi_overbought_var.set(str(config.rsi_overbought))
            self.rsi_oversold_var.set(str(config.rsi_oversold))
            
            self.macd_fast_var.set(str(config.macd_fast_period))
            self.macd_slow_var.set(str(config.macd_slow_period))
            self.macd_signal_var.set(str(config.macd_signal_period))
            
            self.sr_lookback_var.set(str(config.sr_lookback_period))
            self.sr_touches_var.set(str(config.sr_min_touches))
            self.sr_tolerance_var.set(str(config.sr_tolerance))
            
            # Extended Einstellungen
            self.show_original_var.set(extended_config.show_original_menu)
            self.show_extended_var.set(extended_config.show_extended_menu)
            self.menu_style_var.set(extended_config.menu_style)
            
            self.enable_advanced_indicators_var.set(extended_config.enable_advanced_indicators)
            self.enable_enhanced_ai_var.set(extended_config.enable_enhanced_ai_analysis)
            self.enable_multi_scanner_var.set(extended_config.enable_multi_indicator_scanner)
            self.enable_comparison_var.set(extended_config.enable_indicator_comparison)
            
            self.show_status_bar_var.set(extended_config.show_status_bar)
            self.color_scheme_var.set(extended_config.color_scheme)
            
            # Modelle aktualisieren
            self.refresh_models()
            
            # Status aktualisieren
            self.update_status("Konfiguration geladen", "success")
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der Konfiguration: {e}")
            self.update_status("Ladefehler", "error")
    
    def save_config(self):
        """Speichert die aktuelle Konfiguration"""
        try:
            # Konfiguration aus GUI lesen
            config = self.config_manager.fingpt_config
            extended_config = self.config_manager.fingpt_extended_config
            
            # Grundlegende Einstellungen
            config.ollama_url = self.ollama_url_var.get()
            config.selected_model = self.model_var.get() or None
            config.trading_enabled = self.trading_enabled_var.get()
            config.default_lot_size = float(self.lot_size_var.get())
            config.max_risk_percent = float(self.max_risk_var.get())
            config.auto_trading = self.auto_trading_var.get()
            config.auto_trade_symbols = [s.strip() for s in self.symbols_var.get().split(",") if s.strip()]
            config.analysis_interval = int(self.interval_var.get())
            
            # Erweiterte Einstellungen
            config.rsi_period = int(self.rsi_period_var.get())
            config.rsi_overbought = float(self.rsi_overbought_var.get())
            config.rsi_oversold = float(self.rsi_oversold_var.get())
            
            config.macd_fast_period = int(self.macd_fast_var.get())
            config.macd_slow_period = int(self.macd_slow_var.get())
            config.macd_signal_period = int(self.macd_signal_var.get())
            
            config.sr_lookback_period = int(self.sr_lookback_var.get())
            config.sr_min_touches = int(self.sr_touches_var.get())
            config.sr_tolerance = float(self.sr_tolerance_var.get())
            
            # Extended Einstellungen
            extended_config.show_original_menu = self.show_original_var.get()
            extended_config.show_extended_menu = self.show_extended_var.get()
            extended_config.menu_style = self.menu_style_var.get()
            
            extended_config.enable_advanced_indicators = self.enable_advanced_indicators_var.get()
            extended_config.enable_enhanced_ai_analysis = self.enable_enhanced_ai_var.get()
            extended_config.enable_multi_indicator_scanner = self.enable_multi_scanner_var.get()
            extended_config.enable_indicator_comparison = self.enable_comparison_var.get()
            
            extended_config.show_status_bar = self.show_status_bar_var.get()
            extended_config.color_scheme = self.color_scheme_var.get()
            
            # Validieren
            errors = self.config_manager.validate_config(config)
            if errors:
                messagebox.showerror("Validierungsfehler", "\\n".join(errors))
                return
            
            # Speichern
            if self.config_manager.save_configs():
                messagebox.showinfo("Erfolg", "Konfiguration erfolgreich gespeichert!")
                self.update_status("Gespeichert", "success")
                self.config_changed = False
            else:
                messagebox.showerror("Fehler", "Fehler beim Speichern der Konfiguration")
                self.update_status("Speicherfehler", "error")
                
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern: {e}")
            self.update_status("Speicherfehler", "error")
    
    def validate_config(self):
        """Validiert die aktuelle Konfiguration"""
        try:
            config = self.config_manager.fingpt_config
            
            # Konfiguration aus GUI lesen
            config.ollama_url = self.ollama_url_var.get()
            config.selected_model = self.model_var.get() or None
            config.trading_enabled = self.trading_enabled_var.get()
            config.default_lot_size = float(self.lot_size_var.get())
            config.max_risk_percent = float(self.max_risk_var.get())
            config.auto_trading = self.auto_trading_var.get()
            config.auto_trade_symbols = [s.strip() for s in self.symbols_var.get().split(",") if s.strip()]
            config.analysis_interval = int(self.interval_var.get())
            
            config.rsi_period = int(self.rsi_period_var.get())
            config.rsi_overbought = float(self.rsi_overbought_var.get())
            config.rsi_oversold = float(self.rsi_oversold_var.get())
            
            config.macd_fast_period = int(self.macd_fast_var.get())
            config.macd_slow_period = int(self.macd_slow_var.get())
            config.macd_signal_period = int(self.macd_signal_var.get())
            
            config.sr_lookback_period = int(self.sr_lookback_var.get())
            config.sr_min_touches = int(self.sr_touches_var.get())
            config.sr_tolerance = float(self.sr_tolerance_var.get())
            
            # Validieren
            errors = self.config_manager.validate_config(config)
            
            if errors:
                messagebox.showwarning("Validierungsfehler", f"\\n".join(errors))
                self.update_status(f"{len(errors)} Fehler", "error")
            else:
                messagebox.showinfo("Validierung", "Konfiguration ist gültig!")
                self.update_status("Validiert", "success")
                
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler bei der Validierung: {e}")
            self.update_status("Validierungsfehler", "error")
    
    def reset_config(self):
        """Setzt die Konfiguration zurück"""
        if messagebox.askyesno("Zurücksetzen", "Wollen Sie wirklich alle Einstellungen auf Standardwerte zurücksetzen?"):
            if self.config_manager.reset_to_defaults():
                self.load_current_config()
                messagebox.showinfo("Erfolg", "Konfiguration zurückgesetzt!")
                self.update_status("Zurückgesetzt", "success")
            else:
                messagebox.showerror("Fehler", "Fehler beim Zurücksetzen")
                self.update_status("Reset-Fehler", "error")
    
    def import_config(self):
        """Importiert Konfiguration aus Datei"""
        filename = filedialog.askopenfilename(
            title="Konfiguration importieren",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )
        
        if filename:
            if self.config_manager.import_config(filename):
                self.load_current_config()
                messagebox.showinfo("Erfolg", "Konfiguration importiert!")
                self.update_status("Importiert", "success")
            else:
                messagebox.showerror("Fehler", "Fehler beim Importieren")
                self.update_status("Import-Fehler", "error")
    
    def export_config(self):
        """Exportiert Konfiguration in Datei"""
        filename = filedialog.asksaveasfilename(
            title="Konfiguration exportieren",
            defaultextension=".json",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )
        
        if filename:
            if self.config_manager.export_config(filename):
                messagebox.showinfo("Erfolg", "Konfiguration exportiert!")
                self.update_status("Exportiert", "success")
            else:
                messagebox.showerror("Fehler", "Fehler beim Exportieren")
                self.update_status("Export-Fehler", "error")
    
    def refresh_models(self):
        """Aktualisiert die Modell-Liste"""
        def refresh():
            try:
                models = self.config_manager.get_available_models()
                self.model_combo['values'] = models
                self.update_status("Modelle aktualisiert", "success")
            except Exception as e:
                self.update_status("Modell-Fehler", "error")
        
        # In Hintergrundthread ausführen
        threading.Thread(target=refresh, daemon=True).start()
    
    def test_ollama_connection(self):
        """Testet die Ollama-Verbindung"""
        def test():
            try:
                import requests
                url = self.ollama_url_var.get()
                response = requests.get(f"{url}/api/tags", timeout=5)
                
                if response.status_code == 200:
                    self.update_status("Ollama verbunden", "success")
                    messagebox.showinfo("Verbindungstest", "Ollama-Verbindung erfolgreich!")
                else:
                    self.update_status("Ollama Fehler", "error")
                    messagebox.showerror("Verbindungstest", f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.update_status("Verbindungsfehler", "error")
                messagebox.showerror("Verbindungstest", f"Fehler: {e}")
        
        # In Hintergrundthread ausführen
        threading.Thread(target=test, daemon=True).start()
    
    def update_status(self, message: str, status_type: str = "info"):
        """Aktualisiert den Status"""
        self.config_status_label.config(text=message)
        
        if status_type == "success":
            self.config_status_label.config(style='Success.TLabel')
        elif status_type == "error":
            self.config_status_label.config(style='Error.TLabel')
        else:
            self.config_status_label.config(style='TLabel')
    
    def quit_app(self):
        """Beendet die Anwendung"""
        if self.config_changed:
            if messagebox.askyesno("Ungespeicherte Änderungen", 
                                   "Es gibt ungespeicherte Änderungen. Trotzdem beenden?"):
                self.root.quit()
        else:
            self.root.quit()
    
    def run(self):
        """Startet die GUI"""
        self.root.mainloop()


def main():
    """Hauptfunktion"""
    try:
        app = FinGPTConfigGUI()
        app.run()
    except Exception as e:
        print(f"Fehler beim Starten der GUI: {e}")
        messagebox.showerror("Startfehler", f"Fehler beim Starten: {e}")


if __name__ == "__main__":
    main()