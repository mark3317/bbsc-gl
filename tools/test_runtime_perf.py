"""Production progress merge and NPC event index regressions; isolated memory only."""
from pathlib import Path
import os, subprocess, tempfile, sys
s=(Path(__file__).resolve().parents[1]/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def fun(sig):
 a=s.index(sig+' {');i=s.index('{',a)+1;depth=1
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]+'\n'
prefix=r'''
#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>
#include <map>
#include <mutex>
#include <string_view>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s64=int64_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...) ((void)0)
#define BBSC_TIMELINE(...) ((void)0)
#define BBSC_PERF_NESTED(...) ((void)0)
enum class MemoryProt{CpuRead,CpuWrite};
int queries=0;
bool ReadablePointer(u64 p,size_t){return p>0x10000;}
bool HasMemoryAccess(u64 p,size_t,MemoryProt){++queries;return p>0x10000;}
template<class T>T ReadValue(u64 p,size_t off){T v{};memcpy(&v,(void*)(p+off),sizeof(v));return v;}
template<class T>bool WriteValue(u64 p,size_t off,T v){memcpy((void*)(p+off),&v,sizeof(v));return true;}
bool IsBbscPersonalMapEvent(s64 e){return e==7;}
bool IsBbscChaliceBossRewardEvent(s64){return false;}
constexpr size_t BbscWorldGroupBytes=125;
std::mutex bbsc_progress_mutex;
std::vector<u32> bbsc_progress_host_flags;
std::map<u32,std::array<u8,125>> bbsc_progress_groups;
bool bbsc_progress_backed_up=false,backup_ok=true;
int backups=0,sets=0,policy_checks=0;
bool BbscOwnOpeningDone(){return true;}
bool BackupBbscSaves(){++backups;return backup_ok;}
bool BbscEventFlag(u32 f){return f==1;}
u64 Set(u64,u32,u8){++sets;return 0;}
u64 image_base=reinterpret_cast<u64>(&Set)-0x0132E5A0;
std::array<u8,125> live{};
u64 BbscFlagGroupStorage(u32){return reinterpret_cast<u64>(live.data());}
bool BbscSharedMapProgressAllowed(u32 f){++policy_checks;return f%8!=0;}
'''
index=s[s.index('struct BbscQuestRange {'):s.index('\nbool BbscTalkEventIsOurs')]
index='#include "'+(Path(__file__).resolve().parents[1]/'emulator/src/core/bbsc_event_steps.h').as_posix()+'"\n'+index
main=r'''
int main(){
 bbsc_progress_groups[1].fill(0xff);live.fill(0xff);
 auto result=MergeBbscSharedProgress("noop");
 assert(result.first==0&&result.second==0&&backups==0&&policy_checks==0);
 live[0]=0;backup_ok=false;result=MergeBbscSharedProgress("fail");
 assert(result.first==-2&&live[0]==0&&backups==1&&sets==0);
 backup_ok=true;result=MergeBbscSharedProgress("change");
 assert(result.second==7&&live[0]==0x7f&&backups==2);
 result=MergeBbscSharedProgress("repeat");assert(result.second==0&&backups==2);
 bbsc_progress_host_flags={2};result=MergeBbscSharedProgress("boss");assert(sets==1);
 alignas(16) std::array<u8,0x200> inst{},ref{},file{},events{};
 auto ptr=[](auto& a){return reinterpret_cast<u64>(a.data());};
 const u64 instance=ptr(inst),r=ptr(ref),f=ptr(file),ev=f+0x100,instructions=f+0x100000;
 WriteValue(instance,0xA8,r);WriteValue(instance,0xB0,instructions+0x20);
 WriteValue(r,8,f);WriteValue<s64>(f,0x10,2);
 WriteValue(f,0x18,ev-f);WriteValue(f,0x28,instructions-f);
 // Two event ranges: [0,64) personal, [128,192) remote.
 WriteValue<s64>(ev,0,7);WriteValue<u64>(ev,8,2);WriteValue<u64>(ev,0x10,0);
 WriteValue<s64>(ev,0x30,9);WriteValue<u64>(ev,0x38,2);WriteValue<u64>(ev,0x40,128);
 WriteValue<u8>(instance,0x78,1);LocalizeBbscQuestEvent(instance);
 assert(ReadValue<u8>(instance,0x78)==0&&bbsc_quest_indexes.size()==1);
 WriteValue(instance,0xB0,instructions+128);WriteValue<u8>(instance,0x78,1);
 LocalizeBbscQuestEvent(instance);assert(ReadValue<u8>(instance,0x78)==1);
 WriteValue(instance,0xB0,instructions+96);const int before=queries;
 for(int i=0;i<1000;++i)LocalizeBbscQuestEvent(instance);
 assert(queries-before==0); // no full-directory or write validation on a negative hit
 WriteValue(instance,0xB0,instructions+32);WriteValue<s64>(ev,0,9);
 LocalizeBbscQuestEvent(instance);assert(!bbsc_quest_indexes.empty());
 LocalizeBbscQuestEvent(instance);assert(ReadValue<u8>(instance,0x78)==1); // reused event no stale permission
 // Reload / same address, changed table: clear before new map events.
 bbsc_quest_indexes.clear();bbsc_quest_instances.clear();WriteValue<s64>(ev,0,7);
 // Overlap: original first directory row wins, regardless of sorted start.
 WriteValue<u64>(ev,0x10,32);WriteValue<u64>(ev,8,4);
 WriteValue<u64>(ev,0x40,0);WriteValue<u64>(ev,0x38,8);
 WriteValue(instance,0xB0,instructions+64);LocalizeBbscQuestEvent(instance);
 assert(ReadValue<u8>(instance,0x78)==0);
}
'''
npc_only = '--npc-only' in sys.argv
if npc_only:
 main = 'int main(){\n' + main[main.index(' alignas(16)'):]
with tempfile.TemporaryDirectory(prefix='bbsc-runtime-perf-') as d:
 p=Path(d);cpp=p/'t.cpp';exe=p/'t.exe'
 cpp.write_text(prefix+(fun('u8 BbscSharedProgressByte(u32 key, size_t byte, u8 incoming)')+fun('std::pair<s64, size_t> MergeBbscSharedProgress(std::string_view when)') if not npc_only else '')+index+main,encoding='utf-8')
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=15)
if not npc_only:
 assert 'if (bosses == -2) return;' in fun('void TickBbscSharedProgress()')
 assert 'if (bosses == -2) return;' in fun('void ApplyBbscSharedProgressAtLoad()')
assert 'bbsc_quest_indexes.clear();' in s.split('if (site.offset == 0x0178D9C0) {',1)[1].split('}',1)[0]
print('NPC indexed misses/reuse/reload/overlap: PASS' if npc_only else 'Progress and NPC regressions: PASS')
