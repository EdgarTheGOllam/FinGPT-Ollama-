#!/usr/bin/env python3
"""
Terminal Session Manager
Verwaltet Terminal-Sessions mit Zeitstempeln und Persistenz
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path


class TerminalSessionManager:
    """
    Verwaltet Terminal-Sessions: erstellt neue Sessions, speichert Befehle
    und Ausgaben mit Zeitstempeln, und lädt vergangene Sessions.
    """
    
    def __init__(self, storage_path: Optional[str] = None, max_sessions: int = 50):
        """
        Initialisiert den Session Manager.
        
        Args:
            storage_path: Pfad zur JSON-Datei für Persistenz. 
                         Falls None, wird storage/terminal_sessions.json verwendet.
            max_sessions: Maximale Anzahl zu speichernder Sessions.
        """
        self.max_sessions = max_sessions
        
        # Standard-Speicherpfad bestimmen
        if storage_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            storage_path = os.path.join(project_root, "storage", "terminal_sessions.json")
        
        self.storage_path = storage_path
        
        # Sessions-Datenstruktur
        self.sessions: List[Dict[str, Any]] = []
        self.current_session: Optional[Dict[str, Any]] = None
        
        # Verzeichnis erstellen falls nötig
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        # Bestehende Sessions laden
        self._load_sessions()
        
        # Neue Session bei jedem Start erstellen (ohne vorherigen Kontext)
        self.create_new_session()
    
    def _load_sessions(self):
        """Lädt gespeicherte Sessions aus der JSON-Datei."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions = data.get('sessions', [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"Fehler beim Laden der Sessions: {e}")
            self.sessions = []
    
    def _save_sessions(self):
        """Speichert alle Sessions in die JSON-Datei."""
        try:
            all_sessions = list(self.sessions)
            if self.current_session is not None and self.current_session not in all_sessions:
                all_sessions.append(self.current_session)
            
            start_idx = max(0, len(all_sessions) - self.max_sessions)
            sessions_to_save = [all_sessions[i] for i in range(start_idx, len(all_sessions))]
            
            data = {
                'sessions': sessions_to_save,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Fehler beim Speichern der Sessions: {e}")
    
    def create_new_session(self) -> Dict[str, Any]:
        """
        Erstellt eine neue Terminal-Session ohne vorherigen Kontext.
        
        Returns:
            Die neue Session-Dict
        """
        # Aktuelle Session beenden falls vorhanden
        current = self.current_session
        if current is not None:
            current['end_time'] = datetime.now().isoformat()
            self.sessions.append(current)
            self._save_sessions()
        
        # Neue Session erstellen
        session_id = str(uuid.uuid4()).split('-')[0]
        new_session: Dict[str, Any] = {
            'id': session_id,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'commands': []
        }
        self.current_session = new_session
        
        return new_session
    
    def add_command(self, command: str, output: str = "", exit_code: int = 0) -> None:
        """
        Fügt einen Befehl zur aktuellen Session hinzu.
        
        Args:
            command: Der eingegebene Befehl
            output: Die Ausgabe des Befehls
            exit_code: Der Exit-Code des Befehls
        """
        if self.current_session is None:
            self.create_new_session()
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        command_entry = {
            'timestamp': timestamp,
            'command': command,
            'output': output,
            'exit_code': exit_code
        }
        
        current = self.current_session
        if current is not None:
            current['commands'].append(command_entry)
            self._save_sessions()
    
    def close_current_session(self) -> None:
        """Beendet die aktuelle Session und speichert sie dauerhaft."""
        current = self.current_session
        if current is not None:
            current['end_time'] = datetime.now().isoformat()
            if current not in self.sessions:
                self.sessions.append(current)
            self._save_sessions()
            self.current_session = None
    
    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Gibt die aktuelle Session zurück."""
        return self.current_session
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Gibt alle Sessions zurück (aktuellste zuerst).
        
        Returns:
            Liste aller Sessions mit Metadaten
        """
        result = []
        
        # Aktuelle Session hinzufügen (falls vorhanden)
        current = self.current_session
        if current is not None:
            result.append({
                'id': current['id'],
                'start_time': current['start_time'],
                'end_time': current.get('end_time'),
                'command_count': len(current.get('commands', [])),
                'is_active': True,
                'session': current
            })
        
        # Abgeschlossene Sessions hinzufügen (umgekehrt für chronologische Reihenfolge)
        for session in reversed(self.sessions):
            result.append({
                'id': session['id'],
                'start_time': session['start_time'],
                'end_time': session.get('end_time'),
                'command_count': len(session.get('commands', [])),
                'is_active': False,
                'session': session
            })
        
        return result
    
    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Gibt eine Session anhand ihrer ID zurück.
        
        Args:
            session_id: Die ID der gesuchten Session
            
        Returns:
            Die Session oder None falls nicht gefunden
        """
        # Aktuelle Session prüfen
        current = self.current_session
        if current is not None and current['id'] == session_id:
            return current
        
        # Gespeicherte Sessions durchsuchen
        for session in self.sessions:
            if session['id'] == session_id:
                return session
        
        return None
    
    def format_session_for_display(self, session: Dict[str, Any]) -> str:
        """
        Formatiert eine Session für die Anzeige im Popup.
        
        Args:
            session: Die Session-Dict
            
        Returns:
            Formatierter String mit allen Befehlen und Ausgaben
        """
        lines = []
        
        # Header
        start_time = datetime.fromisoformat(session['start_time']).strftime('%Y-%m-%d %H:%M:%S')
        end_time = session.get('end_time')
        if end_time:
            end_time = datetime.fromisoformat(end_time).strftime('%Y-%m-%d %H:%M:%S')
            duration = datetime.fromisoformat(end_time) - datetime.fromisoformat(session['start_time'])
            lines.append(f"Session: {session['id']} | Dauer: {duration}")
        else:
            lines.append(f"Session: {session['id']} | Gestartet: {start_time} | (Aktiv)")
        
        lines.append("=" * 60)
        
        # Befehle
        commands = session.get('commands', [])
        if not commands:
            lines.append("(Keine Befehle ausgeführt)")
        else:
            for cmd in commands:
                lines.append(f"\n[{cmd['timestamp']}] > {cmd['command']}")
                if cmd['output']:
                    lines.append(cmd['output'])
                if cmd['exit_code'] != 0:
                    lines.append(f"[Exit Code: {cmd['exit_code']}]")
        
        return "\n".join(lines)
    
    def clear_history(self) -> None:
        """Löscht alle gespeicherten Sessions (nicht die aktuelle)."""
        self.sessions = []
        self._save_sessions()
    
    def export_session(self, session_id: str, file_path: str) -> bool:
        """
        Exportiert eine Session in eine Textdatei.
        
        Args:
            session_id: Die ID der zu exportierenden Session
            file_path: Der Pfad für die Exportdatei
            
        Returns:
            True falls erfolgreich
        """
        session = self.get_session_by_id(session_id)
        if session is None:
            return False
        
        try:
            content = self.format_session_for_display(session)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except IOError:
            return False


# Singleton-Instanz für einfachen Zugriff
_session_manager_instance: Optional[TerminalSessionManager] = None


def get_session_manager() -> TerminalSessionManager:
    """Gibt die Singleton-Instanz des Session-Managers zurück."""
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = TerminalSessionManager()
    return _session_manager_instance
