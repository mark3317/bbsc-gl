"""Original 1.09 first-encounter and retry branches through native fog gates."""
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
production = source[source.index('void UseBbscLudwigFogVictoryFlag('):
                    source.index('// From an event\'s 2003 instruction')]
production += source[source.index('u8 bbsc_guest_role_skip = 0;'):
                     source.index('void PS4_SYSV_ABI BbscDreamTypeCheckHook(')]
access = (ROOT / 'emulator/src/core/bbsc_guest_access.h').read_text(encoding='utf-8')
retry_table = access.split('BossFogRetrySteps[] = {', 1)[1].split('};', 1)[0]
targets = {int(event): int(step) for event, step in re.findall(r'\{(\d+), (\d+)\}', retry_table)}
guest_table = access.split('GuestFogGates[] = {', 1)[1].split('};', 1)[0]
guest_targets = {int(event): (int(flag), int(step or 4))
                 for event, flag, step in re.findall(r'\{(\d+), (\d+)(?:, (\d+))?\}', guest_table)}

cases = {}
guest_cases = {}
scripts = {}
for script in (game / 'event').glob('*.emevd.dcx'):
    evd = Emevd(script)
    for row, (event, ins) in enumerate(evd.events):
        if event in guest_targets:
            flag, step = guest_targets[event]
            assert ins[step] == (3, 0, (257).to_bytes(4, 'little') + flag.to_bytes(4, 'little'))
            assert ins[step-1][:2] == (3, 0)
            assert ins[step+1] == (4, 3, bytes.fromhex('010000001027000001000000'))
            assert ins[step+2][:2] == (3, 24)
            assert ins[step+4][:2] == (2004, 14)
            guest_cases[event] = (script.stem, row, step, flag)
            scripts[script.stem] = evd.data
        if event not in targets:
            continue
        assert ins[0][:2] == (1003, 2) and ins[0][2][:4] == b'\0\1\0\0'
        assert ins[1][:2] == (1003, 101) and ins[1][2][:4] == b'\0\1\0\0'
        hides_fog = ins[2] == (1003, 5, b'\2\1\0\0')
        if hides_fog:
            assert ins[3][:2] == (2005, 3) and ins[3][2][4:] == bytes(4)
            assert ins[4][:2] == (2006, 1)
        label = ins.index((1014, 0, b''))
        enable = targets[event]
        assert ins[enable][:2] == (2005, 3) and ins[enable][2][4:] == b'\1\0\0\0'
        assert any((b, i) == (2006, 2) for b, i, _ in ins[enable:label])
        assert all((b, i) in ((2005, 3), (2006, 2), (2011, 1)) for b, i, _ in ins[enable:label])
        assert any((b, i) == (3, 24) for b, i, _ in ins[label:])
        cases[event] = (script.stem, row, enable, label, hides_fog)
        scripts[script.stem] = evd.data
assert set(cases) == set(targets)
assert set(guest_cases) == set(guest_targets)
assert {event for event, case in cases.items() if not case[-1]} == {12104810, 12104880}

ludwig = dict(Emevd(game / 'event/m34_00_00_00.emevd.dcx').events)
victory = (9471).to_bytes(4, 'little')
assert ludwig[13404800][0] == ludwig[13404801][1] == (1003, 2, b'\0\1\0\0' + victory)
assert ludwig[13401800][42] == (2003, 2, victory + b'\1\0\0\0')

