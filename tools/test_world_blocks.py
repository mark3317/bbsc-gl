"""Execute production native block coordinator and runtime on allocated memory.

No game process, saves, settings or game assets are changed. Native ABI probes
reuse the original 1.09 ELF contract when BBSC_TEST_EBOOT is supplied.
"""
from pathlib import Path
import os, shutil, subprocess, tempfile

ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include <algorithm>
#include <atomic>
#include <cassert>
#include <mutex>
#include <set>
#include <string_view>
#include "core/bbsc_world_blocks.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI
#define BBSC_TIMELINE(...)
bool BbscCombatTraceEnabled(){return false;}
void TraceBbscCombatPacket(std::string_view,uint32_t,uint32_t,std::span<const uint8_t>,bool){}
void TraceBbscCombatActor(std::string_view,uint64_t,int32_t,bool){}
void ObserveBbscNpcLifecycle(const char*,uint32_t){}
struct GuestRegisterSnapshot {u64 rax{},rbx{},rcx{},rdx{},rsi{},rdi{},rbp{},rsp{},r8{},r9{},r10{},r11{},r12{},r13{},r14{},r15{},rflags{};};
u64 image_base=0;constexpr u64 CandidateLocalStatePointerOffset=0x553E878;
std::array<u8,0x600> world{},block{},mapdata{},entries{},player{},actor{},control{},ownership{},damage{};
u64 addr(auto& a){return reinterpret_cast<u64>(a.data());}
template<class T>void put(auto& a,size_t at,T v){std::memcpy(a.data()+at,&v,sizeof(v));}
template<class T>T ReadValue(u64 a,size_t at){if(a==CandidateLocalStatePointerOffset)return T(addr(world));
 T v{};std::memcpy(&v,reinterpret_cast<void*>(a+at),sizeof(v));return v;}
bool ReadablePointer(u64 a,size_t){return a>0x10000;}
enum class MemoryProt{CpuWrite};bool HasMemoryAccess(u64 a,size_t s,MemoryProt){return ReadablePointer(a,s);}
int ownership_writes=0;
template<class T>void WriteValue(u64 a,size_t at,T v){if(a==addr(ownership))++ownership_writes;std::memcpy(reinterpret_cast<void*>(a+at),&v,sizeof(v));}
bool active=true,curtain=false,flags_ready=true,peer_ready=true;u32 self=11;u32 map=0x17000000;
namespace BbscMod{u32 RegisterOwnId(){return self;}}
std::atomic<u64> bbsc_world_native_load{1};std::atomic<bool> bbsc_world_load_pending{false},bbsc_reload_finish_pending{false};
std::mutex bbsc_world_presence_mutex;World::Presence bbsc_world_presence_local;World::PresenceBook bbsc_world_presence_book;
bool BbscIndependentActive(){return active;}bool BbscCurtainActive(){return curtain;}
bool BbscWorldFlagsReady(const World::Scope&){return flags_ready;}
bool BbscWorldNativePeerReady(u32){return peer_ready;}
u64 BbscWorldOwnershipWord(u64,u64){return addr(ownership);}
bool BbscWorldSceneReady(){return true;}
std::atomic<u32> bbsc_independent_role{2};
u64 BbscWorldDoll(u64){return 0;}
template<class Visit>void BbscWorldCharacters(u64,Visit visit){visit(addr(actor));}
u64 BbscWorldStateStandIn(s32 role){return role;}
u64 GetLocalPlayerCharacter(){return addr(player);}u32 GetCurrentPackedMap(){return map;}
std::set<u64> BbscWorldPlayers(u64){return {addr(player)};}
u32 BbscWorldPeer(u64 a){return a==100?22:0;}
u64 BbscWorldNativeMember(u32 peer){return peer==22?100:0;}
bool BbscWorldSendHere(u32 peer){return peer==22;}
bool BbscWorldPlayerSendHere(u32){return false;}
s64 now=10000;s64 SteadyNowMs(){return now;}
u8 bbsc_independent_send_skip=0;
struct BbscWorldIncoming{u32 sender;World::Control control;std::vector<u8> payload;};
std::vector<BbscWorldIncoming> sent;
void BbscWorldSend(World::Control c,std::span<const u8> bytes={}){sent.push_back({self,c,{bytes.begin(),bytes.end()}});}
void BbscWorldCoordinateBlocks();
std::vector<u8> native_record(u32 id,u8 bits=0){std::vector<u8> r(13);u32 size=13,count=2;
 std::memcpy(r.data(),&id,4);std::memcpy(r.data()+4,&size,4);std::memcpy(r.data()+8,&count,4);r[12]=bits;return r;}
