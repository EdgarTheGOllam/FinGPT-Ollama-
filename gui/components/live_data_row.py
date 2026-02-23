import customtkinter as ctk

class LiveDataRow(ctk.CTkFrame):
    """Eine Zeile für die Scrollbare Live-Daten Ansicht mit MTF Trend Ampel"""
    def __init__(self, master, symbol, price, change, signal, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        # Grid Setup for consistent column widths
        self.grid_columnconfigure((0,1,2,3,4), weight=1, uniform="col")
        
        self.symbol_lbl = ctk.CTkLabel(self, text=symbol, font=ctk.CTkFont(size=13, weight="bold"))
        self.symbol_lbl.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        self.price_lbl = ctk.CTkLabel(self, text=price, font=ctk.CTkFont(size=13))
        self.price_lbl.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        change_color = "#5EBA7D" if "+" in change else "#E74C3C" if "-" in change else "gray"
        self.change_lbl = ctk.CTkLabel(self, text=change, text_color=change_color, font=ctk.CTkFont(size=13, weight="bold"))
        self.change_lbl.grid(row=0, column=2, sticky="w", padx=10, pady=5)
        
        # MTF Trend Ampel Frame
        self.trend_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.trend_frame.grid(row=0, column=3, sticky="w", padx=10, pady=5)
        
        self.trend_m15 = ctk.CTkLabel(self.trend_frame, text="●", text_color="gray", font=ctk.CTkFont(size=16))
        self.trend_m15.pack(side="left", padx=3)
        self.trend_h1 = ctk.CTkLabel(self.trend_frame, text="●", text_color="gray", font=ctk.CTkFont(size=16))
        self.trend_h1.pack(side="left", padx=3)
        self.trend_h4 = ctk.CTkLabel(self.trend_frame, text="●", text_color="gray", font=ctk.CTkFont(size=16))
        self.trend_h4.pack(side="left", padx=3)

        sig_color = "#2E86AB" if signal == "BUY" else "#A23B72" if signal == "SELL" else "gray"
        self.signal_btn = ctk.CTkButton(self, text=signal, width=60, height=24, fg_color=sig_color, hover_color=sig_color, corner_radius=12)
        self.signal_btn.grid(row=0, column=4, sticky="w", padx=10, pady=5)

    def update_data(self, price, change):
        self.price_lbl.configure(text=price)
        self.change_lbl.configure(text=change)
        change_color = "#5EBA7D" if "+" in change else "#E74C3C" if "-" in change else "gray"
        self.change_lbl.configure(text_color=change_color)

    def update_trend(self, m15_color, h1_color, h4_color):
        """Update the 3 timeframe dots with the given hex colors."""
        self.trend_m15.configure(text_color=m15_color)
        self.trend_h1.configure(text_color=h1_color)
        self.trend_h4.configure(text_color=h4_color)
