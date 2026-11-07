"""Server-side customer accounts and private order history."""
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from pathlib import Path
from flask import Blueprint, current_app, jsonify, request, session
import server
import delivery as d

bp=Blueprint('customers',__name__)
bp.before_request(d.csrf)
bp.register_error_handler(server.ApiError,d.api_error)


def initialize(database):
    con=sqlite3.connect(database,timeout=30)
    try:
        exists=con.execute("SELECT 1 FROM delivery_migrations WHERE name='customers-v2'").fetchone()
        if not exists:
            backup=Path(database).with_name(Path(database).stem+'-before-customers.sqlite3')
            if not backup.exists():
                dest=sqlite3.connect(backup)
                try:con.backup(dest)
                finally:dest.close()
        con.execute('BEGIN IMMEDIATE')
        con.execute('''CREATE TABLE IF NOT EXISTS customers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            name TEXT NOT NULL,salt BLOB NOT NULL,hash BLOB NOT NULL,iters INTEGER NOT NULL,
            created INTEGER NOT NULL,phone TEXT NOT NULL DEFAULT '',tg TEXT NOT NULL DEFAULT '',
            address_json TEXT NOT NULL DEFAULT '{}')''')
        con.execute('''CREATE TABLE IF NOT EXISTS customer_sessions(
            token_hash TEXT PRIMARY KEY,customer_id INTEGER NOT NULL REFERENCES customers(id),expires INTEGER NOT NULL)''')
        columns={r[1] for r in con.execute('PRAGMA table_info(orders)')}
        if 'customer_id' not in columns:con.execute('ALTER TABLE orders ADD COLUMN customer_id INTEGER REFERENCES customers(id)')
        if 'customer_hidden' not in columns:con.execute('ALTER TABLE orders ADD COLUMN customer_hidden INTEGER NOT NULL DEFAULT 0')
        if 'tg' not in {r[1] for r in con.execute('PRAGMA table_info(couriers)')}:
            con.execute("ALTER TABLE couriers ADD COLUMN tg TEXT NOT NULL DEFAULT ''")
        con.execute('CREATE INDEX IF NOT EXISTS customer_order_history ON orders(customer_id,customer_hidden,id)')
        con.execute('CREATE INDEX IF NOT EXISTS customer_session_owner ON customer_sessions(customer_id)')
        con.execute("INSERT OR IGNORE INTO delivery_migrations VALUES('customers-v2')")
        con.commit()
    except Exception:
        con.rollback();raise
    finally:con.close()


def telegram(value,required=True):
    value=d.text(value,'Telegram-нік',33,required).removeprefix('@')
    if not value and not required:return ''
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_]{1,30}[A-Za-z0-9]',value):
        d.fail('Telegram-нік: 3–32 символи, латиниця, цифри та підкреслення.')
    return '@'+value


