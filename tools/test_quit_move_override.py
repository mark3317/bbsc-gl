"""Run production quit callbacks through the native CMP/override trampoline."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')

def function(signature):
    start = source.index(signature + ' {')
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

fixture = r'''
#include <windows.h>
#include <cassert>
#include <cstring>
#include "core/cpu_patches.h"
using Core::GuestRegisterSnapshot;
namespace MemoryProt { constexpr int CpuWrite=1; }
u64 image, world=1, player=0;
struct BbscPendingQuit { u64 global=0, character=0, character_control=0; };
BbscPendingQuit bbsc_pending_quit, bbsc_title_quit;
u64 GetGlobalState(){return world;}
u64 GetLocalPlayerCharacter(){return player;}
template<class T> T ReadValue(u64 p, size_t o){return *reinterpret_cast<T*>(p+o);}
bool HasMemoryAccess(u64 p,size_t,int){return p!=0;}
void SetBbscQuitDisableMove(u8 v){
    *reinterpret_cast<u8*>(ReadValue<u64>(player,0x58)+0x111)=v;
}
namespace BbscMod {
u64 EbootAddress(){return image;}
void LogPlain(const char*){}
}
'''
fixture += function('void HoldBbscQuitCharacter(const BbscPendingQuit& q)')
fixture += function('void PS4_SYSV_ABI BbscQuitMovementHook(u64, const GuestRegisterSnapshot* registers)')
fixture += r'''
int main(){
    image=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));
    assert(image);
    // Preserve r12/r14; r12=control, r14=override. Native CMP/JNE selects
    // disabled permission, then TEST r14b/JNE may override it to one.
    const u8 code[]={0x41,0x54,0x41,0x56,0x49,0x89,0xFC,0x49,0x89,0xF6,
        0x41,0x80,0xBC,0x24,0x11,0x01,0,0,0,0x75,7,
        0xB8,1,0,0,0,0xEB,2,0x31,0xC0,
        0x45,0x84,0xF6,0x74,5,0xB8,1,0,0,0,
        0x41,0x5E,0x41,0x5C,0xC3};
    auto* start=reinterpret_cast<u8*>(image);
    std::memcpy(start,code,sizeof(code));
    using Move=u64 PS4_SYSV_ABI (*)(u64,u64);
    auto move=reinterpret_cast<Move>(start);
    alignas(16) u8 chr[0x60]{}, control[0x120]{}, remote[0x120]{};
    player=reinterpret_cast<u64>(chr);
    *reinterpret_cast<u64*>(chr+0x58)=reinterpret_cast<u64>(control);
    control[0x111]=1;
    assert(move(reinterpret_cast<u64>(control),0)==0);
    assert(move(reinterpret_cast<u64>(control),1)==1); // reproduces old override
    assert(Core::InstallGuestCodeHook(start+10,std::span<const u8>{code+10,9},0,BbscQuitMovementHook));
    for(bool title : {false,true}){
        bbsc_pending_quit={};bbsc_title_quit={};
        (title?bbsc_title_quit:bbsc_pending_quit)={world,player,reinterpret_cast<u64>(control)};
        for(u64 override_flag : {0ULL,1ULL}){
            control[0x111]=0; // native reset after ordinary tick
            assert(move(reinterpret_cast<u64>(control),override_flag)==0);
            assert(control[0x111]==1);
        }
        assert(move(reinterpret_cast<u64>(remote),1)==1);
        world=2;control[0x111]=0;
        assert(move(reinterpret_cast<u64>(control),1)==1);world=1;
        *reinterpret_cast<u64*>(chr+0x58)=reinterpret_cast<u64>(remote);
        assert(move(reinterpret_cast<u64>(control),1)==1);
        *reinterpret_cast<u64*>(chr+0x58)=reinterpret_cast<u64>(control);
    }
    bbsc_pending_quit={};bbsc_title_quit={};control[0x111]=0;
    assert(move(reinterpret_cast<u64>(control),1)==1);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-quit-override-') as temporary:
    cpp, exe = Path(temporary)/'test.cpp', Path(temporary)/'test.exe'
    cpp.write_text(fixture, encoding='utf-8')
    subprocess.run([os.environ.get('CXX','g++'), '-std=c++20', '-O0',
                    '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
                    '-I', str(ROOT/'emulator/src'), '-I', str(ROOT/'emulator/externals/xbyak'),
                    str(cpp), str(ROOT/'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=10)
print('Production quit movement override/trampoline: PASS')
