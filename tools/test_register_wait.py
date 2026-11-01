"""Execute the native wait predicate through the production Windows trampoline."""
from pathlib import Path
import os
import subprocess

root = Path(__file__).resolve().parents[1]
source = (root/'emulator/mod/bbsc_register.cpp').read_text(encoding='utf8')
a = source.index('void PS4_SYSV_ABI RegisterWaitHook(')
b = source.index('std::vector<Rank> Snapshot()', a)
# Native 1B33190..1B331D6: internal branches only, no RIP references/calls.
native = bytes.fromhex('488b4708488d88f80d0000f7d94883e107488d8c08f80d0000488b802011000048c1e004488d14800f1f840000000000b0014885d2740f4883c2b0803900488d495075ec31c0c3')
elf = root.parents[1]/'out/register-study.elf'
if elf.exists():
    import capstone
    data = elf.read_bytes()
    actual = data[0x1B33190+0x4000:0x1B331D7+0x4000]
    assert len(actual) == 71
    assert actual[:11].hex() == '488b4708488d88f80d0000'
    instructions = list(capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64).disasm(actual,0x1B33190))
    assert instructions[-1].mnemonic == 'ret'
    assert not any('rip' in i.op_str or i.mnemonic=='call' for i in instructions)
    native = actual

fixture = r'''
#include <windows.h>
#include <atomic>
#include <cassert>
#include <cstring>
#include <cstdio>
#include "core/cpu_patches.h"
#include "bbsc_register_wait.h"
u64 image=0;
std::atomic<bool> ready{true};
std::atomic<u32> book_generation{1};
std::atomic<u64> book_page_result{0};
u8 register_wait_skip=0;
namespace BbscMod {
u64 EbootAddress(){return image;}
void LogPlain(const char* text){std::puts(text);}
}
bool ReadSlotSafely(u64 at,u64* value){SIZE_T n=0;return ReadProcessMemory(GetCurrentProcess(),(void*)at,value,8,&n)&&n==8;}
using BbscMod::RegisterWaitCanFinish;
''' + source[a:b] + r'''
const u8 native_code[]={NATIVE_BYTES};
int main(){
 image=(u64)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(image);
 auto* code=(u8*)image;std::memcpy(code,native_code,sizeof native_code);
 const u64 owner=image+0x10000, start=(owner+0xDF8+7)&~u64{7};
 u64 functor[2]={0,owner};
 auto board=(u32*)(owner+0x2858);auto count=(u64*)(owner+0x1120);
 *board=19;*count=10;
 auto rows=[&](u32 n){for(u32 i=0;i<10;++i)*(u8*)(start+i*0x50)=i<n?1:0;};
 using Predicate=u64 PS4_SYSV_ABI (*)(u64);
 auto poll=(Predicate)code;
 rows(2);assert((poll((u64)functor)&255)==0);
 const std::array<u8,11> expected{0x48,0x8B,0x47,0x08,0x48,0x8D,0x88,0xF8,0x0D,0,0};
 assert(Core::InstallGuestCodeHook(code,expected,0,RegisterWaitHook,&register_wait_skip));
 auto result=[&](bool done,u32 n,u32 generation=1){book_page_result=((u64)generation<<32)|(done?0x80000000ULL:0)|n;};
 result(false,2);assert((poll((u64)functor)&255)==0);
 result(true,2);rows(1);assert((poll((u64)functor)&255)==0);
 rows(2);assert((poll((u64)functor)&255)==1&&register_wait_skip==0);
 *board=18;assert((poll((u64)functor)&255)==0&&register_wait_skip==0);
 *board=19;book_generation=2;assert((poll((u64)functor)&255)==0);
 book_generation=1;result(true,5);rows(4);assert((poll((u64)functor)&255)==0);
 rows(5);assert((poll((u64)functor)&255)==1);
 result(true,0);rows(0);assert((poll((u64)functor)&255)==1);
 assert(!RegisterWaitCanFinish(owner,6,true,ReadSlotSafely));
 *count=11;assert(!RegisterWaitCanFinish(owner,2,true,ReadSlotSafely));
 *count=10;result(true,2);rows(2);ready=false;assert((poll((u64)functor)&255)==0);
 ready=true;assert((poll((u64)functor)&255)==1);
}
'''
fixture = fixture.replace('NATIVE_BYTES',','.join(hex(v) for v in native))
build = root/'build'
cpp = build/'test_register_wait.cpp'
exe = cpp.with_suffix('.exe')
cpp.write_text(fixture,encoding='utf8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
                '-I',str(root/'emulator/src'),'-I',str(root/'emulator/mod'),
                '-I',str(root/'emulator/externals/xbyak'),str(cpp),str(root/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
env=dict(os.environ)
env['PATH']='C:/msys64/clang64/bin;'+env.get('PATH','')
subprocess.run([str(exe)],env=env,check=True,timeout=15)
print('PASS: actual native predicate + production trampoline: pending/ready, 2/5 real rows and empty tail, empty result, stale opening, other boards, disabled provider, entry skip')
