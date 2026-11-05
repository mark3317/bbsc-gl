"""Native pre-audience barrier and production local gate; no game files changed."""
import os, struct, subprocess, sys, tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
sys.path.insert(0,str(root/'tools/gamedata'))
from emevd import Emevd
ev=dict(Emevd(Path(os.environ['BB_GAME'])/'event/m21_00_00_00.emevd.dcx').events)
assert (2005,3,struct.pack('<II',2101800,0)) in ev[12100800]
assert (2006,1,struct.pack('<II',2103800,0)) in ev[12100800]
for flag in (12101802,12104800):
    assert any(struct.pack('<I',flag) in a for b,i,a in ev[12104811])
a=s.index('void TickBbscDreamFirstAudience() {');b=s.index('\nbool PrepareBbscSharedFinaleActor()',a)
body=s[a:b].replace('image_base + 0x01315E50','reinterpret_cast<u64>(&NativeDelete)')
code=r'''
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;
#define PS4_SYSV_ABI
#define BBSC_TIMELINE(...)
constexpr u32 BbscDreamStateMap=0x15000000;constexpr int BbscWorldFlagsFreshMs=6000;
u64 image_base=1;std::atomic<u32>bbsc_load_generation{1};
int state=6,now=10;u32 map=BbscDreamStateMap;bool enabled=true,holding=false,loading=false,ready=true;
int GetSessionState(){return state;}u32 GetCurrentPackedMap(){return map;}
bool BbscDreamEnabled(){return enabled;}bool BbscDreamFinaleHolding(){return holding;}
u64 GetGlobalState(){return 1;}bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64,size_t){return loading;}
bool IsSprjLuaEventManReady(){return !loading;}int SteadyNowMs(){return now;}
struct BbscWorldSnapshot{int complete_ms=1;u64 present=2;std::array<std::array<u8,125>,40>groups{};}snap;
bool BbscHostBlockSnapshot(u32,BbscWorldSnapshot& out){out=snap;return ready;}
std::vector<std::array<u32,3>>calls;
void Draw(u32 id,u32 on){calls.push_back({0,id,on});}
void Collision(u32 id,u32 on){calls.push_back({1,id,on});}
void Create(u64,u32 id){calls.push_back({2,id,1});}
void NativeDelete(u64,u32 id,u32){calls.push_back({2,id,0});}
u64 ObjectDrawOffset=(u64)&Draw-1,ObjectCollisionOffset=(u64)&Collision-1,ObjectSfxEnableOffset=(u64)&Create-1;
''' + body + r'''
int main(){
 auto set=[](u32 flag,bool on){u32 bit=flag%1000;u8 mask=0x80u>>(bit%8);
 snap.groups[1][bit/8]=(snap.groups[1][bit/8]&~mask)|(on?mask:0);};
 for(int r:{0,3,4}){state=r;TickBbscDreamFirstAudience();assert(calls.empty());}
 state=6;ready=false;TickBbscDreamFirstAudience();assert(calls.empty());ready=true;
 loading=true;TickBbscDreamFirstAudience();assert(calls.empty());loading=false;
 auto own=snap.groups;TickBbscDreamFirstAudience();assert(calls.size()==3);
 assert(calls[0][1]==2101800&&calls[0][2]==0&&calls[2][1]==2103800&&calls[2][2]==0);
 TickBbscDreamFirstAudience();assert(calls.size()==3&&snap.groups==own);
 // Host alone starts intro. Close barrier once; subsequent wipes/loads remain native.
 set(12101802,true);TickBbscDreamFirstAudience();assert(calls.size()==6&&calls[3][2]==1&&calls[5][2]==1);
 TickBbscDreamFirstAudience();assert(calls.size()==6);++bbsc_load_generation;
 TickBbscDreamFirstAudience();assert(calls.size()==6);
 // New character/world can have its first audience; old intro/victory does not leak.
 set(12101802,false);++bbsc_load_generation;TickBbscDreamFirstAudience();assert(calls.size()==9);
 holding=true;set(12101800,true);TickBbscDreamFirstAudience();assert(calls.size()==9);
 holding=false;TickBbscDreamFirstAudience();assert(calls.size()==12&&calls[9][2]==0);
}
'''
assert 'talk == GehrmanTalkId && (BbscNightIsOver() || BbscEventFlag(9462))' in s
talks=s[s.index('constexpr std::array<BbscDreamTalk, 10>'):s.index('// Not allowed:')]
assert '{210306,' not in talks
with tempfile.TemporaryDirectory() as tmp:
    cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe';cpp.write_text(code)
    cxx='C:/msys64/clang64/bin/clang++.exe'
    subprocess.run([cxx,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(cxx).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],check=True,env=env)
print('PASS: native first-audience barrier; guest-only local geometry; authoritative intro; normal fog on retries; no progression writes; host-only final Gehrman talk')
