"""
Aurora Background – Tkinter-Integration
=========================================
Lädt den WebGL-Aurora-Hintergrund (aurora_bg.html) via tkinterweb
als Hintergrund-Widget, das korrekt hinter allen CTk-Widgets sitzt.

WICHTIG: Aurora muss INNERHALB des sichtbaren CTkFrame (z.B. main_container)
platziert werden — nicht auf dem Root-Fenster, da CTkFrames opak sind.

Verwendung (in ModernFinGPTGUI.setup_layout, am Anfang):
    from gui.aurora_tkinter import attach_aurora_to_frame
    self._aurora_bg = attach_aurora_to_frame(self.main_container, config={...})
"""

from __future__ import annotations

import math
import time
import tkinter as tk
from pathlib import Path
from typing import Dict, Optional

# ── Pfad zur HTML-Datei ────────────────────────────────────────────────────────
_HERE      = Path(__file__).parent
_HTML_FILE = _HERE / "aurora_bg.html"
_HTML_URL  = _HTML_FILE.as_uri()          # file:///...


# ── Default-Konfiguration ──────────────────────────────────────────────────────
DEFAULT_CONFIG: Dict = {
    "color0":    "5227FF",   # Violet
    "color1":    "00C2FF",   # Cyan-Blue
    "color2":    "5227FF",   # Violet
    "amplitude": 1.0,
    "blend":     0.5,
    "speed":     0.8,
}


# ══════════════════════════════════════════════════════════════════════════════
class AuroraBackground:
    """
    Platziert Aurora als Hintergrund in einem gegebenen Container-Widget.
    Das Widget muss PACK oder GRID-Kinder haben, die 'transparent' sind.
    Aurora selbst wird mit PLACE(relx=0,rely=0,relw=1,relh=1) + lower() eingebettet.
    """

    def __init__(
        self,
        container: tk.Misc,
        config: Optional[Dict] = None,
    ):
        self.container = container
        self.config    = {**DEFAULT_CONFIG, **(config or {})}
        self._running  = False
        self._frame    = None  # tkinterweb HtmlFrame
        self._canvas: Optional[tk.Canvas] = None
        self._anim_id: Optional[str]      = None
        self._fallback_t = 0.0
        self._last_ts    = 0.0

    # ── API ───────────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            import tkinterweb
            self._start_tkinterweb(tkinterweb)
        except ImportError:
            self._start_canvas_fallback()

    def stop(self) -> None:
        self._running = False
        if self._anim_id and self._canvas:
            try:
                self._canvas.after_cancel(self._anim_id)
            except Exception:
                pass

    # ── tkinterweb ────────────────────────────────────────────────────────────

    def _start_tkinterweb(self, tkinterweb) -> None:
        try:
            url = self._build_url()
            frame = tkinterweb.HtmlFrame(
                self.container,
                messages_enabled=False,
                vertical_scrollbar=False,
                horizontal_scrollbar=False,
            )
            # Absolut hinter alle anderen Widgets im Container
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            frame.lower()
            frame.load_url(url)
            self._frame = frame
            print("[Aurora] tkinterweb HtmlFrame geladen ✓")
        except Exception as exc:
            print(f"[Aurora] tkinterweb Fehler: {exc} – Canvas-Fallback aktiv")
            self._start_canvas_fallback()

    # ── Canvas Fallback ───────────────────────────────────────────────────────

    def _start_canvas_fallback(self) -> None:
        """Animierter Gradient-Fallback (kein WebGL erforderlich)."""
        c = tk.Canvas(
            self.container,
            highlightthickness=0,
            bd=0,
            bg="#0B0E14",
        )
        c.place(relx=0, rely=0, relwidth=1, relheight=1)
        c.lower()
        self._canvas = c
        self._fallback_t = 0.0
        self._last_ts    = time.time()

        # Aurora-Palette
        self._palette = [
            (82,  39, 255),   # Violet #5227FF
            (0,  194, 255),   # Cyan   #00C2FF
            (40, 100, 200),   # Midblue
            (82,  39, 255),   # Violet (loop)
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
            self._last_ts     = now
            self._fallback_t += dt * self.config.get("speed", 0.8) * 0.4

            t = self._fallback_t
            n = len(self._palette)

            def lerp(a, b, f):
                return tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))

            idx0 = int(t * 0.1) % n
            idx1 = (idx0 + 1) % n
            frac = (t * 0.1) % 1.0

            aurora_col = lerp(self._palette[idx0], self._palette[idx1], frac)
            base       = (11, 14, 20)   # #0B0E14

            # Welleneffekt (simplifizierter snoise-Ersatz)
            amp   = self.config.get("amplitude", 1.0)
            wave  = math.sin(t * 0.9) * 0.3 + math.sin(t * 1.7 + 1.1) * 0.2
            glow  = int((0.5 + wave * amp * 0.4) * 255)
            glow  = max(0, min(255, glow))

            # Aurora-Band zeichnen (obere ~45% des Fensters)
            self._canvas.delete("aurora")
            steps     = 50
            band_h    = int(h * 0.50)
            blend_val = self.config.get("blend", 0.5)

            for i in range(steps):
                f   = i / steps                             # 0.0 → 1.0 (oben → unten)
                ss  = f * f * (3 - 2 * f)                  # Smooth-step
                # Helligkeit: am oberen Rand am stärksten
                bright = (1.0 - ss) * blend_val * (0.5 + 0.5 * math.sin(t * 0.6 + f * 3))
                bright = max(0.0, min(1.0, bright))
                rc = lerp(aurora_col, base, 1.0 - bright)
                color = "#%02x%02x%02x" % rc
                y0 = int(f * band_h)
                y1 = int((i + 1) / steps * band_h) + 1
                self._canvas.create_rectangle(0, y0, w, y1, fill=color, outline="", tags="aurora")

            # Unterhalb des Aurora-Bands: reines #0B0E14
            self._canvas.create_rectangle(0, band_h, w, h, fill="#0B0E14", outline="", tags="aurora")

        except tk.TclError:
            return

        self._anim_id = self._canvas.after(33, self._animate_fallback)  # ~30fps

    # ── URL-Builder ───────────────────────────────────────────────────────────

    def _build_url(self) -> str:
        from urllib.parse import quote
        c = self.config
        return (
            f"{_HTML_URL}"
            f"?color0={quote(c.get('color0', '5227FF'))}"
            f"&color1={quote(c.get('color1', '00C2FF'))}"
            f"&color2={quote(c.get('color2', '5227FF'))}"
            f"&amplitude={c.get('amplitude', 1.0)}"
            f"&blend={c.get('blend', 0.5)}"
            f"&speed={c.get('speed', 0.8)}"
        )


# ════════════════════════════════════════════════════════════
# Convenience-Funktion
# ════════════════════════════════════════════════════════════

def attach_aurora_to_frame(
    frame: tk.Misc,
    config: Optional[Dict] = None,
) -> AuroraBackground:
    """
    Bindet Aurora direkt in einen sichtbaren Tkinter/CTk Frame.
    Gibt die AuroraBackground-Instanz zurück (für .stop() beim Schließen).
    """
    bg = AuroraBackground(frame, config=config)
    bg.start()
    return bg
