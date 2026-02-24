import re
import json
import requests
import logging

class AIAnalyzer:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.ollama_url = "http://localhost:11434"
        self.available_models = []
        self.selected_model = None
        
    def log(self, level, message, category="AI"):
        if self.logger:
            formatted_message = f"[{category}] {message}"
            if level == "INFO": self.logger.info(formatted_message)
            elif level == "WARNING": self.logger.warning(formatted_message)
            elif level == "ERROR": self.logger.error(formatted_message)
            elif level == "DEBUG": self.logger.debug(formatted_message)
            
    def check_ollama_status(self):
        """Überprüft die Verfügbarkeit des Ollama-Servers"""
        try:
            response = requests.get(f"{self.ollama_url}/api/version", timeout=2)
            return response.status_code == 200
        except:
            return False

    def get_available_models(self):
        """Holt die Liste der installierten Ollama-Modelle"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                self.available_models = [m['name'] for m in models]
                return self.available_models
        except Exception as e:
            self.log("ERROR", f"Modell-Abruf fehlgeschlagen: {e}")
        return []

    def select_finance_model(self):
        """Wählt automatisch das beste finanzspezifische Modell (z.B. Llama3)"""
        models = self.get_available_models()
        if not models:
             print("❌ Keine Ollama Modelle gefunden. Bitte installieren (z.B. 'ollama run llama3')")
             return False
             
        # Prefer llama models if available
        for m in models:
             if 'llama3' in m.lower():
                 self.selected_model = m
                 self.log("INFO", f"Modell automatisch ausgewählt: {m}")
                 return True
                 
        self.selected_model = models[0]
        self.log("INFO", f"Standard-Modell ausgewählt: {self.selected_model}")
        return True

    def chat_with_model(self, message, context=""):
        """Sendet einen Prompt an Ollama und gibt die Antwort zurück"""
        if not self.selected_model:
            if not self.select_finance_model():
                 return "Fehler: Kein KI-Modell verfügbar"

        system_prompt = (
            "Du bist ein professioneller Forex Trading Assistent (FinGPT). "
            "Analysiere die folgenden Marktdaten präzise und objektiv. "
            "Gib immer eine konkrete Empfehlung ab: 'BUY', 'SELL' oder 'WARTEN'. "
            "Begründe diese kurz mit den wichtigsten Indikatoren (RSI, S/R, Trend). "
            "Antworte auf Deutsch im professionellen Ton."
        )

        full_prompt = message
        if context:
            full_prompt = f"Kontextdaten:\n{context}\n\nFrage/Aufgabe:\n{message}"

        data = {
            "model": self.selected_model,
            "prompt": full_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.2, # Low temperature for more analytical responses
                "top_p": 0.9,
            }
        }

        try:
            response = requests.post(f"{self.ollama_url}/api/generate", json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Keine Antwort erhalten")
            else:
                return f"Fehler vom KI-Server (Code: {response.status_code})"
        except requests.exceptions.Timeout:
            return "Fehler: Timeout bei der KI-Anfrage (Modell braucht zu lange)"
        except Exception as e:
            return f"Fehler bei der KI-Anfrage: {str(e)}"

    def parse_ai_recommendation(self, ai_text):
         """Liest die Empfehlung (BUY/SELL/WARTEN) aus dem Text der KI"""
         text = ai_text.upper()
         
         # Starke Signale zuerst
         if "STRONG BUY" in text or "STARKER KAUF" in text: return "STRONG_BUY"
         if "STRONG SELL" in text or "STARKER VERKAUF" in text: return "STRONG_SELL"
         
         # Normale Signale
         if bool(re.search(r'\bBUY\b|\bKAUFEN\b|\bLONG\b', text)): return "BUY"
         if bool(re.search(r'\bSELL\b|\bVERKAUFEN\b|\bSHORT\b', text)): return "SELL"
         
         return "WARTEN"
         
    def extract_trade_reasoning(self, ai_response):
         """Extrahiert die Begründung aus der KI-Antwort"""
         lines = ai_response.split('\n')
         reasonings = []
         capture = False
         
         for line in lines:
             line = line.strip()
             if not line: continue
             
             lower_line = line.lower()
             if any(keyword in lower_line for keyword in ['begründung', 'grund', 'analyse', 'fazit', 'zusammenfassung']):
                 capture = True
                 if ':' in line:
                     content = line.split(':', 1)[1].strip()
                     if content: reasonings.append(content)
                 continue
                 
             if capture:
                 if len(line) > 10 and not line.startswith('Empfehlung:'):
                     reasonings.append(line.replace('*', '').replace('-', '').strip())
                     if len(reasonings) >= 2: break
                     
         if reasonings:
             return " ".join(reasonings)
         
         # Backup logic (first sentence not containing the recommendation)
         sentences = re.split(r'[.!?]+', ai_response)
         for s in sentences:
             if len(s.strip()) > 20 and not any(w in s.upper() for w in ['BUY', 'SELL', 'WARTEN', 'EMPFEHLUNG']):
                 return s.strip()
                 
         return "Basierend auf Indikatoren-Mix"

    def format_ai_response(self, response):
         """Formatiert die KI-Antwort schöner und lesbarer"""
         formatted = response
         formatted = formatted.replace("BUY", "🟢 BUY")
         formatted = formatted.replace("SELL", "🔴 SELL")
         formatted = formatted.replace("WARTEN", "🟡 WARTEN")
         
         # Markdown headers
         formatted = re.sub(r'\*\*(.*?)\*\*', r'\033[1m\1\033[0m', formatted)
         return formatted

    def extract_recommendation_summary(self, ai_response):
         """Extrahiert eine kurze Zusammenfassung der KI-Empfehlung"""
         rec = self.parse_ai_recommendation(ai_response)
         reason = self.extract_trade_reasoning(ai_response)
         reason_short = reason[:40] + "..." if len(reason) > 40 else reason
         return f"{rec} ({reason_short})"

    def display_formatted_analysis(self, symbol, ai_response, live_data=""):
         """Zeigt die KI-Analyse schön formatiert an (CLI helper)"""
         print(f"\n{'='*60}")
         print(f"🤖 KI ANALYSE ERGEBNIS: {symbol}")
         print(f"{'='*60}")
         
         recommendation = self.parse_ai_recommendation(ai_response)
         
         icon = "🟢" if "BUY" in recommendation else "🔴" if "SELL" in recommendation else "🟡"
         print(f"\n{icon} EMPFEHLUNG: {recommendation}")
         print("-" * 60)
         
         print("\n📝 BEGRÜNDUNG:")
         formatted_text = self.format_ai_response(ai_response)
         print(formatted_text)
         
         print(f"\n{'='*60}")
