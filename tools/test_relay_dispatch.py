"""Execute the actual shared relay/P2P dispatcher, including the mount/register collision."""
from pathlib import Path
import os, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
src=(root/'emulator/mod/bbsc_relay.cpp').read_text(encoding='utf-8')
constants=src[src.index('constexpr u16 DefaultRelayPort'):src.index('std::atomic',src.index('constexpr u16 DefaultRelayPort'))]
# Keep only protocol declarations and the wire follow structure.
constants=constants[:constants.index('static_assert(sizeof(FollowPacket)')]+ 'static_assert(sizeof(FollowPacket)==0x22);\n'
dispatch=src[src.index('void Dispatch('):src.index('DWORD WINAPI RelayThread')]
prefix=r'''
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include "core/bbsc_chalice.h"
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using s32=int32_t;
int state=6,book=0,mount=0,kill=0,left=0,follow=0,other=0;
u32 own_id=2,host=1,key=1;int peers=0;
std::atomic<bool> logged_old_sender{false};
void Log(const char*){}
u32 SessionKey(){return key;}
namespace Core::Bloodborne {
int GetBbscRelaySessionState(){return state;} u32 GetBbscRelayHost(){return host;}
void OnBbscPeerLeft(u32,bool){++left;}
void OnBbscChaliceMountPacket(const void*,size_t){++mount;}
void OnBbscHostFollowPacket(u32,float,float,float,float,u32,s32,const Chalice::Key&){++follow;}
void NoteBbscRelayHost(u32,u32,float,float,float){}
void OnBbscLifePacket(u32,u8,u32,bool){++other;}
void OnBbscScalePacket(const u16*){++other;}
void OnBbscPvpPacket(u8,u8){++other;}
void OnBbscProgressPacket(const u32*,size_t){++other;}
void OnBbscKeyItemsPacket(const void*,size_t){++other;}
void OnBbscCutscenePacket(const void*,size_t){++other;}
void OnBbscWorldFlagsPacket(const void*,u32){++other;}
}
namespace Libraries::Np::NpSignaling {constexpr u8 kSignalingBbscWorldFlagsType=0x22;}
namespace BbscMod {
void ForgetSessionRegister(u32){}
void ReceiveSessionRegister(u32,u32,const void*,u32){++book;}
void ReceiveRegisterKill(u32,u32,const void*,u32){++kill;}
void OnHostPlacement(const std::string&,u32){}
void OnAimedHostPlacement(long long,const std::string&,u32){}
}
'''
main=r'''
std::vector<u8> packet(u8 type,size_t size,u32 sender=1,u32 session=1){
 std::vector<u8> p(13+size);std::memcpy(p.data(),"SHAD",4);p[4]=EnvelopeType;
 std::memcpy(p.data()+5,&sender,4);std::memcpy(p.data()+9,&session,4);
 std::memcpy(p.data()+13,"SHAD",4);p[17]=type;return p;
}
int main(){
 using namespace Core::Bloodborne;
 for(bool server:{false,true}){
  Dispatch(packet(Protocol::Register,33),server);
  Dispatch(packet(Chalice::MountPacketType,Chalice::MountPacketSize),server);
  Dispatch(packet(Protocol::RegisterKill,38),server);
 }
 assert(book==2&&mount==2&&kill==2);
 for(auto type:{Protocol::Register,Protocol::RegisterKill,Protocol::ChaliceMount}){
  Dispatch(packet(type,136,3,3)); // unrelated room
  Dispatch(packet(type,136,own_id,1)); // reflected own packet
 }
 assert(book==2&&mount==2&&kill==2);
 state=3;Dispatch(packet(Protocol::ChaliceMount,136));assert(mount==2);
 state=6;Dispatch(packet(Protocol::ChaliceMount,136,3,1));assert(mount==2);
 Dispatch(packet(FollowType,sizeof(FollowPacket)));assert(follow==1);
 Dispatch(packet(SessionLeaveType,6));assert(left==0);
 Dispatch(packet(SessionLeaveType,5));assert(left==1);
 Dispatch({PeersType,9},false);assert(peers==0);
 Dispatch({PeersType,9},true);assert(peers==9);
 auto p=packet(Protocol::ChaliceMount,136);
 for(size_t i=0;i<18;++i)Dispatch(std::vector<u8>(p.begin(),p.begin()+i));
 assert(mount==2);
}
'''
with tempfile.TemporaryDirectory() as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe'
 cpp.write_text(prefix+constants+dispatch+main,encoding='utf-8')
 subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-I'+str(root/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('Production dispatcher: mount/register/kill coexist, roles, sessions, server-only control, truncation: PASS')
