"""Original 1.09 activation machine + production completion hook, fixture only.

Requires BBSC_TEST_EBOOT. Exercises late NPC activation after map takeover,
reactivation and adjacent maps without inventing a polling/spawn simulation.
"""
from pathlib import Path
import os, struct, subprocess, tempfile
import test_independent_native as native

ROOT = Path(__file__).resolve().parents[1]
data = Path(os.environ['BBSC_TEST_EBOOT']).read_bytes()
ph = struct.unpack_from('<Q', data, 32)[0]
size, count = struct.unpack_from('<HH', data, 54)
segments = [struct.unpack_from('<II6Q', data, ph+i*size) for i in range(count)]
def read(address, length):
    for typ, _, off, va, _, fs, _, _ in segments:
        if typ == 1 and va <= address and address+length <= va+fs:
            return data[off+address-va:off+address-va+length]
    raise AssertionError(hex(address))

assert read(0x18bd488,7) == bytes.fromhex('c7 40 10 04 00 00 00')
assert read(0x18bd484,4) == bytes.fromhex('48 8b 43 18') # RBX=ChrIns, RAX=controller
assert read(0x18bd477,5)[0] == 0xe8
assert 0x18bd477+5+struct.unpack('<i',read(0x18bd478,4))[0] == 0x18b9890
assert read(0x18eb7ad,4) == bytes.fromhex('48 89 53 08') # sync table owns its native actor list
assert read(0x190e792,5) == bytes.fromhex('49 8b 44 24 08')
assert read(0x190e7a2,3) == bytes.fromhex('8b 40 08') # CHR map comes from block metadata+8

PREFIX = r'''
#include <windows.h>
#include <array>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <mutex>
#include <set>
#define FMT_HEADER_ONLY
#include "fmt/format.h"
#include "core/bbsc_world_blocks.h"
#include "core/cpu_patches.h"
#include "xbyak/xbyak.h"
using namespace Core::Bloodborne;
#include "core/bbsc_native_sync_test.h"
using Core::GuestRegisterSnapshot;
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;
u64 image_base=0;constexpr u64 CandidateLocalStatePointerOffset=0x553e878;
namespace BbscMod{u64 EbootAddress(){return image_base;}void LogPlain(const char*){}u32 RegisterOwnId(){return 22;}}
enum class MemoryProt{CpuWrite};
bool active=true,setup_ready=true;int reads=0,writes=0,completions=0;
bool trace_enabled=true;std::vector<std::string> trace_lines;
bool BbscTimelineEnabled(){return trace_enabled;}
std::atomic<u64> bbsc_world_native_load{7};
struct TestMutex{bool held=false;void lock(){assert(!held);held=true;}void unlock(){assert(held);held=false;}};
TestMutex bbsc_world_presence_mutex;
#define BBSC_TIMELINE(category,...) do{if(trace_enabled){assert(!bbsc_world_presence_mutex.held);trace_lines.push_back(fmt::format(__VA_ARGS__));}}while(0)
World::Presence bbsc_world_presence_local;
World::OwnerBook bbsc_independent_owners;
u64 addr(auto& a){return (u64)a.data();}
template<class T>T ReadValue(u64 p,size_t off){++reads;T v;memcpy(&v,(void*)(p+off),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t off,T v){++writes;memcpy((void*)(p+off),&v,sizeof(v));}
bool ReadablePointer(u64 p,size_t){return p>0x10000;}
bool HasMemoryAccess(u64 p,size_t n,MemoryProt){return ReadablePointer(p,n);}
bool BbscIndependentActive(){return active;}
u64 doll=0;u64 BbscWorldDoll(u64){return doll;}
bool PS4_SYSV_ABI Ready(u64){return setup_ready;}
bool PS4_SYSV_ABI Setup(u64,u64){return setup_ready;}
void PS4_SYSV_ABI Noop(u64){}
void jump(u64 at,u64 target){auto* p=(u8*)at;p[0]=0x48;p[1]=0xb8;memcpy(p+2,&target,8);p[10]=0xff;p[11]=0xe0;}
// Enter the ORIGINAL transition dispatch, keeping its table and branches.
struct Activation:Xbyak::CodeGenerator{
 Activation(u64 entry){
  // Match the original frame, including the activation-wait tail return.
  push(rbp);mov(rbp,rsp);push(r15);push(r14);push(rbx);sub(rsp,8);
  mov(rbx,rdi);xor_(r14,r14);mov(rax,entry);jmp(rax);ready();
 }
};
'''
production = native.function('u64 BbscWorldOwnershipWord(u64 world,u64 chr)')
production += native.function('u64 BbscWorldNpcBlock(u64 world,u32 block)')
production += native.function('void PS4_SYSV_ABI BbscWorldNpcActivated(u64,const GuestRegisterSnapshot* regs)')
production = production.replace('if(!regs || !BbscIndependentActive())return;',
                                '++completions;if(!regs || !BbscIndependentActive())return;')
