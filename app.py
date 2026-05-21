"""
MotorCraft — Fase 5b: API REST con Flask
=========================================
Endpoints:

  CLIENTES
  GET    /api/clientes              — listar todos
  GET    /api/clientes/<id>         — detalle + historial MongoDB
  POST   /api/clientes              — crear nuevo

  VEHÍCULOS
  GET    /api/vehiculos/<placa>     — buscar por placa

  ÓRDENES
  GET    /api/ordenes               — listar (filtro ?estatus=)
  GET    /api/ordenes/<id>          — detalle enriquecido MongoDB
  POST   /api/ordenes               — nueva orden
  PUT    /api/ordenes/<id>/estatus  — actualizar estatus

  INVENTARIO MongoDB
  GET    /api/inventario            — listar piezas
  GET    /api/inventario/<codigo>   — detalle de pieza
  GET    /api/inventario/bajo-stock — piezas bajo mínimo

  REPORTES
  GET    /api/reportes/ingresos          — ingresos por período
  GET    /api/reportes/servicios-top     — servicios más solicitados
  GET    /api/reportes/cuentas-cobrar    — facturas pendientes

  AUDIT LOG
  GET    /api/audit-log             — últimos 100 eventos

Uso:
  python app.py
  Servidor: http://localhost:5000
"""

import os
from datetime import datetime
from decimal import Decimal

import mysql.connector
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────
MYSQL_CONFIG = {
    "host":     os.getenv("MYSQL_HOST",     "localhost"),
    "port":     int(os.getenv("MYSQL_PORT", "3306")),
    "user":     os.getenv("MYSQL_USER",     "root"),
    "password": os.getenv("MYSQL_PASSWORD", "Transilvania2305"),
    "database": os.getenv("MYSQL_DATABASE", "motorcraft_db"),
    "charset":  "utf8mb4",
}

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB  = os.getenv("MONGO_DB",  "uabcdb")

mongo_cliente = MongoClient(MONGO_URI)
mongo_db      = mongo_cliente[MONGO_DB]


# ─────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────
def get_mysql():
    return mysql.connector.connect(**MYSQL_CONFIG)

def serializar(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def fila_a_dict(cursor, fila):
    cols = [d[0] for d in cursor.description]
    return {k: serializar(v) for k, v in zip(cols, fila)}

def filas_a_lista(cursor):
    cols = [d[0] for d in cursor.description]
    return [{k: serializar(v) for k, v in zip(cols, f)}
            for f in cursor.fetchall()]

def ok(data, codigo=200):
    return jsonify({"ok": True, "data": data}), codigo

def error(mensaje, codigo=400):
    return jsonify({"ok": False, "error": mensaje}), codigo


# ─────────────────────────────────────────────
# CLIENTES
# ─────────────────────────────────────────────
@app.route("/api/clientes", methods=["GET"])
def listar_clientes():
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM CLIENTES ORDER BY fecha_registro DESC")
    datos = filas_a_lista(cur)
    cur.close(); conn.close()
    return ok(datos)


@app.route("/api/clientes/<int:id_cliente>", methods=["GET"])
def detalle_cliente(id_cliente):
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM CLIENTES WHERE id_cliente = %s", (id_cliente,))
    fila = cur.fetchone()
    if not fila:
        cur.close(); conn.close()
        return error("Cliente no encontrado", 404)
    cliente = fila_a_dict(cur, fila)

    historial = mongo_db["clientes_historial"].find_one(
        {"id_cliente": id_cliente}, {"_id": 0}
    )
    if historial:
        cliente["vehiculos_historial"] = historial.get("vehiculos", [])

    cur.close(); conn.close()
    return ok(cliente)


@app.route("/api/clientes", methods=["POST"])
def crear_cliente():
    body = request.get_json()
    if not body or not body.get("nombre") or not body.get("apellido"):
        return error("nombre y apellido son obligatorios")

    conn = get_mysql()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO CLIENTES (nombre, apellido, telefono, email, direccion)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            body.get("nombre"),
            body.get("apellido"),
            body.get("telefono"),
            body.get("email"),
            body.get("direccion"),
        ))
        conn.commit()
        nuevo_id = cur.lastrowid
        cur.close(); conn.close()
        return ok({"id_cliente": nuevo_id, "mensaje": "Cliente creado correctamente"}, 201)
    except mysql.connector.Error as e:
        conn.rollback()
        cur.close(); conn.close()
        return error(str(e))


