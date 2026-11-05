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
u64 image_base=0,remote=0; s64 now=10000;bool active=true,loading=false,missing_model=false;
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
std::vector<u64> GetMultiPlayerInsTasks(){return {reinterpret_cast<u64>(task.data())};}
std::set<u64> BbscWorldPlayers(u64){return {GetLocalPlayerCharacter(),remote};}
u32 BbscWorldPeer(u64 member){return member==remote+0x3d8 || member==reinterpret_cast<u64>(task.data())+0xc8?22:0;}
s32 GetSessionState(){return 3;}u32 GetBbscRelayHost(){return 22;}
s32 hp=594;s32 GetCharacterHp(u64){return hp;}
u64 BbscCharacterDrawState(u64 ch){return ch && !missing_model?reinterpret_cast<u64>(draw.data()):0;}
bool IsValidMemberId(u64){return true;}
bool IsEbootCodeAddress(u64 p){return p==image_base+0x18f27c0;}
int binds=0,inserts=0,resets=0;
void PS4_SYSV_ABI Bind(u64 ch,u64 member){assert(ch==remote&&member==reinterpret_cast<u64>(task.data())+0xc8);++binds;}
void PS4_SYSV_ABI Insert(u64 member,s32 state){assert(member==reinterpret_cast<u64>(task.data())&&state==4);++inserts;}
void PS4_SYSV_ABI Reset(u64 ch,u8 value){assert(ch==remote&&value==1);++resets;}
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
 Link(0x18f27c0,reinterpret_cast<void*>(&Bind));Link(0x18bcf30,reinterpret_cast<void*>(&Reset));Link(MultiPlayerInsSetStateOffset,reinterpret_cast<void*>(&Insert));
 WriteValue(reinterpret_cast<u64>(child.data()),0,reinterpret_cast<u64>(vtable.data()));WriteValue(reinterpret_cast<u64>(vtable.data()),0xd0,image_base+0x18f27c0);
 const u64 t=reinterpret_cast<u64>(task.data());WriteValue(t,0xe8,s32{1});WriteValue(t,0x50,s32{6});WriteValue(t,0x54,s32{6});
 WriteValue(reinterpret_cast<u64>(control.data()),0x38,reinterpret_cast<u64>(flags.data()));
 WriteValue(reinterpret_cast<u64>(control.data()),0x10,s32{4});WriteValue(reinterpret_cast<u64>(control.data()),0x14,s32{4});
 bbsc_world_presence_local.world={11,99};bbsc_world_presence_local.map=0x15000000;bbsc_world_presence_local.visit=1;bbsc_world_presence_local.sequence=1;bbsc_world_presence_local.phase=World::Phase::Playing;bbsc_world_presence_local.alive=1;
 peer=bbsc_world_presence_local;bbsc_world_presence_book.Bind(peer.world,11);Hear();
 remote=reinterpret_cast<u64>(actor1.data());Actor(remote);
 TickBbscWorldPlayers();assert(binds==1&&draw[0xc]==0);
 now+=750;Hear();TickBbscWorldPlayers();assert(draw[0xc]==1&&ReadValue<float>(remote,0x208)==1&&resets==0);
 // Apart hides ONLY rendering; it cannot tear down character attachments.
 peer.map=0x18000000;now++;Hear();TickBbscWorldPlayers();assert(draw[0xc]==0);
 peer.map=0x15000000;peer.visit++;now++;Hear();TickBbscWorldPlayers();assert(draw[0xc]==0);
 now+=750;Hear();TickBbscWorldPlayers();assert(draw[0xc]==1);
 // Native load owns old storage; reused addresses/new graph get a fresh binding.
 loading=true;draw[0xc]=0xa5;now++;TickBbscWorldPlayers();assert(draw[0xc]==0xa5);
 loading=false;bbsc_world_presence_local.visit++;remote=reinterpret_cast<u64>(actor2.data());Actor(remote);draw[0xc]=0;now++;Hear();TickBbscWorldPlayers();
 now+=750;Hear();TickBbscWorldPlayers();assert(draw[0xc]==1&&ReadValue<float>(remote,0x20c)==1);
 // Death owns fading. An authoritative later alive visit repairs render/physics.
 peer.alive=0;hp=0;draw[0xc]=0;now++;Hear();TickBbscWorldPlayers();now+=1000;Hear();TickBbscWorldPlayers();assert(draw[0xc]==0&&resets==0);
 peer.alive=1;peer.visit++;hp=594;WriteValue(reinterpret_cast<u64>(control.data()),0x114,u16{1});now++;Hear();TickBbscWorldPlayers();
 now+=750;Hear();TickBbscWorldPlayers();assert(draw[0xc]==1&&resets==1&&ReadValue<u16>(reinterpret_cast<u64>(control.data()),0x114)==0);
 // Missing actor/model retries are bounded per journey, not per frame/address.
 remote=0;now++;Hear();TickBbscWorldPlayers();now+=2500;Hear();TickBbscWorldPlayers();assert(inserts==1);
 now+=4000;Hear();TickBbscWorldPlayers();assert(inserts==2);now+=4000;Hear();TickBbscWorldPlayers();assert(inserts==2);
 // Independent lifecycles cover all room peers without a hardcoded host/guest slot.
 for(int i=0;i<4;++i){World::PlayerVisualLife life;World::PlayerVisualInput in;in.loading=false;in.here=true;in.alive=in.actor_alive=in.actor_ready=in.task_ready=true;in.local_visit=1;in.peer_visit=i+1;in.actor=i+100;in.model=i+200;in.draw_off=true;
  assert(life.Observe(in,1000).rebind);assert(life.Observe(in,1750).show);in.actor_ready=false;assert(!life.Observe(in,2000).show);assert(!life.Observe(in,6000).insert);in.loading=true;assert(!life.Observe(in,7000).show);}
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
    print('PASS production per-peer player lifecycle: native binding/insertion, load/address reuse, apart/reunion, alive/dead render repair, bounded retries, four remote peers')
if __name__=='__main__':main()
