"""Execute the real game-tick/receive bridge against controlled native observations."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
    start=SOURCE.index(signature+' {')
    pos=SOURCE.index('{',start)+1
    depth=1
    while depth:
        depth+=(SOURCE[pos]=='{')-(SOURCE[pos]=='}')
        pos+=1
    return SOURCE[start:pos]+'\n'

PREFIX=r'''
#include <atomic>
#include <cassert>
#include <mutex>
#include <vector>
#include "core/bbsc_world_presence.h"
using namespace Core::Bloodborne;
namespace Finale = Core::Bbsc::DreamFinale;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
s64 now=10000;u32 key=11,self=11,map=0x18000000;
u64 room=99,image_base=0x800000000ULL;
constexpr u64 MatchingStatePointerOffset=0x05540290;
s32 state=3,hp=594,type=0;bool loading=false,quitting=false,title=false,positioned=true;
s64 SteadyNowMs(){return now;}
s32 GetSessionState(){return state;}
u64 GetLocalPlayerCharacter(){return positioned?0x20000:0;}
u64 GetGlobalState(){return 0x10000;}
struct Identity{u32 room;};
Identity ReadBbscRegisterIdentity(u64){return {0};} // actual local endpoint is zero
namespace BbscMod{u32 RegisterSessionKey(){return key;}u32 RegisterOwnId(){return self;}}
bool BbscQuitInProgress(){return quitting;}bool BbscReturningToTitle(){return title;}
bool IsInvaderType(s32 t){return t==2;}s32 GetLocalPlayerType(){return type;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64 p,size_t offset){
 if(p==image_base+MatchingStatePointerOffset)return static_cast<T>(0x30000);
 if(p==0x30000 && offset==0x18)return static_cast<T>(0x40000);
 if(p==0x40000 && offset==0x400)return static_cast<T>(room);
 return static_cast<T>(loading);
}
bool BbscCurtainActive(){return false;}
enum class BbscWork { Finale };
void QueueBbscWork(BbscWork){}
bool bbsc_finale_hooks_ready=false;
Finale::Signal BbscFinalePresence(World::WorldId){return {};}
bool BbscNativeFinaleWantsPresence(){return false;}
std::atomic<u32> bbsc_load_generation{1};
std::atomic<u64> bbsc_world_player_revision{0};
std::atomic<u64> bbsc_world_load_pending{0};std::atomic<bool> bbsc_reload_finish_pending{false};
struct Transform{std::array<float,4> position{1,2,3,1};};
Transform transform;
std::optional<Transform> ReadCharacterTransform(u64){return positioned?std::optional{transform}:std::nullopt;}
u32 GetCurrentPackedMap(){return map;}
Chalice::Key dungeon;
Chalice::Key ReadBbscChaliceKey(){return dungeon;}
u32 BbscIndependentCapabilities(){return World::PresenceCapability;}
Chalice::Key BbscIndependentDungeonKey(const Chalice::Key& key){return key;}
u64 BbscIndependentRitual(const Chalice::Key&){return 0;}
void BbscWorldCoordinate(){}
s32 GetCharacterHp(u64){return hp;}
std::vector<World::Presence> sent;
namespace Libraries::Np::NpSignaling::Helpers {
u32 SendBbscWorldFlagsToPeers(const void* p,u32 size){
 auto decoded=World::Decode({static_cast<const u8*>(p),size}); assert(decoded);
 sent.push_back(*decoded);return 1;
}}
std::mutex bbsc_world_presence_mutex;
World::PresenceBook bbsc_world_presence_book;
World::Presence bbsc_world_presence_local;
World::PlaceTracker bbsc_world_place;
'''
MAIN=r'''
int main(){
 TickBbscWorldPresence();assert(sent.size()==1);
 assert(sent.back().world==(World::WorldId{11,99}));
 assert(sent.back().phase==World::Phase::Playing&&sent.back().alive==1);
 assert(sent.back().capabilities==World::PresenceCapability);
 assert(!(sent.back().capabilities&World::IndependentTravelCapability));
 const auto initial_visit=sent.back().visit;
 ++bbsc_load_generation;map=0x18010000;now++;TickBbscWorldPresence();assert(sent.back().map==map&&sent.back().visit>initial_visit);
 ++bbsc_load_generation;map=0x18000000;now++;TickBbscWorldPresence();
 const auto baseline=sent.size();
 now+=10;TickBbscWorldPresence();assert(sent.size()==baseline); // steady frame: no resend/scan
 now+=1000;TickBbscWorldPresence();assert(sent.size()==baseline+1);
 hp=0;now++;TickBbscWorldPresence();assert(sent.back().alive==0);
 const auto before=sent.size();
 loading=true;now++;TickBbscWorldPresence();assert(sent.size()==before+1);
 assert(sent.back().phase==World::Phase::Loading&&sent.back().map==map);
 positioned=false;now+=1000;TickBbscWorldPresence();assert(sent.back().phase==World::Phase::Loading);
 loading=false;positioned=true;hp=594;now++;TickBbscWorldPresence();
 assert(sent.back().phase==World::Phase::Playing&&sent.back().visit>initial_visit);
 auto peer=sent.back();peer.sequence=100;
 OnBbscWorldPresencePacket(22,11,&peer,sizeof(peer));
 assert(bbsc_world_presence_book.Find(22,now));
 auto bad=peer;bad.world.room++;
 OnBbscWorldPresencePacket(23,11,&bad,sizeof(bad));assert(!bbsc_world_presence_book.Find(23,now));
 OnBbscWorldPresencePacket(23,12,&peer,sizeof(peer));assert(!bbsc_world_presence_book.Find(23,now));
 OnBbscWorldPresencePacket(23,11,&peer,sizeof(peer)-1);assert(!bbsc_world_presence_book.Find(23,now));
 auto loading_peer=peer;loading_peer.phase=World::Phase::Loading;loading_peer.sequence++;
 OnBbscWorldPresencePacket(22,11,&loading_peer,sizeof(loading_peer));
 OnBbscWorldPresencePacket(22,11,&peer,sizeof(peer));
 assert(bbsc_world_presence_book.Find(22,now)->presence.phase==World::Phase::Loading);
 // Read-flapping at a border cannot advertise a player in two maps.
 map=0x18010000;now++;TickBbscWorldPresence();
 assert(bbsc_world_presence_local.map==0x18000000);
 now+=1500;TickBbscWorldPresence();assert(sent.back().map==map);
 const auto visit=sent.back().visit;
 key=0;state=0;now++;TickBbscWorldPresence();assert(bbsc_world_presence_book.Members().empty());
 key=11;state=3;now++;TickBbscWorldPresence();assert(sent.back().visit>visit);
 room=100;now++;TickBbscWorldPresence();assert(sent.back().world.room==100);
 OnBbscWorldPresencePacket(22,11,&peer,sizeof(peer));assert(!bbsc_world_presence_book.Find(22,now));
 // Local endpoint address/port are zero in real native sessions. Room comes
 // from Matching2, including its upper32 bits; never from the self MemberId.
 room=0x0f05780968768890ULL;now++;TickBbscWorldPresence();
 assert(sent.back().world.room==room);
 auto wrong=sent.back();wrong.world.room^=u64{1}<<40;wrong.sequence+=100;
 OnBbscWorldPresencePacket(22,11,&wrong,sizeof(wrong));assert(!bbsc_world_presence_book.Find(22,now));
 room=0;loading=true;now++;TickBbscWorldPresence();
 assert(sent.back().world.room==0x0f05780968768890ULL); // transient missing controller
 room=0x0f05780968768890ULL;loading=false;
 // A same-map group wipe has three independent loads in one room. Arrival
 // order is arbitrary, and matching map/room does not admit a loading peer.
 hp=0;now++;TickBbscWorldPresence();
 const auto dead_host=sent.back();
 auto dead_guest=dead_host;dead_guest.visit+=4;dead_guest.sequence=500;
 OnBbscWorldPresencePacket(22,11,&dead_guest,sizeof(dead_guest));
 OnBbscWorldPresencePacket(23,11,&dead_guest,sizeof(dead_guest));
 loading=true;now++;TickBbscWorldPresence();
 assert(sent.back().phase==World::Phase::Loading&&sent.back().world==dead_host.world);
 auto loading_guest=dead_guest;loading_guest.phase=World::Phase::Loading;++loading_guest.sequence;
 OnBbscWorldPresencePacket(22,11,&loading_guest,sizeof(loading_guest));
 OnBbscWorldPresencePacket(23,11,&loading_guest,sizeof(loading_guest));
 auto arrived_guest=dead_guest;arrived_guest.alive=1;++arrived_guest.visit;
 arrived_guest.sequence=loading_guest.sequence+1;
 OnBbscWorldPresencePacket(22,11,&arrived_guest,sizeof(arrived_guest));
 assert(!World::SamePlace(bbsc_world_presence_local,bbsc_world_presence_book.Find(22,now)->presence));
 loading=false;hp=594;++bbsc_load_generation;now++;TickBbscWorldPresence();
 assert(sent.back().world==dead_host.world&&sent.back().map==dead_host.map&&sent.back().visit>dead_host.visit);
 assert(World::SamePlace(bbsc_world_presence_local,bbsc_world_presence_book.Find(22,now)->presence));
 assert(!World::SamePlace(bbsc_world_presence_local,bbsc_world_presence_book.Find(23,now)->presence));
 OnBbscWorldPresencePacket(23,11,&arrived_guest,sizeof(arrived_guest));
 OnBbscWorldPresencePacket(23,11,&loading_guest,sizeof(loading_guest));
 assert(World::SamePlace(bbsc_world_presence_local,bbsc_world_presence_book.Find(23,now)->presence));
 assert(bbsc_world_presence_book.Find(23,now)->presence.visit>dead_guest.visit);
 // Chalice identity is observed, never guessed: ritual 0 cannot join simulation.
 map=0x1D0A5A00;loading=true;now++;TickBbscWorldPresence();
 dungeon={55,66,16,0};loading=false;now++;TickBbscWorldPresence();
 assert(sent.back().dungeon==dungeon&&sent.back().ritual==0);
 assert(!World::SamePlace(sent.back(),sent.back()));
 const auto count=sent.size();type=2;now+=1000;TickBbscWorldPresence();assert(sent.size()==count);
}
'''

def main():
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-world-bridge-') as tmp:
        cpp=Path(tmp)/'bridge.cpp';exe=Path(tmp)/('bridge.exe' if os.name=='nt' else 'bridge')
        cpp.write_text(PREFIX+function('u64 ReadBbscWorldRoom()')+function('void TickBbscWorldPresence()')+
            function('void OnBbscWorldPresencePacket(std::uint32_t sender, std::uint32_t session,\n                               const void* data, std::size_t size)')+MAIN,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production world tick/receiver: independent same-room wipe arrivals, borders, session fencing, passive capabilities')

if __name__=='__main__': main()
