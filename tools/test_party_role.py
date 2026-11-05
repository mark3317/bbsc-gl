"""Execute production native host choice, without game files or real profiles."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
prefix = r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <set>
using u64=uint64_t;using u32=uint32_t;using u8=uint8_t;using s32=int32_t;using s64=int64_t;
#define BBSC_MOD
#define PS4_SYSV_ABI
#define BBSC_TIMELINE(...)
std::atomic<u32> bbsc_load_generation{0},bbsc_world_load_pending{0};
std::atomic<bool> bbsc_reload_finish_pending{false};
struct {u64 ticket=0;} bbsc_pending_party_item;
unsigned hint=0;int cancelled=0,applied=0,state=0,members=1,hp=100;
bool loading=false,curtain=false,quit=false,title=false,another=false,has_bell=true,erase_ok=true,own=true;
s64 clock_ms=100;std::set<int> effects;
namespace BbscMod {unsigned PartyHostHint(){return hint;} void PartyCancel(){++cancelled;}}
u64 GetGlobalState(){return 32;}u64 GetLocalPlayerCharacter(){return 17;}
bool ReadablePointer(u64,size_t){return true;}
template<class T>T ReadValue(u64,size_t off){return off==8?T(loading):T(own);}
s64 SteadyNowMs(){return clock_ms;}
bool BbscQuitInProgress(){return quit;}bool BbscReturningToTitle(){return title;}
bool BbscCurtainActive(){return curtain;}bool BbscInAnotherWorld(){return another;}
int GetCharacterHp(u64){return hp;}int GetSessionState(){return state;}
int GetBbscSessionMemberCount(u64){return members;}
u64 BbscLocalEffectNode(int id){return effects.count(id);}
bool BbscEraseLocalEffect(int id){if(!erase_ok)return false;effects.erase(id);return true;}
bool BbscSmallBellSessionBlocked(){return state==3||state==4||state==6||state==7;}
u64 BbscCarriedInventory(){return 1;}bool BbscInventoryHas(u64,u32){return has_bell;}
constexpr int SmallResonantBellGoodsId=205,BellUseArgument=17;
bool NativeApply(u64 p,s32 goods,s32 arg){assert(p==17&&goods==205&&arg==17);++applied;effects.insert(9005);return true;}
const u64 image_base=reinterpret_cast<u64>(&NativeApply);constexpr u64 UseItemNativeApplyOffset=0;
'''
main = r'''
int main(){
 // Existing remote host at initial world load starts native small bell once.
 hint=1;TickBbscPartyRole();assert(applied==1);
 effects.clear();TickBbscPartyRole();assert(applied==1);
 // Every load/lifetime fence prevents automatic item use and cancellation.
 for(int test=0;test<12;++test){
  ++bbsc_load_generation;
  switch(test){case 0:loading=true;break;case 1:curtain=true;break;case 2:quit=true;break;
   case 3:title=true;break;case 4:another=true;break;case 5:state=3;break;
   case 6:state=4;break;case 7:state=7;break;case 8:members=0;break;
   case 9:hp=0;break;case 10:bbsc_world_load_pending=1;break;case 11:bbsc_reload_finish_pending=true;break;}
  TickBbscPartyRole();assert(applied==1&&cancelled==0);
  loading=curtain=quit=title=another=false;state=0;members=1;hp=100;
  bbsc_world_load_pending=0;bbsc_reload_finish_pending=false;
 }
 // The simultaneous loser removes its bell, cancels exactly once, waits for
 // durable release, then starts the native responder. No game-thread HTTP.
 hint=2;effects.insert(9000);TickBbscPartyRole();assert(cancelled==1&&!effects.count(9000));
 for(int i=0;i<100;++i)TickBbscPartyRole();assert(cancelled==1&&applied==1);
 clock_ms+=600;hint=1;TickBbscPartyRole();assert(applied==2&&effects.count(9005));
 effects.clear();++bbsc_load_generation;hint=0;TickBbscPartyRole();clock_ms+=1000;
 hint=1;TickBbscPartyRole();assert(applied==3); // discovery completes after load
 effects.clear();++bbsc_load_generation;hint=0;TickBbscPartyRole();clock_ms+=3100;
 TickBbscPartyRole();hint=1;TickBbscPartyRole();assert(applied==3); // no surprise late auto-ring
 // Existing manual responder/invasion searches are not replaced on a load.
 for(int effect:{9000,9005,9025,7511}){
  ++bbsc_load_generation;effects={effect};TickBbscPartyRole();assert(applied==3);
 }
 // A successful join consumes Small Bell without cancelling membership.
 effects={9005};state=4;TickBbscPartyRole();assert(effects.count(9005));
 state=6;own=false;another=true;members=2;loading=true;
 TickBbscPartyRole();assert(effects.count(9005)); // defer memory mutation through load
 loading=false;TickBbscPartyRole();assert(!effects.count(9005)&&cancelled==1&&applied==3);
 ++bbsc_load_generation;effects={9005};hp=0;TickBbscPartyRole();assert(effects.count(9005));
 hp=100;TickBbscPartyRole();assert(!effects.count(9005)); // guest respawn, no new search
 // Leave/kick/ending: old search state may be restored by native loading.
 effects={9005};state=7;TickBbscPartyRole();assert(effects.count(9005));
 state=0;own=true;another=false;members=1;++bbsc_load_generation;loading=true;hint=1;
 TickBbscPartyRole();assert(effects.count(9005));
 loading=false;erase_ok=false;TickBbscPartyRole();assert(effects.count(9005));
 erase_ok=true;TickBbscPartyRole();assert(!effects.count(9005)&&applied==3&&cancelled==1);
 ++bbsc_load_generation;clock_ms+=5000;TickBbscPartyRole();assert(applied==3); // personal travel stays solo
 effects.insert(9005);TickBbscPartyRole();assert(effects.count(9005)); // new manual ring remains usable
}
'''
with tempfile.TemporaryDirectory() as tmp:
    cpp, exe = Path(tmp)/'role.cpp', Path(tmp)/'role.exe'
    cpp.write_text(prefix+(root/'emulator/src/core/bbsc_party_role.inc').read_text()+main)
    subprocess.run([os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env = dict(os.environ, PATH='C:/msys64/clang64/bin;'+os.environ.get('PATH',''))
    subprocess.run([str(exe)],check=True,env=env)
print('Production native role choice: load, collision, release and lifetime fences PASS')
