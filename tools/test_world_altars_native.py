"""Production altar reads/view/progress routing with native getter ABI stubs.

Uses allocated fixture memory only; does not open real saves or game processes.
"""
from pathlib import Path
import os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'emulator/src/core/bbsc_world_state.inc').read_text(encoding='utf-8')
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
#include "core/bbsc_world_altars.h"
#include "core/bbsc_world_control.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
constexpr u64 WorldFlagManPointerOffset=0x553B100;
constexpr u32 BbscDreamStateMap=0x15000000;
bool active=true;s32 session=6;
u64 image_base=0;
std::array<u8,64> manager{};
std::map<u32,std::array<u8,125>> groups;
std::map<u32,std::array<u8,125>> own_kept;
bool BbscIndependentActive(){return active;}
s32 GetSessionState(){return session;}
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
template<class T>T ReadValue(u64 p,size_t offset){
 if(p==image_base+WorldFlagManPointerOffset)return static_cast<T>(reinterpret_cast<u64>(manager.data()));
 T result;std::memcpy(&result,reinterpret_cast<void*>(p+offset),sizeof(T));return result;
}
u64 BbscFlagGroupStorage(u32 key){auto it=groups.find(key);return it==groups.end()?0:reinterpret_cast<u64>(it->second.data());}
u32 BbscWorldGroupKey(u32,size_t i){return static_cast<u32>(20000+i);}
void KeepBbscOwnWorldGroup(u32 key,const u8* p){std::memcpy(own_kept[key].data(),p,125);}
void KeepBbscGuestTalkBits(u32,const u8*,u8*){}
void KeepBbscNpcOwnBits(u32,const u8* before,u8* live){live[0]=(live[0]&0x7f)|(before[0]&0x80);}
int dream_calls=0;void ApplyBbscHostDreamState(const char*){++dream_calls;}
std::mutex bbsc_world_presence_mutex;
World::Presence bbsc_world_presence_local;
struct BbscWorldIncoming{u32 sender;World::Control control;std::vector<u8> payload;};
std::vector<s32> getter_slots;
void* PS4_SYSV_ABI Channel(void* out,const s32* slot){getter_slots.push_back(*slot);const u64 channel=55+*slot;std::memcpy(out,&channel,8);return out;}
void* PS4_SYSV_ABI Layout(void* out,const s32* slot){getter_slots.push_back(*slot);const u32 map=0x1D0A5A00;std::memcpy(out,&map,4);return out;}
void* PS4_SYSV_ABI Parts(void* out,const s32* slot){getter_slots.push_back(*slot);auto* p=static_cast<s32*>(out);std::fill(p,p+18,-1);p[0]=6109;p[1]=45;return out;}
void* PS4_SYSV_ABI Type(void* out,const s32* slot){getter_slots.push_back(*slot);const s32 type=0;std::memcpy(out,&type,4);return out;}
void Link(u64 offset,void* target){
 auto* p=reinterpret_cast<u8*>(image_base+offset);p[0]=0x48;p[1]=0xB8;
 const u64 address=reinterpret_cast<u64>(target);std::memcpy(p+2,&address,8);p[10]=0xFF;p[11]=0xE0;
}
'''
MAIN=r'''
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,32*1024*1024,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 Link(0x1AB2A40,reinterpret_cast<void*>(&Channel));Link(0x1AB1DB0,reinterpret_cast<void*>(&Layout));
 Link(0x1AB3070,reinterpret_cast<void*>(&Parts));Link(0x1AB31C0,reinterpret_cast<void*>(&Type));
 const u32 first=94300;for(u32 i=0;i<6;++i)groups[first+i]={};
 groups[first][0]=29;groups[first+1][6]=2; // record byte 131, native feature low bits
 BbscWorldAltar altar;assert(BbscWorldReadAltar(3,altar));
 assert(getter_slots==std::vector<s32>({3,3,3,3}));
 assert(altar.entry.occupied&&altar.mount.key.channel==58&&altar.mount.layout_map==0x1D0A5A00);
 assert(altar.mount.parts[0]==6109&&altar.mount.parts[1]==45&&altar.mount.feature==2);
 assert(altar.entry.form.size()==88&&Chalice::HashForm(altar.entry.form)==altar.mount.key.form_hash);
 altar.entry.ritual=12;assert(World::Valid(altar.entry));
 const auto before=groups;groups.erase(first+5);BbscWorldAltar unknown;
 assert(!BbscWorldReadAltar(3,unknown));groups=before;
 // A valid native read never writes the altar flags, selector or a ritual cache.
 assert(groups==before);
 bbsc_world_altars[3]=altar;
 QueueBbscWorldAltarWrite(94305003,5,21);
 assert(bbsc_world_altar_progress[3].mask[0]==0x1F&&bbsc_world_altar_progress[3].bits[0]==0x15);
 const auto mask=bbsc_world_altar_progress[3].mask;
 QueueBbscWorldAltarWrite(94304999,2,3);QueueBbscWorldAltarWrite(94305999,2,3);
 assert(bbsc_world_altar_progress[3].mask==mask);
 // The write is a proposal to the host, never a mutation of the personal/live record.
 assert(groups==before);
 groups[20000].fill(0x80);BbscWorldState state;state.flags_ready=true;state.present=1;state.groups[0].fill(0x11);
 World::Scope scope{{11,99},0x18000000,{},0};BbscWorldApplyFlags(scope,state);
 assert(own_kept[20000][0]==0x80&&groups[20000][0]==0x91&&groups[20000][1]==0x11);
 const auto personal=own_kept;scope.map=0x15000000;BbscWorldApplyFlags(scope,state);
 assert(dream_calls==0&&own_kept==personal); // map snapshots never replay Dream services/phase
 bbsc_world_presence_local.world={11,99};bbsc_world_guest_altars.Bind({11,99});
 for(u8 slot=0;slot<7;++slot){
  BbscWorldAltarWire wire;wire.slot=slot;wire.current=3;wire.revision=10;wire.ritual=8+slot+1;
  if(slot==3){wire.occupied=1;wire.record=altar.entry.record;wire.mount=altar.mount;wire.lamps=1;}
  BbscWorldIncoming message;message.sender=11;message.control.scope={{11,99},0x15000000,{},0};message.control.parts=7;message.control.part=slot;
  message.payload.resize(sizeof(wire));std::memcpy(message.payload.data(),&wire,sizeof(wire));
  BbscWorldReceiveAltar(message);
  assert(bbsc_world_catalog_ready.load()==(slot==6));
 }
 assert(bbsc_world_guest_altars.Destination(3,12,0));
 assert(!bbsc_world_guest_altars.Destination(3,11,0));
 assert(groups[94300]==before.at(94300)); // receiving a guest view does not install it into a save
 VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
'''

def main():
    section=SOURCE[SOURCE.index('struct BbscWorldAltar {'):SOURCE.index('struct BbscWorldState {')]
    state=SOURCE[SOURCE.index('struct BbscWorldState {'):SOURCE.index('std::map<World::Scope,BbscWorldState>')]
    code=PREFIX+section+state+function('void BbscWorldApplyFlags(const World::Scope& scope,const BbscWorldState& state)')+function('void BbscWorldReceiveAltar(const BbscWorldIncoming& message)')+MAIN
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-world-altars-') as tmp:
        cpp=Path(tmp)/'altars.cpp';exe=Path(tmp)/'altars.exe';cpp.write_text(code,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production native altar getters/ABI, layout proof, host progress proposals, personal flag journal, atomic guest view')

if __name__=='__main__':main()
