"""Native stdout capture for the experimental existing runner; no extra process."""
import json
import subprocess
import time
from pathlib import Path

def open_log(user_dir,env):
    root=Path(user_dir); root.mkdir(parents=True,exist_ok=True)
    for n in range(2,-1,-1):
        old=root/('last_run.log' if n==0 else f'last_run.{n}.log')
        if old.exists(): old.replace(root/f'last_run.{n+1}.log')
    stream=(root/'last_run.log').open('w',encoding='utf-8',buffering=1)
    # Do not dump environment: whitelist only launch identity and booleans.
    safe={k:env.get(k,'') for k in ('BBGL_PROFILE_DIR','BB_USER_DIR','BB_COOP','BB_ONLINE','BBSC_PARTY','BB_P2P_PORT')}
    stream.write('BBGL party launch '+json.dumps(safe)+'\n'); stream.flush()
    return stream

def record_exit(stream,pid,code):
    stream.write(f'\nBBGL party runner pid={pid} exit={code} time={time.time()}\n'); stream.flush()
