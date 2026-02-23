import customtkinter as ctk

class MetricCard(ctk.CTkFrame):
    """Eine wiederverwendbare Metrik-Karte mit modernem Design"""
    def __init__(self, master, title, value, **kwargs):
        super().__init__(master, fg_color=("gray85", "gray17"), corner_radius=15, **kwargs)
        
        self.title_label = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="gray60")
        self.title_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.value_label = ctk.CTkLabel(self, text=value, font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color="#2E86AB")
        self.value_label.pack(anchor="w", padx=15, pady=(0, 15))

    def update_value(self, new_value):
        self.value_label.configure(text=new_value)
