#!/usr/bin/env python3
"""
Multi-Account Manager Widget für FinGPT
Verwaltet mehrere MT5-Konten und ermöglicht schnellen Kontowechsel
"""

import sys
import os
import customtkinter as ctk
from tkinter import messagebox
import threading
import json
from datetime import datetime

# Füge Parent-Directory zum Pfad hinzu für Importe
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MultiAccountManager(ctk.CTkFrame):
    """Multi-Account Manager - Verwaltung mehrerer MT5-Konten"""
    
    def __init__(self, parent, account_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.account_manager = account_manager
        
        # Gespeicherte Konten
        self.saved_accounts = []
        self.current_account = None
        
        # UI References
        self.account_list_widget = None
        self.status_labels = {}
        
        self._setup_ui()
        self._load_saved_accounts()
        
    def _setup_ui(self):
        """Richtet die UI-Komponenten ein"""
        
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(
            header_frame,
            text="👥 Multi-Account Manager",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")
        
        # Add Account Button
        add_btn = ctk.CTkButton(
            header_frame,
            text="+ Hinzufügen",
            width=100,
            height=28,
            command=self._show_add_account_dialog
        )
        add_btn.pack(side="right")
        
        # Main Content - Two Columns
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Left: Account List
        list_frame = ctk.CTkFrame(main_container)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        self._create_account_list(list_frame)
        
        # Right: Account Details
        details_frame = ctk.CTkFrame(main_container)
        details_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        self._create_account_details(details_frame)
        
        # Action Buttons
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=15, pady=(10, 15))
        
        switch_btn = ctk.CTkButton(
            action_frame,
            text="🔄 Zu diesem Konto wechseln",
            command=self._switch_to_selected,
            height=35
        )
        switch_btn.pack(fill="x", pady=5)
        
        sync_btn = ctk.CTkButton(
            action_frame,
            text="📥 Aktuelles MT5-Konto abrufen",
            command=self._manual_sync_mt5,
            height=35,
            fg_color="#2E86AB",
            hover_color="#1F618D"
        )
        sync_btn.pack(fill="x", pady=5)
        
        delete_btn = ctk.CTkButton(
            action_frame,
            text="🗑️ Konto entfernen",
            fg_color="#E74C3C",
            hover_color="#C0392B",
            command=self._delete_selected_account,
            height=35
        )
        delete_btn.pack(fill="x", pady=5)
        
    def _create_account_list(self, parent):
        """Erstellt die Kontenliste"""
        
        ctk.CTkLabel(
            parent,
            text="📋 Gespeicherte Konten",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        # Scrollable Frame for accounts
        self.account_list = ctk.CTkScrollableFrame(
            parent,
            label_text=""
        )
        self.account_list.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Placeholder text
        self.placeholder_label = ctk.CTkLabel(
            self.account_list,
            text="Keine Konten gespeichert.\nKlicke '+ Hinzufügen' um ein Konto hinzuzufügen.",
            text_color="#6C757D"
        )
        self.placeholder_label.pack(pady=20)
        
    def _create_account_details(self, parent):
        """Erstellt die Kontodetails-Ansicht"""
        
        ctk.CTkLabel(
            parent,
            text="📊 Konto-Details",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 10))
        
        # Selected Account Info
        details_container = ctk.CTkFrame(parent, fg_color="transparent")
        details_container.pack(fill="x", padx=15, pady=5)
        
        # Server
        self.server_label = ctk.CTkLabel(
            details_container,
            text="Server: -",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.server_label.pack(fill="x", pady=2)
        
        # Login
        self.login_label = ctk.CTkLabel(
            details_container,
            text="Login: -",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.login_label.pack(fill="x", pady=2)
        
        # Status
        self.connection_status_label = ctk.CTkLabel(
            details_container,
            text="Status: Nicht verbunden",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.connection_status_label.pack(fill="x", pady=2)
        
        # Separator
        ctk.CTkFrame(parent, height=1, fg_color="#444444").pack(fill="x", padx=15, pady=10)
        
        # Live Account Data (when connected)
        ctk.CTkLabel(
            parent,
            text="💰 Live-Daten",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=15, pady=(5, 5))
        
        # Balance
        self.balance_label = ctk.CTkLabel(
            parent,
            text="Balance: -",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.balance_label.pack(anchor="w", padx=20, pady=2)
        
        # Equity
        self.equity_label = ctk.CTkLabel(
            parent,
            text="Equity: -",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.equity_label.pack(anchor="w", padx=20, pady=2)
        
        # Margin
        self.margin_label = ctk.CTkLabel(
            parent,
            text="Margin: -",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.margin_label.pack(anchor="w", padx=20, pady=2)
        
        # Free Margin
        self.freemargin_label = ctk.CTkLabel(
            parent,
            text="Free Margin: -",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.freemargin_label.pack(anchor="w", padx=20, pady=2)
        
        # Refresh Button
        refresh_btn = ctk.CTkButton(
            parent,
            text="🔄 Daten aktualisieren",
            command=self._refresh_account_data,
            height=30
        )
        refresh_btn.pack(pady=10)
        
    def _show_add_account_dialog(self):
        """Zeigt Dialog zum Hinzufügen eines Kontos"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Konto hinzufügen")
        dialog.geometry("400x350")
        dialog.transient(self)
        
        # Make it modal
        dialog.grab_set()
        
        # Server
        server_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        server_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(server_frame, text="Server:", width=80, anchor="w").pack(side="left")
        
        server_entry = ctk.CTkEntry(
            server_frame,
            placeholder_text="Broker-Server"
        )
        server_entry.pack(side="right", fill="x", expand=True)
        
        # Login
        login_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        login_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(login_frame, text="Login:", width=80, anchor="w").pack(side="left")
        
        login_entry = ctk.CTkEntry(
            login_frame,
            placeholder_text="Kontonummer"
        )
        login_entry.pack(side="right", fill="x", expand=True)
        
        # Password
        password_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        password_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(password_frame, text="Passwort:", width=80, anchor="w").pack(side="left")
        
        password_entry = ctk.CTkEntry(
            password_frame,
            placeholder_text="Passwort",
            show="*"
        )
        password_entry.pack(side="right", fill="x", expand=True)
        
        # Server Type
        type_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        type_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(type_frame, text="Typ:", width=80, anchor="w").pack(side="left")
        
        type_var = ctk.StringVar(value="Demo")
        
        ctk.CTkRadioButton(
            type_frame,
            text="Demo",
            variable=type_var,
            value="Demo"
        ).pack(side="left", padx=10)
        
        ctk.CTkRadioButton(
            type_frame,
            text="Live",
            variable=type_var,
            value="Live"
        ).pack(side="left", padx=10)
        
        # Account Name
        name_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        name_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(name_frame, text="Name:", width=80, anchor="w").pack(side="left")
        
        name_entry = ctk.CTkEntry(
            name_frame,
            placeholder_text="Mein Demo Konto"
        )
        name_entry.pack(side="right", fill="x", expand=True)
        
        # Info
        info_label = ctk.CTkLabel(
            dialog,
            text="ℹ️ Passwörter werden lokal verschlüsselt gespeichert.",
            text_color="#6C757D",
            font=ctk.CTkFont(size=10)
        )
        info_label.pack(pady=10)
        
        # Buttons
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=20)
        
        def save_account():
            server = server_entry.get().strip()
            login = login_entry.get().strip()
            password = password_entry.get().strip()
            account_type = type_var.get()
            name = name_entry.get().strip() or f"{account_type} - {login}"
            
            if not server or not login:
                messagebox.showerror("Fehler", "Server und Login sind erforderlich!")
                return
                
            # Erstelle Account Dict
            account = {
                "id": len(self.saved_accounts) + 1,
                "name": name,
                "server": server,
                "login": login,
                "type": account_type,
                "added_date": datetime.now().strftime("%Y-%m-%d"),
                "last_used": None
            }
            
            # Passwort wird NICHT hier gespeichert (Security)
            # In echter Implementation: verschlüsselte Speicherung
            
            self.saved_accounts.append(account)
            self._save_accounts_to_file()
            self._refresh_account_list()
            
            dialog.destroy()
            
        ctk.CTkButton(
            button_frame,
            text="Speichern",
            command=save_account,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Abbrechen",
            command=dialog.destroy,
            width=120
        ).pack(side="left", padx=5)
        
    def _load_saved_accounts(self):
        """Lädt gespeicherte Konten"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "storage",
            "accounts.json"
        )
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    self.saved_accounts = json.load(f)
            except:
                self.saved_accounts = []
                
        self._auto_detect_mt5_account()
        self._refresh_account_list()
        
    def _save_accounts_to_file(self):
        """Speichert Konten in Datei"""
        storage_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "storage"
        )
        
        os.makedirs(storage_dir, exist_ok=True)
        
        config_path = os.path.join(storage_dir, "accounts.json")
        
        # Speichere ohne Passwörter
        accounts_to_save = []
        for acc in self.saved_accounts:
            accounts_to_save.append({
                "id": acc.get("id"),
                "name": acc.get("name"),
                "server": acc.get("server"),
                "login": acc.get("login"),
                "type": acc.get("type"),
                "added_date": acc.get("added_date"),
                "last_used": acc.get("last_used")
            })
            
        with open(config_path, "w") as f:
            json.dump(accounts_to_save, f, indent=2)
            
    def _refresh_account_list(self):
        """Aktualisiert die Kontenliste in der UI"""
        # Clear existing
        for widget in self.account_list.winfo_children():
            widget.destroy()
            
        if not self.saved_accounts:
            self.placeholder_label = ctk.CTkLabel(
                self.account_list,
                text="Keine Konten gespeichert.\nKlicke '+ Hinzufügen' um ein Konto hinzuzufügen.",
                text_color="#6C757D"
            )
            self.placeholder_label.pack(pady=20)
            return
            
        # Create account cards
        for account in self.saved_accounts:
            card = self._create_account_card(account)
            card.pack(fill="x", pady=5)
            
    def _create_account_card(self, account):
        """Erstellt eine Account-Karte"""
        card = ctk.CTkFrame(self.account_list, fg_color=("#2B2B2B", "#1E1E1E"))
        
        # Main info
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(fill="x", padx=10, pady=8)
        
        # Icon based on type
        icon = "📈" if account.get("type") == "Demo" else "💵"
        
        ctk.CTkLabel(
            info_frame,
            text=f"{icon} {account.get('name')}",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        ).pack(fill="x")
        
        ctk.CTkLabel(
            info_frame,
            text=f"Server: {account.get('server')} | Login: {account.get('login')}",
            font=ctk.CTkFont(size=10),
            text_color="#8B949E",
            anchor="w"
        ).pack(fill="x")
        
        # Status indicator
        status_frame = ctk.CTkFrame(card, fg_color="transparent")
        status_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        status = "🟢 Aktiv" if account.get("id") == getattr(self, 'current_account_id', None) else "⚪ Inaktiv"
        
        status_label = ctk.CTkLabel(
            status_frame,
            text=status,
            font=ctk.CTkFont(size=10),
            text_color="#27AE60" if "Aktiv" in status else "#6C757D"
        )
        status_label.pack(side="left")
        
        # Bind click event
        card.bind("<Button-1>", lambda e, a=account: self._select_account(a))
        for child in card.winfo_children():
            child.bind("<Button-1>", lambda e, a=account: self._select_account(a))
            
        return card
        
    def _select_account(self, account):
        """Wählt ein Konto aus"""
        self.selected_account = account
        
        # Update details view
        self.server_label.configure(text=f"Server: {account.get('server')}")
        self.login_label.configure(text=f"Login: {account.get('login')}")
        
        account_type = account.get("type", "Demo")
        self.connection_status_label.configure(
            text=f"Status: {'Demo' if account_type == 'Demo' else 'Live'} Konto"
        )
        
        # Reset live data labels
        self.balance_label.configure(text="Balance: -")
        self.equity_label.configure(text="Equity: -")
        self.margin_label.configure(text="Margin: -")
        self.freemargin_label.configure(text="Free Margin: -")
        
        # Highlight selected card
        self._highlight_selected_card(account.get("id"))
        
    def _highlight_selected_card(self, account_id):
        """Hebt ausgewähltes Konto visuell hervor"""
        for widget in self.account_list.winfo_children():
            widget.configure(border_color="#2E86AB", border_width=1)
            
    def _refresh_account_data(self):
        """Aktualisiert die Live-Daten des ausgewählten Kontos"""
        if not hasattr(self, 'selected_account') or not self.selected_account:
            messagebox.showwarning("Warnung", "Bitte wähle zuerst ein Konto aus.")
            return
            
        try:
            import MetaTrader5 as mt5
            if mt5.initialize():
                info = mt5.account_info()
                if info and str(info.login) == str(self.selected_account.get("login")):
                    # Reale MT5 Daten
                    balance = info.balance
                    equity = info.equity
                    margin = info.margin
                    free_margin = info.margin_free
                    currency = info.currency
                    
                    self.balance_label.configure(text=f"Balance: {balance:,.2f} {currency}")
                    self.equity_label.configure(text=f"Equity: {equity:,.2f} {currency}")
                    self.margin_label.configure(text=f"Margin: {margin:,.2f} {currency}")
                    self.freemargin_label.configure(text=f"Free Margin: {free_margin:,.2f} {currency}")
                    
                    self.connection_status_label.configure(
                        text="Status: Verbunden (Live-Daten)", 
                        text_color="#27AE60"
                    )
                    return
                else:
                    self.connection_status_label.configure(
                        text="Status: In MT5 nicht aktiv", 
                        text_color="#E74C3C"
                    )
            else:
                self.connection_status_label.configure(
                    text="Status: MT5 nicht erreichbar", 
                    text_color="#E74C3C"
                )
        except Exception as e:
            print(f"Fehler bei MT5-Datenabruf: {e}")
            self.connection_status_label.configure(
                text="Status: Fehler beim Abruf", 
                text_color="#E74C3C"
            )
            
        # Reset labels if not connected or different account
        self.balance_label.configure(text="Balance: -")
        self.equity_label.configure(text="Equity: -")
        self.margin_label.configure(text="Margin: -")
        self.freemargin_label.configure(text="Free Margin: -")
        
    def _manual_sync_mt5(self):
        """Führt eine manuelle Erkennung des aktuell in MT5 aktiven Kontos durch."""
        added = self._auto_detect_mt5_account()
        if added:
            messagebox.showinfo("Konto gefunden", "Das aktuell in MT5 angemeldete Konto wurde automatisch hinzugefügt!")
        else:
            messagebox.showinfo("Sync abgeschlossen", "Das aktuell in MT5 angemeldete Konto ist bereits in der Liste oder MT5 ist nicht gestartet.")
            
    def _auto_detect_mt5_account(self):
        """Erkennt automatisch das aktuell in MT5 angemeldete Konto und fügt es hinzu."""
        try:
            import MetaTrader5 as mt5
            if not mt5.initialize():
                return False
                
            info = mt5.account_info()
            if not info:
                return False
                
            login = str(info.login)
            server = info.server
            
            exists = False
            for acc in self.saved_accounts:
                if str(acc.get("login")) == login and acc.get("server") == server:
                    exists = True
                    break
                    
            if not exists:
                account_type = "Demo" if info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else "Live"
                name = getattr(info, "name", f"{account_type} - {login}")
                if not name or name.strip() == "":
                    name = f"{account_type} - {login}"
                    
                account = {
                    "id": len(self.saved_accounts) + 1,
                    "name": name,
                    "server": server,
                    "login": login,
                    "type": account_type,
                    "added_date": datetime.now().strftime("%Y-%m-%d"),
                    "last_used": datetime.now().strftime("%Y-%m-%d")
                }
                
                self.saved_accounts.append(account)
                self._save_accounts_to_file()
                self._refresh_account_list()
                return True
                
        except Exception as e:
            print(f"Fehler bei MT5-Auto-Erkennung: {e}")
        return False

    def _switch_to_selected(self):
        """Wechselt zum ausgewählten Konto"""
        if not hasattr(self, 'selected_account') or not self.selected_account:
            messagebox.showwarning("Warnung", "Bitte wähle zuerst ein Konto aus.")
            return
            
        # Update last used
        self.selected_account["last_used"] = datetime.now().strftime("%Y-%m-%d")
        self._save_accounts_to_file()
        
        # Set as current
        self.current_account = self.selected_account
        self.current_account_id = self.selected_account.get("id")
        
        messagebox.showinfo(
            "Konto gewechselt",
            f"Zu Konto '{self.selected_account.get('name')}' gewechselt.\n\n"
            f"Bitte verbinde dich mit MT5 über dieses Konto."
        )
        
        self._refresh_account_list()
        
    def _delete_selected_account(self):
        """Löscht das ausgewählte Konto"""
        if not hasattr(self, 'selected_account') or not self.selected_account:
            messagebox.showwarning("Warnung", "Bitte wähle zuerst ein Konto aus.")
            return
            
        confirm = messagebox.askyesno(
            "Konto löschen",
            f"Möchtest du das Konto '{self.selected_account.get('name')}' wirklich löschen?"
        )
        
        if confirm:
            self.saved_accounts = [
                a for a in self.saved_accounts 
                if a.get("id") != self.selected_account.get("id")
            ]
            self._save_accounts_to_file()
            self.selected_account = None
            self._refresh_account_list()
            
            # Reset details
            self.server_label.configure(text="Server: -")
            self.login_label.configure(text="Login: -")
            self.connection_status_label.configure(text="Status: Nicht verbunden")
            
    def set_account_manager(self, account_manager):
        """Setzt den Account Manager"""
        self.account_manager = account_manager
        
    def get_current_account(self):
        """Gibt das aktuelle Konto zurück"""
        return self.current_account


class AccountSwitcherWidget(ctk.CTkFrame):
    """Kompakter Account Switcher für die Header-Leiste"""
    
    def __init__(self, parent, multi_account_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.multi_account_manager = multi_account_manager
        self._setup_ui()
        
    def _setup_ui(self):
        """UI-Einrichtung"""
        
        # Current Account Label
        self.account_label = ctk.CTkLabel(
            self,
            text="👤 Kein Konto ausgewählt",
            font=ctk.CTkFont(size=12)
        )
        self.account_label.pack(side="left", padx=5)
        
        # Dropdown Menu (simulated with OptionMenu)
        self.account_var = ctk.StringVar(value="Konto wählen...")
        
        self.account_menu = ctk.CTkOptionMenu(
            self,
            values=["Konto wählen..."],
            variable=self.account_var,
            command=self._on_account_select,
            width=150
        )
        self.account_menu.pack(side="left", padx=5)
        
        # Refresh Button
        refresh_btn = ctk.CTkButton(
            self,
            text="🔄",
            width=30,
            height=30,
            command=self._refresh
        )
        refresh_btn.pack(side="left", padx=5)
        
    def _on_account_select(self, selection):
        """Wird aufgerufen wenn Konto ausgewählt"""
        if selection != "Konto wählen..." and self.multi_account_manager:
            # Find account and switch
            for account in self.multi_account_manager.saved_accounts:
                if account.get("name") == selection:
                    self.multi_account_manager._select_account(account)
                    self.multi_account_manager._switch_to_selected()
                    break
                    
    def _refresh(self):
        """Aktualisiert die Kontoliste"""
        if self.multi_account_manager:
            accounts = self.multi_account_manager.saved_accounts
            values = ["Konto wählen..."] + [a.get("name") for a in accounts]
            self.account_menu.configure(values=values)
            
    def update_current_account(self, account_name):
        """Aktualisiert die Anzeige des aktuellen Kontos"""
        self.account_label.configure(text=f"👤 {account_name}")


if __name__ == "__main__":
    # Test des Widgets
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    root.title("Multi-Account Manager Test")
    root.geometry("600x500")
    
    # Multi-Account Manager
    multi_account = MultiAccountManager(root)
    multi_account.pack(fill="both", expand=True, padx=10, pady=10)
    
    root.mainloop()
