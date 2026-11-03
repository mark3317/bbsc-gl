"""Confirmed Blank menu callback: exact native store through production trampoline."""
from pathlib import Path
import os,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a=source.index('void PS4_SYSV_ABI BbscSilenceBeckoningHook(u64, const GuestRegisterSnapshot* registers) {')
b=source.index('\n}',a)+2
code=r'''
#include <windows.h>
#include <atomic>
#include <cassert>
#include <cstring>
#include "core/cpu_patches.h"
using namespace Core;
#define BBSC_MOD
u64 image_base=0;bool enabled=true;
std::atomic<bool> bbsc_beckoning_silenced{false};
namespace BbscMod {u64 EbootAddress(){return image_base;}void LogPlain(const char*){}bool PartyEnabled(){return enabled;}}
FUNCTION
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image_base);
 auto p=(u8*)(image_base+0x1bc6be0);
 // Original RIP-relative load remains in-place; hook only the 10-byte store.
 const u8 native[]={0x48,0x8b,0x05,0x91,0xbc,0x99,0x03,0xc7,0x80,0x74,0x04,0,0,1,0,0,0,0xc3};
 std::memcpy(p,native,sizeof(native));u64 target=image_base+0x1000;
 std::memcpy((void*)(image_base+0x5562878),&target,8);
 assert(InstallGuestCodeHook(p+7,std::span<const u8>{native+7,10},0,BbscSilenceBeckoningHook));
 using Run=void PS4_SYSV_ABI (*)();auto run=(Run)p;
 assert(!bbsc_beckoning_silenced);run();assert(bbsc_beckoning_silenced&&*(u32*)(target+0x474)==1);
 enabled=false;bbsc_beckoning_silenced=false;*(u32*)(target+0x474)=0;run();
 assert(!bbsc_beckoning_silenced&&*(u32*)(target+0x474)==1);
}
'''.replace('FUNCTION',source[a:b])
with tempfile.TemporaryDirectory(prefix='bbsc-target-kick-') as tmp:
    cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe';cpp.write_text(code,encoding='utf-8')
    compiler=os.environ.get('CXX',r'C:\msys64\clang64\bin\clang++.exe')
    subprocess.run([compiler,'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
        '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),str(cpp),
        str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env['PATH']
    subprocess.run([str(exe)],check=True,env=env,timeout=10)
print('PASS: confirmed silence native store and callback, disabled-party preservation')
