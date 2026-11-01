"""Exercise the real provider with a deterministic clock and no running game."""
from pathlib import Path
import os
import re
import subprocess

root = Path(__file__).resolve().parents[1]
source = (root / 'emulator/mod/bbsc_register.cpp').read_text(encoding='utf8')
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
#include <span>
#include <cstdint>
#include <cassert>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_INFO(...)
#define LOG_ERROR(...)
u64 clock_ms=10000;u32 test_session=42;
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
u32 SendRegisterPacket(const void*,u32){return 0;}
}
''' + source + r'''
int main(){using namespace BbscMod;
 _putenv_s("BB_SHADNET_NPID","Host");
 TickSessionRegister(80,true);ready=true;
 Core::GuestRegisterSnapshot r{130};BookUse(0,&r);
 Packet p;strcpy(p.name,"Guest");p.level=100;
 ReceiveSessionRegister(7,999,&p,sizeof p);assert(Snapshot().size()==1);
 ReceiveSessionRegister(7,42,&p,sizeof p);assert(Snapshot().size()==2);
 ReceiveSessionRegister(7,42,&p,sizeof p);assert(Snapshot().size()==2);
 p.level=999;ReceiveSessionRegister(8,42,&p,sizeof p);assert(Snapshot().size()==2);
 Rank rows[3];u64 date;u32 total;
 assert(Range(1,10,1,rows,sizeof rows,nullptr,0,nullptr,0,3,&date,&total,nullptr)==2);
 assert(total==2 && rows[0].score==100 && rows[0].rank==1 && rows[1].score==80 && rows[2].rank==0);
 assert(!rows[0].has_data); // no fabricated character/equipment blob
 assert(Range(1,10,3,rows,sizeof rows,nullptr,0,nullptr,0,3,&date,&total,nullptr)==0);
 assert(Range(1,10,0,rows,sizeof rows,nullptr,0,nullptr,0,3,&date,&total,nullptr)==Invalid);
 IdPc ids[2]{};strcpy(ids[0].id.name,"Host");strcpy(ids[1].id.name,"Absent");
 PlayerRank results[2];
 assert(ById(1,10,ids,sizeof ids,results,sizeof results,nullptr,0,nullptr,0,2,&date,&total,nullptr)==1);
 assert(results[0].has_data && results[0].value.rank==2 && !results[1].has_data);
 clock_ms+=5001;assert(Snapshot().size()==1);
 p.level=100;ReceiveSessionRegister(7,42,&p,sizeof p);ForgetSessionRegister(7);assert(Snapshot().size()==1);
 ReceiveSessionRegister(7,42,&p,sizeof p);test_session=77;assert(Snapshot().size()==1);
 TickSessionRegister(80,true);assert(members.empty());
 test_session=0;clock_ms+=1001;TickSessionRegister(80,false);assert(Snapshot().empty());
 assert(!Ours(11));clock_ms+=600001;assert(!Ours(10));
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
print('PASS: real provider ABI, paging, self lookup, order, stale/foreign/invalid peers, departure/session reset, board scoping')
