from pathlib import Path
import subprocess, os
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
a=s.index('u8 bbsc_bell_refund_skip =');b=s.index('void InstallBbscBellRefundHook()',a)
fixture=r"""
#include <cstdint>
#include <cstring>
#include <cassert>
using u64=uint64_t;using s64=int64_t;using s32=int32_t;using u8=uint8_t;
#define PS4_SYSV_ABI
struct GuestRegisterSnapshot {u64 rsi=0,rax=77;};
bool enabled=true; s64 event=9183;
bool EnvFlagEnabled(const char*){return enabled;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
s64 BbscRunningEventId(u64){return event;}
"""+s[a:b]+r"""
int main(){
 alignas(8) u8 instance[0xC0]{},instruction[0x20]{},args[12]{};
 auto put=[](void* p,size_t o,auto v){memcpy((u8*)p+o,&v,sizeof(v));};
 put(instance,0xB0,(u64)instruction);put(instance,0xB8,(u64)args);
 put(instruction,0,s32(2004));put(instruction,4,s32(8));
 put(args,0,s32(10000));put(args,4,s32(4680));
 GuestRegisterSnapshot regs{(u64)instance,77};
 BbscBellRefundHook(0,&regs);assert(bbsc_bell_refund_skip==1&&regs.rax==1);
 auto pass=[&]{bbsc_bell_refund_skip=0;regs.rax=77;BbscBellRefundHook(0,&regs);assert(!bbsc_bell_refund_skip&&regs.rax==77);};
 for(auto id:{9350,9422,9184}){event=id;pass();} event=9183;
 enabled=false;pass();enabled=true;
 put(args,4,s32(2160));pass();put(args,4,s32(4680));
 put(args,0,s32(10001));pass();put(args,0,s32(10000));
 put(instruction,4,s32(21));pass();put(instruction,4,s32(8));
 // Unparameterized event: resolve its raw file argument block.
 alignas(8) u8 file[0x100]{},ref[16]{};
 put(instance,0xB8,u64(0));put(instance,0xA8,(u64)ref);put(ref,8,(u64)file);
 put(file,0x78,u64(0x90));memcpy(file+0x90,args,12);
 bbsc_bell_refund_skip=0;BbscBellRefundHook(0,&regs);assert(bbsc_bell_refund_skip&&regs.rax==1);
}
"""
fixture=fixture.replace('#include <cassert>','#include <cassert>\n#include <initializer_list>')
build=root/'build';build.mkdir(exist_ok=True);cpp=build/'test_bell_refund.cpp';exe=cpp.with_suffix('.exe');cpp.write_text(fixture,encoding='utf8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20',str(cpp),'-o',str(exe)],check=True)
env=dict(os.environ);env['PATH']='C:/msys64/clang64/bin;'+env.get('PATH','');subprocess.run([str(exe)],env=env,check=True)
print('PASS: suppress only unanswered bell refund; preserve boss/chalice rewards, other effects, disabled mode; raw and resolved arguments')
