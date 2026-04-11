"""
SonarAnimation – GSAP-inspirierte Canvas-Animation für das FinGPT-Dashboard.

Verbesserungen v2:
  1. BG-Farbe dynamisch aus DesignSystem.BG['card'] — kein hardcodierter Ton mehr
  2. Breathing-Idle-Effekt: Ringe pulsieren sanft wie ein Atemzug
  3. Echter Radar-Sweep (rotierender Keil-Scan-Effekt)
  4. Farbcodiertes State-System: idle / analyzing / trading / error
  5. Multi-Layer Glow für den Core-Dot (Bloom / 3D-Kugel-Optik)

Technisch:
  - Easing-Kurven (ease-out-cubic, elastic, bounce) statt linearer Bewegung
  - Partikel-System mit Lebenszeit, Fade-out und Trails
  - Pulse-Wellen mit exponentieller Expansion
  - AI-Bubble-Texte mit Parallax-Scroll
  - Alles in einem einzigen Tkinter-Canvas-Widget
  - Animationsschleife über self.after() – kein Threading → kein Tkinter-Ärger
"""

import tkinter as tk
import math
import random
from datetime import datetime


# ────────────────────────────────────────────
#   Easing helpers  (analog zu GSAP Easings)
# ────────────────────────────────────────────

def ease_out_cubic(t: float) -> float:
    """Verlangsamt am Ende — smoothe Ankunft."""
    return 1 - (1 - t) ** 3


def ease_in_out_sine(t: float) -> float:
    return -(math.cos(math.pi * t) - 1) / 2


def ease_out_elastic(t: float, amplitude: float = 1.0, period: float = 0.3) -> float:
    """Leichter Bounce-Über-Effekt."""
    if t == 0 or t == 1:
        return t
    s = period / (2 * math.pi) * math.asin(1 / amplitude)
    return amplitude * (2 ** (-10 * t)) * math.sin((t - s) * (2 * math.pi) / period) + 1


# ────────────────────────────────────────────
#   Color helpers
# ────────────────────────────────────────────

