"""Production targeted-kick policy and the real native host-entry trampoline."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(sig):
    start=source.index(sig+' {'); end=source.index('{',start)+1; depth=1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}'); end+=1
    return source[start:end]
functions='\n'.join(function(s) for s in [
    'void HandleBbscTargetedKick()',
    'void PS4_SYSV_ABI BbscHostKickRequestHook(u64, const GuestRegisterSnapshot* registers)'])
dispatch=function('void HandleBbscLuaSessionEvent(const GuestRegisterSnapshot& registers)')
assert 'if (name == "OnBeKickOut")' in dispatch
assert 'bbsc_targeted_kick_received = false;' in dispatch
assert 'HandleBbscTargetedKick();' not in dispatch[dispatch.index('if (name.starts_with("OnLeave")'):]
announce=function('void BbscAnnounce(const char16_t* text, std::string_view what)')
assert 'what != "host kick requested"' in announce and 'what != "host kicked you"' in announce
code=r'''
#include <windows.h>
#include <cassert>
#include <cstring>
#include <string_view>
#include "core/cpu_patches.h"
using namespace Core;
u64 image_base=0, global=0x2000;
namespace BbscMod { u64 EbootAddress(){return image_base;} void LogPlain(const char*){} }
bool quit=false,own=false,loading=false,bbsc_targeted_kick_received=false,bbsc_home_return_claimed=false;
int state=6, suspended=0,released=0,host_notices=0,guest_notices=0;
bool BbscQuitInProgress(){return quit;} int GetSessionState(){return state;}
u64 GetGlobalState(){return global;} u64 GetLocalPlayerCharacter(){return 0x10000;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
bool IsValidMemberId(u64 p){return p==0x20000+0x3d8;}
template<class T>T ReadValue(u64 p,size_t offset){
 if(p==global)return static_cast<T>(offset==8?loading:own);
 return *reinterpret_cast<const T*>(p+offset);
}
void SuspendBbscPersistenceOnce(std::string_view){++suspended;}
void ReleaseBbscLeaveLocks(std::string_view){++released;}
const char16_t* BbscL(const char16_t* en,const char16_t*){return en;}
void BbscAnnounce(const char16_t* text,std::string_view what){
 assert(text&&*text);
 if(what=="host kicked you"){assert(suspended>0);++guest_notices;}
 else {assert(what=="host kick requested");++host_notices;}
}
#define BBSC_TIMELINE(...)
FUNCTIONS
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));
 assert(image_base);
 HandleBbscTargetedKick(); assert(suspended==1&&released==1&&guest_notices==1);
 HandleBbscTargetedKick(); assert(suspended==1&&released==1&&guest_notices==1);
 bbsc_targeted_kick_received=false;bbsc_home_return_claimed=true;
 HandleBbscTargetedKick(); assert(suspended==2&&released==1&&guest_notices==2);
 bbsc_targeted_kick_received=false;bbsc_home_return_claimed=false;loading=true;
 HandleBbscTargetedKick(); assert(suspended==3&&released==1); loading=false;
 for(int s : {0,6,7}) {
  bbsc_targeted_kick_received=false;state=s;HandleBbscTargetedKick();
 }
 const int before=suspended;
 for(int guard=0;guard<3;++guard){
  bbsc_targeted_kick_received=false;state=6;own=false;quit=false;
  if(guard==0)state=3;if(guard==1)own=true;if(guard==2)quit=true;
  HandleBbscTargetedKick();assert(suspended==before);
 }
 own=false;quit=false;state=3;
 // Exact 0178DBE0 prologue, original native body returns RSI untouched.
 const u8 native[]={0x55,0x48,0x89,0xe5,0x41,0x57,0x48,0x89,0xf0,0x41,0x5f,0x5d,0xc3};
 auto* entry=reinterpret_cast<u8*>(image_base+0x178dbe0);
 std::memcpy(entry,native,sizeof(native));
 assert(InstallGuestCodeHook(entry,std::span<const u8>{native,6},0,BbscHostKickRequestHook));
 const auto caller=[&](u64 offset){
  auto* p=reinterpret_cast<u8*>(image_base+offset);
  const u8 code[]={0x48,0x83,0xec,8,0xe8,0,0,0,0,0x48,0x83,0xc4,8,0xc3};
  std::memcpy(p,code,sizeof(code));s32 displacement=static_cast<s32>(reinterpret_cast<u64>(entry)-(image_base+offset+9));
  std::memcpy(p+5,&displacement,4);return p;
 };
 using Run=u64 PS4_SYSV_ABI (*)(u64,u64);
 auto run=reinterpret_cast<Run>(caller(0x15be459)); // CALL at 15BE45D -> return 15BE462
 assert(run(0,0x20000)==0x20000&&host_notices==1);
 for(u64 target : {0ull,0x10000ull,0x30000ull})assert(run(0,target)==target);
 assert(host_notices==1);state=6;assert(run(0,0x20000)==0x20000&&host_notices==1);state=3;
 auto other=reinterpret_cast<Run>(caller(0x15bf459));
 assert(other(0,0x20000)==0x20000&&host_notices==1);
 BbscHostKickRequestHook(0,nullptr);
}
'''.replace('FUNCTIONS',functions)
with tempfile.TemporaryDirectory(prefix='bbsc-target-kick-') as tmp:
    cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe';cpp.write_text(code,encoding='utf-8')
    compiler=os.environ.get('CXX',r'C:\msys64\clang64\bin\clang++.exe')
    subprocess.run([compiler,'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
        '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),str(cpp),
        str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env['PATH']
    subprocess.run([str(exe)],check=True,env=env,timeout=10)
print('PASS: addressed guest return/notice guards and selected host kick through exact native entry/caller')
