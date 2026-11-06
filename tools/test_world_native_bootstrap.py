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
#include "core/bbsc_lamp_travel_data.h"
#include "core/bbsc_world_altars.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define BBSC_TIMELINE(...)
#define PS4_SYSV_ABI
bool active=true;u32 self=11,map=0x18010000;int native_state=4,sent=0,applied=0;
namespace BbscMod {u32 RegisterOwnId(){return self;}}
std::mutex bbsc_world_presence_mutex;World::Presence bbsc_world_presence_local;
World::OwnerBook bbsc_independent_owners;
World::PresenceBook bbsc_world_presence_book;
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
s64 native_event=12300000;s64 BbscEventIdOf(u64){return native_event;}
bool BbscIndependentActive(){return active;}bool BbscIndependentTravelAllowed(){return active;}
bool npc_ready=true;
bool blocks_active=false,blocks_ready=false;
bool BbscWorldBlocksActive(){return blocks_active;}
bool BbscWorldAdmitBlocks(const World::Scope&){return blocks_ready;}
bool BbscWorldNativeInitialReady(const World::Scope&,u32,u64){return npc_ready;}
// NPC initial-state admission is a separate production dependency; this fixture
// exercises the Dream/flag barrier after that dependency grants admission.
std::atomic<bool> bbsc_world_catalog_ready{true};
bool dream_ready=true;bool BbscHostDreamStateReady(){return dream_ready;}bool BbscHostWorldFlagsReady(u32){return dream_ready;}
bool altar_ready=false;int session=3,altar_calls=0;
bool BbscWorldApplyAltars(u32){++altar_calls;return session==3||altar_ready;}
u32 GetCurrentPackedMap(){return map;}int GetSessionState(){return session;}
s64 SteadyNowMs(){return 10000;}
std::vector<u64> GetMultiPlayerInsTasks(){return {100};}
u32 GetBbscRelayHost(){return 22;}u32 BbscWorldPeer(u64){return 22;}
template<class T>T ReadValue(u64,size_t off){return off==0xE8?T(1):off==0x50||off==0x54?T(native_state):T(0);}
void BbscWorldSend(const World::Control&){++sent;}
BbscWorldState BbscWorldCaptureFlags(const World::Scope&){return {0,0,1,true};}
void BbscWorldApplyFlags(const World::Scope&,const BbscWorldState&){++applied;intro_live=true;door_live=true;}
int dream_calls=0;void ApplyBbscHostDreamState(const char*){++dream_calls;}
'''
MAIN=r'''
int main(){
 World::Presence p;p.world={11,99};p.map=map;p.phase=World::Phase::Playing;p.visit=1;p.sequence=1;
 bbsc_world_presence_local=p;const auto scope=World::ScopeOf(p);
 bbsc_independent_owners.Bind(p.world);
 bbsc_world_presence_book.Bind(p.world,11);
 auto resident=p;assert(bbsc_world_presence_book.Hear(22,p.world,resident,100));
 World::Control lease;lease.kind=World::ControlKind::Owner;lease.scope=scope;lease.owner=22;lease.epoch=9;
 assert(bbsc_independent_owners.Take(11,lease,100));
 bbsc_independent_states[scope]={9,7,1,true};
 // Disjoint block owners replace the map-wide NPC wait, never the flag gate.
 blocks_active=true;blocks_ready=false;assert(GuardBbscWorldBootstrap(1));
 blocks_ready=true;assert(!GuardBbscWorldBootstrap(1)&&applied==1);
 blocks_ready=false;assert(GuardBbscWorldBootstrap(1)); // newly streamed/unadmitted block
 blocks_ready=true;assert(!GuardBbscWorldBootstrap(1)&&applied==1);
 blocks_active=false;bbsc_world_bootstrap_load=~u64{0};intro_live=door_live=false;applied=0;
 assert(GuardBbscWorldBootstrap(1)); // native FirstSync is not finished
 assert(!intro_live&&!door_live&&applied==0);
 native_state=6;npc_ready=false;assert(GuardBbscWorldBootstrap(1)&&applied==0);
 npc_ready=true;assert(!GuardBbscWorldBootstrap(1));assert(intro_live&&door_live&&applied==1);
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
 // A return request targets Dream BEFORE the native m29 departure event
 // runs its animation/waits/warp. An absent/unready destination owner must
 // not replace the already-admitted CURRENT cup's event scope (both roles).
 for(int role:{3,6}){
  session=role;bbsc_world_presence_local=p;map=0x1d0a5a00;
  bbsc_world_requested_scope=World::Scope{p.world,BbscDreamStateMap,{},0};
  dream_ready=false;altar_ready=false;native_state=4;npc_ready=false;
  const int before_applied=applied,before_dream=dream_calls,before_altar=altar_calls;
  assert(!GuardBbscWorldBootstrap(1)); // REGRESSION: old code blocks all m29 updates
  assert(BbscWorldSceneReady()&&bbsc_world_bootstrap_scope==cup);
  assert(applied==before_applied&&dream_calls==before_dream&&altar_calls==before_altar);
 }
 native_state=6;npc_ready=true;dream_ready=true;
 // The same map-scoping rule serves snapshot availability and arrival apply.
 // Ordinary destinations never inherit the previous cup's key; a stale room's
 // pending request never authorizes any current-map scope.
 const World::Scope dream{p.world,BbscDreamStateMap,{},0};
 assert(World::ScopeForMap(cup,BbscDreamStateMap,std::nullopt)==dream);
 assert(World::ScopeForMap(cup,0x1d0a5a00,dream)==cup);
 assert(World::ScopeForMap(dream,0x1d0a5a00,cup)==cup);
 auto wrong_room=cup;++wrong_room.world.room;
 assert(World::ScopeForMap(cup,0x1d0a5a00,wrong_room)==cup);
 auto another_cup=cup;++another_cup.ritual;
 assert(World::ScopeForMap(dream,BbscDreamStateMap,another_cup)==dream);
 // Dream cannot initialize personal altar events while joining (state4).
 map=BbscDreamStateMap;p.map=map;p.dungeon={};p.ritual=0;bbsc_world_presence_local=p;
 bbsc_world_requested_scope.reset();++bbsc_world_native_load;session=4;
 assert(GuardBbscWorldBootstrap(1));assert(!BbscWorldSceneReady());
 altar_ready=true;dream_ready=false;assert(GuardBbscWorldBootstrap(1));
 dream_ready=true;assert(!GuardBbscWorldBootstrap(1));assert(BbscWorldSceneReady());
 const int calls=altar_calls;assert(!GuardBbscWorldBootstrap(1)&&altar_calls==calls);
 // Native join changes role/table inside the same load. Install the host view
 // again after state4 -> state6, then leave running events alone.
 session=6;assert(!GuardBbscWorldBootstrap(1)&&altar_calls==calls+1);
 assert(!GuardBbscWorldBootstrap(1)&&altar_calls==calls+1);
 ++bbsc_world_native_load;
 World::Control dream_lease=lease;dream_lease.scope=World::ScopeOf(p);
 assert(bbsc_independent_owners.Take(11,dream_lease,100));native_state=4;
 const int dreams=dream_calls;
 assert(GuardBbscWorldBootstrap(1)&&dream_calls==dreams&&altar_calls==calls+1);
 native_state=6;assert(!GuardBbscWorldBootstrap(1)&&dream_calls==dreams+1&&altar_calls==calls+2);
 // A world/NPC bootstrap stall must not trap LOCAL travel or its animation.
 // Other events still wait; no source flags are applied as an escape shortcut.
 ++bbsc_world_native_load;dream_ready=false;altar_ready=false;npc_ready=false;native_state=4;
 const int before_local=applied,before_local_dream=dream_calls;
 for(int role:{3,6})for(s64 event:{7200,12107000,12107100,12107200,12907020,9421,9422}){
  session=role;native_event=event;assert(!GuardBbscWorldBootstrap(1));
  assert(applied==before_local&&dream_calls==before_local_dream);
 }
 native_event=12300000;assert(GuardBbscWorldBootstrap(1));
 session=4;native_event=7200;assert(GuardBbscWorldBootstrap(1));
 native_event=12300000;
 active=false;assert(!GuardBbscWorldBootstrap(1));
}
'''

def main():
    signatures=['bool BbscWorldFlagsReady(const World::Scope& scope)',
                'void BbscWorldEnsureSeed(const World::Scope& scope)',
                'bool BbscWorldSceneReady()',
                'bool BbscWorldNativePeerReady(u32 owner)',
                'bool GuardBbscWorldBootstrap(u64 instance)']
    globals_='World::Scope bbsc_world_bootstrap_scope{};u64 bbsc_world_bootstrap_load=~u64{0};s32 bbsc_world_bootstrap_session=-1;\n'
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-native-bootstrap-') as tmp:
        cpp=Path(tmp)/'world.cpp';exe=Path(tmp)/'world.exe'
        cpp.write_text(PREFIX+globals_+''.join(function(s) for s in signatures)+MAIN,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production pre-event native bootstrap: FirstSync wait, story before events, no rewind, owner epoch, m29 mount namespace')

if __name__=='__main__':main()