def require_customer(con,optional=False):
    token=request.cookies.get('dymok_customer','')
    row=con.execute('''SELECT c.* FROM customers c JOIN customer_sessions s ON s.customer_id=c.id
        WHERE s.token_hash=? AND s.expires>?''',
        (hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone() if token else None
    if not row and not optional:d.fail('Увійдіть або зареєструйтеся, щоб оформити замовлення.',401)
    return row


def customer_dict(row):
    return dict(id=row['id'],username=row['username'],name=row['name'],phone=row['phone'],tg=row['tg'],address=json.loads(row['address_json']))


def customer_response(con,cid):
    token=secrets.token_urlsafe(32)
    con.execute('DELETE FROM customer_sessions WHERE expires<=?',(int(time.time()),))
    con.execute('INSERT INTO customer_sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),cid,int(time.time())+server.SESSION_TTL))
    response=jsonify(customer=customer_dict(con.execute('SELECT * FROM customers WHERE id=?',(cid,)).fetchone()))
    response.set_cookie('dymok_customer',token,max_age=server.SESSION_TTL,httponly=True,samesite='Strict',secure=current_app.config['SESSION_COOKIE_SECURE'] or request.is_secure)
    return response


@bp.get('/api/customer/session')
def customer_session():
    with d.connection() as con:
        c=require_customer(con,True)
        return jsonify(customer=customer_dict(c) if c else None,csrf_token=session['csrf_token'])


@bp.post('/api/customer/register')
def register():
    data=d.body()
    if server.too_many('customer-register:'+d.ip(),10,3600):d.fail('Забагато реєстрацій. Спробуйте пізніше.',429)
    username=d.text(data.get('username'),'Логін',32)
    if not re.fullmatch(r'[A-Za-z0-9_.-]{3,32}',username):d.fail('Логін: 3–32 символи, латиниця, цифри, крапка, дефіс або підкреслення.')
    name=d.text(data.get('name'),'Ім’я',80)
    password=d.password(data.get('password'))
    salt=secrets.token_bytes(16);hashed=server.hash_pw(password,salt)
    with d.connection(True) as con:
        if con.execute('SELECT id FROM customers WHERE username=? COLLATE NOCASE',(username,)).fetchone():d.fail('Цей логін уже зайнятий. Оберіть інший або увійдіть.',409)
        cid=con.execute('INSERT INTO customers(username,name,salt,hash,iters,created) VALUES(?,?,?,?,?,?)',(username,name,salt,hashed,server.PBKDF2_ITERS,int(time.time()))).lastrowid
        old=hashlib.sha256(request.cookies.get('dymok_customer','').encode()).hexdigest()
        con.execute('DELETE FROM customer_sessions WHERE token_hash=?',(old,))
        d.audit(con,'customer','customer_registered',actor_id=cid)
        return customer_response(con,cid)


@bp.post('/api/customer/login')
def login():
    data=d.body()
    if server.too_many('customer-login:'+d.ip(),12,900):d.fail('Забагато спроб входу. Повторіть через 15 хвилин.',429)
    username=d.text(data.get('username'),'Логін',32)
    password=data.get('password','')
    if not isinstance(password,str) or not 1<=len(password)<=256:d.fail('Вкажіть пароль.')
    with d.connection(True) as con:
        c=con.execute('SELECT * FROM customers WHERE username=? COLLATE NOCASE',(username,)).fetchone()
        calc=server.hash_pw(password,c['salt'] if c else bytes(16),c['iters'] if c else server.PBKDF2_ITERS)
        if not c or not hmac.compare_digest(calc,c['hash']):d.fail('Невірний логін або пароль.',401)
        # Rotate this browser's session; other devices remain logged in.
        old=hashlib.sha256(request.cookies.get('dymok_customer','').encode()).hexdigest()
        con.execute('DELETE FROM customer_sessions WHERE token_hash=?',(old,))
        d.audit(con,'customer','customer_login',actor_id=c['id'])
        return customer_response(con,c['id'])


@bp.post('/api/customer/logout')
def logout():
    with d.connection(True) as con:
        c=require_customer(con)
        con.execute('DELETE FROM customer_sessions WHERE token_hash=?',(hashlib.sha256(request.cookies.get('dymok_customer','').encode()).hexdigest(),))
        d.audit(con,'customer','customer_logout',actor_id=c['id'])
    response=jsonify(ok=True);response.delete_cookie('dymok_customer',path='/');return response


@bp.post('/api/customer/profile')
def profile():
    data=d.body();name=d.text(data.get('name'),'Ім’я',80)
    with d.connection(True) as con:
        c=require_customer(con)
        con.execute('UPDATE customers SET name=? WHERE id=?',(name,c['id']))
        return jsonify(customer=customer_dict(con.execute('SELECT * FROM customers WHERE id=?',(c['id'],)).fetchone()))


@bp.post('/api/customer/password')
def password():
    data=d.body();new=d.password(data.get('new'));old=data.get('current','')
    if not isinstance(old,str) or len(old)>256:d.fail('Некоректний поточний пароль.')
    with d.connection(True) as con:
        c=require_customer(con)
        if server.too_many('customer-password:'+str(c['id']),8,900):d.fail('Забагато спроб. Повторіть пізніше.',429)
        if not hmac.compare_digest(server.hash_pw(old,c['salt'],c['iters']),c['hash']):d.fail('Поточний пароль неправильний.',403)
        if hmac.compare_digest(old,new):d.fail('Введіть інший новий пароль.')
        salt=secrets.token_bytes(16)
        con.execute('UPDATE customers SET salt=?,hash=?,iters=? WHERE id=?',(salt,server.hash_pw(new,salt),server.PBKDF2_ITERS,c['id']))
        con.execute('DELETE FROM customer_sessions WHERE customer_id=?',(c['id'],))
        d.audit(con,'customer','customer_password_changed',actor_id=c['id'])
        return customer_response(con,c['id'])


def owned_order(con,cid,oid):
    row=con.execute('SELECT * FROM orders WHERE id=? AND customer_id=?',(oid,cid)).fetchone()
    if not row:d.fail('Замовлення не знайдено.',404)
    return row


def courier_contact(con,row):
    if row['status'] not in d.ACTIVE or not row['courier_id']:return None
    c=con.execute('SELECT name,tg FROM couriers WHERE id=? AND active=1',(row['courier_id'],)).fetchone()
    return dict(name=c['name'],tg=c['tg']) if c else None


def tracking_view(con,row,owned=False):
    result=d.public_order(row)
    result.update(zone_name=row['zone_name'],wish_time=row['wish_time'],assigned_at=row['assigned_at'],completed_at=row['completed_at'],owned=owned)
    # Only explicitly public state changes enter the timeline; courier notes stay private.
    timeline=[{'status':'new','created':row['created']}]
    for e in con.execute("SELECT created,action,details FROM delivery_events WHERE order_id=? AND action IN ('order_updated','status_changed','claimed','assigned','released','released_on_deactivation') ORDER BY id LIMIT 300",(row['id'],)):
        detail=json.loads(e['details']);status=detail.get('status')
        if e['action'] in ('claimed','assigned'):status='assigned'
        elif e['action'] in ('released','released_on_deactivation'):status='ready'
        if status in d.STATUSES and timeline[-1]['status']!=status:timeline.append({'status':status,'created':e['created']})
    result['timeline']=timeline
    if owned:
        result.update(name=row['name'],phone=row['phone'],tg=row['tg'],address=row['address'],pay=row['pay'],
                      items=json.loads(row['items_json']),courier=courier_contact(con,row),hidden=bool(row['customer_hidden']))
    return result


@bp.get('/api/customer/orders')
def orders():
    before=d.integer(request.args.get('before',10**12),1,10**15,'сторінка')
    limit=d.integer(request.args.get('limit',30),1,100,'ліміт')
    active=request.args.get('view')=='active'
    with d.connection() as con:
        c=require_customer(con)
        extra=" AND status NOT IN ('done','cancelled')" if active else ''
        rows=con.execute('SELECT * FROM orders WHERE customer_id=? AND customer_hidden=0 AND id<?'+extra+' ORDER BY id DESC LIMIT ?', (c['id'],before,limit+1)).fetchall()
        counts=dict(con.execute("SELECT COUNT(*) AS total,COALESCE(SUM(status NOT IN ('done','cancelled')),0) AS active,COALESCE(SUM(status='done'),0) AS delivered FROM orders WHERE customer_id=? AND customer_hidden=0",(c['id'],)).fetchone())
        return jsonify(orders=[tracking_view(con,row,True) for row in rows[:limit]],counts=counts,next_before=rows[limit-1]['id'] if len(rows)>limit else None)


@bp.get('/api/customer/orders/<int:oid>')
def order(oid):
    with d.connection() as con:
        c=require_customer(con)
        return jsonify(tracking_view(con,owned_order(con,c['id'],oid),True))


@bp.post('/api/customer/orders/<int:oid>/hide')
def hide(oid):
    d.body()
    with d.connection(True) as con:
        c=require_customer(con);row=owned_order(con,c['id'],oid)
        if row['status']!='done':d.fail('З історії можна видалити лише доставлені замовлення.',409)
        con.execute('UPDATE orders SET customer_hidden=1 WHERE id=? AND customer_id=?',(oid,c['id']))
        if not row['customer_hidden']:d.audit(con,'customer','customer_order_hidden',oid,c['id'])
    return jsonify(ok=True)


@bp.post('/api/customer/orders/import')
def import_orders():
    data=d.body();receipts=data.get('receipts')
    if not isinstance(receipts,list) or not 1<=len(receipts)<=50:d.fail('Оберіть від 1 до 50 замовлень із особистими посиланнями.')
    if server.too_many('customer-import:'+d.ip(),15,600):d.fail('Забагато запитів.',429)
    imported=[]
    with d.connection(True) as con:
        c=require_customer(con)
        for receipt in receipts:
            if not isinstance(receipt,dict):continue
            oid=receipt.get('id');token=receipt.get('token')
            if not isinstance(oid,int) or isinstance(oid,bool) or not isinstance(token,str) or len(token)>100:continue
            row=con.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
            if not row or not row['tracking_token'] or not hmac.compare_digest(token,row['tracking_token']):continue
            if row['customer_id'] not in (None,c['id']):continue
            if row['customer_id'] is None:
                con.execute('UPDATE orders SET customer_id=? WHERE id=? AND customer_id IS NULL',(c['id'],oid))
                d.audit(con,'customer','customer_order_imported',oid,c['id'])
            imported.append(oid)
    return jsonify(imported_ids=imported)


@bp.post('/api/courier/profile')
def courier_profile():
    data=d.body();tg=telegram(data.get('tg'))
    with d.connection(True) as con:
        c=d.courier(con,True)
        con.execute('UPDATE couriers SET tg=? WHERE id=?',(tg,c['id']))
        d.audit(con,'courier','courier_contact_updated',actor_id=c['id'])
        return jsonify(courier=d.courier_dict(con.execute('SELECT * FROM couriers WHERE id=?',(c['id'],)).fetchone()))
