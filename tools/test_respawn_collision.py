"""Execute the respawn collision restore with the original OnEvent_4019."""
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
guard_end = respawn.index("    if (!BbscResetDeathStatuses(player))", guard_start)
guard = respawn[guard_start:guard_end]
restore_start = respawn.index("    const std::array<u8, 16> collision_args")
restore_end = respawn.index("    // Native respawn placement", restore_start)
restore = respawn[restore_start:restore_end]
assert respawn.index("reinterpret_cast<Warp>") < restore_start
assert restore_end < respawn.index("reinterpret_cast<PhysicsReset>")
assert respawn.index("if (!target.has_value())") < guard_start
elf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parents[1] / "out/register-study.elf"
binary = elf_path.read_bytes()
native = binary[0x1386410 + 0x4000:0x1386485 + 0x4000]
signature_body = guard.split("RestoreCollisionSignature{", 1)[1].split("};", 1)[0]
signature = bytes(int(v, 16) for v in re.findall(r"0x([0-9A-Fa-f]{2})", signature_body))
assert native.startswith(signature)
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
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
std::array<u8, 0x400> actor{}, control{};
u64 image_base;
bool have_actor = true;
int finds = 0;
template<class T> T ReadValue(u64 p, size_t offset) {
    T value;
    std::memcpy(&value, reinterpret_cast<const void*>(p + offset), sizeof(value));
    return value;
}
template<class T> void WriteValue(u64 p, size_t offset, T value) {
    std::memcpy(reinterpret_cast<void*>(p + offset), &value, sizeof(value));
}
bool ReadablePointer(u64 p, size_t n) {
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
RESTORE
    return true;
}
int main() {
    image_base = reinterpret_cast<u64>(VirtualAlloc(nullptr, 0x6000000,
        MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    assert(image_base);
    const u8 native[] = {NATIVE};
    std::memcpy(reinterpret_cast<void*>(image_base + 0x1386410), native, sizeof(native));
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
    VirtualFree(reinterpret_cast<void*>(image_base), 0, MEM_RELEASE);
}
"""
fixture = fixture.replace("GUARD", guard).replace("RESTORE", restore)
fixture = fixture.replace("NATIVE", ",".join(map(str, native)))
compiler = Path(os.environ.get("CXX", "C:/msys64/clang64/bin/clang++.exe"))
with tempfile.TemporaryDirectory(prefix="bbsc-respawn-collision-") as temp:
    cpp, exe = Path(temp) / "test.cpp", Path(temp) / "test.exe"
    cpp.write_text(fixture, encoding="utf-8")
    subprocess.run([str(compiler), "-std=c++20", str(cpp), "-o", str(exe)], check=True)
    env = dict(os.environ)
    env["PATH"] = str(compiler.parent) + os.pathsep + env.get("PATH", "")
    subprocess.run([str(exe)], env=env, check=True, timeout=10)
print("PASS: original OnEvent_4019, observed P1 state, host/guest, flag preservation, bad signature and absent actor")
