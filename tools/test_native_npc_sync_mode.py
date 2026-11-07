"""Execute production experiment installation, negotiation, tick and v1.2 rules.

No game process, settings or saves. Native hook installation is an observed stub:
the native branch installs only the retained-session player render admission.
"""
from pathlib import Path
import os, re, subprocess, tempfile
import test_independent_native as native
import test_world_native_bootstrap as bootstrap

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
def function(s,signature):
    a=s.index(signature+' {');b=s.index('{',a)+1;depth=1
    while depth:
        depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[a:b]+'\n'

install=native.function('void InstallBbscIndependentWorld()')
callbacks=sorted(set(re.findall(r'\},(Bbsc\w+),',install)))
prefix=native.PREFIX+r'''
#include <cstdio>
#include <cstring>
#include "core/bbsc_quest_event_rules.h"
#include "core/bbsc_world_blocks.h"
#include "core/bbsc_native_ai_admission.h"
void NativeAi::EmitReceiveChannels(Xbyak::CodeGenerator&,uint64_t,uint64_t){}
void NativeAi::EmitRequest(Xbyak::CodeGenerator&,uint64_t,uint64_t){}
void NativeAi::EmitEmptySelf(Xbyak::CodeGenerator&,uint64_t,uint64_t){}
void NativeAi::EmitEmptyPeer(Xbyak::CodeGenerator&,uint64_t,uint64_t){}
void NativeAi::EmitRequestMember(Xbyak::CodeGenerator&,uint64_t,uint64_t){}
void NativeAi::EmitRetainMember(Xbyak::CodeGenerator&,uint64_t,uint64_t){}
void NativeAi::EmitGrantMember(Xbyak::CodeGenerator&,uint64_t,uint64_t){}
u32 BbscWorldNpcRequestMember(u64,u32){return 0;}
u64 BbscWorldNpcGrantMember(u32){return 0;}
u64 BbscWorldNpcRetainMember(u32){return 0;}
std::vector<u64> rewrite_offsets,rewrite_callbacks;
namespace Core {using GuestCodeEmitter=void(*)(Xbyak::CodeGenerator&,u64,u64);
bool InstallGuestCodeRewrite(void* p,std::span<const u8>,
 void(*)(Xbyak::CodeGenerator&,u64,u64),u64 image,u64 callback){rewrite_offsets.push_back((u64)p-image);rewrite_callbacks.push_back(callback);return true;}}
namespace BbscMod{u32 RegisterOwnId(){return 11;}}
bool BbscCombatTraceEnabled(){return false;}
#define LOG_INFO(...)
#define LOG_ERROR(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
using GuestCodeHook=void(*)(u64,const GuestRegisterSnapshot*);
int hook_installs=0,travel_installs=0;bool hook_success=true;
std::vector<u64> hook_offsets;
bool InstallGuestCodeHook(void* p,std::span<const u8> bytes,u64,GuestCodeHook,const u8*=nullptr,bool resume=false,void*=nullptr);
u64 image_base=0;
bool InstallGuestCodeHook(void* p,std::span<const u8> bytes,u64,GuestCodeHook,const u8*,bool resume,void*){
 ++hook_installs;hook_offsets.push_back(reinterpret_cast<u64>(p)-image_base);
 assert((hook_offsets.back()==0x01E502C3&&bytes.size()==8&&resume)||
        (hook_offsets.back()==0x017894E0&&bytes.size()==6&&!resume)||
        (hook_offsets.back()==0x018BD488&&bytes.size()==7&&!resume)||
        (hook_offsets.back()==0x018ECCD4&&bytes.size()==5&&!resume));return hook_success;
}
u8 bbsc_world_player_render_skip=0,bbsc_world_hp_receive_skip=0,bbsc_world_hp_apply_enter=0,bbsc_world_hp_apply_skip=0;
void InstallBbscWorldTravel(){++travel_installs;bbsc_independent_travel_hooks=true;}
std::atomic<bool> bbsc_independent_active{false};
World::OwnerBook bbsc_independent_owners;
bool BbscQuitInProgress(){return false;}bool BbscReturningToTitle(){return false;}
int coordinates=0,altars=0,snapshots=0,blocks=0,lamps=0,travel=0,checkpoints=0,players=0,combat=0;
void BbscWorldCoordinate(){++coordinates;}void DiscardBbscWorldScenes(){}
void BbscWorldPublishOwner(u32 owner,u32 role,bool){bbsc_independent_owner=owner;bbsc_independent_role=role;}
void TickBbscWorldAltars(){++altars;}void TickBbscWorldSnapshots(){++snapshots;}
void TickBbscWorldBlocks(){++blocks;}void TickBbscWorldLamps(){++lamps;}
void TickBbscWorldTravel(){++travel;}void TickBbscSharedLampCheckpoint(){++checkpoints;}
void TickBbscWorldPlayers(){++players;}void TickBbscCombatTrace(){++combat;}
'''
prefix=prefix.replace('const u8*=','const u8* =').replace('void*=','void* =')
prefix+=''.join(f'void {name}(u64,const GuestRegisterSnapshot*){{}}\n' for name in callbacks)
prefix+='void BbscWorldNpcActivated(u64,const GuestRegisterSnapshot*){}\n'
prefix+='void BbscWorldAiTableCreated(u64,const GuestRegisterSnapshot*){}\n'
production=''.join(native.function(s) for s in [
    'u32 BbscIndependentCapabilities()', 'bool BbscWorldAllMembersReady()',
    'void TickBbscIndependentWorld()'])+install
