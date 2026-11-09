"""Run the production spectate controller; no live game or saves are touched."""
from pathlib import Path
import os, subprocess, tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
start = source.index('void TickBbscSpectate() {')
end = source.index('{', start)+1
depth = 1
while depth:
    depth += (source[end]=='{')-(source[end]=='}'); end += 1
production = source[start:end]
penalty_negative=os.environ.get('BBSC_TEST_GUEST_RELOAD_NO_PENALTY')=='1'
start_entry=source.index('void BeginBbscCoopDeath(std::string_view name, s32 session_state) {')
end_entry=source.index('{',start_entry)+1;depth=1
while depth:
    depth+=(source[end_entry]=='{')-(source[end_entry]=='}');end_entry+=1
entry=source[start_entry:end_entry]
boss_negative=os.environ.get('BBSC_TEST_BOSS_BEFORE_SPECTATE_OLD')=='1'
if boss_negative:
    production=production.replace('bbsc_boss_killed_ms >= bbsc_spectate_death_ms',
                                  'bbsc_boss_killed_ms >= bbsc_spectate_since_ms')

def function(signature):
    a=source.index(signature+' {');b=source.index('{',a)+1;depth=1
    while depth:
        depth+=(source[b]=='{')-(source[b]=='}');b+=1
    return source[a:b]+'\n'
kidnap_production=function('bool BbscKidnapRespawnReady()')+function('bool BbscKidnapDeathPending()')
reload = function("void RequestBbscCoopDeathReload(std::string_view why, bool apply_penalty = true)")
if penalty_negative:
    reload = reload.replace('BbscApplyDeathPenalty("before guest death reload");', '(void)0;')
prefix = r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <mutex>
#include <string_view>
#include "core/bbsc_world_control.h"
namespace World=Core::Bloodborne::World;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define LOG_INFO(...)
int boss_decision_logs=0;
#define BBSC_TIMELINE(kind, message, ...) do { \
 if(std::string_view(message).starts_with("boss death decision=")) ++boss_decision_logs; \
} while(false)
bool BbscTimelineEnabled(){return true;}
#define PS4_SYSV_ABI
bool kidnap=false,prison_ready=false;
bool BbscKidnapDeathPending();bool BbscKidnapRespawnReady();
bool BbscIndependentTravelAllowed();
bool BbscIndependentActive();
// Match live historical9421/9422 on an ordinary checkpoint by default.
bool BbscEventFlag(u32 f){return f==9420?kidnap:(f==9421||f==9422);}

bool independent=true,living=true,loop=false,revive_ok=true,bbsc_wipe_restock_pending=false;
s32 native_members=0;
s32 GetBbscSessionMemberCount(u64){return native_members;}
bool all_report_dead=false,bbsc_boss_wipe_seen=false;
bool bbsc_boss_death_ready=false;
std::mutex bbsc_world_presence_mutex;
World::PresenceBook bbsc_world_presence_book;
World::Presence bbsc_world_presence_local;
int ready_sends=0,reload_sends=0,wipe_loads=0;
bool boss_death_work=false;
enum class BbscWork { BossDeath };
void QueueBbscWork(BbscWork){boss_death_work=true;}
constexpr s64 BbscLifeFreshMs=3000;
void SendBbscLifeState(u8 state){assert(state==2||state==3);if(state==3)++ready_sends;else ++reload_sends;}
void MarkBbscBossWipeLoad(){++wipe_loads;}
bool bbsc_request_death_reload=false,bbsc_spectate_active=true,bbsc_spectate_releasing=false;
bool bbsc_spectate_waiting_host_reload=false,bbsc_spectate_saw_wipe=true,bbsc_spectate_wipe_warped=false;
bool bbsc_spectate_logged_wait=false; s32 role=6;
s64 now=100000,bbsc_spectate_since_ms=100,bbsc_spectate_host_back_ms=1;
s64 bbsc_dead_since_ms=0,bbsc_spectate_death_ms=100;
s64 bbsc_boss_killed_ms=0,bbsc_boss_cleared_since_ms=0,bbsc_spectate_alone_since_ms=0;
u32 bbsc_spectate_revivals_at_death=0,bbsc_spectate_load_generation=1;
std::atomic<u32> bbsc_load_generation{1},bbsc_peer_revivals{1};
enum class BbscDeathMode{Spectate,RespawnNow};BbscDeathMode bbsc_death_mode=BbscDeathMode::RespawnNow;
constexpr s64 BbscWipeHostSettleMs=2000,BbscFollowStaleMs=3000,BbscBossClearedSettleMs=1000;
constexpr s64 BbscSpectateSafetyMs=120000,BbscSpectateReleaseDebounceMs=500,BbscGuestWaitHostMs=30000;
constexpr u64 MatchingStatePointerOffset=1,MultiPlayStopRequestOffset=2;u64 image_base=0;
std::string_view bbsc_spectate_name="death";
std::mutex bbsc_follow_mutex;
struct BbscFollowMessage{s64 received_ms=100000;u32 packed_map=0x18000000;float x=9,y=0,z=0,heading=0;
 s64 arrival_ms=0;bool arrival_by_load=false;};
