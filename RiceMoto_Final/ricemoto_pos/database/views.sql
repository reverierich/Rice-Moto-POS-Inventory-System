-- ================================================================
--  RiceMoto POS — Database Views
--  Purpose : Abstraction layer for reporting, analytics, and UI
--  Tables  : orders, order_items, menu, inventory_supplies,
--            customers, users, categories, order_types,
--            order_statuses, payment_methods, units_of_measure
--
--  Each view joins normalized FK columns back to their lookup
--  tables, falling back to legacy text columns via COALESCE()
--  for backward compatibility during the migration period.
--
--  DELIMITER: //  (split by the script loader)
-- ================================================================

DELIMITER //

-- ════════════════════════════════════════════════════════════════
--  1. vw_order_details
--     Full order header with all lookups resolved.
--     Used by: Receipt dialog, Recent Transactions, Analytics
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_order_details //
CREATE VIEW vw_order_details AS
SELECT
    o.id            AS order_id,
    o.order_code,
    COALESCE(ot.name, o.order_type)                              AS order_type,
    COALESCE(os.name, o.status)                                  AS status,
    COALESCE(pm.name,
        CASE WHEN o.payment_method LIKE 'GCash%' THEN 'GCash'
             ELSE o.payment_method END
    )                                                            AS payment_method,
    o.payment_method                                             AS payment_method_raw,
    o.subtotal,
    o.tax,
    o.delivery_fee,
    o.total,
    COALESCE(c.name, o.customer_name)                            AS customer_name,
    COALESCE(c.contact, o.customer_contact)                      AS customer_contact,
    COALESCE(c.address, o.customer_address)                      AS customer_address,
    u.display_name                                               AS cashier,
    o.created_at,
    o.updated_at
FROM orders o
    LEFT JOIN order_types     ot ON o.order_type_id     = ot.id
    LEFT JOIN order_statuses  os ON o.status_id         = os.id
    LEFT JOIN payment_methods pm ON o.payment_method_id = pm.id
    LEFT JOIN customers        c ON o.customer_id       = c.id
    LEFT JOIN users            u ON o.cashier_id        = u.id //

-- ════════════════════════════════════════════════════════════════
--  2. vw_order_items
--     Line-level order items with menu info resolved.
--     Used by: Receipt dialog, Order detail views
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_order_items //
CREATE VIEW vw_order_items AS
SELECT
    oi.id,
    oi.order_id,
    COALESCE(m.name, oi.item_name)               AS item_name,
    m.emoji,
    COALESCE(oi.unit_price, oi.price)             AS unit_price,
    oi.qty,
    COALESCE(oi.unit_price, oi.price) * oi.qty    AS line_total
FROM order_items oi
    LEFT JOIN menu m ON oi.menu_item_id = m.id //

-- ════════════════════════════════════════════════════════════════
--  3. vw_menu
--     Full menu catalog with category names resolved.
--     Used by: Menu grid, Cashier view, Search
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_menu //
CREATE VIEW vw_menu AS
SELECT
    m.id,
    m.name,
    m.emoji,
    m.price,
    COALESCE(c.name, m.category)    AS category,
    m.rating,
    m.sold,
    m.soldout,
    m.image_data
FROM menu m
    LEFT JOIN categories c ON m.category_id = c.id //

-- ════════════════════════════════════════════════════════════════
--  4. vw_low_stock
--     Inventory items at or below minimum stock level.
--     Used by: Dashboard alerts, Inventory management
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_low_stock //
CREATE VIEW vw_low_stock AS
SELECT
    s.id,
    s.name,
    COALESCE(c.name, s.category)    AS category,
    COALESCE(u.name, s.unit)        AS unit,
    s.quantity,
    s.min_stock,
    ROUND(s.quantity / NULLIF(s.min_stock, 0) * 100, 1) AS stock_pct
FROM inventory_supplies s
    LEFT JOIN categories      c ON s.category_id = c.id
    LEFT JOIN units_of_measure u ON s.unit_id     = u.id
WHERE s.quantity <= s.min_stock //

-- ════════════════════════════════════════════════════════════════
--  5. vw_daily_sales
--     Aggregated sales per day (excludes cancelled orders).
--     Used by: Analytics dashboard, Sales trend chart
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_daily_sales //
CREATE VIEW vw_daily_sales AS
SELECT
    DATE(o.created_at)   AS sale_date,
    COUNT(*)             AS order_count,
    SUM(o.subtotal)      AS gross_subtotal,
    SUM(o.tax)           AS total_tax,
    SUM(o.delivery_fee)  AS total_delivery_fees,
    SUM(o.total)         AS gross_total
FROM orders o
    LEFT JOIN order_statuses os ON o.status_id = os.id
WHERE COALESCE(os.name, o.status) NOT IN ('cancelled')
GROUP BY DATE(o.created_at)
ORDER BY sale_date DESC //

-- ════════════════════════════════════════════════════════════════
--  6. vw_payment_breakdown
--     Revenue split by payment method (excludes cancelled).
--     Used by: Analytics dashboard, Payment pie chart
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_payment_breakdown //
CREATE VIEW vw_payment_breakdown AS
SELECT
    COALESCE(pm.name,
        CASE WHEN o.payment_method LIKE 'GCash%' THEN 'GCash'
             ELSE 'Cash' END
    )               AS method,
    COUNT(*)        AS order_count,
    SUM(o.total)    AS revenue
