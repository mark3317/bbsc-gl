"""Exercise the production goods-use result: guest bell restriction is not a UI-only rule."""
from pathlib import Path
import os, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a=s.index('void ApplyBbscBellsAnywhere(');b=s.index('\nvoid OnBbscCutsceneRequestHook',a)
code=r'''
#include <cassert>
#include <array>
#include <cstdint>
#include <cstring>
#include <map>
#include <mutex>
#include <string>
#include <string_view>
using u64=uint64_t;using u32=uint32_t;using u8=uint8_t;using s32=int32_t;
struct GuestRegisterSnapshot {u64 r13=0x1000,r14=0x3000,rcx=1,rbp=0x2000,r12=1,r15=1,rsi=1,r8=1;};
std::map<u64,u64> memory;int session=0;bool anywhere=false; int session_reads=0; bool has_control=true; bool research=false; int map_queries=0;
s32 GetSessionState(){++session_reads;return session;}
u64 GetLocalPlayerCharacter(){return 0x3000;}
bool ReadablePointer(u64 p,size_t){return p>=0x1000;}
template<class T>T ReadValue(u64 p,size_t o){return static_cast<T>(memory[p+o]);}
u64 BbscCarriedInventory(){return 0x4000;}
bool BbscInventoryHas(u64,u32){return has_control;}
bool EnvFlagEnabled(const char*){return anywhere;}
int GetCharacterHp(u64){return 100;}
u32 GetCurrentPackedMap(){++map_queries;return 0x19000000;}
bool BbscResearchEnabled(){return research;}
namespace fmt {template<class...T>std::string format(const char*,T...){return {};}}
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
'''+s[a:b]+r'''
int main(int argc,char**){
 anywhere=argc>1;research=argc>2;
 ApplyBbscBellsAnywhere(nullptr);
 for(session=0;session<=7;++session)for(int effect:{9000,9005,7511,7,1234})
 for(int native:{0,1})for(bool local:{false,true}){
  memory.clear();GuestRegisterSnapshot r;r.rcx=0xAB00|native;
  std::array<u8,512> stack{}; r.rbp=reinterpret_cast<u64>(stack.data()+512);
  stack[512-0x1D8]=stack[512-0x1D4]=stack[512-0x1B4]=1;
  if(!local)r.r14=0x5000;
  std::array<u8,72> goods{}; r.r13=reinterpret_cast<u64>(goods.data());
  std::memcpy(goods.data(),&effect,sizeof(effect));
  memory[r.r13]=effect;
  memory[r.rbp-0x1D8]=memory[r.rbp-0x1D4]=memory[r.rbp-0x1B4]=1;
  const int before=session_reads;
  ApplyBbscBellsAnywhere(&r);
  if(effect==1234 || effect==7 || effect==7511) assert(session_reads==before);
  if(!research) assert(map_queries==0);
  bool blocked=local && (session==4||session==6) && (effect==9000||effect==9005);
  if(blocked)assert((r.rcx&255)==0 && (r.rcx&~u64{255})==0xAB00);
  else if(native)assert((r.rcx&255)==1); // host, solo, Blank, PvP and other actors unaffected
  else if(anywhere && local && (effect==9000||effect==9005||effect==7511))assert((r.rcx&255)==1);
  else assert((r.rcx&255)==0);

 }
 if(anywhere){
  session=0;
  std::array<u8,512> stack{}; std::array<u8,72> goods{};
  GuestRegisterSnapshot base;base.rbp=reinterpret_cast<u64>(stack.data()+512);
  base.r13=reinterpret_cast<u64>(goods.data());
  auto reset=[&]{stack.fill(0);stack[512-0x1D8]=stack[512-0x1D4]=stack[512-0x1B4]=1;};
  int effect=9000;memcpy(goods.data(),&effect,4);
  // Every retained native condition must still veto the geographical override.
  for(auto [off,value]:std::array<std::pair<int,int>,13>{{{0x1D0,1},{0x1C8,1},{0x1DA,1},{0x1F8,1},{0x1FC,1},{0x200,1},{0x1B8,1},{0x1D9,1},{0x1E8,1},{0x1D8,0},{0x1D4,0},{0x1B9,1},{0x1B4,0}}}){
   reset();stack[512-off]=value;auto r=base;r.rcx=0xAB00;ApplyBbscBellsAnywhere(&r);assert(r.rcx==0xAB00);
  }
  for(int reg=0;reg<4;++reg){
   reset();auto r=base;r.rcx=0xAB00;
   if(reg==0)r.r12=0;if(reg==1)r.r15=0;if(reg==2)r.rsi=0;if(reg==3)r.r8=0;
   ApplyBbscBellsAnywhere(&r);assert(r.rcx==0xAB00);
  }
  for(int condition=-1;condition<6;++condition){
   reset();stack[512-0x1E1]=stack[512-0x1EC]=stack[512-0x1BA]=1; // no lift by default
   if(condition==0)stack[512-0x1E0]=1;if(condition==1)stack[512-0x1E1]=0;
   if(condition==2)stack[512-0x1EC]=0;if(condition==3)stack[512-0x1F4]=1;
   if(condition==4)stack[512-0x1F0]=1;if(condition==5)stack[512-0x1BA]=0;
   auto r=base;r.rcx=0xAB00;ApplyBbscBellsAnywhere(&r);
   assert(r.rcx==u64(condition<0?0xAB00:0xAB01));
  }
  has_control=false;
  for(int e:{9000,9005,7511,7}){memcpy(goods.data(),&e,4);reset();auto r=base;r.rcx=1;ApplyBbscBellsAnywhere(&r);assert(r.rcx==0);}
  has_control=true;
 }
 if(!research)assert(map_queries==0);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-guest-bells-') as tmp:
 cpp,exe=Path(tmp)/'fixture.cpp',Path(tmp)/'fixture.exe'
 cpp.write_text(code,encoding='utf-8')
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=10)
 subprocess.run([str(exe),'anywhere'],check=True,timeout=10)
 subprocess.run([str(exe),'anywhere','research'],check=True,timeout=10)
print('Guest bell use: native/anywhere results, local/remote, roles, Blank and PvP: PASS')
