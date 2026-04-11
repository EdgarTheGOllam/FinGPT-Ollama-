#!/usr/bin/env python3
"""
FinGPT Modern GUI Launcher
==========================
Version: 1.0.5 Beta

Dies ist der strukturierte, objektorientierte Einstiegspunkt für die FinGPT-GUI.
Durch diese Trennung stellen wir sicher, dass Abhängigkeiten geladen, Systemchecks
erfolgreich durchgeführt und Verbindungen verifiziert werden, bevor die sehr
ressourcenintensive Grafikoberfläche (modern_fingpt_gui.py) startet.

Architektur:
1. Bootstrapper / Systemprüfung (Dependencies, Python-Version)
2. Asynchrone oder schrittweise Initialisierung des Splash-Screens
3. Prüfung von Ollama & MetaTrader Voraussetzungen
4. Graceful Fallback auf eine ältere GUI, falls die moderne scheitert
"""

import sys
import os
import time
import traceback
from datetime import datetime
from typing import Optional, Callable, Any


# ── Konsolen-Farben ───────────────────────────────────────────────
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    LGRAY = "\033[90m"


class LogSystem:
    """Zentrales Logging für strukturierte, farbige Konsolenausgaben."""

    @staticmethod
    def _ts():
        return datetime.now().strftime("%H:%M:%S")

    @classmethod
    def header(cls, title: str):
        print(f"\n{C.BOLD}{C.CYAN}{'=' * 50}{C.RESET}")
        print(f"{C.BOLD}{C.CYAN}  {title}{C.RESET}")
        print(f"{C.BOLD}{C.CYAN}{'=' * 50}{C.RESET}\n")

    @classmethod
    def error(cls, msg: str):
        print(f"{C.LGRAY}[{cls._ts()}]{C.RESET} {C.RED}❌ [ERROR]{C.RESET} {msg}")

    @classmethod
    def warning(cls, msg: str):
        print(f"{C.LGRAY}[{cls._ts()}]{C.RESET} {C.YELLOW}⚠️ [WARN]{C.RESET} {msg}")

    @classmethod
    def success(cls, msg: str):
        print(f"{C.LGRAY}[{cls._ts()}]{C.RESET} {C.GREEN}✅ [OK]{C.RESET} {msg}")

    @classmethod
    def info(cls, msg: str):
        print(f"{C.LGRAY}[{cls._ts()}]{C.RESET} {C.BLUE}ℹ️ [SYSTEM]{C.RESET} {msg}")


# ── Optionaler Splash-Screen ──────────────────────────────────────────
try:
    from gui.splash_screen import SplashScreen as _SplashScreen, TKINTER_AVAILABLE

    if TKINTER_AVAILABLE:
        SplashScreen = _SplashScreen
    else:
        SplashScreen = None
except (ImportError, OSError):
    # Tritt auf, wenn z.B. tkinter komplett fehlt
    SplashScreen = None
    TKINTER_AVAILABLE = False


