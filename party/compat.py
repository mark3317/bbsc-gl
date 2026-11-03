"""In-client, loopback-only native APIs. No old server implementation is launched/imported."""
from __future__ import annotations
import base64,copy,datetime,hashlib,http.server,json,os,queue,re,secrets,select,socket,socketserver,struct,threading,time,uuid
from pathlib import Path
from engine import Engine,canonical
from protobuf import encode,decode

def blob(raw): return struct.pack('<I',len(raw))+raw
def packet(kind,cmd,ident,raw): return struct.pack('<BHIQ',kind,cmd,15+len(raw),ident)+raw
def account(who): return int.from_bytes(hashlib.sha256(who.encode()).digest()[:7],'little')+1000

def game_user_id(who):
    # Bloodborne's HTTP UserId is stored in a signed 32-bit field. NP AccountId
    # remains 64-bit and must never be substituted for this game identity.
    return (account(who) & 0x7fffffff) or 1

def game_user_map(members):
    result={who:game_user_id(who) for who in members}
    if len(set(result.values()))!=len(result):
        raise ValueError('Game UserId collision in invitation; use distinct member IDs')
    return result

def native_name_map(members):
    # Stable party IDs own durable state; native NP handles are the chosen names.
    names={who:m.get('name',who) for who,m in members.items()}
    if any(not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,16}',name)
           for name in names.values()):
        raise ValueError('Invalid native player name')
    if len({name.casefold() for name in names.values()})!=len(names):
        raise ValueError('Players must use different names')
    return names

def json_bins(bins):
    return [dict(x,data=base64.b64encode(x.get('data',b'')).decode()) for x in bins]
def merge_bins(old,new):
    merged={x['attr_id']:x for x in old}
    merged.update({x['attr_id']:x for x in new})
    return [merged[key] for key in sorted(merged)]

def native_bins(bins):
    return [dict(x,data=base64.b64decode(x.get('data',''))) for x in bins]

def recv_exact(sock,size,*,idle=False,deadline=None,budget=10,stopped=None):
    # A healthy idle session has no frame in progress. Once the first byte arrives,
    # one absolute deadline covers the entire header AND body, even with slow drip.
    clock=deadline if deadline is not None else [None if idle else time.monotonic()+budget]
    out=bytearray()
    while len(out)<size:
        if stopped and stopped(): raise EOFError()
        now=time.monotonic()
        if clock[0] is not None and now>=clock[0]: raise TimeoutError('Incomplete native frame deadline')
        wait=.25 if clock[0] is None else min(.25,max(0,clock[0]-now))
        ready,_,_=select.select([sock],[],[],wait)
        if not ready: continue
        part=sock.recv(size-len(out))
        if not part: raise EOFError()
        if clock[0] is None: clock[0]=time.monotonic()+budget
        out.extend(part)
    return bytes(out)

class PrivateHTTPServer(http.server.ThreadingHTTPServer):
    request_queue_size=128

class TcpServer(socketserver.ThreadingTCPServer):
    allow_reuse_address=True; daemon_threads=True

COMMANDS={110:('KickoutRoomMemberRequest','KickoutRoomMemberReply'),115:('SendRoomMessageRequest','SendRoomMessageReply'),0:('LoginRequest','LoginReply'),12:(None,'ServerFeaturesReply'),39:(None,'GetTokenReply'),41:('LookupOnlineIdRequest','LookupOnlineIdReply'),
100:('ContextStartRequest',None),101:('CreateRoomRequest','CreateRoomReply'),102:('JoinRoomRequest','JoinRoomReply'),103:('LeaveRoomRequest','LeaveRoomReply'),
104:('SearchRoomRequest','SearchRoomReply'),105:('RequestSignalingInfosRequest','RequestSignalingInfosReply'),106:('ContextStopRequest',None),107:('SetUserInfoRequest','SetUserInfoReply'),
108:('SetRoomDataInternalRequest','SetRoomDataInternalReply'),109:('SetRoomDataExternalRequest','SetRoomDataExternalReply'),111:('GetWorldInfoListRequest','GetWorldInfoListReply'),
112:('GetRoomDataExternalListRequest','GetRoomDataExternalListReply'),113:('GetUserInfoListRequest','GetUserInfoListReply'),114:('GetRoomMemberDataExternalListRequest','GetRoomMemberDataExternalListReply'),
116:('SetRoomMemberDataInternalRequest','SetRoomMemberDataInternalReply')}

def relay_recipients(raw,state,sender):
    # Public discovery/follow and unknown frames keep their bootstrap semantics.
    # Session state must reach pending/departing peers as well as joined members.
    if len(raw)<18 or raw[:5]!=b'SHAD\x40' or raw[13:17]!=b'SHAD':
        return state['roster']
    if raw[17] not in range(0x22,0x2e): return state['roster']
    room=state.get('room') or {}
    active=set(state['joined']) | set(state['pending']) | set(room.get('members',{})) | set(room.get('departing',{}))
    if state['owner']: active.add(state['owner'])
    return [p for p in state['roster'] if p!=sender and p in active]