fixture = r'''
#include <windows.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <vector>
#include "core/cpu_patches.h"
#include "core/bbsc_guest_access.h"
namespace GuestAccess = Core::Bloodborne::GuestAccess;
using Core::GuestRegisterSnapshot;
using s64=int64_t;
using s32=int32_t;
using u32=uint32_t;
u64 image_base=0;
s32 state=6, type=1;
u32 intro=0;
bool introduced=true;
bool ludwig_defeat_event=false, ludwig_victory=false;
u8 bbsc_chalice_reward_gate_skip=0;
namespace BbscMod {u64 EbootAddress(){return image_base;} void LogPlain(const char*){}}
bool ReadablePointer(u64 address, size_t) { return address > 0x10000; }
enum class MemoryProt { CpuWrite };
bool HasMemoryAccess(u64 address, size_t size, MemoryProt) { return ReadablePointer(address, size); }
template<class T> T ReadValue(u64 p, size_t off) {
    T value; memcpy(&value, (void*)(p+off), sizeof(value)); return value;
}
template<class T> bool WriteValue(u64 p, size_t off, T value) {
    memcpy((void*)(p+off), &value, sizeof(value)); return true;
}
s32 GetSessionState() { return state; }
s32 GetLocalPlayerType() { return type; }
bool BbscGuestInHostWorld() { return state == 6; }
bool BbscTimelineEnabled() { return false; }
#define BBSC_TIMELINE(...) ((void)0)
std::atomic<u32> bbsc_load_generation{0};
bool PS4_SYSV_ABI NativeFlag(u64, u32 flag) {
    if (flag==13401800) return ludwig_defeat_event;
    if (flag==9471) return ludwig_victory;
    assert(flag==intro);
    return introduced;
}
bool BbscEventFlag(u32 flag) { return NativeFlag(0, flag); }
struct BbscQuestRange {u64 first, end, row; s64 event;} range;
const BbscQuestRange* LookupBbscQuestRange(u64) { return &range; }
s64 BbscEventIdOf(u64) { return range.event; }
void BbscChaliceRewardGateHook(u64, const GuestRegisterSnapshot*) {
    bbsc_chalice_reward_gate_skip=0;
}
''' + production + r'''
void Load(const char* path, u64 address) {
    std::ifstream file(path,std::ios::binary);
    assert(file);
    std::copy(std::istreambuf_iterator<char>(file), {}, (char*)address);
}
void ExpectLudwigVictoryOperand(std::vector<char>& expected, u64 file, u64 first, u32 step) {
    const u64 args=ReadValue<u64>(file,0x78)+ReadValue<u64>(first+step*0x20,0x10);
    const u64 operand=(u64)expected.data()+args+4;
    assert(ReadValue<u32>(operand,0)==13401800);
    WriteValue<u32>(operand,0,9471);
}
void Check(const char* path, s64 event, u64 row_index, s32 enable, s32 label, bool hides_fog,
           bool hooked) {
    assert(!GuestAccess::EventAllowed(event));
    std::ifstream script(path,std::ios::binary);
    std::vector<char> data(std::istreambuf_iterator<char>(script), {});
    const u64 file=(u64)data.data();
    const u64 row=file+ReadValue<u64>(file,0x18)+row_index*0x30;
    assert(ReadValue<s64>(row,0)==event);
    const u64 first=file+ReadValue<u64>(file,0x28)+ReadValue<u64>(row,0x10);
    range={first, first+ReadValue<u64>(row,8)*0x20, row, event};
    std::array<u64,2> ref{0,file};
    if (event==13404800 && hooked) {
        auto expected=data;
        for (u32 step : {5u,11u,14u}) ExpectLudwigVictoryOperand(expected,file,first,step);
        std::array<u64,26> instance{};
        const u64 p=(u64)instance.data();
        WriteValue<u64>(p,0xA8,(u64)ref.data());
        const auto original=data;
        PrepareBbscBossFogEvent(p,range);
        assert(data==original); // undefeated, with both flags clear
        ludwig_defeat_event=true;
        ludwig_victory=true;
        PrepareBbscBossFogEvent(p,range);
        assert(data==original); // confirmed victory
        ludwig_victory=false;
        PrepareBbscBossFogEvent(p,range);
        assert(data==expected); // preparation runs with detailed logging disabled
        PrepareBbscBossFogEvent(p,range);
        assert(data==expected);
        ludwig_defeat_event=false;
    }
    const u64 args=file+ReadValue<u64>(file,0x78)+ReadValue<u64>(first+0x20,0x10);
    // The common Chalice event substitutes a per-ritual flag into +B8.
    intro=event/100000==129 ? 12906792 : ReadValue<u32>(args,4);
    std::array<u32,2> resolved{256,intro};
    using Bank=u8 PS4_SYSV_ABI (*)(u64,u64);
    using Advance=u8 PS4_SYSV_ABI (*)(u64,u8*);
    const u64 session = ReadValue<u64>(image_base,0x5540290);
    for (auto [role, player] : {std::pair{6,1},std::pair{3,0},std::pair{6,2},std::pair{0,0}})
    for (bool seen : {false,true}) {
        state=role; type=player; introduced=seen;
        WriteValue<s32>(session,0x124,role);
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
        const bool repair=hooked && ((role==6 && player==1) ||
            (event==13404800 && player==0 && (role==0 || role==3)));
        const auto next=!seen ? 2 : repair ? enable : label;
        assert(keep_running==1 && ReadValue<s32>(p,0xA0)==next);
        assert(ReadValue<u64>(p,0xB0)==first+next*0x20);
        if (seen || !hides_fog) continue;

        // Only the first-encounter path reaches the original multiplayer skip.
        // The interpreter resolves +B8 anew; this skip has no slot parameters.
        WriteValue<u64>(p,0xB8,0);
        assert(((Bank)(image_base+0x17bedd0))(0,p)==1);
        assert(((Advance)(image_base+0x12ef2e0))(p+0x80,&keep_running));
        const auto first_geometry = role==6 && !(hooked && player==1) ? 5 : 3;
        if (ReadValue<s32>(p,0xA0)!=first_geometry)
            std::fprintf(stderr,"event %lld, role %d, type %d, hooked %d: step %d, expected %d\n",
                         (long long)event,role,player,hooked,ReadValue<s32>(p,0xA0),first_geometry);
        assert(keep_running==1 && ReadValue<s32>(p,0xA0)==first_geometry);
        assert(ReadValue<u64>(p,0xB0)==first+first_geometry*0x20);
    }
}
void CheckGuest(const char* path, s64 event, u64 row_index, s32 step, u32 flag) {
    std::ifstream script(path,std::ios::binary);
    std::vector<char> data(std::istreambuf_iterator<char>(script), {});
    const u64 file=(u64)data.data();
    const u64 row=file+ReadValue<u64>(file,0x18)+row_index*0x30;
    assert(ReadValue<s64>(row,0)==event);
    const u64 first=file+ReadValue<u64>(file,0x28)+ReadValue<u64>(row,0x10);
    range={first,first+ReadValue<u64>(row,8)*0x20,row,event};
    std::array<u64,2> ref{0,file};
    std::array<u64,26> instance{};
    const u64 p=(u64)instance.data();
    WriteValue<u64>(p,0xA8,(u64)ref.data());
    const u64 args=file+ReadValue<u64>(file,0x78);
    const u64 prior=args+ReadValue<u64>(first+(step-1)*0x20,0x10);
    const u64 battle=args+ReadValue<u64>(first+step*0x20,0x10);
    const auto original=data;
    auto expected=original;
    if (event==13404801) {
        ludwig_defeat_event=true;
        ExpectLudwigVictoryOperand(expected,file,first,2);
    }
    state=0;type=0; // Load in solo, then join in the same map.
    WriteValue<s32>(p,0xA0,2);
    PrepareBbscBossFogEvent(p,range);
    assert(data==original);
    WriteValue<s32>(p,0xA0,0);
    PrepareBbscBossFogEvent(p,range);
    const u64 expected_base=(u64)expected.data();
    if (flag) {
        assert(ReadValue<u64>(battle,0)==ReadValue<u64>(prior,0));
        WriteValue<u64>(expected_base,battle-file,ReadValue<u64>(prior,0));
    } else {
        const u64 count=ReadValue<u64>(row,0x18);
        const u64 param=file+ReadValue<u64>(file,0x58)+ReadValue<u64>(row,0x20)+(count-2)*0x20;
        assert(ReadValue<u64>(param,0x10)==12);
        WriteValue<u64>(expected_base,param+0x10-file,12);
    }
    assert(data!=original);
    assert(data==expected);
    const auto prepared=data;
    state=6;type=1;
    PrepareBbscBossFogEvent(p,range);
    assert(data==prepared);
    ludwig_defeat_event=false;
}
void CheckAll(bool hooked) {
CASES
}
int main() {
    image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);
    assert(image_base);
    Load("bank.bin",image_base+0x17bedd0);
    Load("iterator.bin",image_base+0x12ef2e0);
    Load("role.bin",image_base+0x17b21a0);
    std::array<u8,0x128> session{};
    std::array<u8,0x1700> online{};
    std::array<u8,0x9c> matchmaking{};
    WriteValue<u64>(image_base,0x5540290,(u64)session.data());
    WriteValue<u64>(image_base,0x5556678,(u64)online.data());
    WriteValue<u64>((u64)online.data(),0x16f8,(u64)matchmaking.data());
    WriteValue<s32>((u64)matchmaking.data(),0x98,-1);
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
    assert(Core::InstallGuestCodeHook((void*)(image_base+0x17b21a0),prologue,0,
        BbscGuestRoleGateHook,&bbsc_guest_role_skip));
    CheckAll(true);
GUEST_CASES
}
'''

