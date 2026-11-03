"""The real party allocator and protobuf replies must use shadNet native member IDs."""
import unittest
import time
from collections import defaultdict
from types import SimpleNamespace
from engine import initial, invite, transition
from compat import Compatibility
import test_compat


class NativeMemberIdsTests(unittest.TestCase):
    def test_allocator_reuses_places_and_changes_incarnation_across_generation_wrap(self):
        members = [dict(id=p, host='127.0.0.1', port=38000+i, p2p=39000+i)
                   for i, p in enumerate('ABCDE')]
        cfg = invite(members)
        state, sequence = initial(cfg), defaultdict(int)

        def command(who, kind, **args):
            nonlocal state
            sequence[who] += 1
            state = transition(state, who, sequence[who], dict(kind=kind, **args))

        command('A', 'acquire')
        command('A', 'room_create', room=dict(max_slots=5, world=1, bins=[], flags=0, member_bins=[]))
        room_id = state['room']['id']
        self.assertEqual(state['room']['members']['A']['slot'], 17)
        for who, expected in zip('BCDE', [34, 51, 68, 85]):
            command('A', 'claim', target=who, claim={})
            command(who, 'room_join', room_id=room_id)
            self.assertEqual(state['room']['members'][who]['slot'], expected)
        identities = {p: m['slot'] for p, m in state['room']['members'].items()}
        old_dates = set()
        for _ in range(100):
            command('B', 'room_leave')
            command('A', 'claim', target='B', claim={})
            command('B', 'room_join', room_id=room_id)
            adapter = Compatibility.__new__(Compatibility)
            adapter.e = SimpleNamespace(id='A', state=state,
                                        members={m['id']: m for m in members})
            result = adapter.room_details(state)
            ids = {m['npid']: m['member_id'] for m in result['members']}
            # Same decoder as packaged shadNet's allocMemberId/native allocator fixture.
            self.assertEqual(sorted(value >> 4 for value in ids.values()), [1, 2, 3, 4, 5])
            self.assertEqual(ids['B'] >> 4, 2)
            self.assertEqual(result['room_data']['joined_slot_mask'], 31)
            for p in 'ACDE':
                self.assertEqual(ids[p], identities[p])
            date = next(m['join_date'] for m in result['members'] if m['npid'] == 'B')
            self.assertNotIn(date, old_dates)
            old_dates.add(date)

    def test_legacy_live_room_is_not_rewritten_and_can_drain(self):
        cfg = invite([dict(id=p, host='127.0.0.1', port=38000+i, p2p=39000+i)
                      for i, p in enumerate('AB')])
        state = initial(cfg)
        state = transition(state, 'A', 1, dict(kind='acquire'))
        state = transition(state, 'A', 2, dict(kind='room_create', room=dict(max_slots=5, bins=[], member_bins=[])))
        state['room'].pop('member_id_layout')
        state['room']['members']['A'] = dict(slot=1, bins=[])
        state = transition(state, 'A', 3, dict(kind='claim', target='B', claim={}))
        with self.assertRaisesRegex(ValueError, 'Legacy native room'):
            transition(state, 'B', 1, dict(kind='room_join', room_id=state['room']['id']))
        self.assertEqual(state['room']['members']['A']['slot'], 1)
        state = transition(state, 'B', 1, dict(kind='admission_cancel'))
        state = transition(state, 'A', 4, dict(kind='room_leave'))
        state = transition(state, 'A', 5, dict(kind='release'))
        self.assertIsNone(state['owner'])

    def test_three_real_native_api_clients_receive_correct_ids_and_slot_mask(self):
        probe = test_compat.CompatibilityTests('runTest')
        probe.setUp()
        try:
            a, b, c = probe.group(3, compat=True)
            with probe.np_connect(a, 'A') as sa, probe.np_connect(b, 'B') as sb, probe.np_connect(c, 'C') as sc:
                self.assertEqual(probe.http(a, '/party/acquire', control=True), b'1')
                created = probe.np_call(sa, 101, 'CreateRoomRequest',
                                       {'max_slots': 5}, 'CreateRoomReply')
                rid = created['room_id']
                a.op('claim', target='B', claim={})
                first = probe.np_call(sb, 102, 'JoinRoomRequest', {'room_id': rid}, 'JoinRoomReply')
                a.op('claim', target='C', claim={})
                second = probe.np_call(sc, 102, 'JoinRoomRequest', {'room_id': rid}, 'JoinRoomReply')
                self.assertEqual(first['member_id'], 34)
                self.assertEqual(second['member_id'], 51)
                members = second['details']['members']
                self.assertEqual(sorted(m['member_id'] >> 4 for m in members), [1, 2, 3])
                self.assertEqual(second['details']['room_data']['joined_slot_mask'], 7)
        finally:
            probe.tearDown()

    def test_host_blank_requires_real_native_idle_before_another_beckoner(self):
        probe = test_compat.CompatibilityTests('runTest')
        probe.setUp()
        try:
            a, b, c = probe.group(3, compat=True)
            def native(client, state, bell=False, cancel=0):
                probe.http(client, '/party/tick', dict(state=state, loading=False,
                    bell=bell, cancel_seq=cancel, await_title=False), True)
            with probe.np_connect(a, 'A') as sa, probe.np_connect(b, 'B') as sb, probe.np_connect(c, 'C'):
                native(a, 0); native(b, 0); native(c, 0)
                self.assertEqual(probe.http(a, '/party/acquire', control=True), b'1')
                rid = probe.np_call(sa, 101, 'CreateRoomRequest', {'max_slots': 5}, 'CreateRoomReply')['room_id']
                a.op('claim', target='B', claim={})
                probe.np_call(sb, 102, 'JoinRoomRequest', {'room_id': rid}, 'JoinRoomReply')
                native(a, 3, True); native(b, 6)
                a.op('claim', target='C', claim={'HostData':'failed'})
                probe.http(c, '/summon_messenger/create', {})
                native(a, 3, False, 1)  # Blank stops search; native is not idle yet.
                self.assertEqual(probe.http(b, '/party/acquire', control=True), b'0')
                probe.np_call(sa, 103, 'LeaveRoomRequest', {'room_id': rid}, 'LeaveRoomReply')
                probe.np_call(sb, 103, 'LeaveRoomRequest', {'room_id': rid}, 'LeaveRoomReply')
                native(b, 0)
                # Closing-room maintenance drains the failed idle admission.
                # A concurrent Force delete would legitimately race that drain.
                native(a, 7, False, 1)
                time.sleep(.25)
                self.assertEqual(a.state()['state']['owner'], 'A')
                native(a, 0, False, 1)
                end = time.monotonic() + 6
                while time.monotonic() < end:
                    states = probe.settled([a, b, c])
                    if states[0]['state']['owner'] is None:
                        break
                    time.sleep(.05)
                self.assertTrue(all(s['state']['owner'] is None and s['state']['room'] is None for s in states))
                self.assertEqual(probe.http(b, '/party/acquire', control=True), b'1')
        finally:
            probe.tearDown()


if __name__ == '__main__':
    unittest.main(verbosity=2)
