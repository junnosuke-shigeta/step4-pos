SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS staff (
  staff_id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'STAFF'
);

CREATE TABLE IF NOT EXISTS customer (
  customer_id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS product (
  product_code VARCHAR(50) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  base_price DECIMAL(12,2) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS discount_plan (
  id INT AUTO_INCREMENT PRIMARY KEY,
  product_code VARCHAR(50) NOT NULL,
  customer_only BOOLEAN NOT NULL DEFAULT TRUE,
  discount_type VARCHAR(20) NOT NULL,
  discount_value DECIMAL(12,2) NOT NULL,
  start_date DATETIME NOT NULL,
  end_date DATETIME NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT fk_discount_product FOREIGN KEY (product_code) REFERENCES product(product_code)
);

CREATE TABLE IF NOT EXISTS tax_rate (
  id INT AUTO_INCREMENT PRIMARY KEY,
  rate DECIMAL(8,4) NOT NULL,
  start_date DATETIME NOT NULL,
  end_date DATETIME NULL
);

CREATE TABLE IF NOT EXISTS purchase (
  id INT AUTO_INCREMENT PRIMARY KEY,
  purchased_at DATETIME NOT NULL,
  staff_id VARCHAR(50) NOT NULL,
  customer_id VARCHAR(50) NULL,
  subtotal_excl_tax DECIMAL(12,2) NOT NULL,
  tax_amount DECIMAL(12,2) NOT NULL,
  total_amount DECIMAL(12,2) NOT NULL,
  tax_rate_applied DECIMAL(8,4) NOT NULL,
  CONSTRAINT fk_purchase_staff FOREIGN KEY (staff_id) REFERENCES staff(staff_id),
  CONSTRAINT fk_purchase_customer FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

CREATE TABLE IF NOT EXISTS purchase_item (
  id INT AUTO_INCREMENT PRIMARY KEY,
  purchase_id INT NOT NULL,
  product_code VARCHAR(50) NOT NULL,
  product_name VARCHAR(255) NOT NULL,
  quantity INT NOT NULL,
  base_price DECIMAL(12,2) NOT NULL,
  discounted_price DECIMAL(12,2) NOT NULL,
  final_amount DECIMAL(12,2) NOT NULL,
  CONSTRAINT fk_purchase_item_purchase FOREIGN KEY (purchase_id) REFERENCES purchase(id)
);

-- Default seed data for local verification only.
INSERT INTO staff (staff_id, name, password_hash, role)
VALUES ('ADMIN001', '管理者', '$2b$12$RG5lDU106nZY.7pbtgvzhe9vfvJU.XfoxhrNXnsAUAepaA/n7t41i', 'ADMIN')
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  password_hash = VALUES(password_hash),
  role = VALUES(role);

INSERT INTO staff (staff_id, name, password_hash, role)
VALUES ('STAFF001', 'レジ担当', '$2b$12$RG5lDU106nZY.7pbtgvzhe9vfvJU.XfoxhrNXnsAUAepaA/n7t41i', 'STAFF')
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  password_hash = VALUES(password_hash),
  role = VALUES(role);

INSERT INTO customer (customer_id, name)
VALUES ('MEM001', 'テスト会員')
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO product (product_code, name, base_price, is_active)
VALUES
  ('4901234567894', 'ミネラルウォーター', 100.00, TRUE),
  ('4901234567895', '食パン', 220.00, TRUE)
ON DUPLICATE KEY UPDATE name = VALUES(name), base_price = VALUES(base_price), is_active = VALUES(is_active);

INSERT INTO discount_plan (product_code, customer_only, discount_type, discount_value, start_date, end_date, is_active)
SELECT '4901234567894', TRUE, 'RATE', 10.00, '2026-01-01 00:00:00', NULL, TRUE
WHERE NOT EXISTS (
  SELECT 1 FROM discount_plan WHERE product_code = '4901234567894' AND customer_only = TRUE AND discount_type = 'RATE' AND discount_value = 10.00
);

INSERT INTO tax_rate (rate, start_date, end_date)
SELECT 0.10, '2020-01-01 00:00:00', NULL
WHERE NOT EXISTS (
  SELECT 1 FROM tax_rate WHERE rate = 0.10 AND start_date = '2020-01-01 00:00:00'
);
