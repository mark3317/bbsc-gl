"""Execute the 1.09 resource copy and request with the production spectator hook."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
elf = Path(sys.argv[1]).read_bytes()[0x4000:]
state = source[source.index('struct BbscWatchState {'):source.index('constexpr float BbscWatchHeadHeight')]
hook = source[source.index('void PS4_SYSV_ABI BbscWatchResourcesHook('):source.index('void InstallBbscCinematicHook()')]

# Wrap the original instruction spans in callable functions with their native
# input registers. The middle fragment is the original one-pass request setter.
copy_start = 0x154A3D9
assert elf[copy_start:copy_start + 5] == bytes.fromhex('be f8 03 00 00')
copy_groups = bytes.fromhex('53 49 89 f8 89 d1 48 89 f2') + elf[copy_start:0x154A44D] + b'\x5b\xc3'
request_block = elf[0x1565D70:0x1565D96]
consume_request = (bytes.fromhex('41 57 41 89 f7 48 89 f9') + elf[0x15656B6:0x15656D8]
                   + bytes.fromhex('41 5f c3'))

code = r'''
#include <windows.h>
#include <algorithm>
#include <atomic>
#include <cassert>
#include <cstring>
#include "core/cpu_patches.h"

using Core::GuestRegisterSnapshot;
u64 image_base;
constexpr u64 CandidateLocalStatePointerOffset = 0x0553E878;
enum class BbscDeathMode : u8 { Spectate, RespawnNow };
BbscDeathMode bbsc_death_mode = BbscDeathMode::Spectate;
bool bbsc_spectate_active = true;
u32 bbsc_spectate_load_generation = 1;
std::atomic<u32> bbsc_load_generation{1};
std::array<u8, 0x10> global;
s32 session = 3;
s32 local_hp = 0;

namespace BbscMod {
u64 EbootAddress() { return image_base; }
void LogPlain(const char*) {}
}

bool ReadablePointer(u64 address, size_t) { return address >= 0x10000; }
template<class T> T ReadValue(u64 address, size_t offset) {
    T value{};
    if (ReadablePointer(address, offset + sizeof(value))) {
        std::memcpy(&value, reinterpret_cast<const void*>(address + offset), sizeof(value));
    }
    return value;
}
template<class T> void Write(u64 address, size_t offset, T value) {
    std::memcpy(reinterpret_cast<void*>(address + offset), &value, sizeof(value));
}
u64 GetGlobalState() { return reinterpret_cast<u64>(global.data()); }
s32 GetSessionState() { return session; }
s32 GetCharacterHp(u64) { return local_hp; }
''' + state + hook + r'''
using Mask = std::array<u64, 4>;
constexpr size_t Stride = 0x420;
constexpr s32 Count = 3;

struct Hunter {
    std::array<u8, 0x3B8> character{};
    std::array<u8, 0x116> control{};
    std::array<u8, 0x28> modules{};
    std::array<u8, 0x38> data{};
    std::array<u8, 0x2C> floor{};

    u64 Address() const { return reinterpret_cast<u64>(character.data()); }

    void Init(s32 block, Mask mask) {
        Write(Address(), 0x58, reinterpret_cast<u64>(control.data()));
        Write(Address(), 0x238, mask);
        Write(Address(), 0x288, reinterpret_cast<u64>(floor.data()));
        Write(Address(), 0x3B0, reinterpret_cast<u64>(modules.data()));
        Write(reinterpret_cast<u64>(modules.data()), 0x20, reinterpret_cast<u64>(data.data()));
        Write(reinterpret_cast<u64>(data.data()), 0x34, block);
    }
};

int main() {
    image_base = reinterpret_cast<u64>(VirtualAlloc(nullptr, 0x6000000, MEM_RESERVE | MEM_COMMIT,
                                                    PAGE_EXECUTE_READWRITE));
    assert(image_base);
    const u8 copy_code[] = {COPY_GROUPS};
    const u8 request_code[] = {REQUEST_BLOCK};
    const u8 consume_code[] = {CONSUME_REQUEST};
    const u64 copy_entry = image_base + 0x154A3D9 - 9;
    const u64 consume_entry = image_base + 0x15656B6 - 8;
    std::memcpy(reinterpret_cast<void*>(copy_entry), copy_code, sizeof(copy_code));
    std::memcpy(reinterpret_cast<void*>(image_base + 0x1565D70), request_code, sizeof(request_code));
    std::memcpy(reinterpret_cast<void*>(consume_entry), consume_code, sizeof(consume_code));
    const std::array<u8, 5> expected{0xBE, 0xF8, 0x03, 0x00, 0x00};
    assert(Core::InstallGuestCodeHook(reinterpret_cast<void*>(image_base + 0x154A3D9),
                                      expected, 0, BbscWatchResourcesHook));
    using CopyGroups = void PS4_SYSV_ABI (*)(u64, const Mask*, s32);
    using ConsumeRequest = void PS4_SYSV_ABI (*)(u64, s32);
    const auto copy = reinterpret_cast<CopyGroups>(copy_entry);
    const auto consume = reinterpret_cast<ConsumeRequest>(consume_entry);

    std::array<u8, 0x68> world{};
    std::array<u8, 0x38 * Count> roster{};
    std::array<u8, 0x2B38 + 8> manager{};
    std::array<u8, Stride * Count> resources{};
    std::array<u8, 0x28> visual_consumer{};
    const u64 resource_table = reinterpret_cast<u64>(resources.data());
    const u64 map_manager = reinterpret_cast<u64>(manager.data());
    const u64 world_manager = reinterpret_cast<u64>(world.data());
    const u64 roster_table = reinterpret_cast<u64>(roster.data());
    const u64 visual = reinterpret_cast<u64>(visual_consumer.data());
    Write(image_base, CandidateLocalStatePointerOffset, world_manager);
    Write(world_manager, 0x30, Count);
    Write(world_manager, 0x38, roster_table);
    Write(world_manager, 0x60, u64{0x10000});
    Write(map_manager, 0x2B30, Count);
    Write(map_manager, 0x2B38, resource_table);
    Write(resource_table, Stride + 0x3F8, visual);

    Hunter first, second;
    first.Init(1, {8, 16, 32, 64});
    second.Init(-1, {128, 256, 512, 1024});
    Write(reinterpret_cast<u64>(second.floor.data()), 0x2B, s8{2});
    Write(roster_table, 0x38, first.Address());
    Write(roster_table, 0x70, second.Address());

    const std::array<Mask, Count> local{{{1, 2, 4, 8}, {2, 4, 8, 16}, {4, 8, 16, 32}}};
    auto masks = local;
    auto verify = [&](s32 watched = -1, Mask expected_mask = {}) {
        copy(map_manager, masks.data(), Count);
        assert(masks == local); // the subsequent gameplay consumers still read this input
        for (s32 block = 0; block < Count; ++block) {
            const u64 offset = block * Stride;
            const auto expected = block == watched ? expected_mask : local[block];
            assert(ReadValue<Mask>(resource_table, offset + 0x20) == expected);
            assert(ReadValue<u8>(resource_table, offset + 0xC1) == (block == watched));
        }
        assert(ReadValue<Mask>(visual, 8) == (watched == 1 ? expected_mask : local[1]));
        consume(resource_table, Count);
        for (s32 block = 0; block < Count; ++block) {
            const u64 offset = block * Stride;
            assert(ReadValue<u8>(resource_table, offset + 0xC1) == 0);
            assert(ReadValue<u8>(resource_table, offset + 0xC2) == (block == watched));
            Write(resource_table, offset + 0xC2, u8{0}); // normal selection on the next pass
        }
    };
    verify();
    bbsc_watch.target = first.Address();
    bbsc_watch.stream_slot = 1;
    verify(1, {10, 20, 40, 80});
    bbsc_watch.target = second.Address();
    bbsc_watch.stream_slot = 2;
    session = 6;
    verify(2, {132, 264, 528, 1056});

    Write(reinterpret_cast<u64>(second.data.data()), 0x34, s32{0});
    verify(0, {129, 258, 516, 1032});
    Write(second.Address(), 0x238, Mask{});
    verify(0, local[0]); // native residency request still works without extra groups
    Write(reinterpret_cast<u64>(second.data.data()), 0x34, Count);
    verify();
    Write(reinterpret_cast<u64>(second.data.data()), 0x34, s32{0});

    Write(roster_table, 0x70, first.Address());
    verify();
    Write(roster_table, 0x70, second.Address());
    Write(reinterpret_cast<u64>(second.control.data()), 0x114, u16{1});
    verify();
    Write(reinterpret_cast<u64>(second.control.data()), 0x114, u16{0});
    global[8] = 1;
    verify();
    global[8] = 0;
    ++bbsc_load_generation;
    verify();
    ++bbsc_spectate_load_generation;
    local_hp = 1;
    verify();
    local_hp = 0;
    bbsc_death_mode = BbscDeathMode::RespawnNow;
    verify();
    bbsc_death_mode = BbscDeathMode::Spectate;
    bbsc_watch.stream_slot = -1;
    verify();
    bbsc_watch.stream_slot = 2;
    bbsc_spectate_active = false;
    verify();

    VirtualFree(reinterpret_cast<void*>(image_base), 0, MEM_RELEASE);
}
'''

for label, blob in (('COPY_GROUPS', copy_groups), ('REQUEST_BLOCK', request_block),
                    ('CONSUME_REQUEST', consume_request)):
    code = code.replace(label, ','.join(map(str, blob)))

cxx = Path('C:/msys64/clang64/bin/clang++.exe')
with tempfile.TemporaryDirectory(prefix='bbsc-spectator-resources-') as temporary:
    cpp = Path(temporary) / 'fixture.cpp'
    exe = cpp.with_suffix('.exe')
    cpp.write_text(code, encoding='utf-8')
    subprocess.run([str(cxx), '-std=c++20', '-O2', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
                    '-I', str(ROOT / 'emulator/src'), '-I', str(ROOT / 'emulator/externals/xbyak'),
                    str(cpp), str(ROOT / 'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe)], check=True)
    env = dict(os.environ, PATH=str(cxx.parent) + os.pathsep + os.environ.get('PATH', ''))
    subprocess.run([str(exe)], env=env, check=True, timeout=15)

print('PASS native resource masks and one-pass block request, target switch, and local fallback')
