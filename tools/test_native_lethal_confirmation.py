"""Run original HP application + Kill branches for a predicted-zero remote NPC.

Only fixture memory is executed/modified. Original 1.09 code and production
Windows trampolines verify that authoritative HP0 retains its native lethal
edge once, for host and guest block followers, without direct actor state writes.
"""
from pathlib import Path
import os
import shutil
import struct
import subprocess
import tempfile
import test_independent_native as authority
import test_world_blocks as blocks

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=r'''
#include <windows.h>
#include <cstdio>
#include "xbyak/xbyak.h"
namespace BbscMod {u64 EbootAddress(){return image_base;}void LogPlain(const char*){}}
int setters=0,kills=0,death_calls=0;bool revivable=false;
bool PS4_SYSV_ABI Revivable(u64){return revivable;}
void PS4_SYSV_ABI SetHp(u64 chr,s32 hp){++setters;const auto mods=ReadValue<u64>(chr,0x3b0);
 const auto stats=ReadValue<u64>(mods,0x20);WriteValue<s32>(stats,0xf8,hp);}
void PS4_SYSV_ABI OtherStats(u64,s32){}
void PS4_SYSV_ABI Death(u64 chr){++death_calls;assert(ReadValue<u8>(chr,0x1e3)&1);}
void PS4_SYSV_ABI CountKill(u64,const Core::GuestRegisterSnapshot*){++kills;}
void jump(u64 at,u64 target){auto* p=reinterpret_cast<u8*>(at);p[0]=0x48;p[1]=0xb8;
 memcpy(p+2,&target,8);p[10]=0xff;p[11]=0xe0;}
struct Apply:Xbyak::CodeGenerator {
 u64 exit;
 Apply(u64 entry){
  // SysV: actor, native world. Execute the original pending-bit lookup,
  // consumption, HP unpacking, setter and lethal-edge branch together.
  push(rbp);mov(rbp,rsp);push(rbx);push(r12);push(r13);push(r14);push(r15);sub(rsp,0x208);
  mov(r15,rdi);mov(qword[rbp-0x148],rsi);xor_(r12d,r12d);mov(edi,0x50b);
  mov(dword[rbp-0x138],1);mov(r8d,1);mov(r11,entry);jmp(r11);
  exit=reinterpret_cast<u64>(getCurr());add(rsp,0x208);pop(r15);pop(r14);pop(r13);pop(r12);pop(rbx);pop(rbp);ret();ready();
 }
};
struct Admission:Xbyak::CodeGenerator {
 u64 entered,skipped;
 Admission(u64 entry){
  // SysV: manager containing the REAL native session role.
  push(rbp);mov(rbp,rsp);push(rbx);push(r12);push(r13);push(r14);push(r15);sub(rsp,0x208);
  mov(rax,rdi);mov(r11,entry);jmp(r11);
  entered=reinterpret_cast<u64>(getCurr());mov(eax,1);jmp("exit");
  skipped=reinterpret_cast<u64>(getCurr());xor_(eax,eax);L("exit");
  add(rsp,0x208);pop(r15);pop(r14);pop(r13);pop(r12);pop(rbx);pop(rbp);ret();ready();
 }
};
int main(){
 AddVectoredExceptionHandler(1,[](EXCEPTION_POINTERS* e)->LONG{
  const auto* c=e->ContextRecord;std::fprintf(stderr,"fixture fault %lx rip=%llx offset=%llx rax=%llx r15=%llx\n",
   e->ExceptionRecord->ExceptionCode,c->Rip,c->Rip-image_base,c->Rax,c->R15);return EXCEPTION_CONTINUE_SEARCH;
 });
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 memcpy(reinterpret_cast<void*>(image_base+0x1916d91),admission_native.data(),admission_native.size());
 memcpy(reinterpret_cast<void*>(image_base+0x1916e52),apply_native.data(),apply_native.size());
 memcpy(reinterpret_cast<void*>(image_base+0x18bf9a0),kill_native.data(),kill_native.size());
 std::array<u8,0x2000> global{};std::array<u8,0x130> manager{};u64 cookie=321;
 *reinterpret_cast<u64*>(image_base+0x5556678)=addr(global);put(global,0x176f,u8(1));
 *reinterpret_cast<u64*>(image_base+0x53e3be0)=reinterpret_cast<u64>(&cookie);
 jump(image_base+0x18bcd40,reinterpret_cast<u64>(SetHp));
 jump(image_base+0x18cc6a0,reinterpret_cast<u64>(OtherStats));
 jump(image_base+0x18bd9d0,reinterpret_cast<u64>(Death));
 jump(image_base+0x1a577d0,reinterpret_cast<u64>(Revivable));
 Apply apply(image_base+0x1916e52);Admission admission(image_base+0x1916d91);
 jump(image_base+0x1916f7c,apply.exit);jump(image_base+0x1916db4,admission.entered);jump(image_base+0x1916f96,admission.skipped);
 auto hook=[&](u64 at,size_t size,Core::GuestCodeHook callback,const u8* skip=nullptr,u64 target=0){
  assert(Core::InstallGuestCodeHook(reinterpret_cast<void*>(image_base+at),
   {reinterpret_cast<const u8*>(image_base+at),size},0,callback,skip,false,
   target?reinterpret_cast<void*>(image_base+target):nullptr));};
 hook(0x1916d91,6,BbscWorldHpApplyBegin,&bbsc_world_hp_apply_enter,0x1916db4);
 hook(0x1916ed5,9,BbscWorldHpApplyTarget,&bbsc_world_hp_apply_skip,0x1916f70);
 hook(0x1916ef5,6,BbscWorldHpApplyLethal);hook(0x18bf9a0,6,CountKill);
 bbsc_world_blocks_active=true;World::Scope scope{{11,99},map,{},0};bbsc_world_block_scope=scope;
 bbsc_world_block_inventory_ready=true;bbsc_world_block_inventory_load=1;
 bbsc_world_block_handles[77]=map;auto& item=bbsc_world_block_local[map];item.load=1;item.applied_epoch=1;
 auto& lease=bbsc_world_block_views[{scope,map}].lease;lease.owner=22;lease.epoch=1;
 std::array<u8,0x600> modules{},stats{},proxy{};
 put(actor,0x90,u32(77));put(actor,0x3b0,addr(modules));put(modules,0x20,addr(stats));
 put(actor,0x18,addr(control));put(control,0x10,s32(4));put(control,0x14,s32(4));put(control,0x30,addr(proxy));put(stats,0xfc,s32(100));
 using Admit=u32 PS4_SYSV_ABI (*)(u64);auto admit=admission.getCode<Admit>();
 using Run=void PS4_SYSV_ABI (*)(u64,u64);auto run=apply.getCode<Run>();
 std::array<u8,0x200> native_sync{},native_table{};std::array<u32,78> hp{};std::array<u16,78> pending{};
 put(world,0xa40,addr(native_sync));put(native_sync,8,u32(1));put(native_sync,0x10,addr(native_table));
 put(native_table,0x10,u32(78));put(native_table,0x30,reinterpret_cast<u64>(hp.data()));put(native_table,0x38,reinterpret_cast<u64>(pending.data()));
 auto apply_record=[&]{run(addr(actor),addr(world));};
 auto reset=[&](s32 old,u16 incoming,u8 dead=0){setters=kills=death_calls=0;
  put(stats,0xf8,old);hp[77]=incoming;pending[77]=0x10;put(actor,0x1e3,dead);put(proxy,0x18,u8(0));};
 for(s32 role:{3,6}){
  put(manager,0x124,role);put(global,0x1592,u8(role==3));
  assert(admit(addr(manager))==1); // host also enters unchanged native NPC HP loop
  reset(0,0);apply_record();
  assert(setters==1&&kills==1&&death_calls==1&&(ReadValue<u8>(addr(actor),0x1e3)&1));
  // Duplicate owner HP0 after the transition cannot replay native death.
  setters=kills=death_calls=0;pending[77]=0x10;apply_record();
  assert(setters==1&&!kills&&!death_calls);
  setters=0;apply_record();assert(!setters&&!kills); // no pending owner record, no repair
  for(u8 dead:{1,2,4,6,32}){reset(0,0,dead);apply_record();assert(!kills&&!death_calls);}
  reset(100,0);apply_record();assert(kills==1&&death_calls==1); // original positive edge
  reset(0,50);apply_record();assert(!kills&&ReadValue<s32>(addr(stats),0xf8)==50);
  reset(-1,0);apply_record();assert(!kills);
  reset(0,0);put(proxy,0x18,u8(1));apply_record();assert(!kills); // preserve native proxy exclusion
  reset(0,0);put(control,0x14,s32(0));apply_record();assert(!kills);put(control,0x14,s32(4));
  reset(0,0);lease.owner=self;apply_record();assert(!setters&&!kills&&!(pending[77]&0x10));lease.owner=22;
  reset(0,0);++bbsc_world_native_load;apply_record();assert(!setters&&!kills);--bbsc_world_native_load;
  reset(100,0xf987);apply_record();assert(!setters&&!kills); // native invalid-HP sentinel
 }
 // Original native revival guard remains authoritative; repair does not force HP0.
 reset(0,0);revivable=true;put(stats,0xf0,addr(actor));apply_record();
 assert(kills==1&&ReadValue<s32>(addr(stats),0xf8)==1);put(stats,0xf0,u64(0));revivable=false;
 // Legacy/Dream/disabled paths retain original session/outside-own-world gates.
 map=0x15000000;put(manager,0x124,s32(3));assert(!admit(addr(manager)));
 put(manager,0x124,s32(6));put(global,0x1592,u8(0));assert(admit(addr(manager))==1);
 active=false;reset(0,0);apply_record();assert(setters==1&&!kills);
}
'''

