"""Audit all original global item receipts; replay production code in fake memory.

BB_GAME=dvdroot_ps4 python -B tools/test_native_loot_receipts.py
No real saves, inventory, settings or game processes are changed.
"""
from pathlib import Path
import collections
import os
import struct
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
sys.path.insert(0,str(ROOT/'tools/gamedata'))
import bbfiles
import param
bbfiles.GAME=os.environ['BB_GAME']
ll,_,ld,lr=param.load('ItemLotParam')
nl,_,nd,nr=param.load('NpcParam')
links=collections.defaultdict(set)
for npc,off in nr.items():
    v=param.row_values(nl,nd,off)
    for k in range(1,7):
        if v[f'itemLotId_{k}'] in lr:links[v[f'itemLotId_{k}']].add(npc)
global_rows={}
map_npc=set()
for lot,off in lr.items():
    raw=ld[off:off+0x94]
    main=struct.unpack_from('<i',raw,0x80)[0]
    entry_flags=struct.unpack_from('<8i',raw,0x60)
    assert not any(50000000<=f<50100000 for f in entry_flags), 'Review per-entry receipts before replay'
    if 50000000<=main<50100000:global_rows[lot]=(main,raw)
    if lot in links and main>0 and 21<=(main//1000%10000)//100<=99:map_npc.add(lot)
assert global_rows[29010][0]==50001300
assert global_rows[51000][0]==50003100
assert global_rows[34020][0]==global_rows[34040][0]==50001820

def fun(sig):
    a=s.index(sig+' {');b=s.index('{',a)+1;depth=1
    while depth:
        depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[a:b]+'\n'

code=r'''
#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <map>
#include <mutex>
#include <optional>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;
#define BBSC_TIMELINE(...)
struct BbscSaveSlot{u64 user=1;int slot=0;};
std::optional<s32> bbsc_ledger_loot_cycle;bool bbsc_ledger_dirty=false;
bool WriteBbscLedgerLocked(){return true;}
std::optional<BbscSaveSlot> bbsc_ledger_slot=BbscSaveSlot{};BbscSaveSlot active;
std::optional<BbscSaveSlot> BbscActiveSaveSlot(){return active;}
void SyncBbscLedgerSlot(){}
bool guest=true,enabled=true,params=true,writable=true;u32 map=0x18010000;
bool BbscGuestInHostWorld(){return guest;}
bool EnvFlagEnabled(const char*){return enabled;}
u32 GetCurrentPackedMap(){return map;}
namespace Chalice{bool IsMap(u32 m){return(m>>24)==29;}}
constexpr size_t BbscWorldGroupBytes=125;std::atomic<u32> bbsc_native_loot_receipt_revision{0};
std::atomic<u32> bbsc_load_generation{1};
std::mutex bbsc_ledger_mutex;std::map<s32,u32> bbsc_ledger_lots;
std::map<s32,std::array<u8,0x94>> rows;
std::map<u32,std::array<u8,125>> live;
u64 manager[8]{};std::array<u8,0x38> pointers{};std::array<u8,0x70> game_data{};
constexpr u64 EventFlagManPointerOffset=0x553b100;
u64 image_base=(u64)pointers.data()-EventFlagManPointerOffset;
bool ReadablePointer(u64 p,size_t){return p!=0;}
enum class MemoryProt{CpuWrite};
bool HasMemoryAccess(u64 p,size_t,MemoryProt){return p&&writable;}
template<class T>T ReadValue(u64 p,size_t off){T v;memcpy(&v,(void*)(p+off),sizeof(v));return v;}
u64 BbscLedgerLotRow(s32 lot){return params&&rows.contains(lot)?(u64)rows.at(lot).data():0;}
u64 BbscFlagGroupStorage(u32 key){auto it=live.find(key);return it==live.end()?0:(u64)it->second.data();}
'''
code+=fun('bool IsBbscGlobalLootReceipt(u32 flag)')
code+=fun('std::vector<u32> BbscLotFlags(u64 row)')
code+=fun('void RestoreBbscNativeLootReceipts(bool force)')
code+=r'''
bool bit(u32 f){return live[f/1000][f%1000/8]&(0x80u>>(f%8));}
void clear(u32 f){live[f/1000][f%1000/8]&=~(0x80u>>(f%8));}
void reset(){bbsc_ledger_loot_cycle.reset();game_data.fill(0);++bbsc_load_generation;bbsc_ledger_lots.clear();live.clear();active=BbscSaveSlot{};
 bbsc_ledger_slot=active;guest=enabled=params=writable=true;map=0x18010000;
 manager[5]=(u64)manager;u64 mp=(u64)manager,gp=(u64)game_data.data();
 memcpy(pointers.data(),&mp,8);memcpy(pointers.data()+0x30,&gp,8);
}
int main(){
'''
for lot,(flag,raw) in global_rows.items():
    code+=f'rows[{lot}]={{{",".join(map(str,raw))}}};\n'
code+=r'''
 for(auto& [lot,row]:rows){
  reset();u32 f=ReadValue<u32>((u64)row.data(),0x80);live[f/1000].fill(0);
  RestoreBbscNativeLootReceipts(true);assert(!bit(f)); // not obtained: leave native loot eligible
  bbsc_ledger_lots[lot]=0;RestoreBbscNativeLootReceipts(true);assert(bit(f));
  clear(f);RestoreBbscNativeLootReceipts(false);assert(bit(f)); // native producer reasserts a same-generation reset
  RestoreBbscNativeLootReceipts(true);assert(bit(f)); // actual join callback before generation increment
  clear(f);++bbsc_load_generation;RestoreBbscNativeLootReceipts(false);assert(bit(f));
 }
 // General rejoin regression: actual historical Gilbert receipt survives each native flag reset.
 reset();bbsc_ledger_lots[29010]=0x80018896;live[50001].fill(0);
 live[50001][0]=0x80;RestoreBbscNativeLootReceipts(true);
 assert(bit(50001300)&&live[50001][0]==0x80); // unrelated native flags stay unchanged
 for(int i=0;i<4;++i){clear(50001300);++bbsc_load_generation;RestoreBbscNativeLootReceipts(false);assert(bit(50001300));}
 clear(50001300);++bbsc_load_generation;guest=false;RestoreBbscNativeLootReceipts(false);assert(!bit(50001300));guest=true;
 active.slot=1;RestoreBbscNativeLootReceipts(false);assert(!bit(50001300));active.slot=0;
 map=0x1d000000;RestoreBbscNativeLootReceipts(false);assert(!bit(50001300));map=0x18010000;
 enabled=false;RestoreBbscNativeLootReceipts(false);assert(!bit(50001300));enabled=true;
 params=false;RestoreBbscNativeLootReceipts(false);assert(!bit(50001300));params=true;
 writable=false;RestoreBbscNativeLootReceipts(false);assert(!bit(50001300));writable=true;
 RestoreBbscNativeLootReceipts(false);assert(bit(50001300)); // late readiness was not cached as success
 // A newly recorded lot invalidates the cached masks in the same generation.
 bbsc_ledger_lots[51000]=0x80018895;bbsc_native_loot_receipt_revision.fetch_add(1);
 live[50003].fill(0);RestoreBbscNativeLootReceipts(false);assert(bit(50003100));
 clear(50003100);RestoreBbscNativeLootReceipts(false);assert(bit(50003100));
 // A real native NG+ transition intentionally makes the original drop obtainable again.
 clear(50001300);s32 ng=1;memcpy(game_data.data()+0x68,&ng,4);
 RestoreBbscNativeLootReceipts(false);assert(!bit(50001300)&&!bbsc_ledger_lots.contains(29010));
 bbsc_ledger_lots[29010]=0x80018896;RestoreBbscNativeLootReceipts(true);assert(bit(50001300));
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-native-loot-receipts-') as folder:
    path=Path(folder);cpp=path/'fixture.cpp';exe=path/'fixture.exe'
    cpp.write_text(code,encoding='utf-8')
    compiler='C:/msys64/clang64/bin/clang++.exe'
    subprocess.run([compiler,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],env=env,check=True)
print(f'PASS: {len(global_rows)} original global-receipt lots ({len(set(global_rows)&set(links))} NPC-linked); '
      f'{len(map_npc)} NPC map-receipt lots already in map scope; native bit replay, repeated join, '
      'unclaimed loot, character/dungeon/permission/readiness isolation; no inventory grant')
