"""
Data management and state control for RiceMoto POS.
Acts as a Single Source of Truth.
"""
from PyQt6.QtCore import QObject, pyqtSignal
from .connection import get_connection
import mysql.connector
import hashlib
from decimal import Decimal
from datetime import datetime, timedelta

class DataController(QObject):
    """
    Main Data Controller for the application.
    Handles mock data, user authentication, and state synchronization via signals.
    """
    # Signals for reactive UI updates
    sold_out_changed = pyqtSignal(str, bool)   # (item_name, is_sold_out)
    stock_updated = pyqtSignal(str, int)        # (item_name, new_stock)
    cart_updated = pyqtSignal(list)             # (bin_items)
    order_status_changed = pyqtSignal(str, str) # (order_id, new_status)
    menu_filtered = pyqtSignal(list)            # (filtered_items)

    def __init__(self):
        super().__init__()
        self.conn = None
        self.cursor = None
        self.current_user = None
        self.connect_to_db()

        self._menu = []
        self.load_menu_from_db()

        self._orders = []
        self.load_orders_from_db()
        
        # Mock Staff Data
        self._staff = [
            {"name": "Richnell Capacia",   "initials": "RC", "role": "Head Cashier",  "status": "Active", "color": "#007B6E"},
            {"name": "Necca Nabata","initials": "NN", "role": "Kitchen Lead",  "status": "Active", "color": "#F97316"},
            {"name": "Yzabelle Mercado",    "initials": "YM", "role": "Cashier",       "status": "Active", "color": "#3B82F6"},
        ]
        
        # Mock Audit Trail
        self._audit = [
            {"time": "10:42 AM", "staff": "Richnell Capacia",    "action": "Void Order",       "detail": "Order #1089 — ₱320",       "status": "cancelled"},
            {"time": "10:35 AM", "staff": "Necca Nabata", "action": "Stock Edit",       "detail": "Lechon Kawali –12 pcs",     "status": "completed"},
        ]
        
        self._sales_this_week = [32000, 28500, 41000, 38000, 44200, 52000, 48320]
        self._sales_last_week = [28000, 31000, 35500, 33000, 39000, 47000, 42100]

    # --- Database Initialization ---
    def connect_to_db(self):
        self.conn = get_connection()
        if self.conn:
            self.cursor = self.conn.cursor(dictionary=True)
            self.create_tables()
        else:
            print("Could not establish MySQL connection.")

    def create_tables(self):
        if not self.cursor:
            return

        # ── Core Tables (original, preserved for compatibility) ──────
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                display_name VARCHAR(255) NOT NULL,
                is_active TINYINT(1) DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME NULL
            )
        """)
        self._safe_alter("ALTER TABLE users ADD COLUMN is_active TINYINT(1) DEFAULT 1")

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) UNIQUE,
                emoji VARCHAR(10),
                price DECIMAL(10,2),
                category VARCHAR(100),
                rating DOUBLE,
                sold INT,
                soldout TINYINT(1),
                image_data LONGBLOB DEFAULT NULL
            )
        """)
        self._safe_alter("ALTER TABLE menu DROP COLUMN image_path")
        self._safe_alter("ALTER TABLE menu ADD COLUMN image_data LONGBLOB DEFAULT NULL")
        self._safe_alter("ALTER TABLE menu DROP COLUMN stock")

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_code VARCHAR(64),
                order_type VARCHAR(64),
                status VARCHAR(32) DEFAULT 'pending',
                total DECIMAL(10,2),
                payment_method VARCHAR(255) DEFAULT 'Cash',
                customer_name VARCHAR(255) NULL,
                customer_contact VARCHAR(255) NULL,
                customer_address TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._safe_alter("ALTER TABLE orders ADD COLUMN payment_method VARCHAR(255) DEFAULT 'Cash'")
        self._safe_alter("ALTER TABLE orders ADD COLUMN customer_name VARCHAR(255) NULL")
        self._safe_alter("ALTER TABLE orders ADD COLUMN customer_contact VARCHAR(255) NULL")
        self._safe_alter("ALTER TABLE orders ADD COLUMN customer_address TEXT NULL")
        self._safe_alter("ALTER TABLE orders MODIFY COLUMN customer_name VARCHAR(255) NULL AFTER payment_method")
        self._safe_alter("ALTER TABLE orders MODIFY COLUMN customer_contact VARCHAR(255) NULL AFTER customer_name")
        self._safe_alter("ALTER TABLE orders MODIFY COLUMN customer_address TEXT NULL AFTER customer_contact")
        self._safe_alter("ALTER TABLE orders DROP COLUMN customer_phone")
        self._safe_alter("ALTER TABLE orders DROP COLUMN delivery_address")
        self._safe_alter("ALTER TABLE orders ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        self._safe_alter("ALTER TABLE orders ADD COLUMN delivery_fee DECIMAL(10,2) DEFAULT 0.00")
        self._safe_alter("ALTER TABLE orders ADD COLUMN subtotal DECIMAL(10,2) DEFAULT 0.00")
        self._safe_alter("ALTER TABLE orders ADD COLUMN tax DECIMAL(10,2) DEFAULT 0.00")

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT,
                item_name VARCHAR(255),
                price DECIMAL(10,2),
                qty INT,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                log_type ENUM('activity','error') NOT NULL,
                category VARCHAR(100),
                user VARCHAR(100),
                action VARCHAR(255),
                message TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_supplies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                unit VARCHAR(50) DEFAULT 'pcs',
                quantity DECIMAL(10,2) DEFAULT 0,
                min_stock DECIMAL(10,2) DEFAULT 5,
                notes TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()

        # ── 3NF Normalization: Lookup Tables ────────────────────────
        self._create_lookup_tables()
        # ── 3NF Normalization: FK Columns + Backfill ────────────────
        self._add_fk_columns_and_backfill()
        # ── Data Cleanup: Remove stale customer data ────────────────
        self._cleanup_customer_data()
        # ── 3NF Normalization: Views ────────────────────────────────
        self._create_views()
        # ── Security: Stored Procedures ─────────────────────────────
        self._create_stored_procedures()

        self.conn.commit()

    def _safe_alter(self, sql):
        """Execute an ALTER statement, silently ignoring if it fails (column exists/doesn't exist)."""
        try:
            self.cursor.execute(sql)
        except Exception:
            pass

    def _create_lookup_tables(self):
        """Create reference/lookup tables for 3NF normalization."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE
            ) ENGINE=InnoDB
        """)
        self.cursor.execute("INSERT IGNORE INTO roles (name) VALUES ('manager'), ('staff')")

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE
            ) ENGINE=InnoDB
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_statuses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(32) NOT NULL UNIQUE
            ) ENGINE=InnoDB
        """)
        self.cursor.execute("""
            INSERT IGNORE INTO order_statuses (name) VALUES
                ('pending'),('preparing'),('ready'),('completed'),('cancelled')
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_types (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(64) NOT NULL UNIQUE
            ) ENGINE=InnoDB
        """)
        self.cursor.execute("""
            INSERT IGNORE INTO order_types (name) VALUES
                ('Dine In'),('Take Out'),('Delivery'),('Pickup')
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_methods (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE
            ) ENGINE=InnoDB
        """)
        self.cursor.execute("INSERT IGNORE INTO payment_methods (name) VALUES ('Cash'),('GCash')")

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS units_of_measure (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE
            ) ENGINE=InnoDB
        """)
        self.cursor.execute("""
            INSERT IGNORE INTO units_of_measure (name) VALUES
                ('pcs'),('kg'),('liters'),('packs'),('cans'),('bottles'),('gallons')
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                contact VARCHAR(255),
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_customer_name_contact (name, contact)
            ) ENGINE=InnoDB
        """)
        # Ensure unique index exists on older schemas (safe to re-run)
        self._safe_alter("ALTER TABLE customers ADD UNIQUE INDEX uq_customer_name_contact (name, contact)")

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_trail (
                id INT AUTO_INCREMENT PRIMARY KEY,
                table_name VARCHAR(100) NOT NULL,
                record_id INT NOT NULL,
                action ENUM('INSERT','UPDATE','DELETE') NOT NULL,
                changed_by INT NULL,
                old_values JSON,
                new_values JSON,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
        """)

        # Seed categories from existing data
        self._safe_exec("""
            INSERT IGNORE INTO categories (name)
            SELECT DISTINCT category FROM menu WHERE category IS NOT NULL AND category != ''
        """)
        self._safe_exec("""
            INSERT IGNORE INTO categories (name)
            SELECT DISTINCT category FROM inventory_supplies WHERE category IS NOT NULL AND category != ''
        """)
        # Seed order_types from existing data
        self._safe_exec("""
            INSERT IGNORE INTO order_types (name)
            SELECT DISTINCT order_type FROM orders
            WHERE order_type IS NOT NULL AND order_type != ''
              AND order_type NOT IN (SELECT name FROM order_types)
        """)

        self.conn.commit()

    def _add_fk_columns_and_backfill(self):
        """Add FK columns to existing tables and backfill from legacy text columns."""
        # users.role_id
        self._safe_alter("ALTER TABLE users ADD COLUMN role_id INT NULL")
        self._safe_exec("""
            UPDATE users u SET u.role_id = (SELECT r.id FROM roles r WHERE r.name = u.role LIMIT 1)
            WHERE u.role_id IS NULL
        """)

        # menu.category_id
        self._safe_alter("ALTER TABLE menu ADD COLUMN category_id INT NULL")
        self._safe_exec("""
            UPDATE menu m SET m.category_id = (SELECT c.id FROM categories c WHERE c.name = m.category LIMIT 1)
            WHERE m.category_id IS NULL
        """)

        # orders FK columns
        self._safe_alter("ALTER TABLE orders ADD COLUMN order_type_id INT NULL")
        self._safe_alter("ALTER TABLE orders ADD COLUMN status_id INT NULL")
        self._safe_alter("ALTER TABLE orders ADD COLUMN payment_method_id INT NULL")
        self._safe_alter("ALTER TABLE orders ADD COLUMN customer_id INT NULL")
        self._safe_alter("ALTER TABLE orders ADD COLUMN cashier_id INT NULL")
        self._safe_alter("ALTER TABLE orders ADD COLUMN subtotal DECIMAL(10,2) NULL")
        self._safe_alter("ALTER TABLE orders ADD COLUMN tax DECIMAL(10,2) NULL")

        self._safe_exec("""
            UPDATE orders o SET o.order_type_id = (
                SELECT ot.id FROM order_types ot WHERE ot.name = o.order_type LIMIT 1
            ) WHERE o.order_type_id IS NULL AND o.order_type IS NOT NULL
        """)
        self._safe_exec("""
            UPDATE orders o SET o.status_id = (
                SELECT os.id FROM order_statuses os WHERE os.name = o.status LIMIT 1
            ) WHERE o.status_id IS NULL AND o.status IS NOT NULL
        """)
        self._safe_exec("""
            UPDATE orders o SET o.payment_method_id = (
                SELECT pm.id FROM payment_methods pm
                WHERE pm.name = CASE WHEN o.payment_method LIKE 'GCash%%' THEN 'GCash' ELSE 'Cash' END
                LIMIT 1
            ) WHERE o.payment_method_id IS NULL
        """)
        # Migrate customers (only for Delivery orders with actual customer data)
        self._safe_exec("""
            INSERT IGNORE INTO customers (name, contact, address)
            SELECT DISTINCT customer_name, customer_contact, customer_address
            FROM orders
            WHERE customer_name IS NOT NULL AND customer_name != ''
              AND order_type = 'Delivery'
        """)
        self._safe_exec("""
            UPDATE orders o SET o.customer_id = (
                SELECT c.id FROM customers c
                WHERE c.name = o.customer_name
                  AND COALESCE(c.contact,'') = COALESCE(o.customer_contact,'')
                LIMIT 1
            ) WHERE o.customer_name IS NOT NULL AND o.customer_name != ''
              AND o.order_type = 'Delivery'
              AND o.customer_id IS NULL
        """)
        # Backfill subtotal/tax
        self._safe_exec("""
            UPDATE orders SET subtotal = ROUND(total / 1.12, 2), tax = ROUND(total - (total / 1.12), 2)
            WHERE subtotal IS NULL AND total IS NOT NULL
        """)

        # order_items FK columns
        self._safe_alter("ALTER TABLE order_items ADD COLUMN menu_item_id INT NULL")
        self._safe_alter("ALTER TABLE order_items ADD COLUMN unit_price DECIMAL(10,2) NULL")
        self._safe_exec("""
            UPDATE order_items oi SET
                oi.menu_item_id = (SELECT m.id FROM menu m WHERE m.name = oi.item_name LIMIT 1),
                oi.unit_price   = oi.price
            WHERE oi.menu_item_id IS NULL
        """)

        # inventory_supplies FK columns
        self._safe_alter("ALTER TABLE inventory_supplies ADD COLUMN category_id INT NULL")
        self._safe_alter("ALTER TABLE inventory_supplies ADD COLUMN unit_id INT NULL")
        self._safe_exec("""
            UPDATE inventory_supplies s SET
                s.category_id = (SELECT c.id FROM categories c WHERE c.name = s.category LIMIT 1),
                s.unit_id     = (SELECT u.id FROM units_of_measure u WHERE u.name = s.unit LIMIT 1)
            WHERE s.category_id IS NULL OR s.unit_id IS NULL
        """)

        # system_logs.user_id
        self._safe_alter("ALTER TABLE system_logs ADD COLUMN user_id INT NULL")
        self._safe_exec("""
            UPDATE system_logs sl SET sl.user_id = (
                SELECT u.id FROM users u WHERE u.display_name = sl.user LIMIT 1
            ) WHERE sl.user IS NOT NULL AND sl.user_id IS NULL
        """)

        # ── Add FOREIGN KEY constraints to connect all tables ────────
        fk_constraints = [
            # (table, fk_column, ref_table, ref_column, constraint_name)
            ("users",              "role_id",           "roles",            "id", "fk_users_role"),
            ("menu",               "category_id",       "categories",       "id", "fk_menu_category"),
            ("orders",             "order_type_id",     "order_types",      "id", "fk_orders_order_type"),
            ("orders",             "status_id",         "order_statuses",   "id", "fk_orders_status"),
            ("orders",             "payment_method_id", "payment_methods",  "id", "fk_orders_payment_method"),
            ("orders",             "customer_id",       "customers",        "id", "fk_orders_customer"),
            ("orders",             "cashier_id",        "users",            "id", "fk_orders_cashier"),
            ("order_items",        "menu_item_id",      "menu",             "id", "fk_order_items_menu"),
            ("inventory_supplies", "category_id",       "categories",       "id", "fk_supplies_category"),
            ("inventory_supplies", "unit_id",           "units_of_measure", "id", "fk_supplies_unit"),
            ("system_logs",        "user_id",           "users",            "id", "fk_logs_user"),
            ("audit_trail",        "changed_by",        "users",            "id", "fk_audit_changed_by"),
        ]
        for table, fk_col, ref_table, ref_col, fk_name in fk_constraints:
            self._safe_alter(
                f"ALTER TABLE {table} ADD CONSTRAINT {fk_name} "
                f"FOREIGN KEY ({fk_col}) REFERENCES {ref_table}({ref_col}) "
                f"ON DELETE SET NULL ON UPDATE CASCADE"
            )

        self.conn.commit()

    def _cleanup_customer_data(self):
        """One-time cleanup: remove duplicates and clear stale customer data from non-Delivery orders."""
        # 1. Clear customer fields on Dine In / Take Out orders (they should be NULL)
        self._safe_exec("""
            UPDATE orders
            SET customer_name = NULL,
                customer_contact = NULL,
                customer_address = NULL,
                customer_id = NULL
            WHERE order_type != 'Delivery'
              AND (customer_name IS NOT NULL OR customer_id IS NOT NULL)
        """)

        # 2. Remove duplicate customers — keep only the earliest record per (name, contact)
        self._safe_exec("""
            DELETE c1 FROM customers c1
            INNER JOIN customers c2
            ON c1.name = c2.name
               AND COALESCE(c1.contact, '') = COALESCE(c2.contact, '')
               AND c1.id > c2.id
        """)

        # 3. Rebuild customers table with sequential IDs
        # Copy surviving customers to a temp table, truncate, re-insert in order
        self._safe_exec("DROP TEMPORARY TABLE IF EXISTS _tmp_customers")
        self._safe_exec("""
            CREATE TEMPORARY TABLE _tmp_customers AS
            SELECT name, contact, address, created_at
            FROM customers ORDER BY id
        """)
        # Remove FK references and disable FK checks for TRUNCATE
        self._safe_exec("UPDATE orders SET customer_id = NULL")
        self._safe_exec("SET FOREIGN_KEY_CHECKS = 0")
        # Truncate resets AUTO_INCREMENT to 1
        self._safe_exec("TRUNCATE TABLE customers")
        self._safe_exec("SET FOREIGN_KEY_CHECKS = 1")
        # Re-insert with clean sequential IDs
        self._safe_exec("""
            INSERT INTO customers (name, contact, address, created_at)
            SELECT name, contact, address, created_at FROM _tmp_customers
        """)
        self._safe_exec("DROP TEMPORARY TABLE IF EXISTS _tmp_customers")

        # 4. Re-link Delivery orders to the new sequential customer IDs
        self._safe_exec("""
            UPDATE orders o SET o.customer_id = (
                SELECT c.id FROM customers c
                WHERE c.name = o.customer_name
                  AND COALESCE(c.contact, '') = COALESCE(o.customer_contact, '')
                LIMIT 1
            ) WHERE o.order_type = 'Delivery'
              AND o.customer_name IS NOT NULL AND o.customer_name != ''
        """)

        self.conn.commit()

    def _execute_sql_script(self, file_path, label="Script"):
        """Generic method to execute complex SQL scripts with DELIMITER support."""
        import os
        if not os.path.exists(file_path):
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Split by // which is our block delimiter
            import re
            blocks = re.split(r'//', content)
            for block in blocks:
                # Remove DELIMITER lines and other client-side noise
                lines = block.splitlines()
                clean_lines = [l for l in lines if not l.strip().upper().startswith("DELIMITER")]
                sql_block = "\n".join(clean_lines).strip()
                
                if sql_block:
                    try:
                        self.cursor.execute(sql_block)
                    except Exception as e:
                        # Log but don't crash on standard drops
                        if "DROP" not in sql_block.upper():
                            print(f"Error creating {label} block: {e}")
            
            self.conn.commit()

        except Exception as e:
            print(f"Failed to load {label} script: {e}")

    def _create_stored_procedures(self):
        """Load procedures and triggers from their respective files."""
        import os
        # Load Stored Procedures
        self._execute_sql_script(os.path.join(os.path.dirname(__file__), "stored_procedures.sql"), "Stored Procedures")
        # Load Triggers
        self._execute_sql_script(os.path.join(os.path.dirname(__file__), "triggers.sql"), "Triggers")

    def _safe_exec(self, sql, params=None):
        """Execute a SQL statement, silently ignoring errors."""
        try:
            self.cursor.execute(sql, params)
        except Exception:
            pass

    def _create_views(self):
        """Create database views for abstracted reporting queries."""
        self._safe_exec("""
            CREATE OR REPLACE VIEW vw_order_details AS
            SELECT
                o.id AS order_id, o.order_code,
                COALESCE(ot.name, o.order_type) AS order_type,
                COALESCE(os.name, o.status) AS status,
                COALESCE(pm.name,
                    CASE WHEN o.payment_method LIKE 'GCash%%' THEN 'GCash' ELSE o.payment_method END
                ) AS payment_method,
                o.payment_method AS payment_method_raw,
                o.subtotal, o.tax, o.delivery_fee, o.total,
                COALESCE(c.name, o.customer_name) AS customer_name,
                COALESCE(c.contact, o.customer_contact) AS customer_contact,
                COALESCE(c.address, o.customer_address) AS customer_address,
                u.display_name AS cashier,
                o.created_at, o.updated_at
            FROM orders o
            LEFT JOIN order_types     ot ON o.order_type_id     = ot.id
            LEFT JOIN order_statuses  os ON o.status_id         = os.id
            LEFT JOIN payment_methods pm ON o.payment_method_id = pm.id
            LEFT JOIN customers        c ON o.customer_id       = c.id
            LEFT JOIN users            u ON o.cashier_id        = u.id
        """)

        self._safe_exec("""
            CREATE OR REPLACE VIEW vw_menu AS
            SELECT m.id, m.name, m.emoji, m.price,
                   COALESCE(c.name, m.category) AS category,
                   m.rating, m.sold, m.soldout, m.image_data
            FROM menu m
            LEFT JOIN categories c ON m.category_id = c.id
        """)

        self._safe_exec("""
            CREATE OR REPLACE VIEW vw_low_stock AS
            SELECT s.id, s.name,
                   COALESCE(c.name, s.category) AS category,
                   COALESCE(u.name, s.unit) AS unit,
                   s.quantity, s.min_stock,
                   ROUND(s.quantity / NULLIF(s.min_stock, 0) * 100, 1) AS stock_pct
            FROM inventory_supplies s
            LEFT JOIN categories c ON s.category_id = c.id
            LEFT JOIN units_of_measure u ON s.unit_id = u.id
            WHERE s.quantity <= s.min_stock
        """)

        self._safe_exec("""
            CREATE OR REPLACE VIEW vw_daily_sales AS
            SELECT
                DATE(o.created_at) AS sale_date,
                COUNT(*)           AS order_count,
                SUM(o.subtotal)    AS gross_subtotal,
                SUM(o.tax)         AS total_tax,
                SUM(o.total)       AS gross_total
            FROM orders o
            LEFT JOIN order_statuses os ON o.status_id = os.id
            WHERE COALESCE(os.name, o.status) NOT IN ('cancelled')
            GROUP BY DATE(o.created_at)
            ORDER BY sale_date DESC
        """)

        self._safe_exec("""
            CREATE OR REPLACE VIEW vw_payment_breakdown AS
            SELECT
                COALESCE(pm.name,
                    CASE WHEN o.payment_method LIKE 'GCash%%' THEN 'GCash' ELSE 'Cash' END
                ) AS method,
                COUNT(*) AS order_count,
                SUM(o.total) AS revenue
            FROM orders o
            LEFT JOIN payment_methods pm ON o.payment_method_id = pm.id
            LEFT JOIN order_statuses  os ON o.status_id = os.id
            WHERE COALESCE(os.name, o.status) NOT IN ('cancelled')
            GROUP BY method
        """)

        self._safe_exec("""
            CREATE OR REPLACE VIEW vw_order_items AS
            SELECT
                oi.id, oi.order_id,
                COALESCE(m.name, oi.item_name) AS item_name,
                m.emoji,
                COALESCE(oi.unit_price, oi.price) AS unit_price,
                oi.qty,
                COALESCE(oi.unit_price, oi.price) * oi.qty AS line_total
            FROM order_items oi
            LEFT JOIN menu m ON oi.menu_item_id = m.id
        """)

        self.conn.commit()

        # Seed inventory supplies if empty
        self.cursor.execute("SELECT COUNT(*) as count FROM inventory_supplies")
        if self.cursor.fetchone()["count"] == 0:
            supplies = [
                # SILOG MEALS
                ("Rice", "Silog Meals", "kg", 50, 10, None),
                ("Garlic", "Silog Meals", "kg", 10, 2, None),
                ("Oil", "Silog Meals", "liters", 20, 5, None),
                ("Salt", "Silog Meals", "kg", 5, 1, None),
                ("Black Pepper", "Silog Meals", "kg", 2, 0.5, None),
                ("Tapa", "Silog Meals", "kg", 15, 3, None),
                ("Tocino", "Silog Meals", "kg", 15, 3, None),
                ("Longganisa", "Silog Meals", "pcs", 100, 20, None),
                ("Hotdog", "Silog Meals", "pcs", 100, 20, None),
                ("Pork Chops", "Silog Meals", "kg", 10, 2, None),

                # RICE BOWLS
                ("Siomai", "Rice Bowls", "pcs", 100, 20, None),
                ("Kimchi", "Rice Bowls", "kg", 5, 1, None),

                # SNACKS
                ("French Fries (Packed)", "Snacks", "packs", 50, 10, None),
                ("Potato", "Snacks", "kg", 20, 5, None),
                ("Burger Buns", "Snacks", "pcs", 80, 15, None),
                ("Patty", "Snacks", "pcs", 80, 15, None),
                ("Cheese", "Snacks", "pcs", 50, 10, None),
                ("Ham", "Snacks", "pcs", 50, 10, None),
                ("Canned Tuna", "Snacks", "cans", 30, 5, None),
                ("Ketchup", "Snacks", "bottles", 10, 2, None),
                ("Mayonnaise", "Snacks", "bottles", 10, 2, None),
                ("Lettuce", "Snacks", "kg", 5, 1, None),
                ("Tomato", "Snacks", "kg", 5, 1, None),
                ("Chicken", "Snacks", "kg", 15, 3, None),

                # BEVERAGES
                ("Water", "Beverages", "gallons", 20, 5, None),
                ("Tea Extract", "Beverages", "liters", 10, 2, None),
                ("Sugar", "Beverages", "kg", 20, 5, None),
                ("Lemon Juice", "Beverages", "liters", 5, 1, None),
                ("Strawberry/Calamansi", "Beverages", "kg", 3, 1, None),
                ("Blue Curaçao Syrup", "Beverages", "bottles", 5, 1, None),
                ("Cucumber Extract", "Beverages", "liters", 3, 1, None),

                # FRESH FRUITS
                ("Mango", "Fresh Fruits", "kg", 10, 2, None),
                ("Strawberry", "Fresh Fruits", "kg", 5, 1, None),
                ("Watermelon", "Fresh Fruits", "kg", 10, 2, None),

                # BUKO PANDAN
                ("Coconut", "Buko Pandan", "pcs", 20, 5, None),
                ("Pandan Flavored Gelatin", "Buko Pandan", "packs", 15, 3, None),
                ("Cream", "Buko Pandan", "liters", 5, 1, None),
                ("Condensed Milk", "Buko Pandan", "cans", 15, 3, None),

                # COOKIES N CREAM
                ("Vanilla Cream Base", "Cookies N Cream", "liters", 5, 1, None),
                ("Milk", "Cookies N Cream", "liters", 10, 2, None),
                ("Crushed Chocolate Cookies", "Cookies N Cream", "packs", 15, 3, None),
                ("Ice", "Cookies N Cream", "kg", 20, 5, None),

                # KAPE NG INA MO
                ("Kapeng Barako", "Kape ng Ina Mo", "kg", 5, 1, None),
            ]
            self.cursor.executemany(
                "INSERT INTO inventory_supplies (name, category, unit, quantity, min_stock, notes) VALUES (%s, %s, %s, %s, %s, %s)",
                supplies
            )
            self.conn.commit()

        self.cursor.execute("SELECT COUNT(*) as count FROM system_logs")
        if self.cursor.fetchone()["count"] == 0:
            sample_logs = [
                ("activity", "System", "System", "Startup", "System initialized successfully", None),
                ("activity", "Authentication", "Manager", "Login", "Manager user signed in", None),
                ("activity", "Inventory", "System", "Seed Data", "Default menu seeded", None)
            ]
            self.cursor.executemany(
                "INSERT INTO system_logs (log_type, category, user, action, message, details) VALUES (%s, %s, %s, %s, %s, %s)",
                sample_logs
            )
            self.conn.commit()

        self.cursor.execute("SELECT COUNT(*) as count FROM users")
        if self.cursor.fetchone()["count"] == 0:
            mock_users = [
                ("manager", hashlib.sha256(b"manager123").hexdigest(), "manager", "Manager"),
                ("staff1", hashlib.sha256(b"staff123").hexdigest(), "staff", "Richnell Capacia"),
                ("staff2", hashlib.sha256(b"staff123").hexdigest(), "staff", "Necca Nabata"),
                ("staff3", hashlib.sha256(b"staff123").hexdigest(), "staff", "Yzabelle Mercado")
            ]
            self.cursor.executemany(
                "INSERT INTO users (username, password_hash, role, display_name) VALUES (%s, %s, %s, %s)",
                mock_users
            )
            self.conn.commit()

        self.cursor.execute("SELECT COUNT(*) as count FROM menu")
        if self.cursor.fetchone()["count"] == 0:
            default_menu = [
                ("Lemon IcedTea", "🥤", 35.00, "Beverages", 4.5, 0, 0),
                ("Red IcedTea", "🥤", 35.00, "Beverages", 4.5, 0, 0),
                ("Blue Lemonade IcedTea", "🥤", 35.00, "Beverages", 4.5, 0, 0),
                ("Cucumber IcedTea", "🥤", 35.00, "Beverages", 4.5, 0, 0),
                ("Fresh Fruit Shake", "🥤", 80.00, "Beverages", 4.5, 0, 0),
                ("Cookies ‘n Cream", "🥤", 60.00, "Beverages", 4.5, 0, 0),
                ("Buko Pandan", "🥤", 60.00, "Beverages", 4.5, 0, 0),
                ("Kape ng Ina Mo", "☕", 60.00, "Beverages", 4.5, 0, 0),
                
                ("Tapsilog", "🍳", 85.00, "Silog Meals", 4.5, 0, 0),
                ("Tosilog", "🍳", 85.00, "Silog Meals", 4.5, 0, 0),
                ("Longsilog", "🍳", 85.00, "Silog Meals", 4.5, 0, 0),
                ("Hotsilog", "🍳", 85.00, "Silog Meals", 4.5, 0, 0),
                ("Porksilog", "🍳", 120.00, "Silog Meals", 4.5, 0, 0),
                
                ("Motomix Tapa", "🍚", 70.00, "Rice Bowls", 4.5, 0, 0),
                ("Motomix Tocino", "🍚", 70.00, "Rice Bowls", 4.5, 0, 0),
                ("Motomix Hotdog", "🍚", 70.00, "Rice Bowls", 4.5, 0, 0),
                ("Motomix Siomai", "🍚", 70.00, "Rice Bowls", 4.5, 0, 0),
                ("Kimchi Fried Rice", "🍚", 99.00, "Rice Bowls", 4.5, 0, 0),
                
                ("French Fries", "🍟", 60.00, "Snacks", 4.5, 0, 0),
                ("Chipipay", "🍟", 60.00, "Snacks", 4.5, 0, 0),
                ("Steak Fries", "🍟", 60.00, "Snacks", 4.5, 0, 0),
                ("Potato Platter", "🍟", 199.00, "Snacks", 4.5, 0, 0),
                ("Dugyot Burger", "🍔", 210.00, "Snacks", 4.5, 0, 0),
                ("Buraot Burger", "🍔", 210.00, "Snacks", 4.5, 0, 0),
                ("Cheese Burger", "🍔", 135.00, "Snacks", 4.5, 0, 0),
                ("Chicken Burger", "🍔", 100.00, "Snacks", 4.5, 0, 0),
                ("Ham Sandwich", "🥪", 80.00, "Snacks", 4.5, 0, 0),
                ("Tuna Sandwich", "🥪", 100.00, "Snacks", 4.5, 0, 0),
            ]
            self.cursor.executemany(
                "INSERT INTO menu (name, emoji, price, category, rating, sold, soldout) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                default_menu
            )
            self.conn.commit()

    def load_menu_from_db(self):
        """Fetch all menu items from the database using the optimized view."""
        if not self.cursor:
            return
        
        rows = self._call_procedure("sp_GetMenu")
        if not rows and self._menu:
            return # Don't clear if fetch failed but we have data
            
        new_menu = []
        for r in rows:
            new_menu.append({
                "name": r.get("name"),
                "emoji": r.get("emoji"),
                "price": float(r.get("price") or 0),
                "category": r.get("category"),
                "rating": float(r.get("rating") or 0),
                "sold": r.get("sold", 0),
                "soldout": bool(r.get("soldout")),
                "stock": 0,
                "image_data": r.get("image_data", None)
            })
        self._menu = new_menu
        self.menu_filtered.emit(self._menu)

    def get_menu_categories(self):
        """Return a list of distinct menu categories."""
        rows = self._call_procedure("sp_GetMenuCategories")
        return [r.get("category") for r in rows]

    def update_menu_image(self, item_name, image_data):
        """Save image binary data (LONGBLOB) for a menu item in the database.
        Args:
            item_name: Name of the menu item
            image_data: Binary image data (bytes) to store in database
        """
        if not self.cursor:
            return False
        try:
            self.cursor.execute("CALL sp_UpdateMenuImage(%s, %s)", (item_name, image_data))
            self.conn.commit()
            # Update local cache
            for item in self._menu:
                if item["name"] == item_name:
                    item["image_data"] = image_data
                    break
            return True
        except mysql.connector.Error as e:
            self.conn.rollback()
            self.log_error(
                action="Update Menu Image Failed",
                message=str(e),
                category="Inventory",
                user=self.current_user and self.current_user.get("display_name"),
                details=item_name
            )
            print(f"Error updating menu image: {e}")
            return False
        except Exception as e:
            print(f"Generic error updating menu image: {e}")
            return False

    # --- Inventory Supplies Methods ---
    def get_supplies(self, category=None):
        """Fetch all raw supplies from the database, optionally filtered by category."""
        if not self.cursor:
            return []
        rows = self._call_procedure("sp_GetSupplies", (category,))
        return [dict(r) for r in rows]

    def get_supply_categories(self):
        """Return a list of distinct supply categories."""
        rows = self._call_procedure("sp_GetSupplyCategories")
        return [r.get("category") for r in rows]

    def _ensure_unit(self, unit_name):
        """Ensure a unit exists in the lookup table. Returns unit_id."""
        if not unit_name:
            return None
        unit_id = self._resolve_lookup("units_of_measure", unit_name)
        if unit_id is None:
            self._safe_exec("INSERT IGNORE INTO units_of_measure (name) VALUES (%s)", (unit_name,))
            self.conn.commit()
            unit_id = self._resolve_lookup("units_of_measure", unit_name)
        return unit_id

    def add_supply(self, data):
        """Add a new supply item."""
        if not self.cursor:
            return False
        try:
            # Dual-write: legacy text + normalized FKs
            cat_id = self._ensure_category(data["category"])
            unit_id = self._ensure_unit(data.get("unit", "pcs"))
            self.cursor.execute(
                "CALL sp_AddSupply(%s, %s, %s, %s, %s, %s, %s, %s)",
                (data["name"], data["category"], data.get("unit", "pcs"),
                 data.get("quantity", 0), data.get("min_stock", 5), data.get("notes"), cat_id, unit_id)
            )
            self.conn.commit()
            self.log_activity(
                action="Add Supply",
                message=f"Added supply '{data['name']}' to {data['category']}",
                category="Inventory",
                user=self.current_user and self.current_user.get("display_name")
            )
            return True
        except mysql.connector.Error as e:
            self.conn.rollback()
            self.log_error(
                action="Add Supply Failed",
                message=str(e),
                category="Inventory",
                user=self.current_user and self.current_user.get("display_name"),
                details=str(data)
            )
            print(f"Error adding supply: {e}")
            return False
        except Exception as e:
            print(f"Generic error adding supply: {e}")
            return False

    def update_supply(self, supply_id, data):
        """Update an existing supply item."""
        if not self.cursor:
            return False
        try:
            # Dual-write: legacy text + normalized FKs
            cat_id = self._ensure_category(data["category"])
            unit_id = self._ensure_unit(data.get("unit", "pcs"))
            self.cursor.execute(
                "CALL sp_UpdateSupply(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (supply_id, data["name"], data["category"], data.get("unit", "pcs"),
                 data.get("quantity", 0), data.get("min_stock", 5), data.get("notes"), cat_id, unit_id)
            )
            self.conn.commit()
            self.log_activity(
                action="Update Supply",
                message=f"Updated supply '{data['name']}' (qty: {data.get('quantity', 0)})",
                category="Inventory",
                user=self.current_user and self.current_user.get("display_name")
            )
            return True
        except mysql.connector.Error as e:
            self.conn.rollback()
            self.log_error(
                action="Update Supply Failed",
                message=str(e),
                category="Inventory",
                user=self.current_user and self.current_user.get("display_name"),
                details=f"ID: {supply_id}, Data: {data}"
            )
            print(f"Error updating supply: {e}")
            return False
        except Exception as e:
            print(f"Generic error updating supply: {e}")
            return False

    def delete_supply(self, supply_id):
        """Delete a supply item by ID."""
        if not self.cursor:
            return False
        try:
            self.cursor.execute("SELECT name FROM inventory_supplies WHERE id=%s", (supply_id,))
            row = self.cursor.fetchone()
            name = row["name"] if row else "Unknown"
            self.cursor.execute("CALL sp_DeleteSupply(%s)", (supply_id,))
            self.conn.commit()
            self.log_activity(
                action="Delete Supply",
                message=f"Deleted supply '{name}'",
                category="Inventory",
                user=self.current_user and self.current_user.get("display_name")
            )
            return True
        except mysql.connector.Error as e:
            self.conn.rollback()
            self.log_error(
                action="Delete Supply Failed",
                message=str(e),
                category="Inventory",
                user=self.current_user and self.current_user.get("display_name"),
                details=f"Supply ID: {supply_id}"
            )
            print(f"Error deleting supply: {e}")
            return False
        except Exception as e:
            print(f"Generic error deleting supply: {e}")
            return False

    # --- Authentication Methods ---
    def login(self, username, password):
        if not self.conn:
            print("Database not connected.")
            return None

        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        rows = self._call_procedure("sp_AuthenticateUser", (username, hashed_pw))
        user = rows[0] if rows else None
        if user:
            user = dict(user)
            user["first_name"] = user.get("display_name", "")
            user["last_name"] = ""
            self.current_user = user
            self.log_activity(
                action="Login",
                message=f"User '{user['username']}' signed in",
                category="Authentication",
                user=user["display_name"]
            )
        return user

    def register(self, data):
        if not self.conn:
            return False, "Database connection error."

        self.cursor.execute("SELECT * FROM users WHERE username = %s", (data["username"],))
        if self.cursor.fetchone():
            return False, "Username already exists."

        hashed_pw = hashlib.sha256(data["password"].encode()).hexdigest()
        display_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
        role = "manager" if data.get("role", "Staff").lower() == "manager" else "staff"
        
        # Dual-write: legacy role + normalized role_id
        role_id = self._resolve_lookup("roles", role)

        try:
            self.cursor.execute("CALL sp_RegisterUser(%s, %s, %s, %s, %s)", 
                                (data["username"], hashed_pw, role, role_id, display_name))
            self.conn.commit()
            self.log_activity(
                action="User Registration",
                message=f"Registered new user '{data['username']}'",
                category="Authentication",
                user=display_name
            )
            return True, "Account created successfully!"
        except mysql.connector.Error as e:
            self.conn.rollback()
            self.log_error(
                action="User Registration Failed",
                message=str(e),
                category="Authentication",
                user=display_name,
                details=str(data)
            )
            return False, f"Database error: {e}"

    # --- Menu & Inventory Methods ---
    def get_menu(self, category=None):
        if category and category != "All":
            return [m for m in self._menu if m["category"] == category]
        return list(self._menu)

    def filter_menu(self, query):
        """Filters the menu based on a search query (can be ran in a thread)."""
        if not query:
            filtered = list(self._menu)
        else:
            query = query.lower()
            filtered = [m for m in self._menu if query in m["name"].lower() or query in m["category"].lower()]
        self.menu_filtered.emit(filtered)
        return filtered

    def set_sold_out(self, name, state):
        if self.cursor:
            try:
                self.cursor.execute(
                    "UPDATE menu SET soldout = %s WHERE name = %s",
                    (1 if state else 0, name)
                )
                self.conn.commit()
                
                # Update local cache and UI signals only after DB commit succeeds
                for item in self._menu:
                    if item["name"] == name:
                        item["soldout"] = state
                        self.sold_out_changed.emit(name, state)
                        break

                self.log_activity(
                    action="Sold Out Toggle",
                    message=f"Set soldout={state} for '{name}'",
                    category="Inventory",
                    user=self.current_user and self.current_user.get("display_name")
                )
            except mysql.connector.Error as e:
                self.conn.rollback()
                self.log_error(
                    action="Sold Out Update Failed",
                    message=str(e),
                    category="Inventory",
                    user=self.current_user and self.current_user.get("display_name"),
                    details=name
                )
                print(f"Database error: {e}")

    def update_stock(self, name, qty):
        # Kept for frontend compatibility, but menu stock is handled differently now.
        for item in self._menu:
            if item["name"] == name:
                item["stock"] = qty
                self.stock_updated.emit(name, qty)
                break

    def _ensure_category(self, category_name):
        """Ensure a category exists in the lookup table. Returns category_id."""
        if not category_name:
            return None
        cat_id = self._resolve_lookup("categories", category_name)
        if cat_id is None:
            self._safe_exec("INSERT IGNORE INTO categories (name) VALUES (%s)", (category_name,))
            self.conn.commit()
            cat_id = self._resolve_lookup("categories", category_name)
        return cat_id

    def add_menu_item(self, item_data):
        if self.cursor:
            try:
                # Dual-write: legacy category text + normalized category_id FK
                cat_id = self._ensure_category(item_data["category"])
                self.cursor.execute("""
                    INSERT INTO menu (name, emoji, price, category, category_id, rating, sold, soldout)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    item_data["name"],
                    item_data["emoji"],
                    item_data["price"],
                    item_data["category"],
                    cat_id,
                    item_data["rating"],
                    item_data["sold"],
                    int(item_data["soldout"])
                ))
                self.conn.commit()
                self.log_activity(
                    action="Add Menu Item",
                    message=f"Added new menu item '{item_data['name']}'",
                    category="Inventory",
                    user=self.current_user and self.current_user.get("display_name"),
                    details=str(item_data)
                )
            except mysql.connector.Error as e:
                self.conn.rollback()
                self.log_error(
                    action="Add Menu Item Failed",
                    message=str(e),
                    category="Inventory",
                    user=self.current_user and self.current_user.get("display_name"),
                    details=str(item_data)
                )
                print(f"Database error: {e}")
                return

        self.load_menu_from_db()
        self.menu_filtered.emit(self._menu)

    def edit_menu_item(self, old_name, new_data):
        if self.cursor:
            try:
                # Dual-write: legacy category text + normalized category_id FK
                cat_id = self._ensure_category(new_data["category"])
                self.cursor.execute("""
                    UPDATE menu
                    SET name = %s,
                        emoji = %s,
                        price = %s,
                        category = %s,
                        category_id = %s,
                        rating = %s,
                        sold = %s,
                        soldout = %s
                    WHERE name = %s
                """, (
                    new_data["name"],
                    new_data["emoji"],
                    new_data["price"],
                    new_data["category"],
                    cat_id,
                    new_data["rating"],
                    new_data["sold"],
                    int(new_data["soldout"]),
                    old_name
                ))
                self.conn.commit()
                self.log_activity(
                    action="Edit Menu Item",
                    message=f"Updated menu item '{old_name}' to '{new_data['name']}'",
                    category="Inventory",
                    user=self.current_user and self.current_user.get("display_name"),
                    details=str(new_data)
                )
            except mysql.connector.Error as e:
                self.conn.rollback()
                self.log_error(
                    action="Edit Menu Item Failed",
                    message=str(e),
                    category="Inventory",
                    user=self.current_user and self.current_user.get("display_name"),
                    details=f"Old: {old_name}, New: {new_data}"
                )
                print(f"Database error: {e}")
                return

        self.load_menu_from_db()
        self.menu_filtered.emit(self._menu)

    def delete_menu_item(self, name):
        if self.cursor:
            try:
                self.cursor.execute(
                    "DELETE FROM menu WHERE name = %s",
                    (name,)
                )
                self.conn.commit()
                self.log_activity(
                    action="Delete Menu Item",
                    message=f"Removed menu item '{name}'",
                    category="Inventory",
                    user=self.current_user and self.current_user.get("display_name")
                )
            except mysql.connector.Error as e:
                self.conn.rollback()
                self.log_error(
                    action="Delete Menu Item Failed",
                    message=str(e),
                    category="Inventory",
                    user=self.current_user and self.current_user.get("display_name"),
                    details=f"Item name: {name}"
                )
                print(f"Database error: {e}")
                return

        self.load_menu_from_db()
        self.menu_filtered.emit(self._menu)

    def _record_log(self, log_type, action, message, category=None, user=None, details=None):
        if not self.cursor:
            return
        try:
            self.cursor.execute("CALL sp_AddSystemLog(%s, %s, %s, %s, %s, %s)", 
                                (log_type, category, user, action, message, details))
            self.conn.commit()
        except mysql.connector.Error as e:
            print(f"Log write error: {e}")

    def log_activity(self, action, message, category=None, user=None, details=None):
        self._record_log("activity", action, message, category, user, details)

    def log_error(self, action, message, category=None, user=None, details=None):
        self._record_log("error", action, message, category, user, details)
    def get_logs(self, log_type=None, limit=100):
        if not self.cursor:
            return []
        
        rows = self._call_procedure("sp_GetLogs")
        # Filter in Python if log_type is specified (simpler than complex SP for now)
        if log_type:
            rows = [r for r in rows if r.get("log_type") == log_type]
            
        return [
            {
                "id": r.get("id"),
                "log_type": r.get("log_type"),
                "category": r.get("category"),
                "user": r.get("user"),
                "action": r.get("action"),
                "message": r.get("message"),
                "details": r.get("details"),
                "created_at": r.get("created_at").strftime("%Y-%m-%d %H:%M:%S") if r.get("created_at") else ""
            }
            for r in rows[:limit]
        ]

    def get_activity_logs(self, limit=100):
        return self.get_logs("activity", limit)

    def get_error_logs(self, limit=100):
        return self.get_logs("error", limit)

    # --- Order Management Methods ---
    def load_orders_from_db(self):
        if not self.cursor:
            self._orders = []
            return

        orders = self._call_procedure("sp_GetRecentOrders")

        formatted_orders = []
        for o in orders:
            # Filter only pending/preparing/ready in Python
            status = o.get("status", "").lower()
            if status not in ('pending', 'preparing', 'ready'):
                continue

            order_id = o.get("order_id")
            items = self._call_procedure("sp_GetOrderItems", (order_id,))

            formatted_orders.append({
                "id": str(o.get("order_code", "N/A")),
                "table": o.get("order_type", "N/A"),
                "status": status,
                "time": o["created_at"].strftime("%I:%M %p") if o.get("created_at") and hasattr(o["created_at"], "strftime") else "Just now",
                "items": [f"{i.get('item_name', 'Item')} × {i.get('qty', 1)}" for i in items],
                "total": float(o.get("total") or 0)
            })

        self._orders = formatted_orders
        self.order_status_changed.emit("all", "refresh")

    def get_orders(self):
        return list(self._orders)

    def advance_order(self, order_code):
        if not self.cursor:
            return

        try:
            self.cursor.execute(
                "SELECT status FROM orders WHERE order_code = %s",
                (order_code,)
            )
            row = self.cursor.fetchone()
            if not row:
                return

            current = row["status"]

            if current == "pending":
                new_status = "preparing"
            elif current == "preparing":
                new_status = "ready"
            elif current == "ready":
                new_status = "completed"
            else:
                return

            new_status_id = self._resolve_lookup("order_statuses", new_status)
            self.cursor.execute("CALL sp_AdvanceOrder(%s, %s, %s)", (order_code, new_status, new_status_id))
            self.conn.commit()
            
            self.log_activity(
                action="Advance Order",
                message=f"Order {order_code} moved to {new_status}",
                category="Orders",
                user=self.current_user and self.current_user.get("display_name")
            )
            self.load_orders_from_db()
            self.order_status_changed.emit(order_code, new_status)
        except mysql.connector.Error as e:
            self.conn.rollback()
            self.log_error(
                action="Advance Order Failed",
                message=str(e),
                category="Orders",
                user=self.current_user and self.current_user.get("display_name"),
                details=f"Order Code: {order_code}"
            )
            print(f"Database error advancing order: {e}")

    def cancel_order(self, order_code):
        if not self.cursor:
            return

        try:
            # Dual-write: legacy text + normalized FK
            cancel_id = self._resolve_lookup("order_statuses", "cancelled")
            self.cursor.execute("CALL sp_CancelOrder(%s, %s)", (order_code, cancel_id))
            self.conn.commit()
            
            self.log_activity(
                action="Cancel Order",
                message=f"Order {order_code} cancelled",
                category="Orders",
                user=self.current_user and self.current_user.get("display_name")
            )
            self.load_orders_from_db()
            self.order_status_changed.emit(order_code, "cancelled")
        except mysql.connector.Error as e:
            self.conn.rollback()
            self.log_error(
                action="Cancel Order Failed",
                message=str(e),
                category="Orders",
                user=self.current_user and self.current_user.get("display_name"),
                details=f"Order Code: {order_code}"
            )
            print(f"Database error cancelling order: {e}")

    def add_order(self, cart_items, order_type="Dine In", payment_method="Cash", customer_details=None, delivery_fee=0):
        if not self.cursor:
            return

        # Calculate total including tax (12%)
        subtotal = sum(Decimal(str(i["price"])) * i["qty"] for i in cart_items)
        tax = subtotal * Decimal("0.12")
        # Delivery fee is NOT affected by tax
        total = subtotal + tax + Decimal(str(delivery_fee))
        
        rows = self._call_procedure("sp_GetNextOrderCode")
        count = (rows[0].get("next_code") if rows else 1101)
        order_code = f"#{count}"
        


        try:
            # ── BEGIN TRANSACTION ──
            # Note: autocommit=False in connection.py starts transaction on first write
            
            # Only collect customer info for Delivery orders
            customer_id = None
            c_name = None
            c_contact = None
            c_address = None

            if order_type == "Delivery" and customer_details and customer_details.get("name"):
                c_name = customer_details.get("name")
                c_contact = customer_details.get("contact")
                c_address = customer_details.get("address")
                
                rows = self._call_procedure("sp_UpsertCustomer", (c_name, c_contact, c_address))
                customer_id = rows[0].get("customer_id") if rows else None

            # Resolve FK IDs for normalized columns
            order_type_id = self._resolve_lookup("order_types", order_type)
            status_id = self._resolve_lookup("order_statuses", "pending")
            pm_base = "GCash" if payment_method.startswith("GCash") else "Cash"
            payment_method_id = self._resolve_lookup("payment_methods", pm_base)
            cashier_id = self.current_user.get("id") if self.current_user else None

            # 1. Create Order Header
            res_rows = self._call_procedure("sp_CreateOrder", (
                order_code, order_type,
                float(subtotal), float(tax), float(delivery_fee), float(total),
                payment_method, c_name, c_contact, c_address,
                order_type_id, status_id, payment_method_id, customer_id, cashier_id
            ))
            order_id = res_rows[0].get("order_id") if res_rows else None
            
            if not order_id:
                self.cursor.execute("SELECT id FROM orders WHERE order_code = %s", (order_code,))
                row = self.cursor.fetchone()
                order_id = row["id"] if row else None
            
            if not order_id:
                raise mysql.connector.Error("Failed to retrieve order ID after creation.")

            # ── CREATE SAVEPOINT ──
            # Header is safe; now we start critical item/inventory writes
            self.cursor.execute("SAVEPOINT order_header_created")
            
            try:
                for item in cart_items:
                    # Get menu item ID for normalized FK
                    menu_rows = self._call_procedure("sp_GetMenuIdByName", (item["name"],))
                    menu_item_id = menu_rows[0].get("id") if menu_rows else None

                    # Call stored procedure for adding item and updating inventory
                    self._call_procedure("sp_AddOrderItem", (int(order_id), item["name"], float(item["price"]), item["qty"], menu_item_id))

                # Write to audit trail
                self._call_procedure("sp_AddAuditTrail", ('orders', int(order_id), 'INSERT', cashier_id, f'{{"order_code":"{order_code}","total":{float(total)}}}'))
            except mysql.connector.Error as item_err:
                # ── ROLLBACK TO SAVEPOINT ──
                # If items fail, we go back to header-only or decide to abort
                self.cursor.execute("ROLLBACK TO SAVEPOINT order_header_created")
                raise item_err

            # ── COMMIT TRANSACTION ──
            self.conn.commit()
        except mysql.connector.Error as e:
            # ── GLOBAL ROLLBACK on failure ──
            try:
                self.conn.rollback()
            except Exception:
                pass
            self.log_error(
                action="Order Creation Failed",
                message=str(e),
                category="Orders",
                user=self.current_user and self.current_user.get("display_name"),
                details=str(cart_items)
            )
            print(f"DB Error: {e}")
            return

        self.log_activity(
            action="Create Order",
            message=f"Created order {order_code}",
            category="Orders",
            user=self.current_user and self.current_user.get("display_name"),
            details=f"Order type: {order_type}, total: {total}"
        )

        self.load_orders_from_db()
        self.load_menu_from_db()
        self.menu_filtered.emit(self._menu)
        self.order_status_changed.emit(order_code, "pending")
        return order_code

    def get_order_details(self, order_code):
        """Fetch full order details from the database including items."""
        if not self.cursor:
            return None
        try:
            # 1. Fetch order header info
            rows = self._call_procedure("sp_GetOrderDetailsByCode", (order_code,))
            if not rows:
                return None
            order = rows[0]
            
            # 2. Fetch order items
            items = self._call_procedure("sp_GetOrderItems", (order["order_id"],))
            items = self.cursor.fetchall()
            
            # Map items back to expected format for ReceiptDialog
            formatted_items = []
            for i in items:
                formatted_items.append({
                    "name": i["item_name"],
                    "price": float(i["unit_price"]),
                    "qty": i["qty"],
                    "emoji": i.get("emoji", "🍛")
                })
            
            # Ensure numeric fields are floats for the UI
            for field in ["subtotal", "tax", "delivery_fee", "total"]:
                if order.get(field) is not None:
                    order[field] = float(order[field])
            
            order["items_list"] = formatted_items
            return order
        except Exception as e:
            print(f"Error fetching order details: {e}")
            return None

    def _resolve_lookup(self, table, name):
        """Resolve a lookup table name → id. Returns None if not found."""
        if not name:
            return None
        try:
            self.cursor.execute(f"SELECT id FROM {table} WHERE name = %s LIMIT 1", (name,))
            row = self.cursor.fetchone()
            return row["id"] if row else None
        except Exception:
            return None

    # --- Analytics & Reporting Methods ---
    def get_stats(self):
        """Calculate dashboard statistics, excluding cancelled orders for accuracy."""
        revenue = 0.0
        orders = 0
        avg_order = 0

    def _call_procedure(self, proc_name, params=None):
        """Helper to call a stored procedure and return the first result set's rows."""
        if not self.cursor:
            return []
        try:
            # Consume any existing results to prevent "Unread result found"
            while self.conn.unread_result:
                self.cursor.fetchone()

            self.cursor.callproc(proc_name, params or ())
            results = []
            for result in self.cursor.stored_results():
                results.extend(result.fetchall())
            return results
        except Exception as e:
            print(f"Error calling procedure {proc_name}: {e}")
            # Try to clear state on error
            try:
                while self.conn.unread_result:
                    self.cursor.fetchone()
            except:
                pass
            return []

    def get_stats(self):
        """Calculate dashboard statistics, excluding cancelled orders for accuracy."""
        revenue = 0.0
        orders = 0
        avg_order = 0

        rows = self._call_procedure("sp_GetDashboardStats")
        if rows:
            row = rows[0]
            # Handle both 'order_count' and 'count' for backward/forward compatibility
            orders = row.get("order_count") or row.get("count") or 0
            revenue = float(row.get("revenue") or 0)
            avg_order = int(revenue / orders) if orders else 0

        return {
            "revenue": int(revenue),
            "orders": orders,
            "avg_order": avg_order,
            "active_staff": len([s for s in self._staff if s["status"] == "Active"])
        }

    def get_sales_data(self):
        """Fetch sales data for 'This Week' and 'Last Week' with strict date bucketing."""
        if not self.cursor:
            return [0.0]*7, [0.0]*7

        try:
            # 1. Define strict date boundaries (Local Time)
            now = datetime.now()
            today = now.date()
            
            # Monday of current week
            monday_this_week = today - timedelta(days=today.weekday())
            # Monday of last week
            monday_last_week = monday_this_week - timedelta(days=7)
            # Sunday of last week
            sunday_last_week = monday_this_week - timedelta(days=1)
            
            # 2. Initialize result maps (Mon=0, ..., Sun=6)
            this_week_map = {i: 0.0 for i in range(7)}
            last_week_map = {i: 0.0 for i in range(7)}

            # 3. Fetch data (sp_GetMonthlySalesTrend returns last 30 days)
            rows = self._call_procedure("sp_GetMonthlySalesTrend")

            for r in rows:
                s_date = r.get("day") or r.get("sale_date")
                if not s_date: continue
                
                # Ensure date type
                if isinstance(s_date, datetime):
                    s_date = s_date.date()
                
                total = float(r.get("total") or r.get("gross_total") or 0)
                weekday_idx = s_date.weekday()

                # 4. Strict Bucketing
                if s_date >= monday_this_week:
                    # Current Week (Mon-Today)
                    if weekday_idx < 7:
                        this_week_map[weekday_idx] = total
                elif s_date >= monday_last_week and s_date <= sunday_last_week:
                    # Last Week (Mon-Sun exactly)
                    if weekday_idx < 7:
                        last_week_map[weekday_idx] = total

            # 5. Convert maps to ordered lists
            this_week_list = [this_week_map[i] for i in range(7)]
            last_week_list = [last_week_map[i] for i in range(7)]

            return this_week_list, last_week_list
            
        except Exception as e:
            print(f"Error calculating sales data: {e}")
            return [0.0]*7, [0.0]*7

    def get_monthly_sales(self):
        """Return 30 days of daily sales data from the database."""
        if not self.cursor:
            import random
            return [random.randint(18000, 55000) for _ in range(30)]

        try:
            rows = self._call_procedure("sp_GetMonthlySalesTrend")
            
            # Create a dictionary for quick lookup
            data_map = {r.get("day") or r.get("sale_date"): float(r.get("total") or 0) for r in rows}
            
            # Fill in the last 30 days (including zeros)
            result = []
            for i in range(29, -1, -1):
                day = (datetime.now() - timedelta(days=i)).date()
                result.append(data_map.get(day, 0.0))
            return result
        except Exception as e:
            print(f"Error fetching monthly sales: {e}")
            import random
            return [random.randint(18000, 55000) for _ in range(30)]

    def get_yearly_sales(self):
        """Return 12 months of revenue data from the database."""
        if not self.cursor:
            import random
            return [random.randint(500000, 1500000) for _ in range(12)]

        try:
            rows = self._call_procedure("sp_GetYearlySalesTrend")
            
            # Create a dictionary for quick lookup
            data_map = {r.get("month_key"): float(r.get("total") or 0) for r in rows}
            
            # Fill in the last 12 months
            result = []
            now = datetime.now()
            curr_month = now.month
            curr_year = now.year

            for i in range(11, -1, -1):
                m = curr_month - i
                y = curr_year
                while m <= 0:
                    m += 12
                    y -= 1
                key = f"{y:04d}-{m:02d}"
                result.append(data_map.get(key, 0.0))
            return result
        except Exception as e:
            print(f"Error fetching yearly sales: {e}")
            import random
            return [random.randint(500000, 1500000) for _ in range(12)]
    def get_payment_breakdown(self):
        """Return payment method breakdown from the database using the optimized view."""
        rows = self._call_procedure("sp_GetPaymentBreakdown")
        if rows:
            return {r["method"]: {"count": r["order_count"], "revenue": float(r["revenue"])} for r in rows}
        return {"Cash": {"count": 15, "revenue": 1800}, "GCash": {"count": 7, "revenue": 839}}

    def get_audit(self):
        """Fetch a combined view of recent transactions, system activities, and normalized audit trail."""
        from datetime import datetime
        if not self.cursor:
            return list(self._audit)
        
        try:
            # 1. Fetch latest orders
            order_rows = self._call_procedure("sp_GetAuditHistory")
            
            # 2. Fetch latest critical system logs
            log_rows = self._call_procedure("sp_GetActivityLogs")
            
            # 3. Fetch normalized audit trail
            audit_rows = self._call_procedure("sp_GetFullAuditTrail")
            
            combined = []
            
            # Format Orders
            for o in order_rows:
                ts = o.get("created_at")
                time_str = ts.strftime("%I:%M %p") if hasattr(ts, "strftime") else "Now"
                total_val = float(o.get("total") or 0)
                
                combined.append({
                    "time": time_str,
                    "staff": o.get("cashier") or "Cashier", 
                    "action": f"Order {o.get('order_code', 'Unknown')}",
                    "detail": f"Total: ₱{total_val:,.2f} ({o.get('payment_method', 'Cash')})",
                    "status": o.get("status", "pending"),
                    "timestamp": ts or datetime.min
                })
                
            # Format Logs
            for l in log_rows:
                ts = l.get("created_at")
                time_str = ts.strftime("%I:%M %p") if hasattr(ts, "strftime") else "Now"
                action_text = l.get("action", "Activity")
                status = "cancelled" if "void" in action_text.lower() or "cancel" in action_text.lower() else "completed"
                
                combined.append({
                    "time": time_str,
                    "staff": l.get("user") or "System",
                    "action": action_text,
                    "detail": l.get("message", "System log entry"),
                    "status": status,
                    "timestamp": ts or datetime.min
                })

            # Format Audit Trail
            for a in audit_rows:
                ts = a.get("changed_at")
                time_str = ts.strftime("%I:%M %p") if hasattr(ts, "strftime") else "Now"
                combined.append({
                    "time": time_str,
                    "staff": a.get("staff") or "System",
                    "action": f"{a.get('action')} on {a.get('table_name')}",
                    "detail": str(a.get("new_values") or ""),
                    "status": "completed",
                    "timestamp": ts or datetime.min
                })
            
            # 4. Sort: Priority Statuses (preparing, ready, pending) first, then by timestamp
            def sort_key(item):
                status = item.get("status", "completed").lower()
                # Higher number = higher priority (pushed to top)
                priority = 0
                if status == "preparing": priority = 3
                elif status == "ready": priority = 2
                elif status == "pending": priority = 1
                
                ts = item.get("timestamp")
                if not isinstance(ts, datetime):
                    ts = datetime.min
                    
                return (priority, ts)

            combined.sort(key=sort_key, reverse=True)
            return combined[:50]
            
        except Exception as e:
            print(f"Audit fetch error: {e}")
            return list(self._audit)

    def get_staff(self):
        return list(self._staff)

    # --- User Management Methods ---
    def get_all_users(self):
        """Fetch all users from the database."""
        if not self.cursor:
            return []
        try:
            self.cursor.execute("SELECT id, username, role, display_name, is_active FROM users")
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching users: {e}")
            return []

    def update_user(self, user_id, display_name, role, password_hash=None, username=None):
        """Update a user's details in the database with dual-write for roles."""
        if not self.cursor:
            return False
        try:
            # Resolve role_id for normalized column
            role_id = self._resolve_lookup("roles", role.lower())
            
            query = "UPDATE users SET display_name = %s, role = %s, role_id = %s"
            params = [display_name, role.lower(), role_id]
            
            if username:
                query += ", username = %s"
                params.append(username)
                
            if password_hash:
                query += ", password_hash = %s"
                params.append(password_hash)
                
            query += " WHERE id = %s"
            params.append(user_id)
            
            self.cursor.execute(query, tuple(params))
            self.conn.commit()
            
            # If we updated the current user, refresh our local state
            if self.current_user and self.current_user.get("id") == user_id:
                self.refresh_current_user()
                
            return True
        except mysql.connector.Error as e:
            self.conn.rollback()
            self.log_error(
                action="Update User Failed",
                message=str(e),
                category="Users",
                user=self.current_user and self.current_user.get("display_name"),
                details=f"User ID: {user_id}"
            )
            print(f"Error updating user: {e}")
            return False
        except Exception as e:
            print(f"Generic error updating user: {e}")
            return False

    def refresh_current_user(self):
        """Reload the current user's data from the database."""
        if not self.cursor or not self.current_user:
            return
        try:
            user_id = self.current_user.get("id")
            self.cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = self.cursor.fetchone()
            if user:
                self.current_user = user
        except Exception as e:
            print(f"Error refreshing current user: {e}")

    def set_user_active_state(self, user_id, is_active):
        """Mark a user active or inactive without deleting their record."""
        if not self.cursor:
            return False
        try:
            self.cursor.execute(
                "UPDATE users SET is_active = %s WHERE id = %s",
                (1 if is_active else 0, user_id)
            )
            self.conn.commit()
            if self.current_user and self.current_user.get("id") == user_id:
                self.refresh_current_user()
            return True
        except mysql.connector.Error as e:
            self.conn.rollback()
            self.log_error(
                action="Set User Active State Failed",
                message=str(e),
                category="Users",
                user=self.current_user and self.current_user.get("display_name"),
                details=f"User ID: {user_id}, State: {is_active}"
            )
            print(f"Error setting user active state: {e}")
            return False
        except Exception as e:
            print(f"Generic error setting user active state: {e}")
            return False
