"""Serverless party protocol. Standard library; embedded in the launcher and protocol test clients.
See PROTOCOL.md. No native gameplay datagrams enter this transport.
"""
from __future__ import annotations
import base64
import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
import queue
import random
import socket
import socketserver
import struct
import threading
import time
import uuid
from collections import deque
from party_workers import DurableWriter,PeerSender

MAX_FRAME = 256 * 1024

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with tmp.open('wb') as f:
        f.write(canonical(value)); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def invite(members):
    """Explicit addresses; no discover/broadcast and no privileged networking changes."""
    if not 1 <= len(members) <= 5:
        raise ValueError('1..5 members required')
    result = {'version': 1, 'group': uuid.uuid4().hex, 'epoch': 1,
              'secret': os.urandom(32).hex(), 'members': members}
    validate_invite(result)
    return result

def validate_invite(cfg):
    if cfg['version'] != 1 or len(bytes.fromhex(cfg['secret'])) != 32:
        raise ValueError('Unsupported invitation')
    ids = [m['id'] for m in cfg['members']]
    if len(ids) != len(set(ids)) or not 1 <= len(ids) <= 5:
        raise ValueError('Invalid roster')
    endpoints = set()
    for m in cfg['members']:
        if not m['id'].isascii() or not m['id'].isalnum() or len(m['id']) > 16:
            raise ValueError('Member ID must be 1..16 ASCII letters/digits')
        socket.inet_aton(m['host'])
        if not 1024 <= m['port'] <= 65535 or not 1024 <= m['p2p'] <= 65535:
            raise ValueError('Invalid port')
        endpoint = (m['host'], m['port'])
        if endpoint in endpoints: raise ValueError('Duplicate endpoint')
        endpoints.add(endpoint)

def initial(cfg):
    return {'revision': 0, 'epoch': cfg['epoch'], 'roster': [m['id'] for m in cfg['members']],
            'generation': 0, 'owner': None, 'room': None, 'joined': {}, 'pending': {},
            'completed': {}, 'results': {}}

