"""Exercise departure identity selection through the production native trampoline."""
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
s = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a = s.index('u8 bbsc_finale_departure_line_skip = 0;')
b = s.index('\n}\n', a) + 3
hook = s[a:b]
prefix = r'''
#include <windows.h>
#include <cassert>
#include <cstring>
#include <cstdio>
#include "core/cpu_patches.h"
using namespace Core;
u64 image;
namespace BbscMod { u64 EbootAddress(){return image;} void LogPlain(const char* s){std::puts(s);} }
#define LOG_INFO(...) ((void)0)
u64 GetLocalPlayerCharacter(){return 0x10000;}
int GetCharacterType(u64 p){return p==0x40000 ? 2 : p==0x50000 ? 12 : 1;}
bool IsInvaderType(int t){return t==2 || t==12;}
bool finale_committed = false, messages_enabled = true;
bool BbscNativeFinaleCommitted(){return finale_committed;}
bool BbscMessagesEnabled(){return messages_enabled;}
'''
main = r'''
int main(){
 image=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));
 assert(image);
 // Framed native caller with RBX=departing character and RSI=role-table line.
 const u8 code[]={0x55,0x48,0x89,0xe5,0x53,0x48,0x81,0xec,0xb0,0,0,0,
   0x48,0x89,0xfb,
   0x48,0x8d,0xbd,0x58,0xff,0xff,0xff,
   0x48,0x89,0xf0,0x48,0x81,0xc4,0xb0,0,0,0,0x5b,0x5d,0xc3};
 auto p=reinterpret_cast<u8*>(image)+0x0178B146-15;
 std::memcpy(p,code,sizeof(code));
 auto* exit=reinterpret_cast<u8*>(image)+0x0178B298;
 // Early exit from the original frame, before the banner path.
 const u8 epilogue[]={0xb8,0xff,0xff,0xff,0xff,0x48,0x81,0xc4,0xb0,0,0,0,0x5b,0x5d,0xc3};
 std::memcpy(exit,epilogue,sizeof(epilogue));
 assert(InstallGuestCodeHook(p+15,std::span<const u8>{code+15,7},0,BbscMemberDepartureLineHook,
                             &bbsc_finale_departure_line_skip,false,exit));
 using Run=u64 PS4_SYSV_ABI (*)(u64,u64);
 for(u64 id : {20000406ull,20000405ull,0ull}){
  assert(reinterpret_cast<Run>(p)(0x20000,id)==20000405); // remote role 0 / 7 / missing
  assert(reinterpret_cast<Run>(p)(0x30000,id)==20000405); // second remote
  for(u64 c : {0ull,0x10000ull,0x40000ull,0x50000ull})
   assert(reinterpret_cast<Run>(p)(c,id)==id); // local, absent, invaders unchanged
 }
 for(bool enabled : {true,false}){
  messages_enabled=enabled;
  finale_committed=true;
  for(u64 c : {0x10000ull,0x20000ull,0x30000ull})
   assert(reinterpret_cast<Run>(p)(c,20000406)==0xffffffff);
  finale_committed=false;
  assert(reinterpret_cast<Run>(p)(0x20000,20000406)==(enabled ? 20000405 : 20000406));
 }
 BbscMemberDepartureLineHook(0,nullptr);
 std::puts("Departure identity + native mid-function resume: PASS");
}
'''
# Remote notices retain the native leaveName substitution; local return ids stay native.
for name in ('bbsc_messages.inc','bbsc_messages_ru.inc'):
 table=(ROOT / 'emulator/src/core' / name).read_text(encoding='utf-8')
 for ident in (20000401,20000403,20000406): assert f'{{30, {ident},' not in table
 assert f'{{30, 20000405, u"<?leaveName?>' in table
with tempfile.TemporaryDirectory(prefix='bbsc-departure-') as tmp:
 cpp,exe=Path(tmp)/'fixture.cpp',Path(tmp)/'fixture.exe'
 cpp.write_text(prefix+hook+main,encoding='utf-8')
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
  '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),str(cpp),
  str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=10)
