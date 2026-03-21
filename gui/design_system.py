#!/usr/bin/env python3
"""
FinGPT Design System
Zentrale Definition aller Design-Tokens für konsistente UI-Gestaltung
"""

from typing import Dict, Any, Optional, Tuple
import customtkinter as ctk
import tkinter as tk


class DesignSystem:
    """
    Statische Klasse mit allen Design-Tokens.
    Alle GUI-Komponenten sollten diese Tokens verwenden, nicht hardcodierte Werte.
    """

    # ─────────────────────────────────────────────────────────────
    # FARBSYSTEM (WCAG 2.1 AA konform)
    # ─────────────────────────────────────────────────────────────
    COLORS = {
        # Primärfarben (Neon Blue)
        'primary': {
            'base': '#2979FF',
            'dark': '#0039CB',
            'light': '#75A7FF',
            'hover': '#2962FF'
        },
        'secondary': {
            'base': '#9C27B0',
            'dark': '#6A0080',
            'light': '#D05CE3',
            'hover': '#8E24AA'
        },
        # Success (Neon Green)
        'success': {
            'base': '#00FF66',
            'dark': '#00C853',
            'light': '#69FF97',
            'hover': '#00E676'
        },
        # Warning (Yellow)
        'warning': {
            'base': '#FFEA00',
            'dark': '#C7B700',
            'light': '#FFFF56',
            'hover': '#FFD600'
        },
        # Danger (Neon Red)
        'danger': {
            'base': '#FF1744',
            'dark': '#C4001D',
            'light': '#FF616F',
            'hover': '#D50000'
        },
        'neutral': {
            'white': '#FFFFFF',
            'light': '#8B949E',
            'medium': '#546E7A',
            'dark': '#1A1D24',
            'darker': '#0B0E14',
            'black': '#000000'
        }
    }

    # Semantische Farben (für konsistente Verwendung)
    SEMANTIC = {
        'profit': COLORS['success']['base'],
        'loss': COLORS['danger']['base'],
        'info': COLORS['primary']['base'],
        'warning': COLORS['warning']['base'],
        'error': COLORS['danger']['base'],
        'neutral': COLORS['neutral']['medium'],
        'background': ('#0B0E14', '#0B0E14'),  # TTG Deep Black
        'surface': ('#1A1D24', '#1A1D24'),    # TTG Panel Slate
        'border': ('#2A2D34', '#2A2D34'),     # Dark Border
        # Trading-spezifische Farben
        'premium': '#D05CE3',  # AI-Features, Insights
        'buy_signal': COLORS['success']['base'],
        'sell_signal': COLORS['danger']['base'],
        'hold_signal': COLORS['neutral']['medium'],
        'margin_warning': COLORS['warning']['base'],
    }
    
    # Trading-Farben (für schnellen Zugriff)
    TRADING_COLORS = {
        'profit': '#00FF66',     # Positive P&L, BUY-Signale (Neon Green)
        'loss': '#FF1744',       # Negative P&L, SELL-Signale (Neon Red)
        'neutral': '#8B949E',    # HOLD-Signale, inaktive Elemente
        'warning': '#FFEA00',    # Margin-Warnungen, Risiko-Limits
        'info': '#2979FF',       # Allgemeine Informationen
        'premium': '#D05CE3',    # AI-Features, Insights
    }

    # ─────────────────────────────────────────────────────────────
    # TYPOGRAFIE
    # ─────────────────────────────────────────────────────────────
    TYPOGRAPHY = {
        'font_family': 'Inter',
        'font_family_mono': 'Consolas',

        'sizes': {
            'xs': 11,   # Kleine Labels, Hinweise
            'sm': 13,   # Normale UI-Texte, Tabellen
            'base': 15, # Standard-Text
            'lg': 18,   # Überschriften
            'xl': 24,   # Große Metriken
            '2xl': 32,  # Hero-Texte
            '3xl': 40   # Titel
        },

        'weights': {
            'normal': 'normal',
            'medium': 'normal',  # Tkinter unterstützt keine numerischen weights, 'normal' verwenden
            'bold': 'bold',
            'heavy': 'bold'     # Tkinter unterstützt keine numerischen weights, 'bold' verwenden
        },

        'line_heights': {
            'tight': 1.2,
            'normal': 1.5,
            'relaxed': 1.75
        }
    }

    # ─────────────────────────────────────────────────────────────
    # SPACING (8-Punkte-Grid-System)
    # ─────────────────────────────────────────────────────────────
    SPACING = {
        'xs': 2,   # 2px
        'sm': 4,   # 4px
        'md': 8,  # 8px (Standard)
        'lg': 16,  # 16px
        'xl': 24,  # 24px
        '2xl': 32, # 32px
        '3xl': 48  # 48px
    }

    # ─────────────────────────────────────────────────────────────
    # BORDER RADIUS
    # ─────────────────────────────────────────────────────────────
    RADIUS = {
        'none': 0,
        'sm': 4,   # Kleine Buttons, Inputs
        'md': 6,  # Standard-Karten
        'lg': 8,  # Große Karten, Tabs
        'xl': 12,  # Hero-Elemente
        'full': 9999  # Pill-Buttons, Avatare
    }

    # ─────────────────────────────────────────────────────────────
    # SCHATTEN (falls in Zukunft benötigt)
    # ─────────────────────────────────────────────────────────────
    SHADOWS = {
        'none': '',
        'sm': '0 1px 2px rgba(0,0,0,0.1)',
        'md': '0 4px 6px rgba(0,0,0,0.15)',
        'lg': '0 10px 15px rgba(0,0,0,0.2)',
        'xl': '0 20px 25px rgba(0,0,0,0.25)'
    }

    # ─────────────────────────────────────────────────────────────
    # ANIMATION
    # ─────────────────────────────────────────────────────────────
    ANIMATION = {
        'fast': 100,      # 100ms
        'normal': 200,    # 200ms
        'slow': 350,      # 350ms
        'slower': 500,    # 500ms
        'easing': 'ease-out'  # Standard-Easing
    }

    # ─────────────────────────────────────────────────────────────
    # Z-INDEX LAYER (für Overlays)
    # ─────────────────────────────────────────────────────────────
    Z_INDEX = {
        'base': 0,
        'dropdown': 100,
        'modal': 200,
        'tooltip': 300,
        'toast': 400
    }

    # ─────────────────────────────────────────────────────────────
    # COMPONENT SPECIFISCHE TOKENS
    # ─────────────────────────────────────────────────────────────
    COMPONENTS = {
        'metric_card': {
            'icon_size': 20,
            'value_font_size': TYPOGRAPHY['sizes']['lg'],
            'title_font_size': TYPOGRAPHY['sizes']['xs'],
            'padding': SPACING['md'],
            'hover_scale': 1.02
        },
        'live_data_row': {
            'height': 50,
            'padding': SPACING['md'],
            'sparkline_width': 80,
            'sparkline_height': 30
        },
        'button': {
            'min_height': 32,
            'padding_x': SPACING['md'],
            'padding_y': SPACING['sm'],
            'border_radius': RADIUS['md']
        },
        'input': {
            'min_height': 32,
            'padding': SPACING['sm'],
            'border_radius': RADIUS['sm']
        },
        'tab': {
            'height': 45,
            'padding_x': SPACING['md'],
            'border_radius': RADIUS['lg']
        }
    }

    # ─────────────────────────────────────────────────────────────
    # BREAKPOINTS für Responsive Design
    # ─────────────────────────────────────────────────────────────
    BREAKPOINTS = {
        'sm': 640,   # Mobile
        'md': 768,   # Tablet
        'lg': 1024,  # Desktop
        'xl': 1280,  # Large Desktop
        '2xl': 1536  # Extra Large
    }

    # ─────────────────────────────────────────────────────────────
    # KLASSEN METHODEN
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def get_font(cls, size: str = 'base', weight: str = 'normal', mono: bool = False) -> ctk.CTkFont:
        """Erstellt ein CTkFont-Objekt mit den Design-Tokens."""
        family = cls.TYPOGRAPHY['font_family_mono'] if mono else cls.TYPOGRAPHY['font_family']
        font_size = cls.TYPOGRAPHY['sizes'].get(size, cls.TYPOGRAPHY['sizes']['base'])
        font_weight = cls.TYPOGRAPHY['weights'].get(weight, 'normal')
        return ctk.CTkFont(family=family, size=font_size, weight=font_weight)

    @classmethod
    def get_spacing(cls, size: str = 'md') -> int:
        """Gibt den Spacing-Wert zurück."""
        return cls.SPACING.get(size, cls.SPACING['md'])

    @classmethod
    def get_radius(cls, size: str = 'md') -> int:
        """Gibt den Border-Radius-Wert zurück."""
        return cls.RADIUS.get(size, cls.RADIUS['md'])

    @classmethod
    def get_color(cls, category: str, variant: str = 'base') -> str:
        """Gibt eine Farbe aus dem Farbsystem zurück."""
        if category in cls.COLORS:
            color_dict = cls.COLORS[category]
            if variant in color_dict:
                return color_dict[variant]
            # Fallback: ersten Wert im Dictionary zurückgeben
            if color_dict:
                return next(iter(color_dict.values()))
            return '#000000'
        return cls.SEMANTIC.get(category, '#000000')

    @classmethod
    def get_semantic_color(cls, semantic: str) -> str:
        """Gibt eine semantische Farbe zurück."""
        return cls.SEMANTIC.get(semantic, '#000000')

    @classmethod
    def apply_theme(cls, app: ctk.CTk) -> None:
        """Wendet das Design-System auf die CustomTkinter-App an."""
        # Farbschema setzen
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")  # Basis-Theme, wird überschrieben

        # Hier könnten in Zukunft weitere globale Einstellungen gesetzt werden
        # CustomTkinter hat begrenzte Theme-Anpassungsmöglichkeiten

    @classmethod
    def get_scaled_font(cls, base_size: int, window_width: int = 1400) -> int:
        """
        Skaliert Font-Größen basierend auf der Fenstergröße für Responsive Design.
        """
        if window_width < cls.BREAKPOINTS['md']:
            return int(base_size * 0.9)
        elif window_width > cls.BREAKPOINTS['xl']:
            return int(base_size * 1.1)
        return base_size

    @classmethod
    def get_current_breakpoint(cls, window_width: int) -> str:
        """
        Gibt den aktuellen Breakpoint basierend auf der Fensterbreite zurück.
        """
        if window_width < cls.BREAKPOINTS['sm']:
            return 'xs'
        elif window_width < cls.BREAKPOINTS['md']:
            return 'sm'
        elif window_width < cls.BREAKPOINTS['lg']:
            return 'md'
        elif window_width < cls.BREAKPOINTS['xl']:
            return 'lg'
        else:
            return 'xl'

    @classmethod
    def get_responsive_spacing(cls, spacing_name: str, window_width: int = 1400) -> int:
        """
        Passt Spacing-Werte basierend auf der Fenstergröße an.
        Reduziert Spacing auf kleinen Bildschirmen, um mehr Platz für Inhalte zu schaffen.
        """
        base_spacing = cls.SPACING.get(spacing_name, cls.SPACING['md'])
        
        if window_width < cls.BREAKPOINTS['sm']:
            return max(int(base_spacing * 0.5), 4)
        elif window_width < cls.BREAKPOINTS['md']:
            return max(int(base_spacing * 0.75), 8)
        elif window_width < cls.BREAKPOINTS['lg']:
            return int(base_spacing * 0.9)
        return base_spacing

    @classmethod
    def get_responsive_font(cls, size: str = 'base', window_width: int = 1400) -> ctk.CTkFont:
        """
        Erstellt ein responsive CTkFont-Objekt, das sich an die Fenstergröße anpasst.
        """
        base_size = cls.TYPOGRAPHY['sizes'].get(size, cls.TYPOGRAPHY['sizes']['base'])
        scaled_size = cls.get_scaled_font(base_size, window_width)
        return ctk.CTkFont(family=cls.TYPOGRAPHY['font_family'], size=scaled_size)

    @classmethod
    def get_min_width_for_breakpoint(cls, content_type: str) -> int:
        """
        Gibt die minimale Breite für verschiedene Inhaltstypen zurück.
        """
        min_widths = {
            'metric_card': 150,
            'chart_container': 300,
            'data_row': 600,
            'sidebar': 200,
            'button': 80
        }
        return min_widths.get(content_type, 100)

    @classmethod
    def calculate_grid_columns(cls, window_width: int, min_card_width: int = 150) -> int:
        """
        Berechnet die optimale Anzahl von Grid-Spalten basierend auf der Fensterbreite.
        """
        available_width = window_width - (cls.SPACING['lg'] * 2)  # Account for padding
        return max(1, min(6, available_width // min_card_width))


# Responsive Layout Manager
class ResponsiveLayout:
    """
    Hilfsklasse für responsives Layout-Management.
    Verwaltet die Anpassung von UI-Elementen an verschiedene Bildschirmgrößen.
    """
    
    def __init__(self, window: tk.Tk):
        self.window = window
        self._last_width = window.winfo_width()
        self._last_height = window.winfo_height()
        self._bind_events()
    
    def _bind_events(self):
        """Bindet die Größenänderungs-Events."""
        self.window.bind("<Configure>", self._on_configure)
    
    def _on_configure(self, event):
        """Wird aufgerufen, wenn das Fenster die Größe ändert."""
        if event.widget == self.window:
            new_width = event.width
            new_height = event.height
            
            # Nur aktualisieren, wenn sich die Größe signifikant geändert hat
            if abs(new_width - self._last_width) > 20 or abs(new_height - self._last_height) > 20:
                self._last_width = new_width
                self._last_height = new_height
                self.window.event_generate("<<ResponsiveLayoutChanged>>", when='tail')


# Convenience-Funktionen für häufige Operationen
def create_button(parent, text: str, style: str = 'primary', **kwargs):
    """
    Factory-Funktion für konsistente Buttons.
    Style-Optionen: 'primary', 'secondary', 'success', 'warning', 'danger', 'ghost'
    """
    ds = DesignSystem
    styles = {
        'primary': {'fg_color': ds.get_color('primary'), 'hover_color': ds.get_color('primary', 'hover')},
        'secondary': {'fg_color': ds.get_color('secondary'), 'hover_color': ds.get_color('secondary', 'hover')},
        'success': {'fg_color': ds.get_color('success'), 'hover_color': ds.get_color('success', 'hover')},
        'warning': {'fg_color': ds.get_color('warning'), 'hover_color': ds.get_color('warning', 'hover')},
        'danger': {'fg_color': ds.get_color('danger'), 'hover_color': ds.get_color('danger', 'hover')},
        'ghost': {'fg_color': 'transparent', 'border_width': 1, 'border_color': ds.get_color('primary')}
    }

    style_config = styles.get(style, styles['primary'])

    # Standard-Button-Parameter
    default_kwargs = {
        'height': ds.COMPONENTS['button']['min_height'],
        'corner_radius': ds.COMPONENTS['button']['border_radius'],
        'font': ds.get_font('base', 'medium')
    }

    # Merge mit User-Kwargs (User hat Vorrang)
    config = {**default_kwargs, **style_config, **kwargs}

    return ctk.CTkButton(parent, text=text, **config)


def create_card(parent, **kwargs):
    """Factory-Funktion für konsistente Karten."""
    ds = DesignSystem
    default_kwargs = {
        'corner_radius': ds.COMPONENTS['metric_card']['border_radius'] if 'border_radius' in ds.COMPONENTS['metric_card'] else ds.get_radius('md'),
        'fg_color': ds.SEMANTIC['surface'],
        'border_width': 0
    }
    config = {**default_kwargs, **kwargs}
    return ctk.CTkFrame(parent, **config)


def create_label(parent, text: str, size: str = 'base', weight: str = 'normal', **kwargs):
    """Factory-Funktion für konsistente Labels."""
    ds = DesignSystem
    default_kwargs = {
        'font': ds.get_font(size, weight),
        'text_color': ds.SEMANTIC['neutral']
    }
    config = {**default_kwargs, **kwargs}
    return ctk.CTkLabel(parent, text=text, **config)


def create_entry(parent, **kwargs):
    """Factory-Funktion für konsistente Eingabefelder."""
    ds = DesignSystem
    default_kwargs = {
        'height': ds.COMPONENTS['input']['min_height'],
        'corner_radius': ds.get_radius('sm'),
        'border_width': 1
    }
    config = {**default_kwargs, **kwargs}
    return ctk.CTkEntry(parent, **config)


def create_slider(parent, **kwargs):
    """Factory-Funktion für konsistente Slider."""
    ds = DesignSystem
    default_kwargs = {
        'button_corner_radius': ds.get_radius('full'),
        'button_length': 16,
        'border_width': 0
    }
    config = {**default_kwargs, **kwargs}
    return ctk.CTkSlider(parent, **config)


if __name__ == "__main__":
    # Test des Design-Systems
    print("FinGPT Design System")
    print("=" * 50)
    print(f"Primary Color: {DesignSystem.get_color('primary')}")
    print(f"Success Color: {DesignSystem.get_semantic_color('profit')}")
    print(f"Base Font: {DesignSystem.get_font('base')}")
    print(f"Spacing (lg): {DesignSystem.get_spacing('lg')}px")
    print(f"Radius (md): {DesignSystem.get_radius('md')}px")
    print("\nAlle Tokens erfolgreich definiert!")
