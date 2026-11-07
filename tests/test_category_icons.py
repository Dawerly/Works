import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import catalog_store
import test_catalog as helpers


class CategoryIconTests(unittest.TestCase):
    setUp=helpers.CatalogTests.setUp
    request=helpers.CatalogTests.request

    def test_custom_icon_saved_edited_and_survives_restart(self):
        result=self.request('POST','/api/categories',json={'name':'Комплектуючі','icon':'🔧','attribute_schema':[]})
        self.assertEqual(result.status_code,201,result.json);cid=result.json['id']
        self.assertEqual(result.json['icon'],'🔧')
        update=self.request('PUT',f'/api/categories/{cid}',json={'name':'Комплектуючі','icon':'🧩','attribute_schema':[]})
        self.assertEqual(update.json['icon'],'🧩')
        update=self.request('PUT',f'/api/categories/{cid}',json={'name':'Комплектуючі до рідини','attribute_schema':[]})
        self.assertEqual(update.json['icon'],'🧩')
        catalog_store.initialize(self.app.config['DATABASE'],seed=False)
        self.assertEqual(self.client.get(f'/api/categories/{cid}').json['icon'],'🧩')
        public=next(c for c in self.client.get('/api/catalog').json['categories'] if c['id']=='category-'+str(cid))
        self.assertEqual(public['icon'],'🧩')

    def test_unicode_emoji_sequences_and_empty_default(self):
        for i,icon in enumerate(['🧑🏽‍💻','🇺🇦','1️⃣','❤️','⚙️','']):
            result=self.request('POST','/api/categories',json={'name':'Emoji '+str(i),'icon':icon,'attribute_schema':[]})
            self.assertEqual(result.status_code,201,result.json)
            self.assertEqual(result.json['icon'],icon or '🧩')

    def test_rejects_html_text_wrong_types_and_excessive_input(self):
        for icon in ['<img src=x onerror=alert(1)>','script','🍓 текст','🧩'*33,{},None,'\u200d']:
            response=self.request('POST','/api/categories',json={'name':'Invalid','icon':icon,'attribute_schema':[]})
            self.assertEqual(response.status_code,400,response.json)

    def test_old_categories_keep_their_icons_and_migration_is_repeatable(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'old.db';con=sqlite3.connect(path)
            con.execute("CREATE TABLE categories(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,attribute_schema TEXT NOT NULL DEFAULT '[]',created_at TEXT NOT NULL DEFAULT '',slug TEXT)")
            con.execute("INSERT INTO categories(id,name,slug) VALUES(1,'Рідини','liquid')")
            con.execute("INSERT INTO categories(id,name) VALUES(2,'Власна категорія')");con.commit();con.close()
            catalog_store.initialize(path,seed=False)
            con=sqlite3.connect(path)
            self.assertEqual(con.execute('SELECT icon FROM categories ORDER BY id').fetchall(),[('💧',),('🧩',)])
            con.execute("UPDATE categories SET icon='🍓' WHERE id=2");con.commit();con.close()
            catalog_store.initialize(path,seed=False)
            con=sqlite3.connect(path);self.assertEqual(con.execute('SELECT icon FROM categories WHERE id=2').fetchone()[0],'🍓');con.close()
            backup=sqlite3.connect(Path(folder)/'old-before-category-icons.sqlite3')
            self.assertNotIn('icon',{r[1] for r in backup.execute('PRAGMA table_info(categories)')});backup.close()

if __name__=='__main__':unittest.main()
