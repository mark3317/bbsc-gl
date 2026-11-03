"""Compile the production tick observation block: disabled mode does no game reads."""
import os,subprocess,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
start=s.index('    if (site.offset == BbscGameTickOffset) {')
start=s.index('#ifdef BBSC_MOD',start)+len('#ifdef BBSC_MOD')
end=s.index('#endif',start);block=s[start:end]
prefix=r"""
#include <cassert>
#include <cstdint>
using u64=uint64_t;using u8=uint8_t;
int reads=0;
u64 GetGlobalState(){++reads;return 0x10000;}
int GetSessionState(){++reads;return 0;}
bool ReadablePointer(u64,int){++reads;return true;}
template<class T>T ReadValue(u64,int){++reads;return 0;}
u64 BbscLocalEffectNode(int){++reads;return 0;}
namespace BbscMod {
bool enabled=false;int observations=0;
bool PartyEnabled(){return enabled;}
void PartyObserve(int,bool,bool){++observations;}
}
void tick(){
"""
code=prefix+block+r"""
}
int main(){
 for(int i=0;i<1000;++i)tick();
 assert(reads==0 && BbscMod::observations==0);
 BbscMod::enabled=true;tick();
 assert(reads>0 && BbscMod::observations==1);
}
"""
with tempfile.TemporaryDirectory() as tmp:
 cpp=Path(tmp)/'tick.cpp';exe=Path(tmp)/'tick.exe';cpp.write_text(code)
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('Production party tick: legacy0 reads, enabled observation PASS')
