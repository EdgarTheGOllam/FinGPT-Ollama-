import customtkinter as ctk
import tkinter as tk
from gui.design_system import DesignSystem

def hex_to_rgb(hex_color):
    """Konvertiert einen Hex-Farbstring in ein RGB-Tuple."""
    if hex_color == "transparent":
        # Fallback falls transparent übergeben wird - wir nehmen den TTG Deep Black als Base
        return (9, 9, 11) # #09090B
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    """Konvertiert ein RGB-Tuple in einen Hex-Farbstring."""
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

def interpolate_color(c1_hex, c2_hex, factor):
    """Gibt eine interpolierte Farbe zwischen zwei Hex-Werten als Hex-String zurück."""
    c1 = hex_to_rgb(c1_hex)
    c2 = hex_to_rgb(c2_hex)
    r = c1[0] + (c2[0] - c1[0]) * factor
    g = c1[1] + (c2[1] - c1[1]) * factor
    b = c1[2] + (c2[2] - c1[2]) * factor
    return rgb_to_hex((r, g, b))


class HoverFadeFrame(ctk.CTkFrame):
    """
    Ein interaktiver Frame für das Dashboard. 
    Eigenschaften:
    - Fühlt sich nach einer einstellbaren Inaktivitätszeit in den Hintergrund ein (Fade).
    - Leuchtet bei Mouse-Hover wieder auf.
    - Ermöglicht Drag & Drop zum Tauschen von Grid-Positionen mit anderen HoverFadeFrames.
    """
    
    # Static drag state
    _drag_start_widget = None
    _drag_start_x = 0
    _drag_start_y = 0
    
    def __init__(self, master, 
                 active_bg_color="#18181B", 
                 active_border_color=None, 
                 idle_border_color="#27272A", 
                 fade_delay_ms=3000, 
                 draggable=True,
                 **kwargs):
        super().__init__(master, **kwargs)
        
        ds = DesignSystem
        self.fade_delay_ms = fade_delay_ms
        self.draggable = draggable
        
        # Dashboard Background Color (Deep Black)
        self.dashboard_bg = "#09090B" 
        
        # Colors state
        self.active_bg_color = active_bg_color
        self.active_border_color = active_border_color or ds.get_color('primary')
        self.idle_border_color = idle_border_color
        
        # Momentane Zustände
        self._fade_timer = None
        self._is_hovered = False
        self._is_dragging = False
        
        # Initialer, wacher Zustand
        self.configure(fg_color=self.active_bg_color, border_color=self.idle_border_color)
        
        # Events binden (rekursiv für alle Kinder)
        self._bind_events(self)
        
        # Starte den ersten Fade-Timer
        self.reset_fade_timer()

    def _bind_events(self, widget):
        if str(widget) != str(self):
            widget.bind("<Enter>", self._on_enter, add="+")
            widget.bind("<Leave>", self._on_leave, add="+")
        else:
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
            
        if self.draggable:
            widget.bind("<ButtonPress-1>", self._on_drag_start, add="+")
            widget.bind("<B1-Motion>", self._on_drag_motion, add="+")
            widget.bind("<ButtonRelease-1>", self._on_drag_stop, add="+")
            
        # Optional: Jede Mausbewegung auf Kindern setzt den Timer zurück
        widget.bind("<Motion>", lambda e: self.reset_fade_timer(), add="+")
            
        for child in widget.winfo_children():
            self._bind_events(child)

    def reset_fade_timer(self):
        """Startet den Timer neu, bis das Frame verblasst."""
        if self._fade_timer:
            self.after_cancel(self._fade_timer)
        self._fade_timer = self.after(self.fade_delay_ms, self._fade_out)

    def _on_enter(self, event):
        self._is_hovered = True
        if self._fade_timer:
            self.after_cancel(self._fade_timer)
            self._fade_timer = None
        # Sofort voll aufleuchten
        self.configure(fg_color=self.active_bg_color, border_color=self.active_border_color)

    def _on_leave(self, event):
        # Prüfen, ob wir wirklich das gesamte Frame verlassen haben
        x, y = self.winfo_pointerxy()
        widget_under_mouse = self.winfo_containing(x, y)
        if widget_under_mouse and str(widget_under_mouse).startswith(str(self)):
            return # Noch innerhalb des Frames oder eines Kindes
            
        self._is_hovered = False
        # Zurücksetzen auf den inaktiven "idle" Status bevor es ganz fadet
        self.configure(fg_color=self.active_bg_color, border_color=self.idle_border_color)
        self.reset_fade_timer()

    def _fade_out(self):
        """Sanfter Farb-Übergang zur Dashboard Hintergrundfarbe."""
        if self._is_hovered or self._is_dragging:
            return
            
        # Wir blenden den Border in die Dashboard-HG-Farbe (unsichtbar)
        steps = 15
        duration = 300 # ms
        delay_per_step = duration // steps
        
        current_border = self.cget("border_color")
        if isinstance(current_border, tuple):
            current_border = current_border[0]
            
        for i in range(1, steps + 1):
            factor = i / float(steps)
            new_border = interpolate_color(current_border, self.dashboard_bg, factor)
            # Optional: fg_color auch leicht abdunkeln
            new_bg = interpolate_color(self.active_bg_color, self.dashboard_bg, factor * 0.8) # 80% an den HG anpassen
            
            self.after(i * delay_per_step, lambda b=new_border, bg=new_bg: self._set_colors_if_not_hovered(bg, b))
            
    def _set_colors_if_not_hovered(self, bg, border):
        if not self._is_hovered and not self._is_dragging:
            self.configure(fg_color=bg, border_color=border)

    # --- DRAG AND DROP SWAP LOGIC ---

    def _on_drag_start(self, event):
        HoverFadeFrame._drag_start_widget = self
        self._is_dragging = True
        
        # Setze einen hellen, markanten Rahmen für das Element, das gerade bewegt wird
        self.configure(border_color=DesignSystem.get_color('warning'))

    def _on_drag_motion(self, event):
        pass # Optional: den Rahmen oder Maus-Cursor ändern

    def _on_drag_stop(self, event):
        if not HoverFadeFrame._drag_start_widget or HoverFadeFrame._drag_start_widget != self:
            return
            
        self._is_dragging = False
        HoverFadeFrame._drag_start_widget = None
        self._on_enter(None) # Aktive Farben wiederherstellen
        
        # Finde heraus, welches Element unter der Maus ist beim Loslassen
        x, y = self.winfo_pointerxy()
        widget_under_mouse = self.winfo_containing(x, y)
        
        target_swap = self._get_parent_hover_fade_frame(widget_under_mouse)
        
        # Tausche ihre Grid-Positionen
        if target_swap and target_swap != self:
            self._swap_grid_positions(self, target_swap)

    def _get_parent_hover_fade_frame(self, widget):
        """Such den nächstgelegenen HoverFadeFrame in der Widget-Hierarchie nach oben."""
        current = widget
        while current:
            if isinstance(current, HoverFadeFrame):
                return current
            current = current.master
        return None

    def _swap_grid_positions(self, frame_a, frame_b):
        """Liest die grid_info beider Frames und wendet sie vertauscht an."""
        try:
            info_a = frame_a.grid_info()
            info_b = frame_b.grid_info()
            
            # Wichtige Parameter für den Tausch
            keys = ['row', 'column', 'rowspan', 'columnspan', 'sticky', 'padx', 'pady']
            kw_a = {k: info_a[k] for k in keys if k in info_a}
            kw_b = {k: info_b[k] for k in keys if k in info_b}
            
            # Neu zuweisen
            frame_a.grid(**kw_b)
            frame_b.grid(**kw_a)
            
            # Optional: Kurzes "Blinken" um Tausch zu signalisieren
            frame_a.configure(border_color=DesignSystem.get_semantic_color('profit'))
            frame_b.configure(border_color=DesignSystem.get_semantic_color('profit'))
            
            frame_a.after(300, lambda: frame_a._on_leave(None))
            frame_b.after(300, lambda: frame_b._on_leave(None))
            
        except Exception as e:
            print(f"Fehler beim Drag-Swap: {e}")

