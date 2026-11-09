"""Exercise the original 1.09 INFE serializer and the production join apply hook."""

import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'emulator/src/core'
ELF = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parents[1] / 'out/exit-study.elf'
data = ELF.read_bytes()
ph = struct.unpack_from('<Q', data, 32)[0]
stride, count = struct.unpack_from('<HH', data, 54)
segments = [struct.unpack_from('<II6Q', data, ph + i * stride) for i in range(count)]


def original(address, size):
    segment = next(p for p in segments if p[0] == 1 and p[3] <= address
                   and address + size <= p[3] + p[5])
    offset = segment[2] + address - segment[3]
    return data[offset:offset + size]


def copy_original(address, size):
    values = ','.join(map(str, original(address, size)))
    return f'    {{ const u8 bytes[] = {{{values}}}; memcpy(base + {address}, bytes, sizeof(bytes)); }}\n'


def extract(source, start, end):
    offset = source.index(start)
    return source[offset:source.index(end, offset)]


source = (CORE / 'bloodborne_re.cpp').read_text(encoding='utf8')
prefix = r'''
#include <windows.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <map>
#include <set>
#include <vector>
#include "core/cpu_patches.h"
#include "core/bbsc_quest_event_rules.h"
#include "core/bbsc_local_map_flags.h"
#include "core/bbsc_lift_flags.h"
namespace QuestRules = Core::Bloodborne::QuestRules;
namespace World = Core::Bloodborne::World;
using Core::GuestRegisterSnapshot;
using Core::InstallGuestCodeHook;
constexpr size_t BbscWorldGroupBytes = 125;
constexpr size_t SnapshotBytes = 0xA4 + 12 * BbscWorldGroupBytes;
u64 image_base = 0;
bool missing = false;
std::array<u8, BbscWorldGroupBytes> personal{}, awards{}, map{};
std::map<u32, std::array<u8, BbscWorldGroupBytes>> live_groups;
std::array<u8, SnapshotBytes> applied{};
int applies = 0;
enum class MemoryProt { CpuReadWrite };
bool ReadablePointer(u64 pointer, size_t) { return pointer != 0; }
bool HasMemoryAccess(u64 pointer, size_t, MemoryProt) { return pointer != 0; }
u64 BbscFlagGroupStorage(u32 key) {
    if (const auto it = live_groups.find(key); it != live_groups.end())
        return reinterpret_cast<u64>(it->second.data());
    if (key == 1 && !missing) return reinterpret_cast<u64>(personal.data());
    if (key == 5) return reinterpret_cast<u64>(awards.data());
    if (key == 12410) return reinterpret_cast<u64>(map.data());
    return 0;
}
template<class T> T ReadValue(u64 address, size_t offset) {
    T value; memcpy(&value, reinterpret_cast<void*>(address + offset), sizeof(value)); return value;
}
template<class T> void put(void* address, size_t offset, T value) {
    memcpy(static_cast<u8*>(address) + offset, &value, sizeof(value));
}
void jump(u8* at, u64 target) {
    const u8 op[] = {0xff, 0x25, 0, 0, 0, 0};
    memcpy(at, op, sizeof(op)); put(at, sizeof(op), target);
}
void* PS4_SYSV_ABI Copy(void* to, const void* from, size_t n) { return memcpy(to, from, n); }
u32 PS4_SYSV_ABI SelectedRitual(u64, u32 flag, u32 width) {
    assert(flag == 9020 && width == 7);
    return 1;
}
void PS4_SYSV_ABI Unexpected() { assert(false); }
u64 PS4_SYSV_ABI Apply(u64 manager, u64 bytes) {
    assert(manager == 42);
    memcpy(applied.data(), reinterpret_cast<const void*>(bytes), applied.size());
    ++applies;
    return 73;
}
namespace BbscMod {
u64 EbootAddress() { return image_base; }
void LogPlain(const char* line) { puts(line); }
}
#define LOG_ERROR(...) assert(false)
'''
flags = source.rindex('constexpr std::array', 0, source.index(' BbscNpcQuestFlags{'))
shop_flags = source.rindex('constexpr std::array', 0, source.index(' BbscDreamShopUnlockFlags{'))
prefix += extract(source, source[flags:source.index('{', flags) + 1], '};') + '};\n'
prefix += extract(source, source[shop_flags:source.index('{', shop_flags) + 1],
                  '#ifdef BBSC_MOD\n#include "core/bbsc_native_join_flags.inc"')