def lerp_color(c1: tuple, c2: tuple, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r = int(c1[0] + (c2[0] - c1[0]) * t)
    g = int(c1[1] + (c2[1] - c1[1]) * t)
    b = int(c1[2] + (c2[2] - c1[2]) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgb(h: str) -> tuple:
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rgba_str(r, g, b, a: float, bg_rgb: tuple = (19, 21, 26)) -> str:
    """Gibt einen Tkinter-kompatiblen Hex-Farbstring mit Alpha-Annäherung zurück.
    
    VERBESSERUNG #1: bg_rgb ist jetzt ein Parameter (Standard = bg_card #13151A),
    statt hardcodiertem (11,14,20) = #0B0E14. Alle Pulse/Partikel werden korrekt
    gegen den Kartenhintergrund geblended.
    """
    a = max(0.0, min(1.0, a))
    r2 = int(bg_rgb[0] + (r - bg_rgb[0]) * a)
    g2 = int(bg_rgb[1] + (g - bg_rgb[1]) * a)
    b2 = int(bg_rgb[2] + (b - bg_rgb[2]) * a)
    r2 = max(0, min(255, r2))
    g2 = max(0, min(255, g2))
    b2 = max(0, min(255, b2))
    return f"#{r2:02x}{g2:02x}{b2:02x}"


# ────────────────────────────────────────────
#   State-Definition  (Verbesserung #4)
# ────────────────────────────────────────────

STATE_CONFIG = {
    "idle": {
        "core_rgb":   (26, 100, 80),
        "pulse_rgb":  (26, 188, 156),
        "orbit_colors": ["#1ABC9C", "#2c3e50", "#1a6655", "#27AE60"],
        "status_text": "Zzz  ·  Warte auf Live-Stream",
        "status_color": "#3a5046",
        "sweep_color": None,   # kein Sweep im Idle
    },
    "analyzing": {
        "core_rgb":   (26, 188, 156),
        "pulse_rgb":  (26, 188, 156),
        "orbit_colors": ["#1ABC9C", "#9B59B6", "#3498DB", "#2ECC71"],
        "status_text": "🟢  KI analysiert  {symbol}",
        "status_color": "#1ABC9C",
        "sweep_color": (26, 188, 156),   # teal
    },
    "trading": {
        "core_rgb":   (212, 146, 10),
        "pulse_rgb":  (212, 146, 10),
        "orbit_colors": ["#D4920A", "#E67E22", "#F39C12", "#CC8400"],
        "status_text": "⚡  Trade wird ausgeführt  {symbol}",
        "status_color": "#D4920A",
        "sweep_color": (212, 146, 10),   # amber
    },
    "error": {
        "core_rgb":   (232, 64, 64),
        "pulse_rgb":  (232, 64, 64),
        "orbit_colors": ["#E84040", "#C0392B", "#E74C3C", "#A93226"],
        "status_text": "⚠️  Verbindung unterbrochen",
        "status_color": "#E84040",
        "sweep_color": (232, 64, 64),    # rot
    },
}


# ────────────────────────────────────────────
#   Pulse-Welle
# ────────────────────────────────────────────

class PulseWave:
    """Expandierende Ringwelle, die von der Mitte ausgeht."""
    def __init__(self, cx: float, cy: float, color: tuple, max_radius: float = 100.0,
                 duration: int = 80, width: float = 2.0, bg_rgb: tuple = (19, 21, 26)):
        self.cx = cx
        self.cy = cy
        self.color = color        # (r, g, b)
        self.max_radius = max_radius
        self.duration = duration  # Frames
        self.width = width
        self.age = 0
        self.id = None            # Canvas-Item
        self.bg_rgb = bg_rgb      # Verbesserung #1: dynamischer BG

    @property
    def alive(self):
        return self.age < self.duration

    def draw(self, canvas: tk.Canvas):
        t = self.age / self.duration
        r = ease_out_cubic(t) * self.max_radius
        alpha = 1.0 - ease_out_cubic(t)   # fade out
        color = rgba_str(*self.color, alpha, self.bg_rgb)
        cx, cy = self.cx, self.cy
        if self.id:
            canvas.delete(self.id)
        if alpha > 0.02:
            self.id = canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline=color, width=max(0.5, self.width * (1 - t))
            )
        self.age += 1


# ────────────────────────────────────────────
#   Partikel
# ────────────────────────────────────────────

class Particle:
    """Ein einzelner Lichtpunkt der nach außen driftet und verblasst."""
    def __init__(self, cx: float, cy: float, color_rgb: tuple = None,
                 bg_rgb: tuple = (19, 21, 26)):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.4, 1.8)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.x = cx + random.uniform(-8, 8)
        self.y = cy + random.uniform(-8, 8)
        self.life = random.randint(40, 90)
        self.max_life = self.life
        # Verbesserung #1 & #4: Farbe kommt aus State-Config
        if color_rgb:
            # Leichte Variation um die Basis-Farbe
            self.color = (
                max(0, min(255, color_rgb[0] + random.randint(-20, 40))),
                max(0, min(255, color_rgb[1] + random.randint(-20, 40))),
                max(0, min(255, color_rgb[2] + random.randint(-20, 40))),
            )
        else:
            self.color = random.choice([
                (26, 188, 156), (46, 204, 113), (52, 152, 219), (155, 89, 182)
            ])
        self.size = random.uniform(1.5, 3.5)
        self.id = None
        self.bg_rgb = bg_rgb

    @property
    def alive(self):
        return self.life > 0

    def update(self, canvas: tk.Canvas):
        if self.id:
            canvas.delete(self.id)
        if not self.alive:
            return
        t = 1 - (self.life / self.max_life)
        alpha = ease_out_cubic(1 - t)
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.96
        self.vy *= 0.96
        color = rgba_str(*self.color, alpha, self.bg_rgb)
        s = self.size * (1 - ease_out_cubic(t) * 0.5)
        self.id = canvas.create_oval(
            self.x - s, self.y - s, self.x + s, self.y + s,
            fill=color, outline=""
        )
        self.life -= 1


# ────────────────────────────────────────────
#   Orbiting-Dot
# ────────────────────────────────────────────

