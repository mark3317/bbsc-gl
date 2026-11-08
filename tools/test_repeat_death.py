"""Production native death rearm/lifecycle; isolated memory, no game or saves."""
from pathlib import Path
import os, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')

def function(signature):
    a = source.index(signature+' {'); b = source.index('{',a)+1; depth = 1
    while depth:
        depth += (source[b]=='{')-(source[b]=='}'); b += 1
    return source[a:b]

state = source[source.index('struct BbscNativeDeathRearm {'):source.index('// Recreate only the native death detectors')]
functions = 'void RearmBbscNativeDeathEvents(bool allow_dead = false);\n'+function('u64 BbscLuaEventObject()')+'\n'+function('void RearmBbscNativeDeathEvents(bool allow_dead)')+'\n'+function('void TickBbscDeathLifecycle()')
if os.environ.get('BBSC_TEST_NO_DEATH_HANDOFF')=='1':
    functions=functions.replace('BeginBbscCoopDeath("watchdog", state);','/* historical native-only diagnostic */')
functions = functions.replace('reinterpret_cast<DeleteEvent>(image_base + 0x0132F030)', '&delete_event')
functions = functions.replace('reinterpret_cast<RegisterDeath>(image_base + 0x01329B70)', '&register_death')
functions = functions.replace('reinterpret_cast<RegisterHp>(image_base + 0x01329D30)', '&register_hp')
# Parentheses preserve the actual indirect-call syntax after replacing addresses.
functions = functions.replace('&delete_event(', 'delete_event(').replace('&register_death(', 'register_death(').replace('&register_hp(', 'register_hp(')
prefix = r"""
#include <atomic>
#include <cassert>
#include <cstdint>
#include <map>
#include <string_view>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define BBSC_TIMELINE(...)
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define LOG_ERROR(...)
#define PS4_SYSV_ABI
namespace MemoryProt {constexpr int CpuWrite=1;}
u64 image_base=0x80000000,SprjLuaEventManPointerOffset=0x553B0C8;
u64 player=0x10000,global=0x20000,manager=0x30000,event=0x40000;
s64 now=10000,bbsc_dead_since_ms=0,bbsc_death_script_ms=0;
constexpr s64 BbscDeadWatchdogMs=15000;
std::atomic<u32> bbsc_load_generation{1};
std::map<u64,u64> memory;
int hp=100,state=6,deletes=0,deaths=0,hps=0;
bool enabled=true,quit=false,title=false,writable=true,death_ok=true,hp_ok=true;
bool bbsc_spectate_active=false,bbsc_spectate_releasing=false;
bool bbsc_boss_at_own_death=false,curtain=false;
bool bbsc_boss_wipe_seen=false,all_report_dead=false,living_partner=true;
int handoffs=0,echoes=123,bbsc_echoes_at_death=-1;bool boss=false;
int GetBloodEchoes(){return echoes;}
void BeginBbscCoopDeath(std::string_view why,s32 role){assert(why=="watchdog"&&role==state);assert(bbsc_dead_since_ms>0&&now-bbsc_dead_since_ms>=BbscDeadWatchdogMs);++handoffs;bbsc_spectate_active=true;}
bool BbscSpectateEnabled(){return enabled;}s64 SteadyNowMs(){return now;}
s32 GetSessionState(){return state;}u64 GetGlobalState(){return global;}
u64 GetLocalPlayerCharacter(){return player;}
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
bool HasMemoryAccess(u64,size_t,int){return writable;}
template<class T>T ReadValue(u64 p,size_t o){return static_cast<T>(memory[p+o]);}
template<class T>void WriteValue(u64 p,size_t o,T v){memory[p+o]=v;}
int GetCharacterHp(u64){return hp;}bool BbscCurtainActive(){return curtain;}
bool BbscBossFightAtDeath(){return boss;}
bool BbscAllPartnersReportDead(){return all_report_dead;}
bool LivingPartnerExists(){return living_partner;}
bool BbscQuitInProgress(){return quit;}bool BbscReturningToTitle(){return title;}
void delete_event(u64 e,s32 id){assert(e==event&&id==99999);++deletes;}
bool register_death(u64 e,s32 id,s32 chr,const char* name,u8 once){
 assert(e==event&&id==99999&&chr==10000&&std::string_view(name)=="OnEvent_4000"&&once==0);
 ++deaths;return death_ok;
}
bool register_hp(u64 e,s32 id,s32 chr,const char* name,u8 once,float value){
 assert(e==event&&id==99999&&chr==10000&&std::string_view(name)=="OnEvent_4000_Hp"&&once==1&&value==0);
 assert(memory[event+0x8a]==0);++hps;return hp_ok;
}
"""
main = r"""
void reset(){memory.clear();player=0x10000;global=0x20000;event=0x40000;
 memory[image_base+SprjLuaEventManPointerOffset]=manager;
 memory[manager]=0x50000;memory[manager+8]=event;memory[event+0x8a]=1;
 bbsc_native_death_api_ready=true;bbsc_native_death_rearm={};
 hp=100;state=6;deletes=deaths=hps=0;quit=title=false;writable=true;death_ok=hp_ok=true;
 bbsc_spectate_active=bbsc_spectate_releasing=curtain=false;
 bbsc_dead_since_ms=bbsc_death_script_ms=0;handoffs=0;echoes=123;boss=false;bbsc_echoes_at_death=-1;now+=1000;
}
void retained_death(){bbsc_native_death_rearm={player,global,0,bbsc_load_generation.load()};}
int main(){
 // First life keeps native map initialization. After each kept death both
 // original detectors are recreated once for the same native dispatch next time.
 for(int role:{3,6}){reset();state=role;
  TickBbscDeathLifecycle();assert(deletes==0&&deaths==0&&hps==0);
  for(int life=1;life<=3;++life){
   retained_death();hp=0;bbsc_spectate_active=true;
   TickBbscDeathLifecycle();assert(deletes==life-1);bbsc_spectate_active=false;
   hp=100;TickBbscDeathLifecycle();
   assert(deletes==life&&deaths==life&&hps==life&&memory[event+0x8a]==1);
   assert(bbsc_native_death_rearm.player==0);
   TickBbscDeathLifecycle();assert(deletes==life&&deaths==life&&hps==life);
  }
 }
 // A declined registration retries only the missing half, preserving mode.
 reset();retained_death();hp_ok=false;TickBbscDeathLifecycle();
 assert(deletes==1&&deaths==1&&hps==1&&memory[event+0x8a]==1);
 now+=499;TickBbscDeathLifecycle();assert(hps==1);
 ++now;hp_ok=true;TickBbscDeathLifecycle();assert(deletes==1&&deaths==1&&hps==2);
 assert(!bbsc_native_death_rearm.player);
 reset();retained_death();death_ok=false;TickBbscDeathLifecycle();
 now+=500;death_ok=true;TickBbscDeathLifecycle();assert(deletes==1&&deaths==2&&hps==1);
 // Even a rapid next death while one registration was declined stays native:
 // retry the missing detector, without synthesizing a death final step.
 reset();retained_death();death_ok=false;TickBbscDeathLifecycle();
 hp=0;now+=500;death_ok=true;TickBbscDeathLifecycle();
 assert(deletes==1&&deaths==2&&hps==1&&!bbsc_native_death_rearm.player);
 // Actor/global/load/session fences discard an obsolete attempt.
 for(int mode=0;mode<5;++mode){reset();retained_death();
  if(mode==0)++player;if(mode==1)++global;if(mode==2)++bbsc_load_generation;
  if(mode==3)state=7;if(mode==4)memory[global+8]=1;
  TickBbscDeathLifecycle();assert(deletes==0&&deaths==0&&hps==0);
  assert(!bbsc_native_death_rearm.player);
 }
 // No registration while quitting, still dying, behind curtain or without managers.
 for(int mode=0;mode<8;++mode){reset();retained_death();
  if(mode==0)quit=true;if(mode==1)title=true;if(mode==2){hp=0;bbsc_death_script_ms=now;}
  if(mode==3)curtain=true;if(mode==4)bbsc_spectate_active=true;
  if(mode==5)memory[manager]=0;if(mode==6)writable=false;
  if(mode==7)bbsc_native_death_api_ready=false;
  TickBbscDeathLifecycle();assert(deletes==0&&deaths==0&&hps==0);
 }
 // Regression: the old common handoff must still handle a stalled native
 // script. Capture echoes at death, wait the original15s and enter the SAME
 // controller exactly once; no direct revive/text/status handlers exist here.
 for(int role:{3,6})for(bool in_boss:{false,true}){
  reset();state=role;boss=in_boss;hp=0;TickBbscDeathLifecycle();
  assert(bbsc_echoes_at_death==123&&bbsc_boss_at_own_death==boss);
  now+=14999;echoes=0;TickBbscDeathLifecycle();assert(handoffs==0);
  ++now;TickBbscDeathLifecycle();assert(handoffs==1&&bbsc_spectate_active);
  assert(bbsc_echoes_at_death==123);now+=20000;TickBbscDeathLifecycle();assert(handoffs==1);
 }
 // Loading, quitting, unknown HP, title, solo, active native-final handling
 // and a living character cannot trigger recovery of a stale death.
 for(int mode=0;mode<8;++mode){reset();hp=0;TickBbscDeathLifecycle();now+=20000;
  if(mode==0)memory[global+8]=1;if(mode==1)quit=true;if(mode==2)title=true;
  if(mode==3)hp=-1;if(mode==4)state=0;if(mode==5)hp=100;
  if(mode==6)bbsc_spectate_active=true;if(mode==7)curtain=true;
  TickBbscDeathLifecycle();assert(handoffs==0);
 }
 for(bool other_alive:{false,true}){
  reset();boss=true;hp=0;all_report_dead=!other_alive;living_partner=other_alive;
  TickBbscDeathLifecycle();assert(bbsc_boss_wipe_seen==!other_alive);
  all_report_dead=false;living_partner=true;++now;TickBbscDeathLifecycle();
  assert(bbsc_boss_wipe_seen==!other_alive); // another hunter finished loading first
  hp=100;++now;TickBbscDeathLifecycle();assert(!bbsc_boss_wipe_seen);
 }

}
"""
# Confirm the handoff sites and the removal of the old mod-only death pipeline.
respawn = function('bool BbscRespawnInPlace(std::string_view why)')
assert respawn.index('ClearBbscStaleDeathRequest(why)') < respawn.index('RearmBbscNativeDeathEvents()')
assert 'bbsc_native_death_rearm = {GetLocalPlayerCharacter()' in function('void BeginBbscCoopDeath(std::string_view name, s32 session_state)')
assert 'RaiseBbscDeathText' not in source and 'ShowBbscGuestDeathText' not in source
with tempfile.TemporaryDirectory(prefix='bbsc-native-death-') as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe'
 cpp.write_text(prefix+state+functions+main,encoding='utf-8')
 compiler=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
 subprocess.run([compiler,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
 subprocess.run([str(exe)],env=env,check=True,timeout=5)
print('PASS: native death rearm, three host/guest lives, partial failures, context/load/teardown fences; restored bounded common handoff')

# Read-only byte checks of the original native registration and guest text path.
elf = ROOT.parents[1]/'out/register-study.elf'
if elf.exists():
    import struct
    binary = elf.read_bytes()
    def span(address, size):
        return binary[address+0x4000:address+0x4000+size]
    def call(address):
        assert span(address, 1) == b'\xe8'
        return address+5+struct.unpack('<i', span(address+1,4))[0]
    assert call(0x137D8EA) == 0x1329B70
    assert call(0x137D916) == 0x1329D30
    assert span(0x137D8DA,10).hex() == 'be9f860100ba10270000'
    assert span(0x137D8E4,3).hex() == '4531c0'  # main native detector: once=false
    assert span(0x137D90D,6).hex() == '41b801000000'  # HP watcher: once=true
    assert span(0x492E303,13) == b'OnEvent_4000\x00'
    assert span(0x492E2F3,16) == b'OnEvent_4000_Hp\x00'
    assert span(0x1329B70,6).hex() == '554889e54157'
    assert span(0x1329D30,6).hex() == '554889e54157'
    assert span(0x132F030,6).hex() == '554889e54156'
    assert call(0x13820DD) == 0x132EAD0  # PartyGhostDeath_wait raises native YOU DIED
    assert 0x138DA4F+7+struct.unpack('<i',span(0x138DA4F+3,4))[0] == 0x13813D0
    print('PASS: original native detector arguments, API signatures, OnEvent_4000 binding and guest YOU DIED path')
else:
    print('SKIP: optional original native layout check (out/register-study.elf absent)')
