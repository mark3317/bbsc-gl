"""Execute the original ladder and collision events used at respawn."""
from pathlib import Path
import os
import re
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "emulator/src/core/bloodborne_re.cpp").read_text(encoding="utf-8")
respawn = source.split("bool BbscRespawnInPlace(std::string_view why) {", 1)[1]
guard_start = respawn.index("    static constexpr std::array<u8, 16> RestoreCollisionSignature")
guard_end = respawn.index("    // Regist_LadderAction", guard_start)
guard = respawn[guard_start:guard_end]
ladder_guard_end = respawn.index("    if (!BbscResetDeathStatuses(player))", guard_end)
ladder_guard = respawn[guard_end:ladder_guard_end]
ladder_reset_start = respawn.index("    const std::array<u8, 16> local_event_args")
ladder_reset = respawn[ladder_reset_start:respawn.index("    // 1. opacity", ladder_reset_start)]
restore_start = respawn.index("    reinterpret_cast<LocalPlayerEvent>(restore_collision)")
restore_end = respawn.index("    // Native respawn placement", restore_start)
restore = respawn[restore_start:restore_end]
assert respawn.index("reinterpret_cast<Warp>") < restore_start
assert restore_end < respawn.index("reinterpret_cast<PhysicsReset>")
assert respawn.index("if (!target.has_value())") < guard_start
assert ladder_guard_end < ladder_reset_start < respawn.index("reinterpret_cast<Warp>")
elf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parents[1] / "out/register-study.elf"
binary = elf_path.read_bytes()
native = binary[0x1386410 + 0x4000:0x1386485 + 0x4000]
native_ladder = binary[0x1385CF0 + 0x4000:0x1385D59 + 0x4000]


def signature(block, name):
    body = block.split(name + "{", 1)[1].split("};", 1)[0]
    return bytes(int(v, 16) for v in re.findall(r"0x([0-9A-Fa-f]{2})", body))


assert native.startswith(signature(guard, "RestoreCollisionSignature"))
assert native_ladder.startswith(signature(ladder_guard, "EndLadderSignature"))
for address in (0x138642D, 0x1386454, 0x1386469):
    raw = binary[address + 0x4000:address + 0x4005]
    assert raw[0] == 0xE8
    assert address + 5 + struct.unpack("<i", raw[1:])[0] == 0x13C97A0

