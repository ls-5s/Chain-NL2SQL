PRAGMA foreign_keys = ON;

-- Recreate the demo schema so every initialization starts from the same state.
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Product catalog used by order and aggregation examples.
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL
);

-- Orders reference users and are intentionally simple enough for NL2SQL demos.
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL,
    total_amount REAL NOT NULL,
    created_at TEXT NOT NULL
);

-- Line items provide a second join path through products.
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL
);

-- Deterministic seed data keeps tests and demonstrations reproducible.
INSERT INTO users (id, name, email, created_at) VALUES
    (1, 'Alice', 'alice@example.test', '2026-01-05'),
    (2, 'Bob', 'bob@example.test', '2026-01-06'),
    (3, 'Carol', 'carol@example.test', '2026-01-07');

INSERT INTO products (id, name, category, price) VALUES
    (1, 'Keyboard', 'accessories', 79.00),
    (2, 'Monitor', 'displays', 249.00),
    (3, 'Mouse', 'accessories', 39.00),
    (4, 'USB Hub', 'accessories', 29.00);

INSERT INTO orders (id, user_id, status, total_amount, created_at) VALUES
    (1, 1, 'paid', 328.00, '2026-02-01'),
    (2, 2, 'paid', 79.00, '2026-02-02'),
    (3, 1, 'pending', 68.00, '2026-02-03');

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES
    (1, 1, 2, 1, 249.00),
    (2, 1, 1, 1, 79.00),
    (3, 2, 1, 1, 79.00),
    (4, 3, 3, 1, 39.00),
    (5, 3, 4, 1, 29.00);
