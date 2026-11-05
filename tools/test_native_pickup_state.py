"""Production native completion/receipt persistence in synthetic flag tables."""
from pathlib import Path
import os
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def fun(sig):
    a=s.index(sig+' {');b=s.index('{',a)+1;depth=1
    while depth:
        depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[a:b]+'\n'
def decl(pattern):
    return re.search(pattern,s,re.S).group()+'\n'
code=r'''
#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <map>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s64=int64_t;
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
constexpr size_t BbscWorldGroupBytes=125;
bool guest=true,bbsc_npc_own_active=true,bbsc_own_world_dirty=false,bbsc_loot_dirty=false;
bool BbscGuestInHostWorld(){return guest;}
std::map<u32,std::array<u8,125>> live,bbsc_own_world;
struct Loot{std::array<u8,125> taken{},written{};};
std::map<u32,Loot> bbsc_loot_groups;
std::string bbsc_loot_dungeon;
std::mutex bbsc_npc_own_mutex;std::unordered_map<u32,u8> bbsc_npc_own;
std::unordered_map<u32,bool> bbsc_action_owner;
int own_writes=0,loot_writes=0;
void WriteBbscOwnWorldFile(){++own_writes;}
void WriteBbscGuestLootFile(){++loot_writes;}
std::vector<std::pair<u32,u8>> journal;
void NoteBbscTalkFlag(u32 f,u8 v,u64,bool){journal.emplace_back(f,v);}
bool BbscLedgerOwnAwardFlag(u32){return false;}
bool IsBbscNativeItemStateFlag(u32);
void RecordBbscNativeItemFlag(u32,u8);
namespace Chalice{bool IsLootGroup(u32 k){return k/10000==5&&(k%10000)/100==29;}}
u64 BbscFlagGroupStorage(u32 k){auto it=live.find(k);return it==live.end()?0:(u64)it->second.data();}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
'''
code+=decl(r'constexpr std::array<u32, \d+> BbscNpcQuestFlags\{.*?\n\};')
code+=decl(r'struct BbscScriptedPickup \{.*?\};')
code+=decl(r'constexpr std::array<BbscScriptedPickup, \d+> BbscScriptedPickups\{\{.*?\}\};')
for signature in ['bool IsBbscGlobalLootReceipt(u32 flag)',
                  'bool IsBbscScriptedPickupFlag(u32 flag)',
                  'bool IsBbscNativeItemStateFlag(u32 flag)',
                  'bool BbscNpcFlagBit(u64 storage, u32 flag)',
                  'void SetBbscNpcFlagBit(u64 storage, u32 flag, bool on)',
                  'void MarkBbscTakenInOwnWorld(u32 key, size_t byte, u8 bits)',
                  'void RecordBbscNativeItemFlag(u32 flag, u8 value)',
                  'void RevertBbscNpcOwnFlags()',
                  'void KeepBbscNpcOwnBits(u32 key, const u8* before, u8* live)']:
    code+=fun(signature)
