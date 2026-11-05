"""Production gates + real native death predicate/trampoline, fake actors only.

Usage: python tools/test_quest_rewards.py <read-only analysis ELF>
Optional BB_GAME also checks generated rules against original game events.
"""
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
personal = re.search(r'constexpr std::array<u32, (\d+)> BbscNpcQuestFlags\{(.*?)\n\};', source, re.S)
personal_flags = list(map(int, re.findall(r'\b\d+\b', personal[2])))
assert len(personal_flags) == int(personal[1]) and personal_flags == sorted(set(personal_flags))
rules_header = (root / 'emulator/src/core/bbsc_quest_reward_rules.h').read_text(encoding='utf-8')
required = {int(flag) for flag in re.findall(r'\{\d+, (\d+), (?:true|false)\}', rules_header)}
assert required <= set(personal_flags), f'NPC states not kept personal: {required - set(personal_flags)}'

# The extractor must retain potentially legitimate conditional paths, and must
# not invent an inactive default when the script leaves that actor unchanged.
sys.path.insert(0, str(root / 'tools/gamedata'))
from quest_reward_rules import extract
actor = 2410999
branch = lambda label, flag: (1003, 101, struct.pack('<BBxxi', label, 1, flag))
toggle = lambda disabled: (2004, 29, struct.pack('<ii', actor, disabled))
end = (1000, 4, struct.pack('<i', 0))
script = [branch(1, 1200), branch(2, 1201), toggle(1), end,
          (1014, 1, b''), toggle(1), (1000, 101, struct.pack('<BBbx', 3, 1, 1)), end,
          (1014, 2, b''), toggle(1), (2004, 37, struct.pack('<i', actor)), end,
          (1014, 3, b''), toggle(0), end]
assert extract(script) == {actor: [(1200, True), (1201, True)]}
unknown_default = list(script)
unknown_default[2] = (2000, 5, struct.pack('<i', 0))
assert extract(unknown_default) is None
unresolved_child = list(script)
unresolved_child[5] = (2000, 0, struct.pack('<iii', 0, 12345678, 0))
assert extract(unresolved_child) is None


def function(signature):
    begin = source.index(signature + ' {')
    end = source.index('{', begin) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[begin:end]


elf = Path(sys.argv[1]).read_bytes()
phoff = struct.unpack_from('<Q', elf, 32)[0]
size, count = struct.unpack_from('<HH', elf, 54)
segments = [struct.unpack_from('<IIQQQQQQ', elf, phoff + i * size) for i in range(count)]


def read(address, length):
    for kind, _, offset, virtual, _, size, _, _ in segments:
        if kind == 1 and virtual <= address and address + length <= virtual + size:
            return elf[offset + address - virtual:offset + address - virtual + length]
    raise ValueError(hex(address))


native = read(0x179F940, 0x130)  # complete evaluator and its relative switch table
assert native[:7] == bytes.fromhex('55 48 89 e5 41 56 53')
# Exact native lookup/entity/result fields used by the production hook.
assert bytes.fromhex('8b 7b 2c') in native
assert bytes.fromhex('0f b6 43 28') in native
assert bytes.fromhex('0f b6 4b 29') in native
assert bytes.fromhex('88 4b 10') in native

