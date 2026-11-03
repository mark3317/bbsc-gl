"""In-client, loopback-only native APIs. No old server implementation is launched/imported."""
from __future__ import annotations
import base64,copy,datetime,hashlib,http.server,json,os,queue,re,secrets,socket,socketserver,struct,threading,time,uuid
from pathlib import Path
from engine import Engine,canonical
from protobuf import encode,decode

def blob(raw): return struct.pack('<I',len(raw))+raw
def packet(kind,cmd,ident,raw): return struct.pack('<BHIQ',kind,cmd,15+len(raw),ident)+raw
def account(who): return int.from_bytes(hashlib.sha256(who.encode()).digest()[:7],'little')+1000
def json_bins(bins):
    return [dict(x,data=base64.b64encode(x.get('data',b'')).decode()) for x in bins]
def native_bins(bins):
    return [dict(x,data=base64.b64decode(x.get('data',''))) for x in bins]

def recv_exact(sock,size):
    out=bytearray()
    while len(out)<size:
        part=sock.recv(size-len(out))
        if not part: raise EOFError()
        out.extend(part)
    return bytes(out)

class TcpServer(socketserver.ThreadingTCPServer):
    allow_reuse_address=True; daemon_threads=True

COMMANDS={0:('LoginRequest','LoginReply'),12:(None,'ServerFeaturesReply'),39:(None,'GetTokenReply'),41:('LookupOnlineIdRequest','LookupOnlineIdReply'),
100:('ContextStartRequest',None),101:('CreateRoomRequest','CreateRoomReply'),102:('JoinRoomRequest','JoinRoomReply'),103:('LeaveRoomRequest','LeaveRoomReply'),
104:('SearchRoomRequest','SearchRoomReply'),105:('RequestSignalingInfosRequest','RequestSignalingInfosReply'),106:('ContextStopRequest',None),107:('SetUserInfoRequest','SetUserInfoReply'),
108:('SetRoomDataInternalRequest','SetRoomDataInternalReply'),109:('SetRoomDataExternalRequest','SetRoomDataExternalReply'),111:('GetWorldInfoListRequest','GetWorldInfoListReply'),
112:('GetRoomDataExternalListRequest','GetRoomDataExternalListReply'),113:('GetUserInfoListRequest','GetUserInfoListReply'),114:('GetRoomMemberDataExternalListRequest','GetRoomMemberDataExternalListReply'),
116:('SetRoomMemberDataInternalRequest','SetRoomMemberDataInternalReply')}

