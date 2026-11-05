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
#include <atomic>
#include <string_view>
using u64=uint64_t;using u32=uint32_t;using u8=uint8_t;using s32=int32_t;using s64=int64_t;
#define BBSC_MOD
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
constexpr u64 MatchingStatePointerOffset=0x5540290,CandidateLocalStatePointerOffset=0x553e878;
constexpr u64 MultiPlayStopRequestOffset=0x1ed07a0;
u64 image_base=0,world=0,global=0,player=0,entries=0,manager=0,lua=0;
std::atomic<bool> bbsc_beckoning_silenced{false};
s64 now_ms=1000,bbsc_host_blank_requested_ms=0;
s32 session=3,hp=100,stops=0,cleanups=0,leaves=0,cancels=0;
s32 members=1;
bool bbsc_v8_pending=false;
std::atomic<s64> bbsc_reinsert_armed_ms{0};
std::atomic<bool> bbsc_host_selected_blank{false};
s32 GetBbscSessionMemberCount(u64){return members;}
constexpr u64 SummonSessionRulesPointerOffset=0x0553D6D0;
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
const char16_t* BbscL(const char16_t* text,const char16_t*){return text;}
int notices=0;
void BbscAnnounce(const char16_t*,std::string_view){++notices;}
struct GuestRegisterSnapshot {u64 rsp=0,rsi=0;};
bool IsValidMemberId(u64 p){return p==image_base+0x9000+0x3d8;}
void SendBbscSessionLeave(){++leaves;}
void CleanupBbscDepartingRemotes(){assert(stops==cleanups+1);++cleanups;}
u8 PS4_SYSV_ABI Stop(u64 p){assert(p==manager);assert(!bell);++stops;session=7;return 1;}
'''
for signature in ['void PS4_SYSV_ABI BbscHostKickRequestHook(u64, const GuestRegisterSnapshot* registers)',
                  'void TickBbscHostSearchLimit()',
                  'void ObserveBbscHostBlankItem(u32 goods)',
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
 // Live regression: search expires with two guests; 47s later Dream load
 // temporarily contains only the host. Execute both production ticks in order.
 WriteValue<s32>(world,0x30,3);WriteValue<u64>(entries,0x38,image_base+0x9000);WriteValue<u64>(entries,0x70,image_base+0xa000);
 TickBbscHostSearchLimit();TickBbscHostBlank();now_ms+=300000;
 TickBbscHostSearchLimit();TickBbscHostBlank();assert(!bell&&notices==1&&cancels==0&&stops==0);
 now_ms+=46000;WriteValue<u8>(global,8,1);WriteValue<s32>(world,0x30,0);
 TickBbscHostSearchLimit();TickBbscHostBlank();assert(session==3&&stops==0);
 now_ms+=1000;WriteValue<u8>(global,8,0);WriteValue<s32>(world,0x30,1);
 TickBbscHostSearchLimit();TickBbscHostBlank();assert(session==3&&stops==0&&cleanups==0&&leaves==0&&cancels==0);
 now_ms+=4000;TickBbscHostBlank();assert(session==3&&stops==0); // arrival/reinsert window
 WriteValue<s32>(world,0x30,3);TickBbscHostBlank();assert(session==3&&cancels==0);
 // An empty host also survives passive bell disappearance without a load.
 WriteValue<s32>(world,0x30,1);bell=true;TickBbscHostBlank();bell=false;
 TickBbscHostBlank();now_ms+=4000;TickBbscHostBlank();assert(stops==0&&cancels==0);
 bell=true;
 // An actual Blank must not close a room whose connected guest has no actor
 // during Dream arrival, or whose native membership is not readable yet.
 now_ms+=4000;
 members=2;assert(!CloseBbscEmptyBlankHost(now_ms-3001));assert(stops==0&&bell);
 members=-1;assert(!CloseBbscEmptyBlankHost(now_ms-3001));assert(stops==0);
 members=1;bbsc_v8_pending=true;assert(!CloseBbscEmptyBlankHost(now_ms-3001));
 bbsc_v8_pending=false;bbsc_reinsert_armed_ms=now_ms;assert(!CloseBbscEmptyBlankHost(now_ms-3001));
 bbsc_reinsert_armed_ms=0;
 WriteValue<u64>(image_base,SummonSessionRulesPointerOffset,image_base+0xb000);
 WriteValue<s32>(image_base+0xb000,0x84,3);assert(!CloseBbscEmptyBlankHost(now_ms-3001));
 WriteValue<s32>(image_base+0xb000,0x84,4);
 // Selected kick consumes the generic item intent, including its later effect
 // edge. The remaining guest's transient actor absence cannot close the room.
 GuestRegisterSnapshot kick{image_base+0xc000,image_base+0x9000};
 WriteValue<u64>(kick.rsp,0,image_base+0x015be462);
 session=6;BbscHostKickRequestHook(0,&kick);assert(!bbsc_host_selected_blank);session=3;
 WriteValue<u64>(kick.rsp,0,image_base+0x015be463);
 BbscHostKickRequestHook(0,&kick);assert(!bbsc_host_selected_blank);
 WriteValue<u64>(kick.rsp,0,image_base+0x015be462);
 kick.rsi=player;BbscHostKickRequestHook(0,&kick);assert(!bbsc_host_selected_blank);
 kick.rsi=image_base+0x9000;
 ObserveBbscHostBlankItem(111);TickBbscHostBlank();BbscHostKickRequestHook(0,&kick);
 assert(bbsc_host_selected_blank);
 blank_effect=true;TickBbscHostBlank();blank_effect=false;TickBbscHostBlank();
 now_ms+=11000;TickBbscHostBlank();assert(stops==0&&cancels==0&&bell);
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
 // Explicit menu silence can bypass generic item executors and SpEffect 7.
 TickBbscHostBlank();bbsc_beckoning_silenced=true;TickBbscHostBlank();now_ms+=3001;TickBbscHostBlank();assert(stops==3);
 session=0;TickBbscHostBlank();session=3;bell=true;TickBbscHostBlank();
 // A bell disappearing across a load does not authorize termination.
 WriteValue<u8>(global,8,1);bell=false;TickBbscHostBlank();WriteValue<u8>(global,8,0);
 now_ms+=4000;TickBbscHostBlank();assert(stops==3);
 // Runtime item state is also sufficient, without a generic item hook or effect.
 WriteValue<u32>(player,0x1c0,111);WriteValue<u32>(player,0x490,3);TickBbscHostBlank();
 WriteValue<u32>(player,0x490,0);now_ms+=3001;TickBbscHostBlank();assert(stops==4);
 // Confirmed silence with no room (the runtime item hooks never ran).
 session=0;bell=true;bbsc_beckoning_silenced=true;const int before=cancels;
 TickBbscHostBlank();assert(!bell&&cancels>before&&!bbsc_beckoning_silenced);
 // An existing guest stays; owner release waits for actual native drain.
 session=3;bell=true;WriteValue<s32>(world,0x30,2);WriteValue<u64>(entries,0x38,image_base+0x9000);
 bbsc_beckoning_silenced=true;TickBbscHostBlank();now_ms+=4000;TickBbscHostBlank();
 assert(!bell&&stops==4&&session==3);
 WriteValue<s32>(world,0x30,1);TickBbscHostBlank();assert(stops==5&&session==7);
 VirtualFree((void*)image_base,0,MEM_RELEASE);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-blank-host-') as temporary:
    cpp, exe = Path(temporary)/'fixture.cpp', Path(temporary)/'fixture.exe'
    cpp.write_text(fixture, encoding='utf-8')
    subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O0',str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=10)
print('Host Blank: 300s search expiry + Dream load preserves party; explicit item/effect/menu cancellation, native drain and later host PASS')
