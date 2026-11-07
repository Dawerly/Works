"""Local backup utility; never exposed as a web route. Python standard library only."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import zipfile
import os

ROOT=Path(__file__).resolve().parent

def backup(database, output):
    database=Path(database).resolve();output=Path(output).resolve()
    if not database.is_file():raise ValueError('Базу даних не знайдено.')
    # Backups contain private data and must never be placed under public static directories.
    for name in ('assets','images','admin','courier','order'):
        if output.is_relative_to(ROOT/name):raise ValueError('Оберіть приватну папку для резервної копії.')
    output.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if output.exists():raise ValueError('Файл уже існує. Оберіть нове ім’я.')
    with tempfile.TemporaryDirectory() as directory:
        snapshot=Path(directory)/'dymok.db'
        source=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True);dest=sqlite3.connect(snapshot)
        try:source.backup(dest)
        finally:dest.close();source.close()
        con=sqlite3.connect(snapshot)
        try:
            if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Пошкоджена база даних.')
        finally:con.close()
        temp=output.with_name(output.name+'.partial')
        try:
            with temp.open('xb') as stream:
                os.chmod(temp,0o600)
                with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
                    archive.write(snapshot,'data/dymok.db')
                    key=database.parent/'session.key'
                    if key.is_file():archive.write(key,'data/session.key')
                    media=database.parent/'media'
                    if media.exists():
                        for file in sorted(media.rglob('*')):
                            if file.is_file() and not file.is_symlink():archive.write(file,'data/media/'+file.relative_to(media).as_posix())
                    archive.writestr('backup.json',json.dumps({'format':'dymok-backup-v1','created':datetime.now(timezone.utc).isoformat(),'database':database.name},ensure_ascii=False))
            temp.replace(output)
        finally:
            temp.unlink(missing_ok=True)
    return output

def verify(archive):
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise ValueError('Пошкоджений архів.')
        if json.loads(z.read('backup.json'))['format']!='dymok-backup-v1':raise ValueError('Невідомий формат.')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'check.db';path.write_bytes(z.read('data/dymok.db'))
            con=sqlite3.connect(path)
            try:
                if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Помилка бази.')
                if con.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Порушено зв’язки даних.')
            finally:con.close()
        return len([n for n in z.namelist() if n.startswith('data/media/')])

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Резервні копії Dymok')
    sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('backup');b.add_argument('--database',default=os.environ.get('DYMOK_DB',str(ROOT/'data/dymok.db')));b.add_argument('--output',required=True)
    v=sub.add_parser('verify-backup');v.add_argument('archive')
    args=p.parse_args()
    try:
        if args.command=='backup':print('Резервну копію створено:',backup(args.database,args.output))
        else:print('Копія перевірена. Фотографій:',verify(args.archive))
    except (ValueError,OSError,sqlite3.Error,zipfile.BadZipFile,KeyError) as exc:
        p.exit(1,str(exc)+'\n')
