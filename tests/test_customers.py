import concurrent.futures
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server,delivery,customers,catalog_store
import test_delivery as helpers


class CustomerTests(unittest.TestCase):
    setUp=helpers.DeliveryTests.setUp
    send=helpers.DeliveryTests.send
    payload=helpers.DeliveryTests.payload
    order=helpers.DeliveryTests.order
    status=helpers.DeliveryTests.status
    ready=helpers.DeliveryTests.ready
    make_courier=helpers.DeliveryTests.make_courier
    claim=helpers.DeliveryTests.claim
    move=helpers.DeliveryTests.move

    def register(self,username='another',password='customer-password',name='Інший покупець'):
        c=self.app.test_client();r=self.send(c,'/api/customer/register',{'username':username,'password':password,'name':name})
        self.assertEqual(r.status_code,200,r.json);return c,r.json['customer']

    def test_registration_is_server_backed_and_password_is_hashed(self):
        c,user=self.register(password='  Пароль-покупця-123  ')
        self.assertEqual(user['phone'],'');self.assertEqual(user['tg'],'')
        with delivery.connection() as con:
            row=con.execute('SELECT * FROM customers WHERE id=?',(user['id'],)).fetchone()
            self.assertNotEqual(row['hash'],'  Пароль-покупця-123  '.encode())
            self.assertEqual(row['hash'],server.hash_pw('  Пароль-покупця-123  ',row['salt'],row['iters']))
        response=c.get('/api/customer/session')
        self.assertEqual(response.json['customer']['id'],user['id'])
        self.assertNotIn('hash',response.json['customer']);self.assertNotIn('salt',response.json['customer'])
        new=self.app.test_client()
        self.assertEqual(self.send(new,'/api/customer/login',{'username':'ANOTHER','password':'  Пароль-покупця-123  '}).status_code,200)

    def test_registration_validates_name_login_password_and_duplicate_case(self):
        c=self.app.test_client()
        for changes in [{'name':''},{'username':'x'},{'username':'bad username'},{'password':'short'},{'username':None},{'name':['x']}]:
            data={'username':'valid_name','password':'valid-password','name':'Покупець',**changes}
            self.assertEqual(self.send(c,'/api/customer/register',data).status_code,400)
        self.assertEqual(self.send(c,'/api/customer/register',{'username':'TESTBUYER','password':'other-password','name':'Other'}).status_code,409)

    def test_login_checks_password_and_does_not_create_an_account(self):
        c=self.app.test_client()
        bad=self.send(c,'/api/customer/login',{'username':'testbuyer','password':'wrong-password'})
        absent=self.send(c,'/api/customer/login',{'username':'absent','password':'wrong-password'})
        self.assertEqual((bad.status_code,absent.status_code),(401,401));self.assertEqual(bad.json,absent.json)
        self.assertIsNone(c.get('/api/customer/session').json['customer'])
        forged=self.app.test_client();forged.set_cookie('dymok_customer','not-a-valid-session')
        self.assertEqual(forged.get('/api/customer/orders').status_code,401)
        self.assertEqual(self.send(c,'/api/customer/login',{'username':'TESTBUYER','password':'buyer-test-password'}).status_code,200)

    def test_checkout_requires_login_and_derives_name_and_owner_on_server(self):
        anonymous=self.app.test_client()
        self.assertEqual(self.send(anonymous,'/api/order',self.payload()).status_code,401)
        o=self.order(name='Підмінене ім’я',customer_id=999)
        row=self.buyer.get('/api/customer/orders/'+str(o['id'])).json
        self.assertEqual(row['name'],'Покупець');self.assertTrue(row['owned'])
        self.assertEqual(self.buyer.get('/api/customer/session').json['customer']['phone'],'+380991234567')
        self.assertEqual(self.buyer.get('/api/customer/session').json['customer']['address']['house'],'12')

    def test_orders_persist_across_devices_and_logout_invalidates_only_current_device(self):
        o=self.order();second=self.app.test_client()
        self.assertEqual(self.send(second,'/api/customer/login',{'username':'testbuyer','password':'buyer-test-password'}).status_code,200)
        self.assertEqual(second.get('/api/customer/orders').json['orders'][0]['id'],o['id'])
        self.assertEqual(self.send(self.buyer,'/api/customer/logout',{}).status_code,200)
        self.assertEqual(self.buyer.get('/api/customer/orders').status_code,401)
        self.assertEqual(second.get('/api/customer/orders').status_code,200)
        self.assertIsNone(self.buyer.get('/api/customer/session').json['customer'])

    def test_other_customer_cannot_read_hide_or_claim_orders(self):
        o=self.order();other,_=self.register()
        self.assertEqual(other.get('/api/customer/orders').json['orders'],[])
        self.assertEqual(other.get(f'/api/customer/orders/{o["id"]}').status_code,404)
        self.assertEqual(self.send(other,f'/api/customer/orders/{o["id"]}/hide',{}).status_code,404)
        self.assertEqual(other.get('/api/order-status?id='+str(o['id'])).status_code,404)
        response=other.get('/api/order-status?id='+str(o['id']),headers={'X-Order-Token':o['tracking_token']})
        self.assertEqual(response.status_code,200)
        for key in ['name','phone','tg','address','items','courier','customer_id']:self.assertNotIn(key,response.json)
        attempt=self.send(other,'/api/customer/orders/import',{'receipts':[{'id':o['id'],'token':o['tracking_token']}]})
        self.assertEqual(attempt.json['imported_ids'],[])

    def test_hide_only_delivered_and_preserves_stock_cash_admin_history(self):
        self.send(self.owner,'/api/admin/stock',{'id':1,'qty':10})
        o=self.ready();cid,c=self.make_courier();self.claim(c,o)
        self.assertEqual(self.send(self.buyer,f'/api/customer/orders/{o["id"]}/hide',{}).status_code,409)
        self.move(c,o,'delivering');self.move(c,o,'done',cash_received_cents=o['total_cents'])
        for _ in range(2):self.assertEqual(self.send(self.buyer,f'/api/customer/orders/{o["id"]}/hide',{}).status_code,200)
        self.assertEqual(self.buyer.get('/api/customer/orders').json['orders'],[])
        self.assertEqual(self.buyer.get('/api/customer/orders').json['counts']['delivered'],0)
        self.assertEqual(self.owner.get('/api/admin/orders?status=done').json['orders'][0]['id'],o['id'])
        self.assertEqual(self.owner.get('/api/stock').json['stock']['1'],9)
        self.assertEqual(c.get('/api/courier/orders?view=history').json['orders'][0]['id'],o['id'])
        self.assertEqual(self.owner.get('/api/admin/delivery/reports').json['couriers'][0]['cash_balance_cents'],o['total_cents'])
        with delivery.connection() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM delivery_events WHERE action='customer_order_hidden'").fetchone()[0],1)

    def test_cancelled_order_cannot_be_hidden_as_delivered(self):
        o=self.order();self.status(o['id'],'cancelled')
        self.assertEqual(self.send(self.buyer,f'/api/customer/orders/{o["id"]}/hide',{}).status_code,409)

    def test_customer_and_courier_see_telegram_only_for_assignment(self):
        a_id,a=self.make_courier('first');b_id,b=self.make_courier('second');o=self.ready()
        self.assertIsNone(self.buyer.get(f'/api/customer/orders/{o["id"]}').json['courier'])
        self.claim(a,o)
        self.assertEqual(self.buyer.get(f'/api/customer/orders/{o["id"]}').json['courier']['tg'],'@courier_first')
        self.assertEqual(a.get(f'/api/courier/orders/{o["id"]}').json['tg'],'@customer_1')
        self.assertEqual(b.get(f'/api/courier/orders/{o["id"]}').status_code,404)
        self.assertEqual(self.send(a,'/api/courier/profile',{'tg':'@updated_courier'}).status_code,200)
        self.assertEqual(self.buyer.get(f'/api/customer/orders/{o["id"]}').json['courier']['tg'],'@updated_courier')
        self.assertEqual(self.send(self.owner,f'/api/admin/delivery/orders/{o["id"]}/assign',{'courier_id':b_id,'reason':'Передано іншому'}).status_code,200)
        self.assertEqual(self.buyer.get(f'/api/customer/orders/{o["id"]}').json['courier']['tg'],'@courier_second')
        self.assertEqual(a.get(f'/api/courier/orders/{o["id"]}').status_code,404)
        self.move(b,o,'delivering');self.move(b,o,'done',cash_received_cents=o['total_cents'])
        self.assertIsNone(self.buyer.get(f'/api/customer/orders/{o["id"]}').json['courier'])

    def test_shared_tracking_link_does_not_expose_contacts_or_service_notes(self):
        _,c=self.make_courier();o=self.ready();self.claim(c,o)
        self.move(c,o,'problem',note='PRIVATE-COURIER-NOTE')
        guest=self.app.test_client();response=guest.get('/api/order-status?id='+str(o['id']),headers={'X-Order-Token':o['tracking_token']})
        self.assertEqual(response.status_code,200)
        self.assertNotIn('courier',response.json);self.assertNotIn('PRIVATE-COURIER-NOTE',response.get_data(as_text=True))
        own=self.buyer.get('/api/order-status?id='+str(o['id'])).json
        self.assertTrue(own['owned']);self.assertIn('courier',own)
        self.assertNotIn('PRIVATE-COURIER-NOTE',json.dumps(own))

    def test_password_change_revokes_other_devices_and_old_password(self):
        other=self.app.test_client();self.send(other,'/api/customer/login',{'username':'testbuyer','password':'buyer-test-password'})
        self.assertEqual(self.send(self.buyer,'/api/customer/password',{'current':'wrong-password','new':'new-customer-password'}).status_code,403)
        self.assertEqual(self.send(self.buyer,'/api/customer/password',{'current':'buyer-test-password','new':'new-customer-password'}).status_code,200)
        self.assertEqual(other.get('/api/customer/orders').status_code,401)
        self.assertEqual(self.buyer.get('/api/customer/orders').status_code,200)
        self.assertEqual(self.send(other,'/api/customer/login',{'username':'testbuyer','password':'buyer-test-password'}).status_code,401)
        self.assertEqual(self.send(other,'/api/customer/login',{'username':'testbuyer','password':'new-customer-password'}).status_code,200)

    def test_expired_session_and_other_roles_are_not_customer_login(self):
        with delivery.connection(True) as con:con.execute('UPDATE customer_sessions SET expires=0')
        self.assertIsNone(self.buyer.get('/api/customer/session').json['customer'])
        self.assertEqual(self.send(self.buyer,'/api/order',self.payload()).status_code,401)
        self.assertEqual(self.owner.get('/api/customer/orders').status_code,401)
        _,courier=self.make_courier()
        self.assertEqual(courier.get('/api/customer/orders').status_code,401)
        self.assertEqual(self.buyer.get('/api/admin/couriers').status_code,401)
        self.assertEqual(self.buyer.get('/api/courier/orders').status_code,401)

    def test_idempotency_key_cannot_replay_another_customers_order(self):
        key='customer-replay-test-12345';self.order(request_id=key)
        other,_=self.register();response=self.send(other,'/api/order',self.payload(request_id=key))
        self.assertEqual(response.status_code,409)
        self.assertNotIn('tracking_token',response.json)
        self.assertEqual(other.get('/api/customer/orders').json['orders'],[])

    def test_legacy_import_requires_receipt_and_never_uses_phone_as_ownership(self):
        o=self.order()
        with delivery.connection(True) as con:con.execute('UPDATE orders SET customer_id=NULL WHERE id=?',(o['id'],))
        other,user=self.register()
        for receipt in [{'id':o['id'],'phone':'+380991234567'},{'id':o['id'],'token':'wrong'}]:
            self.assertEqual(self.send(other,'/api/customer/orders/import',{'receipts':[receipt]}).json['imported_ids'],[])
        self.assertEqual(self.send(other,'/api/customer/orders/import',{'receipts':[{'id':o['id'],'token':o['tracking_token']}]}).json['imported_ids'],[o['id']])
        self.assertEqual(other.get(f'/api/customer/orders/{o["id"]}').status_code,200)
        self.assertEqual(self.buyer.get(f'/api/customer/orders/{o["id"]}').status_code,404)
        self.assertEqual(self.send(self.buyer,'/api/customer/orders/import',{'receipts':[{'id':o['id'],'token':o['tracking_token']}]}).json['imported_ids'],[])

    def test_csrf_is_required_for_checkout_registration_and_history(self):
        o=self.order()
        for path,payload in [('/api/order',self.payload()),('/api/customer/register',{'username':'fake','name':'fake','password':'valid-password'}),(f'/api/customer/orders/{o["id"]}/hide',{})]:
            self.assertEqual(self.buyer.post(path,json=payload,headers={'X-Requested-With':'dymok'}).status_code,403)

    def test_concurrent_duplicate_registration_creates_one_identity(self):
        def reg(_):return self.send(self.app.test_client(),'/api/customer/register',{'username':'same_name','name':'Same','password':'same-test-password'}).status_code
        with concurrent.futures.ThreadPoolExecutor(2) as pool:results=list(pool.map(reg,range(2)))
        self.assertEqual(sorted(results),[200,409])
        with delivery.connection() as con:self.assertEqual(con.execute("SELECT COUNT(*) FROM customers WHERE username='same_name'").fetchone()[0],1)

    def test_customer_migration_preserves_v1_orders_accounts_and_backup(self):
        old=server.DB_PATH
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'legacy.db'
            try:
                server.DB_PATH=path;server.init_db();catalog_store.initialize(path);delivery.initialize(path)
                con=sqlite3.connect(path)
                con.execute("INSERT INTO orders(created,name,phone,phone_digits,address,items_json,total,total_cents) VALUES(1,'Historic','0000000000','0000000000','Example','[]',12,1200)")
                salt=b'x'*16;pw=server.hash_pw('legacy-courier-password',salt)
                con.execute("INSERT INTO couriers(username,name,phone,salt,hash,iters,created) VALUES('legacy','Legacy','0000000000',?,?,?,1)",(salt,pw,server.PBKDF2_ITERS));con.commit();con.close()
                customers.initialize(path);customers.initialize(path)
                con=sqlite3.connect(path)
                self.assertEqual(con.execute('SELECT hash FROM couriers').fetchone()[0],pw)
                self.assertEqual(con.execute('SELECT tg FROM couriers').fetchone()[0],'')
                self.assertEqual(con.execute('SELECT total_cents,customer_id FROM orders').fetchone(),(1200,None))
                self.assertEqual(con.execute('SELECT COUNT(*) FROM customers').fetchone()[0],0)
                self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(),[]);con.close()
                backup=sqlite3.connect(Path(folder)/'legacy-before-customers.sqlite3')
                self.assertNotIn('customer_id',{r[1] for r in backup.execute('PRAGMA table_info(orders)')});backup.close()
            finally:server.DB_PATH=old

    def test_history_pagination_and_profile_edit_do_not_rewrite_orders(self):
        first=self.order();second=self.order();third=self.order()
        result=self.buyer.get('/api/customer/orders?limit=2').json
        self.assertEqual([r['id'] for r in result['orders']],[third['id'],second['id']])
        next_page=self.buyer.get('/api/customer/orders?limit=2&before='+str(result['next_before'])).json
        self.assertEqual([r['id'] for r in next_page['orders']],[first['id']])
        self.assertEqual(self.send(self.buyer,'/api/customer/profile',{'name':'Нове ім’я'}).status_code,200)
        self.assertEqual(self.buyer.get('/api/customer/session').json['customer']['name'],'Нове ім’я')
        self.assertEqual(self.buyer.get('/api/customer/orders/'+str(first['id'])).json['name'],'Покупець')

if __name__=='__main__':unittest.main()