class OrbitDot:
    """Ein kleiner Punkt, der einen Orbit umrundet (wie ein Satellit)."""
    def __init__(self, orbit_r: float, speed: float, phase: float,
                 color: str, size: float = 3.0, bg_rgb: tuple = (19, 21, 26)):
        self.orbit_r = orbit_r
        self.speed = speed    # Radianten pro Frame
        self.angle = phase
        self.color = color
        self.size = size
        self.id = None
        self.trail_ids = []
        self.bg_rgb = bg_rgb  # Verbesserung #1

    def set_color(self, color: str):
        """Aktualisiert die Farbe (für State-Wechsel)."""
        self.color = color

    def update(self, canvas: tk.Canvas, cx: float, cy: float):
        # Trail löschen
        for tid in self.trail_ids:
            canvas.delete(tid)
        self.trail_ids.clear()

        # Trail zeichnen (6 Punkte)
        trail_len = 6
        for i in range(trail_len - 1, 0, -1):
            a = self.angle - i * 0.12
            tx = cx + math.cos(a) * self.orbit_r
            ty = cy + math.sin(a) * self.orbit_r
            alpha = (trail_len - i) / trail_len * 0.4
            rgb = hex_to_rgb(self.color)
            tcol = rgba_str(*rgb, alpha, self.bg_rgb)
            ts = self.size * (trail_len - i) / trail_len
            if ts > 0.3:
                tid = canvas.create_oval(tx - ts, ty - ts, tx + ts, ty + ts,
                                        fill=tcol, outline="")
                self.trail_ids.append(tid)

        # Hauptpunkt
        if self.id:
            canvas.delete(self.id)
        x = cx + math.cos(self.angle) * self.orbit_r
        y = cy + math.sin(self.angle) * self.orbit_r
        s = self.size
        self.id = canvas.create_oval(x - s, y - s, x + s, y + s,
                                     fill=self.color, outline="")
        self.angle += self.speed


# ────────────────────────────────────────────
#   AI-Bubble
# ────────────────────────────────────────────

class AIBubble:
    """Schwebender Text-Bubble mit Fade-in/Fade-out."""
    def __init__(self, x: float, y: float, text: str, max_age: int = 160,
                 bg_rgb: tuple = (19, 21, 26)):
        self.x = x
        self.y = y
        self.text = text
        self.age = 0
        self.max_age = max_age
        self.id = None
        self.bg_rgb = bg_rgb

    @property
    def alive(self):
        return self.age < self.max_age

    def update(self, canvas: tk.Canvas):
        if self.id:
            canvas.delete(self.id)
        if not self.alive:
            return

        t = self.age / self.max_age
        # Fade-in erste 15%, Fade-out letzte 30%
        if t < 0.15:
            alpha = t / 0.15
        elif t > 0.7:
            alpha = 1.0 - (t - 0.7) / 0.3
        else:
            alpha = 1.0

        drift_x = self.x + math.sin(self.age * 0.04) * 12
        self.y -= 0.35

        color = rgba_str(94, 186, 125, alpha * 0.95, self.bg_rgb)
        self.id = canvas.create_text(
            drift_x, self.y,
            text=self.text,
            fill=color,
            font=("Consolas", 10, "bold"),
            width=220,
            justify="center"
        )
        self.age += 1


# ────────────────────────────────────────────
#   RadarSweep  (Verbesserung #3)
# ────────────────────────────────────────────

