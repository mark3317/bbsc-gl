"""Late-join protocol and production native bridge, on isolated loopback profiles."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import queue
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import dynamic
from dynamic import DynamicEngine
from engine import atomic_json
import test_compat as native
import test_processes as processes
from compat import game_user_id, blob, recv_exact


class DynamicHelpers:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.engines = []
        self.offers = []

    def tearDown(self):
        for engine in self.engines:
            engine.close()
        self.tmp.cleanup()

    def config(self, who):
        number = ord(who)-ord('A')
        host=f'127.0.0.{101+number}'
        with socket.socket() as sock:
            sock.bind((host,0))
            port=sock.getsockname()[1]
        offer = dict(id=who, seed=hashlib.sha256(who.encode()).hexdigest(),
                     name='Hunter'+who, host=host, port=port, p2p=37658)
        cfg = dict(version=1, group='home-'+who, secret='00'*32, epoch=1,
                   mode='dynamic-worlds-v1', identity=offer,
                   members=[dynamic.member(offer)], peers_file=str(self.root/(who+'-peers.json')))
        self.offers.append(offer)
        atomic_json(cfg['peers_file'], [offer])
        return cfg

    def node(self, who):
        cfg = self.config(who)
        engine = DynamicEngine(cfg, who, self.root/who, cfg['peers_file']).start()
        self.engines.append(engine)
        return engine

    def discover(self):
        for engine in self.engines:
            atomic_json(engine.peers_file, self.offers)
            engine.refresh_peers()

    def eventually(self, condition, timeout=5):
        end = time.monotonic()+timeout
        while time.monotonic() < end:
            if condition():
                return
            time.sleep(.02)
        self.fail('Dynamic condition not reached')

    def host(self, engine):
        engine.command(dict(kind='acquire'))
        return engine.command(dict(kind='room_create', room=dict(max_slots=5, world=1, flags=0, bins=[], member_bins=[])))

    def claim(self, host, guest):
        guest.publish(dict(sign=dict(UserId=game_user_id(guest.id))))
        host.command(dict(kind='claim', target=guest.id, claim={}))
        self.eventually(lambda: guest.finalized() and guest.state['owner'] == host.id)


class DynamicTests(DynamicHelpers, unittest.TestCase):
    def test_unresponsive_discovery_peer_does_not_delay_healthy_sign(self):
        a,b=self.node('A'),self.node('B')
        self.config('C')
        self.discover()
        held,release=threading.Event(),threading.Event()
        rpc=a.rpc
        def stalled(peer,body):
            if peer=='C' and body['kind']=='presence':
                held.set(); release.wait(4)
                raise OSError('Silent peer')
            return rpc(peer,body)
        with patch.object(a,'rpc',side_effect=stalled):
            try:
                self.assertTrue(held.wait(3))
                for seq in (1,2):
                    b.publish({'sign':seq})
                    self.eventually(lambda:a.signs.get('B',{}).get('body',{}).get('sign')==seq,1.5)
            finally:
                release.set()
    def test_late_peer_can_replace_expired_discovery_at_capacity(self):
        a=self.node('A')
        for i in range(16):
            offer=dict(a.identity,id=f'X{i}',name=f'Old{i}',port=38000+i)
            self.offers.append(offer)
        self.discover()
        self.assertEqual(len(a.peers),17)
        late=dict(a.identity,id='Late',name='HunterLate',port=39000)
        atomic_json(a.peers_file,[a.identity,late])
        a.refresh_peers()
        self.assertIn('Late',a.peers)

    def test_invalid_reserve_reply_does_not_abandon_accepted_guest(self):
        a,b=self.node('A'),self.node('B')
        self.discover(); self.host(a)
        b.publish(dict(sign={'UserId':game_user_id('B')}))
        signed=b.signed
        corrupted=threading.Event()
        def wrong_nonce(who, message):
            if message.get('result') is True:
                corrupted.set()
                message=dict(message,nonce='previous-call')
            return signed(who,message)
        with patch.object(b,'signed',side_effect=wrong_nonce):
            seq=a.request(dict(kind='claim',target='B',claim={}))
            self.assertTrue(corrupted.wait(3))
            with self.assertRaises(TimeoutError): a.wait(seq,.25)
            self.assertIsNotNone(a.disk['staged'])
            self.assertFalse(b.finalized())
        a.wait(seq)
        self.eventually(b.finalized)
        self.assertEqual(list(a.state['pending']),['B'])

    def test_timed_out_caller_does_not_block_next_operation(self):
        a=self.node('A')
        with a.mutation:
            seq=a.request(dict(kind='acquire'))
            with self.assertRaises(TimeoutError): a.wait(seq,.05)
            with self.assertRaisesRegex(ValueError,'outstanding'): a.request(dict(kind='release'))
        self.eventually(lambda: a.pending_local is None)
        release=a.request(dict(kind='release'))
        self.assertEqual(a.wait(seq),1)
        a.wait(release)
        self.assertIsNone(a.state['owner'])

    def test_broadcast_and_invalid_new_stream_do_not_break_live_receiver(self):
        a,b=self.node('A'),self.node('B')
        self.discover(); rid=self.host(a); self.claim(a,b)
        b.command(dict(kind='room_join',room_id=rid))
        self.assertTrue(a.relay(b'first'))
        self.assertEqual(b.relay_in.get(timeout=3)[1],b'first')
        bad=dict(kind='relay',session=a.current_session(),incarnation=a.disk['incarnation'],
                 stream=a.relay_stream('B')+5,seq=99,data='',binding={})
        with self.assertRaisesRegex(ValueError,'Out of order'): a.rpc('B',bad)
        a.relay(b'second',recipients=['B'])
        self.assertEqual(b.relay_in.get(timeout=3)[1],b'second')

    def test_late_second_and_third_start_without_restarting_host(self):
        a = self.node('A')
        rid = self.host(a)
        b = self.node('B')
        self.discover()
        self.claim(a, b)
        first = b.command(dict(kind='room_join', room_id=rid))
        c = self.node('C')
        self.discover()
        self.claim(a, c)
        second = c.command(dict(kind='room_join', room_id=rid))
        self.assertNotEqual(first, second)
        self.assertEqual(set(a.state['joined']), {'B', 'C'})
        self.assertEqual(a.state['room']['id'], rid)
        self.eventually(lambda: b.state == a.state and c.state == a.state)

    def test_offline_discovered_player_does_not_block_solo_bell_or_new_guest(self):
        a = self.node('A')
        self.config('C')  # No C runtime is ever started.
        self.discover()
        rid = self.host(a)
        b = self.node('B')
        self.discover()
        self.claim(a, b)
        b.command(dict(kind='room_join', room_id=rid))
        self.assertNotIn('C', a.state['roster'])

    def test_two_hosts_cannot_reserve_same_guest(self):
        a, b, c = [self.node(w) for w in 'ABC']
        self.discover()
        self.host(a)
        self.host(c)
        b.publish(dict(sign=dict(UserId=game_user_id('B'))))
        results = []
        def attempt(host):
            try:
                host.command(dict(kind='claim', target='B', claim={}))
                results.append(host.id)
            except ValueError:
                pass
        threads = [threading.Thread(target=attempt, args=(x,)) for x in (a, c)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(7)
        self.assertEqual(len(results), 1)
        self.assertEqual(b.disk['attachment']['host'], results[0])
        self.assertEqual(sum('B' in h.state['pending'] for h in (a, c)), 1)

    def test_guest_bell_acquire_and_incoming_reservation_are_exclusive(self):
        a, b = self.node('A'), self.node('B')
        self.discover()
        self.host(a)
        b.publish(dict(sign=dict(UserId=game_user_id('B'))))
        barrier = threading.Barrier(2)
        succeeded = []
        def run(engine, op, label):
            barrier.wait()
            try:
                engine.command(op)
                succeeded.append(label)
            except ValueError:
                pass
        threads = [threading.Thread(target=run, args=(a, dict(kind='claim', target='B', claim={}), 'guest')),
                   threading.Thread(target=run, args=(b, dict(kind='acquire'), 'host'))]
        for thread in threads: thread.start()
        for thread in threads: thread.join(7)
        self.assertEqual(len(succeeded), 1)
        if succeeded == ['guest']:
            self.assertIsNotNone(b.disk['attachment'])
            self.assertIsNone(b.disk['home']['owner'])
        else:
            self.assertIsNone(b.disk['attachment'])
            self.assertEqual(b.disk['home']['owner'], 'B')

    def test_accepted_reservation_lost_reply_retries_same_admission_once(self):
        a, b = self.node('A'), self.node('B')
        self.discover()
        self.host(a)
        b.publish(dict(sign=dict(UserId=game_user_id('B'))))
        original = a.rpc
        dropped = threading.Event()
        def lose_ack(who, body):
            answer = original(who, body)
            if body['kind'] == 'reserve' and not dropped.is_set():
                dropped.set()
                raise OSError('Lost reserve reply')
            return answer
        before = a.state['revision']
        with patch.object(a, 'rpc', side_effect=lose_ack):
            a.command(dict(kind='claim', target='B', claim={}))
        self.assertTrue(dropped.is_set())
        self.assertEqual(a.state['revision'], before+1)
        self.assertEqual(list(a.state['pending']), ['B'])

    def test_unconfirmed_reservation_never_authorizes_native_claim(self):
        a, b = self.node('A'), self.node('B')
        self.discover()
        self.host(a)
        b.publish(dict(sign=dict(UserId=game_user_id('B'))))
        original = a.rpc
        blocked = threading.Event()
        def hold_commit(who, body):
            answer = original(who, body)
            if body['kind'] == 'reserve':
                blocked.set()
                raise OSError('Host commit paused')
            return answer
        with patch.object(a, 'rpc', side_effect=hold_commit):
            seq = a.request(dict(kind='claim', target='B', claim={}))
            self.assertTrue(blocked.wait(3))
            self.assertFalse(b.finalized())
            self.assertNotIn('B', a.state['pending'])
        a.wait(seq)
        self.eventually(b.finalized)

    def test_partition_never_releases_or_promotes_guest(self):
        a, b = self.node('A'), self.node('B')
        self.discover()
        rid = self.host(a)
        self.claim(a, b)
        b.command(dict(kind='room_join', room_id=rid))
        with b.lock: b.blocked.add('A')
        with a.lock: a.blocked.add('B')
        seq = b.request(dict(kind='room_leave'))
        with self.assertRaises(TimeoutError): b.wait(seq, .3)
        self.assertEqual(b.state['owner'], 'A')
        self.assertIn('B', a.state['joined'])
        self.assertIsNotNone(b.disk['attachment'])
        with b.lock: b.blocked.clear()
        with a.lock: a.blocked.clear()
        b.wait(seq)
        self.eventually(lambda: b.disk['attachment'] is None)
        self.assertEqual(b.command(dict(kind='acquire')), 1)

    def test_lost_guest_leave_reply_is_not_reexecuted_in_home_world(self):
        a, b = self.node('A'), self.node('B')
        self.discover()
        rid = self.host(a)
        self.claim(a, b)
        b.command(dict(kind='room_join', room_id=rid))
        original = b.rpc
        dropped = threading.Event()
        def lose_reply(who, body):
            result = original(who, body)
            if body['kind'] == 'command' and body['op']['kind'] == 'room_leave' and not dropped.is_set():
                dropped.set()
                raise OSError('Lost leave reply')
            return result
        with patch.object(b, 'rpc', side_effect=lose_reply):
            b.command(dict(kind='room_leave'))
        self.eventually(lambda: b.disk['attachment'] is None)
        self.assertIsNone(b.state['owner'])
        self.assertIsNone(b.state['room'])

    def test_lost_leave_reply_after_host_admits_different_guest(self):
        a,b,c=[self.node(who) for who in 'ABC']
        self.discover();rid=self.host(a);self.claim(a,b)
        b.command(dict(kind='room_join',room_id=rid))
        original=b.rpc
        committed=threading.Event()
        def interrupt(who,body):
            if body['kind']=='view' or (body['kind']=='command' and committed.is_set()):
                raise OSError('Reply path offline')
            reply=original(who,body)
            if body['kind']=='command':
                committed.set()
                raise OSError('Lost leave reply')
            return reply
        with patch.object(b,'rpc',side_effect=interrupt):
            seq=b.request(dict(kind='room_leave'))
            self.assertTrue(committed.wait(3))
            self.claim(a,c);c.command(dict(kind='room_join',room_id=rid))
            self.assertNotIn('B',a.state['roster'])
        b.wait(seq,4)
        self.eventually(lambda:b.disk['attachment'] is None)
        self.assertIn('C',a.state['joined'])
        self.claim(a,b);b.command(dict(kind='room_join',room_id=rid))

    def test_staged_host_crash_and_guest_restart_recover_binding(self):
        a, b = self.node('A'), self.node('B')
        self.discover()
        rid = self.host(a)
        b.publish(dict(sign=dict(UserId=game_user_id('B'))))
        original = a.rpc
        held = threading.Event()
        def hold(who, body):
            reply = original(who, body)
            if body['kind'] == 'reserve':
                held.set()
                raise OSError('Host interrupted before commit')
            return reply
        with patch.object(a, 'rpc', side_effect=hold):
            a.request(dict(kind='claim', target='B', claim={}))
            self.assertTrue(held.wait(3))
            a.close()
        self.engines.remove(a)
        b.close()
        self.engines.remove(b)
        a = DynamicEngine(a.cfg, 'A', self.root/'A', a.peers_file).start()
        b = DynamicEngine(b.cfg, 'B', self.root/'B', b.peers_file).start()
        self.engines.extend([a, b])
        self.eventually(lambda: 'B' in a.state['pending'] and b.finalized())
        self.assertEqual(a.state['room']['id'], rid)
        b.command(dict(kind='room_join', room_id=rid))
        self.assertIn('B', a.state['joined'])

    def test_journal_error_fails_closed_until_durable_write(self):
        a = self.node('A')
        with patch.object(dynamic, 'atomic_json', side_effect=OSError('Disk unavailable')):
            with a.lock:
                a.disk['home']['owner'] = 'A'
                with self.assertRaises(OSError): a.persist()
            self.assertFalse(a.finalized())
            with self.assertRaises(OSError): a.world()
        with a.lock: a.persist()
        self.assertTrue(a.finalized())

    def test_stale_session_command_and_bad_authentication_do_not_touch_new_world(self):
        a, b = self.node('A'), self.node('B')
        self.discover()
        rid = self.host(a)
        self.claim(a, b)
        old_session = list(b.current_session())
        b.command(dict(kind='room_join', room_id=rid))
        b.command(dict(kind='room_leave'))
        a.command(dict(kind='room_leave'))
        a.command(dict(kind='release'))
        new_room = self.host(a)
        self.assertNotEqual(new_room, rid)
        before = copy.deepcopy(a.state)
        with self.assertRaisesRegex(ValueError, 'Stale world command'):
            b.rpc('A', dict(kind='command', session=old_session, seq=999, op=dict(kind='room_leave')))
        forged = b.signed('A', dict(nonce='old', body=dict(kind='presence')))
        forged['body']['kind'] = 'command'
        with self.assertRaisesRegex(ValueError, 'authentication'):
            a.verify('B', forged)
        self.assertEqual(a.state, before)

    def test_relay_order_recipients_dedup_and_new_native_stream(self):
        a, b, c = [self.node(w) for w in 'ABC']
        self.discover()
        rid = self.host(a)
        for guest in (b, c):
            self.claim(a, guest)
            guest.command(dict(kind='room_join', room_id=rid))
        self.eventually(lambda: b.state == a.state and c.state == a.state)
        original = a.rpc
        dropped = threading.Event()
        def lose_relay_ack(who, body):
            reply = original(who, body)
            if body['kind'] == 'relay' and not dropped.is_set():
                dropped.set()
                raise OSError('Lost relay ACK')
            return reply
        with patch.object(a, 'rpc', side_effect=lose_relay_ack):
            for n in range(24): a.relay(f'chunk{n}'.encode(), recipients=['B'])
            actual = [b.relay_in.get(timeout=5)[1] for _ in range(24)]
        self.assertEqual(actual, [f'chunk{n}'.encode() for n in range(24)])
        self.assertTrue(c.relay_in.empty())
        self.assertTrue(b.relay_in.empty())
        # Artificial RTT on real RPCs: multipart traffic must retain a window.
        def latency(who, body):
            answer = original(who, body)
            if body['kind'] == 'relay': time.sleep(.1)
            return answer
        started = time.monotonic()
        with patch.object(a, 'rpc', side_effect=latency):
            for n in range(24): a.relay(f'latency{n}'.encode(), recipients=['B'])
            self.assertEqual([b.relay_in.get(timeout=4)[1] for _ in range(24)],
                             [f'latency{n}'.encode() for n in range(24)])
        self.assertLess(time.monotonic()-started, 2)
        a.reset_relay()
        a.relay(b'new stream', recipients=['B'])
        self.assertEqual(b.relay_in.get(timeout=3)[1], b'new stream')


    def test_reinvite_recovers_failed_peer_without_releasing_host(self):
        a,b,c=self.node('A'),self.node('B'),self.node('C')
        self.discover();rid=self.host(a)
        self.claim(a,c);c.command(dict(kind='room_join',room_id=rid))
        self.claim(a,b);b.command(dict(kind='room_join',room_id=rid))
        generation=a.state['generation']
        old_stream=a.relay_stream('B')
        healthy_stream=a.relay_stream('C')
        a.fail_relay_peer('B','old admission failed')
        b.command(dict(kind='room_leave'))
        self.eventually(lambda:b.state['owner'] is None)
        self.claim(a,b)
        a.fail_relay_peer('B','late failure from previous admission',old_stream)
        self.assertNotIn('B',a.relay_peer_errors)
        self.assertEqual(a.relay_stream('C'),healthy_stream)
        a.relay(b'new placement',recipients=['B'])
        self.assertEqual(b.relay_in.get(timeout=3)[1],b'new placement')
        b.command(dict(kind='room_join',room_id=rid))
        a.relay(b'healthy guest',recipients=['C'])
        self.assertEqual(c.relay_in.get(timeout=3)[1],b'healthy guest')
        self.assertEqual(a.state['generation'],generation)
        self.assertEqual(a.state['owner'],'A')
        self.assertEqual(set(a.state['joined']),{'B','C'})

    def test_delayed_frame_from_previous_admission_cannot_enter_rejoined_guest(self):
        a,b,c=[self.node(who) for who in 'ABC']
        self.discover(); rid=self.host(a)
        for guest in (c,b):
            self.claim(a,guest);guest.command(dict(kind='room_join',room_id=rid))
        self.eventually(lambda:c.state==a.state)
        captured=[]
        rpc=c.rpc
        def capture(who,body):
            if body['kind']=='relay':
                captured.append(copy.deepcopy(body))
                return {'ack':body['seq']}  # delay this frame outside the sender
            return rpc(who,body)
        with patch.object(c,'rpc',side_effect=capture):
            c.relay(b'old',recipients=['B'])
            self.eventually(lambda:bool(captured))
        b.command(dict(kind='room_leave'))
        self.eventually(lambda:b.disk['attachment'] is None)
        self.claim(a,b); b.command(dict(kind='room_join',room_id=rid))
        self.eventually(lambda:c.state==a.state)
        with self.assertRaisesRegex(ValueError,'admission'): c.rpc('B',captured[0])
        self.assertTrue(b.relay_in.empty())
        c.relay(b'current',recipients=['B'])
        self.assertEqual(b.relay_in.get(timeout=3)[1],b'current')

    def test_old_guest_command_cannot_leave_second_visit_to_same_room(self):
        a,b=self.node('A'),self.node('B')
        self.discover(); rid=self.host(a); self.claim(a,b)
        old_ticket=a.state['pending']['B']['ticket']
        b.command(dict(kind='room_join',room_id=rid))
        b.command(dict(kind='room_leave'))
        self.eventually(lambda:b.disk['attachment'] is None)
        self.claim(a,b); b.command(dict(kind='room_join',room_id=rid))
        before=copy.deepcopy(a.state)
        with self.assertRaisesRegex(ValueError,'admission'):
            b.rpc('A',dict(kind='command',session=b.current_session(),seq=b.disk['counter']+1,
                           admission=old_ticket,op={'kind':'room_leave'}))
        self.assertEqual(a.state,before)

    def test_new_world_relay_restarts_without_reconnecting_native(self):
        a,b=self.node('A'),self.node('B')
        self.discover();rid=self.host(a)
        for generation in range(2):
            self.claim(a,b);b.command(dict(kind='room_join',room_id=rid))
            chunks=[f'world{generation}-chunk{n}'.encode() for n in range(24)]
            for raw in chunks:a.relay(raw,recipients=['B'])
            self.assertEqual([b.relay_in.get(timeout=3)[1] for _ in chunks],chunks)
            self.assertTrue(b.relay_in.empty())
            b.command(dict(kind='room_leave'))
            self.eventually(lambda:b.state['owner'] is None)
            a.command(dict(kind='room_leave'));a.command(dict(kind='release'))
            rid=self.host(a)


class DynamicNativeProcesses(DynamicHelpers, unittest.TestCase):
    # Inherit helpers only, keep process coverage separate from the in-process cases.
    np_call = native.CompatibilityTests.np_call
    np_connect = native.CompatibilityTests.np_connect
    http = native.CompatibilityTests.http

    def setUp(self):
        super().setUp()
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            if client.p.poll() is None: client.kill()
        super().tearDown()

    def client(self, who):
        cfg = self.config(who)
        path = self.root/(who+'-config.json')
        atomic_json(path, cfg)
        c = processes.Client(path, who, self.root/who, compat=True)
        self.clients.append(c)
        return c

    def test_real_http_np_late_join_and_host_rotation(self):
        a = self.client('A')
        with self.np_connect(a, 'HunterA') as sa:
            self.assertEqual(self.http(a, '/party/acquire', control=True), b'1')
            rid = self.np_call(sa, 101, 'CreateRoomRequest', {'max_slots': 5}, 'CreateRoomReply')['room_id']
            b = self.client('B')  # Starts after the host already owns a native room.
            for who in 'AB': atomic_json(self.root/(who+'-peers.json'), self.offers)
            sign = dict(UserId=game_user_id('B'), CharaId=12, AreaId=23,
                        SummonData=base64.b64encode(bytes(224)).decode())
            self.http(b, '/summon_messenger/create', sign)
            self.assertEqual(self.http(b, '/party/can_beckon', control=True), b'1')
            found = []
            def sees_guest():
                found[:] = json.loads(self.http(a, '/summon_messenger/get'))['SummonDataList']
                return bool(found)
            self.eventually(sees_guest)
            self.assertEqual(found[0]['UserId'], game_user_id('B'))
            with self.np_connect(b, 'HunterB') as sb:
                self.http(a, '/summon_messenger/request', dict(TargetUserId=game_user_id('B')))
                def receives_claim():
                    return b.state()['state']['owner'] == 'A' and b.state()['final'] >= 0
                self.eventually(receives_claim)
                joined = self.np_call(sb, 102, 'JoinRoomRequest', dict(room_id=rid), 'JoinRoomReply')
                self.assertEqual({m['npid'] for m in joined['details']['members']}, {'HunterA', 'HunterB'})
                self.assertEqual(self.http(b, '/party/can_beckon', control=True), b'0')
                signal = self.np_call(sa, 105, 'RequestSignalingInfosRequest', dict(target_npid='HunterB'), 'RequestSignalingInfosReply')
                self.assertEqual(signal['target_ip'], '127.0.0.102')
                # Production native relay sockets stay connected as peers arrive.
                sockets = [socket.create_connection(('127.0.0.1', c.info['relay']), timeout=4) for c in (a,b)]
                try:
                    for sock in sockets:
                        size, = struct.unpack('<I', recv_exact(sock, 4))
                        recv_exact(sock, size)
                    raw = b'SHAD\x40'+struct.pack('<II',111,111)+b'SHAD\x22'+bytes(64)
                    sockets[0].sendall(blob(raw))
                    size, = struct.unpack('<I', recv_exact(sockets[1], 4))
                    self.assertEqual(recv_exact(sockets[1], size), raw)
                finally:
                    for sock in sockets: sock.close()
                self.np_call(sb, 103, 'LeaveRoomRequest', dict(room_id=rid), 'LeaveRoomReply')
                self.eventually(lambda: b.state()['state']['owner'] is None)
                self.assertEqual(self.http(b, '/party/acquire', control=True), b'1')
                new_rid = self.np_call(sb, 101, 'CreateRoomRequest', dict(max_slots=5), 'CreateRoomReply')['room_id']
                self.assertNotEqual(new_rid, rid)
                self.assertEqual(a.state()['state']['owner'], 'A')
                self.np_call(sa, 103, 'LeaveRoomRequest', dict(room_id=rid), 'LeaveRoomReply')
                self.assertNotIn('error', a.op('release'))
                self.http(a, '/summon_messenger/create', dict(sign, UserId=game_user_id('A')))
                self.eventually(lambda: bool(json.loads(self.http(b, '/summon_messenger/get'))['SummonDataList']))
                self.http(b, '/summon_messenger/request', dict(TargetUserId=game_user_id('A')))
                self.eventually(lambda: a.state()['state']['owner'] == 'B' and a.state()['final'] >= 0)
                returned = self.np_call(sa, 102, 'JoinRoomRequest', dict(room_id=new_rid), 'JoinRoomReply')
                self.assertEqual({m['npid'] for m in returned['details']['members']}, {'HunterA', 'HunterB'})
                token = self.np_call(sa, 39, None, {}, 'GetTokenReply')
                self.assertEqual(token['npid'], 'HunterA')

    def test_launcher_discovery_to_production_runtime_without_prebuilt_roster(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]/'launcher'))
        import bbport_party as discovery
        from compat import start_from_environment
        launchers = []
        bridges = []
        try:
            a = discovery.Discovery(self.root/'pc-a', '127.0.0.151', set(), 'LateHost')
            launchers.append(a)
            env_a = discovery.launch_environment({}, a)
            bridge_a = start_from_environment(env_a, self.root/'package')
            bridges.append(bridge_a)
            self.assertEqual(bridge_a.control('/party/acquire', {}), 1)
            room = bridge_a.np_command(101, dict(max_slots=5))['room_id']
            b = discovery.Discovery(self.root/'pc-b', '127.0.0.152', {a.address}, 'LateGuest')
            launchers.append(b)
            a.targets = {b.address}
            env_b = discovery.launch_environment({}, b)
            bridge_b = start_from_environment(env_b, self.root/'package')
            bridges.append(bridge_b)
            self.eventually(lambda: len(a.offers()) == 2 and len(b.offers()) == 2)
            a.publish_runtime_peers()
            b.publish_runtime_peers()
            sign = dict(UserId=game_user_id(b.offer['id']), SummonData=base64.b64encode(bytes(224)).decode())
            bridge_b.http_call('/summon_messenger/create', sign, {})
            self.eventually(lambda: bool(bridge_a.http_call('/summon_messenger/get', {}, {})['SummonDataList']))
            bridge_a.http_call('/summon_messenger/request', dict(TargetUserId=game_user_id(b.offer['id'])), {})
            self.eventually(lambda: bridge_b.e.finalized() and bridge_b.e.state['owner'] == a.offer['id'])
            joined = bridge_b.np_command(102, dict(room_id=room))
            self.assertEqual(joined['details']['room_data']['room_id'], room)
            self.assertEqual(env_b['BB_SHADNET_NPID'], 'LateGuest')
            self.assertEqual(env_a['BB_PARTY_CONFIG'], str(a.profile/'coop/party/dynamic-config.json'))
        finally:
            for bridge in bridges: bridge.close()
            for launcher in launchers: launcher.close()


if __name__ == '__main__':
    unittest.main()
