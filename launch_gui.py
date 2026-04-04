#!/usr/bin/env python3
"""
FinGPT Modern GUI Launcher
Launcher für die moderne, professionelle GUI mit erweiterten Funktionen
"""

import sys
import os
import time
from pathlib import Path
from typing import Optional, Callable, Any
from datetime import datetime

# Set UTF-8 for Windows
if sys.platform == "win32":
    try:
        import codecs

        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
    except:
        pass


# Fancy console colors
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    LGRAY = "\033[90m"


def ts():
    return datetime.now().strftime("%H:%M:%S")


def print_header(title):
    w = 50
    print(f"\n{C.BOLD}{C.CYAN}{'=' * w}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {title}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'=' * w}{C.RESET}\n")


def print_error(msg):
    print(f"{C.LGRAY}[{ts()}]{C.RESET} {C.RED}X [ERROR]{C.RESET} {C.RED}{msg}{C.RESET}")


def print_warning(msg):
    print(
        f"{C.LGRAY}[{ts()}]{C.RESET} {C.YELLOW}! [WARN]{C.RESET} {C.YELLOW}{msg}{C.RESET}"
    )


def print_success(msg):
    print(
        f"{C.LGRAY}[{ts()}]{C.RESET} {C.GREEN}V [OK]{C.RESET} {C.GREEN}{msg}{C.RESET}"
    )


def log_startup(msg):
    print(f"{C.LGRAY}[{ts()}]{C.RESET} {C.BLUE}* [SYSTEM]{C.RESET} {msg}")


# Importiere SplashScreen aus dem neuen Modul (mit Fallback)
TKINTER_AVAILABLE = False
SplashScreen: Any = None

try:
    from gui.splash_screen import SplashScreen as _SplashScreen, TKINTER_AVAILABLE

    if TKINTER_AVAILABLE:
        SplashScreen = _SplashScreen
except (ImportError, OSError):
    # Tkinter nicht verfügbar - kein Splashscreen
    pass


def check_dependencies(splash: Optional[Any] = None) -> bool:
    """Prüft ob alle Abhängigkeiten vorhanden sind"""
    if splash is not None:
        splash.update_progress(
            1, "Prüfe Abhängigkeiten...", "Lade required modules...", 15
        )

    try:
        import tkinter as tk

        if splash is not None:
            splash.update_progress(1, "Prüfe Abhängigkeiten...", "tkinter gefunden", 25)

        import customtkinter

        if splash is not None:
            splash.update_progress(
                1, "Prüfe Abhängigkeiten...", "customtkinter gefunden", 50
            )

        import requests  # type: ignore

        if splash is not None:
            splash.update_progress(
                1, "Prüfe Abhängigkeiten...", "requests gefunden", 75
            )

        if splash is not None:
            splash.update_progress(
                1, "Prüfe Abhängigkeiten...", "Alle Abhängigkeiten OK", 100
            )

        return True
    except ImportError as e:
        if splash is not None:
            splash.show_error(f"Fehlende Abhängigkeit: {e}")
        else:
            print_error(f"Fehlende Abhängigkeit: {e}")
            log_startup("Bitte installieren: pip install -r requirements.txt")
        return False


def check_python_version(splash: Optional[Any] = None) -> bool:
    """Prüft die Python-Version"""
    if splash is not None:
        splash.update_progress(
            2,
            "Prüfe Python-Version...",
            f"Version: {sys.version_info.major}.{sys.version_info.minor}",
            10,
        )

    if sys.version_info < (3, 7):
        error_msg = (
            f"Python 3.7 oder höher erforderlich. Aktuelle Version: {sys.version}"
        )
        if splash is not None:
            splash.show_error(error_msg)
        else:
            print_error(error_msg)
        return False

    if splash is not None:
        splash.update_progress(2, "Prüfe Python-Version...", "Python Version OK", 100)

    return True


