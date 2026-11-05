"""Execute the real pre-event world barrier and native peer readiness.

Fixture memory only: no game process, save or UI input.
"""
from pathlib import Path
import os, shutil, subprocess, tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT/'emulator/src/core/bbsc_world_state.inc').read_text(encoding='utf-8')

def function(signature):
    a=SOURCE.index(signature+' {'); p=SOURCE.index('{',a)+1; depth=1
    while depth:
        depth+=(SOURCE[p]=='{')-(SOURCE[p]=='}'); p+=1
    return SOURCE[a:p]+'\n'

PREFIX=r'''
#include <atomic>
#include <cassert>
#include <mutex>
#include <set>
#include "core/bbsc_world_control.h"
#include "core/bbsc_world_altars.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define BBSC_TIMELINE(...)
#define PS4_SYSV_ABI
bool active=true;u32 self=11,map=0x18010000;int native_state=4,sent=0,applied=0;
namespace BbscMod {u32 RegisterOwnId(){return self;}}
std::mutex bbsc_world_presence_mutex;World::Presence bbsc_world_presence_local;
World::OwnerBook bbsc_independent_owners;
std::atomic<u64> bbsc_world_native_load{1};
constexpr u32 BbscDreamStateMap=0x15000000;
struct BbscWorldAltar{World::AltarEntry entry;Chalice::Mount mount;};
std::array<BbscWorldAltar,7> bbsc_world_altars;
std::optional<World::Scope> bbsc_world_requested_scope;
struct BbscWorldState{u64 epoch=0,sequence=0,present=0;bool flags_ready=false;};
std::map<World::Scope,BbscWorldState> bbsc_independent_states;
u64 bbsc_world_state_sequence=0;
bool intro_live=false,door_live=false;
bool ReadablePointer(u64 p,size_t){return p!=0;}
bool BbscIndependentActive(){return active;}bool BbscIndependentTravelAllowed(){return active;}
u32 GetCurrentPackedMap(){return map;}int GetSessionState(){return 3;}
s64 SteadyNowMs(){return 10000;}
std::vector<u64> GetMultiPlayerInsTasks(){return {100};}
u32 GetBbscRelayHost(){return 22;}u32 BbscWorldPeer(u64){return 22;}
template<class T>T ReadValue(u64,size_t off){return off==0xE8?T(1):off==0x50||off==0x54?T(native_state):T(0);}
void BbscWorldSend(const World::Control&){++sent;}
BbscWorldState BbscWorldCaptureFlags(const World::Scope&){return {0,0,1,true};}
void BbscWorldApplyFlags(const World::Scope&,const BbscWorldState&){++applied;intro_live=true;door_live=true;}
void ApplyBbscHostDreamState(const char*){}
'''
MAIN=r'''
int main(){
 World::Presence p;p.world={11,99};p.map=map;p.phase=World::Phase::Playing;p.visit=1;p.sequence=1;
 bbsc_world_presence_local=p;const auto scope=World::ScopeOf(p);
 bbsc_independent_owners.Bind(p.world);
 World::Control lease;lease.kind=World::ControlKind::Owner;lease.scope=scope;lease.owner=22;lease.epoch=9;
 assert(bbsc_independent_owners.Take(11,lease,100));
 bbsc_independent_states[scope]={9,7,1,true};
 assert(GuardBbscWorldBootstrap(1)); // native FirstSync is not finished
 assert(!intro_live&&!door_live&&applied==0);
 native_state=6;assert(!GuardBbscWorldBootstrap(1));assert(intro_live&&door_live&&applied==1);
 assert(BbscWorldSceneReady());
 door_live=false;assert(!GuardBbscWorldBootstrap(1)&&applied==1&&!door_live); // do not rewind running events
 ++bbsc_world_native_load;bbsc_independent_states.erase(scope);
 assert(GuardBbscWorldBootstrap(1)&&sent==1&&applied==1);
 assert(!bbsc_independent_states.contains(scope)); // a late host cannot seed over an existing owner
 bbsc_independent_states[scope]={8,99,1,true};assert(!BbscWorldFlagsReady(scope));
 bbsc_independent_states[scope]={9,8,1,true};assert(!GuardBbscWorldBootstrap(1)&&applied==2);
 // Completed layout maps use the same native m29_00 event namespace as preflight.
 map=0x1d0a5a00;++bbsc_world_native_load;
 auto& altar=bbsc_world_altars[1];altar.entry.occupied=true;altar.entry.ritual=18;altar.mount.key={55,66,88,0};
 World::Scope cup{p.world,0x1d000000,altar.mount.key,18};bbsc_world_requested_scope=cup;
 bbsc_independent_states[cup]={0,1,0,true};assert(BbscWorldFlagsReady(cup));
 assert(!GuardBbscWorldBootstrap(1));
 p.map=map;p.dungeon=cup.dungeon;p.ritual=cup.ritual;bbsc_world_presence_local=p;
 assert(World::ScopeOf(p)==cup&&BbscWorldSceneReady());
 active=false;assert(!GuardBbscWorldBootstrap(1));
}
'''

def main():
    signatures=['bool BbscWorldFlagsReady(const World::Scope& scope)',
                'void BbscWorldEnsureSeed(const World::Scope& scope)',
                'bool BbscWorldSceneReady()',
                'bool BbscWorldNativePeerReady(u32 owner)',
                'bool GuardBbscWorldBootstrap(u64 instance)']
    globals_='World::Scope bbsc_world_bootstrap_scope{};u64 bbsc_world_bootstrap_load=~u64{0};\n'
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-native-bootstrap-') as tmp:
        cpp=Path(tmp)/'world.cpp';exe=Path(tmp)/'world.exe'
        cpp.write_text(PREFIX+globals_+''.join(function(s) for s in signatures)+MAIN,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production pre-event native bootstrap: FirstSync wait, story before events, no rewind, owner epoch, m29 mount namespace')

if __name__=='__main__':main()
