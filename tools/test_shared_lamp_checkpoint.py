"""Production shared checkpoint, load preparation and neighbour fence; allocated memory only."""
from pathlib import Path
import os
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')

def function(text, signature):
    start = text.index(signature+' {')
    end = text.index('{', start)+1
    depth = 1
    while depth:
        depth += (text[end] == '{')-(text[end] == '}')
        end += 1
    return text[start:end]

code = r'''
#define NOMINMAX
#include <windows.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdlib>
#include <limits>
#include <map>
#include <mutex>
#include <string_view>
#include "core/bbsc_world_control.h"
#include "core/bbsc_world_altars.h"
#include "core/bbsc_world_lamp_points.h"
#include "core/bbsc_lamp_travel_data.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define BBSC_TIMELINE(...)
#define LOG_INFO(...)
#define PS4_SYSV_ABI __attribute__((sysv_abi))
bool active=true,snapshot=true,prepared=true,ready=true,needs_load=false,writable=true,finale_committed=false;
s32 role=3;u32 self=11,current=0x20000000;s64 now=1000,wall=10000;
bool invader=false; s32 GetLocalCharacterType(){return invader?2:1;}
bool IsInvaderType(s32 type){return type==2;}
bool invaded=false;int RemoteInvaderCount(){return invaded?1:0;}bool LivingPartnerExists(){return false;}
std::array<u8,0x280> player{};
s32 hp=594;u64 GetLocalPlayerCharacter(){return (u64)player.data();}s32 GetCharacterHp(u64){return hp;}
std::array<u8,0x1800> global{};u64 image_base=0;
constexpr u32 BbscDreamStateMap=0x15000000;
std::atomic<u32> bbsc_load_generation{1};
World::Presence bbsc_world_presence_local;
std::mutex bbsc_world_presence_mutex;World::PresenceBook bbsc_world_presence_book;
struct Altar {World::AltarEntry entry{};Chalice::Mount mount{};};std::array<Altar,7> bbsc_world_altars;
std::optional<World::Scope> bbsc_world_requested_scope;
std::optional<Chalice::Mount> bbsc_world_requested_mount;
s32 bbsc_world_altar_visiting=-1,bbsc_world_travel_point=0;
u32 bbsc_world_travel_flag=0,bbsc_world_travel_load=0;
World::WorldId bbsc_world_travel_world{};
bool bbsc_world_travel_inflight=false,bbsc_world_travel_saw_load=false,bbsc_world_travel_native_armed=false;
s64 bbsc_world_travel_since=0,bbsc_world_travel_request_sent=0;
u64 bbsc_world_state_sequence=0;
bool BbscIndependentActive(){return active;}bool BbscIndependentTravelAllowed(){return active;}
bool BbscNativeFinaleCommitted(){return finale_committed;}
s32 GetSessionState(){return role;}s64 SteadyNowMs(){return now;}
u32 GetCurrentPackedMap(){return current;}u64 GetGlobalState(){return (u64)global.data();}
bool IsUsablePackedMap(u32 map){return map!=0;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
namespace BbscMod {u32 RegisterOwnId(){return self;}}
enum class MemoryProt{CpuWrite};bool HasMemoryAccess(u64,size_t,MemoryProt){return writable;}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
template<class T>bool WriteValue(u64 p,size_t o,T v){
 if(!writable)return false;
 memcpy((void*)(p+o),&v,sizeof(v));return true;
}
bool BbscChaliceArrivalReady(u32){return ready;}bool BbscChaliceNeedsLoad(u32){return needs_load;}
bool PrepareBbscChaliceLoad(u32){return prepared;}
void BbscWorldEnsureSeed(const World::Scope&){}bool BbscWorldHasSnapshot(u32){return snapshot;}
int notifications=0,clears=0,loads=0,fallbacks=0,lookups=0,local_selections=0;s32 loaded_point=0;
void NotifyBbscHostDeathReload(){++notifications;}void ClearBbscBossContext(std::string_view){++clears;}
void RequestBbscDeathReload(std::string_view);
constexpr u64 DeathReloadRequestOffset=0x013CDE30;
constexpr u64 SelectSummonedPlacementOffset=0x01332BC0;
bool point_request=false;std::array<u8,16> point_desc{};u64 cookie=123;
u64 PS4_SYSV_ABI NativeReload(){if(point_request){++loads;point_request=false;}else ++fallbacks;return 1;}
void PS4_SYSV_ABI NativeDescriptor(u64 desc,s32 p){
 point_request=true;loaded_point=p;const u32 map=BbscLampPointMap(p);
 const uint16_t area=map>>24,block=(map>>16)&255;
 memcpy(point_desc.data(),&area,2);memcpy(point_desc.data()+2,&block,2);
 memcpy(point_desc.data()+4,&p,4);const s32 aux=101163;memcpy(point_desc.data()+8,&aux,4);
 WriteValue<u64>(desc,0x10,(u64)point_desc.data());
}
void PS4_SYSV_ABI NativeLoad(s32 p){++loads;loaded_point=p;}
void PS4_SYSV_ABI NativeDeathDestination(u32* out,s32 point){
 assert(point==ReadValue<s32>(GetGlobalState(),0x1528));++local_selections;
 *out=point/100000==29?current:BbscLampPointMap(point);
}
bool PS4_SYSV_ABI NativeDeathSelect(u64,s32 point){
 assert(point==-1 && !ReadValue<u8>(GetGlobalState(),0x1520));
 u32 map;NativeDeathDestination(&map,ReadValue<s32>(GetGlobalState(),0x1528));
 WriteValue<u32>(GetGlobalState(),0xC,map);return true;
}
struct BbscWorldIncoming{u32 sender;World::Control control;std::vector<u8> payload;};
std::vector<BbscWorldIncoming> sent;
void BbscWorldSend(const World::Control& c,std::span<const u8> p={}){sent.push_back({self,c,{p.begin(),p.end()}});}
bool BbscWorldLampScopeKnown(const World::Scope& scope){
 return !Chalice::IsMap(scope.map)||std::ranges::any_of(bbsc_world_altars,[&](const auto& a){
  return a.entry.occupied&&a.entry.ritual==scope.ritual&&a.mount.key==scope.dungeon;});
}
struct BbscTransform{std::array<float,4> position{},rotation{};};
std::vector<u32> flags;
bool BbscEventFlag(u32 flag){return std::ranges::find(flags,flag)!=flags.end();}
std::optional<BbscTransform> body;
std::optional<BbscTransform> ReadCharacterTransform(u64){return body;}
s32 unavailable=-1;
// Deliberately succeeds for OTHER resident maps, matching the reported failure.
std::optional<BbscTransform> ResolveLampPoint(s32 p){
 ++lookups;if(p==unavailable)return {};
 BbscTransform t;t.position[0]=p;return t;
}
'''
code = code.replace('void PS4_SYSV_ABI NativeDescriptor', 'u32 BbscLampPointMap(s32 point);\nvoid PS4_SYSV_ABI NativeDescriptor')
code += function(source, 'u32 BbscLampPointMap(s32 point)')
for signature in ('std::optional<u32> BbscLampLitFlag(s32 point)', 's32 BbscChaliceLayerFirstLamp(u64 player)',
                  'void SelectBbscLocalDeathLamp()'):
    code += '\n' + function(source, signature)
