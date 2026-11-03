"""Exercise production HP death lifecycle without game files."""
from pathlib import Path
import os, subprocess, tempfile
source=(Path(__file__).resolve().parents[1]/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a=source.index('void TickBbscDeathLifecycle() {')
b=source.index('// ---- Enemy scaling',a)
code=r'''
#include <cassert>
#include <cstdint>
#include <string_view>
using s64=int64_t;using s32=int32_t;using u64=uint64_t;using u8=uint8_t;
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
s64 now=10000,bbsc_dead_since_ms=0,bbsc_death_script_ms=0;
constexpr s64 BbscRepeatDeathTextMs=500,BbscDeadWatchdogMs=15000;
bool bbsc_kept_death_this_load=true,bbsc_spectate_active=false,bbsc_spectate_releasing=false;
bool bbsc_death_text_submitted=false;
bool bbsc_boss_at_own_death=false,bbsc_death_text_raised=false,loading=false,curtain=false,enabled=true;
int hp=0,state=6,entries=0,texts=0,bbsc_echoes_at_death=0;
std::string_view reason;
bool BbscSpectateEnabled(){return enabled;}s64 SteadyNowMs(){return now;}
s32 GetSessionState(){return state;}u64 GetGlobalState(){return 1;}
u64 GetLocalPlayerCharacter(){return 1;}bool ReadablePointer(u64,int){return true;}
template<class T>T ReadValue(u64,int){return loading;}
s32 GetCharacterHp(u64){return hp;}bool BbscCurtainActive(){return curtain;}
bool BbscBossFightAtDeath(){return true;}int GetBloodEchoes(){return 1234;}
u64 BbscLuaEventObject(){return 1;}bool RaiseBbscDeathText(u64,std::string_view){++texts;return true;}
void BeginBbscCoopDeath(std::string_view why,s32){++entries;reason=why;bbsc_spectate_active=true;}
'''+source[a:b]+r'''
void reset(){hp=100;bbsc_death_text_submitted=true;bbsc_spectate_active=false;TickBbscDeathLifecycle();assert(!bbsc_death_text_submitted);hp=0;now+=1000;}
int main(){
 for(int role:{3,6}){state=role;reset();bbsc_kept_death_this_load=true;
  TickBbscDeathLifecycle();assert(bbsc_echoes_at_death==1234);now+=499;
  int before=entries;TickBbscDeathLifecycle();assert(entries==before);
  ++now;TickBbscDeathLifecycle();assert(entries==before+1&&reason=="repeat HP death");
  now+=20000;TickBbscDeathLifecycle();assert(entries==before+1);
 }
 // Fast next death must not inherit the previous native script timestamp.
 reset();bbsc_death_script_ms=now-100;hp=100;TickBbscDeathLifecycle();assert(bbsc_death_script_ms==0);
 hp=0;TickBbscDeathLifecycle();now+=500;int before=entries;TickBbscDeathLifecycle();assert(entries==before+1);
 // First death and an actual native script keep the 15s safety fallback.
 reset();bbsc_kept_death_this_load=false;TickBbscDeathLifecycle();now+=500;
 before=entries;TickBbscDeathLifecycle();assert(entries==before);now+=14500;
 TickBbscDeathLifecycle();assert(entries==before+1&&reason=="watchdog");
 reset();bbsc_kept_death_this_load=true;TickBbscDeathLifecycle();bbsc_death_script_ms=now;
 now+=500;before=entries;TickBbscDeathLifecycle();assert(entries==before);
 // Loads, missing actor HP, active curtain and teardown do not start another death.
 for(int mode:{0,1,2,3}){reset();loading=mode==0;hp=mode==1?-1:0;curtain=mode==2;state=mode==3?7:6;
  TickBbscDeathLifecycle();now+=20000;TickBbscDeathLifecycle();assert(entries==before);
  loading=false;curtain=false;state=6;}
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-repeat-death-') as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text(code,encoding='utf-8')
 compiler=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
 subprocess.run([compiler,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
 subprocess.run([str(exe)],env=env,check=True,timeout=5)
print('PASS: repeat HP deaths, native fallback, duplicate and load guards')
