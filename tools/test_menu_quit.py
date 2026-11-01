"""Exercise production menu-exit/save ordering without a game or player saves."""
import os
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
#include <atomic>
#include <cassert>
#include <cstdint>
#include <map>
#include <string_view>
#include <vector>
#include <algorithm>
using u8=uint8_t; using u64=uint64_t; using u32=uint32_t;
using s32=int32_t; using s64=int64_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...)
#define LOG_ERROR(...)
struct GuestRegisterSnapshot { u64 rax=0, rbx=0; };
namespace MemoryProt { constexpr int CpuWrite=1; }
u64 image_base=0x100000, world=0x200000, menu=0x300000, manager=0x400000;
constexpr u64 MenuManPointerOffset=0x80, MatchingStatePointerOffset=0x88, SprjLuaEventManPointerOffset=0x90;
std::map<u64,u64> memory;
std::vector<int> events; // journal=1, save=2, notify=3, suspend=4, stop=5
constexpr u64 request_address=0x700008;
u64 BbscEventRequestAddress() { return memory[0x700000]; }
s32 session=6; s64 now=1000; bool accept_save=true;
std::atomic<bool> bbsc_recover_session_cleanup{false};
template<class T> T ReadValue(u64 p, size_t off) { return static_cast<T>(memory[p+off]); }
template<class T> bool WriteValue(u64 p, size_t off, T value) { memory[p+off]=value; return true; }
bool ReadablePointer(u64 p, size_t) { return p>=0x10000; }
bool HasMemoryAccess(u64 p, size_t, int) { return p>=0x10000; }
u64 GetGlobalState() { return world; }
s32 GetSessionState() { return session; }
s64 SteadyNowMs() { return now; }
void LogBbscQuitQueue(u64) {}
void CancelBbscReinsert(std::string_view) {}
void FlushBbscSessionJournals() { events.push_back(1); }
void SendBbscSessionLeave() { events.push_back(3); }
void SuspendBbscPersistence(std::string_view) { events.push_back(4); }
u8 save_stub(s32 slot, s32 flag, s32 erase) {
    assert(session>=0 && session<=7);
    assert(memory[menu+0x2DC]==1 && memory[0x600000+0x8D]==1);
    assert(slot==-1 && flag==0 && erase==0);
    events.push_back(2);
    if (!accept_save) return 0;
    memory[world+0x1554]=1;
    return 1;
}
u8 stop_stub(u64 value) { assert(value==manager); events.push_back(5); session=7; return 1; }
void title_stub() {
    assert((session==0 || session==2 || session==5) && memory[world+0x1554]==0);
    assert(memory[menu+0x250]==0 && memory[menu+0x25C]==0);
    events.push_back(6); memory[request_address]=2;
}
u64 OnReturnTitleOffset=reinterpret_cast<u64>(&title_stub)-image_base;
int closed=0;
void close_stub(s32 mode) { assert(mode==3); ++closed; }
u64 MultiPlayStopRequestOffset=reinterpret_cast<u64>(&stop_stub)-image_base;
'''

begin = SOURCE.index('bool bbsc_quit_prepared = false;')
end = SOURCE.index('std::mutex bbsc_peer_left_mutex;', begin)
state = SOURCE[begin:end].replace(
    'constexpr u64 BbscNativeSaveRequestOffset = 0x0156D570;',
    'u64 BbscNativeSaveRequestOffset = reinterpret_cast<u64>(&save_stub)-image_base;')
state=state.replace('constexpr u64 BbscQuitCloseMenusOffset = 0x0176A900;', 'u64 BbscQuitCloseMenusOffset = reinterpret_cast<u64>(&close_stub)-image_base;')
functions = '\n'.join(function(signature) for signature in (
    'void PrepareBbscQuitToTitle()',
    'void RestoreBbscQuitControls(const BbscPendingQuit& pending)',
    'void CancelBbscPendingQuit(std::string_view why)',
    'void PS4_SYSV_ABI BbscNativeQuitConfirmHook(u64, const GuestRegisterSnapshot* registers)',
    'void PS4_SYSV_ABI BbscQuitSaveResultHook(u64, const GuestRegisterSnapshot* registers)',
    'void TickBbscPendingQuit()',
    'void ReleaseBbscQuitTitleAtLoad(bool native_finish, u64 global)',
))

fixture = r'''
void reset(s32 role=6) {
    memory.clear(); events.clear(); closed=0; session=role; now=1000; accept_save=true;
    bbsc_pending_quit={}; bbsc_title_quit={}; bbsc_quit_prepared=false; bbsc_quit_defer_store=0;
    bbsc_quit_save_hooks_ready=true; bbsc_quit_save_watch=false; bbsc_quit_save_result=-1;
    memory[image_base+MenuManPointerOffset]=menu;
    memory[image_base+SprjLuaEventManPointerOffset]=0x600100; memory[0x600100+8]=0x600000;
    memory[image_base+MatchingStatePointerOffset]=manager;
    memory[image_base+BbscNativeSaveManagerOffset]=0x500000;
    memory[world+0x1490]=2; memory[0x700000]=request_address;
}
void confirm() {
    GuestRegisterSnapshot r; r.rax=menu;
    memory[menu+0x25C]=0; // hook runs before native side effects
    BbscNativeQuitConfirmHook(0,&r);
}
void result(s32 value, bool correct_manager=true) {
    GuestRegisterSnapshot r; r.rax=static_cast<u64>(value);
    r.rbx=correct_manager ? 0x500000 : 0x600000;
    BbscQuitSaveResultHook(0,&r);
}
bool stopped() { return std::find(events.begin(),events.end(),5)!=events.end(); }
void assert_cancelled() {
    assert(!BbscQuitInProgress() && !stopped());
    assert(memory[menu+0x2DC]==0 && memory[0x600000+0x8D]==0);
    assert(memory[menu+0x250]==0 && memory[menu+0x25C]==0);
}
int main() {
    for (s32 role : {1,3,4,6}) {
        reset(role); confirm();
        assert(BbscQuitInProgress() && bbsc_quit_defer_store==1);
        assert(memory[menu+0x250]==0 && !stopped());
        confirm(); assert(events.size()==1 && closed==0); // duplicate preserves the pending save
        PrepareBbscQuitToTitle(); assert(!stopped()); // Lua/load fallback cannot bypass save
        TickBbscPendingQuit();
        assert(events==std::vector<int>({1,2}) && closed==1);
        result(1); TickBbscPendingQuit(); assert(!stopped());
        result(0,false); memory[world+0x1554]=0;
        TickBbscPendingQuit(); assert(!stopped()); // idle is not proof of success
        result(0); memory[world+0x1554]=1;
        TickBbscPendingQuit(); assert(!stopped()); // engine must finish completion handling
        memory[world+0x1554]=0; TickBbscPendingQuit();
        assert(events==std::vector<int>({1,2,1,3,4,5}));
        assert(session==7 && memory[menu+0x250]==0 && BbscQuitInProgress());
        TickBbscPendingQuit(); assert(memory[menu+0x250]==0); // Stop request is not completion
        session=0; TickBbscPendingQuit();
        assert(memory[menu+0x250]==0 && memory[request_address]==2 && BbscQuitInProgress());
        memory[menu+0x2DC]=0; memory[0x600000+0x8D]=0;
        TickBbscPendingQuit(); assert(memory[menu+0x2DC]==1 && memory[0x600000+0x8D]==1);
        ReleaseBbscQuitTitleAtLoad(false,world); assert(BbscQuitInProgress());
        memory[world+0x1592]=0; ReleaseBbscQuitTitleAtLoad(true,world); assert(BbscQuitInProgress());
        memory[world+0x1592]=1; ReleaseBbscQuitTitleAtLoad(true,world); assert(!BbscQuitInProgress());
        TickBbscPendingQuit(); assert(events.size()==7 && events.back()==6); // title once, no delayed disconnect
    }
    reset(); memory[world+0x1554]=1; confirm(); result(0);
    TickBbscPendingQuit(); assert(events.size()==1 && !bbsc_pending_quit.requested);
    memory[world+0x1554]=0; TickBbscPendingQuit();
    assert(bbsc_pending_quit.requested && bbsc_quit_save_result==-1);
    reset(); accept_save=false; confirm(); TickBbscPendingQuit(); assert_cancelled();
    reset(); confirm(); TickBbscPendingQuit(); result(9); memory[world+0x1554]=0;
    TickBbscPendingQuit(); assert_cancelled();
    reset(); confirm(); TickBbscPendingQuit(); now+=BbscQuitSaveTimeoutMs;
    TickBbscPendingQuit(); assert_cancelled();
    reset(); confirm(); memory[world+0x08]=1; TickBbscPendingQuit();
    assert(!BbscQuitInProgress() && !stopped());
    assert(memory[menu+0x2DC]==1 && memory[0x600000+0x8D]==1); // native load owns cleanup
    reset(3); confirm(); session=6; TickBbscPendingQuit(); assert_cancelled();
    reset(); confirm(); memory[world+0x1490]=3; TickBbscPendingQuit(); assert_cancelled();
    reset(); memory[world+0x1490]=static_cast<u64>(-1); confirm();
    TickBbscPendingQuit(); assert_cancelled();
    reset(); confirm(); TickBbscPendingQuit(); result(0); memory[world+0x1554]=0;
    memory[image_base+MatchingStatePointerOffset]=0;
    TickBbscPendingQuit(); assert_cancelled();
    reset(); confirm(); TickBbscPendingQuit(); result(0); memory[world+0x1554]=0;
    TickBbscPendingQuit(); assert(session==7 && BbscQuitInProgress());
    now+=BbscQuitSaveTimeoutMs; TickBbscPendingQuit();
    assert(!BbscQuitInProgress() && !bbsc_quit_prepared && memory[menu+0x250]==0);
    session=0; TickBbscPendingQuit(); assert(memory[menu+0x250]==0); // no late title release
    // Former host, already disconnected: save, then direct title; no Stop needed.
    reset(0); confirm(); assert(BbscQuitInProgress() && bbsc_quit_defer_store==1);
    TickBbscPendingQuit(); result(0); memory[world+0x1554]=0;
    memory[image_base+MatchingStatePointerOffset]=0;
    TickBbscPendingQuit(); TickBbscPendingQuit();
    assert(events==std::vector<int>({1,2,6}));
    assert(memory[request_address]==2 && memory[menu+0x250]==0 && BbscQuitInProgress());
    reset(); confirm(); TickBbscPendingQuit(); result(0); memory[world+0x1554]=0;
    memory[0x700000]=0; TickBbscPendingQuit(); assert_cancelled();
    assert(memory[request_address]==0);
    // A title target disappearing during asynchronous Stop must not be called.
    reset(); confirm(); TickBbscPendingQuit(); result(0); memory[world+0x1554]=0;
    TickBbscPendingQuit(); assert(stopped());
    memory[0x700000]=0; session=0; TickBbscPendingQuit();
    assert(!BbscQuitInProgress() && events.back()==5 && memory[menu+0x250]==0);
    for (s32 role : {-1,8}) {
        reset(role); confirm();
        assert(!BbscQuitInProgress() && bbsc_quit_defer_store==0 && events.empty());
    }
    for (s32 role : {2,5,7}) {
        reset(role); confirm(); TickBbscPendingQuit(); result(0); memory[world+0x1554]=0;
        TickBbscPendingQuit(); if(role==7) session=0; TickBbscPendingQuit();
        assert(memory[request_address]==2 && !stopped());
    }
    // Departure during save still honors confirmation.
    reset(); confirm(); TickBbscPendingQuit(); session=0; result(0); memory[world+0x1554]=0;
    TickBbscPendingQuit(); TickBbscPendingQuit();
    assert(memory[request_address]==2 && !stopped());
    reset(); memory[menu+0x2DC]=9; memory[0x600000+0x8D]=1;
    confirm(); now+=BbscQuitSaveTimeoutMs; TickBbscPendingQuit();
    assert(!BbscQuitInProgress() && memory[menu+0x2DC]==9 && memory[0x600000+0x8D]==1);
    reset(); bbsc_quit_save_hooks_ready=false; confirm();
    assert(!BbscQuitInProgress() && bbsc_quit_defer_store==0 && events.empty());
}
'''

with tempfile.TemporaryDirectory(prefix='bbsc-menu-quit-') as temporary:
    cpp = Path(temporary) / 'test.cpp'
    exe = Path(temporary) / 'test.exe'
    cpp.write_text(prefix + state + functions + fixture, encoding='utf-8')
    subprocess.run([os.environ.get('CXX', 'g++'), '-std=c++20', '-O0', str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=10)
print('Production menu quit: save before disconnect, role/slot guards, error/timeout cancellation: PASS')
