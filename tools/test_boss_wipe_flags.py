"""Run the boss wipe reset with the original flag writer and EMEVD."""
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/gamedata'))
from emevd import Emevd

SOURCE = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')


def function(signature):
    start = SOURCE.index(signature + ' {')
    end = SOURCE.index('{', start) + 1
    depth = 1
    while depth:
        depth += (SOURCE[end] == '{') - (SOURCE[end] == '}')
        end += 1
    return SOURCE[start:end] + '\n'


events = dict(Emevd(Path(sys.argv[1]) / 'event/m24_00_00_00.emevd.dcx').events)
actor = 2400800
start = events[12404802]
assert start[1] == (2004, 1, struct.pack('<II', actor, 0))
assert start[4] == (3, 0, struct.pack('<II', 0x100, 12404800))
assert start[6] == (1003, 1, struct.pack('<II', 0x101, 12404223))
assert start[28] == (2004, 1, struct.pack('<II', actor, 1))
assert events[12404841][17] == (2003, 2, struct.pack('<II', 12404801, 1))
assert events[12404840][1] == (1003, 101, struct.pack('<II', 0x100, 12401802))

mensis = dict(Emevd(Path(sys.argv[1]) / 'event/m26_00_00_00.emevd.dcx').events)
setup = mensis[12604852]
assert setup[3:5] == [(1003, 101, struct.pack('<II', 0x10100, 0)),
                     (3, 0, struct.pack('<II', 0x100, 12604850))]
assert mensis[12604861][17] == (2003, 2, struct.pack('<II', 12604851, 1))
phase = mensis[12604856]
assert phase[2] == (1003, 101, struct.pack('<II', 0x10100, 0))
assert phase[6] == (3, 0, struct.pack('<II', 0x100, 12604986))
assert phase[10] == (1014, 0, b'')
assert phase[13] == (2003, 22, struct.pack('<III', 12604949, 12604959, 0))
assert phase[17] == (2005, 3, struct.pack('<II', 2601851, 0))
assert mensis[12604877][13] == (2003, 22, struct.pack('<III', 12604940, 12604946, 0))
assert mensis[12604986][3] == (2003, 8, struct.pack('<III', 12604985, 0, 0))

with Path(sys.argv[2]).open('rb') as elf:
    elf.seek(0x4000 + 0x013CFCC0)
    writer = elf.read(0xB1)
assert writer[:6] == bytes.fromhex('41 89 d0 8b 4f 1c') and writer[-1] == 0xC3

code = r'''
#define NOMINMAX
#include <windows.h>
#include <atomic>
#include <cassert>
#include <mutex>
#include "core/bbsc_world_control.h"
namespace World = Core::Bloodborne::World;
using u8=uint8_t; using u32=uint32_t; using u64=uint64_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define BBSC_TIMELINE(...)
std::mutex bbsc_world_presence_mutex;
World::Presence bbsc_world_presence_local;
std::atomic<u64> bbsc_world_native_load{1};
constexpr u64 EventFlagManPointerOffset=0x0553B100;
u64 image_base;
bool ReadablePointer(u64 p,size_t) { return p != 0; }
template<class T> T ReadValue(u64 p,size_t off) {
    T value; std::memcpy(&value,(const void*)(p+off),sizeof(value)); return value;
}
void Store(u64 p,size_t off,auto value) { std::memcpy((void*)(p+off),&value,sizeof(value)); }
std::array<u8,125> progress,attempt;
u32 attempt_group=12404;
void SetFixtureFlag(std::array<u8,125>& bank,u32 flag) {
    bank[flag%1000/8] |= 0x80 >> (flag%8);
}
bool BbscEventFlag(u32 flag) {
    const auto& bank=flag/1000==attempt_group?attempt:progress;
    return (bank[flag%1000/8] & (0x80 >> (flag%8))) != 0;
}
'''
code += SOURCE[SOURCE.index('World::Scope bbsc_boss_wipe_scope{};'):
               SOURCE.index('std::atomic<u64> bbsc_world_load_pending')]
array_name = SOURCE.index('BbscEncounterProgressFlags{')
code += SOURCE[SOURCE.rindex('constexpr std::array<', 0, array_name):
               SOURCE.index('bool BbscSharedMapProgressAllowed(')]
