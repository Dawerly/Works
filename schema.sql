PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK(length(trim(name)) BETWEEN 1 AND 120),
    attribute_schema TEXT NOT NULL DEFAULT '[]'
        CHECK(json_valid(attribute_schema) AND json_type(attribute_schema) = 'array'),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 200),
    description TEXT NOT NULL DEFAULT '',
    -- Monetary amounts are stored as integer minor units, never SQLite REAL.
    price_cents INTEGER NOT NULL CHECK(typeof(price_cents) = 'integer' AND price_cents BETWEEN 0 AND 99999999999),
    discount_percentage NUMERIC NOT NULL DEFAULT 0
        CHECK(typeof(discount_percentage) IN ('integer', 'real') AND discount_percentage BETWEEN 0 AND 100),
    attributes TEXT NOT NULL DEFAULT '{}'
        CHECK(json_valid(attributes) AND json_type(attributes) = 'object'),
    image_filename TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
