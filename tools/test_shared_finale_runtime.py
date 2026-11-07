"""Exercise shared scene routing and compatibility with interrupted offline finales."""
import os, subprocess, tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
def fn(sig):
    a=s.index(sig+' {');b=s.index('{',a)+1;depth=1
    while depth:
        depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[a:b]
packet=s[s.index('struct BbscCutscenePacket'):s.index('\n};',s.index('struct BbscCutscenePacket'))+3]
queued=s[s.index('struct BbscQueuedCutscene'):s.index('\n};',s.index('struct BbscQueuedCutscene'))+3]
code=r'''
#include <array>
#include <atomic>
#include <cassert>
#include <cstring>
#include <cstdint>
#include <deque>
#include <map>
#include <mutex>
#include <optional>
#include <string_view>
#include <unordered_map>
#include "core/bbsc_dream_finale.h"
#include "core/bbsc_lamp_travel_data.h"
#include "core/bbsc_world_presence.h"
namespace LampTravel=Core::Bloodborne::LampTravel;
namespace World=Core::Bloodborne::World;
bool BbscIndependentTravelAllowed(){return true;}
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI
#define BBSC_TIMELINE(...)
#define LOG_INFO(...)
constexpr u8 BbscCutsceneType=0x28;
namespace Bbsc=Core::Bbsc;
#pragma pack(push,1)
''' + packet + r'''
#pragma pack(pop)
''' + queued + r'''
int state=6,hp=0,revives=0,penalties=0,camera=0,requests=0,saves=0,stops=0;
u64 image_base=1;u32 map=0x15000000;constexpr u32 BbscDreamStateMap=0x15000000;
bool bbsc_spectate_active=true,loading=false,curtain=false,lua=true,revive_ok=false,quit=false;
bool bbsc_progress_was_guest=true,bbsc_recover_session_cleanup=false;
u64 global=100,player=200,slots=300,local=400,game_data=500,manager=600;
constexpr u64 PlayerSlotManagerPointerOffset=10,MatchingStatePointerOffset=20;
std::map<u64,u64> mem;bool flag=true; s64 event=12100000;
template<class T>T ReadValue(u64 p,size_t off){return static_cast<T>(mem[p+off]);}
template<class T>void WriteValue(u64 p,size_t off,T v){mem[p+off]=v;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
int GetSessionState(){return state;}u32 GetCurrentPackedMap(){return map;}
u64 GetGlobalState(){return global;}u64 GetLocalPlayerCharacter(){return player;}
int GetCharacterHp(u64){return hp;}bool BbscCurtainActive(){return curtain;}
bool IsSprjLuaEventManReady(){return lua;}void BbscApplyDeathPenalty(std::string_view){++penalties;}
bool BbscRespawnInPlace(std::string_view){++revives;if(revive_ok)hp=600;return revive_ok;}
namespace Core::Bbsc{void CinematicForceOff(){++camera;}void CinematicSetWatching(bool){++camera;}}
s64 BbscEventIdOf(u64){return event;}bool BbscEventFlag(u32){return flag;}
void NativeRequest(u64,u32,u32,u64,u32,u32,u64,u64,u64){++requests;}
u8 NativeStop(u64){++stops;state=0;return 1;}
u64 NativeFlag(u64,u32 id,u8 v){mem[10000+id]=v;return 0;}
u8 NativeSave(s32,s32,s32){++saves;return 1;}
u64 MultiPlayStopRequestOffset=(u64)&NativeStop-1;
u64 BbscNativeSaveRequestOffset=(u64)&NativeSave-1;
std::array<u64,6>BbscCutsceneRequestOffsets{(u64)&NativeRequest-1};
std::mutex bbsc_cutscene_mutex;std::deque<BbscQueuedCutscene>bbsc_cutscene_queue;
std::mutex bbsc_world_presence_mutex;World::Presence bbsc_world_presence_local;
World::PresenceBook bbsc_world_presence_book;
std::unordered_map<s32,u32>bbsc_cutscene_seen;std::atomic<u32>bbsc_load_generation{1};
enum class BbscWork{Cutscene};int queued=0;void QueueBbscWork(BbscWork){++queued;}
bool bbsc_cutscene_replaying=false;void ArmBbscCainhurstReveal(int){}
bool BbscCutscenesEnabled(){return true;}
int delegated=0;
bool BbscGroupStoryMovie(u32 map,s32 scene){return (map==0x20000000&&scene==32000000)||(map==0x18000000&&scene==24000030);}
bool QueueBbscRomNativeTransition(s32 scene){assert(BbscGroupStoryMovie(map,scene));++delegated;return true;}
Bbsc::DreamFinale::Playback bbsc_dream_finale;
std::atomic<u32>bbsc_remo_started_sequence{0};u32 bbsc_dream_finale_start_sequence=0;
s32 bbsc_dream_ng_pending=0;u8 bbsc_dream_ng_target=0;
struct Record{u32 phase=0;BbscCutscenePacket packet{};}bbsc_finale_record;
bool bbsc_finale_save_watch=false;std::atomic<int>bbsc_finale_save_result{-1};
bool SaveBbscFinale(u32 phase,const BbscCutscenePacket& p){bbsc_finale_record={phase,p};return true;}
bool BbscDreamFinaleHolding(){return bbsc_dream_finale.scene||bbsc_finale_record.phase||!bbsc_cutscene_queue.empty();}
std::optional<bool> playing=false;std::optional<bool>BbscRemoPlaying(){return playing;}
bool BbscQuitInProgress(){return quit;}bool BbscReturningToTitle(){return false;}
void RecoverBbscFinale(){}void ApplyBbscHostDreamPhase(){}void ApplyBbscDreamBattleFlags(){}
void TickBbscDreamFirstAudience(){}
bool BbscIndependentActive(){return false;}
bool GuardBbscNativeFinaleEvent(u64,s64,s32){return false;}
bool BbscWorldPeerHere(u32){return true;}u32 GetBbscRelayHost(){return 11;}
void FlushBbscSessionJournals(){}void SendBbscSessionLeave(){}
void SuspendBbscPersistenceOnce(std::string_view){}void CleanupBbscDepartingRemotes(){}
void SetOwnWorldRestoreType(int,void*){}std::map<int,int>bbsc_own_world;
void RestoreBbscOwnWorld(std::string_view){bbsc_own_world.clear();}
''' + fn('bool PrepareBbscSharedFinaleActor()') + fn('bool GuardBbscSharedFinaleEvent(u64 instance)') + fn('void OnBbscCutscenePacket(u32 sender, bool from_host, const void* data, std::size_t size)') + fn('void TickBbscCutsceneReplay()') + fn('void CompleteBbscSharedEndingAtHome()').replace(
    'image_base + 0x0132E5A0','reinterpret_cast<u64>(&NativeFlag)') + fn('void TickBbscDreamFinale()') + r'''
int main(){
 mem[image_base+PlayerSlotManagerPointerOffset]=slots;mem[slots+8]=local;
 mem[image_base+MatchingStatePointerOffset]=manager;mem[image_base+0x0553B130]=game_data;
 for(int scene:{24000000,28000040,28001040,22000040}){
 BbscCutscenePacket trip{};trip.cutscene=scene;trip.sequence=scene;
 OnBbscCutscenePacket(11,true,&trip,sizeof trip);assert(bbsc_cutscene_queue.empty());
 }
 BbscCutscenePacket intro{};intro.map=map;intro.cutscene=21000040;intro.sequence=1;
 OnBbscCutscenePacket(11,true,&intro,sizeof intro);OnBbscCutscenePacket(11,true,&intro,sizeof intro);
 assert(bbsc_cutscene_queue.size()==1);TickBbscCutsceneReplay();assert(requests==1);
 intro.sequence=2;OnBbscCutscenePacket(11,true,&intro,sizeof intro);TickBbscCutsceneReplay();assert(requests==1);
 int before_story=requests;flag=false;
 for (auto [scene,area]:{std::pair{32000000,0x20000000u},std::pair{24000030,0x18000000u}}) {
  map=area;intro.map=map;intro.cutscene=scene;intro.sequence=3;
  intro.variant=scene==32000000?5:4;
  auto& local=bbsc_world_presence_local;local.world={11,99};local.map=map;
  local.phase=World::Phase::Playing;local.sequence=1;local.visit=1;
  for(int role:{3,6}){
   state=role;auto& book=bbsc_world_presence_book;book.Clear();book.Bind(local.world,role==3?11:12);
   auto remote=local;remote.map=0x15000000;assert(book.Hear(13,local.world,remote,1));
   OnBbscCutscenePacket(13,false,&intro,sizeof intro);assert(bbsc_cutscene_queue.empty());
   remote.map=map;++remote.sequence;assert(book.Hear(13,local.world,remote,2));
   auto wrong= intro;wrong.variant=0;
   OnBbscCutscenePacket(13,false,&wrong,sizeof wrong);assert(bbsc_cutscene_queue.empty());
   OnBbscCutscenePacket(99,false,&intro,sizeof intro);assert(bbsc_cutscene_queue.empty());
   OnBbscCutscenePacket(13,false,&intro,sizeof intro);++bbsc_load_generation;
   int before=delegated;TickBbscCutsceneReplay();assert(delegated==before);
   OnBbscCutscenePacket(13,false,&intro,sizeof intro);TickBbscCutsceneReplay();assert(delegated==before+1);
   bbsc_cutscene_seen[scene]=bbsc_load_generation;
   OnBbscCutscenePacket(13,false,&intro,sizeof intro);TickBbscCutsceneReplay();assert(delegated==before+1);
   bbsc_cutscene_seen.clear();
  }
 }
 assert(bbsc_cutscene_queue.empty()&&requests==before_story&&delegated==4);map=0x15000000;
 // Dead host is not revived before the group's real victory. Native ending event
 // stays paused if actor/curtain recovery fails, then resumes before its movie.
 state=3;flag=false;assert(!GuardBbscSharedFinaleEvent(1));assert(revives==0);
 flag=true;assert(GuardBbscSharedFinaleEvent(1));revive_ok=true;
 assert(!GuardBbscSharedFinaleEvent(1));assert(hp==600&&!bbsc_spectate_active&&camera==2);
 event=12100002;hp=0;bbsc_spectate_active=true;assert(!GuardBbscSharedFinaleEvent(1));
 event=12100180;hp=0;bbsc_spectate_active=true;assert(!GuardBbscSharedFinaleEvent(1));
 // Old ending packets no longer start a separate guest finale. A journal
 // written by a previous version may still resume while offline.
 for(int scene:{21000010,21000020,21000030}){
 state=6;hp=0;bbsc_spectate_active=true;revive_ok=false;playing=false;
 bbsc_finale_record={};bbsc_dream_finale={};bbsc_dream_ng_pending=0;
 bbsc_cutscene_seen.clear();BbscCutscenePacket p{};p.map=map;p.cutscene=scene;p.reserved=2;
 p.sequence=static_cast<u32>(scene);OnBbscCutscenePacket(11,true,&p,sizeof p);int before=requests;
 assert(bbsc_cutscene_queue.empty()&&state==6);
 state=0;bbsc_finale_record={1,p};bbsc_cutscene_queue.push_back({p});
 TickBbscCutsceneReplay();assert(bbsc_cutscene_queue.size()==1&&bbsc_cutscene_seen.empty()&&requests==before);
 revive_ok=true;curtain=true;TickBbscCutsceneReplay();assert(requests==before);
 curtain=false;TickBbscCutsceneReplay();assert(hp==600&&requests==before+1&&bbsc_dream_finale.scene==scene);
 TickBbscDreamFinale();assert(!bbsc_dream_ng_pending); // request alone is not completion
 playing=true;TickBbscDreamFinale();assert(state==0);
 playing=false;TickBbscDreamFinale();assert(state==0&&bbsc_dream_ng_pending==scene);
 int save_before=saves;TickBbscDreamFinale();assert(saves==save_before); // own trip must drain
 bbsc_progress_was_guest=false;TickBbscDreamFinale();
 assert(saves==save_before+1&&mem[game_data+0x68]==2&&!bbsc_dream_ng_pending);
 assert(mem[10000+20+Bbsc::DreamFinale::EndingNumber(scene)]==1&&mem[10000+6604]==1);
 bbsc_finale_save_result=0;TickBbscDreamFinale();assert(bbsc_finale_record.phase==0);
 TickBbscDreamFinale();assert(saves==save_before+1);bbsc_progress_was_guest=true;
 }
 assert(stops==0);
}
'''
if os.environ.get('BBSC_TEST_SCENES_ONLY'):
    code=code.replace(' // Dead host is not revived before', ' return 0; // scene-dispatch-only regression\n // Dead host is not revived before')
with tempfile.TemporaryDirectory() as tmp:
    cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe';cpp.write_text(code)
    cxx='C:/msys64/clang64/bin/clang++.exe'
    subprocess.run([cxx,'-std=c++20','-I',str(root/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(cxx).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],check=True,env=env)
if os.environ.get('BBSC_TEST_SCENES_ONLY'):
    print('PASS: shared intro replay/dedup; local travel ignored; Rom and Amelia from a guest delegated to either role in the same place')
else:
    print('PASS: ending packets ignored in co-op; legacy offline journal recovery, Remo completion and single save acknowledgement')
