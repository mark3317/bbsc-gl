"""Original second event emitter and real Windows receive/send trampolines.

Allocated fixture memory only. Native network queues are stand-ins; no live
game, save or settings writes. Usage: script.py <original analysis ELF>.
"""
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import capstone

ROOT=Path(__file__).resolve().parents[1]
data=Path(sys.argv[1]).read_bytes()
ph=struct.unpack_from('<Q',data,32)[0];size,n=struct.unpack_from('<HH',data,54)
segments=[struct.unpack_from('<II6Q',data,ph+i*size) for i in range(n)]
def read(a,n):
    s=next(s for s in segments if s[0]==1 and s[3]<=a and a+n<=s[3]+s[5])
    return data[s[2]+a-s[3]:s[2]+a-s[3]+n]
native=read(0x12EE660,0x169)
first_sender=read(0x12EE540,0x119)
receiver=read(0x12EE420,0x115)
condition=read(0x12ECE95,0xD)
assert condition==bytes.fromhex('8b 4b 48 3b 4b 4c 7f 05 b8 02 00 00 00')
assert native[:8]==bytes.fromhex('55 48 89 e5 41 57 41 56')
assert read(0x12F1744,5)==bytes.fromhex('e8 b7 7a 49 00')
assert 0x12F1749+struct.unpack('<i',read(0x12F1745,4))[0]==0x1789200
cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);cs.detail=True
ops=list(cs.disasm(native,0x12EE660))
assert not any(' + 0x78]' in i.op_str for i in ops) # no native NoNetSync test

prefix=r'''
#include <windows.h>
#include "C:/Users/markn/CLionProjects/bloodborne_pc/mods-src/BBSC/emulator/src/core/bbsc_lamp_travel_data.h"
namespace LampTravel=Core::Bloodborne::LampTravel;
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <deque>
#include <map>
#include <mutex>
#include <set>
#include <span>
#include <string>
#include <string_view>
#include <tuple>
#include <utility>
#include <vector>
#include "core/cpu_patches.h"
#include "core/bbsc_quest_event_rules.h"
#include "core/bbsc_dream_finale.h"
using Core::GuestRegisterSnapshot;
namespace Bbsc=Core::Bbsc;
namespace QuestRules=Core::Bloodborne::QuestRules;
bool independent=false;bool BbscIndependentTravelAllowed(){return independent;}
u64 image_base=0;bool own=true,timeline=true;int state=3,logs=0,sends=0;
std::atomic<u32> bbsc_load_generation{1};
namespace BbscMod {u64 EbootAddress(){return image_base;}void LogPlain(const char* s){puts(s);}}
#define BBSC_TIMELINE(...) (++logs)
bool BbscTimelineEnabled(){return timeline;}
s64 SteadyNowMs(){return 1000;}
bool BbscOwnNpcQuestsEnabled(){return own;}
s32 GetSessionState(){return state;}
u32 GetCurrentPackedMap(){return 0x18010000;}
bool IsBbscLocalQuestEvent(s64 e){return std::binary_search(QuestRules::LocalEvents.begin(),QuestRules::LocalEvents.end(),e);}
bool IsBbscKidnapEvent(s64 e){return e==9421||e==9422||e==12400780||e==12700500;}
bool IsBbscPersonalMapEvent(s64 e){return IsBbscLocalQuestEvent(e);}
bool BbscEventFlag(u32){return false;}
s64 BbscEventIdOf(u64 p){return ReadValue<u32>(p,0x28);}
bool ReadablePointer(u64 p,size_t){return p>0x10000;}
template<class T>T ReadValue(u64 p,size_t off){T v;memcpy(&v,(void*)(p+off),sizeof(v));return v;}
template<class T>void put(auto& a,size_t off,T v){memcpy(a.data()+off,&v,sizeof(v));}
void Jump(u64 at,u64 target){const u8 j[]={0xff,0x25,0,0,0,0};memcpy((void*)at,j,6);memcpy((void*)(at+6),&target,8);}
bool PS4_SYSV_ABI Self(u64){return false;}
int PS4_SYSV_ABI Send(u64,u64,u32 channel,const u8* p,u32 n){assert(channel==0x31&&(n==0x18||n==0x1c));assert(ReadValue<u16>((u64)p,2)==(n==0x18?1:2));++sends;return 1;}
std::deque<std::vector<u8>> queued;int reads=0;
s32 PS4_SYSV_ABI Receive(u64,u64,u32,u8* p,u32 cap){++reads;if(queued.empty())return 0;
 auto v=queued.front();queued.pop_front();assert(v.size()<=cap);memcpy(p,v.data(),v.size());return v.size();}
std::vector<u8> packet(u32 event,u16 kind){std::vector<u8> b(kind==1?0x18:0x1c);put(b,2,kind);put(b,4,u32(kind==1?8:12));put(b,8,event);return b;}
'''
# Keep the logging helpers compiled too. The forward declaration above needs
# ReadValue first, just as the production translation unit provides it.
prefix=prefix.replace('s64 BbscEventIdOf(u64 p){return ReadValue<u32>(p,0x28);}\n','')
prefix+='s64 BbscEventIdOf(u64 p){return ReadValue<u32>(p,0x28);}\n'
source=(ROOT/'emulator/src/core/bbsc_personal_events.inc').read_text(encoding='utf-8')
main='int main(){\nimage_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(image_base);\n'
main+='const u8 original[]={'+','.join(map(str,native))+'};memcpy((void*)(image_base+0x12EE660),original,sizeof(original));\n'
main+='const u8 original_receiver[]={'+','.join(map(str,receiver))+'};memcpy((void*)(image_base+0x12EE420),original_receiver,sizeof(original_receiver));\n'
main+='const u8 first_sender[]={'+','.join(map(str,first_sender))+'};memcpy((void*)(image_base+0x12EE540),first_sender,sizeof(first_sender));\n'
main+='const u8 original_condition[]={'+','.join(map(str,condition))+'};memcpy((void*)(image_base+0x12ECE95),original_condition,sizeof(original_condition));\n'
main+='*reinterpret_cast<u8*>(image_base+0x12ECEA2)=0xc3;\n'
# Three used globals: stack guard indirection, matching manager, native network.
targets=[]
for i in ops:
    for op in i.operands:
        if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
            targets.append(i.address+i.size+op.mem.disp)
