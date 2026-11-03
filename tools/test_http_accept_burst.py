"""Real loopback burst against the production HTTP server's pending-accept queue."""
import ast
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import sys

root = Path(__file__).resolve().parents[1]
source = (root/'server/gameserver/bbsc_gameserver.py').read_text(encoding='utf-8')
tree = ast.parse(source)
node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'QuietHTTPServer')
namespace = dict(ThreadingHTTPServer=ThreadingHTTPServer, sys=sys)
exec(compile(ast.Module(body=[node], type_ignores=[]), '<production-server>', 'exec'), namespace)
server_type = namespace['QuietHTTPServer']
assert server_type.request_queue_size == 128


def burst(cls):
    server = cls(('127.0.0.1', 0), BaseHTTPRequestHandler)
    connected = []
    try:
        # Hold accept while the native jobs of several clients connect together.
        for _ in range(24):
            try:
                connected.append(socket.create_connection(server.server_address, timeout=0.15))
            except TimeoutError:
                break
        return len(connected)
    finally:
        for connection in connected:
            connection.close()
        server.server_close()


class OldQueue(server_type):
    request_queue_size = 5


old, new = burst(OldQueue), burst(server_type)
assert new == 24, (old, new)
print(f'PASS: production accept burst {new}/24; previous five-slot queue {old}/24')
