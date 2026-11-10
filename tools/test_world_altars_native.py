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
#include "core/bbsc_lift_flags.h"
#include "core/bbsc_lamp_travel_data.h"
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
std::array<u8,125*1200> lamp_backing{};
s32 PS4_SYSV_ABI LampIndex(s32 kind,s32 area,s32 block,s32 group){assert((kind==1||kind==6||kind==7)&&area>=40&&area<47&&block==0&&group<10);return 61+group*115+(kind==1?0:kind==6?46:69)+(area==40?0:5+area-40);}
std::map<u32,std::array<u8,125>> groups;
std::map<u32,std::array<u8,125>> own_kept;
std::mutex bbsc_progress_mutex;std::map<u32,std::array<u8,125>> bbsc_progress_groups;
bool share=true;bool BbscSharedProgressEnabled(){return share;}
s32 GetLocalPlayerType(){return 1;}
bool BbscBossCompletionBitsAdded(u32,size_t,u8 added){return (added&1)!=0;}
int reward_checks=0;void RequestBbscRewardCheck(){++reward_checks;}
bool BbscIndependentActive(){return active;}
void QueueBbscWorldLampWrite(u32,u32,u32){}
s32 GetSessionState(){return session;}
u32 map=0x18010000;u32 GetCurrentPackedMap(){return map;}
u64 GetGlobalState(){return reinterpret_cast<u64>(manager.data());}
std::atomic<u64> bbsc_world_native_load{1};s64 now=10000;s64 SteadyNowMs(){return now;}
int sends=0;void BbscWorldSend(const World::Control&,std::span<const u8>){++sends;}
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
template<class T>T ReadValue(u64 p,size_t offset){
 if(p==image_base+WorldFlagManPointerOffset)return static_cast<T>(reinterpret_cast<u64>(manager.data()));
 T result;std::memcpy(&result,reinterpret_cast<void*>(p+offset),sizeof(T));return result;
}
u64 BbscFlagGroupStorage(u32 key){auto it=groups.find(key);return it==groups.end()?0:reinterpret_cast<u64>(it->second.data());}
bool BbscEventFlag(u32 flag){const u64 p=BbscFlagGroupStorage(flag/1000);return p&&(reinterpret_cast<u8*>(p)[flag%1000/8]&(0x80>>(flag%8)));}
u32 BbscWorldGroupKey(u32 map,size_t i){return static_cast<u32>((Chalice::IsMap(map)?12900:20000)+i);}
void BbscMergeSharedProgressGroup(u32,u8* live,const u8* incoming){for(size_t i=0;i<125;++i)live[i]|=incoming[i];}
bool BbscIsBossWipeLoad(const World::Scope&){return false;}
void KeepBbscEncounterFlags(const World::Scope&,u32,const u8*,u8*){}
void KeepBbscOwnWorldGroup(u32 key,const u8* p){if(!own_kept.contains(key))std::memcpy(own_kept[key].data(),p,125);}
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
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,128*1024*1024,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 Link(0x1AB2A40,reinterpret_cast<void*>(&Channel));Link(0x1AB1DB0,reinterpret_cast<void*>(&Layout));
 Link(0x1AB3070,reinterpret_cast<void*>(&Parts));Link(0x1AB31C0,reinterpret_cast<void*>(&Type));
 Link(0x13BC710,reinterpret_cast<void*>(&LampIndex));
 u32 stride=125,count=1200;u64 backing=reinterpret_cast<u64>(lamp_backing.data());
 std::memcpy(manager.data()+0x20,&stride,4);std::memcpy(manager.data()+0x24,&count,4);std::memcpy(manager.data()+0x28,&backing,8);
 ORIGINAL_INDEX
 using Index=s32 PS4_SYSV_ABI (*)(s32,s32,s32,s32);
 for(int slot=0;slot<7;++slot){
  const s32 idx=reinterpret_cast<Index>(image_base+0x13BC710)(1,40+slot,0,7);
  assert(idx==LampIndex(1,40+slot,0,7));
  for(int lamp=0;lamp<10;++lamp)for(int form=0;form<2;++form){
   lamp_backing.fill(0);const u32 off=800+lamp*20+form*10;
   lamp_backing[idx*125+off/8]=0x80u>>(off%8);u64 bits=0;
   assert(BbscWorldReadAltarLamps(slot,bits)&&bits==(u64{1}<<(lamp*2+form)));
  }
 }
 lamp_backing.fill(0);lamp_backing[LampIndex(1,43,0,7)*125+101]=0x20;
 u64 unavailable=0;u32 zero_count=0;
 std::memcpy(manager.data()+0x24,&zero_count,4);assert(!BbscWorldReadAltarLamps(3,unavailable));
 std::memcpy(manager.data()+0x24,&count,4);
 const u32 first=94300;for(u32 i=0;i<6;++i)groups[first+i]={};
 groups[first][0]=29;groups[first+1][6]=2; // record byte 131, native feature low bits
 BbscWorldAltar altar;assert(BbscWorldReadAltar(3,altar));
 assert(getter_slots==std::vector<s32>({3,3,3,3}));
 assert(altar.native_lamps==(u64{1}<<1));
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
 assert(own_kept[20000][0]==0x80&&groups[20000][0]==0x91&&groups[20000][1]==0x91);
 const auto personal=own_kept;scope.map=0x15000000;BbscWorldApplyFlags(scope,state);
 assert(dream_calls==0&&own_kept==personal); // map snapshots never replay Dream services/phase
 bbsc_world_presence_local.world={11,99};bbsc_world_guest_altars.Bind({11,99});
 for(u8 slot=0;slot<7;++slot){
  BbscWorldAltarWire wire;wire.slot=slot;wire.current=3;wire.revision=10;wire.ritual=8+slot+1;
  if(slot==3){wire.occupied=1;wire.record=altar.entry.record;wire.mount=altar.mount;wire.lamps=1;wire.native_lamps=altar.native_lamps;}
  BbscWorldIncoming message;message.sender=11;message.control.scope={{11,99},0x15000000,{},0};message.control.parts=7;message.control.part=slot;
  message.payload.resize(sizeof(wire));std::memcpy(message.payload.data(),&wire,sizeof(wire));
  BbscWorldReceiveAltar(message);
  assert(bbsc_world_catalog_ready.load()==(slot==6));
 }
 assert(bbsc_world_altars[3].native_lamps==altar.native_lamps);
 assert(bbsc_world_guest_altars.Destination(3,12,0));
 assert(!bbsc_world_guest_altars.Destination(3,11,0));
 assert(groups[94300]==before.at(94300)); // receiving a guest view does not install it into a save
 // A scoped dungeon snapshot replaces a previously mounted cup's lamps;
 // the guest's original bits remain in its existing own-world journal.
 {World::Scope cup{{11,99},0x1D000000,altar.mount.key,12};
  BbscWorldState mounted;mounted.flags_ready=true;mounted.present=1u|(1u<<7);
  groups[12900]={};
  for (u32 flag : {450,455,460,465}) mounted.groups[0][flag/8]|=0x80u>>(flag%8);
  mounted.groups[0][450/8]|=0x80u>>(449%8); // a neighboring flag still follows the snapshot
  BbscWorldApplyFlags(cup,mounted,true);
  for (u32 flag : {455,460,465}) assert(!BbscEventFlag(12900000+flag));
  assert(BbscEventFlag(12900449)&&BbscEventFlag(12900450));
  groups[12907].fill(0xFF);own_kept.erase(12907);
  BbscWorldApplyFlags(cup,mounted);
  for (u32 flag : {450,455,460,465}) assert(BbscEventFlag(12900000+flag));
  mounted.groups[0]={};
  BbscWorldApplyFlags(cup,mounted,true);
  for (u32 flag : {455,460,465}) assert(BbscEventFlag(12900000+flag));
  assert(!BbscEventFlag(12900449)&&!BbscEventFlag(12900450));
  for(u32 flag:Chalice::LampUnlockFlags){
   assert(!(groups[12907][flag%1000/8]&(0x80u>>(flag%8))));
   assert(own_kept[12907][flag%1000/8]&(0x80u>>(flag%8)));
  }
 }
 // Altar reception/application must leave ordinary map progress untouched.
 groups[12417].fill(0xA5);const auto ordinary_lamps=groups[12417];
 // A resident guest's older map state cannot erase the host's opened progress.
 session=3;scope.map=0x18000000;state.groups[0].fill(0);
 BbscWorldApplyFlags(scope,state);assert(groups[20000][1]==0x91);
 session=6;state.groups[0][1]=0x04;BbscWorldApplyFlags(scope,state);
 assert(groups[20000][1]==0x95);
 BbscWorldState shared;shared.flags_ready=true;shared.present=1;shared.groups[0][2]=1;
 World::Scope ordinary{{11,99},0x18010000,{},0};BbscWorldRememberProgress(ordinary,shared);
 assert(bbsc_progress_groups[20000][2]==1&&reward_checks==1);
 ordinary.map=0x1D000000;shared.groups[0][3]=1;BbscWorldRememberProgress(ordinary,shared);
 assert(bbsc_progress_groups[20000][3]==0); // no chalice leakage into ordinary shared progress
 ordinary.map=0x18010000;share=false;BbscWorldRememberProgress(ordinary,shared);assert(bbsc_progress_groups[20000][3]==0);
 // Guest Dream admission atomically replaces ALL seven slots, including
 // personal cups in slots where the host has no ritual. No timer is involved.
 map=BbscDreamStateMap;
 for(u32 i=0;i<7;++i)for(u32 j=0;j<6;++j)groups[94000+i*100+j].fill(0xA5);
 const auto personal_altars=groups;
 groups.erase(94605);assert(!BbscWorldApplyAltars(map));
 assert(groups[94000]==personal_altars.at(94000)); // no partial installation
 groups[94605]=personal_altars.at(94605);
 assert(BbscWorldApplyAltars(map));
 assert(groups[12417]==ordinary_lamps);
 for(u32 i=0;i<7;++i)for(u32 j=0;j<6;++j){
  const u32 key=94000+i*100+j;
  assert(std::memcmp(groups[key].data(),bbsc_world_altars[i].entry.record.data()+125*j,125)==0);
  assert(own_kept[key]==personal_altars.at(key));
 }
 assert(groups[94000][0]==0&&groups[94300][0]==29); // own cup hidden, host cup visible
 session=4;assert(BbscWorldApplyAltars(map)); // joining events are fenced too
 assert(BbscWorldProtectAltar(94000000,32)&&BbscWorldProtectAltar(94605999,1));
 assert(!BbscWorldProtectAltar(9020,1)); // local native altar selector is still writable
 session=3;groups[94000][0]=0xAA;assert(BbscWorldApplyAltars(map)&&groups[94000][0]==0xAA);
 session=6;bbsc_world_catalog_ready=false;assert(!BbscWorldApplyAltars(map));
 // Host capture is driven by native writes/load changes. Timer retransmission
 // keeps the revision and does not reread the seven rituals.
 session=3;bbsc_world_altar_world=bbsc_world_presence_local.world;
 for(u32 flag:{9020u,9026u,12907800u,12907810u,94000000u}){
  bbsc_world_altars_dirty=false;QueueBbscWorldAltarWrite(flag,1,1);assert(bbsc_world_altars_dirty);
 }
 bbsc_world_altars_dirty=false;QueueBbscWorldAltarWrite(73100001,1,1);assert(!bbsc_world_altars_dirty);
 for(u32 i=0;i<7;++i)for(u32 j=0;j<6;++j)groups[94000+i*100+j]={};
 for(u32 j=0;j<6;++j)groups[94300+j]=before.at(94300+j);
 bbsc_world_altars_dirty=true;TickBbscWorldAltars();
 const auto revision=bbsc_world_altar_revision;const auto reads=getter_slots.size();const auto sent=sends;
 now+=2000;TickBbscWorldAltars();assert(sends==sent+7&&getter_slots.size()==reads&&bbsc_world_altar_revision==revision);
 QueueBbscWorldAltarWrite(94300000,1,0);TickBbscWorldAltars();
 assert(getter_slots.size()>reads&&bbsc_world_altar_revision==revision); // unchanged native write
 groups[94000][1]=1;QueueBbscWorldAltarWrite(94000008,1,1);TickBbscWorldAltars();
 assert(bbsc_world_altar_revision==revision+1);
 const auto read_after=getter_slots.size();++bbsc_world_native_load;TickBbscWorldAltars();
 assert(getter_slots.size()>read_after); // a new backing flag table needs a fresh capture
 // Historical lamp changes alone invalidate/retransmit the existing catalogue.
 const auto lamp_revision=bbsc_world_altar_revision;
 lamp_backing[LampIndex(1,43,0,7)*125+103]^=0x02;
 QueueBbscWorldAltarWrite(12907830,1,1);TickBbscWorldAltars();
 assert(bbsc_world_altar_revision==lamp_revision+1);
 VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
