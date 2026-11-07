"""Production completion/receipt persistence, optionally executing the original ELF writer."""
from pathlib import Path
import os
import re
import struct
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
ELF=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parents[1]/'out/exit-study.elf'
ORIGINAL_START=0x012ED100
ORIGINAL_SIZE=0x276

def original_completion():
    data=ELF.read_bytes()
    ph=struct.unpack_from('<Q',data,32)[0]
    stride,count=struct.unpack_from('<HH',data,54)
    for i in range(count):
        kind,_,offset,address,_,size,_,_=struct.unpack_from('<II6Q',data,ph+i*stride)
        if kind==1 and address<=ORIGINAL_START and ORIGINAL_START+ORIGINAL_SIZE<=address+size:
            offset+=ORIGINAL_START-address
            return data[offset:offset+ORIGINAL_SIZE]
    raise ValueError('Missing the native completion function in the ELF')

s=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def fun(sig):
    a=s.index(sig+' {');b=s.index('{',a)+1;depth=1
    while depth:
        depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[a:b]+'\n'
def decl(pattern):
    return re.search(pattern,s,re.S).group()+'\n'
code=r'''
#include <windows.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <mutex>
#include <optional>
#include <span>
#include <string>
#include <unordered_map>
#include <vector>
#include "core/bbsc_quest_event_rules.h"
#include "core/cpu_patches.h"
namespace QuestRules=Core::Bloodborne::QuestRules;
using Core::GuestRegisterSnapshot;
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
constexpr size_t BbscWorldGroupBytes=125;
bool guest=true,bbsc_npc_own_active=true,bbsc_own_world_dirty=false,bbsc_loot_dirty=false;
bool bbsc_native_item_completion_hook_ready=false;
std::optional<u32> bbsc_native_item_seed_generation;
std::atomic<u32> bbsc_load_generation=0;
constexpr u64 WorldFlagManPointerOffset=0x0553B100;
u64 fixture_manager=42;
u64 image_base=0x800000000;
bool BbscGuestInHostWorld(){return guest;}
std::map<u32,std::array<u8,125>> live,bbsc_own_world;
struct Loot{std::array<u8,125> taken{},written{};};
std::map<u32,Loot> bbsc_loot_groups;
std::string bbsc_loot_dungeon;
std::mutex bbsc_npc_own_mutex;std::unordered_map<u32,u8> bbsc_npc_own;
std::unordered_map<u32,std::array<u8,BbscWorldGroupBytes>> bbsc_npc_checked_groups;
std::unordered_map<u32,bool> bbsc_action_owner;
int own_writes=0,loot_writes=0;
int read_checks=0,group_resolves=0;
int checked_flags=0;
bool readable_groups=true;
void WriteBbscOwnWorldFile(){++own_writes;}
void WriteBbscGuestLootFile(){++loot_writes;}
std::vector<std::pair<u32,u8>> journal;
void NoteBbscTalkFlag(u32 f,u8 v,u64,bool){journal.emplace_back(f,v);}
bool BbscLedgerOwnAwardFlag(u32){return false;}
bool IsBbscNativeItemStateFlag(u32);
bool IsBbscEventWrittenItemStateFlag(u32);
bool ReadablePointer(u64,size_t);
void RecordBbscNativeItemFlag(u32,u8);
namespace Chalice{bool IsLootGroup(u32 k){return k/10000==5&&(k%10000)/100==29;}}
u64 BbscFlagGroupStorage(u32 k){++group_resolves;auto it=live.find(k);return it==live.end()?0:(u64)it->second.data();}
template<class T>T ReadValue(u64 p,size_t o){
 ++read_checks;
 if(p==image_base+WorldFlagManPointerOffset && o==0)return static_cast<T>(fixture_manager);
 T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;
}
'''
code+=decl(r'constexpr std::array<u32, \d+> BbscNpcQuestFlags\{.*?\n\};')
code+=decl(r'struct BbscScriptedPickup \{.*?\};')
code+=decl(r'constexpr std::array<BbscScriptedPickup, \d+> BbscScriptedPickups\{\{.*?\}\};')
code+=decl(r'struct BbscNpcFlagPassCatalog \{.*?\};')
for signature in ['bool IsBbscGlobalLootReceipt(u32 flag)',
                  'bool IsBbscScriptedPickupFlag(u32 flag)',
                  'bool IsBbscKidnapFlag(u32 flag)',
                  'bool IsBbscNativeItemStateFlag(u32 flag)',
                  'bool IsBbscEventWrittenItemStateFlag(u32 flag)',
                  'bool IsBbscNpcQuestFlag(u32 flag)',
                  'void NoteBbscNpcOwnFlag(u32 flag, u8 value)',
                  'const BbscNpcFlagPassCatalog& BbscNpcFlagPassFlags()',
                  'void SetBbscNpcFlagBit(u64 storage, u32 flag, bool on)',
                  'void MarkBbscTakenInOwnWorld(u32 key, size_t byte, u8 bits)',
                  'void RecordBbscNativeItemFlag(u32 flag, u8 value)',
                  'void SeedBbscNativeItemStateAtLoad()',
                  'void RecordBbscNativeItemSetFlag(u64 manager, u32 flag, bool value)',
                  'void PS4_SYSV_ABI BbscNativeItemCompletionHook(u64, const GuestRegisterSnapshot* registers)',
                  'void RevertBbscNpcOwnFlags()',
                  'void KeepBbscNpcOwnBits(u32 key, const u8* before, u8* live)']:
    source=fun(signature)
    if signature.startswith('bool IsBbscNativeItemStateFlag('):
        source=source.replace('{', '{\n    ++checked_flags;', 1)
    code+=source
