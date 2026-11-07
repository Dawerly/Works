#!/usr/bin/env python3
"""Dymok: сайт + база даних + адмін-панель. Python 3.9+, Flask та Pillow (requirements.txt).

Запуск:   python3 server.py        (у Windows: py server.py)
Сайт:     http://localhost:8000/
Адмінка:  http://localhost:8000/admin/

Дані (залишки, замовлення, хеш пароля) лежать у файлі data/dymok.db — робіть його копії.
"""
import getpass
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DB_PATH = Path(os.environ.get('DYMOK_DB', DATA / 'dymok.db'))

HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '8000'))
TRUST_PROXY = os.environ.get('TRUST_PROXY') == '1'
ORDER_LIMIT = int(os.environ.get('ORDER_LIMIT', '15'))   # замовлень з однієї адреси за 10 хвилин

PBKDF2_ITERS = 310_000
SESSION_TTL = 8 * 3600
MAX_BODY = 64 * 1024
MAX_QTY = 100_000
STATUSES = ('new', 'confirmed', 'delivering', 'done', 'cancelled')
# доступні для публічної статики лише ці місця
PUBLIC_FILES = {'index.html', 'logo.png'}
PUBLIC_DIRS = {'assets', 'images', 'admin'}
MIME = {
    '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8', '.svg': 'image/svg+xml',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.webp': 'image/webp', '.ico': 'image/x-icon', '.json': 'application/json; charset=utf-8',
}


# ───────────────────────── база даних ─────────────────────────
def db():
    con = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = db()
    con.execute('PRAGMA journal_mode=WAL')
    con.executescript('''
    CREATE TABLE IF NOT EXISTS admin(
        id INTEGER PRIMARY KEY CHECK (id = 1),
        username TEXT NOT NULL, salt BLOB NOT NULL, hash BLOB NOT NULL, iters INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS sessions(
        token_hash TEXT PRIMARY KEY, expires INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS stock(
        product_id INTEGER PRIMARY KEY, qty INTEGER CHECK (qty IS NULL OR qty >= 0), updated INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT, created INTEGER NOT NULL,
        name TEXT NOT NULL, phone TEXT NOT NULL, phone_digits TEXT NOT NULL, tg TEXT,
        address TEXT NOT NULL, wish_time TEXT, pay TEXT, note TEXT,
        items_json TEXT NOT NULL, total INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'new', delivery_time TEXT, manager_note TEXT,
        restocked INTEGER NOT NULL DEFAULT 0);
    ''')
    con.close()


def hash_pw(password, salt, iters=PBKDF2_ITERS):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iters)


def set_admin(username, password):
    salt = secrets.token_bytes(16)
    con = db()
    con.execute('INSERT OR REPLACE INTO admin(id,username,salt,hash,iters) VALUES(1,?,?,?,?)',
                (username, salt, hash_pw(password, salt), PBKDF2_ITERS))
    con.execute('DELETE FROM sessions')
    con.close()


def ensure_admin():
    con = db()
    row = con.execute('SELECT 1 FROM admin').fetchone()
    con.close()
    if row:
        return
    user, pw = os.environ.get('ADMIN_USER'), os.environ.get('ADMIN_PASS')
    if not (user and pw):
        if not sys.stdin.isatty():
            sys.exit('Адміністратора ще не створено. Запустіть сервер у терміналі або задайте ADMIN_USER та ADMIN_PASS.')
        print('Перший запуск: створіть логін і пароль для адмін-панелі.')
        user, pw = prompt_credentials()
    validate_credentials(user, pw)
    set_admin(user, pw)
    print('Адміністратора створено.')


CONFIG_PATH = ROOT / 'config.json'


def apply_config():
    """Логін і пароль адміна можна вписати у config.json: сервер застосує їх при запуску
    й одразу витре пароль із файлу (у базі лишається тільки хеш). Файл не віддається в інтернет."""
    if not CONFIG_PATH.is_file():
        return
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    except ValueError:
        sys.exit('config.json пошкоджений: перевірте лапки та коми.')
    user, pw = str(cfg.get('admin_username', '')).strip(), str(cfg.get('admin_password', ''))
    if not pw:
        return
    if not user:
        con = db()
        row = con.execute('SELECT username FROM admin').fetchone()
        con.close()
        user = row['username'] if row else ''
    validate_credentials(user, pw)
    set_admin(user, pw)
    cfg['admin_username'], cfg['admin_password'] = user, ''
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Логін і пароль з config.json застосовано (логін: {user}). Пароль із файлу видалено.')
    except OSError:
        print(f'Логін і пароль з config.json застосовано (логін: {user}). Видаліть пароль із файлу вручну.')


