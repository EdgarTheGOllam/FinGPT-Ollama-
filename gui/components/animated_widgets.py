import tkinter as tk
import math
from typing import Optional


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_out_elastic(t: float, amplitude: float = 1.0, period: float = 0.3) -> float:
    if t == 0 or t == 1:
        return t
    s = period / (2 * math.pi) * math.asin(1 / amplitude)
    return amplitude * (2 ** (-10 * t)) * math.sin((t - s) * (2 * math.pi) / period) + 1


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(color1: str, color2: str, t: float) -> str:
    """Interpoliert zwischen zwei Hex-Farben."""

    def hex_to_rgb(hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def rgb_to_hex(r: float, g: float, b: float) -> str:
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    c1 = hex_to_rgb(color1)
    c2 = hex_to_rgb(color2)

    r = lerp(c1[0], c2[0], t)
    g = lerp(c1[1], c2[1], t)
    b = lerp(c1[2], c2[2], t)

    return rgb_to_hex(r, g, b)


class TrendArrowWidget:
    """Canvas-Widget für rotierenden Pfeil."""

    def __init__(self, parent, size: int = 16):
        self.size = size
        self.current_angle = 0
        self.target_angle = 0
        self._animation_job = None

        # Canvas erstellen
        self.canvas = tk.Canvas(
            parent, width=size, height=size, highlightthickness=0, bg="transparent"
        )
        self.canvas.pack(side="left", padx=(0, 2))

        # Pfeil als Polygon (Dreieck)
        padding = 2
        cx = size / 2
        cy = size / 2
        r = (size / 2) - padding

        # Pfeil zeigt nach oben (▲)
        self.arrow_id = self.canvas.create_polygon(
            cx,
            cy - r,  # Top
            cx - r,
            cy + r * 0.6,  # Bottom left
            cx + r,
            cy + r * 0.6,  # Bottom right
            fill="#FFFFFF",
            outline="",
        )

    def animate_rotation(
        self, target_angle: float, duration_ms: float = 500, callback=None
    ):
        """Animiert Rotation von current_angle zu target_angle."""
        if self._animation_job:
            self.canvas.after_cancel(self._animation_job)

        start_angle = self.current_angle
        self.target_angle = target_angle
        start_time = None

        def animate(timestamp):
            nonlocal start_time
            if start_time is None:
                start_time = timestamp

            elapsed = timestamp - start_time
            progress = min(elapsed / duration_ms, 1.0)

            # Easing anwenden
            eased_progress = ease_out_elastic(progress)

            # Aktuellen Winkel berechnen
            angle = lerp(start_angle, target_angle, eased_progress)
            self._rotate_arrow(angle)

            if progress < 1.0:
                self._animation_job = self.canvas.after(
                    16, lambda: animate(self.canvas.winfo_fpixels("."))
                )
            else:
                self.current_angle = target_angle
                if callback:
                    callback()

        self._animation_job = self.canvas.after(
            16, lambda: animate(self.canvas.winfo_fpixels("."))
        )

    def _rotate_arrow(self, angle: float):
        """Rotiert den Pfeil um den gegebenen Winkel."""
        cx = self.size / 2
        cy = self.size / 2
        padding = 2
        r = (self.size / 2) - padding

        # Neue Koordinaten basierend auf Rotation
        rad = math.radians(angle)

        # Punkte berechnen
        p1 = (cx + r * math.sin(rad), cy - r * math.cos(rad))
        p2 = (
            cx + r * 0.7 * math.sin(rad + 2 * math.pi / 3),
            cy - r * 0.7 * math.cos(rad + 2 * math.pi / 3),
        )
        p3 = (
            cx + r * 0.7 * math.sin(rad - 2 * math.pi / 3),
            cy - r * 0.7 * math.cos(rad - 2 * math.pi / 3),
        )

        self.canvas.coords(self.arrow_id, p1[0], p1[1], p2[0], p2[1], p3[0], p3[1])

    def set_rotation(self, angle: float):
        """Setzt Rotation sofort (ohne Animation)."""
        self.current_angle = angle
        self._rotate_arrow(angle)

    def destroy(self):
        """Destroy the widget."""
        if self._animation_job:
            self.canvas.after_cancel(self._animation_job)
        self.canvas.destroy()


class NumberFlowValue:
    """Animiert Zahlen von altem zu neuem Wert mit NumberFlow-Effekt."""

    # Farben
    BADGE_POSITIVE = "#10B981"
    BADGE_NEGATIVE = "#EF4444"

    def __init__(self, parent, initial_value: str = "0"):
        self.parent = parent
        self.current_value = initial_value
        self._animation_job = None
        self._start_value = 0.0
        self._target_value = 0.0
        self._start_color = self.BADGE_POSITIVE

        # Container für Value + Badge
        self._container = tk.Frame(parent, bg="transparent")
        self._container.pack(side="left")

        # Value Label (groß)
        self.value_label = tk.Label(
            self._container,
            text=initial_value,
            font=("Inter", 28, "bold"),
            fg="#FFFFFF",
            bg="#1A1D24",
        )
        self.value_label.pack(side="left")

    def _parse_value(self, value_str: str) -> float:
        """Parst einen String zu Float für Animation."""
        # Entferne Währungssymbole und Prozent
        cleaned = (
            value_str.replace("€", "")
            .replace("$", "")
            .replace("%", "")
            .replace(",", "")
            .strip()
        )

        # Behandle Vorzeichen
        is_negative = cleaned.startswith("-") or cleaned.startswith("(")
        cleaned = cleaned.replace("-", "").replace("(", "").replace(")", "")

        try:
            val = float(cleaned)
            return -val if is_negative else val
        except:
            return 0.0

    def _format_value(self, value: float, original_format: str) -> str:
        """Formatiert den Wert zurück zum Original-Format."""
        # Behalte das Format des Original-Werts bei
        if "€" in original_format:
            return f"€{value:,.2f}".replace(",", ".")
        elif "$" in original_format:
            return f"${value:,.2f}".replace(",", ".")
        elif "%" in original_format:
            return f"{value:.2f}%"
        else:
            return f"{value:,.2f}".replace(",", ".")

    def animate(
        self, new_value: str, duration_ms: float = 900, trend: Optional[str] = None
    ):
        """Animiert von altem zu neuem Wert."""
        if self._animation_job:
            self.parent.after_cancel(self._animation_job)

        # Alten und neuen Wert parsen
        self._start_value = self._parse_value(self.current_value)
        self._target_value = self._parse_value(new_value)

        if self._start_value == self._target_value:
            self.value_label.configure(text=new_value)
            self.current_value = new_value
            return

        start_time = None
        original_format = new_value

        def animate(timestamp):
            nonlocal start_time
            if start_time is None:
                start_time = timestamp

            elapsed = timestamp - start_time
            progress = min(elapsed / duration_ms, 1.0)

            # Easing anwenden
            eased_progress = ease_out_cubic(progress)

            # Aktuellen Wert berechnen
            current = lerp(self._start_value, self._target_value, eased_progress)

            # Formatieren und anzeigen
            self.value_label.configure(
                text=self._format_value(current, original_format)
            )

            if progress < 1.0:
                self._animation_job = self.parent.after(
                    16, lambda: animate(self.parent.winfo_fpixels("."))
                )
            else:
                self.value_label.configure(text=new_value)
                self.current_value = new_value

        self._animation_job = self.parent.after(
            16, lambda: animate(self.parent.winfo_fpixels("."))
        )

    def destroy(self):
        """Destroy the widget."""
        if self._animation_job:
            self.parent.after_cancel(self._animation_job)
        self._container.destroy()


class AnimatedBadge:
    """Animiertes Badge mit Farb-Übergang."""

    BADGE_POSITIVE = "#10B981"
    BADGE_NEGATIVE = "#EF4444"
    BADGE_NEUTRAL = "#8B949E"

    def __init__(self, parent, initial_color: Optional[str] = None):
        self.parent = parent
        self.current_color = initial_color or self.BADGE_NEUTRAL

        # Badge Container
        self.badge = tk.Frame(
            parent,
            bg=self.current_color,
            padx=10,
            pady=4,
        )
        self.badge.pack(side="left", padx=(12, 0), fill="y")
        self.badge.pack_propagate(False)
        self.badge.configure(width=70, height=28)

        # Innerer Container (transparent)
        self.inner = tk.Frame(self.badge, bg="transparent")
        self.inner.pack(fill="both", expand=True, padx=8)

    def animate_color(self, target_color: str, duration_ms: float = 300):
        """Animiert Farbwechsel sanft."""

        def hex_to_rgb(hex_color: str) -> tuple:
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

        start_rgb = hex_to_rgb(self.current_color)
        target_rgb = hex_to_rgb(target_color)

        start_time = None

        def animate(timestamp):
            nonlocal start_time
            if start_time is None:
                start_time = timestamp

            elapsed = timestamp - start_time
            progress = min(elapsed / duration_ms, 1.0)

            eased_progress = ease_out_cubic(progress)

            new_color = lerp_color(
                f"#{start_rgb[0]:02x}{start_rgb[1]:02x}{start_rgb[2]:02x}",
                f"#{target_rgb[0]:02x}{target_rgb[1]:02x}{target_rgb[2]:02x}",
                eased_progress,
            )

            self.badge.configure(bg=new_color)
            self.current_color = new_color

            if progress < 1.0:
                self.badge.after(16, lambda: animate(self.badge.winfo_fpixels(".")))

        self.badge.after(16, lambda: animate(self.badge.winfo_fpixels(".")))

    def set_color(self, color: str):
        """Setzt Farbe sofort (ohne Animation)."""
        self.badge.configure(bg=color)
        self.current_color = color

    def get_inner(self):
        """Gibt den inneren Container zurück für weitere Widgets."""
        return self.inner

    def destroy(self):
        """Destroy the widget."""
        self.badge.destroy()
