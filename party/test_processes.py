import json,queue,socket,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from engine import invite
HERE=Path(__file__).resolve().parent
class Client:
    def __init__(self,path,who,profile,fault=None,compat=False):
        self.p=subprocess.Popen([sys.executable,str(HERE/'lite.py'),'--invite',str(path),'--id',who,'--profile',str(profile),'--fault',json.dumps(fault or {}),*(['--compat'] if compat else [])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
        self.q=queue.Queue(); self.stash={}; self.serial=0
        def read():
            for line in self.p.stdout: self.q.put(json.loads(line))
        threading.Thread(target=read,daemon=True).start()
        try: self.info=self.q.get(timeout=5)
        except queue.Empty:
            self.p.kill(); self.p.wait(); raise RuntimeError(self.p.stderr.read())
        assert self.info['ready']==who
    def send(self,cmd,**kw):
        self.serial+=1; self.p.stdin.write(json.dumps(dict(kw,cmd=cmd,token=self.serial))+'\n'); self.p.stdin.flush(); return self.serial
    def get(self,t,timeout=17):
        if t in self.stash: return self.stash.pop(t)
        end=time.monotonic()+timeout
        while True:
            x=self.q.get(timeout=max(.01,end-time.monotonic()))
            if x['token']==t: return x
            self.stash[x['token']]=x
    def call(self,cmd,**kw): return self.get(self.send(cmd,**kw))
    def op(self,k,**kw): return self.call('command',op=dict(kw,kind=k))
    def state(self): return self.call('state')
    def kill(self):
        self.p.kill(); self.p.wait(5)
        for f in (self.p.stdin,self.p.stdout,self.p.stderr): f.close()
class Tests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.cs=[]
    def tearDown(self):
        for c in self.cs:
            if c.p.poll() is None: c.kill()
        self.tmp.cleanup()
    def group(self,n,fault=None,compat=False,names=None):
        members=[]
        for i in range(n):
            with socket.socket() as s: s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
            members.append({'id':chr(65+i),'host':'127.0.0.1','port':port,'p2p':3658+i})
            if names is not None:members[-1]['name']=names[i]
        self.file=self.root/'invite.json'; self.file.write_text(json.dumps(invite(members)))
        for m in members: self.start(m['id'],fault,compat)
        return self.cs[:]
    def start(self,who,fault=None,compat=False):
        c=Client(self.file,who,self.root/who,fault,compat); self.cs.append(c); return c
    def settled(self,cs=None,timeout=10):
        cs=cs or [c for c in self.cs if c.p.poll() is None]; end=time.monotonic()+timeout
        while time.monotonic()<end:
            states=[c.state() for c in cs]
            if all(x['state']==states[0]['state'] and x['final']==x['state']['revision'] for x in states): return states
            time.sleep(.05)
        self.fail('No unanimous final state')
    def test_one_cancel_generation(self):
        a,=self.group(1); self.assertEqual(a.op('acquire').get('result'),1)
        self.assertNotIn('error',a.op('release')); self.assertEqual(a.op('acquire').get('result'),2); self.settled()
    def test_three_concurrent_rotation(self):
        cs=self.group(3); ts=[c.send('command',op={'kind':'acquire'}) for c in cs]
        rs=[c.get(t) for c,t in zip(cs,ts)]; self.assertEqual(sum('result' in r for r in rs),1,rs)
        owner=self.settled()[0]['state']['owner']; host=cs[ord(owner)-65]
        self.assertNotIn('error',host.op('release')); new=next(c for c in cs if c is not host)
        self.assertEqual(new.op('acquire').get('result'),2); self.settled()
    def test_admission_leave_rejoin(self):
        a,b=self.group(2); self.assertEqual(a.op('acquire').get('result'),1)
        self.assertNotIn('error',a.op('claim',target='B',claim={})); self.assertIn('error',a.op('release'))
        self.assertNotIn('error',b.op('admission_cancel'))
        rid=a.op('room_create',room={'max_slots':5,'world':1,'bins':[],'flags':0,'member_bins':[]})['result']
        a.op('claim',target='B',claim={}); first=b.op('room_join',room_id=rid)['result']
        self.assertIn('error',a.op('room_leave')); self.assertNotIn('error',b.op('room_leave'))
        a.op('claim',target='B',claim={}); second=b.op('room_join',room_id=rid)['result']; self.assertNotEqual(first,second)
        self.assertNotIn('error',b.op('room_leave')); self.assertNotIn('error',a.op('room_leave'))
        self.assertNotIn('error',a.op('release')); self.settled()
    def test_crash_partition_restore(self):
        a,b,c=self.group(3); self.assertEqual(a.op('acquire').get('result'),1); c.kill()
        self.assertIn('error',b.op('acquire'))
        self.assertIn('error',a.call('command',op={'kind':'release'},timeout=2))
        self.assertTrue(all(x.state()['state']['owner']=='A' for x in (a,b)))
        c=self.start('C'); self.settled([a,b,c],timeout=12)
        end=time.monotonic()+8
        while a.state()['state']['owner'] is not None and time.monotonic()<end: time.sleep(.05)
        self.assertIsNone(a.state()['state']['owner']); self.assertEqual(b.op('acquire').get('result'),2)
        a.call('block',peers=['B','C']); b.call('block',peers=['A']); c.call('block',peers=['A'])
        self.assertIn('error',b.call('command',op={'kind':'release'},timeout=2))
        self.assertTrue(all(x.state()['state']['owner']=='B' for x in (a,b,c)))
        for x in (a,b,c): x.call('block',peers=[])
        self.settled([a,b,c],timeout=12)
    def test_faults_and_chunk_delivery(self):
        a,b,c=self.group(3,{'seed':731,'loss':.17,'duplicate':.3,'delay':.11})
        self.assertEqual(b.op('acquire').get('result'),1); self.settled()
        for i in range(8): a.call('relay',data=f'WorldFlags:part:{i}')
        frames=[]; end=time.monotonic()+10
        while len(frames)<8 and time.monotonic()<end:
            frames.extend(b.call('received')['frames']); time.sleep(.1)
        self.assertEqual(frames,[f'WorldFlags:part:{i}' for i in range(8)])
        self.assertNotIn('error',b.op('release')); self.settled()
    def test_membership(self):
        a,b,c=self.group(3); self.assertNotIn('error',a.op('membership',roster=['A','B'])); self.settled()
        self.assertIn('error',c.call('command',op={'kind':'acquire'},timeout=2))
        self.assertIsNone(a.state()['state']['owner']); self.assertEqual(b.op('acquire').get('result'),1); self.settled([a,b])
    def test_coordinator_restart_after_durable_commit(self):
        a,b,c=self.group(3,{'drop_types':['commit']})
        a.send('command',op={'kind':'acquire'},timeout=2)
        end=time.monotonic()+4
        while time.monotonic()<end and a.state()['tx_phase']!='commit': time.sleep(.02)
        self.assertEqual(a.state()['tx_phase'],'commit'); a.kill()
        self.assertIsNone(b.state()['state']['owner']); self.assertIsNone(c.state()['state']['owner'])
        a=self.start('A')
        end=time.monotonic()+10
        while a.state()['final']<1 and time.monotonic()<end: time.sleep(.03)
        settled=self.settled([a,b,c],timeout=12)
        self.assertEqual(settled[0]['state']['owner'],'A')
        b.call('fault',value={}); c.call('fault',value={})
        self.assertNotIn('error',a.op('release'))
    def test_explicit_close_waits_for_guest_acknowledgements(self):
        a,b,c=self.group(3); a.op('acquire')
        rid=a.op('room_create',room={'max_slots':5,'world':1,'bins':[],'flags':0,'member_bins':[]})['result']
        for who,client in [('B',b),('C',c)]:
            a.op('claim',target=who,claim={}); self.assertNotIn('error',client.op('room_join',room_id=rid))
        self.assertNotIn('error',a.op('room_close')); self.assertIn('error',a.op('release'))
        self.assertNotIn('error',b.op('room_leave')); self.assertIn('error',a.op('release'))
        self.assertNotIn('error',c.op('room_leave')); self.assertNotIn('error',a.op('room_leave'))
        self.assertNotIn('error',a.op('release')); self.assertEqual(c.op('acquire').get('result'),2)
        self.settled()
    def test_network_rejects_wrong_group_sender_mac_and_generation(self):
        import hashlib,hmac,struct
        from engine import canonical
        a,b=self.group(2); cfg=json.loads(self.file.read_text()); before=b.state()['state']
        base={'group':cfg['group'],'from':'A','type':'relay','generation':99,'incarnation':1,'seq':1,'data':'b2xk'}
        variants=[dict(base,group='another-group'),dict(base,**{'from':'Outsider'}),dict(base)]
        for i,msg in enumerate(variants):
            msg['mac']=hmac.new(bytes.fromhex(cfg['secret']),canonical(msg),hashlib.sha256).hexdigest() if i!=2 else '0'*64
            with socket.create_connection(('127.0.0.1',cfg['members'][1]['port']),timeout=2) as sock:
                raw=canonical(msg); sock.sendall(struct.pack('<I',len(raw))+raw)
        a.call('inject',target='B',message={k:v for k,v in base.items() if k not in ('group','from')})
        time.sleep(.3); self.assertEqual(b.state()['state'],before); self.assertEqual(b.call('received')['frames'],[])
    def test_stale_generations_and_wrong_coordinator(self):
        from engine import transition
        a,b=self.group(2); base=a.state()['state']
        old={'base':base,'sender':'A','seq':1,'op':{'kind':'acquire'},'next':transition(base,'A',1,{'kind':'acquire'})}
        # B cannot coordinate revision zero, even though it is an invited member.
        for kind in ('prepare','commit','final'):
            b.call('inject',target='A',message={'type':kind,'proposal':old})
        time.sleep(.2); self.assertEqual(a.state()['state'],base)
        self.assertEqual(a.op('acquire').get('result'),1); self.assertNotIn('error',a.op('release'))
        self.assertEqual(b.op('acquire').get('result'),2); before=self.settled()[0]['state']
        for kind in ('prepare','commit','final'):
            a.call('inject',target='B',message={'type':kind,'proposal':old})
        time.sleep(.3); self.assertEqual(b.state()['state'],before)
if __name__=='__main__': unittest.main(verbosity=2)
