"""Exercise the production goods-use result: guest bell restriction is not a UI-only rule."""
from pathlib import Path
import os, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a=s.index('void ApplyBbscBellsAnywhere(');b=s.index('\nvoid OnBbscCutsceneRequestHook',a)
code=r'''
#include <cassert>
#include <cstdint>
#include <map>
#include <mutex>
#include <string>
#include <string_view>
using u64=uint64_t;using u32=uint32_t;using u8=uint8_t;using s32=int32_t;
struct GuestRegisterSnapshot {u64 r13=0x1000,r14=0x3000,rcx=1,rbp=0x2000,r12=1,r15=1,rsi=1,r8=1;};
std::map<u64,u64> memory;int session=0;bool anywhere=false;
s32 GetSessionState(){return session;}
u64 GetLocalPlayerCharacter(){return 0x3000;}
bool ReadablePointer(u64 p,size_t){return p>=0x1000;}
template<class T>T ReadValue(u64 p,size_t o){return static_cast<T>(memory[p+o]);}
u64 BbscCarriedInventory(){return 0x4000;}
bool BbscInventoryHas(u64,u32){return true;}
bool EnvFlagEnabled(const char*){return anywhere;}
int GetCharacterHp(u64){return 100;}
u32 GetCurrentPackedMap(){return 0x19000000;}
namespace fmt {template<class...T>std::string format(const char*,T...){return {};}}
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
'''+s[a:b]+r'''
int main(int argc,char**){
 anywhere=argc>1;
 ApplyBbscBellsAnywhere(nullptr);
 for(session=0;session<=7;++session)for(int effect:{9000,9005,7511,7,1234})
 for(int native:{0,1})for(bool local:{false,true}){
  memory.clear();GuestRegisterSnapshot r;r.rcx=0xAB00|native;
  if(!local)r.r14=0x5000;
  memory[r.r13]=effect;
  memory[r.rbp-0x1D8]=memory[r.rbp-0x1D4]=memory[r.rbp-0x1B4]=1;
  ApplyBbscBellsAnywhere(&r);
  bool blocked=local && (session==4||session==6) && (effect==9000||effect==9005);
  if(blocked)assert((r.rcx&255)==0 && (r.rcx&~u64{255})==0xAB00);
  else if(native)assert((r.rcx&255)==1); // host, solo, Blank, PvP and other actors unaffected
  else if(anywhere && local && (effect==9000||effect==9005||effect==7511))assert((r.rcx&255)==1);
  else assert((r.rcx&255)==0);
 }
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-guest-bells-') as tmp:
 cpp,exe=Path(tmp)/'fixture.cpp',Path(tmp)/'fixture.exe'
 cpp.write_text(code,encoding='utf-8')
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=10)
 subprocess.run([str(exe),'anywhere'],check=True,timeout=10)
print('Guest bell use: native/anywhere results, local/remote, roles, Blank and PvP: PASS')
