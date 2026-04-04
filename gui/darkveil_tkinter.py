"""
DarkVeil Background – Tkinter-Integration
==========================================
Lädt den WebGL-Shader-Hintergrund (darkveil_bg.html) als
transparentes/überlagerndes Fenster.

Unterstützte Backends (automatische Erkennung):
  1. pywebview  – natives Webview, beste Qualität
  2. tkinterweb – Tkinter-Widget mit Gecko/WebKit
  3. Fallback   – animierter Canvas-Gradient (kein WebGL)

Verwendung:
    from gui.darkveil_tkinter import DarkVeilBackground
    bg = DarkVeilBackground(parent_window, config={...})
    bg.start()
    # später:
    bg.stop()
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
import math
import time
from pathlib import Path
from typing import Any, Dict, Optional

# ── Pfad zur HTML-Datei ────────────────────────────────────────────────────────
_HERE      = Path(__file__).parent
_HTML_FILE = _HERE / "darkveil_bg.html"
_HTML_URL  = _HTML_FILE.as_uri()          # file:///...


# ── Backend-Erkennung ──────────────────────────────────────────────────────────
def _detect_backend() -> str:
    try:
        import webview  # noqa: F401
        return "pywebview"
    except ImportError:
        pass
    try:
        import tkinterweb  # noqa: F401
        return "tkinterweb"
    except ImportError:
        pass
    return "canvas"


# ── Default-Konfiguration ──────────────────────────────────────────────────────
DEFAULT_CONFIG: Dict[str, float] = {
    "hueShift":       0.0,
    "noiseIntensity": 0.02,
    "scanIntensity":  0.05,
    "speed":          0.5,
    "scanFreq":       400.0,
    "warpAmount":     0.3,
    "resScale":       1.0,
}


# ══════════════════════════════════════════════════════════════════════════════
# Haupt-Klasse
# ══════════════════════════════════════════════════════════════════════════════

class DarkVeilBackground:
    """
    Fügt einem Tkinter-Toplevel oder Frame einen animierten DarkVeil-
    WebGL-Hintergrund hinzu.

    Parameters
    ----------
    parent : tk.Misc
        Eltern-Widget (z.B. root.Toplevel, selbst ein Frame)
    config : dict, optional
        Shader-Parameter, vgl. DEFAULT_CONFIG
    embed : bool
        True  → Hintergrund wird als eingebettetes Widget platziert
        False → Hintergrund öffnet ein eigenständiges Toplevel-Fenster
        (Standard: True)
    """

    def __init__(
        self,
        parent: tk.Misc,
        config: Optional[Dict[str, float]] = None,
        embed: bool = True,
    ):
        self.parent  = parent
        self.config  = {**DEFAULT_CONFIG, **(config or {})}
        self.embed   = embed
        self.backend = _detect_backend()
        self._running = False

        # Wird je nach Backend gesetzt
        self._webview_window = None
        self._canvas: Optional[tk.Canvas] = None
        self._anim_id: Optional[str] = None

    # ── Öffentliche API ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Startet den Hintergrund-Effekt."""
        if self._running:
            return
        self._running = True
        if self.backend == "pywebview":
            self._start_pywebview()
        elif self.backend == "tkinterweb":
            self._start_tkinterweb()
        else:
            self._start_canvas_fallback()

    def stop(self) -> None:
        """Stoppt den Hintergrund-Effekt und gibt Ressourcen frei."""
        self._running = False
        if self._anim_id and self._canvas:
            try:
                self._canvas.after_cancel(self._anim_id)
            except Exception:
                pass
        if self._webview_window:
            try:
                import webview
                webview.destroy_window(self._webview_window)
            except Exception:
                pass

    # ── pywebview Backend ──────────────────────────────────────────────────────

    def _start_pywebview(self) -> None:
        """Öffnet die HTML-Datei in einem nativen Webview-Fenster."""
        import webview

        url = self._html_url_with_params()

        def _run():
            try:
                w = webview.create_window(
                    "DarkVeil Background",
                    url=url,
                    frameless=True,
                    on_top=False,
                    transparent=True,
                    background_color="#00000000",
                    width=self.parent.winfo_width()  or 800,
                    height=self.parent.winfo_height() or 600,
                )
                self._webview_window = w
                webview.start()
            except Exception as exc:
                print(f"[DarkVeil] pywebview Fehler: {exc}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    # ── tkinterweb Backend ─────────────────────────────────────────────────────

    def _start_tkinterweb(self) -> None:
        """Bettet die HTML-Seite als Tkinter-Widget ein."""
        try:
            import tkinterweb
            frame = tkinterweb.HtmlFrame(self.parent, messages_enabled=False)
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            # Widget hinter alle anderen schieben
            frame.lower()
            url = self._html_url_with_params()
            frame.load_url(url)
        except Exception as exc:
            print(f"[DarkVeil] tkinterweb Fehler: {exc} – verwende Canvas-Fallback")
            self._start_canvas_fallback()

    # ── Canvas Fallback ────────────────────────────────────────────────────────

    def _start_canvas_fallback(self) -> None:
        """
        Animierter Farbverlauf-Hintergrund als Fallback wenn
        kein WebGL-Backend verfügbar ist.
        Die Farben ahmen den CPPN-Farbstil von DarkVeil nach.
        """
        c = tk.Canvas(
            self.parent,
            highlightthickness=0,
            bd=0,
        )
        c.place(relx=0, rely=0, relwidth=1, relheight=1)
        c.lower()   # hinter alle anderen Widgets
        self._canvas = c

        self._fallback_t   = 0.0
        self._last_ts      = time.time()

        # Palette: tief-dunkle Töne (inspiriert vom Shader-Output)
        self._palette = [
            (10,  8,  25),   # Mitternachts-Violett
            (5,  20,  35),   # Tiefsee-Blau
            (15,  5,  30),   # Dunkles Lila
            (8,  15,  20),   # Dunkles Cyan-Blau
            (20,  8,  15),   # Tiefes Burgund
        ]

        self._animate_fallback()

    def _animate_fallback(self) -> None:
        if not self._running or self._canvas is None:
            return
        try:
            w = self._canvas.winfo_width()
            h = self._canvas.winfo_height()
            if w < 2 or h < 2:
                self._anim_id = self._canvas.after(50, self._animate_fallback)
                return

            now = time.time()
            dt  = now - self._last_ts
            self._last_ts = now
            self._fallback_t += dt * self.config.get("speed", 0.5)

            t = self._fallback_t
            n = len(self._palette)

            # Interpoliere zwischen Palette-Farben
            idx0 = int(t * 0.15) % n
            idx1 = (idx0 + 1) % n
            frac = (t * 0.15) % 1.0

            r = lambda i: self._palette[i]

            def lerp_col(a, b, f):
                return tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))

            top_col = lerp_col(r(idx0), r(idx1), frac)
            # Leichte Variation für Bottom
            bot_col = lerp_col(r((idx0+2) % n), r((idx1+2) % n), frac)

            # Subtile Wellen mit sin
            wave_r = int(5 * math.sin(t * 0.3))
            wave_g = int(5 * math.sin(t * 0.5))
            wave_b = int(5 * math.sin(t * 0.7))

            top_col = (
                max(0, min(255, top_col[0] + wave_r)),
                max(0, min(255, top_col[1] + wave_g)),
                max(0, min(255, top_col[2] + wave_b)),
            )

            # Gradient über mehrere Rechtecke simulieren
            self._canvas.delete("grad")
            steps = 30
            for i in range(steps):
                f = i / steps
                rc = lerp_col(top_col, bot_col, f)
                color = "#%02x%02x%02x" % rc
                y0 = int(f * h)
                y1 = int((f + 1.0/steps) * h) + 1
                self._canvas.create_rectangle(
                    0, y0, w, y1,
                    fill=color, outline="", tags="grad"
                )

        except tk.TclError:
            return

        # Nächster Frame
        fps = 30
        self._anim_id = self._canvas.after(int(1000 / fps), self._animate_fallback)

    # ── Hilfsmethoden ─────────────────────────────────────────────────────────

    def _html_url_with_params(self) -> str:
        """Gibt die HTML-URL mit Konfigurations-Query-Parametern zurück."""
        c   = self.config
        url = (
            f"{_HTML_URL}"
            f"?hueShift={c.get('hueShift', 0)}"
            f"&noise={c.get('noiseIntensity', 0.02)}"
            f"&scan={c.get('scanIntensity', 0.05)}"
            f"&speed={c.get('speed', 0.5)}"
            f"&scanFreq={c.get('scanFreq', 400)}"
            f"&warp={c.get('warpAmount', 0.3)}"
            f"&resScale={c.get('resScale', 1.0)}"
        )
        return url


# ══════════════════════════════════════════════════════════════════════════════
# Splash-Screen-spezifische Hilfsfunktion
# ══════════════════════════════════════════════════════════════════════════════

def attach_to_splash(splash_root: tk.Tk, config: Optional[Dict[str, float]] = None) -> DarkVeilBackground:
    """
    Bindet DarkVeil direkt an den Splash-Screen-Root.

    Beispiel:
        from gui.darkveil_tkinter import attach_to_splash
        bg = attach_to_splash(splash.root)
        bg.start()
    """
    bg = DarkVeilBackground(
        parent=splash_root,
        config=config or {
            "hueShift":       120.0,   # leicht bläulich-cyan
            "noiseIntensity": 0.015,
            "scanIntensity":  0.04,
            "speed":          0.4,
            "scanFreq":       300.0,
            "warpAmount":     0.2,
        },
        embed=True,
    )
    bg.start()
    return bg
