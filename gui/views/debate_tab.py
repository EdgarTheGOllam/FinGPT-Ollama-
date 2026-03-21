import customtkinter as ctk
import threading

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
        bull_hdr = ctk.CTkFrame(panels, fg_color=("#DCFCE7", "#14532D"), corner_radius=10)
        bull_hdr.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 4))
        ctk.CTkLabel(bull_hdr, text="🟢 BULL Analyst",
                     font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                     text_color="#4ADE80").pack(anchor="w", padx=12, pady=8)

        self._bull_box = ctk.CTkTextbox(panels, corner_radius=10,
                                         fg_color=("gray92", "gray12"),
                                         font=ctk.CTkFont(family="Inter", size=12),
                                         text_color="#4ADE80", wrap="word",
                                         state="disabled")
        self._bull_box.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        # Bear panel
        bear_hdr = ctk.CTkFrame(panels, fg_color=("#FEE2E2", "#7F1D1D"), corner_radius=10)
        bear_hdr.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 4))
        ctk.CTkLabel(bear_hdr, text="🔴 BEAR Analyst",
                     font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                     text_color="#F87171").pack(anchor="w", padx=12, pady=8)

        self._bear_box = ctk.CTkTextbox(panels, corner_radius=10,
                                         fg_color=("gray92", "gray12"),
                                         font=ctk.CTkFont(family="Inter", size=12),
                                         text_color="#F87171", wrap="word",
                                         state="disabled")
        self._bear_box.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

        # ── Verdict panel ─────────────────────────────────────
        verdict_frame = ctk.CTkFrame(self.tab, corner_radius=12,
                                      fg_color="#1A1D24")
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

    # ── Debate helpers ─────────────────────────────────────────────────────
    def _start_debate(self):
        symbol = self._debate_symbol.get().strip().upper() or "EURUSD"
        self._debate_btn.configure(state="disabled", text="⏳ Läuft…")
        self._debate_status.configure(text="Starte Debatte…", text_color="#A855F7")
        self._debate_progress.start()
        self._write_debate_box(self._bull_box, "🟢 Warte auf Bull Analyst…\n", "#4ADE80")
        self._write_debate_box(self._bear_box, "🔴 Warte auf Bear Analyst…\n", "#F87171")
        self._verdict_lbl.configure(text="⚖️ Richter analysiert noch…", text_color="#8B949E")
        threading.Thread(target=self._run_debate_bg, args=(symbol,), daemon=True).start()

    def _write_debate_box(self, box: ctk.CTkTextbox, text: str, color: str = "#D4D4D4"):
        box.configure(state="normal")
        box.delete("0.0", "end")
        box.insert("end", text)
        box.configure(state="disabled", text_color=color)

    def _run_debate_bg(self, symbol: str):
        """Background thread: fetch market data → 3 Ollama calls → update UI."""
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
                "Antworte auf Deutsch. Maximal 200 Wörter."
            )

            # ── Step 1: BULL ─────────────────────────────────────────
            self.app.after(0, lambda: self._debate_status.configure(
                text="🟢 Bull Analyst denkt…", text_color="#4ADE80"))
            bull_sys = (
                "Du bist ein sehr optimistischer Forex-Analyst. "
                "Deine Aufgabe ist es, ausschließlich BUY/Long-Argumente für das Symbol zu finden. "
                "Nenne konkrete technische und fundamentale Gründe, warum jetzt ein KAUF sinnvoll ist. "
                "Sei überzeugend und zeige mögliche Gewinnziele."
            )
            # Route API call through app instance
            bull_text = self.app._call_llm_api(system_prompt=bull_sys, user_prompt=user_msg, max_tokens=1024)
            self.app.after(0, lambda t=bull_text: self._write_debate_box(self._bull_box, t, "#4ADE80"))

            # ── Step 2: BEAR ─────────────────────────────────────────
            self.app.after(0, lambda: self._debate_status.configure(
                text="🔴 Bear Analyst denkt…", text_color="#F87171"))
            bear_sys = (
                "Du bist ein sehr pessimistischer Forex-Analyst. "
                "Deine Aufgabe ist es, ausschließlich SELL/Short-Argumente für das Symbol zu finden. "
                "Nenne konkrete technische und fundamentale Gründe, warum jetzt ein VERKAUF sinnvoll ist. "
                "Sei überzeugend und zeige mögliche Verlustrisiken beim Kauf."
            )
            bear_text = self.app._call_llm_api(system_prompt=bear_sys, user_prompt=user_msg, max_tokens=1024)
            self.app.after(0, lambda t=bear_text: self._write_debate_box(self._bear_box, t, "#F87171"))

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
            verdict = self.app._call_llm_api(system_prompt=judge_sys, user_prompt=judge_msg, max_tokens=1024)

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
            self.app.after(0, lambda err=e: self._debate_status.configure(
                text=f"Fehler: {err}", text_color="#F87171"))
        finally:
            self.app.after(0, self._debate_progress.stop)
            self.app.after(0, lambda: self._debate_btn.configure(
                state="normal", text="⚔️ Debatte starten"))
