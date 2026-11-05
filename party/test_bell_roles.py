"""Real dynamic RPC/bridge role changes, using isolated loopback journals."""
import base64
import copy
import time
import unittest

from compat import Compatibility, game_user_id
from test_dynamic import DynamicHelpers


class BellRoles(DynamicHelpers, unittest.TestCase):
    def test_yield_survives_winning_host_crash_until_local_bell_stops(self):
        b=self.bridge('B')
        self.config('A'); self.discover()
        self.assertEqual(b.control('/party/acquire',{}),1)
        with b.e.lock:
            b.e.signs['A']=dict(at=time.monotonic(),body={},host=dict(owner='A',occupied=False))
        self.assertEqual(self.tick(b,bell=True)[-1],2)
        with b.e.lock: b.e.signs.pop('A')
        self.assertEqual(self.tick(b,bell=True)[-1],2)
        self.assertEqual(b.control('/party/acquire',{}),0)
        self.tick(b,cancel_seq=1)
        self.until(lambda:b.e.state['owner'] is None,[(b,dict(cancel_seq=1))])
        self.assertEqual(b.control('/party/acquire',{}),1)

    def test_cancelling_host_reports_bell_unavailable_during_load(self):
        b=self.bridge('B')
        self.assertEqual(b.control('/party/acquire',{}),1)
        self.assertEqual(self.tick(b,loading=True,cancel_seq=1)[0],0)
        self.assertEqual(b.control('/party/can_beckon',{}),0)
        self.assertEqual(b.control('/party/acquire',{}),0)
    def setUp(self):
        super().setUp()
        self.bridges = []

    def tearDown(self):
        for bridge in self.bridges:
            bridge.close()
            self.engines.remove(bridge.e)
        super().tearDown()

    def bridge(self, who):
        bridge = Compatibility(self.node(who)).start()
        self.bridges.append(bridge)
        return bridge

    def tick(self, bridge, **changes):
        body = dict(state=0, loading=False, bell=False, responder=False,
                    members=1, alive=True, fresh=True, bell_notice=True,
                    bell_release=True, host_check=True)
        body.update(changes)
        return list(map(int, bridge.control('/party/tick', body).split()))

    def until(self, condition, refresh=()):
        def step():
            for bridge, sample in refresh:
                self.tick(bridge, **sample)
            return condition()
        self.eventually(step)

    def test_switch_to_responder_releases_never_hosted_search_and_admits(self):
        a, b = self.bridge('A'), self.bridge('B')
        self.discover()
        # Both native callers acquired before either rang, as in the live run.
        self.assertEqual(a.control('/party/acquire', {}), 1)
        self.assertEqual(b.control('/party/acquire', {}), 1)
        self.tick(a, bell=True)
        self.tick(b, bell=True)
        sign = dict(UserId=game_user_id('B'), SummonData=base64.b64encode(bytes(224)).decode())
        b.http_call('/summon_messenger/create', sign, {})
        self.until(lambda: a.e.signs.get('B', {}).get('body', {}).get('sign') is None)
        self.tick(b, responder=True)  # No Blank callback or cancel_seq required.
        self.until(lambda: b.e.state['owner'] is None,
                   [(a, dict(bell=True)), (b, dict(responder=True))])
        # Native Small Bell refresh publishes after the old host role drains;
        # a create sent while still hosting is deliberately withheld.
        b.http_call('/summon_messenger/create', sign, {})
        self.until(lambda: bool(a.http_call('/summon_messenger/get', {}, {})['SummonDataList']),
                   [(a, dict(bell=True)), (b, dict(responder=True))])
        room = a.np_command(101, dict(max_slots=5))['room_id']
        a.http_call('/summon_messenger/request', dict(TargetUserId=game_user_id('B')), {})
        self.until(lambda: b.e.finalized() and b.e.state['owner']=='A')
        self.assertEqual(b.np_command(102, dict(room_id=room))['details']['room_data']['room_id'], room)

    def test_world_load_sees_existing_host_and_acquire_is_denied(self):
        a = self.bridge('A')
        self.assertEqual(a.control('/party/acquire', {}), 1)
        self.tick(a, bell=True)
        b = self.bridge('B')
        self.discover()
        self.until(lambda: self.tick(b)[-1] == 1, [(a, dict(bell=True))])
        self.assertEqual(self.tick(b)[0], 0)
        self.assertEqual(b.control('/party/can_beckon', {}), 0)
        self.assertEqual(b.control('/party/acquire', {}), 0)
        self.assertIsNone(b.e.state['owner'])
        # Loss of fresh presence removes the hint, never fabricates an owner.
        with b.e.lock:
            b.e.signs['A']['at'] = time.monotonic()-3
            self.assertIsNone(b.e.preferred_host())

    def test_responder_to_host_ignores_old_sample_withdraws_sign_and_blocks_peers(self):
        a, b = self.bridge('A'), self.bridge('B')
        self.discover()
        self.tick(b, responder=True)
        sign = dict(UserId=game_user_id('B'), SummonData=base64.b64encode(bytes(224)).decode())
        b.http_call('/summon_messenger/create', sign, {})
        self.assertEqual(b.control('/party/acquire', {}), 1)
        generation = b.e.state['generation']
        self.assertIsNone(b.e.local_status['sign'])
        # Reproduce the live ordering: the worker already granted Beckoning,
        # but several native samples still report the OLD Small Bell.
        for _ in range(8):
            self.tick(b, responder=True)
            time.sleep(.07)
        self.assertEqual(b.e.state['owner'], 'B')
        self.assertEqual(b.e.state['generation'], generation)
        # An in-flight Small Bell refresh must not republish the sign.
        b.http_call('/summon_messenger/create', sign, {})
        self.assertIsNone(b.e.local_status['sign'])
        self.until(lambda: self.tick(a)[-1] == 1, [(b, dict(responder=True))])
        self.assertEqual(a.control('/party/can_beckon', {}), 0)
        self.assertEqual(a.control('/party/acquire', {}), 0)
        # Once the NEW host bell was observed, a subsequent deliberate switch
        # back to Small Bell must still release the correct generation.
        self.tick(b, bell=True)
        self.tick(b, responder=True)
        self.until(lambda: b.e.state['owner'] is None, [(b, dict(responder=True))])

    def test_failed_host_application_can_cancel_before_first_beckoning_sample(self):
        b = self.bridge('B')
        self.tick(b, responder=True)
        self.assertEqual(b.control('/party/acquire', {}), 1)
        self.tick(b, cancel_seq=1)
        self.until(lambda: b.e.state['owner'] is None, [(b, dict(cancel_seq=1))])

    def test_join_consumes_sign_and_old_create_cannot_restart_after_home_return(self):
        a, b = self.bridge('A'), self.bridge('B')
        self.discover()
        self.assertEqual(a.control('/party/acquire', {}), 1)
        self.tick(a, bell=True)
        self.tick(b, responder=True)
        sign = dict(UserId=game_user_id('B'), SummonData=base64.b64encode(bytes(224)).decode())
        b.http_call('/summon_messenger/create', sign, {})
        room = a.np_command(101, dict(max_slots=5))['room_id']
        a.e.command(dict(kind='claim', target='B', claim={}))
        self.until(lambda: b.e.finalized() and b.e.state['owner']=='A')
        b.np_command(102, dict(room_id=room))
        self.assertIsNone(b.e.local_status['sign'])
        self.tick(b, state=6, members=2, responder=False)
        b.http_call('/summon_messenger/create', sign, {})
        self.assertIsNone(b.e.local_status['sign'])
        b.np_command(103, dict(room_id=room))
        self.until(lambda: b.e.state['owner'] is None)
        self.tick(b, responder=True)  # residual native search, before cleanup
        b.http_call('/summon_messenger/create', sign, {})
        self.assertIsNone(b.e.local_status['sign'])
        self.tick(b, responder=False) # actual cleared return to personal world
        b.http_call('/summon_messenger/create', sign, {})
        self.assertIsNone(b.e.local_status['sign'])
        self.assertNotIn('B', a.e.state['pending'])
        self.tick(b, responder=True)  # new deliberate Small Bell action
        b.http_call('/summon_messenger/create', sign, {})
        self.assertEqual(b.e.local_status['sign'], sign)

    def test_drained_host_search_keeps_role_blocks_other_host_and_accepts_new_guest(self):
        a, b = self.bridge('A'), self.bridge('B')
        self.discover()
        self.assertEqual(a.control('/party/acquire', {}), 1)
        generation = a.e.state['generation']
        room = a.np_command(101, dict(max_slots=5))['room_id']
        self.tick(b, responder=True)
        sign = dict(UserId=game_user_id('B'))
        b.http_call('/summon_messenger/create', sign, {})
        a.e.command(dict(kind='claim', target='B', claim={}))
        self.until(lambda: b.e.finalized() and b.e.state['owner']=='A')
        b.np_command(102, dict(room_id=room))
        self.tick(a, state=3, bell=True, members=2)
        self.tick(b, state=6, members=2)
        b.np_command(103, dict(room_id=room))
        self.until(lambda: not a.e.state['joined'])
        a.np_command(103, dict(room_id=room))
        self.tick(a, state=3, bell=True) # ordinary last-guest room teardown
        time.sleep(.15)
        end = time.monotonic()+3.5
        while time.monotonic()<end:
            self.tick(a, bell=True)
            self.tick(b)
            time.sleep(.08)
        self.assertEqual(a.e.state['owner'], 'A')
        self.assertEqual(a.e.state['generation'], generation)
        self.assertEqual(a.e.host_presence()['owner'], 'A')
        self.assertEqual(b.control('/party/can_beckon', {}), 0)
        self.assertEqual(b.control('/party/acquire', {}), 0)
        # A new guest joins the same search without another Beckoning action.
        self.tick(b, responder=True)
        b.http_call('/summon_messenger/create', sign, {})
        new_room = a.np_command(101, dict(max_slots=5))['room_id']
        a.e.command(dict(kind='claim', target='B', claim={}))
        self.until(lambda: b.e.finalized() and b.e.state['owner']=='A')
        b.np_command(102, dict(room_id=new_room))
        self.assertEqual(a.e.state['generation'], generation)
        # Explicit silence still drains the role and enables the next host.
        b.np_command(103, dict(room_id=new_room))
        self.until(lambda: not a.e.state['joined'])
        a.np_command(103, dict(room_id=new_room))
        self.tick(a, cancel_seq=1)
        self.until(lambda: a.e.state['owner'] is None, [(a, dict(cancel_seq=1))])
        self.until(lambda: b.e.preferred_host() is None)
        self.assertEqual(b.control('/party/acquire', {}), 1)

    def test_simultaneous_bells_choose_one_empty_host_then_join_hint_after_release(self):
        a, b = self.bridge('A'), self.bridge('B')
        self.discover()
        for bridge in (a,b):
            self.assertEqual(bridge.control('/party/acquire', {}), 1)
        self.until(lambda: self.tick(b, bell=True)[-1] == 2,
                   [(a, dict(bell=True)), (b, dict(bell=True))])
        self.assertEqual(self.tick(a, bell=True)[-1], 0)
        self.assertEqual(self.tick(a, bell=True)[0], 1)
        with self.assertRaisesRegex(ValueError, 'yielding'):
            b.np_command(101, dict(max_slots=5))
        self.tick(b, cancel_seq=1)
        self.until(lambda: b.e.state['owner'] is None,
                   [(a, dict(bell=True)), (b, dict(cancel_seq=1))])
        self.assertEqual(self.tick(b)[-1], 1)

    def test_responder_cannot_release_loading_dead_unknown_or_reserved_world(self):
        b = self.bridge('B')
        self.assertEqual(b.control('/party/acquire', {}), 1)
        before = copy.deepcopy(b.e.state)
        for changes in [dict(loading=True), dict(alive=False), dict(fresh=False), dict(members=0),
                        dict(state=4), dict(bell=True), dict(responder=False)]:
            for _ in range(3):
                self.tick(b, **(dict(responder=True) | changes))
                time.sleep(.07)
            self.assertEqual(b.e.state, before)
        # Even a local empty native room has a real lifetime, not a search lease.
        b.np_command(101, dict(max_slots=5))
        before = copy.deepcopy(b.e.state)
        for _ in range(5):
            self.tick(b, responder=True)
            time.sleep(.07)
        self.assertEqual(b.e.state, before)

    def test_existing_room_never_yields_to_second_host(self):
        a, b = self.bridge('A'), self.bridge('B')
        self.discover()
        for bridge in (a,b):
            self.assertEqual(bridge.control('/party/acquire', {}), 1)
        b.np_command(101, dict(max_slots=5))
        self.until(lambda: self.tick(a, bell=True)[-1] == 2,
                   [(a, dict(bell=True)), (b, dict(state=3, bell=True))])
        self.assertEqual(self.tick(b, state=3, bell=True)[-1], 0)
        self.assertIsNotNone(b.e.state['room'])

    def test_pending_admission_and_host_load_keep_authority(self):
        a, b, c = self.bridge('A'), self.bridge('B'), self.bridge('C')
        self.discover()
        self.assertEqual(b.control('/party/acquire', {}), 1)
        self.tick(b, bell=True)
        c.e.publish(dict(sign=dict(UserId=game_user_id('C'))))
        b.e.command(dict(kind='claim', target='C', claim={}))
        before = copy.deepcopy(b.e.state)
        for _ in range(5):
            self.tick(b, responder=True)
            time.sleep(.07)
        self.assertEqual(b.e.state, before)
        # World loading can clear the native bell/role before Party membership.
        self.until(lambda: self.tick(a)[-1] == 1,
                   [(b, dict(loading=True))])
        self.assertEqual(a.control('/party/acquire', {}), 0)


if __name__ == '__main__':
    unittest.main()
