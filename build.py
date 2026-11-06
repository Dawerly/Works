"""Збирає index.html із HTML-фрагментів. Лише стандартна бібліотека Python 3."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'

def build():
    manifest = json.loads((SRC / 'manifest.json').read_text(encoding='utf-8'))
    page = (SRC / 'index.template.html').read_text(encoding='utf-8')

    def include(match):
        file = (SRC / match.group(1)).resolve()
        if SRC.resolve() not in file.parents:
            raise ValueError('HTML-фрагмент має бути всередині src: ' + match.group(1))
        return '<!-- Файл: src/' + match.group(1) + ' -->\n' + file.read_text(encoding='utf-8')

    page = re.sub(r'\{\{include:([^}]+)\}\}', include, page)
    styles = []
    scripts = []
    for entry in manifest['styles']:
        if not (ROOT / entry['file']).is_file():
            raise FileNotFoundError(entry['file'])
        styles.append('<link rel="stylesheet" href="' + entry['file'] + '">')
    for entry in manifest['scripts']:
        if not (ROOT / entry['file']).is_file():
            raise FileNotFoundError(entry['file'])
        scripts.append('<script src="' + entry['file'] + '" defer></script>')
    page = page.replace('{{STYLES}}', '\n'.join(styles))
    page = page.replace('{{SCRIPTS}}', '\n'.join(scripts))
    if re.search(r'\{\{(?:include:|STYLES|SCRIPTS)', page):
        raise ValueError('У шаблоні залишився незаповнений маркер')
    (ROOT / 'index.html').write_text(page, encoding='utf-8')
    print('Готово: index.html зібрано. Відкрийте його у браузері.')

if __name__ == '__main__':
    build()
