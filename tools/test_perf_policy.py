"""Regression checks for production trace selection and reload-safe param lookup.
Runs the actual C++ helpers extracted from bloodborne_re.cpp in an isolated memory fixture.
Requires a C++20 compiler (CXX, default g++); does not launch or modify the game.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "emulator/src/core/bloodborne_re.cpp").read_text(encoding="utf-8")


def function(signature):
    start = SOURCE.index(signature + " {")
    opening = SOURCE.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (SOURCE[end] == "{") - (SOURCE[end] == "}")
        end += 1
    return SOURCE[start:end]


# Every offset used by functional dispatch must be selected, regardless of research setting.
dispatch = SOURCE.split("const auto& site = Sites[tag];", 1)[1].split(
    "if (!BbscResearchEnabled() && (!capture_file || !BbscEssentialDiagnosticSite", 1)[0]
policy = function("bool BbscFunctionalTraceSite(const TraceSite& site)")
required = set(re.findall(r"site.offset == ([A-Za-z0-9_]+)", dispatch))
selected = set(re.findall(r"site.offset == ([A-Za-z0-9_]+)", policy))
assert required <= selected, required - selected
assert 'site.name.starts_with("BBSC.Remo.")' in policy
assert "TraceKind::ActionFlags" not in policy
# Inventory probes reused the leave-decision enum; they must not survive the production filter.
diagnostics = function("bool BbscEssentialDiagnosticSite(const TraceSite& site)")
constants = dict(re.findall(r"constexpr u64 (\w+) = (0x[0-9A-Fa-f]+);", SOURCE))
offsets = {int(constants.get(value, value), 16) for value in selected}
sites = re.findall(r'\{"([^"]+)",\s*(\w+),\s*TraceKind::(\w+)',
                   SOURCE.split("constexpr auto Sites =", 1)[1].split("});", 1)[0])
assert '!site.name.starts_with("BBSC.Items.")' in diagnostics
production = [(name, value, kind) for name, value, kind in sites
              if int(constants.get(value, value), 16) in offsets or name.startswith("BBSC.Remo.")
              or kind in ("EnginePanic", "LuaSessionEvent")
              or (kind == "MatchingLeaveDecision" and not name.startswith("BBSC.Items."))]
assert not any(name.startswith("BBSC.Items.") for name, _, _ in production)
print(f"trace selection: {len(production)}/{len(sites)} ({len(sites)-len(production)} diagnostic hooks omitted)")


prefix = r"""
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <map>
#include <string>
#include <string_view>
#include <vector>
#include <iostream>
using u64 = uint64_t;
using u32 = uint32_t;
using s32 = int32_t;
u64 image_base = 0x1000;
u64 root = 0;
size_t reads = 0;
std::vector<std::pair<u64, size_t>> regions;
bool ReadablePointer(u64 ptr, size_t size) {
    ++reads;
    for (auto [base, bytes] : regions)
        if (ptr >= base && ptr - base <= bytes && size <= bytes - (ptr - base)) return true;
    return false;
}
template<class T> T ReadValue(u64 base, size_t off) {
    ++reads;
    if (base == image_base + 0x05540340 && off == 0) return static_cast<T>(root);
    T value{};
    if (ReadablePointer(base + off, sizeof(T))) std::memcpy(&value, reinterpret_cast<void*>(base+off), sizeof(T));
    return value;
}
template<size_t N> u64 reg(std::array<unsigned char, N>& a) {
    auto ptr = reinterpret_cast<u64>(a.data()); regions.emplace_back(ptr, N); return ptr;
}
template<class T> void put(u64 base, size_t off, T value) { std::memcpy(reinterpret_cast<void*>(base+off), &value, sizeof(T)); }
"""
main = r"""
int main() {
    std::array<unsigned char, 4096> repo{}, other{};
    std::array<unsigned char, 128> holder{}, resource{}, goods{}, lot{}, replacement{};
    root = reg(repo); const auto alternate = reg(other);
    const auto h = reg(holder), r = reg(resource), g = reg(goods), l = reg(lot), n = reg(replacement);
    std::strcpy(reinterpret_cast<char*>(g+12), "EQUIP_PARAM_GOODS_ST");
    std::strcpy(reinterpret_cast<char*>(l+12), "ITEMLOT_PARAM_ST");
    std::strcpy(reinterpret_cast<char*>(n+12), "ITEMLOT_PARAM_ST");
    put(root, 0x148, s32{1}); put(root, 0xF00, h); put(h, 0x70, r); put(r, 0x70, l);
    assert(BbscGameParamTable("ITEMLOT_PARAM_ST") == l);
    reads = 0;
    for (int i=0; i<100; ++i) assert(BbscGameParamTable("ITEMLOT_PARAM_ST") == l);
    assert(reads == 600); // six validations/reads per late-slot lookup, no duplicate per-field queries
    put(r, 0x70, n); assert(BbscGameParamTable("ITEMLOT_PARAM_ST") == n); // reload, same holder
    put(root, 0x148, s32{0}); assert(BbscGameParamTable("ITEMLOT_PARAM_ST") == 0); // unloaded
    root = alternate; put(root, 0x148, s32{1}); put(root, 0x700, h);
    assert(BbscGameParamTable("ITEMLOT_PARAM_ST") == n); // repository and slot changed
    put(r, 0x70, g); assert(BbscGameParamTable("ITEMLOT_PARAM_ST") == 0); // wrong type/reused resource
    assert(BbscGameParamTable("EQUIP_PARAM_GOODS_ST") == g);
    put(r, 0x70, u64{0xDEAD}); assert(BbscGameParamTable("EQUIP_PARAM_GOODS_ST") == 0);
    put(root, 0x700, u64{0xDEAD}); assert(BbscGameParamTable("ITEMLOT_PARAM_ST") == 0);
    std::array<unsigned char, 0x158> prefix_repo{};
    root=reg(prefix_repo); put(root,0x148,s32{1});put(root,0x150,h);put(r,0x70,l);
    assert(BbscGameParamTable("ITEMLOT_PARAM_ST")==l); // last fully validated prefix slot
    root=0;assert(BbscGameParamTable("ITEMLOT_PARAM_ST")==0);
    assert(!BbscQuietMessage(30, 102001)); // host sees join
    assert(!BbscQuietMessage(30, 102100)); // guest sees join
    assert(!BbscQuietMessage(30, 20000407)); // departure
    assert(BbscQuietMessage(30, 103101)); // death
    assert(BbscQuietMessage(30, 105199)); // boss (network state remains independent)
    assert(BbscQuietMessage(30, 15000011)); // follow/rejoin
    assert(!BbscQuietMessage(30, 14000)); // actionable bell confirmation
    assert(BbscHideBanner(u"[BBSC:silent]"));
    assert(BbscHideBanner(u"?ActionEventInfo?"));
    assert(!BbscHideBanner(u"Player joined your game."));
    assert(!BbscHideBanner(u"PvP РІРєР»СЋС‡РµРЅРѕ."));
    assert(!BbscQuietMessage(200, 302000)); // item/menu name
    std::cout << "param reload/cache and notification policy: PASS\n";
}
"""
with tempfile.TemporaryDirectory(prefix="bbsc-perf-test-") as tmp:
    source = Path(tmp) / "test.cpp"
    binary = Path(tmp) / "test.exe"
    source.write_text(prefix + function("u64 BbscGameParamTable(std::string_view type)") +
                      function("bool BbscQuietMessage(u32 category, u32 id)") +
                      function("bool BbscHideBanner(std::u16string_view text)") + main, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-O2", str(source), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print(f"functional trace dispatch coverage: PASS ({len(required)} offsets + cutscenes)")
