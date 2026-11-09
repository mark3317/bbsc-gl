"""Execute the native-leave policy; active sessions must keep their persistence patches."""
from pathlib import Path
import os
import subprocess
import tempfile
SOURCE = Path('emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')

def function(signature):
    begin = SOURCE.index(signature + ' {')
    at = SOURCE.index('{', begin) + 1
    depth = 1
    while depth:
        depth += (SOURCE[at] == '{') - (SOURCE[at] == '}')
        at += 1
    return SOURCE[begin:at]

code = r'''
#include <cassert>
#include <string_view>
using s64=long long;
int state=0, suspended=0;
bool patches=true;
s64 bbsc_persistence_restore_at_ms=0;
int GetSessionState() { return state; }
bool finale_committed=false;
bool BbscNativeFinaleCommitted() { return finale_committed; }
void SuspendBbscPersistence(std::string_view) {
    ++suspended; patches=false; bbsc_persistence_restore_at_ms=1000;
}
'''
code += function('void SuspendBbscPersistenceOnce(std::string_view why)')
code += function('void ReleaseBbscNativeLeavingSession()')
code += r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <atomic>
#include <cstdint>
#include <cstring>
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define BBSC_TIMELINE(...)
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;
struct GuestRegisterSnapshot {u64 r12=0,r14=0,rbp=0;};
u64 image_base=0, player=0x1234, holder[2]{0,0x4321}, global[2]{};
u64 blank_effect=0;
s64 now=1000;
std::atomic<u32> bbsc_load_generation{1};
std::atomic<u64> bbsc_world_load_pending{0};
std::atomic<bool> bbsc_reload_finish_pending{false};
std::atomic<s64> bbsc_leave_event_ms{0};
bool bbsc_spectate_active=false;
u64 GetLocalPlayerCharacter(){return player;}
u64 GetGlobalState(){return reinterpret_cast<u64>(global);}
u64 BbscLocalEffectNode(int id){assert(id==7);return blank_effect;}
int GetCharacterHp(u64 who){assert(who==player);return 10;}
bool BbscQuitInProgress(){return false;}
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
s64 SteadyNowMs(){return now;}
template<class T>T ReadValue(u64 p,size_t offset){
 if(p==image_base+0x0553B0C8)return static_cast<T>(reinterpret_cast<u64>(holder));
 T value;std::memcpy(&value,reinterpret_cast<void*>(p+offset),sizeof(value));return value;
}
int lua_events=0,slot_leaves=0;
void PS4_SYSV_ABI NativeLeave(u64 lua,u64 name){
 assert(lua==holder[1]&&name==image_base+0x0492EA75);++lua_events;
 bbsc_leave_event_ms=now;
}
void PS4_SYSV_ABI NativeMarkSlots(){++slot_leaves;}
void Link(u64 offset,u64 target){
 u8 jump[]{0x48,0xB8,0,0,0,0,0,0,0,0,0xFF,0xE0};
 std::memcpy(jump+2,&target,sizeof(target));
 std::memcpy(reinterpret_cast<void*>(image_base+offset),jump,sizeof(jump));
}
'''
code += SOURCE[SOURCE.index('constexpr u32 BbscPartingBlankGoodsId'):
               SOURCE.index('void SendBbscPvpPacket')]
code += r'''
void TestBlank() {
    image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x1500000,
        MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));
    assert(image_base);
    Link(0x01339870,reinterpret_cast<u64>(&NativeLeave));
    Link(0x014EB860,reinterpret_cast<u64>(&NativeMarkSlots));
    state=6;
    u32 goods=0x4000006F;
    GuestRegisterSnapshot result{0,player,reinterpret_cast<u64>(&goods)+0xD8};
    ObserveBbscGuestBlankResult(result);TickBbscGuestBlank();
    assert(!lua_events && !bbsc_guest_blank_use.player);
    result.r12=1;
    result.r14=player+1;
    ObserveBbscGuestBlankResult(result);TickBbscGuestBlank();assert(!lua_events);
    result.r14=player;
    ObserveBbscGuestBlankResult(result);TickBbscGuestBlank();TickBbscGuestBlank();
    assert(lua_events==1 && slot_leaves==1);
    blank_effect=1;++now;
    ObserveBbscGuestBlankResult(result);TickBbscGuestBlank();
    assert(lua_events==1 && bbsc_guest_blank_use.player);
    bbsc_leave_event_ms=++now;TickBbscGuestBlank();now+=3000;TickBbscGuestBlank();
    assert(lua_events==1 && !bbsc_guest_blank_use.player);
    ObserveBbscGuestBlankResult(result);now+=2999;TickBbscGuestBlank();assert(lua_events==1);
    ++now;TickBbscGuestBlank();assert(lua_events==2 && slot_leaves==2);
    ++now;ObserveBbscGuestBlankResult(result);++bbsc_load_generation;
    now+=3000;TickBbscGuestBlank();assert(lua_events==2 && !bbsc_guest_blank_use.player);
    VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
int main() {
    for(int s : {-1,0,1,2,3,4,5,6}) {
        state=s; ReleaseBbscNativeLeavingSession();
        assert(patches && suspended==0);
    }
    state=7; finale_committed=true;
    ReleaseBbscNativeLeavingSession();assert(patches && suspended==0);
    finale_committed=false;
    // Native OwnWorldStep can be the only remaining callback during the load.
    for(int i=0;i<4000;++i) ReleaseBbscNativeLeavingSession();
    assert(!patches && suspended==1);
    state=0; ReleaseBbscNativeLeavingSession(); assert(suspended==1);
    bbsc_persistence_restore_at_ms=0; patches=true; state=3;
    ReleaseBbscNativeLeavingSession(); assert(patches);
    state=7; ReleaseBbscNativeLeavingSession(); assert(!patches && suspended==2);
    TestBlank();
}
'''
assert 'ReleaseBbscNativeLeavingSession();' in function('void TickBbscSessionExit(bool peer_work)')
assert 'site.offset == 0x01941C20' in function('bool BbscFunctionalTraceSite(const TraceSite& site)')
assert 'site.offset == 0x018C9364' in function('bool BbscFunctionalTraceSite(const TraceSite& site)')
trace = SOURCE[SOURCE.index('void PS4_SYSV_ABI TraceEntry('):]
own_step = trace[trace.index('if (site.offset == 0x01941C20)'):trace.index('if (site.offset == ItemUsableResultOffset)')]
assert 'ReleaseBbscNativeLeavingSession();' in own_step

with tempfile.TemporaryDirectory(prefix='bbsc-leave-') as tmp:
    cpp, exe = Path(tmp)/'test.cpp', Path(tmp)/'test.exe'
    cpp.write_text(code,encoding='utf-8')
    subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=5)
print('PASS: native state 7 releases once; successful local Blank, native precedence, fallback and load fence')
