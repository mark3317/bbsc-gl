"""One crashed guest must not close the shared native BBSC relay."""
import queue
import socket
import struct
import time
import unittest
from unittest.mock import patch

from compat import Compatibility, blob, recv_exact
from test_processes import Tests as ProcessHelpers
from test_dynamic import DynamicHelpers


class StaticPeerFailure(ProcessHelpers):
    def test_crashed_guest_preserves_ordered_healthy_traffic(self):
        a, b, c = self.group(3)
        self.assertNotIn('error', a.op('acquire'))
        self.settled()
        before = a.state()['state']
        c.kill()
        for n in range(180):
            frame = f'chunk:{n}'
            a.call('relay', data=frame, recipients=['C', 'B'])
            actual = []
            end = time.monotonic()+3
            while not actual and time.monotonic() < end:
                actual.extend(b.call('received')['frames'])
                time.sleep(.01)
            self.assertEqual(actual, [frame], n)
        self.assertIsNone(a.state()['relay_error'])
        self.assertIn('C', a.state()['relay_peer_errors'])
        self.assertEqual(a.state()['state'], before)
        # Traffic in the other direction still uses the same live world.
        b.call('relay', data='still here', recipients=['A'])
        actual = []
        end = time.monotonic()+3
        while not actual and time.monotonic() < end:
            actual.extend(a.call('received')['frames'])
            time.sleep(.01)
        self.assertEqual(actual, ['still here'])

    def test_expired_guest_preserves_healthy_traffic(self):
        a, b, c = self.group(3)
        a.op('acquire')
        self.settled()
        c.kill()
        a.call('relay', data='expire only C', recipients=['C'])
        end = time.monotonic()+13
        while time.monotonic() < end and not a.state()['relay_peer_errors']:
            time.sleep(.05)
        self.assertIn('C', a.state()['relay_peer_errors'])
        self.assertIsNone(a.state()['relay_error'])
        a.call('relay', data='healthy after expiry', recipients=['C', 'B'])
        actual = []
        end = time.monotonic()+3
        while not actual and time.monotonic() < end:
            actual.extend(b.call('received')['frames'])
            time.sleep(.01)
        self.assertEqual(actual, ['healthy after expiry'])
        a.call('reset_relay')
        self.assertEqual(a.state()['relay_peer_errors'], {})


class DynamicPeerFailure(DynamicHelpers, unittest.TestCase):
    def joined(self):
        a, b, c = [self.node(who) for who in 'ABC']
        self.discover()
        rid = self.host(a)
        for guest in (b, c):
            self.claim(a, guest)
            guest.command(dict(kind='room_join', room_id=rid))
        self.eventually(lambda: a.state == b.state == c.state)
        return a, b, c

    def test_crashed_guest_preserves_native_socket_and_healthy_stream(self):
        a, b, c = self.joined()
        before = a.snapshot()['state']
        bridge = Compatibility(a).start()
        native = socket.create_connection(('127.0.0.1', bridge.relay_port), timeout=3)
        c.close()
        try:
            size, = struct.unpack('<I', recv_exact(native, 4))
            recv_exact(native, size)
            # More than the dead recipient's window + backlog. Each healthy ACK
            # is real TCP/RPC/durable ingress, and every native frame is checked.
            for n in range(180):
                raw = b'SHAD\x40'+struct.pack('<II', 1234, 1234)+b'SHAD\x20'+str(n).encode()
                native.sendall(blob(raw))
                self.assertEqual(b.relay_in.get(timeout=3)[1], raw, n)
            self.assertIn('C', a.relay_peer_errors)
            self.assertIsNone(a.relay_error)
            self.assertEqual(a.snapshot()['state'], before)
            reply = b'SHAD\x40'+struct.pack('<II', 5678, 1234)+b'SHAD\x20reply'
            b.relay(reply, {'native_id': 5678, 'connection': [1, 1]}, ['A'])
            size, = struct.unpack('<I', recv_exact(native, 4))
            self.assertEqual(recv_exact(native, size), reply)
            # A new native stream clears the fence; it never resumes with a gap.
            a.reset_relay()
            self.assertFalse(a.relay_peer_errors)
            a.relay(b'new stream', recipients=['B'])
            self.assertEqual(b.relay_in.get(timeout=3)[1], b'new stream')
        finally:
            native.close()
            bridge.close()

    def test_expired_peer_is_fenced_without_stopping_other_workers(self):
        a, b, c = self.joined()
        work = queue.Queue()
        work.put((time.monotonic()-11, dict(session=a.current_session(), stream=a.relay_stream('C'))))
        # One production worker iteration, without waiting ten wall-clock seconds.
        original_get = work.get
        def get(**kw):
            if work.empty():
                raise SystemExit()
            return original_get(**kw)
        with patch.object(work, 'get', side_effect=get):
            with self.assertRaises(SystemExit):
                a.send_relay('C', work)
        self.assertIn('C', a.relay_peer_errors)
        self.assertIsNone(a.relay_error)
        a.relay(b'alive', recipients=['C', 'B'])
        self.assertEqual(b.relay_in.get(timeout=3)[1], b'alive')


if __name__ == '__main__':
    unittest.main()
