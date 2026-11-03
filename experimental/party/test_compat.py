"""Actual socket probes against compatibility components in independent client processes."""
import base64,json,socket,struct,time,urllib.request,unittest
from test_processes import Tests as ProcessTests
from protobuf import encode,decode
from compat import account,game_user_id,packet,blob,recv_exact
class CompatibilityTests(ProcessTests):
    # This class only runs its explicitly named compatibility test below.
    def http(self,c,path,body=None,control=False):
        headers={'Content-Type':'application/json'}
        if control: headers['X-BBSC-Party']=c.info['token']
        req=urllib.request.Request(f"http://127.0.0.1:{c.info['http']}{path}",data=json.dumps(body or {}).encode(),headers=headers)
        with urllib.request.urlopen(req,timeout=12) as r: return r.read()
    def np_connect(self,c,who):
        sock=socket.create_connection(('127.0.0.1',c.info['np']),timeout=5); sock.settimeout(12)
        head=recv_exact(sock,15); self.assertEqual(head[0],3); recv_exact(sock,4)
        self.np_call(sock,0,'LoginRequest',{'npid':who,'password':c.info['token']},'LoginReply')
        self.np_call(sock,100,'ContextStartRequest',{'ctx_id':1},None)
        return sock
    def np_call(self,sock,cmd,name,req,reply):
        sock.sendall(packet(0,cmd,9,blob(encode(name,req)) if name else b''))
        while True:
            kind,code,size,ident=struct.unpack('<BHIQ',recv_exact(sock,15)); data=recv_exact(sock,size-15)
            if kind==2: continue
            self.assertEqual((kind,code,ident),(1,cmd,9)); self.assertEqual(data[0],0)
            return decode(reply,data[5:]) if reply else {}
    def test_compatibility_native_contract(self):
        a,b=self.group(2,compat=True)
        with self.np_connect(a,'A') as sa, self.np_connect(b,'B') as sb:
            login=json.loads(self.http(b,'/basic_utils/login',{'PlatformAccountId':'B'}))
            self.assertEqual(login['UserId'],game_user_id('B'))
            self.assertNotEqual(login['UserId'],account('B'))
            self.assertTrue(0 < login['UserId'] <= 0x7fffffff)
            lookup=self.np_call(sa,41,'LookupOnlineIdRequest',{'npid':'B'},'LookupOnlineIdReply')
            self.assertEqual(lookup['account_id'],account('B'))
            sign={'UserId':struct.unpack('<i',struct.pack('<i',login['UserId']))[0],'SessionId':login['SessionId'],'CharaId':9223372036854775808,
                  'SummonDataVersion':3,'SummonData':base64.b64encode(bytes(224)).decode(),'AreaId':23}
            self.http(b,'/summon_messenger/create',sign)
            self.assertEqual(self.http(a,'/party/acquire',control=True),b'1')
            self.assertEqual(self.http(b,'/party/can_beckon',control=True),b'0')
            self.assertEqual(self.http(b,'/party/acquire',control=True),b'0')
            room=self.np_call(sa,101,'CreateRoomRequest',{'max_slots':5,'world_id':1,'flags':4,'internal_bin_attrs':[{'attr_id':1,'data':b'host-key'}]},'CreateRoomReply')
            room_id=room['room_id']; self.assertEqual(room['details']['room_data']['room_id'],room_id)
            self.np_call(sa,108,'SetRoomDataInternalRequest',{'room_id':room_id,'flag_filter':2,'flag_attr':2,'bin_attrs':[{'attr_id':2,'data':b'updated-only-this-attribute'}]},'SetRoomDataInternalReply')
            self.assertEqual(a.state()['state']['room']['flags'],6)
            end=time.monotonic()+3
            while time.monotonic()<end:
                found=json.loads(self.http(a,'/summon_messenger/get',{}))['SummonDataList']
                if found: break
                time.sleep(.05)
            self.assertEqual(found[0]['CharaId'],9223372036854775808)
            self.assertEqual(base64.b64decode(found[0]['SummonData'])[0x79],1)
            claim={'UserId':game_user_id('A'),'TargetUserId':struct.unpack('<i',struct.pack('<i',sign['UserId']))[0],'TargetCharaId':sign['CharaId'],'SessionId':login['SessionId'],'HostData':'native-opaque'}
            self.http(a,'/summon_messenger/request',claim)
            delivered=json.loads(self.http(b,'/summon_messenger/create',sign)); self.assertEqual(delivered['HostData'],'native-opaque')
            joined=self.np_call(sb,102,'JoinRoomRequest',{'room_id':room_id},'JoinRoomReply')
            self.assertEqual(len(joined['details']['members']),2)
            attrs=joined['details']['room_data']['bin_attrs_internal']
            self.assertEqual({x['attr_id']:x['data'] for x in attrs},{1:b'host-key',2:b'updated-only-this-attribute'})
            endpoint=self.np_call(sa,105,'RequestSignalingInfosRequest',{'target_npid':'B'},'RequestSignalingInfosReply')
            self.assertEqual((endpoint['target_ip'],endpoint['target_port']),('127.0.0.1',3659))
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
                udp.settimeout(2); udp.sendto(b'\xff'*4+b'\x01'+b'A'+bytes(15)+bytes(4),('127.0.0.1',a.info['np']+1))
                raw,_=udp.recvfrom(100); self.assertEqual(raw,b'\xff'*4+socket.inet_aton('127.0.0.1')+struct.pack('!H',3658))
            with socket.create_connection(('127.0.0.1',a.info['relay']),timeout=5) as ra, socket.create_connection(('127.0.0.1',b.info['relay']),timeout=5) as rb:
                for relay in (ra,rb):
                    relay.settimeout(5); length,=struct.unpack('<I',recv_exact(relay,4)); recv_exact(relay,length)
                def envelope(sender,part): return b'SHAD\x40'+struct.pack('<II',sender,111)+b'SHAD\x22'+struct.pack('<I',part)+bytes(60)
                rb.sendall(blob(envelope(222,99)))
                expected=[envelope(111,i) for i in range(16)]
                for frame in expected: ra.sendall(blob(frame))
                actual=[]
                for _ in expected:
                    length,=struct.unpack('<I',recv_exact(rb,4)); actual.append(recv_exact(rb,length))
                self.assertEqual(actual,expected) # Same-type multipart snapshots remain byte-exact.
            self.np_call(sa,115,'SendRoomMessageRequest',{'room_id':room_id,'cast_type':1,'msg':b'native-room-message'},'SendRoomMessageReply')
            kind,code,size,ident=struct.unpack('<BHIQ',recv_exact(sb,15)); notification=recv_exact(sb,size-15)
            self.assertEqual((kind,code),(2,11)); self.assertEqual(decode('NotifyRoomMessage',notification[4:])['msg'],b'native-room-message')
            # Replacing a local native connection and closing the old one must not leave.
            replacement=self.np_connect(b,'B')
            sb.sendall(packet(0,103,88,blob(encode('LeaveRoomRequest',{'room_id':room_id}))))
            sb.close(); time.sleep(.2)
            self.assertIn('B',a.state()['state']['joined'])
            self.np_call(sa,110,'KickoutRoomMemberRequest',{'room_id':room_id,'target_member_id':joined['member_id']},'KickoutRoomMemberReply')
            self.assertIn('B',a.state()['state']['joined']) # native teardown still has to acknowledge
            kind,code,size,ident=struct.unpack('<BHIQ',recv_exact(replacement,15)); notification=recv_exact(replacement,size-15)
            event=decode('NotifyRoomEvent',notification[4:]); self.assertEqual(event['event'],0x1103)
            self.assertEqual(event['error_code'],0xFF000019)
            self.np_call(replacement,103,'LeaveRoomRequest',{'room_id':room_id},'LeaveRoomReply'); replacement.close()
            self.np_call(sa,103,'LeaveRoomRequest',{'room_id':room_id},'LeaveRoomReply')
        self.http(a,'/party/native',{'state':3,'loading':False,'bell':True},True)
        self.http(a,'/party/native',{'state':0,'loading':True,'bell':False},True)
        time.sleep(.2); self.assertEqual(a.state()['state']['owner'],'A')
        self.http(a,'/party/native',{'state':0,'loading':False,'bell':False},True)
        time.sleep(.25); self.assertEqual(a.state()['state']['owner'],'A') # idle/death alone is not release
        self.http(a,'/party/native',{'state':0,'loading':False,'bell':False,'cancel_seq':1},True)
        end=time.monotonic()+5
        while time.monotonic()<end and a.state()['state']['owner'] is not None: time.sleep(.05)
        self.assertIsNone(a.state()['state']['owner'])
        self.assertEqual(self.http(b,'/party/acquire',control=True),b'1')
        xml=base64.b64decode(self.http(a,'/bb-eu/ss.info')).decode()
        self.assertNotIn('{YOUR',xml); self.assertNotIn(':31315',xml)
if __name__=='__main__':
    suite=unittest.TestSuite([CompatibilityTests('test_compatibility_native_contract')])
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
