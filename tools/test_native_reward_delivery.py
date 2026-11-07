"""Production native reward routing, boss tickets and original read-only lots.

BB_GAME=dvdroot_ps4 python -B tools/test_native_reward_delivery.py
Native award entry uses the real trampoline; downstream game engine is a stub.
No real inventory, saves, processes or settings are modified.
"""
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
sys.path.insert(0, str(ROOT / 'tools/gamedata'))
import bbfiles
import param
from scripted_pickups import REVIEWED


def function(signature):
    a = source.index(signature + ' {')
    b = source.index('{', a) + 1
    depth = 1
    while depth:
        depth += (source[b] == '{') - (source[b] == '}')
        b += 1
    return source[a:b] + '\n'


def declaration(pattern):
    return re.search(pattern, source, re.S).group() + '\n'


scripted = set(map(int, re.findall(r'\b\d+\b', re.search(
    r'BbscNativeScriptedLots\{(.*?)\};', source, re.S)[1])))
assert scripted == {entry[1] for entry in REVIEWED.values()} | {43800, 43802}
bosses = [tuple(map(int, x)) for x in re.findall(r'\{(\d+), (\d+), (\d+), (\d+)\}',
          re.search(r'BbscBossRewards\{\{(.*?)\}\};', source, re.S)[1])]
cup_lots = set(map(int,re.findall(r'\{\d+, (\d+)\}', re.search(r'BbscUniqueChaliceRewards\{\{(.*?)\}\};',source,re.S)[1])))
native_lots = cup_lots | scripted | {lot for _, _, first, repeat in bosses for lot in (first, repeat) if lot}
bbfiles.GAME = os.environ['BB_GAME']
_, _, data, rows = param.load('ItemLotParam')
vermin_lots = {5900, 5920, 5930}
assert 'GiveBbscBossGoods' not in source and 'BbscBossGoodsLots' not in source
for legacy in ('NoteBbscBossRewardEvent', 'TickBbscBossRewards', 'bbsc_boss_reward_queue'):
    assert legacy not in source, legacy

code = r'''
#include <windows.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <map>
#include <mutex>
#include <optional>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>
#include "core/cpu_patches.h"
using Core::GuestRegisterSnapshot;using Core::InstallGuestCodeHook;
using s64=int64_t;using s32=int32_t;using u32=uint32_t;using u16=uint16_t;
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
#define BBSC_PERF_SCOPE(...)
u64 image_base=0;
namespace BbscMod{u64 EbootAddress(){return image_base;}void LogPlain(const char*){}}
bool guest=true,ours=true,prerequisite=true,fail=false,empty=false;
bool legacy_skip=false,bbsc_popup_hook_ready=true,bbsc_guest_award_active=false;
bool bbsc_native_boss_award=false,bbsc_ledger_drop_award=false;
namespace Chalice{bool IsMap(u32 m){return (m>>24)==29;}}
struct Ticket{std::array<s64,4> award{};};std::optional<Ticket> bbsc_chalice_reward_context;
bool chalice_ticket=true,chalice_claimed=false;s64 current_event=12300130;
bool IsBbscChaliceBossRewardEvent(s64 e){return e==12901693;}
std::optional<Ticket> BbscCurrentChaliceRewardTicket(s32){return chalice_ticket?std::optional<Ticket>{Ticket{}}:std::nullopt;}
bool BbscChaliceRewardClaimed(const Ticket&){return chalice_claimed;}
bool BbscBossRewardPersistentItem(u64){return true;}
s32 BbscLedgerCount(u32){return 0;}
void NoteBbscChaliceReward(const Ticket&){}
u32 bbsc_native_pickup_flag=0;
u8 bbsc_award_skip=0;u32 map=0x18010000;int manual=0,native_calls=0,skip_checks=0;
std::map<s32,std::array<u8,0x94>> lots;
std::map<u32,int> inventory;std::set<u32> flags;
std::mutex bbsc_ledger_mutex;
std::unordered_map<u32,s64> bbsc_ledger_own_flags;
enum class BbscLedgerSource{Award,Drop,Boss};
struct BbscLedgerContext{BbscLedgerSource source;s32 lot;u32 flag;u32 gives;bool check;};
std::optional<BbscLedgerContext> bbsc_ledger_context;
template<class T>T ReadValue(u64 p,size_t off){T v;memcpy(&v,(void*)(p+off),sizeof(v));return v;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
bool EnvFlagEnabled(const char*){return true;}
bool BbscGuestInHostWorld(){return guest;}
bool BbscItemPopupEnabled(){return true;}
bool BbscEventActionNotOurs(u64){return !ours;}
s64 BbscCurrentEventRunId(){return current_event;}
bool BbscNpcReceiptAllowed(u32){return prerequisite;}
u64 BbscLedgerLotRow(s32 lot){return lots.contains(lot)?(u64)lots.at(lot).data():0;}
std::vector<u32> BbscLotFlags(u64 row){
 std::vector<u32> out;
 for(int i=0;i<9;++i){s32 f=ReadValue<s32>(row,i<8?0x60+4*i:0x80);if(f>0)out.push_back(f);}return out;
}
u32 BbscLotMainFlag(u64 row){auto f=BbscLotFlags(row);return f.empty()?0:f.front();}
bool IsBbscNpcQuestFlag(u32 f){return f==9470||f==6671||f==6673||f==6674;}
s64 SteadyNowMs(){return 1000;}
bool BbscIsNativeKitLot(u64 row){return row==0x1000;}
void SetBbscLedgerFlag(u32 f,u8 on){if(on)flags.insert(f);else flags.erase(f);}
bool SkipBbscRepeatedLot(s32,u64){++skip_checks;return legacy_skip;}
bool BbscLotHasGem(u64){return false;}bool BbscLotIsSure(u64){return true;}
bool BbscEventFlag(u32 f){return flags.contains(f);}
bool bbsc_ledger_picked_award=false;
void GiveBbscGuestDrop(s32,u32){++manual;}
u32 GetCurrentPackedMap(){return map;}
constexpr u64 AwardItemLotOffset=0x17ddc50;
''' + declaration(r'struct BbscBossReward \{.*?\};')
code += declaration(r'constexpr std::array<BbscBossReward, 19> BbscBossRewards\{\{.*?\}\};')
code += declaration(r'struct BbscUniqueChaliceReward \{.*?\};')
code += declaration(r'constexpr std::array<BbscUniqueChaliceReward, 17> BbscUniqueChaliceRewards\{\{.*?\}\};')
code += declaration(r'constexpr std::array<s32, 13> BbscNativeScriptedLots\{.*?\};')
for signature in ('bool IsBbscNativeRewardLot(s32 lot)',
                  'void BeginBbscLedgerAward(s32 lot, u64 row)',
                  'void FinishBbscLedgerContext()',
                  'void PS4_SYSV_ABI BbscGuestAwardHook(u64 /*tag*/, const GuestRegisterSnapshot* registers)'):
    code += function(signature)