production+=function(source,'bool IsBbscLocalQuestEvent(s64 event)')
main=r'''
int main(){
 const bool experiment=SessionTest::NativeNpcSync();
 if(experiment){
  std::vector<u8> image(0x2000000);image_base=reinterpret_cast<u64>(image.data());
  const u8 render[]={0x41,0x80,0xA7,0xE2,0x01,0x00,0x00,0xEF};
  const u8 prologue[]={0x55,0x48,0x89,0xE5,0x41,0x57};
  std::memcpy(image.data()+0x01E502C3,render,sizeof(render));
  const u8 activation[]={0xC7,0x40,0x10,0x04,0x00,0x00,0x00};
  std::memcpy(image.data()+0x018BD488,activation,sizeof(activation));
  const u8 table[]={0x4f,0x89,0x7c,0xee,0x10};std::memcpy(image.data()+0x018ECCD4,table,5);
  std::memcpy(image.data()+0x01789274,NativeAi::ReceiveChannels.data(),NativeAi::ReceiveChannels.size());
  std::memcpy(image.data()+0x01916A82,NativeAi::Request.data(),NativeAi::Request.size());
  std::memcpy(image.data()+0x018F0880,NativeAi::EmptySelf.data(),NativeAi::EmptySelf.size());
  std::memcpy(image.data()+0x018F09D1,NativeAi::EmptyPeer.data(),NativeAi::EmptyPeer.size());
  std::memcpy(image.data()+0x018F092C,NativeAi::RequestMember.data(),NativeAi::RequestMember.size());
  std::memcpy(image.data()+0x018ED1B6,NativeAi::RetainMember.data(),NativeAi::RetainMember.size());
  std::memcpy(image.data()+0x018ED470,NativeAi::GrantMember.data(),NativeAi::GrantMember.size());
  for(u64 offset:{0x018C6390ull,0x019186E0ull,0x018F4A50ull,0x015BC080ull,
                  0x017894E0ull,0x01786360ull,0x0190E8B0ull})
   std::memcpy(image.data()+offset,prologue,sizeof(prologue));
  bbsc_independent_hooks=false;bbsc_independent_travel_hooks=false;
  // Fail closed before publishing independent travel on mismatched native code.
  image[0x01E502C3]^=1;InstallBbscIndependentWorld();
  assert(!hook_installs&&!travel_installs);image[0x01E502C3]^=1;
  image[0x018BD488]^=1;InstallBbscIndependentWorld();
  assert(!hook_installs&&!travel_installs);image[0x018BD488]^=1;
  for(u64 offset:{0x01789274ull,0x01916A82ull,0x018F0880ull,0x018F09D1ull,0x018F092Cull,0x018ED1B6ull,0x018ED470ull}){
   image[offset]^=1;InstallBbscIndependentWorld();assert(!hook_installs&&!travel_installs);image[offset]^=1;
  }
  for(u64 offset:{0x018C6390ull,0x019186E0ull,0x018F4A50ull,0x015BC080ull,
                  0x017894E0ull,0x01786360ull,0x0190E8B0ull}){
   image[offset]^=1;InstallBbscIndependentWorld();assert(!hook_installs&&!travel_installs);image[offset]^=1;
  }
  hook_success=false;InstallBbscIndependentWorld();assert(hook_installs==1&&!travel_installs);
  hook_success=true;InstallBbscIndependentWorld();
  assert(travel_installs==1&&hook_installs==4&&!bbsc_independent_hooks);
  assert((rewrite_offsets==std::vector<u64>{0x01789274,0x01916A82,0x018F0880,0x018F09D1,0x018F092C,0x018ED1B6,0x018ED470}));
  assert((rewrite_callbacks==std::vector<u64>{0,0,0,0,(u64)BbscWorldNpcRequestMember,(u64)BbscWorldNpcRetainMember,(u64)BbscWorldNpcGrantMember}));
  assert((hook_offsets==std::vector<u64>{0x01E502C3,0x01E502C3,0x017894E0,0x018BD488}));
 }
 const u32 caps=BbscIndependentCapabilities();
 assert(caps&World::IndependentTravelCapability);
 assert(bool(caps&World::BlockCapability)==!experiment);
 assert(bool(caps&SessionTest::Capability)==experiment);
 auto& local=bbsc_world_presence_local;
 local.world={11,99};local.map=0x18010000;local.phase=World::Phase::Playing;
 local.visit=local.sequence=1;local.capabilities=caps;
 bbsc_world_presence_book.Bind(local.world,11);
 auto peer=local;assert(bbsc_world_presence_book.Hear(22,local.world,peer,SteadyNowMs()));
 assert(BbscWorldAllMembersReady());
 for(int i=0;i<2000;++i)TickBbscIndependentWorld();
 assert(altars==2000&&snapshots==2000&&lamps==2000&&travel==2000&&checkpoints==2000);
 assert(blocks==(experiment?0:2000)&&players==2000&&combat==(experiment?0:2000));
 // A peer with a different experiment cannot negotiate this travel mode.
 peer.sequence++;peer.capabilities^=SessionTest::Capability;
 assert(bbsc_world_presence_book.Hear(22,local.world,peer,SteadyNowMs()));
 assert(!BbscWorldAllMembersReady());
 for(s64 event:QuestRules::LocalEvents)
  assert(IsBbscLocalQuestEvent(event)==(!experiment||SessionTest::LocalQuest(event)));
 assert(IsBbscLocalQuestEvent(12400520)==!experiment);
 assert(IsBbscLocalQuestEvent(12400521));
 printf("PASS native NPC sync mode=%d: actual installation, 2000 ticks, lamps retained, no new NPC work, peer fence, v1.2 controllers\n",experiment);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-native-sync-test-') as tmp:
    folder=Path(tmp);cpp=folder/'fixture.cpp';exe=folder/'fixture.exe'
    compiler=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
    env=dict(os.environ,PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH',''))
    cpp.write_text(prefix+production+main,encoding='utf8')
    subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],env=env,check=True)
    for mode in ('0','1'):
        subprocess.run([str(exe)],env=dict(env,BBSC_NATIVE_NPC_SYNC_TEST=mode),check=True)
    default_env=dict(env);default_env.pop('BBSC_NATIVE_NPC_SYNC_TEST',None)
    subprocess.run([str(exe)],env=default_env,check=True)
    # Native NPC mode bypasses NPC admission, while mounted ritual flags must
    # still be installed before m29's one-shot lamp initialization.
    bootstrap_prefix=bootstrap.PREFIX.replace('u32 GetCurrentPackedMap(){return map;}',
        'int map_queries=0;u32 GetCurrentPackedMap(){++map_queries;return map;}')
    cpp.write_text(bootstrap_prefix+'World::Scope bbsc_world_bootstrap_scope{};u64 bbsc_world_bootstrap_load=0;s32 bbsc_world_bootstrap_session=0;\n'+''.join(bootstrap.function(s) for s in [
        'bool BbscWorldFlagsReady(const World::Scope& scope)',
        'void BbscWorldEnsureSeed(const World::Scope& scope)',
        'bool BbscWorldSceneReady()',
        'bool BbscWorldNativePeerReady(u32 owner)',
        'bool GuardBbscWorldBootstrap(u64 instance)'])+r'''
