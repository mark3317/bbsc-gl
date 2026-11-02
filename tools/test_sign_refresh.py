"""Exercise the native own-sign dirty queue, not a second HTTP claim consumer."""
from pathlib import Path
import os
import subprocess

root = Path(__file__).resolve().parents[1]
source = (root / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')

def function(name):
    start = source.index(name)
    begin = source.index('{', start)
    depth, end = 1, begin + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

fixture = r'''
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>
using u64=uint64_t;using u32=uint32_t;using u8=uint8_t;using s64=int64_t;
enum class MemoryProt { CpuWrite };
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
std::vector<u8> memory(8192);
u64 base=(u64)memory.data(),broker=base,head=base+512,n1=base+600,n2=base+640;
u64 e1=base+800,e2=base+1100;
bool ReadablePointer(u64 p,size_t n){return p>=base&&p<=base+memory.size()&&n<=base+memory.size()-p;}
bool HasMemoryAccess(u64 p,size_t n,MemoryProt){return ReadablePointer(p,n);}
template<class T>T ReadValue(u64 p,size_t o){assert(ReadablePointer(p+o,sizeof(T)));T v;std::memcpy(&v,(void*)(p+o),sizeof(v));return v;}
template<class T>bool WriteValue(u64 p,size_t o,T v){assert(ReadablePointer(p+o,sizeof(T)));std::memcpy((void*)(p+o),&v,sizeof(v));return true;}
s64 now=1000;int state=0;bool foreign=false,bell=true;
s64 SteadyNowMs(){return now;}int GetSessionState(){return state;}
bool BbscInAnotherWorld(){return foreign;}u64 BbscLocalEffectNode(int id){return bell&&id==9005;}
u64 GetSummonManager(){return broker;}
u64 GetGlobalState(){return base+1500;}
std::atomic<s64> bbsc_native_sign_sent_ms{0};
std::atomic<u32> bbsc_native_sign_pending{0};
std::atomic<bool> bbsc_native_sign_claim_pending{false};
'''
for name in ['u32 QueueBbscNativeSignRefresh(', 'void TickBbscNativeSignPolling()',
             'void BeginBbscNativeSignRequest()', 'void EndBbscNativeSignRequest()',
             'void SetBbscNativeSignClaimPending(bool pending)']:
    fixture += function(name) + '\n'
fixture += r'''
void setup(){
 std::fill(memory.begin(),memory.end(),0x5a);
 WriteValue<u8>(GetGlobalState(),8,0);WriteValue<u8>(GetGlobalState(),0x1592,1);
 WriteValue<u64>(broker,0x158,head);WriteValue<u64>(head,0,n1);
 WriteValue<u64>(n1,0,n2);WriteValue<u64>(n1,0x10,e1);
 WriteValue<u64>(n2,0,head);WriteValue<u64>(n2,0x10,e2);
 WriteValue<u8>(e1,0xa0,0);WriteValue<u8>(e2,0xa0,0);
}
void dirty(bool expected){assert(ReadValue<u8>(e1,0xa0)==expected&&ReadValue<u8>(e2,0xa0)==expected);}
int main(){
 setup();auto before=memory;
 // No private-server create, therefore no work (offline/public unaffected).
 now=10000;TickBbscNativeSignPolling();dirty(false);
 now=1000;BeginBbscNativeSignRequest();now=3000;TickBbscNativeSignPolling();dirty(false);
 EndBbscNativeSignRequest();now=2999;TickBbscNativeSignPolling();dirty(false);
 now=3000;TickBbscNativeSignPolling();dirty(true);
 // Exactly the native dirty bytes change; lifetime, payload and counters survive.
 before[e1-base+0xa0]=1;before[e2-base+0xa0]=1;assert(memory==before);
 WriteValue<u8>(e1,0xa0,0);WriteValue<u8>(e2,0xa0,0);
 now=4999;TickBbscNativeSignPolling();dirty(false);
 now=5000;TickBbscNativeSignPolling();dirty(true);
 // Requests in flight remain serialized, including overlapping native requests.
 setup();BeginBbscNativeSignRequest();BeginBbscNativeSignRequest();
 now+=2000;EndBbscNativeSignRequest();TickBbscNativeSignPolling();dirty(false);
 EndBbscNativeSignRequest();now+=250;TickBbscNativeSignPolling();dirty(true);
 EndBbscNativeSignRequest();assert(bbsc_native_sign_pending==0);
 for(int s:{1,2,3,4,5,6,7}){setup();state=s;now+=2000;TickBbscNativeSignPolling();dirty(false);}
 state=0;setup();bell=false;now+=2000;TickBbscNativeSignPolling();dirty(false);
 bell=true;foreign=true;TickBbscNativeSignPolling();dirty(false);foreign=false;
 setup();SetBbscNativeSignClaimPending(true);now+=2000;TickBbscNativeSignPolling();dirty(false);
 SetBbscNativeSignClaimPending(false);now+=250;TickBbscNativeSignPolling();dirty(true);
 setup();WriteValue<u8>(GetGlobalState(),8,1);now+=2000;TickBbscNativeSignPolling();dirty(false);
 setup();WriteValue<u8>(GetGlobalState(),0x1592,0);now+=2000;TickBbscNativeSignPolling();dirty(false);
 // Validate the whole bounded list before any write (corrupt/stale nodes).
 setup();WriteValue<u64>(n2,0,n1);before=memory;assert(QueueBbscNativeSignRefresh(broker)==0&&memory==before);
 setup();WriteValue<u64>(n2,0x10,1);before=memory;assert(QueueBbscNativeSignRefresh(broker)==0&&memory==before);
 setup();WriteValue<u64>(head,0,head);assert(QueueBbscNativeSignRefresh(broker)==0);
 setup();WriteValue<u64>(n2,0x10,0);assert(QueueBbscNativeSignRefresh(broker)==1);
 assert(ReadValue<u8>(e1,0xa0)==1&&ReadValue<u8>(e2,0xa0)==0);
 std::cout<<"PASS: native sign refresh 2s boundary, serialized requests, all own signs, session/bell guards, bounded validation, lifetime/payload untouched\n";
}
'''
build = root / 'build'
build.mkdir(exist_ok=True)
cpp, exe = build / 'test_sign_refresh.cpp', build / 'test_sign_refresh.exe'
cpp.write_text(fixture, encoding='utf-8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe', '-std=c++20', str(cpp), '-o', str(exe)], check=True)
env = dict(os.environ, PATH='C:/msys64/clang64/bin;' + os.environ.get('PATH', ''))
subprocess.run([str(exe)], check=True, env=env)