class RadarSweep:
    """
    Rotierender Radar-Sweep-Effekt — ein Lichtkeil, der über die Ringe fährt.
    
    Technisch: Polygon-Segmente, die einen Keil mit linearem Alpha-Trail erzeugen.
    Keine PIL benötigt — alles in Tkinter-Canvas.
    """
    def __init__(self, color_rgb: tuple = (26, 188, 156),
                 max_alpha: float = 0.18,
                 sweep_arc_deg: float = 110.0,
                 speed_deg_per_frame: float = 1.8,
                 n_segments: int = 14,
                 bg_rgb: tuple = (19, 21, 26)):
        self.color_rgb = color_rgb
        self.max_alpha = max_alpha
        self.sweep_arc = math.radians(sweep_arc_deg)
        self.speed = math.radians(speed_deg_per_frame)
        self.n_segments = n_segments
        self.bg_rgb = bg_rgb
        self.angle = 0.0          # aktuelle Spitze des Keils
        self._poly_ids: list[int] = []

    def set_color(self, color_rgb: tuple):
        self.color_rgb = color_rgb

    def update(self, canvas: tk.Canvas, cx: float, cy: float, radius: float):
        # Alte Segmente löschen
        for pid in self._poly_ids:
            canvas.delete(pid)
        self._poly_ids.clear()

        # Keil in n_segments aufteilen, jedes etwas dunkler
        seg_arc = self.sweep_arc / self.n_segments
        for i in range(self.n_segments):
            # i=0 ist die Spitze (voll), i=n-1 ist das Ende (fast transparent)
            progress = 1.0 - (i / self.n_segments)
            alpha = self.max_alpha * progress * ease_out_cubic(progress)

            a_start = self.angle - i * seg_arc
            a_end   = a_start - seg_arc

            # Segment als Dreieck: cx/cy → zwei Punkte auf dem Ring
            x1 = cx + math.cos(a_start) * radius
            y1 = cy + math.sin(a_start) * radius
            x2 = cx + math.cos(a_end) * radius
            y2 = cy + math.sin(a_end) * radius

            col = rgba_str(*self.color_rgb, alpha, self.bg_rgb)
            pid = canvas.create_polygon(
                cx, cy, x1, y1, x2, y2,
                fill=col, outline=""
            )
            self._poly_ids.append(pid)

        # Winkel weiterdrehen
        self.angle += self.speed
        if self.angle > 2 * math.pi:
            self.angle -= 2 * math.pi

    def clear(self, canvas: tk.Canvas):
        for pid in self._poly_ids:
            canvas.delete(pid)
        self._poly_ids.clear()


# ────────────────────────────────────────────
#   Haupt-Animations-Widget
# ────────────────────────────────────────────

