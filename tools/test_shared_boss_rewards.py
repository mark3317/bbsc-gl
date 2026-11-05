"""Production shared-victory reconciliation with original EMEVD/PARAM data.

Only synthetic memory/files; no real saves, inventory or running games changed.
BB_GAME=dvdroot_ps4 python -B tools/test_shared_boss_rewards.py
"""
from pathlib import Path
import os
import re
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
s = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
sys.path.insert(0, str(ROOT / 'tools/gamedata'))
import bbfiles
import emevd
import param


def fun(signature):
    start = s.index(signature + ' {')
    end = s.index('{', start) + 1
    depth = 1
    while depth:
        depth += (s[end] == '{') - (s[end] == '}')
        end += 1
    return s[start:end] + '\n'


def decl(pattern):
    return re.search(pattern, s, re.S).group() + '\n'


bosses = [tuple(map(int, row)) for row in re.findall(
    r'\{(\d+), (\d+), (\d+), (\d+)\}',
    re.search(r'BbscBossRewards\{\{(.*?)\}\};', s, re.S)[1])]
defeats = list(map(int, re.findall(r'\d+', re.search(
    r'BbscBossRewardDefeats\{(.*?)\};', s, re.S)[1])))
assert len(defeats) == len(bosses) == 19
bbfiles.GAME = os.environ['BB_GAME']
_, _, data, rows = param.load('ItemLotParam')
_, _, goods_data, goods_rows = param.load('EquipParamGoods')
for (event, _, first, _), defeat in zip(bosses, defeats):
    name = f'm{event // 100000 % 100:02d}_{event // 10000 % 10:02d}_00_00'
    instructions = dict(emevd.Emevd(f'{bbfiles.GAME}/event/{name}.emevd.dcx').events)[event]
    assert any((b, i) == (2003, 4) and struct.unpack_from('<i', a)[0] == first
               for b, i, a in instructions)
    if defeat:
        assert any((b, i) == (2003, 2) and struct.unpack_from('<I', a)[0] == defeat
                   and a[4] == 1 for b, i, a in instructions), (event, defeat)
    raw = data[rows[first]:rows[first] + 0x94]
    entries = [(struct.unpack_from('<i', raw, 4*i)[0],
                struct.unpack_from('<I', raw, 0x20+4*i)[0])
               for i in range(8) if struct.unpack_from('<H', raw, 0x40+2*i)[0]]
    assert len(entries) == 1 and entries[0][0] > 0 and entries[0][1] != 0xffffffff
    assert first + 1 not in rows, 'Review native multi-row award before enabling reconciliation'

