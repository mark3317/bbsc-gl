"""Execute the production deferred item gate + mailbox, including late HTTP answers."""
from pathlib import Path
import os, subprocess, tempfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = r'''
#include <cassert>
#include <chrono>
#include <cstdint>
#include <future>
#include <mutex>
#include <thread>
#include "bbsc_party_acquire.h"
using u64=std::uint64_t;using u32=std::uint32_t;using s32=std::int32_t;using u8=std::uint8_t;
#define BBSC_TIMELINE(...)
#define BBSC_MOD
#define PS4_SYSV_ABI
struct GuestRegisterSnapshot {u64 rdi=17,rsi=200,rdx=17;};
using Box=BbscMod::PartyAcquireMailbox;
Box mailbox;int cancellations=0,rings=0;
bool responder=false,erase_ok=true;
u64 BbscLocalEffectNode(int id){return id==9005&&responder;}
bool BbscEraseLocalEffect(int id){assert(id==9005);if(!erase_ok)return false;responder=false;return true;}
namespace BbscMod {
std::uint64_t PartyRequestAcquire(){return mailbox.Request();}
Box::Result PartyAcquireResult(std::uint64_t t){return mailbox.Poll(t);}
void PartyFinishAcquire(std::uint64_t t){mailbox.Finish(t);}
void PartyBellRang(){++rings;}
void PartyCancel(){++cancellations;mailbox.Cancel();}
}
u64 player=17,global=32;u32 map=0x17000000;s32 state=0,hp=10;bool loading=false,title=false,quit=false;
std::atomic<u32> bbsc_load_generation{0};std::atomic<bool> bbsc_reload_finish_pending{false};
u64 GetLocalPlayerCharacter(){return player;}u64 GetGlobalState(){return global;}
u32 GetCurrentPackedMap(){return map;}s32 GetSessionState(){return state;}
bool BbscReturningToTitle(){return title;}bool BbscQuitInProgress(){return quit;}
bool ReadablePointer(u64 p,std::size_t){return p==global && p!=0;}
template<class T>T ReadValue(u64,std::size_t){return T(loading);}
s32 GetCharacterHp(u64){return hp;}
bool NativeApply(u64,s32,s32);
u64 image_base=reinterpret_cast<u64>(&NativeApply);constexpr u64 UseItemNativeApplyOffset=0;
'''
MAIN = r'''
int applied=0;bool native_ok=true;
bool NativeApply(u64 p,s32 goods,s32 argument){
 assert(p==player && goods==200 && argument==17);
 assert(!responder); // the old Small Bell must stop before native Beckoning
 GuestRegisterSnapshot regs{p,200,17};
 assert(GateBbscPartyItem(regs)); // NativeApply + nested GoodsExecutor use one grant
 assert(GateBbscPartyItem(regs));
 ++applied;return native_ok;
}
void request(){GuestRegisterSnapshot r;assert(!GateBbscPartyItem(r));assert(bbsc_pending_party_item.ticket);}
void grant(){auto t=mailbox.Take();assert(t);assert(mailbox.Complete(t,true));}
int main(){
 responder=true;request();auto first=bbsc_pending_party_item.ticket;
 for(int i=0;i<10000;++i){GuestRegisterSnapshot r;assert(!GateBbscPartyItem(r));TickBbscPartyItem();}
 assert(applied==0 && responder && bbsc_pending_party_item.ticket==first);
 grant();erase_ok=false;TickBbscPartyItem();assert(applied==0&&responder);
 erase_ok=true;TickBbscPartyItem();assert(applied==1 && !responder && !bbsc_pending_party_item.ticket);
 TickBbscPartyItem();assert(applied==1);assert(mailbox.Poll(first)==Box::Idle);
 request();auto denied=mailbox.Take();assert(mailbox.Complete(denied,false));
 TickBbscPartyItem();assert(applied==1 && !bbsc_pending_party_item.ticket);
 // Late reply after cancellation must never authorize a later request.
 request();auto old=mailbox.Take();BbscMod::PartyCancel();TickBbscPartyItem();
 request();auto current=bbsc_pending_party_item.ticket;assert(current!=old);
 assert(!mailbox.Complete(old,true));TickBbscPartyItem();assert(applied==1);
 grant();TickBbscPartyItem();assert(applied==2);
 // Every native lifetime fence cancels before use.
 for(int which=0;which<11;++which){
  request();grant();
  switch(which){case 0:++player;break;case 1:++map;break;case 2:++global;break;
   case 3:loading=true;break;case 4:hp=0;break;case 5:title=true;break;
   case 6:quit=true;break;case 7:state=6;break;
   case 8:bbsc_pending_party_item.started-=std::chrono::seconds(13);break;
   case 9:++bbsc_load_generation;break;case 10:bbsc_reload_finish_pending=true;break;}
  TickBbscPartyItem();assert(applied==2 && !bbsc_pending_party_item.ticket);
  player=17;map=0x17000000;global=32;loading=title=quit=false;hp=10;state=0;bbsc_reload_finish_pending=false;
 }
 request();grant();native_ok=false;int before=cancellations;TickBbscPartyItem();
 assert(applied==3 && rings==2 && cancellations==before+1 && !bbsc_pending_party_item.ticket);
 native_ok=true;
 // Pending network work cannot block thousands of frame callbacks.
 request();auto blocked=mailbox.Take();std::promise<void> release;
 auto ready=release.get_future();auto worker=std::async(std::launch::async,[&]{ready.wait();return mailbox.Complete(blocked,true);});
 for(int i=0;i<10000;++i)TickBbscPartyItem();
 assert(applied==3);BbscMod::PartyCancel();TickBbscPartyItem();
 release.set_value();assert(!worker.get());assert(applied==3);
 // Simultaneous native callbacks share the pending action without a blocking
 // cross-thread lock. The replay's nested entry is covered by NativeApply above.
 auto press=[]{for(int i=0;i<1000;++i){GuestRegisterSnapshot r;assert(!GateBbscPartyItem(r));}};
 auto p1=std::async(std::launch::async,press),p2=std::async(std::launch::async,press);
 p1.get();p2.get();assert(bbsc_pending_party_item.ticket);
 grant();TickBbscPartyItem();assert(applied==4 && rings==3);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-async-item-') as tmp:
    source, binary = Path(tmp)/'test.cpp', Path(tmp)/'test.exe'
    source.write_text(PREFIX + '\n#include "bbsc_party_item.inc"\n' + MAIN, encoding='utf-8')
    subprocess.run([os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe'),'-std=c++20',
                    '-I',str(ROOT/'emulator/mod'),'-I',str(ROOT/'emulator/src/core'),
                    str(source),'-o',str(binary)],check=True)
    env = dict(os.environ, PATH='C:/msys64/clang64/bin;' + os.environ.get('PATH',''))
    subprocess.run([str(binary)],check=True,timeout=10,env=env)
print('PASS: deferred native action, single grant, cancel/late reply, lifetime fences, blocked worker')
