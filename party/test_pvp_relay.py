"""PvP and kill-award frames across worlds with persistent native TCP sockets."""
import socket
import struct
import unittest
from unittest.mock import patch

from compat import Compatibility, blob, recv_exact
from test_dynamic import DynamicHelpers


def frame(sender, host, kind, payload):
    return b'SHAD\x40'+struct.pack('<II', sender, host)+b'SHAD'+bytes([kind])+payload


class PvpRelayTests(DynamicHelpers, unittest.TestCase):
    def test_repeated_world_pvp_requests_state_and_kill_receipts(self):
        a, b = self.node('A'), self.node('B')
        self.discover()
        bridges = [Compatibility(e).start() for e in (a, b)]
        sockets = []
        try:
            for bridge in bridges:
                sock = socket.create_connection(('127.0.0.1', bridge.relay_port), timeout=3)
                sockets.append(sock)
                size, = struct.unpack('<I', recv_exact(sock, 4))
                recv_exact(sock, size)  # peer-count control frame

            def deliver(source, target, raw):
                sockets[source].sendall(blob(raw))
                size, = struct.unpack('<I', recv_exact(sockets[target], 4))
                self.assertEqual(recv_exact(sockets[target], size), raw)

            # No reconnect/reset of native sockets between worlds. In the old
            # sender, world two starts above seq1 while its receiver expects 1.
            for generation in range(3):
                rid = self.host(a)
                self.claim(a, b)
                b.command(dict(kind='room_join', room_id=rid))
                self.eventually(lambda: b.state == a.state)
                for sequence, enabled in enumerate((0, 1, 0, 1), 1):
                    # Guest asks, then the authoritative host confirms to guest.
                    deliver(1, 0, frame(222, 111, 0x25, struct.pack('<BBI', 1, enabled, sequence)))
                    deliver(0, 1, frame(111, 111, 0x25, struct.pack('<BBI', 0, enabled, sequence)))
                # Actual RegisterKill wire layout: version/kind, victim/death,
                # killer's NpId[17], room and member. Claim and receipt in both
                # directions (guest or host can be the finishing attacker).
                for victim, killer, origin, target in ((222, 111, 1, 0), (111, 222, 0, 1)):
                    identity = struct.pack('<17sIH', b'finisher', rid & 0xffffffff, 1)
                    death = generation+1
                    claim = struct.pack('<BBII', 1, 0, victim, death)+identity
                    ack = struct.pack('<BBII', 1, 1, victim, death)+identity
                    deliver(origin, target, frame(victim, 111, 0x2c, claim))
                    deliver(target, origin, frame(killer, 111, 0x2c, ack))
                b.command(dict(kind='room_leave'))
                self.eventually(lambda: b.state['owner'] is None)
                a.command(dict(kind='room_leave'))
                a.command(dict(kind='release'))
        finally:
            for sock in sockets:
                sock.close()
            for bridge in bridges:
                bridge.close()
            self.engines.clear()

    def test_carried_sequence_reproduces_missing_host_pvp(self):
        a, b = self.node('A'), self.node('B')
        self.discover()
        rid = self.host(a)
        self.claim(a, b)
        b.command(dict(kind='room_join', room_id=rid))
        self.eventually(lambda: b.state == a.state)
        raw = frame(111, 111, 0x25, struct.pack('<BBI', 0, 1, 1))
        a.relay(raw, recipients=['B'])
        self.assertEqual(b.relay_in.get(timeout=3)[1], raw)
        b.command(dict(kind='room_leave'))
        self.eventually(lambda: b.state['owner'] is None)
        a.command(dict(kind='room_leave'))
        a.command(dict(kind='release'))
        # Emulate the exact pre-fix acquire: generation advances, outgoing
        # sequence/stream do not. The guest can still ask its host for PvP.
        with patch.object(a, 'reset_relay'), patch.object(a, 'reset_relay_peer'):
            rid = self.host(a)
            self.claim(a, b)
        b.command(dict(kind='room_join', room_id=rid))
        self.eventually(lambda: b.state == a.state)
        request = frame(222, 111, 0x25, struct.pack('<BBI', 1, 1, 2))
        b.relay(request, recipients=['A'])
        self.assertEqual(a.relay_in.get(timeout=3)[1], request)
        a.relay(raw, recipients=['B'])
        self.eventually(lambda: bool(b.relay_buffers))
        self.assertTrue(b.relay_in.empty())
        # Restoring the production generation reset unblocks the same payload.
        a.reset_relay()
        a.relay(raw, recipients=['B'])
        self.assertEqual(b.relay_in.get(timeout=3)[1], raw)


if __name__ == '__main__':
    unittest.main()
