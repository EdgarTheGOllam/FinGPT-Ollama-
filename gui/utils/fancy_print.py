"""
Fancy Console Output - Übersichtliche formatierte Konsolenausgabe für FinGPT
"""

import sys
import time
from datetime import datetime
from typing import Optional


# ANSI Farben
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"

    # Farben
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Helle Varianten
    LGRAY = "\033[90m"
    LRED = "\033[91m"
    LGREEN = "\033[92m"
    LYELLOW = "\033[93m"
    LBLUE = "\033[94m"
    LMAGENTA = "\033[95m"
    LCYAN = "\033[96m"

    # Hintergrund
    BG_DARK = "\033[48m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_RED = "\033[41m"
    BG_BLUE = "\033[44m"


def get_timestamp() -> str:
    """Gibt formatierten Zeitstempel zurück"""
    return datetime.now().strftime("%H:%M:%S")


def cprint(
    text: str,
    level: str = "INFO",
    color: Optional[str] = None,
    icon: Optional[str] = None,
    bold: bool = False,
):
    """
    Fancy print Funktion für FinGPT

    Levels: INFO, SUCCESS, WARN, ERROR, SYSTEM, DEBUG
    """
    # LevelIcons und Farben
    level_config = {
        "INFO": {"icon": "ℹ️", "color": Colors.CYAN},
        "SUCCESS": {"icon": "✅", "color": Colors.GREEN},
        "WARN": {"icon": "⚠️", "color": Colors.YELLOW},
        "ERROR": {"icon": "❌", "color": Colors.RED},
        "SYSTEM": {"icon": "⚙️", "color": Colors.BLUE},
        "DEBUG": {"icon": "🔍", "color": Colors.LGRAY},
        "TRADE": {"icon": "💱", "color": Colors.MAGENTA},
        "RL": {"icon": "🧠", "color": Colors.LMAGENTA},
        "MCP": {"icon": "🔌", "color": Colors.LCYAN},
    }

    config = level_config.get(level, {"icon": "•", "color": Colors.WHITE})

    # Farbe und Icon bestimmen
    use_color = color or config["color"]
    use_icon = icon or config["icon"]

    # Bold für manche Levels
    prefix = Colors.BOLD if bold else ""

    # Formatierte Ausgabe
    timestamp = f"{Colors.LGRAY}[{get_timestamp()}]{Colors.RESET}"
    level_str = f"{use_color}{use_icon} [{level}]{Colors.RESET}"
    message = f"{prefix}{use_color}{text}{Colors.RESET}"

    print(f"{timestamp} {level_str} {message}")


def print_header(title: str):
    """Druckt einen fancy Header"""
    width = 50
    border = "═" * width
    print(f"\n{Colors.BOLD}{Colors.CYAN}{border}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{border}{Colors.RESET}\n")


def print_section(title: str):
    """Druckt einen Section Header"""
    print(f"\n{Colors.BOLD}─── {title} ───{Colors.RESET}\n")


def print_success(msg: str):
    cprint(msg, "SUCCESS")


def print_error(msg: str):
    cprint(msg, "ERROR", bold=True)


def print_warning(msg: str):
    cprint(msg, "WARN")


def print_info(msg: str):
    cprint(msg, "INFO")


def print_system(msg: str):
    cprint(msg, "SYSTEM")


def print_trade(msg: str):
    cprint(msg, "TRADE")


# Intercepted print für bessere Formatierung
_original_print = print


def install_fancy_print():
    """Ersetzt die built-in print Funktion"""
    import builtins

    builtins.print = fancy_print

    # Auch sys.stdout write intercepten
    class FancyStdout:
        def __init__(self, original):
            self.original = original

        def write(self, text):
            if text.strip():
                if "ERROR" in text.upper() or "FEHLER" in text.upper():
                    cprint(text.strip(), "ERROR")
                elif "WARNING" in text.upper() or "WARNUNG" in text.upper():
                    cprint(text.strip(), "WARN")
                elif "SUCCESS" in text.upper() or "ERFOLG" in text.upper():
                    cprint(text.strip(), "SUCCESS")
                else:
                    self.original.write(text)
            else:
                self.original.write(text)

        def flush(self):
            self.original.flush()

    sys.stdout = FancyStdout(sys.stdout)
    sys.stderr = FancyStdout(sys.stderr)


# Convenience Funktionen für FinGPT
def log_startup(msg: str):
    """Für Startup-Meldungen"""
    cprint(f">> {msg}", "SYSTEM")


def log_trade(action: str, symbol: str, price: float = None):
    """Trade Meldung"""
    price_str = f" @ {price:.5f}" if price else ""
    cprint(f"{action} {symbol}{price_str}", "TRADE")


def log_mcp(msg: str):
    """MCP spezifisch"""
    cprint(msg, "MCP")


def log_rl(msg: str):
    """Reinforcement Learning"""
    cprint(msg, "RL")
