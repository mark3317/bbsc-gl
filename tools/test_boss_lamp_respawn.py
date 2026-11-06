"""Production boss identity and respawn destination selection; no game/save access."""
import ast
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')


def function(signature):
    start = SOURCE.index(signature + ' {')
    at = SOURCE.index('{', start) + 1
    depth = 1
    while depth:
        depth += (SOURCE[at] == '{') - (SOURCE[at] == '}')
        at += 1
    return SOURCE[start:at]


table = SOURCE[SOURCE.index('struct BbscBossLamp {'):SOURCE.index('s32 bbsc_encounter_lamp')]
# Check every destination against the independently maintained original-event catalog.
catalog = ast.parse((ROOT.parent.parent / 'scripts/boss_rematches.py').read_text(encoding='utf-8'))
bosses = next(n.value for n in catalog.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'BOSSES' for t in n.targets))
expected = {ast.literal_eval(b.args[2]) + 1000 for b in bosses.elts}
assert {int(p) for p in re.findall(r'\{\d+, (\d+)\}', table)} == expected

code = r'''
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <mutex>
#include <optional>
#include <string_view>
#include <unordered_map>
using u8=uint8_t; using u32=uint32_t; using u64=uint64_t;
using s32=int32_t; using s64=int64_t;
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
struct BbscTransform { std::array<float,4> position{},rotation{}; };
u64 image_base=0x100000,global=0x200000,player=0x300000,gauge=0x400000;
constexpr u64 BossGaugePointerOffset=0x10,CandidateLocalStatePointerOffset=0x18;
std::unordered_map<u64,u64> mem;
template<class T>T ReadValue(u64 p,size_t off){return static_cast<T>(mem[p+off]);}
bool ReadablePointer(u64 p,size_t){return p!=0;}
u64 GetGlobalState(){return global;}
u64 GetLocalPlayerCharacter(){return player;}
bool IsSprjLuaEventManReady(){return true;}
u32 map=0x18010000;
u32 GetCurrentPackedMap(){return map;}
bool BbscMapResident(u32){return false;}
bool IsUsablePackedMap(u32 p){return p!=0;}
u32 BbscMapArea(u32 p){return p>>24;}
bool BbscChaliceArrivalReady(u32){return true;}
bool BbscChaliceNeedsLoad(u32){return false;}
bool independent=false;
bool BbscIndependentActive(){return independent;}
bool shared_checkpoint=false,shared_here=true;
bool ReadBbscSharedLampCheckpoint(s32&,bool&){return shared_checkpoint;}
std::atomic<u32> bbsc_load_generation{7};
s32 bbsc_encounter_lamp=-1;
u32 bbsc_encounter_map=0,bbsc_encounter_load_generation=0;
s64 bbsc_boss_killed_ms=200,bbsc_spectate_since_ms=100;
std::mutex bbsc_follow_mutex;
struct Follow {s64 received_ms=1;s32 lamp_point=2412950;u32 packed_map=0x18010000;};
Follow bbsc_follow_latest;
bool resolve=true;
std::optional<BbscTransform> ResolveLampPoint(s32 p){
 if(!resolve || p==-1)return {}; BbscTransform t;t.position[0]=static_cast<float>(p);return t;
}
s32 own_lamp=2412950;
std::optional<BbscTransform> ResolveLastLampTransform(){return shared_here?ResolveLampPoint(own_lamp):std::nullopt;}
std::optional<BbscTransform> ResolveNearestLoadedLamp(const std::array<float,4>&,s32*){return {};}
u64 FindLivingPartnerCharacter(){return 0;}
std::optional<BbscTransform> ReadCharacterTransform(u64){return {};}
float selected=0;
std::string_view selected_where;
'''
code += table
for sig in ['u32 BbscLampPointMap(s32 point)', 'bool BbscLampBlockLoaded(s32 point)',
            'void RememberBbscBossLamp()',
            'std::optional<BbscTransform> ResolveBbscDefeatedBossLamp(std::string_view why)']:
    code += '\n' + function(sig)
# Execute the unmodified production guards/destination branches, stopping at the
# native revive boundary. Native revive/death accounting itself is unchanged.
selection = function('bool BbscRespawnInPlace(std::string_view why)')
selection = selection[:selection.index('    // Blood echoes are NOT dropped here:')]
negative = os.environ.get('BBSC_TEST_BOSS_SHARED_OLD') == '1'
if negative:
    selection = selection.replace('target = ResolveBbscDefeatedBossLamp(why);',
        'target = shared_checkpoint ? ResolveLastLampTransform() : ResolveBbscDefeatedBossLamp(why);')
