"""Combined bridge RPC, HTTP pooling and final leave checks without native builds."""
import http.client,json,socket,time,unittest
from test_compat import CompatibilityTests
class RPCTests(CompatibilityTests):
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
            self.assertEqual(tick(3,True),'0 0') # native idle is not final group leave
            b.call('block',peers=['A']);ticket=b.send('command',op={'kind':'room_leave'})
            time.sleep(.3);self.assertEqual(tick(3,True),'0 0')
            b.call('block',peers=[]);self.assertNotIn('error',b.get(ticket))
            self.assertEqual(tick(3,True),'0 3')
        finally:connection.close()
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
