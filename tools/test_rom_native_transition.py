"""Original EMEVD, native iterator/interpreter/Remo bank, production delegation.

Only allocated fixture memory; native managers, renderer and stage loading are
stand-ins. The original interpreter must wait for Remo and run its own tail.
"""
from pathlib import Path
import os
import struct
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/gamedata'))
from emevd import Emevd

evd=Emevd(Path(os.environ['BB_GAME'])/'event/m32_00_00_00.emevd.dcx')
original=dict(evd.events)[13201803]
assert original[42:47]==[
    (2002,7,struct.pack('<4I',32000000,0,10000,3)),
    (1001,1,struct.pack('<I',1)),
    (2003,2,struct.pack('<II',9180,0)),
    (2003,2,struct.pack('<II',70002802,1)),
    (2003,49,struct.pack('<I',2802958)),
]
elf=Path(sys.argv[1]).read_bytes()[0x4000:]
source=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
replay=source[source.index('void TickBbscCutsceneReplay() {'):]
assert replay.index('QueueBbscRomNativeTransition(packet.cutscene)')<replay.index('request(0,')
assert 'if(registers)EnableBbscRomNativeTransition(registers->rdi);' in source
production=(ROOT/'emulator/src/core/bbsc_rom_transition.inc').read_text(encoding='utf-8')
negative=os.environ.get('BBSC_ROM_OLD')=='1'

