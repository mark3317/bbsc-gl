"""Both doors use the original action-button admission and rejection."""
from pathlib import Path
import os, subprocess, sys, tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
assert 'BbscGuestTransitionDoorHook' not in s
assert 'BbscActionButtonAcceptOffset' not in s
native=Path(sys.argv[1]).read_bytes()[0x4000:]
assert native[0x1cd97d6:0x1cd97dd]==bytes.fromhex('488b0d03a47003')
assert native[0x1cd97e6:0x1cd97eb]==bytes.fromhex('4883c4585b')
assert 'BbscLocalTransitionActionHook' not in s
assert native[0x1cd91f0:0x1cd91f6]==bytes.fromhex('554889e54157')
assert native[0x1cd925e:0x1cd926a]==bytes.fromhex('4584ff740731c0e96c050000')
code=r'''
#include <windows.h>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <initializer_list>
using u64=uint64_t; using u32=uint32_t;
int main(){
 auto* image=(unsigned char*)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image);
 unsigned char native[]={NATIVE};memcpy(image+0x1cd91f0,native,sizeof(native));
 unsigned char tail[]={TAIL};memcpy(image+0x1cd97d6,tail,sizeof(tail));
 image[0x1f128a0]=0xc3; // param lookup: no row; native permits this
 uint64_t guard=0,ptr=(uint64_t)&guard;memcpy(image+0x53e3be0,&ptr,8);
 // Sentinel at the first instruction AFTER native early rejection. No game dependencies.
 unsigned char allowed[]={0xb8,1,0,0,0,0xe9,0x62,5,0,0};memcpy(image+0x1cd926a,allowed,sizeof(allowed));
 using Accept=int (__attribute__((sysv_abi)) *)(u64,u64,u64,u64,u64,u64);
 auto accept=(Accept)(image+0x1cd91f0);
 for(u32 id: {3200000u,3200001u,7030u,6030u,3200002u}){
  assert(accept(0,0,id,0,0,0)==1);
  assert(accept(0,0,id,1,0,0)==0);
 }
 VirtualFree(image,0,MEM_RELEASE);
}
'''
for key,data in [('NATIVE',native[0x1cd91f0:0x1cd926a]),('TAIL',native[0x1cd97d6:0x1cd97fb])]:
 code=code.replace(key,','.join(hex(v) for v in data))
with tempfile.TemporaryDirectory(prefix='bbsc-doors-') as tmp:
 cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe';cpp.write_text(code)
 cxx='C:/msys64/clang64/bin/clang++.exe'
 subprocess.run([cxx,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 env=dict(os.environ);env['PATH']=str(Path(cxx).parent)+os.pathsep+env.get('PATH','')
 subprocess.run([str(exe)],check=True,env=env,timeout=10)
print('PASS: native action acceptance and rejection for both Lecture doors')