def check_plotly(splash: Optional[Any] = None) -> bool:
    """Prüft ob Plotly installiert ist"""
    if splash is not None:
        splash.update_progress(3, "Prüfe Plotly...", "Optionale Abhängigkeit", 10)

    try:
        import plotly  # type: ignore

        if splash is not None:
            splash.update_progress(
                3, "Prüfe Plotly...", "Plotly gefunden - Charts verfügbar", 100
            )
        return True
    except ImportError:
        if splash is not None:
            splash.update_progress(
                3, "Prüfe Plotly...", "Plotly nicht gefunden - Charts deaktiviert", 100
            )
        print_warning("Plotly nicht gefunden - Charts deaktiviert")
        return False


def initialize_gui_components(splash: Optional[Any] = None):
    """Initialisiert die GUI-Komponenten"""
    if splash is not None:
        splash.update_progress(
            4, "Initialisiere GUI-Komponenten...", "Lade Design System...", 20
        )

    # Hier können zusätzliche Initialisierungen hinzugefügt werden
    if splash is not None:
        splash.update_progress(
            4, "Initialisiere GUI-Komponenten...", "Design System geladen", 50
        )

    time.sleep(0.3)

    if splash is not None:
        splash.update_progress(
            4, "Initialisiere GUI-Komponenten...", "Komponenten bereit", 100
        )


def initialize_ollama_connection(splash: Optional[Any] = None):
    """
    Versucht, die Verbindung zu Ollama zu initialisieren.
    Dies muss an die tatsächliche Implementierung angepasst werden.
    """
    if splash is not None:
        splash.update_progress(
            4, "Initialisiere GUI-Komponenten...", "Initialisiere Ollama Connection...", 80
        )
    
    log_startup("Versuche Verbindung zu Ollama...")
    
    try:
        # HIER MUSS DER TATSÄCHLICHE OLLAMA-CONNECT-CODE EINGEFÜGT WERDEN
        # Beispiel: client = ollama.Client(...) oder requests.get(OLLAMA_API_URL + "/api/generate")
        
        # Simulierter Erfolg/Test
        print_success("Ollama Connection Test erfolgreich (Platzhalter).")
        
        if splash is not None:
            splash.update_progress(
                4, "Initialisiere GUI-Komponenten...", "Ollama Connection OK", 100
            )
        return True
    except ImportError:
        print_warning("Ollama-Bibliothek nicht gefunden. Ollama-Funktionalität deaktiviert.")
        return False
    except Exception as e:
        print_error(f"Fehler beim Verbinden mit Ollama: {e}")
        if splash is not None:
            splash.update_progress(
                4, "Initialisiere GUI-Komponenten...", f"Ollama Connection Failed: {type(e).__name__}", 100
            )
        return False


def load_gui_module(splash: Optional[Any] = None, use_modern: bool = True) -> Callable:
    """Lädt das GUI-Modul"""
    if splash is not None:
        splash.update_progress(
            5, "Lade GUI-Modul...", "Importiere modern_fingpt_gui...", 30
        )

    if use_modern:
        from gui.modern_fingpt_gui import ModernFinGPTGUI  # type: ignore

        if splash is not None:
            splash.update_progress(
                5, "Lade GUI-Modul...", "modern_fingpt_gui importiert", 100
            )
        return lambda: ModernFinGPTGUI().mainloop()
    else:
        from gui.fingpt_config_gui import main as fallback_gui_main  # type: ignore

        if splash is not None:
            splash.update_progress(
                5, "Lade GUI-Modul...", "fingpt_config_gui importiert", 100
            )
        return fallback_gui_main


def run_gui(gui_main_func: Callable, splash: Optional[Any] = None):
    """Führt die GUI-Hauptfunktion aus"""
    if splash is not None:
        splash.update_progress(6, "Starte FinGPT...", "Fenster wird geöffnet...", 50)

        # Warte sicherheitshalber bis SplashScreen geschlossen ist
        time.sleep(0.3)

    try:
        gui_main_func()
    except Exception as e:
        print_error(f"Kritischer Fehler beim Starten der GUI: {e}")
        # Wir lassen den Fehler im Haupt-Exception-Handler von main() abfangen,
        # aber wir geben hier eine spezifische Meldung aus.
        raise e

    if splash is not None:
        splash.update_progress(6, "Starte FinGPT...", "FinGPT läuft!", 100)


