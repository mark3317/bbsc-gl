"""Exercise the production binding/watchdog logic without a DLL or game build."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')


def function(signature):
    start = SOURCE.index(signature + ' {')
    opening = SOURCE.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (SOURCE[end] == '{') - (SOURCE[end] == '}')
        end += 1
    return SOURCE[start:end] + '\n'


prefix = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <map>
#include <vector>
#include <iostream>
#include <string_view>
using u64=uint64_t; using u8=uint8_t; using s64=int64_t; using s32=int32_t;
#define PS4_SYSV_ABI
#define LOG_WARNING(...) ((void)0)
#define LOG_INFO(...) ((void)0)
#define BBSC_TIMELINE(...) ((void)0)
bool BbscResearchEnabled(){return false;}
bool BbscIndependentActive(){return false;}
bool BbscWorldTaskHere(u64){return true;}
constexpr u64 image_base=1, CandidateLocalStatePointerOffset=0x553e878;
constexpr u64 MatchingStatePointerOffset=0x5540290;
std::map<u64,u64> mem;
int reads=0;
template<class T> T ReadValue(u64 a,size_t o){++reads;return static_cast<T>(mem[a+o]);}
template<class T> bool WriteValue(u64 a,size_t o,T v){mem[a+o]=v;return true;}
bool ReadablePointer(u64 a,size_t){return a>=0x10000;}
bool IsValidMemberId(u64 a){return mem[a+8]!=0;}
enum class MemoryProt { CpuWrite };
bool HasMemoryAccess(u64,size_t,MemoryProt){return true;}
int binds=0,restarts=0;
bool TestEquals(u64 a,u64 b){return mem[a]==mem[b];}
u64 child_member=0;
void TestBind(u64 a,u64 b){++binds;mem[a+0x3d8]=mem[b];child_member=mem[b];}
bool check_bind_order=false;
void TestSetState(u64 t,s32 s){if(check_bind_order)assert(child_member==789);++restarts;mem[t+0x54]=s;}
s64 now=10000;
bool quit=false, bbsc_v8_pending=false;
bool BbscQuitInProgress(){return quit;}
s64 SteadyNowMs(){return now;}
u64 GetGlobalState(){return 0x90000;}
s32 GetSessionState(){return ReadValue<s32>(ReadValue<u64>(image_base+MatchingStatePointerOffset,0),0x124);}
s32 hp=100;
s32 GetBbscLocalPlayerHp(){return hp;}
std::vector<u64> tasks{0x30000,0x40000};
std::vector<u64> GetMultiPlayerInsTasks(){return tasks;}
bool remote_exists=true;
bool RemotePlayerExists(u64){return remote_exists;}
constexpr s64 BbscSelfHealMissingMs=4000;
void LogBbscSessionShape(const char*,bool=false){}
s32 bbsc_v8_session_state=3, bbsc_v8_saved_type=-1, bbsc_v8_original_type=0;
s64 bbsc_v8_death_ms=0, bbsc_v8_ready_since_ms=0;
bool bbsc_v8_original_swapped=false;
constexpr s64 BbscReinsertTimeoutMs=120000;
constexpr u64 PlayerSlotManagerPointerOffset=0x553b130;
void CancelBbscReinsert(std::string_view){bbsc_v8_pending=false;}
s32 GetLocalPlayerType(){return 0;}
s32 GetLocalCharacterType(){return 0;}
bool EnvFlagEnabled(const char*){return false;}
void ApplyPhantomCharacterFlags(u64){}
void ArmBbscRejoinLines(bool,uint32_t,s64){}
void TickBbscRejoinLines(){}
void MarkBbscRecreatedMember(u64){}
uint32_t GetCurrentPackedMap(){return 0x18010000;}
bool SetOwnWorldRestoreType(s32,s32*){return true;}
'''

binding = function('bool RepairBbscLocalMemberBinding(s32 session_state, const std::vector<u64>& tasks,\n                                  bool rebuilt = false)')
binding = binding.replace('image_base + MemberIdEqualsOffset', 'reinterpret_cast<u64>(&TestEquals)')
binding = binding.replace('image_base + 0x018F27C0', 'reinterpret_cast<u64>(&TestBind)')
heal = function('void TickBbscSelfHeal()').replace(
    'image_base + MultiPlayerInsSetStateOffset', 'reinterpret_cast<u64>(&TestSetState)')
reinsert = function('void TickBbscReinsertV8()').replace(
    'image_base + MultiPlayerInsSetStateOffset', 'reinterpret_cast<u64>(&TestSetState)')
main = r'''
int main(){
 const u64 w=0x10000,p=0x20000,t=tasks[0],r=tasks[1],child=0x50000,vt=0x60000;
 mem[image_base+CandidateLocalStatePointerOffset]=w;mem[w+0x60]=p;
 mem[p+0x3d8+8]=1;mem[p+0x60]=child;mem[child]=vt;mem[vt+0xd0]=1;
 mem[t+0xc8]=123;mem[t+0xd0]=1;mem[t+0xe8]=0;mem[t+0x50]=6;mem[t+0x54]=6;
 mem[r+0xc8]=456;mem[r+0xd0]=1;mem[r+0xe8]=2;mem[r+0x50]=6;mem[r+0x54]=6;
 mem[image_base+MatchingStatePointerOffset]=0x70000;mem[0x70000+0x124]=6;
 TickBbscSelfHeal();assert(binds==1 && mem[p+0x3d8]==123);
 for(int i=0;i<10000;++i){now+=1000;TickBbscSelfHeal();}
 assert(binds==1 && restarts==0); // healthy session never rebinds or reinserts
 mem[p+0x3d8]=999;now+=1000;TickBbscSelfHeal();assert(binds==2);
 mem[p+0x3d8]=0;mem[0x90000+8]=1;now+=1000;TickBbscSelfHeal();assert(binds==2);
 mem[0x90000+8]=0;hp=0;now+=1000;TickBbscSelfHeal();assert(binds==2);
 hp=100;bbsc_v8_pending=true;now+=1000;TickBbscSelfHeal();assert(binds==2);
 bbsc_v8_pending=false;mem[t+0xed]=2;now+=1000;TickBbscSelfHeal();assert(binds==2);
 mem[t+0xed]=0;mem[t+0x54]=8;now+=1000;TickBbscSelfHeal();assert(binds==2);
 mem[t+0x54]=6;now+=1000;TickBbscSelfHeal();assert(binds==3);
 // A replaced actor gets its own binding, regardless of the old actor's type/id.
 mem[w+0x60]=p+0x1000;mem[p+0x1000+0x3e0]=1;mem[p+0x1000+0x60]=child;
 now+=1000;TickBbscSelfHeal();assert(binds==4);
 // Host uses its self-host member, never a guest task.
 mem[t+0xe8]=3;mem[t+0xc8]=789;mem[0x70000+0x124]=3;
 now+=1000;TickBbscSelfHeal();assert(binds==5 && mem[p+0x1000+0x3d8]==789);
 mem[p+0x1000+0x3d8]=0;mem[0x70000+0x124]=7;
 now+=1000;TickBbscSelfHeal();assert(binds==5);
 // Pending create/leave resets the missing timer; no immediate duplicate create.
 mem[0x70000+0x124]=3;remote_exists=false;now+=1000;TickBbscSelfHeal();
 now+=3000;mem[r+0x54]=4;TickBbscSelfHeal();
 now+=1000;mem[r+0x54]=6;TickBbscSelfHeal();assert(restarts==0);
 now+=4000;TickBbscSelfHeal();assert(restarts==1);
 now+=1000;TickBbscSelfHeal();assert(restarts==1);
 // Queue observer does no memory scan while idle, and throttles active scans.
 mem[0x70000+0x124]=0;now+=2000;int before=reads;TickBbscSendBacklog();
 assert(reads-before==2);
 before=reads;for(int i=0;i<10000;++i)TickBbscSendBacklog();assert(reads==before);
 // Kept reload: an equal PlayerIns id with an unbound rebuilt child MUST
 // invoke the native setter before remote insert tasks are allowed to run.
 mem[0x70000+0x124]=3;mem[t+0xe8]=3;mem[t+0xc8]=789;
 mem[p+0x1000+0x3d8]=789;mem[r+0x54]=6;child_member=0;
 bbsc_v8_pending=true;bbsc_v8_death_ms=now;check_bind_order=true;
 int old_binds=binds,old_restarts=restarts;
 TickBbscReinsertV8();assert(!bbsc_v8_pending && binds==old_binds+1);
 assert(child_member==789 && restarts==old_restarts+1);
 TickBbscReinsertV8();assert(binds==old_binds+1 && restarts==old_restarts+1);
 // Reused actor address in a second generation still requires rebinding.
 mem[r+0x54]=6;child_member=0;bbsc_v8_pending=true;bbsc_v8_death_ms=now;
 TickBbscReinsertV8();assert(child_member==789 && binds==old_binds+2);
 // A self task still creating must defer the ENTIRE remote restart, then
 // recover exactly once when native construction completes.
 mem[t+0x54]=4;mem[r+0x54]=6;child_member=0;
 bbsc_v8_pending=true;bbsc_v8_death_ms=now;old_restarts=restarts;
 TickBbscReinsertV8();assert(bbsc_v8_pending && restarts==old_restarts);
 mem[t+0x54]=6;TickBbscReinsertV8();assert(!bbsc_v8_pending && child_member==789);
 assert(restarts==old_restarts+1);
 // Session loss cancels a waiting recovery rather than binding departed members.
 bbsc_v8_pending=true;mem[0x70000+0x124]=7;old_binds=binds;
 TickBbscReinsertV8();assert(!bbsc_v8_pending && binds==old_binds);
 // Guest recovery uses the self-guest member, never the remote host's id.
 mem[0x70000+0x124]=6;bbsc_v8_session_state=6;mem[t+0xe8]=0;
 mem[r+0xe8]=2;mem[r+0x54]=6;child_member=0;
 bbsc_v8_pending=true;bbsc_v8_death_ms=now;
 TickBbscReinsertV8();assert(!bbsc_v8_pending && child_member==789);
 assert(binds==old_binds+1);
 mem[0x70000+0x124]=6;mem[image_base+0x05540290]=0x70000;
 mem[0x70000+0x188]=0xa0000;mem[0xa0000]=0xa0000;mem[0x70000+0x1b0]=200;
 now+=2000;before=reads;TickBbscSendBacklog();assert(reads>before);
 before=reads;for(int i=0;i<10000;++i)TickBbscSendBacklog();assert(reads==before);
 std::cout << "member binding and continuous missing interval: PASS\n";
}
'''

# No production patch may replace the native reliable-send queue bound.
patches = (ROOT / 'emulator/src/core/bbsc_patch_tables.h').read_text(encoding='utf-8')
assert '"SendBacklog.Limit"' not in patches
backlog = function('void TickBbscSendBacklog()')
assert 'now - last_ms < 2\'000' in backlog
assert 'state != 3 && state != 6' in backlog
assert 'if (!BbscResearchEnabled())' not in backlog
assert 'if (BbscResearchEnabled()) { BBSC_PERF_NESTED("tick TickBbscSendBacklog")' not in SOURCE
with tempfile.TemporaryDirectory(prefix='bbsc-member-test-') as tmp:
    cpp, exe = Path(tmp) / 'test.cpp', Path(tmp) / 'test.exe'
    cpp.write_text('#include "core/bbsc_patch_tables.h"\n#include "core/bbsc_native_sync_test.h"\n' + prefix + binding + heal + reinsert + backlog + main, encoding='utf-8')
    subprocess.run([os.environ.get('CXX', 'g++'), '-std=c++20', '-O2', '-I', str(ROOT / 'emulator/src'), str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
