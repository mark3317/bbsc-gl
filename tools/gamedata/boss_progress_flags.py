"""Print literal boss-encounter denylist candidates from CUSA03173 event scripts.
Usage: python tools/gamedata/boss_progress_flags.py <dvdroot_ps4/event>
No files are changed. Inspect conditional flags before extending the runtime list.
"""
import sys,struct
from pathlib import Path
from emevd import Emevd
flags=set()
for path in sorted(Path(sys.argv[1]).glob('*.emevd.dcx')):
 for event, instructions in Emevd(path).events:
  if not any(b==2003 and i==11 and len(a)>=16 and struct.unpack_from('<I',a)[0]==1 for b,i,a in instructions):
   continue
  candidates={event}
  candidates.update(struct.unpack_from('<I',a,4)[0] for b,i,a in instructions if b==3 and i==0 and len(a)>=8)
  candidates={f for f in candidates if 10000000<=f<20000000 and f%10000>=4000}
  flags.update(candidates)
  print(path.name,event,sorted(candidates))
print('Sorted encounter flags:',sorted(flags))
