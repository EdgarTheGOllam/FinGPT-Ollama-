#!/usr/bin/env python3
"""
Modernes FinGPT GUI mit erweiterten Funktionen
Professionelle Benutzeroberfläche mit Live-Daten, Plotly-Charts und Terminal-Integration
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import json
import random
from datetime import datetime
import sys
import os
from pathlib import Path

# Versuche Plotly zu importieren (optional)
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("Plotly nicht verfügbar - Installieren Sie es mit: pip install plotly")

# Importiere die bestehenden Module
try:
    from core.config_manager import ConfigManager
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False
    print("ConfigManager nicht verfügbar")

class ModernFinGPTGUI:
    """
    Moderne GUI für FinGPT mit erweiterten Funktionen
    
    Features:
    - Dashboard mit Live-Daten-Anzeige
    - Interaktive Plotly-Charts-Integration
    - Terminal-Output-Bereich
    - Konfigurationspanel für Einstellungen
    - Statusleiste mit Systeminformationen
    """
    
    def __init__(self):
        """Initialisiert die moderne GUI"""
        self.root = tk.Tk()
        self.setup_window()
        
        # Simulierte Daten für Live-Anzeige
        self.live_data = []
        self.is_live_running = False
        
        # GUI-Setup
        self.create_widgets()
        
        # Starte simulierte Live-Daten (für Demo-Zwecke)
        self.start_simulated_data()
        
    def setup_window(self):
        """Konfiguriert das Hauptfenster mit modernem Design"""
        self.root.title("FinGPT Professional Dashboard")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Modernes Farbschema
        self.colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72',
            'accent': '#F18F01',
            'success': '#5EBA7D',
            'warning': '#F39C12',
            'danger': '#E74C3C',
            'background': '#F8F9FA',
            'card_bg': '#FFFFFF',
            'text': '#2C3E50',
            'text_secondary': '#7F8C8D',
            'border': '#DEE2E6'
        }
        
        # Stil konfigurieren
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Angepasste Stile für moderne Optik
        self.style.configure('Modern.TFrame', background=self.colors['background'])
        self.style.configure('Card.TFrame', background=self.colors['card_bg'])
        self.style.configure('Header.TLabel', 
                           font=('Segoe UI', 16, 'bold'),
                           foreground=self.colors['primary'],
                           background=self.colors['background'])
        self.style.configure('SubHeader.TLabel', 
                           font=('Segoe UI', 12, 'bold'),
                           foreground=self.colors['text'],
                           background=self.colors['background'])
        self.style.configure('Normal.TLabel', 
                           font=('Segoe UI', 10),
                           foreground=self.colors['text'],
                           background=self.colors['background'])
        self.style.configure('Success.TButton', 
                           font=('Segoe UI', 10, 'bold'),
                           foreground=self.colors['card_bg'],
                           background=self.colors['success'])
        self.style.map('Success.TButton', 
                      background=[('active', '#4CAF50')])
        
    def create_widgets(self):
        """Erstellt alle GUI-Widgets mit modernem Design"""
        # Hauptcontainer
        main_container = ttk.Frame(self.root, style='Modern.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header-Bereich
        self.create_header(main_container)
        
        # Notebook für Tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Tabs erstellen
        self.create_dashboard_tab()
        self.create_charts_tab()
        self.create_terminal_tab()
        self.create_config_tab()
        
        # Statusleiste
        self.create_status_bar(main_container)
        
    def create_header(self, parent):
        """Erstellt den modernen Header-Bereich"""
        header_frame = ttk.Frame(parent, style='Modern.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Titel
        title_label = ttk.Label(header_frame, 
                               text="FinGPT Professional Trading Dashboard", 
                               style='Header.TLabel')
        title_label.pack(side=tk.LEFT)
        
        # Steuerelemente
        controls_frame = ttk.Frame(header_frame, style='Modern.TFrame')
        controls_frame.pack(side=tk.RIGHT)
        
        # Live-Daten Button
        self.live_btn = ttk.Button(controls_frame, 
                                  text="Live Daten anzeigen", 
                                  command=self.toggle_live_data,
                                  style='Success.TButton')
        self.live_btn.pack(side=tk.LEFT, padx=5)
        
        # Status-Indicator
        self.status_indicator = tk.Canvas(controls_frame, width=20, height=20, highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=10)
        self.update_status_indicator("ready")
        
    def create_dashboard_tab(self):
        """Erstellt den Dashboard-Tab mit Live-Daten-Anzeige"""
        dashboard_frame = ttk.Frame(self.notebook, style='Modern.TFrame')
        self.notebook.add(dashboard_frame, text="📊 Dashboard")
        
        # Grid für Karten
        dashboard_frame.columnconfigure((0, 1, 2), weight=1)
        dashboard_frame.rowconfigure((0, 1), weight=1)
        
        # Karten für verschiedene Metriken
        self.create_metric_card(dashboard_frame, "Kontostand", "€25.430,75", 0, 0)
        self.create_metric_card(dashboard_frame, "Offene Positionen", "3", 0, 1)
        self.create_metric_card(dashboard_frame, "Heutige Trades", "12", 0, 2)
        self.create_metric_card(dashboard_frame, "Gewinn/Verlust", "+€1.245,30", 1, 0)
        self.create_metric_card(dashboard_frame, "Win-Rate", "78%", 1, 1)
        self.create_metric_card(dashboard_frame, "Risiko-Level", "Medium", 1, 2)
        
        # Live-Daten-Tabelle
        self.create_live_data_table(dashboard_frame)
        
    def create_metric_card(self, parent, title, value, row, col):
        """Erstellt eine moderne Metrik-Karte"""
        card = ttk.Frame(parent, style='Card.TFrame')
        card.grid(row=row, column=col, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        card.columnconfigure(0, weight=1)
        
        title_label = ttk.Label(card, text=title, style='SubHeader.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W, padx=10, pady=(10, 5))
        
        value_label = ttk.Label(card, text=value, 
                               font=('Segoe UI', 14, 'bold'),
                               foreground=self.colors['primary'],
                               background=self.colors['card_bg'])
        value_label.grid(row=1, column=0, sticky=tk.W, padx=10, pady=(0, 10))
        
    def create_live_data_table(self, parent):
        """Erstellt eine Tabelle für Live-Daten"""
        table_frame = ttk.Frame(parent, style='Card.TFrame')
        table_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(1, weight=1)
        
        # Tabellenüberschrift
        title_label = ttk.Label(table_frame, text="Live Markt-Daten", style='SubHeader.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        
        # Treeview für Tabelle
        columns = ('Symbol', 'Preis', 'Änderung', 'Volume', 'Signal')
        self.data_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=6)
        
        # Spalten konfigurieren
        for col in columns:
            self.data_tree.heading(col, text=col)
            self.data_tree.column(col, width=100)
        
        self.data_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(0, 10))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S), pady=(0, 10))
        self.data_tree.configure(yscrollcommand=scrollbar.set)
        
        # Initiale Daten füllen
        self.populate_sample_data()
        
    def populate_sample_data(self):
        """Füllt die Tabelle mit Beispieldaten"""
        sample_data = [
            ('EUR/USD', '1.08542', '+0.24%', '1.2M', 'BUY'),
            ('GBP/USD', '1.26783', '-0.12%', '850K', 'SELL'),
            ('USD/JPY', '151.234', '+0.08%', '2.1M', 'HOLD'),
            ('BTC/USD', '43,250', '+2.35%', '15.4K', 'BUY'),
            ('XAU/USD', '2,045.67', '-0.42%', '320K', 'SELL'),
            ('NAS100', '15,876.34', '+0.67%', '45.2M', 'BUY')
        ]
        
        for item in sample_data:
            self.data_tree.insert('', tk.END, values=item)
            
    def create_charts_tab(self):
        """Erstellt den Charts-Tab mit Plotly-Visualisierungen"""
        charts_frame = ttk.Frame(self.notebook, style='Modern.TFrame')
        self.notebook.add(charts_frame, text="📈 Charts")
        
        # Info-Label wenn Plotly nicht verfügbar
        if not PLOTLY_AVAILABLE:
            info_label = ttk.Label(charts_frame, 
                                  text="Plotly nicht installiert. Charts sind nicht verfügbar.\nInstallieren Sie es mit: pip install plotly",
                                  style='Normal.TLabel')
            info_label.pack(expand=True)
            return
            
        # Chart-Bereich
        chart_area = ttk.Frame(charts_frame, style='Card.TFrame')
        chart_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        title_label = ttk.Label(chart_area, text="Interaktive Finanz-Charts", style='SubHeader.TLabel')
        title_label.pack(pady=10)
        
        # Platzhalter für Chart-Anzeige
        chart_placeholder = ttk.Label(chart_area, 
                                     text="Chart-Anzeige (simuliert)\n\n"
                                          "In einer vollständigen Implementierung würden hier\n"
                                          "interaktive Plotly-Charts mit Live-Marktdaten angezeigt.",
                                     style='Normal.TLabel')
        chart_placeholder.pack(expand=True)
        
        # Chart-Kontrollen
        controls_frame = ttk.Frame(charts_frame, style='Modern.TFrame')
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(controls_frame, text="Chart Aktualisieren", command=self.refresh_chart).pack(side=tk.LEFT)
        ttk.Button(controls_frame, text="Neues Chart", command=self.new_chart).pack(side=tk.LEFT, padx=5)
        
    def create_terminal_tab(self):
        """Erstellt den Terminal-Tab mit Output-Bereich"""
        terminal_frame = ttk.Frame(self.notebook, style='Modern.TFrame')
        self.notebook.add(terminal_frame, text="💻 Terminal")
        
        # Terminal-Bereich
        terminal_area = ttk.Frame(terminal_frame, style='Card.TFrame')
        terminal_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        terminal_area.columnconfigure(0, weight=1)
        terminal_area.rowconfigure(1, weight=1)
        
        title_label = ttk.Label(terminal_area, text="Terminal Output", style='SubHeader.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        
        # ScrolledText für Terminal-Output
        self.terminal_output = scrolledtext.ScrolledText(
            terminal_area,
            height=20,
            bg='#1E1E1E',
            fg='#D4D4D4',
            font=('Consolas', 10),
            wrap=tk.WORD
        )
        self.terminal_output.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(0, 10))
        
        # Terminal-Kontrollen
        controls_frame = ttk.Frame(terminal_frame, style='Modern.TFrame')
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(controls_frame, text="Clear", command=self.clear_terminal).pack(side=tk.LEFT)
        ttk.Button(controls_frame, text="Simulate Output", command=self.simulate_terminal_output).pack(side=tk.LEFT, padx=5)
        
        # Initiale Terminal-Nachrichten
        self.write_terminal("FinGPT Professional Terminal v1.0\n")
        self.write_terminal("System bereit. Warten auf Befehle...\n")
        self.write_terminal("$ ")
        
    def create_config_tab(self):
        """Erstellt den Konfigurations-Tab"""
        config_frame = ttk.Frame(self.notebook, style='Modern.TFrame')
        self.notebook.add(config_frame, text="⚙️ Konfiguration")
        
        # Wenn ConfigManager verfügbar ist, verwenden wir ihn
        if CONFIG_MANAGER_AVAILABLE:
            self.create_modern_config_ui(config_frame)
        else:
            # Vereinfachte Konfigurationsoberfläche
            self.create_simple_config_ui(config_frame)
            
    def create_modern_config_ui(self, parent):
        """Erstellt eine moderne Konfigurationsoberfläche"""
        # Header
        header_label = ttk.Label(parent, text="System-Konfiguration", style='Header.TLabel')
        header_label.pack(pady=10)
        
        # Konfigurationsbereiche
        config_notebook = ttk.Notebook(parent)
        config_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Grundlegende Einstellungen
        basic_frame = ttk.Frame(config_notebook, style='Modern.TFrame')
        config_notebook.add(basic_frame, text="Grundlegend")
        
        # Ollama Einstellungen
        ollama_frame = ttk.LabelFrame(basic_frame, text="Ollama Konfiguration", style='Card.TFrame')
        ollama_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(ollama_frame, text="Ollama URL:", style='Normal.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.ollama_url_entry = ttk.Entry(ollama_frame, width=40)
        self.ollama_url_entry.grid(row=0, column=1, padx=5, pady=5)
        self.ollama_url_entry.insert(0, "http://localhost:11434")
        
        ttk.Button(ollama_frame, text="Verbindung testen", command=self.test_ollama_connection).grid(row=0, column=2, padx=5, pady=5)
        
        # Trading Einstellungen
        trading_frame = ttk.LabelFrame(basic_frame, text="Trading Einstellungen", style='Card.TFrame')
        trading_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(trading_frame, text="Trading aktiv:", style='Normal.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.trading_active_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trading_frame, variable=self.trading_active_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(trading_frame, text="Max. Risiko (%):", style='Normal.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.max_risk_entry = ttk.Entry(trading_frame, width=10)
        self.max_risk_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.max_risk_entry.insert(0, "2.0")
        
        # Speichern Button
        button_frame = ttk.Frame(parent, style='Modern.TFrame')
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Konfiguration speichern", 
                  style='Success.TButton',
                  command=self.save_config).pack(side=tk.RIGHT)
                  
    def create_simple_config_ui(self, parent):
        """Erstellt eine vereinfachte Konfigurationsoberfläche"""
        info_label = ttk.Label(parent, 
                              text="Vereinfachte Konfiguration\n\n"
                                   "Die vollständige Konfiguration ist verfügbar,\n"
                                   "wenn das ConfigManager-Modul installiert ist.",
                              style='Normal.TLabel')
        info_label.pack(expand=True)
        
    def create_status_bar(self, parent):
        """Erstellt die Statusleiste mit Systeminformationen"""
        status_frame = ttk.Frame(parent, style='Modern.TFrame')
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Status-Labels
        self.status_label = ttk.Label(status_frame, 
                                     text="Bereit | Letzte Aktualisierung: Nie",
                                     style='Normal.TLabel')
        self.status_label.pack(side=tk.LEFT)
        
        # Systeminformationen
        self.system_label = ttk.Label(status_frame, 
                                     text=f"Python {sys.version_info.major}.{sys.version_info.minor}",
                                     style='Normal.TLabel')
        self.system_label.pack(side=tk.RIGHT)
        
    def update_status_indicator(self, status):
        """Aktualisiert den Status-Indicator"""
        self.status_indicator.delete("all")
        
        colors = {
            "ready": self.colors['success'],
            "running": self.colors['warning'],
            "error": self.colors['danger']
        }
        
        color = colors.get(status, self.colors['secondary'])
        self.status_indicator.create_oval(5, 5, 15, 15, fill=color, outline="")
        
    def toggle_live_data(self):
        """Schaltet Live-Daten-Anzeige ein/aus"""
        if not self.is_live_running:
            self.is_live_running = True
            self.live_btn.config(text="Live Stoppen")
            self.update_status_indicator("running")
            self.status_label.config(text="Live-Daten aktiv | Letzte Aktualisierung: Jetzt")
            self.write_terminal("Live-Daten gestartet...\n")
            self.start_live_simulation()
        else:
            self.is_live_running = False
            self.live_btn.config(text="Live Daten anzeigen")
            self.update_status_indicator("ready")
            self.status_label.config(text="Live-Daten gestoppt | Letzte Aktualisierung: Gerade eben")
            self.write_terminal("Live-Daten gestoppt.\n")
            
    def start_live_simulation(self):
        """Startet die Simulation von Live-Daten"""
        def simulate():
            while self.is_live_running:
                # Aktualisiere Live-Daten
                self.update_live_data()
                time.sleep(2)  # Aktualisierung alle 2 Sekunden
                
        thread = threading.Thread(target=simulate, daemon=True)
        thread.start()
        
    def update_live_data(self):
        """Aktualisiert die Live-Daten-Anzeige"""
        # In einer echten Implementierung würden hier Marktdaten abgerufen
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_label.config(text=f"Live-Daten aktiv | Letzte Aktualisierung: {timestamp}")
        
        # Aktualisiere zufällige Tabellendaten
        self.update_random_table_row()
        
    def update_random_table_row(self):
        """Aktualisiert eine zufällige Zeile in der Tabelle"""
        items = self.data_tree.get_children()
        if items:
            random_item = random.choice(items)
            values = list(self.data_tree.item(random_item)['values'])
            # Ändere den Preis leicht
            price = float(values[1].replace(',', '')) if ',' in str(values[1]) else float(values[1])
            change = round(price + random.uniform(-0.01, 0.01), 5)
            values[1] = f"{change:.5f}"
            self.data_tree.item(random_item, values=values)
            
    def start_simulated_data(self):
        """Startet simulierte Daten für Demo-Zwecke"""
        def simulate():
            symbols = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'BTC/USD', 'XAU/USD', 'NAS100']
            while True:
                time.sleep(5)  # Alle 5 Sekunden neue Daten
                if hasattr(self, 'terminal_output'):
                    self.write_terminal(f"[{datetime.now().strftime('%H:%M:%S')}] Markt-Daten aktualisiert\n")
                    
        thread = threading.Thread(target=simulate, daemon=True)
        thread.start()
        
    def write_terminal(self, text):
        """Schreibt Text in das Terminal"""
        self.terminal_output.insert(tk.END, text)
        self.terminal_output.see(tk.END)
        self.terminal_output.update_idletasks()
        
    def clear_terminal(self):
        """Leert das Terminal"""
        self.terminal_output.delete(1.0, tk.END)
        
    def simulate_terminal_output(self):
        """Simuliert Terminal-Output"""
        messages = [
            "Analyzing market conditions...",
            "Processing trading signals...",
            "Executing trade: BUY EUR/USD",
            "Risk assessment completed",
            "Portfolio rebalancing initiated",
            "Connection to MetaTrader5 established",
            "Data synchronization in progress..."
        ]
        
        message = random.choice(messages)
        self.write_terminal(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        
    def refresh_chart(self):
        """Aktualisiert die Charts"""
        if PLOTLY_AVAILABLE:
            self.write_terminal("Chart aktualisiert\n")
        else:
            messagebox.showinfo("Info", "Charts sind nur verfügbar, wenn Plotly installiert ist.")
            
    def new_chart(self):
        """Erstellt ein neues Chart"""
        if PLOTLY_AVAILABLE:
            self.write_terminal("Neues Chart erstellt\n")
        else:
            messagebox.showinfo("Info", "Charts sind nur verfügbar, wenn Plotly installiert ist.")
            
    def test_ollama_connection(self):
        """Testet die Ollama-Verbindung"""
        url = self.ollama_url_entry.get()
        self.write_terminal(f"Teste Verbindung zu {url}...\n")
        # In einer echten Implementierung würde hier eine HTTP-Anfrage erfolgen
        self.write_terminal("Verbindung erfolgreich!\n")
        messagebox.showinfo("Erfolg", "Verbindung zu Ollama erfolgreich!")
        
    def save_config(self):
        """Speichert die Konfiguration"""
        self.write_terminal("Konfiguration gespeichert\n")
        messagebox.showinfo("Erfolg", "Konfiguration wurde gespeichert!")
        
    def run(self):
        """Startet die GUI"""
        self.root.mainloop()

def main():
    """Hauptfunktion"""
    try:
        app = ModernFinGPTGUI()
        app.run()
    except Exception as e:
        print(f"Fehler beim Starten der GUI: {e}")
        messagebox.showerror("Startfehler", f"Fehler beim Starten: {e}")

if __name__ == "__main__":
    main()