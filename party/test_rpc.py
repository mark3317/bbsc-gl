"""Combined bridge RPC, HTTP pooling and final leave checks without native builds."""
import http.client,json,socket,time,unittest,threading
from test_compat import CompatibilityTests
class ClaimRetryLimits(unittest.TestCase):
    def test_timeout_is_bounded_and_never_submits_another_claim(self):
        from unittest.mock import Mock,call
        from compat import Compatibility
        bridge=Compatibility.__new__(Compatibility)
        bridge.e=Mock()
        bridge.e.request.return_value=17
        bridge.e.wait.side_effect=TimeoutError('confirmation unavailable')
        bridge.log=Mock()
        with self.assertRaises(TimeoutError):bridge.command('claim',target='B',claim={})
        bridge.e.request.assert_called_once()
        self.assertEqual(bridge.e.wait.call_args_list,[call(17,8),call(17,8)])

    def test_rejection_and_other_operations_are_not_retried(self):
        from unittest.mock import Mock
        from compat import Compatibility
        for kind,error in [('claim',ValueError('room closed')),('room_leave',TimeoutError())]:
            with self.subTest(kind=kind):
                bridge=Compatibility.__new__(Compatibility)
                bridge.e=Mock()
                bridge.e.wait.side_effect=error
                bridge.log=Mock()
                with self.assertRaises(type(error)):bridge.command(kind)
                bridge.e.request.assert_called_once()
                bridge.e.wait.assert_called_once()

