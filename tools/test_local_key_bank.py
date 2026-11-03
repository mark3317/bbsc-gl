"""Exercise the production hook and native bank switch (read-only ELF argument)."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
start = source.index('void PS4_SYSV_ABI BbscLocalKeyBankHook(')
end = source.index('\nvoid InstallBbscLocalKeyBankHook()', start)
hook = source[start:end]
elf = Path(sys.argv[1]).read_bytes()[0x4000:]
assert elf[0x1ac5600:0x1ac5606] == bytes.fromhex('554889e54157')
assert elf[0x1937a8b:0x1937a9c] == bytes.fromhex('488dbb38030000be01000000e864db1800')
native = elf[0x1ac5600:0x1ac571b]
code = r'''
#include <windows.h>
#include <cassert>
#include <cstdint>
#include <cstring>
using u64=uint64_t; using u32=uint32_t;
#define PS4_SYSV_ABI
struct GuestRegisterSnapshot {u64 rdi=0,rsi=0;};
u64 bag=0;
u64 BbscCarriedInventory(){return bag;}
''' + hook + r'''
int main(){
 auto* image=(unsigned char*)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);
 assert(image);
 unsigned char native[]={NATIVE_BYTES};
 memcpy(image+0x1ac5600,native,sizeof(native));
 uint64_t guard=0;
 uint64_t guard_ptr=(uint64_t)&guard;memcpy(image+0x53e3be0,&guard_ptr,8);
 for(auto off:{0x1ac5720,0x1a8bed0,0x1a8bc00}) image[off]=0xc3;
 alignas(16) unsigned char inv[0xa0]={};
 alignas(16) uint32_t home[4]={0xb0001000,0x40001000,1,0}, phantom[4]={};
 auto put64=[&](int off,u64 v){memcpy(inv+off,&v,8);};
 auto put32=[&](int off,u32 v){memcpy(inv+off,&v,4);};
 put32(0x24,1);put64(0x28,(u64)home);put64(0x38,(u64)phantom);
 bag=(u64)inv;
 using Switch=void (__attribute__((sysv_abi)) *)(void*,int);
 auto run=(Switch)(image+0x1ac5600);
 auto call=[&](bool fixed,int mode){GuestRegisterSnapshot r{bag+0x10,(u64)mode};if(fixed)BbscLocalKeyBankHook(0,&r);run((void*)r.rdi,(int)r.rsi);};
 // Baseline really selects then clears phantom keys at every initialization.
 phantom[0]=0xb0001001;phantom[1]=0x40001001;phantom[2]=1;
 call(false,1);assert(phantom[0]==0 && *(u64*)(inv+0x58)==(u64)phantom);
 // Production fix selects the home bank before first summon, then keeps pickups
 // through repeated death/follow/rejoin initialization and native home selection.
 for(int load=0;load<5;++load){call(true,1);assert(*(u64*)(inv+0x58)==(u64)home);assert(home[0]==0xb0001000 && home[2]==1);}
 call(true,0);assert(*(u64*)(inv+0x58)==(u64)home);
 // No removal guard: an NPC-consumed key stays absent after the next load.
 home[0]=0;home[2]=0;call(true,1);assert(home[0]==0 && home[2]==0);
 // Storage, remote inventories, null and unrelated arguments pass through.
 GuestRegisterSnapshot other{bag+0x20,1};BbscLocalKeyBankHook(0,&other);assert(other.rsi==1);
 bag=0;other={0x10,1};BbscLocalKeyBankHook(0,&other);assert(other.rsi==1);
 BbscLocalKeyBankHook(0,nullptr);
 VirtualFree(image,0,MEM_RELEASE);
}
'''
code = code.replace('NATIVE_BYTES', ','.join(hex(b) for b in native))
code = code.replace('#include <cstring>', '#include <cstring>\n#include <initializer_list>')
with tempfile.TemporaryDirectory(prefix='bbsc-key-bank-') as tmp:
    cpp, exe = Path(tmp)/'test.cpp', Path(tmp)/'test.exe'
    cpp.write_text(code, encoding='utf-8')
    compiler = os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],check=True,env=env,timeout=10)
print('PASS: native baseline clears phantom keys; production hook retains local keys across reloads, permits consumption, ignores other inventories')
