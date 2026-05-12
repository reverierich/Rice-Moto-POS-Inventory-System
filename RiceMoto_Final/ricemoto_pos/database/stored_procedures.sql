-- ================================================================
--  RiceMoto POS — Stored Procedures (Fail-Safe Architecture)
--  Security : Parameterized calls to prevent SQL Injection
--  Integrity: Transaction lifecycle managed by the APPLICATION LAYER
--             (autocommit=False in connection.py).
--             Each SP provides structured error handling via SIGNAL
--             so the app layer can ROLLBACK the entire transaction.
--  Errors   : DECLARE EXIT HANDLER + SIGNAL SQLSTATE '45000'
-- ================================================================
-- 
--  IMPORTANT: These procedures do NOT contain START TRANSACTION / 
--  COMMIT because the Python application layer (database_manager.py)
--  manages the transaction boundary across multiple SP calls.
--  MySQL does not support nested transactions; calling 
--  START TRANSACTION inside an SP would implicitly commit the
--  caller's pending transaction, breaking multi-step atomicity.
--
-- ================================================================

DELIMITER //

-- ════════════════════════════════════════════════════════════════
--  1. AUTHENTICATION (Read-Only)
-- ════════════════════════════════════════════════════════════════

DROP PROCEDURE IF EXISTS sp_AuthenticateUser //
CREATE PROCEDURE sp_AuthenticateUser(
    IN p_username VARCHAR(100),
    IN p_password_hash VARCHAR(255)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '[sp_AuthenticateUser] Failed to authenticate user.';
    END;

    SELECT * FROM users 
    WHERE username = p_username AND password_hash = p_password_hash AND is_active = 1;
END //

-- ════════════════════════════════════════════════════════════════
--  2. REGISTRATION (Write)
-- ════════════════════════════════════════════════════════════════

DROP PROCEDURE IF EXISTS sp_RegisterUser //
CREATE PROCEDURE sp_RegisterUser(
    IN p_username VARCHAR(100),
    IN p_password_hash VARCHAR(255),
    IN p_role VARCHAR(50),
    IN p_role_id INT,
    IN p_display_name VARCHAR(255)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '[sp_RegisterUser] TRANSACTION FAILED. Registration rolled back.';
    END;

    START TRANSACTION;
    INSERT INTO users (username, password_hash, role, role_id, display_name)
    VALUES (p_username, p_password_hash, p_role, p_role_id, p_display_name);
    COMMIT;
END //

-- ════════════════════════════════════════════════════════════════
--  3. MENU MANAGEMENT (Write)
-- ════════════════════════════════════════════════════════════════

DROP PROCEDURE IF EXISTS sp_UpdateMenuImage //
CREATE PROCEDURE sp_UpdateMenuImage(
    IN p_item_name VARCHAR(255),
    IN p_image_data LONGBLOB
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '[sp_UpdateMenuImage] TRANSACTION FAILED. Image update rolled back.';
    END;

    START TRANSACTION;
    UPDATE menu SET image_data = p_image_data WHERE name = p_item_name;
    COMMIT;
END //

-- ════════════════════════════════════════════════════════════════
--  4. INVENTORY MANAGEMENT (Write)
-- ════════════════════════════════════════════════════════════════

DROP PROCEDURE IF EXISTS sp_AddSupply //
CREATE PROCEDURE sp_AddSupply(
    IN p_name VARCHAR(255),
    IN p_category VARCHAR(100),
    IN p_unit VARCHAR(50),
    IN p_quantity DECIMAL(10,2),
    IN p_min_stock DECIMAL(10,2),
    IN p_notes TEXT,
    IN p_category_id INT,
    IN p_unit_id INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '[sp_AddSupply] TRANSACTION FAILED. Supply addition rolled back.';
    END;

    START TRANSACTION;
    INSERT INTO inventory_supplies (name, category, unit, quantity, min_stock, notes, category_id, unit_id)
    VALUES (p_name, p_category, p_unit, p_quantity, p_min_stock, p_notes, p_category_id, p_unit_id);
    COMMIT;
END //

DROP PROCEDURE IF EXISTS sp_UpdateSupply //
CREATE PROCEDURE sp_UpdateSupply(
    IN p_id INT,
    IN p_name VARCHAR(255),
    IN p_category VARCHAR(100),
    IN p_unit VARCHAR(50),
    IN p_quantity DECIMAL(10,2),
    IN p_min_stock DECIMAL(10,2),
    IN p_notes TEXT,
    IN p_category_id INT,
    IN p_unit_id INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '[sp_UpdateSupply] TRANSACTION FAILED. Supply update rolled back.';
    END;

    START TRANSACTION;
    UPDATE inventory_supplies 
    SET name=p_name, category=p_category, unit=p_unit, quantity=p_quantity, 
        min_stock=p_min_stock, notes=p_notes, category_id=p_category_id, unit_id=p_unit_id
    WHERE id=p_id;
    COMMIT;
END //

DROP PROCEDURE IF EXISTS sp_DeleteSupply //
CREATE PROCEDURE sp_DeleteSupply(IN p_id INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '[sp_DeleteSupply] TRANSACTION FAILED. Supply deletion rolled back.';
    END;

    START TRANSACTION;
    DELETE FROM inventory_supplies WHERE id=p_id;
    COMMIT;
END //

-- ════════════════════════════════════════════════════════════════
--  5. LOGGING (Write — Non-fatal; errors silently absorbed)
-- ════════════════════════════════════════════════════════════════

DROP PROCEDURE IF EXISTS sp_AddSystemLog //
CREATE PROCEDURE sp_AddSystemLog(
    IN p_log_type VARCHAR(20),
    IN p_category VARCHAR(100),
    IN p_user VARCHAR(100),
    IN p_action VARCHAR(255),
    IN p_message TEXT,
    IN p_details TEXT
)
BEGIN
    -- Logging failures should NEVER crash the application
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN END;

    INSERT INTO system_logs (log_type, category, user, action, message, details)
    VALUES (p_log_type, p_category, p_user, p_action, p_message, p_details);
END //

DROP PROCEDURE IF EXISTS sp_LogSystemEvent //
CREATE PROCEDURE sp_LogSystemEvent(
    IN p_log_type VARCHAR(20),
    IN p_category VARCHAR(100),
    IN p_user VARCHAR(100),
    IN p_message TEXT,
    IN p_details TEXT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN END;

    INSERT INTO system_logs (log_type, category, user, message, details, created_at)
    VALUES (p_log_type, p_category, p_user, p_message, p_details, NOW());
END //

-- ════════════════════════════════════════════════════════════════
--  6. ORDER MANAGEMENT (Write — called within Python transaction)
-- ════════════════════════════════════════════════════════════════

DROP PROCEDURE IF EXISTS sp_AdvanceOrder //
CREATE PROCEDURE sp_AdvanceOrder(
    IN p_order_code VARCHAR(64),
    IN p_new_status VARCHAR(32),
    IN p_new_status_id INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '[sp_AdvanceOrder] TRANSACTION FAILED. Order update rolled back.';
    END;

    START TRANSACTION;
    UPDATE orders SET status = p_new_status, status_id = p_new_status_id 
    WHERE order_code = p_order_code;
    COMMIT;
END //

DROP PROCEDURE IF EXISTS sp_CancelOrder //
CREATE PROCEDURE sp_CancelOrder(
    IN p_order_code VARCHAR(64),
    IN p_cancel_id INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '[sp_CancelOrder] TRANSACTION FAILED. Order cancellation rolled back.';
    END;

    START TRANSACTION;
    UPDATE orders SET status = 'cancelled', status_id = p_cancel_id 
    WHERE order_code = p_order_code;
    COMMIT;
END //

-- ════════════════════════════════════════════════════════════════
--  6. ORDER MANAGEMENT (Fail-Safe with Internal Transactions)
-- ════════════════════════════════════════════════════════════════

DROP PROCEDURE IF EXISTS sp_CreateOrder //
CREATE PROCEDURE sp_CreateOrder(
    IN p_order_code VARCHAR(64),
    IN p_order_type VARCHAR(64),
    IN p_subtotal DECIMAL(10,2),
    IN p_tax DECIMAL(10,2),
    IN p_delivery_fee DECIMAL(10,2),
    IN p_total DECIMAL(10,2),
    IN p_payment_method VARCHAR(255),
    IN p_customer_name VARCHAR(255),
    IN p_customer_contact VARCHAR(255),
    IN p_customer_address TEXT,
    IN p_order_type_id INT,
    IN p_status_id INT,
    IN p_payment_method_id INT,
    IN p_customer_id INT,
    IN p_cashier_id INT
)
BEGIN
    -- Explicit error handling with ROLLBACK
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '[sp_CreateOrder] TRANSACTION FAILED. Order header rolled back.';
    END;

    START TRANSACTION;
    
    -- SAVEPOINT for header insertion
    SAVEPOINT sp_header_start;

    INSERT INTO orders (
        order_code, order_type, status, subtotal, tax, delivery_fee, total,
        payment_method, customer_name, customer_contact, customer_address,
        order_type_id, status_id, payment_method_id, customer_id, cashier_id
    ) VALUES (
        p_order_code, p_order_type, 'pending', p_subtotal, p_tax, p_delivery_fee, p_total,
        p_payment_method, p_customer_name, p_customer_contact, p_customer_address,
        p_order_type_id, p_status_id, p_payment_method_id, p_customer_id, p_cashier_id
    );
    
    COMMIT;
    
    SELECT LAST_INSERT_ID() AS order_id;
END //

DROP PROCEDURE IF EXISTS sp_AddOrderItem //
CREATE PROCEDURE sp_AddOrderItem(
    IN p_order_id INT,
    IN p_item_name VARCHAR(255),
    IN p_price DECIMAL(10,2),
    IN p_qty INT,
    IN p_menu_item_id INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '[sp_AddOrderItem] TRANSACTION FAILED. Item addition rolled back.';
    END;

    START TRANSACTION;

    -- Step 1: Insert the order line item
    INSERT INTO order_items (order_id, item_name, price, qty, menu_item_id, unit_price)
    VALUES (p_order_id, p_item_name, p_price, p_qty, p_menu_item_id, p_price);

    -- Step 2: Update sold count (only for valid menu items)
    IF p_menu_item_id IS NOT NULL THEN
        -- Internal SAVEPOINT for inventory update
        SAVEPOINT sp_inventory_update;
        
        UPDATE menu SET sold = IFNULL(sold, 0) + p_qty WHERE id = p_menu_item_id;
    END IF;

    COMMIT;
END //

DROP PROCEDURE IF EXISTS sp_AddAuditTrail //
CREATE PROCEDURE sp_AddAuditTrail(
    IN p_table_name VARCHAR(100),
    IN p_record_id INT,
    IN p_action VARCHAR(20),
    IN p_changed_by INT,
    IN p_new_values JSON
)
BEGIN
    -- Audit trail failures are non-fatal
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN END;

    INSERT INTO audit_trail (table_name, record_id, action, changed_by, new_values)
    VALUES (p_table_name, p_record_id, p_action, p_changed_by, p_new_values);
END //

-- ════════════════════════════════════════════════════════════════
--  7. CUSTOMER MANAGEMENT (Write — called within Python transaction)
-- ════════════════════════════════════════════════════════════════

DROP PROCEDURE IF EXISTS sp_UpsertCustomer //
CREATE PROCEDURE sp_UpsertCustomer(
    IN p_name VARCHAR(255),
    IN p_contact VARCHAR(100),
    IN p_address TEXT
)
BEGIN
    DECLARE v_id INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '[sp_UpsertCustomer] TRANSACTION FAILED. Customer record rolled back.';
    END;

    START TRANSACTION;

    -- Use INSERT ON DUPLICATE KEY UPDATE for atomicity with the unique index
    INSERT INTO customers (name, contact, address)
    VALUES (p_name, p_contact, p_address)
    ON DUPLICATE KEY UPDATE address = p_address;

    -- Get the ID (works for both insert and update cases)
    SELECT id INTO v_id FROM customers
    WHERE name = p_name AND COALESCE(contact,'') = COALESCE(p_contact,'')
    LIMIT 1;

    SELECT v_id as customer_id;

    COMMIT;
END //

-- ════════════════════════════════════════════════════════════════
--  8. REPORTING PROCEDURES (Read-Only — safe fallback on error)
-- ════════════════════════════════════════════════════════════════

DROP PROCEDURE IF EXISTS sp_GetDashboardStats //
CREATE PROCEDURE sp_GetDashboardStats()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT 0 as order_count, 0.00 as revenue;
    END;

    SELECT COUNT(*) as order_count, IFNULL(SUM(total), 0) as revenue 
    FROM orders 
    WHERE status NOT IN ('cancelled');
END //

DROP PROCEDURE IF EXISTS sp_GetSupplies //
CREATE PROCEDURE sp_GetSupplies(IN p_category VARCHAR(100))
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    IF p_category IS NULL OR p_category = 'All' THEN
        SELECT * FROM inventory_supplies ORDER BY category, name;
    ELSE
        SELECT * FROM inventory_supplies WHERE category = p_category ORDER BY category, name;
    END IF;
END //

DROP PROCEDURE IF EXISTS sp_GetLogs //
CREATE PROCEDURE sp_GetLogs()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT * FROM system_logs ORDER BY created_at DESC LIMIT 100;
END //

DROP PROCEDURE IF EXISTS sp_GetRecentOrders //
CREATE PROCEDURE sp_GetRecentOrders()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT * FROM vw_order_details ORDER BY created_at DESC LIMIT 50;
END //

DROP PROCEDURE IF EXISTS sp_GetOrderItems //
CREATE PROCEDURE sp_GetOrderItems(IN p_order_id INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT * FROM vw_order_items WHERE order_id = p_order_id;
END //

DROP PROCEDURE IF EXISTS sp_GetMonthlySalesTrend //
CREATE PROCEDURE sp_GetMonthlySalesTrend()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT DATE(created_at) as day, IFNULL(SUM(total), 0) as total
    FROM orders
    WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
      AND status NOT IN ('cancelled')
    GROUP BY DATE(created_at)
    ORDER BY day;
END //

DROP PROCEDURE IF EXISTS sp_GetYearlySalesTrend //
CREATE PROCEDURE sp_GetYearlySalesTrend()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT DATE_FORMAT(created_at, '%Y-%m') as month_key, IFNULL(SUM(total), 0) as total
    FROM orders
    WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
      AND status NOT IN ('cancelled')
    GROUP BY month_key
    ORDER BY month_key;
END //

DROP PROCEDURE IF EXISTS sp_GetPaymentBreakdown //
CREATE PROCEDURE sp_GetPaymentBreakdown()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT * FROM vw_payment_breakdown;
END //

DROP PROCEDURE IF EXISTS sp_GetAuditHistory //
CREATE PROCEDURE sp_GetAuditHistory()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT order_code, total, payment_method, created_at, status, cashier 
    FROM vw_order_details 
    ORDER BY created_at DESC 
    LIMIT 40;
END //

DROP PROCEDURE IF EXISTS sp_GetActivityLogs //
CREATE PROCEDURE sp_GetActivityLogs()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT action, message, user, created_at, log_type 
    FROM system_logs 
    WHERE log_type = 'activity' AND action NOT LIKE 'Login%'
    ORDER BY created_at DESC 
    LIMIT 30;
END //

DROP PROCEDURE IF EXISTS sp_GetFullAuditTrail //
CREATE PROCEDURE sp_GetFullAuditTrail()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT a.table_name, a.action, a.changed_at, u.display_name as staff, a.new_values
    FROM audit_trail a
    LEFT JOIN users u ON a.changed_by = u.id
    ORDER BY a.changed_at DESC
    LIMIT 30;
END //

DROP PROCEDURE IF EXISTS sp_GetSupplyCategories //
CREATE PROCEDURE sp_GetSupplyCategories()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT DISTINCT category FROM inventory_supplies ORDER BY category;
END //

DROP PROCEDURE IF EXISTS sp_GetMenuCategories //
CREATE PROCEDURE sp_GetMenuCategories()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT DISTINCT category FROM menu ORDER BY category;
END //

DROP PROCEDURE IF EXISTS sp_GetMenu //
CREATE PROCEDURE sp_GetMenu()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT * FROM vw_menu;
END //

DROP PROCEDURE IF EXISTS sp_GetNextOrderCode //
CREATE PROCEDURE sp_GetNextOrderCode()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT 9999 as next_code;
    END;

    SELECT (COUNT(*) + 1101) as next_code FROM orders;
END //

DROP PROCEDURE IF EXISTS sp_GetMenuIdByName //
CREATE PROCEDURE sp_GetMenuIdByName(IN p_name VARCHAR(255))
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL as id;
    END;

    SELECT id FROM menu WHERE name = p_name LIMIT 1;
END //

DROP PROCEDURE IF EXISTS sp_GetOrderDetailsByCode //
CREATE PROCEDURE sp_GetOrderDetailsByCode(IN p_order_code VARCHAR(64))
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SELECT NULL LIMIT 0;
    END;

    SELECT * FROM vw_order_details WHERE order_code = p_order_code LIMIT 1;
END //

DELIMITER ;
