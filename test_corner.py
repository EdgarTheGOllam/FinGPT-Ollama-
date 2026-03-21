import customtkinter as ctk
import ctypes

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("600x400")
        self.overrideredirect(True)
        self.configure(fg_color="#1a1a1a")
        
        self.after(200, self._set_appwindow)
        
        self.title_bar = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color="transparent")
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.bind("<B1-Motion>", self._move_window)
        self.title_bar.bind("<Button-1>", self._get_pos)
        
        self.apple_buttons_frame = ctk.CTkFrame(self.title_bar, fg_color="transparent")
        self.apple_buttons_frame.pack(side="left", padx=10)
        
        self.close_btn = ctk.CTkButton(self.apple_buttons_frame, width=12, height=12, corner_radius=6, text="", 
                                       fg_color="#FF5F56", hover_color="#E0443E", command=self.destroy)
        self.close_btn.pack(side="left", padx=4)
        
        self.min_btn = ctk.CTkButton(self.apple_buttons_frame, width=12, height=12, corner_radius=6, text="", 
                                     fg_color="#FFBD2E", hover_color="#DEA121", command=self._minimize_window)
        self.min_btn.pack(side="left", padx=4)
        
        self.max_btn = ctk.CTkButton(self.apple_buttons_frame, width=12, height=12, corner_radius=6, text="", 
                                     fg_color="#27C93F", hover_color="#1AAB29", command=self._maximize_window)
        self.max_btn.pack(side="left", padx=4)
        
        self.lbl = ctk.CTkLabel(self, text="Testing Native Corner Rounding")
        self.lbl.pack(expand=True)

    def _set_appwindow(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            # Windows 11 rounded corners hack
            # DWMWA_WINDOW_CORNER_PREFERENCE = 33
            # DWMWCP_ROUND = 2, DWMWCP_ROUNDSMALL = 3
            value = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(value), ctypes.sizeof(value))
        except Exception as e:
            print(f"Error setting corners: {e}")

    def _get_pos(self, event):
        self._xwin = event.x
        self._ywin = event.y

    def _move_window(self, event):
        self.geometry(f"+{event.x_root - self._xwin}+{event.y_root - self._ywin}")

    def _minimize_window(self):
        pass

    def _maximize_window(self):
        pass

if __name__ == "__main__":
    app = App()
    app.after(3000, app.destroy)
    app.mainloop()
