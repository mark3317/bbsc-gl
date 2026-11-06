"""Execute original FirstSync/render gates through the production Windows hook.

Allocated fixture memory only. BBSC_TEST_EBOOT selects a read-only original1.09
ELF; the parent project's existing analysis cache is the local default.
"""
from pathlib import Path
import os, shutil, struct, subprocess, tempfile
import test_world_player_lifecycle as life

ROOT=life.ROOT

MAIN=r'''
namespace BbscMod {u64 EbootAddress(){return image_base;}void LogPlain(const char*){}}
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 auto* gate=reinterpret_cast<u8*>(image_base+0x1e502b2);
 // Keep all callee-saved registers and execute the original phantom-type
 // branches, AND and continuation at their actual native offsets.
 const u8 prefix[]={0x53,0x41,0x57,0x41,0x55,0x41,0x54,0x48,0x89,0xfb,0x49,0x89,0xf7,0x49,0x89,0xd5};
 std::memcpy(gate-sizeof(prefix),prefix,sizeof(prefix));
 std::memcpy(gate,native_gate,sizeof(native_gate));
 const u8 tail[]={0x4c,0x89,0xf8,0x41,0x5c,0x41,0x5d,0x41,0x5f,0x5b,0xc3};
 std::memcpy(gate+sizeof(native_gate),tail,sizeof(tail));
 std::memcpy(reinterpret_cast<void*>(image_base+0x18f4830),native_render,sizeof(native_render));
 using First=u64 PS4_SYSV_ABI (*)(u64,u64,u64);
 using Render=void PS4_SYSV_ABI (*)(u64);
 auto first=reinterpret_cast<First>(gate-sizeof(prefix));
 auto render=reinterpret_cast<Render>(image_base+0x18f4830);
 remote=reinterpret_cast<u64>(actor1.data());const u64 t=reinterpret_cast<u64>(task.data());
 bbsc_world_presence_local.world={11,99};bbsc_world_presence_local.map=0x15000000;
 bbsc_world_presence_local.visit=2;bbsc_world_presence_local.sequence=1;
 bbsc_world_presence_local.phase=World::Phase::Playing;bbsc_world_presence_local.alive=1;
 peer=bbsc_world_presence_local;peer.visit=1;
 bbsc_world_presence_book.Bind(peer.world,11);Hear();
 auto setup=[&](int mode=1){
  actor1.fill(0);control.fill(0);parts.fill(0);part.fill(0);node.fill(0);task.fill(0);
  WriteValue(t,0xe8,s32(mode));WriteValue(t,0x50,s32{4});WriteValue(t,0x54,s32{4});
  WriteValue(remote,0x1e1,u32{0x1000}); // original constructor's draw admission
  WriteValue(remote,0x18,reinterpret_cast<u64>(control.data()));
  WriteValue(reinterpret_cast<u64>(control.data()),0x10,s32{4});
  WriteValue(remote,0x48,reinterpret_cast<u64>(part.data()));
  WriteValue(remote,0x4d0,reinterpret_cast<u64>(parts.data()));
  WriteValue(remote,0x4b4,u8{1});
  WriteValue(reinterpret_cast<u64>(parts.data()),0x28,reinterpret_cast<u64>(part.data()));
  WriteValue(reinterpret_cast<u64>(part.data()),0x18,reinterpret_cast<u64>(node.data()));
  WriteValue(reinterpret_cast<u64>(node.data()),0x210,u8{0x3f});
  bbsc_world_player_admissions.clear();
 };
 auto drawn=[&](){render(remote);return (ReadValue<u8>(reinterpret_cast<u64>(node.data()),0x210)&1)!=0;};
 // Reproduce the installed defect with COMPLETE original native render gates:
 // assembled, enabled actor becomes invisible solely due to FirstSync's hold.
 setup();assert(drawn());assert(first(t,remote,1)==remote);assert(!drawn());
 const u8 expected[]={0x41,0x80,0xa7,0xe2,1,0,0,0xef};
 assert(Core::InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x1e502c3),expected,0,
   BbscWorldPlayerRenderAdmission,&bbsc_world_player_render_skip,true));
 // Both roles, all phantom types, first/second/further local visits. This
 // preserves the native creation flags; the renderer still applies its gates.
 for(int mode:{1,2})for(u64 type:{1u,2u,12u}){
  fixture_state=mode==2?6:3;setup(mode);
  ArmBbscWorldPlayerAdmission(t,22,bbsc_world_presence_local,peer.visit);
  assert(first(t,remote,type)==remote&&drawn());assert(bbsc_world_player_render_skip==0);
  assert(bbsc_world_player_admissions.empty());
  assert(first(t,remote,type)==remote&&!drawn()); // one shot; ordinary native hold
 }
 fixture_state=3;
 for(u64 type:{0u,3u,9u}){
  setup();ArmBbscWorldPlayerAdmission(t,22,bbsc_world_presence_local,peer.visit);
  assert(first(t,remote,type)==remote&&drawn()); // original type branch skips the hold
  assert(bbsc_world_player_admissions.contains(t)); // our callback was not entered
 }
 for(int invalid=0;invalid<11;++invalid){
  active=true;setup();
  ArmBbscWorldPlayerAdmission(t,22,bbsc_world_presence_local,peer.visit);
  if(invalid==0)bbsc_world_player_admissions.clear(); // ordinary initial summon
  if(invalid==1)active=false;
  if(invalid==2)++bbsc_world_presence_local.visit;
  if(invalid==3)++peer.visit;
  if(invalid==4)peer.map=0x18000000;
  if(invalid==5)peer.alive=0;
  if(invalid==6)now+=15000;
  if(invalid==7)WriteValue(t,0xe8,s32{3}); // self task
  if(invalid==8)WriteValue(t,0xed,u8{2}); // leaving member
  if(invalid==9)bbsc_world_presence_local.world={11,100};
  if(invalid==10)peer.phase=World::Phase::Loading;
  Hear();assert(first(t,remote,1)==remote&&!drawn());
  if(invalid==2)--bbsc_world_presence_local.visit;
  peer.map=0x15000000;peer.alive=1;peer.phase=World::Phase::Playing;
  bbsc_world_presence_local.world={11,99};Hear();
 }
 active=true;setup();ArmBbscWorldPlayerAdmission(t,22,bbsc_world_presence_local,peer.visit);
 assert(first(t,remote,1)==remote&&drawn());
 // Native disabled/render-off/death-related presentation gates remain in
 // control after admission: the hook never writes render nodes or opacity.
 WriteValue(reinterpret_cast<u64>(control.data()),0x20,u8{1});assert(!drawn());
 WriteValue(reinterpret_cast<u64>(control.data()),0x20,u8{0});assert(drawn());
 WriteValue(remote,0x1e1,u32{0});assert(!drawn());
 VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
'''

