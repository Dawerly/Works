import concurrent.futures
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
import catalog_store
from catalog import create_app, get_db


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {'TESTING': True, 'SECRET_KEY': 'integration-key',
                       'DATABASE': str(self.root/'shop.db'), 'UPLOAD_FOLDER': str(self.root/'media')}
        self.app = create_app(self.config)
        server.set_admin('admin', 'test-password')
        server._hits.clear()
        self.client = self.app.test_client()
        self.assertEqual(self.client.post('/api/admin/login', json={'username':'admin', 'password':'test-password'},
                                         headers={'X-Requested-With':'dymok'}).status_code, 200)
        self.token = self.client.get('/api/session').json['csrf_token']
        self.assertEqual(self.client.post('/api/customer/register',json={'username':'buyer','name':'Тест','password':'buyer-test-password'},headers={'X-CSRF-Token':self.token,'X-Requested-With':'dymok'}).status_code,200)

    def request(self, method, path, **kwargs):
        return self.client.open(path, method=method, headers={'X-CSRF-Token':self.token, 'X-Requested-With':'dymok'}, **kwargs)

    def update_product(self, price='199.99', discount='12.50', **kw):
        p = self.client.get('/api/products/1').json
        data = {'name':p['name'], 'category_id':str(p['category_id']), 'price':price,
                'discount_percentage':discount, 'attributes':json.dumps(p['attributes']),
                'brand':p['brand'], 'spec':p['spec'], 'description':'Оновлений опис'}
        data.update(kw)
        result = self.request('PUT', '/api/products/1', data=data, content_type='multipart/form-data')
        self.assertEqual(result.status_code, 200, result.data)
        return result.json

    def order(self, client=None, qty=1, pid=1):
        actual=client or self.client
        token=actual.get('/api/customer/session').json['csrf_token']
        if not actual.get('/api/customer/session').json['customer']:
            actual.post('/api/customer/login',json={'username':'buyer','password':'buyer-test-password'},headers={'X-CSRF-Token':token,'X-Requested-With':'dymok'})
        return actual.post('/api/order', json={'name':'Тест', 'phone':'+380991234567', 'tg':'@test_customer', 'age_confirmed':True,
                    'street':'Тестова', 'house':'1', 'items':[{'id':pid, 'qty':qty, 'price':0.01}]},
                    headers={'X-Requested-With':'dymok','X-CSRF-Token':token})

    def test_shared_login_both_directions_and_logout(self):
        self.assertTrue(self.client.get('/api/session').json['authenticated'])
        self.assertEqual(self.client.get('/api/products').status_code, 200)
        self.assertEqual(self.request('POST', '/api/logout').status_code, 204)
        self.assertEqual(self.client.get('/api/admin/me').status_code, 401)
        self.token = self.client.get('/api/session').json['csrf_token']
        result = self.request('POST', '/api/login', json={'username':'admin', 'password':'test-password'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.client.get('/api/admin/me').status_code, 200)
        self.request('POST', '/api/admin/logout', json={})
        self.assertEqual(self.client.get('/api/products').status_code, 401)

    def test_live_prices_discount_order_stock_and_cancellation(self):
        self.update_product()
        self.request('POST', '/api/admin/stock', json={'id':1, 'qty':5})
        p = next(p for p in self.client.get('/api/catalog').json['products'] if p['id']==1)
        self.assertEqual((p['price_cents'], p['final_price'], p['description']), (17499,'174.99','Оновлений опис'))
        result = self.order(qty=3)
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.json['total_cents'], 52497)
        self.assertEqual(result.json['stock']['1'], 2)
        self.assertEqual(result.json['items'][0]['price_cents'], 17499)
        oid = result.json['id']
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT total_cents FROM orders WHERE id=?',(oid,)).fetchone()[0],52497)
        self.assertEqual(self.order(qty=3).status_code, 409)
        for _ in range(2):
            result=self.request('POST','/api/admin/order',json={'id':oid,'status':'cancelled'})
            self.assertEqual(result.status_code,200)
            self.assertEqual(result.json['stock']['1'],5)
        self.assertEqual(self.request('POST','/api/admin/order',json={'id':oid,'status':'new'}).status_code,409)

    def test_concurrent_order_does_not_oversell(self):
        self.request('POST','/api/admin/stock',json={'id':1,'qty':1})
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.order(client=self.app.test_client()).status_code, range(2)))
        self.assertEqual(sorted(results),[201,409])
        self.assertEqual(self.client.get('/api/stock').json['stock']['1'],0)

    def test_deletion_never_reuses_ids_or_revives_seed(self):
        old=self.order().json
        self.assertEqual(self.request('DELETE','/api/products/162').status_code,204)
        self.assertEqual(self.request('DELETE','/api/products/1').status_code,204)
        self.assertEqual(self.order().status_code,400)
        p=self.client.get('/api/products/3').json
        result=self.request('POST','/api/products',data={'name':'Новий','price':'1','category_id':str(p['category_id']),
                    'attributes':json.dumps(p['attributes'])},content_type='multipart/form-data')
        self.assertEqual(result.status_code,201)
        self.assertGreater(result.json['id'],162)
        catalog_store.initialize(self.config['DATABASE'])
        self.assertEqual(self.client.get('/api/products/1').status_code,404)
        rows=self.client.get('/api/admin/orders').json['orders']
        self.assertEqual(rows[0]['items'][0]['name'],old['items'][0]['name'])

    def test_public_read_private_write_and_static_boundaries(self):
        anonymous=self.app.test_client()
        for path in ['/api/catalog','/api/catalog.js','/','/admin/','/admin/catalog/']:
            with anonymous.get(path) as response:
                self.assertEqual(response.status_code,200,path)
        for path in ['/api/products','/api/categories','/api/admin/products','/api/admin/orders']:
            self.assertEqual(anonymous.get(path).status_code,401,path)
        for path in ['/data/shop.db','/config.json','/catalog-seed.json','/catalog.py','/schema.sql','/data/session.key',
                     '/admin/../../server.py','/media/../../config.json']:
            self.assertEqual(anonymous.get(path).status_code,404,path)
        self.assertIn(b'/api/catalog.js', anonymous.get('/').data)
        self.assertNotIn(b'assets/js/01-products.js', anonymous.get('/').data)
        self.assertEqual(self.client.post('/api/order',json={}).status_code,403)
        self.assertEqual(self.client.post('/api/admin/stock',json={'id':1,'qty':1}).status_code,403)

    def test_custom_categories_and_unicode_search(self):
        response=self.request('POST','/api/categories',json={'name':'Нова категорія','attribute_schema':[{'key':'resistance','label':'Опір','required':True}]})
        category=response.json['id']
        response=self.request('POST','/api/products',data={'name':'Український пристрій','brand':'Brand','spec':'Variant',
                'price':'0.03','discount_percentage':'50','category_id':str(category),
                'attributes':'{"resistance":"0.8 Ом"}'},content_type='multipart/form-data')
        self.assertEqual(response.status_code,201)
        self.assertEqual(self.client.get('/api/products?q=УКРАЇНСЬКИЙ').json['total'],1)
        public=self.client.get('/api/catalog').json
        p=next(p for p in public['products'] if p['id']==response.json['id'])
        self.assertEqual(p['cat'],'category-'+str(category))
        self.assertEqual(p['price_cents'],2)
        self.assertEqual(p['attribute_schema'][0]['label'],'Опір')
        self.assertTrue(any(c['id']==p['cat'] for c in public['categories']))

    def test_image_preserves_legacy_url_until_replaced_or_removed(self):
        original=self.client.get('/api/products/1').json['image_url']
        self.assertTrue(original.startswith('https://'))
        self.assertEqual(self.update_product()['image_url'],original)
        self.assertIsNone(self.update_product(remove_image='1')['image_url'])
        self.assertIsNone(next(p for p in self.client.get('/api/catalog').json['products'] if p['id']==1)['image'])

    def test_restart_idempotent_and_original_catalog_complete(self):
        data=self.client.get('/api/catalog').json
        self.assertEqual(len(data['products']),161)
        seed=json.loads((Path(__file__).resolve().parents[1]/'catalog-seed.json').read_text())
        self.assertEqual({p['id'] for p in data['products']},{p['id'] for p in seed})
        self.update_product(price='7.13',discount='0')
        catalog_store.initialize(self.config['DATABASE'])
        self.assertEqual(self.client.get('/api/products/1').json['final_price'],'7.13')
        self.assertEqual(len(self.client.get('/api/catalog').json['categories']),4)
        backup=self.root/'shop-before-catalog.sqlite3'
        self.assertTrue(backup.is_file())
        con=sqlite3.connect(backup)
        self.assertIsNone(con.execute("SELECT name FROM sqlite_master WHERE name='products'").fetchone())
        con.close()

    def test_password_change_keeps_shared_auth_and_invalidates_other_session(self):
        other=self.app.test_client()
        other.post('/api/admin/login',json={'username':'admin','password':'test-password'},headers={'X-Requested-With':'dymok'})
        response=self.request('POST','/api/admin/password',json={'current':'test-password','new':'new-test-password'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(other.get('/api/products').status_code,401)
        self.assertEqual(self.client.get('/api/products').status_code,200)

class MigrationTests(unittest.TestCase):
    def test_old_order_and_stock_survive_migration_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            database=Path(directory)/'legacy.db'
            original=server.DB_PATH
            try:
                server.DB_PATH=database
                server.init_db()
                server.set_admin('legacy-admin','legacy-password')
                con=server.db()
                con.execute('INSERT INTO stock VALUES(1,7,123)')
                con.execute('''INSERT INTO orders(created,name,phone,phone_digits,address,items_json,total)
                               VALUES(123,'Historic','0000000000','0000000000','Example','[]',12.34)''')
                original_admin=tuple(con.execute('SELECT * FROM admin').fetchone())
                con.close()
                catalog_store.initialize(database)
                catalog_store.initialize(database)
                con=server.db()
                self.assertEqual(tuple(con.execute('SELECT * FROM admin').fetchone()),original_admin)
                self.assertEqual(con.execute('SELECT qty FROM stock WHERE product_id=1').fetchone()[0],7)
                self.assertEqual(con.execute('SELECT total_cents FROM orders').fetchone()[0],1234)
                self.assertEqual(con.execute('SELECT COUNT(*) FROM products').fetchone()[0],161)
                self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(),[])
                con.close()
                backup=sqlite3.connect(Path(directory)/'legacy-before-catalog.sqlite3')
                self.assertEqual(backup.execute('SELECT qty FROM stock WHERE product_id=1').fetchone()[0],7)
                self.assertEqual(backup.execute('SELECT total FROM orders').fetchone()[0],12.34)
                self.assertNotIn('total_cents',{r[1] for r in backup.execute('PRAGMA table_info(orders)')})
                backup.close()
            finally:
                server.DB_PATH=original


if __name__=='__main__':
    unittest.main()
