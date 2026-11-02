"""Run the production repeated-lot guard against isolated inventory/ledger state."""
from pathlib import Path
import os
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
s = (root / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
a = s.index('bool SkipBbscRepeatedLot(s32 lot, u64 row) {')
b = s.index('// Talk items in the host', a)
fixture = r'''
#include <cstdint>
#include <vector>
#include <unordered_map>
#include <mutex>
#include <cassert>
using u32=uint32_t; using u64=uint64_t; using s32=int32_t; using s16=int16_t;
bool bbsc_ledger_regive=false, flagged=true, addable=true, npc=true;
int count=1, area=24, writes=0; s16 maxnum=99; u64 goodsrow=1;
constexpr int BbscChaliceArea=29;
std::mutex bbsc_ledger_mutex;
std::unordered_map<int,u32> bbsc_ledger_lots;
std::unordered_map<u32,int> bbsc_ledger_own_flags;
std::vector<u32> BbscLotFlags(u64){return flagged?std::vector<u32>{50002000}:std::vector<u32>{};}
bool BbscLedgerAddable(u32){return addable;}
int BbscLedgerCount(u32){return count;}
u64 BbscGameParamTable(const char*){return 1;}
u64 BbscParamRow(u64,u32,int){return goodsrow;}
template<class T> T ReadValue(u64,int){return maxnum;}
int GetCurrentPackedMap(){return area;}
int BbscMapArea(int a){return a;}
int GetSessionState(){return 6;}
bool IsBbscNpcQuestFlag(u32){return npc;}
int SteadyNowMs(){return 123;}
void SetBbscLedgerFlag(u32 f,int value){assert(f==50002000 && value==1);++writes;}
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
''' + s[a:b] + r'''
int main(){
 // First claim is allowed, even when the character owns this goods from elsewhere.
 assert(!SkipBbscRepeatedLot(37000,1));
 bbsc_ledger_lots[37000]=0x400005dc;
 for(int n: {0,1,4}){count=n; assert(SkipBbscRepeatedLot(37000,1));}
 assert(writes==3 && bbsc_ledger_own_flags[50002000]==123);
 assert(!SkipBbscRepeatedLot(999,1)); // another lot remains available
 flagged=false; assert(!SkipBbscRepeatedLot(37000,1)); flagged=true;
 area=29; assert(!SkipBbscRepeatedLot(37000,1)); area=24;
 bbsc_ledger_regive=true; assert(!SkipBbscRepeatedLot(37000,1)); bbsc_ledger_regive=false;
 assert(!SkipBbscRepeatedLot(37000,0));
 goodsrow=0; assert(!SkipBbscRepeatedLot(37000,1)); goodsrow=1;
 maxnum=1; count=0; assert(!SkipBbscRepeatedLot(37000,1));
 count=1; assert(SkipBbscRepeatedLot(37000,1)); // owned unique still blocked
 bbsc_ledger_lots[37000]=100; count=0; assert(!SkipBbscRepeatedLot(37000,1));
 count=1; assert(SkipBbscRepeatedLot(37000,1)); // weapon
 addable=false; count=0; assert(SkipBbscRepeatedLot(37000,1)); // gem/rune
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-award-') as d:
    cpp=Path(d)/'check.cpp'; exe=Path(d)/'check.exe'
    cpp.write_text(fixture,encoding='utf8')
    subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env=dict(os.environ); env['PATH']='C:/msys64/clang64/bin;'+env.get('PATH','')
    subprocess.run([str(exe)],env=env,check=True)
print('PASS: production one-time award guard: repeated/spent consumables, first/different lot, unflagged drops, chalices, explicit regive, unknown rows, unique items')
