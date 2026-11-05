"""Native m29 reward gates and scoped receipts. Artificial memory/files only."""
from pathlib import Path
import os
import re
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
s = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
sys.path.insert(0, str(ROOT/'tools/gamedata'))
import bbfiles
import emevd
bbfiles.GAME = os.environ['BB_GAME']
# Byte-verified dispatcher: [4] and [36] share the native call but pass DIFFERENT permissions.
elf = (ROOT.parents[1]/'out/exit-study.elf').read_bytes()
ph = struct.unpack_from('<Q', elf, 32)[0]
segments = [struct.unpack_from('<IIQQQQQQ', elf, ph + i*56)
            for i in range(struct.unpack_from('<H', elf, 56)[0])]
def native(address, size):
    for kind, _, offset, va, _, length, _, _ in segments:
        if kind == 1 and va <= address and address+size <= va+length:
            return elf[offset+address-va:offset+address-va+size]
    raise ValueError(hex(address))
assert native(0x17BEDD0,6) == bytes.fromhex('55 48 89 e5 41 57')
assert native(0x17C0696,10) == bytes.fromhex('ba 01 00 00 00 e9 64 11 00 00')
assert native(0x17C1802,9) == bytes.fromhex('31 d2 89 de e8 45 c4 01 00')
events = dict(emevd.Emevd(bbfiles.GAME+'/event/m29.emevd.dcx').events)
reviewed = [12901594,12901595,12901596,12901597,12901598,12901693,12901730]
for event in reviewed:
    ins = events[event]
    assert any(b == 2003 and i in (4,36) for b,i,a in ins)
    assert any((b,i) == (1003,2) for b,i,a in ins[:3])
    # Early removal changes eligibility only: native waits, choice and awards remain.
    assert any((b,i) == (3,0) for b,i,a in ins)

def fun(sig):
    a=s.index(sig+' {');b=s.index('{',a)+1;depth=1
    while depth:
        depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[a:b]+'\n'

def decl(pattern):
    return re.search(pattern,s,re.S).group()+'\n'

