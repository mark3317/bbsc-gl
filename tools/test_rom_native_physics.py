"""Original native 2004[54] and production boss fog collision guard."""
from pathlib import Path
import os, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
elf=Path(sys.argv[1]).read_bytes()[0x4000:]
source=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
a=source.index('void PS4_SYSV_ABI BbscBossFogCollisionHook(')
z=source.index('\nvoid InstallBbscBellRefundHook()',a)
assert elf[0x17bc977:0x17bc984]==bytes.fromhex('80 b8 92 15 00 00 00 0f 85 10 03 00 00')
code=r'''
#include <windows.h>
#include <array>
#include <cassert>
#include <cstring>

#include "core/cpu_patches.h"
using Core::GuestRegisterSnapshot;
u64 image_base=0;int state=6,type=1;
namespace BbscMod {u64 EbootAddress(){return image_base;}void LogPlain(const char*){}}
bool ReadablePointer(u64 p,size_t){return p>0x10000;}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t o,T v){memcpy((void*)(p+o),&v,sizeof(v));}
int GetSessionState(){return state;}int GetLocalPlayerType(){return type;}
std::array<u8,0x400> actor{};std::array<u8,0x120> physics{};
u32 resolved_entity=0;
u64 PS4_SYSV_ABI Find(u32 entity,u64,u32 zero){assert(zero==0);resolved_entity=entity;return (u64)actor.data();}
void Jump(u64 off,void* target){u8* p=(u8*)(image_base+off);p[0]=0x48;p[1]=0xb8;u64 a=(u64)target;memcpy(p+2,&a,8);p[10]=0xff;p[11]=0xe0;}
u8 bbsc_boss_fog_collision_skip=0;
'''+source[a:z]+r'''
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(image_base);
 const u8 native[]={BANK};memcpy((void*)(image_base+0x17ba6a0),native,sizeof(native));
 u64 canary=0;WriteValue<u64>(image_base,0x53e3be0,(u64)&canary);
 std::array<u8,0x1600> global{};WriteValue<u64>(image_base,0x5556678,(u64)global.data());
 WriteValue<u64>(image_base,0x553b0c8,1);Jump(0x13c97a0,(void*)&Find);
 std::array<u8,0xc0> inst{};std::array<u8,0x20> instruction{};std::array<u32,2> args{10000,0};
 u64 p=(u64)inst.data(),i=(u64)instruction.data();
 WriteValue<u64>(p,0xb0,i);WriteValue<u64>(p,0xb8,(u64)args.data());WriteValue<u32>(p,0x60,10000);
 WriteValue<s32>(i,0,2004);WriteValue<s32>(i,4,54);WriteValue<u64>(i,8,8);
 auto reset=[&](bool disabled){
  actor.fill(0);physics.fill(0);resolved_entity=0;
  WriteValue<u64>((u64)actor.data(),0x58,(u64)physics.data());
  WriteValue<u32>((u64)actor.data(),0x1e1,disabled?0x40:0);
  WriteValue<u16>((u64)physics.data(),0x114,disabled?0x10:0);
 };
 auto check=[&](bool disabled){
  assert(ReadValue<u32>((u64)actor.data(),0x1e1)==(disabled?0x40:0));
  assert(ReadValue<u16>((u64)physics.data(),0x114)==(disabled?0x10:0));
 };
 using Bank=u8 PS4_SYSV_ABI (*)(u64,u64);auto bank=(Bank)(image_base+0x17ba6a0);
 // The original opcode clears map collision near the fog for the borrowed world.
 global[0x1592]=0;reset(false);assert(bank(0,p)==1);check(true);
 const std::array<u8,7> cmp{0x80,0xb8,0x92,0x15,0,0,0};
 assert(Core::InstallGuestCodeHook((void*)(image_base+0x17bc977),cmp,0,BbscBossFogCollisionHook,
  &bbsc_boss_fog_collision_skip,false,(void*)(image_base+0x17bcc94)));
 reset(false);assert(bank(0,p)==1);check(false);
 assert(!resolved_entity && !bbsc_boss_fog_collision_skip && global[0x1592]==0);
 // The companion restore instruction still runs through native physics.
 args[1]=1;reset(true);assert(bank(0,p)==1);check(false);assert(resolved_entity==10000);
 args[1]=0;
 // Original on-disk arguments use the same native path as resolved arguments.
 std::array<u64,2> ref{};
 std::array<u64,0x12> file{};
 ref[1]=(u64)file.data();file[0x78/8]=0x80;file[0x80/8]=10000;
 WriteValue<u64>(p,0xa8,(u64)ref.data());WriteValue<u64>(p,0xb8,0);
 reset(false);assert(bank(0,p)==1);check(false);assert(!resolved_entity);
 WriteValue<u64>(p,0xb8,(u64)args.data());
 // An NPC, the same relative argument resolved to another actor, and an invader
 // must all retain the original native dispatch.
 args[0]=3200110;reset(false);assert(bank(0,p)==1);check(true);assert(resolved_entity==3200110);
 args[0]=10000;WriteValue<u32>(p,0x60,10001);
 reset(false);assert(bank(0,p)==1);check(true);assert(resolved_entity==10001);
 WriteValue<u32>(p,0x60,10000);type=2;
 reset(false);assert(bank(0,p)==1);check(true);
 state=3;type=0;global[0x1592]=1;reset(false);bank(0,p);check(false);assert(!resolved_entity);
 VirtualFree((void*)image_base,0,MEM_RELEASE);
}
'''
code=code.replace('BANK',','.join(map(str,elf[0x17ba6a0:0x17bcfa0])))
with tempfile.TemporaryDirectory(prefix='bbsc-rom-native-physics-') as tmp:
    cpp,exe=Path(tmp)/'fixture.cpp',Path(tmp)/'fixture.exe'
    cpp.write_text(code,encoding='utf8')
    cxx='C:/msys64/clang64/bin/clang++.exe'
    subprocess.run([cxx,'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),str(cpp),str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(cxx).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],env=env,check=True,timeout=15)
print('PASS native 2004[54]: guest keeps map collision and gravity, restore runs, host/invader/NPC retain native dispatch')
