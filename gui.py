"""
MotorCraft — Fase 6: Interfaz Gráfica (GUI) con formularios
============================================================
Requiere:
  pip install customtkinter matplotlib pillow requests

Uso:
  python gui.py
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
# Configuración
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
# Utilidades API
# ─────────────────────────────────────────────
def api_get(endpoint, params=None):
    try:
        r = requests.get(f"{API_URL}{endpoint}", params=params, timeout=5)
        data = r.json()
        return data["data"] if data.get("ok") else []
    except Exception as e:
        messagebox.showerror("Error de conexión", f"No se pudo conectar a la API.\n{e}")
        return []


def api_post(endpoint, body):
    try:
        r = requests.post(f"{API_URL}{endpoint}", json=body, timeout=5)
        return r.json()
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return {"ok": False, "error": str(e)}


def api_put(endpoint, body):
    try:
        r = requests.put(f"{API_URL}{endpoint}", json=body, timeout=5)
        return r.json()
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return {"ok": False, "error": str(e)}


# ─────────────────────────────────────────────
# FORMULARIO: Nuevo cliente
# ─────────────────────────────────────────────
class FormNuevoCliente(ctk.CTkToplevel):
    def __init__(self, parent, callback=None):
        super().__init__(parent)
        self.title("Nuevo cliente")
        self.geometry("420x460")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_CARD)
        self.grab_set()
        self.callback = callback

        ctk.CTkLabel(self, text="Nuevo cliente",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLOR_TEXT).pack(pady=(24, 16))

        campos = [
            ("Nombre *",    "nombre"),
            ("Apellido *",  "apellido"),
            ("Teléfono",    "telefono"),
            ("Email",       "email"),
            ("Dirección",   "direccion"),
        ]
        self.vars = {}
        for label, key in campos:
            ctk.CTkLabel(self, text=label, text_color=COLOR_TEXT,
                         anchor="w").pack(fill="x", padx=32, pady=(6, 0))
            var = ctk.StringVar()
            ctk.CTkEntry(self, textvariable=var, width=356).pack(padx=32)
            self.vars[key] = var

        ctk.CTkButton(
            self, text="Guardar cliente",
            fg_color=COLOR_SUCCESS,
            hover_color="#1e6b4a",
            command=self._guardar,
            height=40,
        ).pack(pady=24, padx=32, fill="x")

    def _guardar(self):
        body = {k: v.get().strip() for k, v in self.vars.items()}
        if not body["nombre"] or not body["apellido"]:
            messagebox.showwarning("Campos requeridos", "Nombre y apellido son obligatorios.")
            return
        resp = api_post("/clientes", body)
        if resp.get("ok"):
            messagebox.showinfo("Éxito", f"Cliente creado con ID {resp['data']['id_cliente']}")
            if self.callback:
                self.callback()
            self.destroy()
        else:
            messagebox.showerror("Error", resp.get("error", "Error desconocido"))


# ─────────────────────────────────────────────
# FORMULARIO: Nueva orden de trabajo
# ─────────────────────────────────────────────
class FormNuevaOrden(ctk.CTkToplevel):
    def __init__(self, parent, callback=None):
        super().__init__(parent)
        self.title("Nueva orden de trabajo")
        self.geometry("440x400")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_CARD)
        self.grab_set()
        self.callback = callback

        ctk.CTkLabel(self, text="Nueva orden de trabajo",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLOR_TEXT).pack(pady=(24, 16))

        # Vehículo por placa
        ctk.CTkLabel(self, text="Placa del vehículo *",
                     text_color=COLOR_TEXT, anchor="w").pack(fill="x", padx=32, pady=(6, 0))
        self.placa_var = ctk.StringVar()
        placa_frame = ctk.CTkFrame(self, fg_color="transparent")
        placa_frame.pack(fill="x", padx=32)
        ctk.CTkEntry(placa_frame, textvariable=self.placa_var, width=240).pack(side="left")
        ctk.CTkButton(placa_frame, text="Buscar", width=80,
                      fg_color=COLOR_PRIMARY,
                      command=self._buscar_vehiculo).pack(side="left", padx=8)

        self.lbl_vehiculo = ctk.CTkLabel(self, text="", text_color="#aaaaaa",
                                          font=ctk.CTkFont(size=12))
        self.lbl_vehiculo.pack(pady=(4, 0))
        self.id_vehiculo = None

        # Mecánico
        ctk.CTkLabel(self, text="Mecánico *",
                     text_color=COLOR_TEXT, anchor="w").pack(fill="x", padx=32, pady=(12, 0))
        empleados = api_get("/clientes")
        self.empleados_data = self._cargar_empleados()
        nombres_emp = [f"{e['id_empleado']} — {e['nombre']} {e['apellido']}"
                       for e in self.empleados_data]
        self.emp_var = ctk.StringVar(value=nombres_emp[0] if nombres_emp else "")
        ctk.CTkOptionMenu(self, values=nombres_emp,
                          variable=self.emp_var,
                          width=356).pack(padx=32)

        # Observaciones
        ctk.CTkLabel(self, text="Observaciones",
                     text_color=COLOR_TEXT, anchor="w").pack(fill="x", padx=32, pady=(12, 0))
        self.obs_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.obs_var, width=356).pack(padx=32)

        ctk.CTkButton(
            self, text="Crear orden",
            fg_color=COLOR_SUCCESS,
            hover_color="#1e6b4a",
            command=self._guardar,
            height=40,
        ).pack(pady=24, padx=32, fill="x")

    def _cargar_empleados(self):
        try:
            r = requests.get(f"{API_URL}/clientes", timeout=5)
            empleados = api_get.__wrapped__ if hasattr(api_get, '__wrapped__') else None
        except:
            pass
        try:
            r = requests.get("http://localhost:5000/api/empleados", timeout=5)
            if r.status_code == 200:
                data = r.json()
                return data.get("data", [])
        except:
            pass
        return [
            {"id_empleado": 1, "nombre": "Carlos",  "apellido": "Mendoza"},
            {"id_empleado": 2, "nombre": "Jorge",   "apellido": "Ramírez"},
            {"id_empleado": 3, "nombre": "Luis",    "apellido": "Pérez"},
            {"id_empleado": 4, "nombre": "Ana",     "apellido": "García"},
        ]

    def _buscar_vehiculo(self):
        placa = self.placa_var.get().strip().upper()
        if not placa:
            messagebox.showwarning("Placa requerida", "Ingresa la placa del vehículo.")
            return
        try:
            r = requests.get(f"{API_URL}/vehiculos/{placa}", timeout=5)
            data = r.json()
            if data.get("ok"):
                v = data["data"]
                self.id_vehiculo = v["id_vehiculo"]
                self.lbl_vehiculo.configure(
                    text=f"✓ {v['marca']} {v['modelo']} {v['anio']} — {v.get('propietario','')}",
                    text_color=COLOR_SUCCESS
                )
            else:
                self.id_vehiculo = None
                self.lbl_vehiculo.configure(
                    text="✗ Vehículo no encontrado",
                    text_color=COLOR_DANGER
                )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _guardar(self):
        if not self.id_vehiculo:
            messagebox.showwarning("Vehículo requerido", "Busca y selecciona un vehículo.")
            return
        sel = self.emp_var.get()
        id_emp = int(sel.split("—")[0].strip())
        body = {
            "id_vehiculo":  self.id_vehiculo,
            "id_empleado":  id_emp,
            "observaciones": self.obs_var.get().strip(),
        }
        resp = api_post("/ordenes", body)
        if resp.get("ok"):
            messagebox.showinfo("Éxito", f"Orden creada con ID {resp['data']['id_orden']}")
            if self.callback:
                self.callback()
            self.destroy()
        else:
            messagebox.showerror("Error", resp.get("error", "Error desconocido"))


# ─────────────────────────────────────────────
# FORMULARIO: Actualizar estatus de orden
# ─────────────────────────────────────────────
class FormActualizarEstatus(ctk.CTkToplevel):
    def __init__(self, parent, id_orden, estatus_actual, callback=None):
        super().__init__(parent)
        self.title(f"Actualizar orden #{id_orden}")
        self.geometry("360x280")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_CARD)
        self.grab_set()
        self.id_orden = id_orden
        self.callback = callback

        ctk.CTkLabel(self, text=f"Orden #{id_orden}",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLOR_TEXT).pack(pady=(24, 4))

        ctk.CTkLabel(self, text=f"Estatus actual: {estatus_actual}",
                     text_color="#aaaaaa").pack(pady=(0, 20))

        ctk.CTkLabel(self, text="Nuevo estatus *",
                     text_color=COLOR_TEXT, anchor="w").pack(fill="x", padx=32)

        self.estatus_var = ctk.StringVar(value="EN_PROCESO")
        ctk.CTkOptionMenu(
            self,
            values=["RECIBIDO", "EN_PROCESO", "LISTO", "ENTREGADO", "CANCELADO"],
            variable=self.estatus_var,
            width=296,
        ).pack(padx=32, pady=8)

        ctk.CTkButton(
            self, text="Actualizar",
            fg_color=COLOR_WARNING,
            text_color="#1a1a1a",
            hover_color="#b07820",
            command=self._guardar,
            height=40,
        ).pack(pady=20, padx=32, fill="x")

    def _guardar(self):
        resp = api_put(f"/ordenes/{self.id_orden}/estatus",
                       {"estatus": self.estatus_var.get()})
        if resp.get("ok"):
            messagebox.showinfo("Éxito", f"Orden #{self.id_orden} actualizada.")
            if self.callback:
                self.callback()
            self.destroy()
        else:
            messagebox.showerror("Error", resp.get("error", "Error desconocido"))


# ─────────────────────────────────────────────
# FORMULARIO: Registrar pago
# ─────────────────────────────────────────────
class FormRegistrarPago(ctk.CTkToplevel):
    def __init__(self, parent, id_factura, total, callback=None):
        super().__init__(parent)
        self.title(f"Registrar pago — Factura #{id_factura}")
        self.geometry("380x320")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_CARD)
        self.grab_set()
        self.id_factura = id_factura
        self.callback   = callback

        ctk.CTkLabel(self, text=f"Factura #{id_factura}",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLOR_TEXT).pack(pady=(24, 4))

        ctk.CTkLabel(self, text=f"Total: ${total:,.2f}",
                     text_color=COLOR_WARNING,
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(0, 16))

        ctk.CTkLabel(self, text="Monto a pagar *",
                     text_color=COLOR_TEXT, anchor="w").pack(fill="x", padx=32)
        self.monto_var = ctk.StringVar(value=str(total))
        ctk.CTkEntry(self, textvariable=self.monto_var, width=316).pack(padx=32, pady=(4, 12))

        ctk.CTkLabel(self, text="Método de pago *",
                     text_color=COLOR_TEXT, anchor="w").pack(fill="x", padx=32)
        self.metodo_var = ctk.StringVar(value="EFECTIVO")
        ctk.CTkOptionMenu(
            self,
            values=["EFECTIVO", "TARJETA", "TRANSFERENCIA", "CHEQUE"],
            variable=self.metodo_var,
            width=316,
        ).pack(padx=32, pady=(4, 16))

        ctk.CTkButton(
            self, text="Registrar pago",
            fg_color=COLOR_SUCCESS,
            hover_color="#1e6b4a",
            command=self._guardar,
            height=40,
        ).pack(padx=32, fill="x")

    def _guardar(self):
        try:
            monto = float(self.monto_var.get())
        except ValueError:
            messagebox.showwarning("Monto inválido", "Ingresa un número válido.")
            return
        try:
            r = requests.post("http://localhost:5000/api/pagos", json={
                "id_factura":  self.id_factura,
                "monto":       monto,
                "metodo_pago": self.metodo_var.get(),
            }, timeout=5)
            resp = r.json()
            if resp.get("ok"):
                messagebox.showinfo("Éxito", "Pago registrado correctamente.")
                if self.callback:
                    self.callback()
                self.destroy()
            else:
                messagebox.showerror("Error", resp.get("error", "Error desconocido"))
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ─────────────────────────────────────────────
# Ventana principal
# ─────────────────────────────────────────────
class MotorCraftApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MotorCraft — Sistema de Gestión")
        self.geometry("1200x700")
        self.minsize(1000, 600)
        self.configure(fg_color=COLOR_BG)
        self._build_sidebar()
        self._build_main()
        self.mostrar_ordenes()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=COLOR_CARD, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="⚙ MotorCraft",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=COLOR_TEXT).pack(pady=(30, 5))

        ctk.CTkLabel(self.sidebar, text="Sistema de Gestión",
                     font=ctk.CTkFont(size=12),
                     text_color="#888888").pack(pady=(0, 30))

        botones = [
            ("🗂  Órdenes activas",    self.mostrar_ordenes),
            ("👤  Clientes",           self.mostrar_clientes),
            ("📦  Inventario",         self.mostrar_inventario),
            ("📊  Reportes",           self.mostrar_reportes),
            ("💰  Cuentas por cobrar", self.mostrar_cuentas),
            ("📋  Audit log",          self.mostrar_audit),
        ]

        for texto, comando in botones:
            ctk.CTkButton(
                self.sidebar, text=texto, command=comando,
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

        self.titulo_header = ctk.CTkLabel(
            self.header, text="Órdenes activas",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXT)
        self.titulo_header.pack(side="left", padx=24, pady=15)

        self.btn_refresh = ctk.CTkButton(
            self.header, text="↻ Actualizar", width=110,
            fg_color=COLOR_PRIMARY, command=self._refresh)
        self.btn_refresh.pack(side="right", padx=16, pady=12)

        self.contenido = ctk.CTkFrame(self.main, fg_color=COLOR_BG)
        self.contenido.pack(fill="both", expand=True, padx=16, pady=16)
        self._vista_actual = None

    def _limpiar(self):
        for w in self.contenido.winfo_children():
            w.destroy()

    def _refresh(self):
        if self._vista_actual:
            self._vista_actual()

    def _set_titulo(self, texto):
        self.titulo_header.configure(text=texto)

    def _tabla(self, parent, columnas, datos, anchos=None):
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

        tree = ttk.Treeview(frame, columns=columnas, show="headings", style="MC.Treeview")
        for i, col in enumerate(columnas):
            ancho = anchos[i] if anchos else 130
            tree.heading(col, text=col)
            tree.column(col, width=ancho, anchor="w")

        for fila in datos:
            valores = [str(fila.get(c, "")) for c in columnas]
            tree.insert("", "end", values=valores)

        sb_y = ttk.Scrollbar(frame, orient="vertical",   command=tree.yview)
        sb_x = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.pack(side="right", fill="y")
        sb_x.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        return tree

    # ── VISTA 1: Órdenes ─────────────────────
    def mostrar_ordenes(self):
        self._vista_actual = self.mostrar_ordenes
        self._set_titulo("Órdenes activas")
        self._limpiar()

        # Barra de acciones
        acc = ctk.CTkFrame(self.contenido, fg_color="transparent")
        acc.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(acc, text="+ Nueva orden",
                      fg_color=COLOR_SUCCESS, hover_color="#1e6b4a",
                      command=self._form_nueva_orden).pack(side="left", padx=(0, 8))

        ctk.CTkButton(acc, text="✏ Cambiar estatus",
                      fg_color=COLOR_WARNING, text_color="#1a1a1a",
                      command=self._form_estatus).pack(side="left", padx=(0, 16))

        # Filtro estatus
        self.filtro_var = ctk.StringVar(value="TODOS")
        for op in ["TODOS", "RECIBIDO", "EN_PROCESO", "LISTO"]:
            ctk.CTkRadioButton(acc, text=op, variable=self.filtro_var,
                               value=op, command=self._cargar_ordenes,
                               text_color=COLOR_TEXT).pack(side="left", padx=6)

        self._frame_ordenes = ctk.CTkFrame(self.contenido, fg_color="transparent")
        self._frame_ordenes.pack(fill="both", expand=True)
        self._cargar_ordenes()

    def _cargar_ordenes(self):
        for w in self._frame_ordenes.winfo_children():
            w.destroy()
        datos   = api_get("/ordenes")
        estatus = self.filtro_var.get()
        if estatus != "TODOS":
            datos = [d for d in datos if d.get("estatus") == estatus]
        if not datos:
            ctk.CTkLabel(self._frame_ordenes, text="No hay órdenes activas",
                         font=ctk.CTkFont(size=14), text_color="#888888").pack(expand=True)
            return
        cols   = ["id_orden", "cliente", "vehiculo", "placa", "mecanico", "estatus", "fecha_entrada"]
        anchos = [70, 160, 130, 80, 140, 100, 150]
        self._tree_ordenes = self._tabla(self._frame_ordenes, cols, datos, anchos)
        self._datos_ordenes = datos

    def _form_nueva_orden(self):
        FormNuevaOrden(self, callback=self._cargar_ordenes)

    def _form_estatus(self):
        if not hasattr(self, "_tree_ordenes"):
            messagebox.showinfo("Selecciona una orden", "Primero carga las órdenes.")
            return
        sel = self._tree_ordenes.selection()
        if not sel:
            messagebox.showinfo("Selecciona una orden", "Haz clic en una orden de la tabla.")
            return
        valores = self._tree_ordenes.item(sel[0])["values"]
        id_orden = valores[0]
        estatus  = valores[5]
        FormActualizarEstatus(self, id_orden, estatus, callback=self._cargar_ordenes)

    # ── VISTA 2: Clientes ─────────────────────
    def mostrar_clientes(self):
        self._vista_actual = self.mostrar_clientes
        self._set_titulo("Clientes")
        self._limpiar()

        acc = ctk.CTkFrame(self.contenido, fg_color="transparent")
        acc.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(acc, text="+ Nuevo cliente",
                      fg_color=COLOR_SUCCESS, hover_color="#1e6b4a",
                      command=self._form_nuevo_cliente).pack(side="left", padx=(0, 16))

        self.busq_var = ctk.StringVar()
        ctk.CTkEntry(acc, textvariable=self.busq_var,
                     placeholder_text="Buscar por nombre...",
                     width=240).pack(side="left", padx=(0, 8))
        ctk.CTkButton(acc, text="Buscar", width=80,
                      fg_color=COLOR_PRIMARY,
                      command=self._buscar_clientes).pack(side="left")
        ctk.CTkButton(acc, text="Ver todos", width=90,
                      fg_color="#444466",
                      command=self._cargar_clientes).pack(side="left", padx=8)

        self._frame_clientes = ctk.CTkFrame(self.contenido, fg_color="transparent")
        self._frame_clientes.pack(fill="both", expand=True)
        self._cargar_clientes()

    def _cargar_clientes(self):
        for w in self._frame_clientes.winfo_children():
            w.destroy()
        datos  = api_get("/clientes")
        cols   = ["id_cliente", "nombre", "apellido", "telefono", "email", "fecha_registro"]
        anchos = [80, 130, 130, 120, 200, 160]
        self._tabla(self._frame_clientes, cols, datos, anchos)

    def _buscar_clientes(self):
        termino = self.busq_var.get().lower()
        for w in self._frame_clientes.winfo_children():
            w.destroy()
        datos = api_get("/clientes")
        filtrados = [d for d in datos
                     if termino in d.get("nombre", "").lower()
                     or termino in d.get("apellido", "").lower()]
        cols   = ["id_cliente", "nombre", "apellido", "telefono", "email", "fecha_registro"]
        anchos = [80, 130, 130, 120, 200, 160]
        self._tabla(self._frame_clientes, cols, filtrados, anchos)

    def _form_nuevo_cliente(self):
        FormNuevoCliente(self, callback=self._cargar_clientes)

    # ── VISTA 3: Inventario ───────────────────
    def mostrar_inventario(self):
        self._vista_actual = self.mostrar_inventario
        self._set_titulo("Inventario de piezas (MongoDB)")
        self._limpiar()

        btn_f = ctk.CTkFrame(self.contenido, fg_color="transparent")
        btn_f.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(btn_f, text="Ver todo", width=110,
                      fg_color=COLOR_PRIMARY,
                      command=self._cargar_inventario).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_f, text="⚠ Bajo stock", width=120,
                      fg_color=COLOR_WARNING, text_color="#1a1a1a",
                      command=self._cargar_bajo_stock).pack(side="left")

        self._frame_inv = ctk.CTkFrame(self.contenido, fg_color="transparent")
        self._frame_inv.pack(fill="both", expand=True)
        self._cargar_inventario()

    def _cargar_inventario(self):
        for w in self._frame_inv.winfo_children():
            w.destroy()
        datos  = api_get("/inventario")
        cols   = ["codigo", "nombre", "categoria", "marca_producto", "stock", "stock_minimo", "precio_unitario"]
        anchos = [120, 220, 100, 110, 60, 90, 110]
        self._tabla(self._frame_inv, cols, datos, anchos)

    def _cargar_bajo_stock(self):
        for w in self._frame_inv.winfo_children():
            w.destroy()
        datos = api_get("/inventario/bajo-stock")
        if not datos:
            ctk.CTkLabel(self._frame_inv,
                         text="✓ Todo el inventario está sobre el mínimo",
                         font=ctk.CTkFont(size=14),
                         text_color=COLOR_SUCCESS).pack(expand=True)
            return
        cols   = ["codigo", "nombre", "categoria", "stock", "stock_minimo"]
        anchos = [120, 240, 120, 70, 100]
        self._tabla(self._frame_inv, cols, datos, anchos)

    # ── VISTA 4: Reportes ─────────────────────
    def mostrar_reportes(self):
        self._vista_actual = self.mostrar_reportes
        self._set_titulo("Reportes y gráficas")
        self._limpiar()

        tabs = ctk.CTkTabview(self.contenido, fg_color=COLOR_CARD)
        tabs.pack(fill="both", expand=True)
        tabs.add("Servicios más solicitados")
        tabs.add("Ingresos por período")

        self._grafica_servicios(tabs.tab("Servicios más solicitados"))
        self._grafica_ingresos(tabs.tab("Ingresos por período"))

    def _grafica_servicios(self, parent):
        datos = api_get("/reportes/servicios-top", {"limite": 7})
        if not datos:
            ctk.CTkLabel(parent, text="Sin datos", text_color=COLOR_TEXT).pack(expand=True)
            return
        nombres  = [d["nombre_servicio"][:22] for d in datos]
        ingresos = [d["ingreso_total"] for d in datos]

        fig, ax = plt.subplots(figsize=(9, 4))
        fig.patch.set_facecolor("#1e1e2e")
        ax.set_facecolor("#1e1e2e")
        bars = ax.barh(nombres, ingresos, color=COLOR_PRIMARY)
        ax.set_title("Ingreso total por servicio ($)", color=COLOR_TEXT, fontsize=12)
        ax.tick_params(colors=COLOR_TEXT)
        ax.spines[:].set_color("#333355")
        for bar, val in zip(bars, ingresos):
            ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height()/2,
                    f"${val:,.0f}", va="center", color=COLOR_TEXT, fontsize=9)
        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

    def _grafica_ingresos(self, parent):
        filtro_f = ctk.CTkFrame(parent, fg_color="transparent")
        filtro_f.pack(fill="x", padx=8, pady=8)

        ctk.CTkLabel(filtro_f, text="Desde:", text_color=COLOR_TEXT).pack(side="left")
        self.desde_var = ctk.StringVar(value="2025-01-01")
        ctk.CTkEntry(filtro_f, textvariable=self.desde_var, width=110).pack(side="left", padx=4)

        ctk.CTkLabel(filtro_f, text="Hasta:", text_color=COLOR_TEXT).pack(side="left", padx=(8,0))
        self.hasta_var = ctk.StringVar(value="2025-12-31")
        ctk.CTkEntry(filtro_f, textvariable=self.hasta_var, width=110).pack(side="left", padx=4)

        self._frame_ing = ctk.CTkFrame(parent, fg_color="transparent")
        self._frame_ing.pack(fill="both", expand=True)

        ctk.CTkButton(filtro_f, text="Generar", width=90,
                      fg_color=COLOR_PRIMARY,
                      command=self._actualizar_ingresos).pack(side="left", padx=8)
        self._actualizar_ingresos()

    def _actualizar_ingresos(self):
        for w in self._frame_ing.winfo_children():
            w.destroy()
        datos = api_get("/reportes/ingresos", {
            "desde": self.desde_var.get(),
            "hasta": self.hasta_var.get(),
        })
        if not datos:
            ctk.CTkLabel(self._frame_ing, text="Sin datos en ese período",
                         text_color="#888888").pack(expand=True)
            return
        fechas  = [d["fecha"][:10] for d in datos]
        totales = [d["total_cobrado"] for d in datos]

        fig, ax = plt.subplots(figsize=(9, 3.5))
        fig.patch.set_facecolor("#1e1e2e")
        ax.set_facecolor("#1e1e2e")
        ax.plot(fechas, totales, marker="o", color=COLOR_PRIMARY, linewidth=2)
        ax.fill_between(range(len(fechas)), totales, alpha=0.15, color=COLOR_PRIMARY)
        ax.set_xticks(range(len(fechas)))
        ax.set_xticklabels(fechas, rotation=30, ha="right", color=COLOR_TEXT, fontsize=9)
        ax.tick_params(colors=COLOR_TEXT)
        ax.spines[:].set_color("#333355")
        ax.set_title("Ingresos por día ($)", color=COLOR_TEXT)
        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self._frame_ing)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

    # ── VISTA 5: Cuentas por cobrar ───────────
    def mostrar_cuentas(self):
        self._vista_actual = self.mostrar_cuentas
        self._set_titulo("Cuentas por cobrar")
        self._limpiar()

        acc = ctk.CTkFrame(self.contenido, fg_color="transparent")
        acc.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(acc, text="💳 Registrar pago",
                      fg_color=COLOR_SUCCESS, hover_color="#1e6b4a",
                      command=self._form_pago).pack(side="left")

        self._frame_cuentas = ctk.CTkFrame(self.contenido, fg_color="transparent")
        self._frame_cuentas.pack(fill="both", expand=True)
        self._cargar_cuentas()

    def _cargar_cuentas(self):
        for w in self._frame_cuentas.winfo_children():
            w.destroy()
        datos = api_get("/reportes/cuentas-cobrar")
        if not datos:
            ctk.CTkLabel(self._frame_cuentas,
                         text="✓ No hay cuentas pendientes",
                         font=ctk.CTkFont(size=16),
                         text_color=COLOR_SUCCESS).pack(expand=True)
            return
        cols   = ["id_factura","cliente","vehiculo","total","pagado","saldo_pendiente","dias_sin_pagar","estatus_pago"]
        anchos = [80, 150, 130, 80, 80, 110, 110, 100]
        self._tree_cuentas = self._tabla(self._frame_cuentas, cols, datos, anchos)
        self._datos_cuentas = datos

    def _form_pago(self):
        if not hasattr(self, "_tree_cuentas"):
            messagebox.showinfo("Selecciona una factura", "Primero carga las cuentas por cobrar.")
            return
        sel = self._tree_cuentas.selection()
        if not sel:
            messagebox.showinfo("Selecciona una factura", "Haz clic en una factura de la tabla.")
            return
        valores    = self._tree_cuentas.item(sel[0])["values"]
        id_factura = valores[0]
        saldo      = float(str(valores[5]).replace(",",""))
        FormRegistrarPago(self, id_factura, saldo, callback=self._cargar_cuentas)

    # ── VISTA 6: Audit log ────────────────────
    def mostrar_audit(self):
        self._vista_actual = self.mostrar_audit
        self._set_titulo("Audit Log — últimos 100 eventos")
        self._limpiar()
        datos = api_get("/audit-log")
        if not datos:
            ctk.CTkLabel(self.contenido,
                         text="Sin eventos registrados aún",
                         font=ctk.CTkFont(size=14),
                         text_color="#888888").pack(expand=True)
            return
        cols   = ["id_log","fecha_hora","usuario","tabla_afectada","accion"]
        anchos = [60, 160, 120, 150, 80]
        self._tabla(self.contenido, cols, datos, anchos)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = MotorCraftApp()
    app.mainloop()
