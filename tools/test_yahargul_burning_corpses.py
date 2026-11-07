"""Original m28 event + production snapshot/progress gates; fixture memory only."""
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/gamedata'))
from emevd import Emevd
from msb import Msb

game = Path(os.environ['BB_GAME'])
evd = Emevd(game / 'event/m28_00_00_00.emevd.dcx')
events = dict(evd.events)
original = events[12805920]
assert original == [
    (1003, 101, bytes.fromhex('0000000000000000')),
    (2006, 5, struct.pack('<II', 0, 1)),
    (1000, 4, struct.pack('<I', 0)),
    (1014, 0, b''),
    (1003, 1, bytes.fromhex('0101020000000000')),
    (2006, 4, struct.pack('<III', 0, 100, 928020)),
    (2003, 5, struct.pack('<7I', 2800560, 0, 100, 6032, 0, 0, 0)),
    (1001, 0, struct.pack('<f', 2)),
    (1000, 4, struct.pack('<I', 1)),
]
calls = [struct.unpack('<4I', a) for b, c, a in events[0]
         if b == 2000 and c == 0 and struct.unpack_from('<I', a, 4)[0] == 12805920]
assert calls == [(i, 12805920, 2801600 + i, 12805942 + i * 5) for i in range(4)]
msb = Msb(game / 'map/MapStudio/m28_00_00_00.msb.dcx')
assert all(next(p for p in msb.parts if p['entity_id'] == obj)['model'] == 'o281110'
           for _, _, obj, _ in calls)
source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')

def function(signature):
    a = source.index(signature + ' {')
    end = source.index('{', a) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[a:end] + '\n'

code = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
#include "core/bbsc_chalice.h"
namespace Chalice=Core::Bloodborne::Chalice;
using u8=uint8_t;using u32=uint32_t;
constexpr size_t BbscWorldGroupBytes=125;
constexpr std::array<u32,1> BbscEncounterProgressFlags{12804800};
bool IsBbscNpcQuestFlag(u32){return false;}
bool IsBbscPersonalMapEvent(u32){return false;}
using Group=std::array<u8,125>;
bool flag(const Group& g,u32 f){return (g[(f%1000)/8]&(0x80u>>(f%8)))!=0;}
void set(Group& g,u32 f,bool v){auto m=0x80u>>(f%8);auto& b=g[(f%1000)/8];b=v?(b|m):(b&~m);}
struct Instruction{int bank,op;std::vector<u8> args;};
u32 arg(const Instruction& i,size_t at){u32 v;memcpy(&v,i.args.data()+at,4);return v;}
'''
for signature in ('bool BbscSharedMapProgressAllowed(u32 flag)',
                  'u8 BbscSharedProgressByte(u32 key, size_t byte, u8 incoming)',
                  'void BbscMergeSharedProgressGroup(u32 key, u8* live, const u8* incoming)'):
    code += function(signature)
code += 'const std::vector<Instruction> original={' + ','.join(
    '{%d,%d,{%s}}' % (b, c, ','.join(map(str, a))) for b, c, a in original) + '};\n'
code += r'''
struct Visual{int creates=0,deletes=0,hazards=0;bool visible=false;float seconds=0;};
// Execute the verified ORIGINAL instruction stream with native slot/flag semantics.
void run(Group& local,int slot,Visual& fx){
 const u32 done=12805920+slot,exhausted=12805942+slot*5;
 for(size_t pc=0;pc<original.size();++pc){const auto& i=original[pc];
  if(i.bank==1003&&i.op==101){if(!flag(local,exhausted))pc=3;continue;}
  if(i.bank==1014)continue;
  if(i.bank==2006&&i.op==5){++fx.deletes;fx.visible=false;continue;}
  if(i.bank==1000){assert(i.op==4);set(local,done,true);return;}
  if(i.bank==1003){assert(i.op==1);if(flag(local,done))++pc;continue;}
  if(i.bank==2006){assert(i.op==4&&arg(i,8)==928020);++fx.creates;fx.visible=true;continue;}
  if(i.bank==2003){assert(i.op==5&&arg(i,12)==6032);++fx.hazards;continue;}
  assert(i.bank==1001&&i.op==0);memcpy(&fx.seconds,i.args.data(),4);
 }
 assert(false);
}
void incoming(Group& local,const Group& host,bool patched=true){
 if(patched)Chalice::CopyHostFlagGroup(12805,local.data(),host);
 else local=host;
 // Direct session-host story merge is a second incoming boundary.
 BbscMergeSharedProgressGroup(12805,local.data(),host.data());
}
int main(){
 for(u32 f=12805900;f<12805970;++f)
  assert(Chalice::IsLocalVisualFlag(f)==(f>=12805920&&f<=12805923));
 // Exhaustive bit preservation: exactly four initialization receipts stay local.
 for(unsigned l=0;l<256;++l)for(unsigned h=0;h<256;++h){
  Group local,host;local.fill(l);host.fill(h);auto before=local;
  incoming(local,host);
  for(u32 bit=0;bit<1000;++bit){u32 f=12805000+bit;
   assert(flag(local,f)==flag(Chalice::IsLocalVisualFlag(f)?before:host,f));}
 }
 for(int slot=0;slot<4;++slot){
  Group host{},local{};for(int j=0;j<4;++j)set(host,12805920+j,true);
  Visual fx;incoming(local,host);run(local,slot,fx);
  assert(fx.visible&&fx.creates==1&&fx.hazards==1&&fx.seconds==2);
  // Both host values must preserve the locally completed receipt.
  for(int n=0;n<2000;++n){set(host,12805920+slot,n%2);incoming(local,host);run(local,slot,fx);}
  assert(fx.creates==1&&fx.hazards==2001);
  set(host,12805942+slot*5,true);incoming(local,host);run(local,slot,fx);
  assert(!fx.visible&&fx.deletes==1&&fx.hazards==2001);
  // Already exhausted at late join: no local effect or hazard is created.
  local={};Visual spent;incoming(local,host);run(local,slot,spent);
  assert(!spent.visible&&spent.creates==0&&spent.hazards==0&&spent.deletes==1);
  // Native reset for a fresh visit: receipt0 survives incoming completion1.
  local={};set(host,12805942+slot*5,false);set(host,12805920+slot,true);
  Visual revisit;incoming(local,host);run(local,slot,revisit);assert(revisit.creates==1);
  // Frozen pre-fix copy reproduces the missing visual while keeping damage.
  local={};Visual old;incoming(local,host,false);run(local,slot,old);
  assert(!old.visible&&old.creates==0&&old.hazards==1);
 }
 // Shared-progress alone must not inject foreign initialization receipts.
 Group local{},host{};host.fill(255);BbscMergeSharedProgressGroup(12805,local.data(),host.data());
 for(u32 f=12805920;f<=12805923;++f)assert(!flag(local,f));
 for(u32 f:{12805942u,12805947u,12805952u,12805957u})assert(flag(local,f));
 // Unrelated maps still copy unchanged. Existing chalice lamp ownership remains.
 for(u32 key:{12804u,12806u,12405u}){Group g{};Chalice::CopyHostFlagGroup(key,g.data(),host);assert(g==host);}
 local={};Chalice::CopyHostFlagGroup(12907,local.data(),host);
 for(u32 f:Chalice::LampUnlockFlags){assert(!flag(local,f));assert(!flag(local,f-10));}
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-burning-corpses-') as tmp:
    cpp, exe = Path(tmp) / 'test.cpp', Path(tmp) / 'test.exe'
    cpp.write_text(code, encoding='utf8')
    cc = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    env = dict(os.environ, PATH=str(Path(cc).parent) + os.pathsep + os.environ.get('PATH', ''))
    subprocess.run([cc, '-std=c++20', '-O2', '-I' + str(ROOT / 'emulator/src'),
                    str(cpp), '-o', str(exe)], env=env, check=True)
    subprocess.run([str(exe)], env=env, check=True, timeout=30)
print('PASS original m28 slots0..3: late join, repeat, exhaustion, reset, snapshot/progress gates, old-copy negative control')
