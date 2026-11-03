"""Run production per-member wipe banner filtering, including concurrent real joins."""
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
start = SOURCE.index('struct BbscRecreatedMember {')
end = SOURCE.index('void PS4_SYSV_ABI BbscBannerMenuHook(', start)
production = SOURCE[start:end].replace('image_base + MemberIdEqualsOffset', 'reinterpret_cast<u64>(&EqualsMember)')
prefix = r'''
#include <algorithm>
#include <vector>
#include <map>
#include <cassert>
#include <cstdint>
#include <iostream>
using u64=uint64_t; using s64=int64_t; using s32=int32_t; using u8=uint8_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...) ((void)0)
std::map<u64,u64> mem;
template<class T>T ReadValue(u64 p, size_t o){return static_cast<T>(mem[p+o]);}
s32 state=3; s64 now=100;
s32 GetSessionState(){return state;}
s64 SteadyNowMs(){return now;}
std::vector<u64> tasks{0x1000,0x2000};
std::vector<u64> GetMultiPlayerInsTasks(){return tasks;}
bool IsValidMemberId(u64 p){return mem[p]!=0;}
bool EqualsMember(u64 a,u64 b){return mem[a]==mem[b];}
constexpr s64 BbscReinsertTimeoutMs=120000;
constexpr u64 BbscHostCaughtUpId=15000012;
struct GuestRegisterSnapshot{u64 r13=0,rsi=0;};
'''
main=r'''
int main(){
 for(s32 role : {3,6}) {
  state=0;PruneBbscRecreatedMembers(); state=role;
  tasks={0x1000,0x2000};mem[0x10c8]=11;mem[0x20c8]=22;
  mem[0x10ed]=mem[0x20ed]=0;
  MarkBbscRecreatedMember(0x1000);MarkBbscRecreatedMember(0x2000);
  mem[0x30d8]=33; GuestRegisterSnapshot r{0x3000,102001};
  BbscMemberArrivalLineHook(0,&r);assert(r.rsi==102001); // genuine concurrent join
  mem[0x40d8]=11;r={0x4000,102001};BbscMemberArrivalLineHook(0,&r);
  assert(r.rsi==BbscHostCaughtUpId && bbsc_recreated_members.size()==1);
  r.rsi=102001;BbscMemberArrivalLineHook(0,&r);assert(r.rsi==102001); // one shot
  mem[0x40d8]=22;r.rsi=102001;BbscMemberArrivalLineHook(0,&r);
  assert(r.rsi==BbscHostCaughtUpId && bbsc_recreated_members.empty());
  // A second wipe gets independent one-shot records.
  MarkBbscRecreatedMember(0x2000);r.rsi=102001;BbscMemberArrivalLineHook(0,&r);
  assert(r.rsi==BbscHostCaughtUpId);
  // Reused task address belongs to a new member: keep the real join.
  MarkBbscRecreatedMember(0x1000);mem[0x10c8]=44;mem[0x40d8]=44;
  r.rsi=102001;BbscMemberArrivalLineHook(0,&r);assert(r.rsi==102001);
  // Leaving, removed task, timeout and session reset revoke stale records.
  MarkBbscRecreatedMember(0x1000);mem[0x10ed]=2;PruneBbscRecreatedMembers();
  mem[0x10ed]=0;assert(!ConsumeBbscRecreatedArrival(0x40d8));
  MarkBbscRecreatedMember(0x1000);tasks.erase(tasks.begin());PruneBbscRecreatedMembers();
  tasks.insert(tasks.begin(),0x1000);assert(!ConsumeBbscRecreatedArrival(0x40d8));
  MarkBbscRecreatedMember(0x1000);now+=120000;assert(!ConsumeBbscRecreatedArrival(0x40d8));
  MarkBbscRecreatedMember(0x1000);state=7;PruneBbscRecreatedMembers();state=role;
  assert(!ConsumeBbscRecreatedArrival(0x40d8));
  MarkBbscRecreatedMember(0x1000);mem[0x40d8]=0;
  assert(!ConsumeBbscRecreatedArrival(0x40d8));BbscMemberArrivalLineHook(0,nullptr);
 }
 std::cout << "wipe arrivals: host/guest, concurrent real join, repeated wipe, lifecycle: PASS\n";
}
'''
# The real restart marks only tasks it actually restarts, before native SetState.
a=SOURCE.index('void TickBbscReinsertV8() {');b=SOURCE.index('// Self-heal',a)
assert SOURCE[a:b].index('MarkBbscRecreatedMember(task);') < SOURCE[a:b].index('set_state(task, 4);')
assert 'ArmBbscRejoinLines(GetSessionState() == 6' not in SOURCE[a:b]
assert 'if (GetSessionState() == 6) ArmBbscRejoinLines(true' in SOURCE[a:b]
assert '0x0196BCEF' in SOURCE and '0x48, 0x8D, 0xBD, 0x10, 0xFF, 0xFF, 0xFF' in SOURCE
with tempfile.TemporaryDirectory(prefix='bbsc-wipe-banner-') as tmp:
 cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe'
 cpp.write_text(prefix+production+main,encoding='utf-8')
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
