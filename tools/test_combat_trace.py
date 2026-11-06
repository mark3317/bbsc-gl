"""Production opt-in combat observer: timing, memory read-only and load fences."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include <atomic>
#include <cassert>
#include <mutex>
#include <string_view>
#include "core/bbsc_world_control.h"
#include "core/bbsc_world_native_initial.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI
struct GuestRegisterSnapshot{u64 rdi{},rsi{},r14{};};
int logs=0,reads=0;template<class... A>void Log(A&&...){++logs;}
#define BBSC_TIMELINE(...) Log(__VA_ARGS__)
bool requested=true,timeline=true,active=true;u32 map=0x17000000;int session=6;
bool EnvFlagEnabled(const char*){return requested;}bool BbscTimelineEnabled(){return timeline;}
bool BbscIndependentActive(){return active;}u32 GetCurrentPackedMap(){return map;}s32 GetSessionState(){return session;}
s64 now=1000;s64 SteadyNowMs(){return now;}
std::atomic<u64> bbsc_world_native_load{1};std::atomic<bool> bbsc_world_load_pending{false},bbsc_reload_finish_pending{false};
std::mutex bbsc_world_presence_mutex;World::Presence bbsc_world_presence_local;
std::array<u8,0xb00> world{};
std::array<u8,0x600> sync{},entry{},record{},slots{},actor{},replacement{},control{},proxy{},modules{},action{},word{};
struct Region{u64 at;size_t bytes;};std::vector<Region> regions;
u64 addr(auto& a){return reinterpret_cast<u64>(a.data());}
template<class T>void put(auto& a,size_t at,T value){memcpy(a.data()+at,&value,sizeof(value));}
constexpr u64 CandidateLocalStatePointerOffset=42;u64 image_base=0;
bool ReadablePointer(u64 at,size_t bytes){
 for(const auto r:regions)if(at>=r.at && at-r.at<=r.bytes && bytes<=r.bytes-(at-r.at))return true;
 return false;
}
template<class T>T ReadValue(u64 at,size_t offset){++reads;
 if(at==CandidateLocalStatePointerOffset)return static_cast<T>(addr(world));
 assert(ReadablePointer(at+offset,sizeof(T)));T result;memcpy(&result,reinterpret_cast<void*>(at+offset),sizeof(result));return result;
}
u32 owner=11;u32 BbscWorldBlockOwner(u32){return owner;}
s32 GetCharacterHp(u64 a){return ReadValue<s32>(a,0x100);}
u64 BbscWorldOwnershipWord(u64,u64){return addr(word);}
u64 checksum(){u64 result=0;for(const auto r:regions){auto* p=reinterpret_cast<u8*>(r.at);
 for(size_t i=0;i<r.bytes;++i)result=result*131+p[i];}return result;}
'''
MAIN=r'''
int main(int argc,char**){
 for(auto* a:{&sync,&entry,&record,&slots,&actor,&replacement,&control,&proxy,&modules,&action,&word})regions.push_back({addr(*a),a->size()});
 regions.push_back({addr(world),world.size()});
 if(argc>1){requested=false;const auto before=checksum();
  TraceBbscCombatActor("hit-selection",addr(actor),0,true);TickBbscCombatTrace();
  assert(reads==0&&logs==0&&before==checksum());return 0;}
 bbsc_world_presence_local.world={11,99};bbsc_world_presence_local.visit=1;
 put(world,0xa40,addr(sync));put(sync,8,u32(1));put(sync,0x10,addr(entry));put(entry,8,addr(record));
 put(record,0,s32(1));put(record,8,addr(slots));put(slots,0,addr(actor));
 put(actor,0x90,u32(0));put(actor,0x100,s32(100));put(actor,0x18,addr(control));put(actor,0x3b0,addr(modules));
 put(modules,8,addr(action));put(control,0x30,addr(proxy));put(control,0x10,s32(4));put(control,0x14,s32(4));
 auto before=checksum();TraceBbscCombatActor("hit-selection",addr(actor),0,true);assert(before==checksum());
 assert(bbsc_combat_watches.size()==1&&bbsc_combat_watches.at(0).last.hp==100);
 GuestRegisterSnapshot r;r.rdi=addr(actor);r.rsi=0;before=checksum();BbscCombatNativeHook(0,&r);assert(before==checksum());
 const auto repeated=logs;BbscCombatNativeHook(0,&r);assert(logs==repeated); // repeated zero request is not a new event
 put(actor,0x100,s32(0));now+=16;TickBbscCombatTrace();assert(bbsc_combat_watches.at(0).last.hp==0);
 assert(bbsc_combat_watches.at(0).last.death==0);
 put(actor,0x1e3,u8(6));put(action,0x1b4,s32(2));now+=1500;before=checksum();TickBbscCombatTrace();
 assert(before==checksum()&&bbsc_combat_watches.at(0).last.death==6&&bbsc_combat_watches.at(0).last.action==2);
 replacement=actor;put(slots,0,addr(replacement));TickBbscCombatTrace();assert(bbsc_combat_watches.at(0).last.actor==addr(replacement));
 put(slots,0,u64(0));before=checksum();TickBbscCombatTrace();assert(before==checksum()&&!bbsc_combat_watches.at(0).last.actor);
 put(slots,0,addr(actor));owner=22;TickBbscCombatTrace();assert(bbsc_combat_watches.at(0).last.owner==22);
 std::array<u8,12> packet{};
 for(int i=0;i<1000;++i)TraceBbscCombatPacket("send-intent",0x15,22,packet,true);
 assert(bbsc_combat_packet_lines==128&&bbsc_combat_lines<512); // actor transitions keep a separate reserve
 now+=15001;TickBbscCombatTrace();assert(bbsc_combat_watches.empty());
 auto watch=[&]{TraceBbscCombatActor("hit-selection",addr(actor),0,true);assert(!bbsc_combat_watches.empty());};
 watch();++bbsc_world_native_load;TickBbscCombatTrace();assert(bbsc_combat_watches.empty());
 watch();++bbsc_world_presence_local.visit;TickBbscCombatTrace();assert(bbsc_combat_watches.empty());
 watch();++bbsc_world_presence_local.world.room;TickBbscCombatTrace();assert(bbsc_combat_watches.empty());
 watch();++map;TickBbscCombatTrace();assert(bbsc_combat_watches.empty());
 watch();session=3;TickBbscCombatTrace();assert(bbsc_combat_watches.empty());
 watch();bbsc_world_load_pending=true;TickBbscCombatTrace();assert(bbsc_combat_watches.empty());bbsc_world_load_pending=false;
 watch();timeline=false;const auto disabled_reads=reads;TickBbscCombatTrace();TraceBbscCombatActor("hit",addr(actor),0,true);
 assert(reads==disabled_reads);timeline=true;
 bbsc_combat_lines=512;const auto bounded_reads=reads;TickBbscCombatTrace();assert(reads==bounded_reads);
 assert(bbsc_combat_watches.size()<=8);
}
'''

def main():
    source=(ROOT/'emulator/src/core/bbsc_combat_trace.inc').read_text(encoding='utf-8')
    assert 'WriteValue' not in source and 'const_cast' not in source
    compiler=shutil.which('clang++') or 'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-combat-trace-') as tmp:
        cpp,exe=Path(tmp)/'trace.cpp',Path(tmp)/'trace.exe'
        cpp.write_text(PREFIX+source+MAIN,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-Wall','-Wextra','-Werror','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],env=env,check=True,timeout=10)
        subprocess.run([str(exe),'disabled'],env=env,check=True,timeout=10)
    print('PASS production combat observer: opt-in, HP0/death distinction, read-only, fresh resolution, scope/load fences, expiry and bounded logging')

if __name__=='__main__':main()
