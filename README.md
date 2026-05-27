# ⚙ MotorCraft — Auto Shop Management System

A full-stack management system for auto repair shops, built with Python, Flask, MySQL, and MongoDB.

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| GUI | Python + CustomTkinter |
| API | Flask + REST |
| Relational DB | MySQL 8.0 |
| NoSQL DB | MongoDB |
| Auth | JWT Tokens |
| Cache | Flask-Caching |

## 📋 Features

- **Work Orders** — create, track and update repair orders by status
- **Clients & Vehicles** — register and search clients and their vehicles
- **Parts Inventory** — MongoDB-based inventory with low stock alerts
- **Billing & Payments** — invoices generated via stored procedures, payment tracking
- **Reports & Charts** — revenue by period, top services with bar charts
- **Accounts Receivable** — pending invoices with days unpaid
- **Audit Log** — full record of all database changes (ADMIN only)
- **Role-Based Access** — 4 roles with different permissions

## 🔐 Roles & Permissions

| Role | Access |
|---|---|
| ADMIN | Full access |
| MECHANIC | Orders, inventory, vehicles |
| RECEPTIONIST | Clients, vehicles, orders |
| ACCOUNTING | Reports, payments, clients |

## 🗄 Database Architecture

- **MySQL** — clients, vehicles, work orders, invoices, payments, employees, payroll, suppliers
- **MongoDB** — parts inventory, repair logs, enriched orders, client history
- **Stored Procedures** — all business logic (10 SPs)
- **Triggers** — audit logging on all critical tables (9 triggers)
- **Views** — 8 views for reports and dashboards

## 🚀 Installation

### Requirements

```bash
pip install flask flask-cors flask-caching pymongo mysql-connector-python python-dotenv PyJWT customtkinter matplotlib pillow requests
```

### Setup

1. Clone the repository
```bash
git clone https://github.com/your-username/motorcraft.git
cd motorcraft
```

2. Create a `.env` file
```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=motorcraft_db

MONGO_URI=mongodb://localhost:27017/
MONGO_DB=motorcraft_db_mongo
```

3. Run the SQL scripts in MySQL Workbench in this order
```
DB_MOTORCRAFT_EN.sql
TRIGGERS_MOTORCRAFT_EN.sql
PROCEDURES_MOTORCRAFT_EN.sql
VIEWS_MOTORCRAFT_EN.sql
```

4. Run the MongoDB structure script
```bash
mongosh "mongodb://localhost:27017/motorcraft_db_mongo" "estructura_mongodb_EN.js"
```

5. Start the API
```bash
python app_EN.py
```

6. Start the GUI (in a separate terminal)
```bash
python gui_EN.py
```

## 📁 Project Structure

```
motorcraft/
├── app_EN.py                   # Flask REST API
├── gui_EN.py                   # Desktop GUI (CustomTkinter)
├── MOTORCRAFT_EN.py            # MySQL → MongoDB sync script
├── DB_MOTORCRAFT_EN.sql        # Database schema + seed data
├── PROCEDURES_MOTORCRAFT_EN.sql# Stored procedures
├── TRIGGERS_MOTORCRAFT_EN.sql  # Triggers + audit log
├── VIEWS_MOTORCRAFT_EN.sql     # Views for reports
├── estructura_mongodb_EN.js    # MongoDB collections + indexes
└── .env                        # Environment variables (not committed)
```

## 👤 Authors

Developed as a final project for the Advanced Databases course — UABC, Tijuana B.C.
