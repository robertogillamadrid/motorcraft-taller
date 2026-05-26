"""
MotorCraft — Clone MySQL → MongoDB (English)
Run in PyCharm: right-click → Run 'MOTORCRAFT'
"""

import os
import sys
import logging
from datetime import datetime, date
from decimal import Decimal

import mysql.connector
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("clonacion.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ── Load .env ─────────────────────────────────────────────────
load_dotenv()

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


# ── Utilities ─────────────────────────────────────────────────
def serialize(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return obj


def clean_row(row: dict) -> dict:
    return {k: serialize(v) for k, v in row.items()}


def get_rows(cursor, table: str) -> list:
    cursor.execute(f"SELECT * FROM {table}")
    columns = [d[0] for d in cursor.description]
    return [clean_row(dict(zip(columns, r))) for r in cursor.fetchall()]


def insert_collection(db, name: str, documents: list) -> int:
    if not documents:
        log.warning("  ⚠  %-28s no data, skipping.", name)
        return 0
    col = db[name]
    col.drop()
    result = col.insert_many(documents, ordered=False)
    return len(result.inserted_ids)


# ── Connections ───────────────────────────────────────────────
def connect_mysql():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        log.info("✓ MySQL connected — database: %s", MYSQL_CONFIG["database"])
        return conn
    except mysql.connector.Error as err:
        log.error("✗ MySQL — %s", err)
        sys.exit(1)


def connect_mongo():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[MONGO_DB]
        log.info("✓ MongoDB connected — database: %s", MONGO_DB)
        return client, db
    except ConnectionFailure as err:
        log.error("✗ MongoDB — %s", err)
        sys.exit(1)


# ── Step 1: Clone tables directly ────────────────────────────
TABLES = [
    "POSITIONS", "EMPLOYEES", "PAYROLL",
    "CLIENTS", "VEHICLES",
    "SERVICES", "WORK_ORDERS", "ORDER_DETAILS",
    "INVOICES", "PAYMENTS",
    "SUPPLIERS", "PURCHASES", "PURCHASE_DETAILS",
    "ROLES", "USERS", "AUDIT_LOG",
]


def clone_tables(cursor, db):
    log.info("─── Step 1: Cloning tables → collections ───")
    total = 0
    for table in TABLES:
        try:
            rows = get_rows(cursor, table)
            n = insert_collection(db, table.lower(), rows)
            log.info("  ✓  %-28s %4d docs", table, n)
            total += n
        except Exception as e:
            log.warning("  ⚠  %-28s skipped: %s", table, e)
    log.info("  Subtotal mirror: %d documents", total)


# ── Step 2a: Enriched orders ──────────────────────────────────
def clone_enriched_orders(cursor, db):
    log.info("─── Step 2a: Enriched orders ───")

    cursor.execute("SELECT * FROM WORK_ORDERS")
    cols   = [d[0] for d in cursor.description]
    orders = [clean_row(dict(zip(cols, r))) for r in cursor.fetchall()]

    documents = []
    for order in orders:
        order_id    = order["order_id"]
        vehicle_id  = order["vehicle_id"]
        employee_id = order["employee_id"]

        # Vehicle + client
        cursor.execute("""
            SELECT v.*, c.first_name, c.last_name, c.phone, c.email
            FROM VEHICLES v
            JOIN CLIENTS c ON v.client_id = c.client_id
            WHERE v.vehicle_id = %s
        """, (vehicle_id,))
        row = cursor.fetchone()
        vc  = clean_row(dict(zip([d[0] for d in cursor.description], row))) if row else {}

        # Mechanic
        cursor.execute("""
            SELECT e.first_name, e.last_name, p.position_name
            FROM EMPLOYEES e
            JOIN POSITIONS p ON e.position_id = p.position_id
            WHERE e.employee_id = %s
        """, (employee_id,))
        row      = cursor.fetchone()
        mechanic = clean_row(dict(zip([d[0] for d in cursor.description], row))) if row else {}

        # Services
        cursor.execute("""
            SELECT s.service_name, od.applied_price, od.quantity
            FROM ORDER_DETAILS od
            JOIN SERVICES s ON od.service_id = s.service_id
            WHERE od.order_id = %s
        """, (order_id,))
        scols    = [d[0] for d in cursor.description]
        services = [clean_row(dict(zip(scols, r))) for r in cursor.fetchall()]

        # Invoice
        cursor.execute("SELECT * FROM INVOICES WHERE order_id = %s", (order_id,))
        fcols = [d[0] for d in cursor.description]
        frow  = cursor.fetchone()
        invoice = clean_row(dict(zip(fcols, frow))) if frow else None

        # Payments
        payments = []
        if invoice:
            cursor.execute("SELECT * FROM PAYMENTS WHERE invoice_id = %s",
                           (invoice["invoice_id"],))
            pcols    = [d[0] for d in cursor.description]
            payments = [clean_row(dict(zip(pcols, r))) for r in cursor.fetchall()]

        documents.append({
            "order_id_sql": order_id,
            "entry_date":   order["entry_date"],
            "exit_date":    order["exit_date"],
            "status":       order["status"],
            "notes":        order["notes"],
            "vehicle": {
                "make":  vc.get("make"),
                "model": vc.get("model"),
                "year":  vc.get("year"),
                "plate": vc.get("plate"),
                "vin":   vc.get("vin"),
                "color": vc.get("color"),
            },
            "client": {
                "client_id":  vc.get("client_id"),
                "first_name": vc.get("first_name"),
                "last_name":  vc.get("last_name"),
                "phone":      vc.get("phone"),
                "email":      vc.get("email"),
            },
            "mechanic": mechanic,
            "services": services,
            "invoice":  {**invoice, "payments": payments} if invoice else None,
            "metadata": {
                "source":    "motorcraft_db (MySQL)",
                "sync_date": datetime.now().isoformat(),
            },
        })

    n = insert_collection(db, "enriched_orders", documents)
    log.info("  ✓  %-28s %4d docs", "enriched_orders", n)


# ── Step 2b: Clients with history ────────────────────────────
def clone_clients_history(cursor, db):
    log.info("─── Step 2b: Clients with history ───")

    cursor.execute("SELECT * FROM CLIENTS")
    cols    = [d[0] for d in cursor.description]
    clients = [clean_row(dict(zip(cols, r))) for r in cursor.fetchall()]

    documents = []
    for client in clients:
        cursor.execute("SELECT * FROM VEHICLES WHERE client_id = %s",
                       (client["client_id"],))
        vcols    = [d[0] for d in cursor.description]
        vehicles = [clean_row(dict(zip(vcols, r))) for r in cursor.fetchall()]

        for vehicle in vehicles:
            cursor.execute("""
                SELECT wo.order_id, wo.entry_date, wo.exit_date,
                       wo.status, wo.notes,
                       GROUP_CONCAT(s.service_name SEPARATOR ', ') AS services,
                       SUM(od.applied_price * od.quantity)          AS total_cost
                FROM WORK_ORDERS wo
                LEFT JOIN ORDER_DETAILS od ON wo.order_id   = od.order_id
                LEFT JOIN SERVICES s       ON od.service_id = s.service_id
                WHERE wo.vehicle_id = %s
                GROUP BY wo.order_id
                ORDER BY wo.entry_date DESC
            """, (vehicle["vehicle_id"],))
            ocols = [d[0] for d in cursor.description]
            vehicle["service_history"] = [
                clean_row(dict(zip(ocols, r))) for r in cursor.fetchall()
            ]

        documents.append({
            **client,
            "vehicles": vehicles,
            "metadata": {
                "source":    "motorcraft_db (MySQL)",
                "sync_date": datetime.now().isoformat(),
            },
        })

    n = insert_collection(db, "clients_history", documents)
    log.info("  ✓  %-28s %4d docs", "clients_history", n)


# ── Step 2c: Suppliers with purchases ────────────────────────
def clone_suppliers_purchases(cursor, db):
    log.info("─── Step 2c: Suppliers with purchases ───")

    cursor.execute("SELECT * FROM SUPPLIERS")
    cols      = [d[0] for d in cursor.description]
    suppliers = [clean_row(dict(zip(cols, r))) for r in cursor.fetchall()]

    documents = []
    for supplier in suppliers:
        cursor.execute("SELECT * FROM PURCHASES WHERE supplier_id = %s",
                       (supplier["supplier_id"],))
        ccols     = [d[0] for d in cursor.description]
        purchases = [clean_row(dict(zip(ccols, r))) for r in cursor.fetchall()]

        for purchase in purchases:
            cursor.execute("SELECT * FROM PURCHASE_DETAILS WHERE purchase_id = %s",
                           (purchase["purchase_id"],))
            dcols = [d[0] for d in cursor.description]
            purchase["details"] = [
                clean_row(dict(zip(dcols, r))) for r in cursor.fetchall()
            ]

        documents.append({
            **supplier,
            "purchases": purchases,
            "metadata": {
                "source":    "motorcraft_db (MySQL)",
                "sync_date": datetime.now().isoformat(),
            },
        })

    n = insert_collection(db, "suppliers_purchases", documents)
    log.info("  ✓  %-28s %4d docs", "suppliers_purchases", n)


# ── Step 3: MongoDB indexes ───────────────────────────────────
def create_indexes(db):
    log.info("─── Step 3: Creating indexes ───")
    db["clients"].create_index([("client_id", ASCENDING)],       unique=True)
    db["vehicles"].create_index([("plate", ASCENDING)],          unique=True)
    db["work_orders"].create_index([("order_id", ASCENDING)],    unique=True)
    db["work_orders"].create_index([("status", ASCENDING)])
    db["invoices"].create_index([("invoice_id", ASCENDING)],     unique=True)
    db["enriched_orders"].create_index([("order_id_sql", ASCENDING)], unique=True)
    db["enriched_orders"].create_index([("vehicle.plate", ASCENDING)])
    db["clients_history"].create_index([("client_id", ASCENDING)],   unique=True)
    db["suppliers_purchases"].create_index([("supplier_id", ASCENDING)], unique=True)
    log.info("  ✓  Indexes created")


# ── Step 4: Final report ──────────────────────────────────────
def final_report(db):
    log.info("─── Collections in %s ───", MONGO_DB)
    total = 0
    for col in sorted(db.list_collection_names()):
        n = db[col].count_documents({})
        total += n
        log.info("  %-32s %4d docs", col, n)
    log.info("  ────────────────────────────────────────────")
    log.info("  Total: %d documents in %d collections", total,
             len(db.list_collection_names()))


# ── MAIN ──────────────────────────────────────────────────────
def main():
    start = datetime.now()
    log.info("═" * 50)
    log.info("  MotorCraft — Clone MySQL → MongoDB")
    log.info("  %s", start.strftime("%Y-%m-%d %H:%M:%S"))
    log.info("═" * 50)

    mysql_conn = connect_mysql()
    mongo_cli, db = connect_mongo()

    try:
        cursor = mysql_conn.cursor()
        clone_tables(cursor, db)
        clone_enriched_orders(cursor, db)
        clone_clients_history(cursor, db)
        clone_suppliers_purchases(cursor, db)
        create_indexes(db)
        final_report(db)
    except Exception as err:
        log.error("Error: %s", err, exc_info=True)
        sys.exit(1)
    finally:
        cursor.close()
        mysql_conn.close()
        mongo_cli.close()

    seconds = (datetime.now() - start).total_seconds()
    log.info("═" * 50)
    log.info("  Completed in %.2f seconds", seconds)
    log.info("═" * 50)


if __name__ == "__main__":
    main()
