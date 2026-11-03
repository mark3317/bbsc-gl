"""Production explicit-host-leave grace and native/fallback return ownership."""
from pathlib import Path
import os,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
source=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
 start=source.index(signature+' {');end=source.index('{',start)+1;depth=1
 while depth:depth+=(source[end]=='{')-(source[end]=='}');end+=1
 return source[start:end]
code=r"""
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <string_view>
using u64=uint64_t;using u32=uint32_t;using u8=uint8_t;using s64=int64_t;using s32=int32_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
#define BBSC_PERF_SCOPE(...)
struct GuestRegisterSnapshot {u64 rsp=0;};
std::array<u8,0x1800> memory{};
u64 image_base=1;int state=0,home_calls=0,transitions=0;
s64 now=1000,bbsc_persistence_restore_at_ms=100,bbsc_confirmed_departure_ms=0;
bool own=false,loading=false,quit=false,finale=false,ready=true;
bool bbsc_home_return_claimed=false,bbsc_release_leave_locks=false;
u8 bbsc_send_home_skip=0;
std::atomic<u32> bbsc_explicit_host_leave_pending{0};
constexpr s64 BbscStrandedMs=15000,BbscConfirmedHostLeaveMs=1000;
u64 GetGlobalState(){return reinterpret_cast<u64>(memory.data());}
int GetSessionState(){return state;}
bool BbscOwnWorldNonGuest(u64){return own;}
bool BbscQuitInProgress(){return quit;}
bool BbscDreamFinaleHolding(){return finale;}
bool BbscGuestStayingInSession(){return state==6 && bbsc_persistence_restore_at_ms==0;}
s64 SteadyNowMs(){return now;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
bool IsSprjLuaEventManReady(){return ready;}
u64 GetLocalPlayerCharacter(){return 1;}
int GetCharacterHp(u64){return 100;}
namespace MemoryProt {constexpr int CpuRead=1;}
bool HasMemoryAccess(u64,size_t,int){return false;}
template<class T>T ReadValue(u64 p,size_t offset){
 if(p==GetGlobalState())return offset==8?loading:offset==0x1592?own:0;
 if(p==image_base+0x0553B0C8)return 100;
 if(p==100 && offset==8)return 200;
 if(p==image_base+0x0553B0D8)return 300;
 return 0;
}
int event_state=0;
template<class T>void WriteValue(u64 p,size_t offset,T value){
 if(p==300)event_state=value;
 else memory.at(offset)=value;
}
void ClearBbscBossContext(std::string_view){}
void home(u64 lua,s32 point){assert(lua==200 && point==-1);assert(bbsc_home_return_claimed && event_state==2 && memory[0x1520]==1);++home_calls;}
u64 transition(){assert(home_calls>transitions);++transitions;loading=true;return 0;}
int peer_calls=0;void OnBbscPeerLeft(u32,bool){++peer_calls;}
"""
code+=function('void OnBbscExplicitSessionLeave(std::uint32_t player, bool host)')+'\n'
code+=function('void TickBbscStrandedGuest()').replace('image_base + 0x01332BC0','reinterpret_cast<u64>(&home)').replace('image_base + 0x013CDE30','reinterpret_cast<u64>(&transition)')+'\n'
code+=function('void PS4_SYSV_ABI BbscSendPhantomHomeHook(u64, const GuestRegisterSnapshot* registers)')
code+=r"""
int main(){
 OnBbscExplicitSessionLeave(12,true);assert(bbsc_explicit_host_leave_pending==12 && peer_calls==1);
 OnBbscExplicitSessionLeave(13,false);assert(bbsc_explicit_host_leave_pending==12 && peer_calls==2);
 bbsc_confirmed_departure_ms=now;TickBbscStrandedGuest();assert(!transitions);
 now+=1000;TickBbscStrandedGuest();assert(transitions==1);
 // A native callback delayed until after the fast fallback cannot return twice.
 BbscSendPhantomHomeHook(0,nullptr);assert(bbsc_send_home_skip==1 && !bbsc_release_leave_locks);
 now+=5000;TickBbscStrandedGuest();assert(transitions==1);
 loading=false;own=true;now+=1000;TickBbscStrandedGuest();
 assert(!bbsc_home_return_claimed && bbsc_confirmed_departure_ms==0);
 // Ordinary loss retains15s grace; no shortening because of an earlier session.
 own=false;now+=1000;TickBbscStrandedGuest();now+=1000;TickBbscStrandedGuest();assert(transitions==1);
 now+=14000;TickBbscStrandedGuest();assert(transitions==2);
 // Quit/loading paths never start a home transition.
 own=true;loading=false;now+=1000;TickBbscStrandedGuest();own=false;quit=true;bbsc_confirmed_departure_ms=now;
 now+=2000;TickBbscStrandedGuest();assert(transitions==2);
 quit=false;loading=true;now+=2000;TickBbscStrandedGuest();assert(transitions==2);
}
"""
with tempfile.TemporaryDirectory() as tmp:
 cpp=Path(tmp)/'return.cpp';exe=Path(tmp)/'return.exe';cpp.write_text(code)
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('Explicit host leave: fast native return, ordinary15s grace, duplicate/load/title guards PASS')
