"""
MotorCraft — REST API with Flask (English DB + Security + JWT)
==============================================================
Security:
  - JWT authentication on all endpoints
  - Role-based access control (ADMIN, MECHANIC, RECEPTIONIST, ACCOUNTING)
  - Sensitive columns filtered per role
  - Passwords hashed with SHA-256

Roles:
  ADMIN       — full access
  MECHANIC    — orders, inventory, vehicles
  RECEPTIONIST— clients, vehicles, orders (read)
  ACCOUNTING  — invoices, payments, payroll, reports

Usage:
  pip install flask flask-cors flask-caching PyJWT python-dotenv
  python app_EN.py
  Server: http://localhost:5000
"""

import os
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from functools import wraps

import jwt
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_caching import Cache
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# Security config
# ─────────────────────────────────────────────
JWT_SECRET  = os.getenv("JWT_SECRET", "motorcraft_secret_2024_!@#")
JWT_EXPIRES = int(os.getenv("JWT_EXPIRES_HOURS", "8"))

# ─────────────────────────────────────────────
# Cache
# ─────────────────────────────────────────────
app.config["CACHE_TYPE"]            = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 30
cache = Cache(app)

# ─────────────────────────────────────────────
# MySQL connection pool
# ─────────────────────────────────────────────
MYSQL_CONFIG = {
    "host":     os.getenv("MYSQL_HOST",     "localhost"),
    "port":     int(os.getenv("MYSQL_PORT", "3306")),
    "user":     os.getenv("MYSQL_USER",     "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "motorcraft_db"),
    "charset":  "utf8mb4",
}
pool = MySQLConnectionPool(pool_name="motorcraft", pool_size=5, **MYSQL_CONFIG)

# ─────────────────────────────────────────────
# MongoDB
# ─────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB  = os.getenv("MONGO_DB",  "motorcraft_db_mongo")
mongo_client = MongoClient(MONGO_URI, maxPoolSize=10)
mongo_db     = mongo_client[MONGO_DB]

# ─────────────────────────────────────────────
# Role permissions
# ─────────────────────────────────────────────
ROLE_PERMISSIONS = {
    "ADMIN":        ["clients", "vehicles", "orders", "inventory",
                     "reports", "employees", "payments", "audit", "payroll"],
    "MECHANIC":     ["orders", "inventory", "vehicles"],
    "RECEPTIONIST": ["clients", "vehicles", "orders"],
    "ACCOUNTING":   ["reports", "payments", "invoices", "payroll", "clients"],
}


# ─────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────
def get_mysql():
    return pool.get_connection()

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

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token(user: dict) -> str:
    payload = {
        "user_id":   user["user_id"],
        "username":  user["username"],
        "role":      user["role"],
        "exp":       datetime.utcnow() + timedelta(hours=JWT_EXPIRES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


# ─────────────────────────────────────────────
# Auth decorators
# ─────────────────────────────────────────────
def token_required(f):
    """Verify JWT token on every request."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        if not token:
            return error("Token is missing. Please log in.", 401)
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            g.current_user = payload
        except jwt.ExpiredSignatureError:
            return error("Session expired. Please log in again.", 401)
        except jwt.InvalidTokenError:
            return error("Invalid token. Please log in.", 401)
        return f(*args, **kwargs)
    return decorated


def role_required(*allowed_permissions):
    """Check if the user's role has permission for this resource."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            role = g.current_user.get("role", "")
            user_perms = ROLE_PERMISSIONS.get(role, [])
            if not any(p in user_perms for p in allowed_permissions):
                return error(
                    f"Access denied. Your role ({role}) does not have permission for this resource.",
                    403
                )
            return f(*args, **kwargs)
        return decorated
    return decorator


# ─────────────────────────────────────────────
# AUTH — Login / Logout
# ─────────────────────────────────────────────
@app.route("/api/auth/login", methods=["POST"])
def login():
    """
    POST /api/auth/login
    Body: { "username": "...", "password": "..." }
    Returns: { "token": "...", "user": { ... } }
    """
    body = request.get_json()
    if not body or not body.get("username") or not body.get("password"):
        return error("username and password are required")

    conn = get_mysql()
    cur  = conn.cursor()
    try:
        cur.execute("""
            SELECT u.user_id, u.username, u.password_hash,
                   r.role_name AS role,
                   e.first_name, e.last_name, e.employee_id
            FROM USERS u
            JOIN ROLES r     ON u.role_id     = r.role_id
            JOIN EMPLOYEES e ON u.employee_id = e.employee_id
            WHERE u.username = %s AND e.active = 1
        """, (body["username"],))
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row:
        return error("Invalid username or password.", 401)

    user = {
        "user_id":    row[0],
        "username":   row[1],
        "pwd_hash":   row[2],
        "role":       row[3],
        "first_name": row[4],
        "last_name":  row[5],
        "employee_id":row[6],
    }

    if hash_password(body["password"]) != user["pwd_hash"]:
        return error("Invalid username or password.", 401)

    token = generate_token(user)
    return ok({
        "token": token,
        "user": {
            "user_id":    user["user_id"],
            "username":   user["username"],
            "role":       user["role"],
            "first_name": user["first_name"],
            "last_name":  user["last_name"],
            "permissions": ROLE_PERMISSIONS.get(user["role"], []),
        }
    })


@app.route("/api/auth/me", methods=["GET"])
@token_required
def me():
    """Returns current user info from token."""
    return ok(g.current_user)


# ─────────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────────
@app.route("/api/clients", methods=["GET"])
@token_required
@role_required("clients")
@cache.cached(timeout=20)
def list_clients():
    role = g.current_user.get("role")
    conn = get_mysql()
    cur  = conn.cursor()
    # ACCOUNTING only sees name + contact, not full address
    if role == "ACCOUNTING":
        cur.execute("""
            SELECT client_id, first_name, last_name, phone, email
            FROM CLIENTS ORDER BY registration_date DESC
        """)
    else:
        cur.execute("SELECT * FROM CLIENTS ORDER BY registration_date DESC")
    data = rows_to_list(cur)
    cur.close(); conn.close()
    return ok(data)


@app.route("/api/clients/<int:client_id>", methods=["GET"])
@token_required
@role_required("clients")
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
@token_required
@role_required("clients")
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
        """, (body.get("first_name"), body.get("last_name"),
              body.get("phone"), body.get("email"), body.get("address")))
        conn.commit()
        new_id = cur.lastrowid
        cache.delete("view//api/clients")
        cur.close(); conn.close()
        return ok({"client_id": new_id, "message": "Client created successfully"}, 201)
    except mysql.connector.Error as e:
        conn.rollback(); cur.close(); conn.close()
        return error(str(e))


# ─────────────────────────────────────────────
# VEHICLES
# ─────────────────────────────────────────────
@app.route("/api/vehicles/<plate>", methods=["GET"])
@token_required
@role_required("vehicles")
def search_vehicle(plate):
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("""
        SELECT v.vehicle_id, v.make, v.model, v.year, v.plate, v.color,
               CONCAT(c.first_name,' ',c.last_name) AS owner, c.phone
        FROM VEHICLES v
        JOIN CLIENTS c ON v.client_id = c.client_id
        WHERE v.plate = %s
    """, (plate.upper(),))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return error("Vehicle not found", 404)
    vehicle = row_to_dict(cur, row)
    log = mongo_db["repair_logs"].find_one({"plate": plate.upper()}, {"_id": 0})
    if log:
        vehicle["last_repair_log"] = log
    cur.close(); conn.close()
    return ok(vehicle)


# ─────────────────────────────────────────────
# WORK ORDERS
# ─────────────────────────────────────────────
@app.route("/api/orders", methods=["GET"])
@token_required
@role_required("orders")
@cache.cached(timeout=15, query_string=True)
def list_orders():
    status = request.args.get("status")
    conn = get_mysql()
    cur  = conn.cursor()
    if status:
        cur.execute("SELECT * FROM vw_active_orders WHERE status = %s", (status.upper(),))
    else:
        cur.execute("SELECT * FROM vw_active_orders")
    data = rows_to_list(cur)
    cur.close(); conn.close()
    return ok(data)


@app.route("/api/orders/<int:order_id>", methods=["GET"])
@token_required
@role_required("orders")
def order_detail(order_id):
    doc = mongo_db["enriched_orders"].find_one({"order_id_sql": order_id}, {"_id": 0})
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
@token_required
@role_required("orders")
def create_order():
    body = request.get_json()
    if not body or not body.get("vehicle_id") or not body.get("employee_id"):
        return error("vehicle_id and employee_id are required")
    conn = get_mysql()
    cur  = conn.cursor()
    try:
        cur.callproc("sp_new_work_order", [
            body.get("vehicle_id"), body.get("employee_id"),
            body.get("notes", ""), 0,
        ])
        conn.commit()
        cur.execute("SELECT LAST_INSERT_ID() AS order_id")
        new_id = cur.fetchone()[0]
        cache.delete("view//api/orders")
        cur.close(); conn.close()
        return ok({"order_id": new_id, "message": "Work order created successfully"}, 201)
    except mysql.connector.Error as e:
        conn.rollback(); cur.close(); conn.close()
        return error(str(e))


@app.route("/api/orders/<int:order_id>/status", methods=["PUT"])
@token_required
@role_required("orders")
def update_order_status(order_id):
    body = request.get_json()
    if not body or not body.get("status"):
        return error("status is required")
    conn = get_mysql()
    cur  = conn.cursor()
    try:
        cur.execute("UPDATE WORK_ORDERS SET status = %s WHERE order_id = %s",
                    (body["status"].upper(), order_id))
        conn.commit()
        cache.delete("view//api/orders")
        cur.close(); conn.close()
        return ok({"message": f"Order {order_id} updated to {body['status']}"})
    except mysql.connector.Error as e:
        conn.rollback(); cur.close(); conn.close()
        return error(str(e))


# ─────────────────────────────────────────────
# INVENTORY (MongoDB)
# ─────────────────────────────────────────────
@app.route("/api/inventory", methods=["GET"])
@token_required
@role_required("inventory")
@cache.cached(timeout=60, query_string=True)
def list_inventory():
    category = request.args.get("category")
    make     = request.args.get("make")
    query = {"active": True}
    if category:
        query["category"] = category
    if make:
        query["compatibility.make"] = make
    # Hide unit_price from MECHANIC role
    projection = {"_id": 0}
    if g.current_user.get("role") == "MECHANIC":
        projection["unit_price"] = 0
    parts = list(mongo_db["parts_inventory"].find(query, projection).sort("name", 1))
    return ok(parts)


@app.route("/api/inventory/low-stock", methods=["GET"])
@token_required
@role_required("inventory")
@cache.cached(timeout=30)
def low_stock():
    parts = list(mongo_db["parts_inventory"].find(
        {"$expr": {"$lte": ["$stock", "$min_stock"]}, "active": True},
        {"_id": 0, "code": 1, "name": 1, "category": 1,
         "stock": 1, "min_stock": 1, "supplier": 1}
    ).sort("stock", 1))
    return ok(parts)


@app.route("/api/inventory/<code>", methods=["GET"])
@token_required
@role_required("inventory")
def part_detail(code):
    part = mongo_db["parts_inventory"].find_one({"code": code.upper()}, {"_id": 0})
    if not part:
        return error("Part not found", 404)
    return ok(part)


# ─────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────
@app.route("/api/reports/revenue", methods=["GET"])
@token_required
@role_required("reports")
@cache.cached(timeout=60, query_string=True)
def report_revenue():
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
@token_required
@role_required("reports", "orders")
@cache.cached(timeout=60, query_string=True)
def report_top_services():
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
@token_required
@role_required("reports", "invoices", "payments")
@cache.cached(timeout=20)
def accounts_receivable():
    conn = get_mysql()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM vw_accounts_receivable")
    data = rows_to_list(cur)
    cur.close(); conn.close()
    return ok(data)


# ─────────────────────────────────────────────
# EMPLOYEES
# ─────────────────────────────────────────────
@app.route("/api/employees", methods=["GET"])
@token_required
@role_required("orders", "employees")
@cache.cached(timeout=120)
def list_employees():
    conn = get_mysql()
    cur  = conn.cursor()
    # Only ADMIN sees full employee data
    if g.current_user.get("role") == "ADMIN":
        cur.execute("""
            SELECT e.employee_id, e.first_name, e.last_name,
                   e.phone, e.email, p.position_name
            FROM EMPLOYEES e
            JOIN POSITIONS p ON e.position_id = p.position_id
            WHERE e.active = 1 ORDER BY e.first_name
        """)
    else:
        cur.execute("""
            SELECT e.employee_id, e.first_name, e.last_name, p.position_name
            FROM EMPLOYEES e
            JOIN POSITIONS p ON e.position_id = p.position_id
            WHERE e.active = 1 ORDER BY e.first_name
        """)
    data = rows_to_list(cur)
    cur.close(); conn.close()
    return ok(data)


# ─────────────────────────────────────────────
# PAYMENTS
# ─────────────────────────────────────────────
@app.route("/api/payments", methods=["POST"])
@token_required
@role_required("payments")
def register_payment():
    body = request.get_json()
    if not body or not body.get("invoice_id") or not body.get("amount"):
        return error("invoice_id and amount are required")
    conn = get_mysql()
    cur  = conn.cursor()
    try:
        cur.callproc("sp_register_payment", [
            body["invoice_id"], body["amount"],
            body.get("payment_method", "CASH"),
        ])
        conn.commit()
        cache.delete("view//api/reports/accounts-receivable")
        cur.close(); conn.close()
        return ok({"message": "Payment registered successfully"}, 201)
    except mysql.connector.Error as e:
        conn.rollback(); cur.close(); conn.close()
        return error(str(e))


# ─────────────────────────────────────────────
# AUDIT LOG — ADMIN only
# ─────────────────────────────────────────────
@app.route("/api/audit-log", methods=["GET"])
@token_required
@role_required("audit")
@cache.cached(timeout=10)
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
    print("  MotorCraft REST API — Secured")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(debug=False, host="0.0.0.0", port=5000)