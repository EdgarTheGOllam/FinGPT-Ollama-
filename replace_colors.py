import os
import re
import glob

views_dir = r"c:\Users\edgar\Desktop\FinGPT-Ollama-\gui\views"
pattern = os.path.join(views_dir, "*.py")

color_map = [
    # Backgrounds and Surfaces
    (r'\("gray85",\s*"[^"]+"\)', '"#1A1D24"'),
    (r'\("gray90",\s*"[^"]+"\)', '"#1A1D24"'),
    (r'\("gray8[0-9]",\s*"[^"]+"\)', '"#1A1D24"'),
    (r'\("white",\s*"[^"]+"\)', '"#1A1D24"'),
    
    # Text colors
    (r'text_color="gray[0-9]+"', 'text_color="#8B949E"'),
    (r'text_color="white"', 'text_color="#FFFFFF"'),
    
    # Hover colors
    (r'hover_color="gray[0-9]+"', 'hover_color="#2A2D34"'),
    (r'\("gray75",\s*"gray25"\)', '"#2A2D34"'),
    
    # Foreground colors (Panels)
    (r'fg_color="gray[0-9]+"', 'fg_color="#1A1D24"'),
    (r'fg_color="transparent"', 'fg_color="transparent"'), # Keep transparent
    
    # Primary/Accent Colors
    (r'"#5EBA7D"', '"#00FF66"'), # Green
    (r'"#2ECC71"', '"#00FF66"'), # Green 2
    (r'"#E74C3C"', '"#FF1744"'), # Red
    (r'"#F39C12"', '"#FFEA00"'), # Yellow
    (r'"#2E86AB"', '"#2979FF"'), # Blue
    (r'"#A23B72"', '"#9C27B0"'), # Purple/Secondary
]

files_changed = 0

for filepath in glob.glob(pattern):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    for pattern_str, replacement in color_map:
        content = re.sub(pattern_str, replacement, content)
        
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        files_changed += 1
        print(f"Updated {os.path.basename(filepath)}")

print(f"Total files updated: {files_changed}")
