// ============================================================
//  MotorCraft — MongoDB Structure (English)
//  Database: motorcraft_db_mongo
// ============================================================

use("motorcraft_db_mongo");

// Drop existing collections to start fresh
db.parts_inventory.drop();
db.repair_logs.drop();

// ─────────────────────────────────────────────────────────────
// COLLECTION 1: parts_inventory
// ─────────────────────────────────────────────────────────────
db.createCollection("parts_inventory");

db.parts_inventory.insertMany([
  {
    code:          "OIL-5W30-001",
    name:          "Synthetic Oil 5W-30 1L",
    category:      "Lubricants",
    brand:         "Mobil 1",
    stock:         48,
    min_stock:     12,
    unit_price:    95.00,
    unit:          "liter",
    compatibility: [
      { make: "Toyota",  models: ["Corolla", "Camry", "RAV4"] },
      { make: "Honda",   models: ["Civic", "Accord", "CRV"] },
      { make: "Nissan",  models: ["Sentra", "Altima", "Versa"] }
    ],
    specifications: {
      viscosity:        "5W-30",
      type:             "Synthetic",
      api_standard:     "SN Plus",
      change_interval:  "8000 km",
      engine_volume:    "up to 4.0L"
    },
    supplier: { supplier_id_sql: 1, name: "Northern Parts Inc" },
    last_received_date: new Date("2025-05-08"),
    active: true
  },
  {
    code:          "BRK-PAD-002",
    name:          "Brembo Front Brake Pads",
    category:      "Brakes",
    brand:         "Brembo",
    stock:         16,
    min_stock:     4,
    unit_price:    520.00,
    unit:          "set",
    compatibility: [
      { make: "Volkswagen", models: ["Jetta", "Golf", "Tiguan"], years: [2018, 2019, 2020, 2021, 2022] },
      { make: "Audi",       models: ["A3", "A4"],                years: [2018, 2019, 2020] }
    ],
    specifications: {
      material:          "Semi-metallic",
      thickness_mm:      12,
      width_mm:          65,
      height_mm:         55,
      includes_sensors:  true,
      max_temperature:   "650°C"
    },
    supplier: { supplier_id_sql: 2, name: "Baja Auto Parts SA" },
    last_received_date: new Date("2025-05-09"),
    active: true
  },
  {
    code:          "SUS-SHK-003",
    name:          "KYB Front Shock Absorber",
    category:      "Suspension",
    brand:         "KYB",
    stock:         8,
    min_stock:     2,
    unit_price:    950.00,
    unit:          "piece",
    compatibility: [
      { make: "Chevrolet", models: ["Aveo", "Spark"], years: [2016, 2017, 2018, 2019, 2020] },
      { make: "Toyota",    models: ["Yaris"],          years: [2016, 2017, 2018] }
    ],
    specifications: {
      type:         "Hydraulic",
      position:     "Front right / left",
      length_mm:    380,
      diameter_mm:  46,
      pressure_bar: 20,
      warranty_km:  80000
    },
    supplier: { supplier_id_sql: 2, name: "Baja Auto Parts SA" },
    last_received_date: new Date("2025-05-09"),
    active: true
  },
  {
    code:          "ELE-SPK-004",
    name:          "NGK Iridium Spark Plugs set x4",
    category:      "Ignition",
    brand:         "NGK",
    stock:         40,
    min_stock:     8,
    unit_price:    240.00,
    unit:          "set",
    compatibility: [
      { make: "Toyota", models: ["Corolla", "Camry"],  years: [2018, 2019, 2020, 2021, 2022] },
      { make: "Honda",  models: ["Civic", "Accord"],   years: [2019, 2020, 2021, 2022] },
      { make: "Nissan", models: ["Sentra", "Altima"],  years: [2018, 2019, 2020] }
    ],
    specifications: {
      type:            "Iridium",
      gap_mm:          1.1,
      thread:          "M14 x 1.25",
      length_mm:       26.5,
      change_interval: "100,000 km",
      max_voltage:     "40,000V"
    },
    supplier: { supplier_id_sql: 3, name: "Moto-Tech Distributor" },
    last_received_date: new Date("2025-05-15"),
    active: true
  },
  {
    code:          "ELE-BAT-005",
    name:          "Optima 12V 65Ah Battery",
    category:      "Electrical",
    brand:         "Optima",
    stock:         6,
    min_stock:     2,
    unit_price:    1850.00,
    unit:          "piece",
    compatibility: [
      { make: "Ford",      models: ["Mustang", "F-150"],   years: [2020, 2021, 2022, 2023] },
      { make: "Chevrolet", models: ["Silverado", "Tahoe"], years: [2019, 2020, 2021, 2022] }
    ],
    specifications: {
      voltage:         12,
      capacity_ah:     65,
      cca:             750,
      type:            "AGM Spiral",
      terminals:       "Standard SAE",
      warranty_months: 36,
      weight_kg:       21.5
    },
    supplier: { supplier_id_sql: 1, name: "Northern Parts Inc" },
    last_received_date: new Date("2025-05-08"),
    active: true
  }
]);