code += r'''
int main() {
    image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);
    assert(image_base);
    const u8 writer[]={NATIVE_WRITER};
    std::memcpy((void*)(image_base+0x013CFCC0),writer,sizeof(writer));
    std::array<u8,0x40> manager{},head{},node{};
    Store(image_base,EventFlagManPointerOffset,(u64)manager.data());
    Store((u64)manager.data(),0x1c,1000u);
    Store((u64)manager.data(),0x38,(u64)head.data());
    head[0x19]=1;
    Store((u64)head.data(),8,(u64)node.data());
    Store((u64)node.data(),0,(u64)head.data());
    Store((u64)node.data(),0x10,(u64)head.data());
    Store((u64)node.data(),0x20,12404u);
    Store((u64)node.data(),0x28,2u);
    Store((u64)node.data(),0x30,(u64)attempt.data());
    attempt[27]=3; attempt[100]=0xf0;
    progress[100]=0xa0;
    auto& local=bbsc_world_presence_local;
    local.world={11,99}; local.map=0x18000000;
    MarkBbscBossWipeLoad();
    ResetBbscWipeEncounterAtSpawn(local.map); // still on the dying visit
    ++bbsc_world_native_load;
    ResetBbscWipeEncounterAtSpawn(0x18010000); // a different destination
    ++local.world.room;
    ResetBbscWipeEncounterAtSpawn(local.map); // another room
    --local.world.room;
    assert(attempt[27]==3 && attempt[100]==0xf0);
    ResetBbscWipeEncounterAtSpawn(local.map);
    assert(attempt[27]==2 && attempt[100]==0x10);
    assert(BbscEventFlag(12401800) && BbscEventFlag(12401802));
    ++bbsc_world_native_load;
    attempt[100]=0xe0;
    ResetBbscWipeEncounterAtSpawn(local.map); // later ordinary arrival
    assert(attempt[100]==0xe0);

    local.map=0x1a000000;
    attempt_group=12604;
    Store((u64)node.data(),0x20,attempt_group);
    attempt.fill(0);
    progress.fill(0);
    SetFixtureFlag(progress,12601852); // Micolash's introduction
    SetFixtureFlag(attempt,12604800); // Wet Nurse arena
    SetFixtureFlag(attempt,12604960); // neighbouring event
    constexpr std::array micolash_flags{
        12604850u,12604851u,12604852u,12604856u,
        12604940u,12604941u,12604942u,12604943u,12604944u,12604945u,12604946u,
        12604949u,12604950u,12604951u,12604952u,12604953u,12604954u,12604955u,
        12604956u,12604957u,12604958u,12604959u,12604985u,12604986u,
    };
    for (u32 flag : micolash_flags) SetFixtureFlag(attempt,flag);
    const auto previous_attempt=attempt;
    ResetBbscWipeEncounterAtSpawn(local.map); // no wipe in this map yet
    MarkBbscBossWipeLoad();
    ++bbsc_world_native_load;
    ResetBbscWipeEncounterAtSpawn(0x18000000); // another destination
    assert(attempt==previous_attempt);

    ResetBbscWipeEncounterAtSpawn(local.map);
    for (u32 flag : micolash_flags) assert(!BbscEventFlag(flag));
    assert(BbscEventFlag(12601852) && BbscEventFlag(12604800) && BbscEventFlag(12604960));

    auto stale_snapshot=previous_attempt;
    KeepBbscEncounterFlags(attempt_group,attempt.data(),stale_snapshot.data());
    assert(stale_snapshot==attempt);

    attempt=previous_attempt;
    SetFixtureFlag(progress,12601850);
    MarkBbscBossWipeLoad(); // a later wipe in Mensis after Micolash is defeated
    ++bbsc_world_native_load;
    ResetBbscWipeEncounterAtSpawn(local.map);
    assert(attempt==previous_attempt && BbscEventFlag(12601850));
}
'''.replace('NATIVE_WRITER', ','.join(map(str, writer)))

with tempfile.TemporaryDirectory(prefix='bbsc-wipe-flags-') as tmp:
    cpp, exe = Path(tmp) / 'wipe.cpp', Path(tmp) / 'wipe.exe'
    cpp.write_text(code, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    env = dict(os.environ, PATH=str(Path(compiler).parent) + os.pathsep + os.environ['PATH'])
    subprocess.run([compiler, '-std=c++20', '-I', str(ROOT / 'emulator/src'), str(cpp),
                    '-o', str(exe)], check=True, env=env)
    subprocess.run([str(exe)], check=True, env=env)
print('PASS original Amelia and Micolash EMEVD and native SetFlag: scoped wipe reset, stale snapshots, and permanent progress')
