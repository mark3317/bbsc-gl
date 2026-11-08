"""Host rotation, failed admission withdrawal and guest cancellation over real sockets."""
import base64,json,time,unittest
from test_compat import CompatibilityTests

class HostRotationTests(CompatibilityTests):
    def setUp(self):
        from unittest.mock import patch
        import os
        mode=patch.dict(os.environ,BB_PARTY_DIAGNOSTICS='1')
        mode.start();self.addCleanup(mode.stop)
        super().setUp()
    def test_former_host_sign_returned_after_rotation_with_another_guest(self):
        a,b,c=self.group(3,compat=True)
        with self.np_connect(a,'A') as sa,self.np_connect(b,'B') as sb,self.np_connect(c,'C') as sc:
            self.assertEqual(self.http(a,'/party/acquire',control=True),b'1')
            first=self.np_call(sa,101,'CreateRoomRequest',{'max_slots':5},'CreateRoomReply')['room_id']
            self.np_call(sa,103,'LeaveRoomRequest',{'room_id':first},'LeaveRoomReply')
            a.op('release');self.settled([a,b,c])
            self.assertEqual(self.http(c,'/party/acquire',control=True),b'1')
            second=self.np_call(sc,101,'CreateRoomRequest',{'max_slots':5},'CreateRoomReply')['room_id']
            c.op('claim',target='B',claim={})
            self.np_call(sb,102,'JoinRoomRequest',{'room_id':second},'JoinRoomReply')
            self.settled([a,b,c])
            sign={'AreaId':230010,'SummonData':base64.b64encode(bytes(224)).decode()}
            self.http(a,'/summon_messenger/create',sign)
            deadline=time.monotonic()+4
            while time.monotonic()<deadline:
                found=json.loads(self.http(c,'/summon_messenger/get'))['SummonDataList']
                if found:break
                time.sleep(.05)
            self.assertEqual(len(found),1)
            self.assertEqual(found[0]['AreaId'],230010)
            self.assertEqual(base64.b64decode(found[0]['SummonData'])[0x79],1)
            events=[json.loads(line) for line in (self.root/'C/party-events.jsonl').read_text().splitlines()]
            searches=[e for e in events if e['event']=='sign_search']
            self.assertTrue(any(e['returned']==1 and
                any(p[:2]==['A','returned'] for p in e['candidates']) for e in searches))
            # A real request must reach the former host; no synthetic invitation.
            from compat import game_user_id
            self.http(c,'/summon_messenger/request',{'TargetUserId':game_user_id('A'),'HostData':'new-owner'})
            self.assertIn('A',self.settled([a,b,c])[0]['state']['pending'])
            self.assertEqual(json.loads(self.http(a,'/summon_messenger/create',sign))['HostData'],'new-owner')

    def wait_for(self, clients, predicate):
        end=time.monotonic()+7
        while time.monotonic()<end:
            states=self.settled(clients)
            if predicate(states[0]['state']): return states[0]['state']
            time.sleep(.05)
        self.fail('Lifecycle did not drain')

    def test_rotation_with_failed_claim_and_quit_during_join(self):
        a,b,c=self.group(3,compat=True)
        clients=[a,b,c]
        def native(client,state,cancel=0,loading=False):
            return self.http(client,'/party/tick',dict(state=state,loading=loading,
                bell=False,cancel_seq=cancel,await_title=bool(cancel)),True)
        with self.np_connect(a,'A') as sa,self.np_connect(b,'B') as sb,self.np_connect(c,'C') as sc:
            native(a,0);native(b,0);native(c,0)
            self.assertEqual(self.http(b,'/party/acquire',control=True),b'1')
            first=self.np_call(sb,101,'CreateRoomRequest',{'max_slots':5},'CreateRoomReply')['room_id']
            b.op('claim',target='C',claim={'HostData':'first'})
            self.np_call(sc,102,'JoinRoomRequest',{'room_id':first},'JoinRoomReply')
            native(b,3);native(c,6)
            self.np_call(sb,103,'LeaveRoomRequest',{'room_id':first},'LeaveRoomReply')
            native(b,0,1);native(c,0)
            self.wait_for(clients,lambda s:s['owner'] is None)
            self.assertEqual(self.http(a,'/party/acquire',control=True),b'1')
            second=self.np_call(sa,101,'CreateRoomRequest',{'max_slots':5},'CreateRoomReply')['room_id']
            self.assertNotEqual(first,second)
            a.op('claim',target='C',claim={'HostData':'retry'})
            ticket=a.state()['state']['pending']['C']['ticket']
            # A withdrawal before this claim was delivered cannot cancel it.
            self.http(c,'/summon_messenger/delete',{'Force':True})
            self.assertIn('C',a.state()['state']['pending'])
            self.http(c,'/summon_messenger/create',{})
            # Plain sign refresh and an ongoing native join are protected.
            self.http(c,'/summon_messenger/delete',{})
            self.assertIn('C',a.state()['state']['pending'])
            native(c,4)
            self.http(c,'/summon_messenger/delete',{'Force':True})
            self.assertIn('C',a.state()['state']['pending'])
            native(c,0,loading=True)
            self.http(c,'/summon_messenger/delete',{'Force':True})
            self.assertIn('C',a.state()['state']['pending'])
            native(c,0)
            self.http(c,'/summon_messenger/delete',{'Force':True})
            self.wait_for(clients,lambda s:'C' not in s['pending'])
            self.assertEqual(a.state()['state']['owner'],'A')
            a.op('claim',target='C',claim={'HostData':'fresh'})
            self.assertIn('error',c.op('admission_cancel',ticket=ticket))
            self.assertIn('C',a.state()['state']['pending'])
            self.np_call(sc,102,'JoinRoomRequest',{'room_id':second},'JoinRoomReply')
            native(a,3);native(c,4)
            # Stop alone/state7 cannot grant title or remove a live guest.
            self.assertEqual(native(c,7,1),b'0 0')
            time.sleep(.2);self.assertIn('C',a.state()['state']['joined'])
            # A confirmed cancel + actual native idle drains membership even
            # when owner has not closed the room; it does not release owner A.
            native(c,0,1)
            self.wait_for(clients,lambda s:'C' not in s['joined'])
            self.assertEqual(native(c,0,1),b'0 1')
            self.assertEqual(a.state()['state']['owner'],'A')
            self.assertEqual(a.state()['state']['room']['id'],second)
            self.np_call(sa,103,'LeaveRoomRequest',{'room_id':second},'LeaveRoomReply')
            native(a,0,1)
            self.wait_for(clients,lambda s:s['owner'] is None)

if __name__=='__main__':
    unittest.main(defaultTest='HostRotationTests.test_rotation_with_failed_claim_and_quit_during_join')
