"""Run the production Dream restoration decision against native join/load roles.

Allocated fixture state only; no real game process, journal or save is opened.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
start = source.index('void TickBbscDreamStateRestore() {')
end = source.index('{', start) + 1
depth = 1
while depth:
    depth += (source[end] == '{') - (source[end] == '}')
    end += 1

code = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
constexpr u32 BbscDreamStateMap=0x15000000;
struct {u64 held=1;s64 applied_ms=0;} bbsc_dream_own;
s64 now=100000;int session=4,restores=0;u32 map=BbscDreamStateMap;
u8 global[0x1600]{};
u64 GetGlobalState(){return reinterpret_cast<u64>(global);}
bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64 p,size_t off){T v;std::memcpy(&v,reinterpret_cast<void*>(p+off),sizeof(v));return v;}
s64 SteadyNowMs(){return now;}
s32 GetSessionState(){return session;}
u32 GetCurrentPackedMap(){return map;}
// Reproduces the old predicate: native join/load can say "own world" while
// the network session still says joining/guest. Personal loot is independent.
bool BbscGuestLootActive(){return (session==4||session==6)&&!global[0x1592];}
void RestoreBbscOwnDreamState(const char*){++restores;bbsc_dream_own.held=0;}
''' + source[start:end] + r'''
int main(){
 global[0x1592]=1; // native local-world loader role, not a session departure
 for(int state:{4,6}){
  session=state;assert(!BbscGuestLootActive());
  for(int tick=0;tick<3;++tick){now+=2000;TickBbscDreamStateRestore();}
  assert(restores==0&&bbsc_dream_own.held==1);
 }
 // Travelling/loading retains the borrowed view until the destination is known.
 map=0x18010000;global[8]=1;now+=2000;TickBbscDreamStateRestore();assert(!restores);
 global[8]=0;bbsc_dream_own.applied_ms=now;now+=2000;
 TickBbscDreamStateRestore();assert(!restores);
 // Once outside the Dream, only its personal services are restored as before.
 now+=30000;TickBbscDreamStateRestore();assert(restores==1&&!bbsc_dream_own.held);
 // An actual session departure in the Dream still restores personal state.
 map=BbscDreamStateMap;session=0;bbsc_dream_own.held=1;now+=2000;
 TickBbscDreamStateRestore();assert(restores==2&&!bbsc_dream_own.held);
}
'''
code = '#include <initializer_list>\n' + code

def main():
    compiler = os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-dream-restore-') as tmp:
        cpp = Path(tmp) / 'dream.cpp'
        exe = Path(tmp) / 'dream.exe'
        cpp.write_text(code, encoding='utf-8')
        subprocess.run([compiler, '-std=c++20', str(cpp), '-o', str(exe)], check=True)
        env = os.environ.copy()
        env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
        subprocess.run([str(exe)], check=True, env=env)
    print('PASS production Dream restore: joining/guest local-world role, loading, travel grace, real departure')

if __name__ == '__main__':
    main()
