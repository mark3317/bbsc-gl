"""Exercise the real provider with a deterministic clock and no running game."""
from pathlib import Path
import os
import re
import subprocess

root = Path(__file__).resolve().parents[1]
source = (root / 'emulator/mod/bbsc_register.cpp').read_text(encoding='utf8')
header = (root / 'emulator/mod/bbsc_register.h').read_text(encoding='utf8')
header = re.sub(r'^#(?:include|pragma once).*$', '', header, flags=re.M)
source = re.sub(r'^#include.*$', '', source, flags=re.M)
fixture = r'''
#include <algorithm>
#include <array>
#include <atomic>
#include <cstring>
#include <cstdlib>
#include <map>
#include <mutex>
#include <vector>
#include <set>
#include <tuple>
#include <span>
#include <cstdint>
#include <cassert>
using u16=uint16_t;using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_INFO(...)
#define LOG_ERROR(...)
u64 clock_ms=10000;u32 test_session=42,test_own=1;
int grants=0;bool can_give=true;std::vector<std::vector<u8>> sent;
u64 GetTickCount64(){return clock_ms;}
namespace Core {
struct GuestRegisterSnapshot { u64 rsi; };
using GuestCodeHook=void PS4_SYSV_ABI (*)(u64,const GuestRegisterSnapshot*);
bool InstallGuestCodeHook(void*,std::span<const u8>,u64,GuestCodeHook){return true;}
}
namespace BbscMod {
u64 EbootAddress(){return 0;}
bool ReadSlotSafely(u64,u64*){return false;}
bool WriteSlotSafely(u64,u64){return false;}
void GuardSlot(u64,u64,void**,const char*){}
u32 RegisterSessionKey(){return test_session;}
u32 RegisterOwnId(){return test_own;}
u32 SendRegisterPacket(const void* p,u32 n){sent.emplace_back((const u8*)p,(const u8*)p+n);return 0;}
}
''' + header + r'''
namespace Core::Bloodborne {
bool GiveSessionBloodDreg(){if(!can_give)return false;++grants;return true;}
void InstallSessionDregHooks(){}
}
''' + source + r'''
int main(){using namespace BbscMod;
 RegisterIdentity me;strcpy(me.name,"SameName");me.room=42;me.member=1;
 TickSessionRegister(0,true,me);ready=true;
 Core::GuestRegisterSnapshot r{130};BookUse(0,&r);
 Packet p;strcpy(p.identity.name,"SameName");p.identity.room=42;p.identity.member=2;p.offered=10;
 ReceiveSessionRegister(2,999,&p,sizeof p);assert(Snapshot().size()==1);
 for(u32 id=2;id<=5;++id){p.identity.member=id;p.offered=id==3?0:id;ReceiveSessionRegister(id,42,&p,sizeof p);}
 assert(Snapshot().size()==5); // includes zero-offering hunters
 ReceiveSessionRegister(5,42,&p,sizeof p);assert(Snapshot().size()==5);
 p.identity.member=6;ReceiveSessionRegister(6,42,&p,sizeof p);assert(Snapshot().size()==5);
 Rank rows[100];u64 date;u32 total;
 assert(Range(1,20,1,rows,sizeof rows,nullptr,0,nullptr,0,100,&date,&total,nullptr)==5);
 assert(total==5 && rows[0].score==5 && rows[0].rank==1 && rows[4].score==0 && rows[4].serial==5);
 assert(!rows[0].has_data);
 // Actual consumer at CCEC80 adds the result to its cursor, independent of totalRecord.
 // A successful zero would spin forever, as the first installed prototype did.
 int calls=0;u32 cursor=0;
 while(cursor<100){assert(++calls<=2);auto n=Range(1,20,cursor+1,rows,sizeof rows,nullptr,0,nullptr,0,100,&date,&total,nullptr);if(n==NoRanking)break;assert(n>0);cursor+=n;}
 assert(calls==2 && cursor==5);
 assert(Range(1,20,0,rows,sizeof rows,nullptr,0,nullptr,0,100,&date,&total,nullptr)==Invalid);
 IdPc ids[2]{};strcpy(ids[0].id.name,"SameName");strcpy(ids[1].id.name,"Absent");PlayerRank results[2];
 assert(ById(1,20,ids,sizeof ids,results,sizeof results,nullptr,0,nullptr,0,2,&date,&total,nullptr)==1);
 assert(results[0].has_data && !results[1].has_data);
 assert(!Ours(10) && Ours(20));u32 tmp=999;
 assert(Record(1,20,999,nullptr,nullptr,&tmp,nullptr,nullptr)==0 && tmp==0);
 assert(RecordData(1,20,0,0,0,nullptr,nullptr)==0);
 assert(GetData(1,20,nullptr,&date,0,nullptr,nullptr)==NoRanking);
 // A final-hit certificate names exactly one room member, even with five identical names.
 KillPacket kill;kill.victim=2;kill.death=1;kill.killer=me;
 ReceiveRegisterKill(2,777,&kill,sizeof kill);assert(pending_kills.empty());
 kill.killer.member=3;ReceiveRegisterKill(2,42,&kill,sizeof kill);assert(pending_kills.empty());
 kill.killer=me;kill.victim=4;ReceiveRegisterKill(2,42,&kill,sizeof kill);assert(pending_kills.empty());
 kill.victim=2;ReceiveRegisterKill(2,42,&kill,sizeof kill);ReceiveRegisterKill(2,42,&kill,sizeof kill);
 assert(pending_kills.size()==1);can_give=false;ServiceKills(true,clock_ms);assert(grants==0);
 can_give=true;ServiceKills(true,clock_ms);assert(grants==1 && pending_kills.empty());
 ReceiveRegisterKill(2,42,&kill,sizeof kill);ServiceKills(true,clock_ms);assert(grants==1);
 ++kill.death;ReceiveRegisterKill(2,42,&kill,sizeof kill);ServiceKills(true,clock_ms);assert(grants==2);
 // Every one of the four other players can be the killer; identities do not collapse by name.
 for(u32 id=2;id<=5;++id){auto target=me;target.member=id;QueueRegisterKill(target);}
 assert(outgoing_kills.size()==4);
 auto outgoing=outgoing_kills.begin()->second.packet;
 assert(outgoing.victim==1 && outgoing.kind==0 && outgoing.killer.member==2);
 const auto before=sent.size();ServiceKills(false,clock_ms);ServiceKills(false,clock_ms+1001);assert(sent.size()==before+8);
 outgoing.kind=1;ReceiveRegisterKill(3,42,&outgoing,sizeof outgoing);assert(outgoing_kills.size()==4);
 ReceiveRegisterKill(2,42,&outgoing,sizeof outgoing);assert(outgoing_kills.size()==3);
 const auto after=sent.size();ServiceKills(false,clock_ms+60000);assert(sent.size()==after+3); // long loads do not discard claims
 clock_ms+=15001;assert(Snapshot().size()==1);
 clock_ms+=1001;TickSessionRegister(0,true,me);assert(members.empty());
 p.identity.member=6;ReceiveSessionRegister(6,42,&p,sizeof p);assert(Snapshot().size()==2); // stale roster entries cannot block a replacement
 ForgetSessionRegister(6);assert(Snapshot().size()==1);
 test_session=77;clock_ms+=1001;TickSessionRegister(20,true,me);
 assert(members.empty() && pending_kills.empty() && outgoing_kills.empty());
 test_session=0;clock_ms+=1001;TickSessionRegister(0,false,me);assert(Snapshot().empty());
 assert(Range(1,20,1,rows,sizeof rows,nullptr,0,nullptr,0,100,&date,&total,nullptr)==NoRanking);
}

'''
build = root / 'build'
build.mkdir(exist_ok=True)
cpp = build / 'test_session_register.cpp'
exe = cpp.with_suffix('.exe')
cpp.write_text(fixture, encoding='utf8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe', '-std=c++20', str(cpp), '-o', str(exe)], check=True)
env = dict(os.environ)
env['PATH'] = 'C:/msys64/clang64/bin;' + env.get('PATH', '')
subprocess.run([str(exe)], env=env, check=True)
print('PASS: real provider: zero offerings, five members, native EOF termination, no remote I/O, last-hit targeting, replay dedup, inventory retry, ACK validation, session reset')
