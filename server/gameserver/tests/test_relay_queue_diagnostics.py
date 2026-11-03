"""Production TCP writer queue accounting; no socket or worker threads in fixtures."""
import importlib.util
from pathlib import Path
import threading
from unittest.mock import patch
import unittest
path=Path(__file__).resolve().parents[1]/'bbsc_gameserver.py'
import sys
sys.path.insert(0,str(path.parent))
spec=importlib.util.spec_from_file_location('server',path);server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
class Thread:
    def __init__(self,*args,**kwargs):pass
    def start(self):pass
class Socket:
    def __init__(self):self.data=[];self.client=None;self.error=False
    def sendall(self,data):
        if self.error:raise OSError(105,'fixture')
        self.data.append(data)
        self.client.fail('fixture finished')
    def shutdown(self,*args):pass
class QueueTests(unittest.TestCase):
    def client(self):
        sock=Socket()
        with patch.object(server.threading,'Thread',Thread):client=server.RelayClient(sock,'fixture')
        sock.client=client
        return sock,client
    def test_batch_bytes_order_and_inflight_accounting(self):
        sock,c=self.client()
        c.send(b'one');c.send(b'two')
        before=c.diagnostics();self.assertEqual(before['frames'],2);self.assertEqual(before['queued'],14)
        c.note_rx();c._writer()
        self.assertEqual(sock.data,[b'\x03\0\0\0one\x03\0\0\0two'])
        after=c.diagnostics()
        self.assertEqual(after['queued'],0);self.assertEqual(after['in_flight'],0)
        self.assertEqual(after['tx_frames'],2);self.assertEqual(after['tx_bytes'],14)
        self.assertEqual(after['rx_frames'],1);self.assertEqual(len(c.queue_times),0)
    def test_failure_preserves_inflight_evidence_and_clears_queue(self):
        sock,c=self.client();sock.error=True;c.send(b'one');c._writer()
        d=c.diagnostics();self.assertEqual(d['tx_frames'],0);self.assertEqual(d['in_flight'],7)
        self.assertTrue(c.closed);self.assertIn('send failed',c.reason)
        self.assertFalse(c.queue_times);self.assertEqual(d['queued'],0)
    def test_oldest_age_and_overflow(self):
        _,c=self.client()
        with patch.object(server.time,'monotonic',return_value=10):c.send(b'one')
        with patch.object(server.time,'monotonic',return_value=12):self.assertEqual(c.diagnostics()['oldest_ms'],2000)
        self.assertFalse(c.send_framed(bytes(server.RELAY_QUEUE_LIMIT)))
        self.assertTrue(c.closed);self.assertFalse(c.queue_times);self.assertFalse(c.queue)
if __name__=='__main__':unittest.main()
