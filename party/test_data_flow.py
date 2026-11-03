"""Network regressions: status refresh and pending/idle relay recipients."""
import base64,select,socket,struct,time,unittest
from test_compat import CompatibilityTests
from compat import relay_recipients,blob,recv_exact
class DataFlowTests(CompatibilityTests):
    def test_status_refresh(self):
        a,b=self.group(2,compat=True)
        sign={'CharaId':1,'SummonData':base64.b64encode(bytes(224)).decode()}
        self.http(b,'/summon_messenger/create',sign)
        end=time.monotonic()+3
        first=None
        while time.monotonic()<end:
            first=a.call('status')['signs'].get('B')
            if first: break
            time.sleep(.05)
        self.assertEqual(first['body'],{'sign':sign})
        before=b.call('status')['tx']
        for _ in range(5):
            self.http(b,'/party/native',{'state':0,'loading':False,'bell':False},True)
            self.http(b,'/summon_messenger/create',sign)
        time.sleep(1)
        self.assertLessEqual(b.call('status')['tx']-before,1)
        time.sleep(12)
        latest=a.call('status')['signs']['B']
        self.assertEqual(latest['stamp'],first['stamp'])
        self.assertGreater(latest['at'],first['at']+6)
        self.assertLessEqual(b.call('status')['tx']-before,7)
        self.http(b,'/summon_messenger/delete',{})
        end=time.monotonic()+3
        while time.monotonic()<end and a.call('status')['signs']['B']['body']['sign'] is not None: time.sleep(.05)
        self.assertIsNone(a.call('status')['signs']['B']['body']['sign'])
    def test_pending_guest_chunks_idle_roster(self):
        a,b,c=self.group(3,compat=True)
        self.assertEqual(self.http(a,'/party/acquire',control=True),b'1')
        self.assertNotIn('error',a.op('claim',target='B',claim={}))
        sockets=[socket.create_connection(('127.0.0.1',x.info['relay']),timeout=5) for x in (a,b,c)]
        try:
            for sock in sockets:
                sock.settimeout(5); n,=struct.unpack('<I',recv_exact(sock,4));recv_exact(sock,n)
            frames=[b'SHAD\x40'+struct.pack('<II',111,111)+b'SHAD\x22'+struct.pack('<I',i)+bytes(60) for i in range(16)]
            for raw in frames: sockets[0].sendall(blob(raw))
            actual=[]
            for _ in frames:
                n,=struct.unpack('<I',recv_exact(sockets[1],4));actual.append(recv_exact(sockets[1],n))
            self.assertEqual(actual,frames)
            self.assertFalse(select.select([sockets[2]],[],[],.25)[0])
        finally:
            for sock in sockets: sock.close()
    def test_routing(self):
        state={'roster':['A','B','C','D'],'owner':'A','joined':{},'pending':{'B':{}},'room':{'members':{'A':{}},'departing':{'C':{}}}}
        def frame(kind):return b'SHAD\x40'+bytes(8)+b'SHAD'+bytes([kind])
        self.assertEqual(relay_recipients(frame(0x22),state,'A'),['B','C'])
        for kind in (0x20,0x21,0x30,0x31,0x60):
            self.assertEqual(relay_recipients(frame(kind),state,'A'),state['roster'])
        state['pending']={};state['room']['departing']={}
        self.assertEqual(relay_recipients(frame(0x2a),state,'B'),['A'])
