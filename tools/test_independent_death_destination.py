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
start_entry=source.index('void BeginBbscCoopDeath(std::string_view name, s32 session_state) {')
end_entry=source.index('{',start_entry)+1;depth=1
while depth:
    depth+=(source[end_entry]=='{')-(source[end_entry]=='}');end_entry+=1
entry=source[start_entry:end_entry]

negative=os.environ.get('BBSC_TEST_DEATH_OLD')=='1'
if negative:
    production=production.replace('const bool independent = BbscIndependentActive();','const bool independent = false;')
prefix = r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <mutex>
#include <string_view>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
#define PS4_SYSV_ABI
bool kidnap=false,prison_ready=false;
bool BbscKidnapDeathPending(){return kidnap;}
bool BbscKidnapRespawnReady(){return prison_ready;}
bool independent=true,living=true,host_reload=true,loop=false,revive_ok=true;
bool bbsc_request_death_reload=false,bbsc_spectate_active=true,bbsc_spectate_releasing=false;
bool bbsc_spectate_waiting_host_reload=false,bbsc_spectate_saw_wipe=true,bbsc_spectate_wipe_warped=false;
bool bbsc_spectate_logged_wait=false; s32 role=6;
s64 now=100000,bbsc_spectate_since_ms=100,bbsc_spectate_host_back_ms=1;
s64 bbsc_boss_killed_ms=0,bbsc_boss_cleared_since_ms=0,bbsc_spectate_alone_since_ms=0;
u32 bbsc_spectate_revivals_at_death=0,bbsc_spectate_load_generation=1;
std::atomic<u32> bbsc_load_generation{1},bbsc_peer_revivals{1};
enum class BbscDeathMode{Spectate,RespawnNow};BbscDeathMode bbsc_death_mode=BbscDeathMode::RespawnNow;
constexpr s64 BbscWipeHostSettleMs=2000,BbscFollowStaleMs=3000,BbscBossClearedSettleMs=1000;
constexpr s64 BbscSpectateSafetyMs=120000,BbscSpectateReleaseDebounceMs=500,BbscGuestWaitHostMs=30000;
constexpr u64 MatchingStatePointerOffset=1,MultiPlayStopRequestOffset=2;u64 image_base=0;
std::string_view bbsc_spectate_name="death";
std::mutex bbsc_follow_mutex;
struct BbscFollowMessage{s64 received_ms=100000;u32 packed_map=0x18000000;float x=9,y=0,z=0,heading=0;};
BbscFollowMessage bbsc_follow_latest;
struct SummonPlacementDescriptor{u32 packed_region;float x,y,z,heading;};
int warps=0,reloads=0,suspends=0,releases=0,revives=0,penalties=0,curtains=0;
bool fade_ok=false,boss=false;
std::atomic<bool> bbsc_own_dead{false};std::atomic<u32> bbsc_revivals_at_own_death{0};
struct NativeRearm {u64 player,global;int retry;u32 load;};NativeRearm bbsc_native_death_rearm{};
u64 GetLocalPlayerCharacter(){return 1;}int GetLocalCharacterType(){return role==6?1:0;}
bool IsInvaderType(int){return false;}int RemoteInvaderCount(){return 0;}
bool BbscBossFightAtDeath(){return boss;}void StashBbscOwnWorldSnapshot(){}
namespace Bbsc {void CinematicForceOff(){} void CinematicSetWatching(bool){}}
void NoteBbscBossBar(){}void RestoreBbscOwnWorldSnapshot(){}
void RequestBbscDeathReload(std::string_view){++reloads;}
bool BbscIndependentActive(){return independent;}s64 SteadyNowMs(){return now;}
s32 GetSessionState(){return role;}bool BbscHostReportsDeathReload(){return host_reload;}
bool LivingPartnerExists(){return living;}bool IsUsablePackedMap(u32){return true;}
u64 GetGlobalState(){return 0;}bool RequestBbscSessionWarp(u64,SummonPlacementDescriptor,std::string_view){++warps;return true;}
bool BbscDiedRightAfterRespawn(std::string_view){return loop;}
void BbscApplyDeathPenalty(std::string_view){++penalties;}
bool StartBbscDeathCurtain(std::string_view){++curtains;return fade_ok;}
bool BbscRespawnInPlace(std::string_view){++revives;return revive_ok;}
void SuspendBbscPersistenceOnce(std::string_view){++suspends;}
void ReleaseBbscGuestRespawnPoint(std::string_view){++releases;}
template<class T>T ReadValue(u64,size_t){return 0;}
bool ReadablePointer(u64,size_t){return false;}
'''
main = r'''
void reset(){warps=reloads=suspends=releases=revives=penalties=curtains=0;fade_ok=false;boss=false;
 bbsc_spectate_active=true;bbsc_spectate_releasing=false;bbsc_request_death_reload=false;
 bbsc_spectate_saw_wipe=true;bbsc_spectate_wipe_warped=false;
 bbsc_spectate_waiting_host_reload=false;bbsc_spectate_alone_since_ms=0;
 bbsc_death_mode=BbscDeathMode::RespawnNow;living=true;loop=false;revive_ok=true;
 bbsc_spectate_host_back_ms=1;bbsc_load_generation=1;bbsc_spectate_load_generation=1;}
int main(){
 for(s32 r:{3,6}){role=r;
  // The old common entry must preserve ordinary no-load fade and boss spectate.
  reset();fade_ok=true;bbsc_spectate_active=false;BeginBbscCoopDeath("watchdog",role);
  assert(bbsc_spectate_active&&bbsc_death_mode==BbscDeathMode::RespawnNow);
  TickBbscSpectate();assert(curtains==1&&revives==0&&reloads==0&&!bbsc_spectate_active);
  reset();fade_ok=true;boss=true;bbsc_spectate_active=false;BeginBbscCoopDeath("watchdog",role);
  assert(bbsc_spectate_active&&bbsc_death_mode==BbscDeathMode::Spectate);
  TickBbscSpectate();assert(curtains==0&&revives==0&&reloads==0&&bbsc_spectate_active);
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
  TickBbscSpectate();assert(revives==0&&reloads==0&&bbsc_spectate_active);
  prison_ready=true;TickBbscSpectate();assert(reloads==1&&revives==0&&!bbsc_spectate_active);
  TickBbscSpectate();assert(reloads==1); // no duplicate request
  reset();bbsc_spectate_active=false;bbsc_request_death_reload=true;prison_ready=false;
  TickBbscSpectate();assert(reloads==0&&bbsc_request_death_reload);
  prison_ready=true;TickBbscSpectate();assert(reloads==1&&!bbsc_request_death_reload);
  kidnap=false;
 }
 // The negotiated-independent guard must not silently change old follow mode.
 independent=false;role=6;reset();host_reload=false;bbsc_death_mode=BbscDeathMode::Spectate;
 bbsc_follow_latest.received_ms=now;TickBbscSpectate();assert(warps==1&&revives==0);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-death-destination-') as tmp:
    cpp, exe = Path(tmp)/'death.cpp', Path(tmp)/'death.exe'
    cpp.write_text(prefix+entry+production+main, encoding='utf-8')
    compiler = os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env = dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    result=subprocess.run([str(exe)],env=env)
    if negative:
        assert result.returncode!=0,'Old death routing did not fail the regression'
    else:
        result.check_returncode()
if negative:
    print('PASS negative control: old host-follow death routing FAILS independent regression')
    raise SystemExit(0)
print('PASS production spectate: both roles, host revival/wipe, repeated death, failed local lamp, no local partners, loading; independent deaths never follow host or leave room; legacy follow retained')
