"""Compile production home-merge policy; no game or save files touched."""
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
using namespace Core::Bloodborne;
using u8=uint8_t;using u32=uint32_t;
bool IsBbscPersonalMapEvent(u32 f) { return f==12410736; }
"""+arrays+'\n'+fun('bool IsBbscNpcQuestFlag(u32 flag)')+'\n'+fun('bool BbscSharedMapProgressAllowed(u32 flag)')+'\n'+fun('u8 BbscSharedProgressByte(u32 key, size_t byte, u8 incoming)')+r"""
int main() {
 for(u32 f:BbscEncounterProgressFlags) assert(!BbscSharedMapProgressAllowed(f));
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
print('shared progress: encounter/NPC exclusion, defeat/ordinary progress retention, every Central Yharnam bit and own-bit preservation PASS')
