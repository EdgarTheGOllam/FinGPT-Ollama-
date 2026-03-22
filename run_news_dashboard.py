#!/usr/bin/env python3
"""
FinGPT News Dashboard Launcher
Startet den Streamlit News-Tab als eigenständige Web-App

Verwendung:
    python run_news_dashboard.py
    oder
    streamlit run gui/views/news_tab_streamlit.py
"""

import subprocess
import sys
import os

def main():
    """Launcher für den Streamlit News-Tab"""
    
    print("=" * 60)
    print("📰 FinGPT News Dashboard - Streamlit")
    print("=" * 60)
    print()
    print("Starte Streamlit News-Tab...")
    print()
    
    # Pfad zur Streamlit Datei
    streamlit_file = os.path.join(
        os.path.dirname(__file__), 
        "gui", "views", "news_tab_streamlit.py"
    )
    
    if not os.path.exists(streamlit_file):
        print(f"❌ Fehler: Datei nicht gefunden: {streamlit_file}")
        sys.exit(1)
    
    # Streamlit starten
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            streamlit_file,
            "--server.port", "8501",
            "--server.address", "localhost",
            "--theme.base", "dark",
            "--theme.primaryColor", "#2979FF"
        ])
    except KeyboardInterrupt:
        print("\n👋 News Dashboard beendet.")
    except FileNotFoundError:
        print("❌ Streamlit nicht gefunden!")
        print("   Bitte installieren: pip install streamlit")
        sys.exit(1)

if __name__ == "__main__":
    main()