code = r'''
#include <windows.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <mutex>
#include <optional>
#include <set>
#include <string_view>
#include <vector>
#include "core/cpu_patches.h"
using s64=int64_t;using s32=int32_t;using u32=uint32_t;using u16=uint16_t;
#define BBSC_TIMELINE(...)
#define LOG_INFO(...)
#define BBSC_PERF_NESTED(...)
constexpr size_t BbscWorldGroupBytes=125;
constexpr u64 ItemManPointerOffset=0x553d6e0,AwardItemLotOffset=0x17ddc50;
u64 image_base=0;std::array<u8,16> global{};
std::mutex bbsc_ledger_mutex,bbsc_boss_reward_mutex;
std::vector<s64> bbsc_boss_reward_given,bbsc_boss_reward_queue;
struct Slot{int user=1,slot=0;};using BbscSaveSlot=Slot;
std::atomic<u32> bbsc_native_loot_receipt_revision{0};std::optional<s32> bbsc_ledger_loot_cycle;std::optional<Slot> bbsc_ledger_slot=Slot{};Slot active;
std::optional<Slot> BbscActiveSaveSlot(){return active;}
void SyncBbscLedgerSlot(){}
bool bbsc_native_boss_award=false,bbsc_ledger_dirty=false,bbsc_ledger_home_ready=true;
u32 bbsc_ledger_home_generation=1;std::atomic<u32> bbsc_load_generation{1};
bool fail=false,write_ok=true,fake_window=false;int calls=0,writes=0;
std::map<s32,u32> bbsc_ledger_lots;
std::map<s32,std::array<u8,0x94>> lots;
std::map<u32,std::array<u8,0x40>> goods;
u64 BbscGameParamTable(const char*){return 1;}
u64 BbscParamRow(u64,u32 id,size_t){return goods.contains(id)?(u64)goods.at(id).data():0;}
void SetBbscLedgerFlag(u32 f,u8 v);
bool guest=false,guest_ready=true;bool BbscGuestInHostWorld(){return guest;}
bool BbscGuestLoadItemsReady(){return guest_ready;}
int GetLocalPlayerType(){return 1;}
bool BbscSharedProgressEnabled(){return true;}
int GetSessionState(){return guest?6:0;}
std::map<u32,s32> bag,storage;std::set<u32> flags;
enum class BbscLedgerSource : u8 {Give=1,Pickup,Award,Drop,Boss,Talk,Key,Retro,Legacy};
struct BbscLedgerContext{BbscLedgerSource source{};s32 lot=0;u32 flag=0,gives=0;bool check=false;};
std::optional<BbscLedgerContext> bbsc_ledger_context;
s64 SteadyNowMs(){return 1000;}
constexpr u64 BbscGiveWindowReturn1=0x017D934D,BbscGiveWindowReturn2=0x017D94CC;
void NoteBbscLedgerGiven(BbscLedgerSource,s32,u32,u32,s32){}
struct Ticket{};std::optional<Ticket> bbsc_chalice_reward_context;void NoteBbscChaliceReward(const Ticket&){}
template<class T>T ReadValue(u64 p,size_t off){T v;memcpy(&v,(void*)(p+off),sizeof(v));return v;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
u64 GetGlobalState(){return (u64)global.data();}
u64 BbscCarriedInventory(){return 1;}
u64 BbscLedgerLotRow(s32 lot){return lots.contains(lot)?(u64)lots.at(lot).data():0;}
bool BbscEventFlag(u32 f){return flags.contains(f);}
bool WriteBbscLedgerBackend();
bool WriteBbscLedgerLocked(){++writes;if(!write_ok)return false;return WriteBbscLedgerBackend();}
std::filesystem::path BbscLedgerPath(const BbscSaveSlot&){return "ledger.bin";}
'''
code += decl(r'struct BbscBossReward \{.*?\};')
code += decl(r'constexpr std::array<BbscBossReward, 19> BbscBossRewards\{\{.*?\}\};')
code += decl(r'struct BbscUniqueChaliceReward \{.*?\};')
code += decl(r'constexpr std::array<BbscUniqueChaliceReward, 17> BbscUniqueChaliceRewards\{\{.*?\}\};')
code += fun('bool IsBbscUniqueChaliceRewardFlag(u32 flag)')
code += decl(r'constexpr std::array<u32, 19> BbscBossRewardDefeats\{.*?\};')
code += decl(r'enum class BbscLedgerState : u8 \{.*?\};')
code += decl(r'struct BbscLedgerEntry \{.*?\n\};')
code += decl(r'constexpr u32 BbscLedgerMagic = .*?;')
code += decl(r'constexpr u32 BbscLedgerVersion = .*?;')
code += 'std::vector<BbscLedgerEntry> bbsc_ledger;std::map<u32,s32> bbsc_ledger_host_counts,bbsc_ledger_trip;std::map<u32,u8> bbsc_ledger_retro;\n'
code += fun('bool WriteBbscLedgerLocked()').replace('bool WriteBbscLedgerLocked()', 'bool WriteBbscLedgerBackend()')
code += fun('void LoadBbscLedgerLocked(const BbscSaveSlot& slot)')
code += fun('bool IsBbscBossRewardLot(s32 lot)')
code += fun('bool BbscLedgerAddable(u32 code)')
code += 's32 BbscLedgerCount(u32 c){return bag[c]+storage[c];}\n'
code += fun('std::vector<u32> BbscLotFlags(u64 row)')
code += fun('void NoteBbscLedgerLot(s32 lot, u32 code)')
code += fun('void NoteBbscLedgerWindow(u64 caller_offset, u32 type, u32 id, s32 count)')
code += fun('bool BbscSharedBossDefeated(size_t index, const std::vector<u32>& flags,\n        const std::map<u32, std::array<u8, BbscWorldGroupBytes>>& groups)')
code += fun('bool BbscBossRewardPersistentItem(u64 row)')
code += fun('void MarkBbscBossRewardAccounted(s64 event)')
code += fun('bool ReconcileBbscUniqueChaliceRewards(const std::vector<u32>& flags, u64 manager)')
code += fun('bool ReconcileBbscSharedBossRewards(const std::vector<u32>& flags,\n        const std::map<u32, std::array<u8, BbscWorldGroupBytes>>& groups)')
code += fun('void CollectBbscOwnBossRewardVictories(std::map<u32, std::array<u8, BbscWorldGroupBytes>>& victories)')
code += 'void RecoverBbscOwnBossRewards(){std::map<u32,std::array<u8,125>> v;CollectBbscOwnBossRewardVictories(v);ReconcileBbscSharedBossRewards({},v);}'
code += r'''
std::mutex bbsc_progress_mutex;
std::vector<u32> bbsc_progress_host_flags;
std::map<u32,std::array<u8,125>> bbsc_progress_groups;
std::optional<Slot> bbsc_progress_slot;
bool bbsc_progress_backed_up=false,backup_ok=true;
enum class BbscWork : u32 {RewardCheck=16};std::atomic<u32> bbsc_pending_work{0};
void QueueBbscWork(BbscWork w){bbsc_pending_work.fetch_or((u32)w);}
std::atomic<bool> bbsc_reward_check_pending{true};bool bbsc_reward_check_complete=false;
void RequestBbscRewardCheck();
bool BbscOwnOpeningDone(){return true;}
bool BackupBbscSaves(){return backup_ok;}
u64 BbscFlagGroupStorage(u32 key){return (u64)bbsc_progress_groups[key].data();}
u8 BbscSharedProgressByte(u32,size_t,u8 incoming){return incoming;}
constexpr u64 EventFlagManPointerOffset=0x553b100;
'''
code += decl(r'constexpr std::array<u32, 49> BbscProgressFlags\{.*?\};')
code += decl(r'constexpr std::array<u32, 8> BbscProgressFlagsMore\{.*?\};')
code += 'std::atomic<int> bbsc_relay_session_state{6};int bbsc_host_time_bits=-1;s64 bbsc_host_time_ms=0;\n'
code += fun('void RequestBbscRewardCheck()')
code += fun('void OnBbscProgressPacket(const std::uint32_t* flags, std::size_t count)')
code += fun('void ProcessBbscRewardCheck()')
code += fun('bool BbscBossCompletionBitsAdded(u32 key, size_t byte, u8 added)')
code += fun('std::pair<s64, size_t> MergeBbscSharedProgress(std::string_view when)')
code += r'''
void PS4_SYSV_ABI NativeAward(u64,s32 lot,u32 host_only){
 assert(host_only==0&&bbsc_native_boss_award);++calls;bbsc_ledger_context=BbscLedgerContext{BbscLedgerSource::Boss,lot};
 if(fail)return;
 auto row=BbscLedgerLotRow(lot);
 for(int i=0;i<8;++i)if(ReadValue<u16>(row,0x40+2*i)){
  u32 c=(ReadValue<u32>(row,0x20+4*i)<<28)|ReadValue<u32>(row,4*i);
  if(!fake_window)bag[c]+=ReadValue<u8>(row,0x8a+i);
  NoteBbscLedgerWindow(BbscGiveWindowReturn1,c&0xf0000000u,c&0x0fffffffu,ReadValue<u8>(row,0x8a+i));
 }
 if(!fake_window)for(u32 f:BbscLotFlags(row))flags.insert(f);
}
void SetBbscLedgerFlag(u32 f,u8 v){if(v)flags.insert(f);else flags.erase(f);}
void PS4_SYSV_ABI NativeSet(u64,u32 f,u8 on){if(on)flags.insert(f);else flags.erase(f);}
void reset(){bbsc_boss_reward_given.clear();bbsc_boss_reward_queue.clear();bbsc_progress_slot.reset();guest=false;guest_ready=true;bbsc_reward_check_pending=true;bbsc_reward_check_complete=false;bbsc_pending_work=0;bbsc_progress_backed_up=false;backup_ok=true;bbsc_progress_host_flags.clear();bbsc_progress_groups.clear();bag.clear();storage.clear();flags.clear();bbsc_ledger_lots.clear();
 std::filesystem::remove("ledger.bin");bbsc_ledger.clear();bbsc_ledger_host_counts.clear();bbsc_ledger_trip.clear();bbsc_ledger_retro.clear();
 calls=writes=0;fail=fake_window=false;write_ok=true;bbsc_ledger_dirty=false;
 bbsc_ledger_slot=Slot{};active=Slot{};bbsc_ledger_home_ready=true;global.fill(0);
 bbsc_ledger_home_generation=1;bbsc_load_generation=1;
}
using Groups=std::map<u32,std::array<u8,125>>;
void bit(Groups& groups,u32 f){groups[f/1000][f%1000/8]|=0x80u>>(f%8);}
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image_base);
 u64 manager=1;memcpy((void*)(image_base+ItemManPointerOffset),&manager,8);
 u8 jump[]={0x48,0xb8,0,0,0,0,0,0,0,0,0xff,0xe0};u64 fn=(u64)NativeAward;
 memcpy(jump+2,&fn,8);memcpy((void*)(image_base+AwardItemLotOffset),jump,sizeof(jump));
 fn=(u64)NativeSet;memcpy(jump+2,&fn,8);memcpy((void*)(image_base+0x0132E5A0),jump,sizeof(jump));
'''
for _, _, first, repeat in bosses:
    for lot in [first] + ([repeat] if repeat else []):
        raw = data[rows[lot]:rows[lot]+0x94]
        code += f'lots[{lot}]={{{",".join(map(str, raw))}}};\n'
