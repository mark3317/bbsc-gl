"""Exercise production HUD acknowledgement, without touching game memory or saves."""
from pathlib import Path
import subprocess, tempfile
root = Path(__file__).resolve().parents[1]
source = (root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a = source.index('constexpr u64 HudEchoWidgetUpdateOffset')
b = source.index('void InstallBbscEchoPathHooks()', a)
fixture = r'''
#include <atomic>
#include <cstdint>
#include <cassert>
#include <cstring>
using u64=uint64_t; using s64=int64_t; using s32=int32_t; using u8=uint8_t;
#define PS4_SYSV_ABI
#define BBSC_PERF_SCOPE(...)
#define LOG_WARNING(...) (++warnings)
struct GuestRegisterSnapshot { u64 r13; };
s64 clock_ms=1000; u64 image_base=1; s32 balance=100; int warnings=0;
u8 global[16]{};
s64 SteadyNowMs(){return clock_ms;}
s32 GetBloodEchoes(){return balance;}
u64 GetGlobalState(){return (u64)global;}
bool ReadablePointer(u64 p, unsigned){return p!=0;}
template<class T>T ReadValue(u64 p,unsigned o){T value; std::memcpy(&value,(void*)(p+o),sizeof value);return value;}
int GetSessionState(){return 6;} int GetLocalPlayerType(){return 1;}
''' + source[a:b] + r'''
void tick(s32 displayed, bool active=true){
 clock_ms+=1000;
 if(active){bbsc_echo_widget_displayed=displayed;bbsc_echo_widget_ms=clock_ms;}
 TickBbscEchoCounter();
}
int main(){
 for(int i=0;i<10;++i) tick(-1,false); assert(warnings==0); // never observed
 for(int i=0;i<8;++i) tick(100); assert(warnings==0); // acknowledged
 for(int i=0;i<10;++i) tick(10+i); assert(warnings==0); // native roll-up
 for(int i=0;i<10;++i){++balance;tick(1);} assert(warnings==0); // ongoing rewards
 for(int i=0;i<7;++i) tick(1); assert(warnings==1); // actual stalled display
 for(int i=0;i<5;++i) tick(1); assert(warnings==1); // bounded warning
 tick(balance); for(int i=0;i<7;++i) tick(2); assert(warnings==2); // rearm
 global[8]=1; for(int i=0;i<7;++i) tick(3); assert(warnings==2); // loading
 global[8]=0; for(int i=0;i<7;++i) tick(3,false); assert(warnings==2); // hidden
 alignas(8) u8 widget[0x1b0]{}; s32 text=123;
 std::memcpy(widget+0x18c,&text,4);GuestRegisterSnapshot regs{(u64)widget};
 BbscEchoWidgetHook(0,&regs);assert(bbsc_echo_widget_displayed==123);
 BbscEchoWidgetHook(0,nullptr);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-echo-hud-') as folder:
    cpp=Path(folder)/'fixture.cpp'; exe=Path(folder)/'fixture.exe'
    cpp.write_text(fixture,encoding='utf-8')
    subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20',str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('HUD acknowledgement production fixture: PASS')
