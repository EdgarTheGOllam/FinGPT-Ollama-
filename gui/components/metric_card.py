import customtkinter as ctk
import tkinter as tk
from gui.design_system import DesignSystem
from gui.components.interactive_frame import HoverFadeFrame
from gui.components.spotlight_overlay import SpotlightOverlay
from typing import Optional, Callable
import threading
import re
import math


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


class MetricCard(HoverFadeFrame):
    """
    Eine wiederverwendbare Metrik-Karte mit modernem Design, Icon, Trend-Anzeige und Hover-Interaction.
    Verwendet das zentrale Design-System für konsistente Farben und Abstände.

    Design inspiriert von NumberFlow/Trading-UI:
    - Großer Wert-Display mit Währungsformatierung
    - Farbcodierter Prozentsatz-Indikator (Grün/Rot)
    - Animierter Pfeil-Indikator
    """

    # Icon-Mapping (Verwendung von Symbols für reine Farbsteuerung statt System-Emojis)
    ICONS = {
        "balance": "✦",  # Kontostand
        "positions": "■",  # Positionen
        "trades": "▲",  # Trades
        "pnl": "●",  # Gewinn/Verlust
        "winrate": "★",  # Win Rate / Margin
        "risk": "◆",  # Risiko / Freie Margin
        "default": "❖",  # Standard
    }

    # Spezifische elegante Premium-Farben für jedes Icon
    ICON_COLORS = {
        "balance": "#10B981",    # Emerald
        "positions": "#F59E0B",  # Amber
        "trades": "#38BDF8",     # Light Blue
        "pnl": "#EF4444",        # Red
        "winrate": "#818CF8",    # Indigo
        "risk": "#F97316",       # Orange
        "default": "#A1A1AA",    # Zinc-400
    }

    # Farben für Trend-Indikatoren (modern Trading-UI Style)
    TREND_COLORS = {
        "positive": "#10B981",  # Emerald Grün
        "negative": "#EF4444",  # Rot
        "neutral": "#71717A",   # Zinc-500
    }

    # Trading-UI Badge-Farben (gedämpft für harmonisches Dark-Theme)
    BADGE_POSITIVE = "#0EA572"  # Gedämpftes Emerald
    BADGE_NEGATIVE = "#E84040"  # Gedämpftes Rot

    def __init__(
        self,
        master,
        title,
        value,
        icon_type="default",
        trend=None,
        trend_value=None,
        min_width=None,
        max_width=None,
        **kwargs,
    ):
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
        self._min_width = min_width or ds.get_min_width_for_breakpoint("metric_card")
        self._max_width = max_width

        radius = ds.get_radius("md")

        # Neue einheitliche Farben aus dem Designsystem
        card_bg     = ds.BG['card']           # '#13151A' — einheitlich für alle Cards
        border_idle = ds.BORDERS['subtle']    # '#1E2128' — sehr subtil
        border_hover= ds.BORDERS['active']    # '#353A47' — sanfte Aufhellung beim Hover

        # Standard-Parameter
        default_kwargs = {
            "corner_radius": radius,
            "border_width": 1,
            "border_color": border_idle,
        }
        config = {**default_kwargs, **kwargs}

        # Hauptframe: einheitlicher bg_card Hintergrund, sanfter Hover-Rahmen
        super().__init__(
            master,
            active_bg_color=card_bg,
            idle_border_color=border_idle,
            active_border_color=border_hover,
            draggable=True,
            **config,
        )

        # Konfiguriere minimale Breite
        self.configure(width=self._min_width)

        self.icon_type = icon_type
        self.trend = trend
        self.trend_value = trend_value
        self._current_value = value

        # ─────────────────────────────────────────────────────────
        # MODERN TRADING-UI LAYOUT (inspiriert von NumberFlow)
        # ─────────────────────────────────────────────────────────

        # Padding
        padding = 20

        # Main container - vertically stacked
        self._main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._main_frame.pack(fill="both", expand=True, padx=padding, pady=padding)

        # Row 1: Value + Trend Badge (wie NumberFlow Trading UI)
        self._value_row = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        self._value_row.pack(fill="x", pady=(0, 8))

        # 1. Value Label (groß, prominent) - mit Animation
        value_font = ctk.CTkFont(family="Inter", size=22, weight="bold")
        self.value_label = ctk.CTkLabel(
            self._value_row,
            text=value,
            font=value_font,
            text_color=("#09090B", "#FFFFFF"),
        )
        self.value_label.pack(side="left")

        # Speichere ursprünglichen Wert für Animation
        self._start_numeric_value = self._parse_value(value)

        # Starte sanfte Einstieg-Animation (Zahl zählt von 0 hoch)
        self.after(100, lambda: self._animate_value_intro(value))

        # 2. Trend Badge (farbcodiert mit rotierendem Pfeil)
        self._trend = trend
        if trend and trend_value:
            # Bestimme Farbe basierend auf Trend
            if trend == "up":
                badge_color = self.BADGE_POSITIVE
                target_angle = 0  # Pfeil zeigt nach oben
            elif trend == "down":
                badge_color = self.BADGE_NEGATIVE
                target_angle = 180  # Pfeil zeigt nach unten
            else:
                badge_color = "#8B949E"
                target_angle = 0

            # Trend Badge Container (gerundet, mit Farbe)
            self.trend_badge = ctk.CTkFrame(
                self._value_row,
                fg_color=badge_color,
                corner_radius=12,
            )
            self.trend_badge.pack(side="left", padx=(12, 0), fill="y")
            self.trend_badge.pack_propagate(False)
            self.trend_badge.configure(width=70, height=28)

            # Trend Content Container
            trend_inner = ctk.CTkFrame(self.trend_badge, fg_color="transparent")
            trend_inner.pack(fill="both", expand=True, padx=8)

            # Canvas für rotierenden Pfeil
            arrow_canvas = tk.Canvas(
                trend_inner, width=14, height=14, highlightthickness=0, bg=badge_color
            )
            arrow_canvas.pack(side="left", padx=(0, 2))

            # Pfeil als Polygon zeichnen
            self._arrow_id = arrow_canvas.create_polygon(
                7,
                2,  # Top
                2,
                12,  # Bottom left
                12,
                12,  # Bottom right
                fill="#FFFFFF",
                outline="",
            )
            self._arrow_canvas = arrow_canvas
            self._current_angle = 0

            # Starte sanfte Einstieg-Rotation
            self.after(300, lambda: self._animate_arrow_rotation(target_angle, 800))

            # Prozent-Wert
            self.trend_value_label = ctk.CTkLabel(
                trend_inner,
                text=self._format_percentage(trend_value),
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#FFFFFF",
            )
            self.trend_value_label.pack(side="left")

        # Row 2: Title + Icon
        self._title_row = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        self._title_row.pack(fill="x")

        # Icon
        icon_text = self.ICONS.get(icon_type, self.ICONS["default"])
        icon_color = self.ICON_COLORS.get(icon_type, self.ICON_COLORS["default"])

        self.icon_label = ctk.CTkLabel(
            self._title_row,
            text=icon_text,
            font=ctk.CTkFont(size=14),
            text_color=icon_color,
        )
        self.icon_label.pack(side="left", padx=(0, 6))

        # Title
        title_font = ctk.CTkFont(family="Inter", size=13, weight="bold")
        self.title_label = ctk.CTkLabel(
            self._title_row,
            text=title,
            font=title_font,
            text_color=ds.SEMANTIC.get('neutral', ('#71717A', '#A1A1AA')),
        )
        self.title_label.pack(side="left")

        # Spotlight-Effekt: Radialer Gradient folgt dem Mauszeiger
        self.spotlight = SpotlightOverlay(
             self,
             spotlight_color="#60A5FA",  # Blauer Spotlight
             spotlight_radius=120,
             intensity=0.12,
             border_glow_color="#4B5563",
             border_glow_intensity=0.3,
        )

        # Event-Bindings für Hover-Animation auf allen relevanten Widgets werden nun im HoverFadeFrame geregelt

    # ─────────────────────────────────────────────────────────
    # Animation Helper Methods
    # ─────────────────────────────────────────────────────────

    def _parse_value(self, value_str: str) -> float:
        """Parst einen String zu Float für Animation."""
        cleaned = (
            value_str.replace("€", "")
            .replace("$", "")
            .replace("%", "")
            .replace(",", "")
            .strip()
        )
        is_negative = cleaned.startswith("-") or cleaned.startswith("(")
        cleaned = cleaned.replace("-", "").replace("(", "").replace(")", "")
        try:
            val = float(cleaned)
            return -val if is_negative else val
        except:
            return 0.0

    def _format_value(self, value: float, original_format: str) -> str:
        """Formatiert den Wert zurück zum Original-Format."""
        if "€" in original_format:
            return f"€{value:,.2f}".replace(",", ".")
        elif "$" in original_format:
            return f"${value:,.2f}".replace(",", ".")
        elif "%" in original_format:
            return f"{value:.2f}%"
        else:
            return f"{value:,.2f}".replace(",", ".")

    def _animate_value_intro(self, target_value: str):
        """Sanfte Einstieg-Animation: Zahl zählt von 0 hoch zum Zielwert."""
        target = self._parse_value(target_value)
        if target <= 0:
            self.value_label.configure(text=target_value)
            return

        duration_ms = 800
        start_time = None
        original_format = target_value

        def animate():
            nonlocal start_time
            timestamp = time.time() * 1000
            if start_time is None:
                start_time = timestamp

            elapsed = timestamp - start_time
            progress = min(elapsed / duration_ms, 1.0)
            eased = ease_out_cubic(progress)

            current = lerp(0, target, eased)
            self.value_label.configure(
                text=self._format_value(current, original_format)
            )

            if progress < 1.0:
                self.after(16, animate)
            else:
                self.value_label.configure(text=target_value)

        import time
        self.after(16, animate)

    def _animate_value_update(self, new_value: str):
        """Animiert Value-Update von altem zu neuem Wert."""
        old_value = self._current_value
        target = self._parse_value(new_value)
        start = self._parse_value(old_value)

        if start == target:
            self.value_label.configure(text=new_value)
            return

        duration_ms = 900
        start_time = None
        original_format = new_value

        def animate():
            nonlocal start_time
            timestamp = time.time() * 1000
            if start_time is None:
                start_time = timestamp

            elapsed = timestamp - start_time
            progress = min(elapsed / duration_ms, 1.0)
            eased = ease_out_cubic(progress)

            current = lerp(start, target, eased)
            self.value_label.configure(
                text=self._format_value(current, original_format)
            )

            if progress < 1.0:
                self.after(16, animate)
            else:
                self.value_label.configure(text=new_value)

        import time
        self.after(16, animate)

    def _animate_arrow_rotation(self, target_angle: float, duration_ms: float = 500):
        """Animiert die Rotation des Pfeils."""
        if not hasattr(self, "_arrow_canvas") or not self._arrow_canvas:
            return

        start_angle = self._current_angle
        start_time = None

        def animate():
            nonlocal start_time, start_angle
            timestamp = time.time() * 1000
            if start_time is None:
                start_time = timestamp

            elapsed = timestamp - start_time
            progress = min(elapsed / duration_ms, 1.0)
            eased = ease_out_elastic(progress)

            angle = lerp(start_angle, target_angle, eased)
            self._rotate_arrow(angle)

            if progress < 1.0:
                self.after(16, animate)
            else:
                self._current_angle = target_angle

        import time
        self.after(16, animate)

    def _rotate_arrow(self, angle: float):
        """Rotiert den Pfeil um den gegebenen Winkel."""
        if not hasattr(self, "_arrow_id") or not self._arrow_canvas:
            return

        cx = 7
        cy = 7
        r = 5

        rad = math.radians(angle)

        p1 = (cx + r * math.sin(rad), cy - r * math.cos(rad))
        p2 = (
            cx + r * 0.7 * math.sin(rad + 2 * math.pi / 3),
            cy - r * 0.7 * math.cos(rad + 2 * math.pi / 3),
        )
        p3 = (
            cx + r * 0.7 * math.sin(rad - 2 * math.pi / 3),
            cy - r * 0.7 * math.cos(rad - 2 * math.pi / 3),
        )

        self._arrow_canvas.coords(
            self._arrow_id, p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]
        )

    def _animate_badge_color(self, target_color: str, duration_ms: float = 300):
        """Animiert Farbwechsel des Badge."""
        if not hasattr(self, "trend_badge") or not self.trend_badge:
            return

        start_color = self.trend_badge.cget("fg_color") or "#8B949E"
        start_time = None

        def animate():
            nonlocal start_time
            timestamp = time.time() * 1000
            if start_time is None:
                start_time = timestamp

            elapsed = timestamp - start_time
            progress = min(elapsed / duration_ms, 1.0)
            eased = ease_out_cubic(progress)

            new_color = lerp_color(start_color, target_color, eased)
            self.trend_badge.configure(fg_color=new_color)

            if progress < 1.0:
                self.after(16, animate)

        import time
        self.after(16, animate)

    # ─────────────────────────────────────────────────────────
    # Public Methods
    # ─────────────────────────────────────────────────────────

    def _format_percentage(self, value: str) -> str:
        """Formatiert den Prozent-Wert für die Anzeige."""
        if not value:
            return "0%"

        # Bereits formatiert?
        if "%" in value:
            return value

        # Versuche als Zahl zu parsen
        try:
            num = float(value.replace(",", ".").replace("%", ""))
            return f"{num:+.2f}%"
        except:
            return value

    def _get_responsive_icon_size(self, window_width: int) -> int:
        """Berechnet responsive Icon-Größe basierend auf Fensterbreite."""
        ds = DesignSystem
        base_size = ds.COMPONENTS["metric_card"]["icon_size"]

        if window_width < ds.BREAKPOINTS["sm"]:
            return int(base_size * 0.75)
        elif window_width < ds.BREAKPOINTS["md"]:
            return int(base_size * 0.85)
        return base_size

    def update_value(self, new_value, trend=None, trend_value=None):
        """
        Aktualisiert den Wert der Karte.

        Args:
            new_value: Neuer Wert (String)
            trend: Optional, neuer Trend ('up', 'down', 'neutral')
            trend_value: Optional, neuer Trend-Wert
        """
        self.value_label.configure(text=new_value)
        self._current_value = new_value

        if trend is not None and trend_value is not None:
            # Update das Badge wenn trend vorhanden
            if hasattr(self, "trend_badge"):
                # Bestimme neue Farbe
                new_badge_color = (
                    self.BADGE_POSITIVE
                    if trend == "up"
                    else self.BADGE_NEGATIVE
                    if trend == "down"
                    else "#8B949E"
                )

                # Bestimme Zielwinkel für Pfeil-Rotation
                target_angle = 0 if trend == "up" else 180 if trend == "down" else 0

                # Animiere Farbwechsel
                self._animate_badge_color(new_badge_color, 300)

                # Animiere Pfeil-Rotation
                if hasattr(self, "_arrow_canvas"):
                    self._animate_arrow_rotation(target_angle, 500)

                # Update Prozent-Wert
                if hasattr(self, "trend_value_label"):
                    self.trend_value_label.configure(
                        text=self._format_percentage(trend_value)
                    )

        # Zusätzlich: Value-Zahlen-Animation (von altem zu neuem Wert)
        self._animate_value_update(new_value)

    def set_icon(self, icon_type):
        """Ändert das Icon der Karte."""
        if icon_type in self.ICONS:
            self.icon_type = icon_type
            self.icon_label.configure(
                text=self.ICONS[icon_type],
                text_color=self.ICON_COLORS.get(icon_type, self.ICON_COLORS["default"]),
            )

    def highlight_change(self, duration_ms=500):
        """
        Hervorhebung bei Wertänderung (Wertetext leuchtet kurz auf).

        Args:
            duration_ms: Dauer der Hervorhebung in Millisekunden
        """
        original_color = ("#09090B", "#FFFFFF")
        flash_color = "#38BDF8"  # Premium Light Blue

        # Leucht-Effekt auf dem Wertetext
        if hasattr(self, "value_label") and self.value_label.winfo_exists():
            self.value_label.configure(text_color=flash_color)
            self.after(
                duration_ms,
                lambda: (
                    self.value_label.configure(text_color=original_color)
                    if self.value_label.winfo_exists()
                    else None
                ),
            )


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
    card1 = MetricCard(
        test_frame,
        "Kontostand",
        "€12,345.67",
        icon_type="balance",
        trend="up",
        trend_value="+2.5%",
    )
    card1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    # Karte 2: Offene Positionen (neutral)
    card2 = MetricCard(test_frame, "Offene Positionen", "5", icon_type="positions")
    card2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

    # Karte 3: P&L mit negativem Trend
    card3 = MetricCard(
        test_frame,
        "Gewinn/Verlust",
        "-€234.50",
        icon_type="pnl",
        trend="down",
        trend_value="-1.2%",
    )
    card3.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

    # Karte 4: Win Rate
    card4 = MetricCard(
        test_frame,
        "Win Rate",
        "68.5%",
        icon_type="winrate",
        trend="up",
        trend_value="+3%",
    )
    card4.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    # Karte 5: Risiko
    card5 = MetricCard(test_frame, "Freie Margin", "€5,432.10", icon_type="risk")
    card5.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

    # Karte 6: Trades
    card6 = MetricCard(
        test_frame,
        "Heutige Trades",
        "23",
        icon_type="trades",
        trend="up",
        trend_value="+5",
    )
    card6.grid(row=1, column=2, padx=10, pady=10, sticky="nsew")

    # Test-Button für Wert-Update
    def update_values():
        import random

        card1.update_value(
            f"€{random.randint(10000, 20000):,}.{random.randint(0, 99):02d}",
            trend="up" if random.random() > 0.5 else "down",
            trend_value=f"{random.choice(['+', '-'])}{random.randint(1, 5)}.{random.randint(0, 9)}%",
        )
        card3.update_value(
            f"€{random.randint(-500, 500):+}",
            trend="up" if random.random() > 0.5 else "down",
            trend_value=f"{random.choice(['+', '-'])}{random.randint(1, 5)}.{random.randint(0, 9)}%",
        )

    update_btn = ctk.CTkButton(root, text="Werte aktualisieren", command=update_values)
    update_btn.pack(pady=10)

    root.mainloop()
