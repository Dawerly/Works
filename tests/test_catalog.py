import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog import create_app, get_db
import server





class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = create_app({
            'TESTING': True, 'SECRET_KEY': 'test-key', 'SEED_CATALOG': False,
            'ADMIN_USERNAME': 'admin', 'DATABASE': str(self.root / 'db.sqlite3'),
            'UPLOAD_FOLDER': str(self.root / 'media'),
        })
        server.set_admin('admin', 'test-password')
        result = self.app.test_cli_runner().invoke(args=['init-db'])
        self.assertEqual(result.exit_code, 0, result.output)
        self.client = self.app.test_client()
        self.token = self.client.get('/api/session').json['csrf_token']
        response = self.request('POST', '/api/login', json={'username': 'admin', 'password': 'test-password'})
        self.assertEqual(response.status_code, 200)
        self.token = response.json['csrf_token']
        self.schema = [{'key': 'volume', 'label': 'Об’єм', 'required': True}]
        self.category = self.request('POST', '/api/categories', json={'name': 'Категорія А', 'attribute_schema': self.schema}).json['id']

    def request(self, method, path, **kwargs):
        response = self.client.open(path, method=method, headers={'X-CSRF-Token': self.token}, **kwargs)
        response.request.environ['wsgi.input'].close()
        return response

    def product(self, **overrides):
        data = {'name': 'Модуль', 'category_id': str(self.category), 'price': '100.00',
                'discount_percentage': '15', 'attributes': json.dumps({'volume': '2 мл'})}
        data.update(overrides)
        return self.request('POST', '/api/products', data=data, content_type='multipart/form-data')

    def image(self):
        stream = io.BytesIO()
        Image.new('RGB', (12, 12), 'green').save(stream, format='PNG')
        stream.seek(0)
        return stream

    def test_product_crud_and_discount(self):
        response = self.product()
        self.assertEqual(response.status_code, 201)
        product = response.json
        self.assertEqual((product['original_price'], product['discount_percentage'], product['final_price']), ('100.00', '15.00', '85.00'))
        self.assertEqual(product['attributes'], {'volume': '2 мл'})
        self.assertEqual(self.client.get(f'/api/products/{product["id"]}').status_code, 200)
        updated = self.request('PUT', f'/api/products/{product["id"]}', data={
            'name': 'Новий модуль', 'category_id': str(self.category), 'price': '20.50',
            'discount_percentage': '0', 'attributes': '{"volume":"3 мл"}'}, content_type='multipart/form-data')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json['final_price'], '20.50')
        self.assertEqual(self.request('DELETE', f'/api/products/{product["id"]}').status_code, 204)
        self.assertEqual(self.client.get(f'/api/products/{product["id"]}').status_code, 404)

    def test_money_rounding_and_boundaries(self):
        for price, discount, expected in [('0.03', '50', '0.02'), ('0.05', '10', '0.05'), ('199.99', '12.50', '174.99'), ('3', '100', '0.00'), ('0', '0', '0.00')]:
            with self.subTest(price=price, discount=discount):
                response = self.product(price=price, discount_percentage=discount)
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json['final_price'], expected)

    def test_invalid_money(self):
        for field, value in [('price', '-1'), ('price', 'NaN'), ('price', '1.001'), ('price', '1e3'), ('price', '1,5'), ('discount_percentage', '100.01'), ('discount_percentage', '-2')]:
            with self.subTest(field=field, value=value):
                self.assertEqual(self.product(**{field: value}).status_code, 400)

    def test_attributes_validated_on_server(self):
        for attributes in ['{}', '[]', '{bad', '{"volume":3}', '{"volume":"2","extra":"x"}']:
            with self.subTest(attributes=attributes):
                self.assertEqual(self.product(attributes=attributes).status_code, 400)
        self.assertEqual(self.product(category_id='9999').status_code, 404)
        self.assertEqual(self.product(category_id='1 OR 1=1').status_code, 400)

    def test_category_crud_and_restricted_delete(self):
        product = self.product().json
        self.assertEqual(self.request('DELETE', f'/api/categories/{self.category}').status_code, 409)
        incompatible = [{'key': 'battery', 'label': 'Батарея', 'required': True}]
        self.assertEqual(self.request('PUT', f'/api/categories/{self.category}', json={'name': 'Нова', 'attribute_schema': incompatible}).status_code, 409)
        compatible = self.schema + [{'key': 'color', 'label': 'Колір', 'required': False}]
        response = self.request('PUT', f'/api/categories/{self.category}', json={'name': 'Нова', 'attribute_schema': compatible})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], 'Нова')
        self.assertEqual(self.client.get('/api/categories').json['items'][0]['product_count'], 1)
        self.request('DELETE', f'/api/products/{product["id"]}')
        self.assertEqual(self.request('DELETE', f'/api/categories/{self.category}').status_code, 204)

    def test_invalid_category_schemas_and_duplicates(self):
        for schema in [{}, [{'key': '__proto__', 'label': 'Bad'}], self.schema * 2, [{'key': 'test', 'label': 'Test', 'required': 'yes'}]]:
            self.assertEqual(self.request('POST', '/api/categories', json={'name': 'Test', 'attribute_schema': schema}).status_code, 400)
        self.assertEqual(self.request('POST', '/api/categories', json={'name': 'Категорія А', 'attribute_schema': []}).status_code, 409)

    def test_image_validation_replace_remove_and_public_delivery(self):
        response = self.product(image=(self.image(), '../../unsafe.png'))
        self.assertEqual(response.status_code, 201)
        product = response.json
        old = self.root / 'media' / product['image_url'].rsplit('/', 1)[1]
        self.assertTrue(old.exists())
        with self.app.test_client().get(product['image_url']) as image_response:
            self.assertEqual(image_response.mimetype, 'image/webp')
        data = {'name': 'Модуль', 'category_id': str(self.category), 'price': '100', 'attributes': '{"volume":"2"}'}
        response = self.request('PUT', f'/api/products/{product["id"]}', data={**data, 'image': (self.image(), 'new.png')}, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(old.exists())
        self.assertEqual(len(list((self.root / 'media').iterdir())), 1)
        response = self.request('PUT', f'/api/products/{product["id"]}', data={**data, 'remove_image': '1'}, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json['image_url'])
        self.assertEqual(list((self.root / 'media').iterdir()), [])
        self.assertEqual(self.product(image=(io.BytesIO(b'<script>bad</script>'), 'fake.png')).status_code, 400)

    def test_image_delete_and_failed_transaction_cleanup(self):
        product = self.product(image=(self.image(), 'photo.png')).json
        self.assertEqual(self.request('DELETE', f'/api/products/{product["id"]}').status_code, 204)
        self.assertEqual(list((self.root / 'media').iterdir()), [])
        with self.app.app_context():
            get_db().executescript("CREATE TRIGGER reject_product BEFORE INSERT ON products BEGIN SELECT RAISE(ABORT, 'test rollback'); END;")
        self.assertEqual(self.product(image=(self.image(), 'photo.png')).status_code, 409)
        self.assertEqual(list((self.root / 'media').iterdir()), [])

    def test_upload_size_limit(self):
        response = self.product(image=(io.BytesIO(b'x' * (5 * 1024 * 1024 + 1)), 'huge.png'))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(list((self.root / 'media').iterdir()), [])

    def test_auth_csrf_and_logout(self):
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get('/api/products').status_code, 401)
        self.assertEqual(self.client.post('/api/categories', json={'name': 'bad'}).status_code, 403)
        self.assertEqual(self.request('POST', '/api/login', json={'username': 'admin', 'password': 'wrong'}).status_code, 401)
        self.assertEqual(self.request('POST', '/api/logout').status_code, 204)
        self.assertEqual(self.client.get('/api/categories').status_code, 401)

    def test_search_pagination_and_literal_wildcards(self):
        self.product(name='100% модуль')
        self.product(name='Інший модуль')
        response = self.client.get('/api/products?q=%25&limit=1').json
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['items'][0]['name'], '100% модуль')
        self.assertEqual(self.client.get('/api/products?limit=1&page=2').json['total'], 2)
        self.assertEqual(self.client.get('/api/products?page=0').status_code, 400)
        self.assertEqual(self.client.get('/api/products?q=%27%20OR%201=1--').json['total'], 0)

    def test_missing_records_and_wrong_content_type(self):
        self.assertEqual(self.request('DELETE', '/api/products/999').status_code, 404)
        self.assertEqual(self.request('DELETE', '/api/categories/999').status_code, 404)
        self.assertEqual(self.request('POST', '/api/products', json={}).status_code, 415)
        self.assertEqual(self.client.get('/admin/../app.py').status_code, 404)


if __name__ == '__main__':
    unittest.main()
