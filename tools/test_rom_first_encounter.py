"""Execute production Rom entrance policy; audit original EMEVD read-only via BB_GAME."""
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
start = source.index('void TickBbscRomFirstEncounter() {')
end = source.index('\nbool PrepareBbscSharedFinaleActor()', start)
body = source[start:end].replace('image_base + 0x01315E50', 'reinterpret_cast<u64>(&NativeDelete)')
tick = source[source.index('        TickBbscDreamFinale();'):]
assert tick.startswith('        TickBbscDreamFinale();\n        TickBbscRomFirstEncounter();')
sys.path.insert(0, str(root / 'tools/gamedata'))
from emevd import Emevd
events = dict(Emevd(Path(os.environ['BB_GAME']) / 'event/m32_00_00_00.emevd.dcx').events)
entrance = events[13204830]
for instruction in ((2005, 3, struct.pack('<II', 3201800, 0)),
                    (2006, 1, struct.pack('<II', 3203800, 0)),
                    (2011, 1, struct.pack('<II', 3204010, 0)),
                    (2005, 3, struct.pack('<II', 3201800, 1)),
                    (2006, 2, struct.pack('<I', 3203800)),
                    (2011, 1, struct.pack('<II', 3204010, 1))):
    assert instruction in entrance, instruction
for flag in (13201800, 13201802, 13204800):
    assert any(struct.pack('<I', flag) in args for _, _, args in events[13204831])

prefix = r'''
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define BBSC_TIMELINE(...)
constexpr int BbscWorldFlagsFreshMs=6000;
u64 image_base=1;std::atomic<u32>bbsc_load_generation{1};
int state=6,now=100;u32 current_map=0x20000000;
bool loading=false,lua=true,ready=true,quit=false,title=false,readable=true;
int GetSessionState(){return state;}u32 GetCurrentPackedMap(){return current_map;}
bool BbscQuitInProgress(){return quit;}bool BbscReturningToTitle(){return title;}
u64 GetGlobalState(){return 1;}bool ReadablePointer(u64,size_t){return readable;}
template<class T>T ReadValue(u64,size_t){return loading;}
bool IsSprjLuaEventManReady(){return lua;}int SteadyNowMs(){return now;}
struct BbscWorldSnapshot{int complete_ms=1;u64 present=2;
 std::array<std::array<u8,125>,40>groups{};}snap;
bool BbscHostBlockSnapshot(u32 map,BbscWorldSnapshot& out){assert(map==0x20000000);out=snap;return ready;}
std::vector<std::array<u32,3>>calls;
void PS4_SYSV_ABI Draw(u32 id,u32 on){calls.push_back({0,id,on});}
void PS4_SYSV_ABI Collision(u32 id,u32 on){calls.push_back({1,id,on});}
void PS4_SYSV_ABI Create(u64 zero,u32 id){assert(zero==0);calls.push_back({2,id,1});}
void PS4_SYSV_ABI NativeDelete(u64 zero,u32 id,u32 all){assert(zero==0&&all==1);calls.push_back({2,id,0});}
u64 ObjectDrawOffset=(u64)&Draw-1,ObjectCollisionOffset=(u64)&Collision-1,ObjectSfxEnableOffset=(u64)&Create-1;
'''
main = r'''
int main(){
 auto set=[](u32 flag,bool on){u32 group=(flag/1000)-13200,bit=flag%1000;
  u8 mask=0x80u>>(bit%8);snap.groups[group][bit/8]=(snap.groups[group][bit/8]&~mask)|(on?mask:0);};
 auto tick=[](){auto before=snap.groups;TickBbscRomFirstEncounter();assert(before==snap.groups);};
 for(int role:{0,3,4}){state=role;tick();assert(calls.empty());}state=6;
 for(u32 map:{0x15000000u,0x1d000000u,0u}){current_map=map;tick();assert(calls.empty());}current_map=0x20000000;
 image_base=0;tick();assert(calls.empty());image_base=1;
 ready=false;tick();assert(calls.empty());ready=true;
 snap.present=1;tick();assert(calls.empty());snap.present=2;
 now=6001;tick();assert(calls.empty());now=100;
 for(bool* guard:{&loading,&quit,&title}){*guard=true;tick();assert(calls.empty());*guard=false;}
 for(bool* guard:{&lua,&readable}){*guard=false;tick();assert(calls.empty());*guard=true;}
 // Fresh guest can reach the lake before any host intro or fight flags.
 tick();assert(calls.size()==4);
 assert((calls[0]==std::array<u32,3>{0,3201800,0}));
 assert((calls[1]==std::array<u32,3>{1,3201800,0}));
 assert((calls[2]==std::array<u32,3>{1,3204010,0}));
 assert((calls[3]==std::array<u32,3>{2,3203800,0}));
 tick();assert(calls.size()==4); // no repeated geometry/SFX writes
 // Host starts encounter: restore normal fog exactly once, even before battle snapshot.
 set(13201802,true);tick();assert(calls.size()==8);
 for(int i=0;i<4;++i){assert(calls[4+i][1]==calls[i][1]);assert(calls[4+i][2]==1);}
 set(13204800,true);tick();assert(calls.size()==8);
 ++bbsc_load_generation;tick();assert(calls.size()==8); // retries stay native
 set(13201800,true);tick();assert(calls.size()==8); // native victory owns fog
 // A different first-encounter world/load must not inherit the prior opened state.
 set(13201802,false);set(13201800,false);set(13204800,false);
 ++bbsc_load_generation;tick();assert(calls.size()==12);
 ready=false;set(13201802,true);tick();assert(calls.size()==12);ready=true;
 set(13201800,true);tick();assert(calls.size()==16);
 for(int i=12;i<16;++i)assert(calls[i][2]==0); // victory while temporarily open
 state=0;tick();state=6;set(13201800,false);set(13201802,false);tick();assert(calls.size()==20);
 ++bbsc_load_generation;tick();assert(calls.size()==24); // reopen new native geometry
}
'''
with tempfile.TemporaryDirectory() as directory:
    cpp = Path(directory) / 'test.cpp'
    exe = Path(directory) / 'test.exe'
    cxx = 'C:/msys64/clang64/bin/clang++.exe'
    env = dict(os.environ)
    env['PATH'] = str(Path(cxx).parent) + os.pathsep + env.get('PATH', '')
    for negative in (False, True):
        policy = body.replace('const bool first = !on(13201800) && !on(13201802);',
                              'const bool first = false;') if negative else body
        cpp.write_text(prefix + policy + main)
        subprocess.run([cxx, '-std=c++20', str(cpp), '-o', str(exe)], check=True)
        result = subprocess.run([str(exe)], env=env, capture_output=True)
        assert (result.returncode != 0) == negative, result.stderr.decode(errors='replace')
print('PASS: production Rom first entrance/geometry/native retry/victory/role/load/freshness guards; '
      'original EMEVD; old closed-entrance negative control fails')
