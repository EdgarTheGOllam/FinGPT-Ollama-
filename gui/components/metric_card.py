import customtkinter as ctk
from gui.design_system import DesignSystem
from typing import Optional, Callable
import threading


class MetricCard(ctk.CTkFrame):
    """
    Eine wiederverwendbare Metrik-Karte mit modernem Design, Icon, Trend-Anzeige und Hover-Interaction.
    Verwendet das zentrale Design-System für konsistente Farben und Abstände.
    """
    
    # Icon-Mapping (Verwendung von Symbols für reine Farbsteuerung statt System-Emojis)
    ICONS = {
        'balance': '✦',      # Kontostand
        'positions': '■',    # Positionen
        'trades': '▲',       # Trades
        'pnl': '●',          # Gewinn/Verlust
        'winrate': '★',      # Win Rate / Margin
        'risk': '◆',         # Risiko / Freie Margin
        'default': '❖'       # Standard
    }
    
    # Spezifische TTG Neon-Farben für jedes Icon
    ICON_COLORS = {
        'balance': '#00FF66',  # Neon Grün
        'positions': '#FFEA00',# Neon Gelb
        'trades': '#2979FF',   # Neon Blau
        'pnl': '#FF1744',      # Neon Rot
        'winrate': '#9C27B0',  # Neon Lila
        'risk': '#FF9100',     # Neon Orange
        'default': '#8B949E'   # Grau
    }
    
    # Farben für Trend-Indikatoren
    TREND_COLORS = {
        'positive': DesignSystem.get_semantic_color('profit'),  # Grün
        'negative': DesignSystem.get_semantic_color('loss'),    # Rot
        'neutral': DesignSystem.get_semantic_color('neutral')  # Grau
    }

    def __init__(self, master, title, value, icon_type='default', trend=None, trend_value=None, 
                 min_width=None, max_width=None, **kwargs):
        """
        Erstellt eine neue MetricCard.
        
        Args:
            master: Parent-Widget
            title: Titel der Karte (z.B. "Kontostand")
            value: Wert der Karte (z.B. "€1,234.56")
            icon_type: Typ des Icons (balance, positions, trades, pnl, winrate, risk, default)
            trend: Trend-Richtung ('up', 'down', 'neutral') für kleinen Pfeil
            trend_value: Wertänderung für Trend-Anzeige (z.B. "+2.5%")
            min_width: Minimale Breite der Karte (verhindert Abschneiden)
            max_width: Maximale Breite der Karte
        """
        # Design-Tokens laden
        ds = DesignSystem
        
        # Minimale Breite setzen (verhindert Abschneiden)
        self._min_width = min_width or ds.get_min_width_for_breakpoint('metric_card')
        self._max_width = max_width
        
        self.default_color = "transparent"
        self.hover_color = "#1A1D24"  # Leichte Aufhellung beim Hover
        
        radius = ds.get_radius('md')
        
        # Standard-Parameter
        default_kwargs = {
            'corner_radius': radius,
            'fg_color': self.default_color,
            'border_width': 1,
            'border_color': "#2A2D34"
        }
        config = {**default_kwargs, **kwargs}
        
        # Hauptframe Container init
        super().__init__(master, **config)
        
        # Konfiguriere minimale Breite
        self.configure(width=self._min_width)
        
        # Responsive Padding
        self._padding = ds.COMPONENTS['metric_card']['padding']
        
        self.icon_type = icon_type
        self.trend = trend
        self.trend_value = trend_value
        
        # Padding aus Design-System
        padding = ds.COMPONENTS['metric_card']['padding']
        
        # Container für besseres Layout (Icon + Title + Value + Trend)
        self._content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._content_frame.pack(fill="both", expand=True, padx=padding, pady=padding)
        self._content_frame.grid_columnconfigure(1, weight=1)  # Title/Value column expands
        
        # Responsive Icon-Größe basierend auf verfügbarer Breite
        window_width = master.winfo_width() if hasattr(master, 'winfo_width') else 1400
        icon_size = self._get_responsive_icon_size(window_width)
        
        # 1. Icon (links)
        icon_text = self.ICONS.get(icon_type, self.ICONS['default'])
        # Dynamische Icon-Farbe statt grau
        icon_color = self.ICON_COLORS.get(icon_type, self.ICON_COLORS['default'])

        # Trend Colors (Semantic)
        self.trend_colors = {
            'up': ds.TRADING_COLORS['profit'],
            'down': ds.TRADING_COLORS['loss'],
            'neutral': ds.SEMANTIC.get('neutral', '#8B949E')
        }
        self.icon_label = ctk.CTkLabel(
            self._content_frame,
            text=icon_text,
            font=ctk.CTkFont(size=icon_size),
            text_color=icon_color # Use the new icon_color
        )
        self.icon_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 10))
        
        # Responsive Font-Größen
        title_font = ds.get_font('sm', 'medium')
        # Value Style (Weiß für besseren Kontrast)
        value_font = ds.get_font('xl', weight='bold', mono=True)
        value_color = "#FFFFFF"
        
        # Prüfe verfügbare Breite und passe ggf. Font-Größen an
        available_width = self.winfo_width() if self.winfo_exists() else 200
        if available_width < 150:
            title_font = ds.get_font('xs', 'medium')
            value_font = ds.get_font('base', 'bold', mono=True)
        
        # 2. Title Label (oben links)
        self.title_label = ctk.CTkLabel(
            self._content_frame,
            text=title,
            font=title_font,
            text_color=ds.get_semantic_color('neutral')
        )
        self.title_label.grid(row=0, column=1, sticky="w", pady=(0, 4))
        
        # 3. Value Label (unten links, neben Title)
        self.value_label = ctk.CTkLabel(
            self._content_frame,
            text=value,
            font=value_font,
            text_color="#FFFFFF"
        )
        self.value_label.grid(row=1, column=1, sticky="w")
        
        # 4. Trend-Indikator (rechts, wenn vorhanden)
        # Trend-Frame nur hinzufügen wenn genug Platz vorhanden
        if trend and trend_value:
            self.trend_frame = ctk.CTkFrame(self._content_frame, fg_color="transparent")
            self.trend_frame.grid(row=0, column=2, rowspan=2, sticky="e", padx=(8, 0))
            
            # Trend-Pfeil
            arrow = "▲" if trend == 'up' else "▼" if trend == 'down' else "●"
            trend_color = self.TREND_COLORS['positive'] if trend == 'up' else \
                          self.TREND_COLORS['negative'] if trend == 'down' else \
                          self.TREND_COLORS['neutral']
            
            # Verkleinere Trend-Text bei wenig Platz
            trend_font_size = 12 if available_width < 180 else 14
            
            self.trend_arrow = ctk.CTkLabel(
                self.trend_frame,
                text=arrow,
                font=ctk.CTkFont(size=trend_font_size, weight="bold"),
                text_color=trend_color
            )
            self.trend_arrow.pack(side="left", padx=(0, 2))
            
            self.trend_value_label = ctk.CTkLabel(
                self.trend_frame,
                text=trend_value,
                font=ds.get_font('xs', 'medium', mono=True),
                text_color=trend_color
            )
            self.trend_value_label.pack(side="left")
        
        # Event-Bindings für Hover-Animation auf allen relevanten Widgets
        self._bind_hover_recursive(self)

    def _get_responsive_icon_size(self, window_width: int) -> int:
        """Berechnet responsive Icon-Größe basierend auf Fensterbreite."""
        ds = DesignSystem
        base_size = ds.COMPONENTS['metric_card']['icon_size']
        
        if window_width < ds.BREAKPOINTS['sm']:
            return int(base_size * 0.75)
        elif window_width < ds.BREAKPOINTS['md']:
            return int(base_size * 0.85)
        return base_size

    def _bind_hover_recursive(self, widget):
        """Bindet Hover-Events rekursiv auf alle Child-Widgets."""
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        for child in widget.winfo_children():
            self._bind_hover_recursive(child)

    def _on_enter(self, event):
        """Sanfter Hover-Effekt mit Hintergrundfarbe und neon blauem Border."""
        self.configure(fg_color=self.hover_color, border_color=DesignSystem.get_color('primary'), border_width=1)
        
    def _on_leave(self, event):
        """Reset bei Mausverlassen."""
        self.configure(fg_color=self.default_color, border_color="#2A2D34", border_width=1)

    def update_value(self, new_value, trend=None, trend_value=None):
        """
        Aktualisiert den Wert der Karte.
        
        Args:
            new_value: Neuer Wert (String)
            trend: Optional, neuer Trend ('up', 'down', 'neutral')
            trend_value: Optional, neuer Trend-Wert
        """
        self.value_label.configure(text=new_value)
        
        if trend is not None and trend_value is not None:
            # Trend-Update nur wenn Trend-Info vorhanden war
            if hasattr(self, 'trend_arrow') and hasattr(self, 'trend_value_label'):
                arrow = "▲" if trend == 'up' else "▼" if trend == 'down' else "●"
                trend_color = self.TREND_COLORS['positive'] if trend == 'up' else \
                              self.TREND_COLORS['negative'] if trend == 'down' else \
                              self.TREND_COLORS['neutral']
                
                self.trend_arrow.configure(text=arrow, text_color=trend_color)
                self.trend_value_label.configure(text=trend_value, text_color=trend_color)
        elif hasattr(self, 'trend_frame'):
            # Trend entfernen, wenn nicht mehr benötigt
            self.trend_frame.destroy()
            delattr(self, 'trend_frame')
            delattr(self, 'trend_arrow')
            delattr(self, 'trend_value_label')

    def set_icon(self, icon_type):
        """Ändert das Icon der Karte."""
        if icon_type in self.ICONS:
            self.icon_type = icon_type
            self.icon_label.configure(
                text=self.ICONS[icon_type], 
                text_color=self.ICON_COLORS.get(icon_type, self.ICON_COLORS['default'])
            )

    def highlight_change(self, duration_ms=500):
        """
        Hervorhebung bei Wertänderung (Wertetext leuchtet kurz Neon-Grün auf).
        
        Args:
            duration_ms: Dauer der Hervorhebung in Millisekunden
        """
        original_color = "#FFFFFF"
        flash_color = "#00FF66" # TTG Neon Green
        
        # Leucht-Effekt auf dem Wertetext
        if hasattr(self, 'value_label') and self.value_label.winfo_exists():
            self.value_label.configure(text_color=flash_color)
            self.after(duration_ms, lambda: self.value_label.configure(text_color=original_color) if self.value_label.winfo_exists() else None)


