"""Run production read-only NPC diagnostics and original backread-off decision.

Allocated fixture memory only; original analysis ELF is a read-only input.
"""
from pathlib import Path
import os
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
data = Path(sys.argv[1]).read_bytes()
ph = struct.unpack_from('<Q', data, 32)[0]
size, count = struct.unpack_from('<HH', data, 54)
segments = [struct.unpack_from('<II6Q', data, ph + i * size) for i in range(count)]

def read(address, length):
    segment = next(s for s in segments if s[0] == 1 and s[3] <= address
                   and address + length <= s[3] + s[5])
    return data[segment[2] + address - segment[3]:segment[2] + address - segment[3] + length]

# Original wake checks Chr+28 BEFORE group overlap, then requests state0.
branch = read(0x019194D7, 20)
unload = read(0x019196AB, 11)
assert branch == bytes.fromhex('807f2800 0f85ca010000 807f2900 0f8575010000')
assert unload == bytes.fromhex('488b4718 c7401400000000')

prefix = r'''
#include <windows.h>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <map>
#include <mutex>
#include <string_view>
#include <utility>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
std::atomic<u32> bbsc_load_generation{1};
bool timeline=true;int role=3;u32 map=0x18000000;u64 image_base=0; s64 now=1000;
std::array<u8,0x100> actor{},replacement{},control{};
u64 resolved=0;int lookups=0;std::vector<std::string_view> boundaries;
template<class T>T ReadValue(u64 p,size_t off){T value;memcpy(&value,(void*)(p+off),sizeof(value));return value;}
template<class T>void put(auto& a,size_t off,T value){memcpy(a.data()+off,&value,sizeof(value));}
bool ReadablePointer(u64 p,size_t size){for(auto* a:{&actor,&replacement,&control}){
 const u64 start=(u64)a->data();if(p>=start&&p-start<=a->size()&&size<=a->size()-(p-start))return true;}return false;}
bool BbscTimelineEnabled(){return timeline;}
s32 GetSessionState(){return role;}u32 GetCurrentPackedMap(){return map;}
s64 SteadyNowMs(){return now;}
bool IsBbscPersonalMapEvent(s64 e){return e==12400520;}
u64 PS4_SYSV_ABI Find(u32,u64,u64){++lookups;return resolved;}
template<class... A>void Record(const char*,const char*,std::string_view boundary,A&&...){boundaries.push_back(boundary);}
#define BBSC_TIMELINE(...) Record(__VA_ARGS__)
'''
main = r'''
int main(){
 image_base=(u64)&Find-0x013C97A0;resolved=(u64)actor.data();
 put(actor,0x18,(u64)control.data());put(actor,0x28,u8(1));put(actor,0x90,s32(77));
 put(control,0x10,s32(4));put(control,0x14,s32(4));
 WatchBbscNpcLifecycle(2400750,12400520,29,0);
 WatchBbscNpcLifecycle(2400751,12400100,29,0); // shared event excluded
 assert(bbsc_npc_lifecycle_watches.size()==1);
 const auto original_actor=actor;const auto original_control=control;
 BeginBbscNpcLifecycleWake();assert(boundaries.size()==1&&boundaries.back()=="wake-before");
 EndBbscNpcLifecycleWake();assert(boundaries.size()==1); // unchanged state deduplicated
 assert(actor==original_actor&&control==original_control); // diagnostics write no engine bytes
 const int previous_lookups=lookups;
 BeginBbscNpcLifecycleWake();EndBbscNpcLifecycleWake();assert(lookups==previous_lookups);
 now+=250;BeginBbscNpcLifecycleWake();
 // Execute exact original cmp/jne and unload branch, with terminal edges only
 // replaced by RET. Native engine decides; diagnostics never enforce hiding.
 auto code=(u8*)VirtualAlloc(nullptr,0x1000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(code);
 const u8 branch[]={BRANCH};const u8 unload[]={UNLOAD};
 memcpy(code,branch,sizeof(branch));memcpy(code+0x1d4,unload,sizeof(unload));
 code[20]=0xc3;code[0x189]=0xc3;code[0x1df]=0xc3;
 using Wake=void PS4_SYSV_ABI (*)(u64);((Wake)code)((u64)actor.data());
 assert(ReadValue<s32>((u64)control.data(),0x14)==0);
 EndBbscNpcLifecycleWake();assert(boundaries.back()=="wake-after");
 assert(bbsc_npc_lifecycle_watches.at(2400750).previous.requested==0);
 put(control,0x10,s32(0));ObserveBbscNpcLifecycle("block-history-before",0x18000000);
 put(control,0x14,s32(4));ObserveBbscNpcLifecycle("block-history-after",0x18000000);
 assert(boundaries.back()=="block-history-after");
 // Actor recreation and streaming disappearance are observed via fresh lookup.
 replacement=actor;resolved=(u64)replacement.data();ObserveBbscNpcLifecycle("recreated");
 assert(bbsc_npc_lifecycle_watches.at(2400750).previous.actor==resolved);
 resolved=0;ObserveBbscNpcLifecycle("unloaded");
 assert(!bbsc_npc_lifecycle_watches.at(2400750).previous.actor);
 resolved=(u64)replacement.data();put(replacement,0x18,u64(1));ObserveBbscNpcLifecycle("bad-control");
 assert(bbsc_npc_lifecycle_watches.at(2400750).previous.requested==-1);
 for(u32 i=0;i<100;++i)WatchBbscNpcLifecycle(2500000+i,12400520,29,0);
 assert(bbsc_npc_lifecycle_watches.size()==64);
 bbsc_npc_lifecycle_lines=511;ObserveBbscNpcLifecycle("budget");assert(bbsc_npc_lifecycle_lines==512);
 const int budget_lookups=lookups;ObserveBbscNpcLifecycle("budget");assert(lookups==budget_lookups);
 bbsc_npc_lifecycle_lines=0;now+=250;BeginBbscNpcLifecycleWake();
 ++bbsc_load_generation;const int before_stale_end=lookups;EndBbscNpcLifecycleWake();
 assert(lookups==before_stale_end); // no old wake-after sample in a new load
 ++bbsc_load_generation;ObserveBbscNpcLifecycle("load");assert(bbsc_npc_lifecycle_watches.empty());
 WatchBbscNpcLifecycle(2400750,12400520,29,0);++map;
 ObserveBbscNpcLifecycle("map");assert(bbsc_npc_lifecycle_watches.empty());
 for(s32 session:{3,4,6}){role=session;WatchBbscNpcLifecycle(2400750,12400520,29,0);
  ObserveBbscNpcLifecycle("role");assert(bbsc_npc_lifecycle_watches.size()==1);}
 role=0;ObserveBbscNpcLifecycle("offline");assert(bbsc_npc_lifecycle_watches.empty());
 role=3;timeline=false;WatchBbscNpcLifecycle(2400750,12400520,29,0);
 ObserveBbscNpcLifecycle("disabled");assert(bbsc_npc_lifecycle_watches.empty());
 assert(actor==original_actor);VirtualFree(code,0,MEM_RELEASE);
 puts("PASS original native backread-off branch; production diagnostics read-only, lifecycle changes, scopes, roles, deduplication and budgets");
}
'''.replace('BRANCH', ','.join(map(str, branch))).replace('UNLOAD', ','.join(map(str, unload)))
with tempfile.TemporaryDirectory(prefix='bbsc-npc-lifecycle-') as tmp:
    folder = Path(tmp)
    cpp, exe = folder/'fixture.cpp', folder/'fixture.exe'
    cpp.write_text(prefix + (ROOT/'emulator/src/core/bbsc_npc_lifecycle.inc').read_text(encoding='utf-8') + main, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler, '-std=c++20', '-O0', '-DNOMINMAX', str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], check=True, env=env, timeout=15)