code=r'''
#include <windows.h>
#include <array>
#include <cassert>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <optional>
#include <set>
#include <string>
#include "core/cpu_patches.h"
using Core::GuestRegisterSnapshot;using Core::InstallGuestCodeHook;
using s64=int64_t;using s32=int32_t;using u32=uint32_t;
#define LOG_ERROR(...)
u64 image_base=0;
namespace BbscMod{u64 EbootAddress(){return image_base;}void LogPlain(const char*){}}
bool guest=true,shared=true,enabled=true;u32 map=0x1d000000;s64 event=12901693;
u8 bbsc_chalice_reward_gate_skip=0;
bool BbscGuestInHostWorld(){return guest;}
bool BbscSharedProgressEnabled(){return shared;}
bool EnvFlagEnabled(const char*){return enabled;}
u32 GetCurrentPackedMap(){return map;}
namespace Chalice{bool IsMap(u32 m){return (m>>24)==29;}}
bool ReadablePointer(u64 p,size_t){return p!=0;}
s64 BbscRunningEventId(u64){return event;}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
template<class T>void put(void* p,size_t o,T v){memcpy((u8*)p+o,&v,sizeof(v));}
'''
code+=fun('bool IsBbscChaliceBossRewardEvent(s64 event)')
code+=decl(r'struct BbscChaliceRewardTicket \{.*?\n\};')
code+='std::map<std::string,std::set<std::array<s64,4>>> bbsc_chalice_reward_receipts;std::set<std::string> bbsc_chalice_reward_invalid;\n'
code+='std::filesystem::path BbscChaliceRewardPath(const std::string& scope){return std::filesystem::path("receipts")/(scope+".bin");}\n'
code+=fun('bool BbscChaliceRewardClaimed(const BbscChaliceRewardTicket& ticket)')
code+=fun('void NoteBbscChaliceReward(const BbscChaliceRewardTicket& ticket)')
code+=r'''
enum class BbscLedgerSource{Give};
struct Context{u32 gives=0;BbscLedgerSource source{};s32 lot=0;u32 flag=0;};
std::optional<Context> bbsc_ledger_context;
std::optional<BbscChaliceRewardTicket> bbsc_chalice_reward_context;
constexpr u64 BbscGiveWindowReturn1=0x017D934D,BbscGiveWindowReturn2=0x017D94CC;
bool IsBbscBossRewardLot(s32){return false;}
void NoteBbscLedgerLot(s32,u32){}
void NoteBbscLedgerGiven(BbscLedgerSource,s32,u32,u32,s32){}
'''
code+=fun('void NoteBbscLedgerWindow(u64 caller_offset, u32 type, u32 id, s32 count)')
code+=r'''
bool boss_dead=false;
bool BbscEventFlag(u32){return boss_dead;}
std::optional<BbscChaliceRewardTicket> MakeBbscChaliceRewardTicket(u64,s64 e,s32 lot){return BbscChaliceRewardTicket{"gate-scope",{e,0,0,lot}};}
'''
code+=fun('void PS4_SYSV_ABI BbscChaliceRewardGateHook(u64, const GuestRegisterSnapshot* registers)')
code+=r'''
int native_runs=0;
u64 PS4_SYSV_ABI OriginalBank(u64,u64){++native_runs;return 77;}
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x2000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image_base);
 constexpr u64 entry=0x017BEDD0;
 const u8 body[]={0x55,0x48,0x89,0xe5,0x41,0x57,0x48,0x83,0xec,8,
 0x48,0xb8,0,0,0,0,0,0,0,0,0xff,0xd0,0x48,0x83,0xc4,8,0x41,0x5f,0x5d,0xc3};
 memcpy((void*)(image_base+entry),body,sizeof(body));u64 fn=(u64)OriginalBank;
 memcpy((void*)(image_base+entry+12),&fn,8);
 assert(InstallGuestCodeHook((void*)(image_base+entry),std::span<const u8>{body,6},0,BbscChaliceRewardGateHook,&bbsc_chalice_reward_gate_skip));
 using Bank=u64 PS4_SYSV_ABI (*)(u64,u64);auto bank=(Bank)(image_base+entry);
 alignas(16) u8 instance[0xc0]{},ref[16]{},file[0x500]{},args[8]{};
 put(instance,0xa8,(u64)ref);put(ref,8,(u64)file);put(file,0x10,u64(1));
 put(file,0x18,u64(0x90));put(file,0x28,u64(0x100));put(file,0x78,u64(0x400));
 put(file,0xa0,u64(0));put(instance,0xb0,(u64)file+0x120);put(instance,0xb8,(u64)args);
 put(file,0x120,s32(1003));put(file,0x124,s32(2));args[1]=1;
 for(s64 e:{12901594,12901595,12901596,12901597,12901598,12901693,12901730}){
  event=e;put(file,0x90,event);assert(bank(0,(u64)instance)==1);
 }
 event=12901693;put(file,0x90,event);
 // Later EndIfFlag and unrelated multiplayer/host gates retain native semantics.
 put(instance,0xb0,(u64)file+0x180);put(file,0x180,s32(1003));put(file,0x184,s32(2));
 assert(bank(0,(u64)instance)==77);
 put(instance,0xb0,(u64)file+0x120);shared=false;assert(bank(0,(u64)instance)==77);shared=true;
 put(file,0x124,s32(105));assert(bank(0,(u64)instance)==1);
 args[1]=3;assert(bank(0,(u64)instance)==77);args[1]=1;
 event=12901708;assert(bank(0,(u64)instance)==77);event=12901693;
 guest=false;assert(bank(0,(u64)instance)==77);guest=true;
 enabled=false;assert(bank(0,(u64)instance)==77);enabled=true;
 map=0x18010000;assert(bank(0,(u64)instance)==77);map=0x1d000000;
 // Same native reward twice is blocked; another ritual, layer, slot or lot is independent.
 BbscChaliceRewardTicket first{"user1-slot0-ritualA",{12901693,0,0,80109000}};
 assert(!BbscChaliceRewardClaimed(first));bbsc_chalice_reward_context=first;
 NoteBbscLedgerWindow(0x123456,0x40000000,6100,1);assert(!BbscChaliceRewardClaimed(first));
 NoteBbscLedgerWindow(BbscGiveWindowReturn1,0x40000000,6100,0);assert(!BbscChaliceRewardClaimed(first));
 NoteBbscLedgerWindow(BbscGiveWindowReturn1,0x40000000,6100,1);assert(BbscChaliceRewardClaimed(first));
 bbsc_chalice_reward_receipts.clear();assert(BbscChaliceRewardClaimed(first)); // production file read
 for(int field=0;field<4;++field){auto other=first;++other.award[field];assert(!BbscChaliceRewardClaimed(other));}
 for(auto scope:{"user2-slot0-ritualA","user1-slot1-ritualA","user1-slot0-ritualB"}){
  auto other=first;other.scope=scope;assert(!BbscChaliceRewardClaimed(other));
 }
 // Truncated/corrupt receipts stay blocked on every subsequent check.
 BbscChaliceRewardTicket broken{"broken",first.award};
 {std::ofstream out(BbscChaliceRewardPath(broken.scope),std::ios::binary);u32 m=0x31524342,n=1;out.write((char*)&m,4);out.write((char*)&n,4);}
 for(int k=0;k<3;++k)assert(BbscChaliceRewardClaimed(broken));
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-native-chalice-') as folder:
    path=Path(folder);cpp=path/'fixture.cpp';exe=path/'fixture.exe'
    cpp.write_text(code,encoding='utf-8')
    compiler=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler,'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
                    '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),
                    str(cpp),str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],cwd=path,env=env,check=True,timeout=20)
print('PASS: 7 original m29 reward events, actual gate trampoline, native negative paths, '
      'production receipt persistence and user/slot/ritual/layer/event/lot isolation')