# ─────────────────────────────────────────────
# VEHÍCULOS
# ─────────────────────────────────────────────
@app.route("/api/vehiculos/<placa>", methods=["GET"])
def buscar_vehiculo(placa):
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("""
        SELECT v.*, CONCAT(c.nombre,' ',c.apellido) AS propietario, c.telefono
        FROM VEHICULOS v
        JOIN CLIENTES c ON v.id_cliente = c.id_cliente
        WHERE v.placa = %s
    """, (placa.upper(),))
    fila = cur.fetchone()
    if not fila:
        cur.close(); conn.close()
        return error("Vehículo no encontrado", 404)
    vehiculo = fila_a_dict(cur, fila)

    bitacora = mongo_db["bitacoras_reparacion"].find_one(
        {"placa": placa.upper()}, {"_id": 0}
    )
    if bitacora:
        vehiculo["ultima_bitacora"] = bitacora

    cur.close(); conn.close()
    return ok(vehiculo)


# ─────────────────────────────────────────────
# ÓRDENES DE TRABAJO
# ─────────────────────────────────────────────
@app.route("/api/ordenes", methods=["GET"])
def listar_ordenes():
    estatus = request.args.get("estatus")
    conn = get_mysql()
    cur  = conn.cursor()
    if estatus:
        cur.execute("""
            SELECT * FROM vw_ordenes_activas
            WHERE estatus = %s
        """, (estatus.upper(),))
    else:
        cur.execute("SELECT * FROM vw_ordenes_activas")
    datos = filas_a_lista(cur)
    cur.close(); conn.close()
    return ok(datos)


@app.route("/api/ordenes/<int:id_orden>", methods=["GET"])
def detalle_orden(id_orden):
    doc = mongo_db["ordenes_enriquecidas"].find_one(
        {"id_orden_sql": id_orden}, {"_id": 0}
    )
    if not doc:
        conn = get_mysql()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM ORDENES_TRABAJO WHERE id_orden = %s", (id_orden,))
        fila = cur.fetchone()
        if not fila:
            cur.close(); conn.close()
            return error("Orden no encontrada", 404)
        doc = fila_a_dict(cur, fila)
        cur.close(); conn.close()
    return ok(doc)


@app.route("/api/ordenes", methods=["POST"])
def crear_orden():
    body = request.get_json()
    if not body or not body.get("id_vehiculo") or not body.get("id_empleado"):
        return error("id_vehiculo e id_empleado son obligatorios")

    conn = get_mysql()
    cur  = conn.cursor()
    try:
        cur.callproc("sp_nueva_orden", [
            body.get("id_vehiculo"),
            body.get("id_empleado"),
            body.get("observaciones", ""),
            0,
        ])
        conn.commit()
        cur.execute("SELECT LAST_INSERT_ID() AS id_orden")
        nuevo_id = cur.fetchone()[0]
        cur.close(); conn.close()
        return ok({"id_orden": nuevo_id, "mensaje": "Orden creada correctamente"}, 201)
    except mysql.connector.Error as e:
        conn.rollback()
        cur.close(); conn.close()
        return error(str(e))


@app.route("/api/ordenes/<int:id_orden>/estatus", methods=["PUT"])
def actualizar_estatus(id_orden):
    body = request.get_json()
    if not body or not body.get("estatus"):
        return error("estatus es obligatorio")

    conn = get_mysql()
    cur  = conn.cursor()
    try:
        cur.execute("""
            UPDATE ORDENES_TRABAJO
            SET estatus = %s
            WHERE id_orden = %s
        """, (body["estatus"].upper(), id_orden))
        conn.commit()
        cur.close(); conn.close()
        return ok({"mensaje": f"Orden {id_orden} actualizada a {body['estatus']}"})
    except mysql.connector.Error as e:
        conn.rollback()
        cur.close(); conn.close()
        return error(str(e))