def main():
    elf=Path(os.environ.get('BBSC_TEST_EBOOT',str(ROOT.parents[1]/'out/exit-study.elf')))
    data=elf.read_bytes();ph=struct.unpack_from('<Q',data,32)[0]
    size,count=struct.unpack_from('<HH',data,54)
    segments=[struct.unpack_from('<II6Q',data,ph+i*size) for i in range(count)]
    def read(a,n):
        seg=next(s for s in segments if s[0]==1 and s[3]<=a and a+n<=s[3]+s[5])
        return data[seg[2]+a-seg[3]:seg[2]+a-seg[3]+n]
    assert read(0x1e502c3,8)==bytes.fromhex('41 80 a7 e2 01 00 00 ef')
    assert read(0x18f4830,11)==bytes.fromhex('8b 87 e1 01 00 00 f6 c4 10 0f 84')
    assert read(0x193a93c,7)==bytes.fromhex('80 8b e2 01 00 00 10')
    assert read(0x18b9daa,11)==bytes.fromhex('41 c7 85 e1 01 00 00 00 10 00 00')
    blobs={'native_gate':read(0x1e502b2,0x1e502d1-0x1e502b2),
           'native_render':read(0x18f4830,0x18f4a41-0x18f4830)}
    code=''.join('const unsigned char '+name+'[]={'+','.join(map(str,b))+'};\n' for name,b in blobs.items())
    prefix=life.PREFIX.replace('s32 GetSessionState(){return 3;}','s32 fixture_state=3;s32 GetSessionState(){return fixture_state;}')
    prefix=prefix.replace('#define NOMINMAX\n','').replace('#define WIN32_LEAN_AND_MEAN\n','')
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-render-admission-') as td:
        cpp=Path(td)/'render.cpp';exe=Path(td)/'render.exe'
        cpp.write_text(code+prefix+life.admission_source()+MAIN,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-I',str(ROOT/'emulator/src'),
            '-I',str(ROOT/'emulator/externals/xbyak'),str(cpp),
            str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],env=env,check=True)
    print('PASS original FirstSync hold -> invisible native renderer reproduced; scoped recreation hook restores drawing, both roles/types, one-shot/expiry/visit/world/dead/loading/self/leave guards, ordinary summon and native hide preserved')

if __name__=='__main__':main()
