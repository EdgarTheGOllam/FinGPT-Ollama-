#!/usr/bin/env python3
"""
Testskript für die moderne FinGPT GUI
Überprüft die Funktionalität und Stabilität der neuen GUI
"""

import sys
import os
import threading
import time
from pathlib import Path

def test_imports():
    """Testet ob alle benötigten Module importiert werden können"""
    print("Teste Modul-Imports...")
    
    try:
        import tkinter as tk
        print("✓ tkinter verfügbar")
    except ImportError as e:
        print(f"✗ tkinter nicht verfügbar: {e}")
        return False
        
    try:
        import plotly
        print("✓ plotly verfügbar")
    except ImportError as e:
        print(f"⚠ plotly nicht verfügbar: {e}")
        
    try:
        import requests
        print("✓ requests verfügbar")
    except ImportError as e:
        print(f"✗ requests nicht verfügbar: {e}")
        return False
        
    try:
        from gui.modern_fingpt_gui import ModernFinGPTGUI
        print("✓ ModernFinGPTGUI verfügbar")
    except ImportError as e:
        print(f"✗ ModernFinGPTGUI nicht verfügbar: {e}")
        return False
        
    return True

def test_gui_creation():
    """Testet ob die GUI erstellt werden kann"""
    print("\nTeste GUI-Erstellung...")
    
    try:
        from gui.modern_fingpt_gui import ModernFinGPTGUI
        # Erstelle eine Instanz der GUI (ohne sie anzuzeigen)
        gui = ModernFinGPTGUI()
        print("✓ GUI-Erstellung erfolgreich")
        return True
    except Exception as e:
        print(f"✗ GUI-Erstellung fehlgeschlagen: {e}")
        return False

def test_launcher():
    """Testet den Launcher"""
    print("\nTeste Launcher...")
    
    try:
        # Führe den Launcher aus und prüfe ob er korrekt startet
        import subprocess
        import sys
        
        # Starte den Launcher für 3 Sekunden und beende ihn dann
        process = subprocess.Popen([sys.executable, "launch_gui.py"], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 text=True)
        
        # Warte 3 Sekunden
        time.sleep(3)
        
        # Prüfe ob der Prozess läuft
        if process.poll() is None:
            # Prozess läuft noch, beende ihn
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
            print("✓ Launcher startet korrekt")
            return True
        else:
            # Prozess hat sich bereits beendet
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                print("✓ Launcher beendet ohne Fehler")
                return True
            else:
                print(f"✗ Launcher beendet mit Fehler (Code {process.returncode}): {stderr}")
                return False
                
    except Exception as e:
        print(f"✗ Launcher-Test fehlgeschlagen: {e}")
        return False

def main():
    """Hauptfunktion für die Tests"""
    print("=== Test der modernen FinGPT GUI ===")
    print(f"Python Version: {sys.version}")
    print(f"Arbeitsverzeichnis: {os.getcwd()}")
    print()
    
    # Führe alle Tests aus
    tests = [
        ("Modul-Imports", test_imports),
        ("GUI-Erstellung", test_gui_creation),
        ("Launcher", test_launcher)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} fehlgeschlagen mit Ausnahme: {e}")
            results.append((test_name, False))
    
    # Zeige Zusammenfassung
    print("\n=== Testergebnisse ===")
    passed = 0
    for test_name, result in results:
        status = "BESTANDEN" if result else "FEHLGESCHLAGEN"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n{passed}/{len(tests)} Tests bestanden")
    
    if passed == len(tests):
        print("🎉 Alle Tests erfolgreich!")
        return 0
    else:
        print("❌ Einige Tests sind fehlgeschlagen!")
        return 1

if __name__ == "__main__":
    sys.exit(main())