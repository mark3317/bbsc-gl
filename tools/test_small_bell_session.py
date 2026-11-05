"""Execute production availability and both native item entry gates, no game data."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
availability = source[source.index('bool BbscSmallBellSessionBlocked()'):source.index(
    'void OnBbscCutsceneRequestHook(u64 offset')]
entry = source.index('    // Native entry, before goods effects')
dispatch = source[entry:source.index('#endif', entry)]
functional = source[source.index('bool BbscFunctionalTraceSite('):source.index(
    'bool BbscEssentialDiagnosticSite(')]
assert 'if (site.offset == 0x018F9720 || site.offset == 0x018C9160) return true;' in functional
assert '(site.offset == 0x018F9720 || site.offset == 0x018C9160) ? &bbsc_party_item_skip :' in source

prefix = r'''
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <mutex>
#include <string>
#include <string_view>
using u64=uint64_t;using u32=uint32_t;using s32=int32_t;using u8=uint8_t;
#define BBSC_MOD
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
namespace fmt {template<class... T> std::string format(T...){return {};}}
struct GuestRegisterSnapshot {
 u64 r13=0,r14=17,rcx=0x123401,rbp=0,r12=1,r15=1,rsi=205,r8=1,rdi=17,rax=99;
};
int state=0,cancelled=0,host_gates=0;bool anywhere=false,party=true;
u64 GetLocalPlayerCharacter(){return 17;}
s32 GetSessionState(){return state;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
u64 BbscCarriedInventory(){return 1;}
bool BbscInventoryHas(u64,u32){return true;}
bool EnvFlagEnabled(const char*){return anywhere;}
int GetCharacterHp(u64){return 100;}
bool BbscResearchEnabled(){return false;}
u32 GetCurrentPackedMap(){return 0;}
namespace BbscMod {
bool PartyEnabled(){return party;}
bool PartyCanBeckon(){return true;}
void PartyCancel(){++cancelled;}
}
void ObserveBbscHostBlankItem(u32){}
bool GateBbscPartyItem(const GuestRegisterSnapshot&){++host_gates;return true;}
u8 bbsc_party_item_skip=0;
struct Site {u64 offset;};
'''
main = r'''
int main(int argc,char**){
 anywhere=argc>1;
 alignas(8) std::array<u8,0x48> row{};
 alignas(8) std::array<u8,0x210> stack{};
 // Valid native frame for the bells-anywhere fallback.
 stack[0x210-0x1E1]=stack[0x210-0x1D8]=stack[0x210-0x1D4]=stack[0x210-0x1B4]=1;
 for(bool use_party:{false,true}) for(int session:{0,2,3,4,5,6,7}) {
  party=use_party;state=session;
  const bool blocked=session==3||session==4||session==6||session==7;
  for(int effect:{9005,7511,7,1234}) for(u64 native:{0ull,1ull}) {
   std::memcpy(row.data(),&effect,4);
   GuestRegisterSnapshot r;r.r13=reinterpret_cast<u64>(row.data());
   r.rbp=reinterpret_cast<u64>(stack.data()+stack.size());r.rcx=0x123400|native;
   ApplyBbscBellsAnywhere(&r);
   if(effect==9005 && blocked) assert(r.rcx==0x123400);
   else if(native || effect==7 || effect==1234) assert(r.rcx==(0x123400|native));
   else assert((r.rcx&255)==(anywhere?1:0));
  }
  for(u64 offset:{0x018F9720ull,0x018C9160ull})
   for(u64 goods:{205ull,4121ull,0x400000CDull,200ull,111ull,201ull,225ull,120ull}) {
    GuestRegisterSnapshot r;r.rsi=goods;
    bbsc_party_item_skip=1;native_entry({offset},&r);
    const bool deny=blocked && ((goods&0x0FFFFFFF)==205 || goods==4121);
    assert(bbsc_party_item_skip==deny);assert(r.rax==(deny?0:99));
    // Checks on remote actors must not interfere with their native actions.
    r.rdi=18;r.rax=99;native_entry({offset},&r);
    assert(!bbsc_party_item_skip && r.rax==99);
   }
 }
 // Returning home releases the prohibition immediately.
 state=3;assert(BbscSmallBellSessionBlocked());state=0;assert(!BbscSmallBellSessionBlocked());
 assert(cancelled>0 && host_gates>0);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-small-bell-') as tmp:
    cpp, exe = Path(tmp)/'test.cpp', Path(tmp)/'test.exe'
    cpp.write_text(prefix + availability + '\nvoid native_entry(Site site,const GuestRegisterSnapshot* registers){\n'
                   + dispatch + '\n}\n' + main, encoding='utf-8')
    subprocess.run([os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe'),
                    '-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env = dict(os.environ, PATH='C:/msys64/clang64/bin;' + os.environ.get('PATH',''))
    for args in ([], ['anywhere']):
        subprocess.run([str(exe), *args],check=True,env=env,timeout=10)
print('PASS: Small Bell host/join/guest/invader availability and native execution, home release, both overrides')
