"""Apply a local release to an existing installation while preserving data and credentials.
Run only after stopping the site. This utility does not deploy to PythonAnywhere itself.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import sqlite3
import zipfile
from maintenance import backup,verify

ROOT=Path(__file__).resolve().parent
# Only application sources/assets, never config.json or data/ from the release.
FILES=('server.py','catalog.py','catalog_store.py','legacy_wsgi.py','wsgi_app.py','delivery.py','customers.py','schema.sql',
       'requirements.txt','build.py','index.html','catalog-seed.json','maintenance.py','update_site.py',
       'README.md','README_DELIVERY.md','CHANGELOG.md','QA.md','start.command','start.bat')
DIRS=('assets','src','admin','courier','order','tests')

def update(target,site_stopped=False,backup_folder=None):
    target=Path(target).resolve()
    if not site_stopped:raise ValueError('Спочатку зупиніть сайт і додайте --site-stopped.')
    if target==ROOT or target.is_relative_to(ROOT) or ROOT.is_relative_to(target):raise ValueError('Розпакуйте оновлення в окрему сусідню папку.')
    if not (target/'server.py').is_file() or not (target/'data/dymok.db').is_file():raise ValueError('Це не наявна інсталяція Dymok із data/dymok.db.')
    # Preflight every destination before changing installed files.
    candidates=[target/name for name in FILES]
    for name in DIRS:
        candidates.extend(target/source.relative_to(ROOT) for source in (ROOT/name).rglob('*'))
    for dest in candidates:
        if any(part.is_symlink() for part in (dest,*dest.parents) if part.is_relative_to(target)):
            raise ValueError('Символічне посилання в інсталяції: '+str(dest.relative_to(target)))
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
    folder=Path(backup_folder).resolve() if backup_folder else target.parent/'dymok-backups'
    if folder==target or folder.is_relative_to(target):raise ValueError('Розмістіть резервну копію поза папкою сайту.')
    folder.mkdir(mode=0o700,parents=True,exist_ok=True)
    snapshot=folder/('dymok-data-'+stamp+'.zip');backup(target/'data/dymok.db',snapshot);verify(snapshot)
    # Save old code and config for rollback. data/ has its separate consistent SQLite snapshot.
    code=folder/('dymok-code-'+stamp+'.zip')
    # Create the code/config backup with private permissions from the outset.
    with code.open('xb') as stream:
        code.chmod(0o600)
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            _backup_code(archive,target)
    for name in FILES:
        if (ROOT/name).is_file():shutil.copy2(ROOT/name,target/name)
    for name in DIRS:
        for source in (ROOT/name).rglob('*'):
            if source.is_symlink() or '__pycache__' in source.parts:continue
            rel=source.relative_to(ROOT);dest=target/rel
            # Refuse symlinks in the installed tree rather than following them outside target.
            if any(part.is_symlink() for part in (dest,*dest.parents) if part.is_relative_to(target)):
                raise ValueError('Символічне посилання в інсталяції: '+str(rel))
            if source.is_dir():dest.mkdir(parents=True,exist_ok=True)
            elif source.is_file():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    return snapshot,code

def _backup_code(archive,target):
    for name in (*FILES,'config.json'):
        f=target/name
        if f.is_file() and not f.is_symlink():archive.write(f,name)
    for name in DIRS:
        if (target/name).exists():
            for f in (target/name).rglob('*'):
                if f.is_file() and not f.is_symlink() and '__pycache__' not in f.parts:archive.write(f,f.relative_to(target))

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Оновлення Dymok зі збереженням data/ та config.json')
    p.add_argument('--target',required=True);p.add_argument('--site-stopped',action='store_true');p.add_argument('--backup-folder')
    a=p.parse_args()
    try:
        data,code=update(a.target,a.site_stopped,a.backup_folder)
        print('Код оновлено. Дані та паролі збережені.');print('Резервна копія даних:',data);print('Резервна копія коду:',code)
        print('Встановіть requirements.txt у virtualenv сайту, потім перезапустіть WSGI. Міграція застосовується при першому запуску.')
    except (ValueError,OSError,sqlite3.Error) as e:p.exit(1,str(e)+'\n')
