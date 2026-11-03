"""Explicit menu/Blank cancellation must not poison a later admission."""
import json,time,unittest
from test_compat import CompatibilityTests
class MenuRejoinTests(CompatibilityTests):
    def setUp(self):
        from unittest.mock import patch
        import os
        mode=patch.dict(os.environ,BB_PARTY_DIAGNOSTICS='1')
        mode.start();self.addCleanup(mode.stop)
        super().setUp()
    def test_cancel_retired_after_guest_idle_and_final_leave(self):
        a,b=self.group(2,compat=True)
        def native(state,loading,cancel):
            self.http(b,'/party/native',{'state':state,'loading':loading,'bell':False,'cancel_seq':cancel},True)
        def retired(seq):
            p=self.root/'B/party-events.jsonl'
            return p.exists() and any(x.get('event')=='guest_cancel_retired' and x['cancel_seq']==seq for x in map(json.loads,p.read_text().splitlines()))
        def wait_retired(seq):
            end=time.monotonic()+5
            while time.monotonic()<end and not retired(seq):time.sleep(.05)
            self.assertTrue(retired(seq))
        with self.np_connect(a,'A') as sa,self.np_connect(b,'B') as sb:
            self.assertEqual(self.http(a,'/party/acquire',control=True),b'1')
            rid=self.np_call(sa,101,'CreateRoomRequest',{'max_slots':5},'CreateRoomReply')['room_id']
            a.op('claim',target='B',claim={})
            first=self.np_call(sb,102,'JoinRoomRequest',{'room_id':rid},'JoinRoomReply')['member_id']
            native(6,False,0)
            native(6,True,1) # menu: cancellation during saved-world transition
            self.np_call(sb,103,'LeaveRoomRequest',{'room_id':rid},'LeaveRoomReply')
            time.sleep(.2);self.assertFalse(retired(1)) # native loading remains a barrier
            native(0,False,1);wait_retired(1)
            self.np_call(sa,103,'LeaveRoomRequest',{'room_id':rid},'LeaveRoomReply')
            rid=self.np_call(sa,101,'CreateRoomRequest',{'max_slots':5},'CreateRoomReply')['room_id']
            a.op('claim',target='B',claim={})
            time.sleep(.3) # old monitor bug cancelled the new claim here
            self.assertIn('B',a.state()['state']['pending'])
            second=self.np_call(sb,102,'JoinRoomRequest',{'room_id':rid},'JoinRoomReply')['member_id']
            time.sleep(.2);self.assertIn('B',a.state()['state']['joined'])
            native(6,False,1);native(6,True,2)
            self.np_call(sb,103,'LeaveRoomRequest',{'room_id':rid},'LeaveRoomReply')
            native(0,False,2);wait_retired(2)
            a.op('claim',target='B',claim={})
            native(0,True,3);time.sleep(.2)
            self.assertIn('B',a.state()['state']['pending'])
            native(0,False,3)
            end=time.monotonic()+5
            while time.monotonic()<end and 'B' in a.state()['state']['pending']:time.sleep(.05)
            self.assertNotIn('B',a.state()['state']['pending'])
            wait_retired(3)
