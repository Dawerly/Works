"""Shared catalogue, one-time legacy import and exact price calculations."""
import json
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATEGORY_ICONS = {'liquid': '💧', 'pod': '🔋', 'disposable': '💨', 'access': '⚙️'}
CATEGORIES = [('liquid', 'Рідини'), ('pod', 'Под-системи'),
              ('disposable', 'Одноразки'), ('access', 'Комплектуючі')]


def initialize(database, seed=True):
    database = Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(database, timeout=15)
    try:
        # SQLite backup includes any uncheckpointed WAL pages.
        exists = con.execute("SELECT 1 FROM sqlite_master WHERE name='catalog_migrations'").fetchone()
        if not exists and con.execute("SELECT 1 FROM sqlite_master WHERE name='orders'").fetchone():
            backup = database.with_name(database.stem + '-before-catalog.sqlite3')
            if not backup.exists():
                dest = sqlite3.connect(backup)
                try:
                    con.backup(dest)
                finally:
                    dest.close()
        if con.execute("SELECT 1 FROM sqlite_master WHERE name='categories'").fetchone() and 'icon' not in {r[1] for r in con.execute('PRAGMA table_info(categories)')}:
            backup = database.with_name(database.stem + '-before-category-icons.sqlite3')
            if not backup.exists():
                dest = sqlite3.connect(backup)
                try:
                    con.backup(dest)
                finally:
                    dest.close()
        con.executescript((ROOT / 'schema.sql').read_text(encoding='utf-8'))
        con.execute('BEGIN IMMEDIATE')
        additions = {'categories': [('slug', 'TEXT'), ('icon', "TEXT NOT NULL DEFAULT ''")], 'products': [
            ('brand', "TEXT NOT NULL DEFAULT ''"), ('spec', "TEXT NOT NULL DEFAULT ''"),
            ('external_image', 'TEXT'), ('vol', 'TEXT'), ('mg', 'TEXT')]}
        for table, columns in additions.items():
            present = {r[1] for r in con.execute('PRAGMA table_info(' + table + ')')}
            for name, definition in columns:
                if name not in present:
                    con.execute('ALTER TABLE ' + table + ' ADD COLUMN ' + name + ' ' + definition)
                    if table == 'categories' and name == 'icon':
                        for row in con.execute('SELECT id,slug FROM categories').fetchall():
                            con.execute('UPDATE categories SET icon=? WHERE id=?', (CATEGORY_ICONS.get(row[1], '🧩'), row[0]))
        if con.execute("SELECT 1 FROM sqlite_master WHERE name='orders'").fetchone():
            if 'total_cents' not in {r[1] for r in con.execute('PRAGMA table_info(orders)')}:
                con.execute('ALTER TABLE orders ADD COLUMN total_cents INTEGER NOT NULL DEFAULT 0')
                for oid, total in con.execute('SELECT id,total FROM orders').fetchall():
                    con.execute('UPDATE orders SET total_cents=? WHERE id=?',
                                (int((Decimal(str(total)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)), oid))
        con.execute('CREATE TABLE IF NOT EXISTS catalog_migrations (name TEXT PRIMARY KEY)')
        if seed and not con.execute("SELECT 1 FROM catalog_migrations WHERE name='legacy-import-v1'").fetchone():
            ids = {}
            for slug, name in CATEGORIES:
                fields = ([{'key': 'volume', 'label': 'Об’єм, мл', 'required': False},
                           {'key': 'strength', 'label': 'Міцність, мг', 'required': False}]
                          if slug == 'liquid' else [])
                ids[slug] = con.execute('INSERT INTO categories(name,attribute_schema,slug,icon) VALUES(?,?,?,?)',
                                       (name, json.dumps(fields, ensure_ascii=False), slug, CATEGORY_ICONS[slug])).lastrowid
            for p in json.loads((ROOT / 'catalog-seed.json').read_text(encoding='utf-8')):
                attrs = ({'volume': str(p['vol']), 'strength': str(p['mg'])} if p['cat'] == 'liquid' else {})
                con.execute('''INSERT INTO products
                    (id,category_id,name,price_cents,attributes,brand,spec,external_image,vol,mg)
                    VALUES(?,?,?,?,?,?,?,?,?,?)''',
                    (p['id'], ids[p['cat']], p['name'], int(Decimal(str(p['price'])) * 100),
                     json.dumps(attrs, ensure_ascii=False), p.get('brand', ''), p.get('spec', ''),
                     p.get('image'), p.get('vol'), p.get('mg')))
            con.execute("INSERT INTO catalog_migrations VALUES('legacy-import-v1')")
        # Never reuse a removed product/category ID: historical orders and carts use them.
        con.execute('CREATE TABLE IF NOT EXISTS catalog_ids (kind TEXT PRIMARY KEY, next_id INTEGER NOT NULL)')
        for kind, table in [('product', 'products'), ('category', 'categories')]:
            next_id = con.execute('SELECT COALESCE(MAX(id),0)+1 FROM ' + table).fetchone()[0]
            con.execute('INSERT INTO catalog_ids VALUES(?,?) ON CONFLICT(kind) DO UPDATE SET next_id=MAX(next_id,excluded.next_id)',
                        (kind, next_id))
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def allocate_id(con, kind):
    value = con.execute('SELECT next_id FROM catalog_ids WHERE kind=?', (kind,)).fetchone()[0]
    con.execute('UPDATE catalog_ids SET next_id=next_id+1 WHERE kind=?', (kind,))
    return value


def final_cents(price_cents, discount):
    return int((Decimal(price_cents) * (1 - Decimal(str(discount)) / 100)).quantize(
        Decimal('1'), rounding=ROUND_HALF_UP))


def shop_product(row):
    attrs = json.loads(row['attributes'])
    cents = final_cents(row['price_cents'], row['discount_percentage'])
    image = '/media/' + row['image_filename'] if row['image_filename'] else row['external_image']
    slug = row['slug'] or 'category-' + str(row['category_id'])
    colors = {'liquid': '#ff18e8', 'pod': '#8b2cff', 'disposable': '#19e7ff'}
    return {'id': row['id'], 'cat': slug, 'category_name': row['category_name'],
            'name': row['name'], 'brand': row['brand'], 'spec': row['spec'],
            'description': row['description'], 'attributes': attrs,
            'attribute_schema': json.loads(row['attribute_schema']),
            'price_cents': cents, 'price': cents / 100,
            'original_price': f"{Decimal(row['price_cents']) / 100:.2f}",
            'discount_percentage': f"{Decimal(str(row['discount_percentage'])):.2f}",
            'final_price': f'{Decimal(cents) / 100:.2f}',
            'image': image, 'color': colors.get(slug, '#b026ff'),
            'vol': attrs.get('volume', '') or '—', 'mg': attrs.get('strength', '') or '—'}


def products(con):
    rows = con.execute('''SELECT p.*, c.slug, c.name AS category_name, c.attribute_schema
                          FROM products p JOIN categories c ON c.id=p.category_id ORDER BY p.id''')
    return {r['id']: shop_product(r) for r in rows}


def public_catalog(con):
    categories = [{'id': r['slug'] or 'category-' + str(r['id']), 'name': r['name'],
                   'desc': 'Переглянути товари', 'icon': r['icon'] or CATEGORY_ICONS.get(r['slug'], '🧩')} for r in con.execute('SELECT * FROM categories ORDER BY id')]
    return {'categories': categories, 'products': list(products(con).values())}
