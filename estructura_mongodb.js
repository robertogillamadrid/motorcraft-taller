// ============================================================
//  MotorCraft — Fase 5a: Estructura MongoDB Nativa
//  Base de datos: uabcdb
//  Ejecutar en: MongoDB Shell (mongosh) o MongoDB Compass
// ============================================================

use("uabcdb");

// ─────────────────────────────────────────────────────────────
// COLECCIÓN 1: inventario_piezas
// Piezas y herramientas con especificaciones variables
// por marca y modelo de vehículo
// ─────────────────────────────────────────────────────────────
db.createCollection("inventario_piezas", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["codigo", "nombre", "categoria", "stock", "precio_unitario"],
      properties: {
        codigo:          { bsonType: "string",  description: "Código único de la pieza" },
        nombre:          { bsonType: "string",  description: "Nombre descriptivo" },
        categoria:       { bsonType: "string",  description: "Aceite, Frenos, Suspensión, etc." },
        stock:           { bsonType: "int",     minimum: 0 },
        stock_minimo:    { bsonType: "int",     minimum: 0 },
        precio_unitario: { bsonType: "double",  minimum: 0 },
        compatibilidad:  { bsonType: "array",   description: "Lista de vehículos compatibles" },
        especificaciones:{ bsonType: "object",  description: "Specs técnicas variables por pieza" },
      }
    }
  }
});

// Documentos de ejemplo — inventario_piezas
db.inventario_piezas.insertMany([
  {
    codigo:          "ACE-5W30-001",
    nombre:          "Aceite sintético 5W-30 1L",
    categoria:       "Lubricantes",
    marca_producto:  "Mobil 1",
    stock:           48,
    stock_minimo:    12,
    precio_unitario: 95.00,
    unidad:          "litro",
    compatibilidad: [
      { marca: "Toyota",    modelos: ["Corolla", "Camry", "RAV4"] },
      { marca: "Honda",     modelos: ["Civic", "Accord", "CRV"] },
      { marca: "Nissan",    modelos: ["Sentra", "Altima", "Versa"] },
    ],
    especificaciones: {
      viscosidad:       "5W-30",
      tipo:             "Sintético",
      norma_api:        "SN Plus",
      intervalo_cambio: "8000 km",
      volumen_motor:    "hasta 4.0L",
    },
    proveedor: {
      id_proveedor_sql: 1,
      nombre:           "Refacciones del Norte SA",
    },
    fecha_ultimo_ingreso: new Date("2025-05-08"),
    activo: true,
  },
  {
    codigo:          "FRE-PAS-002",
    nombre:          "Pastillas de freno Brembo delanteras",
    categoria:       "Frenos",
    marca_producto:  "Brembo",
    stock:           16,
    stock_minimo:    4,
    precio_unitario: 520.00,
    unidad:          "juego",
    compatibilidad: [
      { marca: "Volkswagen", modelos: ["Jetta", "Golf", "Tiguan"], anios: [2018, 2019, 2020, 2021, 2022] },
      { marca: "Audi",       modelos: ["A3", "A4"],                anios: [2018, 2019, 2020] },
    ],
    especificaciones: {
      material:          "Semimetálico",
      espesor_mm:        12,
      ancho_mm:          65,
      alto_mm:           55,
      incluye_sensores:  true,
      temperatura_max:   "650°C",
    },
    proveedor: {
      id_proveedor_sql: 2,
      nombre:           "AutoPartes Baja SA de CV",
    },
    fecha_ultimo_ingreso: new Date("2025-05-09"),
    activo: true,
  },
  {
    codigo:          "SUS-AMO-003",
    nombre:          "Amortiguador delantero KYB",
    categoria:       "Suspensión",
    marca_producto:  "KYB",
    stock:           8,
    stock_minimo:    2,
    precio_unitario: 950.00,
    unidad:          "pieza",
    compatibilidad: [
      { marca: "Chevrolet", modelos: ["Aveo", "Spark"], anios: [2016, 2017, 2018, 2019, 2020] },
      { marca: "Toyota",    modelos: ["Yaris"],          anios: [2016, 2017, 2018] },
    ],
    especificaciones: {
      tipo:             "Hidráulico",
      posicion:         "Delantero derecho / izquierdo",
      longitud_mm:      380,
      diametro_mm:      46,
      presion_bar:      20,
      garantia_km:      80000,
    },
    proveedor: {
      id_proveedor_sql: 2,
      nombre:           "AutoPartes Baja SA de CV",
    },
    fecha_ultimo_ingreso: new Date("2025-05-09"),
    activo: true,
  },
  {
    codigo:          "ELE-BUJ-004",
    nombre:          "Bujías NGK Iridium set x4",
    categoria:       "Encendido",
    marca_producto:  "NGK",
    stock:           40,
    stock_minimo:    8,
    precio_unitario: 240.00,
    unidad:          "set",
    compatibilidad: [
      { marca: "Toyota",  modelos: ["Corolla", "Camry"],     anios: [2018, 2019, 2020, 2021, 2022] },
      { marca: "Honda",   modelos: ["Civic", "Accord"],      anios: [2019, 2020, 2021, 2022] },
      { marca: "Nissan",  modelos: ["Sentra", "Altima"],     anios: [2018, 2019, 2020] },
    ],
    especificaciones: {
      tipo:             "Iridium",
      gap_mm:           1.1,
      rosca:            "M14 x 1.25",
      longitud_mm:      26.5,
      intervalo_cambio: "100,000 km",
      voltaje_max:      "40,000V",
    },
    proveedor: {
      id_proveedor_sql: 3,
      nombre:           "Distribuidora Moto-Tech",
    },
    fecha_ultimo_ingreso: new Date("2025-05-15"),
    activo: true,
  },
  {
    codigo:          "ELE-BAT-005",
    nombre:          "Batería Optima 12V 65Ah",
    categoria:       "Eléctrico",
    marca_producto:  "Optima",
    stock:           6,
    stock_minimo:    2,
    precio_unitario: 1850.00,
    unidad:          "pieza",
    compatibilidad: [
      { marca: "Ford",       modelos: ["Mustang", "F-150"],  anios: [2020, 2021, 2022, 2023] },
      { marca: "Chevrolet",  modelos: ["Silverado", "Tahoe"],anios: [2019, 2020, 2021, 2022] },
    ],
    especificaciones: {
      voltaje:          12,
      capacidad_ah:     65,
      cca:              750,
      tipo:             "AGM Espiral",
      terminales:       "SAE estándar",
      garantia_meses:   36,
      peso_kg:          21.5,
    },
    proveedor: {
      id_proveedor_sql: 1,
      nombre:           "Refacciones del Norte SA",
    },
    fecha_ultimo_ingreso: new Date("2025-05-08"),
    activo: true,
  },
]);