checkpoint = (ROOT/'emulator/src/core/bbsc_world_checkpoint.inc').read_text(encoding='utf-8')
if os.environ.get('BBSC_TEST_SHARED_CHECKPOINT_OLD'):
    checkpoint = checkpoint.replace('lamp.sequence<=bbsc_checkpoint_seen[lamp.actor]', 'false')
checkpoint = checkpoint.replace(function(checkpoint, 's64 BbscLampSelectionTimeMs()'),
                                's64 BbscLampSelectionTimeMs() { return wall; }')
if os.environ.get('BBSC_TEST_LAMP_PRIORITY_OLD'):
    checkpoint = checkpoint.replace('if(bbsc_native_lamp_selected_ms && bbsc_checkpoint.lit_ms<=bbsc_native_lamp_selected_ms)return false;', '')
if os.environ.get('BBSC_TEST_DEATH_MAP_OLD'):
    checkpoint = checkpoint.replace('if(bbsc_checkpoint.scope!=World::ScopeOf(local) ||\n'
        '       bbsc_checkpoint.scope.map!=(Chalice::IsMap(map)?0x1D000000u:map))return false;', '')
code += checkpoint
code += function(source, 'void RequestBbscDeathReload(std::string_view why)')
resolve = function(source, 'std::optional<BbscTransform> ResolveLastLampTransform()')
if os.environ.get('BBSC_TEST_NEIGHBOUR_OLD'):
    resolve = resolve.replace('if (!here) return std::nullopt;', 'if (false) return std::nullopt;')