'''

def main():
    section=SOURCE[SOURCE.index('struct BbscWorldAltar {'):SOURCE.index('struct BbscWorldState {')]
    state=SOURCE[SOURCE.index('struct BbscWorldState {'):SOURCE.index('std::map<World::Scope,BbscWorldState>')]
    code=PREFIX+section+state+function('void BbscWorldRememberProgress(const World::Scope& scope,const BbscWorldState& state)')+function('void BbscWorldApplyFlags(const World::Scope& scope,const BbscWorldState& state,bool live_dungeon = false)')+function('void BbscWorldReceiveAltar(const BbscWorldIncoming& message)')+function('void TickBbscWorldAltars()')+MAIN
    original=''
    if os.environ.get('BBSC_TEST_EBOOT'):
        import struct
        data=Path(os.environ['BBSC_TEST_EBOOT']).read_bytes()
        ph=struct.unpack_from('<Q',data,32)[0];size,n=struct.unpack_from('<HH',data,54)
        segments=[struct.unpack_from('<II6Q',data,ph+i*size) for i in range(n)]
        def read(a,n):
            seg=next(s for s in segments if s[0]==1 and s[3]<=a and a+n<=s[3]+s[5])
            return data[seg[2]+a-seg[3]:seg[2]+a-seg[3]+n]
        # Original selected-slot rebinding uses map40+slot and group7.
        assert read(0x13BA788,15)==bytes.fromhex('41be2f0000004129cebf0100000031')
        assert read(0x13BA98B,8)==bytes.fromhex('4489f6e87d1d0000')
        for a,n in ((0x13BC710,0x16B),(0x4730C10,20),(0x47314D0,136)):
            raw=read(a,n)
            original+=' {const u8 bytes[]={'+','.join(str(x) for x in raw)+'};std::memcpy(reinterpret_cast<void*>(image_base+'+hex(a)+'),bytes,sizeof(bytes));}\n'
    code=code.replace('ORIGINAL_INDEX',original)
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-world-altars-') as tmp:
        cpp=Path(tmp)/'altars.cpp';exe=Path(tmp)/'altars.exe';cpp.write_text(code,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production native altar getters/ABI, layout proof, host progress proposals, personal flag journal, atomic guest view')

if __name__=='__main__':main()
