"""Run the production post-load recovery and kept-death override in a memory fixture.
No game processes or saves are touched. Requires a C++20 compiler.
"""
import os
import sys
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')

def function(signature):
    start = SOURCE.index(signature + ' {')
    opening = SOURCE.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (SOURCE[end] == '{') - (SOURCE[end] == '}')
        end += 1
    return SOURCE[start:end]

prefix = r'''
#include <cassert>
#include <cstdint>
#include <atomic>
#include <string>
#include <string_view>
#include <unordered_map>
using u8=uint8_t; using u32=uint32_t; using u64=uint64_t;
using s32=int32_t; using s64=int64_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...)
#define LOG_WARNING(...)
namespace MemoryProt { constexpr int CpuWrite=1; }
std::unordered_map<u64,u64> memory;
template<class T> T ReadValue(u64 p, size_t off) { return static_cast<T>(memory[p+off]); }
template<class T> void WriteValue(u64 p, size_t off, T v) { memory[p+off]=v; }
bool ReadablePointer(u64 p, size_t) { return p>=0x10000; }
bool HasMemoryAccess(u64 p, size_t, int) { return p>=0x10000; }
constexpr u64 PlayerSlotManagerPointerOffset=0x100, MatchingStatePointerOffset=0x108;
constexpr s64 BbscReinsertSettleMs=2500;
u64 image_base=0x100000, global=0x200000, slots=0x300000, local=0x400000, player=0x500000;
s32 state=6, hp=0; s64 clock_ms=1000;
bool bbsc_wipe_restock_pending=false; int restocks=0;
void BbscRestockFromStorage(std::string_view) { ++restocks; }
bool ready=true, revive_ok=true; int revived=0, stopped=0, suspended=0, camera_off=0, reloaded=0;
u64 GetGlobalState() { return global; }
s32 GetSessionState() { return state; }
s64 SteadyNowMs() { return clock_ms; }
s32 GetLocalPlayerType() { return ReadValue<s32>(local,0xA4); }
s32 GetLocalCharacterType() { return player ? ReadValue<s32>(player,0x78) : -1; }
u64 GetLocalPlayerCharacter() { return player; }
s32 GetBbscLocalPlayerHp() { return hp; }
bool IsSprjLuaEventManReady() { return ready; }

s32 bbsc_v8_saved_type=-1, bbsc_v8_original_type=-1, bbsc_v8_saved_sign_type=0;
s32 bbsc_v8_session_state=-1;
u8 bbsc_v8_saved_sign_extra=0;
s64 bbsc_v8_death_ms=0, bbsc_v8_ready_since_ms=0;
bool bbsc_v8_pending=false, bbsc_v8_original_swapped=false;
std::atomic<u32> bbsc_load_generation{0};
std::atomic<bool> bbsc_reload_finish_pending{false};
bool bbsc_spectate_active=false, bbsc_spectate_releasing=false;
std::atomic<bool> bbsc_recover_session_cleanup{false};
void LogBbscSessionShape(std::string_view) {}
bool BbscRespawnInPlace(std::string_view) { ++revived; if(revive_ok) { hp=100; ++restocks; } return revive_ok; }
namespace Bbsc { void CinematicForceOff() { ++camera_off; } }
void ClearBbscBossContext(std::string_view) {}
void ReleaseBbscDeathLocks(std::string_view) {}
void EndBbscLoadCover(std::string_view) {}
void RequestBbscDeathReload(std::string_view) { ++reloaded; }
u8 Stop(u64) { ++stopped; state=0; return 1; }
u64 MultiPlayStopRequestOffset=reinterpret_cast<u64>(&Stop)-image_base;
'''
functions = '\n'.join(function(sig) for sig in (
    'void TickBbscLoadState()',
    'bool IsInvaderType(s32 type)',
    'bool SetOwnWorldRestoreType(s32 type, s32* previous)',
    'void CancelBbscReinsert(std::string_view why)',
    'void ArmBbscReinsertV8()',
    'bool BbscPhantomType(s32 type)',
))
fixture = r'''
void SuspendBbscPersistenceOnce(std::string_view why) { ++suspended; CancelBbscReinsert(why); }
'''+function('void TickBbscPostLoadRecovery()')+r'''
void tick(int count) { for(int i=0;i<count;++i) { clock_ms+=250; TickBbscPostLoadRecovery(); } }
int main(int argc,char**argv) {
    assert(argc==2); std::string test=argv[1];
    memory[image_base+PlayerSlotManagerPointerOffset]=slots;
    memory[slots+8]=local;
    memory[image_base+0x0553B188]=0x600000;
    memory[image_base+MatchingStatePointerOffset]=0x700000;
    memory[slots+0x8C]=static_cast<u64>(-1);
    memory[local+0xA4]=1; memory[player+0x78]=1;
    if(test=="load_observer") {
        memory[global+8]=1; TickBbscLoadState();
        global=0; TickBbscLoadState(); assert(bbsc_load_generation==0);
        global=0x200000; memory[global+8]=0; TickBbscLoadState();
        assert(bbsc_load_generation==1); TickBbscLoadState();
        assert(bbsc_load_generation==1); return 0;
    }
    if(test=="native_load_observer") {
        // No game ticks during the load: the native callback is the only evidence.
        bbsc_reload_finish_pending=true;
        memory[global+8]=1; TickBbscLoadState(); assert(bbsc_load_generation==0);
        memory[global+8]=0; TickBbscLoadState(); assert(bbsc_load_generation==1);
        TickBbscLoadState(); assert(bbsc_load_generation==1);
        bbsc_reload_finish_pending=true; TickBbscLoadState();
        assert(bbsc_load_generation==2); TickBbscLoadState();
        assert(bbsc_load_generation==2); return 0;
    }
    if(test=="native_wipe_alive" || test=="native_wipe_dead") {
        bbsc_spectate_active=true;
        bbsc_wipe_restock_pending=true;
        hp=test=="native_wipe_alive" ? 100 : 0;
        bbsc_reload_finish_pending=true; TickBbscLoadState();
        assert(bbsc_load_generation==1);
        tick(20);
        assert(!bbsc_spectate_active && camera_off==1 && hp>0 && stopped==0);
        assert(revived==(test=="native_wipe_dead" ? 1 : 0));
        assert(restocks==1 && !bbsc_wipe_restock_pending);
        tick(20); assert(restocks==1);
        return 0;
    }
    if(test=="override") {
        ArmBbscReinsertV8(); assert(bbsc_v8_original_type==0);
        ArmBbscReinsertV8(); assert(bbsc_v8_original_type==0);
        CancelBbscReinsert("leave before home load");
        assert(memory[0x600004]==0 && !bbsc_v8_pending && !bbsc_v8_original_swapped);
        assert(ReadValue<s32>(slots,0x8C)==-1); return 0;
    }
    if(test=="boss_without_load") {
        bbsc_spectate_active=true; tick(80); assert(revived==0 && camera_off==0); return 0;
    }
    if(test=="home" || test=="home_pending") {
        if(test=="home_pending") ArmBbscReinsertV8();
        state=0; memory[global+0x1592]=1; hp=100; ++bbsc_load_generation;
        tick(16); assert(GetLocalPlayerType()==0 && GetLocalCharacterType()==0);
        assert(ReadValue<s32>(slots,0x8C)==-1 && memory[0x600004]==0);
        assert(bbsc_recover_session_cleanup && !bbsc_v8_pending); return 0;
    }
    bbsc_spectate_active=true; ++bbsc_load_generation;
    if(test=="joining") state=4;
    if(test=="invader") { memory[local+0xA4]=2; memory[player+0x78]=2; }
    if(test=="loading") memory[global+8]=1;
    if(test=="lua_unavailable") ready=false;
    if(test=="title") {
        memory[image_base+0x0553B108]=0x800000;
        memory[0x800010]=0x900000; memory[0x900008]=2;
    }
    if(test=="missing") { player=0; revive_ok=false; }
    if(test=="failed_revive") revive_ok=false;
    if(test=="host_missing") { state=3; player=0; revive_ok=false; }
    if(test=="healthy") hp=100;
    tick(72);
    if(test=="loading" || test=="joining" || test=="invader" || test=="title" || test=="lua_unavailable") {
        assert(revived==0 && stopped==0 && camera_off==0);
    } else if(test=="missing" || test=="failed_revive" || test=="host_missing") {
        assert(revived==((test=="missing" || test=="host_missing") ? 0 : 2) && stopped==1 && suspended==1);
        assert(reloaded==(test=="host_missing" ? 1 : 0));
    } else {
        assert(hp>0 && !bbsc_spectate_active && camera_off==1 && stopped==0);
        assert(revived==(test=="healthy" ? 0 : 1));
        // A subsequent death without a new load must remain a normal boss spectator.
        hp=0; bbsc_spectate_active=true; tick(72); assert(camera_off==1);
    }
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-recovery-') as tmp:
    cpp=Path(tmp)/'fixture.cpp'; exe=Path(tmp)/'fixture.exe'
    cpp.write_text(prefix+functions+fixture,encoding='utf-8')
    subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O0',str(cpp),'-o',str(exe)],check=True)
    for scenario in ('load_observer','native_load_observer','native_wipe_alive','native_wipe_dead','override','boss_without_load','home','home_pending','dead','healthy',
                     'missing','failed_revive','host_missing','loading','joining','invader','title','lua_unavailable'):
        if len(sys.argv)>1 and scenario not in sys.argv[1:]: continue
        subprocess.run([str(exe),scenario],check=True,timeout=5)
        print(scenario+': PASS')
# Integration: no health veto on sending a stranded client home; cancellation precedes teardown.
stranded=function('void TickBbscStrandedGuest()')
assert 'GetCharacterHp' not in stranded
suspend=function('void SuspendBbscPersistence(std::string_view why)')
assert suspend.index('CancelBbscReinsert') < suspend.index('SetPersistentSessionPatches(false)')
print('home return integration: PASS')

spectate=function('void TickBbscSpectate()')
assert spectate.index('bbsc_load_generation.load() != bbsc_spectate_load_generation') < spectate.index('LivingPartnerExists()')
assert 'else if (loaded)' not in spectate
print('completed load has one recovery owner: PASS')

assert 'bbsc_reload_finish_pending.store(true);' in SOURCE[SOURCE.index('if (site.offset == 0x0178D9C0) {'):][:250]
print('native reload callback integration: PASS')
