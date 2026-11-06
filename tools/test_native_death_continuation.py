"""Run original Lua dispatcher in isolated allocated memory; no game writes."""
from pathlib import Path
import os, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a=s.index('void PS4_SYSV_ABI BbscDeathContinuationHook(');b=s.index('\n}\n',a)+3
hook=s[a:b]
elf=ROOT.parents[1]/'out/register-study.elf'
data=elf.read_bytes()[0x139a9d0+0x4000:0x139af81+0x4000]
prefix=r'''
#include <windows.h>
#include <array>
#include <cassert>
#include <cstring>
#include <cstdio>
#include "core/cpu_patches.h"
using Core::GuestRegisterSnapshot;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define BBSC_TIMELINE(...)
u8 bbsc_death_continuation_skip=0;bool enabled=true;int state=6,calls=0,frees=0;
bool BbscSpectateEnabled(){return enabled;}int GetSessionState(){return state;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
u64 image_base=0;
namespace BbscMod {u64 EbootAddress(){return image_base;}void LogPlain(const char* s){puts(s);} }
using Dispatch=int PS4_SYSV_ABI (*)(void*,u32,u32,u32,u32,u32,void*,u32,u8);
u64 canary=123;char allocator[0x80]{};u64 allocator_vtable[16]{};
u64 PS4_SYSV_ABI get_allocator(u64){return (u64)allocator;}
void PS4_SYSV_ABI release(u64,u64){++frees;}
u64 PS4_SYSV_ABI length(const char* p){return strlen(p);}
int PS4_SYSV_ABI compare(const char* a,const char* b){return strcmp(a,b);}
void PS4_SYSV_ABI invoke(u64,u64){++calls;}
void PS4_SYSV_ABI panic(){assert(false);}
void put(void* p,size_t off,u64 v){memcpy((char*)p+off,&v,8);}
void imm32(void* p,size_t off,u32 v){memcpy((char*)p+off,&v,4);}
void stub(u8* image,u64 at,u64 fn){image[at]=0x48;image[at+1]=0xb8;put(image,at+2,fn);image[at+10]=0xff;image[at+11]=0xe0;}
'''
main=r'''
int main(){
 auto* image=(u8*)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image);
 image_base=(u64)image;memcpy(image+0x139a9d0,native,sizeof(native));
 stub(image,0x207b720,(u64)get_allocator);stub(image,0x2bbe608,(u64)length);
 stub(image,0x2bbe638,(u64)compare);stub(image,0x2749180,(u64)invoke);
 stub(image,0x20b55b0,(u64)panic);stub(image,0x2bbe4f8,(u64)panic);
 put(image,0x53e3be0,(u64)&canary);
 char manager[0x30]{},event[0xA8]{},list[0x20]{},cache[0x20]{},node[0x20]{},entry[0x50]{};
 char dictionary[0x30]{},lookup[0x20]{};
 const char* name="next";
 put(dictionary,0x20,(u64)lookup);put(dictionary,0x28,(u64)lookup+0x20);
 put(lookup,0,(u64)entry);put(lookup,8,(u64)name);put(lookup,0x18,4);
 put(manager,0x10,0);put(manager,0x18,0);put(image,0x553b0c8,(u64)manager);
 put(event,0x80,(u64)dictionary);
 allocator_vtable[0x70/8]=(u64)release;put(allocator,0,(u64)allocator_vtable);
 auto reset=[&](u32 kind,u32 group){
  memset(entry,0,sizeof(entry));memset(node,0,sizeof(node));
  imm32(entry,0,kind);imm32(entry,4,group);imm32(entry,8,2);imm32(entry,12,3);
  entry[0x10]=1;entry[0x11]=0; // once, local registration mode
  memcpy(entry+0x20,"next",5);put(entry,0x30,4);put(entry,0x38,15);
  put(node,0,(u64)list);put(node,8,(u64)list);put(node,0x10,(u64)entry);
  put(list,0,(u64)node);put(list,8,(u64)node);put(cache,0,(u64)cache);put(cache,8,(u64)cache);
  put(event,0x48,(u64)list);put(event,0x50,1);put(event,0x58,(u64)allocator);
  put(event,0x68,(u64)cache);calls=frees=0;
 };
 auto dispatch=(Dispatch)(image+0x139a9d0);
 auto run=[&](u32 kind,u32 group,bool remote,bool guarded){
  dispatch(event+0x38,kind,group,2,3,0,event,0,remote);
 };
 reset(15,4000);run(15,4000,true,false);
 assert(calls==1&&ReadValue<u64>((u64)event,0x50)==0); // native defect: foreign timer consumes local callback
 constexpr std::array<u8,6> prologue{0x55,0x48,0x89,0xE5,0x41,0x57};
 assert(Core::InstallGuestCodeHook(image+0x139a9d0,prologue,0,BbscDeathContinuationHook,&bbsc_death_continuation_skip));
 reset(15,4000);run(15,4000,true,true);
 assert(calls==0&&ReadValue<u64>((u64)event,0x50)==1);
 run(15,4000,false,true);assert(calls==1&&ReadValue<u64>((u64)event,0x50)==0);
 for(u32 kind:{15u,16u}){
  reset(kind,4000);run(kind,4000,true,true);assert(calls==0);
  run(kind,4000,false,true);assert(calls==1);
 }
 for(auto role:{0,3,6}){state=role;reset(15,4000);run(15,4000,true,true);assert(calls==(role==0?1:0));}
 state=6;
 for(u32 kind:{0x43u,0x3au}){reset(kind,4000);run(kind,4000,true,true);assert(calls==1);}
 reset(12,4000);imm32(entry,12,0);run(12,4000,true,true);assert(calls==1); // HostDead message unchanged
 enabled=false;reset(15,4000);run(15,4000,true,true);assert(calls==1);enabled=true;
 reset(15,4001);run(15,4001,true,true);assert(calls==1);
 BbscDeathContinuationHook(0,nullptr);assert(!bbsc_death_continuation_skip);
 puts("PASS: original native dispatcher consumes foreign local death callback; production trampoline preserves it for local completion; host/guest/solo/disabled/other messages");
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-native-death-dispatch-') as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe'
 cpp.write_text(prefix+hook+'\nstatic const u8 native[]={'+','.join(str(x) for x in data)+'};\n'+main,encoding='utf-8')
 compiler=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
 subprocess.run([compiler,'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),str(cpp),str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
 env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
 subprocess.run([str(exe)],env=env,check=True,timeout=10)
