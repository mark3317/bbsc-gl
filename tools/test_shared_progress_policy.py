"""Compile shared progress policy/live merge; no game or save files touched."""
from pathlib import Path
import re, subprocess, tempfile
s=(Path(__file__).resolve().parents[1]/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def fun(sig):
 start=s.index(sig+' {');at=s.index('{',start)+1;depth=1
 while depth:
  depth+=(s[at]=='{')-(s[at]=='}');at+=1
 return s[start:at]
arrays='\n'.join(re.search(r'constexpr std::array<[^;]+ '+n+r'\{.*?\};',s,re.S).group() for n in ('BbscNpcQuestFlags','BbscEncounterProgressFlags'))
code="""#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include "core/bbsc_chalice.h"
#include "core/bbsc_lamp_travel_data.h"
#include "core/bbsc_quest_event_rules.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u32=uint32_t;
constexpr size_t BbscWorldGroupBytes=125;
bool IsBbscPersonalMapEvent(u32 f) { return f==12410736; }
"""+arrays+'\n'+fun('bool IsBbscNpcQuestFlag(u32 flag)')+'\n'+fun('bool BbscSharedMapProgressAllowed(u32 flag)')+'\n'+fun('u8 BbscSharedProgressByte(u32 key, size_t byte, u8 incoming)')+'\n'+fun('void BbscMergeSharedProgressGroup(u32 key, u8* live, const u8* incoming)')+r"""
int main() {
 // Every ordinary/DLC headstone destination joins the same shared kind1
 // progress as doors and bosses; no 44-bit view can clear an existing lamp.
 for(const auto& destination:LampTravel::Returns) {
  const u32 point=destination.point;
  const u32 flag=10000000+(point/10000)*10000+7810+(point%10000-2950)*20;
  const auto byte=flag%1000/8;const auto bit=static_cast<u8>(0x80u>>(flag%8));
  std::array<u8,125> live{},host{};live[0]=0x80;host[byte]=bit;
  BbscMergeSharedProgressGroup(flag/1000,live.data(),host.data());
  assert((live[byte]&bit)&&live[0]==0x80);
  host.fill(0);BbscMergeSharedProgressGroup(flag/1000,live.data(),host.data());
  assert(live[byte]&bit); // older map-owner data never relocks host progress
 }
 for(u32 f:BbscEncounterProgressFlags) {
  assert(!BbscSharedMapProgressAllowed(f));
  std::array<u8,125> live{},incoming{};incoming[f%1000/8]=0x80u>>(f%8);
  BbscMergeSharedProgressGroup(f/1000,live.data(),incoming.data());
  assert(live[f%1000/8]==0); // a live merge must also exclude encounter state
 }
 for(u32 f:BbscNpcQuestFlags) assert(!BbscSharedMapProgressAllowed(f));
 for(u32 f:Chalice::LampUnlockFlags) {
  assert(!BbscSharedMapProgressAllowed(f) && BbscSharedMapProgressAllowed(f+1));
 }
 for(u32 f:{12414700u,12414702u,12415400u,12410736u}) assert(!BbscSharedMapProgressAllowed(f));
 for(u32 f:{12411700u,12411800u,13201802u,12410010u}) assert(BbscSharedMapProgressAllowed(f));
 for(u32 f=12410000;f<12420000;++f) {
  auto mask=static_cast<u8>(0x80u>>(f%8));
  auto incoming=BbscSharedProgressByte(f/1000,(f%1000)/8,mask);
  assert(incoming==(BbscSharedMapProgressAllowed(f)?mask:0));
  assert(static_cast<u8>(mask|incoming)==mask); // own bit is never erased
 }
}
"""
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.cpp').write_text(code,encoding='utf-8')
 subprocess.run(['g++','-std=c++20','-I'+str(Path(__file__).resolve().parents[1]/'emulator/src'),str(p/'t.cpp'),'-o',str(p/'t.exe')],check=True)
 subprocess.run([str(p/'t.exe')],check=True)
print('PASS shared progress live/home policy: all 44 base/DLC destinations, additive host/guest progress, encounter/NPC/ritual exclusions, every Central Yharnam bit')
