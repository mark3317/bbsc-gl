"""Real HTTP/native relay regression for placement sent before late admission."""
import json
import socket
import struct
import urllib.request
import unittest
import threading
import time
from unittest.mock import patch

from compat import Compatibility, blob, game_user_id, recv_exact
from test_dynamic import DynamicHelpers


class JoinPlacementTests(DynamicHelpers, unittest.TestCase):
    def request(self, bridge, path, body, placement=None, ack=None):
        headers={'Content-Type':'application/json'}
        if placement:headers['X-ShadPS4-Bloodborne-Host-Placement']=placement
        if ack:headers['X-BBSC-Aimed-Placement']=ack
        req=urllib.request.Request(f'http://127.0.0.1:{bridge.http_port}/summon_messenger/{path}',
                                   data=json.dumps(body).encode(),headers=headers)
        with urllib.request.urlopen(req,timeout=12) as response:return json.load(response)

    def run_order(self, before):
        a,b=self.node('A'),self.node('B')
        self.discover();self.host(a)
        bridges=[Compatibility(e).start() for e in (a,b)]
        sockets=[]
        try:
            for bridge in bridges:
                sock=socket.create_connection(('127.0.0.1',bridge.relay_port),timeout=3)
                sockets.append(sock)
                size,=struct.unpack('<I',recv_exact(sock,4));recv_exact(sock,size)
            host,guest=bridges
            placement='1,18010000,c33f16c9,c24a6a5f,43158c4c,3da56540,-241000'
            target=game_user_id('B')
            raw=b'SHAD\x40'+struct.pack('<II',111,111)+b'SHAD\x31'+f'{target}|{placement}'.encode()
            sign=dict(UserId=target,AreaId=23)
            self.request(guest,'create',sign)
            # Delay the flush to test the native claim cannot outrun its placement.
            with patch.object(host,'flush_placements'):
                if before:
                    sockets[0].sendall(blob(raw))
                    self.eventually(lambda:target in host.aimed_placements)
                    self.assertEqual(a.state['roster'],['A'])
                self.request(host,'request',dict(TargetUserId=target),placement)
                self.eventually(lambda:b.finalized() and b.state['owner']=='A')
                if not before:
                    sockets[0].sendall(blob(raw))
                    self.eventually(lambda:target in host.aimed_placements)
                self.assertNotIn('TargetUserId',self.request(guest,'create',sign))
            host.flush_placements()
            self.eventually(lambda:'A' in guest.received_placements)
            size,=struct.unpack('<I',recv_exact(sockets[1],4))
            self.assertEqual(recv_exact(sockets[1],size),raw)
            received=guest.received_placements['A']
            for invalid in ((placement+'x',raw,received[2]),(placement,raw,received[2]+1)):
                guest.received_placements['A']=invalid
                self.assertNotIn('TargetUserId',self.request(guest,'create',sign))
            guest.received_placements['A']=received
            self.assertNotIn('TargetUserId',self.request(guest,'create',sign))
            size,=struct.unpack('<I',recv_exact(sockets[1],4))
            self.assertEqual(recv_exact(sockets[1],size),raw)
            claim=self.request(guest,'create',sign,ack=placement)
            self.assertEqual(claim['TargetUserId'],target)
            self.assertNotIn('_bbsc_placement',claim)
            size,=struct.unpack('<I',recv_exact(sockets[1],4))
            self.assertEqual(recv_exact(sockets[1],size),raw)
            self.assertEqual(self.request(guest,'create',sign)['TargetUserId'],target)
            # No permanent stream of bootstrap replays after delivery.
            self.assertEqual(len(host.sent_placements),1)
            if host.diagnostics:
                for bridge, expected in (
                    (host, ('placement_from_game', 'admission_staged', 'admission_committed', 'placement_queued')),
                    (guest, ('admission_reserved', 'admission_confirmed', 'placement_received',
                             'placement_acknowledged', 'admission_delivered')),
                ):
                    log = bridge.logfile.read_text(encoding='utf-8')
                    events = [json.loads(line)['event'] for line in log.splitlines()]
                    self.assertEqual([event for event in events if event in expected], list(expected))
                    self.assertNotIn(placement, log)
                    self.assertNotIn(bridge.token, log)
        finally:
            for sock in sockets:sock.close()
            for bridge in bridges:bridge.close()
            self.engines.clear()

    def test_aimed_packet_before_dynamic_claim(self):
        with patch.dict('os.environ', BB_PARTY_DIAGNOSTICS='1'):
            self.run_order(True)
    def test_aimed_packet_after_dynamic_claim(self):self.run_order(False)

    @patch.dict('os.environ', BB_PARTY_DIAGNOSTICS='1')
    def test_one_way_party_connection_still_delivers_placement_and_joins(self):
        a,b=self.node('A'),self.node('B')
        self.discover(); room=self.host(a)
        host,guest=bridges=[Compatibility(e).start() for e in (a,b)]
        sockets=[]
        try:
            for bridge in bridges:
                sock=socket.create_connection(('127.0.0.1',bridge.relay_port),timeout=3)
                sockets.append(sock)
                size,=struct.unpack('<I',recv_exact(sock,4));recv_exact(sock,size)
            target=game_user_id('B')
            sign=dict(UserId=target,AreaId=23)
            placement='1,18010000,c33f16c9,c24a6a5f,43158c4c,3da56540,241000'
            raw=b'SHAD\x40'+struct.pack('<II',111,111)+b'SHAD\x31'+f'{target}|{placement}'.encode()
            with patch.object(b,'rpc',side_effect=TimeoutError('Reverse connection timed out')):
                self.request(guest,'create',sign)
                sockets[0].sendall(blob(raw))
                self.request(host,'request',dict(TargetUserId=target),placement)
                self.eventually(lambda:b.finalized() and b.state['owner']=='A')
                self.eventually(lambda:'A' in guest.received_placements)
                self.assertEqual(self.request(guest,'create',sign,ack=placement)['TargetUserId'],target)
                self.assertEqual(guest.np_command(102,dict(room_id=room))['room_id'],room)
                self.assertIn('B',a.state['joined'])
                self.assertIn('B',b.state['joined'])
                events=[json.loads(line) for line in guest.logfile.read_text(encoding='utf-8').splitlines()]
                self.assertIn('presence',[row.get('route') for row in events if row['event']=='admission_confirmed'])
                guest.np_command(103,dict(room_id=room))
                self.assertNotIn('B',a.state['joined'])
                self.assertIsNone(b.disk['attachment'])
        finally:
            for sock in sockets:sock.close()
            for bridge in bridges:bridge.close()
            self.engines.clear()

    def test_join_timeout_retires_only_the_failed_ticket_and_unblocks_bell(self):
        a,b,c=self.node('A'),self.node('B'),self.node('C')
        self.discover(); room=self.host(a)
        self.claim(a,c)
        c.command(dict(kind='room_join',room_id=room))
        host,guest=bridges=[Compatibility(e).start() for e in (a,b)]
        try:
            target=game_user_id('B')
            sign=dict(UserId=target,AreaId=23)
            placement='1,18010000,c33f16c9,c24a6a5f,43158c4c,3da56540,241000'
            self.request(guest,'create',sign)
            with patch.object(b,'rpc',side_effect=TimeoutError('Reverse connection timed out')), \
                 patch.object(b,'reverse_request',return_value=None,create=True):
                self.request(host,'request',dict(TargetUserId=target),placement)
                ticket=a.state['pending']['B']['ticket']
                reservation=b.disk['attachment']['reservation']
                b.signs['A']=dict(at=time.monotonic(),host=dict(owner='A',generation=a.state['generation']))
                self.assertFalse(guest.control('/party/can_beckon',{}))
                with self.assertRaisesRegex(TimeoutError,'Native join placement not acknowledged'):
                    guest.np_command(102,dict(room_id=room))
                self.assertIsNone(b.disk['attachment'])
                self.assertIn(reservation,b.disk['retired'])
                b.signs['A']['at']=time.monotonic()
                self.assertTrue(guest.control('/party/can_beckon',{}))
                self.eventually(lambda:'B' not in a.state['pending'])
                self.assertEqual(list(a.state['joined']),['C'])
                self.request(host,'request',dict(TargetUserId=target),placement)
                self.assertNotEqual(a.state['pending']['B']['ticket'],ticket)
                b.retire_failed_join(('A',a.state['generation'],room,ticket))
                self.assertIsNotNone(b.disk['attachment'])
                guest.control('/party/native',dict(cancel_seq=1,state=0,fresh=True,loading=False))
                self.assertIsNone(b.disk['attachment'])
                self.assertTrue(guest.control('/party/can_beckon',{}))
                self.eventually(lambda:'B' not in a.state['pending'])
                self.assertEqual(list(a.state['joined']),['C'])
        finally:
            for bridge in bridges:bridge.close()
            self.engines=[c]

    def test_repeat_direct_join_waits_for_native_placement_without_sign_poll(self):
        a,b=self.node('A'),self.node('B')
        self.discover();rid=self.host(a)
        host,guest=bridges=[Compatibility(e).start() for e in (a,b)]
        sockets=[];threads=[]
        try:
            for bridge in bridges:
                sock=socket.create_connection(('127.0.0.1',bridge.relay_port),timeout=3)
                sockets.append(sock)
                size,=struct.unpack('<I',recv_exact(sock,4));recv_exact(sock,size)
            target=game_user_id('B')
            generation=a.state['generation']
            for attempt in range(2):
                for responder in (False,True):
                    guest.control('/party/tick',dict(state=0,loading=False,bell=False,
                                  fresh=True,alive=True,members=1,responder=responder))
                placement='1,18010000,c33f16c9,c24a6a5f,43158c4c,3da56540,241000'
                raw=b'SHAD\x40'+struct.pack('<II',111,111)+b'SHAD\x31'+f'{target}|{placement}'.encode()
                self.request(guest,'create',dict(UserId=target,AreaId=23))
                with patch.object(host,'flush_placements'):
                    sockets[0].sendall(blob(raw))
                    self.eventually(lambda:host.aimed_placements.get(target,(None,None,None,None))[3]==placement)
                    self.request(host,'request',dict(TargetUserId=target),placement)
                    self.eventually(lambda:b.finalized() and b.state['owner']=='A')
                    result=[]
                    worker=threading.Thread(target=lambda:result.append(guest.np_command(102,dict(room_id=rid))))
                    threads.append(worker);worker.start()
                    # Regression: native JoinRoom used to consume pending here,
                    # making the later placement flush lose its only recipient.
                    worker.join(.15);self.assertTrue(worker.is_alive())
                    self.assertIn('B',b.state['pending']);self.assertNotIn('B',b.state['joined'])
                # A rejected queue submission must not suppress retries.
                with patch.object(a,'relay',return_value=False):
                    host.flush_placements()
                    self.assertFalse(host.sent_placements)
                host.flush_placements()
                self.eventually(lambda:guest.received_placements.get('A',(None,))[0]==placement)
                key=next(iter(host.sent_placements))
                host.placement_sent_at[key]=time.monotonic()-1
                with patch.object(a,'relay',wraps=a.relay) as retransmit:
                    host.flush_placements()
                    self.assertTrue(retransmit.called)
                # Native replay from the previous admission can still be queued
                # locally; it must not authorize this different placement.
                while True:
                    size,=struct.unpack('<I',recv_exact(sockets[1],4))
                    if recv_exact(sockets[1],size)==raw:break
                # No HTTP sign/create after admission: the worker carries the ack.
                previous_ack = ack if attempt else placement
                guest.control('/party/tick',dict(state=4,loading=False,bell=False,
                              fresh=True,alive=True,members=1,placement_ticket=True,aimed_placement=previous_ack))
                worker.join(.1);self.assertTrue(worker.is_alive())
                ack=f"{placement}|A-{generation}-{key[1]}"
                while True:
                    size,=struct.unpack('<I',recv_exact(sockets[1],4))
                    if recv_exact(sockets[1],size)==raw+ack[len(placement):].encode():break
                guest.control('/party/tick',dict(state=4,loading=False,bell=False,
                              fresh=True,alive=True,members=1,placement_ticket=True,aimed_placement=ack))
                worker.join(3);self.assertFalse(worker.is_alive());self.assertEqual(len(result),1)
                self.assertIn('B',b.state['joined']);self.assertNotIn('B',b.state['pending'])
                guest.np_command(103,dict(room_id=rid))
                self.eventually(lambda:b.state['owner'] is None)
                a.fail_relay_peer('B','previous admission timeout')
                host.np_command(103,dict(room_id=rid))
                rid=host.np_command(101,dict(max_slots=5))['room_id']
                self.assertEqual(a.state['owner'],'A')
                self.assertEqual(a.state['generation'],generation)
        finally:
            guest.closed=True
            for worker in threads:worker.join(1)
            for sock in sockets:sock.close()
            for bridge in bridges:bridge.close()
            self.engines.clear()


if __name__=='__main__':unittest.main()
