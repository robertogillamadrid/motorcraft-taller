"""
MotorCraft — GUI (English DB, PyCharm compatible)
==================================================
Requirements:
  pip install customtkinter matplotlib pillow requests

Usage:
  1. Make sure app_EN.py is running (python app_EN.py)
  2. Run this file: python gui_EN.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
matplotlib.use("TkAgg")

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
API_URL = "http://localhost:5000/api"
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLOR_PRIMARY = "#1f538d"
COLOR_SUCCESS = "#2d936c"
COLOR_WARNING = "#e8a838"
COLOR_DANGER  = "#c0392b"
COLOR_BG      = "#1a1a2e"
COLOR_CARD    = "#16213e"
COLOR_TEXT    = "#e0e0e0"


# ─────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────

import threading

def api_get(endpoint, params=None):
    try:
        r = requests.get(f"{API_URL}{endpoint}", params=params, timeout=10)
        data = r.json()
        return data["data"] if data.get("ok") else []
    except Exception as e:
        messagebox.showerror("Connection Error", f"Could not connect to API.\n{e}")
        return []


def api_post(endpoint, body):
    try:
        r = requests.post(f"{API_URL}{endpoint}", json=body, timeout=10)
        return r.json()
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return {"ok": False, "error": str(e)}


def api_put(endpoint, body):
    try:
        r = requests.put(f"{API_URL}{endpoint}", json=body, timeout=10)
        return r.json()
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return {"ok": False, "error": str(e)}


def run_in_thread(func, *args, callback=None, **kwargs):
    def worker():
        result = func(*args, **kwargs)
        if callback:
            callback(result)
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

# ─────────────────────────────────────────────
# FORM: New Client
# ─────────────────────────────────────────────
class FormNewClient(ctk.CTkToplevel):
    def __init__(self, parent, callback=None):
        super().__init__(parent)
        self.title("New Client")
        self.geometry("420x480")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_CARD)
        self.grab_set()
        self.callback = callback

        ctk.CTkLabel(self, text="New Client",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLOR_TEXT).pack(pady=(24, 16))

        fields = [
            ("First Name *",  "first_name"),
            ("Last Name *",   "last_name"),
            ("Phone",         "phone"),
            ("Email",         "email"),
            ("Address",       "address"),
        ]
        self.vars = {}
        for label, key in fields:
            ctk.CTkLabel(self, text=label, text_color=COLOR_TEXT,
                         anchor="w").pack(fill="x", padx=32, pady=(6, 0))
            var = ctk.StringVar()
            ctk.CTkEntry(self, textvariable=var, width=356).pack(padx=32)
            self.vars[key] = var

        ctk.CTkButton(
            self, text="Save Client",
            fg_color=COLOR_SUCCESS,
            hover_color="#1e6b4a",
            command=self._save,
            height=40,
        ).pack(pady=24, padx=32, fill="x")

    def _save(self):
        body = {k: v.get().strip() for k, v in self.vars.items()}
        if not body["first_name"] or not body["last_name"]:
            messagebox.showwarning("Required Fields", "First name and last name are required.")
            return
        resp = api_post("/clients", body)
        if resp.get("ok"):
            messagebox.showinfo("Success", f"Client created with ID {resp['data']['client_id']}")
            if self.callback:
                self.callback()
            self.destroy()
        else:
            messagebox.showerror("Error", resp.get("error", "Unknown error"))


# ─────────────────────────────────────────────
# FORM: New Work Order
# ─────────────────────────────────────────────
class FormNewOrder(ctk.CTkToplevel):
    def __init__(self, parent, callback=None):
        super().__init__(parent)
        self.title("New Work Order")
        self.geometry("440x420")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_CARD)
        self.grab_set()
        self.callback = callback

        ctk.CTkLabel(self, text="New Work Order",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLOR_TEXT).pack(pady=(24, 16))

        # Vehicle by plate
        ctk.CTkLabel(self, text="Vehicle Plate *",
                     text_color=COLOR_TEXT, anchor="w").pack(fill="x", padx=32, pady=(6, 0))
        self.plate_var = ctk.StringVar()
        plate_frame = ctk.CTkFrame(self, fg_color="transparent")
        plate_frame.pack(fill="x", padx=32)
        ctk.CTkEntry(plate_frame, textvariable=self.plate_var, width=240).pack(side="left")
        ctk.CTkButton(plate_frame, text="Search", width=80,
                      fg_color=COLOR_PRIMARY,
                      command=self._search_vehicle).pack(side="left", padx=8)

        self.lbl_vehicle = ctk.CTkLabel(self, text="", text_color="#aaaaaa",
                                         font=ctk.CTkFont(size=12))
        self.lbl_vehicle.pack(pady=(4, 0))
        self.vehicle_id = None

        # Mechanic — loads from /api/employees
        ctk.CTkLabel(self, text="Mechanic *",
                     text_color=COLOR_TEXT, anchor="w").pack(fill="x", padx=32, pady=(12, 0))
        self.employees_data = self._load_employees()
        emp_names = [f"{e['employee_id']} — {e['first_name']} {e['last_name']}"
                     for e in self.employees_data]
        self.emp_var = ctk.StringVar(value=emp_names[0] if emp_names else "")
        ctk.CTkOptionMenu(self, values=emp_names if emp_names else ["No employees found"],
                          variable=self.emp_var,
                          width=356).pack(padx=32)

        # Notes
        ctk.CTkLabel(self, text="Notes",
                     text_color=COLOR_TEXT, anchor="w").pack(fill="x", padx=32, pady=(12, 0))
        self.notes_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.notes_var, width=356).pack(padx=32)

        ctk.CTkButton(
            self, text="Create Order",
            fg_color=COLOR_SUCCESS,
            hover_color="#1e6b4a",
            command=self._save,
            height=40,
        ).pack(pady=24, padx=32, fill="x")

    def _load_employees(self):
        """Load active employees from /api/employees"""
        try:
            r = requests.get(f"{API_URL}/employees", timeout=5)
            if r.status_code == 200:
                data = r.json()
                return data.get("data", [])
        except Exception:
            pass
        # Fallback
        return [
            {"employee_id": 1, "first_name": "Carlos",  "last_name": "Mendoza"},
            {"employee_id": 2, "first_name": "Jorge",   "last_name": "Ramirez"},
            {"employee_id": 3, "first_name": "Luis",    "last_name": "Perez"},
            {"employee_id": 4, "first_name": "Ana",     "last_name": "Garcia"},
        ]

    def _search_vehicle(self):
        plate = self.plate_var.get().strip().upper()
        if not plate:
            messagebox.showwarning("Plate Required", "Enter the vehicle plate.")
            return
        try:
            r = requests.get(f"{API_URL}/vehicles/{plate}", timeout=5)
            data = r.json()
            if data.get("ok"):
                v = data["data"]
                self.vehicle_id = v["vehicle_id"]
                self.lbl_vehicle.configure(
                    text=f"✓ {v['make']} {v['model']} {v['year']} — {v.get('owner', '')}",
                    text_color=COLOR_SUCCESS
                )
            else:
                self.vehicle_id = None
                self.lbl_vehicle.configure(
                    text="✗ Vehicle not found",
                    text_color=COLOR_DANGER
                )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _save(self):
        if not self.vehicle_id:
            messagebox.showwarning("Vehicle Required", "Search and select a vehicle first.")
            return
        sel = self.emp_var.get()
        try:
            emp_id = int(sel.split("—")[0].strip())
        except (ValueError, IndexError):
            messagebox.showwarning("Error", "Select a valid mechanic.")
            return
        body = {
            "vehicle_id":  self.vehicle_id,
            "employee_id": emp_id,
            "notes":       self.notes_var.get().strip(),
        }
        resp = api_post("/orders", body)
        if resp.get("ok"):
            messagebox.showinfo("Success", f"Order created with ID {resp['data']['order_id']}")
            if self.callback:
                self.callback()
            self.destroy()
        else:
            messagebox.showerror("Error", resp.get("error", "Unknown error"))


# ─────────────────────────────────────────────
# FORM: Update Order Status
# ─────────────────────────────────────────────
class FormUpdateStatus(ctk.CTkToplevel):
    def __init__(self, parent, order_id, current_status, callback=None):
        super().__init__(parent)
        self.title(f"Update Order #{order_id}")
        self.geometry("360x280")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_CARD)
        self.grab_set()
        self.order_id = order_id
        self.callback = callback

        ctk.CTkLabel(self, text=f"Order #{order_id}",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLOR_TEXT).pack(pady=(24, 4))

        ctk.CTkLabel(self, text=f"Current status: {current_status}",
                     text_color="#aaaaaa").pack(pady=(0, 20))

        ctk.CTkLabel(self, text="New Status *",
                     text_color=COLOR_TEXT, anchor="w").pack(fill="x", padx=32)

        self.status_var = ctk.StringVar(value="IN_PROGRESS")
        ctk.CTkOptionMenu(
            self,
            values=["RECEIVED", "IN_PROGRESS", "READY", "DELIVERED", "CANCELLED"],
            variable=self.status_var,
            width=296,
        ).pack(padx=32, pady=8)

        ctk.CTkButton(
            self, text="Update",
            fg_color=COLOR_WARNING,
            text_color="#1a1a1a",
            hover_color="#b07820",
            command=self._save,
            height=40,
        ).pack(pady=20, padx=32, fill="x")

    def _save(self):
        resp = api_put(f"/orders/{self.order_id}/status",
                       {"status": self.status_var.get()})
        if resp.get("ok"):
            messagebox.showinfo("Success", f"Order #{self.order_id} updated.")
            if self.callback:
                self.callback()
            self.destroy()
        else:
            messagebox.showerror("Error", resp.get("error", "Unknown error"))


# ─────────────────────────────────────────────
# FORM: Register Payment
# ─────────────────────────────────────────────
class FormRegisterPayment(ctk.CTkToplevel):
    def __init__(self, parent, invoice_id, balance, callback=None):
        super().__init__(parent)
        self.title(f"Register Payment — Invoice #{invoice_id}")
        self.geometry("380x320")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_CARD)
        self.grab_set()
        self.invoice_id = invoice_id
        self.callback   = callback

        ctk.CTkLabel(self, text=f"Invoice #{invoice_id}",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLOR_TEXT).pack(pady=(24, 4))

        ctk.CTkLabel(self, text=f"Balance: ${balance:,.2f}",
                     text_color=COLOR_WARNING,
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(0, 16))

        ctk.CTkLabel(self, text="Amount to Pay *",
                     text_color=COLOR_TEXT, anchor="w").pack(fill="x", padx=32)
        self.amount_var = ctk.StringVar(value=str(balance))
        ctk.CTkEntry(self, textvariable=self.amount_var, width=316).pack(padx=32, pady=(4, 12))

        ctk.CTkLabel(self, text="Payment Method *",
                     text_color=COLOR_TEXT, anchor="w").pack(fill="x", padx=32)
        self.method_var = ctk.StringVar(value="CASH")
        ctk.CTkOptionMenu(
            self,
            values=["CASH", "CARD", "TRANSFER", "CHECK"],
            variable=self.method_var,
            width=316,
        ).pack(padx=32, pady=(4, 16))

        ctk.CTkButton(
            self, text="Register Payment",
            fg_color=COLOR_SUCCESS,
            hover_color="#1e6b4a",
            command=self._save,
            height=40,
        ).pack(padx=32, fill="x")

    def _save(self):
        try:
            amount = float(self.amount_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Amount", "Enter a valid number.")
            return
        resp = api_post("/payments", {
            "invoice_id":     self.invoice_id,
            "amount":         amount,
            "payment_method": self.method_var.get(),
        })
        if resp.get("ok"):
            messagebox.showinfo("Success", "Payment registered successfully.")
            if self.callback:
                self.callback()
            self.destroy()
        else:
            messagebox.showerror("Error", resp.get("error", "Unknown error"))


# ─────────────────────────────────────────────
# Main Application Window
# ─────────────────────────────────────────────
class MotorCraftApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MotorCraft — Management System")
        self.geometry("1200x700")
        self.minsize(1000, 600)
        self.configure(fg_color=COLOR_BG)
        self._build_sidebar()
        self._build_main()
        self.show_orders()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=COLOR_CARD, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="⚙ MotorCraft",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=COLOR_TEXT).pack(pady=(30, 5))

        ctk.CTkLabel(self.sidebar, text="Management System",
                     font=ctk.CTkFont(size=12),
                     text_color="#888888").pack(pady=(0, 30))

        buttons = [
            ("🗂  Active Orders",         self.show_orders),
            ("👤  Clients",               self.show_clients),
            ("📦  Inventory",             self.show_inventory),
            ("📊  Reports",               self.show_reports),
            ("💰  Accounts Receivable",   self.show_accounts),
            ("📋  Audit Log",             self.show_audit),
        ]

        for text, command in buttons:
            ctk.CTkButton(
                self.sidebar, text=text, command=command,
                fg_color="transparent", hover_color=COLOR_PRIMARY,
                anchor="w", font=ctk.CTkFont(size=13),
                height=42, corner_radius=8,
            ).pack(fill="x", padx=12, pady=3)

        ctk.CTkLabel(self.sidebar, text="v1.0 — Tijuana, B.C.",
                     font=ctk.CTkFont(size=10),
                     text_color="#555555").pack(side="bottom", pady=16)

    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.main.pack(side="right", fill="both", expand=True)

        self.header = ctk.CTkFrame(self.main, fg_color=COLOR_CARD, height=60, corner_radius=0)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        self.title_label = ctk.CTkLabel(
            self.header, text="Active Orders",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXT)
        self.title_label.pack(side="left", padx=24, pady=15)

        self.btn_refresh = ctk.CTkButton(
            self.header, text="↻ Refresh", width=110,
            fg_color=COLOR_PRIMARY, command=self._refresh)
        self.btn_refresh.pack(side="right", padx=16, pady=12)

        self.content = ctk.CTkFrame(self.main, fg_color=COLOR_BG)
        self.content.pack(fill="both", expand=True, padx=16, pady=16)
        self._current_view = None

    def _clear(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _refresh(self):
        if self._current_view:
            self._current_view()

    def _set_title(self, text):
        self.title_label.configure(text=text)

    def _table(self, parent, columns, data, widths=None):
        frame = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=10)
        frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("MC.Treeview",
            background="#1e1e2e", foreground=COLOR_TEXT,
            rowheight=28, fieldbackground="#1e1e2e",
            borderwidth=0, font=("Segoe UI", 11))
        style.configure("MC.Treeview.Heading",
            background=COLOR_PRIMARY, foreground="white",
            font=("Segoe UI", 11, "bold"), relief="flat")
        style.map("MC.Treeview", background=[("selected", COLOR_PRIMARY)])

        tree = ttk.Treeview(frame, columns=columns, show="headings", style="MC.Treeview")
        for i, col in enumerate(columns):
            w = widths[i] if widths else 130
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="w")

        for row in data:
            values = [str(row.get(c, "")) for c in columns]
            tree.insert("", "end", values=values)

        sb_y = ttk.Scrollbar(frame, orient="vertical",   command=tree.yview)
        sb_x = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.pack(side="right", fill="y")
        sb_x.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        return tree

    # ── VIEW 1: Work Orders ───────────────────
    def show_orders(self):
        self._current_view = self.show_orders
        self._set_title("Active Work Orders")
        self._clear()

        acc = ctk.CTkFrame(self.content, fg_color="transparent")
        acc.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(acc, text="+ New Order",
                      fg_color=COLOR_SUCCESS, hover_color="#1e6b4a",
                      command=self._form_new_order).pack(side="left", padx=(0, 8))

        ctk.CTkButton(acc, text="✏ Change Status",
                      fg_color=COLOR_WARNING, text_color="#1a1a1a",
                      command=self._form_status).pack(side="left", padx=(0, 16))

        self.filter_var = ctk.StringVar(value="ALL")
        for op in ["ALL", "RECEIVED", "IN_PROGRESS", "READY"]:
            ctk.CTkRadioButton(acc, text=op, variable=self.filter_var,
                               value=op, command=self._load_orders,
                               text_color=COLOR_TEXT).pack(side="left", padx=6)

        self._frame_orders = ctk.CTkFrame(self.content, fg_color="transparent")
        self._frame_orders.pack(fill="both", expand=True)
        self._load_orders()

    def _load_orders(self):
        for w in self._frame_orders.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._frame_orders, text="Loading...",
                     font=ctk.CTkFont(size=14), text_color="#888888").pack(expand=True)

        def on_data(data):
            for w in self._frame_orders.winfo_children():
                w.destroy()
            status = self.filter_var.get()
            if status != "ALL":
                data = [d for d in data if d.get("status") == status]
            if not data:
                ctk.CTkLabel(self._frame_orders, text="No active orders",
                             font=ctk.CTkFont(size=14), text_color="#888888").pack(expand=True)
                return
            cols = ["order_id", "client", "vehicle", "plate", "mechanic", "status", "entry_date"]
            widths = [70, 160, 130, 80, 140, 110, 150]
            self._tree_orders = self._table(self._frame_orders, cols, data, widths)
            self._orders_data = data

        run_in_thread(api_get, "/orders", callback=on_data)
    def _form_new_order(self):
        FormNewOrder(self, callback=self._load_orders)

    def _form_status(self):
        if not hasattr(self, "_tree_orders"):
            messagebox.showinfo("Select an order", "Load orders first.")
            return
        sel = self._tree_orders.selection()
        if not sel:
            messagebox.showinfo("Select an order", "Click on an order in the table.")
            return
        values   = self._tree_orders.item(sel[0])["values"]
        order_id = values[0]
        status   = values[5]
        FormUpdateStatus(self, order_id, status, callback=self._load_orders)

    # ── VIEW 2: Clients ───────────────────────
    def show_clients(self):
        self._current_view = self.show_clients
        self._set_title("Clients")
        self._clear()

        acc = ctk.CTkFrame(self.content, fg_color="transparent")
        acc.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(acc, text="+ New Client",
                      fg_color=COLOR_SUCCESS, hover_color="#1e6b4a",
                      command=self._form_new_client).pack(side="left", padx=(0, 16))

        self.search_var = ctk.StringVar()
        ctk.CTkEntry(acc, textvariable=self.search_var,
                     placeholder_text="Search by name...",
                     width=240).pack(side="left", padx=(0, 8))
        ctk.CTkButton(acc, text="Search", width=80,
                      fg_color=COLOR_PRIMARY,
                      command=self._search_clients).pack(side="left")
        ctk.CTkButton(acc, text="View All", width=90,
                      fg_color="#444466",
                      command=self._load_clients).pack(side="left", padx=8)

        self._frame_clients = ctk.CTkFrame(self.content, fg_color="transparent")
        self._frame_clients.pack(fill="both", expand=True)
        self._load_clients()

    def _load_clients(self):
        for w in self._frame_clients.winfo_children():
            w.destroy()
        data   = api_get("/clients")
        cols   = ["client_id", "first_name", "last_name", "phone", "email", "registration_date"]
        widths = [80, 130, 130, 120, 200, 160]
        self._table(self._frame_clients, cols, data, widths)

    def _search_clients(self):
        term = self.search_var.get().lower()
        for w in self._frame_clients.winfo_children():
            w.destroy()
        data = api_get("/clients")
        filtered = [d for d in data
                    if term in d.get("first_name", "").lower()
                    or term in d.get("last_name", "").lower()]
        cols   = ["client_id", "first_name", "last_name", "phone", "email", "registration_date"]
        widths = [80, 130, 130, 120, 200, 160]
        self._table(self._frame_clients, cols, filtered, widths)

    def _form_new_client(self):
        FormNewClient(self, callback=self._load_clients)

    # ── VIEW 3: Inventory ─────────────────────
    def show_inventory(self):
        self._current_view = self.show_inventory
        self._set_title("Parts Inventory (MongoDB)")
        self._clear()

        btn_f = ctk.CTkFrame(self.content, fg_color="transparent")
        btn_f.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(btn_f, text="View All", width=110,
                      fg_color=COLOR_PRIMARY,
                      command=self._load_inventory).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_f, text="⚠ Low Stock", width=120,
                      fg_color=COLOR_WARNING, text_color="#1a1a1a",
                      command=self._load_low_stock).pack(side="left")

        self._frame_inv = ctk.CTkFrame(self.content, fg_color="transparent")
        self._frame_inv.pack(fill="both", expand=True)
        self._load_inventory()

    def _load_inventory(self):
        for w in self._frame_inv.winfo_children():
            w.destroy()
        data   = api_get("/inventory")
        cols   = ["code", "name", "category", "brand", "stock", "min_stock", "unit_price"]
        widths = [120, 220, 100, 110, 60, 90, 110]
        self._table(self._frame_inv, cols, data, widths)

    def _load_low_stock(self):
        for w in self._frame_inv.winfo_children():
            w.destroy()
        data = api_get("/inventory/low-stock")
        if not data:
            ctk.CTkLabel(self._frame_inv,
                         text="✓ All inventory is above minimum",
                         font=ctk.CTkFont(size=14),
                         text_color=COLOR_SUCCESS).pack(expand=True)
            return
        cols   = ["code", "name", "category", "stock", "min_stock"]
        widths = [120, 240, 120, 70, 100]
        self._table(self._frame_inv, cols, data, widths)

    # ── VIEW 4: Reports ───────────────────────
    def show_reports(self):
        self._current_view = self.show_reports
        self._set_title("Reports & Charts")
        self._clear()

        tabs = ctk.CTkTabview(self.content, fg_color=COLOR_CARD)
        tabs.pack(fill="both", expand=True)
        tabs.add("Top Services")
        tabs.add("Revenue by Period")

        self._chart_services(tabs.tab("Top Services"))
        self._chart_revenue(tabs.tab("Revenue by Period"))

    def _chart_services(self, parent):
        data = api_get("/reports/top-services", {"limit": 7})
        if not data:
            ctk.CTkLabel(parent, text="No data available", text_color=COLOR_TEXT).pack(expand=True)
            return
        names   = [d["service_name"][:22] for d in data]
        revenue = [d["total_revenue"] for d in data]

        fig, ax = plt.subplots(figsize=(9, 4))
        fig.patch.set_facecolor("#1e1e2e")
        ax.set_facecolor("#1e1e2e")
        bars = ax.barh(names, revenue, color=COLOR_PRIMARY)
        ax.set_title("Total Revenue by Service ($)", color=COLOR_TEXT, fontsize=12)
        ax.tick_params(colors=COLOR_TEXT)
        ax.spines[:].set_color("#333355")
        for bar, val in zip(bars, revenue):
            ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height()/2,
                    f"${val:,.0f}", va="center", color=COLOR_TEXT, fontsize=9)
        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

    def _chart_revenue(self, parent):
        filter_f = ctk.CTkFrame(parent, fg_color="transparent")
        filter_f.pack(fill="x", padx=8, pady=8)

        ctk.CTkLabel(filter_f, text="From:", text_color=COLOR_TEXT).pack(side="left")
        self.from_var = ctk.StringVar(value="2025-01-01")
        ctk.CTkEntry(filter_f, textvariable=self.from_var, width=110).pack(side="left", padx=4)

        ctk.CTkLabel(filter_f, text="To:", text_color=COLOR_TEXT).pack(side="left", padx=(8, 0))
        self.to_var = ctk.StringVar(value="2025-12-31")
        ctk.CTkEntry(filter_f, textvariable=self.to_var, width=110).pack(side="left", padx=4)

        self._frame_rev = ctk.CTkFrame(parent, fg_color="transparent")
        self._frame_rev.pack(fill="both", expand=True)

        ctk.CTkButton(filter_f, text="Generate", width=90,
                      fg_color=COLOR_PRIMARY,
                      command=self._update_revenue).pack(side="left", padx=8)
        self._update_revenue()

    def _update_revenue(self):
        for w in self._frame_rev.winfo_children():
            w.destroy()
        data = api_get("/reports/revenue", {
            "from": self.from_var.get(),
            "to":   self.to_var.get(),
        })
        if not data:
            ctk.CTkLabel(self._frame_rev, text="No data for that period",
                         text_color="#888888").pack(expand=True)
            return
        dates  = [d["report_date"][:10] for d in data]
        totals = [d["collected"] for d in data]

        fig, ax = plt.subplots(figsize=(9, 3.5))
        fig.patch.set_facecolor("#1e1e2e")
        ax.set_facecolor("#1e1e2e")
        ax.plot(dates, totals, marker="o", color=COLOR_PRIMARY, linewidth=2)
        ax.fill_between(range(len(dates)), totals, alpha=0.15, color=COLOR_PRIMARY)
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(dates, rotation=30, ha="right", color=COLOR_TEXT, fontsize=9)
        ax.tick_params(colors=COLOR_TEXT)
        ax.spines[:].set_color("#333355")
        ax.set_title("Daily Revenue ($)", color=COLOR_TEXT)
        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self._frame_rev)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

    # ── VIEW 5: Accounts Receivable ───────────
    def show_accounts(self):
        self._current_view = self.show_accounts
        self._set_title("Accounts Receivable")
        self._clear()

        acc = ctk.CTkFrame(self.content, fg_color="transparent")
        acc.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(acc, text="💳 Register Payment",
                      fg_color=COLOR_SUCCESS, hover_color="#1e6b4a",
                      command=self._form_payment).pack(side="left")

        self._frame_accounts = ctk.CTkFrame(self.content, fg_color="transparent")
        self._frame_accounts.pack(fill="both", expand=True)
        self._load_accounts()

    def _load_accounts(self):
        for w in self._frame_accounts.winfo_children():
            w.destroy()
        data = api_get("/reports/accounts-receivable")
        if not data:
            ctk.CTkLabel(self._frame_accounts,
                         text="✓ No pending accounts",
                         font=ctk.CTkFont(size=16),
                         text_color=COLOR_SUCCESS).pack(expand=True)
            return
        cols   = ["invoice_id","client","vehicle","total","paid","outstanding_balance","days_unpaid","payment_status"]
        widths = [80, 150, 130, 80, 80, 120, 100, 100]
        self._tree_accounts = self._table(self._frame_accounts, cols, data, widths)
        self._accounts_data = data

    def _form_payment(self):
        if not hasattr(self, "_tree_accounts"):
            messagebox.showinfo("Select an invoice", "Load accounts receivable first.")
            return
        sel = self._tree_accounts.selection()
        if not sel:
            messagebox.showinfo("Select an invoice", "Click on an invoice in the table.")
            return
        values     = self._tree_accounts.item(sel[0])["values"]
        invoice_id = values[0]
        balance    = float(str(values[5]).replace(",", ""))
        FormRegisterPayment(self, invoice_id, balance, callback=self._load_accounts)

    # ── VIEW 6: Audit Log ─────────────────────
    def show_audit(self):
        self._current_view = self.show_audit
        self._set_title("Audit Log — Last 100 Events")
        self._clear()
        data = api_get("/audit-log")
        if not data:
            ctk.CTkLabel(self.content,
                         text="No events recorded yet",
                         font=ctk.CTkFont(size=14),
                         text_color="#888888").pack(expand=True)
            return
        cols   = ["log_id","log_timestamp","user","affected_table","action"]
        widths = [60, 160, 120, 150, 80]
        self._table(self.content, cols, data, widths)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = MotorCraftApp()
    app.mainloop()
