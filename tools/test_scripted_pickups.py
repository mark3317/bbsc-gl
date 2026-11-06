"""Production pickup role gates, personal completion masks and native event localization.

Fake memory only; no game, settings or player saves are opened.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')


def function(signature):
    begin = SOURCE.index(signature + ' {')
    end = SOURCE.index('{', begin) + 1
    depth = 1
    while depth:
        depth += (SOURCE[end] == '{') - (SOURCE[end] == '}')
        end += 1
    return SOURCE[begin:end] + '\n'


def declaration(pattern):
    return re.search(pattern, SOURCE, re.S).group() + '\n'


code = r'''
#include "core/bbsc_quest_event_rules.h"
namespace QuestRules=Core::Bloodborne::QuestRules;
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>
#include <map>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>
using u8=uint8_t;using s8=int8_t;using u32=uint32_t;using s32=int32_t;
using u64=uint64_t;using s64=int64_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...)
#define LOG_ERROR(...)
#define BBSC_TIMELINE(...)
#define BBSC_PERF_SCOPE(...)
#define BBSC_PERF_NESTED(...)
struct GuestRegisterSnapshot {u64 rdi=0,rdx=0;};
u64 image_base=0;u32 current_map=0;bool guest=true,writable=true;
s64 event_id=0;
u32 GetCurrentPackedMap(){return current_map;}
bool BbscGuestInHostWorld(){return guest;}
bool BbscResearchEnabled(){return false;}
namespace Chalice{bool IsMap(u32 m){return (m>>24)==29;}}
bool BbscDreamOwnEnabled(){return false;}

bool ReadablePointer(u64 p,size_t){return p!=0;}
enum class MemoryProt {CpuRead,CpuWrite};
bool HasMemoryAccess(u64 p,size_t,MemoryProt m){return p && (m==MemoryProt::CpuRead || writable);}
template<class T>T ReadValue(u64 p,size_t off){T value;memcpy(&value,(void*)(p+off),sizeof(value));return value;}
template<class T>void WriteValue(u64 p,size_t off,T value){assert(writable);memcpy((void*)(p+off),&value,sizeof(value));}
s64 BbscEventIdOf(u64){return event_id;}
void NoteBbscBossRewardEvent(s64){}
std::mutex bbsc_npc_own_mutex;
std::unordered_map<u32,u8> bbsc_npc_own;
bool bbsc_npc_own_active=true;
u8 bbsc_dream_type_skip=0;
std::array<u64,64> bbsc_dream_type_conditions{};
size_t bbsc_dream_type_next=0;
std::vector<s64> bbsc_dream_type_logged;
constexpr std::array<s64,0> BbscDreamGuestEvents{},BbscDreamOwnGuestEvents{};
enum class BbscLedgerSource {Award,Key};enum class BbscLedgerState {Given};
struct BbscLedgerEntry {BbscLedgerSource source;BbscLedgerState state;int retry;s32 lot;u32 flag,code;s32 count;s64 at,check;};
std::mutex bbsc_ledger_mutex;std::vector<BbscLedgerEntry> bbsc_ledger;
std::map<u32,s32> bbsc_ledger_trip,bbsc_ledger_host_counts;
bool bbsc_ledger_dirty=false;
s32 BbscLedgerCount(u32){return 1;}
bool BbscLedgerAddable(u32){return true;}bool BbscLedgerWatched(u32){return true;}
s64 SteadyNowMs(){return 10000;}
void WriteBbscLedgerLocked(){}
void RecordBbscNativeItemFlag(u32,u8){}
std::vector<std::pair<u32,u8>> journal;
void NoteBbscTalkFlag(u32 flag,u8 value,u64,bool){journal.emplace_back(flag,value);}
'''
code += declaration(r'constexpr std::array<s64, \d+> BbscGuestGiftEvents\{.*?\};')
code += declaration(r'constexpr std::array<u32, \d+> BbscNpcQuestFlags\{.*?\n\};')
code += declaration(r'struct BbscScriptedPickup \{.*?\};')
code += declaration(r'constexpr std::array<BbscScriptedPickup, \d+> BbscScriptedPickups\{\{.*?\}\};')
code += declaration(r'constexpr std::array<s64, 3> BbscGuestKnockEvents\{.*?\};')
for signature in [
    'bool IsBbscChaliceBossRewardEvent(s64 event)',
    'bool IsBbscGlobalLootReceipt(u32 flag)',
    'bool IsBbscLocalQuestEvent(s64 event)',
    'bool IsBbscNpcQuestFlag(u32 flag)',
    'bool IsBbscScriptedPickupFlag(u32 flag)',
    'bool IsBbscKidnapFlag(u32 flag)',
                  'bool IsBbscNativeItemStateFlag(u32 flag)',
    'void NoteBbscNpcOwnFlag(u32 flag, u8 value)',
    'void KeepBbscNpcOwnBits(u32 key, const u8* before, u8* live)',
    'bool IsBbscKidnapEvent(s64 event)',
    'bool IsBbscPersonalMapEvent(s64 event)',
    'void EnableBbscScriptedPickupEvent(u64 instance)',
    'void PS4_SYSV_ABI BbscDreamTypeCheckHook(u64 /*tag*/, const GuestRegisterSnapshot* registers)',
    'void NoteBbscLedgerGiven(BbscLedgerSource source, s32 lot, u32 flag, u32 code, s32 count)',
]:
    code += function(signature)
start = SOURCE.index('struct BbscQuestRange {')
end = SOURCE.index('void LocalizeBbscQuestEvent(u64 instance) {', start)
code += SOURCE[start:end]
code += function('void LocalizeBbscQuestEvent(u64 instance)')
code += r'''
int main(){
 assert(std::ranges::is_sorted(BbscScriptedPickups,{},&BbscScriptedPickup::event));
 assert(std::ranges::is_sorted(BbscNpcQuestFlags));
 assert(std::adjacent_find(BbscNpcQuestFlags.begin(),BbscNpcQuestFlags.end())==BbscNpcQuestFlags.end());
 alignas(16) unsigned char instance[0xc0]{},file[0x400]{},ref[0x10]{},condition[0x30]{};
 u64 inst=(u64)instance;
 WriteValue<u64>((u64)ref,8,(u64)file);
 WriteValue<u64>(inst,0xa8,(u64)ref);
 WriteValue<u64>((u64)file,0x10,1);WriteValue<u64>((u64)file,0x18,0xa0);
 WriteValue<u64>((u64)file,0x28,0x100);WriteValue<u64>((u64)file,0x78,0x300);
 WriteValue<u64>(inst,0xb0,(u64)file+0x100);
 WriteValue<u64>((u64)file,0xa8,3);WriteValue<u64>((u64)file,0xb0,0);
 WriteValue<s32>((u64)condition,0x28,10000);
 GuestRegisterSnapshot regs{(u64)condition,inst};
 for(const auto& rule:BbscScriptedPickups){
  event_id=rule.event;current_map=rule.map;
  assert(IsBbscPersonalMapEvent(event_id)&&IsBbscNpcQuestFlag((u32)event_id));
  // Every pickup's host-type condition now works for a guest, even on later evaluations.
  guest=true;WriteValue<s8>((u64)condition,0x2c,0);condition[0x10]=0;
  bbsc_dream_type_skip=0;BbscDreamTypeCheckHook(0,&regs);
  assert(bbsc_dream_type_skip==1&&(condition[0x10]&1));
  guest=false;condition[0x10]=0;bbsc_dream_type_skip=0;BbscDreamTypeCheckHook(0,&regs);
  assert(bbsc_dream_type_skip==0&&condition[0x10]==0);guest=true;
  // Per-player completion: another player's pickup cannot take ours away.
  u32 flag=(u32)event_id,bit=flag%1000;u8 mask=0x80u>>(bit%8);
  for(int player=0;player<3;++player){
   bbsc_npc_own.clear();std::array<u8,125> before{},live{};
   live[bit/8]=mask;KeepBbscNpcOwnBits(flag/1000,before.data(),live.data());
   assert((live[bit/8]&mask)==0);
   bbsc_npc_own[flag]=0; // stale NPC cache must not override native local completion
   NoteBbscNpcOwnFlag(flag,1);before[bit/8]=mask;live.fill(0);
   KeepBbscNpcOwnBits(flag/1000,before.data(),live.data());assert(live[bit/8]&mask);
   // Rejoin with already completed local flag: keep it; do not reset for another host.
   bbsc_npc_own.clear();before[bit/8]=mask;live.fill(0);
   KeepBbscNpcOwnBits(flag/1000,before.data(),live.data());assert(live[bit/8]&mask);
  }
  // Native network-sync suppression starts before the first condition on host AND guest.
  bbsc_quest_indexes.clear();bbsc_quest_instances.clear(); // native load-generation reset
  WriteValue<s64>((u64)file,0xa0,event_id);
  for(u64 offset:{0x100ull,0x120ull,0x140ull}){
   WriteValue<u64>(inst,0xb0,(u64)file+offset);instance[0x78]=1;
   LocalizeBbscQuestEvent(inst);assert(instance[0x78]==0);
  }
  // Only reviewed EndIfClient is replaced. The rest of the event stays native.
  WriteValue<u64>(inst,0xb0,(u64)file+0x100);
  auto reset_gate=[&](){
   WriteValue<s32>((u64)file,0x100,1003);WriteValue<s32>((u64)file,0x104,6);
   WriteValue<u64>((u64)file,0x108,4);WriteValue<u64>((u64)file,0x110,0);
   WriteValue<u32>((u64)file,0x300,256);instance[0x78]=1;
  };
  reset_gate();current_map^=0x10000;EnableBbscScriptedPickupEvent(inst);
  assert(ReadValue<u32>((u64)file,0x300)==256);current_map=rule.map;
  writable=false;EnableBbscScriptedPickupEvent(inst);writable=true;
  assert(ReadValue<u32>((u64)file,0x300)==256);
  WriteValue<u32>((u64)file,0x300,257);EnableBbscScriptedPickupEvent(inst);
  assert(ReadValue<u32>((u64)file,0x300)==257);
  // Parameterized reward has a verified constant role gate; other
  // parameterized event instances remain blocked.
  reset_gate();WriteValue<u64>(inst,0xb8,1);EnableBbscScriptedPickupEvent(inst);
  assert((ReadValue<s32>((u64)file,0x100)==1001)==(rule.event==13400995));
  WriteValue<u64>(inst,0xb8,0);
  reset_gate();EnableBbscScriptedPickupEvent(inst);
  if(rule.client_gate){
   assert(ReadValue<u32>((u64)file,0x300)==0);
   assert(ReadValue<s32>((u64)file,0x100)==1001&&ReadValue<s32>((u64)file,0x104)==1);
   assert(instance[0x78]==0);EnableBbscScriptedPickupEvent(inst);
  }else assert(ReadValue<u32>((u64)file,0x300)==256);
 }
 // Standalone Orphanage Key, Balcony Key and Cainhurst covenant gift:
 // the production host-role gate permits each guest's own original event.
 for(s64 reward:{12420700,13501920,9040,12400780,12700500}){
  event_id=reward;guest=true;WriteValue<s8>((u64)condition,0x2c,0);
  bbsc_dream_type_skip=0;condition[0x10]=0;BbscDreamTypeCheckHook(0,&regs);
  assert(bbsc_dream_type_skip==1&&(condition[0x10]&1));
 }
 // Personal NPC workers must also run locally before the FIRST condition.
 // Otherwise host-synchronized actions bypass the guest's death predicate.
 for(s64 worker:QuestRules::LocalEvents){
  bbsc_quest_indexes.clear();bbsc_quest_instances.clear();
  event_id=worker;WriteValue<s64>((u64)file,0xa0,worker);
  for(u64 offset:{0x100ull,0x120ull,0x140ull}){
   WriteValue<u64>(inst,0xb0,(u64)file+offset);instance[0x78]=1;
   LocalizeBbscQuestEvent(inst);assert(instance[0x78]==0);
  }
 }
 for(s64 worker:{12410761,12410803,12410804})assert(IsBbscLocalQuestEvent(worker));
 for(s64 worker:{9421,9422,12400780,12700500}){
  bbsc_quest_indexes.clear();bbsc_quest_instances.clear();
  event_id=worker;WriteValue<s64>((u64)file,0xa0,worker);
  for(u64 offset:{0x100ull,0x120ull,0x140ull}){
   WriteValue<u64>(inst,0xb0,(u64)file+offset);instance[0x78]=1;
   LocalizeBbscQuestEvent(inst);assert(instance[0x78]==0);
  }
 }
 // Eye Pendant receipt and Cainhurst placement checkpoint must be personal too.
 assert(IsBbscNpcQuestFlag(9470)&&IsBbscNpcQuestFlag(12410511));
 // Unknown/complex world event and a reused instance never inherit pickup permission.
 event_id=12500810;assert(!IsBbscPersonalMapEvent(event_id));
 WriteValue<s64>((u64)file,0xa0,event_id);instance[0x78]=1;
 LocalizeBbscQuestEvent(inst);assert(instance[0x78]==1);
 bbsc_dream_type_conditions.fill(0);bbsc_dream_type_skip=0;condition[0x10]=0;
 BbscDreamTypeCheckHook(0,&regs);assert(!bbsc_dream_type_skip&&condition[0x10]==0);
 // Eye Pendant direct native receipt follows only a positive, matching item delivery.
 image_base=1;guest=true;
 auto given=[&](s32 lot,u32 flag,u32 code,s32 count){NoteBbscLedgerGiven(BbscLedgerSource::Award,lot,flag,code,count);};
 given(3401810,9470,0x40000000u|4017u,1);assert(journal.size()==1&&journal.back().first==9470&&journal.back().second==1);
 given(3401810,9470,0x40000000u|4017u,0);
 given(3401811,9470,0x40000000u|4017u,1);
 given(3401810,9471,0x40000000u|4017u,1);
 given(3401810,9470,0x40000000u|4018u,1);
 guest=false;given(3401810,9470,0x40000000u|4017u,1);assert(journal.size()==1);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-scripted-pickups-') as temporary:
    folder = Path(temporary)
    cpp, exe = folder / 'fixture.cpp', folder / 'fixture.exe'
    cpp.write_text(code, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler, '-std=c++20', '-I', str(ROOT / 'emulator/src'), str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], check=True, env=env, timeout=10)
print('PASS: 12 production pickup/reward gates, three personal completion views, rejoin, native localization and negative paths')
