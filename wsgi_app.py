"""WSGI entry point: shop, catalogue editor, stock and orders."""
import server
from catalog import create_app

server.init_db()
server.apply_config()
server.ensure_admin()
application = create_app()
