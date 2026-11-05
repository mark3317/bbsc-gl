"""Read-only native award permission study (enemy queue removed in native migration).

Usage: python -B tools/test_native_loot_study.py ../../out/exit-study.elf
Only artificial memory and a temporary executable are used. No saves are opened.
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
    start = source.index(signature + ' {')
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


elf = Path(sys.argv[1]).read_bytes()
phoff = struct.unpack_from('<Q', elf, 32)[0]
size, count = struct.unpack_from('<HH', elf, 54)
segments = [struct.unpack_from('<IIQQQQQQ', elf, phoff + i * size) for i in range(count)]


def read(address, length):
    for kind, _, offset, virtual, _, size, _, _ in segments:
        if kind == 1 and virtual <= address and address + length <= virtual + size:
            return elf[offset + address - virtual:offset + address - virtual + length]
    raise ValueError(hex(address))


# Exact native permission branch. AL is the permission computed immediately
# above; R14B is the third AwardItemLot argument. Keep both original jumps.
gate = read(0x17DDD2F, 0x17DDD44 - 0x17DDD2F)
assert gate == bytes.fromhex('84 c0 48 8d 05 f8 d3 d5 03 75 0a 41 80 f6 01 0f 84 8f 07 00 00')
assert read(0x17DDC64, 3) == bytes.fromhex('41 89 d6')  # mov r14d, edx
assert read(0x17DE336, 5) == bytes.fromhex('e8 b5 a6 ff ff')  # call native give

fixture = r'''
#include <windows.h>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <mutex>
#include <utility>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;
#define BBSC_PERF_NESTED(...)
int main(){
 // Execute actual native branch bytes, with synthetic return markers at its
 // continuation/early-return destinations. No other game code is executed.
 auto* mem=(u8*)VirtualAlloc(nullptr,0x2000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(mem);
 const u8 wrapper[]={0x41,0x56,0x89,0xf8,0x41,0x89,0xf6,0xe8,0,0,0,0,0x41,0x5e,0xc3};
 memcpy(mem,wrapper,sizeof(wrapper));int32_t rel=0x100-12;memcpy(mem+8,&rel,4);
 const u8 gate[]={GATE_BYTES};memcpy(mem+0x100,gate,sizeof(gate));
 const u8 yes[]={0xb8,1,0,0,0,0xc3},no[]={0x31,0xc0,0xc3};
 memcpy(mem+0x100+sizeof(gate),yes,sizeof(yes));
 memcpy(mem+0x100+0x17de4d3-0x17ddd2f,no,sizeof(no));
 FlushInstructionCache(GetCurrentProcess(),mem,0x2000);
 using Check=int __attribute__((sysv_abi)) (*)(int,int);auto check=(Check)mem;
 assert(check(0,0)==1);assert(check(0,1)==0);
 assert(check(1,0)==1);assert(check(1,1)==1);
 VirtualFree(mem,0,MEM_RELEASE);
}
'''
fixture = fixture.replace('GATE_BYTES', ','.join(hex(byte) for byte in gate))
with tempfile.TemporaryDirectory(prefix='bbsc-native-loot-study-') as directory:
    cpp = Path(directory) / 'study.cpp'
    exe = cpp.with_suffix('.exe')
    cpp.write_text(fixture, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler, '-std=c++20', '-O0', str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], env=env, check=True, timeout=15)
print('STUDY PASS: actual native award permission branch, 4 argument combinations')
