"""Personal NPC dispatchers use native local event execution, never custom stage gates.

Allocated memory only. Execute the original 1.09 event sender to verify that
production localization prevents remote instruction-pointer overrides.
Usage: python tools/test_personal_npc_dispatch.py <original analysis ELF>
"""
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
header = (ROOT / 'emulator/src/core/bbsc_quest_reward_rules.h').read_text(encoding='utf-8')
controllers = sorted(set(map(int, re.findall(r'Native state dispatcher (\d+),', header))))
assert len(controllers) == 19 and 12410760 in controllers

def function(signature):
    begin = source.index(signature + ' {')
    end = source.index('{', begin) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[begin:end] + '\n'

data = Path(sys.argv[1]).read_bytes()
ph = struct.unpack_from('<Q', data, 32)[0]
size, count = struct.unpack_from('<HH', data, 54)
segments = [struct.unpack_from('<II6Q', data, ph + i * size) for i in range(count)]
def read(address, length):
    for kind, _, offset, virtual, _, size, _, _ in segments:
        if kind == 1 and virtual <= address and address + length <= virtual + size:
            return data[offset + address - virtual:offset + address - virtual + length]
    raise AssertionError(hex(address))

# Complete original event progress sender. All branches and native channel31
# construction remain intact; redirect only external leaf calls/global storage.
native = read(0x12EE540, 0x119)
assert native[0x1F:0x29] == bytes.fromhex('80 7f 78 00 0f 84 cb 00 00 00')
import capstone
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
cs.detail = True
assert len(list(cs.disasm(native, 0x12EE540))) > 50

code = r'''
#define NOMINMAX
#include <windows.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>
#include <map>
#include <vector>
#include "core/bbsc_quest_event_rules.h"
namespace QuestRules=Core::Bloodborne::QuestRules;
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s64=int64_t;
#define BBSC_PERF_NESTED(...)
enum class MemoryProt{CpuRead,CpuWrite};
bool ReadablePointer(u64 p,size_t){return p!=0;}
bool HasMemoryAccess(u64 p,size_t,MemoryProt){return p!=0;}
template<class T>T ReadValue(u64 p,size_t off){T v;memcpy(&v,(void*)(p+off),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t off,T v){memcpy((void*)(p+off),&v,sizeof(v));}
int sends=0;u32 sent_event=0;
bool __attribute__((sysv_abi)) MemberIsSelf(u64){return false;}
int __attribute__((sysv_abi)) Send(u64,u64,u32 channel,const u8* p,u32 size){
 assert(channel==0x31&&size==0x18);++sends;memcpy(&sent_event,p+8,4);return 1;
}
void Jump(u64 at,u64 target){const u8 op[]={0xff,0x25,0,0,0,0};memcpy((void*)at,op,6);memcpy((void*)(at+6),&target,8);}
'''
code += function('bool IsBbscLocalQuestEvent(s64 event)')
# Only the existing production personal-event classifier calls this rule.
assert 'IsBbscLocalQuestEvent(event)' in function('bool IsBbscPersonalMapEvent(s64 event)')
code += 'bool IsBbscPersonalMapEvent(s64 e){return IsBbscLocalQuestEvent(e);}\n'
code += 'bool IsBbscChaliceBossRewardEvent(s64){return false;}\n'
start = source.index('struct BbscQuestRange {')
code += source[start:source.index('\nbool BbscTalkEventIsOurs', start)]
code += 'int main(){\n'
code += 'u64 base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(base);\n'
code += 'const u8 original[]={' + ','.join(map(str, native)) + '};\n'
code += 'memcpy((void*)(base+0x12EE540),original,sizeof(original));\n'
# Original RIP-relative references use the same offsets in the allocated image.
# A fake stack-guard, manager and transport are the only globals it reads.
rip_targets = []
for instruction in cs.disasm(native, 0x12EE540):
    for operand in instruction.operands:
        if operand.type == capstone.x86.X86_OP_MEM and operand.mem.base == capstone.x86.X86_REG_RIP:
            rip_targets.append(instruction.address + instruction.size + operand.mem.disp)
guard = rip_targets[0]
assert rip_targets[-1] == guard
code += f'WriteValue<u64>(base,{guard},base+0x1000);\n'
code += f'WriteValue<u64>(base,{rip_targets[1]},base+0x2000);\n'
code += f'WriteValue<u64>(base,{rip_targets[2]},base+0x3000);\n'
code += r'''
WriteValue<u64>(base+0x3000,0xF8,base+0x4000);WriteValue<u64>(base+0x3000,0x100,base+0x4020);
Jump(base+0xCA1670,(u64)&MemberIsSelf);Jump(base+0x17894E0,(u64)&Send);
alignas(16) std::array<u8,0xC0> instance{};
alignas(16) std::array<u8,0x400> file{};
std::array<u64,2> ref{0,(u64)file.data()};u32 condition_bits=0;
u64 inst=(u64)instance.data(),f=(u64)file.data();
WriteValue<u64>(inst,0x20,(u64)&condition_bits);WriteValue<u64>(inst,0xA8,(u64)ref.data());
WriteValue<u64>(f,0x10,1);WriteValue<u64>(f,0x18,0xA0);WriteValue<u64>(f,0x28,0x100);
WriteValue<u64>(f,0xA8,3);WriteValue<u64>(f,0xB0,0);
using NativeSend=void __attribute__((sysv_abi)) (*)(u64);
auto send=(NativeSend)(base+0x12EE540);
'''
code += 'for(s64 event:{' + ','.join(map(str, controllers)) + '}){\n'
code += r'''
 assert(IsBbscLocalQuestEvent(event)); // FAILS old production catalogue
 bbsc_quest_indexes.clear();bbsc_quest_instances.clear();WriteValue<s64>(f,0xA0,event);
 WriteValue<u32>(inst,0x28,(u32)event);
 // Same event before localization broadcasts native progress to the peer.
 instance[0x78]=1;int before=sends;send(inst);assert(sends==before+1&&sent_event==event);
 for(u64 offset:{0x100ull,0x120ull,0x140ull}){
  WriteValue<u64>(inst,0xB0,f+offset);instance[0x78]=1;auto unchanged=instance;
  LocalizeBbscQuestEvent(inst);assert(instance[0x78]==0);unchanged[0x78]=0;
  assert(instance==unchanged);send(inst);assert(sends==before+1);
 }
}
// Shared boss/ordinary enemy events must retain their original networking;
// a reused instance may not inherit the last personal dispatcher's permission.
for(s64 event:{12401800,12415200,12500810}){
 assert(!IsBbscLocalQuestEvent(event));WriteValue<s64>(f,0xA0,event);instance[0x78]=1;
 LocalizeBbscQuestEvent(inst);assert(instance[0x78]==1);
 int before=sends;send(inst);assert(sends==before+1);
}
VirtualFree((void*)base,0,MEM_RELEASE);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-personal-npc-dispatch-') as temporary:
    folder = Path(temporary)
    cpp, exe = folder / 'test.cpp', folder / 'test.exe'
    cpp.write_text(code, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler, '-std=c++20', '-I', str(ROOT / 'emulator/src'), str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], env=env, check=True, timeout=10)
print('PASS: 19 personal NPC dispatchers, production localization, original native channel31 sender, shared-event exclusions')
