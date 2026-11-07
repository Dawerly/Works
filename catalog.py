"""Flask + sqlite3 admin API. Python 3.11+, no ORM or frontend framework."""
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import warnings
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4

import click
from flask import Flask, current_app, g, jsonify, request, send_from_directory, session
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.exceptions import HTTPException
from flask import Response
import server
import catalog_store


class APIError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
        g.db.create_function('casefold', 1, lambda value: str(value).casefold())
    return g.db


def dumps(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def json_object():
    value = request.get_json()
    if not isinstance(value, dict):
        raise APIError('Очікується JSON-об’єкт.')
    return value


def text(value, label, maximum, required=True):
    if not isinstance(value, str):
        raise APIError(f'{label}: очікується текст.')
    value = value.strip()
    if (required and not value) or len(value) > maximum:
        raise APIError(f'{label}: дозволено від {1 if required else 0} до {maximum} символів.')
    return value


def positive_int(value, label):
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]{1,12}', str(value)) or int(value) < 1:
        raise APIError(f'{label}: потрібне додатне ціле число.')
    return int(value)


def decimal_value(value, label, maximum):
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise APIError(f'{label}: некоректне число.')
    # Accept ordinary decimal notation, maximum two fractional digits.
    raw = str(value)
    if not re.fullmatch(r'[0-9]{1,10}(\.[0-9]{1,2})?', raw):
        raise APIError(f'{label}: використайте крапку та не більше двох десяткових знаків.')
    try:
        number = Decimal(raw)
    except InvalidOperation:
        raise APIError(f'{label}: некоректне число.')
    if not number.is_finite() or not 0 <= number <= maximum:
        raise APIError(f'{label}: допустимий діапазон 0–{maximum}.')
    return number


def validate_schema(schema):
    if not isinstance(schema, list) or len(schema) > 40:
        raise APIError('Схема характеристик має бути масивом із максимум 40 полів.')
    result, seen = [], set()
    for field in schema:
        if not isinstance(field, dict) or set(field) - {'key', 'label', 'required'}:
            raise APIError('Поле схеми має містити key, label та необов’язкове required.')
        key = field.get('key')
        if not isinstance(key, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,49}', key):
            raise APIError('Ключ поля: латиниця, цифри, _, початок із літери, до 50 символів.')
        if key in seen:
            raise APIError(f'Ключ {key} повторюється.')
        required = field.get('required', False)
        if not isinstance(required, bool):
            raise APIError('required має бути true або false.')
        seen.add(key)
        result.append({'key': key, 'label': text(field.get('label'), 'Назва поля', 100), 'required': required})
    return result


def validate_attributes(attributes, schema):
    if not isinstance(attributes, dict):
        raise APIError('Характеристики мають бути JSON-об’єктом.')
    allowed = {field['key'] for field in schema}
    if set(attributes) - allowed:
        raise APIError('Характеристики містять поля, яких немає в цій категорії.')
    result = {}
    for field in schema:
        result[field['key']] = text(attributes.get(field['key'], ''), field['label'], 500, field['required'])
    return result


def category_or_404(category_id):
    row = get_db().execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
    if row is None:
        raise APIError('Категорію не знайдено.', 404)
    return row


def product_or_404(product_id):
    row = get_db().execute('''SELECT p.*, c.name AS category_name FROM products p
                            JOIN categories c ON c.id = p.category_id WHERE p.id = ?''', (product_id,)).fetchone()
    if row is None:
        raise APIError('Товар не знайдено.', 404)
    return row


def category_dict(row):
    result = dict(row)
    result['attribute_schema'] = json.loads(result['attribute_schema'])
    return result


