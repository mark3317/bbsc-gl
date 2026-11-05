"""Snapshot bursts must not discard the following one-shot host finale."""
import socket
import struct
import threading
import time
import unittest
from unittest.mock import patch
from compat import Compatibility, blob, recv_exact
from test_dynamic import DynamicHelpers
from test_pvp_relay import frame


class FinaleRelayTests(DynamicHelpers, unittest.TestCase):
    def test_snapshot_burst_then_finale_with_slow_healthy_recipient(self):
        a, b = self.node('A'), self.node('B')
        self.discover()
        rid = self.host(a)
        self.claim(a, b)
        b.command(dict(kind='room_join', room_id=rid))
        self.eventually(lambda: a.state == b.state)
        bridges = [Compatibility(e).start() for e in (a, b)]
        sockets = [socket.create_connection(('127.0.0.1', x.relay_port), timeout=20) for x in bridges]
        received, errors = [], []
        try:
            for sock in sockets:
                n, = struct.unpack('<I', recv_exact(sock, 4))
                recv_exact(sock, n)
            # Full native 96-byte ending request: variant, absolute NG target,
            # sequence/map/movie followed by scalar native arguments.
            ending = frame(111, 111, 0x28, struct.pack('<BBBI Ii', 0,0,1,777,0x15000000,21000020)+bytes(76))
            packets = [frame(111,111,0x22,struct.pack('<I', i)+bytes(1000)) for i in range(400)] + [ending]
            def drain():
                try:
                    for _ in packets:
                        n, = struct.unpack('<I', recv_exact(sockets[1],4))
                        received.append(recv_exact(sockets[1],n))
                except Exception as ex:
                    errors.append(ex)
            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            original = a.rpc
            def slow(who, body):
                if body.get('kind') == 'relay':
                    time.sleep(.08) # burst exceeds the 128-frame queue; peer is healthy
                return original(who, body)
            with patch.object(a, 'rpc', side_effect=slow):
                sockets[0].sendall(b''.join(blob(raw) for raw in packets))
                reader.join(20)
            self.assertFalse(reader.is_alive(), a.relay_peer_errors)
            self.assertFalse(errors)
            self.assertEqual(received, packets)
            self.assertFalse(a.relay_peer_errors)
            # Guest replies still pass while host backpressure is active.
            raw = frame(222,111,0x23,bytes(10))
            sockets[1].sendall(blob(raw))
            n, = struct.unpack('<I',recv_exact(sockets[0],4))
            self.assertEqual(recv_exact(sockets[0],n),raw)
        finally:
            for sock in sockets: sock.close()
            for bridge in bridges: bridge.close()


if __name__ == '__main__':
    unittest.main()
