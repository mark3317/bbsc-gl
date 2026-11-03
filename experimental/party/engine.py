"""Serverless party protocol. Standard library; embedded in the launcher and lite clients.
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
        room['next_incarnation'] = 1
        room['members'] = {sender: {'slot': 1, 'bins': room.pop('member_bins', [])}}
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
        slots = {m['slot'] & 15 for m in s['room']['members'].values()}
        slot = next((i for i in range(2, 6) if i not in slots), None)
        if slot is None or len(slots) >= s['room']['max_slots']: raise ValueError('Room full')
        # Incarnation bits prevent a late event from resurrecting a reused slot.
        incarnation = s['room']['next_incarnation']
        if incarnation > 4095: raise ValueError('Recreate native room before incarnation wrap')
        member_id = (incarnation << 4) | slot
        s['room']['next_incarnation'] += 1
        s['room']['members'][sender] = {'slot': member_id, 'bins': op.get('bins', [])}
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
        self.fault = fault or {}; self.rng = random.Random(self.fault.get('seed', 1))
        self.blocked = set(); self.delayed = []; self.last_tick = 0
        self.signs = {}; self.update_seq = 0; self.relay_next = 0
        self.relay_scope = None; self.relay_transport = 0
        self.relay_pending = {}; self.relay_received = {}; self.relay_out = queue.Queue(128)
        self.relay_in = queue.Queue(128); self.relay_error = None
        if self.path.exists():
            self.disk = json.loads(self.path.read_text())
            if self.disk['group'] != cfg['group'] or self.disk['id'] != member:
                raise ValueError('Journal belongs to another group/member')
        else:
            self.disk = {'group': cfg['group'], 'id': member, 'state': initial(cfg),
                         'final': 0, 'accepted': None, 'tx': None, 'counter': 0,
                         'incarnation': 0, 'history': {}}
        self.relay_received = {k:tuple(v) for k,v in self.disk.get('relay_received', {}).items()}
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

    def persist(self): atomic_json(self.path, self.disk)
    def snapshot(self):
        with self.lock:
            return {'id': self.id, 'state': copy.deepcopy(self.state), 'final': self.disk['final'],
                    'pending': copy.deepcopy(self.pending_local), 'relay_error': self.relay_error,
                    'tx_phase': self.disk['tx']['phase'] if self.disk['tx'] else None}
    def start(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.thread = threading.Thread(target=self.run, daemon=True); self.thread.start()
        return self
    def close(self):
        self.stop_event.set(); self.server.shutdown(); self.server.server_close()
        for sock in self.links.values():
            try: sock.close()
            except OSError: pass
        if self.thread: self.thread.join(3)
    def coordinator(self, state=None):
        s = state or self.state
        return s['roster'][s['revision'] % len(s['roster'])]
    def request(self, op):
        with self.lock:
            if self.pending_local: raise ValueError('One outstanding command per member')
            self.disk['counter'] += 1; self.persist()
            self.pending_local = {'seq': self.disk['counter'], 'op': copy.deepcopy(op)}
            return self.disk['counter']
    def wait(self, seq, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self.lock:
                done = self.state['completed'].get(self.id)
                if done and self.disk['final'] >= self.state['revision']:
                    results=self.state.get('results',{}).get(self.id,{})
                    if str(seq) in results: return results[str(seq)]
                    if done[0]==seq: return done[1]
                if self.pending_local and self.pending_local.get('error'):
                    error = self.pending_local['error']; self.pending_local = None
                    raise ValueError(error)
            time.sleep(.02)
        raise TimeoutError('Waiting for unanimous party confirmation')
    def command(self, op, timeout=10): return self.wait(self.request(op), timeout)
    def send(self, target, payload):
        if target == self.id:
            self.inbox.put_nowait(dict(payload, **{'from': self.id, 'group': self.cfg['group']})); return
        if target in self.blocked or payload.get('type') in self.fault.get('drop_types',[]): return
        if self.rng.random() < self.fault.get('loss', 0): return
        msg = dict(payload, **{'from': self.id, 'group': self.cfg['group']})
        msg['mac'] = hmac.new(self.key, canonical(msg), hashlib.sha256).hexdigest()
        raw = canonical(msg)
        if len(raw) > MAX_FRAME: raise ValueError('Frame too large')
        delay = self.fault.get('delay', 0) * self.rng.random()
        if delay or self.fault.get('duplicate', 0):
            if len(self.delayed) < 256:
                self.delayed.append((time.monotonic()+delay, target, raw))
                if self.rng.random() < self.fault.get('duplicate', 0):
                    self.delayed.append((time.monotonic()+delay+.025, target, raw))
        else: self.wire(target, raw)
    def wire(self, target, raw):
        if target in self.blocked: return
        sock = self.links.get(target)
        try:
            if sock is None:
                m = self.members[target]
                sock = socket.create_connection((m['host'], m['port']), timeout=.08,source_address=(self.member['host'],0))
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.links[target] = sock
            sock.sendall(struct.pack('<I', len(raw)) + raw)
        except OSError:
            if sock:
                sock.close(); self.links.pop(target, None)
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
            if sender not in tx['acks']: tx['acks'].append(sender)
            if set(tx['acks']) == set(tx['proposal']['base']['roster']):
                if tx['phase'] == 'final': self.disk['tx'] = None
                else: tx['phase'] = {'prepare':'commit','commit':'final'}[tx['phase']]; tx['acks'] = []
            self.persist()
        elif kind == 'status':
            if sender not in s['roster'] or m['epoch'] != s['epoch'] or m.get('generation') != s['generation']: return
            stamp = (m['incarnation'], m['seq'])
            prev = self.signs.get(sender)
            if prev is None or stamp > tuple(prev['stamp']):
                self.signs[sender] = {'stamp': stamp, 'body': m['body'], 'at': time.monotonic()}
        elif kind == 'relay':
            if sender not in s['roster'] or m['generation'] != s['generation'] or not s['owner']: return
            stamp = (m['incarnation'], m['seq'])
            prev = self.relay_received.get(sender, (0, 0))
            if stamp <= prev:
                self.send(sender, {'type':'relay_ack', 'incarnation':m['incarnation'], 'seq':m['seq']}); return
            # Stop-and-wait prevents reordering; sequence can skip after an idle generation.
            raw = base64.b64decode(m['data'], validate=True)
            try: self.relay_in.put_nowait((sender, raw, m.get('binding',{})))
            except queue.Full: self.relay_error = 'receive queue full'; return
            self.relay_received[sender] = stamp
            self.disk['relay_received'] = self.relay_received; self.persist()
            self.send(sender, {'type':'relay_ack', 'incarnation':m['incarnation'], 'seq':m['seq']})
        elif kind == 'relay_ack':
            pending = self.relay_pending.get(sender)
            if pending and (m['incarnation'],m['seq']) == (pending['msg']['incarnation'],pending['msg']['seq']):
                self.relay_pending.pop(sender)
    def publish(self, body):
        with self.lock:
            self.update_seq += 1
            self.signs[self.id] = {'stamp': (self.disk['incarnation'],self.update_seq), 'body': copy.deepcopy(body), 'at': time.monotonic()}
    def reset_relay(self):
        with self.lock:
            self.relay_transport += 1
            self.relay_pending.clear(); self.relay_error = None
            while not self.relay_out.empty(): self.relay_out.get_nowait()

    def relay(self, raw, binding=None):
        if len(raw) > 65536: raise ValueError('Oversized BBSC frame')
        try: self.relay_out.put_nowait((raw,binding or {}))
        except queue.Full:
            self.relay_error = 'send queue full'; raise ValueError(self.relay_error)
    def run(self):
        while not self.stop_event.wait(.01):
            with self.lock:
                try:
                    for _ in range(256):
                        try: msg = self.inbox.get_nowait()
                        except queue.Empty: break
                        try: self.handle(msg)
                        except (ValueError, KeyError, TypeError): pass
                    if self.pending_local:
                        done = self.state['completed'].get(self.id)
                        if done and done[0] >= self.pending_local['seq'] and self.disk['final'] >= self.state['revision']:
                            self.pending_local = None
                    now = time.monotonic()
                    ready = [item for item in self.delayed if item[0] <= now]
                    self.delayed = [item for item in self.delayed if item[0] > now]
                    # Varying delay intentionally reorders traffic in fault scenarios.
                    for _,target,raw in sorted(ready): self.wire(target, raw)
                    if now-self.last_tick >= .12:
                        self.last_tick = now
                        tx = self.disk['tx']
                        if tx: self.fan({'type': tx['phase'], 'proposal': tx['proposal']}, tx['proposal']['base']['roster'])
                        if self.pending_local and not self.pending_local.get('error'):
                            self.send(self.coordinator(), dict(self.pending_local, type='request', revision=self.state['revision']))
                        own = self.signs.get(self.id)
                        if own:
                            self.fan({'type':'status','epoch':self.state['epoch'], 'generation':self.state['generation'], 'incarnation':own['stamp'][0], 'seq':own['stamp'][1], 'body':own['body']}, self.state['roster'])
                    scope=(self.state['generation'],self.state['owner'])
                    if self.relay_scope is not None and self.relay_scope!=scope:
                        self.reset_relay()
                    self.relay_scope=scope
                    if not self.relay_pending and not self.relay_error:
                        try: item = self.relay_out.get_nowait()
                        except queue.Empty: item = None
                        if item is not None:
                            raw,binding=item
                            self.relay_next += 1
                            m = {'type':'relay','incarnation':self.disk['incarnation'], 'seq':self.relay_next,
                                 'generation':self.state['generation'], 'binding':binding, 'data':base64.b64encode(raw).decode()}
                            self.relay_pending = {p:{'msg':m,'at':now,'sent':0} for p in self.state['roster'] if p != self.id}
                    for peer, pending in list(self.relay_pending.items()):
                        if now-pending['at'] > 10:
                            self.relay_error = 'unacknowledged BBSC frame expired'; self.relay_pending.clear(); break
                        if now-pending['sent']>.08:
                            self.send(peer, pending['msg']); pending['sent']=now
                except OSError as error:
                    self.relay_error = str(error)
