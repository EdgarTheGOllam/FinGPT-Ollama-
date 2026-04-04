import math
import random
import time
import tkinter as tk
import customtkinter as ctk


class CosmicMap3D(ctk.CTkFrame):
    """Neural Network Visualization with 3D Cosmic Map and 2D flat network view."""

    def __init__(self, master, bg_color="#090a0f", **kwargs):
        super().__init__(master, fg_color=bg_color, **kwargs)

        # ── Lifecycle flag (must be first – toggle animator checks it) ──
        self.running = True

        # ── Mode state ──────────────────────────────────────────────
        self._mode = "3D"            # "3D" or "2D"
        self._transition_alpha = 1.0 # 1.0 = current mode fully visible
        self._transitioning = False
        self._fade_dir = 1           # 1 = fade in, -1 = fade out
        self._fade_speed = 0.08

        # ── Top bar with iOS toggle ──────────────────────────────────
        self._top_bar = tk.Frame(self, bg="#0d0f18", height=44)
        self._top_bar.pack(side="top", fill="x")
        self._top_bar.pack_propagate(False)

        # Title label
        self._title_lbl = tk.Label(
            self._top_bar, text="🌌  Neural Network Universe",
            bg="#0d0f18", fg="#c9d1d9",
            font=("Inter", 13, "bold")
        )
        self._title_lbl.pack(side="left", padx=16, pady=8)

        # iOS-style animated toggle on the right
        self._build_ios_toggle()

        # ── Canvas ───────────────────────────────────────────────────
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # ── 3D State ─────────────────────────────────────────────────
        self.nodes = []
        self.edges = []
        self.particles = []
        self.stars = []

        self.angle_x = 0.4
        self.angle_y = 0.4
        self.fov = 500
        self.viewer_distance = 600

        self.width = 800
        self.height = 600
        self.canvas.bind("<Configure>", self._on_resize)

        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.is_dragging = False
        self.hovered_node_idx = None

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)

        self.time_elapsed = 0.0
        self.nova_radius = 0
        self.nova_active = False

        # ── 2D Network State ─────────────────────────────────────────
        self._2d_nodes = []   # {x, y, vx, vy, color, size, label}
        self._2d_edges = []   # (i, j, color)
        self._pulse_rings = []
        self._data_packets = []  # {edge_idx, t, speed, color}
        self._ripple_t = 0.0
        self._scan_y = 0.0
        self._glitch_timer = 0

        self._init_starfield()
        self._init_brain()
        self._load_dummy_trades()
        self._build_2d_network()
        self._animate()

    # ═══════════════════════════════════════════════════════════════
    # iOS TOGGLE
    # ═══════════════════════════════════════════════════════════════

    def _build_ios_toggle(self):
        """Build a custom iOS-style animated toggle switch."""
        toggle_frame = tk.Frame(self._top_bar, bg="#0d0f18")
        toggle_frame.pack(side="right", padx=16, pady=6)

        # Label left
        self._lbl_2d = tk.Label(toggle_frame, text="2D", bg="#0d0f18", fg="#555e6e",
                                font=("Inter", 10, "bold"))
        self._lbl_2d.pack(side="left", padx=(0, 6))

        # Canvas for the toggle pill
        self._tog_w = 54
        self._tog_h = 28
        self._tog_canvas = tk.Canvas(toggle_frame, width=self._tog_w, height=self._tog_h,
                                     bg="#0d0f18", highlightthickness=0, cursor="hand2")
        self._tog_canvas.pack(side="left")
        self._tog_canvas.bind("<Button-1>", self._toggle_mode)

        # Label right
        self._lbl_3d = tk.Label(toggle_frame, text="3D", bg="#0d0f18", fg="#e0aaff",
                                font=("Inter", 10, "bold"))
        self._lbl_3d.pack(side="left", padx=(6, 0))

        # Toggle animation state
        self._tog_anim_pos = 1.0   # 0.0 = 2D (left), 1.0 = 3D (right)
        self._tog_target  = 1.0
        self._draw_toggle(self._tog_anim_pos)
        self._animate_toggle()

    def _draw_toggle(self, pos):
        """Draw the iOS pill toggle at animation position pos (0..1)."""
        c = self._tog_canvas
        c.delete("all")
        w, h = self._tog_w, self._tog_h
        r = h // 2

        # Background pill – interpolate color: 2D=#e74c3c(ish) 3D=#8E44AD
        # Use a two-stop gradient via LAB-ish approximation in RGB
        r0, g0, b0 = 0x23, 0x28, 0x3a   # 2D off color (dark blue-grey)
        r1, g1, b1 = 0x8E, 0x44, 0xAD   # 3D on color (purple)
        ri = int(r0 + (r1-r0)*pos)
        gi = int(g0 + (g1-g0)*pos)
        bi = int(b0 + (b1-b0)*pos)
        pill_color = f"#{ri:02x}{gi:02x}{bi:02x}"

        # Draw rounded rect pill
        c.create_arc(0, 0, h, h, start=90, extent=180, fill=pill_color, outline="")
        c.create_arc(w-h, 0, w, h, start=270, extent=180, fill=pill_color, outline="")
        c.create_rectangle(r, 0, w-r, h, fill=pill_color, outline="")

        # Thumb position
        margin = 3
        travel = w - h
        thumb_x = margin + r + travel * pos
        thumb_y = h // 2

        glow_r = r - margin + 4
        for i, alpha in enumerate([("gray12", 2.5), ("gray25", 1.8)]):
            stip, mult = alpha
            gr = glow_r * mult
            c.create_oval(thumb_x - gr, thumb_y - gr, thumb_x + gr, thumb_y + gr,
                          fill="", outline="#ffffff", stipple=stip, width=1)

        tr = r - margin
        c.create_oval(thumb_x - tr, thumb_y - tr, thumb_x + tr, thumb_y + tr,
                      fill="#ffffff", outline="")

    def _animate_toggle(self):
        """Smoothly animate the toggle thumb."""
        if not self.running:
            return
        speed = 0.12
        diff = self._tog_target - self._tog_anim_pos
        if abs(diff) > 0.005:
            self._tog_anim_pos += diff * speed * 3
            self._draw_toggle(self._tog_anim_pos)
        else:
            self._tog_anim_pos = self._tog_target
            self._draw_toggle(self._tog_anim_pos)
        self.after(16, self._animate_toggle)

    def _toggle_mode(self, event=None):
        """Switch between 3D and 2D modes with a fade transition."""
        if self._transitioning:
            return
        if self._mode == "3D":
            self._mode = "2D"
            self._tog_target = 0.0
            self._lbl_3d.configure(fg="#555e6e")
            self._lbl_2d.configure(fg="#00FF66")
        else:
            self._mode = "3D"
            self._tog_target = 1.0
            self._lbl_3d.configure(fg="#e0aaff")
            self._lbl_2d.configure(fg="#555e6e")

        # Start fade-out → fade-in
        self._transitioning = True
        self._transition_alpha = 1.0
        self._fade_dir = -1   # fade out first
        self._run_fade()

    def _run_fade(self):
        """Fade transition animation loop."""
        self._transition_alpha += self._fade_dir * self._fade_speed
        if self._fade_dir == -1 and self._transition_alpha <= 0.0:
            self._transition_alpha = 0.0
            self._fade_dir = 1   # switch to fade in
        elif self._fade_dir == 1 and self._transition_alpha >= 1.0:
            self._transition_alpha = 1.0
            self._transitioning = False
            return

        self.after(20, self._run_fade)

    # ═══════════════════════════════════════════════════════════════
    # RESIZE / MOUSE
    # ═══════════════════════════════════════════════════════════════

    def _on_resize(self, event):
        self.width = event.width
        self.height = event.height

    def _on_press(self, event):
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
        self.is_dragging = True
        self.drag_moved = False

    def _on_drag(self, event):
        if self.is_dragging and self._mode == "3D":
            dx = event.x - self.last_mouse_x
            dy = event.y - self.last_mouse_y
            if abs(dx) > 3 or abs(dy) > 3:
                self.drag_moved = True
            self.angle_y += dx * 0.005
            self.angle_x += dy * 0.005
            self.last_mouse_x = event.x
            self.last_mouse_y = event.y

    def _on_release(self, event):
        self.is_dragging = False
        if not getattr(self, "drag_moved", False) and self.hovered_node_idx is not None:
            node = self.nodes[self.hovered_node_idx]
            if node["type"] == "trade":
                self._open_trade_details(node)

    def _on_hover(self, event):
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

    def _on_mousewheel(self, event):
        zoom_speed = 40
        if hasattr(event, "delta") and event.delta != 0:
            self.fov += zoom_speed if event.delta > 0 else -zoom_speed
        elif hasattr(event, "num"):
            self.fov += zoom_speed if event.num == 4 else -zoom_speed
        self.fov = max(100, min(2000, self.fov))

    # ═══════════════════════════════════════════════════════════════
    # 3D INIT
    # ═══════════════════════════════════════════════════════════════

    def _init_starfield(self):
        for _ in range(300):
            x = random.uniform(-1000, 1000)
            y = random.uniform(-1000, 1000)
            z = random.uniform(-1000, 1000)
            if x*x + y*y + z*z < 300*300:
                x += 400
            size = random.uniform(0.2, 1.2)
            color = random.choice(["#4a4e69", "#9a8c98", "#c9ada7", "#22223b"])
            self.stars.append({"x": x, "y": y, "z": z, "size": size, "color": color})

    def _init_brain(self):
        self.nodes.append({
            "x": 0, "y": 0, "z": 0, "type": "brain",
            "color": "#e0aaff", "base_size": 16, "pulse_phase": 0,
            "label": "FinGPT Core\nNeural Engine Active", "born": 0
        })
        for _ in range(35):
            r = random.uniform(15, 55)
            theta = random.uniform(0, 2*math.pi)
            phi = random.uniform(0, math.pi)
            nx = r * math.sin(phi) * math.cos(theta)
            ny = r * math.sin(phi) * math.sin(theta)
            nz = r * math.cos(phi)
            self.nodes.append({
                "x": nx, "y": ny, "z": nz, "type": "brain_node",
                "color": random.choice(["#9d4edd", "#7b2cbf", "#c77dff"]),
                "base_size": random.uniform(2, 5),
                "pulse_phase": random.uniform(0, 10), "label": "", "born": 0
            })
            self.edges.append((0, len(self.nodes)-1, "core_link"))
            if random.random() > 0.4 and len(self.nodes) > 2:
                other_idx = random.randint(1, len(self.nodes)-2)
                self.edges.append((other_idx, len(self.nodes)-1, "core_link"))

    def _load_dummy_trades(self):
        for _ in range(25):
            profit = random.uniform(-3.0, 6.0)
            self.add_trade(profit, duration_str=f"{random.randint(5, 120)}m", is_new=False)

    def add_trade(self, profit_pct, duration_str="N/A", symbol="EURUSD", is_new=True):
        r = random.uniform(160, 320)
        theta = random.uniform(0, 2*math.pi)
        phi = random.gauss(math.pi/2, 0.4)
        nx = r * math.sin(phi) * math.cos(theta)
        ny = r * math.sin(phi) * math.sin(theta)
        nz = r * math.cos(phi)
        if profit_pct > 0:
            color = "#00FF66"
            base_size = min(9, 4 + profit_pct*1.2)
        elif profit_pct < 0:
            color = "#FF1744"
            base_size = min(9, 4 + abs(profit_pct)*1.2)
        else:
            color = "#00E5FF"
            base_size = 4
        entry = random.uniform(1.0500, 1.1500)
        direction = random.choice(["LONG", "SHORT"])
        exit_p = entry * (1 + (profit_pct/100) * (1 if direction == "LONG" else -1))
        self.nodes.append({
            "x": nx, "y": ny, "z": nz, "type": "trade",
            "color": color, "base_size": base_size, "pulse_phase": random.uniform(0, 10),
            "label": f"{symbol}\nProfit: {profit_pct:+.2f}%\nDur: {duration_str}",
            "born": time.time() if is_new else 0,
            "is_new": is_new,
            "symbol": symbol, "profit_pct": profit_pct, "duration": duration_str,
            "direction": direction, "entry_price": entry, "exit_price": exit_p
        })
        new_idx = len(self.nodes) - 1
        self.edges.append((0, new_idx, "trade_link"))
        trade_indices = [i for i, n in enumerate(self.nodes) if n["type"] == "trade" and i != new_idx]
        if trade_indices:
            num_links = min(random.randint(1, 3), len(trade_indices))
            targets = random.sample(trade_indices, num_links)
            for t_idx in targets:
                self.edges.append((new_idx, t_idx, "neural_link"))
        if is_new:
            self.nova_active = True
            self.nova_radius = 5
            self._create_nova_particles()

    def _create_nova_particles(self):
        self.particles = []
        for _ in range(60):
            vx, vy, vz = random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)
            length = math.sqrt(vx*vx + vy*vy + vz*vz) or 1
            vx, vy, vz = vx/length, vy/length, vz/length
            speed = random.uniform(3, 8)
            self.particles.append({
                "x": 0, "y": 0, "z": 0,
                "vx": vx * speed, "vy": vy * speed, "vz": vz * speed,
                "life": 1.0, "color": random.choice(["#00FF66", "#00E5FF", "#FFFFFF"])
            })

    # ═══════════════════════════════════════════════════════════════
    # 3D Math
    # ═══════════════════════════════════════════════════════════════

    def _rotate_3d(self, x, y, z):
        cos_x, sin_x = math.cos(self.angle_x), math.sin(self.angle_x)
        y1 = y * cos_x - z * sin_x
        z1 = y * sin_x + z * cos_x
        cos_y, sin_y = math.cos(self.angle_y), math.sin(self.angle_y)
        x2 = x * cos_y + z1 * sin_y
        z2 = -x * sin_y + z1 * cos_y
        return x2, y1, z2

    def _project(self, x, y, z):
        x, y, z = self._rotate_3d(x, y, z)
        z_adj = z + self.viewer_distance
        if z_adj <= 0:
            z_adj = 0.1
        factor = self.fov / z_adj
        return x * factor + self.width / 2, y * factor + self.height / 2, factor, z

    def _draw_3d_orbit(self, radius, color, plane="xz"):
        points = []
        steps = 50
        for i in range(steps + 1):
            theta = (i / steps) * 2 * math.pi
            c, s = math.cos(theta) * radius, math.sin(theta) * radius
            if plane == "xz":
                x, y, z = c, 0, s
            elif plane == "xy":
                x, y, z = c, s, 0
            else:
                x, y, z = 0, c, s
            px, py, _, _ = self._project(x, y, z)
            points.append((px, py))
        for i in range(len(points)-1):
            self.canvas.create_line(points[i][0], points[i][1], points[i+1][0], points[i+1][1],
                                    fill=color, dash=(2, 6))

    # ═══════════════════════════════════════════════════════════════
    # 2D NETWORK INIT
    # ═══════════════════════════════════════════════════════════════

    def _build_2d_network(self):
        """Build a layered 2D neural network diagram – EPIC edition."""
        # Layers: Input(5) → Hidden1(6) → Hidden2(6) → Hidden3(6) → Output(3)
        layer_sizes = [5, 6, 6, 6, 3]
        # Electric neon palette per layer
        layer_colors = ["#00FFB2", "#FF6B35", "#FF6B35", "#FF6B35", "#00D4FF"]
        layer_names  = ["Input", "Hidden 1", "Hidden 2", "Hidden 3", "Output"]

        self._2d_nodes = []
        self._2d_edges = []
        self._2d_layers = []   # list of list of node indices per layer
        self._layer_names = layer_names
        self._aurora_phase = 0.0   # animated background aurora
        self._energy_burst = []    # list of {x, y, r, life, color} burst rings

        for li, (size, col) in enumerate(zip(layer_sizes, layer_colors)):
            layer_indices = []
            for ni in range(size):
                self._2d_nodes.append({
                    "layer": li,
                    "index_in_layer": ni,
                    "size_in_layer": size,
                    "color": col,
                    "hover": False,
                    "pulse_phase": random.uniform(0, 6.28),
                    "float_phase": random.uniform(0, 6.28),
                    "glow": 0.0,
                    "activation": 0.0,  # 0..1 activation flash
                })
                layer_indices.append(len(self._2d_nodes) - 1)
            self._2d_layers.append(layer_indices)

        # Edges: fully connect adjacent layers
        edge_palette = [
            ["#2a1a4a", "#3b1f6a"],  # input→h1
            ["#1f2a50", "#2a3a60"],  # h1→h2
            ["#1f2a50", "#2a3a60"],  # h2→h3
            ["#0a2a3a", "#1a3a5a"],  # h3→output
        ]
        for li in range(len(layer_sizes) - 1):
            pal = edge_palette[min(li, len(edge_palette)-1)]
            for a in self._2d_layers[li]:
                for b in self._2d_layers[li+1]:
                    self._2d_edges.append({
                        "i": a, "j": b,
                        "color": random.choice(pal),
                        "active_t": -1.0,  # for activation flash
                    })

        # Data packets – more of them, faster
        self._data_packets = []
        for idx, edge in enumerate(self._2d_edges):
            if random.random() < 0.55:
                self._data_packets.append({
                    "edge_idx": idx,
                    "t": random.uniform(0, 1),
                    "speed": random.uniform(0.006, 0.016),
                    "color": random.choice(["#BF5CFF", "#00FF88", "#00E5FF", "#FFD700", "#FF4DC4"]),
                    "trail": [],   # list of recent t values for trail
                    "size": random.uniform(2.5, 4.5),
                })

    def _get_2d_node_pos(self, node_idx):
        """Compute the 2D screen position of a node based on layer layout."""
        nd = self._2d_nodes[node_idx]
        li = nd["layer"]
        ni = nd["index_in_layer"]
        sz = nd["size_in_layer"]

        num_layers = len(self._2d_layers)
        margin_x = 90
        margin_y = 70
        usable_w = max(self.width - 2 * margin_x, 200)
        usable_h = max(self.height - 2 * margin_y, 200)

        # Horizontal position
        x = margin_x + li * (usable_w / (num_layers - 1)) if num_layers > 1 else self.width / 2

        # Vertical position: center the layer
        spacing = usable_h / (sz - 1) if sz > 1 else 0
        y_start = margin_y + (usable_h - spacing * (sz - 1)) / 2
        y = y_start + ni * spacing

        # Subtle floating animation
        float_amp = 2.5
        y += math.sin(nd["float_phase"] + self.time_elapsed * 0.7) * float_amp

        return x, y

    # ═══════════════════════════════════════════════════════════════
    # 2D DRAWING
    # ═══════════════════════════════════════════════════════════════

    def _draw_2d(self):
        """Render the EPIC 2D neural network visualization."""
        c = self.canvas
        t = self.time_elapsed
        W, H = self.width, self.height

        # ── 1. Aurora / Nebula background ────────────────────────────
        self._aurora_phase += 0.012
        ap = self._aurora_phase
        strip_h = max(1, H // 60)
        for row in range(0, H, strip_h):
            fy = row / max(H, 1)
            # Two aurora bands drifting vertically
            band1 = math.sin(fy * 4.5 + ap * 1.3) * 0.5 + 0.5
            band2 = math.sin(fy * 3.0 - ap * 0.9 + 2.1) * 0.5 + 0.5
            r = int(6  + band1 * 14 + band2 * 8)
            g = int(4  + band1 * 6  + band2 * 14)
            b = int(18 + band1 * 30 + band2 * 20)
            r, g, b = min(r, 255), min(g, 255), min(b, 255)
            c.create_rectangle(0, row, W, row + strip_h,
                               fill=f"#{r:02x}{g:02x}{b:02x}", outline="")

        # ── 2. Subtle hex-grid overlay ────────────────────────────────
        grid_spacing = 52
        grid_color = "#0e1428"
        for gx in range(0, W + grid_spacing, grid_spacing):
            for gy in range(0, H + grid_spacing, grid_spacing):
                # just draw cross-hatch dots
                c.create_oval(gx-1, gy-1, gx+1, gy+1, fill=grid_color, outline="")

        # ── 3. Glitch flash ──────────────────────────────────────────
        self._glitch_timer -= 1
        if self._glitch_timer <= 0:
            self._glitch_timer = random.randint(80, 300)
            for _ in range(random.randint(8, 20)):
                gx = random.randint(0, W)
                gy = random.randint(0, H)
                gw = random.randint(4, 60)
                gh = random.randint(1, 5)
                glitch_col, glitch_stip = random.choice([
                    ("#BF5CFF", "gray12"),
                    ("#00FF88", "gray12"),
                    ("#00E5FF", "gray12"),
                    ("#FFD700", "gray12"),
                ])
                c.create_rectangle(gx, gy, gx+gw, gy+gh,
                                   fill=glitch_col, outline="", stipple=glitch_stip)

        # Compute all positions
        positions = [self._get_2d_node_pos(i) for i in range(len(self._2d_nodes))]

        # ── 4. Draw edges with pulse glow ────────────────────────────
        for edge in self._2d_edges:
            x1, y1 = positions[edge["i"]]
            x2, y2 = positions[edge["j"]]
            # Base dim line
            c.create_line(x1, y1, x2, y2, fill=edge["color"], width=1)
            # Subtle bright centre line for key edges
            if random.random() < 0.08:   # occasional bright flash on a random edge
                c.create_line(x1, y1, x2, y2, fill="#ffffff", width=1, stipple="gray12")

        # ── 5. Data packets with glowing trail ───────────────────────
        for pkt in self._data_packets:
            # Advance
            pkt["trail"].append(pkt["t"])
            if len(pkt["trail"]) > 8:
                pkt["trail"].pop(0)
            pkt["t"] += pkt["speed"]
            if pkt["t"] > 1.0:
                pkt["t"] = 0.0
                pkt["trail"] = []

            edge = self._2d_edges[pkt["edge_idx"]]
            x1, y1 = positions[edge["i"]]
            x2, y2 = positions[edge["j"]]
            col = pkt["color"]
            ps  = pkt["size"]

            # Draw trail fragments (fading dots behind the head)
            for ti, tval in enumerate(pkt["trail"]):
                fade = (ti + 1) / len(pkt["trail"])
                tr_x = x1 + (x2 - x1) * tval
                tr_y = y1 + (y2 - y1) * tval
                tr_r = ps * 0.5 * fade
                stip = "gray25" if fade < 0.5 else "gray50"
                c.create_oval(tr_x - tr_r, tr_y - tr_r, tr_x + tr_r, tr_y + tr_r,
                              fill=col, outline="", stipple=stip)

            # Head position
            px = x1 + (x2 - x1) * pkt["t"]
            py = y1 + (y2 - y1) * pkt["t"]

            # Multi-layer glow for head
            for gm, gs in [(5.0, "gray12"), (3.5, "gray25"), (2.2, "gray50")]:
                gr = ps * gm
                c.create_oval(px-gr, py-gr, px+gr, py+gr,
                              fill="", outline=col, stipple=gs, width=1)
            # Bright core
            c.create_oval(px-ps, py-ps, px+ps, py+ps, fill=col, outline="")
            # Hot white centre
            hw = ps * 0.45
            c.create_oval(px-hw, py-hw, px+hw, py+hw, fill="#ffffff", outline="")

        # ── 6. Draw nodes – EPIC multi-ring style ───────────────────
        for idx, nd in enumerate(self._2d_nodes):
            x, y = positions[idx]
            base_r = 20   # bigger nodes
            pulse = math.sin(nd["pulse_phase"] + t * 2.5) * 3.5
            r = base_r + pulse
            col = nd["color"]

            # Expanding ripple wave (2 staggered)
            for wave_off in [0.0, 0.5]:
                ripple_frac = ((t * 0.45 + nd["pulse_phase"] * 0.12 + wave_off) % 1.0)
                if ripple_frac < 0.75:
                    rip_r = r + ripple_frac * 70
                    fade  = 1.0 - ripple_frac / 0.75
                    stip  = "gray12" if fade < 0.3 else ("gray25" if fade < 0.6 else "gray50")
                    c.create_oval(x - rip_r, y - rip_r, x + rip_r, y + rip_r,
                                  fill="", outline=col, stipple=stip, width=1)

            # 5-layer glow halos
            glow_rings = [
                (4.5, "gray12", 1),
                (3.2, "gray25", 1),
                (2.4, "gray50", 1.5),
                (1.8, "gray50", 2),
                (1.35, "",      2.5),
            ]
            for gm, stip, lw in glow_rings:
                gr = r * gm
                kw = {"fill": "", "outline": col, "width": lw}
                if stip:
                    kw["stipple"] = stip
                c.create_oval(x-gr, y-gr, x+gr, y+gr, **kw)

            # Dark fill
            c.create_oval(x-r, y-r, x+r, y+r, fill="#07080f", outline=col, width=2)

            # Concentric inner rings (3)
            for ring_frac, ring_alpha in [(0.72, "gray50"), (0.50, ""), (0.30, "")]:
                rr = r * ring_frac
                kw = {"fill": "", "outline": col, "width": 1.5}
                if ring_alpha:
                    kw["stipple"] = ring_alpha
                c.create_oval(x-rr, y-rr, x+rr, y+rr, **kw)

            # Bright inner disc
            ir = r * 0.28
            c.create_oval(x-ir, y-ir, x+ir, y+ir, fill=col, outline="")
            # Hot white spark in centre
            sp = ir * 0.55
            c.create_oval(x-sp, y-sp, x+sp, y+sp, fill="#ffffff", outline="")

        # ── 7. Draw layer labels ──────────────────────────────────────
        label_colors = ["#00FFB2", "#FF6B35", "#FF6B35", "#FF6B35", "#00D4FF"]
        for li, (layer, name) in enumerate(zip(self._2d_layers, self._layer_names)):
            if not layer:
                continue
            x, _ = positions[layer[0]]
            lc = label_colors[li % len(label_colors)]
            # Glow text (draw twice: dark shadow + bright)
            c.create_text(x+1, 32+1, text=name, fill="#000000",
                          font=("Consolas", 10, "bold"), anchor="n")
            c.create_text(x, 32, text=name,
                          fill=lc, font=("Consolas", 10, "bold"), anchor="n")

        # ── 8. Bottom HUD ─────────────────────────────────────────────
        hud_text = (
            f"  Nodes: {len(self._2d_nodes)}   "
            f"Connections: {len(self._2d_edges)}   "
            f"Packets: {len(self._data_packets)}  "
        )
        c.create_rectangle(0, H - 24, W, H, fill="#04060e", outline="")
        # Animated accent line above HUD
        anim_x = int((t * 60) % W)
        c.create_line(anim_x, H - 24, min(anim_x + 120, W), H - 24,
                      fill="#00FFB2", width=1, stipple="gray50")
        c.create_text(W // 2, H - 12, text=hud_text,
                      fill="#2a4060", font=("Consolas", 9), anchor="center")

    # ═══════════════════════════════════════════════════════════════
    # 3D DRAWING
    # ═══════════════════════════════════════════════════════════════

    def _draw_3d(self):
        if not self.is_dragging:
            self.angle_y += 0.003
            self.angle_x += 0.001

        # 1. Background Stars
        for star in self.stars:
            px, py, scale, raw_z = self._project(star["x"], star["y"], star["z"])
            if 0 < px < self.width and 0 < py < self.height:
                s = star["size"] * scale
                if s > 0.3:
                    self.canvas.create_oval(px-s, py-s, px+s, py+s, fill=star["color"], outline="")

        # 2. 3D Orbital Rings
        self._draw_3d_orbit(180, "#2c3e50", "xz")
        self._draw_3d_orbit(260, "#1f2a36", "xz")
        self._draw_3d_orbit(220, "#2c3e50", "xy")
        self._draw_3d_orbit(220, "#1f2a36", "yz")

        projected_nodes = []
        closest_dist = float('inf')
        hover_idx = None

        for i, node in enumerate(self.nodes):
            px, py, scale, raw_z = self._project(node["x"], node["y"], node["z"])
            p_size = node["base_size"]
            if node["type"] == "brain":
                p_size += math.sin(self.time_elapsed * 3) * 2
            elif node["type"] == "trade":
                if node.get("is_new") and time.time() - node["born"] < 5:
                    p_size += abs(math.sin(self.time_elapsed * 6) * 4)
                else:
                    p_size += math.sin(node["pulse_phase"] + self.time_elapsed * 1.5) * 1.5
            on_screen_size = p_size * scale
            projected_nodes.append({
                "idx": i, "x": px, "y": py, "z": raw_z,
                "scale": scale, "size": on_screen_size, "node": node
            })
            if not self.is_dragging:
                dx, dy = px - self.last_mouse_x, py - self.last_mouse_y
                dist = dx*dx + dy*dy
                if dist < (on_screen_size + 20)**2 and dist < closest_dist:
                    closest_dist = dist
                    hover_idx = i

        self.hovered_node_idx = hover_idx

        # 3. Edges & Data Flow
        for edge_i, (idx1, idx2, etype) in enumerate(self.edges):
            if idx1 >= len(projected_nodes) or idx2 >= len(projected_nodes):
                continue
            p1, p2 = projected_nodes[idx1], projected_nodes[idx2]
            if p1["z"] > 400 or p2["z"] > 400:
                continue
            if etype == "core_link":
                color = "#3a1c52"
                flow_speed, flow_color, dots = 0.04, "#c77dff", 1
            elif etype == "trade_link":
                color = "#004d40" if self.nodes[idx2].get("is_new") and time.time() - self.nodes[idx2]["born"] < 3 else "#102a43"
                flow_speed, flow_color, dots = 0.02, "#00FF66", 2
            else:
                color = "#122a3d"
                flow_speed, flow_color, dots = 0.015, "#00E5FF", 1
            self.canvas.create_line(p1["x"], p1["y"], p2["x"], p2["y"],
                                    fill=color, width=max(0.2, 1.2 * p1["scale"]))
            for d in range(dots):
                offset = (edge_i * 0.17 + d * (1.0/dots))
                packet_pos = (self.time_elapsed * flow_speed + offset) % 1.0
                kx = p1["x"] + (p2["x"] - p1["x"]) * packet_pos
                ky = p1["y"] + (p2["y"] - p1["y"]) * packet_pos
                packet_size = 1.0 * p1["scale"]
                self.canvas.create_oval(kx-packet_size, ky-packet_size,
                                        kx+packet_size, ky+packet_size, fill=flow_color, outline="")

        # 4. Sort Nodes
        projected_nodes.sort(key=lambda n: n["z"], reverse=True)
        for p_node in projected_nodes:
            node, idx = p_node["node"], p_node["idx"]
            px, py, r = p_node["x"], p_node["y"], max(1, p_node["size"])
            color = node["color"]
            if node["type"] == "brain" or node.get("is_new", False) or idx == self.hovered_node_idx:
                for mult, stipple in [(3.0, "gray12"), (2.0, "gray25"), (1.4, "gray50")]:
                    gr = r * mult
                    self.canvas.create_oval(px-gr, py-gr, px+gr, py+gr,
                                            fill="", outline=color, stipple=stipple, width=1.5)
            elif node["type"] == "trade":
                gr = r * 1.5
                self.canvas.create_oval(px-gr, py-gr, px+gr, py+gr,
                                        fill="", outline=color, stipple="gray25")
            self.canvas.create_oval(px-r, py-r, px+r, py+r,
                                    fill=color,
                                    outline="#ffffff" if idx == self.hovered_node_idx else color)
            if idx == self.hovered_node_idx and node["label"]:
                self._draw_tooltip(px, py, node["label"], color)

        # 5. Nova Burst
        if self.nova_active:
            self.nova_radius += 12
            if self.nova_radius < 500:
                nx, ny, _, _ = self._project(0, 0, 0)
                self.canvas.create_oval(nx-self.nova_radius, ny-self.nova_radius,
                                        nx+self.nova_radius, ny+self.nova_radius,
                                        outline="#00E5FF", width=2, dash=(4, 8))
                ir = self.nova_radius * 0.8
                self.canvas.create_oval(nx-ir, ny-ir, nx+ir, ny+ir,
                                        outline="#00FF66", width=1, dash=(2, 6))
            else:
                self.nova_active = False
            for p in self.particles:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["z"] += p["vz"]
                p["life"] -= 0.03
                if p["life"] > 0:
                    px2, py2, scale, _ = self._project(p["x"], p["y"], p["z"])
                    ps = scale * 2
                    if ps > 0:
                        self.canvas.create_oval(px2-ps, py2-ps, px2+ps, py2+ps,
                                                fill=p["color"], outline="")
            self.particles = [p for p in self.particles if p["life"] > 0]

    # ═══════════════════════════════════════════════════════════════
    # MAIN ANIMATION LOOP
    # ═══════════════════════════════════════════════════════════════

    def _animate(self):
        if not self.running:
            return

        self.time_elapsed += 0.05
        self.canvas.delete("all")

        # Determine which mode to draw (during transition draw both at alpha)
        alpha = self._transition_alpha  # 1.0 = fully opaque current mode

        if self._mode == "3D":
            self._draw_3d()
        else:
            self._draw_2d()

        # Fade overlay during transitions
        if self._transitioning and alpha < 0.98:
            # Map alpha to a dark overlay intensity
            fade_level = int((1.0 - alpha) * 220)
            fade_hex = f"#{fade_level:02x}{fade_level:02x}{fade_level:02x}"
            self.canvas.create_rectangle(0, 0, self.width, self.height,
                                         fill=fade_hex, outline="",
                                         stipple="gray50" if fade_level < 100 else "gray75")

        self.after(16, self._animate)

    # ═══════════════════════════════════════════════════════════════
    # TOOLTIPS & DIALOGS
    # ═══════════════════════════════════════════════════════════════

    def _draw_tooltip(self, x, y, text, color):
        lines = text.split("\n")
        w = max(len(l) for l in lines) * 7 + 25
        h = len(lines) * 16 + 15
        x_off, y_off = x + 18, y - 10
        if x_off + w > self.width:
            x_off = x - w - 15
        if y_off + h > self.height:
            y_off = self.height - h - 15
        self.canvas.create_rectangle(x_off, y_off, x_off+w, y_off+h,
                                     fill="#0b0e14", outline=color, width=1.5)
        self.canvas.create_line(x_off, y_off, x_off, y_off+h, fill=color, width=4)
        for i, line in enumerate(lines):
            fw = "bold" if i == 0 else "normal"
            fc = "#ffffff" if i == 0 else "#a0aab5"
            self.canvas.create_text(x_off+12, y_off+12+i*16, anchor="w",
                                    text=line, fill=fc, font=("Inter", 9, fw))

    def _open_trade_details(self, node):
        popup = ctk.CTkToplevel(self)
        symbol = node.get("symbol", "N/A")
        popup.title(f"Trade Detail: {symbol}")
        popup.geometry("380x420")
        popup.attributes("-topmost", True)
        popup.configure(fg_color="#0b0e14")
        hdr = ctk.CTkFrame(popup, fg_color="#141824", corner_radius=0)
        hdr.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(hdr, text=f"🧬 Neural Trade Node // {symbol}",
                     font=("Inter", 16, "bold"), text_color="#e0aaff").pack(pady=15)
        container = ctk.CTkFrame(popup, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25)

        def add_row(parent, label, value, val_color="#ffffff", bold=False):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=8)
            ctk.CTkLabel(row, text=label, text_color="#8B949E", font=("Inter", 13)).pack(side="left")
            fw = "bold" if bold else "normal"
            ctk.CTkLabel(row, text=value, text_color=val_color, font=("Inter", 14, fw)).pack(side="right")

        profit = node.get("profit_pct", 0.0)
        color = node.get("color", "#ffffff")
        sign = "+" if profit > 0 else ""
        add_row(container, "Direction:", node.get("direction", "LONG"), val_color="#00E5FF", bold=True)
        add_row(container, "Entry Price:", f"{node.get('entry_price', 0):.5f}")
        add_row(container, "Exit Price:", f"{node.get('exit_price', 0):.5f}")
        add_row(container, "Duration:", node.get("duration", "N/A"))
        add_row(container, "Net Profit:", f"{sign}{profit:.2f}%", val_color=color, bold=True)
        ctk.CTkButton(popup, text="Schließen", fg_color="#2c3e50",
                      hover_color="#34495e", command=popup.destroy).pack(pady=20)

    def destroy(self):
        self.running = False
        super().destroy()
