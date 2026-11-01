"""Production home-return functions, without game files or saves."""
from pathlib import Path
import os, subprocess
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
 a=s.index(signature+' {'); b=s.index('{',a)+1; n=1
 while n:
  n+=(s[b]=='{')-(s[b]=='}'); b+=1
 return s[a:b]
# The functional call must precede BOTH diagnostic exits; writer must have no actions.
dispatch=s[s.index('void PS4_SYSV_ABI TraceEntry('):]
assert dispatch.index('HandleBbscLuaSessionEvent(*registers)') < dispatch.index('if (!BbscResearchEnabled()')
assert dispatch.count('HandleBbscLuaSessionEvent(*registers)') == 1
assert 'KeepBbscHomeSpot' not in function('void WriteLuaSessionEvent(std::ostream& out, const GuestRegisterSnapshot& registers)')
assert 'TraceKind::LuaSessionEvent' in function('bool BbscFunctionalTraceSite(const TraceSite& site)')
code=r"""
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <optional>
#include <string>
#include <string_view>
#include <iostream>
using u64=uint64_t;using u32=uint32_t;using u8=uint8_t;using s32=int32_t;
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
std::array<u8,0x1600> memory{};
u64 image_base=1;int state=0;u32 map=0x15000000;
struct Transform {float position[3]={1,2,3};float rotation[3]={0,4,0};};
std::optional<Transform> transform=Transform{};
u64 GetGlobalState(){return (u64)memory.data();}
bool ReadablePointer(u64 p,size_t n){return p>=GetGlobalState()&&p+n<=GetGlobalState()+memory.size();}
template<class T>T ReadValue(u64 p,size_t off){T v{};if(ReadablePointer(p+off,sizeof(v)))memcpy(&v,(void*)(p+off),sizeof(v));return v;}
template<class T>bool WriteValue(u64 p,size_t off,T v){if(!ReadablePointer(p+off,sizeof(v)))return false;memcpy((void*)(p+off),&v,sizeof(v));return true;}
int GetSessionState(){return state;}u32 GetCurrentPackedMap(){return map;}
u64 GetLocalPlayerCharacter(){return 1;}
auto ReadCharacterTransform(u64){return transform;}
bool IsUsablePackedMap(u32 m){return m!=0;}
struct GuestRegisterSnapshot {u64 rsi=0,rcx=0,rbp=0;};
std::string ReadGuestAscii(u64 p,size_t){return (const char*)p;}
int captures=0,ledger=0,world=0,cover=0,leaves=0,ending=0,releases=0;
void CaptureBbscGuestRespawnPoint(){++captures;}
void DeliverBbscLedgerAtJoin(std::string_view){++ledger;}
void CaptureBbscOwnWorldBeforeJoin(){++world;}
void StartBbscLoadCover(std::string_view){++cover;}
void BbscLeaveItemUsed(std::string_view){++leaves;}
void NoteBbscSessionEnding(std::string_view){++ending;}
void ReleaseBbscGuestRespawnPoint(std::string_view){++releases;WriteValue<int>(GetGlobalState(),0x1528,2102961);}
"""
a=s.index('struct BbscHomeSpot {');b=s.index('void KeepBbscHomeSpot()',a)
code+=s[a:b]
for sig in ['void KeepBbscHomeSpot()', 'void TickBbscHomeSpot()', 'bool PutBbscHomeSpot(u64 global)', 'bool BbscOwnWorldNonGuest(u64 global)', 'void GuardBbscStrayForcedWarp(const GuestRegisterSnapshot& registers)', 'void HandleBbscLuaSessionEvent(const GuestRegisterSnapshot& registers)']:
 code+=function(sig)+'\n'
code+=r"""
void event(const char* name){GuestRegisterSnapshot r{};r.rsi=(u64)name;HandleBbscLuaSessionEvent(r);}
int main(){
 auto g=GetGlobalState();GuestRegisterSnapshot r{};r.rcx=g;
 WriteValue<u8>(g,0x1592,1);event("JoinSession_White");
 assert(bbsc_home_spot.valid && bbsc_home_spot.map==0x15000000);
 assert(captures==1&&ledger==1&&world==1&&cover==1);
 state=6;WriteValue<u8>(g,0x1592,0);TickBbscHomeSpot();
 map=0x1d000000;WriteValue<u32>(g,0x14f0,map);WriteValue<u8>(g,0x1520,1);
 // A follow/death reload while connected keeps its host destination.
 GuardBbscStrayForcedWarp(r);assert(ReadValue<u32>(g,0x14f0)==map&&releases==0);
 // Host departure inside chalice must return to the original Dream transform.
 state=0;GuardBbscStrayForcedWarp(r);
 assert(ReadValue<u32>(g,0x14f0)==0x15000000&&ReadValue<u8>(g,0x1520)==1);
 assert(ReadValue<float>(g,0x1500)==1&&ReadValue<float>(g,0x1514)==4&&releases==1);
 // Loading must not discard the snapshot; finish home consumes it.
 WriteValue<u8>(g,8,1);WriteValue<u8>(g,0x1592,1);TickBbscHomeSpot();assert(bbsc_home_spot.valid);
 WriteValue<u8>(g,8,0);TickBbscHomeSpot();assert(!bbsc_home_spot.valid);
 // Second session takes a new point, not the previous session's Dream.
 map=0x18010000;transform->position[0]=12;event("JoinSession_White");
 assert(bbsc_home_spot.map==map&&bbsc_home_spot.position[0]==12);
 state=6;WriteValue<u8>(g,0x1592,0);TickBbscHomeSpot();
 event("JoinSession_White");assert(bbsc_home_spot.map==0x18010000);
 // Missing capture / unavailable transform falls back to OWN lamp, not host m29.
 bbsc_home_spot={};state=0;WriteValue<u32>(g,0x14f0,0x1d000000);WriteValue<u8>(g,0x1520,1);
 GuardBbscStrayForcedWarp(r);assert(ReadValue<u8>(g,0x1520)==0&&ReadValue<int>(g,0x1528)==2102961);
 WriteValue<u8>(g,0x1592,1);transform.reset();event("JoinSession_White");assert(!bbsc_home_spot.valid);
 // Host never captures the guest origin; native leave actions still fire once.
 state=3;int before=captures;event("JoinSession_White");assert(captures==before);
 event("OnLeaveMenu_Yes");assert(leaves==1&&ending==1);
 event("UnrelatedGameplayEvent");assert(leaves==1&&ending==1);
 std::cout<<"PASS: capture-off functional dispatch, chalice home return, follow preserved, repeated sessions, missing-origin native-lamp fallback, leave dispatch\n";
}
"""
build=root/'build';build.mkdir(exist_ok=True)
cpp=build/'test_home_return.cpp';exe=build/'test_home_return.exe';cpp.write_text(code,encoding='utf-8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20',str(cpp),'-o',str(exe)],check=True)
env=dict(os.environ);env['PATH']='C:/msys64/clang64/bin;'+env.get('PATH','')
subprocess.run([str(exe)],check=True,env=env)