def validate_credentials(user, pw):
    if not re.fullmatch(r'[A-Za-z0-9_.-]{3,32}', user or ''):
        sys.exit('Логін: 3–32 символи, лише латиниця, цифри та _ . -')
    if len(pw or '') < 10:
        sys.exit('Пароль має містити щонайменше 10 символів.')


def prompt_credentials():
    user = input('Логін (латиницею): ').strip()
    pw = getpass.getpass('Пароль (мінімум 10 символів): ')
    if pw != getpass.getpass('Повторіть пароль: '):
        sys.exit('Паролі не збігаються.')
    return user, pw


# ───────────────────────── товари (спільний каталог SQLite) ─────────────────────────
def products(con=None):
    """Read the live catalogue; the caller can share its order transaction."""
    from catalog_store import products as catalog_products
    own = con is None
    con = con or db()
    try:
        return catalog_products(con)
    finally:
        if own:
            con.close()


def stock_map(con):
    return {r['product_id']: r['qty'] for r in con.execute('SELECT product_id, qty FROM stock')}


# ───────────────────────── обмеження частоти запитів ─────────────────────────
_hits = {}
_hits_lock = threading.Lock()


def too_many(key, limit, window):
    now = time.time()
    with _hits_lock:
        arr = [t for t in _hits.get(key, []) if now - t < window]
        if len(arr) >= limit:
            _hits[key] = arr
            return True
        arr.append(now)
        _hits[key] = arr
        return False


def failed_login_count(ip):
    now = time.time()
    with _hits_lock:
        return len([t for t in _hits.get('fail:' + ip, []) if now - t < 900])


def note_failed_login(ip):
    with _hits_lock:
        _hits.setdefault('fail:' + ip, []).append(time.time())


def clear_failed_login(ip):
    with _hits_lock:
        _hits.pop('fail:' + ip, None)


# ───────────────────────── допоміжні ─────────────────────────
class ApiError(Exception):
    def __init__(self, code, message, **extra):
        self.code, self.message, self.extra = code, message, extra


def clean(v, maxlen):
    return re.sub(r'\s+', ' ', str(v or '')).strip()[:maxlen]


def to_int(v, lo, hi, what):
    if isinstance(v, bool) or not isinstance(v, (int, str)) or (isinstance(v, str) and not re.fullmatch(r'-?\d{1,9}', v.strip())):
        raise ApiError(400, f'Некоректне значення: {what}')
    n = int(v)
    if not lo <= n <= hi:
        raise ApiError(400, f'Некоректне значення: {what}')
    return n


def order_public(r):
    return {'id': r['id'], 'status': r['status'], 'delivery_time': r['delivery_time'] or '',
            'manager_note': r['manager_note'] or ''}


def order_admin(r):
    d = dict(r)
    d['items'] = json.loads(d.pop('items_json'))
    d.pop('phone_digits', None)
    return d


