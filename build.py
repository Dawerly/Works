"""Збирає index.html із HTML-фрагментів. Лише стандартна бібліотека Python 3."""
from pathlib import Path
import json
import re
from html import escape

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'

def local_file(base, relative, suffix):
    if not isinstance(relative, str):
        raise ValueError('Шлях до файлу має бути текстом')
    file = (base / relative).resolve()
    if base.resolve() not in file.parents or file.suffix != suffix:
        raise ValueError('Неприпустимий шлях або тип файлу: ' + relative)
    if not file.is_file():
        raise FileNotFoundError(relative)
    return file

def build():
    manifest = json.loads((SRC / 'manifest.json').read_text(encoding='utf-8'))
    page = (SRC / 'index.template.html').read_text(encoding='utf-8')

    def include(match):
        file = local_file(SRC, match.group(1), '.html')
        return '<!-- Файл: src/' + escape(match.group(1)) + ' -->\n' + file.read_text(encoding='utf-8')

    page = re.sub(r'\{\{include:([^}]+)\}\}', include, page)
    styles = []
    scripts = []
    for entry in manifest['styles']:
        local_file(ROOT / 'assets' / 'css', str(Path(entry['file']).relative_to('assets/css')), '.css')
        styles.append('<link rel="stylesheet" href="' + escape(entry['file'], quote=True) + '">')
    for entry in manifest['scripts']:
        local_file(ROOT / 'assets' / 'js', str(Path(entry['file']).relative_to('assets/js')), '.js')
        scripts.append('<script src="' + escape(entry['file'], quote=True) + '" defer></script>')
    page = page.replace('{{STYLES}}', '\n'.join(styles))
    page = page.replace('{{SCRIPTS}}', '\n'.join(scripts))
    if re.search(r'\{\{(?:include:|STYLES|SCRIPTS)', page):
        raise ValueError('У шаблоні залишився незаповнений маркер')
    (ROOT / 'index.html').write_text(page, encoding='utf-8')
    print('Готово: index.html зібрано. Відкрийте його у браузері.')

if __name__ == '__main__':
    build()
