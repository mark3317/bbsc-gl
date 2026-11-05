"""Native death-worker bytes + production hooks; artificial actors only.

python -B tools/test_native_enemy_loot.py ../../out/exit-study.elf
The downstream native roll/body constructor is mocked; no game or saves run.
"""
from pathlib import Path
import os
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')


def function(signature):
    a = source.index(signature + ' {')
    b = source.index('{', a) + 1
    depth = 1
    while depth:
        depth += (source[b] == '{') - (source[b] == '}')
        b += 1
    return source[a:b]


elf = Path(sys.argv[1]).read_bytes()
ph = struct.unpack_from('<Q', elf, 32)[0]
size, count = struct.unpack_from('<HH', elf, 54)
segments = [struct.unpack_from('<IIQQQQQQ', elf, ph + i * size) for i in range(count)]


def read(a, n):
    for t, _, o, v, _, s, _, _ in segments:
        if t == 1 and v <= a and a + n <= v + s:
            return elf[o + a - v:o + a - v + n]
    raise ValueError(hex(a))


worker = read(0x18C4F90, 0xE0)
assert read(0x18C5002, 7) == bytes.fromhex('83 b8 f8 00 00 00 00')
assert read(0x18C5009, 2) == bytes.fromhex('7e 52')
assert read(0x18C502E, 5) == bytes.fromhex('e8 7d 80 f1 ff')
assert read(0x18C504A, 7) == bytes.fromhex('48 81 ca 00 20 02 00')
filter_bytes = read(0x17DD193, 6)
assert filter_bytes == bytes.fromhex('88 8d f8 fd ff ff')
# Full native result branch bypasses the guest-only category/guest-drop filter.
native = read(0x17DD0B0, 0xB70)
assert bytes.fromhex('80 bd f8 fd ff ff 00') in native
assert read(0x17DD562, 5) == bytes.fromhex('e8 d9 f4 73 00')  # native lot roll
assert read(0x17DDB8C, 5) == bytes.fromhex('e8 8f 77 ff ff')  # body-item constructor
accept = read(0x17DD75D, 13)
assert accept == bytes.fromhex('80 bd f8 fd ff ff 00 0f 84 3a 02 00 00')
assert 'NoteBbscGuestEnemyDeath' not in source and 'bbsc_guest_drop_queue' not in source
assert 'TickBbscGuestDrops' not in source