# ───────────────────────── API ─────────────────────────
def create_order(body, ip):
    if too_many('order:' + ip, ORDER_LIMIT, 600):
        raise ApiError(429, 'Забагато замовлень з цієї адреси. Спробуйте за кілька хвилин.')
    name, phone = clean(body.get('name'), 80), clean(body.get('phone'), 30)
    digits = re.sub(r'\D', '', phone)
    street, house = clean(body.get('street'), 100), clean(body.get('house'), 20)
    if not name or not street or not house or not 10 <= len(digits) <= 15:
        raise ApiError(400, 'Заповніть імʼя, телефон, вулицю та будинок.')
    address = f'м. Рівне, {street}, буд. {house}'
    for key, label in (('flat', 'кв./офіс'), ('entr', "під'їзд"), ('floor', 'поверх/домофон')):
        val = clean(body.get(key), 30)
        if val:
            address += f', {label} {val}'
    tg = clean(body.get('tg'), 64)
    wish, pay, note = clean(body.get('wishTime'), 60), clean(body.get('pay'), 60), clean(body.get('note'), 500)

    raw = body.get('items')
    if not isinstance(raw, list) or not 1 <= len(raw) <= 40:
        raise ApiError(400, 'Кошик порожній.')
    need = {}
    for it in raw:
        if not isinstance(it, dict):
            raise ApiError(400, 'Некоректний кошик.')
        pid, qty = to_int(it.get('id'), 1, 10**9, 'товар'), to_int(it.get('qty'), 1, 99, 'кількість')
        need[pid] = need.get(pid, 0) + qty
    con = db()
    try:
        con.execute('BEGIN IMMEDIATE')           # блокує інші замовлення, поки рахуємо залишки
        prods = products(con)
        if any(pid not in prods for pid in need):
            raise ApiError(400, 'Один із товарів більше не продається. Оновіть сторінку.')
        stock = stock_map(con)
        short = [{'id': pid, 'available': stock[pid]} for pid, q in need.items()
                 if stock.get(pid) is not None and stock[pid] < q]
        if short:
            con.execute('ROLLBACK')
            raise ApiError(409, 'Не всі товари є в потрібній кількості.', items=short)
        now = int(time.time())
        for pid, q in need.items():
            if stock.get(pid) is not None:
                con.execute('UPDATE stock SET qty = qty - ?, updated = ? WHERE product_id = ?', (q, now, pid))
        items = [{'id': pid, 'name': prods[pid]['name'], 'spec': prods[pid]['spec'],
                  'price': prods[pid]['price'], 'price_cents': prods[pid]['price_cents'], 'qty': q} for pid, q in need.items()]
        total_cents = sum(i['price_cents'] * i['qty'] for i in items)
        total = total_cents / 100
        cur = con.execute(
            'INSERT INTO orders(created,name,phone,phone_digits,tg,address,wish_time,pay,note,items_json,total,total_cents)'
            ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (now, name, phone, digits, tg, address, wish, pay, note, json.dumps(items, ensure_ascii=False), total, total_cents))
        oid = cur.lastrowid
        con.execute('COMMIT')
        left = stock_map(con)
        return {'id': oid, 'total': total, 'total_cents': total_cents, 'address': address, 'items': items,
                'stock': {str(pid): left.get(pid) for pid in need}}
    except ApiError:
        raise
    except Exception:
        try:
            con.execute('ROLLBACK')
        except sqlite3.Error:
            pass
        raise
    finally:
        con.close()


def order_status(query, ip):
    if too_many('status:' + ip, 30, 600):
        raise ApiError(429, 'Забагато запитів.')
    try:
        oid = int(query.get('id', [''])[0])
    except ValueError:
        raise ApiError(400, 'Некоректний номер.')
    digits = re.sub(r'\D', '', query.get('phone', [''])[0])
    con = db()
    row = con.execute('SELECT * FROM orders WHERE id = ?', (oid,)).fetchone()
    con.close()
    if not row or not digits or not hmac.compare_digest(row['phone_digits'], digits):
        raise ApiError(404, 'Замовлення не знайдено.')
    return order_public(row)


def restock(con, row):
    """Повертає товари зі скасованого замовлення на склад (лише для тих, що обліковуються)."""
    now = int(time.time())
    for it in json.loads(row['items_json']):
        con.execute('UPDATE stock SET qty = qty + ?, updated = ? WHERE product_id = ? AND qty IS NOT NULL',
                    (it['qty'], now, it['id']))
    con.execute('UPDATE orders SET restocked = 1 WHERE id = ?', (row['id'],))


def admin_products():
    con = db()
    stock = stock_map(con)
    con.close()
    return [dict(p, qty=stock.get(pid)) for pid, p in sorted(products().items())]


def admin_set_stock(body):
    prods = products()
    rows = body.get('items') if isinstance(body.get('items'), list) else [body]
    if not 1 <= len(rows) <= 1000:
        raise ApiError(400, 'Некоректний запит.')
    parsed = []
    for r in rows:
        if not isinstance(r, dict):
            raise ApiError(400, 'Некоректний запит.')
        pid = to_int(r.get('id'), 1, 10**9, 'товар')
        if pid not in prods:
            raise ApiError(404, 'Товару не існує.')
        if r.get('qty') is None and 'delta' not in r:
            parsed.append((pid, None, None))          # «не обліковувати»
        elif 'delta' in r:
            parsed.append((pid, None, to_int(r['delta'], -MAX_QTY, MAX_QTY, 'зміна')))
        else:
            parsed.append((pid, to_int(r['qty'], 0, MAX_QTY, 'кількість'), None))
    now = int(time.time())
    con = db()
    try:
        con.execute('BEGIN IMMEDIATE')
        out = {}
        for pid, qty, delta in parsed:
            if delta is not None:
                cur = con.execute('SELECT qty FROM stock WHERE product_id = ?', (pid,)).fetchone()
                base = cur['qty'] if cur and cur['qty'] is not None else 0
                qty = max(0, min(MAX_QTY, base + delta))
            con.execute('INSERT INTO stock(product_id,qty,updated) VALUES(?,?,?) '
                        'ON CONFLICT(product_id) DO UPDATE SET qty = excluded.qty, updated = excluded.updated',
                        (pid, qty, now))
            out[str(pid)] = qty
        con.execute('COMMIT')
        return {'stock': out}
    except Exception:
        try:
            con.execute('ROLLBACK')
        except sqlite3.Error:
            pass
        raise
    finally:
        con.close()


