"""Run actual independent player render lifecycle/controller on fixture memory."""
from pathlib import Path
import os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'emulator/src/core/bbsc_independent_world.inc').read_text(encoding='utf-8')
def function(signature):
    start=SOURCE.index(signature+' {');p=SOURCE.index('{',start)+1;depth=1
    while depth:depth+=(SOURCE[p]=='{')-(SOURCE[p]=='}');p+=1
    return SOURCE[start:p]+'\n'
PREFIX=r'''
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <atomic>
#include <cassert>
#include <mutex>
#include <set>
#include <vector>
#include "core/bbsc_world_players.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define BBSC_TIMELINE(...)
constexpr u64 CandidateLocalStatePointerOffset=0x553e878,MultiPlayerInsSetStateOffset=0x1e52560;
u64 image_base=0,remote=0; s64 now=10000;bool active=true,loading=false,missing_model=false,task_present=true;
std::array<u8,0x500> actor1{},actor2{},local{},task{},control{},flags{};
std::array<u8,0x20> draw{};std::array<u8,0xe0> child{},vtable{};
std::atomic<bool> bbsc_reload_finish_pending{false};std::atomic<u64> bbsc_world_load_pending{0};
std::mutex bbsc_world_presence_mutex;World::Presence bbsc_world_presence_local;World::PresenceBook bbsc_world_presence_book;
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
enum class MemoryProt{CpuWrite};bool HasMemoryAccess(u64 p,size_t,MemoryProt){return p>=0x10000;}
template<class T>T ReadValue(u64 p,size_t off){if(p==image_base+CandidateLocalStatePointerOffset)return T(0x70000);T v;std::memcpy(&v,reinterpret_cast<void*>(p+off),sizeof(T));return v;}
template<class T>bool WriteValue(u64 p,size_t off,T v){std::memcpy(reinterpret_cast<void*>(p+off),&v,sizeof(T));return true;}
u64 GetLocalPlayerCharacter(){return reinterpret_cast<u64>(local.data());}
u64 GetGlobalState(){return reinterpret_cast<u64>(local.data());}
bool BbscIndependentActive(){return active;}bool BbscCurtainActive(){return loading;}
s64 SteadyNowMs(){return now;}
std::vector<u64> GetMultiPlayerInsTasks(){return task_present?std::vector<u64>{reinterpret_cast<u64>(task.data())}:std::vector<u64>{};}
std::set<u64> BbscWorldPlayers(u64){return {GetLocalPlayerCharacter(),remote};}
u32 BbscWorldPeer(u64 member){return member==remote+0x3d8 || member==reinterpret_cast<u64>(task.data())+0xc8?22:0;}
s32 GetSessionState(){return 3;}u32 GetBbscRelayHost(){return 22;}
s32 hp=594;s32 GetCharacterHp(u64){return hp;}
u64 BbscCharacterDrawState(u64 ch){return ch && !missing_model?reinterpret_cast<u64>(draw.data()):0;}
bool IsValidMemberId(u64){return true;}
bool IsEbootCodeAddress(u64 p){return p==image_base+0x18f27c0;}
int binds=0,inserts=0,resets=0,removals=0;
void PS4_SYSV_ABI Bind(u64 ch,u64 member){assert(ch==remote&&member==reinterpret_cast<u64>(task.data())+0xc8);++binds;}
void PS4_SYSV_ABI Insert(u64 member,s32 state){assert(member==reinterpret_cast<u64>(task.data())&&state==4);++inserts;}
void PS4_SYSV_ABI Reset(u64 ch,u8 value){assert(ch==remote&&value==1);++resets;}
void PS4_SYSV_ABI Remove(u64 world,u64 ch){assert(world==0x70000&&ch==remote&&ch!=GetLocalPlayerCharacter());++removals;remote=0;}
void PS4_SYSV_ABI Disable(u64 ch,u8 value){assert(ch==remote);WriteValue(reinterpret_cast<u64>(control.data()),0x20,value);}
void MarkBbscRecreatedMember(u64){}
bool RepairBbscLocalMemberBinding(s32,const std::vector<u64>&,bool){return true;}
void Link(u64 offset,void* target){auto* p=reinterpret_cast<u8*>(image_base+offset);p[0]=0x48;p[1]=0xb8;const u64 a=reinterpret_cast<u64>(target);std::memcpy(p+2,&a,8);p[10]=0xff;p[11]=0xe0;}
void Actor(u64 p){WriteValue(p,0x18,reinterpret_cast<u64>(control.data()));WriteValue(p,0x58,reinterpret_cast<u64>(control.data()));WriteValue(p,0x60,reinterpret_cast<u64>(child.data()));WriteValue(p,0x208,0.0f);WriteValue(p,0x20c,0.0f);}
World::Presence peer;
void Hear(){peer.sequence++;assert(bbsc_world_presence_book.Hear(22,peer.world,peer,now));}
'''
MAIN=r'''
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x2000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 Link(0x18f27c0,reinterpret_cast<void*>(&Bind));Link(0x18c6390,reinterpret_cast<void*>(&Disable));
 Link(MultiPlayerInsSetStateOffset,reinterpret_cast<void*>(&Insert));Link(0x19186e0,reinterpret_cast<void*>(&Remove));
 WriteValue(reinterpret_cast<u64>(task.data()),0xe8,s32{1});WriteValue(reinterpret_cast<u64>(task.data()),0x50,s32{6});WriteValue(reinterpret_cast<u64>(task.data()),0x54,s32{6});
 WriteValue(reinterpret_cast<u64>(child.data()),0,reinterpret_cast<u64>(vtable.data()));WriteValue(reinterpret_cast<u64>(vtable.data()),0xd0,image_base+0x18f27c0);
 WriteValue(reinterpret_cast<u64>(control.data()),0x10,s32{4});WriteValue(reinterpret_cast<u64>(control.data()),0x14,s32{4});
 bbsc_world_presence_local.world={11,99};bbsc_world_presence_local.map=0x15000000;bbsc_world_presence_local.visit=1;bbsc_world_presence_local.sequence=1;bbsc_world_presence_local.phase=World::Phase::Playing;bbsc_world_presence_local.alive=1;
 peer=bbsc_world_presence_local;bbsc_world_presence_book.Bind(peer.world,11);Hear();
 remote=reinterpret_cast<u64>(actor1.data());Actor(remote);
 TickBbscWorldPlayers();assert(binds==1&&inserts==0);
 now+=1000;Hear();TickBbscWorldPlayers();assert(draw[0xc]==0&&ReadValue<float>(remote,0x208)==0&&resets==0); // no manual visibility/opacity writes
 peer.map=0x18000000;now++;Hear();TickBbscWorldPlayers();assert(ReadValue<u8>(reinterpret_cast<u64>(control.data()),0x20)==1);
 peer.map=0x15000000;peer.visit++;now++;Hear();TickBbscWorldPlayers();assert(removals==1&&inserts==1&&remote==0);
 // Native creation supplies a NEW actor; subsequent observations must not recreate it again.
 remote=reinterpret_cast<u64>(actor2.data());Actor(remote);now++;Hear();TickBbscWorldPlayers();assert(inserts==1&&binds==2);
 loading=true;bbsc_world_presence_local.visit++;now++;TickBbscWorldPlayers();assert(inserts==1);
 loading=false;now++;Hear();TickBbscWorldPlayers();assert(inserts==2&&removals==2&&remote==0); // address retained across local journey
 // Stage loading may allocate a different actor from retained native slot data.
 // Its new address/draw state does not replace the per-visit native admission.
 remote=reinterpret_cast<u64>(actor1.data());Actor(remote);now++;Hear();TickBbscWorldPlayers();
 loading=true;bbsc_world_presence_local.visit++;now++;TickBbscWorldPlayers();
 remote=reinterpret_cast<u64>(actor2.data());Actor(remote);
 loading=false;now++;Hear();TickBbscWorldPlayers();assert(inserts==3&&removals==3&&remote==0);
 remote=reinterpret_cast<u64>(actor1.data());Actor(remote);now++;Hear();TickBbscWorldPlayers();
 now++;Hear();TickBbscWorldPlayers();assert(inserts==3&&removals==3); // one restart per visit
 remote=0;
 // Missing/unfinished native actors can recover; retries remain bounded.
 now+=2500;Hear();TickBbscWorldPlayers();now+=4000;Hear();TickBbscWorldPlayers();assert(inserts<=5);
 for(int i=0;i<4;++i){
  World::PlayerVisualLife life;World::PlayerVisualInput in;in.loading=false;in.here=true;in.alive=in.actor_alive=in.actor_ready=in.task_ready=true;in.local_visit=1;in.peer_visit=i+1;in.actor=i+100;in.model=i+200;
  assert(life.Observe(in,1000).rebind);assert(!life.Observe(in,2000).insert);
  in.actor_ready=false;assert(!life.Observe(in,2001).insert);assert(life.Observe(in,4501).insert);
  assert(!life.Observe(in,4502).insert);assert(life.Observe(in,8501).insert);assert(!life.Observe(in,15000).insert);
  in.loading=true;assert(!life.Observe(in,16000).insert);
 }
 {
  World::PlayerVisualLife life;World::PlayerVisualInput in;
  in.loading=false;in.here=in.alive=in.actor_alive=in.actor_ready=in.task_ready=true;
  in.local_visit=in.peer_visit=1;in.actor=100;in.model=200;
  assert(life.Observe(in,1000).rebind);
  in.here=false;life.Observe(in,1001);
  // A remote traveller can also acquire a new local copy before its task is ready.
  in.here=true;++in.peer_visit;in.actor=101;in.model=201;in.task_ready=false;
  assert(!life.Observe(in,2000).insert);
  in.actor=102;in.model=202;in.task_ready=true;
  assert(life.Observe(in,2001).insert);
  in.actor=103;in.model=203;
  assert(life.Observe(in,2002).rebind);assert(!life.Observe(in,9000).insert);
  // No actor after a further local journey: begin admission without the old delay.
  ++in.local_visit;in.actor=in.model=0;in.actor_ready=false;
  assert(life.Observe(in,9001).insert);assert(!life.Observe(in,9002).insert);
 }
 active=false;TickBbscWorldPlayers();VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}

'''
def main():
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-world-players-') as tmp:
        cpp=Path(tmp)/'players.cpp';exe=Path(tmp)/'players.exe'
        cpp.write_text(PREFIX+function('void TickBbscWorldPlayers()')+MAIN,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-O2','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production per-peer player lifecycle: native binding/insertion, reused/new/missing actors on local and remote travel, pending tasks, one admission per visit, unfinished actor recovery, no visibility writes, bounded retries, four remote peers')
if __name__=='__main__':main()
