"""Original 1.09 EMEVD retry branches, native bank/iterator and BBSC trampoline."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/gamedata'))
from emevd import Emevd

game = Path(os.environ['BB_GAME'])
elf = Path(sys.argv[1]).read_bytes()[0x4000:]
assert elf[0x17bedd0:0x17bedd6] == bytes.fromhex('55 48 89 e5 41 57')
assert elf[0x12ef2e0:0x12ef2e6] == bytes.fromhex('55 48 89 e5 41 57')
source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
production = source[source.index('constexpr std::pair<s64, s32> BbscBossFogRetrySteps'):
                    source.index('// From an event\'s 2003 instruction')]
targets = {int(event): int(step) for event, step in re.findall(r'\{(\d+), (\d+)\}', production)}

cases = {}
scripts = {}
for script in (game / 'event').glob('*.emevd.dcx'):
    evd = Emevd(script)
    for row, (event, ins) in enumerate(evd.events):
        if event not in targets:
            continue
        assert ins[0][:2] == (1003, 2) and ins[0][2][:4] == b'\0\1\0\0'
        assert ins[1][:2] == (1003, 101) and ins[1][2][:4] == b'\0\1\0\0'
        label = ins.index((1014, 0, b''))
        enable = targets[event]
        assert ins[enable][:2] == (2005, 3) and ins[enable][2][4:] == b'\1\0\0\0'
        assert any((b, i) == (2006, 2) for b, i, _ in ins[enable:label])
        assert all((b, i) in ((2005, 3), (2006, 2), (2011, 1)) for b, i, _ in ins[enable:label])
        assert any((b, i) == (3, 24) for b, i, _ in ins[label:])
        cases[event] = (script.stem, row, enable, label)
        scripts[script.stem] = evd.data
assert set(cases) == set(targets)

fixture = r'''
#include <windows.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <cstring>
#include <fstream>
#include <iterator>
#include <vector>
#include "core/cpu_patches.h"
using Core::GuestRegisterSnapshot;
using s64=int64_t;
using s32=int32_t;
using u32=uint32_t;
u64 image_base=0;
s32 state=6, type=1;
u32 intro=0;
bool introduced=true;
u8 bbsc_chalice_reward_gate_skip=0;
namespace BbscMod {u64 EbootAddress(){return image_base;} void LogPlain(const char*){}}
bool ReadablePointer(u64 address, size_t) { return address > 0x10000; }
template<class T> T ReadValue(u64 p, size_t off) {
    T value; memcpy(&value, (void*)(p+off), sizeof(value)); return value;
}
template<class T> bool WriteValue(u64 p, size_t off, T value) {
    memcpy((void*)(p+off), &value, sizeof(value)); return true;
}
s32 GetSessionState() { return state; }
s32 GetLocalPlayerType() { return type; }
bool PS4_SYSV_ABI NativeFlag(u64, u32 flag) { assert(flag==intro); return introduced; }
bool BbscEventFlag(u32 flag) { return NativeFlag(0, flag); }
struct Range {u64 first, end; s64 event;} range;
const Range* LookupBbscQuestRange(u64) { return &range; }
void BbscChaliceRewardGateHook(u64, const GuestRegisterSnapshot*) {
    bbsc_chalice_reward_gate_skip=0;
}
''' + production + r'''
void Load(const char* path, u64 address) {
    std::ifstream file(path,std::ios::binary);
    assert(file);
    std::copy(std::istreambuf_iterator<char>(file), {}, (char*)address);
}
void Check(const char* path, s64 event, u64 row_index, s32 enable, s32 label, bool hooked) {
    std::ifstream script(path,std::ios::binary);
    std::vector<char> data(std::istreambuf_iterator<char>(script), {});
    const u64 file=(u64)data.data();
    const u64 row=file+ReadValue<u64>(file,0x18)+row_index*0x30;
    assert(ReadValue<s64>(row,0)==event);
    const u64 first=file+ReadValue<u64>(file,0x28)+ReadValue<u64>(row,0x10);
    range={first, first+ReadValue<u64>(row,8)*0x20, event};
    std::array<u64,2> ref{0,file};
    const u64 args=file+ReadValue<u64>(file,0x78)+ReadValue<u64>(first+0x20,0x10);
    // The common Chalice event substitutes a per-ritual flag into +B8.
    intro=event/100000==129 ? 12906792 : ReadValue<u32>(args,4);
    std::array<u32,2> resolved{256,intro};
    using Bank=u8 PS4_SYSV_ABI (*)(u64,u64);
    using Advance=u8 PS4_SYSV_ABI (*)(u64,u8*);
    for (auto [role, player] : {std::pair{6,1},std::pair{3,0},std::pair{6,2}})
    for (bool seen : {false,true}) {
        state=role; type=player; introduced=seen;
        std::array<u64,26> instance{};
        const u64 p=(u64)instance.data();
        WriteValue<u64>(p,0x80,(u64)ref.data());
        WriteValue<u64>(p,0x88,row);
        WriteValue<s32>(p,0xA0,1);
        WriteValue<u64>(p,0xA8,(u64)ref.data());
        WriteValue<u64>(p,0xB0,first+0x20);
        WriteValue<u64>(p,0xB8,event/100000==129 ? (u64)resolved.data() : 0);
        WriteValue<s32>(p,0xC0,1);
        WriteValue<u8>(p,0xC4,1);
        assert(((Bank)(image_base+0x17bedd0))(0,p)==1);
        u8 keep_running=0;
        assert(((Advance)(image_base+0x12ef2e0))(p+0x80,&keep_running));
        const auto next=!seen ? 2 : hooked && role==6 && player==1 ? enable : label;
        assert(keep_running==1 && ReadValue<s32>(p,0xA0)==next);
        assert(ReadValue<u64>(p,0xB0)==first+next*0x20);
    }
}
void CheckAll(bool hooked) {
CASES
}
int main() {
    image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);
    assert(image_base);
    Load("bank.bin",image_base+0x17bedd0);
    Load("iterator.bin",image_base+0x12ef2e0);
    u64 canary=0;
    WriteValue<u64>(image_base,0x53e3be0,(u64)&canary);
    WriteValue<u64>(image_base,0x553b0d8,1);
    const auto flag=(u64)&NativeFlag;
    const u64 stub=image_base+0x1399bf0;
    WriteValue<u16>(stub,0,0xb848);
    WriteValue<u64>(stub,2,flag);
    WriteValue<u16>(stub,10,0xe0ff);
    CheckAll(false);
    const std::array<u8,6> prologue{0x55,0x48,0x89,0xe5,0x41,0x57};
    assert(Core::InstallGuestCodeHook((void*)(image_base+0x17bedd0),prologue,0,
        BbscEventBank1003Hook,&bbsc_chalice_reward_gate_skip));
    CheckAll(true);
}
'''

with tempfile.TemporaryDirectory(prefix='bbsc-fog-retry-') as directory:
    tmp = Path(directory)
    for script, data in scripts.items():
        (tmp / script).write_bytes(data)
    (tmp / 'bank.bin').write_bytes(elf[0x17bedd0:0x17c0384])
    (tmp / 'iterator.bin').write_bytes(elf[0x12ef2e0:0x12ef50b])
    cpp = tmp / 'fixture.cpp'
    cpp.write_text(fixture.replace('CASES', '\n'.join(
        f'    Check("{script}",{event},{row},{enable},{label},hooked);'
        for event, (script, row, enable, label) in cases.items())), encoding='utf-8')
    exe = tmp / 'fixture.exe'
    cxx = Path(os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe'))
    subprocess.run([str(cxx), '-std=c++20', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
                    '-I', str(ROOT / 'emulator/src'), '-I', str(ROOT / 'emulator/externals/xbyak'),
                    str(cpp), str(ROOT / 'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe)],
                   check=True, cwd=tmp)
    subprocess.run([str(exe)], check=True, cwd=tmp, timeout=20,
                   env={**os.environ, 'PATH': str(cxx.parent) + os.pathsep + os.environ['PATH']})
print(f'PASS {len(cases)} original boss fog branches: guest retries reach native enable; first entry, host and invader keep vanilla routing')
