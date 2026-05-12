-- ================================================================
--  RiceMoto POS — Database Migration to Normalized 3NF
--  Target:  MySQL 8.0+   |   DB: ricemoto
--  Safe to re-run (uses IF NOT EXISTS / IGNORE throughout)
-- ================================================================

-- ────────────────────────────────────────────────────────────
-- PHASE 1: Lookup / Reference Tables
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS roles (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;
INSERT IGNORE INTO roles (name) VALUES ('manager'), ('staff');

CREATE TABLE IF NOT EXISTS categories (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS order_statuses (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(32) NOT NULL UNIQUE
) ENGINE=InnoDB;
INSERT IGNORE INTO order_statuses (name) VALUES
    ('pending'),('preparing'),('ready'),('completed'),('cancelled');

CREATE TABLE IF NOT EXISTS order_types (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE
) ENGINE=InnoDB;
INSERT IGNORE INTO order_types (name) VALUES ('Dine In'),('Take Out'),('Delivery'),('Pickup');

CREATE TABLE IF NOT EXISTS payment_methods (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;
INSERT IGNORE INTO payment_methods (name) VALUES ('Cash'),('GCash');

CREATE TABLE IF NOT EXISTS units_of_measure (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;
INSERT IGNORE INTO units_of_measure (name) VALUES
    ('pcs'),('kg'),('liters'),('packs'),('cans'),('bottles'),('gallons');

-- Seed categories from existing data
INSERT IGNORE INTO categories (name)
SELECT DISTINCT category FROM menu WHERE category IS NOT NULL AND category != '';

INSERT IGNORE INTO categories (name)
SELECT DISTINCT category FROM inventory_supplies WHERE category IS NOT NULL AND category != '';

-- Seed order_types from existing data
INSERT IGNORE INTO order_types (name)
SELECT DISTINCT order_type FROM orders
WHERE order_type IS NOT NULL AND order_type != ''
  AND order_type NOT IN (SELECT name FROM order_types);

-- ────────────────────────────────────────────────────────────
-- PHASE 2: New Tables
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS customers (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(255),
    contact    VARCHAR(255),
    address    TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_trail (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id  INT NOT NULL,
    action     ENUM('INSERT','UPDATE','DELETE') NOT NULL,
    changed_by INT NULL,
    old_values JSON,
    new_values JSON,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ────────────────────────────────────────────────────────────
-- PHASE 3: Add FK columns + backfill
-- ────────────────────────────────────────────────────────────

-- 3A: users.role_id
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'role_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE users ADD COLUMN role_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

UPDATE users u SET u.role_id = (SELECT r.id FROM roles r WHERE r.name = u.role LIMIT 1)
WHERE u.role_id IS NULL;

-- 3B: menu.category_id
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'menu' AND COLUMN_NAME = 'category_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE menu ADD COLUMN category_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

UPDATE menu m SET m.category_id = (SELECT c.id FROM categories c WHERE c.name = m.category LIMIT 1)
WHERE m.category_id IS NULL;

-- 3C: orders FK columns
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'orders' AND COLUMN_NAME = 'order_type_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE orders ADD COLUMN order_type_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'orders' AND COLUMN_NAME = 'status_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE orders ADD COLUMN status_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'orders' AND COLUMN_NAME = 'payment_method_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE orders ADD COLUMN payment_method_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'orders' AND COLUMN_NAME = 'customer_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE orders ADD COLUMN customer_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'orders' AND COLUMN_NAME = 'cashier_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE orders ADD COLUMN cashier_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'orders' AND COLUMN_NAME = 'subtotal');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE orders ADD COLUMN subtotal DECIMAL(10,2) NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'orders' AND COLUMN_NAME = 'tax');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE orders ADD COLUMN tax DECIMAL(10,2) NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Backfill orders FK columns
UPDATE orders o SET o.order_type_id = (
    SELECT ot.id FROM order_types ot WHERE ot.name = o.order_type LIMIT 1
) WHERE o.order_type_id IS NULL AND o.order_type IS NOT NULL;

UPDATE orders o SET o.status_id = (
    SELECT os.id FROM order_statuses os WHERE os.name = o.status LIMIT 1
) WHERE o.status_id IS NULL AND o.status IS NOT NULL;

UPDATE orders o SET o.payment_method_id = (
    SELECT pm.id FROM payment_methods pm
    WHERE pm.name = CASE WHEN o.payment_method LIKE 'GCash%' THEN 'GCash' ELSE 'Cash' END
    LIMIT 1
) WHERE o.payment_method_id IS NULL;

-- Migrate customers
INSERT IGNORE INTO customers (name, contact, address)
SELECT DISTINCT customer_name, customer_contact, customer_address
FROM orders
WHERE customer_name IS NOT NULL AND customer_name != '';

UPDATE orders o SET o.customer_id = (
    SELECT c.id FROM customers c
    WHERE c.name = o.customer_name
      AND COALESCE(c.contact,'') = COALESCE(o.customer_contact,'')
    LIMIT 1
) WHERE o.customer_name IS NOT NULL AND o.customer_name != '' AND o.customer_id IS NULL;

-- Backfill subtotal/tax
UPDATE orders SET
    subtotal = ROUND(total / 1.12, 2),
    tax      = ROUND(total - (total / 1.12), 2)
WHERE subtotal IS NULL AND total IS NOT NULL;

-- 3D: order_items FK columns
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'order_items' AND COLUMN_NAME = 'menu_item_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE order_items ADD COLUMN menu_item_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'order_items' AND COLUMN_NAME = 'unit_price');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE order_items ADD COLUMN unit_price DECIMAL(10,2) NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

UPDATE order_items oi SET
    oi.menu_item_id = (SELECT m.id FROM menu m WHERE m.name = oi.item_name LIMIT 1),
    oi.unit_price   = oi.price
WHERE oi.menu_item_id IS NULL;

-- 3E: inventory_supplies FK columns
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'inventory_supplies' AND COLUMN_NAME = 'category_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE inventory_supplies ADD COLUMN category_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'inventory_supplies' AND COLUMN_NAME = 'unit_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE inventory_supplies ADD COLUMN unit_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

UPDATE inventory_supplies s SET
    s.category_id = (SELECT c.id FROM categories c WHERE c.name = s.category LIMIT 1),
    s.unit_id     = (SELECT u.id FROM units_of_measure u WHERE u.name = s.unit LIMIT 1)
WHERE s.category_id IS NULL OR s.unit_id IS NULL;

-- 3F: system_logs.user_id
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'system_logs' AND COLUMN_NAME = 'user_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE system_logs ADD COLUMN user_id INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

UPDATE system_logs sl SET sl.user_id = (
    SELECT u.id FROM users u WHERE u.display_name = sl.user LIMIT 1
) WHERE sl.user IS NOT NULL AND sl.user_id IS NULL;

-- ────────────────────────────────────────────────────────────
-- PHASE 4: Views
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW vw_order_details AS
SELECT
    o.id AS order_id, o.order_code,
    COALESCE(ot.name, o.order_type) AS order_type,
    COALESCE(os.name, o.status) AS status,
    COALESCE(pm.name,
        CASE WHEN o.payment_method LIKE 'GCash%' THEN 'GCash' ELSE o.payment_method END
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
LEFT JOIN users            u ON o.cashier_id        = u.id;

CREATE OR REPLACE VIEW vw_order_items AS
SELECT
    oi.id, oi.order_id, o.order_code,
    COALESCE(m.name, oi.item_name) AS item_name,
    m.emoji,
    COALESCE(oi.unit_price, oi.price) AS unit_price,
    oi.qty,
    COALESCE(oi.unit_price, oi.price) * oi.qty AS line_total,
    c.name AS category
FROM order_items oi
JOIN orders o ON oi.order_id = o.id
LEFT JOIN menu m ON oi.menu_item_id = m.id
LEFT JOIN categories c ON m.category_id = c.id;

CREATE OR REPLACE VIEW vw_menu AS
SELECT m.id, m.name, m.emoji, m.price,
       COALESCE(c.name, m.category) AS category,
       m.rating, m.sold, m.soldout, m.image_data
FROM menu m
LEFT JOIN categories c ON m.category_id = c.id;

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
ORDER BY sale_date DESC;

CREATE OR REPLACE VIEW vw_low_stock AS
SELECT s.id, s.name,
       COALESCE(c.name, s.category) AS category,
       COALESCE(u.name, s.unit) AS unit,
       s.quantity, s.min_stock,
       ROUND(s.quantity / NULLIF(s.min_stock, 0) * 100, 1) AS stock_pct
FROM inventory_supplies s
LEFT JOIN categories c ON s.category_id = c.id
LEFT JOIN units_of_measure u ON s.unit_id = u.id
WHERE s.quantity <= s.min_stock;

CREATE OR REPLACE VIEW vw_payment_breakdown AS
SELECT
    COALESCE(pm.name,
        CASE WHEN o.payment_method LIKE 'GCash%' THEN 'GCash' ELSE 'Cash' END
    ) AS method,
    COUNT(*) AS order_count,
    SUM(o.total) AS revenue
FROM orders o
LEFT JOIN payment_methods pm ON o.payment_method_id = pm.id
LEFT JOIN order_statuses  os ON o.status_id = os.id
WHERE COALESCE(os.name, o.status) NOT IN ('cancelled')
GROUP BY method;

SELECT '✅ Migration completed successfully.' AS result;