def transition(state, sender, seq, op):
    """Pure transition. Exceptions reject a proposal, never advance a revision."""
    s = copy.deepcopy(state)
    if sender not in s['roster']: raise ValueError('Not a member')
    old = s['completed'].get(sender, [0, None])
    if seq <= old[0]: raise ValueError('Already completed')
    kind = op['kind']; result = None
    if kind == 'acquire':
        if s['owner'] is not None: raise ValueError('World already reserved')
        s['owner'] = sender; s['generation'] += 1
        result = s['generation']
    elif kind == 'release':
        if sender != s['owner'] or s['room'] or s['joined'] or s['pending']:
            raise ValueError('World not explicitly drained')
        s['owner'] = None
    elif kind == 'room_create':
        if sender != s['owner'] or s['room']: raise ValueError('Not sole owner')
        # Native room identity is distinct from world generation.
        room = copy.deepcopy(op['room'])
        serial = s.get('room_serial', 1) + 1
        if serial >= 1 << 24: raise ValueError('Native room identity exhausted')
        s['room_serial'] = serial
        room['id'] = (s['generation'] << 24) | serial
        room['member_id_layout'] = 2
        room['next_incarnation'] = 2
        room['members'] = {sender: {'slot': 17, 'incarnation': 1, 'bins': room.pop('member_bins', [])}}
        s['room'] = room; result = room['id']
    elif kind == 'claim':
        target = op['target']
        if sender != s['owner'] or target == sender or target not in s['roster'] or (s['room'] and s['room'].get('closing')):
            raise ValueError('Invalid claim')
        if target in s['pending'] or target in s['joined']: raise ValueError('Already joining')
        s['pending'][target] = {'generation': s['generation'], 'claim': op['claim']}
    elif kind == 'admission_cancel':
        if sender not in s['pending']: raise ValueError('Only joining member may cancel')
        del s['pending'][sender]
    elif kind == 'room_join':
        if s['room'] and s['room'].get('closing'): raise ValueError('Room is closing')
        if not s['room'] or sender not in s['pending'] or op['room_id'] != s['room']['id']:
            raise ValueError('No current admission')
        if s['room'].get('member_id_layout') != 2:
            raise ValueError('Legacy native room must drain before new admission')
        slots = {m['slot'] >> 4 for m in s['room']['members'].values()}
        slot = next((i for i in range(2, 6) if i not in slots), None)
        if slot is None or len(slots) >= s['room']['max_slots']: raise ValueError('Room full')
        # Match stock shadNet: upper bits are the place, low nibble is generation.
        # Keep the full incarnation separately for callbacks after generation wrap.
        incarnation = s['room']['next_incarnation']
        if incarnation > 4095: raise ValueError('Recreate native room before incarnation wrap')
        member_id = (slot << 4) | (incarnation & 15)
        s['room']['next_incarnation'] += 1
        s['room']['members'][sender] = {'slot': member_id, 'incarnation': incarnation, 'bins': op.get('bins', [])}
        s['joined'][sender] = s['generation']; del s['pending'][sender]
        result = member_id
    elif kind == 'room_close':
        if sender != s['owner'] or not s['room']: raise ValueError('Not room owner')
        s['room']['closing'] = True
    elif kind == 'kick':
        target=op['target']
        if sender!=s['owner'] or not s['room'] or target==sender or target not in s['room']['members']: raise ValueError('Invalid native kick')
        s['room'].setdefault('departing',{})[target]=s['room']['members'].pop(target)
    elif kind == 'room_message':
        if not s['room'] or sender not in s['room']['members']: raise ValueError('Not in native room')
        s['room']['message']=dict(op['message'],sender=sender,sequence=s['revision']+1)
    elif kind == 'room_leave':
        if not s['room'] or (sender not in s['room']['members'] and sender not in s['joined']): raise ValueError('Not in room')
        if sender == s['owner']:
            if s['joined'] or s['pending']: raise ValueError('Guests/admissions must drain first')
            s['room'] = None
        else:
            s['room']['members'].pop(sender,None); s['joined'].pop(sender, None)
            s['room'].get('departing',{}).pop(sender,None)
    elif kind == 'room_update':
        if sender != s['owner'] or not s['room']: raise ValueError('Not room owner')
        s['room'].update({k: op[k] for k in ('bins', 'flags') if k in op})
    elif kind == 'member_update':
        if not s['room'] or sender not in s['room']['members']: raise ValueError('Not in room')
        s['room']['members'][sender]['bins'] = op['bins']
    elif kind == 'membership':
        roster = op['roster']
        if s['owner'] or s['room'] or not roster or len(set(roster)) != len(roster) or not set(roster) <= set(s['roster']):
            raise ValueError('Membership requires idle and subset of old roster')
        s['roster'] = roster; s['epoch'] += 1
    else: raise ValueError('Unknown operation')
    s['revision'] += 1
    s['completed'][sender] = [seq, result]
    results=s.setdefault('results',{}).setdefault(sender,{})
    results[str(seq)]=result
    while len(results)>32: del results[min(results,key=int)]
    return s

class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = False
    daemon_threads = True
    def server_bind(self):
        if os.name == 'nt': self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()

