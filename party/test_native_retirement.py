"""Real process/HTTP recovery, using isolated journals and native observations."""
import base64
import copy
import json
import time
import unittest
from engine import atomic_json
from retirement import scope
import test_compat as native_tests
import test_dynamic as dynamic_tests
import test_processes as process_tests
from compat import game_user_id


class NativeHelpers:
    http = native_tests.CompatibilityTests.http
    np_connect = native_tests.CompatibilityTests.np_connect
    np_call = native_tests.CompatibilityTests.np_call

    def observe(self, client, **changes):
        body=dict(state=0, loading=False, bell=False, members=1, alive=True, fresh=True)
        body.update(changes)
        self.http(client, '/party/native', body, True)
        if not hasattr(self,'samples'): self.samples={}
        self.samples[client]=body

    def until(self, predicate, clients=(), timeout=10, refresh=()):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            for client in clients: self.observe(client)
            for client in refresh: self.observe(client,**self.samples[client])
            if predicate(): return
            time.sleep(.08)
        self.fail('Native retirement did not complete')

    def room(self, host, guests, names=None):
        names=names or {c.info['ready']:c.info['ready'] for c in [host,*guests]}
        self.assertEqual(self.http(host,'/party/acquire',control=True),b'1')
        sockets=[self.np_connect(c,names[c.info['ready']]) for c in [host,*guests]]
        self.addCleanup(lambda:[s.close() for s in sockets])
        rid=self.np_call(sockets[0],101,'CreateRoomRequest',{'max_slots':5},'CreateRoomReply')['room_id']
        for guest,sock in zip(guests,sockets[1:]):
            self.assertNotIn('error',host.op('claim',target=guest.info['ready'],claim={}))
            self.until(lambda:guest.state()['state']['owner']==host.info['ready'] and guest.state()['final']>=0)
            self.np_call(sock,102,'JoinRoomRequest',{'room_id':rid},'JoinRoomReply')
        self.observe(host,state=3,bell=True,members=1+len(guests))
        for guest in guests:self.observe(guest,state=6,members=1+len(guests))
        time.sleep(.2)
        return rid

    def travel_keeps_world(self, host, guests):
        old=host.state()['state']
        # Lamp departure: native membership/bell can clear before loading rises.
        self.observe(host,state=3,members=1)
        time.sleep(.4)
        self.assertEqual(host.state()['state'],old)
        self.observe(host,state=0,members=1,loading=True)
        time.sleep(.4)
        self.assertEqual(host.state()['state'],old)
        # The frame loop may be suspended for the whole Dream load. No fresh
        # observation means no evidence of a stopped host, regardless of duration.
        time.sleep(3.2)
        self.assertEqual(host.state()['state'],old)
        self.observe(host,state=0,members=1)
        time.sleep(.4)
        self.observe(host,state=3,bell=True,members=1+len(guests))
        end=time.monotonic()+3.3
        while time.monotonic()<end:
            self.observe(host,state=3,bell=True,members=1+len(guests))
            time.sleep(.2)
        for client in [host,*guests]:
            self.assertEqual(client.state()['state'],old)