for _, _, first, _ in bosses:
    raw = data[rows[first]:rows[first]+0x94]
    for entry in range(8):
        if struct.unpack_from('<H', raw, 0x40+entry*2)[0] and struct.unpack_from('<I', raw, 0x20+entry*4)[0] == 4:
            item = struct.unpack_from('<I', raw, entry*4)[0]
            goods_raw = goods_data[goods_rows[item]:goods_rows[item]+0x40]
            code += f'goods[{item}]={{{",".join(map(str,goods_raw))}}};\n'
cup_rewards=[tuple(map(int,x)) for x in re.findall(r'\{(\d+), (\d+)\}', re.search(r'BbscUniqueChaliceRewards\{\{(.*?)\}\};',s,re.S)[1])]
for flag,lot in cup_rewards:
    raw=data[rows[lot]:rows[lot]+0x94]
    assert struct.unpack_from('<i',raw,0x80)[0]==flag
    item=struct.unpack_from('<i',raw)[0]
    assert struct.unpack_from('<I',raw,0x20)[0]==4
    code+=f'lots[{lot}]={{{",".join(map(str,raw))}}};\n'
    gr=goods_data[goods_rows[item]:goods_rows[item]+0x40]
    code+=f'goods[{item}]={{{",".join(map(str,gr))}}};\n'
