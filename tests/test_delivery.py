import concurrent.futures
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
import delivery
from catalog import create_app


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.database=Path(self.tmp.name)/'shop.db'
        self.app=create_app({'TESTING':True,'SECRET_KEY':'delivery-test-only','DATABASE':str(self.database),
                             'UPLOAD_FOLDER':str(Path(self.tmp.name)/'media')})
        server._hits.clear();server.set_admin('owner','owner-test-password')
        self.owner=self.app.test_client()
        self.buyer=self.app.test_client()
        self.assertEqual(self.send(self.buyer,'/api/customer/register',{'username':'testbuyer','name':'Покупець','password':'buyer-test-password'}).status_code,200)
        self.assertEqual(self.owner.post('/api/admin/login',json={'username':'owner','password':'owner-test-password'},headers={'X-Requested-With':'dymok'}).status_code,200)

    def send(self,client,path,data):
        token=client.get('/api/delivery/session').json['csrf_token']
        return client.post(path,json=data,headers={'X-Requested-With':'dymok','X-CSRF-Token':token})

    def payload(self,**changes):
        value={'name':'Покупець','phone':'+380991234567','tg':'@customer_1','street':'Соборна','house':'12',
               'items':[{'id':1,'qty':1}],'age_confirmed':True,'pay':delivery.CASH}
        value.update(changes);return value

    def order(self,**changes):
        response=self.send(self.buyer,'/api/order',self.payload(**changes))
        self.assertEqual(response.status_code,201,response.json)
        return response.json

    def status(self,oid,status,**extra):
        return self.send(self.owner,'/api/admin/order',{'id':oid,'status':status,**extra})

    def ready(self,**changes):
        o=self.order(**changes)
        for status in ['confirmed','ready']:
            self.assertEqual(self.status(o['id'],status).status_code,200)
        return o

    def make_courier(self,username='runner',ready=True,limit=3):
        r=self.send(self.owner,'/api/admin/couriers',{'name':username,'username':username,'phone':'+380991234568',
                    'password':'temporary-password','tg':'@courier_'+username,'max_active':limit})
        self.assertEqual(r.status_code,200,r.json);cid=r.json['courier']['id']
        c=self.app.test_client();r=self.send(c,'/api/courier/login',{'username':username,'password':'temporary-password'})
        self.assertEqual(r.status_code,200,r.json)
        if ready:
            self.assertEqual(self.send(c,'/api/courier/password',{'current':'temporary-password','new':'personal-password'}).status_code,200)
            self.assertEqual(self.send(c,'/api/courier/shift',{'on_shift':True}).status_code,200)
        return cid,c

    def claim(self,c,o):
        return self.send(c,f'/api/courier/orders/{o["id"]}/claim',{})

    def move(self,c,o,status,**kw):
        return self.send(c,f'/api/courier/orders/{o["id"]}/status',{'status':status,**kw})

    def test_phone_tg_age_required_on_server(self):
        c=self.buyer
        for value in [self.payload(phone=''),self.payload(phone='abcdefghijk'),self.payload(tg=''),self.payload(tg='@x'),self.payload(age_confirmed=False),self.payload(tg=['bad'])]:
            with self.subTest(payload=value):
                self.assertEqual(self.send(c,'/api/order',value).status_code,400)
        with delivery.connection() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM orders').fetchone()[0],0)

    def test_short_collectible_contact_names_are_not_rejected(self):
        self.assertEqual(self.order(tg='@abcd')['id'],1)
        self.assertEqual(self.order(tg='@8888')['id'],2)

    def test_concurrent_claims_respect_one_courier_capacity(self):
        cid,a=self.make_courier(limit=1)
        b=self.app.test_client()
        self.assertEqual(self.send(b,'/api/courier/login',{'username':'runner','password':'personal-password'}).status_code,200)
        first=self.ready();second=self.ready()
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda pair:self.claim(*pair).status_code,[(a,first),(b,second)]))
        self.assertEqual(sorted(results),[200,409])

    def test_replay_exactly_once_stock_and_concurrent_replay(self):
        self.send(self.owner,'/api/admin/stock',{'id':1,'qty':1})
        p=self.payload(request_id='same-request-123456789')
        def send(_):return self.send(self.buyer,'/api/order',p)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:rs=list(pool.map(send,range(2)))
        self.assertEqual([r.status_code for r in rs],[201,201])
        self.assertEqual(rs[0].json['id'],rs[1].json['id'])
        self.assertEqual(self.owner.get('/api/stock').json['stock']['1'],0)
        p['house']='13';self.assertEqual(self.send(self.buyer,'/api/order',p).status_code,409)
        with delivery.connection() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM orders').fetchone()[0],1)

    def test_temporary_password_gate_and_case_insensitive_login(self):
        cid,c=self.make_courier(ready=False)
        self.assertEqual(c.get('/api/courier/orders').status_code,403)
        self.assertEqual(self.send(c,'/api/courier/shift',{'on_shift':True}).status_code,403)
        self.assertEqual(self.send(c,'/api/courier/password',{'current':'temporary-password','new':'temporary-password'}).status_code,400)
        self.assertEqual(self.send(c,'/api/courier/password',{'current':'temporary-password','new':'personal-password'}).status_code,200)
        self.assertEqual(self.send(self.app.test_client(),'/api/courier/login',{'username':'RUNNER','password':'personal-password'}).status_code,200)

    def test_role_isolation_csrf_and_unlisted_static(self):
        cid,c=self.make_courier()
        for path in ['/api/admin/orders','/api/admin/couriers','/api/admin/delivery/settings','/api/admin/delivery/events','/api/admin/delivery/reports','/api/products']:
            self.assertEqual(c.get(path).status_code,401,path)
        self.assertEqual(self.owner.get('/api/courier/orders').status_code,401)
        self.assertEqual(c.post('/api/courier/shift',json={'on_shift':False},headers={'X-Requested-With':'dymok'}).status_code,403)
        token=c.get('/api/delivery/session').json['csrf_token']
        self.assertEqual(c.post('/api/courier/shift',json={'on_shift':False},headers={'X-CSRF-Token':token}).status_code,403)
        for path in ['/courier/../../delivery.py','/admin/delivery/../../delivery.py','/delivery.py','/data/shop-before-delivery.sqlite3','/data/session.key']:
            self.assertEqual(c.get(path).status_code,404,path)

    def test_available_redacted_claim_exclusivity_and_history_redacted(self):
        _,a=self.make_courier('first');_,b=self.make_courier('second');o=self.ready()
        summary=a.get('/api/courier/orders').json['orders'][0]
        for key in ['phone','tg','name','address','items','tracking_token','request_hash','note']:
            self.assertNotIn(key,summary)
        self.assertEqual(a.get(f'/api/courier/orders/{o["id"]}').status_code,404)
        self.assertEqual(self.claim(a,o).status_code,200)
        self.assertEqual(b.get('/api/courier/orders').json['orders'],[])
        self.assertEqual(self.claim(b,o).status_code,409)
        self.assertEqual(b.get(f'/api/courier/orders/{o["id"]}').status_code,404)
        self.assertEqual(a.get(f'/api/courier/orders/{o["id"]}').json['phone'],'+380991234567')
        self.assertEqual(self.move(a,o,'delivering').status_code,200)
        self.assertEqual(self.move(a,o,'done',cash_received_cents=o['total_cents']).status_code,200)
        self.assertEqual(a.get(f'/api/courier/orders/{o["id"]}').status_code,404)
        summary=a.get('/api/courier/orders?view=history').json['orders'][0]
        self.assertNotIn('phone',summary);self.assertNotIn('address',summary)

    def test_two_couriers_concurrent_claim(self):
        _,a=self.make_courier('first');_,b=self.make_courier('second');o=self.ready()
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda c:self.claim(c,o).status_code,[a,b]))
        self.assertEqual(sorted(results),[200,409])
        with delivery.connection() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM delivery_events WHERE action='claimed'").fetchone()[0],1)

    def test_shift_limits_and_only_ready_orders(self):
        cid,c=self.make_courier(limit=1);a=self.ready();b=self.ready();n=self.order()
        self.assertEqual(self.claim(c,n).status_code,409)
        self.send(c,'/api/courier/shift',{'on_shift':False})
        self.assertEqual(c.get('/api/courier/orders').json['orders'],[])
        self.assertEqual(self.claim(c,a).status_code,409)
        self.send(c,'/api/courier/shift',{'on_shift':True})
        self.assertEqual(self.claim(c,a).status_code,200)
        self.assertEqual(self.claim(c,b).status_code,409)
        self.assertEqual(self.send(self.owner,f'/api/admin/delivery/orders/{b["id"]}/assign',{'courier_id':cid}).status_code,409)

    def test_problem_release_and_reassignment_revokes_details(self):
        aid,a=self.make_courier('first');bid,b=self.make_courier('second');o=self.ready();self.claim(a,o)
        self.assertEqual(self.move(a,o,'release_requested',note='').status_code,400)
        self.assertEqual(self.move(a,o,'release_requested',note='Проблема з транспортом').status_code,200)
        self.assertEqual(b.get('/api/courier/orders').json['orders'],[])
        self.assertEqual(self.send(self.owner,f'/api/admin/delivery/orders/{o["id"]}/assign',{'courier_id':bid}).status_code,400)
        r=self.send(self.owner,f'/api/admin/delivery/orders/{o["id"]}/assign',{'courier_id':bid,'reason':'Погоджено передачу'})
        self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(a.get(f'/api/courier/orders/{o["id"]}').status_code,404)
        self.assertEqual(b.get(f'/api/courier/orders/{o["id"]}').status_code,200)

    def test_deactivate_revokes_sessions_and_returns_active_orders_atomically(self):
        cid,c=self.make_courier();a=self.ready();b=self.ready();self.claim(c,a);self.claim(c,b)
        self.assertEqual(self.send(self.owner,f'/api/admin/couriers/{cid}/active',{'active':False}).status_code,409)
        self.assertEqual(c.get('/api/courier/orders?view=mine').status_code,200)
        r=self.send(self.owner,f'/api/admin/couriers/{cid}/active',{'active':False,'release_active':True,'reason':'Передача товару погоджена'})
        self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(c.get('/api/courier/orders?view=mine').status_code,401)
        with delivery.connection() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM orders WHERE status='ready' AND courier_id IS NULL").fetchone()[0],2)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM courier_sessions WHERE courier_id=?',(cid,)).fetchone()[0],0)
        self.send(self.owner,f'/api/admin/couriers/{cid}/active',{'active':True})
        self.assertEqual(c.get('/api/courier/orders').status_code,401)

    def test_reset_password_ends_sessions_and_forces_change(self):
        cid,c=self.make_courier()
        r=self.send(self.owner,f'/api/admin/couriers/{cid}',{'name':'Runner','username':'runner','phone':'+380991234568','password':'new-temporary-password','max_active':3})
        self.assertEqual(r.status_code,200)
        self.assertEqual(c.get('/api/courier/orders').status_code,401)
        self.assertEqual(self.send(c,'/api/courier/login',{'username':'runner','password':'personal-password'}).status_code,401)
        self.assertEqual(self.send(c,'/api/courier/login',{'username':'runner','password':'new-temporary-password'}).status_code,200)
        self.assertEqual(c.get('/api/courier/orders').status_code,403)

    def test_cash_collection_handover_replay_and_archival(self):
        cid,c=self.make_courier();o=self.ready();self.claim(c,o);self.move(c,o,'delivering')
        self.assertEqual(self.move(c,o,'done',cash_received_cents=0).status_code,409)
        self.assertEqual(self.move(c,o,'done',cash_received_cents=o['total_cents']).status_code,200)
        self.assertEqual(self.move(c,o,'done',cash_received_cents=o['total_cents']).status_code,409)
        self.assertEqual(self.status(o['id'],'cancelled').status_code,409)
        amount=f'{o["total_cents"]/100:.2f}';data={'courier_id':cid,'amount':amount,'reference':'handover-1'}
        for _ in range(2):self.assertEqual(self.send(self.owner,'/api/admin/delivery/cash',data).status_code,200)
        self.assertEqual(self.send(self.owner,'/api/admin/delivery/cash',{**data,'reference':'handover-2'}).status_code,409)
        self.assertEqual(self.send(self.owner,'/api/admin/order-delete',{'id':o['id']}).status_code,200)
        report=self.owner.get('/api/admin/delivery/reports').json
        self.assertEqual(report['summary']['delivered'],1)
        self.assertEqual(report['couriers'][0]['cash_balance_cents'],0)
        self.assertEqual(len(report['cash']),2)
        self.assertEqual(self.owner.get('/api/admin/orders?status=archived').json['orders'][0]['id'],o['id'])

    def test_bank_transfer_not_counted_as_cash(self):
        cid,c=self.make_courier();o=self.ready(pay=delivery.CARD);self.claim(c,o);self.move(c,o,'delivering')
        self.assertEqual(self.move(c,o,'done').status_code,200)
        self.assertEqual(c.get('/api/courier/orders').json['cash_balance_cents'],0)

    def zone_config(self,**kw):
        r=self.owner.get('/api/admin/delivery/settings').json;zone=r['zones'][0]
        z={'id':zone['id'],'name':'Центр','active':True,'fee':'50','minimum':'0','free_from':'','reward':'30'};z.update(kw)
        return {'settings':r['settings'],'zones':[z]}

    def test_delivery_tariff_snapshots_and_server_money(self):
        self.assertEqual(self.send(self.owner,'/api/admin/delivery/settings',self.zone_config()).status_code,200)
        o=self.order();self.assertEqual(o['delivery_fee_cents'],5000)
        self.assertEqual(o['total_cents'],o['subtotal_cents']+5000)
        self.assertEqual(self.send(self.owner,'/api/admin/delivery/settings',self.zone_config(fee='90',reward='40')).status_code,200)
        stored=self.owner.get('/api/admin/orders').json['orders'][0]
        self.assertEqual(stored['delivery_fee_cents'],5000);self.assertEqual(stored['reward_cents'],3000)
        self.assertEqual(self.order()['delivery_fee_cents'],9000)

    def test_minimum_free_delivery_closure_and_rollback_stock(self):
        self.send(self.owner,'/api/admin/stock',{'id':1,'qty':5})
        cfg=self.zone_config(minimum='99999');self.send(self.owner,'/api/admin/delivery/settings',cfg)
        self.assertEqual(self.send(self.buyer,'/api/order',self.payload()).status_code,409)
        self.assertEqual(self.owner.get('/api/stock').json['stock']['1'],5)
        cfg=self.zone_config(free_from='1');self.send(self.owner,'/api/admin/delivery/settings',cfg)
        self.assertEqual(self.order()['delivery_fee_cents'],0)
        cfg=self.zone_config();cfg['settings']['accepting']=False;self.send(self.owner,'/api/admin/delivery/settings',cfg)
        self.assertFalse(self.owner.get('/api/delivery/options').json['accepting'])
        self.assertEqual(self.send(self.buyer,'/api/order',self.payload()).status_code,409)

    def test_settings_conflict_and_invalid_zone_do_not_partial_save(self):
        cfg=self.zone_config();self.assertEqual(self.send(self.owner,'/api/admin/delivery/settings',cfg).status_code,200)
        self.assertEqual(self.send(self.owner,'/api/admin/delivery/settings',cfg).status_code,409)
        cfg=self.zone_config(fee='12.345');self.assertEqual(self.send(self.owner,'/api/admin/delivery/settings',cfg).status_code,400)
        self.assertEqual(self.owner.get('/api/admin/delivery/settings').json['zones'][0]['fee_cents'],5000)

    def test_tracking_secret_and_no_personal_data(self):
        o=self.order();path='/api/order-status?id='+str(o['id'])
        self.assertEqual(self.owner.get(path+'&phone=380991234567').status_code,404)
        self.assertEqual(self.owner.get(path,headers={'X-Order-Token':'incorrect'}).status_code,404)
        result=self.owner.get(path,headers={'X-Order-Token':o['tracking_token']})
        self.assertEqual(result.status_code,200)
        for k in ['phone','tg','address','name','courier_note','tracking_token']:
            self.assertNotIn(k,result.json)

    def test_optimistic_version_blocks_stale_admin(self):
        o=self.ready();r=self.owner.get('/api/admin/orders').json['orders'][0]
        self.assertEqual(self.status(o['id'],'ready',version=r['version'],manager_note='Актуальне').status_code,200)
        self.assertEqual(self.status(o['id'],'cancelled',version=r['version']).status_code,409)
        self.assertEqual(self.owner.get('/api/admin/orders').json['orders'][0]['manager_note'],'Актуальне')

    def test_delivery_migration_backup_and_repeat(self):
        o=self.order();delivery.initialize(self.database);delivery.initialize(self.database)
        with delivery.connection() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM orders').fetchone()[0],1)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM delivery_zones').fetchone()[0],1)
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(),[])
        backup=sqlite3.connect(Path(self.tmp.name)/'shop-before-delivery.sqlite3')
        try:self.assertNotIn('courier_id',{r[1] for r in backup.execute('PRAGMA table_info(orders)')})
        finally:backup.close()

    def test_day_and_overnight_opening_hours(self):
        cfg={**delivery.DEFAULTS,'hours_enabled':True,'closed_days':[6]}
        def now(v):return datetime.fromisoformat(v).replace(tzinfo=ZoneInfo('Europe/Kyiv'))
        self.assertTrue(delivery.accepting(cfg,now('2026-11-09T10:00:00')))
        self.assertFalse(delivery.accepting(cfg,now('2026-11-09T20:00:00')))
        cfg.update(opens='20:00',closes='03:00')
        self.assertTrue(delivery.accepting(cfg,now('2026-11-08T02:00:00')))
        self.assertFalse(delivery.accepting(cfg,now('2026-11-09T02:00:00')))
        self.assertFalse(delivery.accepting(cfg,now('2026-11-09T12:00:00')))


