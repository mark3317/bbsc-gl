"""Native successful fog write -> scoped start; no act survives a load."""
import os, subprocess, tempfile, sys, struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/gamedata'))
from emevd import Emevd
game=Path(sys.argv[1])
source=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
module=(ROOT/'emulator/src/core/bbsc_boss_entrance.inc').read_text(encoding='utf-8')
# Original guest events have exactly one successful write, after the timeout
# branch (1000[107]) that skips it. No act is sent on button press/animation start.
checked=0
for path in (game/'event').glob('*.emevd.dcx'):
    for event,ins in Emevd(path).events:
        if event not in [12104811,12104881,12204891,12304731,12304811,12404841,
          12414731,12414811,12424711,12424811,12504811,12604846,12604861,12704841,
          12804881,12906790,12906802,13304871,13404801,13404851,13504801,13504851,13604801]:continue
        writes=[i for i,(bank,op,args) in enumerate(ins) if (bank,op)==(2003,2)]
        assert len(writes)==1 and ins[writes[0]-1][:2] in ((1000,7),(1000,107))
        assert struct.unpack('<II',ins[writes[0]][2])[1]==1
        checked+=1
assert checked==23
code=r'''
#include <atomic>
#include <cassert>
#include <mutex>
#include "core/bbsc_boss_retry.h"
#include "core/bbsc_guest_access.h"
#include "core/bbsc_world_control.h"
namespace World=Core::Bloodborne::World;
namespace Chalice=Core::Bloodborne::Chalice;
namespace BossRetry=Core::Bloodborne::BossRetry;
namespace GuestAccess=Core::Bloodborne::GuestAccess;
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define BBSC_TIMELINE(...)
std::mutex bbsc_world_presence_mutex;
World::Presence bbsc_world_presence_local;
World::PresenceBook bbsc_world_presence_book;
std::atomic<u64> bbsc_world_native_load{1};
struct Cup {Chalice::Mount layout;std::vector<BossRetry::ChaliceAttempt> constructors;};
Cup bbsc_chalice_boss_attempts;
World::Scope fixture_ritual;
Chalice::Mount fixture_catalogue;
bool BbscChaliceBossLayoutMatchesScope(const World::Scope& scope,const Chalice::Mount& layout) {
 return scope==fixture_ritual && Chalice::SameLayout(layout,fixture_catalogue);
}
struct BbscWorldIncoming {u32 sender;World::Control control;std::vector<u8> payload;};
std::vector<BbscWorldIncoming> sent;
std::map<u32,bool> flags;
int writes=0,role=6,type=1,hp=594;bool active=true,ready=true;
std::array<u8,16> global{};
u64 GetGlobalState(){return (u64)global.data();}
bool IsInvaderType(int t){return t==2;}
std::atomic<u64> bbsc_world_load_pending{0};std::atomic<bool> bbsc_reload_finish_pending{false};
bool BbscQuitInProgress(){return false;}bool BbscReturningToTitle(){return false;}
u32 self=2;
namespace BbscMod {u32 RegisterOwnId(){return self;}}
void PS4_SYSV_ABI SetFlag(u64,u32 f,u32 v){flags[f]=v;++writes;}
u64 image_base=(u64)&SetFlag-0x013CFCC0;
constexpr u64 EventFlagManPointerOffset=0x553B100;
template<class T>T ReadValue(u64 p,size_t o){if(p==image_base+EventFlagManPointerOffset)return T(1);T v;std::memcpy(&v,(void*)(p+o),sizeof(v));return v;}
void store(u64 p,size_t o,auto v){std::memcpy((void*)(p+o),&v,sizeof(v));}
bool ReadablePointer(u64 p,size_t){return p!=0;}
bool BbscEventFlag(u32 f){return flags[f];}
bool BbscIndependentActive(){return active;}
int GetSessionState(){return role;}
int GetLocalPlayerType(){return type;}
u64 GetLocalPlayerCharacter(){return 1;}
int GetCharacterHp(u64){return hp;}
bool BbscWorldSceneReady(){return ready;}
s64 event_id=12906802;
s64 BbscEventIdOf(u64){return event_id;}
void BbscWorldSend(World::Control c,std::span<const u8> p){sent.push_back({self,c,{p.begin(),p.end()}});}
'''+module+r'''
int main(){
 auto& local=bbsc_world_presence_local;
 local.world={1,99};local.sequence=1;local.visit=7;local.map=0x1d000000;local.dungeon={12,34,56,0};local.ritual=10;
 local.phase=World::Phase::Playing;local.alive=1;
 bbsc_world_presence_book.Bind(local.world,self);
 auto host=local;host.visit=5;
 assert(bbsc_world_presence_book.Hear(1,local.world,host,1));
 auto scope=World::ScopeOf(local);
 fixture_ritual=scope;
 fixture_catalogue.key=scope.dungeon;
 fixture_catalogue.layout_map=0x1d0a5a00;
 auto native_layout=fixture_catalogue;native_layout.key={scope.dungeon.channel,0,0,0};
 bbsc_chalice_boss_attempts={native_layout,{BossRetry::ReadChaliceInit(std::array{
   1u,12906802u,2903066u,2901036u,12901801u,12900536u,12905511u,12905512u})}};
 std::array<u8,0xc0> instance{};std::array<u8,32> pc{};
 std::array<u32,2> args{12905512,1};u64 p=(u64)instance.data();
 store(p,0xb0,(u64)pc.data());store(p,0xb8,(u64)args.data());store(p,0x2c,u16{1});
 store((u64)pc.data(),0,s32{2003});store((u64)pc.data(),4,s32{2});store((u64)pc.data(),8,u64{8});
 // Canceled/failed traversal never reaches this command. Other commands do nothing.
 store((u64)pc.data(),4,s32{11});NoteBbscGuestBossEntrance(p);assert(writes==0 && sent.empty());
 store((u64)pc.data(),4,s32{2});type=2;NoteBbscGuestBossEntrance(p);assert(writes==0);type=1;
 hp=0;NoteBbscGuestBossEntrance(p);assert(writes==0);hp=594;
 args[1]=0;NoteBbscGuestBossEntrance(p);assert(writes==0);args[1]=1;
 NoteBbscGuestBossEntrance(p);assert(flags[12905511] && !flags[12901801] && sent.size()==1);
 assert(BbscGuestStartedFlag(12905511) && BbscGuestStartedFlag(12905512) && !BbscGuestStartedFlag(12905513));
 assert(sent[0].control.epoch==5 && sent[0].control.sequence==7 && sent[0].control.owner==1);
 // Original next instruction writes entered. A stale owner snapshot cannot undo either.
 std::array<u8,125> before{},stale{};
 for(u32 f:{12905511u,12905512u})before[f%1000/8]|=0x80>>(f%8);
 KeepBbscGuestStartedFlags(12905,before.data(),stale.data());assert(stale==before);
 auto request=sent[0];self=1;role=3;local=host;bbsc_guest_started_boss={};flags.clear();
 bbsc_world_presence_book.Bind(local.world,self);auto guest=host;guest.visit=7;
 assert(bbsc_world_presence_book.Hear(2,local.world,guest,1));
 BbscWorldReceiveBossEntrance(request);assert(flags[12905511]);
 int count=writes;BbscWorldReceiveBossEntrance(request);assert(writes==count); // duplicate
 // Same map reload/new ritual/other member/corrupt pair cannot restart the encounter.
 auto reject=[&](BbscWorldIncoming bad){bbsc_guest_started_boss={};flags.clear();int n=writes;BbscWorldReceiveBossEntrance(bad);assert(writes==n);};
 ++local.visit;reject(request);--local.visit;
 ++local.ritual;reject(request);--local.ritual;
 auto bad=request;bad.sender=3;reject(bad);
 bad=request;++bad.control.sequence;reject(bad);
 bad=request;reinterpret_cast<BbscBossEntrance*>(bad.payload.data())->start=12905502;reject(bad);
 ready=false;reject(request);ready=true;
 global[8]=1;reject(request);global[8]=0;
 bbsc_world_load_pending=1;reject(request);bbsc_world_load_pending=0;
 bbsc_reload_finish_pending=true;reject(request);bbsc_reload_finish_pending=false;
 flags[12901801]=true;bbsc_guest_started_boss={};count=writes;BbscWorldReceiveBossEntrance(request);assert(writes==count);
 flags.clear();++bbsc_world_native_load;stale.fill(0);KeepBbscGuestStartedFlags(12905,before.data(),stale.data());assert(stale!=before);
 // Story/DLC whitelist and exact guest-entered mapping.
 scope={};scope.map=0x18000000;
 auto amelia=ResolveBbscBossEntrance(12404841,0,12404801,scope);assert(amelia.start==12404800 && amelia.victory==12401800);
 assert(!ResolveBbscBossEntrance(12404841,0,12404802,scope).start);
 scope.map=0x22000000;
 auto ludwig=ResolveBbscBossEntrance(13404801,0,13404809,scope);assert(ludwig.start==13404808 && ludwig.victory==9471);
 auto laurence=ResolveBbscBossEntrance(13404851,0,13404859,scope);assert(laurence.victory==13401850);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-boss-entrance-') as temp:
 p=Path(temp);(p/'test.cpp').write_text(code,encoding='utf-8')
 compiler=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
 env=dict(os.environ,PATH=str(Path(compiler).parent)+os.pathsep+os.environ['PATH'])
 subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(p/'test.cpp'),'-o',str(p/'test.exe')],check=True,env=env)
 subprocess.run([str(p/'test.exe')],check=True,env=env)
print('PASS guest native fog completion, peer start, stale snapshots and old-visit rejection; 23 original fog events')
