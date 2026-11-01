"""Never apply a dungeon transform in a Dream loaded by the native summon."""
from pathlib import Path
import os, subprocess, tempfile
src=(Path(__file__).resolve().parents[1]/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
 start=src.index(signature+' {');end=src.index('{',start)+1;depth=1
 while depth:
  depth+=(src[end]=='{')-(src[end]=='}');end+=1
 return src[start:end]
code=r'''
#include <mutex>
#include <cstdint>
#include <cassert>
using u32=uint32_t;using s64=int64_t;
std::mutex bbsc_follow_mutex;
struct Follow {u32 packed_map=0x1d000000;s64 received_ms=100;} bbsc_follow_latest;
s64 now=200;s64 SteadyNowMs(){return now;}
u32 here=0x15000000;u32 GetCurrentPackedMap(){return here;}
bool IsUsablePackedMap(u32 m){return m!=0&&m!=0xffffffff;}
namespace Chalice {bool IsMap(u32 m){return m>>24==29;}}
bool mounted=false,needs=true,resident=false;
bool BbscChaliceArrivalReady(u32){ // also verify mutex is released before nested scope reads
 assert(bbsc_follow_mutex.try_lock());bbsc_follow_mutex.unlock();return mounted;
}
bool BbscChaliceNeedsLoad(u32){return needs;}
bool BbscMapResident(u32){return resident;}
'''+function('bool BbscJoinDestinationKnown()')+function('bool BbscJoinWorldMatchesHost()')+r'''
int main(){
 assert(BbscJoinDestinationKnown());
 assert(!BbscJoinWorldMatchesHost()); // observed Dream vs host dungeon
 here=0x1d000000;assert(!BbscJoinWorldMatchesHost());
 mounted=true;assert(!BbscJoinWorldMatchesHost());
 needs=false;assert(BbscJoinWorldMatchesHost());
 now=6100;assert(!BbscJoinDestinationKnown());now=99;assert(!BbscJoinDestinationKnown());
 now=200;bbsc_follow_latest.received_ms=0;assert(!BbscJoinDestinationKnown());
 bbsc_follow_latest.packed_map=0x18010000;here=0x18000000;
 assert(!BbscJoinWorldMatchesHost());resident=true;assert(BbscJoinWorldMatchesHost());
 here=0x15000000;assert(!BbscJoinWorldMatchesHost());
}
'''
tick=function('void TickBbscJoinTeleport()')
assert tick.index('if (!BbscJoinDestinationKnown())') < tick.index('ReadCharacterTransform(host)')
assert tick.index('if (!BbscJoinWorldMatchesHost()') < tick.index('ReadCharacterTransform(host)')
with tempfile.TemporaryDirectory() as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text(code)
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('Production join destination/map/mount/freshness gates: PASS')