code=r'''
#define NOMINMAX
#include <windows.h>
#include <array>
#include <atomic>
#include <cassert>
#include <cstring>
#include <mutex>
#include <vector>
#include <utility>
#include "core/bbsc_world_presence.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define BBSC_MOD
#define BBSC_TIMELINE(...)
u64 image_base=0;u32 map=0x20000000;int role=6;bool allowed=true,writable=true;
s64 now=1000;std::atomic<u32> bbsc_load_generation{1};
std::mutex bbsc_world_presence_mutex;World::Presence bbsc_world_presence_local;
bool BbscIndependentTravelAllowed(){return allowed;}
u32 GetCurrentPackedMap(){return map;}int GetSessionState(){return role;}
u32 GetBbscRelayHost(){return 11;}s64 SteadyNowMs(){return now;}
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
enum class MemoryProt{CpuWrite};bool HasMemoryAccess(u64,size_t,MemoryProt){return writable;}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t o,T v){memcpy((void*)(p+o),&v,sizeof(v));}
s64 event_id=13201803;s64 BbscEventIdOf(u64){return event_id;}
void Jump(u64 off,void* to){auto* p=(u8*)(image_base+off);p[0]=0x48;p[1]=0xB8;
 u64 target=(u64)to;memcpy(p+2,&target,8);p[10]=0xFF;p[11]=0xE0;}
alignas(8) std::array<u8,0xD0> inst{};
alignas(8) std::array<u8,0x30> cond{},node{};
alignas(8) std::array<u8,0x10> ref{};
alignas(8) u8 file[]={EVD};
bool playing=false;int movies=0,warps=0,clears=0;u32 destination=0;
std::vector<std::pair<u32,u32>> flags;
void PS4_SYSV_ABI Clear(u64 tree){++clears;WriteValue<u64>(tree-0x30,0x40,0);}
void PS4_SYSV_ABI Update(u64,u64,u64){
 if(!playing && ReadValue<u64>((u64)inst.data(),0x40))WriteValue<u8>((u64)cond.data(),0x10,1);
}
void PS4_SYSV_ABI Send(u64){}
void PS4_SYSV_ABI Movie(u64,u32 id,u32,u64,u32,u32 entity,u64 mode){
 assert(id==32000000&&entity==10000&&static_cast<u32>(mode)==3);++movies;playing=true;
}
u64 PS4_SYSV_ABI Allocate(u64,u64 size,u64){assert(size==0x30);cond.fill(0);return (u64)cond.data();}
void PS4_SYSV_ABI Init(u64 c,u64,u64 p){assert(c==(u64)cond.data()&&p==(u64)inst.data());}
void PS4_SYSV_ABI Insert(u64 tree,u64,u64 c){
 node.fill(0);WriteValue<u64>((u64)node.data(),0x10,c);WriteValue<u64>(tree-0x30,0x40,(u64)node.data());
}
void PS4_SYSV_ABI Dispatch(u64 manager,u64 p){
 const u64 instruction=ReadValue<u64>(p,0xB0),f=(u64)file;
 s32 bank=ReadValue<s32>(instruction,0),cmd=ReadValue<s32>(instruction,4);
 const u64 args=f+ReadValue<u64>(f,0x78)+ReadValue<u64>(instruction,0x10);
 if(bank==2002&&cmd==7){using Bank=u8 PS4_SYSV_ABI (*)(u64,u64);((Bank)(image_base+0x17C53B0))(manager,p);}
 else if(bank==1001&&cmd==1){assert(!playing&&ReadValue<u32>(args,0)==1);WriteValue<u8>(p,0xC4,0);}
 else if(bank==2003&&cmd==2){assert(!playing);flags.emplace_back(ReadValue<u32>(args,0),ReadValue<u32>(args,4));}
 else if(bank==2003&&cmd==49){assert(!playing);++warps;destination=ReadValue<u32>(args,0);WriteValue<u8>(p,0xC4,0);}
 else assert(false);
}
''' + production + r'''
void Reset(){
 inst.fill(0);cond.fill(0);node.fill(0);ref.fill(0);++bbsc_load_generation;
 bbsc_rom_transition={};bbsc_world_presence_local.world={11,99};
 role=6;map=0x20000000;allowed=true;writable=true;event_id=13201803;
 playing=false;movies=warps=clears=0;flags.clear();now=1000;
 const u64 f=(u64)file,p=(u64)inst.data();u64 row=0;
 for(s64 k=0;k<ReadValue<s64>(f,0x10);++k){u64 r=f+ReadValue<u64>(f,0x18)+k*0x30;
  if(ReadValue<s64>(r,0)==13201803){row=r;break;}}
 assert(row);WriteValue<s32>(p,0x60,20000);WriteValue<u64>((u64)ref.data(),8,f);
 WriteValue<u64>(p,0x80,(u64)ref.data());WriteValue<u64>(p,0x88,row);
 WriteValue<u64>(p,0xA8,(u64)ref.data());WriteValue<s32>(p,0xA0,49);
 WriteValue<u64>(p,0xB0,f+ReadValue<u64>(f,0x28)+ReadValue<u64>(row,0x10)+49*0x20);
}
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image_base);
 {u8 bytes[]={ITERATOR};memcpy((void*)(image_base+0x12EF2E0),bytes,sizeof(bytes));}
 {u8 bytes[]={EVENT};memcpy((void*)(image_base+0x12ECDC0),bytes,sizeof(bytes));}
 {u8 bytes[]={BANK};memcpy((void*)(image_base+0x17C53B0),bytes,sizeof(bytes));}
 u64 canary=0;WriteValue<u64>(image_base,0x53E3BE0,(u64)&canary);
 std::array<u64,16> manager{};manager[7]=1;WriteValue<u64>(image_base,0x553B0C0,(u64)manager.data());
 WriteValue<u64>(image_base,0x553B0C8,1); // bank's cutscene-manager availability guard
 std::array<u64,16> allocator_vtable{};allocator_vtable[11]=(u64)&Allocate;
 u64 allocator=(u64)allocator_vtable.data();WriteValue<u64>(image_base,0x5540420,(u64)&allocator);
 WriteValue<u64>(image_base,0x532D580,(u64)&Init); // original Remo-condition vtable+10
 Jump(0x12EBFF0,(void*)&Clear);Jump(0x12EC380,(void*)&Update);Jump(0x12EC4A0,(void*)&Update);
 Jump(0x12EE540,(void*)&Send);Jump(0x17B93A0,(void*)&Dispatch);
 Jump(0x131C170,(void*)&Movie);Jump(0x12EC230,(void*)&Insert);
 Reset();u64 p=(u64)inst.data();assert(QueueBbscRomNativeTransition(32000000));
 EnableBbscRomNativeTransition(p);assert(!bbsc_rom_transition.pending&&clears==1);
 assert(ReadValue<s32>(p,0xA0)==42&&ReadValue<u8>(p,0x78)==0);
 using Tick=void PS4_SYSV_ABI (*)(u64,u64);auto tick=(Tick)(image_base+0x12ECDC0);
 std::array<u8,16> frame{};
 tick(p,(u64)frame.data());assert(movies==1&&playing&&warps==0&&flags.empty());
 assert(bbsc_rom_transition.delegated);assert(QueueBbscRomNativeTransition(32000000));
 EnableBbscRomNativeTransition(p);assert(ReadValue<s32>(p,0xA0)==43&&movies==1);
 for(int i=0;i<10;++i){tick(p,(u64)frame.data());assert(warps==0&&flags.empty());}
 playing=false;tick(p,(u64)frame.data());assert(warps==0); // original WaitFrames(1)
 tick(p,(u64)frame.data());assert(warps==1&&destination==2802958);
 assert((flags==std::vector<std::pair<u32,u32>>{{9180,0},{70002802,1}}));
 // Feature/role/map/scene/world fences never create an unsolicited group trip.
 for(int what=0;what<5;++what){Reset();
  if(what==0)allowed=false;if(what==1)role=3;if(what==2)map=0x18000000;
  if(what==3)bbsc_world_presence_local.world={33,99};
  assert(!QueueBbscRomNativeTransition(what==4?24000000:32000000));
 }
 for(int what=0;what<4;++what){Reset();assert(QueueBbscRomNativeTransition(32000000));
  if(what==0)++bbsc_load_generation;if(what==1)bbsc_world_presence_local.world.room=100;
  if(what==2)now+=30001;if(what==3)map=0x1C000000;
  TickBbscRomTransition();assert(!bbsc_rom_transition.pending);
 }
 Reset();assert(QueueBbscRomNativeTransition(32000000));writable=false;
 EnableBbscRomNativeTransition(p);assert(bbsc_rom_transition.pending&&ReadValue<s32>(p,0xA0)==49);
 writable=true;event_id=13200310;EnableBbscRomNativeTransition(p);assert(ReadValue<s32>(p,0xA0)==49);
 event_id=13201803;EnableBbscRomNativeTransition(p);assert(ReadValue<s32>(p,0xA0)==42);
 VirtualFree((void*)image_base,0,MEM_RELEASE);
}
'''
if negative:
    code=code.replace('Reset();u64 p=(u64)inst.data();assert(QueueBbscRomNativeTransition(32000000));',
        'Reset();u64 p=(u64)inst.data();Movie(0,32000000,0,0,0,10000,3);playing=false;assert(warps==1);')
for key,data in [('EVD' ,evd.data),('ITERATOR',elf[0x12EF2E0:0x12EF50B]),
                 ('EVENT',elf[0x12ECDC0:0x12ECFD2]),('BANK',elf[0x17C53B0:0x17C5B70])]:
    code=code.replace(key,','.join(str(b) for b in data))
with tempfile.TemporaryDirectory(prefix='bbsc-rom-native-') as tmp:
    cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe';cpp.write_text(code,encoding='utf-8')
    cxx='C:/msys64/clang64/bin/clang++.exe'
    subprocess.run([cxx,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(cxx).parent)+os.pathsep+env.get('PATH','')
    result=subprocess.run([str(exe)],env=env,timeout=15)
    if negative:
        assert result.returncode!=0,'Old standalone replay unexpectedly retained native continuation'
        print('PASS negative: old standalone movie has no native continuation')
    else:
        result.check_returncode()
        print('PASS original event/iterator/Remo bank: no warp while playing; original frame wait, flags and2802958; scoped production delegation')
