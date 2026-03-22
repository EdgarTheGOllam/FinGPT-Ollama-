#!/usr/bin/env python3
"""
Risk Calculator Widget für FinGPT
Berechnet Positionsgröße, Risk/Reward und Risiko-Parameter
"""

import sys
import os
import customtkinter as ctk
from tkinter import messagebox
import threading

# Füge Parent-Directory zum Pfad hinzu für Importe
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class RiskCalculatorWidget(ctk.CTkFrame):
    """Risk Calculator Widget - Berechnet Trading-Risiken und Positionsgrößen"""
    
    def __init__(self, parent, mt5_connection=None, risk_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.mt5_connection = mt5_connection
        self.risk_manager = risk_manager
        
        # Standardwerte
        self.account_balance = 10000.0
        self.risk_percent = 1.0
        self.stop_loss_pips = 20
        self.entry_price = 1.0850
        self.symbol = "EURUSD"
        self.leverage = 100
        
        # Pip-Werte für verschiedene Symboltypen
        self.pip_multipliers = {
            "EURUSD": 0.0001,
            "GBPUSD": 0.0001,
            "USDJPY": 0.01,
            "XAUUSD": 0.01,
            "BTCUSD": 0.01,
            "AUDUSD": 0.0001,
            "USDCAD": 0.0001,
            "USDCHF": 0.0001
        }
        
        self._setup_ui()
        self._load_account_data()
        
    def _setup_ui(self):
        """Richtet die UI-Komponenten ein"""
        
        # Title
        title = ctk.CTkLabel(
            self,
            text="🧮 Risk Calculator",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title.pack(anchor="w", padx=15, pady=(15, 10))
        
        # Main Container mit zwei Spalten
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Linke Seite - Eingabefelder
        input_frame = ctk.CTkFrame(main_container)
        input_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Input Fields
        self._create_input_section(input_frame)
        
        # Rechte Seite - Ergebnisse
        results_frame = ctk.CTkFrame(main_container)
        results_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        self._create_results_section(results_frame)
        
        # Calculate Button
        calc_button = ctk.CTkButton(
            self,
            text="📊 Berechnen",
            command=self.calculate,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        calc_button.pack(fill="x", padx=15, pady=(10, 15))
        
    def _create_input_section(self, parent):
        """Erstellt die Eingabesektion"""
        
        # Account Balance
        self._create_input_row(
            parent,
            "💰 Kontostand:",
            "account_balance",
            "10000",
            "EUR"
        )
        
        # Risk Percent
        self._create_input_row(
            parent,
            "⚠️ Risiko (%):",
            "risk_percent",
            "1.0",
            "%"
        )
        
        # Symbol Selection
        symbol_frame = ctk.CTkFrame(parent, fg_color="transparent")
        symbol_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(symbol_frame, text="📈 Symbol:").pack(side="left")
        
        self.symbol_var = ctk.StringVar(value=self.symbol)
        symbol_menu = ctk.CTkOptionMenu(
            symbol_frame,
            values=list(self.pip_multipliers.keys()),
            variable=self.symbol_var,
            command=self._on_symbol_change,
            width=120
        )
        symbol_menu.pack(side="right")
        
        # Entry Price
        self._create_input_row(
            parent,
            "🎯 Einstiegspreis:",
            "entry_price",
            "1.0850",
            ""
        )
        
        # Stop Loss
        self._create_input_row(
            parent,
            "🛡️ Stop Loss (Pips):",
            "stop_loss",
            "20",
            "pips"
        )
        
        # Take Profit
        self._create_input_row(
            parent,
            "💵 Take Profit (Pips):",
            "take_profit",
            "40",
            "pips"
        )
        
        # Leverage
        leverage_frame = ctk.CTkFrame(parent, fg_color="transparent")
        leverage_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(leverage_frame, text="📊 Hebel:").pack(side="left")
        
        self.leverage_var = ctk.StringVar(value=str(self.leverage))
        leverage_menu = ctk.CTkOptionMenu(
            leverage_frame,
            values=["10", "20", "50", "100", "200", "500"],
            variable=self.leverage_var,
            width=80
        )
        leverage_menu.pack(side="right")
        
    def _create_input_row(self, parent, label_text, var_name, default_value, suffix=""):
        """Erstellt eine Eingabezeile"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(row, text=label_text, width=140, anchor="w").pack(side="left")
        
        entry = ctk.CTkEntry(
            row,
            placeholder_text=default_value,
            width=100,
            font=ctk.CTkFont(family="Consolas")
        )
        entry.insert(0, default_value)
        entry.pack(side="left", padx=5)
        
        if suffix:
            ctk.CTkLabel(row, text=suffix, width=30).pack(side="left")
            
        # Speichere Referenz
        setattr(self, f"{var_name}_entry", entry)
        
    def _create_results_section(self, parent):
        """Erstellt die Ergebnissection"""
        
        # Title
        ctk.CTkLabel(
            parent,
            text="📋 Ergebnisse",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 10))
        
        # Results Container
        results_container = ctk.CTkFrame(parent, fg_color="transparent")
        results_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Lot Size
        self.lot_result = self._create_result_row(
            results_container,
            "📦 Lot Größe:",
            "0.00",
            "lots"
        )
        
        # Risk Amount
        self.risk_amount_result = self._create_result_row(
            results_container,
            "💸 Risiko Betrag:",
            "0.00",
            "EUR"
        )
        
        # Potential Profit
        self.profit_result = self._create_result_row(
            results_container,
            "💰 Potentialer Gewinn:",
            "0.00",
            "EUR"
        )
        
        # Risk/Reward Ratio
        self.rr_result = self._create_result_row(
            results_container,
            "⚖️ Risk/Reward:",
            "1:1.0",
            ""
        )
        
        # Required Margin
        self.margin_result = self._create_result_row(
            results_container,
            "🔒 Benötigte Margin:",
            "0.00",
            "EUR"
        )
        
        # Separator
        separator = ctk.CTkFrame(parent, height=2, fg_color="#444444")
        separator.pack(fill="x", padx=15, pady=10)
        
        # Quick Info Section
        info_frame = ctk.CTkFrame(parent, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        # Account at Risk
        self.account_risk_info = ctk.CTkLabel(
            info_frame,
            text="Konto-Risiko: 0%",
            font=ctk.CTkFont(size=11),
            text_color="#F39C12"
        )
        self.account_risk_info.pack(anchor="w")
        
        # Position Value
        self.position_value_info = ctk.CTkLabel(
            info_frame,
            text="Positionswert: 0 EUR",
            font=ctk.CTkFont(size=11)
        )
        self.position_value_info.pack(anchor="w")
        
    def _create_result_row(self, parent, label_text, default_value, suffix=""):
        """Erstellt eine Ergebniszeile"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        
        ctk.CTkLabel(
            row,
            text=label_text,
            font=ctk.CTkFont(size=12),
            anchor="w"
        ).pack(side="left")
        
        value_label = ctk.CTkLabel(
            row,
            text=default_value,
            font=ctk.CTkFont(size=14, weight="bold", family="Consolas"),
            text_color="#3498DB",
            anchor="e"
        )
        value_label.pack(side="right")
        
        if suffix:
            ctk.CTkLabel(
                row,
                text=suffix,
                font=ctk.CTkFont(size=11),
                anchor="e",
                width=50
            ).pack(side="right", padx=(5, 0))
            
        return value_label
        
    def _on_symbol_change(self, symbol):
        """Wird aufgerufen wenn Symbol geändert wird"""
        self.symbol = symbol
        # Update entry price with reasonable default
        default_prices = {
            "EURUSD": "1.0850",
            "GBPUSD": "1.2650",
            "USDJPY": "149.50",
            "XAUUSD": "2025.00",
            "BTCUSD": "42500.00",
            "AUDUSD": "0.6550",
            "USDCAD": "1.3550",
            "USDCHF": "0.8850"
        }
        
        if hasattr(self, 'entry_price_entry'):
            self.entry_price_entry.delete(0, "end")
            self.entry_price_entry.insert(0, default_prices.get(symbol, "1.0000"))
            
        self.calculate()
        
    def _load_account_data(self):
        """Lädt Kontodaten (oder verwendet Standardwerte)"""
        # Hier würde echte MT5-Verbindung genutzt
        # Für jetzt: Standardwerte
        self.calculate()
        
    def calculate(self):
        """Führt die Berechnungen durch"""
        try:
            # Hole Eingabewerte
            account_balance = float(self.account_balance_entry.get())
            risk_percent = float(self.risk_percent_entry.get())
            stop_loss = float(self.stop_loss_entry.get())
            take_profit = float(self.take_profit_entry.get())
            entry_price = float(self.entry_price_entry.get())
            leverage = int(self.leverage_var.get())
            symbol = self.symbol_var.get()
            
            # Berechne Pip-Wert
            pip_multiplier = self.pip_multipliers.get(symbol, 0.0001)
            
            # Risiko-Betrag in Account-Währung
            risk_amount = account_balance * (risk_percent / 100)
            
            # Lot-Größe berechnen
            # Lot = Risk Amount / (Stop Loss Pips * Pip Value per Lot)
            # pip_value_per_lot = 10 für Forex (1 Standard Lot = 100,000 units)
            pip_value_per_lot = 10  # Für Standard-Lot
            
            # Adjust für Pip-Größe bei Nicht-Forex
            if symbol in ["XAUUSD", "BTCUSD"]:
                pip_value_per_lot = 1  # Gold, BTC haben unterschiedliche Pip-Werte
                
            lot_size = risk_amount / (stop_loss * pip_value_per_lot)
            
            # Runde auf 2 Dezimalstellen
            lot_size = round(lot_size, 2)
            
            # Begrenzung auf sinnvolle Werte
            lot_size = max(0.01, min(lot_size, 100.0))
            
            # Potentialer Gewinn
            profit_pips = take_profit - stop_loss
            potential_profit = (profit_pips / stop_loss) * risk_amount
            potential_profit = round(potential_profit, 2)
            
            # Risk/Reward Ratio
            rr_ratio = take_profit / stop_loss if stop_loss > 0 else 0
            rr_text = f"1:{rr_ratio:.1f}"
            
            # Required Margin
            # Margin = Lot Size * Contract Size / Leverage
            contract_size = 100000  # Standard für Forex
            if symbol in ["XAUUSD"]:
                contract_size = 100  # Gold
            elif symbol in ["BTCUSD"]:
                contract_size = 1  # BTC
                
            required_margin = (lot_size * contract_size) / leverage
            required_margin = round(required_margin, 2)
            
            # Additional Info
            account_risk_percent = risk_percent
            position_value = lot_size * contract_size
            
            # Update Results
            self.lot_result.configure(text=f"{lot_size:.2f}")
            self.risk_amount_result.configure(
                text=f"{risk_amount:.2f}",
                text_color="#E74C3C"  # Rot für Risiko
            )
            self.profit_result.configure(
                text=f"+{potential_profit:.2f}",
                text_color="#27AE60"  # Grün für Profit
            )
            self.rr_result.configure(text=rr_text)
            self.margin_result.configure(text=f"{required_margin:.2f}")
            
            # Info Labels
            self.account_risk_info.configure(
                text=f"Konto-Risiko: {account_risk_percent}%"
            )
            self.position_value_info.configure(
                text=f"Positionswert: {position_value:,.0f} EUR"
            )
            
            # Risk/Reward Color Coding
            if rr_ratio >= 2.0:
                self.rr_result.configure(text_color="#27AE60")  # Gut
            elif rr_ratio >= 1.5:
                self.rr_result.configure(text_color="#F39C12")  # Okay
            else:
                self.rr_result.configure(text_color="#E74C3C")  # Schlecht
                
        except Exception as e:
            print(f"Calculation Error: {e}")
            messagebox.showerror("Fehler", f"Berechnungsfehler: {e}")
            
    def set_risk_manager(self, risk_manager):
        """Setzt den Risk Manager"""
        self.risk_manager = risk_manager
        
    def set_mt5_connection(self, mt5_connection):
        """Setzt die MT5-Verbidnung"""
        self.mt5_connection = mt5_connection


class QuickTradeWidget(ctk.CTkFrame):
    """Quick Trade Widget - Schnelles Öffnen von Trades"""
    
    def __init__(self, parent, mt5_broker=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.mt5_broker = mt5_broker
        self._setup_ui()
        
    def _setup_ui(self):
        """UI-Einrichtung"""
        
        # Title
        ctk.CTkLabel(
            self,
            text="⚡ Quick Trade",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))
        
        # Symbol
        symbol_frame = ctk.CTkFrame(self, fg_color="transparent")
        symbol_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(symbol_frame, text="📈 Symbol:", width=100, anchor="w").pack(side="left")
        
        self.symbol_var = ctk.StringVar(value="EURUSD")
        symbol_menu = ctk.CTkOptionMenu(
            symbol_frame,
            values=["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"],
            variable=self.symbol_var,
            width=120
        )
        symbol_menu.pack(side="right")
        
        # Lot Size
        lot_frame = ctk.CTkFrame(self, fg_color="transparent")
        lot_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(lot_frame, text="📦 Lot:", width=100, anchor="w").pack(side="left")
        
        self.lot_entry = ctk.CTkEntry(
            lot_frame,
            placeholder_text="0.10",
            width=120
        )
        self.lot_entry.insert(0, "0.10")
        self.lot_entry.pack(side="right")
        
        # Stop Loss Pips
        sl_frame = ctk.CTkFrame(self, fg_color="transparent")
        sl_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(sl_frame, text="🛡️ SL (Pips):", width=100, anchor="w").pack(side="left")
        
        self.sl_entry = ctk.CTkEntry(
            sl_frame,
            placeholder_text="20",
            width=120
        )
        self.sl_entry.insert(0, "20")
        self.sl_entry.pack(side="right")
        
        # Take Profit Pips
        tp_frame = ctk.CTkFrame(self, fg_color="transparent")
        tp_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(tp_frame, text="💵 TP (Pips):", width=100, anchor="w").pack(side="left")
        
        self.tp_entry = ctk.CTkEntry(
            tp_frame,
            placeholder_text="40",
            width=120
        )
        self.tp_entry.insert(0, "40")
        self.tp_entry.pack(side="right")
        
        # Buttons
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        # Buy Button
        buy_btn = ctk.CTkButton(
            buttons_frame,
            text="🟢 KAUFEN",
            fg_color="#27AE60",
            hover_color="#219A52",
            height=40,
            command=self.buy
        )
        buy_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Sell Button
        sell_btn = ctk.CTkButton(
            buttons_frame,
            text="🔴 VERKAUFEN",
            fg_color="#E74C3C",
            hover_color="#C0392B",
            height=40,
            command=self.sell
        )
        sell_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        # Status Label
        self.status_label = ctk.CTkLabel(
            self,
            text="Bereit",
            font=ctk.CTkFont(size=11)
        )
        self.status_label.pack(pady=(5, 10))
        
    def buy(self):
        """Führt einen Kauf-Trade aus"""
        self._execute_trade("BUY")
        
    def sell(self):
        """Führt einen Verkaufs-Trade aus"""
        self._execute_trade("SELL")
        
    def _execute_trade(self, action):
        """Führt den Trade aus"""
        try:
            symbol = self.symbol_var.get()
            lot = float(self.lot_entry.get())
            sl_pips = float(self.sl_entry.get())
            tp_pips = float(self.tp_entry.get())
            
            # Berechne SL und TP Preise (vereinfacht)
            # In echter Implementation: MT5 Preise nutzen
            entry_estimate = 1.0850  # Placeholder
            
            pip_size = 0.0001
            if symbol in ["XAUUSD", "BTCUSD"]:
                pip_size = 0.01
                
            if action == "BUY":
                sl_price = entry_estimate - (sl_pips * pip_size)
                tp_price = entry_estimate + (tp_pips * pip_size)
            else:
                sl_price = entry_estimate + (sl_pips * pip_size)
                tp_price = entry_estimate - (tp_pips * pip_size)
            
            self.status_label.configure(
                text=f"📤 {action} Order gesendet...",
                text_color="#3498DB"
            )
            
            # Hier würde echter Trade ausgeführt
            # if self.mt5_broker:
            #     result = self.mt5_broker.execute_trade(symbol, action, lot, sl_price, tp_price)
            
            # Simulation
            self.after(1000, lambda: self.status_label.configure(
                text=f"✅ {action} Order ausgeführt!",
                text_color="#27AE60"
            ))
            
        except Exception as e:
            self.status_label.configure(
                text=f"❌ Fehler: {e}",
                text_color="#E74C3C"
            )
            
    def set_mt5_broker(self, mt5_broker):
        """Setzt den MT5 Broker"""
        self.mt5_broker = mt5_broker


if __name__ == "__main__":
    # Test des Widgets
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    root.title("Risk Calculator Test")
    root.geometry("500x600")
    
    # Risk Calculator
    risk_calc = RiskCalculatorWidget(root)
    risk_calc.pack(fill="both", expand=True, padx=10, pady=10)
    
    root.mainloop()
