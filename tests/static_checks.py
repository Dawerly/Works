"""Запуск: python3 tests/static_checks.py. Потрібна лише стандартна бібліотека."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
import hashlib
import importlib.util
import json
import re
import sys

sys.dont_write_bytecode=True

ROOT=Path(__file__).resolve().parents[1]
results=[]

def check(name, action):
    try:
        action()
        results.append({'name':name,'status':'PASS'})
    except Exception as e:
        results.append({'name':name,'status':'FAIL','detail':str(e)})

def require(value):
    assert value

spec=importlib.util.spec_from_file_location('site_build',ROOT/'build.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

def deterministic():
    before=(ROOT/'index.html').read_bytes()
    builder.build()
    assert before==(ROOT/'index.html').read_bytes()
check('Збирання відтворює той самий index.html',deterministic)
page=(ROOT/'index.html').read_text()
manifest=json.loads((ROOT/'src/manifest.json').read_text())

class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags=[]
    def handle_starttag(self,tag,attrs):
        self.tags.append((tag,dict(attrs)))
    handle_startendtag=handle_starttag
parser=Tags();parser.feed(page)
ids=[a['id'] for _,a in parser.tags if 'id' in a]
check('У розмітці немає повторюваних id',lambda:require(len(ids)==len(set(ids))))
check('Є рівно один основний main',lambda:require(sum(t=='main' for t,_ in parser.tags)==1))
check('Усі навігаційні блоки мають підписи',lambda:require(all('aria-label' in a for t,a in parser.tags if t=='nav')))
check('У всіх статичних зображень є alt',lambda:require(all('alt' in a for t,a in parser.tags if t=='img')))
check('У шаблоні немає незаповнених маркерів',lambda:require(not re.search(r'\{\{(?:include:|STYLES|SCRIPTS)',page)))

def aria_ids():
    for _,attrs in parser.tags:
        for name in ('aria-labelledby','aria-describedby'):
            for target in attrs.get(name,'').split():
                assert target in ids,target
check('Посилання aria-labelledby та aria-describedby існують',aria_ids)

def assets():
    for _,attrs in parser.tags:
        for name in ('src','href'):
            url=attrs.get(name,'')
            parsed=urlsplit(url)
            if not url or parsed.scheme or parsed.netloc or not parsed.path:
                continue
            assert (ROOT/parsed.path).is_file(),url
check('Усі локальні src і href ведуть на файли',assets)

def manifest_files():
    for kind in ('styles','scripts'):
        entries=manifest[kind]
        assert len(entries)==len({e['file'] for e in entries})
        for entry in entries:
            assert (ROOT/entry['file']).is_file()
check('Маніфест без дублів і відсутніх файлів',manifest_files)
check('Зовнішні вкладки мають noopener',lambda:require(all('noopener' in a.get('rel','').split() for _,a in parser.tags if a.get('target')=='_blank')))
check('Кнопка переходу веде на main',lambda:require(any(a.get('id')=='skipLink' and a.get('href')=='#main-content' for _,a in parser.tags)))
check('У кнопок загальних інструментів заданий type',lambda:require(all(a.get('type')=='button' for t,a in parser.tags if t=='button' and a.get('id') in {'ageYes','ageNo','backToTop'})))

def rejects(relative,suffix):
    try:
        builder.local_file(ROOT/'src',relative,suffix)
    except (ValueError,FileNotFoundError):
        return
    raise AssertionError('Неприпустимий шлях прийнято')
check('Збирач відхиляє вихід за папку джерел',lambda:rejects('../index.html','.html'))
check('Збирач відхиляє неправильний тип файлу',lambda:rejects('manifest.json','.html'))
check('Збирач повідомляє про відсутній фрагмент',lambda:rejects('missing.html','.html'))

def preserved():
    expected=json.loads((ROOT/'tests/preserved-source.json').read_text())
    for file,digest in expected.items():
        assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==digest,file
check('Вихідні дані й логіка поза обсягом змін збережені',preserved)

report={'passed':sum(r['status']=='PASS' for r in results),'failed':sum(r['status']=='FAIL' for r in results),'results':results}
(ROOT/'tests/static-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(bool(report['failed']))
