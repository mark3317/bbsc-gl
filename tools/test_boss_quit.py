"""Run the production boss-clear hook through delayed quit callbacks."""
import os
from pathlib import Path
import subprocess
import tempfile
source = (Path(__file__).resolve().parents[1] / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
start = source.index('void PS4_SYSV_ABI BbscBossClearHook(')
end = source.index('\n}\n', start) + 3
hook = source[start:end]
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
int type=0, guarded=0, armed=0;
u8 bbsc_boss_leave_skip=0, bbsc_boss_home_skip=0;
s64 bbsc_boss_killed_ms=0, bbsc_gate_watch_since_ms=0, bbsc_boss_unlock_until_ms=0;
constexpr s64 BbscBossUnlockMs=5000;
bool BbscQuitInProgress(){return quit;}
bool BbscSessionAlive(){return alive;}
int LocalPlayerType(){return type;}
s64 SteadyNowMs(){return 1000;}
void GuardBbscBossClearCoopCount(){++guarded;}
void ArmBbscDeathLockClear(){++armed;}
'''
code += hook
code += r'''
int main(){
 GuestRegisterSnapshot r;
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
}
'''
code = '#include <initializer_list>\n' + code
with tempfile.TemporaryDirectory() as d:
 p=Path(d); (p/'test.cpp').write_text(code, encoding='utf-8')
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(p/'test.cpp'),'-o',str(p/'test.exe')],check=True)
 subprocess.run([str(p/'test.exe')],check=True)
print('Production boss quit: late host/guest callbacks before and after disconnect PASS')
