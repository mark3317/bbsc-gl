"""Production lamp synchronization in allocated memory, no game/save access."""
from pathlib import Path
import os, shutil, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include <atomic>
#include <cassert>
#include <mutex>
#include "core/bbsc_world_control.h"
#include "core/bbsc_world_altars.h"
#include "core/bbsc_lamp_travel_data.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
bool active=true,finale_committed=false;int session=6;u32 self=22;u32 current=0x18010000;s64 now=1000;
std::array<u8,16> global{};
bool BbscIndependentActive(){return active;}s32 GetSessionState(){return session;}
bool BbscNativeFinaleCommitted(){return finale_committed;}
namespace BbscMod{u32 RegisterOwnId(){return self;}}
u32 GetCurrentPackedMap(){return current;}bool BbscWorldSceneReady(){return true;}
u64 GetGlobalState(){return reinterpret_cast<u64>(global.data());}
bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64 p,size_t o){T v;std::memcpy(&v,reinterpret_cast<void*>(p+o),sizeof(v));return v;}
s64 SteadyNowMs(){return now;}
std::atomic<u32> bbsc_load_generation{1};constexpr u32 BbscDreamStateMap=0x15000000;
std::mutex bbsc_world_presence_mutex,bbsc_progress_mutex;World::Presence bbsc_world_presence_local;
struct Book{const int* Resident(u32 peer){static int member;return peer==22||peer==33?&member:nullptr;}}bbsc_world_presence_book;
struct BbscWorldAltar{World::AltarEntry entry;Chalice::Mount mount;u64 native_lamps=0;};std::array<BbscWorldAltar,7> bbsc_world_altars;
World::WorldId bbsc_world_altar_world{11,99};
std::atomic<bool> bbsc_world_altars_dirty{false};
std::array<std::array<u8,125>,7> host_lamp_groups{};
s32 BbscWorldHostAltarSlot(const World::Scope& scope){
 if(session!=3||scope.world!=bbsc_world_altar_world)return -1;
 for(s32 slot=0;slot<7;++slot)if(bbsc_world_altars[slot].entry.occupied&&bbsc_world_altars[slot].entry.ritual==scope.ritual&&bbsc_world_altars[slot].mount.key==scope.dungeon)return slot;
 return -1;
}
u64 BbscWorldNativeAltarGroup(s32 slot,u32 kind,u32 group){assert(kind==1&&group==7);return slot<0?0:reinterpret_cast<u64>(host_lamp_groups[slot].data());}

