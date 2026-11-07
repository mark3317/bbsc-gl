"""Execute production event lookup/authority/pass against the original door scripts."""
from pathlib import Path
import os
import struct
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
sys.path.insert(0, str(root/'tools/gamedata'))
from emevd import Emevd

game = Path(os.environ['BB_GAME'])
evd = Emevd(game/'event/m32_00_00_00.emevd.dcx')
for event, point, flag in [(13200310, 2602959, 13200124), (13200311, 3302959, 13200123)]:
    assert dict(evd.events)[event] == [
        (5, 2, struct.pack('<II', 0, flag)),
        (2006, 3, struct.pack('<IIII', 1, 3202001 if event == 13200310 else 3202000, 0xffffffff, 932201)),
        (1001, 0, struct.pack('<f', 6)),
        (2003, 49, struct.pack('<I', point)),
    ]

def function(signature):
    start = source.index(signature + ' {')
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

code = r'''
#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <cassert>
#include <initializer_list>
#include <algorithm>
#include <limits>
#include <map>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI
#define BBSC_PERF_SCOPE(...)
#define BBSC_PERF_NESTED(...)
enum class MemoryProt {CpuRead};
bool ReadablePointer(u64 p,size_t){return p!=0;}
bool HasMemoryAccess(u64 p,size_t,MemoryProt){return p!=0;}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof v);return v;}
template<class T>void WriteValue(u64 p,size_t o,T v){memcpy((void*)(p+o),&v,sizeof v);}
u32 map=0x20000000;int state=0;u32 GetCurrentPackedMap(){return map;}int GetSessionState(){return state;}
struct GuestRegisterSnapshot{u64 rdi=0,rax=0,r12=0;};
std::atomic<u32> bbsc_load_generation{1};
std::array<u64,2> bbsc_local_exit_action_load{};
s64 BbscEventIdOf(u64);
u8 bbsc_transition_event_skip=0;bool bbsc_npc_pass_due=false,bbsc_npc_own_active=false;
int other_passes=0;
void EnableBbscScriptedPickupEvent(u64){++other_passes;}
void HideBbscNativeKitGift(u64){}
struct BbscQuestRange;
void LocalizeBbscQuestEvent(u64,const BbscQuestRange*){}
void RevertBbscNpcOwnFlags(){}
bool GuardBbscSharedFinaleEvent(u64){return false;}
bool GuardBbscWorldBootstrap(u64){return false;}
bool BbscIndependentTravelAllowed(){return true;}
bool BbscIndependentActive(){return true;}
void EnableBbscNativeTravelEvent(u64 p){if(BbscEventIdOf(p)==13200310 || BbscEventIdOf(p)==13200311)WriteValue<u8>(p,0x78,0);}
void EnableBbscKidnapEvent(u64){}
void EnableBbscRomNativeTransition(u64){}
void EnableBbscRomJumpEvent(u64){}
bool BbscGuestInHostWorld(){return false;}
bool IsBbscPersonalMapEvent(s64){return false;}
bool IsBbscChaliceBossRewardEvent(s64){return false;}
namespace Chalice{bool IsMap(u32){return false;}}
''' + source[source.index('struct BbscQuestRange {'):source.index('void LocalizeBbscQuestEvent(u64 instance, const BbscQuestRange* range) {', source.index('struct BbscQuestRange {'))] + function('s64 BbscEventIdOf(u64 instance)') + function('void PS4_SYSV_ABI BbscLocalTransitionActionHook(u64, const GuestRegisterSnapshot* registers)') + function('bool GuardBbscLocalTransitionTrigger(u64 instance)') + '\n' + '\n' + function(
    'void PS4_SYSV_ABI BbscNpcPassHook(u64 /*tag*/, const GuestRegisterSnapshot* registers)') + r'''
int main(){
 alignas(8) u8 inst[0xC0]{},ref[0x10]{};
 // Original decompressed EMEVD with its actual directory and all instruction ranges.
 alignas(8) u8 file[]={EVD};
 u64 p=(u64)inst,f=(u64)file;
 WriteValue<u64>(p,0xA8,(u64)ref);WriteValue<u64>((u64)ref,8,f);
 GuestRegisterSnapshot regs{p};
 auto seek=[&](s64 id,int step){
  u64 rows=f+ReadValue<u64>(f,0x18);
  for(s64 k=0;k<ReadValue<s64>(f,0x10);++k){u64 row=rows+k*0x30;
   if(ReadValue<s64>(row,0)==id){WriteValue<u64>(p,0xB0,f+ReadValue<u64>(f,0x28)+ReadValue<u64>(row,0x10)+step*0x20);return;}}
  assert(false);
 };
 for(s64 id:{13200310LL,13200311LL})for(int role=0;role<=8;++role){
  state=role;map=0x20000000;++bbsc_load_generation;
  if(role==3 || role==6){
   seek(id,0);BbscNpcPassHook(0,&regs);assert(bbsc_transition_event_skip);
   GuestRegisterSnapshot action{};action.r12=id==13200311?3200000:3200001;
   BbscLocalTransitionActionHook(0,&action);BbscNpcPassHook(0,&regs);assert(bbsc_transition_event_skip);
   action.rax=1;action.r12=id==13200311?3200001:3200000;
   BbscLocalTransitionActionHook(0,&action);BbscNpcPassHook(0,&regs);assert(bbsc_transition_event_skip);
   action.r12=id==13200311?3200000:3200001;BbscLocalTransitionActionHook(0,&action);
  }
  // Initial wait, activation, SFX, delay and warp: no remote stage can bypass authority.
  for(int step=0;step<4;++step){seek(id,step);inst[0x78]=1;other_passes=0;
   BbscNpcPassHook(0,&regs);
   assert(inst[0x78]==0);assert(!bbsc_transition_event_skip);
   assert(other_passes==0); // unrelated pickup work is no longer dispatched
  }
 }
 state=6;seek(13201800,0);inst[0x78]=1;BbscNpcPassHook(0,&regs);
 assert(!bbsc_transition_event_skip&&inst[0x78]==1); // boss event untouched
 seek(13200310,0);map=0x21000000;BbscNpcPassHook(0,&regs);assert(!bbsc_transition_event_skip);

 bbsc_transition_event_skip=1;BbscNpcPassHook(0,nullptr);assert(!bbsc_transition_event_skip);
}
'''
code = code.replace('EVD', ','.join(str(v) for v in evd.data))
code = '#include "'+(root/'emulator/src/core/bbsc_event_steps.h').as_posix()+'"\nnamespace EventSteps=Core::Bloodborne::EventSteps;\n'+code
install = function('void InstallBbscEventPassHook()')
assert '&bbsc_transition_event_skip' in install and 'BbscNpcPassHook' in install
assert source.count('image_base + 0x012ECDC0') == 1
assert source.index('InstallBbscEventPassHook();') < source.index('InstallBbscDreamHooks();')
with tempfile.TemporaryDirectory(prefix='bbsc-door-authority-') as tmp:
    cpp, exe = Path(tmp)/'test.cpp', Path(tmp)/'test.exe'
    cpp.write_text(code, encoding='utf-8')
    cxx = 'C:/msys64/clang64/bin/clang++.exe'
    subprocess.run([cxx, '-std=c++20', str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(cxx).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], check=True, env=env)
print('PASS: original two door chains; production lookup/pass; all roles/stages; no net stream; guest events run; local accepted action only/wrong exit/stale load; unrelated/null; single option-independent hook')
