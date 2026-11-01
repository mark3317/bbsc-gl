"""Execute production Stop drain hook and loading UI close against memory fixtures."""
from pathlib import Path
import os, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
src=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
 a=src.index(signature+' {');b=src.index('{',a)+1;depth=1
 while depth:
  depth+=(src[b]=='{')-(src[b]=='}');b+=1
 return src[a:b]
prefix=r'''
#include <array>
#include <cassert>
#include <cstdint>
#include <map>
#include "core/bbsc_stop_policy.h"
using namespace Core::Bloodborne;
using u64=uint64_t;using u32=uint32_t;using s32=int32_t;using s64=int64_t;using u8=uint8_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...)
#define LOG_WARNING(...)
struct GuestRegisterSnapshot {u64 rdi;};
enum class MemoryProt {CpuWrite};
std::map<u64,u64> memory;
bool writable=true; s64 now=1000;u64 image_base=0x10000;
bool ReadablePointer(u64 p,size_t){return p!=0;}
bool HasMemoryAccess(u64,size_t,MemoryProt){return writable;}
template<class T>T ReadValue(u64 p,size_t o){return static_cast<T>(memory[p+o]);}
template<class T>void WriteValue(u64 p,size_t o,T v){memory[p+o]=v;}
s64 SteadyNowMs(){return now;}
constexpr u64 MenuManPointerOffset=0x100;
int closes=0;
bool close_stub(){++closes;memory[0x90000+0x804]=3;return false;}
bool open_stub(const void*){return false;}
u64 NowLoadingCloseOffset=reinterpret_cast<u64>(&close_stub)-image_base;
u64 NowLoadingOpenOffset=reinterpret_cast<u64>(&open_stub)-image_base;
'''
main=r'''
int main(){
 constexpr u64 c=0x20000,end=0x30000,node=0x40000,t=0x50000;
 GuestRegisterSnapshot r{c};
 memory[c+0x10]=end;memory[end]=node;memory[node+0x10]=t;
 memory[t+0x24]=12;memory[t+0x20]=1;memory[t+0x18]=30000000;memory[c+0x58]=5000000;
 BbscStopPhaseHook(0xc98110,&r);now+=100;
 BbscStopPhaseHook(0xc9b960,&r);now+=1999;
 BbscStopPhaseHook(0xc9b960,&r);assert(memory[t+0x18]==30000000);
 ++now;BbscStopPhaseHook(0xc9b960,&r);assert(memory[t+0x18]==4999999);
 // The native code now owns timeout cleanup and LeaveRoom. No repeated expiry.
 memory[t+0x18]=7000000;now+=5000;BbscStopPhaseHook(0xc9b960,&r);assert(memory[t+0x18]==7000000);
 memory[t+0x20]=2;BbscStopPhaseHook(0xc9b960,&r);now+=2000;
 writable=false;BbscStopPhaseHook(0xc9b960,&r);assert(memory[t+0x18]==7000000);
 writable=true;BbscStopPhaseHook(0xc9b960,&r);assert(memory[t+0x18]==4999999);
 for(u32 kind:{0u,7u,11u,13u}){
  memory[t+0x24]=kind;memory[t+0x18]=9000000;now+=5000;
  BbscStopPhaseHook(0xc9b960,&r);assert(memory[t+0x18]==9000000);
 }
 memory[t+0x24]=12;memory[t+0x20]=3;
 BbscStopPhaseHook(0xcc53c0,&r);now+=30000;BbscStopPhaseHook(0xcc53c0,&r);
 assert(memory[t+0x18]==9000000); // never expire the network request wait
 memory[end]=end;BbscStopPhaseHook(0xc9b960,&r);
 memory[image_base+MenuManPointerOffset]=0x90000;
 memory[0x90000+0x804]=2;assert(!BbscLoadingScreen(false)&&closes==1);
 for(int i=0;i<1000;++i)assert(!BbscLoadingScreen(false));
 assert(closes==1);memory[0x90000+0x804]=4;assert(!BbscLoadingScreen(false)&&closes==1);
 memory[0x90000+0x804]=0;assert(BbscLoadingScreen(false)&&closes==1);
 memory[0x90000+0x804]=1;assert(!BbscLoadingScreen(false)&&closes==2);
}
'''
code=prefix+function('void PS4_SYSV_ABI BbscStopPhaseHook(u64 phase, const GuestRegisterSnapshot* registers)')+function('bool BbscLoadingScreen(bool open)')+main
with tempfile.TemporaryDirectory() as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text(code,encoding='utf-8')
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-I'+str(root/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('Production Stop: exact drain phase/2s boundary/task identity/native deadline; loading close handshake: PASS')
