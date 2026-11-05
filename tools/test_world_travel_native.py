"""Execute actual ESD/native travel hooks without loading a game or touching saves."""
from pathlib import Path
import os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'emulator/src/core/bbsc_world_travel.inc').read_text(encoding='utf-8')
PREFIX=r'''
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
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
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_ERROR(...)
#define BBSC_TIMELINE(...)
struct GuestRegisterSnapshot{u64 rax{},rbx{},rcx{},rdx{},rsi{},rdi{},rbp{},rsp{},r8{},r9{},r10{},r11{},r12{},r13{},r14{},r15{},rflags{};};
constexpr u64 TalkConditionVtableOffset=0x0535AAB0,WorldFlagManPointerOffset=0x553b100;
std::array<u8,0x1600> global{};
u64 GetGlobalState(){return reinterpret_cast<u64>(global.data());}
enum class MemoryProt{CpuWrite};bool HasMemoryAccess(u64 p,size_t,MemoryProt){return p>=0x10000;}
template<class T>void WriteValue(u64 p,size_t offset,T v){std::memcpy(reinterpret_cast<void*>(p+offset),&v,sizeof(v));}
s64 native_event=12107000;s64 BbscEventIdOf(u64){return native_event;}
u64 image_base=0x100000;s64 now=10000;s32 state=6,hp=594;bool allowed=true,opening=true;
u64 GetLocalPlayerCharacter(){return 0x20000;}
s32 GetLocalPlayerType(){return state==3?0:1;}
s32 GetSessionState(){return state;}
s32 GetCharacterHp(u64){return hp;}
bool BbscRegisterRemotePlayer(u64 p){return p==0x30000;}
bool BbscIndependentTravelAllowed(){return allowed;}
bool scene_ready=true;bool BbscWorldSceneReady(){return scene_ready;}
bool BbscOwnOpeningDone(){return opening;}
s64 SteadyNowMs(){return now;}
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
template<class T>T ReadValue(u64 p,size_t offset){if(p==image_base+WorldFlagManPointerOffset)return static_cast<T>(GetGlobalState());T v;std::memcpy(&v,reinterpret_cast<void*>(p+offset),sizeof(T));return v;}
template<class T,size_t N>void Set(std::array<u8,N>& a,size_t offset,T value){std::memcpy(a.data()+offset,&value,sizeof(T));}
bool BbscEventFlag(u32 flag){return flag>=12907810&&flag<=12907990;}
namespace Core::Bbsc {bool SwitchEnabled(const char*){return true;}}
std::mutex bbsc_world_presence_mutex;World::Presence bbsc_world_presence_local;
struct BbscWorldAltar{World::AltarEntry entry;Chalice::Mount mount;};
std::array<BbscWorldAltar,7> bbsc_world_altars;
std::atomic<bool> bbsc_world_catalog_ready{false};
std::atomic<u32> bbsc_load_generation{1};std::atomic<u64> bbsc_world_native_load{1};
s32 bbsc_world_altar_visiting=-1;
std::optional<Chalice::Mount> bbsc_world_requested_mount;
std::optional<World::Scope> bbsc_world_requested_scope;
'''
PREFIX+=r'''
std::atomic<bool> bbsc_reload_finish_pending{false};std::atomic<u64> bbsc_world_load_pending{0};
namespace BbscMod {u32 RegisterOwnId(){return 22;}}
u64 bbsc_world_state_sequence=0;
u32 current_map=0x15000000;u32 GetCurrentPackedMap(){return current_map;}
bool snapshot_ready=false;int sent=0,arms=0,applies=0,sets=0;u32 released=0;
void BbscWorldEnsureSeed(const World::Scope&){}
bool BbscWorldHasSnapshot(u32){return snapshot_ready;}
void BbscWorldSend(const World::Control&){++sent;}
void ApplyBbscIndependentAtLoad(u32){++applies;}
bool PrepareBbscChaliceLoad(u32){return true;}
void ArmBbscReinsertV8(){++arms;}
void PS4_SYSV_ABI NativeFlag(u64 man,u32 flag,u8 value){assert(man==GetGlobalState()&&value==1);++sets;released=flag;}
void Link(u64 off,void* target){auto* p=reinterpret_cast<u8*>(image_base+off);p[0]=0x48;p[1]=0xb8;u64 a=reinterpret_cast<u64>(target);std::memcpy(p+2,&a,8);p[10]=0xff;p[11]=0xe0;}
'''
MAIN=r'''
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x2000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 Link(0x13cfcc0,reinterpret_cast<void*>(&NativeFlag));
 bbsc_world_presence_local.world={11,99};
 std::array<u8,128> result{},context{};
 Set(context,0,image_base+TalkConditionVtableOffset);Set(context,0x10,u32{210000});
 Set(context,0x18,u64{0x40000}); // actual device actor differs from local PlayerIns
 // Actual203AD60: R12=RDI=result variant, R15=RSI=condition evaluator.
 // The old fixture incorrectly put the evaluator in R12 and missed closed lamps.
 GuestRegisterSnapshot r;r.r12=reinterpret_cast<u64>(result.data());r.r15=reinterpret_cast<u64>(context.data());
 r.r14=0x50000;
 auto command=[&](u32 talk,u64 actor,s32 id){Set(context,0x10,talk);Set(context,0x18,actor);
  NoteBbscWorldTalkRecord(reinterpret_cast<u64>(context.data()),r.r14);r.rax=id;BbscWorldAltarCommand(0,&r);};
 r.rax=26;BbscWorldEsdFunction(0,&r);r.r15=7;r.rax=1;BbscWorldEsdResult(0,&r);assert(r.rax==0);
 assert((result==std::array<u8,128>{})); // result pointer must never be treated as an evaluator
 r.r15=reinterpret_cast<u64>(context.data());BbscWorldLampTalker(0,&r);
 assert(r.r15==reinterpret_cast<u64>(bbsc_world_live_talk.data()));
 Set(context,0x10,u32{210699});r.r15=reinterpret_cast<u64>(context.data());r.rax=14;BbscWorldEsdFunction(0,&r);
 BbscWorldLampTalker(0,&r);assert(r.r15==reinterpret_cast<u64>(context.data())); // no spoofed NPC quests
 Set(context,0x10,u32{241000});r.rax=52;BbscWorldEsdFunction(0,&r);
 r.rax=1;r.rcx=1;BbscWorldLampMultiplayer(0,&r);assert((r.rax&255)==0&&(r.rcx&255)==0);
 command(241000,0x40000,11);
 r.r15=70000200;r.rax=123;BbscWorldLampCommandRange(0,&r);assert(r.rax==reinterpret_cast<u64>(bbsc_world_lamp_command.data()));
 assert(!QueueBbscWorldTravel(6200,1));
 scene_ready=false;assert(BbscWorldTalkAllowed(241000));scene_ready=true;
 assert(QueueBbscWorldTravel(70000200,1));
 assert(bbsc_world_travel_point==2102950&&bbsc_world_requested_scope->map==0x15000000);
 assert(bbsc_world_requested_scope->world==(World::WorldId{11,99}));
 bbsc_world_travel_point=0;now+=2000;assert(QueueBbscWorldTravel(70000200,1)); // no stale talk context
 Set(context,0x18,u64{0x30000});r.r15=reinterpret_cast<u64>(context.data());r.rax=26;BbscWorldEsdFunction(0,&r);
 BbscWorldTalkAllowed(241000);assert(QueueBbscWorldTravel(70000200,1)); // another actor's talk does not move us
 command(241000,0x30000,11);assert(QueueBbscWorldTravel(70000200,1));
 Set(context,0x18,u64{0x40000});r.rax=52;BbscWorldEsdFunction(0,&r);
 BbscWorldTalkAllowed(210000);
 command(210000,0x40000,11);
 const auto destination=LampTravel::Returns[0];assert(QueueBbscWorldTravel(destination.flag,1));
 assert(bbsc_world_travel_point==destination.point&&bbsc_world_requested_scope->map!=0x15000000);
 bbsc_world_travel_point=0;bbsc_world_catalog_ready=true;
 auto& altar=bbsc_world_altars[3];altar.entry.occupied=true;altar.entry.ritual=36;
 altar.mount.key={55,66,88,0};altar.mount.stage_map=0x1D000000;altar.mount.layout_map=0x1D0A5A00;
 command(210080,0x40000,78);assert(r.rax==78);
 BbscWorldTalkAllowed(210721); // another script evaluated: command mapping must still select our altar
 r.rax=78;BbscWorldAltarCommand(0,&r);assert(r.rax==78);
 r.rax=79;BbscWorldAltarCommand(0,&r);assert(r.rax==79);
 altar.entry.occupied=false;r.rax=79;BbscWorldAltarCommand(0,&r);assert(r.rax==88);altar.entry.occupied=true;
 state=3;r.rax=78;BbscWorldAltarCommand(0,&r);assert(r.rax==78);state=6;
 assert(!QueueBbscWorldTravel(72100423,1));
 assert(bbsc_world_travel_point==0); // actual native ESD order: altar first
 assert(QueueBbscWorldTravel(72100302,1));
 assert(bbsc_world_travel_point==2902952&&bbsc_world_altar_visiting==3);
 assert(bbsc_world_requested_scope->ritual==36&&bbsc_world_requested_scope->dungeon==altar.mount.key);
 bbsc_world_travel_inflight=true;r.rax=12345;BbscWorldBonfirePhase(0,&r);
 assert(r.rax==reinterpret_cast<u64>(bbsc_world_bonfire_phase.data()));
 bbsc_world_travel_point=2102950;r.rax=12345;BbscWorldBonfirePhase(0,&r);assert(r.rax==reinterpret_cast<u64>(bbsc_world_bonfire_phase.data()));
 bbsc_world_travel_inflight=false;bbsc_world_travel_point=0;
 state=3;bbsc_world_travel_point=0;command(241000,0x40000,11);assert(QueueBbscWorldTravel(70000200,1)&&bbsc_world_travel_point==2102950);state=6;bbsc_world_travel_point=0;
 allowed=false;assert(!QueueBbscWorldTravel(70000200,1));assert(!BbscWorldTalkAllowed(241000));
 allowed=true;opening=false;assert(BbscWorldTalkAllowed(241000));
 // All actual dungeon lamp scripts: UI, multiplayer gate, executor range and
 // return-to-Dream must work without opening-story or scene-admission gates.
 scene_ready=false;
 for(u32 talk:LampTravel::DungeonTalks){
  bbsc_world_travel_point=0;command(talk,0x40000,11);
  assert(BbscWorldTalkAllowed(talk));
  Set(context,0x10,talk);r.r15=reinterpret_cast<u64>(context.data());r.rax=52;BbscWorldEsdFunction(0,&r);
  r.rax=1;r.rcx=1;BbscWorldLampMultiplayer(0,&r);assert((r.rax&255)==0&&(r.rcx&255)==0);
  r.r15=70000200;r.rax=123;BbscWorldLampCommandRange(0,&r);assert(r.rax==reinterpret_cast<u64>(bbsc_world_lamp_command.data()));
  assert(QueueBbscWorldTravel(70000200,1)&&bbsc_world_travel_point==2102950);
 }
 scene_ready=true;bbsc_world_travel_point=0;
 assert(!BbscWorldTalkAllowed(290600)); // a dungeon NPC is not a lamp
 opening=true;command(210000,0x40000,11);++bbsc_load_generation;
 r.rax=11;BbscWorldAltarCommand(0,&r);assert(QueueBbscWorldTravel(70000200,1)); // retired executor generation

 // Execute the real native release/tick: no StageTransition, forced coordinates,
 // UI closure, or animation reconstructed by the mod can link into this fixture.
 bbsc_world_travel_point=0;command(210000,0x40000,11);now+=1;
 assert(QueueBbscWorldTravel(destination.flag,1));assert(sets==0);
 const auto unchanged=global;TickBbscWorldTravel();assert(sent==1&&sets==0&&arms==0);
 snapshot_ready=true;TickBbscWorldTravel();assert(sets==1&&released==destination.flag&&arms==0&&global==unchanged);
 for(int i=0;i<4;++i){now+=1000;TickBbscWorldTravel();}assert(sets==1&&arms==0);
 r.rdi=destination.point;r.rsi=12345;BbscWorldNativeWarpBegin(&r);BbscWorldNativeWarpBegin(&r);assert(arms==1);
 ++bbsc_load_generation;current_map=bbsc_world_requested_scope->map;TickBbscWorldTravel();assert(!bbsc_world_travel_inflight&&applies==1);
 r.rdi=2102950;BbscWorldNativeWarpBegin(&r);assert(arms==2); // original unqueued return also prepares native admission
 std::array<u8,0xc0> instance{};std::array<u8,0x20> instruction{},reference{};std::array<u8,0x200> file{};
 Set(instance,0xb0,reinterpret_cast<u64>(instruction.data()));Set(instance,0xa8,reinterpret_cast<u64>(reference.data()));
 Set(instance,0x78,u8{1});Set(reference,8,reinterpret_cast<u64>(file.data()));Set(file,0x78,u64{0x100});
 Set(instruction,0,s32{1003});Set(instruction,4,s32{6});Set(instruction,8,u64{4});Set(file,0x100,u32{256});
 native_event=12410000;EnableBbscNativeTravelEvent(reinterpret_cast<u64>(instance.data()));assert(ReadValue<s32>(reinterpret_cast<u64>(instruction.data()),0)==1003);
 native_event=12107000;++bbsc_world_native_load;EnableBbscNativeTravelEvent(reinterpret_cast<u64>(instance.data()));
 assert(ReadValue<s32>(reinterpret_cast<u64>(instruction.data()),0)==1001&&instance[0x78]==0&&ReadValue<u32>(reinterpret_cast<u64>(file.data()),0x100)==0);
 VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);

}
'''
def check_original_altar_scripts(game):
    import sys
    sys.path.insert(0,str(ROOT/'tools/gamedata'))
    import bbfiles,esd
    files=bbfiles.read_bnd4(bbfiles.read_dcx(game/'script/talk/m21_00_00_00.talkesdbnd.dcx'))
    for slot in range(7):
        script=esd.Esd(files[f't{210050+slot*10}.esd'][1])
        commands=[c for g in script.groups.values() for state in g['states'].values() for c in state['entry']]
        assert any(b==1 and i==(78 if slot==0 else 79) and not args for b,i,args in commands)
        choices={int(args[0][0]) for b,i,args in commands if b==1 and i==19 and args and args[0][0].isdigit()}
        assert set(range(1,11))<=choices
        assert any(str(72100420+slot) in str(args) for b,i,args in commands)
    print('PASS original seven altar scripts: native78/79, ten layer choices, exact altar selection flags')
    dungeon=bbfiles.read_bnd4(bbfiles.read_dcx(game/'script/talk/m29_00_00_00.talkesdbnd.dcx'))
    actual=set()
    for name,(_,raw) in dungeon.items():
        commands=esd.Esd(raw).all_commands()
        if any(b==1 and i==11 and any('70000200' in a for a in args) for g,s,b,i,args in commands):
            actual.add(int(name[1:-4]))
    import re
    header=(ROOT/'emulator/src/core/bbsc_lamp_travel_data.h').read_text(encoding='utf-8')
    registered={int(x) for x in re.search(r'DungeonTalks\{([^}]+)',header).group(1).replace('\n','').split(',') if x.strip()}
    assert actual==registered,(actual,registered)
    print('PASS every original chalice lamp ESD is registered, no NPCs substituted')
    from emevd import Emevd
    for name,event,animation in [('m21_00_00_00.emevd.dcx',12107000,101164),('common.emevd.dcx',7200,101160)]:
        script=Emevd(game/'event'/name)
        instructions=next(ins for eid,ins in script.events if eid==event)
        assert instructions[0]==(1003,6,bytes.fromhex('00010000'))
        animate=next(i for i,(b,k,a) in enumerate(instructions) if b==2004 and k==14 and int.from_bytes(a[8:12],'little')==animation)
        warp=next(i for i,(b,k,a) in enumerate(instructions) if b==2003 and k==49)
        assert animate<warp and any(b==1001 and k==0 for b,k,a in instructions[animate:warp])
    print('PASS original native travel: animation and timed native event precede WarpNextStage_Bonfire')


def main():
    source=SOURCE[SOURCE.index('s32 bbsc_world_travel_point='):SOURCE.index('void InstallBbscWorldTravel() {')]
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-world-travel-') as tmp:
        cpp=Path(tmp)/'travel.cpp';exe=Path(tmp)/('travel.exe' if os.name=='nt' else 'travel')
        cpp.write_text(PREFIX+source+MAIN,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production ESD dispatcher ABI: R12=result/R15=evaluator, saved context, local actor, scoped lamps/headstones, host ritual/layer, native phase guard')

if __name__=='__main__':
    main()
    if os.environ.get('BBSC_TEST_GAME'):check_original_altar_scripts(Path(os.environ['BBSC_TEST_GAME']))
