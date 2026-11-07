"""WSGI entry point for PythonAnywhere; uses the existing shop routes."""
from email.message import Message
from http import HTTPStatus
from io import BytesIO
import server


class WSGIHandler(server.Handler):
    def __init__(self, environ):
        self.environ = environ
        self.command = environ['REQUEST_METHOD'].upper()
        self.path = environ.get('PATH_INFO', '/') or '/'
        if environ.get('QUERY_STRING'):
            self.path += '?' + environ['QUERY_STRING']
        self.headers = Message()
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                self.headers[key[5:].replace('_', '-')] = value
        for key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            if environ.get(key):
                self.headers[key.replace('_', '-')] = environ[key]
        self.rfile = environ['wsgi.input']
        self.wfile = BytesIO()
        self.status = 200
        self.response_headers = []

    def client_ip(self):
        # PythonAnywhere appends its trusted ingress peer at the end of XFF.
        forwarded = self.environ.get('HTTP_X_FORWARDED_FOR', '')
        return forwarded.split(',')[-1].strip() if server.TRUST_PROXY and forwarded else self.environ.get('REMOTE_ADDR', '')

    def is_https(self):
        return (self.environ.get('wsgi.url_scheme') == 'https'
                or (server.TRUST_PROXY and self.environ.get('HTTP_X_FORWARDED_PROTO', '').lower() == 'https'))

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, keyword, value):
        self.response_headers.append((keyword, str(value)))

    def end_headers(self):
        pass


def legacy_application(environ, start_response):
    handler = WSGIHandler(environ)
    if handler.command in ('GET', 'HEAD', 'POST'):
        handler.route('GET' if handler.command == 'HEAD' else handler.command,
                      head=handler.command == 'HEAD')
    else:
        handler.send_json(405, {'error': 'Метод не підтримується.'},
                          [('Allow', 'GET, HEAD, POST')])
    body = handler.wfile.getvalue()
    if handler.command == 'HEAD':
        body = b''
    if not any(key.lower() == 'content-type' for key, _ in handler.response_headers):
        handler.response_headers.append(('Content-Type', 'text/plain; charset=utf-8'))
    start_response(f'{handler.status} {HTTPStatus(handler.status).phrase}',
                   handler.response_headers)
    return [body]