class Compatibility:
    def __init__(self,engine):
        self.game_ids=game_user_map(engine.members)
        self.native_names=native_name_map(engine.members)
        self.native_members={name:who for who,name in self.native_names.items()}
        self.e=engine; self.token=secrets.token_hex(24); self.ctx=0; self.np=None; self.np_generation=0
        self.np_lock=threading.Lock(); self.np_operation_lock=threading.Lock(); self.relay_lock=threading.Lock(); self.relay_sock=None; self.relay_generation=0
        self.native={'state':0,'loading':True,'bell':False}; self.observed=False
        self.gate_lock=threading.Lock(); self.closed=False; self.relay_id=0; self.native_bindings={}
        self.previous=copy.deepcopy(engine.state); self.maintenance_seq=None
        self.native_fresh=False; self.recovery_pending=bool(engine.state['owner']==engine.id or engine.id in engine.state['joined'] or engine.id in engine.state['pending'])
        self.release_intent=False; self.latest_cancel=0; self.cancel_floor=0; self.session_id=uuid.uuid4().hex
        self.local_status={'sign':None}
        self.delivered_admission=None
        self.search_diagnostic=None
        self.diagnostics=os.environ.get('BB_PARTY_DIAGNOSTICS',os.environ.get('BB_DIAGNOSTICS','0'))=='1'
        self.logfile=engine.profile/'party-events.jsonl'; self.log_lock=threading.Lock()
        outer=self
        class NP(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.settimeout(10) # send timeout; receive deadlines are per-frame
                with outer.np_lock:
                    outer.np_generation+=1; generation=outer.np_generation
                try:
                    self.request.sendall(packet(3,0,0,struct.pack('<I',1)))
                    authenticated=False
                    handshake_deadline=time.monotonic()+10
                    while not outer.closed:
                        frame=[None if authenticated else handshake_deadline]
                        kind,cmd,size,ident=struct.unpack('<BHIQ',recv_exact(self.request,15,idle=authenticated,deadline=frame,stopped=lambda:outer.closed))
                        if kind!=0 or size<15 or size>262144: return
                        raw=recv_exact(self.request,size-15,deadline=frame,stopped=lambda:outer.closed); spec=COMMANDS.get(cmd)
                        if spec is None:
                            self.request.sendall(packet(1,cmd,ident,b'\x21')); continue
                        try:
                            req={}
                            if spec[0]:
                                if len(raw)<4: raise ValueError('Missing protobuf length')
                                length,=struct.unpack('<I',raw[:4])
                                if length!=len(raw)-4: raise ValueError('Bad protobuf length')
                                req=decode(spec[0],raw[4:])
                            if not authenticated and cmd not in (0,12): raise ValueError('Login required')
                            with outer.np_operation_lock:
                                with outer.np_lock:
                                    if authenticated and (not outer.np or outer.np[1]!=generation): return
                                if cmd==0:
                                    if req.get('npid')!=outer.native_names[engine.id] or req.get('password')!=outer.token: raise ValueError('Wrong local identity')
                                    authenticated=True
                                    with outer.np_lock: outer.np=(self.request,generation)
                                reply=outer.np_command(cmd,req)
                            body=b'\0'+(blob(encode(spec[1],reply)) if spec[1] else b'')
                            outer.log('np_reply',command=cmd,revision=engine.state['revision'])
                        except (ValueError,TimeoutError,KeyError) as ex:
                            outer.log('np_reject',command=cmd,reason=str(ex)); body=b'\x20'
                        with outer.np_lock:
                            self.request.sendall(packet(1,cmd,ident,body))
                except (OSError,EOFError,ValueError): pass
                finally:
                    # Old EOF is transport cleanup only, never a room/member leave.
                    with outer.np_lock:
                        if outer.np and outer.np[1]==generation: outer.np=None
        # Reserve TCP and its native-derived UDP neighbor; ephemeral UDP may already be busy.
        for attempt in range(16):
            self.np_server=TcpServer(('127.0.0.1',0),NP)
            self.np_port=self.np_server.server_address[1]
            self.stun=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            try:
                self.stun.bind(('127.0.0.1',self.np_port+1)); self.stun.settimeout(.25); break
            except (OSError,OverflowError):
                self.stun.close(); self.np_server.server_close()
        else: raise OSError('Cannot reserve native compatibility ports')
        class HTTP(http.server.BaseHTTPRequestHandler):
            protocol_version='HTTP/1.1'
            def setup(self):
                super().setup(); self.connection.settimeout(5)
            def log_message(self,*args): pass
            def do_GET(self): self.respond()
            def do_POST(self): self.respond()
            def respond(self):
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<=size<=65536: raise ValueError('Body too large')
                    raw=self.rfile.read(size); path=self.path.split('?')[0]
                    body=json.loads(raw or '{}')
                    if path.startswith('/party/'):
                        if not secrets.compare_digest(self.headers.get('X-BBSC-Party',''),outer.token):
                            self.send_error(403); return
                        result=outer.control(path,body); content=str(result).encode(); mime='text/plain'
                    elif path.endswith('/ss.info'):
                        content=outer.ss_info(); mime='text/plain'
                    else:
                        result=outer.http_call(path,body,self.headers)
                        content=canonical(result); mime='application/json'
                    self.send_response(200); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(content)))
                    self.end_headers(); self.wfile.write(content)
                except (ValueError,KeyError,TimeoutError) as ex:
                    outer.log('http_reject',path=self.path,reason=str(ex)); self.send_error(409)
                except (OSError,EOFError): pass
        self.http=PrivateHTTPServer(('127.0.0.1',0),HTTP)
        self.http_port=self.http.server_address[1]
        class Relay(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.settimeout(10) # healthy native relay may remain idle indefinitely
                with outer.relay_lock:
                    outer.relay_generation+=1; gen=outer.relay_generation
                    old=outer.relay_sock; outer.relay_sock=self.request
                    engine.reset_relay()
                    if old:
                        try: old.shutdown(socket.SHUT_RDWR)
                        except OSError: pass
                try:
                    self.request.sendall(blob(bytes((127,max(0,len(engine.state['roster'])-1)))))
                    while not outer.closed:
                        frame=[None]
                        size,=struct.unpack('<I',recv_exact(self.request,4,idle=True,deadline=frame,stopped=lambda:outer.closed))
                        if not 18<=size<=65536: return
                        raw=recv_exact(self.request,size,deadline=frame,stopped=lambda:outer.closed)
                        with outer.relay_lock:
                            if gen!=outer.relay_generation: return
                            if raw[:5]!=b'SHAD\x40': return
                            native_id,=struct.unpack('<I',raw[5:9])
                            outer.relay_id=native_id
                            if engine.state['owner'] is not None: engine.relay(raw,{'native_id':native_id,'connection':[engine.disk['incarnation'],gen]},outer.relay_targets(raw))
                except (OSError,EOFError,ValueError): pass
                finally:
                    with outer.relay_lock:
                        if gen==outer.relay_generation: outer.relay_sock=None
        self.relay_server=TcpServer(('127.0.0.1',0),Relay)
        self.relay_port=self.relay_server.server_address[1]
    def relay_targets(self,raw):
        with self.e.lock:return relay_recipients(raw,self.e.state,self.e.id)
    def maintain_command(self,kind,**kw):
        with self.e.lock:
            if self.maintenance_seq is None and not self.e.pending_local:
                self.maintenance_seq=self.e.request(dict(kw,kind=kind))
    def relay_loop(self):
        while not self.closed:
            try:sender,raw,binding=self.e.relay_in.get(timeout=.05)
            except queue.Empty:
                if self.e.relay_error:
                    with self.relay_lock:
                        if self.relay_sock:
                            try:self.relay_sock.shutdown(socket.SHUT_RDWR)
                            except OSError:pass
                continue
            if len(raw)<18 or raw[:5]!=b'SHAD\x40':continue
            native_id,=struct.unpack('<I',raw[5:9]);connection=tuple(binding.get('connection',[]))
            if len(connection)!=2 or native_id!=binding.get('native_id'):continue
            previous=self.native_bindings.get(sender)
            if previous and (connection<previous[0] or (connection==previous[0] and native_id!=previous[1])):continue
            self.native_bindings[sender]=(connection,native_id)
            with self.relay_lock:
                if self.relay_sock:
                    try:self.relay_sock.sendall(blob(raw))
                    except OSError:pass
    def log(self,event,**fields):
        if not self.diagnostics:return
        with self.log_lock:
            with self.logfile.open('a',encoding='utf-8') as f:
                f.write(json.dumps(dict(fields,event=event,id=self.e.id,time=time.time(),generation=self.e.state['generation']))+'\n')
    def start(self):
        for server in (self.np_server,self.http,self.relay_server): threading.Thread(target=server.serve_forever,daemon=True).start()
        threading.Thread(target=self.stun_loop,daemon=True).start()
        threading.Thread(target=self.relay_loop,daemon=True).start()
        threading.Thread(target=self.monitor,daemon=True).start()
        self.log('start',group=self.e.cfg['group'],revision=self.e.state['revision'])
        return self
    def close(self):
        self.closed=True
        for server in (self.np_server,self.http,self.relay_server): server.shutdown(); server.server_close()
        self.stun.close(); self.e.close()
    def publish(self): self.e.publish(self.local_status)
    def state(self):
        with self.e.lock:return copy.deepcopy(self.e.state)
    def command(self,kind,**kw):
        seq=self.e.request(dict(kw,kind=kind))
        try:
            return self.e.wait(seq,8)
        except TimeoutError:
            if kind!='claim': raise
            # A timeout does not cancel the transaction. Check the same ticket
            # again before returning an error that triggers native retry cooldown.
            # Never submit a second consuming claim; bound recovery to one wait.
            self.log('claim_confirmation_retry',sequence=seq)
            return self.e.wait(seq,8)
    def member_data(self,who,m):
        cfg=self.e.members[who]
        return {'npid':self.native_names[who],'member_id':m['slot'],'is_owner':who==self.e.state['owner'],
                'join_date':(self.e.state['generation']<<32)|m.get('incarnation',m['slot']),'nat_type':2,'addr':cfg['host'],
                'port':cfg['p2p'],'account_id':account(who),'platform':2,'bin_attrs_internal':native_bins(m.get('bins',[]))}
    def room_details(self,s):
        room=s['room']; members=room['members']; me=members[self.e.id]['slot']; owner=members[s['owner']]['slot']
        place=lambda m: m['slot']>>4 if room.get('member_id_layout')==2 else m['slot']&15
        mask=sum(1<<(place(m)-1) for m in members.values())
        rd={'public_slots':room['max_slots'],'open_public_slots':room['max_slots']-len(members),
            'max_slot':room['max_slots'],'server_id':1,'world_id':room['world'],'room_id':room['id'],
            'joined_slot_mask':mask,'flags':room['flags'],'bin_attrs_internal':native_bins(room['bins'])}
        return {'room_data':rd,'members':[self.member_data(w,m) for w,m in members.items()],
                'me_member_id':me,'owner_member_id':owner}
    def external(self,s):
        r=s['room']; return {'max_slot':r['max_slots'],'cur_members':len(r['members']),'flags':r['flags'],
            'server_id':1,'world_id':r['world'],'room_id':r['id'],'public_slots':r['max_slots'],
            'open_public_slots':r['max_slots']-len(r['members']),'owner_npid':self.native_names[s['owner']],
            'owner_account_id':account(s['owner']),'owner_platform':2}
    def np_command(self,cmd,r):
        s=self.state(); who=self.e.id
        if cmd==0: return {'user_id':account(who),'friends':[{'npid':self.native_names[p],'online':True} for p in s['roster'] if p!=who]}
        if cmd==12: return {'matching2_enabled':True}
        if cmd==39: return {'user_id':account(who),'npid':self.native_names[who],'token':self.token}
        if cmd==41:
            target=self.native_members.get(r['npid'])
            if target not in s['roster']: raise ValueError('Unknown party member')
            return {'account_id':account(target),'npid':self.native_names[target]}
        if cmd==100: self.ctx=r['ctx_id']; return {}
        if cmd==106: return {}
        if cmd==111: return {'worlds':[{'world_id':1,'rooms_num':int(s['room'] is not None),'room_members_num':len(s['joined'])}]}
        if cmd==105:
            target=self.native_members.get(r['target_npid'])
            if target not in s['roster']: raise ValueError('Unknown signaling target')
            m=self.e.members[target]
            return {'target_npid':self.native_names[target],'target_ip':m['host'],'target_port':m['p2p'],
                    'target_member_id':s['room']['members'].get(target,{}).get('slot',0) if s['room'] else 0}
        if cmd==101:
            if s['owner']!=who or not self.e.finalized(s): raise ValueError('Bell role not finalized')
            self.command('room_create',room={'max_slots':min(5,r.get('max_slots',5)),'world':r.get('world_id',1),
                'flags':r.get('flags',0),'bins':json_bins(r.get('internal_bin_attrs',[])),
                'member_bins':json_bins(r.get('member_bin_attrs',[]))})
            s=self.state(); d=self.room_details(s)
            return {'room_id':s['room']['id'],'server_id':1,'world_id':s['room']['world'],
                    'member_id':d['me_member_id'],'max_slots':s['room']['max_slots'],'cur_members':len(s['room']['members']),'details':d}
        if cmd==102:
            self.command('room_join',room_id=r['room_id'],bins=json_bins(r.get('member_bin_attrs',[])))
            s=self.state(); d=self.room_details(s)
            return {'room_id':s['room']['id'],'member_id':d['me_member_id'],'max_slots':s['room']['max_slots'],
                    'cur_members':len(s['room']['members']),'details':d}
        if cmd==103:
            # Proto3 omits room_id=0 after a failed CreateRoom. It acknowledges
            # no membership; never let it tear down a newer room.
            room_id=r.get('room_id',0)
            if not room_id: return {'room_id':0}
            if s['room'] and s['room']['id']!=room_id: raise ValueError('Stale room leave')
            if s['room'] and (who in s['room']['members'] or who in s['joined']):
                if who==s['owner'] and (s['joined'] or s['pending']): self.command('room_close')
                else: self.command('room_leave')
            return {'room_id':room_id}
        if cmd in (104,112):
            rooms=[self.external(s)] if s['room'] else []
            return {'rooms':rooms,**({'range_start':1,'range_total':len(rooms),'range_result':len(rooms)} if cmd==104 else {})}
        if cmd==113: return {'users':[{'npid':name,'account_id':account(self.native_members[name]),'platform':2}
                                    for name in r.get('npids',[]) if name in self.native_members]}
        if cmd==114:
            if not s['room'] or s['room']['id']!=r['room_id']: return {'members':[]}
            return {'members':[dict(self.member_data(p,m),role=int(p==s['owner'])) for p,m in s['room']['members'].items()]}
        if cmd in (110,115):
            if not s['room'] or s['room']['id']!=r['room_id']: raise ValueError('Stale native room')
            if cmd==110:
                target=next((p for p,m in s['room']['members'].items() if m['slot']==r['target_member_id']),None)
                if not target: raise ValueError('Unknown native member incarnation')
                self.command('kick',target=target)
            else:
                cast=r.get('cast_type',1)
                if cast not in (1,2,3): raise ValueError('Invalid cast type')
                self.command('room_message',message={'cast_type':cast,'targets':r.get('dst_member_ids',[]),'data':base64.b64encode(r.get('msg',b'')).decode()})
            return {'room_id':r['room_id']}
        if cmd==107: return {}
        if cmd in (108,109,116):
            if not s['room'] or s['room']['id']!=r['room_id']: raise ValueError('Stale room update')
            if cmd==108:
                mask=r.get('flag_filter',0)
                flags=(s['room']['flags'] & ~mask) | (r.get('flag_attr',0) & mask)
                self.command('room_update',bins=merge_bins(s['room']['bins'],json_bins(r.get('bin_attrs',[]))),flags=flags)
            elif cmd==116:
                old=s['room']['members'][who].get('bins',[])
                self.command('member_update',bins=merge_bins(old,json_bins(r.get('bin_attrs',[]))))
            # External attributes are not used for private direct room admission.
            return {'room_id':r['room_id']}
        raise ValueError('Unsupported private operation')
    def native_leave_idle(self,n):
        if not self.native_fresh or n.get('loading',True) or n.get('state') not in (0,2,5):return False
        # A saved, stopped menu exit is explicit intent even if native retains
        # Beckoning's SpEffect until title unload. Ordinary ringing still blocks.
        title=n.get('await_title') and n.get('cancel_seq',0)>0 and n['cancel_seq']==self.latest_cancel
        return not n.get('bell') or bool(title)
    def retire_guest_cancel(self):
        # A cancellation belongs to the drained participation, not every later
        # admission in this process. Never retire before final leave + native idle.
        with self.gate_lock, self.e.lock:
            s=self.e.state; n=self.native; room=s['room'] or {}
            if not self.release_intent or not self.native_fresh or self.recovery_pending: return
            if not self.e.finalized(s) or self.e.pending_local: return
            if s['owner']==self.e.id or self.e.id in s['pending'] or self.e.id in s['joined']: return
            if self.e.id in room.get('members',{}) or self.e.id in room.get('departing',{}): return
            if not self.native_leave_idle(n):return
            self.cancel_floor=self.latest_cancel; self.release_intent=False; self.observed=False
            retired=self.cancel_floor;saved_revision=s['revision']
        self.log('guest_cancel_retired',cancel_seq=retired,revision=saved_revision)

    def control(self,path,body):
        if path=='/party/tick':
            self.control('/party/native',body)
            ready=self.control('/party/leave_ready',body) if body.get('await_title') else 0
            # Opt-in extension: older DLLs retain the two-field reply. Read the
            # owner and availability from one finalized snapshot so a temporary
            # fail-closed gate cannot masquerade as a new bell.
            with self.e.lock:
                s=self.e.state; final=self.e.finalized(s)
                available=int(self.e.id in s['roster'] and s['owner'] in (None,self.e.id) and final)
                answer=f"{available} {int(body.get('cancel_seq',0)) if ready else 0}"
                if body.get('bell_notice'):
                    generation=s['generation'] if final and s['owner'] not in (None,self.e.id) else 0
                    answer+=f" {generation}"
                    if body.get('bell_release'):
                        released=s['generation'] if final and s['owner'] is None and available else 0
                        answer+=f" {released}"
                return answer
        if path=='/party/acquire':
            with self.gate_lock:
                s=self.state()
                if s['owner']==self.e.id and self.release_intent: return 0
                if s['owner'] is None:
                    self.command('acquire'); self.observed=False; self.release_intent=False; self.cancel_floor=self.latest_cancel
                s=self.state()
                return int(s['owner']==self.e.id and self.e.finalized(s))
        if path=='/party/native':
            with self.gate_lock:
                self.native=body; self.native_fresh=True
                self.latest_cancel=max(self.latest_cancel,int(body.get('cancel_seq',0)))
                if self.latest_cancel>self.cancel_floor: self.release_intent=True
                if body.get('state') in (1,3,4,6) or body.get('bell'): self.observed=True
            return 1
        if path=='/party/leave_ready':
            with self.gate_lock, self.e.lock:
                s=self.e.state; n=self.native; room=s['room'] or {}
                seq=int(body.get('cancel_seq',0))
                if seq<=0 or seq!=self.latest_cancel or seq!=n.get('cancel_seq'): return 0
                if not self.native_leave_idle(n):return 0
                if not self.e.finalized(s) or self.e.pending_local: return 0
                if s['owner']==self.e.id or self.e.id in s['pending'] or self.e.id in s['joined']: return 0
                return int(self.e.id not in room.get('members',{}) and self.e.id not in room.get('departing',{}))
        if path=='/party/can_beckon':
            with self.e.lock:
                s=self.e.state
                return int(self.e.id in s['roster'] and s['owner'] in (None,self.e.id) and self.e.finalized(s))
        if path=='/party/owner':
            with self.e.lock:
                s=self.e.state
                return int(s['owner']==self.e.id and self.e.finalized(s))
        raise ValueError('Unknown local control')
    def ss_info(self):
        text=Path(__file__).with_name('ss_info_template.xml').read_text(encoding='utf-8-sig')
        here=f'http://127.0.0.1:{self.http_port}'
        text=text.replace('http://{YOUR SHADNET SERVER}:31315',here).replace('http://127.0.0.1:20443',here)
        for tag in ('SummonDataGetListInterval2','SummonDataCreateInterval2'):
            text=re.sub(fr'<{tag}>.*?</{tag}>',f'<{tag}>2</{tag}>',text)
        text=re.sub(r'<(Playlog\w*2)>1</\1>',r'<\1>0</\1>',text)
        return base64.b64encode(text.encode())
    def http_call(self,path,body,headers):
        names={'create':'SummonDataCreateResponse','get':'SummonDataGetListResponse','request':'SummonDataSummonResponse','delete':'SummonDataRemoveResponse'}
        s=self.state(); who=self.e.id
        if path.startswith('/summon_messenger/'):
            if 'UserId' in body and int(body['UserId'])!=self.game_ids[who]:
                raise ValueError('Summon UserId does not belong to this member')
            kind=path.rsplit('/',1)[-1]; result={'ResKind':0,'MessageId':names[kind]}
            if kind=='create':
                self.local_status['sign']=body; self.publish()
                pending=s['pending'].get(who)
                if pending and not (s['room'] and s['room'].get('closing')):
                    result.update({k:v for k,v in pending['claim'].items() if k not in ('MessageId','ResKind')})
                    if self.delivered_admission!=pending.get('ticket',0):
                        self.log('admission_delivered',ticket=pending.get('ticket',0),generation=s['generation'])
                    self.delivered_admission=pending.get('ticket',0)
            elif kind=='get':
                result['SummonDataList']=[]
                diagnostic=[]
                if s['owner']==who and self.e.finalized(s):
                    with self.e.lock: signs=copy.deepcopy(self.e.signs)
                    if self.diagnostics:diagnostic.extend((peer,'not_received') for peer in s['roster'] if peer!=who and peer not in signs)
                    for peer,entry in signs.items():
                        sign=entry['body'].get('sign')
                        reason=('self' if peer==who else 'outside_roster' if peer not in s['roster'] else
                                'pending' if peer in s['pending'] else 'joined' if peer in s['joined'] else
                                'no_sign' if not sign else 'stale' if time.monotonic()-entry['at']>12 else None)
                        if reason:
                            if self.diagnostics:diagnostic.append((peer,reason))
                            continue
                        sign=dict(sign)
                        try:
                            data=bytearray(base64.b64decode(sign.get('SummonData','')))
                            if len(data)==224: data[0x79]=max(1,data[0x79]); sign['SummonData']=base64.b64encode(data).decode()
                        except ValueError:
                            if self.diagnostics:diagnostic.append((peer,'invalid_base64'))
                            continue
                        if self.diagnostics:diagnostic.append((peer,'returned',sign.get('AreaId'),len(data),
                                           list(data[0x78:0x7b]) if len(data)==224 else []))
                        sign.pop('MessageId',None); result['SummonDataList'].append(sign)
                if self.diagnostics:
                    snapshot=(s['owner'],self.e.finalized(s),diagnostic)
                    if snapshot!=self.search_diagnostic:
                        self.search_diagnostic=copy.deepcopy(snapshot)
                        self.log('sign_search',owner=s['owner'],finalized=snapshot[1],
                                 candidates=diagnostic,returned=len(result['SummonDataList']))
            elif kind=='request':
                target=next((p for p in s['roster'] if self.game_ids[p]==int(body['TargetUserId'])),None)
                if target is None: raise ValueError('Unknown claim target')
                if target not in s['pending'] and target not in s['joined']:
                    self.command('claim',target=target,claim=body)
            elif kind=='delete':
                self.local_status['sign']=None; self.publish()
                # Force is the mod's explicit withdrawal of its failed invitation.
                # Ordinary sign refresh/deletion must not withdraw an admission,
                # and a joined/loading native guest must still leave via Matching2.
                # Keeping pending here returned the same failed claim forever and
                # hid the sign from the new owner's search after host rotation.
                n=self.native
                if (body.get('Force') is True and who in s['pending'] and
                    self.delivered_admission==s['pending'][who].get('ticket',0) and
                    self.native_fresh and not n.get('loading',True) and n.get('state') in (0,2,5)):
                    self.command('admission_cancel',ticket=self.delivered_admission)
                    self.delivered_admission=None
                    self.log('failed_admission_withdrawn',revision=self.state()['revision'])
            return result
        lists=['PublishCharacterIdList','BloodMessList','BloodMessEvaluationList','LostBloodMessIdList','ChairMessList','WanderingGhostList','ChannelList','ChannelInfoList','LostChannelIdList','TombMessList','NoticeList','Agreements']
        result={k:[] for k in lists}; result.update(ResKind=0,MessageId='UnknownResponse')
        if path=='/basic_utils/login':
            result.update(ServerVersion=1,UserStatus=0,SessionId=self.session_id,PlatformAccountId=str(body.get('PlatformAccountId',account(who))),LanguageId=19,UserId=self.game_ids[who],IssuerId=100,MessageId='LoginResponse')
        else:
            ids={'/basic_utils/get_normal_notice':'NormalNoticeGetResponse','/basic_utils/get_emergency_notice':'EmergencyNoticeGetResponse','/basic_utils/get_user_agreement':'UserAgreementGetResponse',
                 '/basic_utils/get_datetime':'DateTimeResponse','/basic_utils/sync_chara_id':'SyncCharaIdResponse','/wandering_ghost/get':'WanderingGhostGetResponse',
                 '/wandering_ghost/create':'WanderingGhostCreateResponse','/chair_messenger/get':'ChairMessGetListResponse','/chair_messenger/update':'ChairMessRespawnPointNoticeResponse',
                 '/penalty/check_user_priority_move_count':'UserPropertiesMoveCountCheckResponse'}
            result['MessageId']=ids.get(path,'UnknownResponse'); result['Timestamp']=int(time.time()*1000)
        return result
    def stun_loop(self):
        while not self.closed:
            try:
                raw,addr=self.stun.recvfrom(2048)
                if len(raw)==25 and raw[:5]==b'\xff\xff\xff\xff\x01' and raw[5:21].rstrip(b'\0').decode()==self.native_names[self.e.id]:
                    echo=b'\xff'*4+socket.inet_aton(self.e.member['host'])+struct.pack('!H',self.e.member['p2p'])
                    self.stun.sendto(echo,addr)
            except (OSError,UnicodeError): pass
    def notify(self,event,member=None,room=None,cause=1,error=0):
        s=room or self.state(); r=s['room']
        if not r or not self.ctx: return
        obj={'ctx_id':self.ctx,'room_id':r['id'],'event':event,'event_cause':cause,'error_code':error}
        if member: obj['member']=self.member_data(*member)
        else: obj['bin_attrs']=native_bins(r['bins']); obj['flags']=r['flags']
        raw=packet(2,10,0,blob(encode('NotifyRoomEvent',obj)))
        with self.np_lock:
            if self.np:
                try: self.np[0].sendall(raw)
                except OSError: pass
    def monitor(self):
        while not self.closed:
            time.sleep(.05)
            try:
                if self.maintenance_seq is not None:
                    try:
                        done,_=self.e.poll(self.maintenance_seq)
                        if done:self.maintenance_seq=None
                    except ValueError:self.maintenance_seq=None
                confirmed,changed=self.e.confirmed_state(self.previous['revision'])
                if not confirmed:continue
                old=self.previous;s=changed if changed is not None else old
                if changed is not None:
                    self.log('final',revision=s['revision'],owner=s['owner'],members=list(s['joined']),pending=list(s['pending']),room_id=s['room']['id'] if s['room'] else None,closing=bool(s['room'] and s['room'].get('closing')))
                    oldroom=old.get('room'); room=s.get('room')
                    if oldroom and room and oldroom['id']==room['id']:
                        if room.get('closing') and not oldroom.get('closing') and self.e.id!=s['owner']:
                            self.notify(0x1104,room=s)
                        for p,m in room['members'].items():
                            if p!=self.e.id and p not in oldroom['members']: self.notify(0x1101,(p,m),s)
                        for p,m in oldroom['members'].items():
                            if p not in room['members']:
                                kicked=p in room.get('departing',{})
                                if p==self.e.id and kicked: self.notify(0x1103,room=old,cause=2,error=0xFF000019)
                                elif p!=self.e.id: self.notify(0x1102,(p,m),old,cause=2 if kicked else 1)
                        message=room.get('message')
                        if message and message!=oldroom.get('message') and self.e.id in room['members']:
                            me=room['members'][self.e.id]['slot']
                            if message['cast_type']==1 or me in message['targets']:
                                source=message['sender']; src=room['members'].get(source)
                                if src:
                                    obj={'ctx_id':self.ctx,'room_id':room['id'],'src_member_id':src['slot'],
                                         'event':0x2102,'cast_type':message['cast_type'],'dst_member_ids':message['targets'],
                                         'src_npid':self.native_names[source],'src_account_id':account(source),'src_platform':2,'msg':base64.b64decode(message['data'])}
                                    with self.np_lock:
                                        if self.np:
                                            try: self.np[0].sendall(packet(2,11,0,blob(encode('NotifyRoomMessage',obj))))
                                            except OSError: pass
                        if room['bins']!=oldroom['bins'] or room['flags']!=oldroom['flags']: self.notify(0x1106,room=s)
                    self.previous=s
                self.retire_guest_cancel()
                n=self.native
                # Explicit native termination is required; EOF/loading/death never do this.
                recovery=self.native_fresh and self.recovery_pending
                if recovery and self.native_leave_idle(n):
                    self.recovery_pending=False; self.release_intent=True; self.observed=True
                # A confirmed owner LeaveRoom closes admission first. Once guests
                # acknowledge and native is idle, retire that room even if the
                # Beckoning effect remains. World ownership still needs cancel.
                if s['owner']==self.e.id and s['room'] and s['room'].get('closing') and not s['joined'] and not s['pending'] and not n.get('loading',True) and n.get('state') in (0,2,5) and not self.e.pending_local:
                    self.maintain_command('room_leave')
                    continue
                if (self.observed or recovery or self.e.id in s['pending']) and (self.release_intent or (s['room'] and (s['room'].get('closing') or self.e.id in s['room'].get('departing',{})))) and self.native_leave_idle(n) and not self.e.pending_local:
                    if self.e.id in s['pending']:
                        self.maintain_command('admission_cancel',ticket=s['pending'][self.e.id].get('ticket',0))
                    elif self.e.id in s['joined'] and s['room'] and (self.release_intent or s['room'].get('closing') or self.e.id in s['room'].get('departing',{}) or recovery):
                        self.maintain_command('room_leave')
                    elif s['owner']==self.e.id and not s['joined'] and not s['pending']:
                        if s['room']: self.maintain_command('room_leave')
                        else:
                            self.maintain_command('release')
            except (ValueError,TimeoutError,OSError,KeyError): pass

def start_from_environment(env,port):
    cfg=json.loads(Path(env['BB_PARTY_CONFIG']).read_text(encoding='utf-8-sig'))
    member=env['BB_PARTY_MEMBER']; profile=Path(env['BBGL_PROFILE_DIR'])
    state_dir=profile/'coop/party/groups'/cfg['group']
    engine=Engine(cfg,member,state_dir).start(); compat=Compatibility(engine).start()
    native=Path(port)/'coop/client/bbsc/bbsc-launch.exe'
    probe=Path(port)/'bin/bb-probe.exe'
    if not probe.exists(): probe=Path(port)/'bb-probe.exe'
    overrides=state_dir/'host_overrides.json'
    overrides.write_text(json.dumps({'https://ss4.scej-network.jp:20443':f'http://127.0.0.1:{compat.http_port}'}),encoding='utf-8')
    env.update(BBSC_PARTY='1',BBSC_PARTY_INSTANCE=cfg['group']+'-'+member,BBSC_PARTY_PORT=str(compat.http_port),BBSC_PARTY_TOKEN=compat.token,
        BBSC_RELAY=f'127.0.0.1:{compat.relay_port}',BB_SHADNET_SERVER=f'127.0.0.1:{compat.np_port}',
        BB_SHADNET_WEBAPI=f'http://127.0.0.1:{compat.http_port}',BB_SHADNET_NPID=compat.native_names[member],BB_SHADNET_PASSWORD=compat.token,
        BB_HOST_OVERRIDES=str(overrides),BB_P2P_PORT=str(engine.member['p2p']),BB_P2P_RELAY='off',
        BB_ONLINE='1',BB_COOP='1',BB_UPNP='0',BB_PROBE=str(native),BBSC_EMULATOR=str(probe),BBSC_DATA_DIR=str(profile/'coop/bbsc'))
    for key in ('BB_NET_BACKEND','BB_THD_TOKEN','BB_THD_SERVER'): env.pop(key,None)
    return compat