code += r'''
 for(size_t i=0;i<BbscBossRewards.size();++i){
  const auto& r=BbscBossRewards[i];Groups groups;bit(groups,(u32)r.event);
  const u64 original=BbscLedgerLotRow(r.first_lot);
  if(!r.flag&&BbscLotFlags(original).empty()&&!BbscBossRewardPersistentItem(original)){
   reset();assert(ReconcileBbscSharedBossRewards({},groups)&&calls==0);continue;
  }
  reset();bbsc_boss_reward_queue.push_back(r.event);assert(ReconcileBbscSharedBossRewards({},groups));assert(calls==1&&writes==1);
  assert(bbsc_boss_reward_queue.empty()&&std::ranges::find(bbsc_boss_reward_given,r.event)!=bbsc_boss_reward_given.end());
  assert(bbsc_ledger_lots.contains(r.first_lot));assert(!bbsc_native_boss_award);
  // Repeated merge, rejoin, and a spent/sold reward never issue the repeat lot.
  bag.clear();storage.clear();flags.clear();
  for(int k=0;k<4;++k)assert(ReconcileBbscSharedBossRewards({},groups));assert(calls==1);
  // The same character's persisted journal survives a new process (disk fixture).
  bbsc_ledger_lots.clear();LoadBbscLedgerLocked(*bbsc_ledger_slot);
  assert(ReconcileBbscSharedBossRewards({},groups)&&calls==1);
  // A native award from participating in the fight already recorded this lot.
  reset();NoteBbscLedgerLot(r.first_lot,0);assert(ReconcileBbscSharedBossRewards({},groups)&&calls==0);
  if(r.repeat_lot){reset();NoteBbscLedgerLot(r.repeat_lot,0);assert(ReconcileBbscSharedBossRewards({},groups)&&calls==0);}
  // A failed give retains pending progress and is retried only via the native entry.
  reset();fail=true;assert(!ReconcileBbscSharedBossRewards({},groups));assert(!bbsc_ledger_lots.contains(r.first_lot));
  fail=false;assert(ReconcileBbscSharedBossRewards({},groups));assert(calls==2);
  reset();write_ok=false;assert(!ReconcileBbscSharedBossRewards({},groups));assert(calls==1);
  write_ok=true;assert(ReconcileBbscSharedBossRewards({},groups)&&calls==1);
  // Loading / wrong slot / not-yet-reconciled bag: no give and no premature receipt.
  reset();global[8]=1;assert(!ReconcileBbscSharedBossRewards({},groups)&&calls==0);
  reset();active.slot=2;assert(!ReconcileBbscSharedBossRewards({},groups)&&calls==0);
  reset();bbsc_ledger_home_ready=false;assert(!ReconcileBbscSharedBossRewards({},groups)&&calls==0);
  reset();bbsc_load_generation=2;assert(!ReconcileBbscSharedBossRewards({},groups)&&calls==0);
  auto row=BbscLedgerLotRow(r.first_lot);auto receipts=BbscLotFlags(row);
  for(u32 f:receipts){reset();flags.insert(f);assert(ReconcileBbscSharedBossRewards({},groups)&&calls==(BbscBossRewardPersistentItem(row)?1:0));}
  if(r.flag){reset();flags.insert(r.flag);assert(ReconcileBbscSharedBossRewards({},groups)&&calls==(BbscBossRewardPersistentItem(row)?1:0));}
  // Existing carried OR stored award prevents a duplicate, including old journals.
  for(int e=0;e<8;++e)if(ReadValue<u16>(row,0x40+e*2)){
   u32 c=(ReadValue<u32>(row,0x20+4*e)<<28)|ReadValue<u32>(row,4*e);
   if(BbscLedgerAddable(c)){
    reset();storage[c]=ReadValue<u8>(row,0x8a+e);assert(ReconcileBbscSharedBossRewards({},groups)&&calls==0);
    reset();fake_window=true;assert(!ReconcileBbscSharedBossRewards({},groups));
    assert(!bbsc_ledger_lots.contains(r.first_lot));
   }
  }
  if(BbscBossRewardDefeats[i]){reset();assert(ReconcileBbscSharedBossRewards({BbscBossRewardDefeats[i]},{}));assert(bbsc_ledger_lots.contains(r.first_lot));}
 }
 reset();assert(ReconcileBbscSharedBossRewards({},{}));assert(calls==0);
 // Shared stage flags cannot confuse Laurence with Ludwig.
 assert(ReconcileBbscSharedBossRewards({3400,3401,3402,3403},{}));assert(calls==0);
 // Ordinary consumables stay excluded even for a new shared victory.
 reset();bbsc_progress_host_flags={9452};assert(MergeBbscSharedProgress("consumable").first==1&&calls==0);
 // Upgrade recovery: already merged Blood-starved Beast, stale native receipt, no chalice.
 reset();flags.insert(9453);flags.insert(5000);RecoverBbscOwnBossRewards();
 assert(calls==1&&bag[0x40000000u|6109u]==1&&flags.contains(5000));
 RecoverBbscOwnBossRewards();assert(calls==1);
 // Old spent flagless consumables are ambiguous: do not reissue from own victory alone.
 reset();flags.insert(9452);RecoverBbscOwnBossRewards();assert(calls==0);
 reset();flags.insert(9453);flags.insert(5000);fail=true;RecoverBbscOwnBossRewards();
 assert(flags.contains(5000)&&!bbsc_ledger_lots.contains(80000000));
 fail=false;RecoverBbscOwnBossRewards();assert(bag[0x40000000u|6109u]==1);
 reset();bbsc_progress_host_flags={9453};fail=true;
 assert(MergeBbscSharedProgress("test").first==1&&flags.contains(9453)&&calls==0);
 ProcessBbscRewardCheck();assert(calls==1&&!bbsc_reward_check_complete);
 fail=false;ProcessBbscRewardCheck();assert(calls==1); // no timed retry
 RequestBbscRewardCheck();ProcessBbscRewardCheck();assert(calls==2&&bbsc_reward_check_complete);
 assert(MergeBbscSharedProgress("test").first==0&&calls==2);
 reset();bbsc_progress_host_flags={9453};backup_ok=false;
 assert(MergeBbscSharedProgress("test").first==-2&&!flags.contains(9453)&&calls==0);
 for(const auto& r:BbscBossRewards){u32 f=(u32)r.event;
  assert(BbscBossCompletionBitsAdded(f/1000,f%1000/8,0x80u>>(f%8)));
  assert(!BbscBossCompletionBitsAdded(f/1000,f%1000/8,0));
 }
 assert(!BbscBossCompletionBitsAdded(12410,1,0xff)); // ordinary map flags do not trigger a reward scan
 // Receipt packets carry entitlement, and identical heartbeats do not schedule another check.
 reset();u32 incoming[]={5020,5001,99999999};bbsc_reward_check_pending=false;
 OnBbscProgressPacket(incoming,3);assert(bbsc_progress_host_flags.size()==2&&bbsc_pending_work==16);
 bbsc_pending_work=0;bbsc_reward_check_pending=false;OnBbscProgressPacket(incoming,3);
 assert(bbsc_pending_work==0&&!bbsc_reward_check_pending);
 // Do not use the previous character's collected eligibility after a character switch.
 reset();guest=true;bbsc_progress_slot=Slot{};bbsc_progress_slot->slot=5;
 bbsc_progress_host_flags={5020};ProcessBbscRewardCheck();assert(calls==0&&bbsc_reward_check_pending);
 // Host-load event: receive entitlement with no local boss defeat and no local receipt.
 for(const auto& cup:BbscUniqueChaliceRewards){
  reset();guest=true;bbsc_ledger_home_ready=false;bbsc_progress_host_flags={cup.flag};
  guest_ready=false;ProcessBbscRewardCheck();assert(calls==0&&bbsc_reward_check_pending);
  guest_ready=true;RequestBbscRewardCheck();ProcessBbscRewardCheck();
  assert(calls==1&&bbsc_reward_check_complete&&bbsc_ledger_lots.contains(cup.lot));
  RequestBbscRewardCheck();ProcessBbscRewardCheck();assert(calls==1);
  reset();bbsc_progress_host_flags={cup.flag};fail=true;
  assert(MergeBbscSharedProgress("receipt").first==0&&!flags.contains(cup.flag)&&calls==0);
  RequestBbscRewardCheck();ProcessBbscRewardCheck();assert(!flags.contains(cup.flag));
 }
 reset();guest=true;bbsc_ledger_home_ready=false;bbsc_progress_host_flags={9453};
 ProcessBbscRewardCheck();assert(calls==1&&bbsc_ledger_lots.contains(80000000));
 for(int i=0;i<100;++i)ProcessBbscRewardCheck();assert(calls==1); // no polling
 reset();Groups all;for(auto& r:BbscBossRewards)bit(all,(u32)r.event);
 assert(ReconcileBbscSharedBossRewards({},all));assert(calls==15);
 assert(ReconcileBbscSharedBossRewards({},all)&&calls==15);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-shared-boss-') as folder:
    path = Path(folder)
    cpp, exe = path/'fixture.cpp', path/'fixture.exe'
    cpp.write_text(code, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler, '-std=c++20', '-O0', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
                    '-I', str(ROOT/'emulator/src'), str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], cwd=path, env=env, check=True, timeout=20)
print('PASS: 19 original boss lots/defeat indicators; native catch-up; receipts, inventory/storage, '
      'spent rewards, rejoin/restart, failed give/write, slot/load gates and Ludwig/Laurence isolation')
