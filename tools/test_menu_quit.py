"""Production native System-exit ownership and peer departure on fake memory."""
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
    a=SOURCE.index(signature+' {'); b=SOURCE.index('{',a)+1; depth=1
    while depth:
        depth+=(SOURCE[b]=='{')-(SOURCE[b]=='}'); b+=1
    return SOURCE[a:b]
prefix=r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <map>
#include <mutex>
#include <string_view>
#include <vector>
#include <algorithm>
using u8=uint8_t; using u64=uint64_t; using u32=uint32_t;
using s32=int32_t; using s64=int64_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...)
#define LOG_ERROR(...)
#define BBSC_TIMELINE(...)
#define BBSC_MOD
namespace BbscMod { int cancels=0; void PartyCancel(){++cancels;} }
struct GuestRegisterSnapshot {u64 rax=0,rbx=0,rsi=0;};
namespace MemoryProt {constexpr int CpuWrite=1;}
u64 image_base=0x100000,world=0x200000,menu=0x300000,manager=0x400000;
constexpr u64 MenuManPointerOffset=0x80,MatchingStatePointerOffset=0x88;
std::map<u64,u64> memory;
std::vector<int> events;
s32 session=6; s64 now=1000;
u64 GetGlobalState(){return world;} s32 GetSessionState(){return session;}
s64 SteadyNowMs(){return now;}
template<class T>T ReadValue(u64 p,size_t off){return static_cast<T>(memory[p+off]);}
template<class T>bool WriteValue(u64 p,size_t off,T v){memory[p+off]=v;return true;}
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
bool HasMemoryAccess(u64 p,size_t,int){return p>=0x10000;}
u64 GetLocalPlayerCharacter(){return 0x800000;} int GetCharacterHp(u64){return 100;}
bool returning=false;
bool BbscReturningToTitle(){return returning;}
std::atomic<bool> bbsc_recover_session_cleanup{false};
s64 bbsc_persistence_restore_at_ms=0;
void CancelBbscReinsert(std::string_view){}
void FlushBbscSessionJournals(){events.push_back(1);}
void SuspendBbscPersistence(std::string_view){events.push_back(4);bbsc_persistence_restore_at_ms=now+20000;}
void SendBbscSessionLeave(){events.push_back(3);}
void LogBbscQuitQueue(u64){}
u8 stop_stub(u64 m){assert(m==manager);events.push_back(5);session=7;return 1;}
void cleanup_stub(u64){events.push_back(7);}
u64 MultiPlayStopRequestOffset=reinterpret_cast<u64>(&stop_stub)-image_base;
u64 WorldChrManRemoteCleanupOffset=reinterpret_cast<u64>(&cleanup_stub)-image_base;
enum class BbscWork{PeerLeft}; void QueueBbscWork(BbscWork){}
bool BbscDreamFinaleHolding(){return false;}
std::pair<u32,u32> BbscPeerLifeCounts(){return {0,0};}
int RemotePlayerCount(){return 0;}
void ClearBbscBossContext(std::string_view){}
void ReleaseBbscLeaveLocks(std::string_view){}
void ReleaseBbscDeathLocks(std::string_view){}
'''
a=SOURCE.index('bool bbsc_quit_prepared = false;');b=SOURCE.index('void SendBbscSessionLeave()',a)
state=SOURCE[a:b]
functions='\n'.join(function(sig) for sig in (
 'void SuspendBbscPersistenceOnce(std::string_view why)',
 'void ReleaseBbscNativeLeavingSession()',
 'void CleanupBbscDepartingRemotes()',
 'void ObserveBbscNativeTitleStop()',
 'void PrepareBbscQuitToTitle()',
 'void PS4_SYSV_ABI BbscNativeQuitConfirmHook(u64, const GuestRegisterSnapshot* registers)',
 'void PS4_SYSV_ABI BbscQuitSaveResultHook(u64, const GuestRegisterSnapshot* registers)',
 'void TickBbscSessionExit(bool peer_work)',
))
fixture=r'''
void reset(s32 role=6){
 memory.clear();events.clear();session=role;returning=false;
 bbsc_title_quit={};bbsc_quit_prepared=false;bbsc_quit_defer_store=0;
 bbsc_quit_save_hooks_ready=true;bbsc_recover_session_cleanup=false;
 bbsc_peer_left_pending.clear();bbsc_explicit_host_leave_pending=0;
 bbsc_persistence_restore_at_ms=0;BbscMod::cancels=0;
 memory[image_base+MenuManPointerOffset]=menu;
 memory[image_base+MatchingStatePointerOffset]=manager;
 memory[world+0x1490]=2;memory[world+0x1592]=1;memory[world+0x16F8]=0x900000;
}
void confirm(){GuestRegisterSnapshot r;BbscNativeQuitConfirmHook(0,&r);}
int main(){
 for(s32 role:{0,1,2,3,4,5,6,7}){
  reset(role);memory[world+0x1592]=(role==4||role==6)?0:1;
  memory[menu+0x2DC]=9;memory[world+0x1554]=1;
  confirm();
  assert(bbsc_quit_defer_store==0 && bbsc_title_quit.native_system);
  assert(bbsc_title_quit.session==role && events==std::vector<int>({1,4}));
  // No native save/Stop/menu/latch/input writes from the observer, even with an
  // autosave pending or a peer departure arriving on the same existing tick.
  assert(memory[menu+0x250]==0 && memory[menu+0x25C]==0 && memory[world+0x1554]==1);
  bbsc_peer_left_pending[99]=true;TickBbscSessionExit(true);
  returning=true;PrepareBbscQuitToTitle();
  assert(events==std::vector<int>({1,4}) && BbscMod::cancels==0);
  memory[menu+0x250]=1;memory[menu+0x25C]=1;
  confirm();assert(bbsc_quit_defer_store==1 && memory[menu+0x250]==1 && memory[menu+0x25C]==1);
  ObserveBbscNativeTitleStop();bbsc_quit_prepared=false;ObserveBbscNativeTitleStop();
  assert(events==std::vector<int>({1,4,3}) && BbscMod::cancels==1);
  assert(memory[menu+0x2DC]==9 && memory[world+8]==0);
 }
 // Reproduce P1: the last guest leaves, then the host selects System exit.
 // Neither the departure nor confirmation may issue the old early Stop/home load.
 reset(3);bbsc_peer_left_pending[42]=false;TickBbscSessionExit(true);
 assert(events.empty() && session==3 && bbsc_persistence_restore_at_ms==0);
 confirm();assert(events==std::vector<int>({1,4}) && session==3);
 // A native departure already in progress and former-host solo both keep native Yes.
 for(s32 role:{7,0}){reset(role);confirm();assert(bbsc_quit_defer_store==0);}
 // Host leaving still sends a guest home when that guest did NOT choose title.
 for(s32 role:{4,6}){
  reset(role);bbsc_peer_left_pending[42]=true;bbsc_explicit_host_leave_pending=42;
  TickBbscSessionExit(true);
  assert(events==std::vector<int>({1,4,5,7}) && session==7 && bbsc_confirmed_departure_ms==now);
 }
 for(s32 role:{-1,8}){reset(role);confirm();assert(events.empty() && !BbscQuitInProgress());}
 reset();memory[image_base+MenuManPointerOffset]=0;confirm();assert(events.empty());
 // A failed/unavailable BBSC save observer must not disable native exit observation.
 reset();bbsc_quit_save_hooks_ready=false;confirm();assert(bbsc_title_quit.native_system);
 // Remaining talk/finale save diagnostics retain the native pending/error/success values.
 reset();memory[image_base+BbscNativeSaveManagerOffset]=0x500000;
 GuestRegisterSnapshot r;r.rbx=0x500000;r.rax=1;
 bbsc_talk_save_watch=true;bbsc_talk_save_result=-1;
 BbscQuitSaveResultHook(0,&r);assert(bbsc_talk_save_result==-1);
 r.rax=9;BbscQuitSaveResultHook(0,&r);assert(bbsc_talk_save_result==9);
 r.rax=0;BbscQuitSaveResultHook(0,&r);assert(bbsc_talk_save_result==0);
}
'''
def run(source_functions=functions, expect_failure=False):
 with tempfile.TemporaryDirectory(prefix='bbsc-menu-native-') as temp:
  cpp,exe=Path(temp)/'test.cpp',Path(temp)/'test.exe';cpp.write_text(prefix+state+source_functions+fixture,encoding='utf-8')
  subprocess.run([os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe'),'-std=c++20','-O0',str(cpp),'-o',str(exe)],check=True)
  env=dict(os.environ);env['PATH']='C:/msys64/clang64/bin;'+env.get('PATH','')
  result=subprocess.run([str(exe)],check=False,timeout=10,env=env,capture_output=expect_failure)
  if expect_failure:
   assert result.returncode!=0, 'Old ordering unexpectedly passed the production scenario'
  else:
   result.check_returncode()
if __name__=='__main__':
 run()
 if '--negative-controls' in __import__('sys').argv:
  old_host=functions.replace('if ((state == 4 || state == 6) && host && !BbscQuitInProgress()) {', 'if (((state == 4 || state == 6) && host) || (state == 3 && known == 0 && RemotePlayerCount() <= 1)) {')
  assert old_host!=functions
  run(old_host,expect_failure=True)
  old_guest=functions.replace('if (!registers || state < 0 || state > 7) return;', 'if (!registers || state < 0 || state > 7 || state == 4 || state == 6) return;')
  assert old_guest!=functions
  run(old_guest,expect_failure=True)
  print('PASS: negative controls reject former host forced Stop and guest native-confirmation omission')
 print('PASS: production native System Yes for all roles, one-shot Stop observer, last-guest departure then host exit, simultaneous host leave, native guest-home fallback')
