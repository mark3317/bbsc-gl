"""ORIGINAL host receive/list/prune/arbitration/grant and guest grant application.

No remote PlayerIns or host-side NPC block is present. Network delivery and
allocator services are fixture boundaries; the native request/grant control
flow and production membership resolver/Windows rewrites are executed.
"""
from pathlib import Path
import os, struct, subprocess, tempfile
import test_independent_native as native

ROOT=Path(__file__).resolve().parents[1]
data=Path(os.environ['BBSC_TEST_EBOOT']).read_bytes()
ph=struct.unpack_from('<Q',data,32)[0]
sz,count=struct.unpack_from('<HH',data,54)
segments=[struct.unpack_from('<II6Q',data,ph+i*sz) for i in range(count)]
def read(a,n):
    for t,_,o,v,_,fs,_,_ in segments:
        if t==1 and v<=a and a+n<=v+fs:return data[o+a-v:o+a-v+n]
    raise AssertionError(hex(a))

prefix=r'''
#include <windows.h>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <deque>
#include <map>
#include <mutex>
#include <vector>
#include "xbyak/xbyak.h"
#include "core/cpu_patches.h"
#include "core/bbsc_world_control.h"
#include "core/bbsc_native_ai_admission.h"
#include "bbsc_register.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;
u64 image_base=0;constexpr u64 MatchingStatePointerOffset=0x5540290,CandidateLocalStatePointerOffset=0x553e878;
u64 addr(auto& a){return (u64)a.data();}
void put(u64 p,size_t o,auto v){memcpy((void*)(p+o),&v,sizeof(v));}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
bool ReadablePointer(u64 p,size_t){return p>0x10000;}
bool IsValidMemberId(u64 p){return p>0x10000&&ReadValue<u64>(p,0)>0x10000;}
std::mutex bbsc_world_presence_mutex;World::Presence bbsc_world_presence_local;
bool active=true;bool BbscIndependentActive(){return active;}
#define BBSC_TIMELINE(...)
int request_resolves=0,grant_resolves=0,retain_resolves=0;
BbscMod::RegisterIdentity registered_identity{};u32 registered_peer=22;
namespace BbscMod {
u64 EbootAddress(){return image_base;}void LogPlain(const char* s){puts(s);}
u32 RegisterOwnId(){return 11;}
u32 FindSessionRegisterPeer(const RegisterIdentity& id){
 return !memcmp(&id,&registered_identity,sizeof(id))?registered_peer:0;
}
}
'''
a=native.NATIVE.index('struct BbscNpcMemberBinding')
b=native.NATIVE.index('World::WorldId BbscWorldNpcRoom()',a)
production=''.join(native.function(s) for s in [
 'BbscMod::RegisterIdentity BbscWorldIdentity(u64 member_id)',
 'u32 BbscWorldPeer(u64 member_id)',
 'u64 BbscWorldNativeMember(u32 peer)'])+native.NATIVE[a:b]+''.join(native.function(s) for s in [
 'World::WorldId BbscWorldNpcRoom()', 'bool BbscWorldNpcHost()',
 'void BbscWorldNpcForgetPeer(u32 peer,bool host)', 'bool BbscWorldNpcRoomKeyMode()',
 'u32 PS4_SYSV_ABI BbscWorldNpcRequestMember(u64 member,u32 bytes)',
 'u64 PS4_SYSV_ABI BbscWorldNpcGrantMember(u32 key)',
 'u64 PS4_SYSV_ABI BbscWorldNpcRetainMember(u32 key)'])
production=production.replace('u32 PS4_SYSV_ABI BbscWorldNpcRequestMember(u64 member,u32 bytes) {',
    'u32 PS4_SYSV_ABI BbscWorldNpcRequestMember(u64 member,u32 bytes) {++request_resolves;')
production=production.replace('u64 PS4_SYSV_ABI BbscWorldNpcGrantMember(u32 key) {',
    'u64 PS4_SYSV_ABI BbscWorldNpcGrantMember(u32 key) {++grant_resolves;')
