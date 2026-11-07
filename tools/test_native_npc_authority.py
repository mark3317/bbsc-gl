"""Original native request loops, stale-list replacement, grants and XYZ codec.

Runs against cached original ELF and production Windows rewrites, no live game.
Only native allocator, distance-priority and vector append are fixture services.
"""
from pathlib import Path
import os, struct, subprocess, tempfile

ROOT=Path(__file__).resolve().parents[1]
data=Path(os.environ['BBSC_TEST_EBOOT']).read_bytes()
ph=struct.unpack_from('<Q',data,32)[0]
sz,count=struct.unpack_from('<HH',data,54)
segments=[struct.unpack_from('<II6Q',data,ph+i*sz) for i in range(count)]
def read(a,n):
    for t,_,o,v,_,fs,_,_ in segments:
        if t==1 and v<=a and a+n<=v+fs:return data[o+a-v:o+a-v+n]
    raise AssertionError(hex(a))

code=r'''
#include <windows.h>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <vector>
#include "xbyak/xbyak.h"
#include "core/cpu_patches.h"
#include "core/bbsc_native_ai_admission.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;
u64 fixture_image=0;namespace BbscMod{u64 EbootAddress(){return fixture_image;}void LogPlain(const char* s){puts(s);}}
template<size_t N>u64 addr(std::array<u8,N>& a){return (u64)a.data();}
void put(u64 p,size_t o,auto v){memcpy((void*)(p+o),&v,sizeof(v));}
template<class T>T get(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
void jump(u8* at,u64 target){at[0]=0x48;at[1]=0xb8;memcpy(at+2,&target,8);at[10]=0xff;at[11]=0xe0;}
int priorities=0,freed=0;std::vector<u32> requests;
u64 local_module=0;int local_updates=0,remote_updates=0;
void PS4_SYSV_ABI Bind(u64,u64,u64){}
void PS4_SYSV_ABI Update(u64 module,u64){if(module==local_module)++local_updates;else ++remote_updates;}
u32 PS4_SYSV_ABI Priority(u64 chr){++priorities;return get<u32>(chr,0x3a8);}
bool PS4_SYSV_ABI Special(u64){return false;}
void PS4_SYSV_ABI Append(u64,u64 value){requests.push_back(get<u32>(value,0));}
u64 PS4_SYSV_ABI Allocate(u64,u64 n,u64){return (u64)calloc(1,n);}
void PS4_SYSV_ABI Free(u64,u64 p){++freed;free((void*)p);}
// Each wrapper supplies the live register/stack contract for an ORIGINAL block.
// Its original exits branch to this wrapper's epilogue, without a C++ callback.
struct Wrapper:Xbyak::CodeGenerator{
 Wrapper(u64 image,int mode,u64 body,u64 end1,u64 end2=0):CodeGenerator(4096){
  using namespace Xbyak::util;
  push(rbp);mov(rbp,rsp);push(rbx);push(r12);push(r13);push(r14);push(r15);sub(rsp,0x208);
  if(mode==0){mov(qword[rbp-0x148],rdi);mov(r15,rdi);}
  if(mode==1){mov(rax,rdi); /* list,count,values */}
  if(mode==2){mov(rax,rdi);mov(r12d,esi);test(r12d,r12d);}
  if(mode==3){mov(r8,rdi);mov(r12d,esi);lea(rax,ptr[rdi+0x208]);mov(qword[rbp-0xf0],rax);}
  if(mode==4){ // table, sync, word array; native position sender after handle resolution
   mov(r15,rdi);mov(r12,rsi);mov(rax,rdx);xor_(edx,edx);mov(edi,4<<11);xor_(ebx,ebx);
   mov(qword[rbp-0x108],rcx);
  }
  if(mode==5){ // native receiver: sync, packet
   mov(rcx,rdi);mov(qword[rbp-0xf8],rdi);lea(r12,ptr[rsi+4]);mov(r15d,1);mov(edx,0x50b);
  }
  if(mode==6){mov(qword[rbp-0xe8],rdi);mov(rax,rsi);movss(xmm1,xmm0);}
  mov(r11,image+body);jmp(r11);
  const auto finish=(u64)getCurr();
  if(mode==4)mov(eax,ebx);
  add(rsp,0x208);pop(r15);pop(r14);pop(r13);pop(r12);pop(rbx);pop(rbp);ret();ready();
  jump((u8*)(image+end1),finish);if(end2)jump((u8*)(image+end2),finish);
 }
};
using Fn=void PS4_SYSV_ABI (*)(u64,int,u64);
using Build=void PS4_SYSV_ABI (*)(u64);
using Send=int PS4_SYSV_ABI (*)(u64,u64,u64,u64);
using Receive=void PS4_SYSV_ABI (*)(u64,u64);
int main(){
 auto* base=(u8*)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(base);
 u64 image=(u64)base;fixture_image=image;
 LOADS
 std::array<u8,32> roles{};
 if(!NEGATIVE_REQUEST)assert(Core::InstallGuestCodeRewrite(base+0x1916a82,NativeAi::Request,NativeAi::EmitRequest,image,(u64)roles.data()));
 if(!NEGATIVE_EMPTY){
  assert(Core::InstallGuestCodeRewrite(base+0x18f0880,NativeAi::EmptySelf,NativeAi::EmitEmptySelf,image,0));
  assert(Core::InstallGuestCodeRewrite(base+0x18f09d1,NativeAi::EmptyPeer,NativeAi::EmitEmptyPeer,image,0));
 }
 jump(base+0x18cd180,(u64)Priority);jump(base+0x27dc9b0,(u64)Append);
 jump(base+0x2bbe688,(u64)+[](u64 p,int v,size_t n) PS4_SYSV_ABI ->u64 {memset((void*)p,v,n);return p;});
 Wrapper build(image,0,0x1916965,0x1916af0);
 Wrapper self(image,1,0x18f0880,0x18f088c);
 Wrapper peer(image,2,0x18f09ce,0x18f0900);
 Wrapper grant(image,3,0x18ed0ae,0x18ed159);
 Wrapper sender(image,4,0x18ee829,0x18ee91a);
 Wrapper receiver(image,5,0x18eebb0,0x18eeccd);
 Wrapper lod(image,6,0x1915ffa,0x1916030);
 alignas(16) std::array<u8,0xb00> world{};
 std::array<u8,0x800> sync{};std::array<u8,0x500> chr{},vt{},ctrl{};
 std::array<u8,16> list{};std::array<u8,0x38> entry{};std::array<u8,0x50> table{};
 std::array<u8,24> poses{};std::array<u16,1> words{0xffff},flags{2};
 put(addr(world),0x278,int(3));put(addr(world),0x280,addr(list));put(addr(world),0xa40,addr(sync));
 put(addr(list),0,int(1));put(addr(list),8,addr(entry));put(addr(entry),0,addr(chr));
 put(addr(chr),0,addr(vt));put(addr(vt),0x4c8,(u64)Special);put(addr(chr),0x90,u32(4<<11));
 put(addr(chr),0x18,addr(ctrl));put(addr(ctrl),0x10,int(4));put(addr(ctrl),0x14,int(4));
 put(addr(chr),0xe4,int(0));put(addr(chr),0x3a8,u32(100));
 put(addr(sync),8,int(17));put(addr(sync),0x10+4*8,addr(table));put(addr(sync),0x200,int(1));put(addr(sync),0x208,addr(table));
 put(addr(table),8,addr(list));put(addr(table),0x10,int(1));put(addr(table),0x18,(u64)words.data());
 put(addr(table),0x20,addr(poses));put(addr(table),0x38,(u64)flags.data());
 *(u64*)(base+0x553e878)=addr(world);
 u64 cookie=123;*(u64*)(base+0x53e3be0)=(u64)&cookie;
 alignas(16) std::array<u8,0x500> model{},modules{},transform{},local_ai{},remote_ai{},ai_vt{};
 put(addr(chr),0x58,addr(model));put(addr(model),8,addr(chr));put(addr(chr),0x3b0,addr(modules));
 put(addr(modules),0x68,addr(transform));put(addr(chr),0x3b8,addr(local_ai));put(addr(chr),0x3c0,addr(remote_ai));
 put(addr(local_ai),0,addr(ai_vt));put(addr(remote_ai),0,addr(ai_vt));
 put(addr(ai_vt),0x38,(u64)Bind);put(addr(ai_vt),0x18,(u64)Update);local_module=addr(local_ai);
 using Select=void PS4_SYSV_ABI (*)(u64,u8);auto select=(Select)(base+0x18e6540);
 auto brain=[&](bool want_local){int l=local_updates,r=remote_updates;select(addr(chr),0);
  assert(local_updates-l==int(want_local)&&remote_updates-r==int(!want_local));
  assert(get<u64>(addr(chr),0x60)==(want_local?addr(local_ai):addr(remote_ai)));
  assert(get<u64>(addr(model),0x80)==get<u64>(addr(chr),0x60));};
 auto request=[&](u8 role){roles[4]=role;requests.clear();build.getCode<Build>()(addr(world));return requests;};
 auto local=request(1);assert(local.size()==1&&(local[0]&0xffff)==(4<<11));
 // ORIGINAL distance LOD selects5 near its threshold,30 outside it, and
 // preserves the event's pinned-level flag. HP/activation alone are not LOD.
 std::array<u8,0x40> lod_config{};put(addr(lod_config),0x2c,10.f);
 using Lod=void PS4_SYSV_ABI (*)(u64,u64,float);auto level=lod.getCode<Lod>();
 level(addr(chr),addr(lod_config),20.f);assert(get<u32>(addr(chr),0xe4)==30);
 level(addr(chr),addr(lod_config),5.f);assert(get<u32>(addr(chr),0xe4)==5);
 put(addr(chr),0xe4,int(0));put(addr(chr),0x1e1,u32(1));level(addr(chr),addr(lod_config),20.f);
 assert(get<u32>(addr(chr),0xe4)==0);put(addr(chr),0x1e1,u32(0));
 assert(request(2)==local); // A discoverer is eligible even if another player owns the map.
 assert(request(0)==local); // unknown / offline native fallback
 brain(false); // No speculative second brain before a native grant.
 words[0]=1;auto retained=request(2);assert((retained.at(0)>>16)==0x7fff);brain(true);
 words[0]=0xffff;put(addr(chr),0x3a8,u32(0x7fff));auto challenger=request(1);
 assert((challenger.at(0)>>16)==0x7ffe);brain(false);
 put(addr(chr),0x3a8,u32(100));
 put(addr(ctrl),0x14,int(0));assert(request(1).empty());put(addr(ctrl),0x14,int(4));
 put(addr(chr),0x3a8,u32(0));words[0]=1;assert(request(1).empty());words[0]=0xffff;put(addr(chr),0x3a8,u32(100));
 roles[5]=1;assert(request(2)==local); // Map metadata cannot suppress native discovery.
 // Reproduce the four live NPCs: update level30 is an original omission gate.
 // It becomes eligible through the native active flag, without fabricating AI.
 put(addr(chr),0xe4,int(30));assert(request(2).empty());
 put(addr(chr),0x1e1,u32(8));assert(request(2)==local);put(addr(chr),0x1e1,u32(0));put(addr(chr),0xe4,int(0));
 // Native allocator/list assignment, not a mock of zero-length replacement.
 std::array<u8,0x80> allocator_vt{},allocator{},host{},guest{},hs{},gs{};
 put(addr(allocator),0,addr(allocator_vt));put(addr(allocator_vt),0x58,(u64)Allocate);put(addr(allocator_vt),0x70,(u64)Free);
 for(auto pair:{std::pair{addr(host),addr(hs)},std::pair{addr(guest),addr(gs)}}){
  put(pair.first,0x10,pair.second);put(pair.first,0x20,addr(allocator));put(pair.second,0,pair.second);put(pair.second,8,pair.second);
 }
 auto assign=(Fn)(base+0x1a6c590);
 self.getCode<Fn>()(addr(host),1,(u64)local.data());
 memcpy(base+0x5570094,local.data(),4);peer.getCode<Fn>()(addr(guest),1,0);
 assert(get<u64>(addr(host),0x18)==1&&get<u64>(addr(guest),0x18)==1);
 self.getCode<Fn>()(addr(host),-1,0);peer.getCode<Fn>()(addr(guest),-1,0);
 assert(get<u64>(addr(host),0x18)==1&&get<u64>(addr(guest),0x18)==1); // malformed negative count stays rejected
 // Host's old request survives a plain empty list in the original branch.
 self.getCode<Fn>()(addr(host),0,(u64)local.data());assert(get<u64>(addr(host),0x18)==0);
 // Same fix for the member receive path; packet payload uses the original buffer.
 peer.getCode<Fn>()(addr(guest),0,0);assert(get<u64>(addr(guest),0x18)==0);
 assert(freed==2);
 assign(addr(host),1,(u64)local.data());assign(addr(guest),1,(u64)local.data());
 using Merge=void PS4_SYSV_ABI (*)(u64,u64);auto merge=(Merge)(base+0x1a6c700);
 merge(addr(host),addr(guest));merge(addr(guest),addr(host));
 assert(get<u64>(addr(host),0x18)+get<u64>(addr(guest),0x18)==1); // simultaneous first claims: exactly one winner
 assign(addr(host),0,0);assign(addr(guest),0,0);
 assign(addr(guest),1,(u64)local.data());
 merge(addr(host),addr(guest));merge(addr(guest),addr(host));
 assert(get<u64>(addr(host),0x18)==0&&get<u64>(addr(guest),0x18)==1);
 // Already granted discoverer retains the NPC when a closer host/challenger
 // returns. ORIGINAL native merge arbitrates the unchanged packet format.
 assign(addr(host),1,(u64)challenger.data());assign(addr(guest),1,(u64)retained.data());
 merge(addr(host),addr(guest));merge(addr(guest),addr(host));
 assert(get<u64>(addr(host),0x18)==0&&get<u64>(addr(guest),0x18)==1);
 auto apply=[&](int n){u32 h=4<<11;memcpy(base+0x5570094,&h,4);grant.getCode<Fn>()(addr(sync),n,0);};
 apply(0);assert(words[0]==0xffff);brain(false);
 apply(1);assert(words[0]==1);brain(true); // Native grant controls BOTH AI and movement.
 // Execute native position-authority gate, delta calculation, codec, receiver
 // and reconstructed XYZ. The host/follower must not emit a competing position.
 put(addr(chr),0xb0,10.f);put(addr(chr),0xb4,20.f);put(addr(chr),0xb8,30.f);
 put(addr(poses),0,12.f);put(addr(poses),4,23.f);put(addr(poses),8,34.f);
 u64 flag=(u64)flags.data();auto send=sender.getCode<Send>();
 words[0]=0xffff;assert(send(addr(table),addr(sync),(u64)words.data(),flag)==0);
 words[0]=1;assert(send(addr(table),addr(sync),(u64)words.data(),flag)==1);
 // Receiver consumes the real packed channel4 entry; transport delivery itself is external.
 put(addr(poses),0,0.f);put(addr(poses),4,0.f);put(addr(poses),8,0.f);
 receiver.getCode<Receive>()(addr(sync),addr(sync)+0x6c8);
 for(auto [offset,want]:{std::pair{0,12.f},std::pair{4,23.f},std::pair{8,34.f}})
  assert(std::abs(get<float>(addr(poses),offset)-want)<0.05f);
 assert(flags[0]&1);
 // Release after streaming out uses the existing native empty-list path.
 put(addr(ctrl),0x14,int(0));assert(request(1).empty());
 peer.getCode<Fn>()(addr(guest),0,0);assert(get<u64>(addr(guest),0x18)==0);
 put(addr(ctrl),0x14,int(4));words[0]=0xffff;
 assign(addr(host),1,(u64)local.data());merge(addr(host),addr(guest));
 assert(get<u64>(addr(host),0x18)==1); // other active discoverer can take over
 assign(addr(host),0,0);
 assign(addr(guest),0,0);
 puts("PASS ORIGINAL requests/level30 omission, sticky native holder, empty-list release, merge/grants, EnemyIns brain binding/update and channel4 XYZ sender/receiver; distant discoverer and host return; no additional NPC passes");
}
'''
# Original functions/blocks plus constants used by the original float codec.
spans=[(0x1916965,0x1916af0),(0x18f0880,0x18f088c),(0x18f09ce,0x18f09ee),
       (0x1a6c590,0x1a6c6c2),(0x1a6c700,0x1a6c823),(0x18ed0ae,0x18ed159),
       (0x18ee829,0x18ee91a),(0x18eebb0,0x18eeccd),
       (0x178fa90,0x178fe46),(0x48fdbc0,0x48fdc00),(0x49271c8,0x49271f0)]
