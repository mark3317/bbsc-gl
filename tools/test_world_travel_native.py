"""Execute actual ESD/native travel hooks without loading a game or touching saves."""
from pathlib import Path
import os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'emulator/src/core/bbsc_world_travel.inc').read_text(encoding='utf-8')
PREFIX=r'''
#include <atomic>
#include <cassert>
#include <mutex>
#include "core/bbsc_world_control.h"
#include "core/bbsc_world_altars.h"
#include "core/bbsc_world_lamp_points.h"
#include "core/bbsc_lamp_travel_data.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#undef PS4_SYSV_ABI
#define PS4_SYSV_ABI
#define BBSC_TIMELINE(...)
struct GuestRegisterSnapshot{u64 rax{},rbx{},rcx{},rdx{},rsi{},rdi{},rbp{},rsp{},r8{},r9{},r10{},r11{},r12{},r13{},r14{},r15{},rflags{};};
constexpr u64 TalkConditionVtableOffset=0x0535AAB0;
u64 image_base=0x100000;s64 now=10000;s32 state=6,hp=594;bool allowed=true,opening=true;
u64 GetLocalPlayerCharacter(){return 0x20000;}
s32 GetLocalPlayerType(){return state==3?0:1;}
s32 GetSessionState(){return state;}
s32 GetCharacterHp(u64){return hp;}
bool BbscIndependentTravelAllowed(){return allowed;}
bool BbscOwnOpeningDone(){return opening;}
s64 SteadyNowMs(){return now;}
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
template<class T>T ReadValue(u64 p,size_t offset){T v;std::memcpy(&v,reinterpret_cast<void*>(p+offset),sizeof(T));return v;}
template<class T>void Set(std::array<u8,128>& a,size_t offset,T value){std::memcpy(a.data()+offset,&value,sizeof(T));}
bool BbscEventFlag(u32 flag){return flag>=12907810&&flag<=12907990;}
namespace Core::Bbsc {bool SwitchEnabled(const char*){return true;}}
std::mutex bbsc_world_presence_mutex;World::Presence bbsc_world_presence_local;
struct BbscWorldAltar{World::AltarEntry entry;Chalice::Mount mount;};
std::array<BbscWorldAltar,7> bbsc_world_altars;
std::atomic<bool> bbsc_world_catalog_ready{false};
s32 bbsc_world_altar_visiting=-1;
std::optional<Chalice::Mount> bbsc_world_requested_mount;
std::optional<World::Scope> bbsc_world_requested_scope;
'''
MAIN=r'''
int main(){
 bbsc_world_presence_local.world={11,99};
 std::array<u8,128> condition{},context{};
 Set(condition,0,image_base+TalkConditionVtableOffset);Set(condition,0x10,u32{210000});
 Set(context,0x10,u32{2100950}); // entity id is deliberately NOT the ESD talk id
 Set(context,0x18,u64{0x20000});
 GuestRegisterSnapshot r;r.r12=reinterpret_cast<u64>(condition.data());r.r15=reinterpret_cast<u64>(context.data());
 r.rax=26;BbscWorldEsdFunction(0,&r);r.rax=1;BbscWorldEsdResult(0,&r);assert(r.rax==0);
 r.r15=reinterpret_cast<u64>(context.data());BbscWorldLampTalker(0,&r);
 assert(r.r15==reinterpret_cast<u64>(bbsc_world_live_talk.data()));
 Set(condition,0x10,u32{210699});r.r15=reinterpret_cast<u64>(context.data());
 BbscWorldLampTalker(0,&r);assert(r.r15==reinterpret_cast<u64>(context.data())); // no spoofed NPC quests
 Set(condition,0x10,u32{241000});r.rax=52;BbscWorldEsdFunction(0,&r);
 r.rax=1;r.rcx=1;BbscWorldLampMultiplayer(0,&r);assert((r.rax&255)==0&&(r.rcx&255)==0);
 assert(!QueueBbscWorldTravel(6200,1));
 assert(QueueBbscWorldTravel(70000200,1));
 assert(bbsc_world_travel_point==2102950&&bbsc_world_requested_scope->map==0x15000000);
 assert(bbsc_world_requested_scope->world==(World::WorldId{11,99}));
 bbsc_world_travel_point=0;now+=2000;assert(!QueueBbscWorldTravel(70000200,1)); // no stale talk context
 Set(context,0x18,u64{0x30000});r.r15=reinterpret_cast<u64>(context.data());r.rax=26;BbscWorldEsdFunction(0,&r);
 BbscWorldTalkAllowed(241000);assert(!QueueBbscWorldTravel(70000200,1)); // another actor's talk does not move us
 Set(context,0x18,u64{0x20000});r.rax=52;BbscWorldEsdFunction(0,&r);
 BbscWorldTalkAllowed(210000);
 const auto destination=LampTravel::Returns[0];assert(QueueBbscWorldTravel(destination.flag,1));
 assert(bbsc_world_travel_point==destination.point&&bbsc_world_requested_scope->map!=0x15000000);
 bbsc_world_travel_point=0;bbsc_world_catalog_ready=true;
 auto& altar=bbsc_world_altars[3];altar.entry.occupied=true;altar.entry.ritual=36;
 altar.mount.key={55,66,88,0};altar.mount.stage_map=0x1D000000;altar.mount.layout_map=0x1D0A5A00;
 BbscWorldTalkAllowed(210080);r.rax=78;BbscWorldAltarCommand(0,&r);assert(r.rax==41);
 r.rax=79;BbscWorldAltarCommand(0,&r);assert(r.rax==88);
 state=3;r.rax=78;BbscWorldAltarCommand(0,&r);assert(r.rax==78);state=6;
 assert(QueueBbscWorldTravel(72100423,1));
 assert(bbsc_world_travel_point==0); // actual native ESD order: altar first
 assert(QueueBbscWorldTravel(72100302,1));
 assert(bbsc_world_travel_point==2902952&&bbsc_world_altar_visiting==3);
 assert(bbsc_world_requested_scope->ritual==36&&bbsc_world_requested_scope->dungeon==altar.mount.key);
 bbsc_world_travel_inflight=true;r.rax=12345;BbscWorldBonfirePhase(0,&r);
 assert(r.rax==reinterpret_cast<u64>(bbsc_world_bonfire_phase.data()));
 bbsc_world_travel_point=2102950;r.rax=12345;BbscWorldBonfirePhase(0,&r);assert(r.rax==12345);
 bbsc_world_travel_inflight=false;bbsc_world_travel_point=0;
 allowed=false;assert(!QueueBbscWorldTravel(70000200,1));assert(!BbscWorldTalkAllowed(241000));
 allowed=true;opening=false;assert(!BbscWorldTalkAllowed(241000));
}
'''
def main():
    source=SOURCE[SOURCE.index('s32 bbsc_world_travel_point='):SOURCE.index('void TickBbscWorldTravel() {')]
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-world-travel-') as tmp:
        cpp=Path(tmp)/'travel.cpp';exe=Path(tmp)/('travel.exe' if os.name=='nt' else 'travel')
        cpp.write_text(PREFIX+source+MAIN,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production ESD scope, local actor, actual evaluator/entity distinction, lamps/headstones, selected host ritual/layer, native phase guard')

if __name__=='__main__':main()