code+=r'''
enum class BbscLedgerSource{Pickup,Award,Boss};
struct BbscLedgerContext{BbscLedgerSource source;s64 lot;u32 flag,gives;bool check;};
std::optional<BbscLedgerContext> bbsc_ledger_context;
std::optional<int> bbsc_chalice_reward_context;
u32 bbsc_native_pickup_flag=0;u64 image_base=0x800000000;
s64 BbscLotOfFlag(u32 f){return f+1;}
struct GuestRegisterSnapshot{u64 rsp;};
bool ReadablePointer(u64 p,size_t){return p!=0;}
'''
code+=fun('void BeginBbscLedgerPickup()')
part=fun('void PS4_SYSV_ABI BbscPickupHook(u64 tag, const GuestRegisterSnapshot* registers)')
part=part[part.index('    case 3: {'):part.index('    case 4:')]
part=part.replace('    case 3: {','void GiveHook(const GuestRegisterSnapshot* registers) {',1)
code+=part
code+=r'''
void set(std::map<u32,std::array<u8,125>>& table,u32 f,bool on){
 auto& b=table[f/1000][f%1000/8];u8 m=0x80u>>(f%8);b=on?(b|m):(b&~m);
}
bool bit(const std::map<u32,std::array<u8,125>>& table,u32 f){
 auto p=table.find(f/1000);return p!=table.end()&&(p->second[f%1000/8]&(0x80u>>(f%8)));
}
int main(){
 // Native event writes completion directly; an old zero in the NPC cache must not undo it.
 u32 ritual=12300130;bbsc_npc_own[ritual]=0;set(live,ritual,true);set(bbsc_own_world,ritual,false);
 RevertBbscNpcOwnFlags();assert(bit(live,ritual)&&bit(bbsc_own_world,ritual));
 assert(journal.back()==std::pair(ritual,u8(1)));
 // Incoming host bits preserve the current local native bit, not a stale NPC cache.
 bbsc_npc_own[ritual]=0;std::array<u8,125> incoming{};
 KeepBbscNpcOwnBits(ritual/1000,live.at(ritual/1000).data(),incoming.data());
 assert(incoming[ritual%1000/8]&(0x80u>>(ritual%8)));
 std::array<u8,125> before{};incoming.fill(0xff);
 KeepBbscNpcOwnBits(ritual/1000,before.data(),incoming.data());
 assert(!(incoming[ritual%1000/8]&(0x80u>>(ritual%8))));
 // Other personal NPC states still reject a remote change.
 u32 npc=1325;
 assert(npc);bbsc_npc_own[npc]=0;set(live,npc,true);RevertBbscNpcOwnFlags();assert(!bit(live,npc));
 // A real take immediately after a boss award must carry its own receipt.
 for(u64 offset:{0x017D8758u,0x017D88D3u}){
  u64 caller=image_base+offset;GuestRegisterSnapshot regs{(u64)&caller};
  bbsc_ledger_context=BbscLedgerContext{BbscLedgerSource::Boss,80000000,5000,1,false};
  bbsc_chalice_reward_context=1;bbsc_native_pickup_flag=52300420;GiveHook(&regs);
  assert(bbsc_ledger_context->source==BbscLedgerSource::Pickup&&bbsc_ledger_context->flag==52300420);
  assert(!bbsc_chalice_reward_context);
 }
 // Confirmed map pickup in another area persists immediately, without the one-second poll.
 u32 receipt=52300420;set(bbsc_own_world,receipt,false);
 RecordBbscNativeItemFlag(receipt,1);assert(bit(bbsc_own_world,receipt));
 assert(bbsc_loot_groups.at(receipt/1000).taken[receipt%1000/8]&(0x80u>>(receipt%8)));
 auto restored=bbsc_own_world;assert(bit(restored,receipt)); // home snapshot contains the receipt
 RecordBbscNativeItemFlag(receipt,1);assert(restored==bbsc_own_world); // idempotent, no award call
 // Global one-time enemy receipts have no map baseline; preserve only the actual picked bit.
 u32 gilbert=50001300;assert(!bbsc_own_world.contains(gilbert/1000));
 RecordBbscNativeItemFlag(gilbert,1);assert(bit(bbsc_own_world,gilbert));
 size_t global_bits=0;for(u8 b:bbsc_own_world.at(gilbert/1000))global_bits+=std::popcount(b);
 assert(global_bits==1); // no other host receipts imported
 // No foreign ritual or unsnapshotted host receipt can enter our own world.
 u32 dungeon=52900420;set(bbsc_own_world,dungeon,false);RecordBbscNativeItemFlag(dungeon,1);assert(!bit(bbsc_own_world,dungeon));
 u32 absent=53200420;RecordBbscNativeItemFlag(absent,1);assert(!bbsc_own_world.contains(absent/1000));
 u32 foreign=52400420;set(bbsc_own_world,foreign,false);bbsc_loot_dungeon="foreign";
 RecordBbscNativeItemFlag(foreign,1);assert(!bit(bbsc_own_world,foreign));bbsc_loot_dungeon.clear();
 guest=false;RecordBbscNativeItemFlag(foreign,1);assert(!bit(bbsc_own_world,foreign));guest=true;
 RecordBbscNativeItemFlag(foreign,0);assert(!bit(bbsc_own_world,foreign));
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-native-pickup-state-') as folder:
    path=Path(folder);cpp=path/'fixture.cpp';exe=path/'fixture.exe'
    cpp.write_text(code,encoding='utf-8')
    compiler='C:/msys64/clang64/bin/clang++.exe'
    subprocess.run([compiler,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],env=env,check=True)
print('PASS: native completion not rolled back, remote NPC isolation, immediate exact pickup '
      'receipt in own snapshot, repeated recording and foreign-dungeon/missing-baseline guards')