code = r'''
#include <windows.h>
#include <cassert>
#include <cstring>
#include <set>
#include <vector>
#include <mutex>
#include <map>
#include <string>
#include <atomic>
#include <utility>
#include <cstdio>
#include "core/cpu_patches.h"
#include "core/bbsc_quest_reward_rules.h"
using Core::GuestRegisterSnapshot;
namespace QuestRules=Core::Bloodborne::QuestRules;
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
namespace fmt { template<class... T> std::string format(const char*,T...){return {};}}
u64 image_base,actor_address,info_address;
bool guest=true,own=true,free_bell=true;
std::set<u32> flags;
namespace BbscMod{u64 EbootAddress(){return image_base;} void LogPlain(const char* s){puts(s);}}
bool BbscOwnNpcQuestsEnabled(){return own;}
bool BbscGuestInHostWorld(){return guest;}
bool BbscEventFlag(u32 f){return flags.contains(f);}
bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64 p,size_t off){T v;memcpy(&v,(void*)(p+off),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t off,T v){memcpy((void*)(p+off),&v,sizeof(v));}
bool EnvFlagEnabled(const char* name){return strcmp(name,"SHADPS4_BBSC_FREE_BELL")?true:free_bell;}
int GetLocalPlayerType(){return 1;}u64 GetLocalPlayerCharacter(){return 0x123;}
bool IsEbootCodeAddress(u64 a){return a>=image_base && a<image_base+0x6000000;}
enum class BbscWork{GuestDrop};void QueueBbscWork(BbscWork){}
bool bbsc_native_enemy_loot_ready=true;
std::set<std::pair<u64,u32>> bbsc_native_loot_deaths;
u32 bbsc_native_loot_generation=~u32{0};std::atomic<u32> bbsc_load_generation{0};
u8 bbsc_quest_death_skip=0,bbsc_bell_refund_skip=0;
s64 BbscRunningEventId(u64){return 9183;}
s64 now=1000;s64 SteadyNowMs(){return now;}u32 GetCurrentPackedMap(){return 0x18010000;}
constexpr u64 ItemManagerPointerOffset=0x0553d6e0,EventFlagManPointerOffset=0x0553b100,ItemEnableOffset=0x017d9e70;
std::map<u32,u64> bbsc_script_hidden_items;
int enable_calls=0;u64 item_address=0;
u64 PS4_SYSV_ABI FindItem(u64,u32){return item_address;}
u64 PS4_SYSV_ABI EnableItem(u64,u32*,u32 on){assert(on==0);++enable_calls;WriteValue<u16>(item_address,0x48,0);return 1;}
u64 PS4_SYSV_ABI Find(u32 id,u64,u64){return id==2410781?actor_address:0;}
u64 PS4_SYSV_ABI Info(u64){return info_address;}
void stub(u64 off,u64 target){u8 b[12]={0x48,0xb8};memcpy(b+2,&target,8);b[10]=0xff;b[11]=0xe0;memcpy((void*)(image_base+off),b,12);}
'''
for signature in ['bool BbscNpcRewardAllowed(u32 entity)',
                  'bool BbscNpcReceiptAllowed(u32 receipt)',
                  'bool BbscNpcActorRewardAllowed(u64 actor)',
                  'void PS4_SYSV_ABI BbscQuestDeathHook(u64, const GuestRegisterSnapshot* registers)',
                  'void PS4_SYSV_ABI BbscNativeEnemyLootHook(u64 tag, const GuestRegisterSnapshot* registers)',
                  'void PS4_SYSV_ABI BbscBellRefundHook(u64, const GuestRegisterSnapshot* registers)',
                  'void PS4_SYSV_ABI BbscTreasureVisibilityHook(u64, const GuestRegisterSnapshot* registers)',
                  'void TickBbscGuestItemsPickable()']:
    code += function(signature) + '\n'