// ─────────────────────────────────────────────────────────────
// COLLECTION 2: repair_logs
// ─────────────────────────────────────────────────────────────
db.createCollection("repair_logs");

db.repair_logs.insertMany([
  {
    order_id_sql:  1,
    plate:         "ABC1234",
    vehicle:       "Toyota Corolla 2019",
    mechanic:      "Jorge Ramirez",
    date:          new Date("2025-05-10"),
    service_type:  "Preventive maintenance",
    diagnosis: {
      obd_codes:       [],
      description:     "Vehicle in good overall condition. Oil very dark.",
      urgency_level:   "Low",
      systems_checked: ["Engine", "Brakes", "Lights", "Fluid levels"]
    },
    work_performed: [
      { task: "Oil change 5W-30",       completed: true, time_min: 20 },
      { task: "Oil filter replacement",  completed: true, time_min: 10 },
      { task: "Brake inspection",        completed: true, time_min: 15 },
      { task: "Tire inflation",          completed: true, time_min: 10 }
    ],
    parts_used: [
      { mongo_ref: "OIL-5W30-001", description: "5W-30 Oil", quantity: 4, cost: 380.00 }
    ],
    recommendations: [
      "Battery replacement at next visit — 3 years of use",
      "Check rear brake pads at 5,000 km"
    ],
    media:            [],
    client_signature: true,
    rating:           5
  },
  {
    order_id_sql:  2,
    plate:         "GHI9012",
    vehicle:       "Nissan Sentra 2020",
    mechanic:      "Luis Perez",
    date:          new Date("2025-05-11"),
    service_type:  "Brake correction",
    diagnosis: {
      obd_codes:       ["C1130", "C1132"],
      description:     "Metal noise when braking. Pads worn to the limit.",
      urgency_level:   "High",
      systems_checked: ["Brakes", "Suspension"]
    },
    work_performed: [
      { task: "Front brake pad replacement", completed: true,  time_min: 60 },
      { task: "Brake bleeding",              completed: true,  time_min: 30 },
      { task: "OBD2 diagnostics",            completed: true,  time_min: 20 },
      { task: "Shock absorber inspection",   completed: false, time_min: 0,
        pending_reason: "No time — schedule appointment" }
    ],
    parts_used: [
      { mongo_ref: "BRK-PAD-002", description: "Brembo Pads", quantity: 1, cost: 520.00 }
    ],
    recommendations: [
      "Schedule shock absorber inspection urgently",
      "Rotors worn — replace within 10,000 km max"
    ],
    media: [
      { type: "photo", name: "worn_rotor.jpg", url: "/media/orders/2/worn_rotor.jpg" }
    ],
    client_signature: true,
    rating: 4
  }
]);

// ─────────────────────────────────────────────────────────────
// INDEXES
// ─────────────────────────────────────────────────────────────
db.parts_inventory.createIndex({ code: 1 },                 { unique: true });
db.parts_inventory.createIndex({ category: 1 });
db.parts_inventory.createIndex({ "compatibility.make": 1 });
db.parts_inventory.createIndex({ stock: 1 });

db.repair_logs.createIndex({ order_id_sql: 1 },             { unique: true });
db.repair_logs.createIndex({ plate: 1 });
db.repair_logs.createIndex({ date: -1 });
db.repair_logs.createIndex({ "diagnosis.urgency_level": 1 });

print("✓ Collections created successfully in motorcraft_db_mongo");
print("✓ Indexes applied");