with tempfile.TemporaryDirectory(prefix='bbsc-fog-retry-') as directory:
    tmp = Path(directory)
    for script, data in scripts.items():
        (tmp / script).write_bytes(data)
    (tmp / 'bank.bin').write_bytes(elf[0x17bedd0:0x17c0384])
    (tmp / 'iterator.bin').write_bytes(elf[0x12ef2e0:0x12ef50b])
    (tmp / 'role.bin').write_bytes(elf[0x17b21a0:0x17b244c])
    cpp = tmp / 'fixture.cpp'
    cpp.write_text(fixture.replace('GUEST_CASES', '\n'.join(
        f'    CheckGuest("{script}",{event},{row},{step},{flag});'
        for event, (script, row, step, flag) in guest_cases.items())).replace('CASES', '\n'.join(
        f'    Check("{script}",{event},{row},{enable},{label},{str(hides).lower()},hooked);'
        for event, (script, row, enable, label, hides) in cases.items())), encoding='utf-8')
    exe = tmp / 'fixture.exe'
    cxx = Path(os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe'))
    subprocess.run([str(cxx), '-std=c++20', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
                    '-I', str(ROOT / 'emulator/src'), '-I', str(ROOT / 'emulator/externals/xbyak'),
                    str(cpp), str(ROOT / 'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe)],
                   check=True, cwd=tmp)
    subprocess.run([str(exe)], check=True, cwd=tmp, timeout=20,
                   env={**os.environ, 'PATH': str(cxx.parent) + os.pathsep + os.environ['PATH']})
print(f'PASS {len(cases)} original boss fog events: guest first entry reaches native disable and retries reach native enable')
print(f'PASS {len(guest_cases)} original guest fog events: current-fight dependency replaced at event start')
print('PASS Ludwig fog: original victory flag used by both entrances, only the intended operands changed')