code += '\n' + selection + 'selected=target->position[0]; selected_where=where; return true;\n}\n'
code += r'''
void bars(s32 name){
 for(int slot=0;slot<3;++slot)mem[gauge+0x165C+slot*0x14]=static_cast<u32>(-1);
 if(name!=-1){mem[gauge+0x165C]=123;mem[gauge+0x1658]=name;}
}
int main(){
 mem[image_base+BossGaugePointerOffset]=gauge;
 mem[image_base+CandidateLocalStatePointerOffset]=0x500000;
 mem[player+0x58]=0x600000;mem[player+0x3B0]=0x700000;
 mem[0x600000+0x280]=1;
 // Every mapped phase/name matches its own map, and survives death's HUD clear.
 for(auto boss:BbscBossLamps){
  map=BbscLampPointMap(boss.point);bars(boss.name);RememberBbscBossLamp();
  assert(bbsc_encounter_lamp==boss.point);
  bars(-1);RememberBbscBossLamp();
  assert(ResolveBbscDefeatedBossLamp("boss killed")->position[0]==boss.point);
 }
 map=0x18010000;bars(500000);RememberBbscBossLamp();bars(-1);
 for(bool guest:{false,true}){
  mem[global+0x1592]=guest?0:1;
  assert(BbscRespawnInPlace("boss killed"));
  assert(selected==2412952 && selected_where=="defeated boss lamp");
  assert(BbscRespawnInPlace("no boss fight"));
  assert(selected==2412950); // ordinary deaths still use the previous lamp
 }
 assert(!ResolveBbscDefeatedBossLamp("wipe"));
 // Independent guests never borrow a different host lamp or partner position.
 // Each participant retains its selected lamp even with the host elsewhere.
 independent=true;own_lamp=2412951;
 for(bool guest:{false,true})for(u32 host_map:{0x18010000u,0x15000000u}){
  mem[global+0x1592]=guest?0:1;bbsc_follow_latest.packed_map=host_map;
  bbsc_follow_latest.lamp_point=2412950;
  assert(BbscRespawnInPlace("no boss fight")&&selected==own_lamp);
  assert(BbscRespawnInPlace("boss killed")&&selected==2412952);
  own_lamp=-1;assert(!BbscRespawnInPlace("no boss fight"));own_lamp=2412951;
 }
 // Victory always uses the encounter's boss lamp for both roles, including
 // when the shared checkpoint is in a different (possibly resident) map.
 shared_checkpoint=true;
 for(bool guest:{false,true}){
  mem[global+0x1592]=guest?0:1;
  for(bool here:{false,true}){
   shared_here=here;
   assert(BbscRespawnInPlace("boss killed")&&selected==2412952&&selected_where=="defeated boss lamp");
   if(here)assert(BbscRespawnInPlace("no boss fight")&&selected==own_lamp&&selected_where=="last lamp");
   else assert(!BbscRespawnInPlace("no boss fight"));
   // Stale kill/encounter never authorizes a boss-lamp teleport.
   bbsc_boss_killed_ms=0;
   if(here)assert(BbscRespawnInPlace("boss killed")&&selected==own_lamp);
   else assert(!BbscRespawnInPlace("boss killed"));
   bbsc_boss_killed_ms=200;
  }
 }
 shared_here=true;
 shared_checkpoint=false;
 independent=false;own_lamp=2412950;
 bbsc_boss_killed_ms=0;assert(!ResolveBbscDefeatedBossLamp("boss killed"));
 bbsc_boss_killed_ms=99;assert(!ResolveBbscDefeatedBossLamp("boss killed"));
 bbsc_boss_killed_ms=200;
 ++bbsc_load_generation;assert(!ResolveBbscDefeatedBossLamp("boss killed"));
 --bbsc_load_generation;
 map=0x18000000;assert(!ResolveBbscDefeatedBossLamp("boss killed"));
 map=0x18010000;resolve=false;assert(!ResolveBbscDefeatedBossLamp("boss killed"));
 resolve=true;
 for(u32 other:{0x1d000000u,0x15000000u}){
  map=other;bars(500000);RememberBbscBossLamp();
  assert(bbsc_encounter_lamp==-1); // chalice/wrong map cannot reuse story lamp
 }
 map=0x18010000;bars(500000);RememberBbscBossLamp();
 bars(899000);RememberBbscBossLamp();assert(bbsc_encounter_lamp==-1); // no own lamp
}
'''
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    (path / 'test.cpp').write_text(code, encoding='utf-8')
    subprocess.run([os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe'),
                    '-std=c++20', str(path / 'test.cpp'), '-o', str(path / 'test.exe')], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')).parent)+os.pathsep+env.get('PATH','')
    result = subprocess.run([str(path / 'test.exe')], env=env)
    if negative:
        assert result.returncode != 0, 'Shared-first regression passed boss-lamp priority checks'
    else:
        result.check_returncode()
if negative:
    print('PASS negative control: shared-first regression FAILS boss-lamp priority')
    raise SystemExit(0)
print('Boss lamp: 19 original destinations/all phases, dead HUD, host/guest priority, '
      'ordinary death, stale kill/load/map, unavailable point and unknown/chalice guards PASS')