prefix += (CORE / 'bbsc_native_join_flags.inc').read_text(encoding='utf8')
main = r'''
int main() {
    auto* base = static_cast<u8*>(VirtualAlloc(nullptr, 0x6000000, MEM_COMMIT | MEM_RESERVE,
                                               PAGE_EXECUTE_READWRITE));
    assert(base); image_base = reinterpret_cast<u64>(base);
'''
for start, end in [(0x13BE3C0, 0x13BECA0), (0x13BC710, 0x13BC880),
                   (0x4730BF0, 0x4730C30), (0x47314D0, 0x4731558),
                   (0x17851CE, 0x17851D3), (0x1786183, 0x1786188)]:
    main += copy_original(start, end - start)
main += r'''
    jump(base + 0x261A1B0, reinterpret_cast<u64>(&Copy));
    jump(base + 0x13CFD80, reinterpret_cast<u64>(&SelectedRitual));
    jump(base + 0x20B55B0, reinterpret_cast<u64>(&Unexpected));
    jump(base + 0x2BBE4F8, reinterpret_cast<u64>(&Unexpected));
    jump(base + 0x13BECA0, reinterpret_cast<u64>(&Apply));
    base[0x17851D3] = 0xC3;
    base[0x1786188] = 0xC3;
    InstallBbscNativeJoinFlags();
    assert(base[0x17851CE] == 0xE9 && base[0x1786183] == 0xE9);

    std::array<u8, 0x400> player{};
    std::array<u8, 0x68> world{};
    std::array<u8, 0xB8> manager{};
    std::array<u8, 1200 * BbscWorldGroupBytes> host{};
    std::array<u8, SnapshotBytes> snapshot{};
    u64 guard = 0x1234;
    put(base, 0x53E3BE0, &guard);
    put(base, 0x553B148, world.data());
    put(base, 0x553E878, world.data());
    put(base, 0x0556388C, u32(SnapshotBytes));
    put(world.data(), 0x60, player.data());
    put(player.data(), 0x3F8, u32(0x18010000));
    put(manager.data(), 0x20, u32(BbscWorldGroupBytes));
    put(manager.data(), 0x28, host.data());
    using Index = u32 PS4_SYSV_ABI (*)(u32, u32, u32, u32);
    using Serialize = void PS4_SYSV_ABI (*)(void*, void*);
    using Receive = u64 PS4_SYSV_ABI (*)(u64, u8*);
    const auto index = reinterpret_cast<Index>(base + 0x13BC710);
    const auto serialize = reinterpret_cast<Serialize>(base + 0x13BE3C0);
    const auto send = reinterpret_cast<Serialize>(base + 0x1786183);
    const auto receive = reinterpret_cast<Receive>(base + 0x17851CE);
    const u32 global1 = index(0, 0, 0, 1), global5 = index(0, 0, 0, 5), map1 = index(1, 24, 1, 0);
    const auto set = [](u8* group, u32 flag) {
        const auto bit = flag % 1000;
        group[bit / 8] |= 0x80 >> (bit % 8);
    };
    set(host.data() + global1 * 125, 1361);
    set(host.data() + global1 * 125, 1999);
    set(host.data() + global5 * 125, 5912);
    set(host.data() + map1 * 125, 12410000);
    set(host.data() + map1 * 125, 12410801);
    set(personal.data(), 1363);
    serialize(manager.data(), snapshot.data());
    const auto is_set = [](const auto& packet, u32 slot, u32 flag) {
        for (u32 i = 0; i < 12; ++i) {
            const u32 descriptor = 0x14 + i * 12;
            if (ReadValue<u32>(reinterpret_cast<u64>(packet.data()), descriptor) != slot) continue;
            const u32 data = 0xA4 + ReadValue<u32>(reinterpret_cast<u64>(packet.data()), descriptor + 4);
            const u32 bit = flag % 1000;
            return (packet[data + bit / 8] & (0x80 >> (bit % 8))) != 0;
        }
        assert(false);
        return false;
    };
    assert(is_set(snapshot, global1, 1361) && !is_set(snapshot, global1, 1363));
    assert(is_set(snapshot, global5, 5912) && is_set(snapshot, map1, 12410801));
    const auto original = snapshot;
    assert(receive(42, snapshot.data()) == 73 && applies == 1);
    assert(!is_set(applied, global1, 1361) && is_set(applied, global1, 1363));
    assert(!is_set(applied, global5, 5912) && !is_set(applied, map1, 12410801));
    assert(is_set(applied, global1, 1999) && is_set(applied, map1, 12410000));

    const auto original_host = host;
    send(manager.data(), snapshot.data());
    assert(!is_set(snapshot, global1, 1361) && !is_set(snapshot, global5, 5912));
    assert(!is_set(snapshot, map1, 12410801));
    assert(is_set(snapshot, global1, 1999) && is_set(snapshot, map1, 12410000));
    assert(host == original_host);
    receive(42, snapshot.data());
    assert(is_set(applied, global1, 1363) && !is_set(applied, global1, 1361));
    serialize(manager.data(), snapshot.data());
    assert(snapshot == original); // direct local serializer has no send mask

    snapshot = original; missing = true;
    receive(42, snapshot.data());
    assert(is_set(applied, global1, 1361) && !is_set(applied, global1, 1363));
    missing = false; snapshot = original; put(base, 0x0556388C, u32(SnapshotBytes - 1));
    receive(42, snapshot.data());
    assert(applied == original);
    put(base, 0x0556388C, u32(SnapshotBytes));
    put(snapshot.data(), 0x14 + 11 * 12 + 4, u32(0xFFFF));
    const auto malformed = snapshot;
    receive(42, snapshot.data());
    assert(applied == malformed && applies == 5);
    snapshot = original; put(snapshot.data(), 0, u32(0));
    const auto bad_magic = snapshot;
    receive(42, snapshot.data());
    assert(applied == bad_magic && applies == 6);
    puts("PASS original join serializer and production send/apply hooks: private zero/one, shared flags, local serializer, missing group and malformed input");

    std::array<u8, 0x38> extended_head{};
    std::array<u8, 125> extended_data{};
    extended_head[0x19] = 1;
    put(extended_head.data(), 8, extended_head.data());
    put(extended_head.data(), 0x28, extended_data.data());
    put(manager.data(), 0xB0, extended_head.data());
    const auto npc_flag = [](u32 flag) { return std::ranges::binary_search(BbscNpcQuestFlags, flag); };
    const auto completion_flag = [](u32 flag) { return std::ranges::binary_search(QuestRules::LocalEvents, flag); };
    const auto shop_flag = [](u32 flag) {
        return (flag / 1000 == 5 || flag / 1000 == 6) &&
               std::ranges::find(BbscDreamShopUnlockFlags, flag) != BbscDreamShopUnlockFlags.end();
    };
    std::set<u32> all_private_groups;
    for (u32 flag : BbscNpcQuestFlags) all_private_groups.insert(flag / 1000);
    for (u32 flag : QuestRules::LocalEvents) all_private_groups.insert(flag / 1000);
    for (u32 flag : BbscDreamShopUnlockFlags) all_private_groups.insert(flag / 1000);
    constexpr std::array local_map_flags{
        9301u, 9303u, 12300751u, 12401803u, 12604741u, 12604743u, 12805920u, 12805921u,
        12805922u, 12805923u, 13200101u, 13201803u, 13404741u, 13404743u,
        13504741u, 13504743u, 13604741u, 13604743u};
    const auto local_map_flag = [&](u32 flag) {
        return std::ranges::binary_search(local_map_flags, flag);
    };
    for (u32 flag : local_map_flags) all_private_groups.insert(flag / 1000);
    for (u32 key : all_private_groups) {
        std::array<u8, 125> actual;
        actual.fill(0xFF);
        MaskBbscSharedFlagGroup(key, actual.data());
        for (u32 bit = 0; bit < 1000; ++bit) {
            const u32 flag = key * 1000 + bit;
            const bool shared = !(npc_flag(flag) || completion_flag(flag) || shop_flag(flag) ||
                                  local_map_flag(flag));
            assert(World::IsLocalMapFlag(flag) == local_map_flag(flag));
            assert(((actual[bit / 8] & (0x80 >> (bit % 8))) != 0) == shared);
        }
    }
    printf("PASS shared snapshot mask: every bit in %zu catalogue groups\n", all_private_groups.size());

    std::set<u32> npc_on_wire, completions_on_wire, shops_on_wire;
    std::set<u32> local_map_on_wire;
    for (u32 map_index = 0; map_index <= 17; ++map_index) {
        // The extra case exercises the original unknown-map fallback to 99/0.
        const u32 area = map_index == 17 ? 99 : ReadValue<u32>(image_base, 0x47314D0 + map_index * 8);
        const u32 block = map_index == 17 ? 0 : ReadValue<u32>(image_base, 0x47314D4 + map_index * 8);
        put(player.data(), 0x3F8, (area << 24) | (block << 16));
        const u32 map_key = 10000 + area * 100 + block * 10;
        const std::array<u32, 12> keys{0, 1, 5, 9, map_key, map_key + 1, map_key + 4,
            map_key + 5, map_key + 6, map_key + 7, map_key + 50000, map_key + 50001};
        for (u8 host_byte : {u8{0}, u8{0xFF}}) {
            host.fill(host_byte);
            extended_data.fill(host_byte);
            const u8 guest_byte = host_byte ^ 0xFF;
            for (u32 key : keys) live_groups[key].fill(guest_byte);
            serialize(manager.data(), snapshot.data());
            auto expected_send = snapshot;
            auto expected_apply = snapshot;
            for (u32 i = 0; i < keys.size(); ++i) {
                const u32 key = keys[i];
                const u32 descriptor = 0x14 + i * 12;
                if (i < 4 || (area != 29 && area != 99)) {
                    const u32 slot = i < 4 ? index(0, 0, 0, key) : index(key / 10000, area, block, key % 10);
                    assert(ReadValue<u32>(reinterpret_cast<u64>(snapshot.data()), descriptor) == slot);
                }
                const u32 offset = 0xA4 + ReadValue<u32>(reinterpret_cast<u64>(snapshot.data()), descriptor + 4);
                for (u32 bit = 0; bit < 1000; ++bit) {
                    const u32 flag = key * 1000 + bit;
                    const bool npc = npc_flag(flag);
                    const bool completion = completion_flag(flag);
                    const bool shop = shop_flag(flag);
                    const bool local_map = local_map_flag(flag);
                    const u8 mask = 0x80 >> (bit % 8);
                    const bool motion_interlock = area != 29 &&
                        std::ranges::any_of(World::LiftFlags(key), [=](const auto& lift) {
                            return lift.offset == bit / 8 && (lift.temporary & mask);
                        });
                    if (!npc && !completion && !shop && !local_map && !motion_interlock) continue;
                    if (local_map) local_map_on_wire.insert(flag);
                    if (npc) npc_on_wire.insert(flag);
                    if (completion) completions_on_wire.insert(flag);
                    if (shop) shops_on_wire.insert(flag);
                    expected_send[offset + bit / 8] &= ~mask;
                    expected_apply[offset + bit / 8] = (expected_apply[offset + bit / 8] & ~mask) |
                        (guest_byte & mask);
                }
            }
            const auto unmasked = snapshot;
            send(manager.data(), snapshot.data());
            assert(snapshot == expected_send);
            receive(42, snapshot.data());
            assert(applied == expected_apply);
            snapshot = unmasked;
            receive(42, snapshot.data());
            assert(applied == expected_apply);
        }
    }
    assert(std::ranges::equal(local_map_on_wire, local_map_flags));
    printf("PASS 17 native maps and fallback, both bit polarities: %zu/%zu NPC flags, %zu/%zu completions, %zu/%zu shop flags occur in native join snapshots; remaining bits are unchanged\n",
        npc_on_wire.size(), BbscNpcQuestFlags.size(), completions_on_wire.size(), QuestRules::LocalEvents.size(),
        shops_on_wire.size(), BbscDreamShopUnlockFlags.size());
}
'''

compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
with tempfile.TemporaryDirectory(prefix='bbsc-native-join-flags-') as tmp:
    directory = Path(tmp)
    cpp, exe = directory / 'test.cpp', directory / 'test.exe'
    cpp.write_text(prefix + main, encoding='utf8')
    subprocess.run([compiler, '-std=c++20', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
                    '-I', str(ROOT / 'emulator/src'), '-I', str(ROOT / 'emulator/externals/xbyak'),
                    str(cpp), str(ROOT / 'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe)], check=True)
    env = dict(os.environ, PATH=str(Path(compiler).parent) + os.pathsep + os.environ.get('PATH', ''))
    subprocess.run([str(exe)], env=env, check=True, timeout=15)
