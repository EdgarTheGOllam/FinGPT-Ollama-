import customtkinter as ctk
import tkinter as tk
import threading
from datetime import datetime
import re
import os
import time
try:
    from tkinter import TclError
except ImportError:
    TclError = Exception

from gui.design_system import DesignSystem

class TerminalView:
    def __init__(self, master_tab, app):
        """
        master_tab: The ctk.CTkFrame inside the Tabview where this view is rendered.
        app: The ModernFinGPTGUI instance, used to access shared state and methods.
        """
        self.tab = master_tab
        self.app = app
        self._log_buffer = []
        self._log_paused = False
        self._log_filter_value = "ALL"
        self._log_tail_running = False
        self.setup_ui()

    def setup_ui(self):
        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_rowconfigure(1, weight=1)

        # ── Control bar ──────────────────────────────────────────────
        controls = ctk.CTkFrame(self.tab, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))

        ctk.CTkButton(controls, text="🧹 Leeren", command=self.clear_terminal,
                      fg_color="#FF1744", hover_color="#C0392B", width=90).pack(side="left", padx=(0, 6))

        self._pause_btn = ctk.CTkButton(controls, text="⏸ Pause", command=self._toggle_log_pause,
                                        fg_color="#E67E22", hover_color="#D35400", width=90)
        self._pause_btn.pack(side="left", padx=(0, 6))

        ctk.CTkButton(controls, text="📂 Log-Ordner", command=self._open_log_folder,
                      fg_color="transparent", border_width=1, width=110).pack(side="left", padx=(0, 14))

        # Filter buttons
        ctk.CTkLabel(controls, text="Filter:", text_color="#8B949E").pack(side="left", padx=(0, 5))
        for label, val, color in [("Alle", "ALL", "#2979FF"), ("TRADE 💰", "TRADE", "#00FF66"),
                                   ("ERROR ❌", "ERROR", "#FF1744"), ("WARN ⚠️", "WARNING", "#F1C40F"),
                                   ("AI 🤖", "AI", "#8E44AD")]:
            ctk.CTkButton(controls, text=label, width=80,
                          command=lambda v=val: self._set_log_filter(v),
                          fg_color=color, hover_color="#2A2D34",
                          border_width=1).pack(side="left", padx=2)

        # Right side: live log status indicator
        self._log_status_lbl = ctk.CTkLabel(controls, text="● Log: warte...", text_color="#8B949E",
                                             font=ctk.CTkFont(family="Inter", size=11))
        self._log_status_lbl.pack(side="right", padx=15)

        # ── Terminal text box ─────────────────────────────────────────
        # We use the underlying Tk Text widget directly for full tag/color support
        # Design-System Farben verwenden
        ds = DesignSystem
        bg_color = ds.get_color('neutral', 'darker')
        
        self._term_frame = ctk.CTkFrame(self.tab, corner_radius=ds.get_radius('lg'), fg_color=bg_color)
        self._term_frame.grid(row=1, column=0, sticky="nsew", padx=ds.get_spacing('md'), pady=ds.get_spacing('md'))
        self._term_frame.grid_rowconfigure(0, weight=1)
        self._term_frame.grid_columnconfigure(0, weight=1)

        self.terminal_box = tk.Text(self._term_frame,
                                    bg=bg_color, fg=ds.get_semantic_color('neutral'),
                                    font=ds.get_font('sm', 'normal', mono=True),
                                    insertbackground=ds.get_semantic_color('neutral'),
                                    selectbackground=ds.get_color('primary'),
                                    relief="flat", borderwidth=0,
                                    wrap="word", state="disabled")
        self.terminal_box.grid(row=0, column=0, sticky="nsew", padx=ds.get_spacing('sm'), pady=ds.get_spacing('sm'))

        # CustomTkinter Scrollbar (besser integriert)
        sb = ctk.CTkScrollbar(self._term_frame, command=self.terminal_box.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.terminal_box.configure(yscrollcommand=sb.set)

        # Color tags - mit Design-System Farben
        self.terminal_box.tag_configure("ts",      foreground=ds.get_color('primary', 'light'))      # timestamp (hellblau)
        self.terminal_box.tag_configure("INFO",    foreground=ds.get_semantic_color('neutral'))     # neutral grau
        self.terminal_box.tag_configure("SYSTEM",  foreground=ds.get_color('secondary', 'light'))   # lila-licht
        self.terminal_box.tag_configure("MT5",     foreground=ds.get_color('success', 'light'))     # grün-licht
        self.terminal_box.tag_configure("AI",      foreground=ds.get_color('secondary'))            # lila
        self.terminal_box.tag_configure("TRADE",   foreground=ds.get_semantic_color('profit'))      # grün ★ important
        self.terminal_box.tag_configure("WARNING", foreground=ds.get_semantic_color('warning'))     # orange
        self.terminal_box.tag_configure("ERROR",   foreground=ds.get_semantic_color('error'), 
                                        font=(ds.TYPOGRAPHY['font_family_mono'], ds.TYPOGRAPHY['sizes']['sm'], "bold"))
        self.terminal_box.tag_configure("DEBUG",   foreground=ds.get_color('neutral', 'medium'))    # mittelgrau
        self.terminal_box.tag_configure("INDICATORS", foreground=ds.get_color('warning', 'dark'))   # dunkel orange
        self.terminal_box.tag_configure("RISK",    foreground=ds.get_semantic_color('error'))       # rot
        self.terminal_box.tag_configure("PROMPT",  foreground=ds.get_color('warning'))              # gelb
        self.terminal_box.tag_configure("CATEGORY",foreground=ds.get_color('success', 'dark'))      # dunkelgrün
        self.terminal_box.tag_configure("separator",foreground=ds.get_color('neutral', 'medium'))

        # Boot messages
        self.write_terminal("FinGPT Professional", "SYSTEM")
        self.write_terminal("  ─────────────────────────────────────────────\n", "separator")
        self.write_terminal("  System initialisiert. Log-Stream startet...\n\n", "SYSTEM")

        # Start live log tail
        self._start_log_tail()

    def write_terminal(self, text, tag="INFO"):
        """Write colored text to the terminal safely from any thread."""
        self._safe_after(0, lambda t=text, tg=tag: self._write_terminal_sync(t, tg))

    def _write_terminal_sync(self, text, tag="INFO"):
        try:
            # ── 0. Auto-Tagging (falls kein spezieller Tag übergeben wurde)
            if tag == "INFO":
                if "[ERROR]" in text or "❌" in text:
                    tag = "ERROR"
                elif "[WARNING]" in text or "WARN" in text or "⚠️" in text:
                    tag = "WARNING"
                elif "[TRADE]" in text or "💰" in text or "✅" in text:
                    tag = "TRADE"
                elif "[AI]" in text or "🤖" in text:
                    tag = "AI"
                elif "[MT5]" in text or "📊" in text:
                    tag = "MT5"
                elif "[RISK]" in text:
                    tag = "RISK"
                elif "[SYSTEM]" in text or "FinGPT" in text:
                    tag = "SYSTEM"
                elif "[DEBUG]" in text:
                    tag = "DEBUG"

            # ── 1. Timestamping 
            if text.strip() and not re.match(r'^\[\d{2}:\d{2}:\d{2}\]', text.strip()):
                timestamp = datetime.now().strftime('%H:%M:%S')
                text = f"[{timestamp}] {text}"
                
            # Ersetze literales "\n" durch echte Zeilenumbrüche
            text = text.replace('\\n', '\n')
            
            # Füge einen leeren Zeilenumbruch (leere Spalte) am Ende hinzu, wenn nicht vorhanden
            text = text.rstrip('\n') + '\n\n'
                
            # Keep max 1000 lines in memory
            if len(self._log_buffer) > 1000:
                self._log_buffer.pop(0)
            self._log_buffer.append((text, tag))

            # ── 3. Check filters & pause 
            if self._log_paused:
                return
            if self._log_filter_value != "ALL" and tag != "separator" and tag != "SYSTEM":
                # Only show selected filter (System/Separator always pass)
                if tag != self._log_filter_value:
                    return

            tb = self.terminal_box
            tb.configure(state="normal")
            tb.insert("end", text, tag)
            tb.configure(state="disabled")
            tb.see("end")
        except Exception:
            pass  # terminal may not be ready yet

    def clear_terminal(self):
        self._safe_after(0, self._clear_terminal_sync)

    def _clear_terminal_sync(self):
        try:
            self._log_buffer.clear()
            self.terminal_box.configure(state="normal")
            self.terminal_box.delete("1.0", "end")
            self.terminal_box.configure(state="disabled")
            self.write_terminal("> Terminal geleert\n", "SYSTEM")
        except Exception:
            pass

    def _toggle_log_pause(self):
        self._log_paused = not self._log_paused
        tb = self.terminal_box
        if self._log_paused:
            self._pause_btn.configure(text="▶ Weiter", fg_color="#00FF66", hover_color="#4CAF50")
            tb.configure(state="normal")
            tb.insert("end", "\n--- TERMINAL PAUSIERT ---\n", "WARNING")
            tb.configure(state="disabled")
            tb.see("end")
        else:
            self._pause_btn.configure(text="⏸ Pause", fg_color="#E67E22", hover_color="#D35400")
            # Force re-render from buffer to catch up
            self._set_log_filter(self._log_filter_value, soft_refresh=True)

    def _open_log_folder(self):
        import subprocess
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
        os.makedirs(log_dir, exist_ok=True)
        subprocess.Popen(f'explorer "{log_dir}"')

    def _set_log_filter(self, value, soft_refresh=False):
        self._log_filter_value = value
        
        # Re-render entire terminal from buffer
        tb = self.terminal_box
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        
        if not soft_refresh:
            tb.insert("end", f"\n── Filter gesetzt: {value} ──\n", "separator")
        
        for text, tag in self._log_buffer:
            if value == "ALL" or tag == value or tag in ("SYSTEM", "separator", "INFO"):
                tb.insert("end", text, tag)
                
        tb.configure(state="disabled")
        tb.see("end")

    def _parse_log_line(self, line):
        """Parse a FinGPT log line and return (formatted_text, tag).
        Log format: '2024-01-01 12:34:56,789 | INFO | [CATEGORY] message'
        or console format: '12:34:56 ℹ️  [SYSTEM] message'
        """
        line = line.rstrip('\n\r')
        if not line.strip():
            return None, None

        # Determine color tag by scanning for known keywords
        tag = "INFO"
        if "ERROR" in line or "❌" in line:
            tag = "ERROR"
        elif "WARNING" in line or "WARN" in line or "⚠️" in line:
            tag = "WARNING"
        elif "TRADE" in line or "💰" in line or "BUY" in line or "SELL" in line or "ORDER" in line:
            tag = "TRADE"
        elif "AI" in line or "🤖" in line or "LLM" in line or "Ollama" in line or "model" in line.lower():
            tag = "AI"
        elif "MT5" in line or "📊" in line or "MetaTrader" in line:
            tag = "MT5"
        elif "RISK" in line or "risk" in line.lower():
            tag = "RISK"
        elif "INDICATOR" in line or "indicator" in line.lower():
            tag = "INDICATORS"
        elif "DEBUG" in line or "🔍" in line:
            tag = "DEBUG"
        elif "SYSTEM" in line or "FinGPT" in line:
            tag = "SYSTEM"

        # Format: prepend a clean timestamp if not already at start
        ts_match = re.match(r'(\d{2}:\d{2}:\d{2})', line)
        full_ts_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)

        if full_ts_match:
            # Standard logging format: strip date, keep time
            ts = full_ts_match.group(1).split(' ')[1]
            body = line[len(full_ts_match.group(1)):].lstrip(' |,0123456789')
            return f"  {ts}  {body}\n", tag
        elif ts_match:
            # Already has HH:MM:SS prefix
            return f"  {line}\n", tag
        else:
            return f"  {line}\n", tag

    def _safe_after(self, ms, func):
        """Schedule func on the main thread, silently ignoring errors if the
        Tkinter event loop has already been torn down."""
        try:
            self.app.after(ms, func)
        except (RuntimeError, TclError):
            # Window destroyed – stop the tail loop
            self._log_tail_running = False

    def destroy(self):
        """Stop the background log-tail thread (call when the tab/app closes)."""
        self._log_tail_running = False

    def _start_log_tail(self):
        """Start background thread that tails the live FinGPT log file."""
        self._log_tail_running = True

        def tail_loop():
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
            last_inode = None
            last_pos = 0

            while self._log_tail_running:
                try:
                    log_file = os.path.join(log_dir, f"fingpt_{datetime.now().strftime('%Y%m%d')}.log")
                    if not os.path.exists(log_file):
                        self._safe_after(0, lambda: self._log_status_lbl.configure(
                            text="● Log: keine Datei", text_color="#8B949E"))
                        time.sleep(3)
                        continue

                    stat = os.stat(log_file)
                    inode = stat.st_ino

                    if inode != last_inode:
                        # File rotated or first open
                        last_inode = inode
                        last_pos = 0

                    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(last_pos)
                        lines = f.readlines()
                        last_pos = f.tell()

                    if lines:
                        for line in lines:
                            text, tag = self._parse_log_line(line)
                            if text:
                                self._safe_after(0, lambda t=text, tg=tag: self.write_terminal(t, tg))

                        count = stat.st_size
                        self._safe_after(0, lambda c=count: self._log_status_lbl.configure(
                            text=f"● Log aktiv  ({c//1024}KB)", text_color="#00FF66"))
                    else:
                        self._safe_after(0, lambda: self._log_status_lbl.configure(
                            text="● Log: verbunden", text_color="#00FF66"))

                except (RuntimeError, TclError):
                    # Tkinter is gone – exit thread cleanly
                    self._log_tail_running = False
                    return
                except Exception as ex:
                    self._safe_after(0, lambda e=str(ex): self._log_status_lbl.configure(
                        text=f"● Log Fehler: {e[:30]}", text_color="#FF1744"))

                time.sleep(1)  # poll every 1 second

        threading.Thread(target=tail_loop, daemon=True).start()

    def simulate_terminal_output(self):
        """Kept for backwards compatibility - now injects a realistic log line."""
        msgs = [
            ("12:34:56 ℹ️  [SYSTEM] Analysiere EURUSD Marktstruktur...", "SYSTEM"),
            ("12:34:57 💰 [TRADE] BUY Signal erkannt | GBPUSD | Konfidenz: 87.4%", "TRADE"),
            ("12:34:58 🤖 [AI] Ollama Inference abgeschlossen | 412ms | model: llama3", "AI"),
            ("12:34:59 ⚠️  [WARNING] Margin Level unter 200% - Vorsicht!", "WARNING"),
            ("12:35:00 📊 [MT5] Tick empfangen: EURUSD Bid=1.08421 Ask=1.08435", "MT5"),
            ("12:35:01 ❌ [ERROR] Slippage zu hoch auf USDJPY - Trade abgebrochen", "ERROR"),
            ("12:35:02 ℹ️  [RISK] Max Daily Loss Grenze: 3.0% | Aktuell: 0.8%", "RISK"),
        ]
        import random
        txt, tag = random.choice(msgs)
        self.write_terminal(f"  {txt}\n", tag)
