"""Execute the production missing-character watchdog with an isolated native fixture.

The preceding quit/invasion/confirmed-leave handlers are intentionally outside
this fixture: this regression concerns only the old 180-second distance timer.
No game process, assets or saves are accessed.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
start = source.index('    static bool partner_seen = false;', source.index('void TickBbscSessionEnd()'))
end = source.index('\n}\n', start)
watchdog = source[start:end]
prefix = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <initializer_list>
#include <string_view>
using u8=uint8_t; using u64=uint64_t; using s32=int32_t; using s64=int64_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...)
bool independent=false;
int remotes=0, stops=0, cleanups=0, suspends=0;
s64 bbsc_partner_missing_since_ms=0, bbsc_persistence_restore_at_ms=0;
constexpr s64 BbscPartnerGoneMs=180000;
constexpr u64 MatchingStatePointerOffset=1, MultiPlayStopRequestOffset=0, WorldChrManRemoteCleanupOffset=0;
u64 image_base=0;
u8 StopFixture(u64) {++stops; return 1;}
void CleanupFixture(u64) {++cleanups;}
bool BbscIndependentActive(){return independent;}
int RemotePlayerCount(){return remotes;}
u64 GetGlobalState(){return 100;}
bool ReadablePointer(u64,size_t){return true;}
template<class T> T ReadValue(u64,size_t offset) {
    if(offset==0x08)return 0;
    if(offset==0x16F8)return 200;
    return static_cast<T>(300);
}
void SuspendBbscPersistence(std::string_view){++suspends;}
'''
# Replace only the two native address expressions with fixture callbacks;
# all production timer/role/independent-mode decisions execute unchanged.
watchdog = watchdog.replace('image_base + MultiPlayStopRequestOffset', 'reinterpret_cast<u64>(&StopFixture)')
watchdog = watchdog.replace('image_base + WorldChrManRemoteCleanupOffset', 'reinterpret_cast<u64>(&CleanupFixture)')
main = r'''
int main(){
    s64 now=1000;
    for(int role : {3,6}) {
        Tick(0,now++); // reset session-local "seen" state
        independent=true;remotes=1;Tick(role,now++);
        remotes=0;
        for(int i=0;i<1000;++i){now+=1000;Tick(role,now);}
        assert(stops==0 && cleanups==0 && suspends==0);
        assert(bbsc_partner_missing_since_ms==0);
        // Even a timer armed before negotiation must be discarded.
        independent=false;remotes=1;Tick(role,now++);
        remotes=0;Tick(role,now++);assert(bbsc_partner_missing_since_ms);
        independent=true;now+=180001;Tick(role,now);
        assert(stops==0 && suspends==0 && bbsc_partner_missing_since_ms==0);
    }
    // Legacy non-independent sessions retain bounded missing-partner cleanup.
    independent=false;
    for(int role : {3,6}) {
        Tick(0,now++);remotes=1;Tick(role,now++);remotes=0;
        Tick(role,now++);now+=179000;Tick(role,now);
        assert(stops==(role==6?1:0) && suspends==0);
        now+=1001;Tick(role,now);
        assert(stops==1 && cleanups==1 && suspends==(role==6?1:0));
    }
}
'''
compiler = os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
with tempfile.TemporaryDirectory(prefix='bbsc-session-distance-') as tmp:
    cpp, exe = Path(tmp)/'test.cpp', Path(tmp)/'test.exe'
    cpp.write_text(prefix+'void Tick(s32 session_state,s64 now){\n'+watchdog+'\n}\n'+main, encoding='utf-8')
    subprocess.run([compiler,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],check=True,env=env,timeout=10)
print('PASS: independent host/guest separation preserves session; stale timer discarded; legacy timeout retained')