class RPCTests(CompatibilityTests):
    def test_claim_recovers_confirmation_after_first_deadline(self):
        a,b=self.group(2,compat=True)
        a.op('acquire')
        a.op('room_create',room={'max_slots':5,'world':1,'bins':[],'flags':0,'member_bins':[]})
        self.settled()
        before=a.state()['state']['revision']
        b.call('block',peers=['A'])
        recovery=threading.Timer(9,lambda:b.call('block',peers=[]))
        recovery.start()
        try:
            from compat import game_user_id
            started=time.monotonic()
            answer=json.loads(self.http(a,'/summon_messenger/request',{'TargetUserId':game_user_id('B')}))
            self.assertEqual(answer['ResKind'],0)
            self.assertGreaterEqual(time.monotonic()-started,8)
            self.settled()
            state=a.state()['state']
            self.assertEqual(state['revision'],before+1)
            self.assertIn('B',state['pending'])
        finally:
            recovery.join()
            b.call('block',peers=[])

    def test_combined_status_keepalive_and_current_title_ticket(self):
        a,b=self.group(2,compat=True)
        connection=http.client.HTTPConnection('127.0.0.1',b.info['http'],timeout=5)
        def tick(cancel,awaiting):
            body={'state':0,'loading':False,'bell':False,'cancel_seq':cancel,'await_title':awaiting}
            connection.request('POST','/party/tick',json.dumps(body),{'Content-Type':'application/json','X-BBSC-Party':b.info['token']})
            response=connection.getresponse();self.assertEqual(response.status,200);self.assertEqual(response.version,11)
            return response.read().decode()
        try:
            self.assertEqual(tick(0,False),'1 0');sock=connection.sock
            self.assertEqual(tick(1,False),'1 0');self.assertIs(connection.sock,sock)
            self.assertEqual(tick(1,True),'1 1')
            self.assertEqual(tick(2,False),'1 0') # Blank alone never keeps polling title
            self.assertEqual(tick(2,True),'1 2') # new ticket, not an earlier ACK
            a.op('acquire')
            rid=a.op('room_create',room={'max_slots':5,'world':1,'bins':[],'flags':0,'member_bins':[]})['result']
            a.op('claim',target='B',claim={});b.op('room_join',room_id=rid)
            self.assertEqual(tick(3,True),'0 3') # title unload does not release the group
            b.call('block',peers=['A']);ticket=b.send('command',op={'kind':'room_leave'})
            time.sleep(.3);self.assertEqual(tick(3,True),'0 3')
            b.call('block',peers=[]);self.assertNotIn('error',b.get(ticket))
            self.assertEqual(tick(3,True),'0 3')
        finally:connection.close()
    def test_title_with_offline_peer_keeps_unresolved_membership(self):
        a,b=self.group(2,compat=True)
        a.op('acquire')
        rid=a.op('room_create',room={'max_slots':5,'world':1,'bins':[],'flags':0,'member_bins':[]})['result']
        a.op('claim',target='B',claim={});b.op('room_join',room_id=rid)
        self.settled();a.kill()
        body=dict(state=0,loading=False,bell=False,cancel_seq=1,await_title=True)
        self.assertEqual(self.http(b,'/party/tick',body,True),b'0 1')
        time.sleep(.5)
        snap=b.state()['state']
        self.assertEqual(snap['owner'],'A');self.assertIn('B',snap['joined'])
        self.assertEqual(self.http(b,'/party/can_beckon',{},True),b'0')
        for state,loading in [(7,False),(6,False),(0,True)]:
            body.update(state=state,loading=loading)
            self.assertEqual(self.http(b,'/party/tick',body,True),b'0 0')
        body.update(state=0,loading=False,cancel_seq=2,await_title=False)
        self.assertEqual(self.http(b,'/party/tick',body,True),b'0 0')
        body['await_title']=True
        self.assertEqual(self.http(b,'/party/tick',body,True),b'0 2')

    def test_host_menu_retained_bell_waits_for_guest_then_releases(self):
        a,b=self.group(2,compat=True)
        self.http(a,'/party/acquire',control=True)
        with self.np_connect(a,'A') as sa,self.np_connect(b,'B') as sb:
            rid=self.np_call(sa,101,'CreateRoomRequest',{'max_slots':5},'CreateRoomReply')['room_id']
            a.op('claim',target='B',claim={});self.np_call(sb,102,'JoinRoomRequest',{'room_id':rid},'JoinRoomReply')
            body={'state':0,'loading':False,'bell':True,'cancel_seq':1,'await_title':False}
            self.http(a,'/party/tick',body,True);time.sleep(.15)
            self.assertEqual(a.state()['state']['owner'],'A') # ringing/idle alone is not enough
            body['await_title']=True;body['loading']=True
            self.assertEqual(self.http(a,'/party/tick',body,True),b'0 0')
            body['loading']=False
            self.np_call(sa,103,'LeaveRoomRequest',{'room_id':rid},'LeaveRoomReply')
            self.assertEqual(self.http(a,'/party/tick',body,True),b'0 1')
            self.assertIn('B',a.state()['state']['joined'])
            self.np_call(sb,103,'LeaveRoomRequest',{'room_id':rid},'LeaveRoomReply')
            end=time.monotonic()+5;answer=b''
            while time.monotonic()<end:
                answer=self.http(a,'/party/tick',body,True)
                if answer==b'1 1' and a.state()['state']['owner'] is None:break
                time.sleep(.05)
            self.assertEqual(answer,b'1 1')
            self.assertIsNone(a.state()['state']['owner']);self.assertIsNone(a.state()['state']['room'])
            body['cancel_seq']=2;body['loading']=True
            self.assertEqual(self.http(a,'/party/tick',body,True),b'1 0')
    def test_bell_notice_generation_excludes_host_and_legacy_reply(self):
        a,b,c=self.group(3,compat=True)
        body=dict(state=0,loading=False,bell=False,cancel_seq=0,bell_notice=True)
        def ticks():
            return [self.http(client,'/party/tick',body,True).decode() for client in (a,b,c)]
        self.assertEqual(ticks(),['1 0 0']*3)
        a.op('acquire');self.settled()
        self.assertEqual(ticks(),['1 0 0','0 0 1','0 0 1'])
        self.assertEqual(ticks(),['1 0 0','0 0 1','0 0 1'])
        self.assertEqual(self.http(b,'/party/tick',dict(body,bell_notice=False),True),b'0 0')
        a.op('release');self.settled()
        self.assertEqual(ticks(),['1 0 0']*3)
        c.op('acquire');self.settled()
        self.assertEqual(ticks(),['0 0 2','0 0 2','1 0 0'])

    def test_bell_release_is_explicit_final_and_legacy_compatible(self):
        a,b,c=self.group(3,compat=True)
        body=dict(state=0,loading=False,bell=False,cancel_seq=0,bell_notice=True,bell_release=True)
        a.op('acquire');self.settled()
        self.assertEqual(self.http(b,'/party/tick',body,True),b'0 0 1 0')
        a.op('release');self.settled()
        self.assertEqual(self.http(b,'/party/tick',body,True),b'1 0 0 1')
        self.assertEqual(self.http(b,'/party/tick',dict(body,bell_release=False),True),b'1 0 0')
        c.op('acquire');self.settled()
        self.assertEqual(self.http(b,'/party/tick',body,True),b'0 0 2 0')

    def test_private_http_backlog_capacity(self):
        from compat import Compatibility
        from engine import Engine,invite
        import concurrent.futures
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        e=Engine(invite([{'id':'X','host':'127.0.0.1','port':port,'p2p':3658}]),'X',self.root/'backlog')
        c=Compatibility(e);held=[]
        def connect(_):
            sock=socket.socket();sock.settimeout(.3)
            try:sock.connect(c.http.server_address);held.append(sock);return True
            except OSError:sock.close();return False
        try:
            self.assertEqual(c.http.request_queue_size,128)
            with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:self.assertEqual(sum(pool.map(connect,range(24))),24)
        finally:
            for sock in held:sock.close()
            c.http.server_close();c.np_server.server_close();c.relay_server.server_close();c.stun.close();e.server.server_close();e.journal.close()
