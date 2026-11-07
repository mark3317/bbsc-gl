"""Production Rom gate with the original EMEVD, scheduler and iterator."""
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
elf = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT.parents[1] / 'out/exit-study.elf').read_bytes()[0x4000:]
assert events[13204821][0] == (2000, 2, struct.pack('<I', 0))
# This guest completion bit is read ONLY by the music event, never boss activation.
assert {e for e, _, _, _, _ in evd.instructions_with(13204801)} == {13204803, 13204821}
assert not any(b == 2003 and c == 2 and struct.unpack_from('<I', a)[0] in
               (13204800, 13201802) for b, c, a in events[13204821])
prefix = r'''
#include <cassert>
#include <windows.h>
#include <array>
#include <cstdint>
#include <cstring>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define BBSC_TIMELINE(...)
#define PS4_SYSV_ABI __attribute__((sysv_abi))
u64 image_base=0;
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
alignas(8) std::array<u8,0x20> group{},flag{},region{},timer{};
int clears=0,fx=0;bool inside=false,active=false,elapsed=false,protected_now=false;
void PS4_SYSV_ABI Clear(u64 tree){++clears;WriteValue<u64>(tree-0x30,0x40,0);group.fill(0);WriteValue<u64>((u64)flag.data(),8,0);}
void PS4_SYSV_ABI Update(u64,u64,u64){
 WriteValue<u8>((u64)flag.data(),0x10,active);
 WriteValue<u8>((u64)region.data(),0x10,inside);
 WriteValue<u8>((u64)timer.data(),0x10,elapsed);
}
void PS4_SYSV_ABI Send(u64){}
void PS4_SYSV_ABI Dispatch(u64,u64 p){
 const u64 f=ReadValue<u64>(ReadValue<u64>(p,0xA8),8),ins=ReadValue<u64>(p,0xB0);
 const u64 args=f+ReadValue<u64>(f,0x78)+ReadValue<u64>(ins,0x10);
 const s32 bank=ReadValue<s32>(ins,0),op=ReadValue<s32>(ins,4);
 auto wait=[&](u64 first){WriteValue<u64>((u64)group.data(),0x10,first);WriteValue<u64>(p,0x40,(u64)group.data());};
 if(bank==2000){assert(op==2);WriteValue<u8>(p,0x78,0);}
 else if(bank==3&&op==0){assert(ReadValue<u32>(args,4)==13204800);WriteValue<u64>((u64)group.data(),0x10,(u64)flag.data());}
 else if(bank==3&&op==2){assert(ReadValue<u32>(args,8)==3202800);
  if(ReadValue<u64>((u64)group.data(),0x10))WriteValue<u64>((u64)flag.data(),8,(u64)region.data());
  else WriteValue<u64>((u64)group.data(),0x10,(u64)region.data());
 }
 else if(bank==0){assert(op==0);wait(ReadValue<u64>((u64)group.data(),0x10));WriteValue<u8>(p,0xC4,0);}
 else if(bank==2004){assert(op==15&&ReadValue<u32>(args,0)==10000);protected_now=ReadValue<u8>(args,4)!=0;}
 else if(bank==2006){assert(op==3&&protected_now&&ReadValue<u32>(args,12)==932210);++fx;}
 else if(bank==1001&&op==1){assert(ReadValue<u32>(args,0)==0);}
 else if(bank==1001&&op==0){assert(ReadValue<float>(args,0)==5);wait((u64)timer.data());WriteValue<u8>(p,0xC4,0);}
 else if(bank==2003){assert(op==2&&!protected_now&&ReadValue<u32>(args,0)==13204801);}
 else {assert(bank==1000&&op==4);WriteValue<s32>(p,0xC0,-9);WriteValue<u8>(p,0xC4,0);}
}
void Jump(u64 offset,u64 target){const u8 j[]={0xff,0x25,0,0,0,0};memcpy((void*)(image_base+offset),j,6);memcpy((void*)(image_base+offset+6),&target,8);}
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(image_base);
 const u8 iterator[]={ITERATOR},scheduler[]={SCHEDULER};
 memcpy((void*)(image_base+0x12EF2E0),iterator,sizeof(iterator));
 memcpy((void*)(image_base+0x12ECDC0),scheduler,sizeof(scheduler));
 u64 canary=0;WriteValue<u64>(image_base,0x53E3BE0,(u64)&canary);
 std::array<u64,16> manager{};manager[7]=1;WriteValue<u64>(image_base,0x553B0C0,(u64)manager.data());
 Jump(0x12EBFF0,(u64)&Clear);Jump(0x12EC380,(u64)&Update);Jump(0x12EC4A0,(u64)&Update);
 Jump(0x12EE540,(u64)&Send);Jump(0x17B93A0,(u64)&Dispatch);
 std::vector<u8> file=original;u64 f=(u64)file.data();
 alignas(8) u8 instance[0xd0]{},ref[0x10]{};u64 p=(u64)instance;
 WriteValue<u64>(p,0xa8,(u64)ref);WriteValue<u64>((u64)ref,8,f);
 u64 first=0,row=0;int count=0;
 for(int k=0;k<ReadValue<s64>(f,0x10);++k){row=f+ReadValue<u64>(f,0x18)+k*0x30;
  if(ReadValue<s64>(row,0)==13204821){first=f+ReadValue<u64>(f,0x28)+ReadValue<u64>(row,0x10);count=ReadValue<s64>(row,8);break;}}
 assert(first&&count==10);
 auto reset=[&](){memset(instance,0,sizeof(instance));WriteValue<u64>(p,0x80,(u64)ref);
  WriteValue<u64>(p,0x88,row);WriteValue<u64>(p,0xa8,(u64)ref);WriteValue<u64>(p,0xb0,first);WriteValue<s32>(p,0xc0,1);
  WriteValue<u8>(p,0xc4,1);WriteValue<s32>(p,0x4c,-1);
  group.fill(0);flag.fill(0);region.fill(0);timer.fill(0);fx=clears=0;inside=active=elapsed=protected_now=false;};
 reset();
 auto gate=[&](){EnableBbscRomJumpEvent(p);};
 std::array<u8,16> frame{};
 auto tick=[&](bool patch=true){if(patch)gate();using Tick=void PS4_SYSV_ABI (*)(u64,u64);
  reinterpret_cast<Tick>(image_base+0x12ECDC0)(p,(u64)frame.data());};
 // One native update enters at command 0 and installs both conditions.
 // A hook that matches only the PC of command 1 misses it entirely.
 tick(false);assert(ReadValue<s32>(p,0xA0)==4&&ReadValue<u64>((u64)group.data(),0x10)==(u64)flag.data());
 inside=true;tick(false);assert(fx==0&&!protected_now);
 tick();assert(ReadValue<u64>((u64)group.data(),0x10)==(u64)region.data());
 tick();assert(fx==1&&protected_now);tick();assert(protected_now);
 elapsed=true;tick();assert(!protected_now);
 file=original;reset();state=6;tick();
 assert(ReadValue<s32>(p,0xA0)==4&&ReadValue<u64>((u64)group.data(),0x10)==(u64)region.data());
 tick();assert(fx==0&&!protected_now);
 // Losing guest role at an active region wait restores the original AND group.
 state=3;inside=true;tick();tick();assert(fx==0&&!protected_now);
 active=true;tick();assert(fx==1&&protected_now);elapsed=true;tick();assert(!protected_now);
 file=original;reset();state=6;

 for(s64 e:{13204820,13204832,13204833})for(int role:{0,3,6})for(u32 area:{0x20000000u,0x1d000000u}){
  event=e;state=role;map=area;WriteValue<u8>(p,0x78,1);gate();
  assert(ReadValue<u8>(p,0x78)==(!(area==0x20000000&&(role==3||role==6))));
  assert(file==original);
 }
 event=13204821;state=6;map=0x20000000;
 // Guard malformed/unrelated event, map, parameterized row and unwritable memory.
 auto pristine=file;
 event=13204820;gate();assert(file==pristine);event=13204821;
 map=0x1d000000;gate();assert(file==pristine);map=0x20000000;
 WriteValue<u64>(row,0x18,1);gate();assert(ReadValue<s32>(first+0x20,0)==3);WriteValue<u64>(row,0x18,0);assert(file==pristine);
 writable=false;gate();assert(file==pristine);writable=true;
 for(int role:{0,3,4}){state=role;gate();assert(file==pristine);}state=6;
 // Walk the ORIGINAL local event's commands, adapting only the production gate.
 // Time advances deterministically; region membership and activation are independent.
 auto jump=[&](bool active,bool region,bool patch){
  reset();if(patch)gate();
  bool condition=true,invincible=false;int fx=0,elapsed=0,entry=0;
  for(int step=0;step<count;++step){
   u64 ins=first+step*0x20;WriteValue<u64>(p,0xb0,ins);
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
 reset();state=3;gate();assert(file==pristine);assert(jump(false,true,true)==0);
 reset();state=6;gate();assert(file==patched);
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
for marker, start, end in [('ITERATOR', 0x12EF2E0, 0x12EF50B), ('SCHEDULER', 0x12ECDC0, 0x12ECFD2)]:
    main = main.replace(marker, ','.join(map(str, elf[start:end])))
with tempfile.TemporaryDirectory(prefix='bbsc-rom-jump-') as directory:
    cpp, exe = Path(directory) / 'fixture.cpp', Path(directory) / 'fixture.exe'
    data = 'std::vector<u8> original={' + ','.join(map(str, evd.data)) + '};\n'
    cpp.write_text(prefix + body + data + main, encoding='utf8')
    compiler = 'C:/msys64/clang64/bin/clang++.exe'
    subprocess.run([compiler, '-std=c++20', str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], check=True, env=env, timeout=15)
print('PASS original scheduler/iterator: first update and already compiled wait / local region / '
      'five-second protection+SFX+cleanup / repeat / active battle / no boss writes / role restore / new load')