class MaintenanceTests(unittest.TestCase):
    def test_backup_can_be_restored_to_independent_sqlite(self):
        import maintenance
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);db=root/'dymok.db';con=sqlite3.connect(db)
            con.execute('CREATE TABLE orders(id INTEGER PRIMARY KEY,value TEXT)');con.execute("INSERT INTO orders VALUES(1,'kept')");con.commit();con.close()
            (root/'media').mkdir();(root/'media/example.webp').write_bytes(b'image-test')
            (root/'session.key').write_text('test-only-session-key')
            archive=maintenance.backup(db,root/'backup.zip')
            self.assertEqual(maintenance.verify(archive),1)
            import zipfile
            with zipfile.ZipFile(archive) as z:
                restored=root/'restored.db';restored.write_bytes(z.read('data/dymok.db'))
                self.assertEqual(z.read('data/media/example.webp'),b'image-test')
                self.assertEqual(z.read('data/session.key'),b'test-only-session-key')
            con=sqlite3.connect(restored)
            self.assertEqual(con.execute('SELECT value FROM orders').fetchone()[0],'kept');con.close()

    def test_update_preserves_data_configuration_and_key(self):
        import update_site
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'installed';target.mkdir();(target/'data').mkdir();(target/'data/media').mkdir()
            (target/'server.py').write_text('# old code')
            (target/'config.json').write_text('{"local_setting":"preserve"}')
            (target/'data/session.key').write_text('existing-local-key')
            con=sqlite3.connect(target/'data/dymok.db');con.execute('CREATE TABLE keep_this(id INTEGER)');con.execute('INSERT INTO keep_this VALUES(42)');con.commit();con.close()
            with self.assertRaises(ValueError):update_site.update(target)
            snapshot,code=update_site.update(target,True)
            self.assertTrue(snapshot.exists());self.assertTrue(code.exists())
            self.assertTrue((target/'delivery.py').is_file())
            self.assertEqual((target/'data/session.key').read_text(),'existing-local-key')
            self.assertEqual(json.loads((target/'config.json').read_text()),{'local_setting':'preserve'})
            con=sqlite3.connect(target/'data/dymok.db');self.assertEqual(con.execute('SELECT * FROM keep_this').fetchone()[0],42);con.close()

if __name__=='__main__':unittest.main()