code = r'''
#include <windows.h>
#include <array>
#include <atomic>
#include <cassert>
#include <cstring>
#include <set>
#include "core/cpu_patches.h"
using Core::GuestRegisterSnapshot;using Core::InstallGuestCodeHook;
#define BBSC_TIMELINE(...)
u64 base=0;
namespace BbscMod{u64 EbootAddress(){return base;}void LogPlain(const char*){}}
bool guest=true,allowed=true,enabled=true;int player_type=1;
bool bbsc_native_enemy_loot_ready=true;
std::set<std::pair<u64,u32>> bbsc_native_loot_deaths;
u32 bbsc_native_loot_generation=~u32{0};std::atomic<u32> bbsc_load_generation{0};
bool EnvFlagEnabled(const char*){return enabled;}
bool BbscGuestInHostWorld(){return guest;}
int GetLocalPlayerType(){return player_type;}
bool BbscNpcActorRewardAllowed(u64){return allowed;}
void RestoreBbscNativeLootReceipts(bool=false){}
bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
template<class T>void put(u64 p,size_t o,T v){memcpy((void*)(p+o),&v,sizeof(v));}
''' + function('void PS4_SYSV_ABI BbscNativeEnemyLootHook(u64 tag, const GuestRegisterSnapshot* registers)') + r'''
u64 info[2]{};int rolls=0,bodies=0;u8 filter_frame[0x220]{};
using Filter=u64 PS4_SYSV_ABI (*)(u64,u64);Filter filter;
u64 PS4_SYSV_ABI Info(u64){return (u64)info;}
void PS4_SYSV_ABI NativeRollBody(u64,u32,u64){
 ++rolls;
 // One native result (e.g. Yurie, a rune, gear, or mixed supplies) is kept in
 // full. Guest-filter true would retain only native guest-eligible entries.
 filter((u64)filter_frame,0xA501);
 if(filter_frame[0]==0)++bodies;
}
void stub(u64 off,u64 target){u8 b[12]={0x48,0xb8};memcpy(b+2,&target,8);b[10]=0xff;b[11]=0xe0;memcpy((void*)(base+off),b,12);}
int main(){
 base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(base);
 const u8 worker[]={WORKER};memcpy((void*)(base+0x18c4f90),worker,sizeof(worker));
 alignas(16) u8 actor[0x400]{},row[0x160]{},root[0x100]{},local[0x400]{},module[0x30]{},life[0x100]{};
 u64 vt[0x40]{};vt[0x168/8]=(u64)Info;put((u64)actor,0,(u64)vt);put((u64)actor,8,u32{0x123456});info[1]=(u64)row;
 put(base,0x553e878,(u64)root);put((u64)root,0x60,(u64)local);
 put((u64)local,0x3b0,(u64)module);put((u64)module,0x20,(u64)life);
 put(base,0x553d6e0,u64{0x123});stub(0x17dd0b0,(u64)NativeRollBody);
 // Native filter MOV, with an artificial frame/epilogue; RCX upper bits stay intact.
 const u8 fw[]={0x55,0x48,0x8d,0xaf,0x08,0x02,0,0,0x48,0x89,0xf1,
               0x88,0x8d,0xf8,0xfd,0xff,0xff,0x48,0x89,0xc8,0x5d,0xc3};
 memcpy((void*)(base+0x1000),fw,sizeof(fw));filter=(Filter)(base+0x1000);
 using Worker=void PS4_SYSV_ABI (*)(u64);auto run=(Worker)(base+0x18c4f90);
 put((u64)life,0xf8,s32{0});run((u64)actor);assert(rolls==0); // original simultaneous-death failure
 assert(InstallGuestCodeHook((void*)(base+0x18c5002),std::span<const u8>{worker+0x72,7},0,BbscNativeEnemyLootHook));
 assert(InstallGuestCodeHook((void*)(base+0x100b),std::span<const u8>{fw+11,6},1,BbscNativeEnemyLootHook));
 run((u64)actor);assert(rolls==1&&bodies==1);assert(ReadValue<s32>((u64)life,0xf8)==0);
 assert((ReadValue<u32>((u64)actor,0x1e1)&0x22000)==0x22000);
 for(int i=0;i<5;++i)run((u64)actor);assert(rolls==1&&bodies==1); // no reroll
 put((u64)life,0xf8,s32{100});run((u64)actor);assert(rolls==1); // guest respawn alone not new loot
 put((u64)actor,0x1e1,u32{0});run((u64)actor);assert(rolls==2); // real enemy respawn may drop again
 put((u64)actor,0x1e1,u32{0});put((u64)actor,8,u32{0x654321});run((u64)actor);assert(rolls==3);
 put((u64)actor,0x1e1,u32{0});allowed=false;run((u64)actor);assert(rolls==3);allowed=true;
 // Original native ownership/exclusion and missing-param guards still execute.
 put((u64)actor,0x1e1,u32{0x220000});run((u64)actor);assert(rolls==3);
 put((u64)actor,0x1e1,u32{0});info[1]=0; // Info itself non-null; native producer owns row validation
 info[1]=(u64)row;
 for(int type:{0,2,3}){player_type=type;put((u64)life,0xf8,s32{0});run((u64)actor);assert(rolls==3);}player_type=1;
 guest=false;run((u64)actor);assert(rolls==3);assert(filter((u64)filter_frame,0xA501)==0xA501);guest=true;
 bbsc_native_enemy_loot_ready=false;run((u64)actor);assert(rolls==3);bbsc_native_enemy_loot_ready=true;
 assert(filter((u64)filter_frame,0xA501)==0xA500);
 // Actual native branch jumps straight to accepting the original rolled
 // entry when the guest filter is off; it does not roll a second time.
 const u8 accept[]={ACCEPT};
 const u8 prefix[]={0x55,0x48,0x8d,0xaf,0x08,0x02,0,0};
 memcpy((void*)(base+0x2000),prefix,sizeof(prefix));
 memcpy((void*)(base+0x2008),accept,sizeof(accept));
 const u8 yes[]={0xb8,1,0,0,0,0x5d,0xc3},no[]={0x31,0xc0,0x5d,0xc3};
 memcpy((void*)(base+0x2008+13),no,sizeof(no));
 memcpy((void*)(base+0x2008+13+0x23a),yes,sizeof(yes));
 using Accept=int PS4_SYSV_ABI (*)(u64);auto accepts=(Accept)(base+0x2000);
 assert(accepts((u64)filter_frame)==1);
 filter_frame[0]=1;assert(accepts((u64)filter_frame)==0);filter_frame[0]=0;
 // New loaded actor/item tree, and independent client process state.
 run((u64)actor);assert(rolls==4);
 ++bbsc_load_generation;run((u64)actor);assert(rolls==4); // reload counter alone cannot unlock native latch
 put((u64)actor,0x1e1,u32{0});run((u64)actor);assert(rolls==5); // fresh native actor tree
 put((u64)actor,0x1e1,u32{0});run((u64)actor);assert(rolls==6); // independent client state
}
'''
code = code.replace('WORKER', ','.join(hex(x) for x in worker))
code = code.replace('ACCEPT', ','.join(hex(x) for x in accept))
with tempfile.TemporaryDirectory(prefix='bbsc-native-enemy-loot-') as folder:
    cpp = Path(folder) / 'test.cpp'
    exe = cpp.with_suffix('.exe')
    cpp.write_text(code, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler, '-std=c++20', '-O0', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
                    '-I', str(ROOT / 'emulator/src'), '-I', str(ROOT / 'emulator/externals/xbyak'),
                    str(cpp), str(ROOT / 'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], env=env, check=True, timeout=15)
print('PASS: actual native death worker + production trampolines: simultaneous death, '
      'repeat/respawn/incarnation/load, quest/role/ownership guards; native roll/body call sites; no BBSC parallel roll')
