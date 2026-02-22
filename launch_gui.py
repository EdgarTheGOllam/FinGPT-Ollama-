#!/usr/bin/env python3
"""
FinGPT Modern GUI Launcher
Launcher für die moderne, professionelle GUI mit erweiterten Funktionen
"""

import sys
import os
from pathlib import Path

def check_dependencies():
    """Prüft ob alle Abhängigkeiten vorhanden sind"""
    try:
        import tkinter as tk
        import customtkinter
        import requests
        import json
        return True
    except ImportError as e:
        print(f"Fehlende Abhängigkeit: {e}")
        print("Bitte installieren Sie fehlende Pakete (z.B. pip install customtkinter):")
        print("pip install -r requirements.txt")
        return False

def check_python_version():
    """Prüft die Python-Version"""
    if sys.version_info < (3, 7):
        print("Python 3.7 oder höher erforderlich")
        print(f"Aktuelle Version: {sys.version}")
        return False
    return True

def check_plotly():
    """Prüft ob Plotly installiert ist"""
    try:
        import plotly
        return True
    except ImportError:
        print("Plotly nicht gefunden - optionale Charts-Funktionalität nicht verfügbar")
        print("Installation: pip install plotly")
        return False

def main():
    """Hauptfunktion"""
    print("FinGPT Modern GUI Launcher")
    print("=" * 40)
    
    # Python-Version prüfen
    if not check_python_version():
        sys.exit(1)
    
    # Abhängigkeiten prüfen
    if not check_dependencies():
        sys.exit(1)
    
    # Optionale Abhängigkeiten prüfen
    plotly_available = check_plotly()
    
    # GUI starten
    try:
        print("Starte moderne FinGPT GUI...")
        from gui.modern_fingpt_gui import main as gui_main
        gui_main()
    except KeyboardInterrupt:
        print("\nProgramm durch Benutzer beendet")
    except Exception as e:
        print(f"Fehler beim Starten: {e}")
        print("Versuche Fallback zur klassischen GUI...")
        try:
            from gui.fingpt_config_gui import main as fallback_gui_main
            print("Starte klassische Konfigurations-GUI...")
            fallback_gui_main()
        except Exception as fallback_e:
            print(f"Auch Fallback fehlgeschlagen: {fallback_e}")
            sys.exit(1)

if __name__ == "__main__":
    main()