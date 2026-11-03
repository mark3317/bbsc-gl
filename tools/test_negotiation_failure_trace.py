"""Execute the production failure observer through its exact native instruction hook."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'emulator/mod/bbsc_channel.cpp').read_text(encoding='utf-8')
observer = source[source.index('void ReplyToFirstNativeExchange('):
                  source.index('void InstallDisconnectTrace()')]
fixture = r'''
#include <windows.h>
#include <atomic>
#include <cassert>
#include <cstring>
#include "core/cpu_patches.h"
u64 image;
namespace BbscMod {
u64 EbootAddress() { return image; }
void LogPlain(const char*) {}
bool ReadSlotSafely(u64 address, u64* value) {
    if (!address) return false;
    std::memcpy(value, reinterpret_cast<void*>(address), 8); return true;
}
}
namespace BbscMod {
bool WriteSlotSafely(u64 address,u64 value){std::memcpy((void*)address,&value,8);return true;}
}
unsigned logs=0,exchange_logs=0;
void CaptureInfo(const char*, u64 exchange,u32 channel,u32 subtype,u32 bytes,u32 tag,u32 version) {
    assert(exchange && channel==0 && subtype==0 && bytes==2 && tag==0x2d && version==7);++exchange_logs;
}
void CaptureInfo(const char*, u64 outer,u64 channel,u64 exchange) { assert(outer&&channel&&exchange); }

u64 expected_target=0;
template<class... Args> void Capture(const char*, u64 site, u32 phase, float seconds,
    u32 task_phase, u64 result, bool channel, bool exchange, bool ready, bool accepted) {
    assert(site==0x1481AF9 && phase==12 && seconds==0.0f);
    assert(task_phase==12 && result==0x1234 && channel && exchange && ready && !accepted);
    ++logs;
}
template<class... Args> void Capture(const char*, u64 site, u64 target, u32 kind, u32 bytes,
    u32 room, u32 member, u32 self_room, u32 self_member) {
    assert(site==0x1789742 && target==expected_target && kind==17 && bytes==48);
    assert(room==14 && member==34 && self_room==0 && self_member==0); ++logs;
}
#define LOG_INFO(category, ...) CaptureInfo(__VA_ARGS__)
#define LOG_WARNING(category, ...) Capture(__VA_ARGS__)
OBSERVER
int main() {
    image=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));
    assert(image);
    // PUSH RBX; MOV RBX,RDI; exact failure-store instruction; MOVZX EAX,[RBX+D0]; POP RBX; RET.
    const u8 code[]={0x53,0x48,0x89,0xfb,0xc6,0x83,0xd0,0,0,0,1,
                     0x0f,0xb6,0x83,0xd0,0,0,0,0x5b,0xc3};
    auto* start=reinterpret_cast<u8*>(image);
    std::memcpy(start,code,sizeof(code));
    assert(Core::InstallGuestCodeHook(start+4,std::span<const u8>{code+4,7},0x1481AF9,TraceNativeNegotiationFailure));
    alignas(8) u8 outer[0x100]{}, task[0xc0]{}, channel[0x330]{}, exchange[0xa0]{};
    auto put=[](u8* p,size_t off,u64 v){std::memcpy(p+off,&v,8);};
    put(outer,0x0c,12); put(outer,0x38,reinterpret_cast<u64>(task));
    put(outer,0xd8,reinterpret_cast<u64>(channel));
    put(task,0xb4,12); put(task,0x68,0x1234);
    put(channel,0x20,reinterpret_cast<u64>(exchange)); put(exchange,0x90,1);
    // These snippets return EAX; upper RAX bits after MOV AL are unspecified.
    using Body=u32 PS4_SYSV_ABI (*)(void*);
    assert(reinterpret_cast<Body>(start)(outer)==1 && outer[0xd0]==1 && logs==1);
    // Native reject point uses stack locals and must preserve CMP flags for fallback.
    const u8 send_code[]={0x55,0x48,0x89,0xe5,0x48,0x81,0xec,0xa0,0,0,0,
        0x48,0x89,0xbd,0x68,0xff,0xff,0xff,
        0xc7,0x45,0x80,17,0,0,0,0xc7,0x85,0x7c,0xff,0xff,0xff,48,0,0,0,
        0x48,0x8b,0x45,0x80,0x83,0xf8,7,0x0f,0x93,0xc0,0xc9,0xc3};
    auto* send_start=start+0x1000;
    std::memcpy(send_start,send_code,sizeof(send_code));
    assert(Core::InstallGuestCodeHook(send_start+35,std::span<const u8>{send_code+35,7},
        0x1789742,TraceNativeSendFailure));
    alignas(8) u8 member[0x60]{};
    put(member,0,image+0x052C5C00); put(member,0x30,(34ull<<32)|14);
    u64 target=reinterpret_cast<u64>(member); expected_target=target;
    assert(reinterpret_cast<Body>(send_start)(&target)==1 && logs==2);
    // Full native 01478130 callback, including original validation and readiness writes.
    // Placed at original RVA so the RIP-relative version-owner reference is exact.
    const u8 exchange_code[]={0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,0x41,0x54,0x53,0x48,0x89,0xd3,0x49,0x89,0xf6,0x48,0x85,0xdb,0xf,0x84,0x91,0x0,0x0,0x0,0x48,0x8b,0x73,0x8,0x48,0x85,0xf6,0x74,0x21,0xf,0xb6,0x46,0x1,0x83,0xf8,0x1,0x75,0x14,0x4d,0x85,0xf6,0x74,0x7a,0x48,0x83,0xc6,0x4,0x49,0x8b,0x7e,0x20,0xe8,0x42,0x66,0x0,0x0,0xeb,0x6b,0x85,0xc0,0x75,0x67,0x4d,0x85,0xf6,0x74,0x62,0x48,0x85,0xf6,0x74,0x48,0x80,0x7e,0x4,0x2d,0x75,0x46,0x44,0x8a,0x7e,0x5,0x4c,0x8d,0x25,0x91,0x2f,0xc,0x4,0x49,0x8b,0x4,0x24,0x48,0x85,0xc0,0x75,0x25,0x48,0x8d,0x3d,0xca,0x31,0x4c,0x3,0x48,0x8d,0x15,0x17,0x32,0x4c,0x3,0x48,0x8d,0xd,0x98,0x2b,0x4c,0x3,0xbe,0xb1,0x0,0x0,0x0,0x31,0xc0,0xe8,0xf7,0xd3,0xc3,0x0,0x49,0x8b,0x4,0x24,0x44,0x3a,0x78,0xc,0xf,0x94,0xc0,0xeb,0x6,0x31,0xc0,0xeb,0x2,0x31,0xc0,0x41,0xc6,0x86,0x90,0x0,0x0,0x0,0x1,0x41,0x88,0x86,0x91,0x0,0x0,0x0,0x48,0x89,0xd8,0x5b,0x41,0x5c,0x41,0x5e,0x41,0x5f,0x5d,0xc3};
    auto* exchange_start=start+0x1478130;std::memcpy(exchange_start,exchange_code,sizeof(exchange_code));
    alignas(8) u8 version_owner[32]{};version_owner[12]=7;
    put(reinterpret_cast<u8*>(image),0x553b120,reinterpret_cast<u64>(version_owner));
    assert(Core::InstallGuestCodeHook(exchange_start,std::span<const u8>{exchange_code,6},0x1478130,TraceNativeExchangeReceive));
    alignas(8) u8 blob[0x10]{},message[8]{0,0,2,0,0x2d,7};
    put(blob,8,reinterpret_cast<u64>(message));
    using Receive=u64 PS4_SYSV_ABI (*)(u64,void*,void*);
    assert(reinterpret_cast<Receive>(exchange_start)(0,exchange,blob)==reinterpret_cast<u64>(blob));
    assert(exchange_logs==1);
    // Actual callback entry trampoline queues native response only on first
    // valid version, never overwriting native readiness or other fields.
    put(exchange,0x90,0);put(exchange,0x88,0x1234567800000000ull);
    assert(reinterpret_cast<Receive>(exchange_start)(0,exchange,blob)==reinterpret_cast<u64>(blob));
    u64 pending=0;std::memcpy(&pending,exchange+0x88,8);
    assert(pending==0x1234567800000101ull && exchange[0x90]==1 && exchange[0x91]==1);
    // Native consumes flags and marks receive complete. Duplicates don't echo.
    put(exchange,0x88,0);put(exchange,0x90,0x101);
    reinterpret_cast<Receive>(exchange_start)(0,exchange,blob);
    assert(exchange[0x88]==0 && exchange[0x89]==0 && exchange[0x91]==1);
    Core::GuestRegisterSnapshot regs{};regs.rsi=reinterpret_cast<u64>(exchange);regs.rdx=reinterpret_cast<u64>(blob);
    put(exchange,0x90,0);
    for(int bad=0;bad<4;++bad){
      message[0]=0;message[1]=0;message[4]=0x2d;message[5]=7;
      if(bad==0)message[0]=1;if(bad==1)message[1]=1;if(bad==2)message[4]=0;if(bad==3)message[5]=8;
      ReplyToFirstNativeExchange(&regs);assert(exchange[0x88]==0 && exchange[0x89]==0);
    }
    ReplyToFirstNativeExchange(nullptr);
    for (int i=0;i<100;++i) assert(reinterpret_cast<Body>(send_start)(&target)==1);
    assert(logs==2); // diagnostic throttle must preserve native result/flags

}
'''.replace('OBSERVER', observer)
with tempfile.TemporaryDirectory(prefix='bbsc-negotiation-trace-') as temporary:
    cpp, exe = Path(temporary)/'fixture.cpp', Path(temporary)/'fixture.exe'
    cpp.write_text(fixture, encoding='utf-8')
    subprocess.run([os.environ.get('CXX', 'g++'), '-std=c++20', '-O0', '-DNOMINMAX',
        '-DWIN32_LEAN_AND_MEAN', '-I', str(ROOT/'emulator/src'),
        '-I', str(ROOT/'emulator/externals/xbyak'), str(cpp),
        str(ROOT/'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=10)
print('Native failure observer: original fields and exact mid-function trampoline: PASS')