def admin_orders(query):
    status = query.get('status', [''])[0]
    con = db()
    if status in STATUSES:
        rows = con.execute('SELECT * FROM orders WHERE status = ? ORDER BY id DESC LIMIT 500', (status,)).fetchall()
    elif status == 'all':
        rows = con.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 500').fetchall()
    else:       # за замовчуванням лише активні: доставлені й скасовані вже не показуємо
        rows = con.execute("SELECT * FROM orders WHERE status NOT IN ('done','cancelled') ORDER BY id DESC LIMIT 500").fetchall()
    con.close()
    return {'orders': [order_admin(r) for r in rows]}


def admin_delete_order(body):
    oid = to_int(body.get('id'), 1, 10**9, 'замовлення')
    con = db()
    try:
        con.execute('BEGIN IMMEDIATE')
        row = con.execute('SELECT status FROM orders WHERE id = ?', (oid,)).fetchone()
        if not row:
            raise ApiError(404, 'Замовлення не знайдено.')
        if row['status'] not in ('done', 'cancelled'):
            raise ApiError(409, 'Видаляти можна лише доставлені або скасовані замовлення.')
        con.execute('DELETE FROM orders WHERE id = ?', (oid,))
        con.execute('COMMIT')
    except Exception:
        try:
            con.execute('ROLLBACK')
        except sqlite3.Error:
            pass
        raise
    finally:
        con.close()
    return {'ok': True}


def admin_update_order(body):
    oid = to_int(body.get('id'), 1, 10**9, 'замовлення')
    con = db()
    try:
        con.execute('BEGIN IMMEDIATE')
        row = con.execute('SELECT * FROM orders WHERE id = ?', (oid,)).fetchone()
        if not row:
            raise ApiError(404, 'Замовлення не знайдено.')
        status = body.get('status', row['status'])
        if status not in STATUSES:
            raise ApiError(400, 'Невідомий статус.')
        if row['status'] == 'cancelled' and status != 'cancelled':
            raise ApiError(409, 'Скасоване замовлення відновити не можна — оформіть нове.')
        dt = clean(body['delivery_time'], 120) if 'delivery_time' in body else row['delivery_time']
        mn = clean(body['manager_note'], 500) if 'manager_note' in body else row['manager_note']
        con.execute('UPDATE orders SET status = ?, delivery_time = ?, manager_note = ? WHERE id = ?',
                    (status, dt, mn, oid))
        if status == 'cancelled' and not row['restocked']:
            restock(con, row)
        con.execute('COMMIT')
    except Exception:
        try:
            con.execute('ROLLBACK')
        except sqlite3.Error:
            pass
        raise
    finally:
        con.close()
    con = db()
    row = con.execute('SELECT * FROM orders WHERE id = ?', (oid,)).fetchone()
    stock = stock_map(con)
    con.close()
    return {'order': order_admin(row), 'stock': {str(i['id']): stock.get(i['id']) for i in json.loads(row['items_json'])}}


