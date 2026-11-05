"""Exercise actual follow broadcast, receiver and tick with controlled game state."""
from pathlib import Path
import os, subprocess, tempfile

ROOT = Path(__file__).resolve().parents[1]
s = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(name):
    a=s.index(name); b=s.index('{',a); d=1; e=b+1
    while d:
        d+=(s[e]=='{')-(s[e]=='}'); e+=1
    return s[a:e]+'\n'
def region(a,b):
    return s[s.index(a):s.index(b,s.index(a))]

code=r'''
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>
#include <mutex>
#include <optional>
#include <string>
#include "core/bbsc_follow.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u32=uint32_t;using s32=int32_t;using u64=uint64_t;using s64=int64_t;
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
#define PS4_SYSV_ABI
#define BbscL(a,b) a
s64 clock_ms=10000; s64 SteadyNowMs(){return clock_ms;}
u64 image_base=1;std::atomic<u32> bbsc_load_generation{1};
std::atomic<u64> bbsc_world_load_pending{0};std::atomic<bool> bbsc_reload_finish_pending{false};
s32 state=3,hp=100;bool loading=false,own=true,quitting=false,flags=true;
u32 map=0x18000000;int requests=0,sends=0;bool bbsc_join_teleport_done=true;
bool BbscWarpTogetherEnabled(){return true;}bool BbscQuitInProgress(){return quitting;}
bool BbscDreamFinaleHolding(){return false;}u64 GetGlobalState(){return 0x10000;}
bool ReadablePointer(u64,size_t){return true;}
template<class T>T ReadValue(u64,size_t off){
 if(off==8)return loading;if(off==0x1592)return own;return 0;
}
template<class T>void WriteValue(u64,size_t,T){}
s32 GetSessionState(){return state;}int GetLocalPlayerType(){return 1;}
u64 GetLocalPlayerCharacter(){return 0x20000;}int GetCharacterHp(u64){return hp;}
u32 GetCurrentPackedMap(){return map;}bool IsUsablePackedMap(u32 m){return (m>>24)>=21&&(m>>24)<=36;}
struct Transform{std::array<float,4> position{1,2,3,1},rotation{0,4,0,0};};
Transform transform;std::optional<Transform> ReadCharacterTransform(u64){return transform;}
Chalice::Key ReadBbscChaliceKey(){return {};}
void SendBbscChaliceMount(){}void ArmBbscRejoinLines(bool,u32,s64){}
constexpr s64 BbscHostRejoinLinesMs=1000,BbscGuestRejoinGraceMs=1000;
constexpr s64 BbscFollowBroadcastMs=500,BbscFollowStaleMs=15000,BbscFollowSettleMs=2000;
constexpr s64 BbscWorldFlagsWaitMs=4000;constexpr u32 BbscDreamStateMap=0x15000000;
bool IsEbootCodeAddress(u64){return false;}
bool BbscChaliceArrivalReady(u32){return true;}bool BbscChaliceNeedsLoad(u32){return false;}
bool BbscChaliceLoadReady(u32){return true;}bool BbscMapResident(u32){return true;}
std::string BbscResidentMapsText(){return "resident";}
bool BbscLatestChaliceMount(u32,Chalice::Mount&){return false;}
bool BbscOwnOpeningDone(){return true;}bool BbscDreamEnabled(){return false;}
bool BbscDreamOwnEnabled(){return false;}bool BbscHostDreamStateReady(){return true;}
bool BbscHostWorldFlagsReady(u32){return flags;}
void ApplyBbscHostWorldFlags(u32,const char*){}void ApplyBbscHostTime(const char*){}
void ApplyBbscGuestLootView(u32,const char*){}void ApplyBbscHostDreamState(const char*){}
void RestoreBbscOwnDreamState(const char*){}void LogBbscHostWorldFlagsDiff(u32,const char*){}
bool PrepareBbscChaliceLoad(u32){return true;}
void BbscAnnounce(const char16_t*,const char*){}
struct SummonPlacementDescriptor{u32 packed_region;float x,y,z,heading;};
bool RequestBbscSessionWarp(u64,const SummonPlacementDescriptor&,const char*){++requests;return true;}
Follow::Arrival sent_arrival;u32 sent_map;
namespace Libraries::Np::NpSignaling::Helpers {
u32 SendBbscFollowToPeers(u32 m,float,float,float,float,u32,s32,const Chalice::Key&,const Follow::Arrival& a){
 ++sends;sent_arrival=a;sent_map=m;return 1;
}
}
'''
code+=region('struct BbscFollowMessage {','bool BbscWarpTogetherEnabled()')
code+=function('void TickBbscFollowBroadcast()')
code+=region('constexpr s64 BbscFollowArriveTimeoutMs','// True when that map is loaded')
code+=region('struct BbscFollowSpot {','// Guest side:')
code+=region('constexpr s64 BbscFollowAfterLoadMs','void TickBbscFollowHost()')
code+=function('void TickBbscFollowHost()')
code+=function('void OnBbscHostFollowPacket(')
code+=r'''
#pragma pack(push,1)
struct Packet{u8 magic[4]={'S','H','A','D'};u8 type=Protocol::Follow,kind=0;u32 packed_map=0x18000000;
 float x=0,y=0,z=0,heading=0;u32 sequence=1;s32 lamp_point=-1;};
#pragma pack(pop)
static_assert(sizeof(Packet)==34);
void receive(u32 seq,const Follow::Arrival& a,u32 where){
 OnBbscHostFollowPacket(where,1,2,3,4,seq,-1,{},a);
}
int main(){
 // Repeat immutable arrival through walking; send the new completion immediately.
 TickBbscFollowBroadcast();assert(sends==1&&sent_arrival.generation==1&&sent_arrival.map==map);
 transform.position[0]=90;clock_ms+=500;TickBbscFollowBroadcast();assert(sent_arrival.x==1);
 map=0x17000000;clock_ms+=500;TickBbscFollowBroadcast();assert(sent_arrival.map==0x18000000&&sent_map==map);
 loading=true;++bbsc_load_generation;clock_ms+=1;TickBbscFollowBroadcast();assert(sends==3);
 loading=false;clock_ms+=1;TickBbscFollowBroadcast();assert(sends==4&&sent_arrival.generation==2&&sent_arrival.map==map);
 bbsc_world_load_pending=1;clock_ms+=500;TickBbscFollowBroadcast();assert(sends==4);
 bbsc_world_load_pending=0;
 Follow::Arrival a{2,map,90,2,3,4};Packet p;p.packed_map=map;
 for(u32 m:{0x17000000u,0x1d000000u}){
  p.packed_map=m;Chalice::Key key{42,43,140,1},out;Follow::Arrival got;Packet decoded;
  auto bytes=Follow::Encode(p,key,a);
  assert(Follow::Decode(bytes.data(),bytes.size(),decoded,out,got));
  assert(decoded.kind==1&&got.generation==2&&got.x==90);
  assert(out.channel==(Chalice::IsMap(m)?42:0));
  for(size_t n=0;n<bytes.size();++n)assert(!Follow::Decode(bytes.data(),n,decoded,out,got));
  bytes.push_back(0);assert(!Follow::Decode(bytes.data(),bytes.size(),decoded,out,got));
 }
 p.packed_map=map;Packet decoded;Chalice::Key out;Follow::Arrival got;
 assert(Follow::Decode(&p,sizeof(p),decoded,out,got)&&got.generation==0);
 assert(Follow::Decode(&p,30,decoded,out,got)&&decoded.lamp_point==-1);
 p.kind=7;assert(!Follow::Decode(&p,sizeof(p),decoded,out,got));p.kind=0;
 a.x=std::numeric_limits<float>::infinity();auto bad=Follow::Encode(p,{},a);
 assert(!Follow::Decode(bad.data(),bad.size(),decoded,out,got));a.x=90;
 // No receive silence: explicit load overrides resident-map walking suppression.
 state=6;own=false;map=0x18000000;loading=false;clock_ms=20000;bbsc_load_generation=3;
 Follow::Arrival old{1,map,1,2,3,4};receive(1,old,map);TickBbscFollowHost();assert(requests==0);
 clock_ms+=500;receive(2,a,a.map);TickBbscFollowHost();assert(requests==0);
 clock_ms=24999;receive(3,a,a.map);TickBbscFollowHost();assert(requests==0);
 clock_ms=25250;receive(4,a,a.map);TickBbscFollowHost();assert(requests==1);
 auto arrival_time=bbsc_follow_latest.arrival_ms;clock_ms+=2000;receive(5,a,a.map);
 assert(bbsc_follow_latest.arrival_ms==arrival_time&&bbsc_follow_latest.arrival_x==90);
 receive(4,old,map);assert(bbsc_follow_latest.sequence==5);
 // Consume completed load; guest walking away must not start another follow.
 map=a.map;clock_ms+=250;TickBbscFollowHost();
 clock_ms+=250;TickBbscFollowHost();
 map=0x18000000;clock_ms+=2000;receive(6,a,a.map);TickBbscFollowHost();assert(requests==1);
 // Safe explicit arrival follows on the first check, subject to life and world state.
 a={3,0x1a000000,1,2,3,4};clock_ms+=500;receive(7,a,a.map);hp=0;TickBbscFollowHost();assert(requests==1);
 hp=100;flags=false;clock_ms+=250;TickBbscFollowHost();assert(requests==1);
 flags=true;clock_ms+=250;TickBbscFollowHost();assert(requests==2);
 // Entire loading screen can pass between ticks: generation still blocks repeat load.
 ++bbsc_load_generation;map=a.map;clock_ms+=500;TickBbscFollowHost();
 clock_ms+=2000;TickBbscFollowHost();
 clock_ms+=250;TickBbscFollowHost();
 a={4,0x21000000,1,2,3,4};clock_ms+=250;receive(8,a,a.map);TickBbscFollowHost();assert(requests==2);
 clock_ms+=3000;receive(9,a,a.map);TickBbscFollowHost();assert(requests==3);
 // Legacy hosts retain their conservative border debounce.
 map=a.map;clock_ms+=2250;TickBbscFollowHost();clock_ms+=250;TickBbscFollowHost();
 clock_ms+=2000;receive(10,{},0x22000000);TickBbscFollowHost();assert(requests==3);
 clock_ms+=2250;receive(11,{},0x22000000);TickBbscFollowHost();assert(requests==3);
 clock_ms+=250;receive(12,{},0x22000000);TickBbscFollowHost();assert(requests==4);
 map=0x22000000;clock_ms+=2250;TickBbscFollowHost();clock_ms+=250;TickBbscFollowHost();
 a={5,0x23000000,1,2,3,4};clock_ms+=250;receive(13,a,a.map);
 bbsc_reload_finish_pending=true;TickBbscFollowHost();assert(requests==4);
 bbsc_reload_finish_pending=false;clock_ms+=4999;receive(14,a,a.map);TickBbscFollowHost();assert(requests==4);
 clock_ms+=251;receive(15,a,a.map);TickBbscFollowHost();assert(requests==5);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-follow-') as tmp:
    cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text(code,encoding='utf-8')
    subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-I'+str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('PASS: production follow broadcast/receive/tick; explicit loads vs walking; wire formats; safe fast follow; guest load-generation guard; flags/death')
