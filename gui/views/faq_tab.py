import customtkinter as ctk
from customtkinter import CTkImage
import os
import glob
import re
import webbrowser
from PIL import Image
import urllib.request
import io

class FAQView:
    def __init__(self, master_tab, app):
        self.tab = master_tab
        self.app = app
        self.faq_dataset = {}
        self._load_markdown_docs()
        self.setup_ui()

    def _load_markdown_docs(self):
        """Loads FAQ content from local markdown files"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        docs_dir = os.path.join(base_dir, "faq_docs")
        
        if not os.path.exists(docs_dir):
            self.app.write_terminal("[WARN] FAQ Docs Ordner nicht gefunden.", "WARN")
            return
            
        md_files = glob.glob(os.path.join(docs_dir, "*.md"))
        
        for file in md_files:
            if os.path.basename(file).lower() == "readme.md":
                continue # Skip the welcome file
                
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Very basic extraction: 
            # 1. Category name from first # header
            # 2. Pairs of ### Question / Text
            
            category_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            category_name = category_match.group(1).strip() if category_match else os.path.basename(file).replace('.md', '').title()
            
            # Extract Q/A blocks
            # Split by ### 
            parts = re.split(r'^###\s+', content, flags=re.MULTILINE)
            
            qa_list = []
            for part in parts[1:]: # First part is everything before the first ###
                lines = part.strip().split('\n')
                if not lines: continue
                question = lines[0].strip()
                answer = '\n'.join(lines[1:]).strip()
                qa_list.append((question, answer))
                
            if qa_list:
                self.faq_dataset[category_name] = qa_list

    def setup_ui(self):
        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_columnconfigure(1, weight=4)
        self.tab.grid_rowconfigure(1, weight=1)
        
        # Header
        header = ctk.CTkFrame(self.tab, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(header, text="Häufig gestellte Fragen (FAQ)", 
                     font=ctk.CTkFont(family="Inter", size=24, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="Hilfe zur Software & Trading-Plattform", 
                     font=ctk.CTkFont(family="Inter", size=14), text_color="#8B949E").pack(side="left", padx=(15, 0), pady=(8, 0))

        # Check if we loaded anything
        if not self.faq_dataset:
            ctk.CTkLabel(self.tab, text="Keine Dokumentation gefunden.\nGeneriere die Markdown-Dateien im faq_docs/ Ordner.", 
                         text_color="#8B949E").grid(row=1, column=0, columnspan=2)
            return

        # Sidebar for categories
        sidebar = ctk.CTkFrame(self.tab, corner_radius=10, fg_color="#1A1D24")
        sidebar.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))
        
        # Configure sidebar rows: row 0 = header, row 1 = buttons (expandable), row 2 = links
        sidebar.grid_rowconfigure(0, weight=0)
        sidebar.grid_rowconfigure(1, weight=1)
        sidebar.grid_rowconfigure(2, weight=0)
        
        ctk.CTkLabel(sidebar, text="Themen", font=ctk.CTkFont(family="Inter", size=14, weight="bold"), text_color="#8B949E").grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))

        # Content area for questions
        self.faq_content_area = ctk.CTkScrollableFrame(self.tab, fg_color="transparent")
        self.faq_content_area.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(0, 20))

        # Render Category Buttons
        self.faq_buttons = []
        
        def sort_key(cat_name):
            # Sort by the actual text, ignoring leading emojis
            clean = re.sub(r'^.*?([a-zA-Z])', r'\1', cat_name).strip().lower()
            return clean if clean else cat_name.lower()
            
        # Category buttons container
        buttons_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        buttons_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        for cat in sorted(self.faq_dataset.keys(), key=sort_key):
            btn = ctk.CTkButton(buttons_frame, text=cat, fg_color="transparent", text_color="#8B949E", anchor="w",
                                hover_color="#2A2A2A", command=lambda c=cat: self._render_faq_category(c))
            btn.pack(fill="x", padx=5, pady=2)
            self.faq_buttons.append((cat, btn))

        # Social Links section at the bottom
        self._create_social_links(sidebar)

        # Load first category
        if self.faq_dataset:
            first_cat = list(self.faq_dataset.keys())[0]
            self._render_faq_category(first_cat)

    def _render_faq_category(self, category_name):
        """Updates the FAQ content area with items matching the selected category."""
        # Update button highlighting
        for name, btn in self.faq_buttons:
            if name == category_name:
                btn.configure(fg_color="#333333", text_color="#00FF66", font=ctk.CTkFont(family="Inter", weight="bold"))
            else:
                btn.configure(fg_color="transparent", text_color="#8B949E", font=ctk.CTkFont(family="Inter", weight="normal"))

        # Clear existing cards
        for widget in self.faq_content_area.winfo_children():
            widget.destroy()

        # Title for the section
        ctk.CTkLabel(self.faq_content_area, text=category_name, font=ctk.CTkFont(family="Inter", size=22, weight="bold"), 
                     text_color="#FFFFFF").pack(anchor="w", padx=10, pady=(0, 15))

        # Render new cards
        faqs = self.faq_dataset.get(category_name, [])
        for question, answer in faqs:
            card = ctk.CTkFrame(self.faq_content_area, fg_color="#1A1D24", corner_radius=12)
            card.pack(fill="x", padx=5, pady=(0, 15))
            card.grid_columnconfigure(0, weight=1)
            
            q_lbl = ctk.CTkLabel(card, text=f"{question}", font=ctk.CTkFont(family="Inter", size=15, weight="bold"), 
                                 text_color="#00FF66", justify="left", anchor="w", wraplength=750)
            q_lbl.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
            
            a_lbl = ctk.CTkLabel(card, text=answer, font=ctk.CTkFont(family="Inter", size=13), 
                                 text_color="#8B949E", justify="left", anchor="w", wraplength=750)
            a_lbl.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))

    def _create_social_links(self, sidebar):
        """Creates social links section at the bottom of the FAQ sidebar."""
        # Separator line
        separator = ctk.CTkFrame(sidebar, height=1, fg_color="#333333")
        separator.grid(row=2, column=0, sticky="ew", padx=15, pady=(10, 10))
        
        # Links container
        links_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        links_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 15))
        
        # Configure link buttons at the bottom of sidebar row 2
        links_frame.grid_columnconfigure(0, weight=1)
        links_frame.grid_columnconfigure(1, weight=1)
        links_frame.grid_columnconfigure(2, weight=1)
        
        # Social links configuration - Edit these URLs as needed
        # Download icons from Flaticon CDN
        icons = {}
        icon_urls = {
            "github": "https://cdn-icons-png.flaticon.com/512/25/25231.png",
            "web": "https://cdn-icons-png.flaticon.com/512/1927/1927746.png",
            "discord": "https://cdn-icons-png.flaticon.com/512/5968/5968756.png",
        }
        
        for name, url in icon_urls.items():
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    image_data = response.read()
                    image = Image.open(io.BytesIO(image_data))
                    icons[name] = CTkImage(image, size=(20, 20))
            except Exception as e:
                self.app.write_terminal(f"[WARN] {name.title()} Icon konnte nicht geladen werden: {e}", "WARN")
        
        # Create buttons for each social link
        social_links = [
            {"name": "github", "icon": icons.get("github"), "fallback": "🌐", "url": "https://github.com/EdgarTheGOllam/FinGPT-Ollama-"},
            {"name": "web", "icon": icons.get("web"), "fallback": "🌍", "url": "https://ihre-website.de"},
            {"name": "discord", "icon": icons.get("discord"), "fallback": "💬", "url": "https://discord.gg/ihre-invite"},
        ]
        
        for idx, link in enumerate(social_links):
            if link["icon"]:
                btn = ctk.CTkButton(
                    links_frame,
                    text="",
                    image=link["icon"],
                    fg_color="transparent",
                    hover_color="#2A2A2A",
                    width=40,
                    command=lambda u=link["url"]: self._open_link(u)
                )
            else:
                btn = ctk.CTkButton(
                    links_frame,
                    text=link["fallback"],
                    fg_color="transparent",
                    text_color="#8B949E",
                    hover_color="#2A2A2A",
                    width=40,
                    command=lambda u=link["url"]: self._open_link(u)
                )
            btn.grid(row=0, column=idx, padx=5, pady=5)

    def _open_link(self, url):
        """Opens the given URL in the default web browser."""
        try:
            webbrowser.open(url)
        except Exception as e:
            self.app.write_terminal(f"[FEHLER] Konnte Link nicht öffnen: {url} - {str(e)}", "ERROR")
