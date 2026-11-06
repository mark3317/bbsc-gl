"""Original 1.09 hit TARGET routing and native animation/status owner fences.

Uses BBSC_TEST_EBOOT read-only. Only fixture memory is executed/modified;
the original hit selection/packet assembly and state application loops run
through production Windows trampolines. No game process or save is touched.
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
#include "xbyak/xbyak.h"
namespace BbscMod {u64 EbootAddress(){return image_base;}void LogPlain(const char*){}}
int hits=0;u32 hit_handle=0;
bool PS4_SYSV_ABI IsPlayer(u64){return true;}
s32 PS4_SYSV_ABI NoExtraHit(u64){return -1;}
void PS4_SYSV_ABI ApplyHit(u64,u64,u64,u32){}
s32 PS4_SYSV_ABI SendHit(u64,u32 channel,const void* data,u32 size){
 assert(channel==0x15&&size==12);GuestRegisterSnapshot r{};
 r.rdx=channel;r.rcx=reinterpret_cast<u64>(data);r.r8=size;r.rsi=999;
 bbsc_independent_send_skip=0;assert(BbscWorldBlockPacketSend(&r));
 if(!bbsc_independent_send_skip){++hits;hit_handle=ReadValue<u32>(r.rcx,0);assert(r.rsi==100);}
 return 1;
}
void jump(u64 at,u64 target){auto* p=reinterpret_cast<u8*>(at);p[0]=0x48;p[1]=0xb8;memcpy(p+2,&target,8);p[10]=0xff;p[11]=0xe0;}
struct Receiver:Xbyak::CodeGenerator {
 u64 exit;
 Receiver(u64 entry,bool status){
  // SysV arguments: sync, wire bytes, byte count, native member.
  push(rbp);mov(rbp,rsp);push(rbx);push(r12);push(r13);push(r14);push(r15);sub(rsp,0x208);
  mov(qword[rbp-0xf8],rdi);lea(rax,ptr[rsi+4]);
  if(status){mov(qword[rbp-0x108],rax);mov(rbx,rsi);mov(r12,rcx);mov(r14,0xaaaaaaaaaaaaaaabULL);}
  else{mov(qword[rbp-0x100],rax);mov(r15,rsi);mov(r14,rcx);mov(r12d,0x50b);mov(rbx,0x28f5c28f5c28f5c3ULL);}
  mov(rax,rdx);mov(r11,entry);jmp(r11);
  exit=reinterpret_cast<u64>(getCurr());add(rsp,0x208);
  pop(r15);pop(r14);pop(r13);pop(r12);pop(rbx);pop(rbp);ret();ready();
 }
};
int main(){
 AddVectoredExceptionHandler(1,[](EXCEPTION_POINTERS* e)->LONG{
  auto* c=e->ContextRecord;std::fprintf(stderr,"fixture fault code=%lx rip=%llx offset=%llx rax=%llx rdi=%llx r12=%llx\n",
   e->ExceptionRecord->ExceptionCode,c->Rip,c->Rip-image_base,c->Rax,c->Rdi,c->R12);
  std::fflush(stderr);return EXCEPTION_CONTINUE_SEARCH;
 });
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 memcpy(reinterpret_cast<void*>(image_base+0x1a29e40),hit_native.data(),hit_native.size());
 memcpy(reinterpret_cast<void*>(image_base+0x18ef108),animation_native.data(),animation_native.size());
 memcpy(reinterpret_cast<void*>(image_base+0x18efd12),status_native.data(),status_native.size());
 u64 cookie=1234;*reinterpret_cast<u64*>(image_base+0x53e3be0)=reinterpret_cast<u64>(&cookie);
 *reinterpret_cast<u64*>(image_base+0x553e880)=1; // original world-presence assertion
 std::array<u8,0x130> manager{};put(manager,0x124,s32(6));
 *reinterpret_cast<u64*>(image_base+0x5540290)=addr(manager);
 jump(image_base+0x1789a40,reinterpret_cast<u64>(SendHit));
 auto hook=[&](u64 site,size_t size,Core::GuestCodeHook fn){
  assert(Core::InstallGuestCodeHook(reinterpret_cast<void*>(image_base+site),
   {reinterpret_cast<const u8*>(image_base+site),size},0,fn));
 };
 hook(0x1a2a102,6,BbscWorldHitState);
 hook(0x18ef108,6,BbscWorldBlockAnimationReceived);
 hook(0x18efd12,6,BbscWorldBlockStatusReceived);
 Receiver animation(image_base+0x18ef108,false),status(image_base+0x18efd12,true);
 jump(image_base+0x18ef1fc,animation.exit);jump(image_base+0x18efe1d,status.exit);
 s32 host=3,guest=6;memcpy(bbsc_world_host_state.data()+0x124,&host,4);memcpy(bbsc_world_guest_state.data()+0x124,&guest,4);
 bbsc_world_blocks_active=true;World::Scope scope{{11,99},map,{},0};bbsc_world_block_scope=scope;
 bbsc_world_block_inventory_ready=true;bbsc_world_block_inventory_load=1;
 auto owner=[&](u32 id,u32 peer){auto& l=bbsc_world_block_local[id];l.load=1;l.applied_epoch=1;
  auto& lease=bbsc_world_block_views[{World::BlockScope(scope,id),id}].lease;lease.epoch=1;lease.owner=peer;};
 owner(map,self);owner(map+0x10000,22);bbsc_world_block_handles[199]=map;bbsc_world_block_handles[77]=map+0x10000;
 std::array<u8,0x600> attacker{},target{},module{},hit{},attacker_vt{},module_vt{};
 put(attacker,0,addr(attacker_vt));put(attacker_vt,0x1b8,reinterpret_cast<u64>(IsPlayer));
 put(module,0,addr(module_vt));put(module,8,addr(target));
 put(module_vt,0x68,reinterpret_cast<u64>(ApplyHit));put(module_vt,0xa0,reinterpret_cast<u64>(NoExtraHit));
 put(hit,0x22c,s32(50));
 using Hit=void PS4_SYSV_ABI (*)(u64,u64,u64);auto native_hit=reinterpret_cast<Hit>(image_base+0x1a29e40);
 for(u32 role:{1u,2u}){
  std::fprintf(stderr,"hit role%u\n",role);
  bbsc_independent_role=role;put(manager,0x124,role==1?host:guest);
  // LOCAL attacker, REMOTE target: message MUST reach the target owner.
  put(attacker,0x90,u32(199));put(target,0x90,u32(77));hits=0;
  native_hit(addr(module),addr(attacker),addr(hit));assert(hits==1&&hit_handle==77);
  // REMOTE attacker, LOCAL target: native authority already handles the hit.
  put(attacker,0x90,u32(77));put(target,0x90,u32(199));hits=0;
  native_hit(addr(module),addr(attacker),addr(hit));assert(!hits);
  // Native replicated-hit marker retains its original no-report path.
  put(hit,0x218,u8(1));put(target,0x90,u32(77));hits=0;
  native_hit(addr(module),addr(attacker),addr(hit));assert(!hits);put(hit,0x218,u8(0));
 }
 // Native state receivers must accept CURRENT owner state, never proxy/stale
 // data overwriting an owner's death/animation/status with an older live one.
 std::array<u8,0x4000> sync{};std::array<u8,0x60> table{};
 std::array<u8,200*96> animations{};std::array<u8,200*20> statuses{};
 std::array<u16,200> flags{};
 put(sync,8,u32(1));put(sync,0x10,addr(table));put(table,0x10,u32(200));
 put(table,0x28,addr(animations));put(table,0x40,addr(statuses));put(table,0x38,reinterpret_cast<u64>(flags.data()));
 using Rx=void PS4_SYSV_ABI (*)(u64,u64,u64,u64);
 for(u32 channel:{0x3Du,0x41u}){
  const size_t stride=channel==0x3D?100:24,width=stride-4;
  std::fprintf(stderr,"state channel%x\n",channel);std::vector<u8> wire(stride*2,0x72);
  auto fill=[&]{u32 h=77;memcpy(wire.data(),&h,4);h=199;memcpy(wire.data()+stride,&h,4);
   animations.fill(0x39);statuses.fill(0x39);flags.fill(0);};
  fill();GuestRegisterSnapshot r{};r.rdx=channel;r.rsi=100;r.rcx=reinterpret_cast<u64>(wire.data());r.r8=wire.size();
  const auto original=wire;bbsc_independent_send_skip=0;assert(BbscWorldBlockPacketSend(&r)&&!bbsc_independent_send_skip);
  assert(wire==original && ReadValue<u32>(r.rcx,stride)==199);
  assert(static_cast<s32>(ReadValue<u32>(r.rcx,0))<0);
  assert(!memcmp(reinterpret_cast<void*>(r.rcx+stride+4),wire.data()+stride+4,width));
  auto run=channel==0x3D?animation.getCode<Rx>():status.getCode<Rx>();
  run(addr(sync),reinterpret_cast<u64>(wire.data()),wire.size(),100);
  const auto* received=channel==0x3D?animations.data():statuses.data();
  assert(received[77*width]==0x72 && received[199*width]==0x39);
  assert(flags[77]&(channel==0x3D?4:0x40));assert(!flags[199]);
  // An unknown member and a former owner cannot apply even otherwise valid state.
  fill();run(addr(sync),reinterpret_cast<u64>(wire.data()),wire.size(),999);
  received=channel==0x3D?animations.data():statuses.data();assert(received[77*width]==0x39&&!flags[77]);
  owner(map+0x10000,33);fill();run(addr(sync),reinterpret_cast<u64>(wire.data()),wire.size(),100);
  received=channel==0x3D?animations.data():statuses.data();assert(received[77*width]==0x39&&!flags[77]);owner(map+0x10000,22);
 }
}
'''


def main():
    data = Path(os.environ['BBSC_TEST_EBOOT']).read_bytes()
    ph = struct.unpack_from('<Q', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 54)
    segments = [struct.unpack_from('<II6Q', data, ph + i * size) for i in range(count)]
    def read(address, length):
        for typ, _, off, va, _, fs, _, _ in segments:
            if typ == 1 and va <= address and address + length <= va + fs:
                return data[off + address - va:off + address - va + length]
        raise AssertionError(hex(address))
    authority.check_original_sites(Path(os.environ['BBSC_TEST_EBOOT']))
    # Real ABI: RSI -> attacker RBX, RDI -> target damage module R12;
    # the original native packet obtains its target from [R12+8].
    assert read(0x1a29e57,6) == bytes.fromhex('48 89 f3 49 89 fc')
    assert read(0x1a29fed,5) == bytes.fromhex('49 8b 44 24 08')
    prefix = blocks.PREFIX.replace('#define PS4_SYSV_ABI\n','').replace('u64 BbscWorldStateStandIn(s32 role){return role;}','')
    prefix = prefix.replace('struct GuestRegisterSnapshot {u64 rax{},rbx{},rcx{},rdx{},rsi{},rdi{},rbp{},rsp{},r8{},r9{},r10{},r11{},r12{},r13{},r14{},r15{},rflags{};};',
                            '#include "core/cpu_patches.h"\nusing Core::GuestRegisterSnapshot;')
    source = (ROOT/'emulator/src/core/bbsc_world_blocks.inc').read_text(encoding='utf-8')
    for original,mock in [('reinterpret_cast<Serialize>(image_base+0x0190E750)','MockSerialize'),('reinterpret_cast<Apply>(image_base+0x0190E8B0)','MockApply')]:
        source=source.replace(original,mock)
    callbacks=''.join(authority.function(s) for s in ['u64 BbscWorldStateStandIn(s32 role)',
        'void PS4_SYSV_ABI BbscWorldHitState(u64,const GuestRegisterSnapshot* regs)'])
    negative=os.environ.get('BBSC_TEST_ENEMY_OLD')
    if negative=='hit':
        assert 'BbscWorldBlockRole(target)' in callbacks
        callbacks=callbacks.replace('BbscWorldBlockRole(target)','BbscWorldBlockRole(regs->rbx)').replace('const u64 target=', '[[maybe_unused]] const u64 target=')
    elif negative=='state':
        start=source.index('void BbscWorldBlockStateReceived(');end=source.index('void PS4_SYSV_ABI BbscWorldBlockAnimationReceived',start)
        source=source[:start]+'void BbscWorldBlockStateReceived(const GuestRegisterSnapshot*,u32){}\n'+source[end:]
    declarations='alignas(16) std::array<u8,0x130> bbsc_world_host_state{},bbsc_world_guest_state{};\n'
    arrays=''
    for name,start,end in [('hit',0x1a29e40,0x1a2a277),('animation',0x18ef108,0x18ef1fc),('status',0x18efd12,0x18efe1d)]:
        raw=read(start,end-start);arrays+='const std::array<u8,%d> %s_native{%s};\n'%(len(raw),name,','.join(map(str,raw)))
    compiler=shutil.which('clang++') or 'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-enemy-state-') as tmp:
        cpp,exe=Path(tmp)/'states.cpp',Path(tmp)/'states.exe'
        cpp.write_text(prefix+declarations+source+callbacks+arrays+FIXTURE,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-O0','-Wall','-Wextra','-Werror','-Wno-unused-local-typedef',
            '-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),
            str(cpp),str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        result=subprocess.run([str(exe)],env=env,timeout=20)
        if negative:
            assert result.returncode!=0,'Old behavior was not detected'
            print('PASS negative control:',negative,'old policy FAILS native regression')
        else:
            result.check_returncode()
            print('PASS original native hit target/packet routing and animation/status receivers through production Windows hooks; current-owner, stale/proxy rejection and both roles')


if __name__=='__main__':
    main()
