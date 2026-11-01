"""Run the production Windows hook trampoline on synthetic code, never on the game."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
fixture = r'''
#include <windows.h>
#include <cassert>
#include <cstdio>
#include <cstring>
#include "core/cpu_patches.h"
u64 image;
u8 skip=0;
bool should_skip=false;
namespace BbscMod {
u64 EbootAddress() { return image; }
void LogPlain(const char* text) { std::puts(text); }
}
void PS4_SYSV_ABI callback(u64 tag, const Core::GuestRegisterSnapshot* snapshot) {
    skip=should_skip ? 1 : 0;
    if (tag==1 && should_skip) const_cast<Core::GuestRegisterSnapshot*>(snapshot)->rax=13;
}
int main() {
    image=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));
    assert(image);
    // push rbp; mov rbp,rsp; mov rax,rdi; mov dword [rax],7; mov eax,42; pop rbp; ret
    const u8 code[]={0x55,0x48,0x89,0xE5,0x48,0x89,0xF8,0xC7,0,7,0,0,0,0xB8,42,0,0,0,0x5D,0xC3};
    auto* start=reinterpret_cast<u8*>(image);
    std::memcpy(start,code,sizeof(code));
    using Body=u64 PS4_SYSV_ABI (*)(int*);
    auto body=reinterpret_cast<Body>(start);
    int value=5;
    assert(body(&value)==42 && value==7);
    assert(Core::InstallGuestCodeHook(start+7,std::span<const u8>{code+7,6},0,callback,&skip,true));
    for (bool enabled : {false,true,false,true}) {
        should_skip=enabled; value=5;
        assert(body(&value)==42); // resumed in the body, preserved its stack/return path
        assert(value==(enabled ? 5 : 7));
        assert(skip==0);
    }
    const u8 entry_code[]={0xB8,99,0,0,0,0xC3};
    std::memcpy(start+0x1000,entry_code,sizeof(entry_code));
    using Entry=u64 PS4_SYSV_ABI (*)();
    auto entry=reinterpret_cast<Entry>(start+0x1000);
    assert(Core::InstallGuestCodeHook(start+0x1000,std::span<const u8>{entry_code,5},1,callback,&skip));
    should_skip=false; assert(entry()==99);
    should_skip=true; assert(entry()==13); // existing entry-skip API still returns to caller
    // Native Yes callback: initial LEA has no stack effects. Hook its next MOV/CMP,
    // so RET skips the entire callback before native save flags can be written.
    const u8 yes_code[]={0x48,0x8D,0x05,0xF9,0x00,0x00,0x00,
        0x48,0x8B,0x00,0x48,0x83,0x78,0x08,0x00,0xB8,99,0,0,0,0xC3};
    auto* yes_start=start+0x2000;
    std::memcpy(yes_start,yes_code,sizeof(yes_code));
    *reinterpret_cast<u64*>(yes_start+0x100)=reinterpret_cast<u64>(yes_start+0x200);
    auto yes=reinterpret_cast<Entry>(yes_start);
    assert(Core::InstallGuestCodeHook(yes_start+7,std::span<const u8>{yes_code+7,8},1,callback,&skip));
    for(int n=0;n<10;++n){
        should_skip=false; assert(yes()==99);
        should_skip=true; assert(yes()==13 && skip==0);
    }
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-hook-resume-') as temporary:
    cpp = Path(temporary) / 'fixture.cpp'
    exe = Path(temporary) / 'fixture.exe'
    cpp.write_text(fixture, encoding='utf-8')
    subprocess.run([
        os.environ.get('CXX', 'g++'), '-std=c++20', '-O0', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
        '-I', str(ROOT / 'emulator/src'), '-I', str(ROOT / 'emulator/externals/xbyak'),
        str(cpp), str(ROOT / 'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe),
    ], check=True)
    subprocess.run([str(exe)], check=True, timeout=10)
print('Production trampoline: mid-function resume and existing function-entry skip: PASS')
