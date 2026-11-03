"""Production BBR1 relay trace: identical frame hashes, drops, failures and bound."""
import errno
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bbhost_service as service


class Socket:
    def __init__(self):
        self.sent = []
        self.error = False

    def sendto(self, data, addr):
        if self.error:
            raise OSError(errno.ENOBUFS, 'fixture')
        self.sent.append((data, addr))
        return len(data)


class PacketTrace(unittest.TestCase):
    def test_attempt_renewal_duplicates_expiry_and_isolation(self):
        relay = service.Relay()
        relay.sock = Socket()
        relay.packet_trace_remaining = 0  # exhausted by an earlier game run
        a, b, c = [x.ljust(16, b'\0') for x in (b'a', b'b', b'c')]
        aa, bb = ('192.0.2.1', 3658), ('192.0.2.1', 3659)
        relay._shad(b'BBR1\1' + a, aa)
        relay._shad(b'BBR1\1' + b, bb)
        marker = lambda token: b'BBR1\6' + a + b + token.to_bytes(8, 'big')
        relay._shad(marker(100), ('192.0.2.1', 9999))
        self.assertFalse(relay.attempt_traces)  # unauthorized markers cannot renew
        relay._shad(marker(100), aa)
        key = tuple(sorted((a, b)))
        capture = relay.attempt_traces[key]
        self.assertEqual(relay.sock.sent[-1], (b'BBR1\7' + marker(100)[5:], bb))
        frame = bytes.fromhex('ff8300280028') + b'body'
        packet = b'BBR1\3' + b + a + bytes(6) + frame
        lines = []
        previous = service._log
        service._log = lambda text, **kwargs: lines.append(text)
        try:
            relay._shad(packet, aa)
            self.assertEqual(capture['remaining'], 8190)
            self.assertTrue(all('attempt=0000000000000064' in x for x in lines))
            expiry = capture['expires']
            capture['remaining'] = 0
            relay._shad(marker(100), aa)
            relay._shad(marker(99), aa)
            self.assertEqual(capture['expires'], expiry)
            self.assertEqual(capture['remaining'], 0)
            before = len(lines)
            relay._shad(packet, aa)  # capture limit never affects forwarding
            self.assertEqual(len(lines), before)
            self.assertEqual(relay.sock.sent[-1][0], b'BBR1\4' + a + bytes(6) + frame)
            relay._shad(marker(101), aa)  # same peer and connection, new attempt
            renewed = relay.attempt_traces[key]
            self.assertEqual(renewed['remaining'], 8192)
            relay._shad(packet, aa)
            self.assertTrue('attempt=0000000000000065' in lines[-1])
            before = len(lines)
            relay._trace_shad_packet('RX', a, c, frame, aa, 'received')
            self.assertEqual(len(lines), before)  # unrelated pair cannot consume
            relay._trace_shad_packet('RX', a, b, bytes.fromhex('ff83001e001e'), aa, 'received')
            self.assertEqual(renewed['remaining'], 8190)  # bulk vport30 excluded
            renewed['expires'] = 0
            relay._shad(packet, aa)
            self.assertEqual(len(lines), before)
        finally:
            service._log = previous

    def test_production_forward_drop_error_and_bound(self):
        relay = service.Relay()
        relay.sock = Socket()
        a, b = b'trace-a'.ljust(16, b'\0'), b'trace-b'.ljust(16, b'\0')
        aa, bb = ('127.0.0.1', 3658), ('127.0.0.1', 3659)
        lines = []
        previous = service._log
        service._log = lambda text, **kwargs: lines.append(text)
        try:
            relay._shad(b'BBR1\1' + a, aa)
            relay._shad(b'BBR1\1' + b, bb)
            frame = b'hello'  # known FNV-1a64 a430d84680aabd0b, same as native
            packet = b'BBR1\3' + b + a + bytes(6) + frame
            relay._shad(packet, aa)
            self.assertEqual(relay.sock.sent[-1], (b'BBR1\4' + a + bytes(6) + frame, bb))
            self.assertTrue(any('stage=RX' in x and 'hash=a430d84680aabd0b' in x for x in lines))
            self.assertTrue(any('stage=TX' in x and 'hash=a430d84680aabd0b' in x and 'result=32' in x for x in lines))
            before = len(relay.sock.sent)
            relay._shad(packet, ('127.0.0.1', 9999))
            self.assertEqual(len(relay.sock.sent), before)
            self.assertIn('sender-unregistered-or-address', lines[-1])
            del relay.shad[b]
            relay._shad(packet, aa)
            self.assertTrue(any('destination-unregistered' in x for x in lines))
            relay.shad[b] = {'addr': bb, 'seen': 0}
            relay.sock.error = True
            with self.assertRaises(OSError):
                relay._shad(packet, aa)
            self.assertIn('result=error-', lines[-1])
            self.assertEqual(relay.send_errors, 1)
            relay.packet_trace_remaining = 0
            count = len(lines)
            relay.sock.error = False
            relay._shad(packet, aa)
            self.assertEqual(len(lines), count)
            self.assertEqual(relay.shad_frames, 2)
        finally:
            service._log = previous


if __name__ == '__main__':
    unittest.main()