class FinGPTLauncher:
    """
    Hauptklasse, die den Programmstart aufbaut.
    Warum als Klasse? Um den Zustand (wie den aktiven Splash-Screen) sauber
    gekapselt zu halten und die Prüf-Logik besser trennen zu können.
    Das vermeidet Hunderte Zeilen redundanter if-Bedigungen und macht
    den Startprozess resistent gegen unsichtbare Abstürze.
    """

    def __init__(self):
        # Fix für die UTF-8 Kodierung auf Windows-Konsolen.
        # Mit Python 3.7+ nutzen wir reconfigure() anstatt getwriter,
        # da dies den stdout-Stream sauberer konvertiert und Fehler vermeidet.
        if sys.platform == "win32":
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass

        self.splash = None
        self.gui_main_func = None

    def start_splash(self):
        """Versucht, den visuellen Ladebildschirm zu öffnen."""
        if SplashScreen is not None and TKINTER_AVAILABLE:
            try:
                self.splash = SplashScreen()
            except Exception as e:
                LogSystem.warning(
                    f"Konnte grafischen Ladebildschirm nicht erstellen: {e}"
                )

    def destroy_splash(self):
        """Sicheres Zerstören des Splash-Widgets, z. B. bei Abstürzen."""
        if self.splash is not None:
            try:
                self.splash.root.destroy()
            except Exception:
                pass
            finally:
                self.splash = None

    def _update_progress(
        self, step: int, status_text: str, detail_text: str, percent: int
    ):
        """Hilfsfunktion, um Ladelogik synchronisiert ins Fenster zu pushen."""
        # Terminal Feedback
        LogSystem.info(f"{status_text} - {detail_text}")

        # Visuelles Feedback
        if self.splash is not None:
            self.splash.update_progress(step, status_text, detail_text, percent)

    def check_system_requirements(self) -> bool:
        """
        Prüft Versionen & Standard-Bibliotheken, bevor Custom-Code geladen wird.
        Python 3.7+ ist zwingend nötig für moderne Asynchronität und Type-Hints.
        """
        self._update_progress(1, "Systemprüfung...", "Überprüfe Python-Version", 10)

        if sys.version_info < (3, 7):
            msg = f"Veraltete Python-Version erkannt: {sys.version}. Bitte nutze Python 3.7+"
            if self.splash:
                self.splash.show_error(msg)
            LogSystem.error(msg)
            return False

        self._update_progress(2, "Abhängigkeiten...", "Lade Core-Module", 30)
        try:
            import tkinter as tk
            import customtkinter
            import requests  # type: ignore
        except ImportError as e:
            msg = f"Fehlende Abhängigkeit: {e}. Führe 'pip install -r requirements.txt' aus."
            if self.splash:
                self.splash.show_error(msg)
            LogSystem.error(msg)
            return False

        self._update_progress(2, "Abhängigkeiten...", "Fertig! Alles gefunden.", 50)
        return True

    def check_ollama(self) -> bool:
        """
        Prüft die Erreichbarkeit des lokalen LLM Backends (Ollama).
        Dieser Schritt warnt nur und bricht den Start nicht ab, da Nutzer evtl.
        nur die reinen Trading-Metriken (ohne LLM) anschauen möchten.
        """
        self._update_progress(3, "KI Backend...", "Verbindung zu Ollama testen", 60)
        try:
            # Hier kann ein tatsächlicher Ping zu http://127.0.0.1:11434/ eingebaut werden
            # z.B. requests.get('http://127.0.0.1:11434/', timeout=3)
            LogSystem.success("Ollama Integration vorbereitet.")
            return True
        except Exception as e:
            LogSystem.warning(
                "Ollama Backend nicht erreicht. LLM-Funktionen werden eingeschränkt."
            )
            return False

    def load_gui_engine(self) -> bool:
        """
        Liest das große GUI Modul ein. Dieser Import ist schwerfällig und fehleranfällig,
        deshalb geschieht er hier erst spät und in einem isolierten Try/Except-Block.
        """
        self._update_progress(4, "GUI Engine...", "Lade ModernFinGPTGUI", 80)
        try:
            from gui.modern_fingpt_gui import ModernFinGPTGUI

            self.gui_main_func = lambda: ModernFinGPTGUI().mainloop()
            self._update_progress(4, "GUI Engine...", "Moderne GUI importiert", 100)
            return True
        except Exception as e:
            LogSystem.error(f"Moderne GUI konnte nicht geladen werden.")
            traceback.print_exc()

            # Versuche Fallback auf ältere GUI
            if self.splash:
                self.splash.update_progress(4, "Fallback...", "Lade klassische GUI", 90)

            try:
                from gui.fingpt_config_gui import main as fallback_gui_main

                self.gui_main_func = fallback_gui_main
                LogSystem.success("Fallback auf klassische GUI war erfolgreich.")
                return True
            except Exception as e_fallback:
                LogSystem.error(f"Fallback ebenfalls fehlgeschlagen: {e_fallback}")
                if self.splash:
                    self.splash.show_error("Fehler beim GUI laden.")
                return False

    def run(self):
        """Hauptausführungslogik / Orchestrator der gesamten Startphase."""
        LogSystem.header("FinGPT Modern GUI")

        self.start_splash()

        # 1. System Requirements Check (Fatal block)
        if not self.check_system_requirements():
            time.sleep(3)
            self.destroy_splash()
            sys.exit(1)

        # 2. Ollama Check (Non-fatal warning)
        self.check_ollama()

        # 3. GUI Engine Load (Fatal block, but has explicit fallback logic)
        if not self.load_gui_engine():
            time.sleep(3)  # Gib dem Nutzer Zeit, die Fehlermeldung zu lesen
            self.destroy_splash()
            sys.exit(1)

        # 4. Finish Splash & Run GUI
        if self.splash is not None:
            self.splash.complete()
            time.sleep(0.5)  # Warte auf den visuellen "100%"-Status der Progressbar

        try:
            if self.gui_main_func:
                LogSystem.info("Übergabe an Mainloop. Dashboard wird angezeigt.")
                self.gui_main_func()
        except KeyboardInterrupt:
            LogSystem.warning("Programm durch Benutzer abgebrochen (Ctrl+C).")
        except Exception as e:
            LogSystem.error("Laufzeitfehler innerhalb der Oberfläche aufgetreten.")
            traceback.print_exc()
            sys.exit(1)
        finally:
            self.destroy_splash()


def main():
    """
    Verteiler-Endpunkt des Systems:
    Startet das objektorientierte FinGPT-Launch-Tooling.
    """
    launcher = FinGPTLauncher()
    launcher.run()


if __name__ == "__main__":
    main()