production=production.replace('u64 PS4_SYSV_ABI BbscWorldNpcRetainMember(u32 key) {',
    'u64 PS4_SYSV_ABI BbscWorldNpcRetainMember(u32 key) {++retain_resolves;')

body=r'''
u64 allocator_addr=0,guest_entry=0,last_target=0,guest_endpoint=0,host_endpoint=0;int sends=0,received=0,queue_calls=0;
std::deque<std::vector<u32>> requests,grants;
u64 PS4_SYSV_ABI Allocate(u64,u64 n,u64){return (u64)calloc(1,n);}
void PS4_SYSV_ABI Free(u64,u64 p){free((void*)p);}
void PS4_SYSV_ABI AllocatorFlags(u64 p,u64,u64){put(p,0,u8(0x20));}
u64 PS4_SYSV_ABI GetAllocator(u64){return allocator_addr;}
u64 PS4_SYSV_ABI Fill(u64 p,int v,size_t n){memset((void*)p,v,n);return p;}
bool native_online=true;
bool PS4_SYSV_ABI Online(u64){return native_online;}
bool PS4_SYSV_ABI ValidId(u64 p){return p&&ReadValue<u64>(p,0);}
int PS4_SYSV_ABI ReceiveQueue(u64 endpoint,u32 channel,u64 out,u32 capacity){
 ++queue_calls;
 assert(capacity==0x1000);
 auto* queue=channel==0x16&&endpoint==guest_endpoint?&requests:
             channel==0x17&&endpoint==host_endpoint?&grants:nullptr;
 if(!queue||queue->empty())return 0;
 auto bytes=queue->front();queue->pop_front();assert(bytes.size()*4<=capacity);
 memcpy((void*)out,bytes.data(),bytes.size()*4);if(channel==0x16)++received;return int(bytes.size()*4);
}
int PS4_SYSV_ABI SendMember(u64,u64 member,u32 channel,u64 packet,u32 size){
 assert(ReadValue<u64>(member,0)==ReadValue<u64>(guest_entry,0)&&channel==0x17&&size>=4&&size<=0x1000);
 last_target=member;++sends;grants.emplace_back((u32*)packet,(u32*)(packet+size));return 1;
}
bool PS4_SYSV_ABI CompareId(u64 a,u64 b){return ReadValue<u64>(a,0)&&ReadValue<u64>(a,0)==ReadValue<u64>(b,0);}
void jump(u8* at,u64 target){at[0]=0x48;at[1]=0xb8;memcpy(at+2,&target,8);at[10]=0xff;at[11]=0xe0;}
struct GrantReturn:Xbyak::CodeGenerator{
 GrantReturn(){using namespace Xbyak::util;add(rsp,0x108);pop(rbx);pop(r12);pop(r13);pop(r14);pop(r15);pop(rbp);ret();ready();}
};
struct PositionSender:Xbyak::CodeGenerator{
 PositionSender(u64 image){using namespace Xbyak::util;
  push(rbp);mov(rbp,rsp);push(rbx);push(r12);push(r13);push(r14);push(r15);sub(rsp,0x208);
  mov(r15,rdi);mov(r12,rsi);mov(rax,rdx);xor_(edx,edx);mov(edi,4<<11);xor_(ebx,ebx);
  mov(qword[rbp-0x108],rcx);mov(r11,image+0x18ee829);jmp(r11);
  u64 finish=(u64)getCurr();mov(eax,ebx);add(rsp,0x208);pop(r15);pop(r14);pop(r13);pop(r12);pop(rbx);pop(rbp);ret();ready();
  jump((u8*)(image+0x18ee91a),finish);
 }
};
using Intake=void PS4_SYSV_ABI (*)(u64);
using Grant=void PS4_SYSV_ABI (*)(u64,u32,float);
u64 local_module=0;int local_updates=0,remote_updates=0;
bool PS4_SYSV_ABI Special(u64){return false;}
bool PS4_SYSV_ABI NetworkPlayer(u64){return true;}
void PS4_SYSV_ABI Bind(u64,u64,u64){}
void PS4_SYSV_ABI Update(u64 m,u64){if(m==local_module)++local_updates;else ++remote_updates;}
int main(){
 SetErrorMode(SEM_NOGPFAULTERRORBOX|SEM_FAILCRITICALERRORS);
 AddVectoredExceptionHandler(1,[](EXCEPTION_POINTERS* e)->LONG{fprintf(stderr,"fault offset=%llx rax=%llx rdi=%llx\n",e->ContextRecord->Rip-image_base,e->ContextRecord->Rax,e->ContextRecord->Rdi);return EXCEPTION_CONTINUE_SEARCH;});
 auto* base=(u8*)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(base);image_base=(u64)base;
 LOADS
 const auto install=[&](u64 offset,auto bytes,auto emitter,u64 callback){assert(Core::InstallGuestCodeRewrite(base+offset,bytes,emitter,image_base,callback));};
 if(!NEG_TRANSPORT)install(0x1789274,NativeAi::ReceiveChannels,NativeAi::EmitReceiveChannels,0);
 install(0x18f0880,NativeAi::EmptySelf,NativeAi::EmitEmptySelf,0);
 install(0x18f09d1,NativeAi::EmptyPeer,NativeAi::EmitEmptyPeer,0);
 if(!NEG_REQUEST)install(0x18f092c,NativeAi::RequestMember,NativeAi::EmitRequestMember,(u64)BbscWorldNpcRequestMember);
 if(!NEG_RETAIN)install(0x18ed1b6,NativeAi::RetainMember,NativeAi::EmitRetainMember,(u64)BbscWorldNpcRetainMember);
 if(!NEG_GRANT)install(0x18ed470,NativeAi::GrantMember,NativeAi::EmitGrantMember,(u64)BbscWorldNpcGrantMember);
 std::array<u8,0x80> allocator{},allocator_vt{};allocator_addr=addr(allocator);
 put(allocator_addr,0,addr(allocator_vt));put(addr(allocator_vt),0x58,(u64)Allocate);put(addr(allocator_vt),0x70,(u64)Free);put(addr(allocator_vt),0x20,(u64)AllocatorFlags);
 *(u64*)(base+0x5540438)=allocator_addr;*(u64*)(base+0x5540408)=allocator_addr;
 u64 cookie=123;*(u64*)(base+0x53e3be0)=(u64)&cookie;
 jump(base+0x207b720,(u64)GetAllocator);jump(base+0x2bbe688,(u64)Fill);
 // Execute real ReceiveFromMember AND ReceiveFromHost. Only the actual queue
 // consumption and authenticated native-session services are fixture boundaries.
 jump(base+0x17910f0,(u64)ReceiveQueue);jump(base+0xc8f570,(u64)Online);
 jump(base+0xca1400,(u64)ValidId);jump(base+0x17894e0,(u64)SendMember);jump(base+0xca1c70,(u64)CompareId);
 GrantReturn finish; jump(base+0x18ed68f,(u64)finish.getCode()); // unrelated native object channels follow this stage
 std::array<u8,0xb00> world{};std::array<u8,0x200> manager{},config{};
 std::array<u8,0x800> host_sync{},client_sync{};std::array<u8,0x18> list_head{};
 std::array<u8,0x500> self{};std::array<u8,0x38*5> player_slots{};std::array<u8,16> player_list{};
 std::array<std::array<u8,0x80>,2> identities{};std::array<u8,64> members{};
 put(addr(world),8,addr(config));put(addr(config),0x18,u32(17));
 put(addr(world),0x30,u32(5));put(addr(world),0x38,addr(player_slots));put(addr(player_slots),0,addr(self));
 put(addr(self),8,u32(0x10044000));put(addr(world),0x60,addr(self));
 put(addr(player_list),0,u32(5));put(addr(player_list),8,addr(player_slots));put(addr(world),0x850+17*8,addr(player_list));
 put(addr(world),0xa40,addr(host_sync));*(u64*)(base+0x553e878)=addr(world);
 *(u64*)(base+MatchingStatePointerOffset)=addr(manager);put(addr(manager),0x124,u32(3));
 put(addr(manager),0xf8,addr(members));put(addr(manager),0x100,addr(members)+64);
 for(int i=0;i<2;++i){put(addr(identities[i]),0,image_base+0x52c5c00);put(addr(identities[i]),0x30,u32(7));put(addr(identities[i]),0x34,u16(i+1));put(addr(members),i*32,addr(identities[i]));}
 memcpy(identities[1].data()+0x36,"GUEST",6);guest_entry=addr(members)+32;
 std::array<u8,0x80> net{},net_root{},host_node{},guest_node{},host_ep{},guest_ep{};
 *(u64*)(base+0x553d6d0)=addr(net);put(addr(net),0x28,addr(net_root));
 put(addr(net_root),0,addr(host_node));put(addr(host_node),0,addr(guest_node));put(addr(guest_node),0,addr(net_root));
 host_endpoint=addr(host_ep);guest_endpoint=addr(guest_ep);
 put(addr(host_node),0x10,host_endpoint);put(addr(guest_node),0x10,guest_endpoint);
 put(host_endpoint,8,addr(identities[0]));put(guest_endpoint,8,addr(identities[1]));
 put(addr(manager),0xd0,addr(identities[0]));
 registered_identity=BbscWorldIdentity(guest_entry);bbsc_world_presence_local.world={11,99};
 put(addr(host_sync),0x5f0,addr(list_head));put(addr(list_head),0,addr(list_head));put(addr(list_head),8,addr(list_head));
 put(addr(host_sync),0x600,allocator_addr);put(addr(host_sync),8,u32(17)); // NO host NPC table for client block4
 auto intake=(Intake)(base+0x18f0780);auto grant=(Grant)(base+0x18eceb0);
 auto submit=[&](std::vector<u32> packet){requests.push_back(std::move(packet));intake(addr(host_sync));};
 // Real transport: no remote actor, both ownership channels reach only their
 // matching native endpoint. All OTHER channels keep exactly their old policy.
 using Receive=u32 PS4_SYSV_ABI (*)(u64,u64,u32,u64,u32);
 auto receive=(Receive)(base+0x1789200);std::array<u32,16> received_words{};
 requests.push_back({1,123});grants.push_back({1,456});
 if(NEG_TRANSPORT){assert(receive(addr(net),guest_entry,NEG_GRANT_TRANSPORT?0x17:0x16,(u64)received_words.data(),0x1000)==8);}
 for(u32 channel=0;channel<=0x44;++channel){
  auto nr=requests.size(),ng=grants.size();int before_queue=queue_calls;
  auto bytes=receive(addr(net),guest_entry,channel,(u64)received_words.data(),0x1000);
  const bool old_actor_free=(channel>=7&&channel<=0x42&&((0x80000000004067Bull>>(channel-7))&1))||
      (channel>=0x1a&&channel<=0x2a&&!((0x9e00u>>(channel-0x1a))&1));
  assert(queue_calls-before_queue==int(old_actor_free||channel==0x16||channel==0x17));
  if(channel==0x16){assert(bytes==8&&received_words[1]==123);requests.push_back({1,123});}
  else assert(bytes==0&&requests.size()==nr&&grants.size()==ng);
 }
 assert(receive(addr(net),addr(members),0x17,(u64)received_words.data(),0x1000)==8&&received_words[1]==456);
 std::array<u8,32> unknown_identity{};put(addr(unknown_identity),0,addr(identities[0])+1);
 assert(!receive(addr(net),addr(unknown_identity),0x16,(u64)received_words.data(),0x1000));
 native_online=false;assert(!receive(addr(net),guest_entry,0x16,(u64)received_words.data(),0x1000));native_online=true;
 requests.clear();grants.clear();received=0;
 auto list_for=[&](u32 key){u64 root=ReadValue<u64>(addr(host_sync),0x5f0),node=ReadValue<u64>(root,0);
  for(int i=0;i<8&&node!=root;++i){u64 obj=ReadValue<u64>(node,0x10);if(ReadValue<u32>(obj,0)==key)return obj;node=ReadValue<u64>(node,0);}return u64(0);};
 // Invalid length/count, foreign member pointer, self and non-host cannot bind.
 put(image_base+0x5570090,0,u32(0));assert(BbscWorldNpcRequestMember(guest_entry,3)==0);
 put(image_base+0x5570090,0,u32(5));assert(BbscWorldNpcRequestMember(guest_entry,4)==0);
 put(image_base+0x5570090,0,u32(0xffffffff));assert(BbscWorldNpcRequestMember(guest_entry,8)==0);
 assert(BbscWorldNpcRequestMember(guest_entry,0x1004)==0);
 put(image_base+0x5570090,0,u32(0));assert(BbscWorldNpcRequestMember(addr(members),4)==0);
 std::array<u8,32> fake{};put(addr(fake),0,addr(identities[1]));assert(BbscWorldNpcRequestMember(addr(fake),4)==0);
 put(addr(manager),0x124,u32(6));assert(!BbscWorldNpcRequestMember(guest_entry,4));put(addr(manager),0x124,u32(3));
 assert(bbsc_npc_members.empty());
 active=false;assert(BbscWorldNpcRequestMember(guest_entry,4)==1);active=true;
 int idle_request=request_resolves,idle_grant=grant_resolves,idle_retain=retain_resolves;
 intake(addr(host_sync));grant(addr(host_sync),0,0.016f);
 assert(request_resolves==idle_request&&grant_resolves==idle_grant&&retain_resolves==idle_retain&&grants.empty());
 // Full ORIGINAL intake: room member is valid, remote PlayerIns slots are NULL.
 submit({1,(u32(123)<<16)|(4<<11)});assert(received==1);
 assert(bbsc_npc_peer_keys.contains(22));u32 key=bbsc_npc_peer_keys.at(22);
 assert((key&0x80000000)&&list_for(key)&&ReadValue<u64>(list_for(key),0x18)==1);
 assert(BbscWorldNpcGrantMember(key)==guest_entry);
 // Near-player / actor recreation preserves exactly the same network key.
 std::array<u8,0x500> remote_player{},player_vt{};put(addr(remote_player),8,u32(0x10044001));
 put(addr(remote_player),0,addr(player_vt));put(addr(player_vt),0x1a8,(u64)NetworkPlayer);
 put(addr(remote_player),0x3d8,addr(identities[1]));
 put(addr(player_slots),0x38,addr(remote_player));submit({1,(u32(123)<<16)|(4<<11)});
 assert(bbsc_npc_peer_keys.at(22)==key&&bbsc_npc_members.size()==1);
 active=false;submit({1,(u32(123)<<16)|(4<<11)});assert(bbsc_npc_peer_keys.at(22)==key);active=true;
 // Reproduce a positive PlayerIns-keyed list left over from the initial join.
 using FindList=u64 PS4_SYSV_ABI (*)(u64,u32);using Assign=void PS4_SYSV_ABI (*)(u64,u32,u64);
 auto find_list=(FindList)(base+0x18f0b70);auto assign=(Assign)(base+0x1a6c590);
 u32 old_claim=(u32(0x7fff)<<16)|(4<<11);u64 old_alias=find_list(addr(host_sync),0x10044001);
 assign(old_alias,1,(u64)&old_claim);assert(list_for(0x10044001));
 // Full ORIGINAL host prune, merge, native payload construction and member send.
 active=false;grant(addr(host_sync),0,0.016f);active=true;
 assert(sends==1&&grants.size()==1&&list_for(key)&&!list_for(0x10044001)&&last_target==guest_entry);
 put(addr(player_slots),0x38,u64(0));
 grants.clear();sends=0;grant(addr(host_sync),0,0.016f);
 assert(sends==1&&grants.size()==1&&last_target==guest_entry); // positive grant with no remote actor
 assert(grants.front().size()==2&&grants.front()[0]==1&&(grants.front()[1]&0xffff)==(4<<11));
 // Full ORIGINAL guest receives channel17 and updates its real NPC grant table.
 std::array<u8,0x50> table{};std::array<u16,1> words{0xffff};
 put(addr(client_sync),8,u32(17));put(addr(client_sync),0x10+4*8,addr(table));put(addr(client_sync),0x200,u32(1));put(addr(client_sync),0x208,addr(table));
 put(addr(table),0x10,u32(1));put(addr(table),0x18,(u64)words.data());
 // The live failing guest had24 queued old grants. Native receive must drain
 // that backlog, then apply the latest grant for the newly loaded map.
 for(int i=0;i<24;++i)grants.push_front({1,31<<11});
 put(addr(manager),0x124,u32(6));grant(addr(client_sync),0,0.016f);assert(words[0]==1&&grants.empty());
 // Original EnemyIns uses that very grant for its local brain/model binding.
 alignas(16) std::array<u8,0x500> chr{},vt{},model{},modules{},transform{},local{},remote{},module_vt{};
 put(addr(world),0xa40,addr(client_sync));put(addr(chr),0,addr(vt));put(addr(vt),0x4c8,(u64)Special);put(addr(chr),0x90,u32(4<<11));
 put(addr(chr),0x58,addr(model));put(addr(model),8,addr(chr));put(addr(chr),0x3b0,addr(modules));put(addr(modules),0x68,addr(transform));
 put(addr(chr),0x3b8,addr(local));put(addr(chr),0x3c0,addr(remote));put(addr(local),0,addr(module_vt));put(addr(remote),0,addr(module_vt));
 put(addr(module_vt),0x38,(u64)Bind);put(addr(module_vt),0x18,(u64)Update);local_module=addr(local);
 using Select=void PS4_SYSV_ABI (*)(u64,u8);auto select=(Select)(base+0x18e6540);
 select(addr(chr),0);assert(local_updates==1&&remote_updates==0&&ReadValue<u64>(addr(model),0x80)==addr(local));
 // The very grant received above admits ORIGINAL XYZ packet production too.
 std::array<u8,16> npc_list{};std::array<u8,0x38> npc_slot{};std::array<float,6> pose{1,2,3,0,0,0};u16 pose_flags=2;
 put(addr(table),8,addr(npc_list));put(addr(npc_list),0,u32(1));put(addr(npc_list),8,addr(npc_slot));put(addr(npc_slot),0,addr(chr));
 put(addr(table),0x20,addr(pose));put(addr(table),0x38,(u64)&pose_flags);
 PositionSender position(image_base);using SendPosition=int PS4_SYSV_ABI (*)(u64,u64,u64,u64);
 auto send_position=position.getCode<SendPosition>();
 assert(send_position(addr(table),addr(client_sync),(u64)words.data(),(u64)&pose_flags)==1);
 assert(ReadValue<u32>(addr(client_sync),0x6c8)==(4<<11));
 // Empty request releases authority through the SAME ORIGINAL host/guest flow.
 put(addr(manager),0x124,u32(3));put(addr(world),0xa40,addr(host_sync));submit({0});
 assert(ReadValue<u64>(list_for(key),0x18)==0);grant(addr(host_sync),0,0.016f);
 put(addr(manager),0x124,u32(6));grant(addr(client_sync),0,0.016f);assert(words[0]==0xffff);
 select(addr(chr),0);assert(remote_updates==1);
 pose_flags=2;assert(send_position(addr(table),addr(client_sync),(u64)words.data(),(u64)&pose_flags)==0);
 // Membership resolution cost depends on participants, not NPC count.
 put(addr(manager),0x124,u32(3));std::vector<u32> many{64};
 for(u32 i=0;i<64;++i)many.push_back((u32(123)<<16)|(4<<11)|i);
 submit(many);int before=grant_resolves;grant(addr(host_sync),0,0.016f);
 assert(grant_resolves-before==2&&grants.size()==1&&grants.front().at(0)==64);grants.clear();
 // A departed key is pruned even if its positive request list is still queued.
 put(addr(manager),0x124,u32(3));submit({1,(u32(123)<<16)|(4<<11)});
 BbscWorldNpcForgetPeer(22,false);assert(!BbscWorldNpcGrantMember(key));
 grant(addr(host_sync),0,0.016f);assert(!list_for(key)&&grants.empty());
 // Rejoin / changed full identity cannot inherit the departed list or key.
 put(addr(identities[1]),0x34,u16(3));registered_identity=BbscWorldIdentity(guest_entry);
 submit({1,(u32(456)<<16)|(4<<11)});u32 next=bbsc_npc_peer_keys.at(22);assert(next!=key&&!BbscWorldNpcGrantMember(key));
 grant(addr(host_sync),0,0.016f);assert(grants.size()==1&&BbscWorldNpcGrantMember(next)==guest_entry);grants.clear();
 put(addr(manager),0x100,addr(members)+32);assert(!BbscWorldNpcGrantMember(next));
 grant(addr(host_sync),0,0.016f);assert(grants.empty()); // original one-member early exit
 BbscWorldNpcForgetPeer(22,false);put(addr(manager),0x100,addr(members)+64);
 submit({0});grant(addr(host_sync),0,0.016f);assert(!list_for(next));grants.clear();
 bbsc_world_presence_local.world.room=100;
 assert(!BbscWorldNpcGrantMember(next));submit({0});assert(bbsc_npc_peer_keys.at(22)!=next);
 BbscWorldNpcForgetPeer(0,true);assert(bbsc_npc_members.empty()&&bbsc_npc_peer_keys.empty());
 bbsc_npc_member_sequence=0x7ffffffe;put(image_base+0x5570090,0,u32(0));
 assert(BbscWorldNpcRequestMember(guest_entry,4)==0); // never wrap/reuse an old key
 puts("PASS full ORIGINAL transport ReceiveFromMember/ReceiveFromHost + cross-map request/list/prune/merge/grant/guest apply/EnemyIns AI/XYZ; no remote PlayerIns; all other channels/session/endpoint gates retained");
}
'''
spans=[(0x18f0780,0x18f0c90+0x40),(0x18eceb0,0x18ed68f),
       (0x1a6c420,0x1a6c51a),(0x1a6c590,0x1a6c6c2),(0x1a6c700,0x1a6c823),
       (0x18e6540,0x18e66ed),(0x18ee829,0x18ee91a),
       (0x178fa90,0x178fcc3),(0x49271c8,0x49271f0),
       (0x1789200,0x1789380),(0x17893e0,0x17894e0)]
