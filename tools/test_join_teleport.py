"""Exercise the production initial placement tick; no game/DLL build or live saves."""
from pathlib import Path
import os
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a = source.index('void TickBbscJoinTeleport() {')
b = source.index('// ---- Warping together', a)
code = r'''
#include <array>
#include <optional>
#include <mutex>
#include <cstdint>
#include <cassert>
using u32=uint32_t; using u64=uint64_t; using u8=uint8_t; using s64=int64_t; using s32=int32_t;
#define PS4_SYSV_ABI
#define LOG_WARNING(...)
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
bool bbsc_join_teleport_done=false;
std::mutex seamless_placement_mutex;
std::optional<int> bbsc_connect_first_placement;
s64 now=10000; int state=6,type=1,hp=100,host_hp=100,warps=0,blacks=0,reveals=0;
bool quit=false,loading=false,home=false,curtain=false,known=true,matches=true;
bool follow=false,valid_transform=true,valid_warp=true,fade_available=true;
u64 actor=10,host=20;
struct Transform {std::array<float,4> position{10,20,30,1},rotation{0,0,0,0};};
void warp(u64 chr,float* pos,float*,unsigned flag){
 assert(chr==actor&&pos[0]==11&&pos[1]==20&&flag==1);++warps;
}
bool BbscQuitInProgress(){return quit;} bool BbscCurtainActive(){return curtain;}
s64 SteadyNowMs(){return now;} int GetSessionState(){return state;}
u64 GetGlobalState(){return 1;} u64 GetLocalPlayerCharacter(){return actor;}
bool ReadablePointer(u64 p,int){return p!=0;}
template<class T>T ReadValue(u64 p,int off){
 if(p==1)return off==8?loading:home;
 if(p==actor&&off==0)return 30;
 if(p==30&&off==0x5F8)return reinterpret_cast<u64>(&warp);
 return 0;
}
template<class T>void WriteValue(u64,int,T){}
int GetLocalPlayerType(){return type;} bool BbscJoinDestinationKnown(){return known;}
bool BbscJoinWorldMatchesHost(){return matches;} bool BbscChaliceJoinNeedsFollow(){return follow;}
u64 FindRemoteHostCharacter(){return host;} int GetCharacterHp(u64 p){return p==actor?hp:host_hp;}
std::optional<Transform> ReadCharacterTransform(u64){return valid_transform?std::optional<Transform>{{}}:std::nullopt;}
bool IsEbootCodeAddress(u64){return valid_warp;}
int GetCurrentPackedMap(){return 24;} void LogBbscHostWorldFlagsDiff(int,const char*){}
bool BbscFadeTo(float alpha,float seconds){
 if(!fade_available)return false;
 if(alpha==1){assert(seconds==0);++blacks;}else{assert(seconds==0.15f);++reveals;}
 return true;
}
''' + source[a:b] + r'''
void reset(){
 state=0;loading=false;quit=false;curtain=false;hp=100;TickBbscJoinTeleport();
 state=6;type=1;home=false;known=true;matches=true;follow=false;host=20;
 valid_transform=true;valid_warp=true;fade_available=true;host_hp=100;
 warps=blacks=reveals=0;now+=1000;
}
int main(){
 reset(); TickBbscJoinTeleport();assert(blacks==1&&warps==0&&!bbsc_join_teleport_done);
 // One native update, no 250ms polling or 2-second settle. Once per session.
 now+=17;TickBbscJoinTeleport();assert(warps==1&&bbsc_join_teleport_done);
 now+=99;TickBbscJoinTeleport();assert(reveals==0&&warps==1);
 ++now;TickBbscJoinTeleport();assert(reveals==1&&warps==1);
 now+=3000;TickBbscJoinTeleport();assert(warps==1&&blacks==1);
 // All admission/readiness gates still precede the cover and warp.
 for(int mode=0;mode<10;++mode){
 reset(); if(mode==0)loading=true;if(mode==1)home=true;if(mode==2)known=false;
 if(mode==3)host=0;if(mode==4)hp=0;if(mode==5)host_hp=0;
 if(mode==6)valid_transform=false;if(mode==7)valid_warp=false;
 if(mode==8)curtain=true;if(mode==9)quit=true;
 TickBbscJoinTeleport();assert(warps==0&&blacks==0&&!bbsc_join_teleport_done);
 }
 reset();type=2;TickBbscJoinTeleport();assert(warps==0&&blacks==0&&bbsc_join_teleport_done);
 for(int mode=0;mode<2;++mode){reset();matches=mode!=0;follow=mode==1;
 TickBbscJoinTeleport();assert(warps==0&&blacks==0&&bbsc_join_teleport_done);}
 // Missing fade must not strand a guest; a bad vtable remains retryable.
 reset();fade_available=false;TickBbscJoinTeleport();assert(warps==1&&bbsc_join_teleport_done);
 reset();valid_warp=false;TickBbscJoinTeleport();valid_warp=true;
 TickBbscJoinTeleport();now+=17;TickBbscJoinTeleport();assert(warps==1);
 // Readiness loss releases black after 500ms. Disconnect releases it too.
 reset();TickBbscJoinTeleport();host=0;now+=501;TickBbscJoinTeleport();assert(reveals==1&&warps==0);
 reset();TickBbscJoinTeleport();state=7;TickBbscJoinTeleport();assert(reveals==1&&!bbsc_join_teleport_done);
 // Native transitions, actor replacement, death and quit own the fade: never reveal over them.
 for(int mode=0;mode<5;++mode){reset();TickBbscJoinTeleport();
 if(mode==0)loading=true;if(mode==1)++actor;if(mode==2)curtain=true;
 if(mode==3)hp=0;if(mode==4)quit=true;
 now+=1000;TickBbscJoinTeleport();assert(reveals==0&&warps==0);
 }
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-join-teleport-') as tmp:
    cpp = Path(tmp) / 'test.cpp'
    exe = Path(tmp) / 'test.exe'
    cpp.write_text(code, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler, '-std=c++20', str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], env=env, check=True, timeout=5)
print('PASS: immediate join placement, cover ownership, retry, map/role/load/readiness gates')
