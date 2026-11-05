"""Independent runtime lamp changes must not be pulled back by legacy follow guard."""
from pathlib import Path
import os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
start=source.index('bool GuardBbscGuestRespawnPoint(u64 global, s64 value) {')
p=source.index('{',start)+1;depth=1
while depth:depth+=(source[p]=='{')-(source[p]=='}');p+=1
code=r'''
#include <cassert>
#include <cstdint>
#include <mutex>
#include <string_view>
using u64=uint64_t;using s64=int64_t;using u8=uint8_t;using u32=uint32_t;using s32=int32_t;
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
bool independent=true;int session=6,hp=594,writes=0; s64 latest=0;
s64 bbsc_guest_respawn_own=2412950;bool bbsc_guest_respawn_held=true,bbsc_guest_respawn_released=false;
constexpr s32 BbscLampAux=101163,BbscDreamLampAux=101200;constexpr u32 BbscDreamStateMap=0x15000000;
int GetSessionState(){return session;}bool BbscIndependentActive(){return independent;}
int GetLocalCharacterType(){return 1;}int GetLocalPlayerType(){return 1;}bool IsInvaderType(int){return false;}
template<class T>T ReadValue(u64,size_t){return T(0);}
template<class T>void WriteValue(u64,size_t,T value){++writes;latest=value;}
u64 GetLocalPlayerCharacter(){return 1;}int GetCharacterHp(u64){return hp;}
u32 GetCurrentPackedMap(){return BbscDreamStateMap;}u32 BbscMapArea(u32 map){return map>>24;}
u32 BbscLampPointMap(s32 point){return point/10000==210?BbscDreamStateMap:0x18010000;}
std::mutex bbsc_follow_mutex;struct Follow{s64 received_ms=100;int lamp_point=2412951;}bbsc_follow_latest;
'''+source[start:p]+r'''
int main(){
 assert(!GuardBbscGuestRespawnPoint(1,2102950)&&writes==0&&bbsc_guest_respawn_own==2412950);
 hp=0;assert(!GuardBbscGuestRespawnPoint(1,2102950)&&writes==0); // isolated death stays local
 independent=false;hp=594;assert(GuardBbscGuestRespawnPoint(1,2102950)&&latest==2412950);
 independent=true;session=0;assert(GuardBbscGuestRespawnPoint(1,2102950)&&latest==2412950&&!bbsc_guest_respawn_held);
}
'''
compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
with tempfile.TemporaryDirectory(prefix='bbsc-world-respawn-') as tmp:
    cpp=Path(tmp)/'guard.cpp';exe=Path(tmp)/'guard.exe';cpp.write_text(code,encoding='utf-8')
    subprocess.run([compiler,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],check=True,env=env)
print('PASS production runtime lamp guard: independent alive/dead, legacy mode, original home point retained')
