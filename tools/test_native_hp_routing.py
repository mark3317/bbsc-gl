"""Run original 1.09 dirty HP producer AND receiver through production hooks.

BBSC_TEST_EBOOT points to an original read-only cached ELF. The fixture runs
only in its own allocated memory; networking calls are mocked, native dirty
scan/packet assembly/receive application and Windows hook trampolines are real.
"""
from pathlib import Path
import os
import shutil
import struct
import subprocess
import tempfile

import test_independent_native as authority
import test_world_blocks as blocks

ROOT = Path(__file__).resolve().parents[1]

FIXTURE = r'''
#include <windows.h>
#include <cstdio>
#include "core/cpu_patches.h"
#include "xbyak/xbyak.h"
namespace BbscMod {
u64 EbootAddress(){return image_base;}
void LogPlain(const char*){}
}
int packets=0,receives=0,accepted=0;
bool got_receive=false;
bool PS4_SYSV_ABI NetworkEnabled(u64){return true;}
bool PS4_SYSV_ABI IsSelf(u64){return false;}
int PS4_SYSV_ABI Send(u64,u64 member,u32 channel,const void* data,u32 size){
 assert(channel==5 && size==80);
 GuestRegisterSnapshot r;r.rdx=channel;r.rsi=member;r.rcx=reinterpret_cast<u64>(data);r.r8=size;
 bbsc_independent_send_skip=0;assert(BbscWorldBlockPacketSend(&r));
 if(!bbsc_independent_send_skip){
  ++packets;assert(r.rsi==100);
  for(size_t i=0;i<size;i+=8){
   const auto handle=ReadValue<u32>(r.rcx,i);
   assert(handle==0xffffffffu || BbscWorldBlockOwner(handle)==self);
   accepted+=handle==199 && ReadValue<u32>(r.rcx,i+4)==0;
  }
 }
 return 1;
}
int PS4_SYSV_ABI Receive(u64,u32 channel,void* buffer,u32 size){
 assert(channel==5 && size==80);++receives;
 // The real receiver selects a responsible native member using this hook.
 GuestRegisterSnapshot source;source.r12=5;source.rbx=999;
 BbscWorldHpSource(0,&source);assert(source.rbx+0xd0==100);
 if(got_receive)return 0;got_receive=true;
 const u32 packet[]={77,0,199,999};memcpy(buffer,packet,sizeof(packet));return sizeof(packet);
}
void jump(u64 at,u64 target){
 auto* p=reinterpret_cast<u8*>(at);p[0]=0x48;p[1]=0xb8;
 memcpy(p+2,&target,8);p[10]=0xff;p[11]=0xe0;
}
int main(){
 AddVectoredExceptionHandler(1,[](EXCEPTION_POINTERS* e)->LONG{
  const auto* c=e->ContextRecord;
  std::fprintf(stderr,"fixture fault code=%lx rip=%llx offset=%llx rdi=%llx r12=%llx rbp=%llx\n",
   e->ExceptionRecord->ExceptionCode,c->Rip,c->Rip-image_base,c->Rdi,c->R12,c->Rbp);
  std::fflush(stderr);return EXCEPTION_CONTINUE_SEARCH;
 });
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));
 assert(image_base);memcpy(reinterpret_cast<void*>(image_base+0x18ef578),native.data(),native.size());
 std::array<u8,0x200> manager{},native_world{};
 *reinterpret_cast<u64*>(image_base+0x5540290)=addr(manager);
 *reinterpret_cast<u64*>(image_base+0x553e878)=addr(native_world);
 put(native_world,0x60,u64(1));put(manager,0xf8,u64(100));put(manager,0x100,u64(132));
 jump(image_base+0xc8f570,reinterpret_cast<u64>(NetworkEnabled));
 jump(image_base+0xca1670,reinterpret_cast<u64>(IsSelf));
 jump(image_base+0x17894e0,reinterpret_cast<u64>(Send));
 jump(image_base+0x17893e0,reinterpret_cast<u64>(Receive));
 struct Wrapper:Xbyak::CodeGenerator {
  u64 exit;
  Wrapper(u64 entry){
   push(rbp);mov(rbp,rsp);push(rbx);push(r12);push(r13);push(r14);push(r15);sub(rsp,0x208);
   mov(rbx,rsi);mov(rax,entry);jmp(rax);
   exit=reinterpret_cast<u64>(getCurr());
   add(rsp,0x208);pop(r15);pop(r14);pop(r13);pop(r12);pop(rbx);pop(rbp);ret();ready();
  }
 } wrapper(image_base+0x18ef578);
 jump(image_base+0x18ef98d,wrapper.exit);
 auto hook=[&](u64 at,size_t size,Core::GuestCodeHook callback,const u8* skip=nullptr,u64 target=0){
  assert(Core::InstallGuestCodeHook(reinterpret_cast<void*>(image_base+at),
   {reinterpret_cast<const u8*>(image_base+at),size},0,callback,skip,false,
   target?reinterpret_cast<void*>(image_base+target):nullptr));
 };
 hook(0x18ef578,6,BbscWorldHpState);hook(0x18ef587,7,BbscWorldHpRestore);
 hook(0x18ef684,6,BbscWorldHpRestore);hook(0x18ef759,6,BbscWorldBlockHpReceived);
 hook(0x18ef94f,6,BbscWorldHpReceiveAfterSend,&bbsc_world_hp_receive_skip,0x18ef6c6);
 const s32 host=3,guest=6;
 memcpy(bbsc_world_host_state.data()+0x124,&host,4);memcpy(bbsc_world_guest_state.data()+0x124,&guest,4);
 bbsc_world_blocks_active=true;
 World::Scope scope{{11,99},map,{},0};bbsc_world_block_scope=scope;
 bbsc_world_block_inventory_ready=true;bbsc_world_block_inventory_load=1;
 bbsc_world_block_handles[199]=map;bbsc_world_block_handles[77]=map+0x10000;
 for(u32 id:{map,map+0x10000}){
  auto& item=bbsc_world_block_local[id];item.load=1;item.applied_epoch=1;
  auto& lease=bbsc_world_block_views[{World::BlockScope(scope,id),id}].lease;
  lease.epoch=1;lease.owner=id==map?self:22;
 }
 std::array<u8,0x800> sync{};std::array<u8,0x60> table{};
 std::array<u32,200> health{};std::array<u16,200> flags{};
 put(sync,8,u32(1));put(sync,0x10,addr(table));put(sync,0x670,u32(10));
 put(table,0x10,u32(200));put(table,0x30,reinterpret_cast<u64>(health.data()));
 put(table,0x38,reinterpret_cast<u64>(flags.data()));
 auto reset=[&]{
  packets=receives=accepted=0;got_receive=false;health.fill(100);flags.fill(0);
  // A kill late in a large block. Foreign dirty HP must never be published.
  health[199]=0;flags[199]=0x20;flags[77]=0x20;
  put(sync,0x664,u8(1));put(sync,0x660,u32(0));put(sync,0x65c,u32(0));
 };
 using Run=void PS4_SYSV_ABI (*)(u64,u64);auto run=wrapper.getCode<Run>();
 // Both native session roles: block owner sends the kill immediately AND
 // receives another owner's kill on the SAME native pass, without a timer.
 for(u32 role:{1u,2u}){
  bbsc_independent_role=role;put(manager,0x124,role==1?host:guest);reset();
  std::fprintf(stderr,"native HP fixture role%u\n",role);
  run(addr(manager),addr(sync));
  assert(packets==1 && accepted==1 && receives==2);
  assert(health[77]==0 && health[199]==0); // owner0 HP accepted, foreign999 rejected
  assert(!bbsc_world_hp_receive_frame && !bbsc_world_hp_receive_skip);
  assert(!bbsc_world_hp_original);
 }
 // A participant with no owned block receives only; never claims foreign HP.
 bbsc_world_block_views[{scope,map}].lease.owner=22;reset();run(addr(manager),addr(sync));
 assert(!packets && receives==2 && health[199]==999 && health[77]==0);
 // A load fence cannot publish the previous scene's pending HP.
 ++bbsc_world_native_load;reset();run(addr(manager),addr(sync));assert(!packets);
 --bbsc_world_native_load;
 // Legacy/non-block and disabled modes preserve original role branching.
 map=0x15000000;bbsc_independent_role=1;put(manager,0x124,host);
 reset();run(addr(manager),addr(sync));assert(!receives);
 bbsc_independent_role=2;put(manager,0x124,guest);reset();run(addr(manager),addr(sync));assert(receives==2);
 active=false;reset();put(manager,0x124,host);run(addr(manager),addr(sync));assert(!receives);
}
'''