spans.append((0x18e6540,0x18e66ed))
spans.append((0x1915ffa,0x1916030))
loads=[]
for i,(start,end) in enumerate(spans):
    b=read(start,end-start)
    loads.append(f'const u8 c{i}[]={{'+','.join(map(str,b))+f'}};memcpy(base+{start},c{i},sizeof(c{i}));')
code=code.replace('LOADS','\n'.join(loads))
negative=os.environ.get('BBSC_NPC_AUTHORITY_NEGATIVE','')
code=code.replace('NEGATIVE_REQUEST','true' if negative=='request' else 'false')
code=code.replace('NEGATIVE_EMPTY','true' if negative=='empty' else 'false')
compiler='C:/msys64/clang64/bin/clang++.exe'
env=dict(os.environ,PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH',''))
with tempfile.TemporaryDirectory(prefix='bbsc-npc-authority-') as tmp:
    cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe'
    cpp.write_text(code,encoding='utf8')
    subprocess.run([compiler,'-std=c++20','-O2','-Wall','-Wextra','-Werror','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
                    '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),
                    str(cpp),str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],env=env,check=True)
    result=subprocess.run([str(exe)],env=env,timeout=20)
    if negative:
        assert result.returncode!=0,'Native authority regression was not detected'
        print('PASS negative control:',negative)
    else:result.check_returncode()
