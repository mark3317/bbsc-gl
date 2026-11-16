"""Native load retires only old death bookkeeping; new death stays native."""
import ast, os, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
    a=source.index(signature+' {'); b=source.index('{',a)+1; depth=1
    while depth:
        depth+=(source[b]=='{')-(source[b]=='}'); b+=1
    return source[a:b]
tree=ast.parse((ROOT/'tools/test_post_load_recovery.py').read_text())
prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
prefix=prefix.replace('void FinishBbscDeathAtNativeLoad() {}','void FinishBbscDeathAtNativeLoad();')
extra=r'''
#include <optional>
#define BBSC_TIMELINE(...)
constexpr s64 BbscLateDeathStepMs=15000;
int GetCharacterHp(u64){return hp;}
void ClearBbscStaleDeathRequest(std::string_view){assert(false);}
void ArmBbscDeathLockClear(){assert(false);}
enum class BbscCurtainStep {Idle,FadingOut};
struct Curtain {BbscCurtainStep step=BbscCurtainStep::Idle;};
Curtain bbsc_curtain;
struct Rearm {int player=0;}; Rearm bbsc_native_death_rearm;
enum class BbscDeathMode {Spectate,RespawnNow};
enum class BbscBossDeathGroup {Unavailable,Ready};
BbscDeathMode bbsc_death_mode=BbscDeathMode::Spectate;
BbscBossDeathGroup bbsc_boss_death_group=BbscBossDeathGroup::Unavailable;
bool bbsc_request_death_reload=false,bbsc_boss_at_own_death=false,bbsc_boss_wipe_seen=false,bbsc_boss_death_ready=false;
s64 bbsc_spectate_since_ms=0,bbsc_spectate_death_ms=0,bbsc_spectate_alone_since_ms=0;
s64 bbsc_dead_since_ms=0,bbsc_death_script_ms=0,bbsc_inplace_respawn_ms=0;
s64 bbsc_death_lock_until_ms=0,bbsc_state_diff_at_ms=0,bbsc_boss_cleared_since_ms=0;
u32 bbsc_spectate_load_generation=0;
std::string_view bbsc_spectate_name;
int bbsc_echoes_at_death=-1;
u8 bbsc_late_death_skip[3]={},bbsc_late_final_skip[2]={};
std::optional<u32> bbsc_death_reload_generation;
void stale(){
 bbsc_spectate_active=bbsc_spectate_releasing=bbsc_request_death_reload=true;
 bbsc_boss_at_own_death=bbsc_boss_wipe_seen=bbsc_boss_death_ready=true;
 bbsc_spectate_since_ms=bbsc_spectate_death_ms=bbsc_spectate_alone_since_ms=99;
 bbsc_dead_since_ms=bbsc_death_script_ms=bbsc_inplace_respawn_ms=99;
 bbsc_death_lock_until_ms=bbsc_state_diff_at_ms=bbsc_boss_cleared_since_ms=99;
 bbsc_curtain.step=BbscCurtainStep::FadingOut;bbsc_native_death_rearm.player=1;
 for(auto& x:bbsc_late_death_skip)x=1;for(auto& x:bbsc_late_final_skip)x=1;
 bbsc_echoes_at_death=123;bbsc_death_reload_generation=bbsc_load_generation.load();
 bbsc_v8_pending=true;bbsc_wipe_restock_pending=true;
}
void clean(){
 assert(!bbsc_spectate_active&&!bbsc_spectate_releasing&&!bbsc_request_death_reload);
 assert(!bbsc_boss_at_own_death&&!bbsc_boss_wipe_seen&&!bbsc_boss_death_ready);
 assert(!bbsc_dead_since_ms&&!bbsc_death_script_ms&&!bbsc_inplace_respawn_ms);
 assert(!bbsc_death_lock_until_ms&&!bbsc_state_diff_at_ms&&!bbsc_boss_cleared_since_ms);
 assert(bbsc_curtain.step==BbscCurtainStep::Idle&&!bbsc_native_death_rearm.player);
 for(auto x:bbsc_late_death_skip)assert(!x);for(auto x:bbsc_late_final_skip)assert(!x);
 assert(bbsc_echoes_at_death==-1&&!bbsc_death_reload_generation&&!bbsc_wipe_restock_pending);
 assert(bbsc_v8_pending); // session reconstruction remains independent of death
}
'''
main=r'''
int main(){
 memory[player+0x78]=1;
 for(int role:{0,3,6})for(int health:{-1,0,100}){
  state=role;hp=health;stale();int before=restocks;auto native=memory;
  FinishBbscDeathAtNativeLoad();clean();assert(hp==health&&memory==native);
  assert(restocks==before+(role==6&&health>0));
 }
 state=6;hp=100;
 bbsc_inplace_respawn_ms=clock_ms;
 bbsc_reload_finish_pending=true;assert(!BbscLateDeathStep("new load"));bbsc_reload_finish_pending=false;
 bbsc_world_load_pending=global;assert(!BbscLateDeathStep("new actor"));bbsc_world_load_pending=0;
 memory[global+8]=1;assert(!BbscLateDeathStep("loading"));memory[global+8]=0;
 hp=0;assert(!BbscLateDeathStep("real new death"));hp=100;
 for(int mode=0;mode<3;++mode){
  stale();auto gen=bbsc_load_generation.load();
  if(mode==0){memory[global+8]=1;TickBbscLoadState();assert(bbsc_spectate_active);memory[global+8]=0;}
  if(mode==1)bbsc_reload_finish_pending=true;
  if(mode==2)bbsc_world_load_pending=global;
  TickBbscLoadState();assert(bbsc_load_generation==gen+1);clean();
  // A new death after completion is not cleaned again on the next ordinary tick.
  hp=0;bbsc_spectate_active=true;bbsc_dead_since_ms=clock_ms;
  TickBbscLoadState();assert(bbsc_spectate_active&&bbsc_dead_since_ms==clock_ms&&hp==0);
  hp=100;
 }
}
'''
code=prefix+extra+function('bool IsInvaderType(s32 type)')+function('bool BbscLateDeathStep(std::string_view name)')+function('void FinishBbscDeathAtNativeLoad()')+function('void TickBbscLoadState()')+main
with tempfile.TemporaryDirectory(prefix='bbsc-life-boundary-') as tmp:
    cpp=Path(tmp)/'test.cpp'; exe=Path(tmp)/'test.exe'; cpp.write_text(code)
    subprocess.run([os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=5)
assert 'BbscRespawnLoopMs' not in source and 'BbscDiedRightAfterRespawn' not in source
assert 'BbscRespawnInPlace' not in function('void TickBbscPostLoadRecovery()')
print('PASS: native load boundary, host/guest/solo, alive/dead/missing HP, skipped load ticks, new death preserved, no 10-second reload')
