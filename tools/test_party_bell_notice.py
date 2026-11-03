"""Execute the production bell-notice tick without the game."""
from pathlib import Path
import os,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a=s.index('void TickBbscPartyBellNotice() {');b=s.index('\n}\n',a)+3
prefix=r'''
#include <cassert>
#include <cstdint>
#include <string_view>
using u64=std::uint64_t;using s64=std::int64_t;using u8=std::uint8_t;
u64 released=0,generation=0,bbsc_notice_serial=0,player=1; s64 now=1000;
bool quit=false,title=false,loading=false,ready=true;int attempts=0,shown=0;
namespace BbscMod {u64 PartyBellGeneration(){return generation;}u64 PartyBellReleasedGeneration(){return released;}}
bool BbscQuitInProgress(){return quit;}bool BbscReturningToTitle(){return title;}
u64 GetGlobalState(){return 1;}bool ReadablePointer(u64,size_t){return true;}
template<class T>T ReadValue(u64,size_t){return T(loading);}
u64 GetLocalPlayerCharacter(){return player;}s64 SteadyNowMs(){return now;}
const char16_t* BbscL(const char16_t* en,const char16_t*){return en;}
void BbscAnnounce(const char16_t* text,std::string_view what){
 assert((what=="party bell started"&&std::u16string_view(text)==u"The chime of a beckoning bell resonates across the world") ||
        (what=="party bell stopped"&&std::u16string_view(text)==u"The Beckoning Bell has fallen silent"));++attempts;if(ready){++shown;++bbsc_notice_serial;}
}
'''
main=r'''
int main(){
 TickBbscPartyBellNotice();assert(!shown); // unknown/idle never announces
 generation=1;loading=true;TickBbscPartyBellNotice();assert(!attempts);
 loading=false;ready=false;TickBbscPartyBellNotice();assert(attempts==1&&!shown);
 TickBbscPartyBellNotice();assert(attempts==1); // bounded retry
 now+=500;ready=true;TickBbscPartyBellNotice();assert(shown==1);
 for(int i=0;i<1000;++i){now+=500;TickBbscPartyBellNotice();}assert(shown==1);
 generation=0;TickBbscPartyBellNotice();generation=1;TickBbscPartyBellNotice();assert(shown==1);
 generation=2;quit=true;TickBbscPartyBellNotice();assert(shown==1);
 quit=false;title=true;TickBbscPartyBellNotice();assert(shown==1);
 title=false;player=0;TickBbscPartyBellNotice();assert(shown==1);
 player=1;TickBbscPartyBellNotice();assert(shown==2);
 generation=1;now+=500;TickBbscPartyBellNotice();assert(shown==2);
 generation=0;released=1;TickBbscPartyBellNotice();assert(shown==2); // stale release
 released=2;loading=true;TickBbscPartyBellNotice();assert(shown==2);
 loading=false;TickBbscPartyBellNotice();assert(shown==3);
 for(int i=0;i<20;++i){now+=500;TickBbscPartyBellNotice();}assert(shown==3);
 released=0;TickBbscPartyBellNotice();released=2;TickBbscPartyBellNotice();assert(shown==3);
 generation=3;released=0;TickBbscPartyBellNotice();assert(shown==4);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-bell-notice-') as tmp:
 cpp,exe=Path(tmp)/'notice.cpp',Path(tmp)/'notice.exe'
 cpp.write_text(prefix+s[a:b]+main,encoding='utf-8')
 subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=10,env=dict(os.environ,PATH='C:/msys64/clang64/bin;'+os.environ['PATH']))
print('PASS: once per generation, idle/network loss, load/title/quit, banner readiness retry')
