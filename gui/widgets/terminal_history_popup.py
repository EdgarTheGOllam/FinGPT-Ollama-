#!/usr/bin/env python3
"""
Terminal History Popup
Popup-Fenster zur Anzeige der Terminal-Sitzungshistorie
"""

import customtkinter as ctk
import tkinter as tk
from datetime import datetime
from typing import Optional, Dict, Any, List

from gui.design_system import DesignSystem


class TerminalHistoryPopup(ctk.CTkToplevel):
    """
    Popup-Fenster zur Anzeige und Verwaltung der Terminal-Sitzungshistorie.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Fenster konfigurieren
        self.title("📜 Terminal Historie")
        self.geometry("900x600")
        self.resizable(True, True)
        
        # Design System
        ds = DesignSystem
        bg_color = ds.get_color('neutral', 'darker')
        
        self.configure(fg_color=bg_color)
        
        # Verhindern, dass das Fenster maximiert werden kann
        self.attributes('-topmost', True)
        
        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        
        self._setup_ui()
        
        # Zentrieren des Fensters
        self._center_window()
    
    def _center_window(self):
        """Zentriert das Fenster auf dem Bildschirm."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def _setup_ui(self):
        """Richtet die UI-Komponenten ein."""
        ds = DesignSystem
        bg_color = ds.get_color('neutral', 'darker')
        surface_color = ds.get_color('neutral', 'dark')
        
        # ═══════════════════════════════════════════════════════════
        # Linke Seite: Session-Liste
        # ═══════════════════════════════════════════════════════════
        left_frame = ctk.CTkFrame(self, fg_color=surface_color, corner_radius=ds.get_radius('md'))
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)
        
        # Header
        header = ctk.CTkLabel(
            left_frame, 
            text="📂 Sessions",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=ds.get_semantic_color('neutral')
        )
        header.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))
        
        # Session-Liste (Scrollable Frame)
        self.session_list = ctk.CTkScrollableFrame(
            left_frame,
            fg_color="transparent",
            label_text="Verfügbare Sessions"
        )
        self.session_list.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # ═══════════════════════════════════════════════════════════
        # Rechte Seite: Session-Inhalt
        # ═══════════════════════════════════════════════════════════
        right_frame = ctk.CTkFrame(self, fg_color=surface_color, corner_radius=ds.get_radius('md'))
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)
        
        # Header mit Session-Info
        self.content_header = ctk.CTkLabel(
            right_frame,
            text="Session-Inhalt",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=ds.get_semantic_color('neutral')
        )
        self.content_header.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))
        
        # Text-Widget für Session-Inhalt
        content_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        self.content_text = tk.Text(
            content_frame,
            bg=ds.get_color('neutral', 'darker'),
            fg=ds.get_semantic_color('neutral'),
            font=ds.get_font('sm', 'normal', mono=True),
            insertbackground=ds.get_semantic_color('neutral'),
            selectbackground=ds.get_color('primary'),
            relief="flat",
            borderwidth=0,
            wrap="word",
            state="disabled"
        )
        self.content_text.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(content_frame, command=self.content_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.content_text.configure(yscrollcommand=scrollbar.set)
        
        # Farb-Tags
        self.content_text.tag_configure("timestamp", foreground=ds.get_color('primary', 'light'))
        self.content_text.tag_configure("command", foreground=ds.get_color('success', 'light'))
        self.content_text.tag_configure("output", foreground=ds.get_semantic_color('neutral'))
        self.content_text.tag_configure("error", foreground=ds.get_semantic_color('error'))
        self.content_text.tag_configure("header", foreground=ds.get_color('secondary', 'light'))
        
        # ═══════════════════════════════════════════════════════════
        # Untere Buttons
        # ═══════════════════════════════════════════════════════════
        button_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        button_frame.grid(row=2, column=0, sticky="e", padx=15, pady=(0, 15))
        
        ctk.CTkButton(
            button_frame,
            text="🗑️ Verlauf löschen",
            command=self._clear_history,
            fg_color=ds.get_color('danger', 'base'),
            hover_color=ds.get_color('danger', 'dark'),
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="📋 Exportieren",
            command=self._export_session,
            fg_color="transparent",
            border_width=1,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="✕ Schließen",
            command=self.destroy,
            fg_color=ds.get_color('primary', 'base'),
            hover_color=ds.get_color('primary', 'hover'),
            width=100
        ).pack(side="left", padx=5)
    
    def load_sessions(self, sessions: List[Dict[str, Any]], session_manager) -> None:
        """
        Lädt die Sessions in die Liste.
        
        Args:
            sessions: Liste der Sessions vom Session-Manager
            session_manager: Referenz zum Session-Manager für Aktionen
        """
        self.sessions = sessions
        self.session_manager = session_manager
        
        # Bestehende Einträge entfernen
        for widget in self.session_list.winfo_children():
            widget.destroy()
        
        # Sessions anzeigen (umgekehrt für aktuellste zuerst)
        for session_info in reversed(sessions):
            self._add_session_entry(session_info)
    
    def _add_session_entry(self, session_info: Dict[str, Any]) -> None:
        """Fügt einen Eintrag zur Session-Liste hinzu."""
        ds = DesignSystem
        
        # Zeit formatieren
        start_dt = datetime.fromisoformat(session_info['start_time'])
        start_str = start_dt.strftime('%Y-%m-%d %H:%M')
        
        end_time = session_info.get('end_time')
        if end_time:
            end_str = datetime.fromisoformat(end_time).strftime('%H:%M')
            duration = datetime.fromisoformat(end_time) - start_dt
            duration_str = f"{duration.seconds // 60}min"
            status = f"✅ Beendet ({duration_str})"
            status_color = ds.get_semantic_color('neutral')
        else:
            status = "🔄 Aktiv"
            status_color = ds.get_color('success', 'light')
        
        cmd_count = session_info.get('command_count', 0)
        
        # Frame für jeden Eintrag
        entry_frame = ctk.CTkFrame(
            self.session_list,
            fg_color=ds.get_color('neutral', 'darker'),
            corner_radius=ds.get_radius('sm')
        )
        entry_frame.pack(fill="x", padx=5, pady=3)
        
        # Auswahl-Button
        select_btn = ctk.CTkButton(
            entry_frame,
            text=f"📄 {start_str}",
            command=lambda s=session_info: self._show_session(s),
            fg_color="transparent",
            hover_color=ds.get_color('primary'),
            height=32,
            anchor="w"
        )
        select_btn.pack(fill="x", padx=5, pady=(5, 0))
        
        # Status-Label
        status_label = ctk.CTkLabel(
            entry_frame,
            text=f"{status} | {cmd_count} Befehle",
            font=ctk.CTkFont(size=10),
            text_color=status_color
        )
        status_label.pack(fill="x", padx=5, pady=(0, 5))
    
    def _show_session(self, session_info: Dict[str, Any]) -> None:
        """Zeigt den Inhalt einer ausgewählten Session an."""
        session = session_info.get('session', {})
        
        # Header aktualisieren
        start_dt = datetime.fromisoformat(session['start_time'])
        start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        
        end_time = session.get('end_time')
        if end_time:
            end_str = datetime.fromisoformat(end_time).strftime('%Y-%m-%d %H:%M:%S')
            status = f"Beendet: {end_str}"
        else:
            status = "Noch aktiv"
        
        header_text = f"Session: {session['id']} | Gestartet: {start_str} | Status: {status}"
        self.content_header.configure(text=header_text)
        
        # Inhalt anzeigen
        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")
        
        commands = session.get('commands', [])
        if not commands:
            self.content_text.insert("end", "(Keine Befehle ausgeführt)\n", "output")
        else:
            for cmd in commands:
                self.content_text.insert("end", f"[{cmd['timestamp']}] ", "timestamp")
                self.content_text.insert("end", f"> {cmd['command']}\n", "command")
                
                if cmd['output']:
                    self.content_text.insert("end", f"{cmd['output']}\n", "output")
                
                if cmd['exit_code'] != 0:
                    self.content_text.insert("end", f"[Exit Code: {cmd['exit_code']}]\n", "error")
                
                self.content_text.insert("end", "\n")
        
        self.content_text.configure(state="disabled")
        self.content_text.see("1.0")
    
    def _clear_history(self) -> None:
        """Löscht die gesamte Session-Historie."""
        from tkinter import messagebox
        
        result = messagebox.askyesno(
            "Verlauf löschen",
            "Möchten Sie wirklich die gesamte Session-Historie löschen?\nDie aktuelle Session bleibt erhalten.",
            icon="warning"
        )
        
        if result:
            if hasattr(self, 'session_manager'):
                self.session_manager.clear_history()
            
            # Liste aktualisieren
            if hasattr(self, 'sessions'):
                self.load_sessions(self.session_manager.get_all_sessions(), self.session_manager)
            
            # Inhalt leeren
            self.content_text.configure(state="normal")
            self.content_text.delete("1.0", "end")
            self.content_text.insert("end", "(Verlauf wurde gelöscht)\n", "output")
            self.content_text.configure(state="disabled")
    
    def _export_session(self) -> None:
        """Exportiert die ausgewählte Session in eine Datei."""
        from tkinter import filedialog, messagebox
        
        if not hasattr(self, 'sessions') or not self.sessions:
            messagebox.showinfo("Export", "Keine Session zum Exportieren ausgewählt.")
            return
        
        # Einfachheitshalber: erste Session exportieren (könnte erweitert werden)
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Textdateien", "*.txt"), ("Alle Dateien", "*.*")],
            initialfile=f"terminal_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if file_path and hasattr(self, 'session_manager'):
            # Aktuellste Session exportieren
            latest = self.sessions[-1]
            if self.session_manager.export_session(latest['id'], file_path):
                messagebox.showinfo("Export", f"Session erfolgreich exportiert nach:\n{file_path}")
            else:
                messagebox.showerror("Export", "Fehler beim Exportieren der Session.")


def show_history_popup(session_manager) -> None:
    """
    Zeigt das Historie-Popup an.

    Args:
        session_manager: Die TerminalSessionManager-Instanz
    """
    popup = TerminalHistoryPopup()
    sessions = session_manager.get_all_sessions()
    popup.load_sessions(sessions, session_manager)

    # Aktive Session sofort anzeigen (erste in der Liste, da neueste zuerst)
    if sessions:
        popup._show_session(sessions[0])

