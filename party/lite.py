import argparse,json,sys,threading
from pathlib import Path
from engine import Engine
ap=argparse.ArgumentParser(); ap.add_argument('--invite'); ap.add_argument('--id'); ap.add_argument('--profile'); ap.add_argument('--fault',default='{}'); ap.add_argument('--compat',action='store_true'); a=ap.parse_args()
cfg=json.loads(Path(a.invite).read_text(encoding='utf-8-sig'))
if cfg.get('mode')=='dynamic-worlds-v1':
    from dynamic import DynamicEngine
    e=DynamicEngine(cfg,a.id,a.profile,cfg['peers_file']).start()
else:
    e=Engine(cfg,a.id,a.profile,fault=json.loads(a.fault)).start()
lock=threading.Lock()
def emit(x):
    with lock: print(json.dumps(x),flush=True)
compat=None
if a.compat:
    from compat import Compatibility
    compat=Compatibility(e).start()
emit(dict(ready=a.id,**({'http':compat.http_port,'np':compat.np_port,'relay':compat.relay_port,'token':compat.token} if compat else {})))
def command(r):
    try: emit({'token':r['token'],'result':e.command(r['op'],r.get('timeout',12))})
    except (ValueError,TimeoutError) as ex: emit({'token':r['token'],'error':str(ex)})
try:
    for line in sys.stdin:
        r=json.loads(line); c=r['cmd']; t=r['token']
        if c=='status':
            with e.lock:emit({'token':t,'signs':e.signs,'tx':e.status_tx})
        elif c=='state': emit(dict(e.snapshot(),token=t))
        elif c=='command': threading.Thread(target=command,args=(r,),daemon=True).start()
        elif c=='block':
            with e.lock: e.blocked=set(r['peers'])
            emit({'token':t,'ok':True})
        elif c=='fault':
            with e.lock: e.fault=r['value']
            emit({'token':t,'ok':True})
        elif c=='inject': e.send(r['target'],r['message']); emit({'token':t,'ok':True})
        elif c=='reset_relay': e.reset_relay(); emit({'token':t,'ok':True})
        elif c=='relay': e.relay(r['data'].encode(),recipients=r.get('recipients')); emit({'token':t,'ok':True})
        elif c=='received':
            frames=[]
            while not e.relay_in.empty(): frames.append(e.relay_in.get_nowait()[1].decode())
            emit({'token':t,'frames':frames})
finally:
    if compat: compat.close()
    else: e.close()
