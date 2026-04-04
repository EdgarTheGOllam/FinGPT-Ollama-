import tkinter as tk
from tkinter import TclError
import customtkinter as ctk
from typing import Tuple, Optional


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Konvertiert Hex-Farbe zu RGB-Tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Konvertiert RGB zu Hex-Farbe."""
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def blend_colors(base_hex: str, overlay_hex: str, alpha: float) -> str:
    """Blendet zwei Farben mit Alpha-Wert (0.0-1.0)."""
    base = hex_to_rgb(base_hex)
    overlay = hex_to_rgb(overlay_hex)
    r = base[0] * (1 - alpha) + overlay[0] * alpha
    g = base[1] * (1 - alpha) + overlay[1] * alpha
    b = base[2] * (1 - alpha) + overlay[2] * alpha
    return rgb_to_hex(int(r), int(g), int(b))


class SpotlightOverlay:
    """
    Canvas-basierter Spotlight-Effekt fr MetricCards.
    Erzeugt einen radialen Gradienten, der dem Mauszeiger folgt.
    """

    def __init__(
        self,
        parent,
        spotlight_color: str = "#4B5563",
        spotlight_radius: int = 150,
        intensity: float = 0.15,
        border_glow_color: str = "#60A5FA",
        border_glow_intensity: float = 0.4,
    ):
        self.parent = parent
        self.spotlight_color = spotlight_color
        self.radius = spotlight_radius
        self.intensity = intensity
        self.border_glow_color = border_glow_color
        self.border_glow_intensity = border_glow_intensity

        self.mouse_x = 0
        self.mouse_y = 0
        self.is_hovering = False
        self._draw_timer = None

        # Canvas wird spter erstellt, wenn die Parent-Grcke bekannt ist
        self.canvas = None
        self._setup_done = False

        # Bind mouse events on parent and all children
        self._bind_hover_events(parent)

    def _bind_hover_events(self, widget):
        """Bindet Mouse-Events rekursiv auf Widget und allen Kindern."""
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<Motion>", self._on_motion, add="+")
        for child in widget.winfo_children():
            self._bind_hover_events(child)

    def _ensure_canvas(self):
        """Erstellt das Canvas-Overlay beim ersten Hover."""
        if self._setup_done:
            return

        try:
            w = self.parent.winfo_width()
            h = self.parent.winfo_height()
        except tk.TclError:
            return

        if w <= 1 or h <= 1:
            return

        # Canvas über dem gesamten Parent erstellen - WICHTIG: Transparenter Hintergrund
        self.canvas = tk.Canvas(
            self.parent,
            width=w,
            height=h,
            highlightthickness=0,
            bg="",  # Transparent - kein Hintergrund!
        )
        # Canvas-Konfiguration: komplett transparent machen
        self.canvas.configure(bg=self.parent.cget("fg_color") or "#1E2228")

        # Das Canvas muss HINTER allen anderen Widgets liegen
        # Da lower() ohne Argumente in neueren Tkinter-Versionen nicht funktioniert,
        # verwenden wir einen alternativen Trick: canvas mit lower() auf ein existierendes Geschwister
        try:
            # Versuche alle Geschwister-Widgets zu finden, die vor dem Canvas liegen sollten
            siblings = self.parent.winfo_children()
            if siblings:
                # Finde das erste Geschwister und setze es vor unser Canvas
                first_sibling = siblings[0]
                self.canvas.lower(first_sibling)
            else:
                # Keine Geschwister - versuche es ohne Argumente (funktioniert in älterem Tkinter)
                self.canvas.lower()
        except (TclError, tk.TclError, AttributeError):
            # Fallback: after() mit verzögertem Versuch
            def lower_canvas():
                try:
                    siblings = self.parent.winfo_children()
                    if siblings:
                        self.canvas.lower(siblings[0])
                except Exception:
                    pass

            self.parent.after(100, lower_canvas)

        # Positioniere das Canvas
        self.canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        # Canvas-Events fr Mausverfolgung
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)

        self._setup_done = True

    def _on_enter(self, event):
        self.is_hovering = True
        self._ensure_canvas()
        if event:
            self.mouse_x = event.x
            self.mouse_y = event.y
        self._draw_spotlight()

    def _on_leave(self, event):
        self.is_hovering = False
        if self._draw_timer:
            self.parent.after_cancel(self._draw_timer)
            self._draw_timer = None
        self._clear_spotlight()

    def _on_motion(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y
        if self.is_hovering:
            if self._draw_timer:
                self.parent.after_cancel(self._draw_timer)
            # Verzgertes Neuzeichnen fr Performance
            self._draw_timer = self.parent.after(16, self._draw_spotlight)

    def _draw_spotlight(self):
        """Zeichnet den radialen Spotlight-Gradienten."""
        if not self.canvas or not self.is_hovering:
            return

        try:
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
        except tk.TclError:
            return

        if w <= 1 or h <= 1:
            return

        self.canvas.delete("spotlight")

        cx = self.mouse_x
        cy = self.mouse_y
        r = self.radius

        # Radialer Gradient mit konzentrischen Kreisen
        steps = 20
        for i in range(steps, 0, -1):
            alpha = (i / steps) * self.intensity
            current_r = r * (i / steps)

            color = blend_colors("#1E2228", self.spotlight_color, alpha)

            x0 = cx - current_r
            y0 = cy - current_r
            x1 = cx + current_r
            y1 = cy + current_r

            self.canvas.create_oval(
                x0,
                y0,
                x1,
                y1,
                fill=color,
                outline="",
                tags="spotlight",
            )

        # Border-Glow-Effekt (subtile Kantenbeleuchtung)
        self._draw_border_glow(cx, cy, w, h)

    def _draw_border_glow(self, cx: float, cy: float, w: int, h: int):
        """Zeichnet einen subtilen Glow-Effekt an den Card-Kanten."""
        glow_width = 2
        alpha = self.border_glow_intensity

        # Berechne Distanz vom Mauszeiger zu jeder Kante
        dist_top = cy
        dist_bottom = h - cy
        dist_left = cx
        dist_right = w - cx

        min_dist = min(dist_top, dist_bottom, dist_left, dist_right)
        max_dist = max(w, h) / 2

        # Glow-Strke basierend auf Nhe zur Kante
        edge_alpha = max(0, alpha * (1 - min_dist / (max_dist * 0.5)))

        if edge_alpha > 0.02:
            glow_color = blend_colors("#2A2D34", self.border_glow_color, edge_alpha)

            # Oben
            if dist_top < self.radius:
                a = max(0, edge_alpha * (1 - dist_top / self.radius))
                c = blend_colors("#2A2D34", self.border_glow_color, a)
                self.canvas.create_rectangle(
                    0, 0, w, glow_width, fill=c, outline="", tags="spotlight"
                )
            # Unten
            if dist_bottom < self.radius:
                a = max(0, edge_alpha * (1 - dist_bottom / self.radius))
                c = blend_colors("#2A2D34", self.border_glow_color, a)
                self.canvas.create_rectangle(
                    0, h - glow_width, w, h, fill=c, outline="", tags="spotlight"
                )
            # Links
            if dist_left < self.radius:
                a = max(0, edge_alpha * (1 - dist_left / self.radius))
                c = blend_colors("#2A2D34", self.border_glow_color, a)
                self.canvas.create_rectangle(
                    0, 0, glow_width, h, fill=c, outline="", tags="spotlight"
                )
            # Rechts
            if dist_right < self.radius:
                a = max(0, edge_alpha * (1 - dist_right / self.radius))
                c = blend_colors("#2A2D34", self.border_glow_color, a)
                self.canvas.create_rectangle(
                    w - glow_width, 0, w, h, fill=c, outline="", tags="spotlight"
                )

    def _clear_spotlight(self):
        """Entfernt den Spotlight-Effekt."""
        if self.canvas:
            self.canvas.delete("spotlight")

    def update_bindings(self):
        """Aktualisiert Event-Bindings nach Widget-nderungen."""
        self._bind_hover_events(self.parent)