class Engine:
    def __init__(self, cfg, member, profile, *, fault=None):
        validate_invite(cfg)
        self.cfg = copy.deepcopy(cfg); self.id = member; self.profile = Path(profile)
        self.member = next(m for m in cfg['members'] if m['id'] == member)
        self.members = {m['id']: m for m in cfg['members']}
        self.key = bytes.fromhex(cfg['secret'])
        self.path = self.profile / 'party-journal.json'
        self.lock = threading.RLock(); self.inbox = queue.Queue(512)
        self.stop_event = threading.Event(); self.links = {}; self.thread = None
        self.journal=None;self.control_ticket=0;self.relay_ticket=0;self.deferred=[]
        self.final_ticket=0;self.final_marker=None
        self.fault = fault or {}; self.rng = random.Random(self.fault.get('seed', 1))
        self.blocked = set(); self.delayed = []; self.last_tick = 0
        self.signs = {}; self.update_seq = 0; self.relay_next = 0
        self.status_last = None; self.status_at = 0; self.status_tx = 0
        self.relay_scope = None; self.relay_transport = 0
        self.relay_pending = {}; self.relay_received = {}; self.relay_out = queue.Queue(128)
        self.relay_backlogs={};self.relay_sequences={};self.relay_buffers={};self.relay_rtt={}
        self.relay_window=16;self.relay_streams={}
        self.relay_in = queue.Queue(128); self.relay_error = None
        if self.path.exists():
            self.disk = json.loads(self.path.read_text())
            if self.disk['group'] != cfg['group'] or self.disk['id'] != member:
                raise ValueError('Journal belongs to another group/member')
        else:
            self.disk = {'group': cfg['group'], 'id': member, 'state': initial(cfg),
                         'final': 0, 'accepted': None, 'tx': None, 'counter': 0,
                         'incarnation': 0, 'history': {}}
        receipts=self.disk.pop('relay_received',{})
        self.relay_path=self.profile/'party-relay-journal.json'
        if self.relay_path.exists():
            relay_disk=json.loads(self.relay_path.read_text())
            if relay_disk['group']!=cfg['group'] or relay_disk['id']!=member:raise ValueError('Relay journal identity mismatch')
            receipts=relay_disk['received']
        self.relay_received={k:tuple(v) if len(v)==3 else (v[0],-1,v[1]) for k,v in receipts.items()}
        if receipts and not self.relay_path.exists():
            atomic_json(self.relay_path,{'group':cfg['group'],'id':member,'received':self.relay_received})
        self.disk['incarnation'] += 1; self.persist()
        self.state = self.disk['state']; self.pending_local = None
        engine = self
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.settimeout(3)
                try:
                    while not engine.stop_event.is_set():
                        head = self.read(4)
                        if not head: return
                        size, = struct.unpack('<I', head)
                        if not 0 < size <= MAX_FRAME: return
                        raw = self.read(size)
                        msg = json.loads(raw)
                        mac = msg.pop('mac', '')
                        if not hmac.compare_digest(mac, hmac.new(engine.key, canonical(msg), hashlib.sha256).hexdigest()): return
                        sender = msg.get('from')
                        if msg.get('group') != cfg['group'] or sender not in engine.members: return
                        if self.client_address[0] != engine.members[sender]['host']: return
                        if sender in engine.blocked: continue
                        try: engine.inbox.put_nowait(msg)
                        except queue.Full: return
                except (OSError, ValueError, KeyError, TypeError): return
            def read(self, n):
                out = bytearray()
                while len(out) < n:
                    part = self.request.recv(n-len(out))
                    if not part: return None
                    out.extend(part)
                return bytes(out)
        self.server = _Server((self.member['host'], self.member['port']), Handler)
        self.journal=DurableWriter(atomic_json)

    def persist(self):
        if self.journal is None:atomic_json(self.path,self.disk)
        else:self.control_ticket=self.journal.submit(self.path,self.disk)
        if self.final_marker!=self.disk['final']:
            self.final_marker=self.disk['final'];self.final_ticket=self.control_ticket
    def finalized(self,state=None):
        with self.lock:
            state=state or self.state
            return self.disk['final']==state['revision'] and (self.journal is None or self.journal.ready(self.final_ticket))
    def confirmed_state(self,revision):
        with self.lock:
            if not self.finalized():return False,None
            return True,copy.deepcopy(self.state) if self.state['revision']!=revision else None
    def snapshot(self):
        with self.lock:
            return {'id': self.id, 'state': copy.deepcopy(self.state), 'final': self.disk['final'] if self.finalized() else min(self.disk['final'],self.state['revision']-1),
                    'pending': copy.deepcopy(self.pending_local), 'relay_error': self.relay_error,
                    'tx_phase': self.disk['tx']['phase'] if self.disk['tx'] else None}
    def start(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.thread = threading.Thread(target=self.run, daemon=True); self.thread.start()
        return self
    def close(self):
        self.stop_event.set(); self.server.shutdown(); self.server.server_close()
        if self.thread:self.thread.join(3)
        for link in list(self.links.values()):link.close()
        self.journal.close()
    def coordinator(self, state=None):
        s = state or self.state
        return s['roster'][s['revision'] % len(s['roster'])]
    def request(self, op):
        with self.lock:
            if self.pending_local: raise ValueError('One outstanding command per member')
            self.disk['counter'] += 1; self.persist()
            self.pending_local = {'seq': self.disk['counter'], 'op': copy.deepcopy(op)}
            return self.disk['counter']
    def poll(self,seq):
        with self.lock:
            done=self.state['completed'].get(self.id)
            if done and self.finalized():
                results=self.state.get('results',{}).get(self.id,{})
                if str(seq) in results or done[0]==seq:
                    if self.pending_local and self.pending_local['seq']==seq:self.pending_local=None
                    return True,results.get(str(seq),done[1])
            if self.pending_local and self.pending_local['seq']==seq and self.pending_local.get('error'):
                error=self.pending_local['error'];self.pending_local=None;raise ValueError(error)
            return False,None
    def wait(self,seq,timeout=10):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            ready,result=self.poll(seq)
            if ready:return result
            time.sleep(.02)
        raise TimeoutError('Waiting for unanimous party confirmation')
    def command(self, op, timeout=10): return self.wait(self.request(op), timeout)
    def send(self,target,payload,ticket=None):
        with self.lock:self._send(target,payload,ticket)
    def _send(self,target,payload,ticket=None):
        if target==self.id:
            self.inbox.put_nowait(dict(payload,**{'from':self.id,'group':self.cfg['group']}));return
        if target in self.blocked or payload.get('type') in self.fault.get('drop_types',[]):return
        if self.rng.random()<self.fault.get('loss',0):return
        msg=dict(payload,**{'from':self.id,'group':self.cfg['group']})
        msg['mac']=hmac.new(self.key,canonical(msg),hashlib.sha256).hexdigest();raw=canonical(msg)
        if len(raw)>MAX_FRAME:raise ValueError('Frame too large')
        priority=2 if payload['type']=='relay' else 1 if payload['type']=='status' else 0
        dependency=self.control_ticket if ticket is None else ticket
        delay=self.fault.get('delay',0)*self.rng.random()
        copies=2 if self.rng.random()<self.fault.get('duplicate',0) else 1
        if len(self.deferred)+copies>512:
            self.relay_error='outbound scheduling queue full';return
        for i in range(copies):self.deferred.append((time.monotonic()+delay+i*.025,target,raw,priority,dependency))
    def wire(self,target,raw,priority=0):
        if target in self.blocked:return
        if target not in self.links:
            m=self.members[target]
            self.links[target]=PeerSender((m['host'],m['port']),self.member['host'],self.stop_event,self.network_error,lambda:target not in self.blocked)
        self.links[target].put(raw,priority)
    def network_error(self,message):self.relay_error=message
    def flush_outbound(self,now):
        waiting=[]
        for at,target,raw,priority,ticket in self.deferred:
            if at<=now and self.journal.ready(ticket):self.wire(target,raw,priority)
            else:waiting.append((at,target,raw,priority,ticket))
        self.deferred=waiting
    def fan(self, payload, roster):
        for target in roster: self.send(target, payload)
    @staticmethod
    def digest(p): return hashlib.sha256(canonical(p)).hexdigest()
    def remember(self, p):
        self.disk['history'][str(p['next']['revision'])] = self.digest(p)
        while len(self.disk['history']) > 32:
            del self.disk['history'][min(self.disk['history'], key=int)]
    def seen(self, p):
        return self.disk['history'].get(str(p['next']['revision'])) == self.digest(p)
    def handle(self, m):
        kind = m['type']; sender = m['from']; s = self.state
        if kind == 'request':
            if self.id != self.coordinator() or self.disk['final'] != s['revision']: return
            if sender not in s['roster'] or m['revision'] != s['revision']: return
            if self.disk['tx']: return
            done = s['completed'].get(sender, [0, None])
            if m['seq'] <= done[0]: return
            try: next_state = transition(s, sender, m['seq'], m['op'])
            except ValueError as error:
                self.send(sender, {'type': 'reject', 'seq': m['seq'], 'revision': s['revision'], 'error': str(error)}); return
            p = {'base': copy.deepcopy(s), 'sender': sender, 'seq': m['seq'], 'op': m['op'], 'next': next_state}
            self.disk['tx'] = {'proposal': p, 'phase': 'prepare', 'acks': []}; self.persist()
        elif kind == 'reject':
            if sender == self.coordinator() and m['revision'] == s['revision'] and self.pending_local and m['seq'] == self.pending_local['seq']:
                self.pending_local['error'] = m['error']
        elif kind in ('prepare', 'commit', 'final'):
            p = m['proposal']; base = p['base']; rev = p['next']['revision']
            if sender != self.coordinator(base) or self.id not in base['roster']: return
            if self.seen(p):
                if kind == 'final' and self.disk['final'] < rev:
                    self.disk['final'] = rev; self.disk['accepted'] = None; self.persist()
                self.send(sender, {'type': {'prepare':'prepared','commit':'committed','final':'finalized'}[kind], 'digest': self.digest(p)})
                return
            if base != s or self.disk['final'] != s['revision']: return
            try:
                if transition(base, p['sender'], p['seq'], p['op']) != p['next']: return
            except (ValueError, KeyError, TypeError): return
            accepted = self.disk['accepted']
            if accepted and accepted != p: return
            if kind == 'prepare':
                self.disk['accepted'] = p; self.persist()
                self.send(sender, {'type': 'prepared', 'digest': self.digest(p)})
            elif kind == 'commit' and accepted == p:
                self.disk['state'] = self.state = p['next']; self.remember(p); self.persist()
                self.send(sender, {'type': 'committed', 'digest': self.digest(p)})
        elif kind in ('prepared', 'committed', 'finalized'):
            tx = self.disk['tx']
            if not tx or m['digest'] != self.digest(tx['proposal']): return
            if sender not in tx['proposal']['base']['roster']: return
            expected = {'prepare': 'prepared', 'commit': 'committed', 'final': 'finalized'}[tx['phase']]
            if kind != expected: return
            if sender in tx['acks']:return
            tx['acks'].append(sender)
            if set(tx['acks']) == set(tx['proposal']['base']['roster']):
                if tx['phase'] == 'final': self.disk['tx'] = None
                else: tx['phase'] = {'prepare':'commit','commit':'final'}[tx['phase']]; tx['acks'] = []
            self.persist()
        elif kind == 'status':
            if sender not in s['roster'] or m['epoch'] != s['epoch'] or m.get('generation') != s['generation']: return
            stamp = (m['incarnation'], m['seq'])
            prev = self.signs.get(sender)
            if prev is not None and stamp == tuple(prev['stamp']) and m['body'] == prev['body']:
                prev['at'] = time.monotonic() # periodic full refresh, including after reconnect
            elif prev is None or stamp > tuple(prev['stamp']):
                self.signs[sender] = {'stamp': stamp, 'body': m['body'], 'at': time.monotonic()}
        elif kind=='relay':self.receive_relay(sender,m)
        elif kind=='relay_ack':
            window=self.relay_pending.get(sender,{})
            stamp=(m['incarnation'],m.get('stream',-1))
            now=time.monotonic()
            for seq,pending in list(window.items()):
                msg=pending['msg']
                if (msg['incarnation'],msg.get('stream',-1))==stamp and seq<=m['seq']:
                    if pending['attempts']==1:
                        sample=now-pending['sent'];old=self.relay_rtt.get(sender,sample)
                        self.relay_rtt[sender]=.875*old+.125*sample
                    del window[seq]
    def receive_relay(self,sender,m):
        s=self.state
        if sender not in s['roster'] or m['generation']!=s['generation'] or not s['owner']:return
        if 'stream' not in m:
            if (m['incarnation'],-1)<self.relay_streams.get(sender,(0,-1)):return
            # Read old journals/wire conservatively during an all-client upgrade.
            stamp=(m['incarnation'],-1,m['seq'])
            if stamp<=self.relay_received.get(sender,(0,-1,0)):
                self.send(sender,{'type':'relay_ack','incarnation':m['incarnation'],'seq':m['seq']},self.relay_ticket);return
            raw=base64.b64decode(m['data'],validate=True)
            try:self.relay_in.put_nowait((sender,raw,m.get('binding',{})))
            except queue.Full:return
            self.relay_received[sender]=stamp;self.persist_relay()
            self.send(sender,{'type':'relay_ack','incarnation':m['incarnation'],'seq':m['seq']},self.relay_ticket);return
        stream=(int(m['incarnation']),int(m['stream']));seq=int(m['seq'])
        if min(stream)<0 or seq<=0:return
        previous=self.relay_received.get(sender,(0,-1,0))
        active=self.relay_streams.get(sender,previous[:2])
        if stream<max(active,previous[:2]):return
        if sender not in self.relay_streams or stream!=active:
            self.relay_buffers[sender]={};self.relay_streams[sender]=stream
        expected=previous[2]+1 if previous[:2]==stream else 1
        if seq<expected:
            self.ack_relay(sender,stream,previous[2]);return
        if seq>=expected+self.relay_window:return
        buffer=self.relay_buffers.setdefault(sender,{})
        raw=base64.b64decode(m['data'],validate=True)
        if len(raw)>65536:raise ValueError('Oversized relay frame')
        buffer.setdefault(seq,(raw,m.get('binding',{})))
        self.drain_relay(sender)
    def persist_relay(self):
        self.relay_ticket=self.journal.submit(self.relay_path,{'group':self.cfg['group'],'id':self.id,'received':self.relay_received})
    def ack_relay(self,sender,stream,seq):
        self.send(sender,{'type':'relay_ack','incarnation':stream[0],'stream':stream[1],'seq':seq},self.relay_ticket)
    def drain_relay(self,sender):
        stream=self.relay_streams.get(sender)
        if stream is None:return
        previous=self.relay_received.get(sender,(0,-1,0))
        expected=previous[2]+1 if previous[:2]==stream else 1
        buffer=self.relay_buffers.get(sender,{})
        changed=False
        while expected in buffer:
            raw,binding=buffer[expected]
            try:self.relay_in.put_nowait((sender,raw,binding))
            except queue.Full:break
            del buffer[expected];self.relay_received[sender]=(*stream,expected)
            expected+=1;changed=True
        if changed:
            self.persist_relay();self.ack_relay(sender,stream,expected-1)
    def publish(self, body):
        with self.lock:
            previous = self.signs.get(self.id)
            if previous and previous['body'] == body: return
            self.update_seq += 1
            self.signs[self.id] = {'stamp': (self.disk['incarnation'],self.update_seq), 'body': copy.deepcopy(body), 'at': time.monotonic()}
    def reset_relay(self):
        with self.lock:
            self.relay_transport+=1;self.relay_pending.clear();self.relay_error=None
            self.relay_backlogs.clear();self.relay_sequences.clear()
            self.relay_buffers.clear();self.relay_streams.clear()
            while not self.relay_out.empty():self.relay_out.get_nowait()
    def sync_relay_scope(self):
        scope=(self.state['generation'],self.state['owner'])
        if self.relay_scope is not None and self.relay_scope!=scope:self.reset_relay()
        self.relay_scope=scope
    def relay(self,raw,binding=None,recipients=None):
        if len(raw)>65536:raise ValueError('Oversized BBSC frame')
        with self.lock:
            self.sync_relay_scope()
            try:self.relay_out.put_nowait((raw,binding or {},None if recipients is None else tuple(recipients)))
            except queue.Full:
                self.relay_error='send queue full';raise ValueError(self.relay_error)
    def pump_relay(self,now):
        for _ in range(32):
            try:raw,binding,recipients=self.relay_out.get_nowait()
            except queue.Empty:break
            data=base64.b64encode(raw).decode()
            for peer in self.state['roster']:
                if peer==self.id or (recipients is not None and peer not in recipients):continue
                backlog=self.relay_backlogs.setdefault(peer,deque())
                if len(backlog)>=128:self.relay_error='peer relay backlog full';return
                backlog.append((data,binding,now))
        for peer,backlog in self.relay_backlogs.items():
            window=self.relay_pending.setdefault(peer,{})
            while backlog and len(window)<self.relay_window:
                data,binding,at=backlog.popleft()
                seq=self.relay_sequences.get(peer,0)+1;self.relay_sequences[peer]=seq
                msg={'type':'relay','incarnation':self.disk['incarnation'],'stream':self.relay_transport,'seq':seq,
                     'generation':self.state['generation'],'binding':binding,'data':data}
                window[seq]={'msg':msg,'at':at,'sent':0,'attempts':0,'rto':max(.15,min(2,3*self.relay_rtt.get(peer,.1)))}
            for pending in window.values():
                if now-pending['at']>10:self.relay_error='unacknowledged BBSC frame expired';return
                if not pending['attempts'] or now-pending['sent']>=pending['rto']:
                    if pending['attempts']:pending['rto']=min(2,pending['rto']*2)
                    self.send(peer,pending['msg']);pending['sent']=now;pending['attempts']+=1
        for peer in list(self.relay_buffers):self.drain_relay(peer)
    def run(self):
        while not self.stop_event.wait(.01):
            with self.lock:
                try:
                    now=time.monotonic();self.flush_outbound(now);self.sync_relay_scope()
                    if not self.journal.ready(self.control_ticket):continue
                    for _ in range(256):
                        try:msg=self.inbox.get_nowait()
                        except queue.Empty:break
                        try:self.handle(msg)
                        except (ValueError,KeyError,TypeError):pass
                        self.sync_relay_scope()
                        if not self.journal.ready(self.control_ticket):break
                    if self.pending_local:
                        done=self.state['completed'].get(self.id)
                        if done and done[0]>=self.pending_local['seq'] and self.finalized():self.pending_local=None
                    now=time.monotonic()
                    if now-self.last_tick>=.12:
                        self.last_tick=now
                        tx=self.disk['tx']
                        if tx:self.fan({'type':tx['phase'],'proposal':tx['proposal']},tx['proposal']['base']['roster'])
                        if self.pending_local and not self.pending_local.get('error'):
                            self.send(self.coordinator(),dict(self.pending_local,type='request',revision=self.state['revision']))
                        own=self.signs.get(self.id)
                        stamp=(self.state['epoch'],self.state['generation'],own['stamp']) if own else None
                        if own and (stamp!=self.status_last or now-self.status_at>=2):
                            self.status_last=stamp;self.status_at=now;self.status_tx+=1
                            self.fan({'type':'status','epoch':self.state['epoch'],'generation':self.state['generation'],
                                      'incarnation':own['stamp'][0],'seq':own['stamp'][1],'body':own['body']},self.state['roster'])
                    if not self.relay_error:self.pump_relay(now)
                except OSError as error:self.relay_error=str(error)
