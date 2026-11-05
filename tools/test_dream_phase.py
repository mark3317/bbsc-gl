"""Run production selective finale borrowing; native original EMEVD stays read-only."""
import os, struct, subprocess, sys, tempfile
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = (root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
sys.path.insert(0, str(root/'tools/gamedata'))
from emevd import Emevd
events = dict(Emevd(Path(os.environ['BB_GAME'])/'event/m21_00_00_00.emevd.dcx').events)
for event, flag in [(12100300,9462),(12100310,9462),(12100400,9462),
                    (12100143,1029),(12100144,1030),(12100145,12101800)]:
    assert any(struct.pack('<I',flag) in a for _,_,a in events[event]), (event,flag)
start = source.index('void ApplyBbscHostDreamPhase() {')
body = source[start:source.index('\n// Guest side:', start)]
code = r'''
#include <array>
#include <cstdint>
#include <mutex>
#include <cassert>
#include <cstring>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;
constexpr u32 BbscDreamStateMap=0x15000000;constexpr int BbscWorldFlagsFreshMs=6000;
struct BbscWorldSnapshot{u32 map=BbscDreamStateMap;int complete_ms=1;u64 present=33;std::array<std::array<u8,125>,57> groups{};};
BbscWorldSnapshot bbsc_dream_ready;std::mutex bbsc_world_mutex;
int role=6,now=100;int GetSessionState(){return role;}int SteadyNowMs(){return now;}
bool finale=false;bool BbscDreamFinaleHolding(){return finale;}
std::array<std::array<u8,125>,10> live{},saved{};bool held[10]{};int writes=0;
u64 BbscFlagGroupStorage(u32 k){return k<10?(u64)live[k].data():0;}
void KeepBbscOwnTimeBits(){}
void KeepBbscOwnWorldGroup(u32 k,u8* p){if(!held[k]){memcpy(saved[k].data(),p,125);held[k]=true;}}
void WriteBbscOwnWorldFile(){++writes;}
#define BBSC_TIMELINE(...)
''' + body + r'''
int main(){
 for(auto& g:live)g.fill(0x55);auto original=live;
 bbsc_dream_ready.groups[5].fill(0xff);bbsc_dream_ready.groups[0].fill(0xff);
 for(int r:{0,3,5,7}){role=r;ApplyBbscHostDreamPhase();assert(live==original);}
 role=4;ApplyBbscHostDreamPhase();assert(writes==1);
 for(u32 k=0;k<10;++k)for(u32 bit=0;bit<1000;++bit){bool allowed=(k==9&&bit==462)||(k==1&&bit>=28&&bit<=30);
 u8 mask=0x80u>>(bit%8);assert((live[k][bit/8]&mask)==(allowed?mask:(original[k][bit/8]&mask)));}
 assert(saved[1]==original[1]&&saved[9]==original[9]);
 role=6;ApplyBbscHostDreamPhase();assert(writes==1);
 bbsc_dream_ready.groups[5].fill(0);bbsc_dream_ready.groups[0].fill(0);
 finale=true;auto frozen=live;ApplyBbscHostDreamPhase();assert(live==frozen);finale=false;
 now=6001;auto before=live;ApplyBbscHostDreamPhase();assert(live==before);
 now=100;bbsc_dream_ready.present=0;ApplyBbscHostDreamPhase();assert(live==before);
 bbsc_dream_ready.present=33;bbsc_dream_ready.map=0x1a000000;ApplyBbscHostDreamPhase();assert(live==before);
 bbsc_dream_ready.map=BbscDreamStateMap;ApplyBbscHostDreamPhase();assert(writes==2);
 assert(saved[1]==original[1]&&saved[9]==original[9]);
}
'''
assert 'const bool dream = map == BbscDreamStateMap && BbscDreamEnabled();' in source
own = source[source.index('void ApplyBbscHostDreamState(std::string_view why) {'):]
assert own.index('ApplyBbscHostDreamPhase();') < own.index('our own Hunter')
with tempfile.TemporaryDirectory() as tmp:
    cpp, exe = Path(tmp)/'test.cpp', Path(tmp)/'test.exe'
    cpp.write_text(code)
    cxx = 'C:/msys64/clang64/bin/clang++.exe'
    subprocess.run([cxx,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(cxx).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],check=True,env=env)
print('PASS: native workshop/finale predicates; production roles, freshness, missing/wrong snapshots, on/off, personal bits and own journal')