loads=[]
for i,(start,end) in enumerate(spans):
    loads.append(f'const u8 c{i}[]={{'+','.join(map(str,read(start,end-start)))+f'}};memcpy(base+{start},c{i},sizeof(c{i}));')
body=body.replace('LOADS','\n'.join(loads))
negative=os.environ.get('BBSC_NPC_MEMBER_NEGATIVE','')
body=body.replace('NEG_GRANT_TRANSPORT','true' if negative=='transport-grant' else 'false')
for name,kind in [('NEG_REQUEST','request'),('NEG_RETAIN','retain'),('NEG_GRANT','grant'),('NEG_TRANSPORT','transport')]:
    body=body.replace(name,'true' if negative==kind or name=='NEG_TRANSPORT' and negative=='transport-grant' else 'false')
compiler='C:/msys64/clang64/bin/clang++.exe'
env=dict(os.environ,PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH',''))
with tempfile.TemporaryDirectory(prefix='bbsc-npc-member-') as tmp:
    cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe'
    cpp.write_text(prefix+production+body,encoding='utf8')
    subprocess.run([compiler,'-std=c++20','-O2','-Wall','-Wextra','-Werror','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
                    '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/mod'),'-I',str(ROOT/'emulator/externals/xbyak'),
                    str(cpp),str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],env=env,check=True)
    result=subprocess.run([str(exe)],env=env,timeout=20)
    if negative:
        assert result.returncode!=0,'Missing cross-map native boundary was not detected'
        print('PASS negative control:',negative)
    else:result.check_returncode()
