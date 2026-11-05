"""Permanent shared-key receipts survive trip completion and a journal reload."""
from pathlib import Path
import os, subprocess, tempfile
src=(Path(__file__).resolve().parents[1]/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
 start=src.index(signature+' {'); end=src.index('{',start)+1; depth=1
 while depth:
  depth+=(src[end]=='{')-(src[end]=='}'); end+=1
 return src[start:end]
a=src.index('constexpr std::array<u32, 25> BbscPermanentKeyReceipts{')
b=src.index('// Retain receipts',a)
code=r'''
#include <algorithm>
#include <array>
#include <map>
#include <vector>
#include <mutex>
#include <cstdint>
#include <cassert>
#include <string_view>
using s32=int32_t;
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
using u32=uint32_t;
std::map<u32,int> inventory;int restore_adds=0;
bool BbscLedgerAddable(u32){return true;}
int BbscLedgerCount(u32 id){return inventory[id];}
bool AddBbscLedgerItem(u32 id,int count){inventory[id]+=count;restore_adds+=count;return true;}
enum class BbscLedgerState { Given, Owed };
struct BbscLedgerEntry { BbscLedgerState state; };
std::mutex bbsc_ledger_mutex;
std::vector<BbscLedgerEntry> bbsc_ledger;
std::map<u32,int> bbsc_ledger_trip, bbsc_ledger_host_counts, disk;
bool bbsc_ledger_dirty=false;
void WriteBbscLedgerLocked(){disk=bbsc_ledger_trip;}
'''+src[a:b]+function('void FinishBbscTripAtHome()')+function('size_t CheckBbscTripItems(bool steady, std::string_view where, size_t* short_out = nullptr)')+r'''
int main(){
 // A new guest with no receipts gains nothing: host inventories are irrelevant.
 assert(CheckBbscTripItems(false,"empty")==0&&inventory.empty()&&restore_adds==0);
 for(auto id:BbscPermanentKeyReceipts) bbsc_ledger_trip[0x40000000u|id]=1;
 bbsc_ledger_trip[0x40000123]=5;
 bbsc_ledger_trip[0x10000fa0]=1; // same id, wrong category
 bbsc_ledger.push_back({BbscLedgerState::Given});
 bbsc_ledger.push_back({BbscLedgerState::Owed});
 // Received keys restore from their existing receipts after a load/home return.
 assert(CheckBbscTripItems(false,"after load")==BbscPermanentKeyReceipts.size()+6);
 assert(restore_adds==(int)BbscPermanentKeyReceipts.size()+6);
 auto restored=restore_adds;assert(CheckBbscTripItems(false,"again")==0&&restore_adds==restored);
 FinishBbscTripAtHome();
 assert(bbsc_ledger_trip.size()==BbscPermanentKeyReceipts.size());
 assert(bbsc_ledger.size()==1 && bbsc_ledger[0].state==BbscLedgerState::Owed);
 inventory.clear();bbsc_ledger_trip.clear();bbsc_ledger_trip=disk; // restart: existing serialized journal
 FinishBbscTripAtHome();
 assert(CheckBbscTripItems(false,"restart")==BbscPermanentKeyReceipts.size());
 for(auto id:BbscPermanentKeyReceipts) assert(bbsc_ledger_trip.at(0x40000000u|id)==1);
}
'''
with tempfile.TemporaryDirectory() as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text(code)
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('Permanent personal/legacy key receipts: PASS')