def main():
    data=Path(os.environ['BBSC_TEST_EBOOT']).read_bytes();ph=struct.unpack_from('<Q',data,32)[0]
    size,count=struct.unpack_from('<HH',data,54);segments=[struct.unpack_from('<II6Q',data,ph+i*size) for i in range(count)]
    def read(a,n):
        s=next(s for s in segments if s[0]==1 and s[3]<=a and a+n<=s[3]+s[5]);return data[s[2]+a-s[3]:s[2]+a-s[3]+n]
    authority.check_original_sites(Path(os.environ['BBSC_TEST_EBOOT']))
    assert read(0x1916f38,9)==bytes.fromhex('83 bd c0 fe ff ff 00 7e 2f')
    assert read(0x1916f5b,5)==bytes.fromhex('e8 40 8a fa ff')
    prefix=blocks.PREFIX.replace('#define PS4_SYSV_ABI\n','')
    prefix=prefix.replace('std::array<u8,0x600> world{},','std::array<u8,0xb00> world{};std::array<u8,0x600> ')
    prefix=prefix.replace('struct GuestRegisterSnapshot {u64 rax{},rbx{},rcx{},rdx{},rsi{},rdi{},rbp{},rsp{},r8{},r9{},r10{},r11{},r12{},r13{},r14{},r15{},rflags{};};',
                          '#include "core/cpu_patches.h"\nusing Core::GuestRegisterSnapshot;')
    source=(ROOT/'emulator/src/core/bbsc_world_blocks.inc').read_text(encoding='utf-8')
    for original,mock in [('reinterpret_cast<Serialize>(image_base+0x0190E750)','MockSerialize'),('reinterpret_cast<Apply>(image_base+0x0190E8B0)','MockApply')]:source=source.replace(original,mock)
    callbacks=''.join(authority.function(s) for s in ['void PS4_SYSV_ABI BbscWorldHpApplyBegin(u64,const GuestRegisterSnapshot* regs)',
       'void PS4_SYSV_ABI BbscWorldHpApplyTarget(u64,const GuestRegisterSnapshot* regs)',
       'void PS4_SYSV_ABI BbscWorldHpApplyLethal(u64,const GuestRegisterSnapshot* regs)'])
    if os.environ.get('BBSC_TEST_LETHAL_OLD'):
        callbacks=callbacks[:callbacks.index('void PS4_SYSV_ABI BbscWorldHpApplyLethal')]+'''void PS4_SYSV_ABI BbscWorldHpApplyLethal(u64,const GuestRegisterSnapshot*){}\n'''
    arrays=''
    for name,a,b in [('admission',0x1916d91,0x1916db4),('apply',0x1916e52,0x1916f7c),('kill',0x18bf9a0,0x18bfafd)]:
        raw=read(a,b-a);arrays+='const std::array<u8,%d> %s_native{%s};\n'%(len(raw),name,','.join(map(str,raw)))
    compiler=shutil.which('clang++') or 'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-native-lethal-') as tmp:
        cpp,exe=Path(tmp)/'lethal.cpp',Path(tmp)/'lethal.exe'
        cpp.write_text(prefix+'u8 bbsc_world_hp_apply_enter=0,bbsc_world_hp_apply_skip=0;\n'+source+callbacks+arrays+FIXTURE,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-O0','-Wall','-Wextra','-Werror','-Wno-unused-local-typedef','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
            '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),str(cpp),str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        result=subprocess.run([str(exe)],env=env,timeout=20)
        if os.environ.get('BBSC_TEST_LETHAL_OLD'):
            assert result.returncode!=0,'Old missing-lethal-edge policy was not detected';print('PASS negative control: original predicted-zero path FAILS native death transition')
        else:
            result.check_returncode();print('PASS original native HP apply + original Kill/proxy/revival branches, predicted-zero confirmation ONCE, both roles, stale/local/load/legacy fences; production Windows hooks')

if __name__=='__main__':main()
