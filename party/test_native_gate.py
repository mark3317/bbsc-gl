"""Production gate dispatch + actual Windows trampoline and exact item entry bytes."""
from pathlib import Path
import os,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
start=s.index('    // Native entry, before goods effects')
body=s[start:s.index('#endif',start)]
fixture=r'''
#include <windows.h>
#include <cassert>
#include <cstring>
#include <string>
#include "core/cpu_patches.h"
using Core::GuestRegisterSnapshot;
u64 image; u8 bbsc_party_item_skip=0; bool enabled=true,grant=false; int requests=0;
namespace BbscMod {
u64 EbootAddress(){ return image; }
void LogPlain(const char*){}
bool PartyEnabled(){ return enabled; }
bool PartyAcquire(){ ++requests; return grant; }
void PartyCancel(){}
}
u64 GetLocalPlayerCharacter(){ return 17; }
void PS4_SYSV_ABI callback(u64 tag,const Core::GuestRegisterSnapshot* registers){
struct Site { u64 offset; } site{tag};
BODY
}
int main(){
image=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE)); assert(image);
// Exact 1.09 NativeApply/GoodsExecutor entry followed by a synthetic resource effect.
const u8 code[]={0x55,0x48,0x89,0xE5,0x41,0x57,0xC7,0x02,1,0,0,0,0xB8,1,0,0,0,0x41,0x5F,0x5D,0xC3};
using Apply=u64 PS4_SYSV_ABI (*)(u64,u64,int*);
for(u64 tag : {0x018F9720ull,0x018C9160ull}){
auto* p=reinterpret_cast<u8*>(image+(tag==0x018F9720?0:0x1000)); std::memcpy(p,code,sizeof(code));
assert(Core::InstallGuestCodeHook(p,std::span<const u8>{code,6},tag,callback,&bbsc_party_item_skip));
auto apply=reinterpret_cast<Apply>(p); int effect=0;
grant=false; assert(apply(17,200,&effect)==0 && effect==0 && requests>0);
grant=true; assert(apply(17,200,&effect)==1 && effect==1); effect=0;
grant=false; const int count=requests; assert(apply(17,205,&effect)==1 && effect==1 && requests==count); effect=0;
assert(apply(18,200,&effect)==1 && effect==1 && requests==count); effect=0;
enabled=false; assert(apply(17,200,&effect)==1 && effect==1 && requests==count); enabled=true;
}
}
'''.replace('BODY',body)
with tempfile.TemporaryDirectory(prefix='bbsc-party-gate-') as tmp:
 cpp=Path(tmp)/'gate.cpp'; exe=Path(tmp)/'gate.exe'; cpp.write_text(fixture)
 subprocess.run([os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe'),'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-I',str(root/'emulator/src'),'-I',str(root/'emulator/externals/xbyak'),str(cpp),str(root/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=10)
print('Production native item gate: deny before effect, allow after grant, guest bell unaffected: PASS')
