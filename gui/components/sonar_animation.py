"""
SonarAnimation – GSAP-inspirierte Canvas-Animation für das FinGPT-Dashboard.

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


def rgba_str(r, g, b, a: float, bg_color: tuple = (11, 14, 20)) -> str:
    """Gibt einen Tkinter-kompatiblen Hex-Farbstring mit Alpha-Annäherung zurück."""
    bg = bg_color  # #09090B – FinGPT Background Farbe (Deep Black)
    r2 = int(bg[0] + (r - bg[0]) * a)
    g2 = int(bg[1] + (g - bg[1]) * a)
    b2 = int(bg[2] + (b - bg[2]) * a)
    return f"#{r2:02x}{g2:02x}{b2:02x}"


# ────────────────────────────────────────────
#   Pulse-Welle
# ────────────────────────────────────────────

class PulseWave:
    """Expandierende Ringwelle, die von der Mitte ausgeht."""
    def __init__(self, cx: float, cy: float, color: tuple, max_radius: float = 100.0,
                 duration: int = 80, width: float = 2.0):
        self.cx = cx
        self.cy = cy
        self.color = color        # (r, g, b)
        self.max_radius = max_radius
        self.duration = duration  # Frames
        self.width = width
        self.age = 0
        self.id = None           # Canvas-Item

    @property
    def alive(self):
        return self.age < self.duration

    def draw(self, canvas: tk.Canvas):
        t = self.age / self.duration
        r = ease_out_cubic(t) * self.max_radius
        alpha = 1.0 - ease_out_cubic(t)   # fade out
        color = rgba_str(*self.color, alpha)
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
    def __init__(self, cx: float, cy: float):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.4, 1.8)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.x = cx + random.uniform(-8, 8)
        self.y = cy + random.uniform(-8, 8)
        self.life = random.randint(40, 90)
        self.max_life = self.life
        r = random.choice([(26, 188, 156), (46, 204, 113), (52, 152, 219), (155, 89, 182)])
        self.color = r
        self.size = random.uniform(1.5, 3.5)
        self.id = None

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
        color = rgba_str(*self.color, alpha)
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
                 color: str, size: float = 3.0):
        self.orbit_r = orbit_r
        self.speed = speed    # Radianten pro Frame
        self.angle = phase
        self.color = color
        self.size = size
        self.id = None
        self.trail_ids = []

    def update(self, canvas: tk.Canvas, cx: float, cy: float):
        # Trail löschen
        for tid in self.trail_ids:
            canvas.delete(tid)
        self.trail_ids.clear()

        # Trail zeichnen (5 Punkte)
        trail_len = 6
        for i in range(trail_len - 1, 0, -1):
            a = self.angle - i * 0.12
            tx = cx + math.cos(a) * self.orbit_r
            ty = cy + math.sin(a) * self.orbit_r
            alpha = (trail_len - i) / trail_len * 0.4
            rgb = hex_to_rgb(self.color)
            tcol = rgba_str(*rgb, alpha)
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
    def __init__(self, x: float, y: float, text: str, max_age: int = 160):
        self.x = x
        self.y = y
        self.text = text
        self.age = 0
        self.max_age = max_age
        self.id = None

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

        color = rgba_str(94, 186, 125, alpha * 0.95)
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
#   Haupt-Animations-Widget
# ────────────────────────────────────────────

class SonarAnimation:
    """
    GSAP-inspiriertes Sonar/Radar-Widget für das FinGPT-Dashboard.

    Verwendung:
        anim = SonarAnimation(parent_frame, width=300, height=140)
        anim.set_active(True)          # startet Animation
        anim.add_bubble("BUY EURUSD")  # zeigt KI-Bubble an
        anim.set_symbol("EURUSD")
    """

    def __init__(self, master, width: int = 300, height: int = 140, fps: int = 60, bg_color: str = "#09090B"):
        self.master = master
        self.width = width
        self.height = height
        self.fps = fps
        self._frame_ms = max(16, int(1000 / fps))
        self.bg_color = bg_color

        self._active = False
        self._symbol = "KI-Engine"
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

        # Orbital-Satelliten
        self._orbits = [
            OrbitDot(orbit_r=38,  speed=0.035,  phase=0.0,           color="#1ABC9C", size=4.5),
            OrbitDot(orbit_r=58,  speed=-0.022, phase=math.pi/3,     color="#9B59B6", size=3.5),
            OrbitDot(orbit_r=80,  speed=0.015,  phase=math.pi,       color="#3498DB", size=2.5),
            OrbitDot(orbit_r=72,  speed=0.028,  phase=math.pi*1.5,   color="#2ECC71", size=2.2),
        ]

        # Statische Ring-IDs (werden bei Resize neu gezeichnet)
        self._ring_ids: list[int] = []

        # Core-Dot (pulsiert)
        self._core_id: int | None = None

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
        self._active = active
        if not active:
            self._draw_idle()

    def set_symbol(self, symbol: str):
        self._symbol = symbol

    def add_bubble(self, text: str):
        """Fügt einen KI-Chat-Bubble zur Animation hinzu."""
        x = random.choice([
            random.uniform(30, self.cx - 50),
            random.uniform(self.cx + 50, self.width - 30)
        ])
        y = random.uniform(self.cy - 40, self.cy + 30)
        self._bubbles.append(AIBubble(x, y, text, max_age=180))

    def resize(self, width: int, height: int):
        self.width = width
        self.height = height
        self.canvas.configure(width=width, height=height)
        self._draw_static_bg()

    # ── Statischer Hintergrund ────────────────────────────

    def _draw_static_bg(self):
        """Zeichnet das Hintergrundgitter und die statischen Ringe."""
        for gid in self._grid_ids + self._ring_ids:
            self.canvas.delete(gid)
        self._grid_ids.clear()
        self._ring_ids.clear()

        cx, cy = self.cx, self.cy

        # Kein Rastermuster mehr
        
        # Statische Ringe (immer sichtbar, sehr blass)
        ring_radii = [25, 52, 78, 105]
        ring_colors = [
            rgba_str(26, 188, 156, 0.12),
            rgba_str(26, 188, 156, 0.09),
            rgba_str(26, 188, 156, 0.06),
            rgba_str(26, 188, 156, 0.04),
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

        if self._active:
            self._draw_active()
        else:
            self._draw_idle()

    # ── Idle-State ─────────────────────────────────────

    def _draw_idle(self):
        if self._core_id:
            self.canvas.delete(self._core_id)

        # Core: langsam pulsierender Punkt (dunkel)
        cx, cy = self.cx, self.cy
        pulse = 0.4 + 0.15 * math.sin(self._phase * 0.5)
        r = 8 + 3 * pulse
        col = rgba_str(26, 100, 80, 0.6 + 0.3 * pulse)
        self._core_id = self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r, fill=col, outline=""
        )

        # Status-Text
        self._update_status("Zzz  ·  Warte auf Live-Stream", "#3a4a44")

    # ── Active-State ────────────────────────────────────

    def _draw_active(self):
        cx, cy = self.cx, self.cy

        # ── Core-Dot (pulsierend, Elastic-Easing simuliert) ──
        if self._core_id:
            self.canvas.delete(self._core_id)

        t_core = (math.sin(self._phase * 1.2) + 1) / 2   # 0..1
        core_r = 7 + 7 * ease_in_out_sine(t_core)
        inner_alpha = 0.7 + 0.3 * t_core
        col_core = rgba_str(26, 188, 156, inner_alpha)
        self._core_id = self.canvas.create_oval(
            cx - core_r, cy - core_r, cx + core_r, cy + core_r,
            fill=col_core, outline=rgba_str(94, 255, 200, 0.4), width=1
        )

        # ── Pulse-Wellen spawnen ──
        self._pulse_timer += 1
        if self._pulse_timer >= self._pulse_interval:
            self._pulse_timer = 0
            colors = [(26, 188, 156), (46, 204, 113), (52, 152, 219)]
            col = random.choice(colors)
            self._pulses.append(PulseWave(cx, cy, col,
                                          max_radius=min(cx, cy) * 1.7,
                                          duration=80,
                                          width=2.5))

        # ── Partikel spawnen ──
        self._particle_timer += 1
        if self._particle_timer >= self._particle_interval:
            self._particle_timer = 0
            if len(self._particles) < 40:
                self._particles.append(Particle(cx, cy))

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

        # ── Core vorder-rund (über allem) ──
        self.canvas.tag_raise(self._core_id)

        # ── Status-Text ──
        self._update_status(f"🟢  KI analysiert  {self._symbol}", "#1ABC9C")

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
