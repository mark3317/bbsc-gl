"""Native stdout capture for the existing runner; no extra process."""
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

def write_header(stream,env):
    # Do not dump environment: whitelist only launch identity and booleans.
    safe={k:env.get(k,'') for k in ('BBGL_PROFILE_DIR','BB_USER_DIR','BB_COOP','BB_ONLINE','BBSC_PARTY','BB_P2P_PORT')}
    stream.write('BBGL party launch '+json.dumps(safe)+'\n'); stream.flush()

def native_output(user_dir,env):
    """An existing launcher pipe owns the log; never open a second log for it."""
    owner=env.get('BB_RUN_LOG_OWNER','')
    try:
        piped=stat.S_ISFIFO(os.fstat(sys.stdout.fileno()).st_mode)
    except (AttributeError,OSError,ValueError):
        piped=False
    if owner=='launcher' or (not owner and piped):
        write_header(sys.stdout,env)
        return None,dict(stderr=subprocess.STDOUT)
    stream=open_log(user_dir,env)
    return stream,dict(stdout=stream,stderr=subprocess.STDOUT)

def open_log(user_dir,env):
    root=Path(user_dir); root.mkdir(parents=True,exist_ok=True)
    name=time.strftime('run_%Y%m%d_%H%M%S')
    sequence=1
    while True:
        suffix='' if sequence==1 else f'_{sequence}'
        try:
            stream=(root/f'{name}{suffix}.log').open('x',encoding='utf-8',buffering=1)
            break
        except FileExistsError:
            sequence+=1
    write_header(stream,env)
    return stream

def record_exit(stream,pid,code):
    stream.write(f'\nBBGL party runner pid={pid} exit={code} time={time.time()}\n'); stream.flush()
