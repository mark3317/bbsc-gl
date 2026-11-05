import json,socket,struct,threading,time,unittest,tempfile
from pathlib import Path
from test_compat import CompatibilityTests
from compat import recv_exact
from run_log import open_log,record_exit

class IdleTests(CompatibilityTests):
 def test_real_np_and_relay_survive_idle(self):
  a,=self.group(1,compat=True)
  with self.np_connect(a,'A') as np, socket.create_connection(('127.0.0.1',a.info['relay']),timeout=2) as relay:
   relay.settimeout(2); size,=struct.unpack('<I',recv_exact(relay,4)); recv_exact(relay,size)
   time.sleep(23) # both old production timeouts must be crossed on the SAME sockets
   self.assertTrue(self.np_call(np,12,None,{},'ServerFeaturesReply')['matching2_enabled'])
   relay.setblocking(False)
   with self.assertRaises(BlockingIOError): relay.recv(1) # open, not EOF
 def test_partial_header_and_body_share_deadline(self):
  for body in (False,True):
   with self.subTest(body=body):
    listener=socket.socket(); listener.bind(('127.0.0.1',0));listener.listen()
    client=socket.create_connection(listener.getsockname()); server,_=listener.accept(); listener.close()
    deadline=[None]; result=[]
    def receive():
     try:
      recv_exact(server,4,idle=True,deadline=deadline,budget=.18)
      if body: recv_exact(server,8,deadline=deadline,budget=.18)
     except Exception as ex: result.append(type(ex))
    t=threading.Thread(target=receive);t.start()
    if body:
     client.sendall(bytes(4));time.sleep(.1);client.sendall(b'x')
    else: client.sendall(b'x')
    t.join(1); self.assertEqual(result,[TimeoutError]);client.close();server.close()
 def test_stdout_timestamp_and_no_secret_dump(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp); (root/'last_run.log').write_text('previous')
   f=open_log(root,{'BB_COOP':'1','BBSC_PARTY_TOKEN':'must-never-be-logged'})
   f.write('native output\n');record_exit(f,123,7);f.close()
   text=next(root.glob('run_*.log')).read_text()
   self.assertIn('native output',text);self.assertIn('exit=7',text);self.assertNotIn('must-never',text)
   self.assertEqual((root/'last_run.log').read_text(),'previous')
if __name__=='__main__':
 suite=unittest.TestSuite(IdleTests(name) for name in ('test_real_np_and_relay_survive_idle','test_partial_header_and_body_share_deadline','test_stdout_timestamp_and_no_secret_dump'))
 raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