class StaticRetirement(NativeHelpers, unittest.TestCase):
    setUp = process_tests.Tests.setUp
    tearDown = process_tests.Tests.tearDown
    group = process_tests.Tests.group
    start = process_tests.Tests.start
    settled = process_tests.Tests.settled

    def test_host_dream_reload_preserves_both_guests(self):
        a,b,c=self.group(3,compat=True)
        self.room(a,[b,c])
        self.travel_keeps_world(a,[b,c])

    def test_native_end_supersedes_partial_commit_and_late_final(self):
        a,b,c=self.group(3,compat=True)
        self.room(a,[b,c])
        self.assertEqual(a.state()['state']['revision']%3,0)
        a.call('fault',value=dict(drop_types=['commit']))
        # Keep the command outstanding through the new 3s confirmation window.
        b.send('command',op=dict(kind='member_update',bins=[]),timeout=8)
        self.until(lambda:a.state()['tx_phase']=='commit')
        proposal=json.loads((self.root/'A/party-journal.json').read_text())['tx']['proposal']
        c.kill()
        self.observe(a,state=3,members=1)
        self.until(lambda:a.state()['state']['owner'] is None,timeout=6,refresh=[a])
        self.until(lambda:b.state()['state']['owner'] is None)
        a.call('fault',value={})
        for kind in ('prepare','commit','final'):
            a.call('inject',target='B',message=dict(type=kind,proposal=proposal))
        time.sleep(.3)
        self.assertIsNone(b.state()['state']['owner'])
        c=self.start('C',compat=True)
        self.settled([a,b,c])

    def test_confirmed_host_role_loss_retires_even_with_residual_bell_effect(self):
        a,b=self.group(2,compat=True)
        self.room(a,[b])
        self.observe(a,state=0,bell=True,members=1)
        self.until(lambda:a.state()['state']['owner'] is None,timeout=6,refresh=[a])
        self.until(lambda:b.state()['state']['owner'] is None)

    def test_empty_host_retires_crashed_guest_and_old_certificate_cannot_reset_new_host(self):
        a,b,c=self.group(3,compat=True)
        self.room(a,[b,c])
        old=a.state()['state']
        c.kill()
        self.observe(a,state=3,members=1)
        self.until(lambda:a.state()['state']['owner'] is None,timeout=6,refresh=[a])
        self.until(lambda:b.state()['state']['owner'] is None)
        self.until(lambda:self.http(b,'/party/can_beckon',control=True)==b'1')
        certificate=json.loads((self.root/'A/party-journal.json').read_text())['native_retirements'][str(old['generation'])]
        c=self.start('C',compat=True)
        self.settled([a,b,c])
        self.assertNotIn('error',b.op('acquire'))
        self.settled([a,b,c])
        a.call('inject',target='B',message=dict(type='native_retirement',record=certificate))
        time.sleep(.3)
        self.assertEqual(b.state()['state']['owner'],'B')
        self.assertGreater(b.state()['state']['generation'],old['generation'])

    def test_bell_members_load_death_unknown_and_stale_observation_keep_binding(self):
        a,b=self.group(2,compat=True)
        self.room(a,[b])
        for changes in (dict(bell=True),dict(members=2),dict(loading=True),dict(alive=False),
                        dict(members=0),dict(fresh=False),dict(state=7)):
            self.observe(a,**dict(dict(state=3),**changes))
            time.sleep(.13)
            self.assertEqual(a.state()['state']['owner'],'A',changes)
        # A stale DLL sample, even repeated by its worker, is never proof.
        self.observe(a,state=3,fresh=False)
        time.sleep(1.6)
        self.assertEqual(a.state()['state']['owner'],'A')
        self.observe(a,state=3)
        self.until(lambda:a.state()['state']['owner'] is None,timeout=6,refresh=[a])

    def test_host_crash_releases_after_native_exit_without_host_vote_and_survives_restart(self):
        a,b,c=self.group(3,compat=True)
        self.room(a,[b,c]); a.kill()
        # A missing control connection alone cannot release a live native world.
        end=time.monotonic()+6.5
        while time.monotonic()<end:
            self.observe(b,state=6,members=3)
            time.sleep(.2)
        self.assertEqual(b.state()['state']['owner'],'A')
        self.observe(b)
        self.until(lambda:b.state()['state']['owner'] is None,clients=[b])
        self.until(lambda:c.state()['state']['owner'] is None)
        b.kill(); b=self.start('B',compat=True)
        self.assertIsNone(b.state()['state']['owner'])
        a=self.start('A',compat=True)
        self.settled([a,b,c])
        self.assertNotIn('error',b.op('acquire'))
        self.settled([a,b,c])

    def test_guest_leaving_live_host_does_not_retire_other_guest(self):
        a,b,c=self.group(3,compat=True)
        self.room(a,[b,c])
        self.assertNotIn('error',b.op('room_leave'))
        end=time.monotonic()+6.5
        while time.monotonic()<end:
            self.observe(a,state=3,bell=True,members=2)
            self.observe(b)
            time.sleep(.2)
        self.assertEqual(c.state()['state']['owner'],'A')
        self.assertIn('C',c.state()['state']['joined'])


