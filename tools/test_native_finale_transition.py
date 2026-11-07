"""Run the channel 13 branch and exercise the actual BBSC finale transition code."""
import os
from pathlib import Path
import struct
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
core = root / 'emulator/src/core'
finale = (core / 'bbsc_native_finale.inc').read_text(encoding='utf-8')


def extract(start, end):
    return finale[finale.index(start):finale.index(end)]


source_file = (core / 'bloodborne_re.cpp').read_text(encoding='utf-8')
spawn = source_file.split('if (site.offset == 0x01938F65) {', 1)[1].split('if (site.offset ==', 1)[0]
assert 'DepartBbscNativeFinaleAtSpawn(registers->r13);' in spawn
assert 'if (GetSessionState() == 7 && !BbscNativeFinaleCommitted())' in source_file

elf = (root.parents[1] / 'out/exit-study.elf').read_bytes()
native_test = elf[0x1783681 + 0x4000:0x1783686 + 0x4000]
native_panic = elf[0x1783686 + 0x4000:0x178368B + 0x4000]
test_bytes = ','.join(map(str, native_test + native_panic))
source = r'''
#include <algorithm>
#include <atomic>
#include <cassert>
#include <map>
#include <mutex>
#include <optional>
#include <vector>
#include <windows.h>
#include "core/bbsc_dream_finale.h"
#include "core/bbsc_patch_tables.h"
using u8 = uint8_t;
using u32 = uint32_t;
using u64 = uint64_t;
using s32 = int32_t;
namespace Finale = Core::Bbsc::DreamFinale;
namespace World {
struct WorldId { u64 room = 0; auto operator<=>(const WorldId&) const = default; };
struct Presence { WorldId world{1}; Finale::Signal finale{}; };
}
namespace EventSteps { constexpr int Finale = 1; }
namespace Chalice { bool IsMap(u32 map) { return map == 0x1d000000; } }
#define BBSC_TIMELINE(...)
#define PS4_SYSV_ABI __attribute__((sysv_abi))
using FinalePhase = Finale::Phase;
constexpr u64 image_base = 0x100000, PlayerSlotManagerPointerOffset = 0x100;
constexpr u64 global = 0x200000, data = 0x300000, descriptor = 0x400000, event = 0x500000;
constexpr u64 task = 0x600000, manager = 0x700000, rules = 0x800000;
constexpr u64 MatchingStatePointerOffset = 0x110, SummonSessionRulesPointerOffset = 0x120;
std::map<u64, u64> memory;
template<class T> T ReadValue(u64 base, size_t offset) { return static_cast<T>(memory[base + offset]); }
template<class T> bool WriteValue(u64 base, size_t offset, T value) {
    if (!base) return false;
    memory[base + offset] = value;
    return true;
}
bool ReadablePointer(u64 p, size_t) { return p != 0; }
int role = 6;
u32 map = Finale::Map;
u64 room = 1;
int GetSessionState() { return role; }
u32 GetCurrentPackedMap() { return map; }
u64 GetGlobalState() { return global; }
u64 ReadBbscWorldRoom() { return room; }
int stops = 0, cleanups = 0;
u8 PS4_SYSV_ABI Stop(u64 ptr) {
    assert(ptr == manager && (role == 3 || role == 6));
    ++stops;
    role = 7;
    return 1;
}
const u64 MultiPlayStopRequestOffset = reinterpret_cast<u64>(Stop) - image_base;
void CleanupBbscDepartingRemotes() { assert(role == 7 || role == 0); ++cleanups; }
bool bbsc_recover_session_cleanup = false;
bool actor_ready = true;
bool PrepareBbscSharedFinaleActor() { return actor_ready; }
struct Range { int handlers = EventSteps::Finale; int64_t event = 0; } range;
const Range* LookupBbscQuestRange(u64) { return &range; }
enum class BbscWork { Finale };
void QueueBbscWork(BbscWork) {}
std::atomic<u32> bbsc_load_generation{7};
std::mutex bbsc_world_presence_mutex, bbsc_progress_mutex, bbsc_npc_own_mutex;
World::Presence bbsc_world_presence_local;
std::vector<int> bbsc_progress_host_flags, bbsc_progress_groups, bbsc_npc_own, bbsc_action_owner;
std::vector<int> bbsc_independent_states;
struct Scope {
    u32 map;
    auto operator<=>(const Scope&) const = default;
};
std::map<Scope, u64> bbsc_world_lamps, bbsc_world_lamp_pending;
std::optional<int> bbsc_progress_slot{1};
struct { bool valid = true; } bbsc_home_spot;
bool bbsc_guest_respawn_held = true;
int bbsc_host_time_bits = 64;
int restores = 0, world_clears = 0, pending_finishes = 0, trip_finishes = 0, memory_drops = 0;
void RestoreBbscOwnWorld(const char*, bool) { ++restores; }
void ClearBbscHostWorldSnapshots() { ++world_clears; }
void FinishBbscPendingProgress() { ++pending_finishes; }
void FinishBbscTripJournal(int) { ++trip_finishes; }
void DropBbscTripJournalMemory() { ++memory_drops; }
void BindBbscSharedLamp(World::WorldId) {}
void RetireBbscNativeFinaleCycle();
''' + extract('struct BbscNativeFinaleState', 'void ConsumeBbscFinaleDialog();') + extract(
    'bool BbscNativeFinaleCommitted()', 'bool BbscNativeFinaleWantsPresence()') + extract(
    'bool GuardBbscNativeFinaleCommand(', '// The original yes/no message') + r'''

void CheckReceive() {
    using namespace Core::Bbsc::PatchTables;
    const auto& patch = EntryJumps.back();
    assert(patch.site == 0x1783686 && patch.target == 0x1783590 && patch.group == Group::Stage);
    constexpr u8 branch[] = {''' + test_bytes + r'''};
    auto* code = static_cast<u8*>(VirtualAlloc(nullptr, 0x1000, MEM_COMMIT | MEM_RESERVE,
                                              PAGE_EXECUTE_READWRITE));
    assert(code);
    constexpr size_t base = 0x1783500, entry = 0x178367E - base;
    const u8 argument[] = {0x48, 0x89, 0xc8}; // Windows x64: move WorldChrMan argument into RAX
    std::copy_n(argument, 3, code + entry);
    std::copy_n(branch, sizeof branch, code + entry + 3);
    const u8 panic[] = {0xb8, 3, 0, 0, 0, 0xc3};
    const u8 ready[] = {0xb8, 2, 0, 0, 0, 0xc3};
    const u8 next[] = {0xb8, 1, 0, 0, 0, 0xc3};
    std::copy_n(panic, 6, code + 0x178368B - base);
    std::copy_n(ready, 6, code + 0x17836B1 - base);
    std::copy_n(next, 6, code + patch.target - base);
    const auto receive = reinterpret_cast<int(*)(u64)>(code + entry);
    assert(FlushInstructionCache(GetCurrentProcess(), code, 0x1000));
    assert(receive(0) == 3 && receive(1) == 2); // original reaches the panic only for null
    assert(std::equal(patch.prologue.begin(), patch.prologue.end(), code + patch.site - base));
    const auto jump = EncodeRel32(0xe9, patch.site, patch.target);
    std::copy(jump.begin(), jump.end(), code + patch.site - base);
    assert(FlushInstructionCache(GetCurrentProcess(), code, 0x1000));
    assert(receive(0) == 1 && receive(1) == 2);
    VirtualFree(code, 0, MEM_RELEASE);
}

int main() {
    CheckReceive();
    WriteValue(image_base, PlayerSlotManagerPointerOffset, data);
    WriteValue(image_base, MatchingStatePointerOffset, manager);
    WriteValue(image_base, SummonSessionRulesPointerOffset, rules);
    for (auto ending : {1, 2, 3}) {
        const auto& native = Finale::Events[ending - 1];
        range.event = native.id;
        role = 3;
        bbsc_native_finale = {};
        bbsc_native_finale.world = {1};
        bbsc_native_finale.signal = {FinalePhase::Recall, 1, 0};
        bbsc_native_finale.recall = 1;
        WriteValue(event, 0xA0, native.start);
        // A recall by itself cannot start the shared ending. Once the native
        // dialogue admitted the room, a later roster refresh is unnecessary.
        assert(!GuardBbscNativeFinaleCommand(event));
        assert(bbsc_native_finale.signal.phase == FinalePhase::Recall);
        bbsc_native_finale.dialogue = true;
        actor_ready = false;
        assert(GuardBbscNativeFinaleCommand(event));
        assert(bbsc_native_finale.signal.phase == FinalePhase::Recall);
        actor_ready = true;
        assert(!GuardBbscNativeFinaleCommand(event));
        assert((bbsc_native_finale.signal == Finale::Signal{FinalePhase::Play, 1,
                                                           static_cast<u8>(ending)}));
        assert(!bbsc_native_finale.dialogue);
        assert(!GuardBbscNativeFinaleCommand(event));

        role = 6;
        bbsc_native_finale = {};
        bbsc_native_finale.world = {1};
        bbsc_native_finale.selected = ending;
        bbsc_native_finale.recall = 1;
        bbsc_native_finale_committed = false;
        WriteValue(global, 0x1598, 1);
        WriteValue(global, 0x159C, ending == 3 ? 7 : 0);
        WriteValue(data, 0x68, 4); // host's cycle, used in the guest's borrowed world
        WriteValue(event, 0xA0, native.increment);
        assert(!GuardBbscNativeFinaleCommand(event));
        const auto previous = ReadValue<s32>(data, 0x68);
        assert(previous == (ending == 3 ? 7 : 0));
        const auto advanced = std::min(previous + 1, 7); // native 017C0FD2
        WriteValue(data, 0x68, advanced);
        assert(!GuardBbscNativeFinaleCommand(event));
        assert(ReadValue<s32>(data, 0x68) == advanced);
        WriteValue(event, 0xA0, native.commit);
        assert(GuardBbscNativeFinaleCommand(event) && !BbscNativeFinaleCommitted());
        bbsc_native_finale.released = true;
        assert(!GuardBbscNativeFinaleCommand(event) && BbscNativeFinaleCommitted());
        assert(role == 6 && restores == ending);

        WriteValue(descriptor, 8, 0x18010000);
        WriteValue(descriptor, 0x54, 8);
        WriteValue(descriptor, 0x58, 1);
        WriteValue(descriptor, 0x8C, previous);
        assert(!ApplyBbscNativeFinaleDescriptor(descriptor));
        assert(ReadValue<s32>(descriptor, 0x8C) == previous);
        WriteValue(descriptor, 0x58, 2);
        assert(ApplyBbscNativeFinaleDescriptor(descriptor));
        assert(ReadValue<s32>(descriptor, 0x8C) == advanced);
        WriteValue(data, 0x68, ReadValue<s32>(descriptor, 0x8C)); // native 01937D51

        bbsc_progress_groups = {1};
        bbsc_progress_host_flags = {2};
        bbsc_world_lamps = {{{0x18010000}, 1}, {{0x1d000000}, 2}};
        bbsc_world_lamp_pending = bbsc_world_lamps;
        bbsc_home_spot.valid = bbsc_guest_respawn_held = true;
        role = ending == 1 ? 3 : ending == 2 ? 6 : 0;
        WriteValue(task, 0x58, 0x18010000);
        WriteValue(task, 0xA4, 2);
        WriteValue(global, 0x1592, 1);
        DepartBbscNativeFinaleAtSpawn(task); // ordinary load
        WriteValue(task, 0xA4, 8);
        WriteValue(task, 0x58, Finale::Map);
        DepartBbscNativeFinaleAtSpawn(task); // wrong map
        WriteValue(task, 0x58, 0x18010000);
        WriteValue(global, 0x1592, 0);
        DepartBbscNativeFinaleAtSpawn(task); // still in the borrowed world
        WriteValue(global, 0x1592, 1);
        assert(!bbsc_native_finale.stopping);
        if (role != 0) {
            room = 2;
            DepartBbscNativeFinaleAtSpawn(task); // different live room
            assert(!bbsc_native_finale.stopping);
            room = 1;
        }
        WriteValue(rules, 0xF0, 0);
        DepartBbscNativeFinaleAtSpawn(task);
        DepartBbscNativeFinaleAtSpawn(task);
        assert(bbsc_recover_session_cleanup && BbscNativeFinaleCommitted());
        assert(stops == std::min(ending, 2) && cleanups == ending);
        assert(ReadValue<s32>(rules, 0xF0) == (ending == 3 ? 0 : 8));
        assert(world_clears == ending && trip_finishes == ending && pending_finishes == ending &&
               memory_drops == ending);
        assert(bbsc_progress_groups.empty() && bbsc_progress_host_flags.empty());
        assert(!bbsc_home_spot.valid && !bbsc_guest_respawn_held);
        assert(bbsc_world_lamps.size() == 1 && bbsc_world_lamp_pending == bbsc_world_lamps);
        assert(bbsc_world_lamps.contains({0x1d000000}));
        role = 0;
        map = 0x18010000;
        FinishBbscNativeFinaleLoad(); // room loss alone cannot finish the transition
        assert(BbscNativeFinaleCommitted());
        ++bbsc_load_generation;
        FinishBbscNativeFinaleLoad();
        assert(!BbscNativeFinaleCommitted());
        assert(!ApplyBbscNativeFinaleDescriptor(descriptor));
        assert(ReadValue<s32>(data, 0x68) == advanced);
        map = Finale::Map;
    }
}
'''

with tempfile.TemporaryDirectory() as tmp:
    cpp, exe = Path(tmp) / 'transition.cpp', Path(tmp) / 'transition.exe'
    cpp.write_text(source, encoding='utf-8')
    compiler = Path(os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe'))
    subprocess.run([str(compiler), '-std=c++20', '-I', str(core.parent), str(cpp), '-o', str(exe)],
                   check=True)
    env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ['PATH'])
    subprocess.run([str(exe)], check=True, env=env)
print('PASS: all three native endings, native cycle inputs, quiet-load departure gates and retirement')