code += r'''
// Stub behind the hooked native entry: deterministic original lot data, no
// fallback or scheduling. The routing test proves the engine is called once;
// the actual engine's random roll/storage implementation is not simulated.
void PS4_SYSV_ABI NativeAward(u64,s32 lot,u32 host_only){
 assert(!guest||host_only==0);++native_calls;
 assert(bbsc_ledger_context&&bbsc_ledger_context->lot==lot&&!bbsc_ledger_context->check);
 if(fail||empty)return;
 auto row=BbscLedgerLotRow(lot);
 for(int i=0;i<8;++i){
  s32 id=ReadValue<s32>(row,4*i);u32 cat=ReadValue<u32>(row,0x20+4*i);
  if(id>0&&cat!=0xffffffffu&&ReadValue<u16>(row,0x40+2*i)>0){
   u32 code=(cat<<28)|id;inventory[code]+=ReadValue<u8>(row,0x8a+i);
   ++bbsc_ledger_context->gives;break;
  }
 }
 for(u32 f:BbscLotFlags(row))flags.insert(f);
}
void reset(){
 manual=native_calls=skip_checks=0;inventory.clear();flags.clear();
 bbsc_ledger_context.reset();
 bbsc_ledger_own_flags.clear();guest=ours=prerequisite=true;fail=empty=false;
 bbsc_native_boss_award=false;bbsc_award_skip=0;legacy_skip=true;current_event=12300130;chalice_ticket=true;chalice_claimed=false;
 map=0x18010000;
}
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image_base);
'''
for lot in sorted(native_lots | vermin_lots):
    raw = data[rows[lot]:rows[lot] + 0x94]
    code += f'lots[{lot}]={{{",".join(map(str,raw))}}};\n'
