"""Run production send-home hook and deferred lock release without game files."""
from pathlib import Path
import os
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
    begin = source.index(signature + ' {')
    end = source.index('{', begin) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[begin:end]

code = r'''
#include <cassert>
#include <cstdint>
#include <string_view>
using u64=uint64_t; using u8=uint8_t; using s64=int64_t;
#define PS4_SYSV_ABI
#define BBSC_PERF_SCOPE(...)
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
struct GuestRegisterSnapshot {u64 rsp=0;};
int state=6, hp=100, releases=0, deaths=0; bool quit=false, finale=false, loading=false, own=false;
u64 image_base=1; s64 now=100, bbsc_persistence_restore_at_ms=0;
u8 bbsc_send_home_skip=0; bool bbsc_release_leave_locks=false, bbsc_home_return_claimed=false;
int GetSessionState(){return state;} int GetCharacterHp(u64){return hp;}
u64 GetLocalPlayerCharacter(){return 1;} bool BbscQuitInProgress(){return quit;}
bool BbscDreamFinaleHolding(){return finale;} u64 GetGlobalState(){return 1;}
bool BbscOwnWorldNonGuest(u64){return own;}
bool ReadablePointer(u64,int){return true;}
template<class T>T ReadValue(u64,size_t off){return off==8 ? loading : 0;}
enum class MemoryProt {CpuRead}; bool HasMemoryAccess(u64,size_t,MemoryProt){return false;}
s64 SteadyNowMs(){return now;}
void ReleaseBbscLeaveLocks(std::string_view){++releases;}
void ReleaseBbscDeathLocks(std::string_view){++deaths;}
'''
for sig in ['bool BbscGuestStayingInSession()',
            'void PS4_SYSV_ABI BbscSendPhantomHomeHook(u64, const GuestRegisterSnapshot* registers)',
            'void TickBbscLeaveLocks()']:
    code += function(sig) + '\n'
code += r'''
void hook(){bbsc_send_home_skip=0;bbsc_release_leave_locks=false;BbscSendPhantomHomeHook(0,nullptr);}
int main(){
 // Remaining guest: skip the delayed native warp, release locks next tick.
 hook(); assert(bbsc_send_home_skip && bbsc_release_leave_locks);
 TickBbscLeaveLocks();assert(releases==0);++now;TickBbscLeaveLocks();assert(releases==1&&deaths==1);
 // Local Blank suspends persistence before native Lua schedules send-home.
 bbsc_persistence_restore_at_ms=1000;hook();assert(!bbsc_send_home_skip);
 // A repeated native callback in the same return must be suppressed.
 hook();assert(bbsc_send_home_skip&&!bbsc_release_leave_locks);
 bbsc_persistence_restore_at_ms=0;
 // Host lost / real native teardown / joining / dead: native recovery remains.
 for(int s : {0,4,7}){bbsc_home_return_claimed=false;state=s;hook();assert(!bbsc_send_home_skip);}
 bbsc_home_return_claimed=false;state=6;hp=0;hook();assert(!bbsc_send_home_skip);hp=100;
 bbsc_home_return_claimed=false;quit=true;hook();assert(!bbsc_send_home_skip);quit=false;
 // Departure between skip and deferred release must not unlock the real leave.
 hook();TickBbscLeaveLocks();bbsc_persistence_restore_at_ms=1000;++now;
 TickBbscLeaveLocks();assert(releases==1);
 // Existing own-world host protection and finale behavior remain.
 state=3;own=true;hook();assert(bbsc_send_home_skip);
 state=0;own=false;finale=true;hook();assert(bbsc_send_home_skip);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-resident-leave-') as tmp:
    cpp, exe = Path(tmp)/'test.cpp', Path(tmp)/'test.exe'
    cpp.write_text(code, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler, '-std=c++20', str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], check=True, env=env, timeout=5)
print('PASS: resident guest stays, local leave/loss/quit/death recover, deferred release respects departure')
