"""Real HTTP keep-alive resets must not hide unrelated handler failures."""
import http.client
import socket
import struct
import sys
import threading
import time
import unittest
from unittest.mock import patch

from compat import Compatibility
from test_dynamic import DynamicHelpers


class HttpDisconnect(DynamicHelpers, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.bridge = Compatibility(self.node('A')).start()
        self.errors = []
        self.failed = threading.Event()
        def error(request, address):
            self.errors.append(sys.exc_info()[1])
            self.failed.set()
        self.bridge.http.handle_error = error

    def tearDown(self):
        self.bridge.close()
        self.engines.clear()
        super().tearDown()

    def connection(self):
        return http.client.HTTPConnection('127.0.0.1', self.bridge.http_port, timeout=3)

    def request(self, conn, path='/party/can_beckon', body='{}'):
        conn.request('POST', path, body, {'X-BBSC-Party':self.bridge.token})
        reply = conn.getresponse()
        return reply.status, reply.read()

    def test_keepalive_reset_is_quiet_and_server_keeps_serving(self):
        for _ in range(4):
            conn = self.connection()
            self.assertEqual(self.request(conn), (200,b'1'))
            conn.sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                struct.pack('hh' if sys.platform=='win32' else 'ii',1,0))
            conn.close()
        self.failed.wait(.3)
        self.assertEqual(self.errors, [])
        conn = self.connection()
        try:
            self.assertEqual(self.request(conn, '/party/acquire'), (200,b'1'))
        finally:
            conn.close()

    def test_unexpected_handler_failure_still_reaches_server_diagnostics(self):
        with patch.object(self.bridge.http.RequestHandlerClass, 'handle_one_request',
                          side_effect=RuntimeError('unexpected handler fixture')):
            with socket.create_connection(('127.0.0.1',self.bridge.http_port), timeout=3):
                self.assertTrue(self.failed.wait(3))
        self.assertEqual(len(self.errors),1)
        self.assertIsInstance(self.errors[0],RuntimeError)
        conn = self.connection()
        try:
            self.assertEqual(self.request(conn), (200,b'1'))
        finally:
            conn.close()

    def test_invalid_request_is_rejected_and_next_connection_works(self):
        conn = self.connection()
        try:
            self.assertEqual(self.request(conn,body='{')[0],409)
        finally:
            conn.close()
        conn = self.connection()
        try:
            self.assertEqual(self.request(conn), (200,b'1'))
        finally:
            conn.close()
        self.assertEqual(self.errors,[])


if __name__ == '__main__':
    unittest.main()
