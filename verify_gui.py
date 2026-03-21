import sys
import os
sys.path.insert(0, r"c:\Users\edgar\Desktop\FinGPT-Ollama-")

try:
    from gui.modern_fingpt_gui import main, ModernFinGPTGUI
    print("Imports successful.")
    
    # Try just initializing the app class to catch any widget parameter errors (like bad colors)
    app = ModernFinGPTGUI()
    print("App initialized successfully without crashing! Colors and widgets are valid.")
    app.destroy()
except Exception as e:
    print(f"Error during initialization: {e}")
    sys.exit(1)
