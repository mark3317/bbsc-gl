"""Execute production native population snapshot and worker JSON construction."""
import os
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
s=(root/'emulator/mod/bbsc_party.cpp').read_text(encoding='utf-8')
observe=s[s.index('void PartyObserve('):s.index('void PartyMaintain()')]
maintain=s[s.index('void PartyMaintain()'):s.index('    const std::string result=Call(')]
prefix=r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <string>
using ULONGLONG=std::uint64_t;
ULONGLONG now=1000;
ULONGLONG GetTickCount64(){return now;}
bool enabled=true;
bool PartyEnabled(){return enabled;}
bool ExclusiveNative(){return true;}
std::atomic<std::uint64_t> native{1u<<8};
std::atomic<unsigned> cancel_sequence{0};
std::atomic<bool> title_pending{false};
std::string payload;
std::string AimedPlacementAcknowledgment(){return "1,18000000,0,0,0,0,23";}
'''
main=r'''
bool has(const char* value){return payload.find(value)!=std::string::npos;}
int main(){
 PartyMaintain();assert(has("\"fresh\":false"));
 assert(has("\"aimed_placement\":\"1,18000000,0,0,0,0,23\""));
 now+=250;PartyObserve(3,false,true,3,true);PartyMaintain();
 assert(has("\"state\":3")&&has("\"bell\":true")&&has("\"members\":3")&&has("\"alive\":true")&&has("\"fresh\":true"));
 now+=250;PartyObserve(0,false,false,1,true);PartyMaintain();
 assert(has("\"state\":0")&&has("\"bell\":false")&&has("\"members\":1")&&has("\"fresh\":true"));
 now+=1500;PartyMaintain();assert(has("\"fresh\":false"));
 now+=250;PartyObserve(0,true,false,-1,false);PartyMaintain();
 assert(has("\"members\":0")&&has("\"loading\":true")&&has("\"alive\":false"));
 enabled=false;now+=2000;PartyObserve(3,false,false,1,true);enabled=true;PartyMaintain();
 assert(has("\"fresh\":false")&&has("\"members\":0"));
}
'''
with tempfile.TemporaryDirectory() as tmp:
    cpp=Path(tmp)/'population.cpp';exe=Path(tmp)/'population.exe'
    cpp.write_text(prefix+observe+maintain+'    payload=body;\n}\n'+main,encoding='utf-8')
    subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('Production native population, fresh atomic snapshot, JSON and stalled-frame expiry PASS')
