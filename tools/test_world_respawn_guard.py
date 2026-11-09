"""Independent runtime lamp changes must not be pulled back by legacy follow guard."""
from pathlib import Path
import os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
start=source.index('constexpr s32 BbscLampAux =')
end=source.index('void TickBbscRespawnPointWatch() {',start)
code=r'''
#include <cassert>
#include <cstdint>
#include <mutex>
#include <string_view>
using u64=uint64_t;using s64=int64_t;using u8=uint8_t;using u32=uint32_t;using s32=int32_t;
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
bool independent=true,loading=false,home=true,writable=true;
int session=0,hp=594,writes=0,slot=2;
constexpr s64 HomeLamp=(s64{101163}<<32)|2412950;
constexpr s64 GuestLamp=(s64{101200}<<32)|2102950;
s64 latest=HomeLamp;
constexpr u32 BbscDreamStateMap=0x15000000;
int GetSessionState(){return session;}bool BbscIndependentActive(){return independent;}
int GetLocalCharacterType(){return 1;}int GetLocalPlayerType(){return 1;}bool IsInvaderType(int){return false;}
u64 GetGlobalState(){return 1;}bool ReadablePointer(u64,size_t){return true;}
template<class T>T ReadValue(u64,size_t off){
 return static_cast<T>(off==8?loading:off==0x1592?home:off==0x1490?slot:off==0x1528?latest:0);
}
template<class T>bool WriteValue(u64,size_t,T value){
 if(!writable)return false;
 ++writes;latest=value;return true;
}
u64 GetLocalPlayerCharacter(){return 1;}int GetCharacterHp(u64){return hp;}
u32 GetCurrentPackedMap(){return BbscDreamStateMap;}u32 BbscMapArea(u32 map){return map>>24;}
u32 BbscLampPointMap(s32 point){return point/10000==210?BbscDreamStateMap:0x18010000;}
std::mutex bbsc_follow_mutex;struct Follow{s64 received_ms=100;int lamp_point=2412951;}bbsc_follow_latest;
'''+source[start:end]+r'''
int main(){
 CaptureBbscGuestRespawnPoint();
 assert(bbsc_guest_respawn_held&&bbsc_guest_respawn_own==HomeLamp);
 assert(!GuardBbscGuestRespawnPoint(1,latest)&&bbsc_guest_respawn_held);
 session=4;
 assert(!GuardBbscGuestRespawnPoint(1,latest)&&bbsc_guest_respawn_held);
 loading=true;latest=GuestLamp;
 CaptureBbscGuestRespawnPoint(); // duplicate accept cannot recapture a borrowed lamp
 assert(!GuardBbscGuestRespawnPoint(1,latest)&&bbsc_guest_respawn_own==HomeLamp);
 session=6;home=false;loading=false;
 assert(!GuardBbscGuestRespawnPoint(1,latest)&&writes==0);
 hp=0;assert(!GuardBbscGuestRespawnPoint(1,latest)&&writes==0);
 session=7;assert(!GuardBbscGuestRespawnPoint(1,latest)&&bbsc_guest_respawn_held);
 session=0;assert(!GuardBbscGuestRespawnPoint(1,latest)&&bbsc_guest_respawn_held);
 writable=false;ReleaseBbscGuestRespawnPoint("not writable");
 assert(writes==0&&bbsc_guest_respawn_held);
 writable=true;
 ReleaseBbscGuestRespawnPoint("return home map choice");
 assert(writes==1&&latest==HomeLamp&&!bbsc_guest_respawn_held);
 ReleaseBbscGuestRespawnPoint("duplicate");assert(writes==1);

 // A cancelled accept while still at home neither rewrites the native lamp
 // nor blocks a fresh accept. A later join restores that fresh backup.
 home=true;CaptureBbscGuestRespawnPoint();
 session=4;assert(!GuardBbscGuestRespawnPoint(1,latest));
 session=0;latest=HomeLamp+1;
 assert(!GuardBbscGuestRespawnPoint(1,latest)&&writes==1&&!bbsc_guest_respawn_held);
 CaptureBbscGuestRespawnPoint();assert(bbsc_guest_respawn_own==HomeLamp+1);
 session=6;home=false;latest=GuestLamp;hp=594;
 assert(!GuardBbscGuestRespawnPoint(1,latest));
 independent=false;assert(GuardBbscGuestRespawnPoint(1,latest)&&latest==HomeLamp+1);
 independent=true;session=0;home=true;latest=GuestLamp;
 assert(GuardBbscGuestRespawnPoint(1,latest)&&latest==HomeLamp+1&&!bbsc_guest_respawn_held);

 CaptureBbscGuestRespawnPoint();session=6;home=false;latest=GuestLamp;
 assert(!GuardBbscGuestRespawnPoint(1,latest));
 ++slot;session=0;home=true;
 assert(!GuardBbscGuestRespawnPoint(1,latest)&&latest==GuestLamp&&!bbsc_guest_respawn_held);
}
'''
compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
with tempfile.TemporaryDirectory(prefix='bbsc-world-respawn-') as tmp:
    cpp=Path(tmp)/'guard.cpp';exe=Path(tmp)/'guard.exe';cpp.write_text(code,encoding='utf-8')
    subprocess.run([compiler,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],check=True,env=env)
print('PASS production guest lamp: capture, connecting and loading, duplicate accept, departure, cancelled join, legacy mode and slot fence')