MAIN = r'''
int main(){
 AddVectoredExceptionHandler(1,[](EXCEPTION_POINTERS* e)->LONG{
  auto* c=e->ContextRecord;fprintf(stderr,"fault rip=%llx offset=%llx rax=%llx rbx=%llx rdi=%llx\n",
   c->Rip,c->Rip-image_base,c->Rax,c->Rbx,c->Rdi);fflush(stderr);return EXCEPTION_CONTINUE_SEARCH;});
 image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image_base);
 const u8 machine[]={MACHINE};memcpy((void*)(image_base+0x18bd38c),machine,sizeof(machine));
 Activation dispatch(image_base+0x18bd38c);
 jump(image_base+0x18b9890,(u64)&Setup);
 const u8 site[]={0xc7,0x40,0x10,4,0,0,0};
 std::array<u8,0xB00> world{};std::array<u8,0x110> sync{};
 std::array<std::array<u8,0x40>,4> tables{};
 std::array<std::array<u8,0x10>,4> lists{};
 std::array<std::array<u8,0x38>,4> entries{};
 std::array<std::array<u8,0x160>,4> blocks{};
 std::array<std::array<u8,0x18>,4> maps{};
 std::array<std::array<u8,0x500>,4> actors{};
 std::array<std::array<u8,0x100>,4> controls{},aux{};
 std::array<u16,4> words{};std::array<u64,0x100> vtable{};
 vtable[0x78/8]=(u64)&Ready;vtable[0x58/8]=(u64)&Noop;
 vtable[0x60/8]=(u64)&Noop;vtable[0x68/8]=(u64)&Noop;
 vtable[0xb8/8]=(u64)&Noop;
 vtable[0xc0/8]=(u64)&Noop;
 WriteValue(image_base,CandidateLocalStatePointerOffset,addr(world));
 WriteValue(addr(world),0x278,s32(4));WriteValue(addr(world),0xA40,addr(sync));
 WriteValue(addr(world),0x20,s32(2));WriteValue(addr(world),0x28,addr(blocks));
 WriteValue(addr(sync),8,u32(4));
 const u32 cathedral=0x18000000,central=0x18010000;
 for(size_t i=0;i<4;++i){
  WriteValue(addr(sync),0x10+i*8,addr(tables[i]));
  const u64 list=i<2?addr(blocks[i])+0xb8:addr(lists[i]);
  WriteValue(addr(tables[i]),8,list);WriteValue(addr(tables[i]),0x10,u32(1));
  WriteValue(addr(tables[i]),0x18,(u64)&words[i]);
  WriteValue(list,0,u32(1));WriteValue(list,8,addr(entries[i]));
  WriteValue(addr(entries[i]),0,addr(actors[i]));
  WriteValue(addr(world),0x280+i*0x18,list);WriteValue(addr(world),0x850+i*8,list);
  WriteValue(addr(world),0x290+i*0x18,addr(blocks[i]));
  WriteValue(addr(blocks[i]),8,addr(maps[i]));WriteValue(addr(maps[i]),8,i==0?cathedral:central);
  WriteValue(addr(actors[i]),0,addr(vtable));WriteValue(addr(actors[i]),0x18,addr(controls[i]));
  WriteValue(addr(actors[i]),0x30,addr(aux[i]));WriteValue(addr(actors[i]),0x90,s32(i<<11));
  WriteValue(addr(controls[i]),0x14,s32(4));WriteValue(addr(controls[i]),0x10,s32(2));
 }
 auto& local=bbsc_world_presence_local;
 local.world={11,99};local.map=cathedral;local.phase=World::Phase::Playing;local.visit=local.sequence=1;
 local.capabilities=World::PresenceCapability|World::OwnerCapability;bbsc_independent_owners.Bind(local.world);
 auto lease=[&](u32 map,u32 owner,u64 epoch){World::Control c;c.scope=World::ScopeOf(local);c.scope.map=map;c.owner=owner;c.epoch=epoch;
  assert(bbsc_independent_owners.Take(11,c,100));};
 lease(cathedral,22,2);lease(central,11,1); // guest is map owner after host departure
 auto run=dispatch.getCode<void PS4_SYSV_ABI (*)(u64)>();
 const int samples=2000;const s32 preparing=2;
 auto begin=std::chrono::steady_clock::now();
 for(int i=0;i<samples;++i){memcpy(controls[0].data()+0x10,&preparing,4);run(addr(actors[0]));}
 const auto original_ns=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-begin).count();
 assert(!completions);
 assert(Core::InstallGuestCodeHook((void*)(image_base+0x18bd488),site,0,BbscWorldNpcActivated));
 WriteValue(addr(controls[0]),0x10,preparing);words.fill(0xffff);run(addr(actors[0]));
 assert(ReadValue<s32>(addr(controls[0]),0x10)==4&&words[0]==0xffff&&completions==1);
 assert(trace_lines.size()==1);
 assert(trace_lines.back().find("owner=00000016 epoch=2 local_owner=true")!=std::string::npos);
 assert(trace_lines.back().find("before=0xffff desired=0xffff after=0xffff applied=true visit=1 load=7 native_mode=true native_local=false")!=std::string::npos);
 // Return of the native host does not change the resident's authoritative lease.
 const int before_reads=reads,before_writes=writes,before_completions=completions;
 for(int i=0;i<2000;++i)run(addr(actors[0]));
 assert(reads==before_reads&&writes==before_writes&&completions==before_completions);
 assert(trace_lines.size()==1); // no heartbeat/frame logging
 // An unchanged assignment after the host's return still yields evidence.
 WriteValue(addr(controls[0]),0x10,s32(2));run(addr(actors[0]));
 assert(trace_lines.size()==2&&words[0]==0xffff);
 assert(trace_lines.back().find("owner=00000016 epoch=2")!=std::string::npos);
 assert(trace_lines.back().find("before=0xffff desired=0xffff after=0xffff applied=true")!=std::string::npos);
 // Same actor is later reactivated; take the current lease, not a cached decision.
 lease(cathedral,11,3);words[0]=1;WriteValue(addr(controls[0]),0x10,s32(2));run(addr(actors[0]));
 assert(words[0]==1&&completions==3);
 assert(trace_lines.back().find("owner=0000000b epoch=3 local_owner=false")!=std::string::npos);
 lease(cathedral,22,4);WriteValue(addr(controls[0]),0x10,s32(3));run(addr(actors[0]));assert(words[0]==1);
 // A streamed adjacent-map NPC has its OWN map lease, despite local role1.
 words[1]=1;run(addr(actors[1]));assert(words[1]==1);
 assert(trace_lines.back().find("npc_map=0x18010000 local_map=0x18000000 scope_map=0x18010000")!=std::string::npos);
 // Player tables keep the original native assignment.
 words[2]=123;run(addr(actors[2]));assert(words[2]==123);
 // Incomplete native activation must never acquire authority early.
 setup_ready=false;WriteValue(addr(controls[0]),0x10,s32(2));words[0]=0xffff;
 const int waiting=completions;run(addr(actors[0]));assert(completions==waiting&&words[0]==0xffff);
 setup_ready=true;run(addr(actors[0]));assert(words[0]==0xffff&&completions==waiting+1);
 // A recycled handle pointing at a different actor does not receive a lease.
 WriteValue(addr(controls[0]),0x10,s32(2));WriteValue(addr(entries[0]),0,addr(actors[1]));words[0]=77;
 run(addr(actors[0]));assert(words[0]==77);WriteValue(addr(entries[0]),0,addr(actors[0]));
 assert(trace_lines.back().find("skipped reason=actor-binding")!=std::string::npos);
 // Offline/loading preserve native results; no watchdog/retry is armed.
 active=false;WriteValue(addr(controls[0]),0x10,s32(2));run(addr(actors[0]));assert(words[0]==77);active=true;
 local.phase=World::Phase::Loading;WriteValue(addr(controls[0]),0x10,s32(2));run(addr(actors[0]));assert(words[0]==77);
 assert(trace_lines.back().find("skipped reason=loading")!=std::string::npos);
 local.phase=World::Phase::Playing;
 const auto saved_book=bbsc_independent_owners;bbsc_independent_owners.Clear();
 WriteValue(addr(controls[0]),0x10,s32(2));run(addr(actors[0]));assert(words[0]==77);
 assert(trace_lines.back().find("skipped reason=no-owner")!=std::string::npos);bbsc_independent_owners=saved_book;
 // The existing personal Dream doll exception survives native reactivation.
 WriteValue(addr(maps[0]),8,u32(0x15000000));lease(0x15000000,11,5);doll=addr(actors[0]);
 WriteValue(addr(controls[0]),0x10,s32(2));run(addr(actors[0]));assert(words[0]==77);
 doll=0;WriteValue(addr(maps[0]),8,cathedral);
 trace_enabled=false;const auto recorded=trace_lines.size();
 begin=std::chrono::steady_clock::now();const int before_bench=reads;
 for(int i=0;i<samples;++i){memcpy(controls[0].data()+0x10,&preparing,4);run(addr(actors[0]));}
 const auto fixed_ns=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-begin).count();
 printf("Fixture activation cost only: original %.3f us, fixed %.3f us, production reads/activation %d (memory guards mocked)\n",
  double(original_ns)/samples/1000,double(fixed_ns)/samples/1000,(reads-before_bench)/samples);
 assert(trace_lines.size()==recorded&&(reads-before_bench)/samples==26);
 puts("PASS event-only AI diagnostics: actual before/desired/readback, unchanged ownership, epoch/map/visit/load, skip reasons, no logging under presence lock, diagnostic-OFF no extra actor reads");
 puts("PASS original read-only native activation: late NPC, reactivation, native grants preserved across map lease changes, adjacent map, players, setup wait, recycled handle, loading/offline; 2000 active ticks zero callback/read/write");
}
'''.replace('MACHINE',','.join(map(str,read(0x18bd38c,0x18bd698-0x18bd38c))))
if os.environ.get('BBSC_ACTIVATION_AI_NEGATIVE') == '1':
    assert 'const u16 desired=native?before:' in production
    production = production.replace('const u16 desired=native?before:', 'const u16 desired=')

with tempfile.TemporaryDirectory(prefix='bbsc-activation-ai-') as tmp:
    cpp, exe = Path(tmp)/'fixture.cpp', Path(tmp)/'fixture.exe'
    cpp.write_text(PREFIX+production+MAIN,encoding='utf8')
    compiler=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
    env=dict(os.environ,PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH',''))
    subprocess.run([compiler,'-std=c++20','-O0','-Wall','-Wextra','-Werror','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
                    '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),
                    '-I',str(ROOT/'emulator/externals/fmt/include'),str(cpp),
                    str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True,env=env)
    result=subprocess.run([str(exe)],env=env,timeout=20)
    if os.environ.get('BBSC_ACTIVATION_AI_NEGATIVE') == '1':
        assert result.returncode!=0,'Old metadata-only activation unexpectedly passed'
        print('PASS negative control: activation must not fabricate/revoke native grants')
    else:
        result.check_returncode()