code += resolve
code += r'''
const World::WorldId world{11,99};
void local(u32 peer,u32 map){
 self=peer;role=peer==11?3:6;current=map;
 bbsc_world_presence_local={};bbsc_world_presence_local.world=world;bbsc_world_presence_local.map=map;
 bbsc_world_presence_book.Bind(world,peer);
}
void reset(){BindBbscSharedLamp({11,100});BindBbscSharedLamp(world);sent.clear();global.fill(0);bbsc_world_presence_book.Bind({11,100},11);local(11,0x20000000);
 bbsc_world_requested_scope.reset();bbsc_world_requested_mount.reset();bbsc_world_travel_inflight=false;bbsc_world_altar_visiting=-1;}
void member(u32 id){World::Presence p=bbsc_world_presence_local;p.sequence=1;p.visit=1;p.phase=World::Phase::Playing;
 assert(bbsc_world_presence_book.Hear(id,world,p,now));}
BbscWorldIncoming proposal(u32 peer,s32 point,u64 seq){
 World::Control c;c.kind=World::ControlKind::LampCheckpoint;c.scope={world,BbscLampPointMap(point),{},0};
 c.owner=peer;c.sequence=seq;BbscWorldIncoming m{peer,c,std::vector<u8>(12)};
 memcpy(m.payload.data(),&point,4);const s64 stamp=wall++;memcpy(m.payload.data()+4,&stamp,8);return m;
}
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(image_base);
 auto* jump=(u8*)(image_base+0x013CDF30);jump[0]=0x48;jump[1]=0xb8;
 void* target=(void*)&NativeLoad;memcpy(jump+2,&target,8);jump[10]=0xff;jump[11]=0xe0;
 jump=(u8*)(image_base+DeathReloadRequestOffset);jump[0]=0x48;jump[1]=0xb8;
 target=(void*)&NativeReload;memcpy(jump+2,&target,8);jump[10]=0xff;jump[11]=0xe0;
 jump=(u8*)(image_base+0x01332BC0);jump[0]=0x48;jump[1]=0xb8;
 target=(void*)&NativeDeathSelect;memcpy(jump+2,&target,8);jump[10]=0xff;jump[11]=0xe0;
 // ORIGINAL_POINT_LOAD
 reset();member(22);member(33);
 auto a=proposal(22,3202950,1);BbscWorldReceiveLampCheckpoint(a);
 assert(bbsc_checkpoint.point==3202950&&bbsc_checkpoint.revision==1);
 const auto first=sent.back();
 auto b=proposal(33,2702951,1);BbscWorldReceiveLampCheckpoint(b);
 assert(bbsc_checkpoint.point==2702951&&bbsc_checkpoint.revision==2);
 const auto second=sent.back();
 BbscWorldReceiveLampCheckpoint(a); // lost ack / delayed resend cannot move latest backwards
 assert(bbsc_checkpoint.point==2702951&&bbsc_checkpoint.revision==2);
 const auto ack=sent.back();assert(ack.control.owner==22&&ack.control.epoch==1);
 auto bad=a;bad.sender=77;bad.control.sequence=9;BbscWorldReceiveLampCheckpoint(bad);
 bad=a;bad.control.scope.world.room++;BbscWorldReceiveLampCheckpoint(bad);
 bad=a;bad.payload.clear();BbscWorldReceiveLampCheckpoint(bad);
 assert(bbsc_checkpoint.revision==2);
 auto bytes=World::Encode(second.control,second.payload);assert(World::DecodeControl(bytes)->kind==World::ControlKind::LampCheckpoint);
 // Two guests, late arrival, stale canonical packets and retry acknowledgement.
 for(u32 peer:{22u,33u}){
  reset();local(peer,0x20000000);bbsc_checkpoint_offer={a.control.scope,3202950,22,1,0};
  BbscWorldReceiveLampCheckpoint(second);assert(bbsc_checkpoint.point==2702951);
  BbscWorldReceiveLampCheckpoint(first);assert(bbsc_checkpoint.point==2702951);
  if(peer==22)assert(!bbsc_checkpoint_offer.point); // ack must not restore old checkpoint
  s32 p=0;bool here=true;assert(!ReadBbscSharedLampCheckpoint(p,here));
  lookups=0;assert(!ResolveLastLampTransform()&&lookups==0); // resident neighbour rejected before lookup
  WriteValue<s32>(GetGlobalState(),0x1528,3202950);
  assert(ResolveLastLampTransform()->position[0]==3202950); // foreign shared lamp cannot hide personal local lamp
  const int personal_reload=fallbacks,foreign_load=loads;
  RequestBbscDeathReload("no living partner at the death step");
  assert(!bbsc_checkpoint_reload.point&&fallbacks==personal_reload+1&&loads==foreign_load);
  assert(!bbsc_world_requested_scope&&!bbsc_world_travel_inflight);
  // Same-map death still uses the shared lamp and original point-load entry.
  current=0x1b000000;bbsc_world_presence_local.map=current;
  const int reload_before=fallbacks;RequestBbscDeathReload("no living partner at the death step");
  assert(bbsc_checkpoint_reload.point==2702951&&fallbacks==reload_before);
  const int before=loads;snapshot=false;now+=1000;TickBbscSharedLampCheckpoint();assert(loads==before);
  snapshot=true;finale_committed=true;TickBbscSharedLampCheckpoint();assert(loads==before);
  finale_committed=false;TickBbscSharedLampCheckpoint();assert(loads==before+1&&loaded_point==2702951);
  // NATIVE_DESTINATION_CHECK
  TickBbscSharedLampCheckpoint();assert(loads==before+1); // single stage request
  assert(bbsc_world_requested_scope->map==0x1b000000&&bbsc_world_travel_inflight);
  assert(ResolveLastLampTransform());
 }
 // Local host and either guest can select a newly lit lamp, including relighting
 // a lamp whose native personal checkpoint already has that point.
 for(u32 peer:{11u,22u,33u}){
  reset();local(peer,0x20000000);QueueBbscSharedLampCheckpoint(3202950);
  assert(sent.back().control.owner==peer&&sent.back().payload.size()==12);
  if(peer==11)assert(bbsc_checkpoint.point==3202950);
  else {assert(bbsc_checkpoint_offer.point==3202950);now+=1000;TickBbscSharedLampCheckpoint();assert(sent.size()==2);}
 }
 // A guest's own new ignition is authoritative before its host ack arrives.
 reset();local(22,0x18010000);wall=19000;
 auto shared=proposal(33,2412951,9);shared.sender=11;shared.control.epoch=1;
 BbscWorldReceiveLampCheckpoint(shared);wall=19500;
 QueueBbscSharedLampCheckpoint(2412953);WriteValue<s32>(GetGlobalState(),0x1528,2412953);
 s32 pending=0;bool pending_here=false;assert(!ReadBbscSharedLampCheckpoint(pending,pending_here));
 assert(ResolveLastLampTransform()->position[0]==2412953);
 // Shared Central Yharnam followed by personal Oedon Tomb (same m24_01).
 for(u32 peer:{11u,22u,33u}){
  reset();local(peer,0x18010000);wall=20000;hp=594;
  auto ignition=proposal(22,2412951,10);ignition.sender=11;ignition.control.epoch=1;
  if(peer==11){ignition.sender=22;ignition.control.epoch=0;member(22);}
  BbscWorldReceiveLampCheckpoint(ignition);
  WriteValue<s32>(GetGlobalState(),0x1528,2412953);
  wall=21000;NoteBbscNativeLampSelection();
  s32 p=0;bool here=false;assert(!ReadBbscSharedLampCheckpoint(p,here));
  assert(ResolveLastLampTransform()->position[0]==2412953);
  const int reloaded=fallbacks;RequestBbscDeathReload("wipe");
  assert(fallbacks==reloaded+1&&!bbsc_checkpoint_reload.point);
  BbscWorldReceiveLampCheckpoint(ignition);assert(!ReadBbscSharedLampCheckpoint(p,here));
  wall=22000;auto newer=proposal(33,2412951,11);newer.sender=11;newer.control.epoch=2;
  if(peer==11){newer.sender=33;newer.control.epoch=0;member(33);}
  BbscWorldReceiveLampCheckpoint(newer);assert(ReadBbscSharedLampCheckpoint(p,here)&&p==2412951&&here);
  hp=0;wall=23000;NoteBbscNativeLampSelection();
  assert(ReadBbscSharedLampCheckpoint(p,here));hp=594;
  // First delivery after a newer journey must also retain the original date.
  reset();local(peer,0x18010000);wall=25000;NoteBbscNativeLampSelection();
  if(peer==11)member(22);
  BbscWorldReceiveLampCheckpoint(ignition);assert(!ReadBbscSharedLampCheckpoint(p,here));
 }
 reset();member(22);member(33);wall=30000;auto older=proposal(22,3202950,21);
 wall=31000;auto newer=proposal(33,2702951,22);
 BbscWorldReceiveLampCheckpoint(newer);BbscWorldReceiveLampCheckpoint(older);
 assert(bbsc_checkpoint.point==2702951&&bbsc_checkpoint.revision==1);
 // A different dungeon generation cannot use a resident m29 lamp point.
 reset();auto& altar=bbsc_world_altars[2];altar.entry.occupied=true;altar.entry.ritual=7;
 altar.mount.key={55,66,88,0};altar.mount.revision=7;
 local(11,0x1d000000);bbsc_world_presence_local.dungeon=altar.mount.key;bbsc_world_presence_local.ritual=7;
 QueueBbscSharedLampCheckpoint(2902952);assert(bbsc_checkpoint.point==2902952);
 assert(ResolveLastLampTransform());bbsc_world_presence_local.ritual=8;
 assert(!ResolveLastLampTransform());
 assert(!RequestBbscSharedLampReload());
 const int foreign_cup_loads=loads,foreign_cup_notices=notifications;
 assert(!BeginBbscSharedLampLoad(bbsc_checkpoint.scope,2902952));
 assert(loads==foreign_cup_loads&&notifications==foreign_cup_notices&&!bbsc_world_requested_scope);
 bbsc_world_presence_local.ritual=7;
 assert(RequestBbscSharedLampReload());prepared=false;const int n=loads;TickBbscSharedLampCheckpoint();assert(loads==n);
 prepared=true;TickBbscSharedLampCheckpoint();assert(loads==n+1&&bbsc_world_altar_visiting==2);
 assert(bbsc_world_requested_mount->key==altar.mount.key&&bbsc_world_requested_scope->ritual==7);
 // Removing the selected ritual invalidates it rather than resolving another cup.
 altar.entry.ritual=9;s32 p=0;bool here=false;assert(!ReadBbscSharedLampCheckpoint(p,here));
 // Scripted abduction keeps its prison destination even with a shared lamp.
 reset();QueueBbscSharedLampCheckpoint(3202950);const int old_fallback=fallbacks;
 RequestBbscDeathReload("native Snatcher abduction");assert(fallbacks==old_fallback+1&&!bbsc_checkpoint_reload.point);
 // No infinite hold when a provider disappears; fallback remains one local death reload.
 reset();QueueBbscSharedLampCheckpoint(3202950);assert(RequestBbscSharedLampReload());
 snapshot=false;const int old_loads=loads,old_reload=fallbacks;now+=30001;
 TickBbscSharedLampCheckpoint();assert(fallbacks==old_reload+1&&loads==old_loads&&!bbsc_checkpoint_reload.point);
 snapshot=true;
 // Captured P1 failure: native Central Yharnam, newer P2 ignition Old Yharnam.
 // Both host and guests retain their own map; date priority still applies INSIDE it.
 for(u32 peer:{11u,22u,33u}){
  reset();local(peer,0x18010000);wall=40000;NoteBbscNativeLampSelection();
  WriteValue<s32>(GetGlobalState(),0x1528,2412951);
  wall=41000;auto foreign=proposal(22,2302950,31);foreign.sender=11;foreign.control.epoch=1;
  if(peer==11){member(22);foreign.sender=22;foreign.control.epoch=0;}
  BbscWorldReceiveLampCheckpoint(foreign);assert(bbsc_checkpoint.point==2302950);
  assert(ResolveLastLampTransform()->position[0]==2412951);
  const int old=loads,old_fallback=fallbacks,notice=notifications;
  assert(!RequestBbscSharedLampReload());
  assert(!BeginBbscSharedLampLoad(bbsc_checkpoint.scope,2302950));
  assert(loads==old&&notifications==notice&&!bbsc_world_requested_scope&&!bbsc_world_requested_mount);
  RequestBbscDeathReload("no living partner at the death step");
  assert(fallbacks==old_fallback+1&&loads==old&&!bbsc_checkpoint_reload.point);
  assert(ReadValue<s32>(GetGlobalState(),0x1528)==2412951);
 }
 // Revalidate a frozen target before any preparation if the local scope changes.
 reset();QueueBbscSharedLampCheckpoint(3202950);assert(RequestBbscSharedLampReload());
 local(11,0x1b000000);WriteValue<s32>(GetGlobalState(),0x1528,2702951);
 const int frozen_loads=loads,frozen_fallback=fallbacks;
 TickBbscSharedLampCheckpoint();assert(!bbsc_checkpoint_reload.point&&loads==frozen_loads&&fallbacks==frozen_fallback+1);
 assert(!bbsc_world_requested_scope&&!bbsc_world_requested_mount&&!bbsc_world_travel_inflight);
 // Personal fallback is also fenced against adjacent maps even before any shared record.
 reset();local(22,0x20000000);WriteValue<s32>(GetGlobalState(),0x1528,2702951);
 lookups=0;assert(!ResolveLastLampTransform()&&lookups==0);
 WriteValue<s32>(GetGlobalState(),0x1528,3202950);assert(ResolveLastLampTransform());
 // A session change clears canonical state, retries and pending death loads.
 BindBbscSharedLamp({11,100});assert(!bbsc_checkpoint.point&&!bbsc_checkpoint_offer.point&&!bbsc_checkpoint_reload.point);
 // Each participant loads locally from the same accepted checkpoint. The
 // host has not loaded yet when either guest starts.
 for(u32 client:{22u,33u,11u}){
  reset();local(client,0x18020000);
  bbsc_checkpoint={World::ScopeOf(bbsc_world_presence_local),2422952,11,1,1};
  const int before=loads;
  RequestBbscDeathReload("no living partner");
  TickBbscSharedLampCheckpoint();TickBbscSharedLampCheckpoint();
  assert(loads==before+1&&loaded_point==2422952&&role==(client==11?3:6));
 }
 // A guest without negotiated travel uses the room point already selected
 // by the native death flow, even without a shared snapshot or a host load.
 reset();local(22,0x18020000);active=false;snapshot=false;
 WriteValue<s32>(GetGlobalState(),0x1528,2102950);assert(!RequestBbscSharedLampReload());
 WriteValue<s32>(GetGlobalState(),0x1528,2422952);
 invader=true;assert(!RequestBbscSharedLampReload());invader=false;
 const int before=loads;RequestBbscDeathReload("no living partner");
 assert(loads==before+1&&loaded_point==2422952&&role==6);

 // Rom wipe: foreign shared and native points cannot send either role to
 // Cathedral. Only the lit, resolved Byrgenwerth lamp is eligible.
 active=true;snapshot=true;hp=0;
 for(u32 peer:{11u,22u}){
  reset();local(peer,0x20000000);flags={12407800,13207800,13207840};
  WriteValue<s32>(GetGlobalState(),0x1528,2402950);
  WriteValue<u32>(GetGlobalState(),0xC,0x18000000);
  bbsc_checkpoint={{world,0x18000000,{},0},2402950,11,1,1};
  const int chosen=local_selections,reloaded=fallbacks;
  RequestBbscDeathReload("all hunters finished boss death");
  assert(local_selections==chosen+1&&fallbacks==reloaded+1&&!bbsc_checkpoint_reload.point);
  assert(ReadValue<u32>(GetGlobalState(),0xC)==0x20000000);
  assert(ReadValue<s32>(GetGlobalState(),0x1528)==3202950);
  assert(ReadValue<s32>(GetGlobalState(),0x152c)==101163);
  assert(bbsc_checkpoint.point==2402950&&!bbsc_world_travel_inflight&&sent.empty());
 }
 // Multiple suitable lamps choose by native position, with an ID tie break.
 reset();flags={13207800,13207820};body=BbscTransform{};body->position[0]=3202950.5f;
 WriteValue<s32>(GetGlobalState(),0x1528,2402950);
 SelectBbscLocalDeathLamp();assert(ReadValue<s32>(GetGlobalState(),0x1528)==3202950);
 body->position[0]=3202951;WriteValue<s32>(GetGlobalState(),0x1528,2402950);
 SelectBbscLocalDeathLamp();assert(ReadValue<s32>(GetGlobalState(),0x1528)==3202951);
 // A suitable explicit native point remains authoritative.
 body->position[0]=3202950;const int explicit_point=local_selections;
 SelectBbscLocalDeathLamp();assert(local_selections==explicit_point);
 // With no body transform the lowest eligible local ID still wins.
 WriteValue<s32>(GetGlobalState(),0x1528,2402950);body.reset();
 SelectBbscLocalDeathLamp();
 assert(local_selections==explicit_point+1&&ReadValue<s32>(GetGlobalState(),0x1528)==3202950);
 // Unavailable and unlit lamps, loading, forced return, read-only checkpoint,
 // invasion and offline keep the original destination.
 WriteValue<s32>(GetGlobalState(),0x1528,2402950);const int chosen=local_selections;
 flags={13207800};unavailable=3202950;
 SelectBbscLocalDeathLamp();assert(local_selections==chosen);unavailable=-1;
 WriteValue<u8>(GetGlobalState(),8,1);SelectBbscLocalDeathLamp();
 WriteValue<u8>(GetGlobalState(),8,0);WriteValue<u8>(GetGlobalState(),0x1520,1);
 SelectBbscLocalDeathLamp();WriteValue<u8>(GetGlobalState(),0x1520,0);
 writable=false;SelectBbscLocalDeathLamp();writable=true;
 invaded=true;SelectBbscLocalDeathLamp();invaded=false;
 role=0;SelectBbscLocalDeathLamp();role=3;
 RequestBbscDeathReload("native Snatcher abduction");
 assert(local_selections==chosen);

 // The same loaded m29 map can hold the Hall and multiple layers.
 // Native area 290110 belongs to layer 2, even with layer 1's lamp nearer.
 reset();local(22,0x1d000000);flags={12907800,12907820,12907840,12907860,12907880};
 body=BbscTransform{};body->position[0]=2902951;
 WriteValue<s32>(GetLocalPlayerCharacter(),0x278,-290110);
 WriteValue<s32>(GetGlobalState(),0x1528,2902951);
 assert(!ResolveLastLampTransform());
 SelectBbscLocalDeathLamp();assert(ReadValue<s32>(GetGlobalState(),0x1528)==2902953);
 flags={12907820,12907840,12907880};WriteValue<s32>(GetGlobalState(),0x1528,2902951);
 const int cup=local_selections;SelectBbscLocalDeathLamp();
 assert(local_selections==cup); // second lamp requires the layer's boss flag
 flags.push_back(12901801);ready=false;SelectBbscLocalDeathLamp();
 assert(local_selections==cup);ready=true;
 SelectBbscLocalDeathLamp();assert(ReadValue<s32>(GetGlobalState(),0x1528)==2902954);
 WriteValue<s32>(GetLocalPlayerCharacter(),0x278,0);
 WriteValue<s32>(GetGlobalState(),0x1528,2402950);
 SelectBbscLocalDeathLamp();assert(local_selections==cup+1);
}
'''
if os.environ.get('BBSC_TEST_EBOOT'):
    with open(os.environ['BBSC_TEST_EBOOT'], 'rb') as f:
        f.seek(0x13cdf30+0x4000)
        native = f.read(0xeb)
        f.seek(0x1332bc0+0x4000)
        native_death = f.read(0x129)
    assert native[:6] == bytes.fromhex('554889e54157') and native[-1] == 0xc3
    def rip(off):
        return 0x13cdf30+off+7+struct.unpack_from('<i',native,off+3)[0]
    assert rip(0x74) == rip(0xc4) == 0x5556678
    original = 'const u8 original[]={' + ','.join(map(str,native)) + '};\n'
    original += 'memcpy((void*)(image_base+0x13cdf30),original,sizeof(original));\n'
    original += f'WriteValue<u64>(image_base,{rip(0xf)},(u64)&cookie);WriteValue<u64>(image_base,{rip(0x74)},GetGlobalState());\n'
    original += 'jump=(u8*)(image_base+0x1f26b40);jump[0]=0x48;jump[1]=0xb8;target=(void*)&NativeDescriptor;memcpy(jump+2,&target,8);jump[10]=0xff;jump[11]=0xe0;\n'
    assert native_death[:8] == bytes.fromhex('554889e541574156') and native_death[-1] == 0xc3
    original += 'const u8 native_death[]={' + ','.join(map(str,native_death)) + '};\n'
    original += 'memcpy((void*)(image_base+0x1332bc0),native_death,sizeof(native_death));\n'
    original += 'jump=(u8*)(image_base+0x13ca100);jump[0]=0x48;jump[1]=0xb8;target=(void*)&NativeDeathDestination;memcpy(jump+2,&target,8);jump[10]=0xff;jump[11]=0xe0;\n'
    code = code.replace('// ORIGINAL_POINT_LOAD', original)
    code = code.replace('// NATIVE_DESTINATION_CHECK', 'assert(ReadValue<u32>(GetGlobalState(),0xC)==0x1b000000 && ReadValue<s32>(GetGlobalState(),0x153c)==2702951);')
compiler = os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
with tempfile.TemporaryDirectory(prefix='bbsc-shared-lamp-') as tmp:
    cpp, exe = Path(tmp)/'checkpoint.cpp', Path(tmp)/'checkpoint.exe'
    cpp.write_text(code, encoding='utf-8')
    subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
    env = dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    result = subprocess.run([str(exe)],env=env)
    if any(os.environ.get(k) for k in ('BBSC_TEST_SHARED_CHECKPOINT_OLD','BBSC_TEST_NEIGHBOUR_OLD','BBSC_TEST_LAMP_PRIORITY_OLD','BBSC_TEST_DEATH_MAP_OLD')):
        assert result.returncode != 0,'Missing replay fence passed regression'
        print('PASS negative control: missing checkpoint/neighbor fence FAILS regression')
    else:
        result.check_returncode()
        print('PASS production death lamps: shared checkpoint ordering and fences, Rom wipe for both roles, nearest local lamp and exact chalice layer')