int main(){blocks_active=true;blocks_ready=false;npc_ready=false;
 for(int i=0;i<2000;++i)assert(!GuardBbscWorldBootstrap(1));
 assert(!sent&&!applied&&BbscWorldSceneReady()&&map_queries==2);
 for(int role:{3,6}){
  session=role;map=0x1d0a5a00;++bbsc_world_native_load;
  World::Presence p;p.world={11,99};p.map=map;p.phase=World::Phase::Playing;
  auto& altar=bbsc_world_altars[1];altar.entry.occupied=true;
  altar.entry.ritual=18;altar.mount.key={55,66,88,0};
  p.dungeon=altar.mount.key;p.ritual=18;bbsc_world_presence_local=p;
  const auto cup=World::ScopeOf(p);self=22; // no local seed can hide a missing snapshot
  bbsc_independent_states.clear();native_event=12907010;
  const int before=applied;assert(GuardBbscWorldBootstrap(1)&&applied==before);
  bbsc_independent_states[cup]={0,1,0,true};
  assert(GuardBbscWorldBootstrap(1)&&applied==before);
  bbsc_independent_states[cup]={0,1,0x3FF,true};
  assert(!GuardBbscWorldBootstrap(1)&&applied==before+1);
  // Unready NPC/block state cannot trap lamps; a running cup is never rewound.
  const int queries=map_queries;
  for(int i=0;i<2000;++i)assert(!GuardBbscWorldBootstrap(1));
  assert(applied==before+1&&map_queries==queries);
  native_event=12907020;bbsc_world_requested_scope=World::Scope{p.world,BbscDreamStateMap,{},0};
  assert(!GuardBbscWorldBootstrap(1)&&applied==before+1);
  bbsc_world_requested_scope.reset();
 }
 assert(!dream_calls&&!altar_calls);
 puts("PASS native mode: ordinary fast exit, cup flags before lamp initialization, both roles, no NPC admission or per-step replay");}
''',encoding='utf8')
    subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],env=env,check=True)
    subprocess.run([str(exe)],env=dict(env,BBSC_NATIVE_NPC_SYNC_TEST='1'),check=True)
