"""Production popup callback + Windows trampoline + original native branch (no saves)."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
start = source.index('constexpr u64 BbscItemPopupControlRead =')
callback = source[start:source.index('void ShowBbscItemPopup(', start)]
assert 'image_base + BbscItemPopupControlRead' in source
assert 'std::span<const u8>{PopupControlRead}, 0,' in source
assert '0x48,0x8B,0x40,0x38,0x48,0x85,0xC0' in source
fixture = r'''
#include <windows.h>
#include <array>
#include <cassert>
#include <cstring>
#include "core/cpu_patches.h"
using namespace Core;
u64 image_base,player,queue; int session=6,hp=100;bool popups=true;
std::array<u8,16> global{};
namespace BbscMod {
u64 EbootAddress(){return image_base;}
void LogPlain(const char*){}
}
int GetSessionState(){return session;}
bool BbscItemPopupEnabled(){return popups;}
int GetCharacterHp(u64){return hp;}
u64 GetGlobalState(){return reinterpret_cast<u64>(global.data());}
u64 GetLocalPlayerCharacter(){return player;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64 p,size_t off){T v;std::memcpy(&v,reinterpret_cast<void*>(p+off),sizeof(v));return v;}
template<class T>void put(void* p,size_t off,T v){std::memcpy(static_cast<u8*>(p)+off,&v,sizeof(v));}
''' + callback + r'''
int main(){
 auto* image=static_cast<u8*>(VirtualAlloc(nullptr,0x9000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));
 assert(image);image_base=reinterpret_cast<u64>(image);
 std::array<u8,0x60> character{},control{};std::array<u8,0x42> flags{};
 std::array<u64,3> pending{};
 player=reinterpret_cast<u64>(character.data());queue=reinterpret_cast<u64>(pending.data());
 put(character.data(),0x58,reinterpret_cast<u64>(control.data()));
 put(control.data(),0x38,reinterpret_cast<u64>(flags.data()));
 put(image,0x0553B1C0,queue);pending[1]=123;
 // Synthetic function sets exactly the two live registers at 16D873C.
 // Replays MOV/TEST, then native JE and TEST flags+41 / JNE.
 // Return 1 means continuation to the original action registration, not a click.
 const u8 body[]={0x41,0x54,0x48,0x89,0xF8,0x49,0x89,0xF4,
   0x48,0x8B,0x40,0x38,0x48,0x85,0xC0,0x74,13,
   0xF6,0x40,0x41,0x80,0x75,7,0xB8,1,0,0,0,0xEB,2,
   0x31,0xC0,0x41,0x5C,0xC3};
 auto* code=image+0x2000;std::memcpy(code,body,sizeof(body));
 using Check=u64 PS4_SYSV_ABI (*)(u64,u64);auto check=reinterpret_cast<Check>(code);
 const u64 ctl=reinterpret_cast<u64>(control.data());
 flags[0x41]=0x85;assert(check(ctl,queue)==0); // old native path reproduces missing OK
 assert(InstallGuestCodeHook(code+8,std::span<const u8>{body+8,7},0,BbscItemPopupConfirmHook));
 for(int repeat=0;repeat<3;++repeat){
  assert(check(ctl,queue)==1);assert(flags[0x41]==0x85&&pending[1]==123);
  assert(ReadValue<u64>(ctl,0x38)==reinterpret_cast<u64>(flags.data()));
 }
 for(int other:{0,2,3,4,5,7}){session=other;assert(check(ctl,queue)==0);}session=6;
 popups=false;assert(check(ctl,queue)==0);popups=true;
 hp=0;assert(check(ctl,queue)==0);hp=100;
 global[8]=1;assert(check(ctl,queue)==0);global[8]=0;
 pending[1]=0;assert(check(ctl,queue)==0);pending[1]=123;
 assert(check(ctl,queue+8)==0);
 put(character.data(),0x58,u64{0});assert(check(ctl,queue)==0);
 put(character.data(),0x58,ctl);
 flags[0x41]=5;assert(check(ctl,queue)==1);assert(flags[0x41]==5);
 put(control.data(),0x38,u64{0});assert(check(ctl,queue)==0);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-item-confirm-') as directory:
    cpp = Path(directory) / 'fixture.cpp'
    exe = cpp.with_suffix('.exe')
    cpp.write_text(fixture, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler, '-std=c++20', '-O0', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
                    '-I', str(ROOT / 'emulator/src'),
                    '-I', str(ROOT / 'emulator/externals/xbyak'),
                    str(cpp), str(ROOT / 'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], env=env, check=True, timeout=10)
print('PASS: native item OK branch + production trampoline; guest-only, loading/dead/empty '
      'queue guards; character flags and queue unchanged')