int applies=0,serializes=0,admission_scans=0;u8 native_bits=0,last_applied=0;
s32 MockSerialize(u64 a,u8* out){assert(a==addr(block));++serializes;auto r=native_record(0x17000000,native_bits);std::memcpy(out,r.data(),r.size());return r.size();}
void MockApply(u64 a,const u8* r,const u8* bits){assert(a==addr(block)&&r==bits);++applies;last_applied=r[12];}
'''

MAIN=r'''
int main(){
 const World::WorldId worldid{11,99};World::Scope scope{worldid,0x17000000,{},0};
 const u32 a=0x17000000,b=0x17010000;
 World::BlockCoordinator coordinator;coordinator.Bind(worldid);
 auto resident=[](u32,const World::Scope&,u64){return true;};
 // Disjoint footprints: neither player must supply the other's missing block.
 assert(coordinator.Offer(scope,11,{1,1,0,true,false,native_record(a)}));
 assert(coordinator.Offer(scope,22,{1,1,0,true,false,native_record(b)}));
 coordinator.Elect(resident);
 auto get=[&](u32 id)->const World::BlockLease& {return coordinator.Blocks().at({World::BlockScope(scope,id),id}).lease;};
 assert(get(a).owner==11&&get(b).owner==22);
 // Two players on opposite sides of a map border still share ONE block lease.
 auto adjacent=scope;adjacent.map=0x17010000;
 assert(coordinator.Offer(adjacent,33,{1,1,0,true,false,native_record(a)}));
 coordinator.Elect(resident);assert(coordinator.Blocks().size()==2&&get(a).owner==11);
 auto epoch=get(a).epoch;
 // Dormant incumbent loses only THIS block, through a revoke/final-ack fence.
 assert(coordinator.Offer(scope,11,{1,2,epoch,false,false,native_record(a,1)}));
 assert(coordinator.Offer(scope,22,{1,2,0,true,false,native_record(a)}));
 coordinator.Elect(resident);assert(!get(a).owner&&get(a).retiring==11&&get(b).owner==22);
 const auto retiring_epoch=get(a).epoch;
 // Old-epoch data cannot acknowledge revocation or clear deaths.
 assert(coordinator.Offer(scope,11,{1,3,epoch,false,true,native_record(a)}));
 coordinator.Elect(resident);assert(get(a).retiring==11&&get(a).native[12]==1);
 assert(coordinator.Offer(scope,11,{1,4,retiring_epoch,false,true,native_record(a,3)}));
 coordinator.Elect(resident);assert(get(a).owner==22&&!get(a).retiring&&get(a).native[12]==3);
 assert(!coordinator.Offer(scope,11,{1,3,epoch,true,false,native_record(a)}));
 // A follower's private dead/alive table cannot alter authoritative history.
 assert(coordinator.Offer(scope,11,{1,5,get(a).epoch,true,false,native_record(a,0)}));
 assert(get(a).native[12]==3);
 // Streaming out retains history while the map is occupied, including final kills.
 assert(coordinator.Offer(scope,22,{1,6,get(a).epoch,false,false,native_record(a,3),false}));
 coordinator.Elect(resident);assert(get(a).native[12]==3);
 coordinator.ResetUnoccupied([](const World::Scope&){return true;});assert(get(a).native[12]==3);
 coordinator.ResetUnoccupied([](const World::Scope&){return false;});assert(!get(a).owner&&get(a).native[12]==0);
 assert(coordinator.Offer(scope,11,{2,7,0,true,false,native_record(a)}));coordinator.Elect(resident);
 assert(get(a).owner==11&&get(a).native[12]==0); // legitimate complete map reload
 // Identical generated geometry in different ritual incarnations never shares deaths.
 World::Scope cup{worldid,0x1d000000,{55,66,88,0},18},other_cup=cup;other_cup.ritual=19;
 assert(coordinator.Offer(cup,11,{3,10,0,true,false,native_record(0x1d010000,1)}));
 assert(coordinator.Offer(other_cup,22,{3,10,0,true,false,native_record(0x1d010000,0)}));
 coordinator.Elect(resident);
 assert(coordinator.Blocks().at({cup,0x1d010000}).lease.native[12]==1);
 assert(coordinator.Blocks().at({other_cup,0x1d010000}).lease.native[12]==0);
 auto wrong=scope;wrong.world.room++;assert(!coordinator.Offer(wrong,11,{2,8,0,true,false,native_record(a)}));
 auto malformed=native_record(a);malformed[4]=0;assert(!World::ValidNativeBlock(malformed));
 World::BlockWire wire;wire.block=a;auto encoded=World::EncodeBlock(wire,native_record(a));assert(World::DecodeBlock(encoded));
 for(size_t n=0;n<encoded.size();++n)assert(!World::DecodeBlock({encoded.data(),n}));
 encoded[19]=1;assert(!World::DecodeBlock(encoded));
 // Full production runtime: native capture -> offer -> host lease -> native apply.
 auto& p=bbsc_world_presence_local;p.world=worldid;p.phase=World::Phase::Playing;p.map=map;p.visit=1;p.sequence=1;
 p.capabilities=World::PresenceCapability|World::IndependentTravelCapability|World::OwnerCapability|World::BlockCapability;
 bbsc_world_presence_book.Bind(worldid,11);
 put(world,0x278,s32(3));put(world,0x280,u64(1));put(world,0x290,addr(block));
 put(block,0xB8,s32(2));put(block,0xC0,addr(entries));put(entries,0,addr(actor));
 put(actor,0x90,s32(77));put(player,0x90,s32(88));put(block,0x38,u32(1));put(player,0x218,u32(1));
 put(actor,0x18,addr(control));put(control,0x14,s32(4));
 TickBbscWorldBlocks();assert(BbscWorldBlocksActive()&&serializes==1&&applies==0);
 now+=100;TickBbscWorldBlocks();assert(applies==1&&BbscWorldBlockOwner(77)==11&&BbscWorldBlockOwnsAny());
 assert(BbscWorldAdmitBlocks(scope)&&applies==1); // once per block/epoch/load
 const int scans=admission_scans,serialized=serializes;
 for(int repeat=0;repeat<2000;++repeat)assert(BbscWorldAdmitBlocks(scope));
 assert(admission_scans==scans&&serializes==serialized&&applies==1);
 auto foreign=scope;++foreign.world.room;assert(!BbscWorldAdmitBlocks(foreign));
 GuestRegisterSnapshot auth;auth.rdi=addr(world);auth.rbx=addr(actor);
 put(damage,8,addr(actor));auth.r12=addr(damage); // native target, distinct from attacker RBX
 BbscWorldOwnership(0,&auth);assert(ReadValue<u16>(addr(ownership),0)==1); // map follower owns THIS block
 const int writes=ownership_writes;
 for(int repeat=0;repeat<2000;++repeat)BbscWorldOwnership(0,&auth);
 assert(ownership_writes==writes);
 put(control,0x14,s32(0));BbscWorldOwnership(0,&auth);
 assert(ReadValue<u16>(addr(ownership),0)==0xffff&&ownership_writes==writes+1);
 BbscWorldOwnership(0,&auth);assert(ownership_writes==writes+1);
 put(control,0x14,s32(4));BbscWorldOwnership(0,&auth);
 assert(ReadValue<u16>(addr(ownership),0)==1&&ownership_writes==writes+2);
 BbscWorldHpRound(0,&auth);assert(auth.rflags&(u64{1}<<6));
 BbscWorldHitState(0,&auth);assert(auth.rax==3);
 put(block,0xB8,s32(-1));BbscWorldCaptureBlocks(scope);
 assert(!BbscWorldAdmitBlocks(scope)&&BbscWorldBlockOwner(77)==0); // malformed is not an empty map
 put(block,0xB8,s32(2));BbscWorldCaptureBlocks(scope);assert(BbscWorldAdmitBlocks(scope));
 // Unauthorized lease, stale lease, and native count mismatch cannot admit.
 auto lease=sent.back();auto view=bbsc_world_block_views.at({scope,a});
 lease.control.owner=22;lease.control.epoch++;lease.control.sequence+=20;
 BbscWorldReceiveBlock({22,lease.control,lease.payload});assert(bbsc_world_block_views.at({scope,a}).lease.owner==11);
 wire.visit=p.visit;wire.origin_map=self;
 lease.payload=World::EncodeBlock(wire,native_record(a,1));
 BbscWorldReceiveBlock({11,lease.control,lease.payload});assert(BbscWorldBlockOwner(77)==0);
 peer_ready=false;assert(BbscWorldAdmitBlocks(scope)&&applies==2&&last_applied==1&&BbscWorldBlockOwner(77)==22);
 bbsc_independent_role=1;BbscWorldOwnership(0,&auth);assert(ReadValue<u16>(addr(ownership),0)==0xffff);
 const int follower_writes=ownership_writes;
 for(int repeat=0;repeat<2000;++repeat)BbscWorldOwnership(0,&auth);
 assert(ownership_writes==follower_writes);
 auth.rflags=0x40;BbscWorldHpRound(0,&auth);assert(!(auth.rflags&0x40));
 BbscWorldHitState(0,&auth);assert(auth.rax==6); // map owner follows another block owner
 ++bbsc_world_native_load;assert(BbscWorldBlockOwner(77)==0&&!BbscWorldAdmitBlocks(scope));
 --bbsc_world_native_load;
 GuestRegisterSnapshot r;std::array<u32,4> hp{77,200,88,300};
 r.rdx=5;r.rsi=100;r.rcx=reinterpret_cast<u64>(hp.data());r.r8=16;
 assert(BbscWorldBlockPacketSend(&r));assert(!bbsc_independent_send_skip);
 assert(ReadValue<u32>(r.rcx,0)==0xffffffffu&&ReadValue<u32>(r.rcx,8)==88);
 assert(hp[0]==77); // native producer buffer is untouched
 // Damage routes to this block's native member, rather than the map owner.
 std::array<u32,3> hit{77,1,2};r.rdx=0x15;r.rsi=200;r.rcx=reinterpret_cast<u64>(hit.data());r.r8=12;
 assert(BbscWorldBlockPacketSend(&r)&&r.rsi==100);
 // Receive drops stale/foreign HP while preserving data from the current owner.
 bbsc_world_block_hp_source=11;r.rax=8;r.r15=reinterpret_cast<u64>(hp.data());
 BbscWorldBlockHpReceived(0,&r);assert(hp[0]==0xffffffffu);
 hp[0]=77;bbsc_world_block_hp_source=22;BbscWorldBlockHpReceived(0,&r);assert(hp[0]==77);
 // Host metadata coordination remains available while its own game is loading.
 auto remote=p;remote.map=0x18000000;remote.visit=3;remote.sequence=2;
 assert(bbsc_world_presence_book.Hear(22,worldid,remote,now));p.phase=World::Phase::Loading;
 World::Control offer;offer.kind=World::ControlKind::BlockOffer;offer.scope=World::BlockScope(World::ScopeOf(remote),b);offer.owner=22;offer.sequence=100;
 wire.visit=remote.visit;wire.origin_map=remote.map;wire.block=b;wire.active=1;
 BbscWorldReceiveBlock({22,offer,World::EncodeBlock(wire,native_record(b))});
 assert(bbsc_world_block_views.at({offer.scope,b}).lease.owner==22);
 // A stale visit cannot keep simulating or publish the old map's history.
 remote.visit++;remote.sequence++;assert(bbsc_world_presence_book.Hear(22,worldid,remote,now));
 const auto before=sent.size();BbscWorldReceiveBlock({22,offer,World::EncodeBlock(wire,native_record(b,3))});
 assert(sent.size()==before);
 // Both players leave for Dream. The vacancy must invalidate EVERY cached
 // lease, including the one on the coordinator's own process.
 ++p.world.room;scope.world=p.world;bbsc_world_presence_book.Bind(p.world,11);
 p.phase=World::Phase::Playing;p.map=map;p.visit=20;
 ++bbsc_world_native_load;native_bits=1;now+=1100;TickBbscWorldBlocks();
 now+=1100;TickBbscWorldBlocks();
 const auto dead=bbsc_world_block_views.at({scope,a});assert(dead.lease.native[12]==1);
 auto stale=sent.back();
 p.phase=World::Phase::Loading;now+=1100;TickBbscWorldBlocks();
 auto vacant=bbsc_world_block_views.at({scope,a});
 assert(!vacant.lease.owner&&vacant.lease.native[12]==0&&vacant.lease.epoch>dead.lease.epoch);
 p.map=0x15000000;p.phase=World::Phase::Playing;now+=1100;TickBbscWorldBlocks();
 // First arrival starts clean before any historical-death application.
 p.map=map;p.visit++;++bbsc_world_native_load;native_bits=0;
 BbscWorldCaptureBlocks(scope);const auto applied_before=applies;
 assert(!BbscWorldAdmitBlocks(scope)&&applies==applied_before);
 now+=1100;TickBbscWorldBlocks();now+=1100;TickBbscWorldBlocks();
 assert(BbscWorldAdmitBlocks(scope)&&last_applied==0);
 BbscWorldReceiveBlock(stale);assert(bbsc_world_block_views.at({scope,a}).lease.native[12]==0);
 // A later load cannot reuse a cached occupied lease either: wait for a
 // coordinator publication received in this load; preserve deaths if occupied.
 ++p.visit;++bbsc_world_native_load;BbscWorldCaptureBlocks(scope);
 assert(!BbscWorldAdmitBlocks(scope));
 now+=1100;BbscWorldCoordinateBlocks();assert(!BbscWorldAdmitBlocks(scope));
 now+=1100;TickBbscWorldBlocks();assert(BbscWorldAdmitBlocks(scope));
}
'''

def main():
    source=(ROOT/'emulator/src/core/bbsc_world_blocks.inc').read_text(encoding='utf-8')
    loop='for(auto& [id,item]:bbsc_world_block_local){'
    assert source.count(loop)==1
    source=source.replace(loop,'++admission_scans;'+loop)
    for actual,mock in [('reinterpret_cast<Serialize>(image_base+0x0190E750)','MockSerialize'),
                        ('reinterpret_cast<Apply>(image_base+0x0190E8B0)','MockApply')]:
        assert source.count(actual)==1
        source=source.replace(actual,mock)
    compiler=shutil.which('clang++') or 'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-blocks-') as tmp:
        cpp=Path(tmp)/'blocks.cpp';exe=Path(tmp)/'blocks.exe'
        import test_independent_native as authority
        callbacks=''.join(authority.function(signature) for signature in [
            'void PS4_SYSV_ABI BbscWorldOwnership(u64,const GuestRegisterSnapshot* regs)',
            'void PS4_SYSV_ABI BbscWorldHpRound(u64,const GuestRegisterSnapshot* regs)',
            'void PS4_SYSV_ABI BbscWorldHitState(u64,const GuestRegisterSnapshot* regs)'])
        cpp.write_text(PREFIX+source+callbacks+MAIN,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-Wall','-Wextra','-Werror','-Wno-unused-local-typedef','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],env=env,check=True)
    print('PASS production native blocks: disjoint coverage, revoke/final-ack, native death history, streaming/reload, scope/visit/epoch fences, native HP filtering and host-loading coordination')
    if os.environ.get('BBSC_TEST_EBOOT'):
        import test_world_native_initial as native
        import test_independent_native as authority
        native.original_contract(os.environ['BBSC_TEST_EBOOT'])
        authority.check_original_sites(Path(os.environ['BBSC_TEST_EBOOT']))

if __name__=='__main__':main()
