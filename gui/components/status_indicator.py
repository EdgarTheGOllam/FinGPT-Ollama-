#!/usr/bin/env python3
"""
Status Indicator Component
Modernes UI-Element zur Anzeige von Verbindungsstatus und Systemzuständen
"""

import customtkinter as ctk
from typing import Optional
from gui.design_system import DesignSystem


class StatusIndicator(ctk.CTkFrame):
    """
    Moderner Status-Indikator mit animiertem Punkt und Label.
    Zeigt Verbindungsstatus (MT5, KI, etc.) visuell an.
    """
    
    def __init__(
        self, 
        master, 
        status: str = "disconnected",
        label: str = "",
        **kwargs
    ):
        """
        Args:
            master: Parent Widget
            status: initialer Status ('connected', 'disconnected', 'warning', 'error', 'loading')
            label: Anzuzeigende Beschriftung
        """
        # Design System Tokens
        ds = DesignSystem
        
        # Status-Farben
        self._status_colors = {
            'connected': ds.TRADING_COLORS.get('profit', '#27AE60'),
            'disconnected': ds.TRADING_COLORS.get('neutral', '#71717A'),
            'warning': ds.TRADING_COLORS.get('warning', '#F39C12'),
            'error': ds.TRADING_COLORS.get('loss', '#E74C3C'),
            'loading': ds.COLORS.get('primary', {}).get('base', '#38BDF8'),
        }
        
        self._current_status = status
        self._label_text = label
        self._pulsing = False
        
        # Default kwargs überschreiben
        default_kwargs = {
            'corner_radius': ds.get_radius('lg'),
            'fg_color': 'transparent',
            'border_width': 0,
        }
        default_kwargs.update(kwargs)
        
        super().__init__(master, **default_kwargs)
        
        # Layout
        self._setup_layout()
        
        # Status setzen
        self.set_status(status, label)
    
    def _setup_layout(self):
        """Richtet das interne Layout ein"""
        self.grid_columnconfigure(0, weight=0)  # Status-Punkt
        self.grid_columnconfigure(1, weight=1)  # Label
        
        # Status Punkt (animierter Kreis)
        self.status_dot = ctk.CTkCanvas(
            self, 
            width=12, 
            height=12, 
            bg='transparent', 
            highlightthickness=0
        )
        self.status_dot.grid(row=0, column=0, padx=(12, 8), pady=12, sticky="w")
        
        # Zeichne initialen Kreis
        self._dot_id = self.status_dot.create_oval(
            2, 2, 10, 10,
            fill=self._status_colors.get(self._current_status, '#71717A'),
            outline=''
        )
        
        # Label
        self.label = ctk.CTkLabel(
            self,
            text=self._label_text,
            font=DesignSystem.get_font('sm', 'normal'),
            text_color=DesignSystem.SEMANTIC.get('neutral', 'gray')
        )
        self.label.grid(row=0, column=1, padx=(0, 12), pady=12, sticky="w")
    
    def set_status(self, status: str, label: Optional[str] = None):
        """
        Setzt den Status und optional das Label.
        
        Args:
            status: neuer Status
            label: optional neues Label
        """
        if status not in self._status_colors:
            status = 'disconnected'
        
        self._current_status = status
        color = self._status_colors[status]
        
        # Update dot color
        self.status_dot.itemconfig(self._dot_id, fill=color)
        
        # Update label if provided
        if label is not None:
            self._label_text = label
            self.label.configure(text=label)
        
        # Handle loading pulse animation
        if status == 'loading':
            self._start_pulse()
        else:
            self._stop_pulse()
    
    def _start_pulse(self):
        """Startet Pulsieren für loading-Status"""
        if self._pulsing:
            return
        self._pulsing = True
        self._pulse_animation()
    
    def _stop_pulse(self):
        """Stoppt Pulsieren"""
        self._pulsing = False
    
    def _pulse_animation(self):
        """Pulsieren Animation"""
        if not self._pulsing:
            # Reset opacity
            self.status_dot.itemconfig(self._dot_id, fill=self._status_colors.get('loading', '#38BDF8'))
            return
        
        # Einfache Pulsieren durch Farbwechsel simulieren
        colors = ['#38BDF8', '#7DD3FC', '#38BDF8']
        current = getattr(self, '_pulse_index', 0)
        self._pulse_index = (current + 1) % len(colors)
        
        self.status_dot.itemconfig(self._dot_id, fill=colors[self._pulse_index])
        
        # Nächster Frame nach 500ms
        self.after(500, self._pulse_animation)
    
    def get_status(self) -> str:
        """Gibt den aktuellen Status zurück"""
        return self._current_status


