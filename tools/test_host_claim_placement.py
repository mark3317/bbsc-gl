"""Exercise the native summon-build hook and the header read by the host's HTTP claim."""
import os
from pathlib import Path
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / "emulator/src/core/bloodborne_re.cpp").read_text(
    encoding="utf-8"
)


def region(start, end):
    begin = source.index(start)
    return source[begin:source.index(end, begin)]


code = r"""
#include <bit>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <mutex>
#include <optional>
#include <sstream>
#include <string_view>
using u64 = uint64_t;
using u32 = uint32_t;
using s32 = int32_t;
struct GuestRegisterSnapshot { u64 rsi; };
enum class MemoryProt { CpuRead };
"""
code += region("struct SummonPlacementDescriptor {", "std::optional<SummonPlacementDescriptor> seamless_received")
code += r"""
SummonPlacementDescriptor local{0x1d000000, 1, 2, 3, 4, 290100};
bool readable = true, writable = true;
bool ReadLocalSummonPlacement(SummonPlacementDescriptor& host, std::string_view& result) {
    result = readable ? "captured" : "invalid_transform";
    if (readable) host = local;
    return readable;
}
bool HasMemoryAccess(u64, size_t, MemoryProt) { return true; }
bool IsUsablePackedMap(u32 map) { return map != 0; }
bool WriteValue(u64 ptr, size_t offset, const SummonPlacementDescriptor& value) {
    if (writable) std::memcpy(reinterpret_cast<void*>(ptr + offset), &value, sizeof(value));
    return writable;
}
"""
code += region("void ApplyCrossMapSummonHostPlacement(", "// The summoned reload spawns")
code += region("std::optional<std::string> GetSeamlessHostPlacementHeader() {", "bool SetSeamlessHostPlacementHeader(")
code += r"""
int main() {
    struct { u32 prefix; SummonPlacementDescriptor candidate; } prepared{};
    GuestRegisterSnapshot regs{reinterpret_cast<u64>(&prepared)};
    prepared.candidate.packed_region = 0x15000000;
    ApplyCrossMapSummonHostPlacement(regs);
    assert(prepared.candidate.x == 1 && GetSeamlessHostPlacementHeader());
    // Host moved since the first guest. Same-map guest keeps its own native candidate.
    local.x = 8;
    ApplyCrossMapSummonHostPlacement(regs);
    assert(prepared.candidate.x == 1);
    assert(GetSeamlessHostPlacementHeader() ==
           "1,1d000000,41000000,40000000,40400000,40800000,290100");
    readable = false;
    ApplyCrossMapSummonHostPlacement(regs);
    assert(!GetSeamlessHostPlacementHeader());
    readable = true;
    writable = false;
    prepared.candidate.packed_region = 0x15000000;
    ApplyCrossMapSummonHostPlacement(regs);
    assert(!GetSeamlessHostPlacementHeader());
}
"""

with tempfile.TemporaryDirectory(prefix="bbsc-host-placement-") as tmp:
    cpp = Path(tmp) / "test.cpp"
    exe = Path(tmp) / "test.exe"
    cpp.write_text(code, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