BbscFollowMessage bbsc_follow_latest;
struct SummonPlacementDescriptor{u32 packed_region;float x,y,z,heading;};
int warps=0,reloads=0,suspends=0,releases=0,revives=0,penalties=0,curtains=0;
bool fade_ok=false,boss=false,invader=false;
int expected_penalties_at_reload=-1,local_hp=0;
std::atomic<bool> bbsc_own_dead{false};std::atomic<u32> bbsc_revivals_at_own_death{0};
struct NativeRearm {u64 player,global;int retry;u32 load;};NativeRearm bbsc_native_death_rearm{};
u64 GetLocalPlayerCharacter(){return 1;}int GetLocalCharacterType(){return role==6?1:0;}
s32 GetCharacterHp(u64){return local_hp;}
bool IsInvaderType(int){return invader;}int RemoteInvaderCount(){return 0;}
bool BbscBossFightAtDeath(){return boss;}void StashBbscOwnWorldSnapshot(){}
namespace Bbsc {void CinematicForceOff(){} void CinematicSetWatching(bool){}}
void NoteBbscBossBar(){}void RestoreBbscOwnWorldSnapshot(){}
void RequestBbscDeathReload(std::string_view){
 if(expected_penalties_at_reload>=0)assert(penalties==expected_penalties_at_reload);
 ++reloads;
}
bool BbscIndependentTravelAllowed(){return independent;}
bool BbscIndependentActive(){return independent;}s64 SteadyNowMs(){return now;}
s32 GetSessionState(){return role;}
bool LivingPartnerExists(){return living;}bool IsUsablePackedMap(u32){return true;}
bool BbscAllPartnersReportDead(){return all_report_dead;}
u64 GetGlobalState(){return 0x10000;}bool RequestBbscSessionWarp(u64,SummonPlacementDescriptor,std::string_view){++warps;return true;}
bool BbscDiedRightAfterRespawn(std::string_view){return loop;}
void BbscApplyDeathPenalty(std::string_view){++penalties;}
bool StartBbscDeathCurtain(std::string_view){++curtains;return fade_ok;}
bool BbscRespawnInPlace(std::string_view){++revives;return revive_ok;}
void SuspendBbscPersistenceOnce(std::string_view){++suspends;}
void ReleaseBbscGuestRespawnPoint(std::string_view){++releases;}
template<class T>T ReadValue(u64 p,size_t off){return p==0x10000&&off==0x1528?T(prison_ready?2802959:2412951):T(0);}
bool ReadablePointer(u64 p,size_t){return p==0x10000;}
'''
main = r'''
void reset(){warps=reloads=suspends=releases=revives=penalties=curtains=0;fade_ok=false;boss=false;
 ready_sends=reload_sends=wipe_loads=local_hp=0;
 native_members=0;
 bbsc_boss_death_ready=boss_death_work=false;
 bbsc_death_reload_generation.reset();
 bbsc_boss_death_group=BbscBossDeathGroup::Unavailable;
 bbsc_world_presence_local={};bbsc_world_presence_book.Clear();bbsc_peer_life.clear();
 invader=false;expected_penalties_at_reload=-1;bbsc_wipe_restock_pending=false;
 all_report_dead=false;bbsc_boss_wipe_seen=false;
 bbsc_dead_since_ms=0;bbsc_boss_killed_ms=0;bbsc_spectate_death_ms=100;
 bbsc_spectate_active=true;bbsc_spectate_releasing=false;bbsc_request_death_reload=false;
 bbsc_spectate_saw_wipe=true;bbsc_spectate_wipe_warped=false;
 bbsc_spectate_alone_since_ms=0;
 bbsc_death_mode=BbscDeathMode::RespawnNow;living=true;loop=false;revive_ok=true;
 bbsc_spectate_host_back_ms=1;bbsc_load_generation=1;bbsc_spectate_load_generation=1;}
