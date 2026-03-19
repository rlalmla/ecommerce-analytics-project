-- ============================================================
-- E-Commerce Analytics Platform — PostgreSQL Schema
-- Amazon India 2015-2025
-- ============================================================

-- Drop tables if they exist 
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS time_dimension CASCADE;

-- ============================================================
-- 1. TIME DIMENSION TABLE
-- ============================================================
CREATE TABLE time_dimension (
    date_key        DATE PRIMARY KEY,
    day             INT,
    month           INT,
    month_name      VARCHAR(15),
    quarter         INT,
    year            INT,
    week_of_year    INT,
    day_of_week     INT,
    day_name        VARCHAR(15),
    is_weekend      BOOLEAN,
    is_festival     BOOLEAN,
    festival_name   VARCHAR(50)
);

-- ============================================================
-- 2. CUSTOMERS TABLE
-- ============================================================
CREATE TABLE customers (
    customer_id         VARCHAR(50) PRIMARY KEY,
    customer_city       VARCHAR(100),
    customer_state      VARCHAR(100),
    city_tier           VARCHAR(20),       -- Metro / Tier1 / Tier2 / Rural
    age_group           VARCHAR(30),
    is_prime_member     BOOLEAN,
    first_order_date    DATE,
    last_order_date     DATE,
    total_orders        INT,
    total_spent         NUMERIC(14, 2),
    avg_order_value     NUMERIC(10, 2),
    rfm_segment         VARCHAR(30)        -- Champions / Loyal / At Risk / etc.
);

-- ============================================================
-- 3. PRODUCTS TABLE
-- ============================================================
CREATE TABLE products (
    product_id          VARCHAR(50) PRIMARY KEY,
    product_name        VARCHAR(300),
    category            VARCHAR(100),
    sub_category        VARCHAR(100),
    brand               VARCHAR(100),
    original_price_inr  NUMERIC(12, 2),
    is_prime_eligible   BOOLEAN,
    avg_rating          NUMERIC(3, 1),
    total_units_sold    INT,
    total_revenue       NUMERIC(14, 2),
    return_rate         NUMERIC(5, 2)
);

-- ============================================================
-- 4. TRANSACTIONS TABLE (main fact table)
-- ============================================================
CREATE TABLE transactions (
    order_id            VARCHAR(50) PRIMARY KEY,
    order_date          DATE NOT NULL,
    customer_id         VARCHAR(50) REFERENCES customers(customer_id),
    product_id          VARCHAR(50) REFERENCES products(product_id),
    category            VARCHAR(100),
    sub_category        VARCHAR(100),
    brand               VARCHAR(100),
    quantity            INT,
    original_price_inr  NUMERIC(12, 2),
    discount_percent    NUMERIC(5, 2),
    final_price_inr     NUMERIC(12, 2),
    total_amount_inr    NUMERIC(14, 2),
    payment_method      VARCHAR(50),
    customer_city       VARCHAR(100),
    customer_state      VARCHAR(100),
    city_tier           VARCHAR(20),
    is_prime_member     BOOLEAN,
    is_prime_eligible   BOOLEAN,
    is_festival_sale    BOOLEAN,
    festival_name       VARCHAR(50),
    delivery_days       INT,
    customer_rating     NUMERIC(3, 1),
    is_returned         BOOLEAN,
    age_group           VARCHAR(30),
    year                INT,
    month               INT,
    quarter             INT
);

-- ============================================================
-- INDEXES for dashboard query performance
-- ============================================================
CREATE INDEX idx_txn_date       ON transactions(order_date);
CREATE INDEX idx_txn_year       ON transactions(year);
CREATE INDEX idx_txn_category   ON transactions(category);
CREATE INDEX idx_txn_city       ON transactions(customer_city);
CREATE INDEX idx_txn_customer   ON transactions(customer_id);
CREATE INDEX idx_txn_product    ON transactions(product_id);
CREATE INDEX idx_txn_payment    ON transactions(payment_method);
CREATE INDEX idx_txn_festival   ON transactions(is_festival_sale);
CREATE INDEX idx_txn_prime      ON transactions(is_prime_member);
CREATE INDEX idx_cust_tier      ON customers(city_tier);
CREATE INDEX idx_prod_category  ON products(category);

-- ============================================================
-- VIEWS for common dashboard queries
-- ============================================================

-- Monthly revenue summary
CREATE OR REPLACE VIEW vw_monthly_revenue AS
SELECT
    year,
    month,
    TO_CHAR(DATE_TRUNC('month', order_date), 'Mon YYYY') AS month_label,
    COUNT(order_id)                  AS total_orders,
    SUM(total_amount_inr)            AS total_revenue,
    AVG(total_amount_inr)            AS avg_order_value,
    COUNT(DISTINCT customer_id)      AS unique_customers
FROM transactions
GROUP BY year, month, DATE_TRUNC('month', order_date)
ORDER BY year, month;

-- Category performance summary
CREATE OR REPLACE VIEW vw_category_performance AS
SELECT
    category,
    COUNT(order_id)              AS total_orders,
    SUM(total_amount_inr)        AS total_revenue,
    AVG(discount_percent)        AS avg_discount,
    AVG(customer_rating)         AS avg_rating,
    SUM(CASE WHEN is_returned THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 AS return_rate_pct
FROM transactions
GROUP BY category
ORDER BY total_revenue DESC;

-- City tier revenue
CREATE OR REPLACE VIEW vw_tier_revenue AS
SELECT
    city_tier,
    COUNT(DISTINCT customer_id)  AS unique_customers,
    COUNT(order_id)              AS total_orders,
    SUM(total_amount_inr)        AS total_revenue,
    AVG(total_amount_inr)        AS avg_order_value
FROM transactions
GROUP BY city_tier;

-- Payment method trends
CREATE OR REPLACE VIEW vw_payment_trends AS
SELECT
    year,
    payment_method,
    COUNT(order_id)         AS total_orders,
    SUM(total_amount_inr)   AS total_revenue
FROM transactions
GROUP BY year, payment_method
ORDER BY year, total_revenue DESC;

-- Festival vs non-festival comparison
CREATE OR REPLACE VIEW vw_festival_impact AS
SELECT
    is_festival_sale,
    festival_name,
    COUNT(order_id)             AS total_orders,
    SUM(total_amount_inr)       AS total_revenue,
    AVG(total_amount_inr)       AS avg_order_value,
    AVG(discount_percent)       AS avg_discount
FROM transactions
GROUP BY is_festival_sale, festival_name;
