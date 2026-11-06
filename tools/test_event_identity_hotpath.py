"""Compare production indexed identity with original linear lookup on synthetic EMEVDs."""
from pathlib import Path
import os, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def fun(sig):
    a=s.index(sig+' {');b=s.index('{',a)+1;depth=1
    while depth:
        depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[a:b]+'\n'
index=s[s.index('struct BbscQuestRange {'):s.index('\nbool BbscTalkEventIsOurs')]
prefix=r'''
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <map>
#include <thread>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s64=int64_t;
#define BBSC_PERF_NESTED(...)
enum class MemoryProt{CpuRead};
thread_local int queries=0;bool readable=true;
bool ReadablePointer(u64 p,size_t){++queries;return readable&&p>0x10000;}
bool HasMemoryAccess(u64 p,size_t n,MemoryProt){return ReadablePointer(p,n);}
template<class T>T ReadValue(u64 p,size_t o){T v{};if(ReadablePointer(p+o,sizeof v))memcpy(&v,(void*)(p+o),sizeof v);return v;}
template<class T>void WriteValue(u64 p,size_t o,T v){memcpy((void*)(p+o),&v,sizeof v);}
bool IsBbscPersonalMapEvent(s64 e){return e==7;}bool IsBbscChaliceBossRewardEvent(s64){return false;}
// Frozen pre-change lookup: independent of the optimized index.
s64 LegacyEventId(u64 instance){
 const u64 ref=ReadValue<u64>(instance,0xa8),instruction=ReadValue<u64>(instance,0xb0);
 if(!ReadablePointer(ref,0x10))return -1;const u64 file=ReadValue<u64>(ref,8);
 if(!ReadablePointer(file,0x90))return -1;
 const s64 count=ReadValue<s64>(file,0x10);
 const u64 events=file+ReadValue<u64>(file,0x18),instructions=file+ReadValue<u64>(file,0x28);
 if(count<=0||count>100000||instruction<instructions||!HasMemoryAccess(events,count*0x30,MemoryProt::CpuRead))return -1;
 const u64 at=(instruction-instructions)/0x20;
 for(s64 k=0;k<count;++k){std::array<u64,3> row{};memcpy(row.data(),(void*)(events+k*0x30),sizeof row);
  if(at>=row[2]/0x20&&at<row[2]/0x20+row[1])return row[0];}return -1;
}
'''
main=r'''
int main(){
 std::array<u8,0xc0> instance{};std::array<u8,0x10> ref{};std::vector<u8> file(0x100+512*0x30);
 const u64 inst=(u64)instance.data(),r=(u64)ref.data(),f=(u64)file.data(),events=f+0x100,instructions=f+0x100000;
 WriteValue(inst,0xa8,r);WriteValue(r,8,f);WriteValue<s64>(f,0x10,512);
 WriteValue(f,0x18,events-f);WriteValue(f,0x28,instructions-f);
 for(u64 k=0;k<512;++k){WriteValue<s64>(events+k*0x30,0,k==350?7:1000+k);
  WriteValue<u64>(events+k*0x30,8,2);WriteValue<u64>(events+k*0x30,0x10,k*64);}
 for(u64 k=0;k<512;++k){WriteValue(inst,0xb0,instructions+k*64+32);assert(BbscEventIdOf(inst)==LegacyEventId(inst));}
 WriteValue(inst,0xb0,instructions+350*64);assert(BbscEventIdOf(inst)==7);
 queries=0;for(int i=0;i<2000;++i)assert(BbscEventIdOf(inst)==7);const int fast=queries;
 queries=0;for(int i=0;i<2000;++i)assert(LegacyEventId(inst)==7);const int slow=queries;assert(fast*2<slow);
 // Native restarts can restore network sync: still localize before the next step.
 instance[0x78]=1;LocalizeBbscQuestEvent(inst);assert(instance[0x78]==0);
 instance[0x78]=1;LocalizeBbscQuestEvent(inst);assert(instance[0x78]==0);
 // In-place identity change with unchanged addresses must not inherit event7.
 WriteValue<s64>(events+350*0x30,0,9);assert(BbscEventIdOf(inst)==9);
 instance[0x78]=1;LocalizeBbscQuestEvent(inst);assert(instance[0x78]==1);
 // Independent thread caches are invalidated by the same native load epoch.
 WriteValue<s64>(events+350*0x30,0,7);++bbsc_quest_index_epoch;
 std::atomic<int> phase{0};
 std::thread other([&]{assert(BbscEventIdOf(inst)==7);phase.store(1,std::memory_order_release);
  while(phase.load(std::memory_order_acquire)!=2)std::this_thread::yield();
  assert(BbscEventIdOf(inst)==9);});
 while(phase.load(std::memory_order_acquire)!=1)std::this_thread::yield();
 WriteValue<s64>(events+350*0x30,0,9);++bbsc_quest_index_epoch;phase.store(2,std::memory_order_release);other.join();
 assert(BbscEventIdOf(inst)==9);
 // Overlaps always use original directory order, including when the PC moves.
 WriteValue<s64>(events,0,7);WriteValue<u64>(events,8,1024);++bbsc_quest_index_epoch;
 for(u64 k:{350,400,200}){WriteValue(inst,0xb0,instructions+k*64);assert(BbscEventIdOf(inst)==LegacyEventId(inst));assert(BbscEventIdOf(inst)==7);}
 readable=false;assert(BbscEventIdOf(inst)==-1);readable=true;
 printf("PASS event identity: linear equivalence512 events, warm queries %d->%d; row reuse, overlap PC movement, native relocalization and cross-thread reload epoch\n",slow,fast);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-event-id-') as tmp:
    p=Path(tmp);cpp=p/'t.cpp';exe=p/'t.exe'
    cpp.write_text(prefix+index+fun('s64 BbscEventIdOf(u64 instance)')+main,encoding='utf-8')
    cc=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
    env=dict(os.environ,PATH=str(Path(cc).parent)+os.pathsep+os.environ.get('PATH',''))
    subprocess.run([cc,'-std=c++20','-O2',str(cpp),'-o',str(exe)],env=env,check=True)
    subprocess.run([str(exe)],env=env,check=True,timeout=15)