class Compatibility:
    def __init__(self,engine):
        self.e=engine; self.token=secrets.token_hex(24); self.ctx=0; self.np=None; self.np_generation=0
        self.np_lock=threading.Lock(); self.np_operation_lock=threading.Lock(); self.relay_lock=threading.Lock(); self.relay_sock=None; self.relay_generation=0
        self.native={'state':0,'loading':True,'bell':False}; self.observed=False; self.acquiring=False
        self.gate_lock=threading.Lock(); self.closed=False; self.relay_id=0; self.native_bindings={}
        self.previous=copy.deepcopy(engine.state); self.recovering=copy.deepcopy(engine.state)
        self.native_fresh=False; self.recovery_pending=bool(engine.state['owner']==engine.id or engine.id in engine.state['joined'] or engine.id in engine.state['pending'])
        self.release_intent=False; self.latest_cancel=0; self.cancel_floor=0; self.session_id=uuid.uuid4().hex
        self.local_status={'sign':None,'placement':'','relay_id':0,'native':self.native}
        self.logfile=engine.profile/'party-events.jsonl'; self.log_lock=threading.Lock()
        outer=self
        class NP(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.settimeout(20)
                with outer.np_lock:
                    outer.np_generation+=1; generation=outer.np_generation
                try:
                    self.request.sendall(packet(3,0,0,struct.pack('<I',1)))
                    authenticated=False
                    while not outer.closed:
                        kind,cmd,size,ident=struct.unpack('<BHIQ',recv_exact(self.request,15))
                        if kind!=0 or size<15 or size>262144: return
                        raw=recv_exact(self.request,size-15); spec=COMMANDS.get(cmd)
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
                                    if req.get('npid')!=engine.id or req.get('password')!=outer.token: raise ValueError('Wrong local identity')
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
        self.http=http.server.ThreadingHTTPServer(('127.0.0.1',0),HTTP)
        self.http_port=self.http.server_address[1]
        class Relay(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.settimeout(15)
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
                        size,=struct.unpack('<I',recv_exact(self.request,4))
                        if not 18<=size<=65536: return
                        raw=recv_exact(self.request,size)
                        with outer.relay_lock:
                            if gen!=outer.relay_generation: return
                            if raw[:5]!=b'SHAD\x40': return
                            native_id,=struct.unpack('<I',raw[5:9])
                            outer.relay_id=native_id; outer.local_status['relay_id']=native_id
                            outer.publish()
                            if engine.state['owner'] is not None: engine.relay(raw,{'native_id':native_id,'connection':[engine.disk['incarnation'],gen]})
                except (OSError,EOFError,ValueError): pass
                finally:
                    with outer.relay_lock:
                        if gen==outer.relay_generation: outer.relay_sock=None
        self.relay_server=TcpServer(('127.0.0.1',0),Relay)
        self.relay_port=self.relay_server.server_address[1]
    def log(self,event,**fields):
        with self.log_lock:
            with self.logfile.open('a',encoding='utf-8') as f:
                f.write(json.dumps(dict(fields,event=event,id=self.e.id,time=time.time(),generation=self.e.state['generation']))+'\n')
    def start(self):
        for server in (self.np_server,self.http,self.relay_server): threading.Thread(target=server.serve_forever,daemon=True).start()
        threading.Thread(target=self.stun_loop,daemon=True).start()
        threading.Thread(target=self.monitor,daemon=True).start()
        self.log('start',group=self.e.cfg['group'],revision=self.e.state['revision'])
        return self
    def close(self):
        self.closed=True
        for server in (self.np_server,self.http,self.relay_server): server.shutdown(); server.server_close()
        self.stun.close(); self.e.close()
    def publish(self): self.e.publish(self.local_status)
    def state(self): return self.e.snapshot()['state']
    def command(self,kind,**kw):
        seq=self.e.request(dict(kw,kind=kind)); return self.e.wait(seq,8)
    def member_data(self,who,m):
        cfg=self.e.members[who]
        return {'npid':who,'member_id':m['slot'],'is_owner':who==self.e.state['owner'],
                'join_date':(self.e.state['generation']<<32)|m['slot'],'nat_type':2,'addr':cfg['host'],
                'port':cfg['p2p'],'account_id':account(who),'platform':2,'bin_attrs_internal':native_bins(m.get('bins',[]))}
    def room_details(self,s):
        room=s['room']; members=room['members']; me=members[self.e.id]['slot']; owner=members[s['owner']]['slot']
        mask=sum(1<<((m['slot']&15)-1) for m in members.values())
        rd={'public_slots':room['max_slots'],'open_public_slots':room['max_slots']-len(members),
            'max_slot':room['max_slots'],'server_id':1,'world_id':room['world'],'room_id':room['id'],
            'joined_slot_mask':mask,'flags':room['flags'],'bin_attrs_internal':native_bins(room['bins'])}
        return {'room_data':rd,'members':[self.member_data(w,m) for w,m in members.items()],
                'me_member_id':me,'owner_member_id':owner}
    def external(self,s):
        r=s['room']; return {'max_slot':r['max_slots'],'cur_members':len(r['members']),'flags':r['flags'],
            'server_id':1,'world_id':r['world'],'room_id':r['id'],'public_slots':r['max_slots'],
            'open_public_slots':r['max_slots']-len(r['members']),'owner_npid':s['owner'],
            'owner_account_id':account(s['owner']),'owner_platform':2}
    def np_command(self,cmd,r):
        s=self.state(); who=self.e.id
        if cmd==0: return {'user_id':account(who),'friends':[{'npid':p,'online':True} for p in s['roster'] if p!=who]}
        if cmd==12: return {'matching2_enabled':True}
        if cmd==39: return {'user_id':account(who),'npid':who,'token':self.token}
        if cmd==41:
            target=r['npid']
            if target not in s['roster']: raise ValueError('Unknown party member')
            return {'account_id':account(target),'npid':target}
        if cmd==100: self.ctx=r['ctx_id']; return {}
        if cmd==106: return {}
        if cmd==111: return {'worlds':[{'world_id':1,'rooms_num':int(s['room'] is not None),'room_members_num':len(s['joined'])}]}
        if cmd==105:
            target=r['target_npid']
            if target not in s['roster']: raise ValueError('Unknown signaling target')
            m=self.e.members[target]
            return {'target_npid':target,'target_ip':m['host'],'target_port':m['p2p'],
                    'target_member_id':s['room']['members'].get(target,{}).get('slot',0) if s['room'] else 0}
        if cmd==101:
            if s['owner']!=who or self.e.disk['final']!=s['revision']: raise ValueError('Bell role not finalized')
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
            if s['room'] and s['room']['id']!=r['room_id']: raise ValueError('Stale room leave')
            if s['room'] and who in s['room']['members']:
                if who==s['owner'] and (s['joined'] or s['pending']): self.command('room_close')
                else: self.command('room_leave')
            return {'room_id':r['room_id']}
        if cmd in (104,112):
            rooms=[self.external(s)] if s['room'] else []
            return {'rooms':rooms,**({'range_start':1,'range_total':len(rooms),'range_result':len(rooms)} if cmd==104 else {})}
        if cmd==113: return {'users':[{'npid':p,'account_id':account(p),'platform':2} for p in r.get('npids',[]) if p in s['roster']]}
        if cmd==114:
            if not s['room'] or s['room']['id']!=r['room_id']: return {'members':[]}
            return {'members':[dict(self.member_data(p,m),role=int(p==s['owner'])) for p,m in s['room']['members'].items()]}
        if cmd==107: return {}
        if cmd in (108,109,116):
            if not s['room'] or s['room']['id']!=r['room_id']: raise ValueError('Stale room update')
            if cmd==108: self.command('room_update',bins=json_bins(r.get('bin_attrs',[])),flags=r.get('flag_attr',s['room']['flags']))
            elif cmd==116: self.command('member_update',bins=json_bins(r.get('bin_attrs',[])))
            # External attributes are not used for private direct room admission.
            return {'room_id':r['room_id']}
        raise ValueError('Unsupported private operation')
    def control(self,path,body):
        if path=='/party/acquire':
            with self.gate_lock:
                s=self.state()
                if s['owner']==self.e.id and self.release_intent: return 0
                if s['owner'] is None:
                    self.command('acquire'); self.observed=False; self.release_intent=False; self.cancel_floor=self.latest_cancel
                s=self.state()
                return int(s['owner']==self.e.id and self.e.disk['final']==s['revision'])
        if path=='/party/native':
            self.native=body; self.native_fresh=True; self.local_status['native']=body; self.publish()
            self.latest_cancel=max(self.latest_cancel,int(body.get('cancel_seq',0)))
            if self.latest_cancel>self.cancel_floor: self.release_intent=True
            if body.get('state') in (1,3,4,6) or body.get('bell'): self.observed=True
            return 1
        if path=='/party/can_beckon':
            s=self.state(); return int(self.e.id in s['roster'] and s['owner'] in (None,self.e.id) and self.e.disk['final']==s['revision'])
        if path=='/party/owner':
            s=self.state(); return int(s['owner']==self.e.id and self.e.disk['final']==s['revision'])
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
            kind=path.rsplit('/',1)[-1]; result={'ResKind':0,'MessageId':names[kind]}
            if kind=='create':
                self.local_status['sign']=body; self.publish()
                pending=s['pending'].get(who)
                if pending and not (s['room'] and s['room'].get('closing')): result.update({k:v for k,v in pending['claim'].items() if k not in ('MessageId','ResKind')})
            elif kind=='get':
                result['SummonDataList']=[]
                if s['owner']==who and self.e.disk['final']==s['revision']:
                    placement=headers.get('X-ShadPS4-Bloodborne-Host-Placement','')
                    self.local_status['placement']=placement; self.publish()
                    with self.e.lock: signs=copy.deepcopy(self.e.signs)
                    for peer,entry in signs.items():
                        sign=entry['body'].get('sign')
                        if peer==who or peer not in s['roster'] or peer in s['pending'] or peer in s['joined'] or not sign or time.monotonic()-entry['at']>12: continue
                        sign=dict(sign)
                        try:
                            data=bytearray(base64.b64decode(sign.get('SummonData','')))
                            if len(data)==224: data[0x79]=max(1,data[0x79]); sign['SummonData']=base64.b64encode(data).decode()
                        except ValueError: continue
                        sign.pop('MessageId',None); result['SummonDataList'].append(sign)
            elif kind=='request':
                target=next((p for p in s['roster'] if account(p)==int(body['TargetUserId'])),None)
                if target is None: raise ValueError('Unknown claim target')
                if target not in s['pending'] and target not in s['joined']:
                    self.command('claim',target=target,claim=body)
            elif kind=='delete':
                self.local_status['sign']=None; self.publish()
                # Only explicit local native idle can cancel an unfinished admission.
                # Maintenance polls the native bridge; HTTP deletion alone is not leave.
            return result
        lists=['PublishCharacterIdList','BloodMessList','BloodMessEvaluationList','LostBloodMessIdList','ChairMessList','WanderingGhostList','ChannelList','ChannelInfoList','LostChannelIdList','TombMessList','NoticeList','Agreements']
        result={k:[] for k in lists}; result.update(ResKind=0,MessageId='UnknownResponse')
        if path=='/basic_utils/login':
            result.update(ServerVersion=1,UserStatus=0,SessionId=self.session_id,PlatformAccountId=str(body.get('PlatformAccountId',account(who))),LanguageId=19,UserId=account(who),IssuerId=100,MessageId='LoginResponse')
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
                if len(raw)==25 and raw[:5]==b'\xff\xff\xff\xff\x01' and raw[5:21].rstrip(b'\0').decode()==self.e.id:
                    echo=b'\xff'*4+socket.inet_aton(self.e.member['host'])+struct.pack('!H',self.e.member['p2p'])
                    self.stun.sendto(echo,addr)
            except (OSError,UnicodeError): pass
    def notify(self,event,member=None,room=None):
        s=room or self.state(); r=s['room']
        if not r or not self.ctx: return
        obj={'ctx_id':self.ctx,'room_id':r['id'],'event':event,'event_cause':1}
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
                s=self.state(); old=self.previous
                if self.e.disk['final']!=s['revision']: continue
                if s!=old:
                    self.log('final',revision=s['revision'],owner=s['owner'],members=list(s['joined']),pending=list(s['pending']))
                    oldroom=old.get('room'); room=s.get('room')
                    if oldroom and room and oldroom['id']==room['id']:
                        if room.get('closing') and not oldroom.get('closing') and self.e.id!=s['owner']:
                            self.notify(0x1104,room=s)
                        for p,m in room['members'].items():
                            if p!=self.e.id and p not in oldroom['members']: self.notify(0x1101,(p,m),s)
                        for p,m in oldroom['members'].items():
                            if p!=self.e.id and p not in room['members']: self.notify(0x1102,(p,m),old)
                        if room['bins']!=oldroom['bins'] or room['flags']!=oldroom['flags']: self.notify(0x1106,room=s)
                    self.previous=copy.deepcopy(s)
                # Forward all chunks individually. ACK IDs, generation and per-member native IDs
                # are checked before existing BBSC dispatch sees an opaque frame.
                while not self.e.relay_in.empty():
                    sender,raw,binding=self.e.relay_in.get_nowait()
                    if len(raw)<18 or raw[:5]!=b'SHAD\x40': continue
                    native_id,=struct.unpack('<I',raw[5:9])
                    connection=tuple(binding.get('connection',[]))
                    if len(connection)!=2 or native_id!=binding.get('native_id'): continue
                    previous=self.native_bindings.get(sender)
                    if previous and (connection<previous[0] or (connection==previous[0] and native_id!=previous[1])): continue
                    self.native_bindings[sender]=(connection,native_id)
                    with self.relay_lock:
                        if self.relay_sock:
                            try: self.relay_sock.sendall(blob(raw))
                            except OSError: pass
                if self.e.relay_error:
                    with self.relay_lock:
                        if self.relay_sock:
                            try: self.relay_sock.shutdown(socket.SHUT_RDWR)
                            except OSError: pass
                n=self.native
                # Explicit native termination is required; EOF/loading/death never do this.
                recovery=self.native_fresh and self.recovery_pending
                if recovery and not n.get('loading',True) and n.get('state') in (0,2,5) and not n.get('bell'):
                    self.recovery_pending=False; self.release_intent=True; self.observed=True
                if (self.observed or recovery) and (self.release_intent or (s['room'] and s['room'].get('closing'))) and not n.get('loading',True) and n.get('state') in (0,2,5) and not n.get('bell') and not self.e.pending_local:
                    if self.e.id in s['pending']:
                        self.command('admission_cancel')
                    elif self.e.id in s['joined'] and s['room'] and (s['room'].get('closing') or recovery):
                        self.command('room_leave')
                    elif s['owner']==self.e.id and not s['joined'] and not s['pending']:
                        if s['room']: self.command('room_leave')
                        else:
                            self.command('release'); self.observed=False; self.release_intent=False; self.cancel_floor=self.latest_cancel
            except (ValueError,TimeoutError,OSError,KeyError): pass

def start_from_environment(env,port):
    cfg=json.loads(Path(env['BB_PARTY_CONFIG']).read_text(encoding='utf-8-sig'))
    member=env['BB_PARTY_MEMBER']; profile=Path(env['BBGL_PROFILE_DIR'])
    engine=Engine(cfg,member,profile/'party').start(); compat=Compatibility(engine).start()
    native=Path(port)/'coop/client/bbsc/bbsc-launch.exe'
    probe=Path(port)/'bin/bb-probe.exe'
    if not probe.exists(): probe=Path(port)/'bb-probe.exe'
    overrides=profile/'party/host_overrides.json'
    overrides.write_text(json.dumps({'https://ss4.scej-network.jp:20443':f'http://127.0.0.1:{compat.http_port}'}),encoding='utf-8')
    env.update(BBSC_PARTY='1',BBSC_PARTY_INSTANCE=cfg['group']+'-'+member,BBSC_PARTY_PORT=str(compat.http_port),BBSC_PARTY_TOKEN=compat.token,
        BBSC_RELAY=f'127.0.0.1:{compat.relay_port}',BB_SHADNET_SERVER=f'127.0.0.1:{compat.np_port}',
        BB_SHADNET_WEBAPI=f'http://127.0.0.1:{compat.http_port}',BB_SHADNET_NPID=member,BB_SHADNET_PASSWORD=compat.token,
        BB_HOST_OVERRIDES=str(overrides),BB_P2P_PORT=str(engine.member['p2p']),BB_P2P_RELAY='off',
        BB_ONLINE='1',BB_COOP='1',BB_UPNP='0',BB_PROBE=str(native),BBSC_EMULATOR=str(probe),BBSC_DATA_DIR=str(profile/'coop/bbsc'))
    for key in ('BB_NET_BACKEND','BB_THD_TOKEN','BB_THD_SERVER'): env.pop(key,None)
    return compat