class StatusBar(ctk.CTkFrame):
    """
    Status-Leiste mit mehreren StatusIndikatoren.
    Zeigt alle wichtigen Systemzustände auf einen Blick.
    """
    
    def __init__(self, master, **kwargs):
        ds = DesignSystem
        
        default_kwargs = {
            'corner_radius': 0,
            'fg_color': '#09090B',
            'height': 30,
        }
        default_kwargs.update(kwargs)
        
        super().__init__(master, **default_kwargs)
        
        self._indicators = {}
        self._setup_layout()
    
    def _setup_layout(self):
        """Richtet das Layout ein"""
        # Flexible Spalten
        self.grid_columnconfigure(0, weight=1)  # Linke Seite (MT5)
        self.grid_columnconfigure(1, weight=1)  # Mitte (KI)
        self.grid_columnconfigure(2, weight=1)  # Rechte (Zeit/Version)
        
        # Status-Indikatoren erstellen
        self.mt5_indicator = StatusIndicator(self, status='disconnected', label='MT5')
        self.mt5_indicator.grid(row=0, column=0, padx=20, pady=5, sticky="w")
        
        self.ai_indicator = StatusIndicator(self, status='disconnected', label='KI')
        self.ai_indicator.grid(row=0, column=1, padx=20, pady=5, sticky="w")
        
        self.trading_indicator = StatusIndicator(self, status='disconnected', label='Trading')
        self.trading_indicator.grid(row=0, column=2, padx=20, pady=5, sticky="e")
        
        # Referenzen speichern
        self._indicators = {
            'mt5': self.mt5_indicator,
            'ai': self.ai_indicator,
            'trading': self.trading_indicator
        }
    
    def update_mt5_status(self, connected: bool):
        """Aktualisiert MT5-Status"""
        status = 'connected' if connected else 'disconnected'
        label = 'MT5: Verbunden' if connected else 'MT5: Getrennt'
        self.mt5_indicator.set_status(status, label)
    
    def update_ai_status(self, connected: bool, model_name: str = None):
        """Aktualisiert KI-Status"""
        if connected:
            label = f'KI: {model_name or "Bereit"}'
            self.ai_indicator.set_status('connected', label)
        else:
            self.ai_indicator.set_status('disconnected', 'KI: Nicht verfügbar')
    
    def update_trading_status(self, enabled: bool):
        """Aktualisiert Trading-Status"""
        if enabled:
            self.trading_indicator.set_status('connected', 'Trading: Aktiv')
        else:
            self.trading_indicator.set_status('disconnected', 'Trading: Inaktiv')
    
    def set_warning(self, indicator: str, message: str):
        """Setzt einen Warnungsstatus"""
        if indicator in self._indicators:
            self._indicators[indicator].set_status('warning', message)
    
    def set_error(self, indicator: str, message: str):
        """Setzt einen Fehlerstatus"""
        if indicator in self._indicators:
            self._indicators[indicator].set_status('error', message)


if __name__ == "__main__":
    # Test des StatusIndicator
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    
    app = ctk.CTk()
    app.geometry("400x200")
    
    # StatusBar Test
    status_bar = StatusBar(app)
    status_bar.pack(fill="x", side="bottom")
    
    # Einzelne Indicator Test
    frame = ctk.CTkFrame(app)
    frame.pack(pady=20)
    
    indicator1 = StatusIndicator(frame, status='connected', label='MT5 Verbunden')
    indicator1.pack(pady=5, padx=10, fill="x")
    
    indicator2 = StatusIndicator(frame, status='loading', label='Verbindung wird hergestellt...')
    indicator2.pack(pady=5, padx=10, fill="x")
    
    indicator3 = StatusIndicator(frame, status='warning', label='Warnung: Niedrige Margin')
    indicator3.pack(pady=5, padx=10, fill="x")
    
    indicator4 = StatusIndicator(frame, status='error', label='Fehler: Verbindung verloren')
    indicator4.pack(pady=5, padx=10, fill="x")
    
    def toggle_mt5():
        current = indicator1.get_status()
        new_status = 'disconnected' if current == 'connected' else 'connected'
        label = 'MT5 Verbunden' if new_status == 'connected' else 'MT5 Getrennt'
        indicator1.set_status(new_status, label)
    
    btn = ctk.CTkButton(frame, text="MT5 Status Toggle", command=toggle_mt5)
    btn.pack(pady=10)
    
    app.mainloop()