# ─────────────────────────────────────────────
# INVENTARIO (MongoDB)
# ─────────────────────────────────────────────
@app.route("/api/inventario", methods=["GET"])
def listar_inventario():
    categoria = request.args.get("categoria")
    marca     = request.args.get("marca")

    filtro = {"activo": True}
    if categoria:
        filtro["categoria"] = categoria
    if marca:
        filtro["compatibilidad.marca"] = marca

    piezas = list(mongo_db["inventario_piezas"].find(
        filtro, {"_id": 0}
    ).sort("nombre", 1))
    return ok(piezas)


@app.route("/api/inventario/bajo-stock", methods=["GET"])
def bajo_stock():
    piezas = list(mongo_db["inventario_piezas"].find(
        {"$expr": {"$lte": ["$stock", "$stock_minimo"]}, "activo": True},
        {"_id": 0, "codigo": 1, "nombre": 1, "categoria": 1,
         "stock": 1, "stock_minimo": 1, "proveedor": 1}
    ).sort("stock", 1))
    return ok(piezas)


@app.route("/api/inventario/<codigo>", methods=["GET"])
def detalle_pieza(codigo):
    pieza = mongo_db["inventario_piezas"].find_one(
        {"codigo": codigo.upper()}, {"_id": 0}
    )
    if not pieza:
        return error("Pieza no encontrada", 404)
    return ok(pieza)


# ─────────────────────────────────────────────
# REPORTES
# ─────────────────────────────────────────────
@app.route("/api/reportes/ingresos", methods=["GET"])
def reporte_ingresos():
    fecha_inicio = request.args.get("desde", "2025-01-01")
    fecha_fin    = request.args.get("hasta", "2025-12-31")
    conn = get_mysql()
    cur  = conn.cursor()
    cur.callproc("sp_reporte_ingresos", [fecha_inicio, fecha_fin])
    datos = []
    for result in cur.stored_results():
        datos = [{k: serializar(v) for k, v in zip(
            [d[0] for d in result.description], fila
        )} for fila in result.fetchall()]
    cur.close(); conn.close()
    return ok(datos)


@app.route("/api/reportes/servicios-top", methods=["GET"])
def reporte_servicios():
    limite = int(request.args.get("limite", 10))
    conn = get_mysql()
    cur  = conn.cursor()
    cur.callproc("sp_reporte_servicios_top", [limite])
    datos = []
    for result in cur.stored_results():
        datos = [{k: serializar(v) for k, v in zip(
            [d[0] for d in result.description], fila
        )} for fila in result.fetchall()]
    cur.close(); conn.close()
    return ok(datos)


@app.route("/api/reportes/cuentas-cobrar", methods=["GET"])
def cuentas_por_cobrar():
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM vw_cuentas_por_cobrar")
    datos = filas_a_lista(cur)
    cur.close(); conn.close()
    return ok(datos)


# ─────────────────────────────────────────────
# EMPLEADOS (para formulario de órdenes)
# ─────────────────────────────────────────────
@app.route("/api/empleados", methods=["GET"])
def listar_empleados():
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("""
        SELECT e.id_empleado, e.nombre, e.apellido, p.nombre_puesto
        FROM EMPLEADOS e
        JOIN PUESTOS p ON e.id_puesto = p.id_puesto
        WHERE e.activo = 1
        ORDER BY e.nombre
    """)
    datos = filas_a_lista(cur)
    cur.close(); conn.close()
    return ok(datos)


# ─────────────────────────────────────────────
# PAGOS
# ─────────────────────────────────────────────
@app.route("/api/pagos", methods=["POST"])
def registrar_pago():
    body = request.get_json()
    if not body or not body.get("id_factura") or not body.get("monto"):
        return error("id_factura y monto son obligatorios")

    conn = get_mysql()
    cur  = conn.cursor()
    try:
        cur.callproc("sp_registrar_pago", [
            body["id_factura"],
            body["monto"],
            body.get("metodo_pago", "EFECTIVO"),
        ])
        conn.commit()
        cur.close(); conn.close()
        return ok({"mensaje": "Pago registrado correctamente"}, 201)
    except mysql.connector.Error as e:
        conn.rollback()
        cur.close(); conn.close()
        return error(str(e))


# ─────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────
@app.route("/api/audit-log", methods=["GET"])
def audit_log():
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM vw_audit_log LIMIT 100")
    datos = filas_a_lista(cur)
    cur.close(); conn.close()
    return ok(datos)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  MotorCraft API REST")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