fixture = r"""
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
using u8 = std::uint8_t;
using u16 = std::uint16_t;
using u64 = std::uint64_t;
using s32 = std::int32_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
std::array<u8, 0x400> actor{}, control{}, actor_modules{}, action{}, world{};
alignas(16) std::array<u8, 0x60> ladder_data{};
u64 image_base;
bool have_actor = true;
int finds = 0;
template<class T> u64 address(T& memory) { return reinterpret_cast<u64>(memory.data()); }
template<class T> T ReadValue(u64 p, size_t offset) {
    T value;
    std::memcpy(&value, reinterpret_cast<const void*>(p + offset), sizeof(value));
    return value;
}
template<class T> void WriteValue(u64 p, size_t offset, T value) {
    std::memcpy(reinterpret_cast<void*>(p + offset), &value, sizeof(value));
}
bool ReadablePointer(u64 p, size_t n) {
    for (u64 start : {address(actor_modules), address(action), address(world), address(ladder_data)}) {
        if (p == start) return n <= (start == address(ladder_data) ? ladder_data.size() : world.size());
    }
    return p >= image_base && p - image_base < 0x6000000 &&
           n <= 0x6000000 - (p - image_base);
}
u64 PS4_SYSV_ABI Find(unsigned entity) {
    assert(entity == 10000);
    ++finds;
    return have_actor ? reinterpret_cast<u64>(actor.data()) : 0;
}
bool restore_collision() {
GUARD
    const std::array<u8, 16> local_event_args{};
    using LocalPlayerEvent = void PS4_SYSV_ABI (*)(u64, u64, const u8*);
RESTORE
    return true;
}
bool end_ladder_action() {
    const u64 modules = address(actor_modules);
    const u64 world_chr = address(world);
    const u64 player = address(actor);
LADDER_GUARD
LADDER_RESET
    return true;
}
void check_ladder_action() {
    WriteValue<u64>(image_base, 0x553e878, address(world));
    WriteValue<u64>(address(world), 0x60, address(actor));
    WriteValue<u64>(address(actor), 0x3b0, address(actor_modules));
    WriteValue<u64>(address(actor_modules), 0x58, address(action));
    WriteValue<u64>(address(action), 0x28, address(ladder_data));
    for (int role : {0, 1}) {
        WriteValue<s32>(address(actor), 0x78, role);
        for (s32 mode : {1, 2}) {
            ladder_data.fill(0xaa);
            WriteValue<s32>(address(ladder_data), 0, mode);
            control[0x111] = 1;
            auto expected = ladder_data;
            std::memset(expected.data(), 0, 0x0c);
            std::memset(expected.data() + 0x10, 0, 0x10);
            WriteValue<s32>(address(expected), 0x20, static_cast<s32>(0xbdcccccd));
            WriteValue<s32>(address(expected), 0x28, -1);
            assert(end_ladder_action());
            assert(ladder_data == expected && control[0x111] == 0);
        }
    }
    auto before = ladder_data;
    control[0x111] = 1;
    auto& opcode = *reinterpret_cast<u8*>(image_base + 0x1385cf0);
    opcode ^= 1;
    assert(end_ladder_action()); // inactive module needs no callback
    assert(ladder_data == before && control[0x111] == 1);
    WriteValue<s32>(address(ladder_data), 0, 1);
    before = ladder_data;
    assert(!end_ladder_action()); // bad signature during a ladder action
    assert(ladder_data == before && control[0x111] == 1);
    opcode ^= 1;
    WriteValue<u64>(address(world), 0x60, 0);
    assert(!end_ladder_action()); // native callback would resolve a different actor
    assert(ladder_data == before && control[0x111] == 1);
    WriteValue<u64>(address(action), 0x28, 0);
    assert(end_ladder_action()); // player without a ladder module
}
int main() {
    image_base = reinterpret_cast<u64>(VirtualAlloc(nullptr, 0x6000000,
        MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    assert(image_base);
    const u8 native[] = {NATIVE};
    const u8 ladder_code[] = {NATIVE_LADDER};
    std::memcpy(reinterpret_cast<void*>(image_base + 0x1386410), native, sizeof(native));
    std::memcpy(reinterpret_cast<void*>(image_base + 0x1385cf0), ladder_code, sizeof(ladder_code));
    const u64 find = image_base + 0x13c97a0;
    WriteValue<u16>(find, 0, 0xb848);
    WriteValue<u64>(find, 2, reinterpret_cast<u64>(&Find));
    WriteValue<u16>(find, 10, 0xe0ff);
    WriteValue<u64>(image_base, 0x553b0c8, 1);
    WriteValue<u64>(reinterpret_cast<u64>(actor.data()), 0x58,
                    reinterpret_cast<u64>(control.data()));
    FlushInstructionCache(GetCurrentProcess(), reinterpret_cast<void*>(image_base), 0x6000000);
    // Includes the observed P1 state D8/0000, gravity disabled, a death bit,
    // unrelated flag bits, and already-restored state for both player roles.
    for (int role : {0, 1}) {
        WriteValue<unsigned>(reinterpret_cast<u64>(actor.data()), 0x78, role);
        for (unsigned flags = 0; flags < 256; ++flags) {
            for (u16 physics : {u16(0), u16(0x10), u16(0x11), u16(0xffff)}) {
                actor[0x1e1] = static_cast<u8>(flags);
                control[0x111] = 0xff;
                WriteValue<u16>(reinterpret_cast<u64>(control.data()), 0x114, physics);
                finds = 0;
                assert(restore_collision() && finds == 3);
                assert(actor[0x1e1] == (flags & ~0x40));
                assert(ReadValue<u16>(reinterpret_cast<u64>(control.data()), 0x114) == (physics & ~0x10));
                assert(control[0x111] == 0);
            }
        }
    }
    auto before_actor = actor;
    auto before_control = control;
    *reinterpret_cast<u8*>(image_base + 0x1386410) ^= 1;
    finds = 0;
    assert(!restore_collision() && finds == 0);
    assert(actor == before_actor && control == before_control);
    *reinterpret_cast<u8*>(image_base + 0x1386410) ^= 1;
    have_actor = false;
    assert(restore_collision() && finds == 3);
    assert(actor == before_actor && control == before_control);
    check_ladder_action();
    VirtualFree(reinterpret_cast<void*>(image_base), 0, MEM_RELEASE);
}
"""
fixture = fixture.replace("LADDER_GUARD", ladder_guard).replace("LADDER_RESET", ladder_reset)
fixture = fixture.replace("GUARD", guard).replace("RESTORE", restore)
fixture = fixture.replace("NATIVE_LADDER", ",".join(map(str, native_ladder)))
fixture = fixture.replace("NATIVE", ",".join(map(str, native)))
compiler = Path(os.environ.get("CXX", "C:/msys64/clang64/bin/clang++.exe"))
with tempfile.TemporaryDirectory(prefix="bbsc-respawn-collision-") as temp:
    cpp, exe = Path(temp) / "test.cpp", Path(temp) / "test.exe"
    cpp.write_text(fixture, encoding="utf-8")
    subprocess.run([str(compiler), "-std=c++20", str(cpp), "-o", str(exe)], check=True)
    env = dict(os.environ)
    env["PATH"] = str(compiler.parent) + os.pathsep + env.get("PATH", "")
    subprocess.run([str(exe)], env=env, check=True, timeout=10)
print("PASS: original OnEvent_4001 and OnEvent_4019, host/guest, active/inactive ladder, bad signatures and absent actor")