def main():
    elf = Path(os.environ['BBSC_TEST_EBOOT'])
    data = elf.read_bytes()
    ph = struct.unpack_from('<Q', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 54)
    address, length = 0x18ef578, 0x18ef98d - 0x18ef578
    for i in range(count):
        typ, _, off, va, _, fs, _, _ = struct.unpack_from('<II6Q', data, ph + i * size)
        if typ == 1 and va <= address and address + length <= va + fs:
            native = data[off + address - va:off + address - va + length]
            break
    else:
        raise AssertionError('Native worker outside ELF')
    authority.check_original_sites(elf)
    source = (ROOT / 'emulator/src/core/bbsc_world_blocks.inc').read_text(encoding='utf-8')
    for original, mock in [('reinterpret_cast<Serialize>(image_base+0x0190E750)', 'MockSerialize'),
                           ('reinterpret_cast<Apply>(image_base+0x0190E8B0)', 'MockApply')]:
        source = source.replace(original, mock)
    prefix = blocks.PREFIX.replace('u64 BbscWorldStateStandIn(s32 role){return role;}', '')
    prefix = prefix.replace('#define PS4_SYSV_ABI\n', '')
    # Use the real ABI snapshot shared with the production Windows trampoline.
    prefix = prefix.replace('struct GuestRegisterSnapshot {u64 rax{},rbx{},rcx{},rdx{},rsi{},rdi{},rbp{},rsp{},r8{},r9{},r10{},r11{},r12{},r13{},r14{},r15{},rflags{};};',
                            '#include "core/cpu_patches.h"\nusing Core::GuestRegisterSnapshot;')
    signatures = ['u64 BbscWorldStateStandIn(s32 role)',
                  'void PS4_SYSV_ABI BbscWorldHpState(u64,const GuestRegisterSnapshot* regs)',
                  'void PS4_SYSV_ABI BbscWorldHpRestore(u64,const GuestRegisterSnapshot* regs)',
                  'void PS4_SYSV_ABI BbscWorldHpReceiveAfterSend(u64,const GuestRegisterSnapshot* regs)',
                  'void PS4_SYSV_ABI BbscWorldHpSource(u64,const GuestRegisterSnapshot* regs)']
    callbacks = ''.join(authority.function(s) for s in signatures)
    if os.environ.get('BBSC_TEST_HP_OLD'):
        old = 'const bool producer=blocks?BbscWorldBlockOwnsAny():bbsc_independent_role.load()==1;'
        assert old in callbacks
        callbacks = callbacks.replace(old, 'const bool producer=!blocks && bbsc_independent_role.load()==1;')
    declarations = '''
alignas(16) std::array<u8,0x130> bbsc_world_host_state{},bbsc_world_guest_state{};
thread_local u64 bbsc_world_hp_original=0,bbsc_world_hp_receive_frame=0;
std::atomic<u32> bbsc_independent_owner{22};
u8 bbsc_world_hp_receive_skip=0;
u64 BbscWorldStateStandIn(s32 role);
'''
    native_array = 'const std::array<u8,%d> native{%s};\n' % (len(native), ','.join(map(str, native)))
    compiler = shutil.which('clang++') or 'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-native-hp-') as tmp:
        cpp, exe = Path(tmp) / 'hp.cpp', Path(tmp) / 'hp.exe'
        cpp.write_text(prefix + declarations + source + callbacks + native_array + FIXTURE, encoding='utf-8')
        subprocess.run([compiler, '-std=c++20', '-O0', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-local-typedef', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
                        '-I', str(ROOT / 'emulator/src'), '-I', str(ROOT / 'emulator/externals/xbyak'),
                        str(cpp), str(ROOT / 'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe)], check=True)
        env = os.environ.copy()
        env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
        result = subprocess.run([str(exe)], env=env, timeout=20)
        if os.environ.get('BBSC_TEST_HP_OLD'):
            assert result.returncode != 0, 'Regression did not detect disabled native dirty producer'
            print('PASS negative control: old receive-only block branch FAILS kill-delivery assertion')
        else:
            result.check_returncode()
            print('PASS original native dirty HP scan/send + receive in one pass, both roles, correct owners, load fence and legacy paths; production Windows trampolines')


if __name__ == '__main__':
    main()
