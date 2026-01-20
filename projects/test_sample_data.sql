-- Sample test database for Query Tester integration testing

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    age INTEGER,
    created_at TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT,
    price REAL,
    stock_quantity INTEGER,
    supplier_id INTEGER
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    order_date TEXT,
    total_amount REAL,
    status TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Insert sample users
INSERT INTO users (username, email, age, created_at, is_active) VALUES
    ('alice', 'alice@example.com', 28, '2024-01-15', 1),
    ('bob', 'bob@example.com', 35, '2024-02-20', 1),
    ('charlie', 'charlie@example.com', 42, '2024-03-10', 0),
    ('diana', 'diana@example.com', 31, '2024-04-05', 1),
    ('eve', 'eve@example.com', 26, '2024-05-12', 1);

-- Insert sample products
INSERT INTO products (product_name, category, price, stock_quantity, supplier_id) VALUES
    ('Laptop', 'Electronics', 999.99, 50, 1),
    ('Mouse', 'Electronics', 29.99, 200, 1),
    ('Keyboard', 'Electronics', 79.99, 150, 1),
    ('Desk Chair', 'Furniture', 299.99, 30, 2),
    ('Monitor', 'Electronics', 399.99, 75, 1),
    ('Desk Lamp', 'Furniture', 49.99, 100, 2),
    ('Notebook', 'Stationery', 5.99, 500, 3),
    ('Pen Set', 'Stationery', 12.99, 300, 3);

-- Insert sample orders
INSERT INTO orders (user_id, order_date, total_amount, status) VALUES
    (1, '2024-06-01', 1029.98, 'completed'),
    (1, '2024-06-15', 79.99, 'completed'),
    (2, '2024-06-10', 399.99, 'completed'),
    (2, '2024-07-01', 649.98, 'shipped'),
    (3, '2024-06-20', 299.99, 'cancelled'),
    (4, '2024-07-05', 1499.95, 'processing'),
    (4, '2024-07-10', 18.98, 'completed'),
    (5, '2024-07-15', 449.98, 'shipped');
