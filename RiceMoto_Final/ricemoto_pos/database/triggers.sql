-- RiceMoto POS — Database Triggers
-- Automates audit logging and data integrity

-- ── 1. MENU AUDIT LOGS ──────────────────────────────────────────

DROP TRIGGER IF EXISTS tr_AfterMenuUpdate;
DELIMITER //
CREATE TRIGGER tr_AfterMenuUpdate
AFTER UPDATE ON menu
FOR EACH ROW
BEGIN
    IF OLD.price <> NEW.price THEN
        CALL sp_LogSystemEvent(
            'security', 
            'Price Change', 
            'System',
            CONCAT('Item: ', NEW.name, ' | Price updated from ', OLD.price, ' to ', NEW.price),
            CONCAT('ID: ', NEW.id)
        );
    END IF;
    
    IF OLD.soldout <> NEW.soldout THEN
        CALL sp_LogSystemEvent(
            'activity', 
            'Stock Status', 
            'System',
            CONCAT('Item: ', NEW.name, ' | Status changed to ', IF(NEW.soldout, 'Sold Out', 'Available')),
            CONCAT('ID: ', NEW.id)
        );
    END IF;
END //
DELIMITER ;

-- ── 2. ORDER AUDIT LOGS ──────────────────────────────────────────

DROP TRIGGER IF EXISTS tr_AfterOrderInsert;
DELIMITER //
CREATE TRIGGER tr_AfterOrderInsert
AFTER INSERT ON orders
FOR EACH ROW
BEGIN
    CALL sp_LogSystemEvent(
        'activity', 
        'New Order', 
        'System',
        CONCAT('Order ', NEW.order_code, ' created | Total: ', NEW.total),
        CONCAT('ID: ', NEW.id)
    );
END //
DELIMITER ;

DROP TRIGGER IF EXISTS tr_AfterOrderUpdate;
DELIMITER //
CREATE TRIGGER tr_AfterOrderUpdate
AFTER UPDATE ON orders
FOR EACH ROW
BEGIN
    IF OLD.status <> NEW.status THEN
        CALL sp_LogSystemEvent(
            'activity', 
            'Order Status', 
            'System',
            CONCAT('Order ', NEW.order_code, ' changed from ', OLD.status, ' to ', NEW.status),
            CONCAT('ID: ', NEW.id)
        );
    END IF;
END //
DELIMITER ;

-- ── 3. SUPPLIES AUDIT LOGS ───────────────────────────────────────

DROP TRIGGER IF EXISTS tr_AfterSupplyUpdate;
DELIMITER //
CREATE TRIGGER tr_AfterSupplyUpdate
AFTER UPDATE ON inventory_supplies
FOR EACH ROW
BEGIN
    -- Log significant stock changes or low stock alerts
    IF NEW.quantity <= NEW.min_stock AND OLD.quantity > OLD.min_stock THEN
        CALL sp_LogSystemEvent(
            'error', 
            'Low Stock Alert', 
            'System',
            CONCAT('Supply: ', NEW.name, ' is running low (', NEW.quantity, ' ', NEW.unit, ' left)'),
            CONCAT('ID: ', NEW.id)
        );
    END IF;
END //
DELIMITER ;
