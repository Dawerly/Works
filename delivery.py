"""Delivery, isolated courier identities and transactional order assignment.

All money is integer kopecks. Existing shop/admin credentials and stock are retained.
"""
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request, send_from_directory, session
import server

bp = Blueprint('delivery', __name__)
STATUSES = ('new', 'confirmed', 'ready', 'assigned', 'delivering', 'problem', 'done', 'cancelled')
ACTIVE = ('assigned', 'delivering', 'problem')
TRANSITIONS = {
    'new': {'new', 'confirmed', 'cancelled'},
    'confirmed': {'confirmed', 'ready', 'cancelled'},
    'ready': {'ready', 'confirmed', 'cancelled'},
    'assigned': {'assigned', 'delivering', 'problem', 'cancelled'},
    'delivering': {'delivering', 'done', 'problem', 'cancelled'},
    'problem': {'problem', 'assigned', 'delivering', 'cancelled'},
    'done': {'done'}, 'cancelled': {'cancelled'},
}
CASH = 'Готівкою при отриманні'
CARD = 'Переказом на картку'
DEFAULTS = {'accepting': True, 'hours_enabled': False, 'opens': '09:00', 'closes': '20:00',
            'closed_days': [], 'timezone': 'Europe/Kyiv'}


def initialize(database):
    """Idempotent migration, with a SQLite snapshot before the first delivery change."""
    con = sqlite3.connect(database, timeout=30)
    try:
        migrated = con.execute("SELECT 1 FROM sqlite_master WHERE name='delivery_migrations'").fetchone()
        if not migrated:
            backup = Path(database).with_name(Path(database).stem + '-before-delivery.sqlite3')
            if not backup.exists():
                dest = sqlite3.connect(backup)
                try:
                    con.backup(dest)
                finally:
                    dest.close()
        con.execute('BEGIN IMMEDIATE')
        # Execute individually: executescript would commit the migration prematurely.
        statements = [
            '''CREATE TABLE IF NOT EXISTS couriers(
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                name TEXT NOT NULL, phone TEXT NOT NULL, salt BLOB NOT NULL, hash BLOB NOT NULL,
                iters INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1,
                on_shift INTEGER NOT NULL DEFAULT 0, must_change INTEGER NOT NULL DEFAULT 1,
                max_active INTEGER NOT NULL DEFAULT 3 CHECK(max_active BETWEEN 1 AND 50),
                created INTEGER NOT NULL)''',
            '''CREATE TABLE IF NOT EXISTS courier_sessions(
                token_hash TEXT PRIMARY KEY, courier_id INTEGER NOT NULL REFERENCES couriers(id),
                expires INTEGER NOT NULL)''',
            '''CREATE TABLE IF NOT EXISTS delivery_zones(
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
                fee_cents INTEGER NOT NULL, minimum_cents INTEGER NOT NULL,
                free_from_cents INTEGER, reward_cents INTEGER NOT NULL DEFAULT 0)''',
            '''CREATE TABLE IF NOT EXISTS delivery_settings(id INTEGER PRIMARY KEY CHECK(id=1),
                value TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1)''',
            '''CREATE TABLE IF NOT EXISTS delivery_events(id INTEGER PRIMARY KEY AUTOINCREMENT,
                created INTEGER NOT NULL, actor TEXT NOT NULL, actor_id INTEGER,
                order_id INTEGER, action TEXT NOT NULL, details TEXT NOT NULL)''',
            '''CREATE TABLE IF NOT EXISTS courier_cash(id INTEGER PRIMARY KEY AUTOINCREMENT,
                created INTEGER NOT NULL, courier_id INTEGER NOT NULL REFERENCES couriers(id),
                order_id INTEGER UNIQUE, amount_cents INTEGER NOT NULL, kind TEXT NOT NULL,
                reference TEXT UNIQUE, note TEXT NOT NULL DEFAULT '')''',
            'CREATE TABLE IF NOT EXISTS delivery_migrations(name TEXT PRIMARY KEY)',
        ]
        for statement in statements:
            con.execute(statement)
        columns = {r[1] for r in con.execute('PRAGMA table_info(orders)')}
        additions = {
            'courier_id': 'INTEGER REFERENCES couriers(id)', 'zone_id': 'INTEGER',
            'zone_name': "TEXT NOT NULL DEFAULT 'Рівне'", 'delivery_fee_cents': 'INTEGER NOT NULL DEFAULT 0',
            'reward_cents': 'INTEGER NOT NULL DEFAULT 0', 'subtotal_cents': 'INTEGER NOT NULL DEFAULT 0',
            'tracking_token': 'TEXT', 'request_key': 'TEXT', 'request_hash': 'TEXT',
            'version': 'INTEGER NOT NULL DEFAULT 1', 'assigned_at': 'INTEGER', 'completed_at': 'INTEGER',
            'courier_note': "TEXT NOT NULL DEFAULT ''", 'release_requested': 'INTEGER NOT NULL DEFAULT 0',
            'archived': 'INTEGER NOT NULL DEFAULT 0',
        }
        for name, definition in additions.items():
            if name not in columns:
                con.execute('ALTER TABLE orders ADD COLUMN ' + name + ' ' + definition)
        if not con.execute("SELECT 1 FROM delivery_migrations WHERE name='delivery-v1'").fetchone():
            con.execute('UPDATE orders SET subtotal_cents=total_cents')
            con.execute('INSERT INTO delivery_zones(name,fee_cents,minimum_cents,reward_cents) VALUES(?,?,?,?)',
                        ('Рівне', 0, 0, 0))
            con.execute('INSERT INTO delivery_settings(id,value) VALUES(1,?)', (json.dumps(DEFAULTS),))
            con.execute("INSERT INTO delivery_migrations VALUES('delivery-v1')")
        for statement in [
            'CREATE UNIQUE INDEX IF NOT EXISTS order_request_key ON orders(request_key)',
            'CREATE INDEX IF NOT EXISTS order_courier_status ON orders(courier_id,status)',
            'CREATE INDEX IF NOT EXISTS delivery_events_order ON delivery_events(order_id,id)',
            'CREATE INDEX IF NOT EXISTS courier_sessions_owner ON courier_sessions(courier_id)',
        ]:
            con.execute(statement)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@contextmanager