// ─────────────────────────────────────────────────────────────
// COLECCIÓN 2: bitacoras_reparacion
// Registro detallado de diagnósticos con esquema flexible
// ─────────────────────────────────────────────────────────────
db.createCollection("bitacoras_reparacion");

db.bitacoras_reparacion.insertMany([
  {
    id_orden_sql:   1,
    placa:          "ABC1234",
    vehiculo:       "Toyota Corolla 2019",
    mecanico:       "Jorge Ramírez",
    fecha:          new Date("2025-05-10"),
    tipo_servicio:  "Mantenimiento preventivo",
    diagnostico: {
      codigo_obd:      [],
      descripcion:     "Vehículo en buenas condiciones generales. Aceite muy oscuro.",
      nivel_urgencia:  "Bajo",
      sistemas_revisados: ["Motor", "Frenos", "Luces", "Niveles de fluidos"],
    },
    trabajos_realizados: [
      { tarea: "Cambio de aceite 5W-30",   completada: true,  tiempo_min: 20 },
      { tarea: "Cambio de filtro de aceite",completada: true,  tiempo_min: 10 },
      { tarea: "Revisión de frenos",        completada: true,  tiempo_min: 15 },
      { tarea: "Inflado de llantas",        completada: true,  tiempo_min: 10 },
    ],
    piezas_usadas: [
      { ref_mongo: "ACE-5W30-001", descripcion: "Aceite 5W-30", cantidad: 4, costo: 380.00 },
    ],
    recomendaciones: [
      "Cambio de batería en próxima visita — 3 años de uso",
      "Revisar pastillas de freno trasero en 5,000 km",
    ],
    multimedia: [],
    firma_cliente: true,
    calificacion:  5,
  },
  {
    id_orden_sql:   2,
    placa:          "GHI9012",
    vehiculo:       "Nissan Sentra 2020",
    mecanico:       "Luis Pérez",
    fecha:          new Date("2025-05-11"),
    tipo_servicio:  "Corrección de frenos",
    diagnostico: {
      codigo_obd:      ["C1130", "C1132"],
      descripcion:     "Ruido metálico al frenar. Pastillas desgastadas al límite.",
      nivel_urgencia:  "Alto",
      sistemas_revisados: ["Frenos", "Suspensión"],
    },
    trabajos_realizados: [
      { tarea: "Cambio pastillas delanteras", completada: true,  tiempo_min: 60 },
      { tarea: "Sangrado de frenos",          completada: true,  tiempo_min: 30 },
      { tarea: "Diagnóstico OBD2",            completada: true,  tiempo_min: 20 },
      { tarea: "Revisión amortiguadores",     completada: false, tiempo_min: 0,
        motivo_pendiente: "Sin tiempo — programar cita" },
    ],
    piezas_usadas: [
      { ref_mongo: "FRE-PAS-002", descripcion: "Pastillas Brembo", cantidad: 1, costo: 520.00 },
    ],
    recomendaciones: [
      "Programar revisión de amortiguadores urgente",
      "Discos de freno con desgaste — cambio en 10,000 km máximo",
    ],
    multimedia: [
      { tipo: "foto", nombre: "disco_desgastado.jpg", url: "/media/ordenes/2/disco_desgastado.jpg" },
    ],
    firma_cliente: true,
    calificacion:  4,
  },
]);

// ─────────────────────────────────────────────────────────────
// ÍNDICES para las colecciones nativas
// ─────────────────────────────────────────────────────────────
db.inventario_piezas.createIndex({ codigo: 1 },           { unique: true });
db.inventario_piezas.createIndex({ categoria: 1 });
db.inventario_piezas.createIndex({ "compatibilidad.marca": 1 });
db.inventario_piezas.createIndex({ stock: 1 });

db.bitacoras_reparacion.createIndex({ id_orden_sql: 1 },  { unique: true });
db.bitacoras_reparacion.createIndex({ placa: 1 });
db.bitacoras_reparacion.createIndex({ fecha: -1 });
db.bitacoras_reparacion.createIndex({ "diagnostico.nivel_urgencia": 1 });

print("✓ Colecciones nativas creadas correctamente en uabcdb");
print("✓ Índices aplicados");
