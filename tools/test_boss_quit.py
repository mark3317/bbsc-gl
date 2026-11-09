"""Exercise boss-clear departure gates, compatibility and delayed quit callbacks."""
import os
from pathlib import Path
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
source = (root / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
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
#ifdef BBSC_TEST_NATIVE_ADMISSION
void CheckNativeAdmission();
#endif
int main(){
#ifdef BBSC_TEST_NATIVE_ADMISSION
 CheckNativeAdmission();
#endif
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
if elf_path := os.environ.get('BBSC_TEST_EBOOT'):
    elf = Path(elf_path).read_bytes()
    assert elf[:4] == b'\x7fELF'

    def native_bytes(start, end):
        return ','.join(map(str, elf[start + 0x4000:end + 0x4000]))

    code = '#define BBSC_TEST_NATIVE_ADMISSION\n' + code + r'''
#include <windows.h>
#include <algorithm>
#include "core/bbsc_patch_tables.h"

void CheckNativeAdmission() {
    using Core::Bbsc::PersistNoOpOffset;
    using namespace Core::Bbsc::PatchTables;
    const auto patch = std::find_if(Retargets.begin(), Retargets.end(), [](const auto& site) {
        return site.site == 0x01384B89;
    });
    assert(patch != Retargets.end() && patch->group == Group::Spectate);
    assert(patch->original == 0x0178D7B0 && patch->target == PersistNoOpOffset);

    constexpr u64 gate = 0x01ED121E, allowed = 0x01ED122D, kicked = 0x01ED14F1;
    constexpr size_t size = 0x01ED2000;
    auto* image = static_cast<u8*>(VirtualAlloc(nullptr, size, MEM_COMMIT | MEM_RESERVE,
                                               PAGE_EXECUTE_READWRITE));
    assert(image);
    const auto put = [&](u64 at, std::initializer_list<u8> bytes) {
        std::copy(bytes.begin(), bytes.end(), image + at);
    };
    // Windows ABI bridges. Keep the original victory call, latch write and admission branch.
    put(patch->site - 3, {0x48, 0x89, 0xc8}); // RAX = session
    put(patch->site, {VICTORY_CALL});
    put(patch->site + 5, {0xc3});
    put(0x0178D7B0, {LATCH_WRITE, 0xc3});
    put(PersistNoOpOffset, {NO_OP});
    put(gate - 5, {0x41, 0x54, 0x49, 0x89, 0xcc}); // save R12, R12 = session
    put(gate, {ADMISSION_BRANCH});
    put(allowed, {0x31, 0xc0, 0x41, 0x5c, 0xc3});
    put(kicked, {0xb8, 1, 0, 0, 0, 0x41, 0x5c, 0xc3});
    const auto original = EncodeRel32(patch->opcode, patch->site, patch->original);
    assert(std::equal(original.begin(), original.end(), image + patch->site));
    assert(FlushInstructionCache(GetCurrentProcess(), image, size));

    u8 session[0x119]{};
    const auto victory = reinterpret_cast<void(*)(u8*)>(image + patch->site - 3);
    const auto refused = reinterpret_cast<int(*)(u8*)>(image + gate - 5);
    assert(!refused(session));
    victory(session);
    assert(session[0x118] == 1 && refused(session));

    const auto keep_open = EncodeRel32(patch->opcode, patch->site, patch->target);
    std::copy(keep_open.begin(), keep_open.end(), image + patch->site);
    assert(FlushInstructionCache(GetCurrentProcess(), image + patch->site, keep_open.size()));
    session[0x118] = 0;
    victory(session);
    assert(session[0x118] == 0 && !refused(session));
    session[0x118] = 1; // A different caller can still close admission.
    assert(refused(session));
    assert(VirtualFree(image, 0, MEM_RELEASE));
}
'''.replace('VICTORY_CALL', native_bytes(0x01384B89, 0x01384B8E)).replace(
        'LATCH_WRITE', native_bytes(0x0178D7F8, 0x0178D7FF)).replace(
        'NO_OP', native_bytes(0x013001E0, 0x013001E1)).replace(
        'ADMISSION_BRANCH', native_bytes(0x01ED121E, 0x01ED122D))
with tempfile.TemporaryDirectory() as d:
 p=Path(d); (p/'test.cpp').write_text(code, encoding='utf-8')
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-I',str(root/'emulator/src'),str(p/'test.cpp'),'-o',str(p/'test.exe')],check=True)
 subprocess.run([str(p/'test.exe')],check=True,timeout=15)
print('Production boss clear: scoped departure gates, one-shot compatibility and late quit PASS')
if elf_path:
    print('Native 1.09: victory reproduces the admission kick, patched victory keeps admission open PASS')
