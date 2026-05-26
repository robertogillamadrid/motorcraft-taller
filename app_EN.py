"""
MotorCraft — REST API with Flask (English DB)
=============================================
Endpoints:

  CLIENTS
  GET    /api/clients              — list all
  GET    /api/clients/<id>         — detail + MongoDB history
  POST   /api/clients              — create new

  VEHICLES
  GET    /api/vehicles/<plate>     — search by plate

  WORK ORDERS
  GET    /api/orders               — list (filter ?status=)
  GET    /api/orders/<id>          — enriched detail from MongoDB
  POST   /api/orders               — new order (stored procedure)
  PUT    /api/orders/<id>/status   — update status

  INVENTORY (MongoDB)
  GET    /api/inventory            — list parts
  GET    /api/inventory/<code>     — part detail
  GET    /api/inventory/low-stock  — parts below minimum

  REPORTS (stored procedures)
  GET    /api/reports/revenue           — revenue by period
  GET    /api/reports/top-services      — most requested services
  GET    /api/reports/accounts-receivable — pending invoices

  AUDIT LOG
  GET    /api/audit-log            — last 100 events

Usage:
  python app.py
  Server: http://localhost:5000
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
# Configuration
# ─────────────────────────────────────────────
MYSQL_CONFIG = {
    "host":     os.getenv("MYSQL_HOST",     "localhost"),
    "port":     int(os.getenv("MYSQL_PORT", "3306")),
    "user":     os.getenv("MYSQL_USER",     "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "motorcraft_db"),
    "charset":  "utf8mb4",
}

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB  = os.getenv("MONGO_DB",  "motorcraft_db_mongo")

mongo_client = MongoClient(MONGO_URI)
mongo_db     = mongo_client[MONGO_DB]


# ─────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────
def get_mysql():
    return mysql.connector.connect(**MYSQL_CONFIG)

def serialize(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def row_to_dict(cursor, row):
    cols = [d[0] for d in cursor.description]
    return {k: serialize(v) for k, v in zip(cols, row)}

def rows_to_list(cursor):
    cols = [d[0] for d in cursor.description]
    return [{k: serialize(v) for k, v in zip(cols, r)}
            for r in cursor.fetchall()]

def ok(data, code=200):
    return jsonify({"ok": True, "data": data}), code

def error(message, code=400):
    return jsonify({"ok": False, "error": message}), code


# ─────────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────────
@app.route("/api/clients", methods=["GET"])
def list_clients():
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM CLIENTS ORDER BY registration_date DESC")
    data = rows_to_list(cur)
    cur.close(); conn.close()
    return ok(data)


@app.route("/api/clients/<int:client_id>", methods=["GET"])
def client_detail(client_id):
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM CLIENTS WHERE client_id = %s", (client_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return error("Client not found", 404)
    client = row_to_dict(cur, row)

    history = mongo_db["clients_history"].find_one(
        {"client_id": client_id}, {"_id": 0}
    )
    if history:
        client["vehicle_history"] = history.get("vehicles", [])

    cur.close(); conn.close()
    return ok(client)


@app.route("/api/clients", methods=["POST"])
def create_client():
    body = request.get_json()
    if not body or not body.get("first_name") or not body.get("last_name"):
        return error("first_name and last_name are required")

    conn = get_mysql()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO CLIENTS (first_name, last_name, phone, email, address)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            body.get("first_name"),
            body.get("last_name"),
            body.get("phone"),
            body.get("email"),
            body.get("address"),
        ))
        conn.commit()
        new_id = cur.lastrowid
        cur.close(); conn.close()
        return ok({"client_id": new_id, "message": "Client created successfully"}, 201)
    except mysql.connector.Error as e:
        conn.rollback()
        cur.close(); conn.close()
        return error(str(e))


# ─────────────────────────────────────────────
# VEHICLES
# ─────────────────────────────────────────────
@app.route("/api/vehicles/<plate>", methods=["GET"])
def search_vehicle(plate):
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("""
        SELECT v.*, CONCAT(c.first_name,' ',c.last_name) AS owner, c.phone
        FROM VEHICLES v
        JOIN CLIENTS c ON v.client_id = c.client_id
        WHERE v.plate = %s
    """, (plate.upper(),))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return error("Vehicle not found", 404)
    vehicle = row_to_dict(cur, row)

    log = mongo_db["repair_logs"].find_one(
        {"plate": plate.upper()}, {"_id": 0}
    )
    if log:
        vehicle["last_repair_log"] = log

    cur.close(); conn.close()
    return ok(vehicle)


# ─────────────────────────────────────────────
# WORK ORDERS
# ─────────────────────────────────────────────
@app.route("/api/orders", methods=["GET"])
def list_orders():
    status = request.args.get("status")
    conn = get_mysql()
    cur  = conn.cursor()
    if status:
        cur.execute("""
            SELECT * FROM vw_active_orders
            WHERE status = %s
        """, (status.upper(),))
    else:
        cur.execute("SELECT * FROM vw_active_orders")
    data = rows_to_list(cur)
    cur.close(); conn.close()
    return ok(data)


@app.route("/api/orders/<int:order_id>", methods=["GET"])
def order_detail(order_id):
    doc = mongo_db["enriched_orders"].find_one(
        {"order_id_sql": order_id}, {"_id": 0}
    )
    if not doc:
        conn = get_mysql()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM WORK_ORDERS WHERE order_id = %s", (order_id,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return error("Order not found", 404)
        doc = row_to_dict(cur, row)
        cur.close(); conn.close()
    return ok(doc)


@app.route("/api/orders", methods=["POST"])
def create_order():
    """Uses stored procedure sp_new_work_order"""
    body = request.get_json()
    if not body or not body.get("vehicle_id") or not body.get("employee_id"):
        return error("vehicle_id and employee_id are required")

    conn = get_mysql()
    cur  = conn.cursor()
    try:
        # Call stored procedure
        cur.callproc("sp_new_work_order", [
            body.get("vehicle_id"),
            body.get("employee_id"),
            body.get("notes", ""),
            0,   # OUT param placeholder
        ])
        conn.commit()
        cur.execute("SELECT LAST_INSERT_ID() AS order_id")
        new_id = cur.fetchone()[0]
        cur.close(); conn.close()
        return ok({"order_id": new_id, "message": "Work order created successfully"}, 201)
    except mysql.connector.Error as e:
        conn.rollback()
        cur.close(); conn.close()
        return error(str(e))


@app.route("/api/orders/<int:order_id>/status", methods=["PUT"])
def update_order_status(order_id):
    body = request.get_json()
    if not body or not body.get("status"):
        return error("status is required")

    conn = get_mysql()
    cur  = conn.cursor()
    try:
        cur.execute("""
            UPDATE WORK_ORDERS
            SET status = %s
            WHERE order_id = %s
        """, (body["status"].upper(), order_id))
        conn.commit()
        cur.close(); conn.close()
        return ok({"message": f"Order {order_id} updated to {body['status']}"})
    except mysql.connector.Error as e:
        conn.rollback()
        cur.close(); conn.close()
        return error(str(e))


# ─────────────────────────────────────────────
# INVENTORY (MongoDB)
# ─────────────────────────────────────────────
@app.route("/api/inventory", methods=["GET"])
def list_inventory():
    category = request.args.get("category")
    make     = request.args.get("make")

    query = {"active": True}
    if category:
        query["category"] = category
    if make:
        query["compatibility.make"] = make

    parts = list(mongo_db["parts_inventory"].find(
        query, {"_id": 0}
    ).sort("name", 1))
    return ok(parts)


@app.route("/api/inventory/low-stock", methods=["GET"])
def low_stock():
    parts = list(mongo_db["parts_inventory"].find(
        {"$expr": {"$lte": ["$stock", "$min_stock"]}, "active": True},
        {"_id": 0, "code": 1, "name": 1, "category": 1,
         "stock": 1, "min_stock": 1, "supplier": 1}
    ).sort("stock", 1))
    return ok(parts)


@app.route("/api/inventory/<code>", methods=["GET"])
def part_detail(code):
    part = mongo_db["parts_inventory"].find_one(
        {"code": code.upper()}, {"_id": 0}
    )
    if not part:
        return error("Part not found", 404)
    return ok(part)


# ─────────────────────────────────────────────
# REPORTS — all use stored procedures
# ─────────────────────────────────────────────
@app.route("/api/reports/revenue", methods=["GET"])
def report_revenue():
    """Calls stored procedure sp_report_revenue"""
    start_date = request.args.get("from", "2025-01-01")
    end_date   = request.args.get("to",   "2025-12-31")
    conn = get_mysql()
    cur  = conn.cursor()
    cur.callproc("sp_report_revenue", [start_date, end_date])
    data = []
    for result in cur.stored_results():
        data = [{k: serialize(v) for k, v in zip(
            [d[0] for d in result.description], row
        )} for row in result.fetchall()]
    cur.close(); conn.close()
    return ok(data)


@app.route("/api/reports/top-services", methods=["GET"])
def report_top_services():
    """Calls stored procedure sp_report_top_services"""
    limit = int(request.args.get("limit", 10))
    conn = get_mysql()
    cur  = conn.cursor()
    cur.callproc("sp_report_top_services", [limit])
    data = []
    for result in cur.stored_results():
        data = [{k: serialize(v) for k, v in zip(
            [d[0] for d in result.description], row
        )} for row in result.fetchall()]
    cur.close(); conn.close()
    return ok(data)


@app.route("/api/reports/accounts-receivable", methods=["GET"])
def accounts_receivable():
    """Returns pending invoices from view vw_accounts_receivable"""
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM vw_accounts_receivable")
    data = rows_to_list(cur)
    cur.close(); conn.close()
    return ok(data)


# ─────────────────────────────────────────────
# EMPLOYEES (for order form dropdown)
# ─────────────────────────────────────────────
@app.route("/api/employees", methods=["GET"])
def list_employees():
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("""
        SELECT e.employee_id, e.first_name, e.last_name, p.position_name
        FROM EMPLOYEES e
        JOIN POSITIONS p ON e.position_id = p.position_id
        WHERE e.active = 1
        ORDER BY e.first_name
    """)
    data = rows_to_list(cur)
    cur.close(); conn.close()
    return ok(data)


# ─────────────────────────────────────────────
# PAYMENTS — uses stored procedure
# ─────────────────────────────────────────────
@app.route("/api/payments", methods=["POST"])
def register_payment():
    """Calls stored procedure sp_register_payment"""
    body = request.get_json()
    if not body or not body.get("invoice_id") or not body.get("amount"):
        return error("invoice_id and amount are required")

    conn = get_mysql()
    cur  = conn.cursor()
    try:
        cur.callproc("sp_register_payment", [
            body["invoice_id"],
            body["amount"],
            body.get("payment_method", "CASH"),
        ])
        conn.commit()
        cur.close(); conn.close()
        return ok({"message": "Payment registered successfully"}, 201)
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
    data = rows_to_list(cur)
    cur.close(); conn.close()
    return ok(data)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  MotorCraft REST API")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(debug=False, host="0.0.0.0", port=5000)