def connection(write=False):
    con = server.db()
    try:
        if write:
            con.execute('BEGIN IMMEDIATE')
        yield con
        if write:
            con.commit()
    except Exception:
        if write:
            con.rollback()
        raise
    finally:
        con.close()


def fail(message, code=400):
    raise server.ApiError(code, message)


def body():
    if request.content_length and request.content_length > server.MAX_BODY:
        fail('Запит завеликий.', 413)
    data = request.get_json()
    if not isinstance(data, dict):
        fail('Очікується JSON-об’єкт.')
    return data


def text(value, label, limit=100, required=True):
    if not isinstance(value, str) or len(value.strip()) > limit or (required and not value.strip()):
        fail(f'{label}: заповніть поле (до {limit} символів).')
    return value.strip()


def integer(value, lo, hi, label):
    return server.to_int(value, lo, hi, label)


def boolean(value, label):
    if not isinstance(value, bool):
        fail(f'{label}: очікується так/ні.')
    return int(value)


def money(value, label):
    try:
        raw = str(value)
        if not re.fullmatch(r'\d{1,8}(\.\d{1,2})?', raw):
            raise ValueError()
        return int(Decimal(raw) * 100)
    except (ValueError, InvalidOperation):
        fail(f'{label}: вкажіть невід’ємну суму з максимум двома знаками після крапки.')


def ip():
    from legacy_wsgi import WSGIHandler
    return WSGIHandler(request.environ).client_ip()


def admin():
    from legacy_wsgi import WSGIHandler
    if not WSGIHandler(request.environ).is_admin():
        fail('Потрібен вхід адміністратора.', 401)


