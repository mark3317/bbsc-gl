"""Execute ORIGINAL EnemyIns AI-controller selection without map-owner overrides.

The native entry, ownership gate, controller binding, publication and update run.
Only external module methods/cookie data are fixture objects. No live process/save.
"""
from pathlib import Path
import os, struct, subprocess, tempfile
import test_independent_native as native

ROOT=Path(__file__).resolve().parents[1]
data=Path(os.environ['BBSC_TEST_EBOOT']).read_bytes()
ph=struct.unpack_from('<Q',data,32)[0]
sz,count=struct.unpack_from('<HH',data,54)
segments=[struct.unpack_from('<II6Q',data,ph+i*sz) for i in range(count)]
def read(a,n):
    for t,_,o,v,_,fs,_,_ in segments:
        if t==1 and v<=a and a+n<=v+fs:return data[o+a-v:o+a-v+n]
    raise AssertionError(hex(a))

PREFIX=r'''

#include <windows.h>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdio>
#include <mutex>
#include <chrono>
#include <set>
#include "xbyak/xbyak.h"
#include "core/cpu_patches.h"
#include "core/bbsc_native_ai_admission.h"
#include "core/bbsc_world_blocks.h"
using namespace Core::Bloodborne;
using Core::GuestRegisterSnapshot;
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;
u64 image_base=0;constexpr u64 CandidateLocalStatePointerOffset=0x553e878;
namespace BbscMod{u64 EbootAddress(){return image_base;}void LogPlain(const char*){}u32 RegisterOwnId(){return 22;}}
std::mutex bbsc_world_presence_mutex;
World::OwnerBook bbsc_independent_owners;
World::Presence bbsc_world_presence_local;
std::array<std::atomic<u8>,32> bbsc_native_ai_roles{};
std::array<World::Scope,32> bbsc_native_ai_scopes{};
std::atomic<u64> bbsc_world_native_load{1};
std::atomic<u32> bbsc_independent_owner{0},bbsc_independent_role{0};
void Trace(auto...){ }
#define BBSC_TIMELINE(...) Trace(__VA_ARGS__)
#define LOG_WARNING(...)
bool active=true;bool BbscIndependentActive(){return active;}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t o,T v){memcpy((void*)(p+o),&v,sizeof(v));}
bool ReadablePointer(u64 p,size_t){return p>0x10000;}
enum class MemoryProt{CpuWrite};bool HasMemoryAccess(u64 p,size_t n,MemoryProt){return ReadablePointer(p,n);}
bool BbscWorldSceneReady(){return true;}bool BbscWorldBlockSimulation(){return false;}
u64 GetLocalPlayerCharacter(){return 0;}u64 BbscWorldDoll(u64){return 0;}u32 BbscWorldBlockRole(u64){return 0;}
u64 addr(auto& a){return (u64)a.data();}
void put(auto& a,size_t o,auto v){memcpy(a.data()+o,&v,sizeof(v));}
int local_updates=0,remote_updates=0,bindings=0;
u64 local_module=0;
bool special=false;
bool PS4_SYSV_ABI Special(u64){return special;}
void PS4_SYSV_ABI Bind(u64,u64,u64){++bindings;}
void PS4_SYSV_ABI Update(u64 p,u64){if(p==local_module)++local_updates;else ++remote_updates;}
struct Publish:Xbyak::CodeGenerator{
 Publish(u64 site){using namespace Xbyak::util;push(r13);push(r14);push(r15);
  mov(r14,rdi);mov(r13,rsi);mov(r15,rdx);mov(rax,site);call(rax);
  pop(r15);pop(r14);pop(r13);ret();ready();}
};
using PublishFn=void PS4_SYSV_ABI (*)(u64,u64,u64);
PublishFn fixture_publish=nullptr;
std::array<std::array<u8,0x50>,20> registered_tables{};
std::array<std::array<u16,2>,20> registered_words{};
void PS4_SYSV_ABI SyncRegistered(u64 sync,u32 block,u64 list){
 if(block>=ReadValue<u32>(sync,8))return; // original018ECC80..8D; player IDs are outside NPC sync
 assert(block<20&&list);auto& table=registered_tables[block];
 put(table,8,list);put(table,0x10,ReadValue<u32>(list,0));put(table,0x18,addr(registered_words[block]));
 fixture_publish(sync,block,addr(table));
}
void jump(u8* at,u64 target){at[0]=0x48;at[1]=0xb8;memcpy(at+2,&target,8);at[10]=0xff;at[11]=0xe0;}

'''
MAIN=r'''

int main(){
 auto* base=(u8*)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(base);
 image_base=(u64)base;const u8 code[]={MACHINE};memcpy(base+0x18e6540,code,sizeof(code));
 u64 cookie=456;*(u64*)(base+0x53e3be0)=(u64)&cookie;
 alignas(16) std::array<u8,0x500> chr{},vt{},model{},modules{},transform{},local{},remote{},module_vt{};
 std::array<u8,0xb00> world{};std::array<u8,0x110> sync{};
 std::array<u8,0x50> table{};std::array<u16,2> words{0xffff,0xffff};
 put(chr,0,addr(vt));put(vt,0x4c8,(u64)Special);put(chr,0x90,s32(0));
 put(chr,0x58,addr(model));put(model,8,addr(chr));put(chr,0x3b0,addr(modules));put(modules,0x68,addr(transform));
 put(chr,0x3b8,addr(local));put(chr,0x3c0,addr(remote));put(local,0,addr(module_vt));put(remote,0,addr(module_vt));
 put(module_vt,0x38,(u64)Bind);put(module_vt,0x18,(u64)Update);local_module=addr(local);
 put(world,0xa40,addr(sync));put(sync,8,u32(1));put(sync,0x10,addr(table));
 put(table,0x10,u32(2));put(table,0x18,addr(words));*(u64*)(base+CandidateLocalStatePointerOffset)=addr(world);
 using Select=void PS4_SYSV_ABI (*)(u64,u8);auto select=(Select)(base+0x18e6540);
 auto run=[&](bool want_local,u8 forced=0){int l=local_updates,r=remote_updates;select(addr(chr),forced);
  assert(local_updates-l==int(want_local)&&remote_updates-r==int(!want_local));
  assert(ReadValue<u64>(addr(chr),0x60)==(want_local?addr(local):addr(remote)));
  assert(ReadValue<u64>(addr(model),0x80)==ReadValue<u64>(addr(chr),0x60));};
 // Original controller/update uses the SAME native grant as position authority.
 // An obsolete map-role cache cannot create a second brain or suppress a grant.
 for(u8 role:{0,1,2}){
  bbsc_native_ai_roles[0]=role;words[0]=0xffff;run(false);words[0]=1;run(true);
  words[0]=0xffff;run(false);run(true,1);special=true;run(true);special=false;
 }
 // Adjacent/new NPC slot has its own grant, independent of nearby NPCs.
 put(chr,0x90,s32(1));words[0]=1;words[1]=0xffff;run(false);words[1]=1;run(true);
 puts("PASS ORIGINAL EnemyIns selection/binding/model/update: grant gain/loss, host return, independent new NPC, stale map-role ignored, native special/forced paths");
}

'''

MAIN=MAIN.replace('MACHINE',','.join(map(str,read(0x18e6540,0x18e66ed-0x18e6540))))
compiler='C:/msys64/clang64/bin/clang++.exe'
env=dict(os.environ,PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH',''))
with tempfile.TemporaryDirectory(prefix='bbsc-native-ai-') as tmp:
    cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe'
    cpp.write_text(PREFIX+MAIN,encoding='utf8')
    subprocess.run([compiler,'-std=c++20','-O2','-Wall','-Wextra','-Werror','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
                    '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),
                    str(cpp),'-o',str(exe)],check=True,env=env)
    subprocess.run([str(exe)],check=True,env=env,timeout=20)