class DynamicRetirement(NativeHelpers, dynamic_tests.DynamicHelpers, unittest.TestCase):
    client = dynamic_tests.DynamicNativeProcesses.client

    def setUp(self):
        super().setUp()
        self.clients=[]

    def tearDown(self):
        for client in self.clients:
            if client.p.poll() is None: client.kill()
        super().tearDown()

    def group_dynamic(self):
        a,b=self.client('A'),self.client('B')
        for who in 'AB':atomic_json(self.root/(who+'-peers.json'),self.offers)
        # Dynamic claims require the guest's own search sign.
        self.assertEqual(self.http(a,'/party/acquire',control=True),b'1')
        self.http(b,'/summon_messenger/create',dict(UserId=game_user_id('B'),CharaId=12,AreaId=23,
                  SummonData=base64.b64encode(bytes(224)).decode()))
        self.until(lambda:bool(json.loads(self.http(a,'/summon_messenger/get'))['SummonDataList']))
        self.room(a,[b],dict(A='HunterA',B='HunterB'))
        return a,b

    def test_host_empty_releases_room_and_guest_attachment(self):
        a,b=self.group_dynamic()
        self.observe(a,state=3)
        self.until(lambda:a.state()['state']['owner'] is None,timeout=6,refresh=[a])
        self.until(lambda:b.state()['state']['owner'] is None)
        self.assertEqual(self.http(b,'/party/can_beckon',control=True),b'1')

    def test_stopped_occupied_room_with_residual_bell_still_recovers(self):
        a,b=self.group_dynamic()
        self.observe(a,state=0,bell=True,members=1)
        self.until(lambda:a.state()['state']['owner'] is None,timeout=6,refresh=[a])
        self.until(lambda:b.state()['state']['owner'] is None)

    def test_host_dream_reload_preserves_guest_attachment(self):
        a,b=self.group_dynamic()
        self.travel_keeps_world(a,[b])

    def test_host_crash_detaches_guest_and_rejects_old_reservation(self):
        a,b=self.group_dynamic()
        path=self.root/'B/dynamic-journal.json'
        attached=json.loads(path.read_text())['attachment']
        a.kill()
        self.until(lambda:b.state()['state']['owner'] is None,clients=[b],timeout=12)
        disk=json.loads(path.read_text())
        self.assertIsNone(disk['attachment'])
        self.assertIn(attached['reservation'],disk['retired'])
        self.assertEqual(self.http(b,'/party/acquire',control=True),b'1')
        self.assertEqual(b.state()['state']['owner'],'B')


class ScopeTests(dynamic_tests.DynamicHelpers, unittest.TestCase):
    def test_retired_guest_reservation_and_late_snapshot_cannot_reattach(self):
        a,b=self.node('A'),self.node('B');self.discover()
        rid=self.host(a);self.claim(a,b)
        b.command(dict(kind='room_join',room_id=rid))
        self.eventually(lambda:b.state==a.state)
        old_world=a.world();witness=copy.deepcopy(b.state)
        old_reservation=copy.deepcopy(b.disk['attachment']['reservation'])
        b.retire_native('host_lost',scope(b.state),witness)
        with self.assertRaisesRegex(ValueError,'Unexpected world'):
            b.accept_world(old_world)
        with self.assertRaisesRegex(ValueError,'retired'):
            a.rpc('B',dict(kind='reserve',seq=old_reservation[-1],world=old_world))
        self.assertIsNone(b.state['owner'])

    def test_stale_native_scope_cannot_retire_new_world(self):
        a=self.node('A');self.host(a);old=scope(a.state)
        a.retire_native('host_empty',old)
        self.host(a)
        with self.assertRaisesRegex(ValueError,'Stale native session'):
            a.retire_native('host_empty',old)
        self.assertEqual(a.state['owner'],'A')