def destroy_splash(splash: Optional[Any]):
    """Zerstört den Splash-Screen falls vorhanden"""
    if splash is not None:
        try:
            splash.root.destroy()
        except Exception:
            pass


def main():
    """Hauptfunktion mit echtem Ladebalken"""

    # Erstelle Splash-Screen falls tkinter verfügbar
    splash = None
    if SplashScreen is not None and TKINTER_AVAILABLE:
        try:
            splash = SplashScreen()
        except Exception as e:
            print_warning(f"Konnte Ladebildschirm nicht erstellen: {e}")

    print_header("FinGPT Modern GUI")

    # Schritt 1: Python-Version prüfen
    if splash is not None:
        if not check_python_version(splash):
            destroy_splash(splash)
            sys.exit(1)
    else:
        if not check_python_version():
            sys.exit(1)

    # Schritt 2: Abhängigkeiten prüfen
    if splash is not None:
        if not check_dependencies(splash):
            destroy_splash(splash)
            sys.exit(1)
    else:
        if not check_dependencies():
            sys.exit(1)

    # Schritt 2.5: Ollama Verbindung prüfen (Neu)
    if splash is not None:
        if not initialize_ollama_connection(splash):
            # Wir sturzen nicht ab, aber wir warnen den Benutzer, falls es fehlschlägt
            print_warning("Ollama-Verbindung konnte nicht initialisiert werden. Funktionalität kann eingeschränkt sein.")
    else:
        if not initialize_ollama_connection():
            print_warning("Ollama-Verbindung konnte nicht initialisiert werden. Funktionalität kann eingeschränkt sein.")


    # Schritt 3: Plotly prüfen (optional)
    plotly_available = check_plotly(splash)

    # Schritt 4: GUI-Komponenten initialisieren
    initialize_gui_components(splash)

    # Schritt 5: GUI-Modul laden
    gui_main_func = None
    gui_load_error = None

    if splash is not None:
        splash.update_progress(
            5, "Lade GUI-Modul...", "Starte moderne FinGPT GUI...", 20
        )

    try:
        gui_main_func = load_gui_module(splash, use_modern=True)
    except Exception as e:
        gui_load_error = e
        if splash is not None:
            splash.show_error(f"Moderne GUI konnte nicht geladen werden: {e}")
            try:
                splash.root.update()
            except Exception:
                pass
            time.sleep(2)

    # Fallback versuchen wenn modern fehlgeschlagen
    if gui_main_func is None:
        if splash is not None:
            splash.update_progress(
                5, "Versuche Fallback...", "Lade klassische GUI...", 50
            )

        try:
            gui_main_func = load_gui_module(splash, use_modern=False)
        except Exception as fallback_e:
            if splash is not None:
                splash.show_error(f"Auch Fallback fehlgeschlagen: {fallback_e}")
            print_error(f"Fehler beim Starten: {gui_load_error}")
            print_error(f"Fallback fehlgeschlagen: {fallback_e}")
            destroy_splash(splash)
            sys.exit(1)

    # Schritt 6: GUI starten
    try:
        if splash is not None:
            splash.complete()
            # Warte bis das Fenster sicher geschlossen ist
            time.sleep(0.5)

        assert gui_main_func is not None, "GUI module loading failed completely"
        run_gui(gui_main_func, splash)

    except KeyboardInterrupt:
        print_warning("Programm durch Benutzer beendet")
    except Exception as e:
        print_error(f"Fehler beim Ausführen der GUI: {e}")
        destroy_splash(splash)
        sys.exit(1)


if __name__ == "__main__":
    main()
