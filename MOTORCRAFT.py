"""
MotorCraft — Clonación MySQL → MongoDB
Ejecutar en PyCharm: clic derecho → Run 'clonar_mysql_mongodb'
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

# ── Cargar .env ───────────────────────────────────────────────
load_dotenv()

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "DB_MOTORCRAFT"),
    "charset": "utf8mb4",
}

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "uabcdb")


# ── Utilidades ────────────────────────────────────────────────
def serializar(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return obj


def limpiar_fila(fila: dict) -> dict:
    return {k: serializar(v) for k, v in fila.items()}


def obtener_filas(cursor, tabla: str) -> list:
    cursor.execute(f"SELECT * FROM {tabla}")
    columnas = [d[0] for d in cursor.description]
    return [limpiar_fila(dict(zip(columnas, f))) for f in cursor.fetchall()]


def insertar_coleccion(db, nombre: str, documentos: list) -> int:
    if not documentos:
        log.warning("  ⚠  %-28s sin datos, se omite.", nombre)
        return 0
    col = db[nombre]
    col.drop()
    resultado = col.insert_many(documentos, ordered=False)
    return len(resultado.inserted_ids)


# ── Conexiones ────────────────────────────────────────────────
def conectar_mysql():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        log.info("✓ MySQL conectado — base: %s", MYSQL_CONFIG["database"])
        return conn
    except mysql.connector.Error as err:
        log.error("✗ MySQL — %s", err)
        sys.exit(1)


def conectar_mongo():
    try:
        cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        cliente.admin.command("ping")
        db = cliente[MONGO_DB]
        log.info("✓ MongoDB conectado — base: %s", MONGO_DB)
        return cliente, db
    except ConnectionFailure as err:
        log.error("✗ MongoDB — %s", err)
        sys.exit(1)


# ── Paso 1: Clonar tablas directamente ───────────────────────
TABLAS = [
    "PUESTOS", "EMPLEADOS", "NOMINA",
    "CLIENTES", "VEHICULOS",
    "SERVICIOS", "ORDENES_TRABAJO", "DETALLE_ORDEN",
    "FACTURAS", "PAGOS",
    "PROVEEDORES", "COMPRAS", "DETALLE_COMPRA",
    "ROLES", "USUARIOS", "AUDIT_LOG",
]


def clonar_tablas(cursor, db):
    log.info("─── Paso 1: Clonando tablas → colecciones ───")
    total = 0
    for tabla in TABLAS:
        try:
            filas = obtener_filas(cursor, tabla)
            n = insertar_coleccion(db, tabla.lower(), filas)
            log.info("  ✓  %-28s %4d docs", tabla, n)
            total += n
        except Exception as e:
            log.warning("  ⚠  %-28s omitida: %s", tabla, e)
    log.info("  Subtotal espejo: %d documentos", total)


# ── Paso 2a: Órdenes enriquecidas ────────────────────────────
def clonar_ordenes_enriquecidas(cursor, db):
    log.info("─── Paso 2a: Órdenes enriquecidas ───")

    cursor.execute("SELECT * FROM ORDENES_TRABAJO")
    cols = [d[0] for d in cursor.description]
    ordenes = [limpiar_fila(dict(zip(cols, f))) for f in cursor.fetchall()]

    documentos = []
    for orden in ordenes:
        id_orden = orden["id_orden"]
        id_vehiculo = orden["id_vehiculo"]
        id_empleado = orden["id_empleado"]

        # Vehículo + cliente
        cursor.execute("""
            SELECT v.*, c.nombre, c.apellido, c.telefono, c.email
            FROM VEHICULOS v
            JOIN CLIENTES c ON v.id_cliente = c.id_cliente
            WHERE v.id_vehiculo = %s
        """, (id_vehiculo,))
        vc = limpiar_fila(dict(zip([d[0] for d in cursor.description],
                                   cursor.fetchone() or []))) if cursor.rowcount else {}

        # Mecánico
        cursor.execute("""
            SELECT e.nombre, e.apellido, p.nombre_puesto
            FROM EMPLEADOS e JOIN PUESTOS p ON e.id_puesto = p.id_puesto
            WHERE e.id_empleado = %s
        """, (id_empleado,))
        fila = cursor.fetchone()
        mecanico = limpiar_fila(dict(zip([d[0] for d in cursor.description],
                                         fila))) if fila else {}

        # Servicios
        cursor.execute("""
            SELECT s.nombre_servicio, do.precio_aplicado, do.cantidad
            FROM DETALLE_ORDEN do
            JOIN SERVICIOS s ON do.id_servicio = s.id_servicio
            WHERE do.id_orden = %s
        """, (id_orden,))
        scols = [d[0] for d in cursor.description]
        servicios = [limpiar_fila(dict(zip(scols, f))) for f in cursor.fetchall()]

        # Factura
        cursor.execute("SELECT * FROM FACTURAS WHERE id_orden = %s", (id_orden,))
        fcols = [d[0] for d in cursor.description]
        ffila = cursor.fetchone()
        factura = limpiar_fila(dict(zip(fcols, ffila))) if ffila else None

        # Pagos
        pagos = []
        if factura:
            cursor.execute("SELECT * FROM PAGOS WHERE id_factura = %s",
                           (factura["id_factura"],))
            pcols = [d[0] for d in cursor.description]
            pagos = [limpiar_fila(dict(zip(pcols, f))) for f in cursor.fetchall()]

        documentos.append({
            "id_orden_sql": id_orden,
            "fecha_entrada": orden["fecha_entrada"],
            "fecha_salida": orden["fecha_salida"],
            "estatus": orden["estatus"],
            "observaciones": orden["observaciones"],
            "vehiculo": {
                "marca": vc.get("marca"),
                "modelo": vc.get("modelo"),
                "anio": vc.get("anio"),
                "placa": vc.get("placa"),
                "vin": vc.get("vin"),
                "color": vc.get("color"),
            },
            "cliente": {
                "id_cliente": vc.get("id_cliente"),
                "nombre": vc.get("nombre"),
                "apellido": vc.get("apellido"),
                "telefono": vc.get("telefono"),
                "email": vc.get("email"),
            },
            "mecanico": mecanico,
            "servicios": servicios,
            "factura": {**factura, "pagos": pagos} if factura else None,
            "metadata": {
                "fuente": "motorcraft_db (MySQL)",
                "fecha_sync": datetime.now().isoformat(),
            },
        })

    n = insertar_coleccion(db, "ordenes_enriquecidas", documentos)
    log.info("  ✓  %-28s %4d docs", "ordenes_enriquecidas", n)


# ── Paso 2b: Clientes con historial ──────────────────────────
def clonar_clientes_historial(cursor, db):
    log.info("─── Paso 2b: Clientes con historial ───")

    cursor.execute("SELECT * FROM CLIENTES")
    cols = [d[0] for d in cursor.description]
    clientes = [limpiar_fila(dict(zip(cols, f))) for f in cursor.fetchall()]

    documentos = []
    for cli in clientes:
        cursor.execute("SELECT * FROM VEHICULOS WHERE id_cliente = %s",
                       (cli["id_cliente"],))
        vcols = [d[0] for d in cursor.description]
        vehiculos = [limpiar_fila(dict(zip(vcols, f))) for f in cursor.fetchall()]

        for veh in vehiculos:
            cursor.execute("""
                SELECT ot.id_orden, ot.fecha_entrada, ot.fecha_salida,
                       ot.estatus, ot.observaciones,
                       GROUP_CONCAT(s.nombre_servicio SEPARATOR ', ') AS servicios,
                       SUM(do.precio_aplicado * do.cantidad)          AS costo_total
                FROM ORDENES_TRABAJO ot
                LEFT JOIN DETALLE_ORDEN do ON ot.id_orden    = do.id_orden
                LEFT JOIN SERVICIOS s      ON do.id_servicio = s.id_servicio
                WHERE ot.id_vehiculo = %s
                GROUP BY ot.id_orden
                ORDER BY ot.fecha_entrada DESC
            """, (veh["id_vehiculo"],))
            ocols = [d[0] for d in cursor.description]
            veh["historial_servicios"] = [
                limpiar_fila(dict(zip(ocols, f))) for f in cursor.fetchall()
            ]

        documentos.append({
            **cli,
            "vehiculos": vehiculos,
            "metadata": {
                "fuente": "motorcraft_db (MySQL)",
                "fecha_sync": datetime.now().isoformat(),
            },
        })

    n = insertar_coleccion(db, "clientes_historial", documentos)
    log.info("  ✓  %-28s %4d docs", "clientes_historial", n)


# ── Paso 2c: Proveedores con compras ─────────────────────────
def clonar_proveedores_compras(cursor, db):
    log.info("─── Paso 2c: Proveedores con compras ───")

    cursor.execute("SELECT * FROM PROVEEDORES")
    cols = [d[0] for d in cursor.description]
    proveedores = [limpiar_fila(dict(zip(cols, f))) for f in cursor.fetchall()]

    documentos = []
    for prov in proveedores:
        cursor.execute("SELECT * FROM COMPRAS WHERE id_proveedor = %s",
                       (prov["id_proveedor"],))
        ccols = [d[0] for d in cursor.description]
        compras = [limpiar_fila(dict(zip(ccols, f))) for f in cursor.fetchall()]

        for compra in compras:
            cursor.execute("SELECT * FROM DETALLE_COMPRA WHERE id_compra = %s",
                           (compra["id_compra"],))
            dcols = [d[0] for d in cursor.description]
            compra["detalle"] = [
                limpiar_fila(dict(zip(dcols, f))) for f in cursor.fetchall()
            ]

        documentos.append({
            **prov,
            "compras": compras,
            "metadata": {
                "fuente": "motorcraft_db (MySQL)",
                "fecha_sync": datetime.now().isoformat(),
            },
        })

    n = insertar_coleccion(db, "proveedores_compras", documentos)
    log.info("  ✓  %-28s %4d docs", "proveedores_compras", n)


# ── Paso 3: Índices MongoDB ───────────────────────────────────
def crear_indices(db):
    log.info("─── Paso 3: Creando índices ───")
    db["clientes"].create_index([("id_cliente", ASCENDING)], unique=True)
    db["vehiculos"].create_index([("placa", ASCENDING)], unique=True)
    db["ordenes_trabajo"].create_index([("id_orden", ASCENDING)], unique=True)
    db["ordenes_trabajo"].create_index([("estatus", ASCENDING)])
    db["facturas"].create_index([("id_factura", ASCENDING)], unique=True)
    db["ordenes_enriquecidas"].create_index([("id_orden_sql", ASCENDING)], unique=True)
    db["ordenes_enriquecidas"].create_index([("vehiculo.placa", ASCENDING)])
    db["clientes_historial"].create_index([("id_cliente", ASCENDING)], unique=True)
    db["proveedores_compras"].create_index([("id_proveedor", ASCENDING)], unique=True)
    log.info("  ✓  Índices creados")


# ── Paso 4: Reporte final ─────────────────────────────────────
def reporte_final(db):
    log.info("─── Colecciones en %s ───", MONGO_DB)
    total = 0
    for col in sorted(db.list_collection_names()):
        n = db[col].count_documents({})
        total += n
        log.info("  %-32s %4d docs", col, n)
    log.info("  ────────────────────────────────────────────")
    log.info("  Total: %d documentos en %d colecciones", total,
             len(db.list_collection_names()))


# ── MAIN ──────────────────────────────────────────────────────
def main():
    inicio = datetime.now()
    log.info("═" * 50)
    log.info("  MotorCraft — Clonación MySQL → MongoDB")
    log.info("  %s", inicio.strftime("%Y-%m-%d %H:%M:%S"))
    log.info("═" * 50)

    mysql_conn = conectar_mysql()
    mongo_cli, db = conectar_mongo()

    try:
        cursor = mysql_conn.cursor()
        clonar_tablas(cursor, db)
        clonar_ordenes_enriquecidas(cursor, db)
        clonar_clientes_historial(cursor, db)
        clonar_proveedores_compras(cursor, db)
        crear_indices(db)
        reporte_final(db)
    except Exception as err:
        log.error("Error: %s", err, exc_info=True)
        sys.exit(1)
    finally:
        cursor.close()
        mysql_conn.close()
        mongo_cli.close()

    segundos = (datetime.now() - inicio).total_seconds()
    log.info("═" * 50)
    log.info("  Completado en %.2f segundos", segundos)
    log.info("═" * 50)


if __name__ == "__main__":
    main()