int main(){
 // A guest alone on its map must drop before reload, once per death.
 // Host, solo, invasion and legacy mode keep their existing native rules.
 for(bool mode:{false,true})for(s32 r:{0,3,6})for(bool invading:{false,true}){
  independent=mode;role=r;reset();invader=invading;living=false;
  bbsc_spectate_active=false;
  BeginBbscCoopDeath("native final",role);
  assert(bbsc_request_death_reload&&!bbsc_spectate_active);
  expected_penalties_at_reload=r==6&&!invading?1:0;
  TickBbscSpectate();
  assert(reloads==1&&penalties==expected_penalties_at_reload);
  assert(bbsc_wipe_restock_pending==(r==6&&!invading));
  TickBbscSpectate();assert(reloads==1&&penalties==expected_penalties_at_reload);
  // The next death is also charged exactly once.
  BeginBbscCoopDeath("native final",role);
  expected_penalties_at_reload*=2;TickBbscSpectate();
  assert(reloads==2&&penalties==expected_penalties_at_reload);
 }
 // Production entry + controller: delayed final/watchdog, ordinary final,
 // stale victory, repeated death, and the existing settle/load boundaries.
 for(bool mode:{false,true})for(s32 r:{3,6})for(int order:{0,1,2,3}){
  independent=mode;role=r;reset();boss=true;fade_ok=true;
  bbsc_spectate_active=false;bbsc_spectate_saw_wipe=false;
  bbsc_peer_revivals=0;bbsc_revivals_at_own_death=0;
  const s64 death=now-15000;
  bbsc_dead_since_ms=order==3?0:death;
  bbsc_boss_killed_ms=order==0?death+8000:order==2?death-1:0;
  BeginBbscCoopDeath("watchdog",role);
  assert(bbsc_spectate_since_ms==now); // existing timers must not move
  assert(bbsc_spectate_death_ms==(order==3?now:death));
  if(order==1||order==3)bbsc_boss_killed_ms=now+1;
  if(order==1||order==3)++now;
  TickBbscSpectate();assert(curtains==0&&reloads==0&&warps==0);
  now+=BbscBossClearedSettleMs-1;TickBbscSpectate();assert(curtains==0);
  ++now;TickBbscSpectate();
  if(order==2){assert(curtains==0&&bbsc_spectate_active);}
  else{
   assert(curtains==1&&penalties==1&&revives==0&&!bbsc_spectate_active);
   TickBbscSpectate();assert(curtains==1); // no duplicate revival
   // The previous kill cannot authorize the next death.
   bbsc_dead_since_ms=0;BeginBbscCoopDeath("native final",role);
   now+=BbscBossClearedSettleMs+1;TickBbscSpectate();
   assert(curtains==1&&bbsc_spectate_active);
  }
  reset();boss=true;bbsc_dead_since_ms=now-15000;
  bbsc_boss_killed_ms=now-7000;BeginBbscCoopDeath("watchdog",role);
  ++bbsc_load_generation;TickBbscSpectate();now+=3000;TickBbscSpectate();
  assert(curtains==0&&revives==0&&reloads==0&&warps==0);
 }
 independent=true;bbsc_peer_revivals=1;
 for(s32 r:{3,6}){role=r;
  // The old common entry must preserve ordinary no-load fade and boss spectate.
  reset();fade_ok=true;bbsc_spectate_active=false;BeginBbscCoopDeath("watchdog",role);
  assert(bbsc_spectate_active&&bbsc_death_mode==BbscDeathMode::RespawnNow);
  TickBbscSpectate();assert(curtains==1&&revives==0&&reloads==0&&!bbsc_spectate_active);
  reset();fade_ok=true;boss=true;bbsc_spectate_active=false;BeginBbscCoopDeath("watchdog",role);
  assert(bbsc_spectate_active&&bbsc_death_mode==BbscDeathMode::Spectate);
  TickBbscSpectate();assert(curtains==0&&revives==0&&reloads==0&&bbsc_spectate_active);
  TickBbscSpectate();assert(ready_sends==1); // no independent presence locally
  reset();TickBbscSpectate();assert(revives==1&&warps==0&&reloads==0&&!bbsc_spectate_active);
  assert(!bbsc_spectate_waiting_host_reload&&penalties==1);
  reset();loop=true;TickBbscSpectate();assert(reloads==1&&warps==0&&suspends==0&&releases==0);
  reset();revive_ok=false;TickBbscSpectate();assert(reloads==1&&warps==0&&suspends==0&&releases==0);
  reset();living=false;TickBbscSpectate();now+=501;TickBbscSpectate();
  assert(reloads==1&&warps==0&&suspends==0&&releases==0);
  reset();bbsc_load_generation=2;TickBbscSpectate();assert(warps==0&&revives==0&&reloads==0);
 }
 // Native abduction must wait for 9421, then load the prison, even with a partner.
 for(s32 r:{3,6}){role=r;reset();kidnap=true;prison_ready=false;
  expected_penalties_at_reload=0;
  TickBbscSpectate();assert(revives==0&&reloads==0&&bbsc_spectate_active);
  prison_ready=true;TickBbscSpectate();assert(reloads==1&&revives==0&&!bbsc_spectate_active);
  TickBbscSpectate();assert(reloads==1); // no duplicate request
  reset();bbsc_spectate_active=false;bbsc_request_death_reload=true;prison_ready=false;
  expected_penalties_at_reload=0;
  TickBbscSpectate();assert(reloads==0&&bbsc_request_death_reload);
  prison_ready=true;TickBbscSpectate();assert(reloads==1&&!bbsc_request_death_reload);
  kidnap=false;prison_ready=false;
 }
 // All three clients run their own native death load on the same room.
 // Cover different orders, both travel modes, and no host placement packet.
 for(bool mode:{false,true})for(s32 first:{3,6}) {
  independent=mode;
  for(s32 r:{first,first==3?6:3,6}) {
   reset();role=r;boss=true;bbsc_spectate_active=false;
   BeginBbscCoopDeath("native final",role);
   TickBbscSpectate();assert(bbsc_spectate_active&&reloads==0);
   living=false;TickBbscSpectate();
   now+=BbscSpectateReleaseDebounceMs-1;TickBbscSpectate();assert(reloads==0);
   ++now;TickBbscSpectate();TickBbscSpectate();
   assert(reloads==1&&warps==0&&suspends==0&&releases==0&&role==r);
   assert(penalties==(r==6?1:0)&&bbsc_wipe_restock_pending==(r==6));
  }
 }
 // A genuine session end still completes the native return exactly once.
 // A temporary absence is not a wipe, and a confirmed wipe survives the
 // first teammate finishing a native load during our original debounce.
 for(bool confirmed:{false,true}){
  reset();role=6;boss=true;bbsc_spectate_active=false;
  BeginBbscCoopDeath("native final",role);
  living=false;all_report_dead=confirmed;TickBbscSpectate();assert(reloads==0);
  living=true;all_report_dead=false;now+=BbscSpectateReleaseDebounceMs;
  TickBbscSpectate();TickBbscSpectate();
  assert(reloads==(confirmed?1:0)&&bbsc_spectate_active!=confirmed);
 }
 // The final hunter can be in the death animation while a teammate returns.
 reset();role=3;boss=true;bbsc_spectate_active=false;bbsc_boss_wipe_seen=true;
 BeginBbscCoopDeath("delayed native final",role);TickBbscSpectate();
 assert(reloads==1&&!bbsc_spectate_active&&role==3);

 reset();living=false;role=0;TickBbscSpectate();TickBbscSpectate();
 assert(!bbsc_spectate_active&&reloads==1&&warps==0&&penalties==0);
 // Failed in-place recovery uses a full load and does not charge twice.
 reset();role=6;revive_ok=false;TickBbscSpectate();TickBbscSpectate();
 assert(reloads==1&&warps==0&&penalties==1&&bbsc_wipe_restock_pending);

 // Same-map hunters wait for the LAST native handoff. Each player may be
 // first, middle or last to reach it, independently of the room host role.
 for(u32 self:{11u,22u,33u})for(u32 last:{11u,22u,33u}){
  reset();role=self==11?3:6;boss=true;bbsc_spectate_active=false;
  auto& local=bbsc_world_presence_local;local.world={11,99};local.map=0x18000000;
  local.phase=World::Phase::Playing;local.sequence=1;local.visit=7;
  local.capabilities|=World::BossDeathReadyCapability;
  bbsc_world_presence_book.Bind(local.world,self);
  auto peer=local;
  assert(bbsc_world_presence_book.Hear(44,local.world,[&]{auto p=peer;p.map=0x15000000;p.alive=1;return p;}(),now));
  for(u32 id:{11u,22u,33u})if(id!=self){
   assert(bbsc_world_presence_book.Hear(id,local.world,peer,now));
   OnBbscLifePacket(id,id==last?u8{1}:u8{3},1,id==11,false);
  }
  assert(boss_death_work);
  living=false;all_report_dead=true;bbsc_boss_wipe_seen=true;
  BeginBbscCoopDeath("native final",role);TickBbscSpectate();
  assert(ready_sends==1);
  if(self!=last){
   now+=2*BbscSpectateReleaseDebounceMs;TickBbscSpectate();
   assert(!reloads&&!wipe_loads&&bbsc_spectate_active&&ready_sends==1);
   // A readiness report for another visit or room cannot release this wipe.
   auto& life=bbsc_peer_life[last];life.dead=3;--life.visit;RefreshBbscBossDeathGroup();
   TickBbscSpectate();assert(!reloads);
   ++life.visit;++life.world.room;RefreshBbscBossDeathGroup();
   TickBbscSpectate();assert(!reloads);
   --life.world.room;
   peer.sequence=2;peer.alive=1;
   assert(bbsc_world_presence_book.Hear(last,local.world,peer,now));
   RefreshBbscBossDeathGroup();TickBbscSpectate();assert(!reloads);
   peer.sequence=3;peer.alive=0;
   if(self==11){
    // The same death's native Loading observation also works if the final
    // life datagram was lost. An alive player's lamp load is not that proof.
    life.dead=1;peer.phase=World::Phase::Loading;
   }
   assert(bbsc_world_presence_book.Hear(last,local.world,peer,now));
   RefreshBbscBossDeathGroup();TickBbscSpectate();
  }
  assert(reloads==1&&wipe_loads==1&&!bbsc_spectate_active&&ready_sends==1);
  TickBbscSpectate();assert(reloads==1&&penalties==(role==6?1:0));
 }

 // A guest may issue its native reload before the death presence arrives.
 // A raw dead report still cannot release the group.
 {
  reset();role=3;boss=true;bbsc_spectate_active=false;living=false;
  auto& local=bbsc_world_presence_local;local.world={11,99};local.map=0x22000000;
  local.phase=World::Phase::Playing;local.sequence=1;local.visit=7;
  local.capabilities|=World::BossDeathReadyCapability;
  bbsc_world_presence_book.Bind(local.world,11);
  auto peer=local;peer.alive=1;
  assert(bbsc_world_presence_book.Hear(22,local.world,peer,now));
  OnBbscLifePacket(22,1,1,false,false);
  BeginBbscCoopDeath("native final",role);TickBbscSpectate();
  assert(!reloads&&ready_sends==1);
  OnBbscLifePacket(22,BbscLifeDeathReloading,2,false,false);
  RefreshBbscBossDeathGroup();TickBbscSpectate();
  assert(reloads==1&&wipe_loads==1);
 }
 // The first guest has a native roster of three but has only heard the dead
 // host. Losing the remaining hunter's model or route must not release it.
 for(bool travel_ready:{false,true})for(bool last_hunter_here:{false,true}){
  reset();role=6;boss=true;bbsc_spectate_active=false;living=false;
  independent=travel_ready;native_members=3;
  auto& local=bbsc_world_presence_local;local.world={11,99};local.map=0x22000000;
  local.phase=World::Phase::Playing;local.sequence=1;local.visit=7;
  local.capabilities|=World::BossDeathReadyCapability;
  bbsc_world_presence_book.Bind(local.world,22);
  auto peer=local;
  assert(bbsc_world_presence_book.Hear(11,local.world,peer,now));
  OnBbscLifePacket(11,BbscLifeBossDeathReady,1,true,false);
  const int initial_decision_logs=boss_decision_logs;
  BeginBbscCoopDeath("native final",role);TickBbscSpectate();
  assert(boss_decision_logs==initial_decision_logs+1);
  RefreshBbscBossDeathGroup();
  assert(boss_decision_logs==initial_decision_logs+1);
  now+=2*BbscSpectateReleaseDebounceMs;TickBbscSpectate();
  assert(!reloads&&bbsc_spectate_active&&ready_sends==1);

  peer.alive=1;
  if(!last_hunter_here)peer.map=0x15000000;
  assert(bbsc_world_presence_book.Hear(33,local.world,peer,now));
  OnBbscLifePacket(33,0,1,false,false);
  RefreshBbscBossDeathGroup();TickBbscSpectate();
  assert(boss_decision_logs==initial_decision_logs+2);
  if(last_hunter_here){
   assert(!reloads&&bbsc_spectate_active);
   peer.alive=0;peer.sequence=2;
   assert(bbsc_world_presence_book.Hear(33,local.world,peer,now));
   OnBbscLifePacket(33,BbscLifeBossDeathReady,2,false,false);
   RefreshBbscBossDeathGroup();TickBbscSpectate();
  }
  assert(reloads==1&&wipe_loads==1&&!bbsc_spectate_active);
 }
 // Only actual death reloads publish the fallback proof. Guests and hosts
 // both publish it before the native load, once per death.
 for(s32 r:{3,6}){
  reset();role=r;bbsc_spectate_active=false;local_hp=1;
  NotifyBbscDeathReload();assert(!reload_sends);
  local_hp=0;
  NotifyBbscDeathReload();NotifyBbscDeathReload();
  assert(reload_sends==1&&bbsc_death_reload_generation==bbsc_load_generation.load());
 }
 reset();role=6;invader=true;
 NotifyBbscDeathReload();assert(!reload_sends);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-death-destination-') as tmp:
    cpp, exe = Path(tmp)/'death.cpp', Path(tmp)/'death.exe'
    group = source[source.index('struct BbscPeerLife {'):source.index('u64 BbscCharacterDrawState(')]
    life_receive = function('void OnBbscLifePacket(std::uint32_t player, std::uint8_t dead, std::uint32_t sequence, bool /*host*/,\n                      bool model_visible)')
    notify = function('void NotifyBbscDeathReload()')
    cpp.write_text(prefix+group+notify+life_receive+kidnap_production+entry+reload+production+main, encoding='utf-8')
    compiler = os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
    env = dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    result=subprocess.run([str(exe)],env=env)
    if boss_negative or penalty_negative:
        assert result.returncode!=0,'Old death routing did not fail the regression'
    else:
        result.check_returncode()
if penalty_negative:
    print('PASS negative control: omitted native penalty FAILS guest reload regression')
    raise SystemExit(0)
if boss_negative:
    print('PASS negative control: pre-fix boss timestamp comparison FAILS delayed-death regression')
    raise SystemExit(0)
print('PASS production death controller: last native handoff for every role, scoped readiness, one local load and penalty, victory, prison and departure')