def product_dict(row):
    result = dict(row)
    original = Decimal(result.pop('price_cents')) / 100
    discount = Decimal(str(result['discount_percentage']))
    final = (original * (1 - discount / 100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    # Strings preserve exact money values in JSON and can go directly into HTML inputs.
    result.update(original_price=f'{original:.2f}', discount_percentage=f'{discount:.2f}', final_price=f'{final:.2f}')
    result['attributes'] = json.loads(result['attributes'])
    filename = result.pop('image_filename')
    result['image_url'] = f'/media/{filename}' if filename else result.get('external_image')
    return result


def save_image(upload):
    if upload is None or not upload.filename:
        return None
    data = upload.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise APIError('Зображення завелике: максимум 5 МіБ.', 413)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise APIError('Дозволені лише справжні JPEG, PNG або WebP.')
                if source.width * source.height > 20_000_000:
                    raise APIError('Максимальний розмір зображення — 20 мегапікселів.')
                source.load()
                image = ImageOps.exif_transpose(source).convert('RGBA')
                image.thumbnail((2400, 2400))
                encoded = io.BytesIO()
                image.save(encoded, format='WEBP', quality=90)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise APIError('Не вдалося прочитати зображення.')
    filename = f'{uuid4().hex}.webp'
    target = Path(current_app.config['UPLOAD_FOLDER']) / filename
    try:
        with target.open('xb') as stream:
            stream.write(encoded.getvalue())
    except OSError:
        target.unlink(missing_ok=True)
        raise
    return filename


def cleanup_image(filename):
    if not filename or not re.fullmatch(r'[0-9a-f]{32}\.webp', filename):
        return
    try:
        (Path(current_app.config['UPLOAD_FOLDER']) / filename).unlink(missing_ok=True)
    except OSError:
        current_app.logger.exception('Could not remove unused image %s', filename)


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        DATABASE=str(server.DB_PATH),
        UPLOAD_FOLDER=str(server.DB_PATH.parent / 'media'),
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE') == '1',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    )
    if config:
        app.config.update(config)
    if not app.config['SECRET_KEY']:
        keyfile = Path(app.config['DATABASE']).parent / 'session.key'
        keyfile.parent.mkdir(parents=True, exist_ok=True)
        tempkey = keyfile.with_name('.session-' + secrets.token_hex(12))
        try:
            with tempkey.open('x', encoding='utf-8') as stream:
                stream.write(secrets.token_hex(32))
            tempkey.chmod(0o600)
            try:
                os.link(tempkey, keyfile)
            except FileExistsError:
                pass
        finally:
            tempkey.unlink(missing_ok=True)
        app.config['SECRET_KEY'] = keyfile.read_text(encoding='utf-8').strip()
    server.DB_PATH = Path(app.config['DATABASE'])
    server.init_db()
    catalog_store.initialize(app.config['DATABASE'], seed=app.config.get('SEED_CATALOG', True))
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

    @app.teardown_appcontext
    def close_db(_error):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    @app.cli.command('init-db')
    def init_db():
        """Create the new schema without deleting data. Not a legacy migration."""
        db = get_db()
        db.execute('PRAGMA journal_mode = WAL')
        db.executescript((Path(app.root_path) / 'schema.sql').read_text(encoding='utf-8'))
        click.echo('SQLite schema initialized.')

    def legacy_handler():
        from legacy_wsgi import WSGIHandler
        return WSGIHandler(request.environ)

    @app.before_request
    def protect_api():
        protected = request.path in {'/api/session', '/api/login', '/api/logout'} or request.path.startswith(('/api/categories', '/api/products'))
        if not protected:
            return
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)
        if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            token = request.headers.get('X-CSRF-Token', '')
            if not hmac.compare_digest(token.encode(), session['csrf_token'].encode()):
                raise APIError('Недійсний CSRF-токен. Оновіть сторінку.', 403)
        if request.path not in {'/api/session', '/api/login'} and not legacy_handler().is_admin():
            raise APIError('Потрібен вхід адміністратора.', 401)

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        if request.path.startswith('/admin/catalog'):
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' https: blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            )
        if request.path.startswith(('/api/', '/admin')):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.errorhandler(APIError)
    def api_error(error):
        return jsonify(error=error.message), error.status

    @app.errorhandler(sqlite3.IntegrityError)
    def integrity_error(_error):
        return jsonify(error='Конфлікт даних: назва категорії вже існує або категорія містить товари.'), 409

    @app.errorhandler(sqlite3.OperationalError)
    def database_error(error):
        app.logger.error('Database error: %s', error)
        status = 503 if 'locked' in str(error).lower() else 500
        return jsonify(error='База тимчасово недоступна.' if status == 503 else 'Помилка бази даних. Перевірте ініціалізацію схеми.'), status

    @app.errorhandler(HTTPException)
    def http_error(error):
        message = 'Запит завеликий: максимум 6 МіБ.' if error.code == 413 else error.description
        return jsonify(error=message), error.code

    @app.errorhandler(500)
    def server_error(_error):
        return jsonify(error='Внутрішня помилка сервера.'), 500

    @app.get('/admin/catalog/')
    def admin_index():
        return send_from_directory(Path(app.root_path) / 'admin' / 'catalog', 'index.html')

    @app.get('/admin/catalog/<filename>')
    def admin_asset(filename):
        if filename not in {'admin.js', 'admin.css', 'index.html'}:
            raise APIError('Файл не знайдено.', 404)
        return send_from_directory(Path(app.root_path) / 'admin' / 'catalog', filename)

    @app.get('/media/<filename>')
    def media(filename):
        if not re.fullmatch(r'[0-9a-f]{32}\.webp', filename):
            raise APIError('Зображення не знайдено.', 404)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.get('/api/session')
    def session_info():
        return jsonify(authenticated=legacy_handler().is_admin(), csrf_token=session['csrf_token'])

    @app.post('/api/login')
    def login():
        handler = legacy_handler()
        try:
            token = handler.login(json_object())
        except server.ApiError as error:
            raise APIError(error.message, error.code)
        session.clear()
        session['csrf_token'] = secrets.token_urlsafe(32)
        session.permanent = True
        response = jsonify(authenticated=True, csrf_token=session['csrf_token'])
        response.headers.add(*handler.cookie(token, server.SESSION_TTL))
        return response

    @app.post('/api/logout')
    def logout():
        handler = legacy_handler()
        handler.headers['X-Requested-With'] = 'dymok'
        handler.api('POST', '/api/admin/logout', {})
        session.clear()
        response = Response(status=204)
        response.headers.add(*handler.cookie('', 0))
        return response

    @app.get('/api/catalog')
    def storefront_catalog():
        return jsonify(catalog_store.public_catalog(get_db()))

    @app.get('/api/catalog.js')
    def storefront_bootstrap():
        data = catalog_store.public_catalog(get_db())
        script = 'const PRODUCTS = ' + dumps(data['products']) + ';\nconst LIVE_CATEGORIES = ' + dumps(data['categories']) + ';\n'
        return Response(script, mimetype='application/javascript')

    @app.get('/api/categories')
    def list_categories():
        rows = get_db().execute('''SELECT c.*, COUNT(p.id) AS product_count FROM categories c
                                  LEFT JOIN products p ON p.category_id = c.id GROUP BY c.id ORDER BY c.id''')
        return jsonify(items=[category_dict(row) for row in rows])

    @app.get('/api/categories/<int:category_id>')
    def get_category(category_id):
        return jsonify(category_dict(category_or_404(category_id)))

    @app.post('/api/categories')
    @app.put('/api/categories/<int:category_id>')
    def save_category(category_id=None):
        data = json_object()
        name = text(data.get('name'), 'Назва категорії', 120)
        schema = validate_schema(data.get('attribute_schema', []))
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            if category_id is None:
                category_id = catalog_store.allocate_id(db, 'category')
                db.execute('INSERT INTO categories(id, name, attribute_schema) VALUES (?, ?, ?)', (category_id, name, dumps(schema)))
                status = 201
            else:
                category_or_404(category_id)
                for product in db.execute('SELECT id, attributes FROM products WHERE category_id = ?', (category_id,)):
                    try:
                        validate_attributes(json.loads(product['attributes']), schema)
                    except APIError:
                        raise APIError(f'Нова схема несумісна з товаром #{product["id"]}. Спершу оновіть товари або зробіть нові поля необов’язковими.', 409)
                db.execute('UPDATE categories SET name = ?, attribute_schema = ? WHERE id = ?', (name, dumps(schema), category_id))
                status = 200
        return jsonify(category_dict(category_or_404(category_id))), status

    @app.delete('/api/categories/<int:category_id>')
    def delete_category(category_id):
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            category_or_404(category_id)
            if db.execute('SELECT 1 FROM products WHERE category_id = ? LIMIT 1', (category_id,)).fetchone():
                raise APIError('Категорія містить товари. Спочатку перенесіть або видаліть їх.', 409)
            db.execute('DELETE FROM categories WHERE id = ?', (category_id,))
        return '', 204

    @app.get('/api/products')
    def list_products():
        page = positive_int(request.args.get('page', '1'), 'Сторінка')
        limit = min(positive_int(request.args.get('limit', '20'), 'Ліміт'), 100)
        query = text(request.args.get('q', ''), 'Пошук', 200, required=False)
        clauses, params = [], []
        if query:
            clauses.append("casefold(p.name) LIKE casefold(?) ESCAPE '\\'")
            escaped = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            params.append(f'%{escaped}%')
        if request.args.get('category_id'):
            clauses.append('p.category_id = ?')
            params.append(positive_int(request.args['category_id'], 'Категорія'))
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        # `where` contains only fixed SQL fragments. All user values are bound parameters.
        total = get_db().execute('SELECT COUNT(*) FROM products p' + where, params).fetchone()[0]
        rows = get_db().execute('''SELECT p.*, c.name AS category_name FROM products p
                                 JOIN categories c ON c.id = p.category_id''' + where +
                                ' ORDER BY p.id DESC LIMIT ? OFFSET ?', [*params, limit, (page - 1) * limit])
        return jsonify(items=[product_dict(row) for row in rows], total=total, page=page, limit=limit)

    @app.get('/api/products/<int:product_id>')
    def get_product(product_id):
        return jsonify(product_dict(product_or_404(product_id)))

    @app.post('/api/products')
    @app.put('/api/products/<int:product_id>')
    def save_product(product_id=None):
        if request.mimetype != 'multipart/form-data':
            raise APIError('Для товарів використайте multipart/form-data.', 415)
        form = request.form
        name = text(form.get('name'), 'Назва товару', 200)
        description = text(form.get('description', ''), 'Опис', 10000, required=False)
        brand = text(form.get('brand', ''), 'Бренд', 120, required=False)
        spec = text(form.get('spec', ''), 'Варіант', 200, required=False)
        category_id = positive_int(form.get('category_id'), 'Категорія')
        price = decimal_value(form.get('price'), 'Ціна', Decimal('999999999.99'))
        discount = decimal_value(form.get('discount_percentage', '0'), 'Знижка', Decimal('100'))
        try:
            attributes = json.loads(form.get('attributes', '{}'))
        except (ValueError, TypeError):
            raise APIError('Некоректний JSON характеристик.')
        remove_image = form.get('remove_image', '0')
        if remove_image not in {'0', '1'}:
            raise APIError('remove_image має бути 0 або 1.')
        upload = request.files.get('image')
        if remove_image == '1' and upload and upload.filename:
            raise APIError('Оберіть заміну або видалення картинки.')
        new_image, old_image = None, None
        try:
            with get_db() as db:
                # Serialize schema validation and writes against category edits/deletes.
                db.execute('BEGIN IMMEDIATE')
                old = product_or_404(product_id) if product_id is not None else None
                category = category_or_404(category_id)
                attributes = validate_attributes(attributes, json.loads(category['attribute_schema']))
                new_image = save_image(upload)
                old_image = old['image_filename'] if old else None
                filename = new_image or (None if remove_image == '1' else old_image)
                external_image = None if new_image or remove_image == '1' else (old['external_image'] if old else None)
                values = (category_id, name, description, int(price * 100), str(discount), dumps(attributes), filename, brand, spec, external_image)
                if old is None:
                    product_id = catalog_store.allocate_id(db, 'product')
                    db.execute('''INSERT INTO products
                        (category_id, name, description, price_cents, discount_percentage, attributes, image_filename, brand, spec, external_image, id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (*values, product_id))
                    status = 201
                else:
                    db.execute('''UPDATE products SET category_id=?, name=?, description=?, price_cents=?,
                        discount_percentage=?, attributes=?, image_filename=?, brand=?, spec=?, external_image=?,
                        updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id=?''', (*values, product_id))
                    status = 200
        except Exception:
            cleanup_image(new_image)
            raise
        if old_image and (new_image or remove_image == '1'):
            cleanup_image(old_image)
        return jsonify(product_dict(product_or_404(product_id))), status

    @app.delete('/api/products/<int:product_id>')
    def delete_product(product_id):
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = product_or_404(product_id)
            db.execute('DELETE FROM products WHERE id = ?', (product_id,))
            db.execute('DELETE FROM stock WHERE product_id = ?', (product_id,))
        cleanup_image(row['image_filename'])
        return '', 204

    @app.route('/', defaults={'path': ''}, methods=['GET', 'HEAD', 'POST'])
    @app.route('/<path:path>', methods=['GET', 'HEAD', 'POST'])
    def legacy_routes(path):
        from legacy_wsgi import legacy_application
        status_headers = []
        body = legacy_application(request.environ, lambda status, headers: status_headers.extend([status, headers]))
        return Response(b''.join(body), status=int(status_headers[0].split()[0]), headers=status_headers[1])

    return app