code += r'''
 // Native entry has the same byte-verified prologue as the actual award.
 const u8 body[]={0x55,0x48,0x89,0xe5,0x41,0x57,0x48,0x83,0xec,8,
                  0x48,0xb8,0,0,0,0,0,0,0,0,0xff,0xd0,0x48,0x83,0xc4,8,0x41,0x5f,0x5d,0xc3};
 memcpy((void*)(image_base+AwardItemLotOffset),body,sizeof(body));
 u64 target=(u64)NativeAward;memcpy((void*)(image_base+AwardItemLotOffset+12),&target,8);
 assert(InstallGuestCodeHook((void*)(image_base+AwardItemLotOffset),std::span<const u8>{body,6},0,BbscGuestAwardHook,&bbsc_award_skip));
 using Award=void PS4_SYSV_ABI (*)(u64,s32,u32);auto award=(Award)(image_base+AwardItemLotOffset);
 for(auto& [lot,row]:lots){
  if(lot==5900||lot==5920||lot==5930)continue; // tested through BlockClear2 below
  reset();award(1,lot,1);assert(native_calls==1&&manual==0&&skip_checks==0&&!inventory.empty());
  FinishBbscLedgerContext();assert(manual==0);
  for(bool no_result:{false,true}){
   reset();fail=!no_result;empty=no_result;award(1,lot,0);FinishBbscLedgerContext();
   assert(native_calls==1&&manual==0&&inventory.empty()); // no reroll on empty/full result
  }
  reset();ours=false;award(1,lot,0);assert(native_calls==0&&manual==0);
  reset();prerequisite=false;award(1,lot,0);assert(native_calls==0&&manual==0);
  reset();guest=false;award(1,lot,0);assert(native_calls==1&&manual==0&&skip_checks==0);
 }
 // Personal receipt marking survives native delivery without a manual add.
 reset();award(1,43800,0);assert(bbsc_ledger_own_flags.contains(6671));
 // A direct legitimate native call is not suppressed just because a local
 // inventory history contains the item. Event completion owns its repetition.
 award(1,43800,0);assert(native_calls==2&&skip_checks==0&&manual==0);
 const u8 chalice_call[]={0x55,0x48,0x89,0xe5,0x41,0x57,0x48,0x83,0xec,8,0x90,0x90,0x90,0x90,
  0xe8,0x45,0xc4,0x01,0x00,0x48,0x83,0xc4,8,0x41,0x5f,0x5d,0xc3};
 memcpy((void*)(image_base+0x17c17f8),chalice_call,sizeof(chalice_call));
 auto chalice_award=(Award)(image_base+0x17c17f8);
 // m29 parameterized lots use native Award even though absent from the base-game whitelist.
 lots[999998]=lots.at(43800);
 for(bool command36:{false,true}){
  reset();map=0x1d000000;current_event=12901693;
  chalice_award(1,999998,command36?0:1);assert(native_calls==1&&manual==0&&skip_checks==0&&bbsc_chalice_reward_context);
  FinishBbscLedgerContext();assert(!bbsc_chalice_reward_context);
  chalice_claimed=true;chalice_award(1,999998,1);assert(native_calls==1&&manual==0);
  chalice_claimed=false;chalice_ticket=false;chalice_award(1,999998,1);assert(native_calls==1&&manual==0);
  guest=false;chalice_award(1,999998,1);assert(native_calls==2&&manual==0);
 }
 assert(!IsBbscNativeRewardLot(0)&&!IsBbscNativeRewardLot(999999));
 // Unrelated NPC gifts retain their existing guards/backend.
 lots[999999]=lots.at(43800);reset();award(1,999999,0);
 assert(skip_checks==1&&native_calls==0&&manual==0);
 reset();legacy_skip=false;award(1,999999,0);
 assert(skip_checks==1&&native_calls==0&&manual==1);

 // Use the original BlockClear2 call site and the native one-item lots.
 u8 block_clear_call[sizeof(chalice_call)];
 memcpy(block_clear_call,chalice_call,sizeof(block_clear_call));
 const s32 displacement=AwardItemLotOffset-0x0138515B;
 memcpy(block_clear_call+15,&displacement,sizeof(displacement));
 memcpy((void*)(image_base+0x01385148),block_clear_call,sizeof(block_clear_call));
 auto block_clear_award=(Award)(image_base+0x01385148);
 for(s32 lot:{5900,5920,5930}){
  reset();map=0x1d000000;
  block_clear_award(1,lot,0);FinishBbscLedgerContext();
  assert(native_calls==1&&manual==0&&skip_checks==0&&inventory.at(0x400006A4)==1);
  block_clear_award(1,lot,0);FinishBbscLedgerContext();
  assert(native_calls==2&&manual==0&&skip_checks==0&&inventory.at(0x400006A4)==2);
  reset();map=0x1d000000;legacy_skip=false;fail=true;
  block_clear_award(1,lot,0);FinishBbscLedgerContext();
  assert(native_calls==1&&manual==0&&skip_checks==0&&inventory.empty());
 }
 reset();legacy_skip=false;block_clear_award(1,5900,0);
 assert(native_calls==0&&manual==1&&skip_checks==1); // outside the Chalice
 reset();map=0x1d000000;legacy_skip=false;award(1,5900,0);
 assert(native_calls==0&&manual==1&&skip_checks==1); // different caller
 reset();map=0x1d000000;legacy_skip=false;guest=false;block_clear_award(1,5900,0);
 assert(native_calls==1&&manual==0&&skip_checks==1); // host's original routing
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-native-rewards-') as folder:
    cpp, exe = Path(folder) / 'fixture.cpp', Path(folder) / 'fixture.exe'
    cpp.write_text(code, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler, '-std=c++20', '-O0', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
                    '-I', str(ROOT / 'emulator/src'), '-I', str(ROOT / 'emulator/externals/xbyak'),
                    str(cpp), str(ROOT / 'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], env=env, check=True, timeout=15)
print(f"PASS: {len(native_lots)} original native lots; 12 scripted sources; 19 boss events' first/repeat lots; "
      'guest Vermin in m29; personal guards; no manual add/K3 duplicate gate/reroll fallback; actual award trampoline')
