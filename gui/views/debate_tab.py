import re
import threading
import tkinter as tk
import customtkinter as ctk


class DebateView:
    def __init__(self, tab, app):
        """
        tab: The ctk.CTkFrame inside the Tabview where this view is rendered.
        app: The ModernFinGPTGUI instance, used to access shared state and methods.
        """
        self.tab = tab
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        """🎭 KI Debate Mode — Bull vs Bear vs Judge."""
        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_rowconfigure(2, weight=1)

        # ── Header / Controls ────────────────────────────────
        ctrl = ctk.CTkFrame(self.tab, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        ctrl.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(ctrl, text="🎭 KI Debate Mode",
                     font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
                     text_color="#A855F7").grid(row=0, column=0, padx=(0, 20), sticky="w")

        ctk.CTkLabel(ctrl, text="Symbol:").grid(row=0, column=1, padx=(0, 6), sticky="w")
        self._debate_symbol = ctk.CTkEntry(ctrl, width=120, placeholder_text="EURUSD")
        self._debate_symbol.insert(0, "EURUSD")
        self._debate_symbol.grid(row=0, column=2, sticky="w", padx=(0, 12))

        self._debate_btn = ctk.CTkButton(
            ctrl, text="⚔️ Debatte starten",
            fg_color="#7C3AED", hover_color="#6D28D9", width=170,
            command=self._start_debate)
        self._debate_btn.grid(row=0, column=3, padx=(0, 12))

        self._debate_status = ctk.CTkLabel(ctrl, text="Bereit.", text_color="#8B949E",
                                           font=ctk.CTkFont(family="Inter", size=12))
        self._debate_status.grid(row=0, column=4, sticky="w")

        # ── Progress bar ─────────────────────────────────────
        self._debate_progress = ctk.CTkProgressBar(self.tab, mode="indeterminate",
                                                    progress_color="#7C3AED")
        self._debate_progress.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        self._debate_progress.set(0)

        # ── Main debate area: Bull | Bear ─────────────────────
        panels = ctk.CTkFrame(self.tab, fg_color="transparent")
        panels.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 6))
        panels.grid_columnconfigure((0, 1), weight=1)
        panels.grid_rowconfigure(1, weight=1)

        # Bull panel
        bull_hdr = ctk.CTkFrame(panels, fg_color=("gray90", "#14532D"), corner_radius=10)
        bull_hdr.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 4))
        ctk.CTkLabel(bull_hdr, text="🟢 BULL Analyst",
                     font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                     text_color="#4ADE80").pack(anchor="w", padx=12, pady=8)

        self._bull_box = self._make_rich_textbox(panels, accent="#4ADE80")
        self._bull_box.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        # Bear panel
        bear_hdr = ctk.CTkFrame(panels, fg_color=("gray90", "#7F1D1D"), corner_radius=10)
        bear_hdr.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 4))
        ctk.CTkLabel(bear_hdr, text="🔴 BEAR Analyst",
                     font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                     text_color="#F87171").pack(anchor="w", padx=12, pady=8)

        self._bear_box = self._make_rich_textbox(panels, accent="#F87171")
        self._bear_box.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

        # ── Verdict panel ─────────────────────────────────────
        verdict_frame = ctk.CTkFrame(self.tab, corner_radius=12, fg_color="#1A1D24")
        verdict_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))
        verdict_frame.grid_columnconfigure(1, weight=1)
        self.tab.grid_rowconfigure(3, weight=0)

        ctk.CTkLabel(verdict_frame, text="⚖️",
                     font=ctk.CTkFont(family="Inter", size=26)).grid(row=0, column=0, padx=(14, 8), pady=10)
        self._verdict_lbl = ctk.CTkLabel(verdict_frame,
                                          text="Richter-Urteil erscheint hier nach der Debatte…",
                                          font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
                                          text_color="#8B949E", wraplength=700, justify="left")
        self._verdict_lbl.grid(row=0, column=1, sticky="w", padx=(0, 14), pady=10)

    # ── Rich Text / Markdown helpers ─────────────────────────────────────────

    def _make_rich_textbox(self, parent, accent: str = "#D4D4D4") -> tk.Text:
        """Create a native tk.Text widget configured for Markdown rendering."""
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg   = "#1e1e1e" if is_dark else "#f8f8f8"
        fg   = "#D4D4D4" if is_dark else "#111111"
        sel  = "#3a3a3a" if is_dark else "#c8e6fa"

        txt = tk.Text(
            parent,
            wrap="word",
            state="disabled",
            relief="flat",
            bd=0,
            bg=bg,
            fg=fg,
            selectbackground=sel,
            selectforeground=fg,
            padx=14,
            pady=10,
            cursor="arrow",
            font=("Inter", 12),
        )
        txt.configure(highlightthickness=0)

        # ── Define tags for Markdown elements ──
        # Headings
        txt.tag_configure("h1", font=("Inter", 18, "bold"),   foreground=accent,  spacing3=6)
        txt.tag_configure("h2", font=("Inter", 15, "bold"),   foreground=accent,  spacing3=4)
        txt.tag_configure("h3", font=("Inter", 13, "bold"),   foreground=accent,  spacing3=2)
        # Inline styles
        txt.tag_configure("bold",   font=("Inter", 12, "bold"))
        txt.tag_configure("italic", font=("Inter", 12, "italic"))
        txt.tag_configure("bold_italic", font=("Inter", 12, "bold italic"))
        txt.tag_configure("code",   font=("Courier New", 11), background="#2a2a2a" if is_dark else "#e8e8e8",
                          foreground="#FCD34D")
        # Other
        txt.tag_configure("hr",     font=("Inter", 6),        foreground="#555555")
        txt.tag_configure("bullet", lmargin1=16, lmargin2=28, spacing1=2)
        txt.tag_configure("table_header",  font=("Inter", 11, "bold"), foreground=accent)
        txt.tag_configure("table_sep",     font=("Courier New", 10),  foreground="#555555")
        txt.tag_configure("table_cell",    font=("Inter", 11))
        txt.tag_configure("blockquote",    lmargin1=20, lmargin2=20,
                          foreground="#9ca3af", font=("Inter", 12, "italic"))
        txt.tag_configure("normal", font=("Inter", 12))

        return txt

    def _render_markdown(self, widget: tk.Text, text: str, accent: str = "#D4D4D4"):
        """Parse markdown text and insert it into a tk.Text widget with appropriate tags."""
        widget.configure(state="normal")
        widget.delete("1.0", "end")

        lines = text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # ── Horizontal rule ──────────────────────────────
            if re.match(r"^(\-{3,}|\*{3,}|_{3,})\s*$", line):
                widget.insert("end", "─" * 62 + "\n", "hr")
                i += 1
                continue

            # ── Headings ─────────────────────────────────────
            h_match = re.match(r"^(#{1,3})\s+(.+)", line)
            if h_match:
                level = len(h_match.group(1))
                text_part = h_match.group(2)
                tag = f"h{level}"
                self._insert_inline(widget, text_part, base_tag=tag, accent=accent)
                widget.insert("end", "\n", tag)
                i += 1
                continue

            # ── Blockquote ───────────────────────────────────
            if line.startswith("> "):
                content = line[2:]
                self._insert_inline(widget, content, base_tag="blockquote", accent=accent)
                widget.insert("end", "\n", "blockquote")
                i += 1
                continue

            # ── Table – detect by pipe characters ────────────
            if "|" in line and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|", lines[i + 1]):
                # Header row
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                row_text = "  ".join(f"{c:<18}" for c in cells)
                widget.insert("end", row_text + "\n", "table_header")
                i += 1
                # Separator row
                if i < len(lines) and re.match(r"^\|[\s\-:|]+\|", lines[i]):
                    sep = "─" * min(62, len(row_text))
                    widget.insert("end", sep + "\n", "table_sep")
                    i += 1
                # Data rows
                while i < len(lines) and "|" in lines[i]:
                    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    row_text = "  ".join(f"{c:<18}" for c in cells)
                    widget.insert("end", row_text + "\n", "table_cell")
                    i += 1
                widget.insert("end", "\n")
                continue

            # ── Bullet list  ─────────────────────────────────
            bullet_match = re.match(r"^(\s*[-*+]|\s*\d+\.)\s+(.+)", line)
            if bullet_match:
                content = bullet_match.group(2)
                indent = len(re.match(r"^\s*", line).group())
                is_numbered = bool(re.match(r"^\s*\d+\.", line))
                prefix = "• " if not is_numbered else re.match(r"(\s*\d+\.\s*)", line).group(1)
                widget.insert("end", " " * indent + prefix, "bullet")
                self._insert_inline(widget, content, base_tag="bullet", accent=accent)
                widget.insert("end", "\n", "bullet")
                i += 1
                continue

            # ── Empty line ───────────────────────────────────
            if line.strip() == "":
                widget.insert("end", "\n")
                i += 1
                continue

            # ── Normal paragraph line ─────────────────────────
            self._insert_inline(widget, line, base_tag="normal", accent=accent)
            widget.insert("end", "\n", "normal")
            i += 1

        widget.configure(state="disabled")

    def _insert_inline(self, widget: tk.Text, text: str, base_tag: str = "normal", accent: str = "#D4D4D4"):
        """Insert text with inline Markdown formatting (bold, italic, code) applied via tags."""
        # Pattern: ***bold italic***, **bold**, *italic*, `code`
        pattern = re.compile(
            r"(\*\*\*(.+?)\*\*\*"     # ***bold italic***
            r"|\*\*(.+?)\*\*"          # **bold**
            r"|\*(.+?)\*"              # *italic*
            r"|`(.+?)`)"               # `code`
        )
        last = 0
        for m in pattern.finditer(text):
            # Insert plain text before match
            if m.start() > last:
                widget.insert("end", text[last:m.start()], base_tag)
            # ── Determine which matched group ──
            if m.group(2):  # ***bold italic***
                widget.insert("end", m.group(2), ("bold_italic", base_tag))
            elif m.group(3):  # **bold**
                widget.insert("end", m.group(3), ("bold", base_tag))
            elif m.group(4):  # *italic*
                widget.insert("end", m.group(4), ("italic", base_tag))
            elif m.group(5):  # `code`
                widget.insert("end", m.group(5), ("code",))
            last = m.end()
        # Remaining plain text
        if last < len(text):
            widget.insert("end", text[last:], base_tag)

    # ── Debate helpers ─────────────────────────────────────────────────────
    def _start_debate(self):
        symbol = self._debate_symbol.get().strip().upper() or "EURUSD"
        self._debate_btn.configure(state="disabled", text="⏳ Läuft…")
        self._debate_status.configure(text="Starte Debatte…", text_color="#A855F7")
        self._debate_progress.start()
        self.app.after(0, lambda: self._render_markdown(self._bull_box, "🟢 _Warte auf Bull Analyst…_\n", "#4ADE80"))
        self.app.after(0, lambda: self._render_markdown(self._bear_box, "🔴 _Warte auf Bear Analyst…_\n", "#F87171"))
        self._verdict_lbl.configure(text="⚖️ Richter analysiert noch…", text_color="#8B949E")
        threading.Thread(target=self._run_debate_bg, args=(symbol,), daemon=True).start()

    def _run_debate_bg(self, symbol: str):
        """Background thread: fetch market data → 3 LLM calls → update UI."""
        import MetaTrader5 as mt5
        try:
            # ── Step 0: Gather basic market data from MT5 ──────────────
            market_ctx = f"Symbol: {symbol}\n"
            try:
                if mt5.initialize():
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        market_ctx += f"Bid: {tick.bid:.5f} | Ask: {tick.ask:.5f}\n"
                    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 20)
                    if rates is not None and len(rates) > 1:
                        closes = [r['close'] for r in rates]
                        gain = closes[-1] - closes[0]
                        market_ctx += f"H1 letzte 20 Kerzen: Eröffnung {closes[0]:.5f} → Jetzt {closes[-1]:.5f} | Diff: {gain:+.5f}\n"
                else:
                    market_ctx += "(MT5 nicht verfügbar – nur KI-Analyse)\n"
            except Exception:
                market_ctx += "(MT5 nicht verfügbar – nur KI-Analyse)\n"

            user_msg = (
                f"Analysiere {symbol} für einen möglichen Trade.\n"
                f"Marktdaten:\n{market_ctx}\n"
                "Antworte auf Deutsch. Nutze **fett** für wichtige Begriffe, ## für Abschnitte, "
                "- für Listen und | für Tabellen (Markdown-Format). Verfasse eine ausführliche strukturierte Analyse."
            )

            # ── Step 1: BULL ─────────────────────────────────────────
            self.app.after(0, lambda: self._debate_status.configure(
                text="🟢 Bull Analyst denkt…", text_color="#4ADE80"))
            bull_sys = (
                "Du bist ein sehr optimistischer Forex-Analyst. "
                "Deine Aufgabe ist es, ausschließlich BUY/Long-Argumente für das Symbol zu finden. "
                "Nenne konkrete technische und fundamentale Gründe, warum jetzt ein KAUF sinnvoll ist. "
                "Sei überzeugend und zeige mögliche Gewinnziele. "
                "Formatiere deine Antwort mit Markdown: Nutze **fett**, ## Überschriften, - Listen und Tabellen."
            )
            bull_text = self.app._call_llm_api(system_prompt=bull_sys, user_prompt=user_msg, max_tokens=4096)
            self.app.after(0, lambda t=bull_text: self._render_markdown(self._bull_box, t, "#4ADE80"))
            if bull_text.startswith("[API Fehler"):
                raise Exception(f"Bull Analyst: {bull_text}")

            # ── Step 2: BEAR ─────────────────────────────────────────
            self.app.after(0, lambda: self._debate_status.configure(
                text="🔴 Bear Analyst denkt…", text_color="#F87171"))
            bear_sys = (
                "Du bist ein sehr pessimistischer Forex-Analyst. "
                "Deine Aufgabe ist es, ausschließlich SELL/Short-Argumente für das Symbol zu finden. "
                "Nenne konkrete technische und fundamentale Gründe, warum jetzt ein VERKAUF sinnvoll ist. "
                "Sei überzeugend und zeige mögliche Verlustrisiken beim Kauf. "
                "Formatiere deine Antwort mit Markdown: Nutze **fett**, ## Überschriften, - Listen und Tabellen."
            )
            bear_text = self.app._call_llm_api(system_prompt=bear_sys, user_prompt=user_msg, max_tokens=4096)
            self.app.after(0, lambda t=bear_text: self._render_markdown(self._bear_box, t, "#F87171"))
            if bear_text.startswith("[API Fehler"):
                raise Exception(f"Bear Analyst: {bear_text}")

            # ── Step 3: JUDGE ────────────────────────────────────────
            self.app.after(0, lambda: self._debate_status.configure(
                text="⚖️ Richter urteilt…", text_color="#FBBF24"))
            judge_sys = (
                "Du bist ein unparteiischer Senior-Analyst. Du hast gerade zwei Analysten gehört: "
                "einen sehr bullischen und einen sehr bärischen. "
                "Deine Aufgabe: Bewerte beide Argumente fair, entscheide wer recht hat, "
                "und gib eine klare Empfehlung: BUY, SELL oder HOLD. "
                "Format deiner Antwort: Kurze Zusammenfassung beider Seiten (2 Sätze), "
                "dann: URTEIL: [BUY/SELL/HOLD] — Konfidenz: [0-100%] — Grund: [1 Satz]"
            )
            judge_msg = (
                f"Symbol: {symbol}\n\n"
                f"BULL-Argumente:\n{bull_text}\n\n"
                f"BEAR-Argumente:\n{bear_text}\n\n"
                "Was ist dein Urteil?"
            )
            verdict = self.app._call_llm_api(system_prompt=judge_sys, user_prompt=judge_msg, max_tokens=4096)
            if verdict.startswith("[API Fehler"):
                raise Exception(f"Richter: {verdict}")

            # Parse verdict colour
            v_upper = verdict.upper()
            if "BUY" in v_upper:
                v_color = "#4ADE80"
            elif "SELL" in v_upper:
                v_color = "#F87171"
            else:
                v_color = "#FBBF24"

            self.app.after(0, lambda t=verdict, c=v_color: (
                self._verdict_lbl.configure(text=t, text_color=c),
                self._debate_status.configure(text="Debatte abgeschlossen ✅", text_color="#8B949E"),
            ))

        except Exception as e:
            err_str = str(e)
            # Verbesserte Fehlermeldung für Ollama-Probleme
            if "Ollama" in err_str or "11434" in err_str or "Connection" in err_str:
                if "nicht erreichbar" in err_str or "Connection refused" in err_str or "10061" in err_str:
                    user_msg = "Ollama nicht erreichbar! Bitte Ollama starten (ollama serve) oder in den Einstellungen die URL prüfen."
                elif "automatisch zu starten" in err_str:
                    user_msg = "Ollama konnte nicht automatisch gestartet werden. Bitte manuell starten."
                else:
                    user_msg = f"Ollama Fehler: {err_str}"
            else:
                user_msg = f"Fehler: {err_str}"
            self.app.after(0, lambda msg=user_msg: (
                self._debate_status.configure(text=msg, text_color="#F87171"),
                self._bull_box.configure(state="normal"),
                self._bull_box.delete("1.0", "end"),
                self._bull_box.insert("1.0", f"❌ Fehler bei der Analyse.\n\n{user_msg}\n\nBitte überprüfen Sie:\n1. Ollama läuft (ollama serve)\n2. URL in den Einstellungen korrekt ist\n3. Ein Modell ausgewählt ist"),
                self._bull_box.configure(state="disabled"),
                self._bear_box.configure(state="normal"),
                self._bear_box.delete("1.0", "end"),
                self._bear_box.insert("1.0", "—"),
                self._bear_box.configure(state="disabled")
            ))
        finally:
            self.app.after(0, self._debate_progress.stop)
            self.app.after(0, lambda: self._debate_btn.configure(
                state="normal", text="⚔️ Debatte starten"))
