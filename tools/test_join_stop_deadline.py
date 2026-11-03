"""Execute the production hook and exact native deadline predicate/trampoline."""
from pathlib import Path
import os,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
hook=s[s.index('void PS4_SYSV_ABI BbscJoiningStopDeadlineHook('):s.index('\nvoid InstallBbscStopHooks()')]
fixture=r'''
#include <windows.h>
#include <cassert>
#include <cstring>
#include "core/cpu_patches.h"
using Core::GuestRegisterSnapshot;
#define LOG_INFO(...)
u64 image_base; int state=0;
constexpr u64 MatchingStatePointerOffset=0x88;
namespace BbscMod { void LogPlain(const char*){} u64 EbootAddress(){return image_base;} }
template<class T>T ReadValue(u64 p,size_t off){T v;std::memcpy(&v,reinterpret_cast<void*>(p+off),sizeof(v));return v;}
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
int GetSessionState(){return state;}
int aborted=0;
void PS4_SYSV_ABI abort_join(u64){++aborted;}
HOOK
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0xD00000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE));assert(image_base);
 alignas(16) u8 manager[0x140]{},controller[0x70]{},other[0x70]{},sentinel[0x18]{},node[0x18]{},task[0x30]{};
 auto put=[](u8*p,size_t n,u64 v){std::memcpy(p+n,&v,8);};
 put(reinterpret_cast<u8*>(image_base),MatchingStatePointerOffset,reinterpret_cast<u64>(manager));
 put(manager,0x18,reinterpret_cast<u64>(controller));
 for(auto*c:{controller,other}){put(c,0x10,reinterpret_cast<u64>(sentinel));put(c,0x58,100);}
 put(sentinel,0,reinterpret_cast<u64>(node));put(node,0x10,reinterpret_cast<u64>(task));
 put(task,0x18,200);put(task,0x24,8);
 // Actual C9C6A0, hook at +0xB: MOV deadline; CMP now; SETB AL; RET.
 const u8 code[]={0x48,0x8b,0x47,0x10,0x48,0x8b,0x00,0x48,0x8b,0x40,0x10,
  0x48,0x8b,0x40,0x18,0x48,0x3b,0x47,0x58,0x0f,0x92,0xc0,0xc3};
 auto*p=reinterpret_cast<u8*>(image_base+0xC9C6A0);std::memcpy(p,code,sizeof(code));
 assert(Core::InstallGuestCodeHook(p+11,std::span<const u8>{code+11,8},0xC9C6AB,BbscJoiningStopDeadlineHook));
 using Predicate=u8 PS4_SYSV_ABI (*)(void*);auto predicate=reinterpret_cast<Predicate>(p);
 for(state=0;state<=6;++state)assert(predicate(controller)==0);
 state=7;assert(predicate(controller)==1 && predicate(other)==0);
 assert(ReadValue<u64>(reinterpret_cast<u64>(task),0x18)==200); // no task mutation
 put(task,0x24,12);assert(predicate(controller)==0); // queued Stop not altered
 put(task,0x24,8);put(controller,0x58,0);assert(predicate(controller)==0);
 put(controller,0x58,100);put(task,0x18,50);state=6;assert(predicate(controller)==1); // real timeout retained
 // Exact CC51F0 native join wait. Its readiness helper returns false; native
 // vfunc120 is the hooked predicate, vfunc110 observes the failure cleanup.
 const u8 wait_code[]={0x55,0x48,0x89,0xe5,0x53,0x50,0x48,0x89,0xfb,0xe8,0xd2,0x74,0xfd,0xff,0x84,0xc0,0x74,0x11,0x48,0x8d,0x35,0x37,0,0,0,0x31,0xd2,0x48,0x89,0xdf,0xe8,0x0d,0x5b,0xff,0xff,0x48,0x8b,0x03,0x48,0x89,0xdf,0xff,0x90,0x20,0x01,0,0,0x84,0xc0,0x74,0x12,0x48,0x8b,0x03,0x48,0x89,0xdf,0x48,0x83,0xc4,0x08,0x5b,0x5d,0xff,0xa0,0x10,0x01,0,0,0x48,0x83,0xc4,0x08,0x5b,0x5d,0xc3};
 auto*wait=reinterpret_cast<u8*>(image_base+0xCC51F0);std::memcpy(wait,wait_code,sizeof(wait_code));
 const u8 not_ready[]={0x31,0xc0,0xc3};std::memcpy(reinterpret_cast<void*>(image_base+0xC9C6D0),not_ready,3);
 alignas(16) u8 vtable[0x130]{};put(vtable,0x110,reinterpret_cast<u64>(&abort_join));put(vtable,0x120,reinterpret_cast<u64>(p));put(controller,0,reinterpret_cast<u64>(vtable));
 using Wait=void PS4_SYSV_ABI (*)(void*);auto native_wait=reinterpret_cast<Wait>(wait);
 put(task,0x18,200);state=4;native_wait(controller);assert(aborted==0);
 state=7;native_wait(controller);assert(aborted==1);
 put(task,0x24,12);native_wait(controller);assert(aborted==1);
 put(task,0x24,8);state=6;put(task,0x18,50);native_wait(controller);assert(aborted==2);
}
'''.replace('HOOK',hook)
with tempfile.TemporaryDirectory(prefix='bbsc-join-stop-') as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text(fixture,encoding='utf-8')
 subprocess.run([os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe'),'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-I',str(root/'emulator/src'),'-I',str(root/'emulator/externals/xbyak'),str(cpp),str(root/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=10)
print('Native join Stop: exact deadline CMP/SETB trampoline, controller/task/state isolation: PASS')
