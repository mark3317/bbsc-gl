"""Verify the original Dream stages and the independent snapshot exclusion."""
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'tools/gamedata'))
from emevd import Emevd

game = Path(os.environ['BB_GAME']) / 'event'
events = dict(Emevd(game / 'm21_00_00_00.emevd.dcx').events)
common = dict(Emevd(game / 'common.emevd.dcx').events)
assert common[50][42:44] == [
    (1003, 1, struct.pack('<II', 2, 12601800)),
    (2003, 2, struct.pack('<II', 9462, 1)),
]
assert events[12100143][2] == (3, 0, struct.pack('<II', 257, 9462))
assert events[12100143][5] == (2003, 2, struct.pack('<II', 1028, 1))
assert events[12100160][13] == (1003, 101, struct.pack('<II', 258, 1028))
assert events[12100160][25] == (2004, 41, struct.pack('<IIII', 2100600, 1, 2102312, 0xFFFFFFFF))
for event in (12100300, 12100310, 12100400):
    assert any(struct.pack('<I', 9462) in args for _, _, args in events[event])
assert events[12101028][0] == (1003, 101, struct.pack('<II', 256, 50000100))
assert (2003, 4, struct.pack('<I', 10040)) in events[12101028]

source = (root / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
world = (root / 'emulator/src/core/bbsc_world_state.inc').read_text(encoding='utf8')
assert world.index('SetBbscLedgerFlag(9462, 1)') < world.index('ApplyBbscHostDreamState("independent arrival")')
start = source.index('constexpr u32 BbscDlcEyeReceipt')
keep = source[start:source.index('\n// Guest side:', start)]
apply = source[source.index('void ApplyBbscHostDreamState(std::string_view why) {'):]
assert apply.index('Chalice::CopyHostFlagGroup(BbscDreamStateKeys[i]') < apply.index('KeepBbscLocalDreamFlags(')
assert 'KeepBbscLocalDreamFlags(BbscDreamStateKeys[i], live, bbsc_dream_own.own[i].data(),' in apply
code = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include "core/bbsc_event_steps.h"
#include "core/bbsc_local_map_flags.h"
using u8=uint8_t;
using u32=uint32_t;
using namespace Core::Bloodborne;
''' + keep + r'''
int main() {
    for (int event : {12100100, 12100143, 12100144, 12100145, 12100160})
        assert(EventSteps::Classify(event, false) & EventSteps::DreamPhase);
    for (int event : {12100000, 12100142, 12101802, 12104800})
        assert(!(EventSteps::Classify(event, false) & EventSteps::DreamPhase));
    for (u32 group : {1, 2, 9, 12100, 12601, 50000}) {
        for (bool independent : {false, true}) for (u8 value : {0, 255}) {
            std::array<u8,125> own{}, live{};
            own.fill(value);
            live.fill(value ^ 255);
            KeepBbscLocalDreamFlags(group, own.data(), live.data(), independent);
            for (u32 bit=0; bit<1000; ++bit) {
                const bool phase = (group == 1 && bit < 40) || (group == 12601 && bit == 800) ||
                    (group == 9 && (bit == 462 || (800 <= bit && bit <= 802)));
                const bool local = (independent && phase) || (group == 50000 && bit == 100) ||
                    (group == 9 && (bit == 301 || bit == 303));
                const u8 mask = 0x80 >> (bit % 8);
                assert((live[bit / 8] & mask) == ((local ? value : value ^ 255) & mask));
            }
        }
    }
}
'''
with tempfile.TemporaryDirectory() as tmp:
    cpp, exe = Path(tmp) / 'test.cpp', Path(tmp) / 'test.exe'
    cpp.write_text(code)
    cxx = Path('C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([str(cxx), '-std=c++20', '-I', str(root / 'emulator/src'),
                    str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ, PATH=str(cxx.parent) + os.pathsep + os.environ.get('PATH', ''))
    subprocess.run([str(exe)], check=True, env=env)
print('PASS: original burning Dream, native Gehrman placement, snapshot and restore keep local phases and Insight receipts')
