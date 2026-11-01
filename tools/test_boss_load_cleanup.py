"""Exercise production pre-load boss cleanup ordering; no game or saves used."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')


def function(signature):
    start = SOURCE.index(signature + ' {')
    at = SOURCE.index('{', start) + 1
    depth = 1
    while depth:
        depth += (SOURCE[at] == '{') - (SOURCE[at] == '}')
        at += 1
    return SOURCE[start:at]


code = r'''
#include <array>
#include <cassert>
#include <cstdint>
#include <string_view>
using u8=uint8_t; using u32=uint32_t; using u64=uint64_t;
using s32=int32_t; using s64=int64_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
namespace MemoryProt { constexpr int CpuWrite=1; }
u64 image_base=0x100000, gauge=0x200000, rules=0x300000;
constexpr u64 BossGaugePointerOffset=0x10, SummonSessionRulesPointerOffset=0x18;
std::array<int,3> handles{1,2,3};
bool bbsc_boss_at_own_death=true;
s64 bbsc_boss_bar_seen_ms=100, bbsc_boss_killed_ms=50;
bool selected=true, writable=true, chalice_ready=true, valid=true;
bool bbsc_chalice_transition_owned=false;
int clears=0, transitions=0, notified=0;
u32 selected_map=24;
template<class T> T ReadValue(u64 p,size_t off) {
    if(p==image_base+BossGaugePointerOffset) return static_cast<T>(gauge);
    if(p==image_base+SummonSessionRulesPointerOffset) return static_cast<T>(rules);
    return static_cast<T>(off==0x0C ? selected_map : 0);
}
template<class T> void WriteValue(u64,size_t,T) {}
bool ReadablePointer(u64 p,size_t) { return p>=0x10000; }
bool HasMemoryAccess(u64,size_t,int) { return true; }
bool BossFightActive() { for(auto h:handles) if(h!=-1) return true; return false; }
void NativeClear() { ++clears; handles.fill(-1); }
void NotifyBbscHostDeathReload() { ++notified; }
struct SummonPlacementDescriptor { u32 packed_region=24; float x=0,y=0,z=0; };
namespace Chalice { bool IsMap(u32 map) { return map==29; } }
bool PrepareBbscChaliceLoad(u32) { return chalice_ready; }
void CancelBbscChaliceLoad() {}
bool IsUsablePackedMap(u32) { return valid; }
bool WriteTransportedSummonPlacement(u64,const SummonPlacementDescriptor&) { return writable; }
void StartBbscLoadCover(std::string_view) {}
void Placement(const void*) {}
void Flag() {}
bool Select(u64,s32) { return selected; }
u64 Transition() {
    assert(!BossFightActive());
    assert(!bbsc_boss_at_own_death && bbsc_boss_bar_seen_ms==0 && bbsc_boss_killed_ms==0);
    ++transitions; return 1;
}
u64 SetForcedSummonPositionOffset=reinterpret_cast<u64>(&Placement)-image_base;
u64 SetForcedSummonOrientationOffset=SetForcedSummonPositionOffset;
u64 SetForcedSummonMapOffset=SetForcedSummonPositionOffset;
u64 SetForcedSummonWarpOffset=reinterpret_cast<u64>(&Flag)-image_base;
u64 SelectSummonedPlacementOffset=reinterpret_cast<u64>(&Select)-image_base;
u64 StageTransitionOffset=reinterpret_cast<u64>(&Transition)-image_base;
u64 DeathReloadRequestOffset=StageTransitionOffset;
'''
# Redirect only the fixed native HUD address to the fixture's native reset.
code += function('void ClearBbscBossContext(std::string_view why)').replace(
    'image_base + 0x01336D00', 'reinterpret_cast<u64>(&NativeClear)')
code += '\n' + function('void RequestBbscDeathReload(std::string_view why)')
code += '\n' + function('bool RequestBbscSessionWarp(u64 global, const SummonPlacementDescriptor& to, std::string_view why)')
code += r'''
void arm() { handles={10,20,30}; bbsc_boss_at_own_death=true;
             bbsc_boss_bar_seen_ms=100; bbsc_boss_killed_ms=50; }
int main() {
    RequestBbscDeathReload("wipe");
    assert(clears==1 && transitions==1 && notified==1);
    arm(); SummonPlacementDescriptor to;
    selected=false;
    assert(!RequestBbscSessionWarp(0x400000,to,"wipe"));
    assert(clears==1 && BossFightActive()); // failed request preserves current encounter
    selected=true; selected_map=25;
    assert(!RequestBbscSessionWarp(0x400000,to,"wipe"));
    assert(clears==1 && BossFightActive());
    selected_map=24; writable=false;
    assert(!RequestBbscSessionWarp(0x400000,to,"wipe"));
    assert(clears==1 && BossFightActive());
    writable=true;
    assert(RequestBbscSessionWarp(0x400000,to,"wipe"));
    assert(clears==2 && transitions==2 && !bbsc_chalice_transition_owned);
    arm(); to.packed_region=29; chalice_ready=false;
    assert(!RequestBbscSessionWarp(0x400000,to,"wipe"));
    assert(clears==2 && BossFightActive());
    // New encounter after a completed request remains visible; no periodic suppression.
    handles={40,-1,-1}; assert(BossFightActive());
}
'''
home = function('void TickBbscStrandedGuest()')
assert home.index('ClearBbscBossContext("before return home")') < home.index(
    'reinterpret_cast<Transition>(image_base + 0x013CDE30)()')
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    (path / 'test.cpp').write_text(code, encoding='utf-8')
    subprocess.run([os.environ.get('CXX', 'g++'), '-std=c++20', str(path / 'test.cpp'),
                    '-o', str(path / 'test.exe')], check=True)
    subprocess.run([str(path / 'test.exe')], check=True)
print('boss load cleanup: native 3-slot reset, pre-transition ordering, rejected warps and new encounter PASS')