# Test-Funktion (nur bei direkter Ausführung)
if __name__ == "__main__":
    import tkinter as tk
    
    root = ctk.CTk()
    root.title("MetricCard Test")
    root.geometry("800x400")
    
    # Design-System anwenden
    DesignSystem.apply_theme(root)
    
    # Test-Karten erstellen
    test_frame = ctk.CTkFrame(root)
    test_frame.pack(fill="both", expand=True, padx=20, pady=20)
    test_frame.grid_columnconfigure((0, 1, 2), weight=1)
    
    # Karte 1: Kontostand mit positivem Trend
    card1 = MetricCard(test_frame, "Kontostand", "€12,345.67", icon_type='balance', trend='up', trend_value='+2.5%')
    card1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    
    # Karte 2: Offene Positionen (neutral)
    card2 = MetricCard(test_frame, "Offene Positionen", "5", icon_type='positions')
    card2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
    
    # Karte 3: P&L mit negativem Trend
    card3 = MetricCard(test_frame, "Gewinn/Verlust", "-€234.50", icon_type='pnl', trend='down', trend_value='-1.2%')
    card3.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
    
    # Karte 4: Win Rate
    card4 = MetricCard(test_frame, "Win Rate", "68.5%", icon_type='winrate', trend='up', trend_value='+3%')
    card4.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    
    # Karte 5: Risiko
    card5 = MetricCard(test_frame, "Freie Margin", "€5,432.10", icon_type='risk')
    card5.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
    
    # Karte 6: Trades
    card6 = MetricCard(test_frame, "Heutige Trades", "23", icon_type='trades', trend='up', trend_value='+5')
    card6.grid(row=1, column=2, padx=10, pady=10, sticky="nsew")
    
    # Test-Button für Wert-Update
    def update_values():
        import random
        card1.update_value(f"€{random.randint(10000, 20000):,}.{random.randint(0, 99):02d}", 
                          trend='up' if random.random() > 0.5 else 'down', 
                          trend_value=f"{random.choice(['+', '-'])}{random.randint(1, 5)}.{random.randint(0, 9)}%")
        card3.update_value(f"€{random.randint(-500, 500):+}", 
                          trend='up' if random.random() > 0.5 else 'down', 
                          trend_value=f"{random.choice(['+', '-'])}{random.randint(1, 5)}.{random.randint(0, 9)}%")
    
    update_btn = ctk.CTkButton(root, text="Werte aktualisieren", command=update_values)
    update_btn.pack(pady=10)
    
    root.mainloop()