code+=r'''
enum class BbscLedgerSource{Pickup,Award,Boss};
struct BbscLedgerContext{BbscLedgerSource source;s64 lot;u32 flag,gives;bool check;};
std::optional<BbscLedgerContext> bbsc_ledger_context;
std::optional<int> bbsc_chalice_reward_context;
u32 bbsc_native_pickup_flag=0;
namespace BbscMod {
u64 EbootAddress(){return image_base;}
void LogPlain(const char* line){puts(line);}
}
s64 BbscLotOfFlag(u32 f){return f+1;}
bool ReadablePointer(u64 p,size_t){return readable_groups&&p!=0;}
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
template<class T> void put(void* address,size_t offset,T value){
 memcpy(static_cast<u8*>(address)+offset,&value,sizeof(value));
}
void TestNativeCompletion(std::span<const u8> original){
 if(original.empty())return;
 auto* base=static_cast<u8*>(VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE));
 assert(base);image_base=reinterpret_cast<u64>(base);
 auto* entry=base+0x012ED100;
 memcpy(entry,original.data(),original.size());
 static constexpr std::array<u8,9> store{0x0f,0xb6,0x0c,0x02,0x09,0xf1,0x88,0x0c,0x02};
 assert(Core::InstallGuestCodeHook(base+0x012ED357,store,0,BbscNativeItemCompletionHook));
 using Complete=void PS4_SYSV_ABI (*)(void*,u8);
 const auto complete=reinterpret_cast<Complete>(entry);
 std::array<u8,0x40> manager{},root{},node{},nil{};
 std::array<u8,0xD0> event{};
 put(base,0x0553B100,manager.data());
 put(manager.data(),0x1c,u32{1000});put(manager.data(),0x38,root.data());
 put(root.data(),8,node.data());put(node.data(),0,nil.data());put(node.data(),0x10,nil.data());
 put(nil.data(),0x19,u8{1});put(node.data(),0x28,u32{2});
 // The completion payload is already staged. Run the original flag lookup,
 // event ID plus slot, live store and epilogue without its allocator dependencies.
 put(event.data(),0x2e,u8{1});
 const auto run=[&](u32 flag,bool present){
  set(live,flag,false);set(bbsc_own_world,flag,false);
  put(node.data(),0x20,flag/1000+!present);
  put(node.data(),0x30,live.at(flag/1000).data());
  put(event.data(),0x28,flag-1);put(event.data(),0x2c,s16{1});
  complete(event.data(),0);
  assert(bit(live,flag)==present);
 };
 guest=true;journal.clear();
 run(12300130,true);
 assert(journal.size()==1 && journal.back()==std::pair(u32{12300130},u8{1}));
 assert(bit(bbsc_own_world,12300130));
 run(9421,false);assert(journal.size()==1 && !bit(bbsc_own_world,9421));
 run(12400651,true);assert(journal.size()==1 && !bit(bbsc_own_world,12400651));
 guest=false;run(9421,true);assert(journal.size()==1 && !bit(bbsc_own_world,9421));
 puts("PASS original EMEVD completion with production trampoline: native flag, slot, absent group, unrelated flag and host");
}
void OriginalFixture();
int main(){
 // Incoming snapshots can neither grant nor clear a local Eileen completion,
 // including the initial snapshot before the quest guard is active.
 for(bool active:{false,true}){
  bbsc_npc_own_active=active;
  for(u32 event:{12400651u,12400652u,12410809u}){
   std::array<u8,125> local{},incoming{};
   const u32 byte=(event%1000)/8;const u8 mask=0x80u>>(event%8);
   incoming[byte]=mask;
   KeepBbscNpcOwnBits(event/1000,local.data(),incoming.data());assert(!(incoming[byte]&mask));
   local[byte]=mask;
   KeepBbscNpcOwnBits(event/1000,local.data(),incoming.data());assert(incoming[byte]&mask);
  }
 }
 // Abduction progress is native and personal, including event-completion writes
 // outside SetFlag. A host snapshot cannot grant or erase the visitor's first trip.
 for(u32 f=9420;f<=9423;++f){
  assert(IsBbscNativeItemStateFlag(f));
  set(live,f,false);set(bbsc_own_world,f,false);
  auto incoming=live.at(9);incoming[f%1000/8]|=0x80u>>(f%8);
  KeepBbscNpcOwnBits(9,live.at(9).data(),incoming.data());
  assert(!(incoming[f%1000/8]&(0x80u>>(f%8))));
  set(live,f,true);RevertBbscNpcOwnFlags();assert(bit(live,f)&&bit(bbsc_own_world,f));
  incoming.fill(0);KeepBbscNpcOwnBits(9,live.at(9).data(),incoming.data());
  assert(incoming[f%1000/8]&(0x80u>>(f%8)));
  set(live,f,false);RevertBbscNpcOwnFlags();assert(!bit(live,f)&&!bit(bbsc_own_world,f));
 }

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
 bbsc_npc_own[ritual]=1; // restore the observed value after the stale-cache test
 // Other personal NPC states still reject a remote change.
 u32 npc=1325;
 assert(npc);bbsc_npc_own[npc]=0;set(live,npc,true);RevertBbscNpcOwnFlags();assert(!bit(live,npc));
 // A real take immediately after a boss award must carry its own receipt.
 for(u64 offset:{0x017D8758u,0x017D88D3u}){
  u64 caller=image_base+offset;GuestRegisterSnapshot regs{};regs.rsp=(u64)&caller;
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
 // Fully loaded synthetic table, including groups absent from the above cases.
 for(u32 flag:BbscNpcQuestFlags)if(flag>=1000)live.try_emplace(flag/1000);
 checked_flags=0;RevertBbscNpcOwnFlags();assert(checked_flags>0);
 const auto all_flags=std::ranges::count_if(BbscNpcQuestFlags,[](u32 flag){return flag>=1000;});
 checked_flags=read_checks=group_resolves=0;RevertBbscNpcOwnFlags();
 const auto groups=group_resolves;
 assert(read_checks==0&&checked_flags==0&&groups==(int)bbsc_npc_checked_groups.size());
 // A native write that bypasses SetFlag, between tick and EMEVD, touches one group.
 set(live,npc,true);checked_flags=0;RevertBbscNpcOwnFlags();assert(!bit(live,npc));
 const auto group_flags=std::ranges::count_if(BbscNpcQuestFlags,[&](u32 flag){return flag/1000==npc/1000;});
 assert(checked_flags==group_flags);
 checked_flags=0;RevertBbscNpcOwnFlags();assert(checked_flags==0);
 // SetFlag can update the desired value even if a native write restores the old byte
 // before the next pass. Its notification must invalidate an otherwise warm group.
 set(live,npc,true);NoteBbscNpcOwnFlag(npc,1);set(live,npc,false);
 RevertBbscNpcOwnFlags();assert(bit(live,npc));
 // A direct native completion must also become visible with the group warmed.
 set(live,ritual,false);RevertBbscNpcOwnFlags();assert(journal.back()==std::pair(ritual,u8(0)));
 set(live,ritual,true);RevertBbscNpcOwnFlags();assert(journal.back()==std::pair(ritual,u8(1)));
 // Memory can become inaccessible or be replaced on reload.
 NoteBbscNpcOwnFlag(npc,0);set(live,npc,true);readable_groups=false;
 RevertBbscNpcOwnFlags();assert(bit(live,npc)&&bbsc_npc_own[npc]==0);
 readable_groups=true;RevertBbscNpcOwnFlags();assert(!bit(live,npc));
 auto previous=live.extract(npc/1000);set(live,npc,true);
 RevertBbscNpcOwnFlags();assert(!bit(live,npc));
 printf("PASS personal flags: %td protected flags in %d groups, 0 rechecked unchanged, %td on one changed group\n",
        all_flags,groups,group_flags);

 // With both native observers available, exactly these flags stop polling.
 bbsc_native_item_completion_hook_ready=true;
 bbsc_npc_checked_groups.clear();bbsc_npc_own.clear();journal.clear();
 const auto& observed=BbscNpcFlagPassFlags().observed_at_write;
 assert(observed.size()==17 && !IsBbscEventWrittenItemStateFlag(6671) && !IsBbscEventWrittenItemStateFlag(9470));
 group_resolves=0;RevertBbscNpcOwnFlags();
 assert(group_resolves==23 && !bbsc_npc_checked_groups.contains(12300));
 for(u32 flag:observed) {
  set(live,flag,false);set(bbsc_own_world,flag,false);
  const auto before=journal.size();
  GuestRegisterSnapshot regs{};regs.rax=(flag%1000)/8;regs.r8=flag/1000*1000;regs.r14=7-(flag%8);
  BbscNativeItemCompletionHook(0,&regs);
  assert(journal.size()==before+1 && journal.back()==std::pair(flag,u8(1)));
  assert(!bit(live,flag) && bit(bbsc_own_world,flag)); // the native store still owns live memory
  const auto writes=own_writes;
  BbscNativeItemCompletionHook(0,&regs);
  assert(own_writes==writes); // same completion cannot rewrite the own-world file
  RecordBbscNativeItemSetFlag(fixture_manager,flag,false);
  assert(journal.back()==std::pair(flag,u8(0)) && !bit(bbsc_own_world,flag));
 }
 // Initial reads are shared by the native load and playable guest edges. A loaded zero never
 // clears an existing personal completion; a confirmed SetFlag zero can.
 set(live,ritual,true);set(live,9421,false);set(bbsc_own_world,9421,true);
 guest=false;SeedBbscNativeItemStateAtLoad();assert(!bit(bbsc_own_world,ritual));
 guest=true;SeedBbscNativeItemStateAtLoad();
 assert(bit(bbsc_own_world,ritual) && bit(bbsc_own_world,9421));
 const auto load_reads=group_resolves;SeedBbscNativeItemStateAtLoad();assert(group_resolves==load_reads);
 ++bbsc_load_generation;SeedBbscNativeItemStateAtLoad();assert(group_resolves>load_reads);
 RecordBbscNativeItemSetFlag(fixture_manager,9421,false);assert(!bit(bbsc_own_world,9421));
 set(live,ritual,false);set(bbsc_own_world,ritual,false);live.erase(ritual/1000);
 const auto no_group=journal.size();
 RecordBbscNativeItemSetFlag(fixture_manager,ritual,true);assert(journal.size()==no_group);
 RecordBbscNativeItemSetFlag(fixture_manager+1,9421,true);assert(journal.size()==no_group);
 guest=false;SeedBbscNativeItemStateAtLoad();assert(journal.size()==no_group);
 GuestRegisterSnapshot invalid{};invalid.rax=125;invalid.r8=9000;
 BbscNativeItemCompletionHook(0,&invalid);assert(journal.size()==no_group);
 puts("PASS native completion and SetFlag: all 17 direct flags, one load seed, no duplicate save, 32 -> 23 periodic groups");
 OriginalFixture();
}
'''
if len(sys.argv)>1 or ELF.is_file():
    values=','.join(map(str,original_completion()))
    code+=f'void OriginalFixture(){{const u8 original[]={{{values}}};TestNativeCompletion(original);}}\n'
else:
    code+='void OriginalFixture(){}\n'
with tempfile.TemporaryDirectory(prefix='bbsc-native-pickup-state-') as folder:
    path=Path(folder);cpp=path/'fixture.cpp';exe=path/'fixture.exe'
    cpp.write_text(code,encoding='utf-8')
    compiler='C:/msys64/clang64/bin/clang++.exe'
    subprocess.run([compiler,'-std=c++20','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
                    '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),
                    str(cpp),str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],env=env,check=True)
print('PASS: native completion not rolled back, remote NPC isolation, immediate exact pickup '
      'receipt in own snapshot, repeated recording and foreign-dungeon/missing-baseline guards')
