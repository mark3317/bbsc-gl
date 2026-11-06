"""Production guest guard and actual native action rejection; read-only ELF input."""
from pathlib import Path
import os, subprocess, sys, tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
assert 'BbscGuestTransitionDoorHook' not in s
assert 'BbscActionButtonAcceptOffset' not in s
native=Path(sys.argv[1]).read_bytes()[0x4000:]
assert native[0x1cd97d6:0x1cd97dd]==bytes.fromhex('488b0d03a47003')
assert native[0x1cd97e6:0x1cd97eb]==bytes.fromhex('4883c4585b')
assert 'image_base+0x01CD97E6' in s and 'image_base+0x01CD97D6' not in s
# R12 retains the original action ID at the result observer; AL is native bool.
import capstone
ops=list(capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64).disasm(native[0x1cd91f0:0x1cd97d6],0x1cd91f0))
assert [(i.mnemonic,i.op_str) for i in ops if i.op_str.startswith(('r12,','r12d,'))]==[('mov','r12d, edx')]
assert native[0x1cd91f0:0x1cd91f6]==bytes.fromhex('554889e54157')
assert native[0x1cd925e:0x1cd926a]==bytes.fromhex('4584ff740731c0e96c050000')
code=r'''
#include <windows.h>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include "core/cpu_patches.h"
using u64=uint64_t; using u32=uint32_t;
using Core::GuestRegisterSnapshot;
u64 mapped=0;int observations=0;u32 observed_action=0;bool observed_result=false;
namespace BbscMod {u64 EbootAddress(){return mapped;} void LogPlain(const char* s){std::puts(s);}}
void PS4_SYSV_ABI observe(u64,const GuestRegisterSnapshot* r){
 ++observations;observed_action=u32(r->r12);observed_result=(r->rax&255)!=0;
}
int state=0; int GetSessionState(){return state;}
'''+r'''
int main(){
 auto* image=(unsigned char*)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image);
 mapped=reinterpret_cast<u64>(image);
 unsigned char native[]={NATIVE};memcpy(image+0x1cd91f0,native,sizeof(native));
 unsigned char tail[]={TAIL};memcpy(image+0x1cd97d6,tail,sizeof(tail));
 image[0x1f128a0]=0xc3; // param lookup: no row; native permits this
 uint64_t guard=0,ptr=(uint64_t)&guard;memcpy(image+0x53e3be0,&ptr,8);
 // Sentinel at the first instruction AFTER native early rejection. No game dependencies.
 unsigned char allowed[]={0xb8,1,0,0,0,0xe9,0x62,5,0,0};memcpy(image+0x1cd926a,allowed,sizeof(allowed));
 using Accept=int (__attribute__((sysv_abi)) *)(u64,u64,u64,u64,u64,u64);
 auto accept=(Accept)(image+0x1cd91f0);
 // Execute the DLL trampoline, not merely the untouched original function.
 assert(Core::InstallGuestCodeHook(image+0x1cd97e6,{tail+0x10,5},0,observe));
 for(int role=0;role<=8;++role){state=role;
  for(u32 id: {3200000u,3200001u,7030u,6030u,3200002u}){
   GuestRegisterSnapshot r{};r.rdx=id;
   bool blocked=false;
   const auto before=observations;
   assert(r.rcx==(blocked?1u:0u));assert(accept(0,0,r.rdx,r.rcx,0,0)==(blocked?0:1));
   assert(observations==before+1&&observed_action==id&&observed_result);
   r.rcx=1;assert(accept(0,0,r.rdx,r.rcx,0,0)==0);
   assert(observations==before+2&&observed_action==id&&!observed_result);
  }
 }
 VirtualFree(image,0,MEM_RELEASE);
}
'''
code=code.replace('#include <cstring>','#include <cstring>\n#include <initializer_list>')
for key,data in [('NATIVE',native[0x1cd91f0:0x1cd926a]),('TAIL',native[0x1cd97d6:0x1cd97fb])]:
 code=code.replace(key,','.join(hex(v) for v in data))
with tempfile.TemporaryDirectory(prefix='bbsc-doors-') as tmp:
 cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe';cpp.write_text(code)
 cxx='C:/msys64/clang64/bin/clang++.exe'
 subprocess.run([cxx,'-std=c++20','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
                 '-I',str(root/'emulator/src'),'-I',str(root/'emulator/externals/xbyak'),
                 str(cpp),str(root/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
 env=dict(os.environ);env['PATH']=str(Path(cxx).parent)+os.pathsep+env.get('PATH','')
 subprocess.run([str(exe)],check=True,env=env,timeout=10)
print('PASS: original action function through production DLL trampoline: accepted/rejected AL and R12 action ID preserved for all roles; safe non-relative epilogue')
