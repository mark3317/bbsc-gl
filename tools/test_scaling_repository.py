"""Live repository discovery, real table preparation, span/fallback scaling and owner lifetime."""
from pathlib import Path
import os,subprocess,tempfile
s=(Path(__file__).resolve().parents[1]/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def fun(sig):
 a=s.index(sig+' {');i=s.index('{',a)+1;d=1
 while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]+'\n'
prefix=r'''
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <map>
#include <optional>
#include <string_view>
#include <vector>
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;
using s16=int16_t;using s32=int32_t;using s64=int64_t;
#define LOG_INFO(...) ((void)0)
#define BBSC_TIMELINE(...) ((void)0)
#define BBSC_PERF_NESTED(...) ((void)0)
enum class MemoryProt{CpuRead,CpuWrite};
std::vector<std::pair<u64,size_t>> regions;
int queries=0,writes=0,restarts=0;bool fragmented=false,deny_writes=false,split_directory=false; s64 now=100,step=0;
bool HasMemoryAccess(u64 p,size_t n,MemoryProt access){
 ++queries;if(split_directory && access==MemoryProt::CpuRead && n>336)return false;if(fragmented&&access==MemoryProt::CpuWrite&&n>336)return false;
 for(auto [base,size]:regions)if(p>=base && p-base<=size && n<=size-(p-base))return true;
 return false;
}
bool ReadablePointer(u64 p,size_t n){return HasMemoryAccess(p,n,MemoryProt::CpuRead);}
template<class T>T ReadValue(u64 p,size_t o){T v{};if(ReadablePointer(p+o,sizeof(v)))memcpy(&v,(void*)(p+o),sizeof(v));return v;}
template<class T>bool WriteValue(u64 p,size_t o,T v){++writes;if(deny_writes)return false;if(!HasMemoryAccess(p+o,sizeof(v),MemoryProt::CpuWrite))return false;memcpy((void*)(p+o),&v,sizeof(v));return true;}
s64 SteadyNowMs(){now+=step;return now;}
u64 image_base=1,active_npc=0,active_effect=0;
u64 BbscGameParamTable(std::string_view type){return type=="NPC_PARAM_ST"?active_npc:active_effect;}
bool BbscScalingEnabled(){return true;}
struct BbscScaledNpc{u64 row; s16 armor;bool boss;};
enum class BbscScaleState {Idle,Scanning,Ready,Failed};
std::atomic<BbscScaleState> bbsc_scale_state{BbscScaleState::Idle};
std::vector<u64> bbsc_scale_rows_enemy,bbsc_scale_rows_boss;
std::vector<BbscScaledNpc> bbsc_scaled_npcs;
u64 bbsc_scale_npc_table=0,bbsc_scale_effect_table=0,bbsc_scale_armor_begin=0,bbsc_scale_armor_end=0;
u16 bbsc_scale_npc_count=0;
void StartBbscScaling(){++restarts;bbsc_scale_state=BbscScaleState::Scanning;}
constexpr u32 BbscScaleTemplateEffect=7500,BbscEnemyScaleEffect=7502,BbscBossScaleEffect=7503;
constexpr size_t SpEffectRowSize=528;
struct BbscScaleNumbers{std::array<int,5> percent;bool operator==(const BbscScaleNumbers&)const=default;};
struct BbscAppliedScale{BbscScaleNumbers numbers;int guests;bool operator==(const BbscAppliedScale&)const=default;};
std::optional<BbscAppliedScale> bbsc_scale_written;
BbscScaleNumbers own{{40,100,15,15,20}};
const BbscScaleNumbers& BbscOwnScaleNumbers(){return own;}
const BbscScaleNumbers& BbscCachedHostScale(s64& ms){ms=0;return own;}
constexpr s64 BbscScaleFreshMs=15000;
int guests=1;
s32 GetSessionState(){return 3;}
s32 GetBbscScalingGuests(){return guests;}
s32 GetBbscGuestCount(){return guests;}
template<class T>void put(u64 p,size_t o,T v){memcpy((void*)(p+o),&v,sizeof(v));}
struct Table {
 std::vector<u8> data;u64 p;size_t start,row_size;u16 count;
 Table(u16 n,size_t size):data(0x40+n*24+n*size),start(0x40+n*24),row_size(size),count(n){
  p=reinterpret_cast<u64>(data.data());regions.emplace_back(p,data.size());
  put<u16>(p,0xA,n);
  for(u32 i=0;i<n;++i){put<u32>(p,0x40+i*24,i);put<u64>(p,0x48+i*24,start+i*size);}
 }
 u64 row(size_t i){return p+start+i*row_size;}
};
'''
view=s[s.index('struct BbscParamView {'):s.index('// The table the game itself reads')]
code=prefix+fun('u64 BbscCheckedParamRow(u64 table, u16 count, u64 offset, size_t size)')+fun('u64 BbscParamRow(u64 table, u32 id, size_t size = 8)')+fun('std::vector<u64> FindBbscParamTables(std::string_view type, u16 min_rows = 1000,\n                                     u32 first_id = 0)')+view+fun('void PrepareBbscScaling()')+fun('void TickBbscScaling()')+r'''
int main(){
 assert(FindBbscParamTables("NPC_PARAM_ST").empty());
 Table npc(1002,336),effects(1002,528);active_npc=npc.p;active_effect=effects.p;
 put<u32>(effects.p,0x40+24,7500);put<u32>(effects.p,0x40+48,7502);put<u32>(effects.p,0x40+72,7503);
 put<float>(effects.row(1),16,1.5f);
 for(int i=0;i<npc.count;++i){
  for(int slot=0;slot<8;++slot)put<s32>(npc.row(i),72+slot*4,-1);
  put<s16>(npc.row(i),280,100);put<u8>(npc.row(i),303,23);put<u8>(npc.row(i),329,i%2?16:0);
 }
 assert(FindBbscParamTables("NPC_PARAM_ST").size()==1);
 queries=0;PrepareBbscScaling();assert(bbsc_scale_state==BbscScaleState::Ready);
 assert(bbsc_scaled_npcs.size()==1002&&queries<100); // bulk validation, not thousands of queries
 assert(ReadValue<s32>(npc.row(0),72)==7502&&ReadValue<s32>(npc.row(1),72)==7503);
 queries=0;TickBbscScaling();assert(!bbsc_scale_written&&queries<10);
 assert(ReadValue<s16>(npc.row(0),280)==115&&ReadValue<s16>(npc.row(1),280)==120);
 assert(ReadValue<s16>(npc.row(128),280)==100);
 for(int i=0;i<10;++i)TickBbscScaling();assert(bbsc_scale_written);
 // Same-table retry must retain original armor rather than scaling an already scaled value.
 PrepareBbscScaling();assert(bbsc_scaled_npcs[0].armor==100);
 active_npc=0;guests=0;TickBbscScaling();assert(ReadValue<s16>(npc.row(0),280)==115);
 active_npc=npc.p;fragmented=true;deny_writes=true;writes=0;TickBbscScaling();
 assert(writes==1&&ReadValue<s16>(npc.row(0),280)==115&&!bbsc_scale_written);
 deny_writes=false;writes=0;TickBbscScaling();assert(writes==8&&!bbsc_scale_written);
 assert(ReadValue<s16>(npc.row(0),280)==100&&ReadValue<s16>(npc.row(8),280)==115);
 // A slow operation ends the fallback batch after one row, not eight.
 writes=0;step=1;TickBbscScaling();step=0;assert(writes==1);
 for(int i=0;i<140;++i)TickBbscScaling();assert(bbsc_scale_written);
 fragmented=false;
 split_directory=true;auto split=BbscParamViewFor(npc.p,336);assert(!split.directory);
 assert(BbscParamViewRow(split,0,336)==npc.row(0));
 assert(BbscParamRow(effects.p,7500,528)==effects.row(1));
 split_directory=false;
 auto view=BbscParamViewFor(npc.p,336);assert(view.writable);
 put<u64>(npc.p,0x48,8);assert(BbscParamViewRow(view,0,336)==0); // header-targeting corrupt offset
 put<u64>(npc.p,0x48,~u64{0});assert(BbscParamViewRow(view,0,336)==0);
 Table replacement(1002,336);active_npc=replacement.p;
 TickBbscScaling();assert(restarts==1&&!bbsc_scale_written&&bbsc_scale_state==BbscScaleState::Scanning);
}
'''
for name in ['std::vector<u64> FindBbscParamTables','void PrepareBbscScaling','void StartBbscSolidNpcs','void StartBbscDuelBell']:
 a=s.index(name);b=s.index('\n}\n',a)+3
 assert 'FindInMemory' not in s[a:b]
assert s[s.index('void StartBbscDuelBell()'):s.index('// The items the local player carries')].count('.detach()')==1
with tempfile.TemporaryDirectory(prefix='bbsc-param-repo-') as d:
 p=Path(d);cpp=p/'t.cpp';exe=p/'t.exe';cpp.write_text(code,encoding='utf-8')
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=20)
print('Repository-only lookup; bulk preparation/direct armor; fragmented fallback/deadline; reload owners; corrupt offsets: PASS')
