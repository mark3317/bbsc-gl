"""Permanent shared-key receipts survive trip completion and a journal reload."""
from pathlib import Path
import os, subprocess, tempfile
src=(Path(__file__).resolve().parents[1]/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
 start=src.index(signature+' {'); end=src.index('{',start)+1; depth=1
 while depth:
  depth+=(src[end]=='{')-(src[end]=='}'); end+=1
 return src[start:end]
a=src.index('constexpr std::array<u32, 25> BbscSharedKeyItems{')
b=src.index('static_assert',a)
code=r'''
#include <algorithm>
#include <array>
#include <map>
#include <vector>
#include <mutex>
#include <cstdint>
#include <cassert>
using u32=uint32_t;
enum class BbscLedgerState { Given, Owed };
struct BbscLedgerEntry { BbscLedgerState state; };
std::mutex bbsc_ledger_mutex;
std::vector<BbscLedgerEntry> bbsc_ledger;
std::map<u32,int> bbsc_ledger_trip, bbsc_ledger_host_counts, disk;
bool bbsc_ledger_dirty=false;
void WriteBbscLedgerLocked(){disk=bbsc_ledger_trip;}
'''+src[a:b]+function('void FinishBbscTripAtHome()')+r'''
int main(){
 for(auto id:BbscSharedKeyItems) bbsc_ledger_trip[0x40000000u|id]=1;
 bbsc_ledger_trip[0x40000123]=5;
 bbsc_ledger_trip[0x10000fa0]=1; // same id, wrong category
 bbsc_ledger.push_back({BbscLedgerState::Given});
 bbsc_ledger.push_back({BbscLedgerState::Owed});
 FinishBbscTripAtHome();
 assert(bbsc_ledger_trip.size()==BbscSharedKeyItems.size());
 assert(bbsc_ledger.size()==1 && bbsc_ledger[0].state==BbscLedgerState::Owed);
 bbsc_ledger_trip.clear();bbsc_ledger_trip=disk; // restart: existing serialized journal
 FinishBbscTripAtHome();
 for(auto id:BbscSharedKeyItems) assert(bbsc_ledger_trip.at(0x40000000u|id)==1);
}
'''
tick=function('void TickBbscSharedKeyItems()')
assert tick.index('if (!BbscGuestLoadItemsReady()) return;') < tick.index('const u32 items =')
assert tick.index('if (received)') < tick.index('ShowBbscItemPopup')
assert 'if (BbscLedgerCount(code) == 0 && !AddBbscLedgerItem(code, 1)) continue;' in tick
with tempfile.TemporaryDirectory() as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text(code)
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('Shared keys permanent receipts and restore ordering: PASS')