guard=targets[0]
main+=f'*reinterpret_cast<u64*>(image_base+{guard})=image_base+0x1000;\n'
main+=r'''
*reinterpret_cast<u64*>(image_base+0x5540290)=image_base+0x3000;
*reinterpret_cast<u64*>(image_base+0x553D6D0)=image_base+0x2000;
*reinterpret_cast<u64*>(image_base+0x3000+0xF8)=image_base+0x4000;
*reinterpret_cast<u64*>(image_base+0x3000+0x100)=image_base+0x4020;
Jump(image_base+0xCA1670,(u64)&Self);Jump(image_base+0x17894E0,(u64)&Send);
std::array<u8,0xC0> instance{};u32 bits=0;put(instance,0x20,(u64)&bits);
put(instance,0x28,u32(12410760));put(instance,0x60,u32(10001));
auto unchanged=instance;
using Emit=void PS4_SYSV_ABI (*)(u64);auto emit=(Emit)(image_base+0x12EE660);
// The installed previous fix set event+78=0. COMPLETE original emitter STILL
// broadcasts continuation: regression reproduces the uncovered native path.
assert(instance[0x78]==0);emit((u64)instance.data());assert(sends==1&&instance==unchanged);
assert(Core::InstallGuestCodeHook((void*)(image_base+0x12EE660),{original,8},2,BbscPersonalEventSendHook,&bbsc_personal_event_send_skip));
for(s32 role:{3,4,6}){state=role;emit((u64)instance.data());assert(sends==1&&instance==unchanged);}
state=0;emit((u64)instance.data());assert(sends==2);state=3;
own=false;emit((u64)instance.data());assert(sends==3);own=true;
put(instance,0x28,u32(12410100));emit((u64)instance.data());assert(sends==4); // shared door
auto emit_first=(Emit)(image_base+0x12EE540);
put(instance,0x28,u32(12410760));instance[0x78]=1;
emit_first((u64)instance.data());assert(sends==5); // native reset can restore +78
assert(Core::InstallGuestCodeHook((void*)(image_base+0x12EE540),{first_sender,8},1,BbscPersonalEventSendHook,&bbsc_personal_event_send_skip));
emit_first((u64)instance.data());assert(sends==5);instance[0x78]=0;
// COMPLETE original receiver ignores event+78 and overwrites the local
// pending step/condition bank even though this is a personal local event.
using Apply=void PS4_SYSV_ABI (*)(u64,u64,u16,const u8*,u32);
auto apply=(Apply)(image_base+0x12EE420);
auto foreign=packet(12410760,2);put(foreign,0x10,u32(10002));put(foreign,0x14,u32(8));put(foreign,0x18,u32(0x1234));
put(instance,0x28,u32(12410760));put(instance,0x48,u32(7));put(instance,0x4c,u32(0));bits=0;
auto local=instance;assert(instance[0x78]==0);
apply((u64)instance.data(),22,2,foreign.data()+0x10,12);
assert(ReadValue<u32>((u64)instance.data(),0x4c)==8&&bits==0x1234);
// Original tick conditional override: native FALSE local conditions become
// mode2 (run the command) when the remote pending step covers this step.
const u8 decide[]={0x53,0x48,0x89,0xfb,0x31,0xc0,0xe8,0,0,0,0,0x5b,0xc3};
u64 dec=image_base+0x20000;memcpy((void*)dec,decide,sizeof(decide));
*reinterpret_cast<s32*>(dec+7)=s32(image_base+0x12ECE95-(dec+11));
using Decide=u32 PS4_SYSV_ABI (*)(u64);auto decision=(Decide)dec;
assert(decision((u64)instance.data())==2);instance=local;bits=0;
assert(decision((u64)instance.data())==0);
// A minimal native CALL frame at the REAL receiver callsite, followed by RET.
const u8 wrapper[]={0x48,0x83,0xec,8,0xe8,0xb7,0x7a,0x49,0,0x48,0x83,0xc4,8,0xc3};
memcpy((void*)(image_base+0x12F1740),wrapper,sizeof(wrapper));Jump(image_base+0x1789200,(u64)&Receive);
using Read=s32 PS4_SYSV_ABI (*)(u64,u64,u32,u8*,u32);auto run=(Read)(image_base+0x12F1740);
std::array<u8,256> output{};queued.push_back(packet(12410760,1));
assert(run(11,22,0x31,output.data(),output.size())==0x18); // old receiver passes a personal PC
assert(Core::InstallGuestCodeHook((void*)(image_base+0x12F1744),{wrapper+4,5},0,BbscPersonalEventReceiveHook,&bbsc_personal_event_receive_skip,true));
queued.push_back(foreign);
assert(run(11,22,0x31,output.data(),output.size())==0);
assert(instance==local&&bits==0&&decision((u64)instance.data())==0);
for(u16 kind:{1,2}){
 queued.push_back(packet(12410760,kind));auto shared=packet(12410100,kind);queued.push_back(shared);
 assert(run(11,22,0x31,output.data(),output.size())==(s32)shared.size());
 assert(std::equal(shared.begin(),shared.end(),output.begin()));
}
for(s64 e:QuestRules::LocalEvents){queued.push_back(packet((u32)e,2));assert(run(11,22,0x31,output.data(),output.size())==0);}
for(bool enabled:{false,true}){own=enabled;state=enabled?0:3;
 queued.push_back(packet(12410760,2));assert(run(11,22,0x31,output.data(),output.size())==0x1c);}
state=3;own=true;queued.push_back(packet(12410760,2));assert(run(11,22,0x30,output.data(),output.size())==0x1c);
auto bad=packet(12410760,1);bad[4]=12;queued.push_back(bad);assert(run(11,22,0x31,output.data(),output.size())==0x18);
for(int i=0;i<9;++i)queued.push_back(packet(12410760,2));int before=reads;
assert(run(11,22,0x31,output.data(),output.size())==0&&reads==before+8&&queued.size()==1);
assert(run(11,22,0x31,output.data(),output.size())==0&&queued.empty());
// Travel event continuations must be local for BOTH roles and independent
// of the personal-NPC switch. Execute both complete original native senders.
for(int role:{3,6})for(bool npc:{false,true}){
 state=role;own=npc;independent=true;
 for(u32 event:{7100u,12907010u,7200u,12107000u,12107100u,12107200u,12907020u,13201803u,13200310u,13200311u,12800430u,12800431u,12405263u,12200131u,12407040u,12507020u,12607020u,9421u,9422u,12400780u,12700500u}){
  put(instance,0x28,event);instance[0x78]=1;
  const int previous=sends;emit((u64)instance.data());emit_first((u64)instance.data());
  assert(sends==previous);
  for(u16 kind:{1,2}){queued.push_back(packet(event,kind));assert(run(11,22,0x31,output.data(),output.size())==0);}
 }
 // Elevator unlocks remain shared in BOTH original emitter schemas. Native
 // pending remote steps must also release a locally false condition.
 for(u32 event:{12200121u,12410330u,12700137u,12700147u,12800607u,
                13300111u,13501105u,13501115u,13501125u,13601105u}){
  put(instance,0x28,event);instance[0x78]=1;
  const int previous=sends;emit((u64)instance.data());emit_first((u64)instance.data());
  assert(sends==previous+2);
  for(u16 kind:{1,2}){auto shared=packet(event,kind);queued.push_back(shared);
   assert(run(11,22,0x31,output.data(),output.size())==(s32)shared.size());
   assert(std::equal(shared.begin(),shared.end(),output.begin()));}
  put(instance,0x48,u32(5));put(instance,0x4c,u32(6));
  assert(decision((u64)instance.data())==2);
 }
 // Personal events still honor their own switch, and shared world events pass.
 queued.push_back(packet(12410760,2));
 assert(run(11,22,0x31,output.data(),output.size())==(npc?0:0x1c));
 queued.push_back(packet(12410100,2));assert(run(11,22,0x31,output.data(),output.size())==0x1c);
}
independent=false;own=true;state=3;
for(u32 event:{7100u,12907010u,7200u,12107000u,12107100u,12107200u,12907020u,13201803u,12401803u,13200310u,13200311u,12800430u,12800431u,12405263u,12200131u}){
 put(instance,0x28,event);instance[0x78]=1;const int previous=sends;
 emit((u64)instance.data());assert(sends==previous+1);
 queued.push_back(packet(event,2));assert(run(11,22,0x31,output.data(),output.size())==0x1c);
}
for(bool features:{false,true}){independent=features;own=features;
for(int role:{3,4,6})for(u32 rom:{13204820u,13204821u,13204832u,13204833u}){state=role;put(instance,0x28,rom);instance[0x78]=1;
 const int previous=sends;emit((u64)instance.data());emit_first((u64)instance.data());assert(sends==previous);
 put(instance,0x48,u32(5));put(instance,0x4c,u32(0));bits=0;
 const auto waiting=instance;
 for(u16 kind:{1,2}){auto remote=packet(rom,kind);
  if(kind==2){put(remote,0x10,u32(10002));put(remote,0x14,u32(6));put(remote,0x18,u32(0x1234));}
  queued.push_back(remote);assert(run(11,22,0x31,output.data(),output.size())==0);
  assert(instance==waiting&&bits==0&&decision((u64)instance.data())==0);
 }
}
}
VirtualFree((void*)image_base,0,MEM_RELEASE);
puts("PASS original timed continuation bypass reproduced; native send/receive trampolines, both schemas, all personal events, shared doors/feature-off/malformed/bounded drain");
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-personal-event-transport-') as temporary:
    folder=Path(temporary);cpp,exe=folder/'fixture.cpp',folder/'fixture.exe'
    cpp.write_text(prefix+source+main,encoding='utf-8')
    compiler=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler,'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
        '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),
        str(cpp),str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],check=True,env=env,timeout=15)
