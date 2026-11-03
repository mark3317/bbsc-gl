"""Durability barriers and network isolation without native compilation or game data."""
import json,socket,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from engine import Engine,invite,atomic_json
from party_workers import DurableWriter,PeerSender
class WorkerTests(unittest.TestCase):
    def test_batched_receipts_ack_after_disk_and_restart_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            cfg=invite([{'id':'A','host':'127.0.0.1','port':port,'p2p':3658},{'id':'B','host':'127.0.0.1','port':port+1 if port<65535 else port-1,'p2p':3659}])
            e=Engine(cfg,'A',Path(tmp));release=threading.Event();entered=threading.Event();sent=[]
            original=e.journal.write
            def slow(path,value):
                if path==e.relay_path:entered.set();release.wait(3)
                original(path,value)
            e.journal.write=slow;e.wire=lambda *args:sent.append(args)
            m={'type':'relay','from':'B','generation':0,'incarnation':8,'stream':3,'seq':1,'data':'eA=='}
            try:
                e.state['owner']='B'
                with e.lock:e.handle(m)
                self.assertTrue(entered.wait(1));self.assertEqual(e.relay_in.get_nowait()[1],b'x')
                done=threading.Event()
                thread=threading.Thread(target=lambda:(e.snapshot(),done.set()));thread.start()
                self.assertTrue(done.wait(.2),'snapshot blocked by disk write');thread.join()
                with e.lock:e.flush_outbound(time.monotonic())
                self.assertFalse(sent,'ACK escaped before durable receipt')
                for seq in range(2,17):
                    with e.lock:e.handle(dict(m,seq=seq))
                release.set();end=time.monotonic()+2
                while not e.journal.ready(e.relay_ticket) and time.monotonic()<end:time.sleep(.01)
                self.assertTrue(e.journal.ready(e.relay_ticket));self.assertLess(e.journal.writes,16)
                with e.lock:e.flush_outbound(time.monotonic())
                self.assertTrue(sent)
                disk=json.loads(e.relay_path.read_text());self.assertEqual(disk['received']['B'],[8,3,16])
                self.assertNotIn('relay_received',json.loads(e.path.read_text()))
                # Recreate engine with persisted receipts, same sender incarnation/stream.
                e.server.server_close();e.journal.close()
                restarted=Engine(cfg,'A',Path(tmp))
                try:
                    restarted.state['owner']='B';restarted.handle(dict(m,seq=16))
                    self.assertTrue(restarted.relay_in.empty())
                    restarted.handle(dict(m,seq=17));self.assertEqual(restarted.relay_in.get_nowait()[1],b'x')
                    # A newer stream may arrive out of order; late legacy frames cannot enter it.
                    restarted.handle(dict(m,stream=4,seq=2))
                    old=dict(m,seq=18);del old['stream'];restarted.handle(old)
                    self.assertTrue(restarted.relay_in.empty())
                    restarted.handle(dict(m,stream=4,seq=1))
                    self.assertEqual([restarted.relay_in.get_nowait()[1] for _ in range(2)],[b'x',b'x'])
                finally:restarted.server.server_close();restarted.journal.close()
            finally:release.set();e.server.server_close();e.journal.close()
    def test_legacy_receipts_migrated_before_control_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            cfg=invite([{'id':'A','host':'127.0.0.1','port':port,'p2p':3658}]);profile=Path(tmp)
            first=Engine(cfg,'A',profile);first.server.server_close();first.journal.close()
            old=json.loads(first.path.read_text());old['relay_received']={'B':[5,10]};atomic_json(first.path,old)
            second=Engine(cfg,'A',profile)
            try:
                self.assertEqual(second.relay_received['B'],(5,-1,10))
                self.assertEqual(json.loads(second.relay_path.read_text())['received']['B'],[5,-1,10])
                self.assertNotIn('relay_received',json.loads(second.path.read_text()))
            finally:second.server.server_close();second.journal.close()
    def test_final_revision_not_visible_before_control_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            cfg=invite([{'id':'A','host':'127.0.0.1','port':port,'p2p':3658}])
            e=Engine(cfg,'A',Path(tmp));entered=threading.Event();release=threading.Event()
            original=e.journal.write
            def slow(path,value):entered.set();release.wait(2);original(path,value)
            e.journal.write=slow
            try:
                with e.lock:
                    e.state['revision']=1;e.state['completed']['A']=[1,7]
                    e.disk['final']=1;e.pending_local={'seq':1,'op':{'kind':'acquire'}};e.persist()
                self.assertTrue(entered.wait(1));self.assertFalse(e.finalized())
                self.assertEqual(e.poll(1),(False,None));self.assertLess(e.snapshot()['final'],1)
                release.set();end=time.monotonic()+2
                while not e.journal.ready(e.final_ticket) and time.monotonic()<end:time.sleep(.01)
                self.assertTrue(e.finalized());self.assertEqual(e.poll(1),(True,7))
            finally:release.set();e.server.server_close();e.journal.close()
    def test_disk_failure_never_acknowledged(self):
        def fail(*args):raise OSError('fixture')
        writer=DurableWriter(fail)
        try:
            ticket=writer.submit(Path('unused'),{})
            writer.thread.join(1)
            with self.assertRaises(OSError):writer.ready(ticket)
            with self.assertRaises(OSError):writer.submit(Path('unused'),{})
        finally:writer.close()
    def test_slow_peer_does_not_block_other_peer(self):
        stop=threading.Event();release=threading.Event();fast=threading.Event()
        class Socket:
            def setsockopt(self,*args):pass
            def sendall(self,raw):fast.set()
            def close(self):pass
            def shutdown(self,*args):pass
        def connect(endpoint,**kwargs):
            if endpoint[1]==1:release.wait(2)
            return Socket()
        with patch('party_workers.socket.create_connection',connect):
            slow=PeerSender(('127.0.0.1',1),'127.0.0.1',stop,self.fail)
            quick=PeerSender(('127.0.0.1',2),'127.0.0.1',stop,self.fail)
            try:
                slow.put(b'slow',0);quick.put(b'fast',0)
                self.assertTrue(fast.wait(.3))
            finally:stop.set();release.set();slow.close();quick.close()
