"""Execute the native-leave policy; active sessions must keep their persistence patches."""
from pathlib import Path
import os
import subprocess
import tempfile
SOURCE = Path('emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')

def function(signature):
    begin = SOURCE.index(signature + ' {')
    at = SOURCE.index('{', begin) + 1
    depth = 1
    while depth:
        depth += (SOURCE[at] == '{') - (SOURCE[at] == '}')
        at += 1
    return SOURCE[begin:at]

code = r'''
#include <cassert>
#include <string_view>
using s64=long long;
int state=0, suspended=0;
bool patches=true;
s64 bbsc_persistence_restore_at_ms=0;
int GetSessionState() { return state; }
void SuspendBbscPersistence(std::string_view) {
    ++suspended; patches=false; bbsc_persistence_restore_at_ms=1000;
}
'''
code += function('void SuspendBbscPersistenceOnce(std::string_view why)')
code += function('void ReleaseBbscNativeLeavingSession()')
code += r'''
int main() {
    for(int s : {-1,0,1,2,3,4,5,6}) {
        state=s; ReleaseBbscNativeLeavingSession();
        assert(patches && suspended==0);
    }
    state=7;
    // Native OwnWorldStep can be the only remaining callback during the load.
    for(int i=0;i<4000;++i) ReleaseBbscNativeLeavingSession();
    assert(!patches && suspended==1);
    state=0; ReleaseBbscNativeLeavingSession(); assert(suspended==1);
    bbsc_persistence_restore_at_ms=0; patches=true; state=3;
    ReleaseBbscNativeLeavingSession(); assert(patches);
    state=7; ReleaseBbscNativeLeavingSession(); assert(!patches && suspended==2);
}
'''
assert 'ReleaseBbscNativeLeavingSession();' in function('void TickBbscSessionExit(bool peer_work)')
assert 'site.offset == 0x01941C20' in function('bool BbscFunctionalTraceSite(const TraceSite& site)')
trace = SOURCE[SOURCE.index('void PS4_SYSV_ABI TraceEntry('):]
own_step = trace[trace.index('if (site.offset == 0x01941C20)'):trace.index('if (site.offset == ItemUsableResultOffset)')]
assert 'ReleaseBbscNativeLeavingSession();' in own_step

with tempfile.TemporaryDirectory(prefix='bbsc-leave-') as tmp:
    cpp, exe = Path(tmp)/'test.cpp', Path(tmp)/'test.exe'
    cpp.write_text(code,encoding='utf-8')
    subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=5)
print('PASS: native state 7 releases once, active/joining sessions preserved, native load-step fallback retained')
