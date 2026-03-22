#!/usr/bin/env python3
"""
Order Book Widget für FinGPT
Zeigt aktuelle Buy/Sell Orders und Markttiefe
"""

import sys
import os
import customtkinter as ctk
from datetime import datetime
import threading

# Füge Parent-Directory zum Pfad hinzu für Importe
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class OrderBookWidget(ctk.CTkFrame):
    """Order Book Widget - Zeigt Markttiefe und aktuelle Orders"""
    
    def __init__(self, parent, mt5_connection=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.mt5_connection = mt5_connection
        self.update_thread = None
        self.stop_update = False
        self.current_symbol = "EURUSD"
        
        # Farben für das Order Book
        self.buy_color = "#27AE60"   # Grün für Käufe
        self.sell_color = "#E74C3C"  # Rot für Verkäufe
        self.neutral_color = "#6C757D"
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Richtet die UI-Komponenten ein"""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.title_label = ctk.CTkLabel(
            header_frame,
            text="📊 Order Book",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title_label.pack(side="left")
        
        # Symbol Selector
        self.symbol_var = ctk.StringVar(value=self.current_symbol)
        symbol_menu = ctk.CTkOptionMenu(
            header_frame,
            values=["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD", "AUDUSD", "USDCAD"],
            variable=self.symbol_var,
            command=self._on_symbol_change,
            width=100
        )
        symbol_menu.pack(side="right")
        
        # Main Content Frame
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Column Headers
        headers = ctk.CTkFrame(content_frame, fg_color="transparent")
        headers.pack(fill="x", padx=5, pady=(5, 0))
        
        ctk.CTkLabel(headers, text="Volumen", width=80, anchor="w").pack(side="left")
        ctk.CTkLabel(headers, text="Preis", width=100, anchor="center").pack(side="left")
        ctk.CTkLabel(headers, text="Zeit", width=80, anchor="e").pack(side="right")
        
        # Order Lists Container
        lists_container = ctk.CTkFrame(content_frame, fg_color="transparent")
        lists_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Sell Orders (Above - Red)
        sell_frame = ctk.CTkFrame(lists_container, fg_color="transparent")
        sell_frame.pack(fill="x", pady=(0, 2))
        
        ctk.CTkLabel(
            sell_frame, 
            text="🔴 SELL Orders", 
            text_color=self.sell_color,
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", pady=(0, 2))
        
        self.sell_orders_container = ctk.CTkFrame(sell_frame, fg_color=("#2B2B2B", "#1E1E1E"))
        self.sell_orders_container.pack(fill="x")
        
        # Current Price
        price_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        price_frame.pack(fill="x", padx=5, pady=5)
        
        self.current_price_label = ctk.CTkLabel(
            price_frame,
            text="1.08500",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#3498DB"
        )
        self.current_price_label.pack()
        
        # Spread Label
        self.spread_label = ctk.CTkLabel(
            price_frame,
            text="Spread: 1.0 Pips",
            font=ctk.CTkFont(size=11)
        )
        self.spread_label.pack()
        
        # Buy Orders (Below - Green)
        buy_frame = ctk.CTkFrame(lists_container, fg_color="transparent")
        buy_frame.pack(fill="x", pady=(2, 0))
        
        ctk.CTkLabel(
            buy_frame, 
            text="🟢 BUY Orders", 
            text_color=self.buy_color,
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", pady=(0, 2))
        
        self.buy_orders_container = ctk.CTkFrame(buy_frame, fg_color=("#2B2B2B", "#1E1E1E"))
        self.buy_orders_container.pack(fill="x")
        
        # Status Bar
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        self.status_indicator = ctk.CTkLabel(
            status_frame,
            text="●",
            text_color="#27AE60",
            font=ctk.CTkFont(size=14)
        )
        self.status_indicator.pack(side="left")
        
        self.last_update_label = ctk.CTkLabel(
            status_frame,
            text="Letzte Aktualisierung: --:--:--",
            font=ctk.CTkFont(size=10)
        )
        self.last_update_label.pack(side="right")
        
        # Sample Data anzeigen
        self._show_sample_data()
        
    def _on_symbol_change(self, symbol):
        """Wird aufgerufen wenn Symbol geändert wird"""
        self.current_symbol = symbol
        self._show_sample_data()
        
    def _show_sample_data(self):
        """Zeigt Beispieldaten (falls MT5 nicht verbunden)"""
        # Clear existing
        for widget in self.sell_orders_container.winfo_children():
            widget.destroy()
        for widget in self.buy_orders_container.winfo_children():
            widget.destroy()
            
        # Sample Prices basierend auf Symbol
        base_prices = {
            "EURUSD": 1.0850,
            "GBPUSD": 1.2650,
            "USDJPY": 149.50,
            "XAUUSD": 2025.00,
            "BTCUSD": 42500.00,
            "AUDUSD": 0.6550,
            "USDCAD": 1.3550
        }
        
        base_price = base_prices.get(self.current_symbol, 1.0850)
        
        # Generate sample SELL orders (asks - above price)
        for i in range(5):
            price = base_price + (i + 1) * 0.0001 if self.current_symbol not in ["XAUUSD", "BTCUSD", "USDJPY"] else base_price + (i + 1) * (0.5 if self.current_symbol == "XAUUSD" else 0.1)
            volume = 0.5 + (i * 0.25)
            self._add_order_row(self.sell_orders_container, volume, price, self.sell_color, is_sell=True)
            
        # Generate sample BUY orders (bids - below price)
        for i in range(5):
            price = base_price - (i + 1) * 0.0001 if self.current_symbol not in ["XAUUSD", "BTCUSD", "USDJPY"] else base_price - (i + 1) * (0.5 if self.current_symbol == "XAUUSD" else 0.1)
            volume = 0.5 + (i * 0.25)
            self._add_order_row(self.buy_orders_container, volume, price, self.buy_color, is_sell=False)
            
        # Update current price display
        self.current_price_label.configure(text=f"{base_price:.5f}" if base_price < 100 else f"{base_price:.2f}")
        
        # Update spread
        spread_pips = 1.0
        self.spread_label.configure(text=f"Spread: {spread_pips:.1f} Pips")
        
        # Update timestamp
        self.last_update_label.configure(text=f"Letzte Aktualisierung: {datetime.now().strftime('%H:%M:%S')}")
        
    def _add_order_row(self, parent, volume, price, color, is_sell=True):
        """Fügt eine Order-Zeile hinzu"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=1)
        
        # Volume Bar (visual representation)
        bar_width = min(int(volume * 30), 120)
        
        volume_label = ctk.CTkLabel(
            row,
            text=f"{volume:.2f}",
            width=80,
            anchor="w",
            font=ctk.CTkFont(size=11, family="Consolas")
        )
        volume_label.pack(side="left", padx=(5, 0))
        
        # Visual bar
        bar = ctk.CTkFrame(row, width=bar_width, height=16, fg_color=color)
        bar.pack(side="left", padx=5)
        
        price_label = ctk.CTkLabel(
            row,
            text=f"{price:.5f}" if price < 100 else f"{price:.2f}",
            width=100,
            anchor="center",
            font=ctk.CTkFont(size=11, family="Consolas"),
            text_color=color
        )
        price_label.pack(side="left")
        
        time_label = ctk.CTkLabel(
            row,
            text=datetime.now().strftime("%H:%M"),
            width=80,
            anchor="e",
            font=ctk.CTkFont(size=10)
        )
        time_label.pack(side="right", padx=(0, 5))
        
    def set_mt5_connection(self, mt5_connection):
        """Setzt die MT5-Verbindung"""
        self.mt5_connection = mt5_connection
        
    def start_auto_update(self, interval_ms=1000):
        """Startet automatische Updates"""
        if self.update_thread and self.update_thread.is_alive():
            return
            
        self.stop_update = False
        self.update_thread = threading.Thread(target=self._update_loop, args=(interval_ms,))
        self.update_thread.daemon = True
        self.update_thread.start()
        
    def stop_auto_update(self):
        """Stoppt automatische Updates"""
        self.stop_update = True
        if self.update_thread:
            self.update_thread.join(timeout=2)
            
    def _update_loop(self, interval_ms):
        """Update-Loop für Order Book Daten"""
        import time
        while not self.stop_update:
            try:
                if self.mt5_connection:
                    self._fetch_order_book_data()
                time.sleep(interval_ms / 1000)
            except Exception as e:
                print(f"Order Book Update Error: {e}")
                break
                
    def _fetch_order_book_data(self):
        """Holt Order Book Daten von MT5"""
        # Diese Methode würde mit echter MT5-Verbindung arbeiten
        # Für jetzt zeigen wir Sample-Daten
        self._show_sample_data()
        
    def destroy(self):
        """Cleanup bei Destruktion"""
        self.stop_auto_update()
        super().destroy()


class MarketDepthWidget(ctk.CTkFrame):
    """Market Depth Widget - Zeigt Markttiefe als horizontale Balken"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.buy_color = "#27AE60"
        self.sell_color = "#E74C3C"
        
        self._setup_ui()
        
    def _setup_ui(self):
        """UI-Einrichtung"""
        # Header
        header = ctk.CTkLabel(
            self,
            text="📈 Markttiefe",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        header.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Canvas für visuelle Darstellung
        self.canvas = ctk.CTkCanvas(
            self,
            height=100,
            bg="#1E1E1E",
            highlightthickness=0
        )
        self.canvas.pack(fill="x", padx=10, pady=5)
        
        # Legend
        legend_frame = ctk.CTkFrame(self, fg_color="transparent")
        legend_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(
            legend_frame,
            text="● Bids (Buy)",
            text_color=self.buy_color,
            font=ctk.CTkFont(size=10)
        ).pack(side="left")
        
        ctk.CTkLabel(
            legend_frame,
            text="● Asks (Sell)",
            text_color=self.sell_color,
            font=ctk.CTkFont(size=10)
        ).pack(side="right")
        
        # Zeige Beispieldaten
        self._show_sample_depth()
        
    def _show_sample_depth(self):
        """Zeigt Beispieldaten für Markttiefe"""
        self.canvas.delete("all")
        
        width = self.canvas.winfo_width() or 400
        center_x = width / 2
        
        # Sample data: cumulative volumes
        bids = [5.0, 4.5, 4.0, 3.5, 3.0]
        asks = [4.8, 4.2, 3.8, 3.2, 2.8]
        
        max_vol = max(max(bids), max(asks))
        
        # Draw asks (left side - red)
        x_pos = center_x
        for i, vol in enumerate(asks):
            bar_width = (vol / max_vol) * center_x * 0.9
            self.canvas.create_rectangle(
                center_x - bar_width, 
                10 + i * 18,
                center_x, 
                25 + i * 18,
                fill=self.sell_color,
                outline=""
            )
            
        # Draw bids (right side - green)
        for i, vol in enumerate(bids):
            bar_width = (vol / max_vol) * center_x * 0.9
            self.canvas.create_rectangle(
                center_x, 
                10 + i * 18,
                center_x + bar_width, 
                25 + i * 18,
                fill=self.buy_color,
                outline=""
            )
            
        # Center line
        self.canvas.create_line(
            center_x, 5, center_x, 95,
            fill="#444444",
            width=2
        )


if __name__ == "__main__":
    # Test des Widgets
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    root.title("Order Book Test")
    root.geometry("400x500")
    
    # Order Book
    order_book = OrderBookWidget(root)
    order_book.pack(fill="both", expand=True, padx=10, pady=10)
    
    root.mainloop()
