"""Production inventory/Dream guards and memory-cache regressions.
Native death processing is covered by test_repeat_death.py.
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
MOD = (ROOT / 'emulator/mod/bbsc_mod.cpp').read_text(encoding='utf-8')


def function(source, signature):
    start = source.index(signature + ' {')
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


prefix = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>
#include <string_view>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;
using s8=int8_t;using s16=int16_t;using s32=int32_t;using s64=int64_t;
#define BBSC_PERF_SCOPE(...)
#define PS4_SYSV_ABI
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
struct Region {u64 at;size_t bytes;};
std::vector<Region> regions;
int guards=0;
bool ReadablePointer(u64 p,size_t n){++guards;for(auto r:regions)
 if(p>=r.at && p-r.at<=r.bytes && n<=r.bytes-(p-r.at))return true;return false;}
template<class T>T ReadValue(u64 p,size_t off){T t{};
 if(ReadablePointer(p+off,sizeof(t)))memcpy(&t,(void*)(p+off),sizeof(t));return t;}
template<class T>void put(u64 p,size_t off,T t){memcpy((void*)(p+off),&t,sizeof(t));}
template<size_t N>u64 memory(std::array<u8,N>& a){u64 p=(u64)a.data();regions.push_back({p,N});return p;}
u64 player=0,image_base=0;
u64 GetLocalPlayerCharacter(){return player;}
bool IsEbootCodeAddress(u64 p){return p!=0;}
'''

main = r'''
int main(){
 std::array<u8,0x80> inv{};std::array<u8,0x7E1*2> hashes{};
 std::array<u8,32> entries{},slots{},extra{};
 auto i=memory(inv),h=memory(hashes),en=memory(entries),sl=memory(slots),ex=memory(extra);
 constexpr u32 code=0x40000078;
 hashes.fill(0xff);put(i,0x68,h);put(i,0x78,en);put(i,0x24,u32{1});put(i,0x58,sl);put(i,0x48,ex);
 put(h,(code%0x7E1)*2,s16{0});put(en,0,code+0x7E1);put(en,4,u32{2<<12});
 put(en,8,code);put(en,12,u32{0});put(sl,0,u32{123});
 guards=0;assert(BbscInventoryHas(i,code));assert(guards==8);
 put(en,12,u32{1});put(ex,0,u32{456});assert(BbscInventoryHas(i,code));
 put(ex,0,u32{0});assert(!BbscInventoryHas(i,code));
 assert(!BbscInventoryHas(i,code+1));
 put(en,8,code+2);put(en,12,u32{1<<12});assert(!BbscInventoryHas(i,code));
 put(en,4,u32{4095<<12});assert(!BbscInventoryHas(i,code));
 put(i,0x68,u64{0});assert(!BbscInventoryHas(i,code));
}
'''

dream_prefix = r'''
struct GuestRegisterSnapshot {u64 rdi,rdx;};
bool guest_world=true;int rewards=0;s64 event_id=7;
std::array<u64,16> bbsc_dream_type_conditions{};
size_t bbsc_dream_type_next=0;u8 bbsc_dream_type_skip=0;
std::vector<s64> bbsc_dream_type_logged;
constexpr std::array<s64,1> BbscDreamGuestEvents{7},BbscDreamOwnGuestEvents{8},BbscGuestGiftEvents{9};
bool BbscGuestInHostWorld(){return guest_world;}
s64 BbscEventIdOf(u64){return event_id;}
void NoteBbscBossRewardEvent(s64){++rewards;}
bool BbscDreamOwnEnabled(){return false;}
bool IsBbscPersonalMapEvent(s64 e){return e==10;}
bool BbscResearchEnabled(){return false;}
u32 GetCurrentPackedMap(){return 0;}
template<class T>bool WriteValue(u64 p,size_t off,T t){
 if(!ReadablePointer(p+off,sizeof(t)))return false;put(p,off,t);return true;}
'''
dream_main = r'''
int main(){std::array<u8,0x30> condition{};std::array<u8,0xc0> event_memory{};
 auto c=memory(condition),e=memory(event_memory);GuestRegisterSnapshot regs{c,e};
 put(c,0x28,s32{10000});put(c,0x2c,s8{1});guards=0;
 BbscDreamTypeCheckHook(0,&regs);assert(rewards==1&&!bbsc_dream_type_skip&&guards==2);
 put(c,0x2c,s8{0});BbscDreamTypeCheckHook(0,&regs);assert(bbsc_dream_type_skip&&condition[0x10]==1);
 bbsc_dream_type_skip=0;event_id=999;BbscDreamTypeCheckHook(0,&regs);assert(!bbsc_dream_type_skip);
 guest_world=false;int old=rewards;BbscDreamTypeCheckHook(0,&regs);assert(rewards==old);
 regs.rdi=0;BbscDreamTypeCheckHook(0,&regs);BbscDreamTypeCheckHook(0,nullptr);
}
'''

cache_prefix = r'''
#include <array>
#include <cassert>
#include <cstdint>
using u64=uint64_t;using DWORD=uint32_t;
struct MEMORY_BASIC_INFORMATION {void* BaseAddress;size_t RegionSize;DWORD State,Protect;};
int queries=0;u64 now=100;
u64 GetTickCount64(){return now;}
int VirtualQuery(void* p,MEMORY_BASIC_INFORMATION* out,size_t){
 ++queries;auto at=(u64)p;if(at<0x10000)return 0;
 *out={(void*)(at&~u64{4095}),4096,0x1000,4};return sizeof(*out);}
'''
cache_main = r'''
int main(){CachedRegion out;
 for(int pass=0;pass<10;++pass)for(u64 n=0;n<48;++n)
   assert(QueryRegion(0x10000+n*0x1000,out));
 assert(queries==48); // original 16 slots thrash: 480 VirtualQuery calls
 now+=251;assert(QueryRegion(0x10000,out));assert(queries==49);
 assert(!QueryRegion(0,out)); // invalid addresses are never cached
}
'''

with tempfile.TemporaryDirectory(prefix='bbsc-death-hotpaths-') as tmp:
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    cache = MOD[MOD.index('struct CachedRegion {'):MOD.index('\nbool Readable(', MOD.index('struct CachedRegion {'))]
    inventory = function(SOURCE, 'bool BbscInventoryHas(u64 inventory, u32 code)')
    for name, code in [('inventory', prefix+inventory+main),
                       ('regions', cache_prefix+cache+cache_main),
                       ('dream', prefix+dream_prefix+function(SOURCE, 'void PS4_SYSV_ABI BbscDreamTypeCheckHook(u64 /*tag*/, const GuestRegisterSnapshot* registers)')+dream_main)]:
        cpp, exe = Path(tmp)/(name+'.cpp'), Path(tmp)/(name+'.exe')
        cpp.write_text(code, encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-O2',str(cpp),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],env=env,check=True,timeout=10)
print('PASS: inventory guards, region churn/expiry and Dream guards; death processing covered by test_repeat_death')
