"""Execute production host Blank completion with native Stop stubbed in executable memory."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')

def function(signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

fixture = r'''
#include <windows.h>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using u64=uint64_t;using u32=uint32_t;using u8=uint8_t;using s32=int32_t;using s64=int64_t;
#define BBSC_MOD
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
constexpr u64 MatchingStatePointerOffset=0x5540290,CandidateLocalStatePointerOffset=0x553e878;
constexpr u64 MultiPlayStopRequestOffset=0x1ed07a0;
u64 image_base=0,world=0,global=0,player=0,entries=0,manager=0,lua=0;
s64 now_ms=1000,bbsc_host_blank_requested_ms=0;
s32 session=3,hp=100,stops=0,cleanups=0,leaves=0,cancels=0;
bool quit=false,foreign=false,erase_ok=true,bell=true,blank_effect=false,bbsc_duel_bell_ready=true;
std::vector<int> bbsc_blank_effect_rows{7};
bool ReadablePointer(u64 p,size_t n){return p>=image_base&&n<=0x5600000&&p-image_base<=0x5600000-n;}
template<class T>T ReadValue(u64 p,size_t off){assert(ReadablePointer(p+off,sizeof(T)));T v;std::memcpy(&v,(void*)(p+off),sizeof(T));return v;}
template<class T>bool WriteValue(u64 p,size_t off,T v){assert(ReadablePointer(p+off,sizeof(T)));std::memcpy((void*)(p+off),&v,sizeof(T));return true;}
s64 SteadyNowMs(){return now_ms;}s32 GetSessionState(){return session;}
bool BbscQuitInProgress(){return quit;}bool BbscInAnotherWorld(){return foreign;}
u64 GetGlobalState(){return global;}u64 GetLocalPlayerCharacter(){return player;}
s32 GetCharacterHp(u64){return hp;}
u64 BbscLocalEffectNode(int id){assert(id==9000);return bell;}
bool BbscEraseLocalEffect(int id){assert(id==9000);if(erase_ok)bell=false;return erase_ok;}
bool BbscLocalEffectActive(const std::vector<int>&){return blank_effect;}
namespace BbscMod {void PartyCancel(){++cancels;}}
void SendBbscSessionLeave(){++leaves;}
void CleanupBbscDepartingRemotes(){assert(stops==cleanups+1);++cleanups;}
u8 PS4_SYSV_ABI Stop(u64 p){assert(p==manager);assert(!bell);++stops;session=7;return 1;}
'''
for signature in ['void ObserveBbscHostBlankItem(u32 goods)',
                  'bool CloseBbscEmptyBlankHost(s64 requested_ms)',
                  'void TickBbscHostBlank()']:
    fixture += function(signature) + '\n'
fixture += r'''
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x5600000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image_base);
 world=image_base+0x1000;global=image_base+0x2000;player=image_base+0x4000;entries=image_base+0x5000;manager=image_base+0x6000;lua=image_base+0x7000;
 WriteValue<u64>(image_base,MatchingStatePointerOffset,manager);WriteValue<u64>(image_base,CandidateLocalStatePointerOffset,world);
 WriteValue<u64>(image_base,0x553b0c8,image_base+0x8000);WriteValue<u64>(image_base+0x8000,8,lua);
 WriteValue<u8>(global,0x1592,1);WriteValue<u64>(world,0x60,player);WriteValue<s32>(world,0x30,1);WriteValue<u64>(world,0x38,entries);WriteValue<u64>(entries,0,player);
 u8 jump[]={0x48,0xb8,0,0,0,0,0,0,0,0,0xff,0xe0};u64 stop=(u64)&Stop;std::memcpy(jump+2,&stop,8);std::memcpy((void*)(image_base+MultiPlayStopRequestOffset),jump,sizeof(jump));
 ObserveBbscHostBlankItem(201);assert(!bbsc_host_blank_requested_ms);
 session=6;ObserveBbscHostBlankItem(111);assert(!bbsc_host_blank_requested_ms);
 session=3;quit=true;ObserveBbscHostBlankItem(111);assert(!bbsc_host_blank_requested_ms);quit=false;
 ObserveBbscHostBlankItem(111);TickBbscHostBlank();assert(stops==0); // effect absent, item entry retained
 now_ms+=3001;
 WriteValue<s32>(world,0x30,2);WriteValue<u64>(entries,0x38,image_base+0x9000);TickBbscHostBlank();assert(stops==0&&bell); // remaining guest
 WriteValue<u64>(entries,0x38,1);TickBbscHostBlank();assert(stops==0); // unreadable remote, fail closed
 WriteValue<s32>(world,0x30,0);TickBbscHostBlank();assert(stops==0); // table not ready
 WriteValue<s32>(world,0x30,1);WriteValue<u8>(global,8,1);TickBbscHostBlank();assert(stops==0);
 WriteValue<u8>(global,8,0);hp=0;TickBbscHostBlank();assert(stops==0);hp=100;
 foreign=true;TickBbscHostBlank();assert(stops==0);foreign=false;
 quit=true;TickBbscHostBlank();assert(stops==0&&cancels==0);quit=false;
 erase_ok=false;TickBbscHostBlank();assert(stops==0&&bell);erase_ok=true;
 TickBbscHostBlank();assert(stops==1&&cleanups==1&&leaves==1&&cancels==1&&session==7&&!bell);
 TickBbscHostBlank();assert(stops==1); // native Stop is never repeated while stopping
 session=0;WriteValue<u8>(lua,0x8d,1);TickBbscHostBlank();assert(!ReadValue<u8>(lua,0x8d)&&cancels==2);
 session=3;bell=true;now_ms+=60000;TickBbscHostBlank();assert(stops==1&&bell); // later host survives
 // Existing effect-only path still drains an empty host, including no Lua lock.
 blank_effect=true;TickBbscHostBlank();blank_effect=false;now_ms+=3001;TickBbscHostBlank();assert(stops==2);
 session=0;TickBbscHostBlank();session=3;bell=true;now_ms+=10000;TickBbscHostBlank();assert(stops==2&&bell);
 // Host item can bypass both generic item executors and leave no SpEffect 7.
 TickBbscHostBlank();bell=false;TickBbscHostBlank();now_ms+=3001;TickBbscHostBlank();assert(stops==3);
 session=0;TickBbscHostBlank();session=3;bell=true;TickBbscHostBlank();
 // A bell disappearing across a load does not authorize termination.
 WriteValue<u8>(global,8,1);bell=false;TickBbscHostBlank();WriteValue<u8>(global,8,0);
 now_ms+=4000;TickBbscHostBlank();assert(stops==3);
 // Runtime item state is also sufficient, without a generic item hook or effect.
 WriteValue<u32>(player,0x1c0,111);WriteValue<u32>(player,0x490,3);TickBbscHostBlank();
 WriteValue<u32>(player,0x490,0);now_ms+=3001;TickBbscHostBlank();assert(stops==4);
 VirtualFree((void*)image_base,0,MEM_RELEASE);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-blank-host-') as temporary:
    cpp, exe = Path(temporary)/'fixture.cpp', Path(temporary)/'fixture.exe'
    cpp.write_text(fixture, encoding='utf-8')
    subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O0',str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=10)
print('Host Blank: actual item latch, empty-world gate, native Stop/cleanup, idle release and later host PASS')
