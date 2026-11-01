"""Production inventory barrier: never open a guest world before its generation is reconciled."""
from pathlib import Path
import os, subprocess, tempfile
src=(Path(__file__).resolve().parents[1]/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
 start=src.index(signature+' {'); end=src.index('{',start)+1; depth=1
 while depth:
  depth+=(src[end]=='{')-(src[end]=='}'); end+=1
 return src[start:end]
prefix=r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <string>
#include <string_view>
#include <mutex>
using u64=uint64_t; using u32=uint32_t; using u8=uint8_t;
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
bool world_ready=true, quitting=false;

bool BbscQuitInProgress(){return quitting;}
int state=6, loading=0, fades=0; u64 global=0x10000;
u64 GetGlobalState(){return global;}
int GetSessionState(){return state;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64,size_t){return static_cast<T>(loading);}
std::atomic<u64> bbsc_world_load_pending{0};
std::atomic<bool> bbsc_reload_finish_pending{false};
std::atomic<u32> bbsc_load_generation{1};
u32 bbsc_ledger_guest_ready_generation=0;
struct Cover { bool active=true,own_screen=false; long long started_ms=0; std::string why="summon"; } bbsc_load_cover;
std::string bbsc_load_cover_pending_end;
void KeepClosingBbscLoadingScreen(std::string_view){}
bool BbscCurtainActive(){return false;}
void BbscFadeTo(float,float){++fades;}
constexpr float BbscCurtainFadeInS=1;
long long SteadyNowMs(){return 3000;}
'''
prefix+=r'''
u32 current_map=0x18010000; bool mounted=true, needs_load=false, resident=false;
std::mutex bbsc_follow_mutex;
struct Follow {long long received_ms=1; u32 packed_map=0x18010000;} bbsc_follow_latest;
u64 GetLocalPlayerCharacter(){return 0x20000;}
int GetCharacterHp(u64){return world_ready?100:0;}
u32 GetCurrentPackedMap(){return current_map;}
bool IsUsablePackedMap(u32 m){return m!=0&&m!=0xffffffff;}
bool BbscChaliceArrivalReady(u32){return mounted;}
bool BbscChaliceNeedsLoad(u32){return needs_load;}
u32 BbscMapArea(u32 m){return m>>24;}
bool BbscMapResident(u32){return resident;}
'''
code=prefix+function('bool BbscGuestWorldReady()')+function('bool BbscGuestLoadItemsReady()')+function('void EndBbscLoadCover(std::string_view how)')+r'''
int main(){
 assert(BbscGuestWorldReady());
 bbsc_follow_latest.packed_map=0x15000000;resident=true;assert(!BbscGuestWorldReady());
 bbsc_follow_latest.packed_map=0x18020000;assert(BbscGuestWorldReady());
 resident=false;assert(!BbscGuestWorldReady());
 bbsc_follow_latest.packed_map=current_map;mounted=false;assert(!BbscGuestWorldReady());
 mounted=true;needs_load=true;assert(!BbscGuestWorldReady());needs_load=false;
 bbsc_follow_latest.received_ms=0;assert(!BbscGuestWorldReady());bbsc_follow_latest.received_ms=1;

 EndBbscLoadCover("placed");assert(bbsc_load_cover.active&&fades==0);
 bbsc_ledger_guest_ready_generation=1;loading=1;
 EndBbscLoadCover("placed");assert(fades==0);
 loading=0;bbsc_world_load_pending=global;
 EndBbscLoadCover("placed");assert(fades==0);
 bbsc_world_load_pending=0;bbsc_reload_finish_pending=true;
 EndBbscLoadCover("placed");assert(fades==0);
 bbsc_reload_finish_pending=false;
 EndBbscLoadCover("placed");assert(fades==1&&!bbsc_load_cover.active);
 EndBbscLoadCover("placed");assert(fades==1);
 bbsc_load_cover.active=true;bbsc_load_generation=2;
 EndBbscLoadCover("placed");assert(fades==1); // previous load is not ready
 EndBbscLoadCover("time limit");assert(fades==1); // no uncovering an unreconciled world
 bbsc_ledger_guest_ready_generation=2;world_ready=false;
 EndBbscLoadCover("placed");assert(fades==1);
 world_ready=true;EndBbscLoadCover("placed");assert(fades==2);
 bbsc_load_cover.active=true;state=0;
 EndBbscLoadCover("no session");assert(fades==3); // departure cannot wait for guest items
}
'''
with tempfile.TemporaryDirectory() as tmp:
 cpp=Path(tmp)/'test.cpp'; exe=Path(tmp)/'test.exe';cpp.write_text(code)
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('Production load readiness barrier: PASS')