FROM orders o
    LEFT JOIN payment_methods pm ON o.payment_method_id = pm.id
    LEFT JOIN order_statuses  os ON o.status_id         = os.id
WHERE COALESCE(os.name, o.status) NOT IN ('cancelled')
GROUP BY method //

-- ════════════════════════════════════════════════════════════════
--  7. vw_inventory_full
--     Complete inventory listing with resolved category & unit.
--     Used by: Inventory management, Supply reports
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_inventory_full //
CREATE VIEW vw_inventory_full AS
SELECT
    s.id,
    s.name,
    COALESCE(c.name, s.category)    AS category,
    COALESCE(u.name, s.unit)        AS unit,
    s.quantity,
    s.min_stock,
    s.notes,
    s.updated_at,
    CASE
        WHEN s.quantity <= 0          THEN 'OUT_OF_STOCK'
        WHEN s.quantity <= s.min_stock THEN 'LOW_STOCK'
        ELSE 'IN_STOCK'
    END AS stock_status,
    ROUND(s.quantity / NULLIF(s.min_stock, 0) * 100, 1) AS stock_pct
FROM inventory_supplies s
    LEFT JOIN categories       c ON s.category_id = c.id
    LEFT JOIN units_of_measure u ON s.unit_id     = u.id //

-- ════════════════════════════════════════════════════════════════
--  8. vw_top_selling_items
--     Menu items ranked by total sold count.
--     Used by: Analytics dashboard, Popular dishes section
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_top_selling_items //
CREATE VIEW vw_top_selling_items AS
SELECT
    m.id,
    m.name,
    m.emoji,
    m.price,
    COALESCE(c.name, m.category)   AS category,
    m.sold,
    m.soldout,
    m.rating
FROM menu m
    LEFT JOIN categories c ON m.category_id = c.id
ORDER BY m.sold DESC //

-- ════════════════════════════════════════════════════════════════
--  9. vw_customer_orders
--     Customer purchase history (Delivery orders only).
--     Used by: Customer management, Delivery reports
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_customer_orders //
CREATE VIEW vw_customer_orders AS
SELECT
    c.id            AS customer_id,
    c.name          AS customer_name,
    c.contact       AS customer_contact,
    c.address       AS customer_address,
    COUNT(o.id)     AS total_orders,
    SUM(o.total)    AS total_spent,
    MAX(o.created_at) AS last_order_date
FROM customers c
    INNER JOIN orders o ON o.customer_id = c.id
    LEFT JOIN order_statuses os ON o.status_id = os.id
WHERE COALESCE(os.name, o.status) NOT IN ('cancelled')
GROUP BY c.id, c.name, c.contact, c.address //

-- ════════════════════════════════════════════════════════════════
--  10. vw_staff_performance
--      Per-cashier order count and revenue.
--      Used by: Staff reports, Analytics
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_staff_performance //
CREATE VIEW vw_staff_performance AS
SELECT
    u.id            AS staff_id,
    u.display_name  AS staff_name,
    u.role,
    COUNT(o.id)     AS orders_handled,
    IFNULL(SUM(o.total), 0)  AS total_revenue,
    MAX(o.created_at)        AS last_order_time
FROM users u
    LEFT JOIN orders o ON o.cashier_id = u.id
        AND o.status NOT IN ('cancelled')
WHERE u.is_active = 1
GROUP BY u.id, u.display_name, u.role //

-- ════════════════════════════════════════════════════════════════
--  11. vw_hourly_sales
--      Sales aggregated by hour of day (for peak hour analysis).
--      Used by: Analytics dashboard
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_hourly_sales //
CREATE VIEW vw_hourly_sales AS
SELECT
    HOUR(o.created_at)  AS sale_hour,
    COUNT(*)            AS order_count,
    SUM(o.total)        AS revenue
FROM orders o
    LEFT JOIN order_statuses os ON o.status_id = os.id
WHERE COALESCE(os.name, o.status) NOT IN ('cancelled')
GROUP BY HOUR(o.created_at)
ORDER BY sale_hour //

-- ════════════════════════════════════════════════════════════════
--  12. vw_order_type_breakdown
--      Revenue and order count per order type.
--      Used by: Analytics dashboard
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_order_type_breakdown //
CREATE VIEW vw_order_type_breakdown AS
SELECT
    COALESCE(ot.name, o.order_type)   AS order_type,
    COUNT(*)                          AS order_count,
    SUM(o.total)                      AS revenue,
    AVG(o.total)                      AS avg_order_value
FROM orders o
    LEFT JOIN order_types    ot ON o.order_type_id = ot.id
    LEFT JOIN order_statuses os ON o.status_id     = os.id
WHERE COALESCE(os.name, o.status) NOT IN ('cancelled')
GROUP BY order_type //

-- ════════════════════════════════════════════════════════════════
--  13. vw_recent_audit
--      Combined view of audit trail with staff names.
--      Used by: Audit log panel
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS vw_recent_audit //
CREATE VIEW vw_recent_audit AS
SELECT
    a.id,
    a.table_name,
    a.record_id,
    a.action,
    u.display_name      AS changed_by_name,
    a.old_values,
    a.new_values,
    a.changed_at
FROM audit_trail a
    LEFT JOIN users u ON a.changed_by = u.id
ORDER BY a.changed_at DESC //

DELIMITER ;