# ───────────────────────── HTTP ─────────────────────────
class Handler(BaseHTTPRequestHandler):
    server_version = 'Dymok'
    sys_version = ''
    protocol_version = 'HTTP/1.1'

    # --- службові
    def log_message(self, fmt, *args):
        sys.stderr.write('%s %s\n' % (self.log_date_time_string(), fmt % args))

    def client_ip(self):
        if TRUST_PROXY:
            xff = self.headers.get('X-Forwarded-For', '')
            if xff:
                return xff.split(',')[-1].strip()
        return self.client_address[0]

    def is_https(self):
        return TRUST_PROXY and self.headers.get('X-Forwarded-Proto', '').lower() == 'https'

    def send_security_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('X-Frame-Options', 'DENY')

    def send_json(self, code, obj, headers=None):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_security_headers()
        for k, v in (headers or []):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        if 'application/json' not in self.headers.get('Content-Type', ''):
            raise ApiError(415, 'Очікується JSON.')
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise ApiError(400, 'Некоректний запит.')
        if length > MAX_BODY:
            raise ApiError(413, 'Запит завеликий.')
        try:
            body = json.loads(self.rfile.read(length) or b'{}')
        except ValueError:
            raise ApiError(400, 'Некоректний JSON.')
        if not isinstance(body, dict):
            raise ApiError(400, 'Некоректний запит.')
        return body

    # --- авторизація
    def session_token(self):
        for part in self.headers.get('Cookie', '').split(';'):
            k, _, v = part.strip().partition('=')
            if k == 'dymok_admin':
                return v
        return ''

    def is_admin(self):
        tok = self.session_token()
        if not tok:
            return False
        h = hashlib.sha256(tok.encode()).hexdigest()
        con = db()
        row = con.execute('SELECT expires FROM sessions WHERE token_hash = ?', (h,)).fetchone()
        if row and row['expires'] < time.time():
            con.execute('DELETE FROM sessions WHERE token_hash = ?', (h,))
            row = None
        con.close()
        return bool(row)

    def cookie(self, value, max_age):
        c = f'dymok_admin={value}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age}'
        return ('Set-Cookie', c + ('; Secure' if self.is_https() or os.environ.get('COOKIE_SECURE') == '1' else ''))

    def login(self, body):
        ip = self.client_ip()
        if failed_login_count(ip) >= 5:
            raise ApiError(429, 'Забагато невдалих спроб. Спробуйте через 15 хвилин.')
        user, pw = str(body.get('username', ''))[:64], str(body.get('password', ''))[:256]
        con = db()
        row = con.execute('SELECT * FROM admin WHERE id = 1').fetchone()
        salt = row['salt'] if row else b'\0' * 16
        calc = hash_pw(pw, salt, row['iters'] if row else PBKDF2_ITERS)     # час однаковий і для хибного логіна
        ok = bool(row) and hmac.compare_digest(calc, row['hash']) and hmac.compare_digest(user.encode(), row['username'].encode())
        if not ok:
            con.close()
            note_failed_login(ip)
            time.sleep(0.6)
            raise ApiError(401, 'Невірний логін або пароль.')
        clear_failed_login(ip)
        tok = secrets.token_urlsafe(32)
        con.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
        con.execute('INSERT INTO sessions(token_hash, expires) VALUES(?,?)',
                    (hashlib.sha256(tok.encode()).hexdigest(), int(time.time()) + SESSION_TTL))
        con.close()
        return tok

    def change_password(self, body):
        cur, new = str(body.get('current', ''))[:256], str(body.get('new', ''))[:256]
        if len(new) < 10:
            raise ApiError(400, 'Новий пароль має містити щонайменше 10 символів.')
        con = db()
        row = con.execute('SELECT * FROM admin WHERE id = 1').fetchone()
        con.close()
        if not hmac.compare_digest(hash_pw(cur, row['salt'], row['iters']), row['hash']):
            raise ApiError(403, 'Поточний пароль невірний.')
        set_admin(row['username'], new)          # скидає всі сесії
        tok = secrets.token_urlsafe(32)
        con = db()
        con.execute('INSERT INTO sessions(token_hash, expires) VALUES(?,?)',
                    (hashlib.sha256(tok.encode()).hexdigest(), int(time.time()) + SESSION_TTL))
        con.close()
        return tok

    # --- маршрути
    def do_GET(self):
        self.route('GET')

    def do_HEAD(self):
        self.route('GET', head=True)

    def do_POST(self):
        self.route('POST')

    def route(self, method, head=False):
        try:
            url = urlparse(self.path)
            path, query = url.path, parse_qs(url.query)
            if path.startswith('/api/'):
                return self.api(method, path, query)
            if method != 'GET':
                raise ApiError(405, 'Метод не підтримується.')
            return self.static(path, head)
        except ApiError as e:
            self.send_json(e.code, dict({'error': e.message}, **e.extra))
        except BrokenPipeError:
            pass
        except Exception as e:                               # не віддаємо подробиці назовні
            sys.stderr.write(f'ПОМИЛКА: {e!r}\n')
            try:
                self.send_json(500, {'error': 'Внутрішня помилка сервера.'})
            except Exception:
                pass

    def api(self, method, path, query):
        ip = self.client_ip()
        if method == 'GET':
            if path == '/api/stock':
                con = db()
                stock = stock_map(con)
                con.close()
                return self.send_json(200, {'stock': {str(k): v for k, v in stock.items()}})
            if path == '/api/order-status':
                return self.send_json(200, order_status(query, ip))
        if path.startswith('/api/admin/'):
            return self.admin_api(method, path, query)
        if method == 'POST' and path == '/api/order':
            self.need_xhr()
            return self.send_json(201, create_order(self.read_json(), ip))
        raise ApiError(404, 'Не знайдено.')

    def need_xhr(self):
        # власний заголовок не можна додати з чужого сайту без дозволу CORS → захист від CSRF
        if self.headers.get('X-Requested-With') != 'dymok':
            raise ApiError(403, 'Заборонено.')

    def admin_api(self, method, path, query):
        if method == 'POST':
            self.need_xhr()
        if path == '/api/admin/login' and method == 'POST':
            tok = self.login(self.read_json())
            return self.send_json(200, {'ok': True}, [self.cookie(tok, SESSION_TTL)])
        if not self.is_admin():
            raise ApiError(401, 'Потрібен вхід.')
        if method == 'GET':
            if path == '/api/admin/me':
                return self.send_json(200, {'ok': True})
            if path == '/api/admin/products':
                return self.send_json(200, {'products': admin_products()})
            if path == '/api/admin/orders':
                return self.send_json(200, admin_orders(query))
        elif method == 'POST':
            if path == '/api/admin/logout':
                con = db()
                con.execute('DELETE FROM sessions WHERE token_hash = ?',
                            (hashlib.sha256(self.session_token().encode()).hexdigest(),))
                con.close()
                return self.send_json(200, {'ok': True}, [self.cookie('', 0)])
            if path == '/api/admin/stock':
                return self.send_json(200, admin_set_stock(self.read_json()))
            if path == '/api/admin/order':
                return self.send_json(200, admin_update_order(self.read_json()))
            if path == '/api/admin/order-delete':
                return self.send_json(200, admin_delete_order(self.read_json()))
            if path == '/api/admin/password':
                tok = self.change_password(self.read_json())
                return self.send_json(200, {'ok': True}, [self.cookie(tok, SESSION_TTL)])
        raise ApiError(404, 'Не знайдено.')

    def static(self, path, head):
        if path == '/admin':
            self.send_response(301)
            self.send_header('Location', '/admin/')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        rel = path.lstrip('/') or 'index.html'
        if rel.endswith('/'):
            rel += 'index.html'
        parts = Path(rel).parts
        allowed = rel in PUBLIC_FILES or (len(parts) > 1 and parts[0] in PUBLIC_DIRS)
        file = (ROOT / rel).resolve()
        if not allowed or ROOT not in file.parents or not file.is_file() or any(p.startswith('.') for p in parts):
            raise ApiError(404, 'Не знайдено.')
        data = file.read_bytes()
        if rel == 'index.html':
            data = data.replace(b'assets/js/01-products.js', b'/api/catalog.js')
        self.send_response(200)
        self.send_header('Content-Type', MIME.get(file.suffix.lower(), 'application/octet-stream'))
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-cache')
        self.send_security_headers()
        if parts[0] == 'admin':
            self.send_header('Content-Security-Policy',
                             "default-src 'self'; img-src 'self' https: data:; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        if not head:
            self.wfile.write(data)


def main():
    if '--set-password' in sys.argv:           # відновлення доступу: лише з доступом до сервера
        init_db()
        user, pw = prompt_credentials()
        validate_credentials(user, pw)
        set_admin(user, pw)
        print('Логін і пароль змінено, усі сесії завершено.')
        return
    init_db()
    apply_config()
    ensure_admin()
    from catalog import create_app
    from werkzeug.serving import run_simple
    application = create_app()
    products()
    ThreadingHTTPServer.request_queue_size = 128
    ThreadingHTTPServer.daemon_threads = True
    print(f'Dymok працює: http://{"localhost" if HOST in ("127.0.0.1", "0.0.0.0") else HOST}:{PORT}/   '
          f'Адмінка: /admin/   (Ctrl+C — зупинити)')
    try:
        run_simple(HOST, PORT, application, threaded=True)
    except KeyboardInterrupt:
        print('\nЗупинено.')


if __name__ == '__main__':
    sys.modules.setdefault('server', sys.modules[__name__])
    main()
