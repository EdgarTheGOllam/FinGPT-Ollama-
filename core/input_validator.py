#!/usr/bin/env python3
"""
FinGPT Input Validator Module
Sichere Eingabevalidierung für alle Benutzereingaben
"""

import re
from typing import Optional, Any
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Ergebnis der Validierung"""
    is_valid: bool
    value: Any = None
    error_message: str = ""
    sanitized: bool = False

class InputValidator:
    """Sichere Validierungsklasse für Benutzereingaben"""
    
    # Regex-Patterns für Validierung
    PATTERNS = {
        'symbol': re.compile(r'^[A-Z]{6}$'),
        'action': re.compile(r'^(BUY|SELL)$', re.IGNORECASE),
        'lot_size': re.compile(r'^0?\.\d{1,2}$|^1\.0$|^0\.[01]$'),
        'interval': re.compile(r'^[1-9]\d{0,3}$'),
        'percentage': re.compile(r'^100$|^([1-9]\d?\.\d+)$|^0\.\d+$'),
        'choice': re.compile(r'^[1-9]\d*$'),
        'yes_no': re.compile(r'^(ja|nein|yes|no)$', re.IGNORECASE),
        'confirmation': re.compile(r'^[A-Z_]+$'),
        'pairs_list': re.compile(r'^[A-Z]{6}(,[A-Z]{6})*$')
    }
    
    LIMITS = {
        'lot_size': {'min': 0.01, 'max': 10.0},
        'interval': {'min': 10, 'max': 3600},
        'percentage': {'min': 0.0, 'max': 100.0},
    }
    MAX_PAIRS = 10
    MAX_STRING_LENGTH = 100
    
    @classmethod
    def validate_symbol(cls, input_str: str) -> ValidationResult:
        """Validiert ein Trading-Symbol (z.B. EURUSD)"""
        try:
            if not input_str or not isinstance(input_str, str):
                return ValidationResult(False, None, "Symbol darf nicht leer sein")
            
            symbol = input_str.strip()
            
            # Pattern-Validierung (nur Großbuchstaben)
            if not cls.PATTERNS['symbol'].match(symbol):
                return ValidationResult(False, None, 
                    f"Symbol '{symbol}' ungültig. Erwartet: 6 Großbuchstaben (z.B. EURUSD)")
            
            return ValidationResult(True, symbol, sanitized=True)
            
        except Exception as e:
            return ValidationResult(False, None, f"Validierungsfehler: {str(e)}")
    
    @classmethod
    def validate_action(cls, input_str: str) -> ValidationResult:
        """Validiert Trading-Aktion (BUY/SELL)"""
        try:
            if not input_str or not isinstance(input_str, str):
                return ValidationResult(False, None, "Aktion darf nicht leer sein")
            
            action = input_str.strip().upper()
            
            if not cls.PATTERNS['action'].match(action):
                return ValidationResult(False, None, 
                    "Aktion ungültig. Erlaubt: BUY oder SELL")
            
            return ValidationResult(True, action, sanitized=True)
            
        except Exception as e:
            return ValidationResult(False, None, f"Validierungsfehler: {str(e)}")
    
    @classmethod
    def validate_lot_size(cls, input_str: str) -> ValidationResult:
        """Validiert Lot Size"""
        try:
            if not input_str:
                return ValidationResult(False, None, "Lot Size darf nicht leer sein")
            
            lot_str = input_str.strip()
            
            # Pattern-Validierung
            if not cls.PATTERNS['lot_size'].match(lot_str):
                return ValidationResult(False, None, 
                    f"Lot Size '{lot_str}' ungültig. Format: 0.01 - 10.0")
            
            lot_size = float(lot_str)
            
            # Limits prüfen
            limits = cls.LIMITS['lot_size']
            if lot_size < limits['min'] or lot_size > limits['max']:
                return ValidationResult(False, None, 
                    f"Lot Size muss zwischen {limits['min']} und {limits['max']} liegen")
            
            return ValidationResult(True, lot_size, sanitized=True)
            
        except ValueError:
            return ValidationResult(False, None, "Lot Size muss eine Zahl sein")
        except Exception as e:
            return ValidationResult(False, None, f"Validierungsfehler: {str(e)}")
    
    @classmethod
    def validate_interval(cls, input_str: str) -> ValidationResult:
        """Validiert Zeitintervall in Sekunden"""
        try:
            if not input_str:
                return ValidationResult(False, None, "Intervall darf nicht leer sein")
            
            interval_str = input_str.strip()
            
            # Pattern-Validierung
            if not cls.PATTERNS['interval'].match(interval_str):
                return ValidationResult(False, None, 
                    "Intervall ungültig. Erwartet: ganze Zahl (10-3600)")
            
            interval = int(interval_str)
            
            # Limits prüfen
            limits = cls.LIMITS['interval']
            if interval < limits['min'] or interval > limits['max']:
                return ValidationResult(False, None, 
                    f"Intervall muss zwischen {limits['min']} und {limits['max']} Sekunden liegen")
            
            return ValidationResult(True, interval, sanitized=True)
            
        except ValueError:
            return ValidationResult(False, None, "Intervall muss eine ganze Zahl sein")
        except Exception as e:
            return ValidationResult(False, None, f"Validierungsfehler: {str(e)}")
    
    @classmethod
    def validate_percentage(cls, input_str: str) -> ValidationResult:
        """Validiert Prozentwert"""
        try:
            if not input_str:
                return ValidationResult(False, None, "Prozentwert darf nicht leer sein")
            
            pct_str = input_str.strip()
            
            # Pattern-Validierung
            if not cls.PATTERNS['percentage'].match(pct_str):
                return ValidationResult(False, None, 
                    "Prozentwert ungültig. Erwartet: 0.0 - 100.0")
            
            percentage = float(pct_str)
            
            # Limits prüfen
            limits = cls.LIMITS['percentage']
            if percentage < limits['min'] or percentage > limits['max']:
                return ValidationResult(False, None, 
                    f"Prozentwert muss zwischen {limits['min']} und {limits['max']} liegen")
            
            return ValidationResult(True, percentage, sanitized=True)
            
        except ValueError:
            return ValidationResult(False, None, "Prozentwert muss eine Zahl sein")
        except Exception as e:
            return ValidationResult(False, None, f"Validierungsfehler: {str(e)}")
    
    @classmethod
    def validate_choice(cls, input_str: str, max_choice: int) -> ValidationResult:
        """Validiert Menü-Auswahl"""
        try:
            if not input_str:
                return ValidationResult(False, None, "Auswahl darf nicht leer sein")
            
            choice_str = input_str.strip()
            
            # Pattern-Validierung
            if not cls.PATTERNS['choice'].match(choice_str):
                return ValidationResult(False, None, "Auswahl ungültig. Erwartet: ganze Zahl")
            
            choice = int(choice_str)
            
            if choice < 1 or choice > max_choice:
                return ValidationResult(False, None, 
                    f"Auswahl muss zwischen 1 und {max_choice} liegen")
            
            return ValidationResult(True, choice, sanitized=True)
            
        except ValueError:
            return ValidationResult(False, None, "Auswahl muss eine ganze Zahl sein")
        except Exception as e:
            return ValidationResult(False, None, f"Validierungsfehler: {str(e)}")
    
    @classmethod
    def validate_pairs_list(cls, input_str: str) -> ValidationResult:
        """Validiert Liste von Währungspaaren"""
        try:
            if not input_str:
                return ValidationResult(False, None, "Paar-Liste darf nicht leer sein")
            
            pairs_str = input_str.strip().upper()
            
            # Pattern-Validierung
            if not cls.PATTERNS['pairs_list'].match(pairs_str):
                return ValidationResult(False, None, 
                    "Paar-Liste ungültig. Format: EURUSD,GBPUSD,USDJPY")
            
            pairs = [pair.strip() for pair in pairs_str.split(',')]
            
            # Maximale Anzahl prüfen (>= max_pairs wird als ungültig betrachtet)
            if len(pairs) >= cls.MAX_PAIRS:
                return ValidationResult(False, None, 
                    f"Maximal {cls.MAX_PAIRS - 1} Paare erlaubt")
            
            # Duplikate entfernen
            unique_pairs = list(dict.fromkeys(pairs))
            
            return ValidationResult(True, unique_pairs, sanitized=True)
            
        except Exception as e:
            return ValidationResult(False, None, f"Validierungsfehler: {str(e)}")
    
    @classmethod
    def validate_confirmation(cls, input_str: str, expected: str) -> ValidationResult:
        """Validiert Bestätigungseingabe"""
        try:
            if not input_str:
                return ValidationResult(False, None, "Bestätigung darf nicht leer sein")
            
            confirmation = input_str.strip()
            
            if confirmation != expected:
                return ValidationResult(False, None, 
                    f"Bestätigung ungültig. Erwartet: '{expected}'")
            
            return ValidationResult(True, confirmation, sanitized=True)
            
        except Exception as e:
            return ValidationResult(False, None, f"Validierungsfehler: {str(e)}")
    
    @classmethod
    def sanitize_string(cls, input_str: str, max_length: Optional[int] = None) -> ValidationResult:
        """Allgemeine String-Sanitization"""
        try:
            if not input_str or not isinstance(input_str, str):
                return ValidationResult(False, None, "Eingabe muss ein String sein")
            
            # Längenbegrenzung
            max_len = max_length or cls.MAX_STRING_LENGTH
            if len(input_str) > max_len:
                return ValidationResult(False, None, 
                    f"Eingabe zu lang. Maximal {max_len} Zeichen erlaubt")
            
            # Gefährliche Zeichen entfernen
            sanitized = re.sub(r'[<>"\'\x00-\x1f\x7f-\x9f]', '', input_str.strip())
            
            return ValidationResult(True, sanitized, sanitized=True)
            
        except Exception as e:
            return ValidationResult(False, None, f"Sanitization-Fehler: {str(e)}")

class SafeInput:
    """Sichere Eingabe-Wrapper mit Validierung"""
    
    @staticmethod
    def get_symbol(prompt: str = "Symbol: ") -> Optional[str]:
        """Sichere Symbol-Eingabe"""
        while True:
            try:
                user_input = input(prompt)
                result = InputValidator.validate_symbol(user_input)
                
                if result.is_valid:
                    return result.value
                else:
                    print(f"❌ {result.error_message}")
                    
            except KeyboardInterrupt:
                print("\n👋 Eingabe abgebrochen")
                return None
            except EOFError:
                print("\n👋 Eingabe beendet")
                return None
    
    @staticmethod
    def get_action(prompt: str = "Aktion (BUY/SELL): ") -> Optional[str]:
        """Sichere Aktion-Eingabe"""
        while True:
            try:
                user_input = input(prompt)
                result = InputValidator.validate_action(user_input)
                
                if result.is_valid:
                    return result.value
                else:
                    print(f"❌ {result.error_message}")
                    
            except KeyboardInterrupt:
                print("\n👋 Eingabe abgebrochen")
                return None
            except EOFError:
                print("\n👋 Eingabe beendet")
                return None
    
    @staticmethod
    def get_lot_size(prompt: str = "Lot Size: ") -> Optional[float]:
        """Sichere Lot Size-Eingabe"""
        while True:
            try:
                user_input = input(prompt)
                result = InputValidator.validate_lot_size(user_input)
                
                if result.is_valid:
                    return result.value
                else:
                    print(f"❌ {result.error_message}")
                    
            except KeyboardInterrupt:
                print("\n👋 Eingabe abgebrochen")
                return None
            except EOFError:
                print("\n👋 Eingabe beendet")
                return None
    
    @staticmethod
    def get_interval(prompt: str = "Intervall (Sekunden): ", default: Optional[int] = None) -> Optional[int]:
        """Sichere Intervall-Eingabe"""
        while True:
            try:
                user_input = input(prompt)
                if not user_input and default is not None:
                    return default
                    
                result = InputValidator.validate_interval(user_input)
                
                if result.is_valid:
                    return result.value
                else:
                    print(f"❌ {result.error_message}")
                    
            except KeyboardInterrupt:
                print("\n👋 Eingabe abgebrochen")
                return None
            except EOFError:
                print("\n👋 Eingabe beendet")
                return None
    
    @staticmethod
    def get_choice(prompt: str, max_choice: int) -> Optional[int]:
        """Sichere Menü-Auswahl"""
        while True:
            try:
                user_input = input(prompt)
                result = InputValidator.validate_choice(user_input, max_choice)
                
                if result.is_valid:
                    return result.value
                else:
                    print(f"❌ {result.error_message}")
                    
            except KeyboardInterrupt:
                print("\n👋 Eingabe abgebrochen")
                return None
            except EOFError:
                print("\n👋 Eingabe beendet")
                return None
    
    @staticmethod
    def get_confirmation(prompt: str, expected: str) -> bool:
        """Sichere Bestätigung"""
        try:
            user_input = input(prompt)
            result = InputValidator.validate_confirmation(user_input, expected)
            return result.is_valid
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Eingabe abgebrochen")
            return False