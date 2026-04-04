"""
SplashScreen - Ladebildschirm mit echtem Fortschrittsbalken für FinGPT
"""

from typing import Optional, Any
import time
import tkinter as tk
from tkinter import ttk

# DarkVeil WebGL-Hintergrund (mit automatischem Fallback)
try:
    from gui.darkveil_tkinter import attach_to_splash as _attach_darkveil
    _DARKVEIL_AVAILABLE = True
except Exception:
    _DARKVEIL_AVAILABLE = False


class SplashScreen:
    """Ladebildschirm mit echtem Fortschrittsbalken"""
    
    def __init__(self, title: str = "FinGPT - Ladevorgang", width: int = 500, height: int = 200):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(f"{width}x{height}")
        self.root.resizable(False, False)
        
        # Fenster zentrieren
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Verhindern dass Fenster geschlossen werden kann während des Ladens
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_attempt)
        
        # Styling
        self.root.configure(bg="#1a1a2e")
        
        # Icon setzen
        try:
            import os
            icon_path = r"C:\Users\edgar\Downloads\generated-image-removebg-preview.png"
            if os.path.exists(icon_path):
                img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, img)
                self._app_icon = img
        except Exception:
            pass
        
        # ── DarkVeil WebGL Hintergrund ──────────────────────────────────────
        self._darkveil_bg = None
        if _DARKVEIL_AVAILABLE:
            try:
                self._darkveil_bg = _attach_darkveil(self.root)
            except Exception:
                pass
        
        # Container (über DarkVeil, transparent damit der Hintergrund sichtbar bleibt)
        container = tk.Frame(self.root, bg="#1a1a2e")
        container.pack(expand=True, fill="both", padx=30, pady=30)
        
        # Logo/Titel
        self.title_label = tk.Label(
            container,
            text="FinGPT",
            font=("Segoe UI", 24, "bold"),
            bg="#1a1a2e",
            fg="#00d4ff"
        )
        self.title_label.pack(pady=(0, 5))
        
        self.subtitle_label = tk.Label(
            container,
            text="Trading Intelligence Platform",
            font=("Segoe UI", 10),
            bg="#1a1a2e",
            fg="#888888"
        )
        self.subtitle_label.pack(pady=(0, 20))
        
        # Status-Label
        self.status_label = tk.Label(
            container,
            text="Initialisiere...",
            font=("Segoe UI", 10),
            bg="#1a1a2e",
            fg="#ffffff",
            anchor="w"
        )
        self.status_label.pack(fill="x", pady=(0, 5))
        
        # Fortschrittsbalken (tkinter ttk Progressbar)
        style = ttk.Style()
        style.theme_use('clam')
        
        # Progressbar Styling
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor="#2d2d44",
            background="#00d4ff",
            thickness=20
        )
        
        self.progress = ttk.Progressbar(
            container,
            style="Horizontal.TProgressbar",
            mode='determinate',
            length=400
        )
        self.progress.pack(pady=(0, 10))
        
        # Prozent-Anzeige
        self.percent_label = tk.Label(
            container,
            text="0%",
            font=("Segoe UI", 9),
            bg="#1a1a2e",
            fg="#888888"
        )
        self.percent_label.pack()
        
        # Detail-Status
        self.detail_label = tk.Label(
            container,
            text="",
            font=("Segoe UI", 8),
            bg="#1a1a2e",
            fg="#666666"
        )
        self.detail_label.pack(pady=(10, 0))
        
        # Fortschritts-Variablen
        self.current_step = 0
        self.total_steps = 6
        self._close_requested = False
        self._loading_complete = False
        self._error_occurred = False
        self._error_message = ""
        
        # Force update
        self.root.update()
    
    def _on_close_attempt(self):
        """Verhindert Schließen während des Ladens"""
        if not self._loading_complete:
            pass
        else:
            self.root.destroy()
    
    def update_progress(self, step: int, status: str, detail: str = "", percent: Optional[int] = None):
        """Aktualisiert den Fortschrittsbalken"""
        if self._close_requested and not self._loading_complete:
            return
        
        # Prüfen ob Fenster noch existiert
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return
            
        self.current_step = step
        
        # Berechne Prozentsatz
        if percent is not None:
            progress_percent = percent
        else:
            progress_percent = int((step / self.total_steps) * 100)
        
        # Update GUI
        try:
            self.status_label.config(text=status)
            self.detail_label.config(text=detail)
            self.progress['value'] = progress_percent
            self.percent_label.config(text=f"{progress_percent}%")
            
            # Force GUI update
            self.root.update()
        except Exception:
            # Fenster wurde geschlossen
            return
            
        time.sleep(0.05)  # Kurze Pause für visuelle Aktualisierung
    
    def show_error(self, message: str):
        """Zeigt einen Fehler an"""
        self._error_occurred = True
        self._error_message = message
        
        try:
            self.status_label.config(text="Fehler aufgetreten!", fg="#ff4444")
            self.detail_label.config(text=message, fg="#ff4444")
            self.root.update()
        except Exception:
            # Fenster wurde bereits geschlossen
            pass
    
    def complete(self):
        """Markiert den Ladevorgang als abgeschlossen"""
        self._loading_complete = True
        
        try:
            self.update_progress(self.total_steps, "Fertig!", "FinGPT wird gestartet...", 100)
        except Exception:
            # Fenster wurde bereits geschlossen
            return
        
        # Kurze Anzeige des 100% Zustands
        try:
            self.root.update()
        except Exception:
            return
            
        time.sleep(0.5)
        
        # DarkVeil stoppen bevor Fenster zerstört wird
        if self._darkveil_bg is not None:
            try:
                self._darkveil_bg.stop()
            except Exception:
                pass
        
        # Fenster schließen - mit Exception-Handling
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except Exception:
            pass
        
        # Referenz aufheben
        self.root = None
        self._darkveil_bg = None
    
    def get_error_state(self):
        """Gibt zurück ob ein Fehler aufgetreten ist"""
        return self._error_occurred, self._error_message


# Flag für Verfügbarkeit
TKINTER_AVAILABLE = True
