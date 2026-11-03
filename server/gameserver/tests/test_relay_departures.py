"""Relay EOF notifications must be scoped to the departing player's party."""
import collections
import importlib.util
from pathlib import Path
import struct
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
spec = importlib.util.spec_from_file_location(
    'bbsc_gameserver', Path(__file__).resolve().parents[1] / 'bbsc_gameserver.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class Peer:
    def __init__(self):
        self.sender_hint = None
        self.session_hint = None
        self.seen_envelope = False
        self.controls = []
        self.frames = []

    def send(self, data):
        self.controls.append(data)
        return 1

    def send_framed(self, data):
        self.frames.append(data)
        return 1


class Timer:
    def __init__(self, interval, callback, args=()):
        self.callback, self.args = callback, args
        self.cancelled = False
    def start(self): pass
    def cancel(self): self.cancelled = True
    def fire(self): self.callback(*self.args)  # even a racing cancelled callback must be harmless


class DepartureTests(unittest.TestCase):
    def setUp(self):
        self.timers = patch.object(server.threading, 'Timer', Timer)
        self.timers.start()
        self.addCleanup(self.timers.stop)
        server.RELAY_PENDING_DEPARTURES.clear()
        server.RELAY_CLIENTS.clear()
        server.RELAY_ROSTER = ()
        server.RELAY_HINT_COUNTS = collections.Counter()
        server.RELAY_HINTED_CLIENTS = 0
        # Even when observation and routing are off, departures need party metadata.
        server.ARGS = types.SimpleNamespace(relay_tcp_stats_interval=0,
                                            relay_session_routing=False)

    def expire(self):
        for pending in list(server.RELAY_PENDING_DEPARTURES.values()):
            pending['timer'].fire()

    def join(self, sender, party):
        conn, peer = object(), Peer()
        server._relay_register_client(conn, peer)
        packet = b'SHAD\x40' + struct.pack('<II', sender, party) + b'SHAD\x23'
        server._relay_forward(conn, packet)
        return conn, peer

    def test_guest_eof_notifies_host_and_other_guest_only(self):
        host, hp = self.join(10, 10)
        guest, gp = self.join(11, 10)
        other, op = self.join(12, 10)
        unrelated, up = self.join(20, 20)
        self.assertEqual(server._relay_unregister_client(guest), 3)
        self.assertEqual(hp.controls, [])  # transport grace, not an immediate departure
        self.expire()
        expected = struct.pack('<BII', 0x7E, 11, 10)
        self.assertEqual(hp.controls, [expected])
        self.assertEqual(op.controls, [expected])
        self.assertEqual(gp.controls, [])
        self.assertEqual(up.controls, [])
        self.assertEqual(server.RELAY_HINT_COUNTS, {10: 2, 20: 1})

    def test_host_eof_identifies_host_without_closing_other_connections(self):
        host, hp = self.join(10, 10)
        guest, gp = self.join(11, 10)
        server._relay_unregister_client(host)
        self.expire()
        self.assertEqual(gp.controls, [struct.pack('<BII', 0x7E, 10, 10)])
        self.assertIn(guest, server.RELAY_CLIENTS)

    def test_duplicate_eof_does_not_repeat_notification(self):
        host, hp = self.join(10, 10)
        guest, gp = self.join(11, 10)
        server._relay_unregister_client(guest)
        server._relay_unregister_client(guest)
        self.expire()
        self.assertEqual(len(hp.controls), 1)

    def test_solo_or_unidentified_socket_cannot_end_a_party(self):
        host, hp = self.join(10, 10)
        solo, sp = self.join(30, 0)
        unknown, peer = object(), Peer()
        server._relay_register_client(unknown, peer)
        server._relay_unregister_client(solo)
        server._relay_unregister_client(unknown)
        self.assertEqual(hp.controls, [])

    def test_changed_party_does_not_notify_previous_party(self):
        host, hp = self.join(10, 10)
        second, sp = self.join(20, 20)
        guest, gp = self.join(11, 10)
        server._relay_forward(guest, b'SHAD\x40' + struct.pack('<II', 11, 20) + b'SHAD\x23')
        server._relay_unregister_client(guest)
        self.assertEqual(hp.controls, [])
        self.expire()
        self.assertEqual(sp.controls, [struct.pack('<BII', 0x7E, 11, 20)])

    def test_replacement_before_old_eof_preserves_party(self):
        old, old_peer = self.join(10, 10)
        guest, gp = self.join(11, 10)
        new, new_peer = self.join(10, 10)
        server._relay_unregister_client(old, "stale timeout")
        self.expire()
        self.assertEqual(gp.controls, [])
        self.assertEqual(server.RELAY_PENDING_DEPARTURES, {})
        self.assertIn(new, server.RELAY_CLIENTS)

    def test_replacement_after_eof_cancels_even_racing_timer(self):
        old, _ = self.join(10, 10)
        guest, gp = self.join(11, 10)
        server._relay_unregister_client(old)
        stale_timer = server.RELAY_PENDING_DEPARTURES[(10, 10)]['timer']
        new, _ = self.join(10, 10)
        self.assertTrue(stale_timer.cancelled)
        stale_timer.fire()
        self.assertEqual(gp.controls, [])
        self.assertFalse(server.RELAY_PENDING_DEPARTURES)

    def test_new_socket_genuine_eof_not_hidden_by_old_socket(self):
        old, old_peer = self.join(10, 10)
        guest, gp = self.join(11, 10)
        new, _ = self.join(10, 10)
        server._relay_unregister_client(new)
        pending = server.RELAY_PENDING_DEPARTURES[(10, 10)]
        # A late state frame from the obsolete transport must not cancel it.
        packet = b'SHAD\x40' + struct.pack('<II', 10, 10) + b'SHAD\x23'
        self.assertEqual(server._relay_forward(old, packet), 0)
        self.assertIs(server.RELAY_PENDING_DEPARTURES[(10, 10)], pending)
        self.expire()
        self.assertEqual(gp.controls, [struct.pack('<BII', 0x7E, 10, 10)])
        server._relay_unregister_client(old)
        self.expire()
        self.assertEqual(len(gp.controls), 1)

    def test_explicit_leave_is_immediate_but_stale_socket_cannot_send_it(self):
        old, _ = self.join(10, 10)
        guest, gp = self.join(11, 10)
        new, _ = self.join(10, 10)
        payload = b'SHAD\x40' + struct.pack('<II', 10, 10) + b'SHAD\x2a'
        before = len(gp.frames)
        self.assertEqual(server._relay_forward(old, payload), 0)
        self.assertEqual(len(gp.frames), before)
        server._relay_forward(new, payload)
        self.assertEqual(gp.frames[-1], struct.pack('<I', len(payload)) + payload)

    def test_wrong_identity_or_party_does_not_cancel_pending(self):
        host, _ = self.join(10, 10)
        guest, gp = self.join(11, 10)
        server._relay_unregister_client(host)
        self.join(10, 20)  # same player now in a different party
        self.join(12, 10)  # different player in the old party
        self.expire()
        self.assertEqual(gp.controls, [struct.pack('<BII', 0x7E, 10, 10)])

    def test_old_callback_cannot_remove_newer_pending_decision(self):
        old, _ = self.join(10, 10)
        guest, gp = self.join(11, 10)
        server._relay_unregister_client(old)
        old_timer = server.RELAY_PENDING_DEPARTURES[(10, 10)]['timer']
        new, _ = self.join(10, 10)
        server._relay_unregister_client(new)
        current = server.RELAY_PENDING_DEPARTURES[(10, 10)]
        old_timer.fire()
        self.assertIs(server.RELAY_PENDING_DEPARTURES[(10, 10)], current)
        self.expire()
        self.assertEqual(len(gp.controls), 1)


if __name__ == '__main__':
    unittest.main()
