"""Execute production Rom gate over original EMEVD; no game process/save writes."""
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/gamedata'))
from emevd import Emevd

source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
start = source.index('void EnableBbscRomJumpEvent(u64 instance) {')
body = source[start:source.index('\nvoid EnableBbscKidnapEvent(', start)]
assert 'EnableBbscRomJumpEvent(registers->rdi);' in source
game = Path(os.environ['BB_GAME'])
evd = Emevd(game / 'event/m32_00_00_00.emevd.dcx')
events = dict(evd.events)
assert events[13204821][0] == (2000, 2, struct.pack('<I', 0))
# This guest completion bit is read ONLY by the music event, never boss activation.
assert {e for e, _, _, _, _ in evd.instructions_with(13204801)} == {13204803, 13204821}
assert not any(b == 2003 and c == 2 and struct.unpack_from('<I', a)[0] in
               (13204800, 13201802) for b, c, a in events[13204821])
prefix = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define BBSC_TIMELINE(...)
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t o,T v){memcpy((void*)(p+o),&v,sizeof(v));}
bool ReadablePointer(u64 p,size_t){return p>0x10000;}
enum class MemoryProt{CpuWrite};bool writable=true;
bool HasMemoryAccess(u64,size_t,MemoryProt){return writable;}
s64 event=13204821;int state=6;u32 map=0x20000000;
s64 BbscEventIdOf(u64){return event;}int GetSessionState(){return state;}
u32 GetCurrentPackedMap(){return map;}
'''
main = r'''
int main(){
 std::vector<u8> file=original;u64 f=(u64)file.data();
 alignas(8) u8 instance[0xc0]{},ref[0x10]{};u64 p=(u64)instance;
 WriteValue<u64>(p,0xa8,(u64)ref);WriteValue<u64>((u64)ref,8,f);
 u64 first=0;int count=0;
 for(int k=0;k<ReadValue<s64>(f,0x10);++k){u64 row=f+ReadValue<u64>(f,0x18)+k*0x30;
  if(ReadValue<s64>(row,0)==13204821){first=f+ReadValue<u64>(f,0x28)+ReadValue<u64>(row,0x10);count=ReadValue<s64>(row,8);}}
 assert(first&&count==10);
 auto gate=[&](){WriteValue<u64>(p,0xb0,first+0x20);EnableBbscRomJumpEvent(p);};
 // Guard malformed/unrelated event, map, inline args and unwritable memory.
 auto pristine=file;
 event=13204820;gate();assert(file==pristine);event=13204821;
 map=0x1d000000;gate();assert(file==pristine);map=0x20000000;
 WriteValue<u64>(p,0xb8,1);gate();assert(file==pristine);WriteValue<u64>(p,0xb8,0);
 writable=false;gate();assert(file==pristine);writable=true;
 for(int role:{0,3,4}){state=role;gate();assert(file==pristine);}state=6;
 // Walk the ORIGINAL local event's commands, adapting only the production gate.
 // Time advances deterministically; region membership and activation are independent.
 auto jump=[&](bool active,bool region,bool patch){
  bool condition=true,invincible=false;int fx=0,elapsed=0,entry=0;
  for(int step=0;step<count;++step){
   u64 ins=first+step*0x20;WriteValue<u64>(p,0xb0,ins);
   if(patch)EnableBbscRomJumpEvent(p);
   int bank=ReadValue<s32>(ins,0),cmd=ReadValue<s32>(ins,4);
   u64 a=f+ReadValue<u64>(f,0x78)+ReadValue<u64>(ins,0x10);
   if(bank==2000){assert(cmd==2&&ReadValue<u32>(a,0)==0);continue;}
   if(bank==3&&cmd==0){assert(ReadValue<u32>(a,4)==13204800);condition&=active;continue;}
   if(bank==1001&&cmd==1){assert(ReadValue<u64>(ins,8)==4&&ReadValue<u32>(a,0)==0);continue;}
   if(bank==3&&cmd==2){assert(ReadValue<u32>(a,4)==10000&&ReadValue<u32>(a,8)==3202800);condition&=region;continue;}
   if(bank==0){assert(cmd==0);if(!condition)break;continue;}
   if(bank==2004){assert(cmd==15&&ReadValue<u32>(a,0)==10000);
    invincible=ReadValue<u32>(a,4)!=0;if(!invincible)assert(elapsed==5);continue;}
   if(bank==2006){assert(cmd==3&&invincible&&ReadValue<u32>(a,0)==2&&ReadValue<u32>(a,4)==10000&&ReadValue<u32>(a,8)==246&&ReadValue<u32>(a,12)==932210);++fx;continue;}
   if(bank==1001){assert(cmd==0&&invincible&&fx==1&&ReadValue<float>(a,0)==5);elapsed=5;continue;}
   if(bank==2003){assert(cmd==2&&!invincible);assert(ReadValue<u32>(a,0)==13204801);++entry;continue;}
   assert(bank==1000&&cmd==4&&ReadValue<u32>(a,0)==1); // native restart
  }
  assert(!invincible);assert(entry==fx);return fx;
 };
 assert(jump(false,true,false)==0); // regression reproduced by original event
 assert(jump(false,true,true)==1); // safe before activation, no boss flag writes
 auto patched=file;gate();assert(file==patched); // idempotent
 assert(jump(false,false,true)==0); // no protection outside the original region
 assert(jump(true,false,true)==0);
 assert(jump(true,true,true)==1); // normal active encounter
 assert(jump(false,true,true)==1); // repeated jump still gets cleanup
 // Restoration handles sessions switching to host without unloading the script.
 state=3;gate();assert(file==pristine);assert(jump(false,true,true)==0);
 state=6;gate();assert(file==patched);
 map=0x1d000000;gate();assert(file==pristine);map=0x20000000;
 // New load uses new script memory and receives the same bounded patch.
 memcpy(file.data(),original.data(),original.size());gate();assert(file==patched);
 // No other original event/command or unused argument byte was touched.
 for(size_t k=0;k<file.size();++k){
  u64 pos=f+k,ins=first+0x20,a=f+ReadValue<u64>(f,0x78)+ReadValue<u64>(ins,0x10);
  if((pos>=ins&&pos<ins+16)||(pos>=a&&pos<a+4))continue;
  assert(file[k]==original[k]);
 }
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-rom-jump-') as directory:
    cpp, exe = Path(directory) / 'fixture.cpp', Path(directory) / 'fixture.exe'
    data = 'std::vector<u8> original={' + ','.join(map(str, evd.data)) + '};\n'
    cpp.write_text(prefix + body + data + main, encoding='utf8')
    compiler = 'C:/msys64/clang64/bin/clang++.exe'
    subprocess.run([compiler, '-std=c++20', str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], check=True, env=env, timeout=15)
print('PASS original guest jump regression / production gate / region / native five-second '
      'protection+SFX+cleanup / repeat / active battle / no boss writes / role restore / new load')