class SonarAnimation:
    """
    GSAP-inspiriertes Sonar/Radar-Widget für das FinGPT-Dashboard.

    Verwendung:
        anim = SonarAnimation(parent_frame, width=300, height=140)
        anim.set_state("analyzing")    # oder "idle", "trading", "error"
        anim.add_bubble("BUY EURUSD")  # zeigt KI-Bubble an
        anim.set_symbol("EURUSD")

    Rückwärtskompatibel:
        anim.set_active(True)  → intern: set_state("analyzing")
        anim.set_active(False) → intern: set_state("idle")
    """

    def __init__(self, master, width: int = 300, height: int = 140, fps: int = 60,
                 bg_color: str = None):
        self.master = master
        self.width = width
        self.height = height
        self.fps = fps
        self._frame_ms = max(16, int(1000 / fps))

        # ── Verbesserung #1: BG aus DesignSystem holen ──────────────
        try:
            from gui.design_system import DesignSystem
            self.bg_color = bg_color or DesignSystem.BG['card']   # '#13151A'
        except Exception:
            self.bg_color = bg_color or "#13151A"

        self.bg_rgb = hex_to_rgb(self.bg_color)
        # ────────────────────────────────────────────────────────────

        # ── Verbesserung #4: State-System ───────────────────────────
        self._state = "idle"         # idle | analyzing | trading | error
        self._active = False         # Rückwärtskompatibilität
        self._symbol = "KI-Engine"
        # ────────────────────────────────────────────────────────────

        self._phase = 0.0

        # Canvas
        self.canvas = tk.Canvas(
            master,
            width=width, height=height,
            bg=self.bg_color,
            highlightthickness=0
        )

        # Objekt-Listen
        self._pulses: list[PulseWave] = []
        self._particles: list[Particle] = []
        self._bubbles: list[AIBubble] = []

        # ── Verbesserung #4: Orbit-Farben aus State-Config ─────────
        cfg = STATE_CONFIG["idle"]
        self._orbits = [
            OrbitDot(orbit_r=38,  speed=0.035,  phase=0.0,           color=cfg["orbit_colors"][0], size=4.5, bg_rgb=self.bg_rgb),
            OrbitDot(orbit_r=58,  speed=-0.022, phase=math.pi/3,     color=cfg["orbit_colors"][1], size=3.5, bg_rgb=self.bg_rgb),
            OrbitDot(orbit_r=80,  speed=0.015,  phase=math.pi,       color=cfg["orbit_colors"][2], size=2.5, bg_rgb=self.bg_rgb),
            OrbitDot(orbit_r=72,  speed=0.028,  phase=math.pi*1.5,   color=cfg["orbit_colors"][3], size=2.2, bg_rgb=self.bg_rgb),
        ]

        # ── Verbesserung #3: RadarSweep ─────────────────────────────
        self._sweep = RadarSweep(
            color_rgb=(26, 188, 156),
            max_alpha=0.16,
            sweep_arc_deg=110.0,
            speed_deg_per_frame=1.8,
            n_segments=14,
            bg_rgb=self.bg_rgb,
        )

        # Statische Ring-IDs (werden bei Resize neu gezeichnet)
        self._ring_ids: list[int] = []

        # Core-Dot IDs (Multi-Layer Glow → Liste)
        self._core_ids: list[int] = []

        # Hintergrundgitter
        self._grid_ids: list[int] = []

        # Pulse-Timer
        self._pulse_timer = 0
        self._pulse_interval = 45   # alle 45 Frames einen Pulse spawnen

        # Partikel-Timer
        self._particle_timer = 0
        self._particle_interval = 8

        # Status-Text
        self._status_id: int | None = None

        self._draw_static_bg()
        self._schedule()

    # ── Layout ──────────────────────────────────────────

    def grid(self, **kwargs):
        self.canvas.grid(**kwargs)

    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)

    def place(self, **kwargs):
        self.canvas.place(**kwargs)

    @property
    def cx(self) -> float:
        return self.width / 2

    @property
    def cy(self) -> float:
        return self.height / 2

    # ── Public API ───────────────────────────────────────

    def set_active(self, active: bool):
        """Rückwärtskompatibel: True → 'analyzing', False → 'idle'."""
        self._active = active
        self.set_state("analyzing" if active else "idle")

    def set_state(self, state: str):
        """
        Setzt den Animationszustand.
        Erlaubte Werte: 'idle', 'analyzing', 'trading', 'error'
        """
        if state not in STATE_CONFIG:
            state = "idle"
        self._state = state
        self._active = (state != "idle")

        cfg = STATE_CONFIG[state]

        # Orbit-Farben aktualisieren
        for i, orb in enumerate(self._orbits):
            orb.set_color(cfg["orbit_colors"][i])

        # Sweep-Farbe aktualisieren
        if cfg["sweep_color"]:
            self._sweep.set_color(cfg["sweep_color"])

    def set_symbol(self, symbol: str):
        self._symbol = symbol

    def add_bubble(self, text: str):
        """Fügt einen KI-Chat-Bubble zur Animation hinzu."""
        x = random.choice([
            random.uniform(30, self.cx - 50),
            random.uniform(self.cx + 50, self.width - 30)
        ])
        y = random.uniform(self.cy - 40, self.cy + 30)
        self._bubbles.append(AIBubble(x, y, text, max_age=180, bg_rgb=self.bg_rgb))

    def resize(self, width: int, height: int):
        self.width = width
        self.height = height
        self.canvas.configure(width=width, height=height)
        self._draw_static_bg()

    # ── Statischer Hintergrund ────────────────────────────

    def _draw_static_bg(self):
        """Zeichnet die statischen Hintergrund-Ringe."""
        for gid in self._grid_ids + self._ring_ids:
            self.canvas.delete(gid)
        self._grid_ids.clear()
        self._ring_ids.clear()

        cx, cy = self.cx, self.cy

        # Statische Ringe (immer sichtbar, sehr blass)
        ring_radii = [25, 52, 78, 105]
        ring_colors = [
            rgba_str(26, 188, 156, 0.13, self.bg_rgb),
            rgba_str(26, 188, 156, 0.09, self.bg_rgb),
            rgba_str(26, 188, 156, 0.06, self.bg_rgb),
            rgba_str(26, 188, 156, 0.03, self.bg_rgb),
        ]
        for r, col in zip(ring_radii, ring_colors):
            rid = self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                         outline=col, width=1)
            self._ring_ids.append(rid)

    # ── Animations-Loop ──────────────────────────────────

    def _schedule(self):
        self._tick()

    def _tick(self):
        try:
            self._frame()
        except Exception:
            pass
        self.canvas.after(self._frame_ms, self._tick)

    def _frame(self):
        self._phase += 0.025

        if self._state == "idle":
            self._draw_idle()
        else:
            self._draw_active()

    # ── Idle-State (Verbesserung #2: Breathing-Effekt) ─────────────

    def _draw_idle(self):
        """
        VERBESSERUNG #2: Breathing-Idle-Effekt.
        Die statischen Ringe pulsieren sanft wie ein Atemzug.
        Der Core-Dot atmet zwischen teal und fast-schwarz.
        """
        cx, cy = self.cx, self.cy

        # Lösche Core
        for cid in self._core_ids:
            self.canvas.delete(cid)
        self._core_ids.clear()

        # Breathing-Faktor: sehr langsam (phase * 0.3)
        breath = ease_in_out_sine((math.sin(self._phase * 0.3) + 1) / 2)

        # Pulsierende Ringe (überschreiben die statischen)
        for i, (rid, base_r) in enumerate(zip(self._ring_ids, [25, 52, 78, 105])):
            # Leichte Radius-Variation ±2px
            pulsed_r = base_r + 1.5 * breath * (1 - i * 0.2)
            base_alphas = [0.13, 0.09, 0.06, 0.03]
            pulsed_alpha = base_alphas[i] + 0.05 * breath * (1 - i * 0.2)
            col = rgba_str(26, 188, 156, pulsed_alpha, self.bg_rgb)
            self.canvas.coords(rid,
                               cx - pulsed_r, cy - pulsed_r,
                               cx + pulsed_r, cy + pulsed_r)
            self.canvas.itemconfig(rid, outline=col)

        # VERBESSERUNG #5: Multi-Layer Glow Core (auch im Idle)
        core_r = 7 + 3 * breath
        core_rgb = STATE_CONFIG["idle"]["core_rgb"]
        glow_layers = [
            (core_r * 3.2, 0.025 + 0.015 * breath),
            (core_r * 2.2, 0.05  + 0.03  * breath),
            (core_r * 1.5, 0.12  + 0.06  * breath),
            (core_r,       0.55  + 0.25  * breath),
        ]
        for layer_r, layer_alpha in glow_layers:
            col = rgba_str(*core_rgb, layer_alpha, self.bg_rgb)
            cid = self.canvas.create_oval(
                cx - layer_r, cy - layer_r, cx + layer_r, cy + layer_r,
                fill=col, outline=""
            )
            self._core_ids.append(cid)

        # Highlight auf dem Kern (3D-Kugel-Optik)
        hl_r = core_r * 0.35
        hl_x = cx - core_r * 0.28
        hl_y = cy - core_r * 0.28
        hl_col = rgba_str(200, 255, 240, 0.18 + 0.07 * breath, self.bg_rgb)
        hl_id = self.canvas.create_oval(
            hl_x - hl_r, hl_y - hl_r,
            hl_x + hl_r, hl_y + hl_r,
            fill=hl_col, outline=""
        )
        self._core_ids.append(hl_id)

        # Status-Text mit pulsierender Opacity
        text_alpha = 0.45 + 0.2 * breath
        status_rgb = hex_to_rgb(STATE_CONFIG["idle"]["status_color"])
        status_col = rgba_str(*status_rgb, text_alpha, self.bg_rgb)
        self._update_status(STATE_CONFIG["idle"]["status_text"], status_col)

    # ── Active-State ────────────────────────────────────

    def _draw_active(self):
        cx, cy = self.cx, self.cy
        cfg = STATE_CONFIG[self._state]

        # ── Verbesserung #3: Radar-Sweep (zuerst, damit er hinter allem liegt) ──
        sweep_radius = min(cx, cy) * 1.55
        if cfg["sweep_color"]:
            self._sweep.set_color(cfg["sweep_color"])
            self._sweep.update(self.canvas, cx, cy, sweep_radius)

        # ── Pulsierende Ringe (Rücksetzen auf statische Werte) ──
        for i, (rid, base_r) in enumerate(zip(self._ring_ids, [25, 52, 78, 105])):
            base_alphas = [0.13, 0.09, 0.06, 0.03]
            col = rgba_str(26, 188, 156, base_alphas[i], self.bg_rgb)
            self.canvas.coords(rid,
                               cx - base_r, cy - base_r,
                               cx + base_r, cy + base_r)
            self.canvas.itemconfig(rid, outline=col)

        # ── Verbesserung #5: Multi-Layer Glow Core-Dot ──────────────
        for cid in self._core_ids:
            self.canvas.delete(cid)
        self._core_ids.clear()

        t_core = (math.sin(self._phase * 1.2) + 1) / 2   # 0..1
        core_r = 7 + 7 * ease_in_out_sine(t_core)
        core_rgb = cfg["core_rgb"]

        # 4 Glow-Schichten von außen nach innen
        glow_layers = [
            (core_r * 3.5, 0.03  + 0.02 * t_core),   # äußerste Aura
            (core_r * 2.4, 0.07  + 0.04 * t_core),
            (core_r * 1.6, 0.18  + 0.10 * t_core),
            (core_r,       0.75  + 0.25 * t_core),    # Kern
        ]
        for layer_r, layer_alpha in glow_layers:
            col = rgba_str(*core_rgb, min(1.0, layer_alpha), self.bg_rgb)
            cid = self.canvas.create_oval(
                cx - layer_r, cy - layer_r,
                cx + layer_r, cy + layer_r,
                fill=col, outline=""
            )
            self._core_ids.append(cid)

        # Outline-Ring auf dem Kern
        outline_col = rgba_str(
            min(255, core_rgb[0] + 60),
            min(255, core_rgb[1] + 60),
            min(255, core_rgb[2] + 40),
            0.35, self.bg_rgb
        )
        out_id = self.canvas.create_oval(
            cx - core_r, cy - core_r,
            cx + core_r, cy + core_r,
            outline=outline_col, width=1, fill=""
        )
        self._core_ids.append(out_id)

        # Highlight (3D-Kugel-Optik)
        hl_r = core_r * 0.32
        hl_x = cx - core_r * 0.27
        hl_y = cy - core_r * 0.27
        hl_col = rgba_str(220, 255, 245, 0.22 + 0.08 * t_core, self.bg_rgb)
        hl_id = self.canvas.create_oval(
            hl_x - hl_r, hl_y - hl_r,
            hl_x + hl_r, hl_y + hl_r,
            fill=hl_col, outline=""
        )
        self._core_ids.append(hl_id)

        # ── Pulse-Wellen spawnen ──
        self._pulse_timer += 1
        if self._pulse_timer >= self._pulse_interval:
            self._pulse_timer = 0
            pulse_rgb = cfg["pulse_rgb"]
            # Leichte Farbvariation
            col = (
                max(0, min(255, pulse_rgb[0] + random.randint(-15, 15))),
                max(0, min(255, pulse_rgb[1] + random.randint(-10, 10))),
                max(0, min(255, pulse_rgb[2] + random.randint(-10, 10))),
            )
            self._pulses.append(PulseWave(
                cx, cy, col,
                max_radius=min(cx, cy) * 1.7,
                duration=80,
                width=2.5,
                bg_rgb=self.bg_rgb,
            ))

        # ── Partikel spawnen ──
        self._particle_timer += 1
        if self._particle_timer >= self._particle_interval:
            self._particle_timer = 0
            if len(self._particles) < 40:
                self._particles.append(Particle(
                    cx, cy,
                    color_rgb=cfg["pulse_rgb"],
                    bg_rgb=self.bg_rgb,
                ))

        # ── Partikel updaten ──
        alive_p = []
        for p in self._particles:
            p.update(self.canvas)
            if p.alive:
                alive_p.append(p)
        self._particles = alive_p

        # ── Pulses updaten ──
        alive_w = []
        for w in self._pulses:
            w.draw(self.canvas)
            if w.alive:
                alive_w.append(w)
        self._pulses = alive_w

        # ── Orbitale Satelliten ──
        for orb in self._orbits:
            orb.update(self.canvas, cx, cy)

        # ── KI-Bubbles ──
        alive_b = []
        for b in self._bubbles:
            b.update(self.canvas)
            if b.alive:
                alive_b.append(b)
        self._bubbles = alive_b

        # ── Core ganz vorne ──
        for cid in self._core_ids:
            self.canvas.tag_raise(cid)

        # ── Status-Text ──
        status_text = cfg["status_text"].format(symbol=self._symbol)
        self._update_status(status_text, cfg["status_color"])

    # ── Status-Text ─────────────────────────────────────

    def _update_status(self, text: str, color: str):
        if self._status_id:
            self.canvas.delete(self._status_id)
        self._status_id = self.canvas.create_text(
            self.cx, self.height - 12,
            text=text,
            fill=color,
            font=("Consolas", 9),
            anchor="center"
        )
