"""Run the production Windows hook trampoline on synthetic code, never on the game."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
# StopRequest is already a selected Sites hook. Its lightweight observer must
# execute through that owner even when research and capture are both disabled.
dispatch = source[source.index('void PS4_SYSV_ABI TraceEntry('):]
assert dispatch.index('BbscStopRequestHook(0, registers);') < dispatch.index(
    'if (!BbscResearchEnabled() && (!capture_file')
stop_install = source[source.index('void InstallBbscStopHooks()'):source.index(
    'void InstallBbscStopHooks()') + 1200]
assert 'image_base + 0x01ED07A0' not in stop_install
fixture = r'''
#include <windows.h>
#include <cassert>
#include <cstdio>
#include <cstring>
#include "core/cpu_patches.h"
u64 image;
u8 skip=0;
bool should_skip=false;
u64 stop_caller=0;
namespace BbscMod {
u64 EbootAddress() { return image; }
void LogPlain(const char* text) { std::puts(text); }
}
void PS4_SYSV_ABI callback(u64 tag, const Core::GuestRegisterSnapshot* snapshot) {
    if (tag==5) {
        if (should_skip) const_cast<Core::GuestRegisterSnapshot*>(snapshot)->rsi=15000012;
        return;
    }
    if (tag==4) {
        stop_caller=*reinterpret_cast<const u64*>(snapshot->rsp);
        assert(snapshot->rdi==17);
        return;
    }
    if (tag==3) {
        if (should_skip) *reinterpret_cast<u8*>(snapshot->r12+0x111)=1;
        return;
    }
    skip=should_skip ? 1 : 0;
    if (tag==1 && should_skip) const_cast<Core::GuestRegisterSnapshot*>(snapshot)->rax=13;
    if (tag==2 && should_skip) const_cast<Core::GuestRegisterSnapshot*>(snapshot)->rsi=0xDEADCAFE;
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
    // Actual save-vector hook instruction: RSI is the serializer's source;
    // the displaced LEA changes RDI only, so callback-supplied RSI must survive.
    const u8 vector_code[]={0x48,0x81,0xEC,0x18,1,0,0,0x48,0x89,0xFE,
        0x48,0x8D,0xBC,0x24,0,1,0,0,0x48,0x89,0xF0,
        0x48,0x81,0xC4,0x18,1,0,0,0xC3};
    auto* vector_start=start+0x3000;
    std::memcpy(vector_start,vector_code,sizeof(vector_code));
    using Vector=u64 PS4_SYSV_ABI (*)(u64);
    auto vector=reinterpret_cast<Vector>(vector_start);
    assert(Core::InstallGuestCodeHook(vector_start+10,std::span<const u8>{vector_code+10,8},2,callback));
    should_skip=false;assert(vector(0x1234)==0x1234);
    should_skip=true;assert(vector(0x1234)==0xDEADCAFE);
    // Exact native movement CMP followed by its JNE: callback must run before
    // CMP, then displaced instruction must establish the flags consumed by JNE.
    const u8 move_code[]={0x41,0x54,0x49,0x89,0xFC,
        0x41,0x80,0xBC,0x24,0x11,0x01,0,0,0,0x75,7,
        0xB8,1,0,0,0,0xEB,2,0x31,0xC0,0x41,0x5C,0xC3};
    auto* move_start=start+0x4000;
    std::memcpy(move_start,move_code,sizeof(move_code));
    auto move=reinterpret_cast<Vector>(move_start);
    assert(Core::InstallGuestCodeHook(move_start+5,std::span<const u8>{move_code+5,9},3,callback));
    u8 control[0x112]{};
    for(bool enabled : {false,true,false,true}) {
        control[0x111]=0; should_skip=enabled;
        assert(move(reinterpret_cast<u64>(control))==(enabled ? 0 : 1));
        assert(control[0x111]==(enabled ? 1 : 0));
    }
    // Exact member-arrival LEA: RSI carries the message id; RDI is a local
    // string destination. Replaying LEA must preserve the callback's new RSI.
    const u8 arrival_code[]={0x55,0x48,0x89,0xe5,0x48,0x81,0xec,0xf0,0,0,0,
        0x48,0x8d,0xbd,0x10,0xff,0xff,0xff,0x48,0x89,0xf0,0xc9,0xc3};
    auto* arrival_start=start+0x5000;
    std::memcpy(arrival_start,arrival_code,sizeof(arrival_code));
    using Arrival=u64 PS4_SYSV_ABI (*)(u64,u64);
    assert(Core::InstallGuestCodeHook(arrival_start+11,std::span<const u8>{arrival_code+11,7},5,callback));
    for(bool enabled : {false,true,false,true}) {
        should_skip=enabled;
        assert(reinterpret_cast<Arrival>(arrival_start)(0,102001)==(enabled ? 15000012 : 102001));
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
    // Native event dispatch may leave its existing stack through a VERIFIED
    // epilogue, without running the warp or instruction-advance body.
    const u8 tail_code[]={0x55,0x48,0x89,0xe5,0x48,0x89,0xf8,
        0xc7,0,7,0,0,0,0xc7,0x40,4,9,0,0,0,0xb8,42,0,0,0,0x5d,0xc3};
    auto* tail_start=start+0x4000;memcpy(tail_start,tail_code,sizeof(tail_code));
    assert(Core::InstallGuestCodeHook(tail_start+7,{tail_code+7,6},0,callback,&skip,false,tail_start+20));
    using Tail=u64 PS4_SYSV_ABI (*)(int*);auto tail=(Tail)tail_start;
    for(bool pending:{true,false,true,false}){
        should_skip=pending;int fields[]={1,2};
        assert(tail(fields)==42 && fields[0]==(pending?1:7) && fields[1]==(pending?2:9));
        assert(skip==0);
    }
    // Exact Stop entry prologue: observer reads the original caller before
    // PUSH RBP/PUSH R15, then the native body and epilogue run unchanged.
    const u8 stop_code[]={0x55,0x48,0x89,0xe5,0x41,0x57,
        0x48,0x89,0xf8,0x41,0x5f,0x5d,0xc3};
    auto* stop_start=start+0x3000;
    std::memcpy(stop_start,stop_code,sizeof(stop_code));
    using Stop=u64 PS4_SYSV_ABI (*)(u64);
    assert(Core::InstallGuestCodeHook(stop_start,std::span<const u8>{stop_code,6},4,callback));
    assert(reinterpret_cast<Stop>(stop_start)(17)==17 && stop_caller!=0);
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
