import argparse,json,sys,threading
from pathlib import Path
from engine import Engine
ap=argparse.ArgumentParser(); ap.add_argument('--invite'); ap.add_argument('--id'); ap.add_argument('--profile'); ap.add_argument('--fault',default='{}'); a=ap.parse_args()
e=Engine(json.loads(Path(a.invite).read_text(encoding='utf-8-sig')),a.id,a.profile,fault=json.loads(a.fault)).start()
lock=threading.Lock()
def emit(x):
    with lock: print(json.dumps(x),flush=True)
emit({'ready':a.id})
def command(r):
    try: emit({'token':r['token'],'result':e.command(r['op'],r.get('timeout',12))})
    except (ValueError,TimeoutError) as ex: emit({'token':r['token'],'error':str(ex)})
try:
    for line in sys.stdin:
        r=json.loads(line); c=r['cmd']; t=r['token']
        if c=='state': emit(dict(e.snapshot(),token=t))
        elif c=='command': threading.Thread(target=command,args=(r,),daemon=True).start()
        elif c=='block':
            with e.lock: e.blocked=set(r['peers'])
            emit({'token':t,'ok':True})
        elif c=='relay': e.relay(r['data'].encode()); emit({'token':t,'ok':True})
        elif c=='received':
            frames=[]
            while not e.relay_in.empty(): frames.append(e.relay_in.get_nowait()[1].decode())
            emit({'token':t,'frames':frames})
finally: e.close()