code += r'''
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image_base);
 const u8 native[]={NATIVE};memcpy((void*)(image_base+0x179f940),native,sizeof(native));
 alignas(16) u8 actor[0x400]={},holder[0x40]={},life[0x40]={},condition[0x40]={},row[0x160]={};
 u64 vtable[0x40]={},info[2]={0,(u64)row};
 actor_address=(u64)actor;info_address=(u64)info;
 WriteValue<u64>((u64)actor,0x18,(u64)holder);WriteValue<u64>((u64)holder,0x30,(u64)life);
 life[0x18]=1; // native dead bit, as may be replicated even for an inactive actor
 WriteValue<u64>(image_base,0x553b0c8,1);stub(0x13c97a0,(u64)Find);stub(0x1000,(u64)Info);
 using Check=void PS4_SYSV_ABI (*)(u64);
 auto check=(Check)(image_base+0x179f940);
 condition[0x29]=1;WriteValue<u32>((u64)condition,0x2c,2410781);
 flags={1240};check((u64)condition);assert(condition[0x10]&1); // original accepts inactive NPC
 const u8 prologue[]={0x55,0x48,0x89,0xe5,0x41,0x56,0x53};
 assert(Core::InstallGuestCodeHook((void*)check,std::span<const u8>{prologue},0,BbscQuestDeathHook,&bbsc_quest_death_skip));
 for(u32 phase:{1240,1241,1242,1243,1244}){
  flags={phase};condition[0x10]=0xa5;check((u64)condition);assert(condition[0x10]==0xa4);
 }
 flags.clear();check((u64)condition);assert(!(condition[0x10]&1));
 for(u32 phase:{1246,1245}){flags={phase};check((u64)condition);assert(condition[0x10]&1);}
 flags={1240,1246};check((u64)condition);assert(!(condition[0x10]&1)); // native first branch wins
 flags={1246};life[0x18]=0;check((u64)condition);assert(!(condition[0x10]&1)); // no synthetic death
 condition[0x29]=0;flags={1240};check((u64)condition);assert(condition[0x10]&1); // alive test intact
 condition[0x29]=1;life[0x18]=1;guest=false;check((u64)condition);assert(condition[0x10]&1);
 guest=true;own=false;check((u64)condition);assert(condition[0x10]&1);own=true;
 // Native body-loot eligibility uses exactly the same personal NPC gate.
 WriteValue<u64>((u64)actor,0,(u64)vtable);vtable[0x168/8]=image_base+0x1000;
 WriteValue<u32>((u64)actor,0x278,2410781);WriteValue<s32>((u64)row,0x2c,29010);WriteValue<s32>((u64)row,0x30,-1);
 GuestRegisterSnapshot loot{};alignas(16) u8 loot_life[0x100]={};
 loot.rbx=(u64)actor;loot.rax=(u64)loot_life;
 flags={1240};BbscNativeEnemyLootHook(0,&loot);assert(ReadValue<s32>(loot.rax,0xf8)==0);
 loot.rax=(u64)loot_life;flags={1246};BbscNativeEnemyLootHook(0,&loot);assert(ReadValue<s32>(loot.rax,0xf8)==1);
 // Scripted ForceCharacterTreasure is blocked independently of native death reward.
 alignas(16) u8 instance[0xc0]={},instruction[0x20]={};u32 args[3]={2410781,0,0};
 WriteValue<u64>((u64)instance,0xb0,(u64)instruction);WriteValue<u64>((u64)instance,0xb8,(u64)args);
 WriteValue<s32>((u64)instruction,0,2004);WriteValue<s32>((u64)instruction,4,37);
 GuestRegisterSnapshot r{};r.rsi=(u64)instance;flags={1240};BbscBellRefundHook(0,&r);
 assert(bbsc_bell_refund_skip&&r.rax==1);bbsc_bell_refund_skip=0;
 flags={1245};BbscBellRefundHook(0,&r);assert(!bbsc_bell_refund_skip);
 free_bell=false;flags={1240};BbscBellRefundHook(0,&r);assert(bbsc_bell_refund_skip);bbsc_bell_refund_skip=0;
 WriteValue<s32>((u64)instruction,4,8);args[0]=10000;args[1]=4680;
 BbscBellRefundHook(0,&r);assert(!bbsc_bell_refund_skip);free_bell=true;BbscBellRefundHook(0,&r);assert(bbsc_bell_refund_skip);
 // Other NPC variants obey their own dispatchers; unrelated enemies remain native.
 flags={1181};assert(BbscNpcRewardAllowed(2400730)&&!BbscNpcRewardAllowed(2400732));
 flags={1189};assert(!BbscNpcRewardAllowed(2400730)&&BbscNpcRewardAllowed(2400732));
 flags={1220};assert(!BbscNpcRewardAllowed(2400750));flags={1224};assert(BbscNpcRewardAllowed(2400750));
 flags.clear();assert(BbscNpcRewardAllowed(2410001));
 for(const auto& state:QuestRules::NpcRewardStates){
  flags.clear();assert(!BbscNpcRewardAllowed(state.entity));
  flags={state.flag};
  auto first=std::find_if(QuestRules::NpcRewardStates.begin(),QuestRules::NpcRewardStates.end(),
    [&](auto row){return row.entity==state.entity&&row.flag==state.flag;});
  assert(BbscNpcRewardAllowed(state.entity)==first->allowed);
 }
 flags={1240};assert(!BbscNpcReceiptAllowed(50001300));flags={1246};assert(BbscNpcReceiptAllowed(50001300));
 flags={1181};assert(BbscNpcReceiptAllowed(50001000));flags={1187};assert(!BbscNpcReceiptAllowed(50001000));
 // White-ribbon/chest regression: explicit script hiding wins and the periodic
 // pass NEVER enables a disabled pickup, even when its receipt flag is clear.
 alignas(16) u8 manager[0x60]={},item[0xc0]={};item_address=(u64)item;
 WriteValue<u64>(image_base,ItemManagerPointerOffset,(u64)manager);WriteValue<u64>(image_base,EventFlagManPointerOffset,1);
 WriteValue<u64>((u64)manager,0x18,(u64)item);WriteValue<u32>((u64)item,0x20,0x53);
 stub(ItemEnableOffset,(u64)EnableItem);stub(0x017d81a0,(u64)FindItem);
 TickBbscGuestItemsPickable();assert(enable_calls==0&&ReadValue<u16>((u64)item,0x48)==0);
 now+=1000;WriteValue<u16>((u64)item,0x48,0x40);TickBbscGuestItemsPickable();assert(enable_calls==0); // legitimate pickup
 u64 caller=image_base+0x0131cf94;u32 itemid=0x53;
 r={};r.rsp=(u64)&caller;r.rsi=(u64)&itemid;r.rdi=(u64)manager;
 BbscTreasureVisibilityHook(0,&r);assert(bbsc_script_hidden_items[0x53]==(u64)item);
 now+=1000;TickBbscGuestItemsPickable();assert(enable_calls==1&&ReadValue<u16>((u64)item,0x48)==0);
 r.rdx=1;BbscTreasureVisibilityHook(0,&r);assert(bbsc_script_hidden_items.empty());
 now+=1000;TickBbscGuestItemsPickable();assert(enable_calls==1); // a script permit does not force periodic enable
 WriteValue<u16>((u64)item,0x48,0x40);WriteValue<s32>((u64)item,0x28,52410900);flags={52410900};
 now+=1000;TickBbscGuestItemsPickable();assert(enable_calls==2); // actual taken-item flag still hides
 flags.clear();WriteValue<s32>((u64)item,0x28,0);WriteValue<u16>((u64)item,0x48,0x40);
 bbsc_script_hidden_items[0x53]=(u64)item+0x100;now+=1000;TickBbscGuestItemsPickable();assert(enable_calls==2); // recycled numeric ID
 // Native/network item creation is covered even outside SetTreasureState.
 bbsc_script_hidden_items.clear();WriteValue<s32>((u64)item,0x28,50001300);flags={1240};
 caller=image_base+0x1234;r.rdx=1;BbscTreasureVisibilityHook(0,&r);assert(r.rdx==0&&bbsc_script_hidden_items.empty());
 WriteValue<u16>((u64)item,0x48,0x40);now+=1000;TickBbscGuestItemsPickable();assert(enable_calls==3);
 flags={1246};r.rdx=1;BbscTreasureVisibilityHook(0,&r);assert(r.rdx==1); // valid native enable stays valid
 WriteValue<u16>((u64)item,0x48,0x40);now+=1000;TickBbscGuestItemsPickable();assert(enable_calls==3);
 puts("PASS: real native inactive death reproduced; quest states, trampoline, valid deaths, drops/visibility, white ribbon/chests");
}
'''
code = code.replace('NATIVE', ','.join(map(str, native)))
compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
with tempfile.TemporaryDirectory(prefix='bbsc-quest-rewards-') as tmp:
    cpp, exe = Path(tmp) / 'test.cpp', Path(tmp) / 'test.exe'
    cpp.write_text(code, encoding='utf-8')
    subprocess.run([compiler, '-std=c++20', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
        '-I', str(root / 'emulator/src'), '-I', str(root / 'emulator/externals/xbyak'),
        str(cpp), str(root / 'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], check=True, timeout=15, env=env)
if os.environ.get('BB_GAME'):
    subprocess.run([sys.executable, '-I', str(root / 'tools/gamedata/quest_reward_rules.py'), '--check'], check=True)
