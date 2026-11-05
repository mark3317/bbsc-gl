"""Execute the actual shared relay/P2P dispatcher, including the mount/register collision."""
from pathlib import Path
import os, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
src=(root/'emulator/mod/bbsc_relay.cpp').read_text(encoding='utf-8')
constants=src[src.index('constexpr u16 DefaultRelayPort'):src.index('std::atomic',src.index('constexpr u16 DefaultRelayPort'))]
# Keep only protocol declarations and the wire follow structure.
constants=constants[:constants.index('static_assert(sizeof(FollowPacket)')]+ 'static_assert(sizeof(FollowPacket)==0x22);\n'
start=src.index('void Dispatch(')
opening=src.index('{',start);end=opening+1;depth=1
while depth:
 depth+=(src[end]=='{')-(src[end]=='}');end+=1
dispatch=src[start:end]
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
#include "core/bbsc_follow.h"
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using s32=int32_t;
int state=6,book=0,mount=0,kill=0,left=0,follow=0,other=0,pvp=0,pvp_kind=-1,pvp_on=-1;
int world_presence=0;u32 world_sender=0,world_session=0;
u32 own_id=2,host=1,key=1;int peers=0;
std::atomic<bool> logged_old_sender{false};
void Log(const std::string&){}
u32 SessionKey(){return key;}
namespace Core::Bloodborne {
int GetBbscRelaySessionState(){return state;} u32 GetBbscRelayHost(){return host;}
void OnBbscPeerLeft(u32,bool){++left;}
void OnBbscExplicitSessionLeave(u32,bool){++left;}
void OnBbscChaliceMountPacket(const void*,size_t){++mount;}
void OnBbscWorldPresencePacket(u32 sender,u32 session,const void*,size_t){
 ++world_presence;world_sender=sender;world_session=session;
}
Follow::Arrival last_arrival;
void OnBbscHostFollowPacket(u32,float,float,float,float,u32,s32,const Chalice::Key&,const Follow::Arrival& a){++follow;last_arrival=a;}
void NoteBbscRelayHost(u32,u32,float,float,float){}
int life_packets=0;bool visible=false;
void OnBbscLifePacket(u32,u8,u32,bool,bool shown){++life_packets;visible=shown;}
void OnBbscScalePacket(const u16*){++other;}
void OnBbscPvpPacket(u8 kind,u8 on){++pvp;pvp_kind=kind;pvp_on=on;}
void OnBbscProgressPacket(const u32*,size_t){++other;}
void OnBbscKeyItemsPacket(const void*,size_t){++other;}
int key_requests=0;
void OnBbscKeyItemsRequest(u32,const void*,size_t){++key_requests;}
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
 auto life=packet(Protocol::Life,15);life.back()=1;Dispatch(life);
 assert(life_packets==1&&visible);
 Dispatch(packet(Protocol::Life,14));assert(life_packets==2&&!visible);
 Dispatch(packet(Protocol::Life,15,3,3));assert(life_packets==2);
 // The presence bridge uses exactly the shared session envelope on both paths.
 for(bool server:{false,true}){
  Dispatch(packet(Protocol::WorldPresence,88,3,1),server);
  assert(world_sender==3&&world_session==1);
 }
 assert(world_presence==2);
 Dispatch(packet(Protocol::WorldPresence,88,3,3));
 Dispatch(packet(Protocol::WorldPresence,88,own_id,1));
 assert(world_presence==2);
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
 FollowPacket fp;fp.packed_map=0x18000000;
 Follow::Arrival arrival{3,fp.packed_map,1,2,3,4};
 auto wire=Follow::Encode(fp,{},arrival);auto extended=packet(FollowType,wire.size());
 std::memcpy(extended.data()+13,wire.data(),wire.size());
 Dispatch(extended);assert(follow==2&&last_arrival.generation==3&&last_arrival.map==fp.packed_map);
 auto wrong_follow=extended;u32 stranger=7;std::memcpy(wrong_follow.data()+9,&stranger,4);
 Dispatch(wrong_follow);assert(follow==2);
 extended.pop_back();Dispatch(extended);assert(follow==2);
 Dispatch(packet(SessionLeaveType,6));assert(left==0);
 Dispatch(packet(SessionLeaveType,5));assert(left==1);
 Dispatch({PeersType,9},false);assert(peers==0);
 Dispatch({PeersType,9},true);assert(peers==9);
 // PvP host confirmations and guest requests take the same validated native
 // dispatcher on relay and P2P. Other rooms/guest-authored host state stay out.
 for(bool server:{false,true}){
  own_id=2;host=key=1;state=6;
  auto on=packet(PvpType,11);on[18]=0;on[19]=1;
  Dispatch(on,server);assert(pvp_kind==0&&pvp_on==1);
  int before=pvp;
  Dispatch(packet(PvpType,10),server);assert(pvp==before);
  auto wrong=on;u32 stranger=3;std::memcpy(wrong.data()+5,&stranger,4);
  Dispatch(wrong,server);assert(pvp==before);
  wrong=on;std::memcpy(wrong.data()+9,&stranger,4);
  Dispatch(wrong,server);assert(pvp==before);
  own_id=key=1;state=3;
  auto request=packet(PvpType,11,2,1);request[18]=1;request[19]=1;
  Dispatch(request,server);assert(pvp==before+1&&pvp_kind==1&&pvp_on==1);
  before=pvp;wrong=request;std::memcpy(wrong.data()+9,&stranger,4);
  Dispatch(wrong,server);assert(pvp==before);
 }
 // Retired key snapshots/requests have no dispatch path in any session role.
 for(bool server:{false,true})for(int role:{3,4,6}){
  state=role;own_id=role==3?1:2;key=host=1;int before=other,requests=key_requests;
  Dispatch(packet(Protocol::KeyItems,13),server);
  Dispatch(packet(Protocol::KeyItems,21),server);
  Dispatch(packet(Protocol::KeyItemsRequest,13,2,1),server);
  assert(other==before&&key_requests==requests);
 }
 own_id=2;host=key=1;state=6;
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
print('Production dispatcher: mount/register/kill, PvP host state and guest requests, roles, sessions, server-only control, truncation: PASS')