std::atomic<bool> bbsc_world_catalog_ready{true};
struct BbscWorldState{bool flags_ready=false;u64 present=0;std::array<std::array<u8,125>,30> groups{};};
std::map<u32,std::array<u8,125>> groups,own,bbsc_progress_groups;
bool BbscSharedProgressEnabled(){return true;}
u64 BbscFlagGroupStorage(u32 k){return reinterpret_cast<u64>(groups[k].data());}
void KeepBbscOwnWorldGroup(u32 k,const u8* p){if(!own.contains(k))std::memcpy(own[k].data(),p,125);}
bool BbscEventFlag(u32 f){return groups[f/1000][f%1000/8]&(0x80u>>(f%8));}
u32 BbscLampPointMap(s32 p){return ((p/100000)<<24)|(((p/10000)%10)<<16);}
u32 BbscWorldGroupKey(u32 map,size_t i){return 10000+(map>>24)*100+((map>>16)&255)*10+i;}
struct BbscWorldIncoming{u32 sender;World::Control control;std::vector<u8> payload;};
std::vector<BbscWorldIncoming> sent;
void BbscWorldSend(const World::Control& c,std::span<const u8> b){sent.push_back({self,c,{b.begin(),b.end()}});}
'''
MAIN=r'''
int main(){
 // Every original ordinary destination, both flag forms, both native setter widths.
 const World::WorldId world{11,99};
 for(size_t i=0;i<LampTravel::Returns.size();++i){
  current=BbscLampPointMap(LampTravel::Returns[i].point);bbsc_world_presence_local.world=world;bbsc_world_presence_local.map=current;
  bbsc_world_lamp_pending.clear();const u32 flag=BbscWorldLampFlag(i,false);
  QueueBbscWorldLampWrite(flag-10,1,1);assert(bbsc_world_lamp_pending.begin()->second==(u64{1}<<i));
  bbsc_world_lamp_pending.clear();QueueBbscWorldLampWrite(flag-1,2,1);assert(bbsc_world_lamp_pending.begin()->second==(u64{1}<<i));
  bbsc_world_lamp_pending.clear();QueueBbscWorldLampWrite(flag,1,0);QueueBbscWorldLampWrite(flag+1,1,1);assert(bbsc_world_lamp_pending.empty());
 }
 current=0x18010000;bbsc_world_presence_local.world=world;bbsc_world_presence_local.map=current;
 // Non-owner guest lights the actual native 7800 flag, not merely the 7810 menu flag.
 QueueBbscWorldLampWrite(12417800,1,1);assert(bbsc_world_lamp_pending.size()==1);
 TickBbscWorldLamps();assert(sent.size()==1);const auto proposal=sent.back();assert(proposal.control.kind==World::ControlKind::Lamps);
 const auto guest_pending=bbsc_world_lamp_pending;
 // Host is in another map. It accepts a member's discovery without an NPC-owner lease.
 bbsc_world_lamp_pending.clear();bbsc_world_lamps.clear();self=11;session=3;current=0x15000000;bbsc_world_presence_local.map=current;
 BbscWorldReceiveLamps(proposal);assert(bbsc_world_lamps.size()==1);
 now+=1000;sent.clear();TickBbscWorldLamps();assert(BbscEventFlag(12417800)&&BbscEventFlag(12417810));assert(sent.size()==1);
 const auto canonical=sent.back();auto invalid=canonical;invalid.sender=77;
 // Two guests in Dream/another ordinary map get the headstone AND lit state.
 for(u32 peer:{22u,33u}){
  groups.clear();own.clear();bbsc_progress_groups.clear();bbsc_world_lamps.clear();bbsc_world_lamp_pending=guest_pending;
  self=peer;session=6;current=peer==22?0x15000000:0x17000000;bbsc_world_presence_local.map=current;
  BbscWorldReceiveLamps(invalid);assert(bbsc_world_lamps.empty());
  BbscWorldReceiveLamps(canonical);BbscWorldReceiveLamps(canonical);now+=1000;
  finale_committed=true;sent.clear();TickBbscWorldLamps();
  assert(!BbscEventFlag(12417800)&&sent.empty());
  finale_committed=false;TickBbscWorldLamps();
  assert(BbscEventFlag(12417800)&&BbscEventFlag(12417810));assert((own[12417]==std::array<u8,125>{}));
  assert((bbsc_world_lamp_pending.begin()->second==0&&bbsc_progress_groups[12417]!=std::array<u8,125>{}));
 }
 // Two cups with identical m29 map IDs have distinct ritual/channel scopes.
 auto& a=bbsc_world_altars[2];a.entry.occupied=true;a.entry.ritual=11;a.mount.key={55,66,88,0};
 auto& b=bbsc_world_altars[3];b.entry.occupied=true;b.entry.ritual=12;b.mount.key={56,66,88,0};
 current=0x1D0A5A00;bbsc_world_presence_local.map=current;bbsc_world_presence_local.dungeon=a.mount.key;bbsc_world_presence_local.ritual=11;
 groups[12907].fill(0);groups[12907][1]=0x20;const auto personal=groups[12907];own.erase(12907);
 QueueBbscWorldLampWrite(12907820,1,1);const auto cup=World::ScopeOf(bbsc_world_presence_local);
 assert(bbsc_world_lamp_pending[cup]==2&&own[12907]==personal);
 // Transport retry is retained until canonical host acknowledgement.
 now+=1000;sent.clear();TickBbscWorldLamps();auto cup_proposal=sent.back();assert(cup_proposal.control.scope==cup);
 self=11;session=3;bbsc_world_lamp_pending.clear();
 current=0x15000000;bbsc_world_presence_local.map=current;
 const auto unrelated=groups[12907];BbscWorldReceiveLamps(cup_proposal);
 assert((host_lamp_groups[2][103]&0x02)&&(host_lamp_groups[2][102]&0x08));
 assert(groups[12907]==unrelated&&bbsc_world_altars_dirty.load());
 now+=1000;sent.clear();TickBbscWorldLamps();auto cup_canonical=sent.back();
 self=22;session=6;bbsc_world_lamps.clear();BbscWorldReceiveLamps(cup_canonical);
 current=0x15000000;bbsc_world_presence_local.map=current;bbsc_world_presence_local.dungeon={};bbsc_world_presence_local.ritual=0;
 BbscWorldSelectLampMenu(2);assert(BbscEventFlag(12907820)&&BbscEventFlag(12907830));
 World::Scope other{world,0x1D000000,b.mount.key,12};bbsc_world_lamps[other]=4;
 BbscWorldSelectLampMenu(3);assert(!BbscEventFlag(12907830)&&BbscEventFlag(12907850));
 BbscWorldSelectLampMenu(2);assert(BbscEventFlag(12907830)&&!BbscEventFlag(12907850));
 assert(own[12907]==personal&&!bbsc_progress_groups.contains(12907));
 // Historical host lamps arrive with the catalogue BEFORE any interaction,
 // discovery packet or mounted snapshot. Exact native forms are preserved.
 bbsc_world_lamps.clear();bbsc_world_lamp_pending.clear();
 for(int slot=0;slot<7;++slot){
  auto& altar=bbsc_world_altars[slot];altar.entry.occupied=true;
  altar.entry.ritual=100+slot;altar.mount.key={u64(1000+slot),66,88,0};
  for(int i=0;i<10;++i)for(int form=0;form<2;++form){
   groups[12907].fill(255);altar.native_lamps=u64{1}<<(2*i+form);
   BbscWorldSelectLampMenu(slot);
   for(int j=0;j<10;++j)for(int f=0;f<2;++f)
    assert(BbscEventFlag(12907800+j*20+f*10)==(j==i&&f==form));
  }
 }
 // A native empty cup is empty because of authoritative state, not a missing
 // discovery-cache entry; unrelated bits/personal backup remain untouched.
 a.native_lamps=0;b.native_lamps=0;const auto personal_backup=own[12907];
 groups[12907].fill(255);BbscWorldSelectLampMenu(2);
 for(int i=0;i<10;++i)assert(!BbscEventFlag(12907810+i*20));
 assert(own[12907]==personal_backup&&groups[12907][0]==255);
 // A missing catalogue or a different world is not fabricated lamp data.
 const auto before_guard=groups[12907];bbsc_world_catalog_ready=false;
 BbscWorldSelectLampMenu(3);assert(groups[12907]==before_guard);bbsc_world_catalog_ready=true;
 ++bbsc_world_presence_local.world.room;BbscWorldSelectLampMenu(3);
 assert(groups[12907]==before_guard);--bbsc_world_presence_local.world.room;
 // A new confirmed discovery augments historical state before a new revision.
 const World::Scope fresh{world,0x1D000000,b.mount.key,b.entry.ritual};
 b.native_lamps=u64{2}<<12;bbsc_world_lamps[fresh]=4;
 BbscWorldSelectLampMenu(3);assert(BbscEventFlag(12907930)&&BbscEventFlag(12907850));
 // Host native state is never projected from either catalogue or cache.
 session=3;groups[12907].fill(255);BbscWorldSelectLampMenu(2);
 assert(BbscEventFlag(12907850));session=6;
 // Restore the original scope for the subsequent lighting/snapshot tests.
 a.entry.ritual=11;a.mount.key={55,66,88,0};b.entry.ritual=12;b.mount.key={56,66,88,0};
 // Every dungeon lamp uses both lit/menu flags and a ritual-scoped snapshot.
 for(size_t i=0;i<10;++i){
  current=0x1D0A5A00;bbsc_world_presence_local.map=current;bbsc_world_presence_local.dungeon=a.mount.key;bbsc_world_presence_local.ritual=11;
  groups[12907].fill(0);bbsc_world_lamp_pending.clear();
  QueueBbscWorldLampWrite(12907800+i*20,1,1);assert(bbsc_world_lamp_pending[cup]==(u64{1}<<i));
  BbscWorldState initial;initial.flags_ready=true;initial.present=1u<<7;
  const u32 f=12907810+i*20;initial.groups[7][f%1000/8]=0x80u>>(f%8);
  bbsc_world_lamp_pending.clear();BbscWorldRememberLampSnapshot(cup,initial);assert(bbsc_world_lamp_pending[cup]==(u64{1}<<i));
 }
 // Wire roundtrip uses the existing version2 session envelope.
 auto wire=World::Encode(canonical.control,canonical.payload);auto decoded=World::DecodeControl(wire);assert(decoded&&decoded->kind==World::ControlKind::Lamps);
 // Re-created ritual and foreign session packets never unlock the replacement.
 a.entry.ritual=19;bbsc_world_lamps.clear();BbscWorldReceiveLamps(cup_canonical);assert(bbsc_world_lamps.empty());
 auto foreign=canonical;foreign.control.scope.world.room++;BbscWorldReceiveLamps(foreign);assert(bbsc_world_lamps.empty());
 // Malformed bitsets/foreign senders and native resets are ignored.
 auto malformed=canonical;malformed.payload.assign(8,255);BbscWorldReceiveLamps(malformed);assert(bbsc_world_lamps.empty());
 bbsc_world_lamp_pending.clear();active=false;QueueBbscWorldLampWrite(12417820,1,1);assert(bbsc_world_lamp_pending.empty());active=true;
 BbscWorldLampBind({11,100});assert(bbsc_world_lamp_pending.empty()&&bbsc_world_lamps.empty()&&bbsc_world_lamp_menu==-1);
}
'''
def main(negative=False):
 compiler=shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
 with tempfile.TemporaryDirectory(prefix='bbsc-lamps-') as tmp:
  p=Path(tmp);cpp=p/'lamps.cpp';exe=p/'lamps.exe'
  source=(ROOT/'emulator/src/core/bbsc_world_lamps.inc').read_text()
  if negative:source=source.replace('u64 flags=a.native_lamps;', 'u64 flags=0;')
  cpp.write_text(PREFIX+source+MAIN,encoding='utf-8')
  subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
  env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
  result=subprocess.run([str(exe)],env=env,capture_output=True)
  assert (result.returncode!=0) if negative else (result.returncode==0),result.stderr.decode(errors='replace')
 if negative:
  print('PASS negative control: omitted native historical lamp flags rejected');return
 print('PASS production session lamps: non-owner guest -> host -> two guests, lit/headstone bits, retry/ack, separate rituals, personal backup, native historical catalogue for seven slots/ten lamps, exact flag forms, malformed/stale/world fencing')
if __name__=='__main__':main();main(negative=True)
