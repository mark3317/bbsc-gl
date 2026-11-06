"""Production message binding on synthetic FMGs: reuse, reload and permissions."""
from pathlib import Path
import os, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def fun(sig):
    a=s.index(sig+' {');b=s.index('{',a)+1;depth=1
    while depth:
        depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[a:b]+'\n'
lookup=s[s.index('struct BbscMessageCategory {'):s.index("// The game's language as BBSC sees it")]
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
#include <optional>
#include <span>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define LOG_INFO(...)
enum class MemoryProt{CpuRead,CpuWrite};
struct Region{u64 start;size_t size;bool readable=true,writable=true;};
std::vector<Region> regions;int queries=0,writes=0;bool enabled=true,russian=false;
std::atomic<u32> bbsc_load_generation{0};s64 now=10000;
bool HasMemoryAccess(u64 p,size_t n,MemoryProt mode){++queries;
 for(auto& r:regions)if(p>=r.start && n<=r.size && p-r.start<=r.size-n)
  return mode==MemoryProt::CpuRead?r.readable:r.writable;return false;}
bool ReadablePointer(u64 p,size_t n){return HasMemoryAccess(p,n,MemoryProt::CpuRead);}
template<class T>T ReadValue(u64 p,size_t o){T value{};
 if(ReadablePointer(p+o,sizeof value))memcpy(&value,(void*)(p+o),sizeof value);return value;}
template<class T>bool WriteValue(u64 p,size_t o,T value){
 if(!HasMemoryAccess(p+o,sizeof value,MemoryProt::CpuWrite))return false;
 memcpy((void*)(p+o),&value,sizeof value);++writes;return true;}
template<class T>void put(u64 p,size_t o,T value){memcpy((void*)(p+o),&value,sizeof value);}
template<class T>u64 addr(T& a){return reinterpret_cast<u64>(a.data());}
template<class T>void add(T& a){regions.push_back({addr(a),a.size()*sizeof(a[0])});}
u64 image_base=0;constexpr u64 MsgRepositoryPointerOffset=0;
bool BbscRussian(){return russian;}bool BbscMessagesEnabled(){return enabled;}
s64 SteadyNowMs(){return now;}
struct BbscMessage{u32 category,id;const char16_t* text;};
constexpr BbscMessage BbscMessages[]={{30,100,u"One <?joinName?>"},{30,101,u"Two"},{101,700,u"Other"}};
constexpr BbscMessage BbscMessagesRu[]={{30,100,u"Один <?joinName?>"},{30,101,u"Два"},{101,700,u"Другой"}};
constexpr char16_t BbscSilentBanner[]=u"[BBSC:silent]";
bool BbscQuietMessage(u32,u32){return false;}
'''
main=r'''
int main(){
 std::array<u8,8> image{},versions{};std::array<u8,16> repo{};
 std::array<u64,102> categories{};std::array<u8,0x80> fmg{},other{};
 std::array<u64,3> table{},second{};
 for(auto* v:{&fmg,&other}){add(*v);put<s32>(addr(*v),0x0c,2);put<s32>(addr(*v),0x10,3);}
 add(image);add(versions);add(repo);add(categories);add(table);add(second);
 image_base=addr(image);put(image_base,0,addr(repo));put(addr(repo),8,addr(versions));
 put(addr(versions),0,addr(categories));categories[30]=addr(fmg);
 put(addr(fmg),0x18,addr(table));put<u32>(addr(fmg),0x28,0);
 put<u32>(addr(fmg),0x2c,100);put<u32>(addr(fmg),0x30,100);
 put<u32>(addr(fmg),0x38,1);put<u32>(addr(fmg),0x3c,101);put<u32>(addr(fmg),0x40,101);
 // A missing category is retried when it becomes available.
 TickBbscMessages();assert(writes==2);assert(table[0]==(u64)BbscMessages[0].text-addr(fmg));
 queries=writes=0;for(int i=0;i<1000;++i)TickBbscMessages();assert(!queries&&!writes);
 now+=2000;queries=0;TickBbscMessages();assert(queries<=15&&!writes);
 const int warm_queries=queries;
 // Native may overwrite a slot without replacing the repository: repair it.
 table[0]=123;now+=2000;TickBbscMessages();assert(writes==1);
 categories[101]=addr(other);put(addr(other),0x18,addr(second));
 put<u32>(addr(other),0x28,0);put<u32>(addr(other),0x2c,700);put<u32>(addr(other),0x30,700);
 now+=2000;TickBbscMessages();assert(second[0]==(u64)BbscMessages[2].text-addr(other));
 russian=true;now+=2000;TickBbscMessages();assert(table[1]==(u64)BbscMessagesRu[1].text-addr(fmg));
 // Same FMG address, changed row/table: never write through an old binding.
 put<u32>(addr(fmg),0x28,2);table[0]=456;now+=2000;TickBbscMessages();
 assert(table[0]==456 && table[2]==(u64)BbscMessagesRu[0].text-addr(fmg));
 std::array<u64,3> replacement{};add(replacement);put(addr(fmg),0x18,addr(replacement));
 ++bbsc_load_generation;now+=2000;TickBbscMessages();assert(replacement[2]==table[2]);
 // Unmapped/read-only slots and malformed rows fail safely, then retry.
 regions.back().writable=false;replacement[2]=0;now+=2000;TickBbscMessages();assert(!replacement[2]);
 regions.back().writable=true;regions.back().readable=false;now+=2000;TickBbscMessages();assert(!replacement[2]);
 regions.back().readable=true;now+=2000;TickBbscMessages();assert(replacement[2]==table[2]);
 put<u32>(addr(fmg),0x28,10000);replacement[2]=321;now+=2000;TickBbscMessages();assert(replacement[2]==321);
 put<u32>(addr(fmg),0x28,2);now+=2000;TickBbscMessages();assert(replacement[2]==table[2]);
 queries=writes=0;enabled=false;now+=2000;TickBbscMessages();assert(!queries&&!writes);
 printf("PASS message hotpath: unchanged tick0queries, warm pass%dqueries; slot overwrite, missing category, ru/en, reused rows/table/load and access failure retry\n",warm_queries);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-messages-') as tmp:
    p=Path(tmp);cpp=p/'t.cpp';exe=p/'t.exe'
    cpp.write_text(prefix+lookup+fun('void TickBbscMessages()')+main,encoding='utf-8')
    cc=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
    env=dict(os.environ,PATH=str(Path(cc).parent)+os.pathsep+os.environ.get('PATH',''))
    subprocess.run([cc,'-std=c++20','-O2',str(cpp),'-o',str(exe)],check=True,env=env)
    subprocess.run([str(exe)],check=True,env=env,timeout=15)
