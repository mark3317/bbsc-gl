"""Run the boss wipe reset with the original flag writer and EMEVD."""
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/gamedata'))
from emevd import Emevd

SOURCE = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
RULES = (ROOT / 'emulator/src/core/bbsc_boss_retry.h').read_text(encoding='utf-8')
EVENTS = Path(sys.argv[1]) / 'event'


def function(signature):
    start = SOURCE.index(signature + ' {')
    end = SOURCE.index('{', start) + 1
    depth = 1
    while depth:
        depth += (SOURCE[end] == '{') - (SOURCE[end] == '}')
        end += 1
    return SOURCE[start:end] + '\n'


def words(args):
    return struct.unpack('<' + 'I' * (len(args) // 4), args)


gauges = set()
for path in EVENTS.glob('m*_00_00.emevd.dcx'):
    area, block = map(int, path.name[1:6].split('_'))
    if area == 29:
        continue
    for event, instructions in Emevd(path).events:
        if event < 10_000_000:
            continue
        for bank, opcode, args in instructions:
            if (bank, opcode) == (2003, 11) and words(args)[0] == 1:
                gauges.add((area << 24 | block << 16, words(args)[3]))
arena_rows = re.findall(r'\{(0x\w+),\s+\d+,\s+\d+,\s+\d+, \{([\d, ]+)\}', RULES)
assert len(arena_rows) == 22
assert gauges <= {(int(packed, 16), int(name)) for packed, names in arena_rows
                  for name in names.split(',')}

def initializers(path):
    return [words(args) for bank, opcode, args in dict(Emevd(path).events).get(0, [])
            if (bank, opcode) == (2000, 0)]


parts = sorted(EVENTS.rglob('m29_*.emevd.dcx'))
regular_arenas = 0
for path in parts:
    inits = initializers(path)
    starts = {(init[4], init[6]) for init in inits if init[1] == 12906802}
    setups = {(init[4], init[5]) for init in inits if init[1] in (12906795, 12906806)}
    assert starts <= setups, path
    regular_arenas += sum(init[1] == 12906802 for init in inits)
assert len(parts) == 2641 and regular_arenas == 8485

watchers = initializers(next(EVENTS.rglob('m29_30_90_00.emevd.dcx')))
watchers = [init for init in watchers if init[1] in (12906795, 12906802) and init[4] == 12901800]
assert len(watchers) == 2

events = dict(Emevd(EVENTS / 'm24_00_00_00.emevd.dcx').events)
actor = 2400800
start = events[12404802]
assert start[1] == (2004, 1, struct.pack('<II', actor, 0))
assert start[4] == (3, 0, struct.pack('<II', 0x100, 12404800))
assert start[6] == (1003, 1, struct.pack('<II', 0x101, 12404223))
assert start[28] == (2004, 1, struct.pack('<II', actor, 1))
assert events[12404841][17] == (2003, 2, struct.pack('<II', 12404801, 1))
assert events[12404840][1] == (1003, 101, struct.pack('<II', 0x100, 12401802))

mensis = dict(Emevd(Path(sys.argv[1]) / 'event/m26_00_00_00.emevd.dcx').events)
setup = mensis[12604852]
assert setup[3:5] == [(1003, 101, struct.pack('<II', 0x10100, 0)),
                     (3, 0, struct.pack('<II', 0x100, 12604850))]
assert mensis[12604861][17] == (2003, 2, struct.pack('<II', 12604851, 1))
phase = mensis[12604856]
assert phase[2] == (1003, 101, struct.pack('<II', 0x10100, 0))
assert phase[6] == (3, 0, struct.pack('<II', 0x100, 12604986))
assert phase[10] == (1014, 0, b'')
assert phase[13] == (2003, 22, struct.pack('<III', 12604949, 12604959, 0))
assert phase[17] == (2005, 3, struct.pack('<II', 2601851, 0))
assert mensis[12604877][13] == (2003, 22, struct.pack('<III', 12604940, 12604946, 0))
assert mensis[12604986][3] == (2003, 8, struct.pack('<III', 12604985, 0, 0))

ludwig = dict(Emevd(Path(sys.argv[1]) / 'event/m34_00_00_00.emevd.dcx').events)
assert ludwig[13404802][10] == (3, 0, struct.pack('<II', 0x100, 13404808))
assert ludwig[13404801][16] == (2003, 2, struct.pack('<II', 13404809, 1))
phase = ludwig[13404825]
assert phase[0:4] == [(1003, 2, struct.pack('<II', 0x100, 9471)),
                      (1003, 101, struct.pack('<II', 0x10000, 0)),
                      (2004, 5, struct.pack('<II', 3400800, 0)),
                      (1000, 4, bytes(4))]
assert phase[8] == (3, 0, struct.pack('<II', 0x101, 13404824))
assert ludwig[13404802][39] == (1003, 1, struct.pack('<II', 0x105, 13404825))
for event in range(13404820, 13404824):
    assert (2004, 17, struct.pack('<III', 3400800, 100 + event - 13404820, 0)) in ludwig[event]
    if event > 13404820:
        assert ludwig[event][9] == (3, 0, struct.pack('<II', 0x103, event - 1))

with Path(sys.argv[2]).open('rb') as elf:
    elf.seek(0x4000 + 0x013CFCC0)
    writer = elf.read(0xB1)
assert writer[:6] == bytes.fromhex('41 89 d0 8b 4f 1c') and writer[-1] == 0xC3

code = r'''
#define NOMINMAX
#include <windows.h>
#include <atomic>
#include <cassert>
#include <mutex>
#include "core/bbsc_boss_retry.h"
#include "core/bbsc_world_control.h"
namespace World = Core::Bloodborne::World;
namespace Chalice = Core::Bloodborne::Chalice;
namespace BossRetry = Core::Bloodborne::BossRetry;
using u8=uint8_t; using u32=uint32_t; using u64=uint64_t; using s32=int32_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define BBSC_TIMELINE(...)
std::mutex bbsc_world_presence_mutex;
World::Presence bbsc_world_presence_local;
std::atomic<u64> bbsc_world_native_load{1};
std::atomic<u32> bbsc_load_generation{1};
u64 GetLocalPlayerCharacter(){return 1;}
s32 layer_lamp=-1;
s32 BbscChaliceLayerFirstLamp(u64){return layer_lamp;}
constexpr u64 EventFlagManPointerOffset=0x0553B100;
u64 image_base;
bool ReadablePointer(u64 p,size_t) { return p != 0; }
template<class T> T ReadValue(u64 p,size_t off) {
    T value; std::memcpy(&value,(const void*)(p+off),sizeof(value)); return value;
}
void Store(u64 p,size_t off,auto value) { std::memcpy((void*)(p+off),&value,sizeof(value)); }
std::array<u8,125> progress,attempt;
u32 attempt_group=12404;
void SetFixtureFlag(std::array<u8,125>& bank,u32 flag) {
    bank[flag%1000/8] |= 0x80 >> (flag%8);
}
bool BbscEventFlag(u32 flag) {
    const auto& bank=flag/1000==attempt_group?attempt:progress;
    return (bank[flag%1000/8] & (0x80 >> (flag%8))) != 0;
}
'''
code += SOURCE[SOURCE.index('World::Scope bbsc_boss_wipe_scope{};'):
               SOURCE.index('std::atomic<u64> bbsc_world_load_pending')]
array_name = SOURCE.index('BbscEncounterProgressFlags{')
code += SOURCE[SOURCE.rindex('constexpr std::array<', 0, array_name):
               SOURCE.index('bool BbscSharedMapProgressAllowed(')]
code += r'''
using s64=int64_t;
struct BbscQuestRange { u64 first, end; };
World::Scope bbsc_world_bootstrap_scope;
u64 bbsc_world_bootstrap_load;
'''
code += function('void RememberBbscChaliceBossInit(u64 instance, const BbscQuestRange& range)')
code += r'''
int main() {
    image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);
    assert(image_base);
    const u8 writer[]={NATIVE_WRITER};
    std::memcpy((void*)(image_base+0x013CFCC0),writer,sizeof(writer));
    std::array<u8,0x40> manager{},head{},node{};
    Store(image_base,EventFlagManPointerOffset,(u64)manager.data());
    Store((u64)manager.data(),0x1c,1000u);
    Store((u64)manager.data(),0x38,(u64)head.data());
    head[0x19]=1;
    Store((u64)head.data(),8,(u64)node.data());
    Store((u64)node.data(),0,(u64)head.data());
    Store((u64)node.data(),0x10,(u64)head.data());
    Store((u64)node.data(),0x20,12404u);
    Store((u64)node.data(),0x28,2u);
    Store((u64)node.data(),0x30,(u64)attempt.data());
    attempt[27]=3; attempt[100]=0xf0;
    progress[100]=0x20;
    auto& local=bbsc_world_presence_local;
    local.world={11,99}; local.map=0x18000000;
    bbsc_encounter_map=local.map; bbsc_encounter_load_generation=1; bbsc_encounter_name=502000;
    MarkBbscBossWipeLoad();
    ResetBbscWipeEncounterAtSpawn(local.map); // still on the dying visit
    ++bbsc_world_native_load;
    ResetBbscWipeEncounterAtSpawn(0x18010000); // a different destination
    ++local.world.room;
    ResetBbscWipeEncounterAtSpawn(local.map); // another room
    --local.world.room;
    assert(attempt[27]==3 && attempt[100]==0xf0);
    ResetBbscWipeEncounterAtSpawn(local.map);
    assert(attempt[27]==2 && attempt[100]==0x10);
    assert(!BbscEventFlag(12401800) && BbscEventFlag(12401802));
    ++bbsc_world_native_load;
    attempt[100]=0xe0;
    ResetBbscWipeEncounterAtSpawn(local.map); // later ordinary arrival
    assert(attempt[100]==0xe0);

    local.map=0x1a000000;
    bbsc_encounter_map=local.map; bbsc_encounter_name=899000;
    attempt_group=12604;
    Store((u64)node.data(),0x20,attempt_group);
    attempt.fill(0);
    progress.fill(0);
    SetFixtureFlag(progress,12601852); // Micolash's introduction
    SetFixtureFlag(attempt,12604800); // Wet Nurse arena
    SetFixtureFlag(attempt,12604960); // neighbouring event
    constexpr std::array micolash_flags{
        12604850u,12604851u,12604852u,12604856u,
        12604940u,12604941u,12604942u,12604943u,12604944u,12604945u,12604946u,
        12604949u,12604950u,12604951u,12604952u,12604953u,12604954u,12604955u,
        12604956u,12604957u,12604958u,12604959u,12604985u,12604986u,
    };
    for (u32 flag : micolash_flags) SetFixtureFlag(attempt,flag);
    const auto previous_attempt=attempt;
    ResetBbscWipeEncounterAtSpawn(local.map); // no wipe in this map yet
    MarkBbscBossWipeLoad();
    ++bbsc_world_native_load;
    ResetBbscWipeEncounterAtSpawn(0x18000000); // another destination
    assert(attempt==previous_attempt);

    ResetBbscWipeEncounterAtSpawn(local.map);
    for (u32 flag : micolash_flags) assert(!BbscEventFlag(flag));
    assert(BbscEventFlag(12601852) && BbscEventFlag(12604800) && BbscEventFlag(12604960));

    auto stale_snapshot=previous_attempt;
    KeepBbscEncounterFlags(World::ScopeOf(local),attempt_group,attempt.data(),stale_snapshot.data());
    assert(stale_snapshot==attempt);

    attempt=previous_attempt;
    SetFixtureFlag(progress,12601850);
    MarkBbscBossWipeLoad(); // a later wipe in Mensis after Micolash is defeated
    ++bbsc_world_native_load;
    ResetBbscWipeEncounterAtSpawn(local.map);
    assert(attempt==previous_attempt && BbscEventFlag(12601850));

    local.map=0x22000000;
    bbsc_encounter_map=local.map; bbsc_encounter_name=451005;
    attempt_group=13404;
    Store((u64)node.data(),0x20,attempt_group);
    attempt.fill(0);
    progress.fill(0);
    SetFixtureFlag(progress,13401800); // guest's local completion can be stale
    SetFixtureFlag(progress,13401801); // first encounter
    SetFixtureFlag(attempt,13404811); // completed approach
    SetFixtureFlag(attempt,13404852); // Laurence
    SetFixtureFlag(attempt,13404858);
    constexpr std::array ludwig_flags{13404802u,13404808u,13404809u,13404820u,13404821u,
                                      13404822u,13404823u,13404824u,13404825u};
    for (u32 flag : ludwig_flags) SetFixtureFlag(attempt,flag);
    const auto old_ludwig_attempt=attempt;
    ResetBbscWipeEncounterAtSpawn(local.map);
    assert(attempt==old_ludwig_attempt);
    MarkBbscBossWipeLoad();
    ++bbsc_world_native_load;
    ResetBbscWipeEncounterAtSpawn(local.map);
    for (u32 flag : ludwig_flags) assert(!BbscEventFlag(flag));
    assert(BbscEventFlag(13401800) && BbscEventFlag(13401801) && BbscEventFlag(13404811));
    assert(BbscEventFlag(13404852) && BbscEventFlag(13404858));
    stale_snapshot=old_ludwig_attempt;
    KeepBbscEncounterFlags(World::ScopeOf(local),attempt_group,attempt.data(),stale_snapshot.data());
    assert(stale_snapshot==attempt);
    attempt=old_ludwig_attempt;
    SetFixtureFlag(progress,9471);
    MarkBbscBossWipeLoad();
    ++bbsc_world_native_load;
    ResetBbscWipeEncounterAtSpawn(local.map);
    assert(attempt==old_ludwig_attempt && BbscEventFlag(9471));

    // Phase 2 Gascoigne may share the map with an undefeated Cleric Beast.
    local.map=0x18010000;
    bbsc_encounter_map=local.map; bbsc_encounter_name=272000;
    attempt_group=12414;
    Store((u64)node.data(),0x20,attempt_group);
    progress.fill(0);
    attempt.fill(0);
    SetFixtureFlag(attempt,12414700);
    SetFixtureFlag(attempt,12414801);
    SetFixtureFlag(attempt,12414807);
    MarkBbscBossWipeLoad();
    ++bbsc_world_native_load;
    ResetBbscWipeEncounterAtSpawn(local.map);
    assert(BbscEventFlag(12414700) && !BbscEventFlag(12414801) && !BbscEventFlag(12414807));

    // Real Watchers constructor in the failed cup. Keep progress in this
    // ritual and every other layer, even when a late old snapshot arrives.
    local.map=0x1d000000;
    local.dungeon={12,34,56,0}; local.ritual=28;
    bbsc_encounter_map=local.map; bbsc_encounter_name=304003;
    layer_lamp=2902951;
    constexpr auto watcher=BossRetry::ReadChaliceInit(
        std::array{0u,12906795u,2900102u,304001u,12901800u,12905502u,12905504u,2900104u,2900106u});
    constexpr auto guest=BossRetry::ReadChaliceInit(
        std::array{0u,12906802u,2903071u,2901034u,12901800u,12900532u,12905502u,12905503u});
    static_assert(watcher.victory==12901800 && watcher.flags[2]==12906795);
    static_assert(guest.victory==12901800 && guest.flags[0]==12905502 &&
                  guest.flags[1]==12905503 && guest.flags[2]==12906802);
    constexpr auto side=BossRetry::ReadChaliceInit(
        std::array{1u,12906791u,2900250u,216000u,12900680u,12905650u,12905670u});
    static_assert(side.victory==12900680 && side.name==216000 &&
                  side.flags[0]==12905650 && side.flags[1]==12905670 && side.flags[2]==12906792);
    constexpr auto special=BossRetry::ReadChaliceInit(
        std::array{3u,12906806u,2900105u,1010u,12901801u,12905600u,12900537u});
    static_assert(special.victory==12901801 && special.flags[0]==12905600 &&
                  special.flags[1]==12906809 && special.flags[2]==0);
    auto& cup=bbsc_chalice_boss_attempts;
    bbsc_world_bootstrap_scope=World::ScopeOf(local);
    bbsc_world_bootstrap_load=bbsc_world_native_load.load();
    std::array<u8,0xB0> file{};
    std::array<u8,0xC0> instance{};
    std::array<u8,0x20> pc{};
    const u64 file_at=(u64)file.data(), pc_at=(u64)pc.data(), instance_at=(u64)instance.data();
    const std::array<u64,2> ref{0,file_at};
    Store(instance_at,0xA8,(u64)ref.data());
    Store(instance_at,0xB0,pc_at);
    Store(pc_at,0,2000);
    Store(file_at,0x70,u64{40});
    Store(file_at,0x78,u64{0x80});
    const auto capture = [&](const auto& native_args) {
        Store(pc_at,8,(u64)(native_args.size() * sizeof(u32)));
        std::memcpy(file.data()+0x80,native_args.data(),native_args.size()*sizeof(u32));
        RememberBbscChaliceBossInit(instance_at,{pc_at,pc_at+0x20});
    };
    std::apply([&](const auto&... args) { (capture(args), ...); }, WATCHERS_CTORS);
    assert(cup.scope==World::ScopeOf(local) && cup.arenas[0].flags.size()==5);
    cup.arenas[1]={{12905509,12906806,12906802},{216000}};
    attempt_group=12905;
    Store((u64)node.data(),0x20,attempt_group);
    progress.fill(0); attempt.fill(0);
    SetFixtureFlag(progress,12901801);
    SetFixtureFlag(progress,12900532);
    for (u32 flag : {12905502u,12905503u,12905504u,12905509u}) SetFixtureFlag(attempt,flag);
    const auto old_cup_attempt=attempt;
    MarkBbscBossWipeLoad();
    assert(std::ranges::find(bbsc_boss_wipe_attempt.flags,12906802u) ==
           bbsc_boss_wipe_attempt.flags.end());
    ++bbsc_world_native_load;
    ResetBbscWipeEncounterAtSpawn(local.map); // the ritual is mounted at admission
    auto wrong_ritual=World::ScopeOf(local);
    ++wrong_ritual.ritual;
    ResetBbscWipeEncounter(wrong_ritual);
    assert(attempt==old_cup_attempt);
    ResetBbscWipeEncounter(World::ScopeOf(local));
    assert(!BbscEventFlag(12905502) && !BbscEventFlag(12905503) && !BbscEventFlag(12905504));
    assert(BbscEventFlag(12905509) && BbscEventFlag(12901801) && BbscEventFlag(12900532));
    auto incoming=old_cup_attempt;
    KeepBbscEncounterFlags(wrong_ritual,attempt_group,attempt.data(),incoming.data());
    assert(incoming==old_cup_attempt);
    KeepBbscEncounterFlags(World::ScopeOf(local),attempt_group,attempt.data(),incoming.data());
    assert(incoming==attempt);
    SetFixtureFlag(attempt,12905502); // a new native attempt has legitimately started
    ResetBbscWipeEncounter(World::ScopeOf(local)); // re-admission on the same load
    assert(BbscEventFlag(12905502));
    incoming.fill(0);
    KeepBbscEncounterFlags(World::ScopeOf(local),attempt_group,attempt.data(),incoming.data());
    assert((incoming[502/8] & (0x80 >> (502%8))) != 0);
}
'''.replace('NATIVE_WRITER', ','.join(map(str, writer))).replace(
    'WATCHERS_CTORS', 'std::tuple{' + ','.join(
        'std::array{' + ','.join(f'{word}u' for word in init) + '}' for init in watchers) + '}')

with tempfile.TemporaryDirectory(prefix='bbsc-wipe-flags-') as tmp:
    cpp, exe = Path(tmp) / 'wipe.cpp', Path(tmp) / 'wipe.exe'
    cpp.write_text(code, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    env = dict(os.environ, PATH=str(Path(compiler).parent) + os.pathsep + os.environ['PATH'])
    subprocess.run([compiler, '-std=c++20', '-I', str(ROOT / 'emulator/src'), str(cpp),
                    '-o', str(exe)], check=True, env=env)
    subprocess.run([str(exe)], check=True, env=env)
print('PASS original EMEVD and native SetFlag: story and Chalice wipes, stale snapshots, and scoped permanent progress')