def courier(con, allow_change=False):
    token = request.cookies.get('dymok_courier', '')
    row = con.execute('''SELECT c.* FROM couriers c JOIN courier_sessions s ON c.id=s.courier_id
        WHERE s.token_hash=? AND s.expires>? AND c.active=1''',
                      (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
    if not row:
        fail('Увійдіть у кабінет кур’єра.', 401)
    if row['must_change'] and not allow_change:
        fail('Спочатку змініть тимчасовий пароль.', 403)
    if not row['tg'] and not allow_change:
        fail('Спочатку додайте свій Telegram у профілі кур’єра.', 403)
    return row


def courier_dict(row):
    return {k: row[k] for k in ('id', 'username', 'name', 'phone', 'active', 'on_shift', 'must_change', 'max_active', 'tg')}


def audit(con, actor, action, order_id=None, actor_id=None, **details):
    con.execute('INSERT INTO delivery_events(created,actor,actor_id,order_id,action,details) VALUES(?,?,?,?,?,?)',
                (int(time.time()), actor, actor_id, order_id, action, json.dumps(details, ensure_ascii=False)))


def order_row(con, oid):
    row = con.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
    if not row:
        fail('Замовлення не знайдено.', 404)
    return row


def check_version(row, data):
    if 'version' in data and data['version'] != row['version']:
        fail('Замовлення вже змінилося. Оновіть список.', 409)


def order_dict(con, row):
    result = server.order_admin(row)
    result.pop('request_key', None)
    result.pop('request_hash', None)
    result.pop('tracking_token', None)
    c = con.execute('SELECT name FROM couriers WHERE id=?', (row['courier_id'],)).fetchone()
    result['courier_name'] = c['name'] if c else ''
    return result


def short_order(row):
    return {k: row[k] for k in ('id', 'created', 'status', 'zone_name', 'wish_time', 'delivery_time',
                                'total_cents', 'delivery_fee_cents', 'reward_cents', 'pay', 'version', 'completed_at')}


def public_order(row):
    return {k: row[k] for k in ('id', 'status', 'delivery_time', 'manager_note', 'total_cents',
                                'subtotal_cents', 'delivery_fee_cents', 'created')}


def settings(con):
    row = con.execute('SELECT * FROM delivery_settings WHERE id=1').fetchone()
    return dict(json.loads(row['value']), version=row['version'])


def accepting(config, now=None):
    if not config['accepting']:
        return False
    if not config['hours_enabled']:
        return True
    now = now or datetime.now(ZoneInfo('Europe/Kyiv'))
    clock = now.strftime('%H:%M')
    start, end = config['opens'], config['closes']
    if start < end:
        return now.weekday() not in config['closed_days'] and start <= clock < end
    # Overnight hours belong to the day on which the shift started.
    day = now.weekday() if clock >= start else (now.weekday() - 1) % 7
    return day not in config['closed_days'] and (clock >= start or clock < end)


def zone_quote(con, data, subtotal):
    config = settings(con)
    if not accepting(config):
        fail('Зараз приймання замовлень закрите. Перевірте графік доставки.', 409)
    zid = data.get('zone_id')
    if zid is None:
        # Existing clients remain usable with the initial single-zone configuration.
        zones = con.execute('SELECT * FROM delivery_zones WHERE active=1').fetchall()
        if len(zones) != 1:
            fail('Оберіть район доставки.')
        zone = zones[0]
    else:
        zone = con.execute('SELECT * FROM delivery_zones WHERE id=? AND active=1',
                           (integer(zid, 1, 10**9, 'район'),)).fetchone()
    if not zone:
        fail('Район доставки недоступний.')
    if subtotal < zone['minimum_cents']:
        fail(f'Мінімальна сума товарів для цього району — {zone["minimum_cents"] / 100:.2f} грн.', 409)
    free = zone['free_from_cents'] is not None and subtotal >= zone['free_from_cents']
    return zone, 0 if free else zone['fee_cents']


@bp.before_request
def csrf():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        # All authenticated writes require the same-origin header and a CSRF token.
        if request.headers.get('X-Requested-With') != 'dymok':
            fail('Заборонено.', 403)
        supplied = request.headers.get('X-CSRF-Token', '')
        if not hmac.compare_digest(supplied.encode(), session['csrf_token'].encode()):
            fail('Оновіть сторінку та повторіть дію.', 403)


@bp.errorhandler(server.ApiError)
def api_error(error):
    return jsonify(error=error.message, **error.extra), error.code


@bp.get('/api/delivery/session')
def session_info():
    with connection() as con:
        try:
            c = courier_dict(courier(con, True))
        except server.ApiError:
            c = None
    return jsonify(csrf_token=session['csrf_token'], courier=c)


@bp.get('/courier/')
@bp.get('/courier/<filename>')
def courier_page(filename='index.html'):
    if filename not in ('index.html', 'courier.js', 'courier.css'):
        fail('Не знайдено.', 404)
    return send_from_directory(Path(current_app.root_path) / 'courier', filename)


@bp.get('/order/')
@bp.get('/order/<filename>')
def tracking_page(filename='index.html'):
    if filename not in ('index.html', 'order.js', 'order.css'):
        fail('Не знайдено.', 404)
    return send_from_directory(Path(current_app.root_path) / 'order', filename)


@bp.get('/admin/delivery/')
@bp.get('/admin/delivery/<filename>')
def admin_page(filename='index.html'):
    if filename not in ('index.html', 'delivery.js'):
        fail('Не знайдено.', 404)
    return send_from_directory(Path(current_app.root_path) / 'admin' / 'delivery', filename)


def auth_response(con, cid):
    token = secrets.token_urlsafe(32)
    con.execute('DELETE FROM courier_sessions WHERE expires<=?', (int(time.time()),))
    con.execute('INSERT INTO courier_sessions VALUES(?,?,?)',
                (hashlib.sha256(token.encode()).hexdigest(), cid, int(time.time()) + server.SESSION_TTL))
    response = jsonify(courier=courier_dict(con.execute('SELECT * FROM couriers WHERE id=?', (cid,)).fetchone()))
    response.set_cookie('dymok_courier', token, max_age=server.SESSION_TTL, httponly=True, samesite='Strict',
                        secure=current_app.config['SESSION_COOKIE_SECURE'] or request.is_secure)
    return response


@bp.post('/api/courier/login')
def login():
    data = body()
    key = 'courier-login:' + ip()
    if server.too_many(key, 10, 900):
        fail('Забагато спроб входу. Повторіть через 15 хвилин.', 429)
    user = text(data.get('username', ''), 'Логін', 32)
    pw = data.get('password', '')
    if not isinstance(pw, str) or not 1 <= len(pw) <= 256:
        fail('Вкажіть пароль.')
    with connection(True) as con:
        row = con.execute('SELECT * FROM couriers WHERE username=? COLLATE NOCASE', (user,)).fetchone()
        calc = server.hash_pw(pw, row['salt'] if row else bytes(16), row['iters'] if row else server.PBKDF2_ITERS)
        if not row or not row['active'] or not hmac.compare_digest(calc, row['hash']):
            fail('Невірний логін або пароль.', 401)
        audit(con, 'courier', 'login', actor_id=row['id'])
        return auth_response(con, row['id'])


@bp.post('/api/courier/logout')
def logout():
    with connection(True) as con:
        c = courier(con, True)
        con.execute('DELETE FROM courier_sessions WHERE token_hash=?',
                    (hashlib.sha256(request.cookies.get('dymok_courier', '').encode()).hexdigest(),))
        audit(con, 'courier', 'logout', actor_id=c['id'])
    response = jsonify(ok=True)
    response.delete_cookie('dymok_courier', path='/')
    return response


def password(value):
    if not isinstance(value, str) or not 10 <= len(value) <= 256:
        fail('Пароль має містити від 10 до 256 символів.')
    return value


@bp.post('/api/courier/password')
def change_password():
    data = body()
    pw = password(data.get('new'))
    with connection(True) as con:
        c = courier(con, True)
        if server.too_many('courier-password:' + str(c['id']), 8, 900):
            fail('Забагато спроб. Повторіть через 15 хвилин.', 429)
        old = str(data.get('current', ''))[:256]
        if not hmac.compare_digest(server.hash_pw(old, c['salt'], c['iters']), c['hash']):
            fail('Поточний пароль неправильний.', 403)
        if hmac.compare_digest(old, pw):
            fail('Новий пароль має відрізнятися від тимчасового.')
        salt = secrets.token_bytes(16)
        con.execute('UPDATE couriers SET salt=?,hash=?,iters=?,must_change=0 WHERE id=?',
                    (salt, server.hash_pw(pw, salt), server.PBKDF2_ITERS, c['id']))
        con.execute('DELETE FROM courier_sessions WHERE courier_id=?', (c['id'],))
        audit(con, 'courier', 'password_changed', actor_id=c['id'])
        return auth_response(con, c['id'])


@bp.post('/api/courier/shift')
def shift():
    data = body()
    with connection(True) as con:
        c = courier(con)
        value = boolean(data.get('on_shift'), 'Зміна')
        con.execute('UPDATE couriers SET on_shift=? WHERE id=?', (value, c['id']))
        audit(con, 'courier', 'shift_changed', actor_id=c['id'], on_shift=value)
    return jsonify(ok=True)


@bp.get('/api/courier/orders')
def courier_orders():
    view = request.args.get('view', 'available')
    if view not in ('available', 'mine', 'history'):
        fail('Невідомий список.')
    with connection() as con:
        c = courier(con)
        if view == 'available':
            rows = con.execute("SELECT * FROM orders WHERE status='ready' AND courier_id IS NULL AND archived=0 ORDER BY id LIMIT 200").fetchall() if c['on_shift'] else []
            data = [short_order(row) for row in rows]
        elif view == 'mine':
            rows = con.execute("SELECT * FROM orders WHERE courier_id=? AND status IN ('assigned','delivering','problem') AND archived=0 ORDER BY id", (c['id'],))
            data = [order_dict(con, row) for row in rows]
        else:
            rows = con.execute("SELECT * FROM orders WHERE courier_id=? AND status IN ('done','cancelled') ORDER BY id DESC LIMIT 200", (c['id'],))
            data = [short_order(row) for row in rows]
        balance = con.execute('SELECT COALESCE(SUM(amount_cents),0) FROM courier_cash WHERE courier_id=?', (c['id'],)).fetchone()[0]
    return jsonify(orders=data, cash_balance_cents=balance)


@bp.get('/api/courier/orders/<int:oid>')
def courier_order(oid):
    with connection() as con:
        c = courier(con)
        row = order_row(con, oid)
        if row['courier_id'] != c['id'] or row['status'] not in ACTIVE or row['archived']:
            fail('Доставка недоступна.', 404)
        return jsonify(order_dict(con, row))


def can_assign(con, cid):
    c = con.execute('SELECT * FROM couriers WHERE id=? AND active=1', (cid,)).fetchone()
    if not c or not c['on_shift'] or c['must_change'] or not c['tg']:
        fail('Кур’єр має бути активним, змінити пароль, указати Telegram і почати зміну.', 409)
    count = con.execute("SELECT COUNT(*) FROM orders WHERE courier_id=? AND status IN ('assigned','delivering','problem')", (cid,)).fetchone()[0]
    if count >= c['max_active']:
        fail('Досягнуто ліміт активних доставок кур’єра.', 409)
    return c


@bp.post('/api/courier/orders/<int:oid>/claim')
def claim(oid):
    data = body()
    with connection(True) as con:
        c = courier(con)
        row = order_row(con, oid)
        if row['courier_id'] == c['id'] and row['status'] == 'assigned':
            return jsonify(order_dict(con, row))
        if row['status'] != 'ready' or row['courier_id'] is not None or row['archived']:
            fail('Доставку вже прийнято або вона недоступна.', 409)
        check_version(row, data)
        can_assign(con, c['id'])
        con.execute("UPDATE orders SET courier_id=?,status='assigned',assigned_at=?,version=version+1 WHERE id=?",
                    (c['id'], int(time.time()), oid))
        audit(con, 'courier', 'claimed', oid, c['id'])
        return jsonify(order_dict(con, order_row(con, oid)))


def complete(con, row, data):
    if not row['courier_id']:
        fail('Спочатку призначте кур’єра.', 409)
    if row['pay'] == CASH:
        received = integer(data.get('cash_received_cents'), 0, 10**12, 'отримана готівка')
        if received != row['total_cents']:
            fail('Для завершення отримана готівка має дорівнювати сумі замовлення. При проблемі повідомте адміністратора.', 409)
    else:
        received = 0
    con.execute('INSERT INTO courier_cash(created,courier_id,order_id,amount_cents,kind) VALUES(?,?,?,?,?)',
                (int(time.time()), row['courier_id'], row['id'], received, 'collection'))
    con.execute('UPDATE orders SET completed_at=? WHERE id=?', (int(time.time()), row['id']))


@bp.post('/api/courier/orders/<int:oid>/status')
def courier_status(oid):
    data = body()
    target = data.get('status')
    with connection(True) as con:
        c = courier(con)
        row = order_row(con, oid)
        if row['courier_id'] != c['id'] or row['archived']:
            fail('Доставка недоступна.', 404)
        check_version(row, data)
        if row['status'] not in ACTIVE:
            fail('Доставка вже завершена.', 409)
        note = text(data.get('note', ''), 'Причина', 500, False)
        release = target == 'release_requested'
        if release:
            target = 'problem'
        if target not in ('delivering', 'done', 'problem') or target not in TRANSITIONS[row['status']]:
            fail('Такий перехід статусу недоступний.', 409)
        if target == 'problem' and not note:
            fail('Опишіть проблему або причину відмови.')
        if target == 'done':
            complete(con, row, data)
        con.execute('UPDATE orders SET status=?,courier_note=?,release_requested=?,version=version+1 WHERE id=?',
                    (target, note, int(release), oid))
        audit(con, 'courier', 'release_requested' if release else 'status_changed', oid, c['id'], status=target, note=note)
    return jsonify(ok=True)


@bp.get('/api/delivery/options')
def options():
    with connection() as con:
        cfg = settings(con)
        zones = [{k: row[k] for k in ('id', 'name', 'fee_cents', 'minimum_cents', 'free_from_cents')}
                 for row in con.execute('SELECT * FROM delivery_zones WHERE active=1 ORDER BY id')]
    return jsonify(zones=zones, settings=cfg, accepting=accepting(cfg))


@bp.post('/api/order')
def create_order():
    from customers import require_customer
    data = body()
    with connection() as auth_con:
        buyer = require_customer(auth_con)
        buyer_id = buyer['id']
    if server.too_many('order:' + ip(), server.ORDER_LIMIT, 600):
        fail('Забагато замовлень. Спробуйте пізніше.', 429)
    key = data.get('request_id')
    if key is not None and (not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', key)):
        fail('Некоректний ідентифікатор запиту.')
    fingerprint = hashlib.sha256(json.dumps({'customer_id': buyer_id, 'payload': data}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    name = buyer['name']
    phone = text(data.get('phone'), 'Телефон', 30)
    digits = re.sub(r'\D', '', phone)
    if not re.fullmatch(r'\+?[\d\s()\-]{10,30}', phone) or not 10 <= len(digits) <= 15:
        fail('Вкажіть коректний номер телефону (10–15 цифр).')
    tg = text(data.get('tg'), 'Telegram-нік', 64).removeprefix('@')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_]{1,30}[A-Za-z0-9]', tg):
        fail('Telegram-нік: 3–32 символи, латиниця, цифри та підкреслення.')
    tg = '@' + tg
    if data.get('age_confirmed') is not True:
        fail('Підтвердіть вік 18+ і доставку в межах Рівного.')
    street, house = text(data.get('street'), 'Вулиця', 100), text(data.get('house'), 'Будинок', 20)
    address = f'м. Рівне, {street}, буд. {house}'
    for k, label in [('flat', 'кв./офіс'), ('entr', 'під’їзд'), ('floor', 'поверх/домофон')]:
        val = text(data.get(k, ''), label, 30, False)
        if val:
            address += f', {label} {val}'
    pay = data.get('pay', CASH)
    if pay not in (CASH, CARD):
        fail('Оберіть спосіб оплати.')
    note = text(data.get('note', ''), 'Коментар', 500, False)
    wish = text(data.get('wishTime', ''), 'Час', 60, False)
    raw = data.get('items')
    if not isinstance(raw, list) or not 1 <= len(raw) <= 40:
        fail('Кошик порожній або завеликий.')
    need = {}
    for item in raw:
        if not isinstance(item, dict):
            fail('Некоректний кошик.')
        pid = integer(item.get('id'), 1, 10**9, 'товар')
        qty = integer(item.get('qty'), 1, 99, 'кількість')
        need[pid] = need.get(pid, 0) + qty
        if need[pid] > 99:
            fail('Максимум 99 одиниць одного товару.')
    with connection(True) as con:
        buyer = require_customer(con)
        name = buyer['name']
        if key:
            existing = con.execute('SELECT * FROM orders WHERE request_key=?', (key,)).fetchone()
            if existing:
                if existing['customer_id'] != buyer['id'] or not hmac.compare_digest(existing['request_hash'], fingerprint):
                    fail('Цей запит уже використано. Оновіть оформлення.', 409)
                return jsonify(created_response(con, existing)), 201
        prods, stock = server.products(con), server.stock_map(con)
        if any(pid not in prods for pid in need):
            fail('Один із товарів більше не продається. Оновіть каталог.')
        shortages = [{'id': pid, 'available': stock[pid]} for pid, qty in need.items()
                     if stock.get(pid) is not None and stock[pid] < qty]
        if shortages:
            raise server.ApiError(409, 'Не вистачає товарів.', items=shortages)
        items = [dict(id=pid, name=prods[pid]['name'], spec=prods[pid]['spec'], price=prods[pid]['price'],
                      price_cents=prods[pid]['price_cents'], qty=qty) for pid, qty in need.items()]
        subtotal = sum(item['price_cents'] * item['qty'] for item in items)
        zone, fee = zone_quote(con, data, subtotal)
        now = int(time.time())
        for pid, qty in need.items():
            if stock.get(pid) is not None:
                con.execute('UPDATE stock SET qty=qty-?,updated=? WHERE product_id=?', (qty, now, pid))
        total = subtotal + fee
        oid = con.execute('''INSERT INTO orders(created,name,phone,phone_digits,tg,address,wish_time,pay,note,
            items_json,total,total_cents,subtotal_cents,zone_id,zone_name,delivery_fee_cents,reward_cents,
            tracking_token,request_key,request_hash,customer_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (now, name, phone, digits, tg, address, wish, pay, note, json.dumps(items, ensure_ascii=False),
             total / 100, total, subtotal, zone['id'], zone['name'], fee, zone['reward_cents'],
             secrets.token_urlsafe(32), key, fingerprint, buyer['id'])).lastrowid
        saved_address = {k: data.get(k, '') for k in ('street','house','flat','entr','floor','zone_id')}
        con.execute('UPDATE customers SET phone=?,tg=?,address_json=? WHERE id=?', (phone,tg,json.dumps(saved_address,ensure_ascii=False),buyer['id']))
        audit(con, 'customer', 'created', oid, buyer['id'], zone_id=zone['id'])
        return jsonify(created_response(con, order_row(con, oid))), 201


def created_response(con, row):
    stock = server.stock_map(con)
    items = json.loads(row['items_json'])
    return dict(id=row['id'], total=row['total'], total_cents=row['total_cents'], items=items,
                subtotal_cents=row['subtotal_cents'], delivery_fee_cents=row['delivery_fee_cents'],
                address=row['address'], tracking_token=row['tracking_token'],
                stock={str(item['id']): stock.get(item['id']) for item in items})


@bp.get('/api/order-status')
def order_status():
    if server.too_many('tracking:' + ip(), 180, 600):
        fail('Забагато запитів.', 429)
    oid = integer(request.args.get('id'), 1, 10**9, 'замовлення')
    with connection() as con:
        from customers import require_customer, tracking_view
        row = order_row(con, oid)
        buyer = require_customer(con, True)
        owned = bool(buyer and row['customer_id'] == buyer['id'])
        token = request.headers.get('X-Order-Token', '')
        if row['tracking_token']:
            valid = bool(token) and hmac.compare_digest(token, row['tracking_token'])
        else:
            # Only pre-migration orders retain the historical phone lookup.
            digits = re.sub(r'\D', '', request.args.get('phone', ''))
            valid = bool(digits) and hmac.compare_digest(digits, row['phone_digits'])
        if not owned and not valid:
            fail('Замовлення не знайдено.', 404)
        return jsonify(tracking_view(con, row, owned))


@bp.get('/api/admin/orders')
def admin_orders():
    admin()
    mode = request.args.get('status', '')
    with connection() as con:
        if mode in STATUSES:
            rows = con.execute('SELECT * FROM orders WHERE status=? AND archived=0 ORDER BY id DESC LIMIT 500', (mode,))
        elif mode == 'archived':
            rows = con.execute('SELECT * FROM orders WHERE archived=1 ORDER BY id DESC LIMIT 500')
        elif mode == 'all':
            rows = con.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 500')
        else:
            rows = con.execute("SELECT * FROM orders WHERE status NOT IN ('done','cancelled') AND archived=0 ORDER BY id DESC LIMIT 500")
        return jsonify(orders=[order_dict(con, row) for row in rows])


@bp.post('/api/admin/order')
def admin_order():
    admin()
    data = body()
    oid = integer(data.get('id'), 1, 10**9, 'замовлення')
    with connection(True) as con:
        row = order_row(con, oid)
        check_version(row, data)
        target = data.get('status', row['status'])
        if target not in TRANSITIONS.get(row['status'], set()):
            fail('Такий перехід статусу недоступний. Пройдіть попередні етапи доставки.', 409)
        dt = text(data.get('delivery_time', row['delivery_time'] or ''), 'Час доставки', 120, False)
        mn = text(data.get('manager_note', row['manager_note'] or ''), 'Повідомлення клієнту', 500, False)
        if target == 'done' and row['status'] != 'done':
            complete(con, row, data)
        if target == 'cancelled' and not row['restocked']:
            server.restock(con, row)
        con.execute('UPDATE orders SET status=?,delivery_time=?,manager_note=?,version=version+1 WHERE id=?',
                    (target, dt, mn, oid))
        audit(con, 'admin', 'order_updated', oid, previous=row['status'], status=target)
        result = order_dict(con, order_row(con, oid))
        return jsonify(order=result, stock={str(k): v for k, v in server.stock_map(con).items()})


@bp.post('/api/admin/order-delete')
def archive():
    admin()
    data = body()
    oid = integer(data.get('id'), 1, 10**9, 'замовлення')
    with connection(True) as con:
        row = order_row(con, oid)
        if row['status'] not in ('done', 'cancelled'):
            fail('Архівувати можна завершені або скасовані замовлення.', 409)
        con.execute('UPDATE orders SET archived=1,version=version+1 WHERE id=?', (oid,))
        audit(con, 'admin', 'archived', oid)
    return jsonify(ok=True)


@bp.get('/api/admin/couriers')
def admin_couriers():
    admin()
    with connection() as con:
        rows = []
        for row in con.execute('SELECT * FROM couriers ORDER BY active DESC,id'):
            result = courier_dict(row)
            result['active_orders'] = con.execute("SELECT COUNT(*) FROM orders WHERE courier_id=? AND status IN ('assigned','delivering','problem')", (row['id'],)).fetchone()[0]
            result['cash_balance_cents'] = con.execute('SELECT COALESCE(SUM(amount_cents),0) FROM courier_cash WHERE courier_id=?', (row['id'],)).fetchone()[0]
            rows.append(result)
    return jsonify(couriers=rows)


@bp.post('/api/admin/couriers')
@bp.post('/api/admin/couriers/<int:cid>')
def save_courier(cid=None):
    admin()
    data = body()
    name = text(data.get('name'), 'Ім’я', 80)
    username = text(data.get('username'), 'Логін', 32)
    if not re.fullmatch(r'[A-Za-z0-9_.-]{3,32}', username):
        fail('Логін: 3–32 символи латиницею, цифри, крапка, дефіс або підкреслення.')
    phone = text(data.get('phone'), 'Телефон', 30)
    if not re.fullmatch(r'\+?[\d\s()\-]+', phone) or not 10 <= len(re.sub(r'\D', '', phone)) <= 15:
        fail('Вкажіть коректний телефон.')
    from customers import telegram
    tg = telegram(data.get('tg', ''), required=cid is None or 'tg' in data)
    limit = integer(data.get('max_active', 3), 1, 50, 'ліміт доставок')
    pw = password(data.get('password')) if data.get('password') else None
    with connection(True) as con:
        if con.execute('SELECT id FROM couriers WHERE username=? COLLATE NOCASE AND id!=?', (username, cid or 0)).fetchone():
            fail('Такий логін уже використовується.', 409)
        if cid is None:
            if pw is None:
                fail('Задайте тимчасовий пароль.')
            salt = secrets.token_bytes(16)
            cid = con.execute('INSERT INTO couriers(username,name,phone,salt,hash,iters,max_active,created,tg) VALUES(?,?,?,?,?,?,?,?,?)',
                              (username, name, phone, salt, server.hash_pw(pw, salt), server.PBKDF2_ITERS, limit, int(time.time()), tg)).lastrowid
            action = 'courier_created'
        else:
            if not con.execute('SELECT id FROM couriers WHERE id=?', (cid,)).fetchone():
                fail('Кур’єра не знайдено.', 404)
            con.execute('UPDATE couriers SET username=?,name=?,phone=?,max_active=?,tg=CASE WHEN ? THEN ? ELSE tg END WHERE id=?', (username, name, phone, limit, int('tg' in data), tg, cid))
            if pw:
                salt = secrets.token_bytes(16)
                con.execute('UPDATE couriers SET salt=?,hash=?,iters=?,must_change=1,on_shift=0 WHERE id=?',
                            (salt, server.hash_pw(pw, salt), server.PBKDF2_ITERS, cid))
                con.execute('DELETE FROM courier_sessions WHERE courier_id=?', (cid,))
            action = 'courier_updated'
        audit(con, 'admin', action, courier_id=cid, password_reset=bool(pw))
        return jsonify(courier=courier_dict(con.execute('SELECT * FROM couriers WHERE id=?', (cid,)).fetchone()))


@bp.post('/api/admin/couriers/<int:cid>/active')
def courier_active(cid):
    admin()
    data = body()
    active = boolean(data.get('active'), 'Активність')
    with connection(True) as con:
        if not con.execute('SELECT 1 FROM couriers WHERE id=?', (cid,)).fetchone():
            fail('Кур’єра не знайдено.', 404)
        rows = con.execute("SELECT * FROM orders WHERE courier_id=? AND status IN ('assigned','delivering','problem')", (cid,)).fetchall()
        if not active and rows:
            if data.get('release_active') is not True:
                fail('Є активні доставки. Підтвердьте їх повернення до доступних або спочатку перепризначте.', 409)
            reason = text(data.get('reason'), 'Причина повернення доставок', 500)
            for row in rows:
                con.execute("UPDATE orders SET courier_id=NULL,status='ready',assigned_at=NULL,release_requested=0,courier_note='',version=version+1 WHERE id=?", (row['id'],))
                audit(con, 'admin', 'released_on_deactivation', row['id'], courier_id=cid, reason=reason)
        con.execute('UPDATE couriers SET active=?,on_shift=0 WHERE id=?', (active, cid))
        con.execute('DELETE FROM courier_sessions WHERE courier_id=?', (cid,))
        audit(con, 'admin', 'courier_activated' if active else 'courier_deactivated', courier_id=cid)
    return jsonify(ok=True)


@bp.post('/api/admin/delivery/orders/<int:oid>/assign')
def assign(oid):
    admin()
    data = body()
    cid = data.get('courier_id')
    if cid is not None:
        cid = integer(cid, 1, 10**9, 'кур’єр')
    with connection(True) as con:
        row = order_row(con, oid)
        check_version(row, data)
        if row['status'] not in ('ready', *ACTIVE) or row['archived']:
            fail('Спочатку підтвердіть і підготуйте замовлення.', 409)
        if cid == row['courier_id']:
            return jsonify(ok=True)
        reason = text(data.get('reason', ''), 'Причина', 500, False)
        if row['courier_id'] and not reason:
            fail('Вкажіть причину перепризначення або повернення.')
        if cid:
            can_assign(con, cid)
        con.execute('''UPDATE orders SET courier_id=?,status=?,assigned_at=?,courier_note='',
            release_requested=0,version=version+1 WHERE id=?''',
            (cid, 'assigned' if cid else 'ready', int(time.time()) if cid else None, oid))
        audit(con, 'admin', 'assigned' if cid else 'released', oid, previous_courier=row['courier_id'], courier_id=cid, reason=reason)
    return jsonify(ok=True)


@bp.get('/api/admin/delivery/settings')
def get_settings():
    admin()
    with connection() as con:
        return jsonify(settings=settings(con), zones=[dict(row) for row in con.execute('SELECT * FROM delivery_zones ORDER BY id')])


@bp.post('/api/admin/delivery/settings')
def save_settings():
    admin()
    data = body()
    cfg = data.get('settings', {})
    if not isinstance(cfg, dict):
        fail('Некоректні налаштування.')
    parsed = dict(DEFAULTS)
    for key in ('accepting', 'hours_enabled'):
        parsed[key] = bool(boolean(cfg.get(key), key))
    for key in ('opens', 'closes'):
        value = cfg.get(key, '')
        if not isinstance(value, str) or not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', value):
            fail('Час має бути у форматі ГГ:ХХ.')
        parsed[key] = value
    if parsed['opens'] == parsed['closes'] and parsed['hours_enabled']:
        fail('Початок і кінець роботи мають відрізнятися.')
    days = cfg.get('closed_days', [])
    if not isinstance(days, list) or any(isinstance(d, bool) or not isinstance(d, int) or not 0 <= d <= 6 for d in days):
        fail('Некоректні вихідні дні.')
    parsed['closed_days'] = sorted(set(days))
    zones = data.get('zones')
    if not isinstance(zones, list) or not 1 <= len(zones) <= 50:
        fail('Потрібно від 1 до 50 районів.')
    with connection(True) as con:
        existing = settings(con)
        if cfg.get('version') != existing['version']:
            fail('Налаштування вже змінилися. Оновіть сторінку.', 409)
        seen, active_count = set(), 0
        for z in zones:
            if not isinstance(z, dict):
                fail('Некоректний район.')
            zid = z.get('id')
            name = text(z.get('name'), 'Назва району', 80)
            active = boolean(z.get('active'), 'Доступність району')
            active_count += active
            fee = money(z.get('fee'), 'Вартість доставки')
            minimum = money(z.get('minimum'), 'Мінімальна покупка')
            free = None if z.get('free_from') in ('', None) else money(z['free_from'], 'Безкоштовна доставка від')
            reward = money(z.get('reward'), 'Винагорода кур’єру')
            if zid:
                zid = integer(zid, 1, 10**9, 'район')
                if zid in seen or not con.execute('SELECT 1 FROM delivery_zones WHERE id=?', (zid,)).fetchone():
                    fail('Некоректний або повторний район.')
                con.execute('UPDATE delivery_zones SET name=?,active=?,fee_cents=?,minimum_cents=?,free_from_cents=?,reward_cents=? WHERE id=?',
                            (name, active, fee, minimum, free, reward, zid))
                seen.add(zid)
            else:
                zid = con.execute('INSERT INTO delivery_zones(name,active,fee_cents,minimum_cents,free_from_cents,reward_cents) VALUES(?,?,?,?,?,?)',
                                  (name, active, fee, minimum, free, reward)).lastrowid
                seen.add(zid)
        if not active_count:
            fail('Залиште хоча б один активний район. Для паузи вимкніть приймання замовлень.')
        for row in con.execute('SELECT id FROM delivery_zones').fetchall():
            if row['id'] not in seen:
                con.execute('UPDATE delivery_zones SET active=0 WHERE id=?', (row['id'],))
        con.execute('UPDATE delivery_settings SET value=?,version=version+1 WHERE id=1', (json.dumps(parsed),))
        audit(con, 'admin', 'settings_changed', zones=sorted(seen))
    return jsonify(ok=True)


@bp.post('/api/admin/delivery/cash')
def cash_handover():
    admin()
    data = body()
    cid = integer(data.get('courier_id'), 1, 10**9, 'кур’єр')
    amount = money(data.get('amount'), 'Сума')
    if amount <= 0:
        fail('Сума має бути більшою за нуль.')
    reference = text(data.get('reference'), 'Номер операції', 80)
    note = text(data.get('note', ''), 'Коментар', 300, False)
    with connection(True) as con:
        old = con.execute('SELECT * FROM courier_cash WHERE reference=?', (reference,)).fetchone()
        if old:
            if old['courier_id'] != cid or old['amount_cents'] != -amount:
                fail('Номер операції вже використано.', 409)
            return jsonify(ok=True)
        balance = con.execute('SELECT COALESCE(SUM(amount_cents),0) FROM courier_cash WHERE courier_id=?', (cid,)).fetchone()[0]
        if amount > balance:
            fail('Сума перевищує залишок готівки кур’єра.', 409)
        con.execute('INSERT INTO courier_cash(created,courier_id,amount_cents,kind,reference,note) VALUES(?,?,?,?,?,?)',
                    (int(time.time()), cid, -amount, 'handover', reference, note))
        audit(con, 'admin', 'cash_handover', courier_id=cid, amount_cents=amount, reference=reference)
    return jsonify(ok=True)


@bp.get('/api/admin/delivery/events')
def events():
    admin()
    oid = request.args.get('order_id')
    before = integer(request.args.get('before', 10**9), 1, 10**12, 'сторінка журналу')
    with connection() as con:
        clause, params = (' AND order_id=?', [integer(oid, 1, 10**9, 'замовлення')]) if oid else ('', [])
        rows = [dict(row) for row in con.execute('SELECT * FROM delivery_events WHERE id<?' + clause + ' ORDER BY id DESC LIMIT 100', [before, *params])]
        for row in rows:
            row['details'] = json.loads(row['details'])
        return jsonify(events=rows, next_before=rows[-1]['id'] if len(rows) == 100 else None)


@bp.get('/api/admin/delivery/reports')
def reports():
    admin()
    start, end = 0, int(time.time()) + 86400
    try:
        if request.args.get('from'):
            start = int(datetime.strptime(request.args['from'], '%Y-%m-%d').replace(tzinfo=ZoneInfo('Europe/Kyiv')).timestamp())
        if request.args.get('to'):
            end = int((datetime.strptime(request.args['to'], '%Y-%m-%d').replace(tzinfo=ZoneInfo('Europe/Kyiv')) + timedelta(days=1)).timestamp())
    except ValueError:
        fail('Некоректна дата.')
    if start >= end:
        fail('Початок періоду має передувати завершенню.')
    with connection() as con:
        summary = dict(con.execute('''SELECT COUNT(*) AS delivered,COALESCE(SUM(total_cents),0) AS sales_cents,
            COALESCE(SUM(delivery_fee_cents),0) AS fees_cents,COALESCE(SUM(reward_cents),0) AS rewards_cents
            FROM orders WHERE status='done' AND completed_at>=? AND completed_at<?''', (start, end)).fetchone())
        rows = []
        for c in con.execute('SELECT id,name,active FROM couriers ORDER BY id'):
            r = dict(c)
            r.update(dict(con.execute('''SELECT COUNT(*) AS delivered,COALESCE(SUM(reward_cents),0) AS rewards_cents
                FROM orders WHERE courier_id=? AND status='done' AND completed_at>=? AND completed_at<?''', (c['id'], start, end)).fetchone()))
            r['cash_balance_cents'] = con.execute('SELECT COALESCE(SUM(amount_cents),0) FROM courier_cash WHERE courier_id=?', (c['id'],)).fetchone()[0]
            rows.append(r)
        cash = [dict(r) for r in con.execute('''SELECT l.*,c.name FROM courier_cash l JOIN couriers c ON c.id=l.courier_id
            WHERE l.created>=? AND l.created<? ORDER BY l.id DESC LIMIT 500''', (start, end))]
        summary['average_cents'] = round(summary['sales_cents'] / summary['delivered']) if summary['delivered'] else 0
        return jsonify(summary=summary, couriers=rows, cash=cash)
