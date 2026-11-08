"""Exercise boss-clear departure gates, compatibility and delayed quit callbacks."""
import os
from pathlib import Path
import subprocess
import tempfile
source = (Path(__file__).resolve().parents[1] / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def callback(name):
    start = source.index(f'void PS4_SYSV_ABI {name}(')
    return source[start:source.index('\n}\n', start) + 3]


assert 'TickBbscBossUnlock' not in source
code = r'''
#include <cassert>
#include <cstdint>
using u64=uint64_t; using s64=int64_t; using u8=uint8_t;
#define PS4_SYSV_ABI
#define BBSC_PERF_SCOPE(...)
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
struct GuestRegisterSnapshot {};
bool quit=false, alive=false, bbsc_spectate_active=false;
bool bbsc_boss_departure_gates_ready=true, loading=false;
int type=0, guarded=0, armed=0, hp=100, leave_releases=0, death_releases=0;
u8 bbsc_boss_leave_skip=0, bbsc_boss_home_skip=0;
u8 bbsc_boss_departure_gate_skip=0;
s64 bbsc_boss_killed_ms=0, bbsc_gate_watch_since_ms=0;
bool BbscQuitInProgress(){return quit;}
bool BbscSessionAlive(){return alive;}
int LocalPlayerType(){return type;}
u64 GetGlobalState(){return 1;}
u64 GetLocalPlayerCharacter(){return 2;}
bool ReadablePointer(u64 p, u64){return p!=0;}
template<class T> T ReadValue(u64,u64){return loading;}
int GetCharacterHp(u64){return hp;}
s64 SteadyNowMs(){return 1000;}
void GuardBbscBossClearCoopCount(){++guarded;}
void ArmBbscDeathLockClear(){++armed;}
void ReleaseBbscLeaveLocks(const char*){++leave_releases;}
void ReleaseBbscDeathLocks(const char*){++death_releases;}
'''
code += callback('BbscBossDepartureGateHook') + '\n' + callback('BbscBossClearHook')
code += r'''
int main(){
 GuestRegisterSnapshot r;
 for(bool ready : {false,true}) for(bool live : {false,true})
 for(bool exiting : {false,true}) for(int t : {0,1,2,8}) {
  bbsc_boss_departure_gates_ready=ready;
  alive=live; quit=exiting; type=t;
  bbsc_boss_departure_gate_skip=0;
  BbscBossDepartureGateHook(0,&r);
  assert(bool(bbsc_boss_departure_gate_skip)==(ready && live && !exiting && t==1));
 }
 for(bool live : {false,true}) for(int t : {0,1}) {
  alive=live; type=t; quit=true;
  bbsc_boss_leave_skip=bbsc_boss_home_skip=0;
  BbscBossClearHook(0,&r); assert(!guarded && !armed);
  BbscBossClearHook(1,&r); assert(bbsc_boss_leave_skip==1);
  BbscBossClearHook(2,&r); assert(bbsc_boss_home_skip==1);
 }
 quit=false; alive=true; type=0;
 bbsc_boss_home_skip=0; BbscBossClearHook(2,&r); assert(!bbsc_boss_home_skip);
 type=1; BbscBossClearHook(2,&r); assert(bbsc_boss_home_skip);
 BbscBossClearHook(0,&r); assert(guarded==1 && armed==1);
 alive=false; bbsc_boss_home_skip=0; BbscBossClearHook(2,&r); assert(!bbsc_boss_home_skip);
 quit=true; BbscBossClearHook(2,nullptr); assert(!bbsc_boss_home_skip);
 assert(leave_releases==0 && death_releases==0);

 bbsc_boss_departure_gates_ready=false;
 quit=false; alive=true; type=1;
 hp=0; BbscBossClearHook(2,&r); assert(leave_releases==0 && death_releases==0);
 hp=100; loading=true;
 BbscBossClearHook(2,&r); assert(leave_releases==0 && death_releases==0);
 loading=false; BbscBossClearHook(2,&r);
 assert(bbsc_boss_home_skip && leave_releases==1 && death_releases==1);
}
'''
code = '#include <initializer_list>\n' + code
with tempfile.TemporaryDirectory() as d:
 p=Path(d); (p/'test.cpp').write_text(code, encoding='utf-8')
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(p/'test.cpp'),'-o',str(p/'test.exe')],check=True)
 subprocess.run([str(p/'test.exe')],check=True)
print('Production boss clear: scoped departure gates, one-shot compatibility and late quit PASS')
