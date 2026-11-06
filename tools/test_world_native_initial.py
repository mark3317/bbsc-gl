"""Production native CHR admission on allocated memory; no game/save access.

Native transport and historical-death handler are mocked. Original 1.09 bytes
independently establish the native serializer, bitmap meaning and handler ABI.
"""
from pathlib import Path
import os, shutil, struct, subprocess, tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'emulator/src/core/bbsc_world_native_initial.inc').read_text(encoding='utf-8')
PREFIX=r'''
#include <atomic>
#include <cassert>
#include <deque>
#include <mutex>
#include <set>
#include "core/bbsc_world_control.h"
#include "core/bbsc_world_native_initial.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI
#define BBSC_TIMELINE(...)
u64 image_base=0;constexpr u64 CandidateLocalStatePointerOffset=0x553E878;
std::array<u8,0x400> world{},block{},block2{},mapdata{},mapdata2{},entries{},net{};
u64 addr(auto& a){return reinterpret_cast<u64>(a.data());}
template<class T>void put(auto& a,size_t off,T v){std::memcpy(a.data()+off,&v,sizeof(v));}
template<class T>T ReadValue(u64 a,size_t off){
 if(a==CandidateLocalStatePointerOffset)return T(addr(world));
 if(a==0x553D6D0)return T(addr(net));
 T v;std::memcpy(&v,reinterpret_cast<void*>(a+off),sizeof(v));return v;
}
bool ReadablePointer(u64 p,size_t){return p>0x10000;}
bool active=true,here=true,scene=true,send_ok=true;u32 self=11;u64 native_member=200;
bool BbscIndependentActive(){return active;}
bool BbscWorldPeerHere(u32){return here;}
bool BbscWorldSceneReady(){return scene;}
u64 BbscWorldNativeMember(u32){return native_member;}
namespace BbscMod{u32 RegisterOwnId(){return self;}}
std::atomic<u64> bbsc_world_native_load{1};s64 now=10000;s64 SteadyNowMs(){return now;}
std::mutex bbsc_world_presence_mutex;World::Presence bbsc_world_presence_local;
World::PresenceBook bbsc_world_presence_book;World::OwnerBook bbsc_independent_owners;
struct BbscWorldIncoming{u32 sender;World::Control control;std::vector<u8> payload;};
std::vector<BbscWorldIncoming> sent;void BbscWorldSend(World::Control c,std::span<const u8> p={}){sent.push_back({self,c,{p.begin(),p.end()}});}
thread_local u32 bbsc_world_initial_sending=0;thread_local u64 bbsc_world_initial_fingerprint=0;
std::vector<u8> packet;std::deque<std::vector<u8>> received;int applied=0,native_sends=0;
void MockApply(u64 b,const u8* header,const u8* bits){assert(header==bits);assert(b==addr(block)||b==addr(block2));++applied;}
bool MockSend(u64 unused,u64 member){assert(!unused&&member==native_member);++native_sends;
 assert(bbsc_world_initial_sending);bbsc_world_initial_fingerprint=World::NativeInitialFingerprint(packet);return send_ok;}
s32 MockReceive(u64 n,u64 member,u32 ch,u8* bytes,u32 cap){assert(n==addr(net)&&member==native_member&&ch==0x11);
 if(received.empty())return 0;auto p=received.front();received.pop_front();assert(p.size()<=cap);std::memcpy(bytes,p.data(),p.size());return p.size();}
'''
MAIN=r'''
void word(std::vector<u8>& v,u32 x){auto n=v.size();v.resize(n+4);std::memcpy(v.data()+n,&x,4);}
std::vector<u8> make(bool second=false){
 std::vector<u8> chr;word(chr,0x43485220);word(chr,0x15091700);
 word(chr,0x18000000);word(chr,13);word(chr,2);chr.push_back(1); // enemy0 dead, enemy1 alive
 if(second){word(chr,0x18010000);word(chr,13);word(chr,2);chr.push_back(2);}
 word(chr,0xFFFFFFFF);word(chr,0);word(chr,0);
 std::vector<u8> out;word(out,0);word(out,0);word(out,chr.size());out.insert(out.end(),chr.begin(),chr.end());return out;
}
int main(){
 packet=make();assert(World::NativeInitialCharacters(packet)->size()==1);
 for(size_t n=0;n<packet.size();++n)assert(!World::NativeInitialCharacters({packet.data(),n}));
 auto bad=packet;bad.push_back(0);assert(!World::NativeInitialCharacters(bad));
 bad=packet;bad[12]=0;assert(!World::NativeInitialCharacters(bad));
 bad=packet;bad[24]=255;assert(!World::NativeInitialCharacters(bad));
 put(world,0x278,s32(3));put(world,0x280,u64(1));put(world,0x290,addr(block));
 put(block,8,addr(mapdata));put(mapdata,8,u32(0x18000000));put(block,0xB8,s32(2));put(block,0xC0,addr(entries));
 assert(BbscWorldApplyNativeInitial(packet)&&applied==1);
 put(block,0xB8,s32(3));assert(!BbscWorldApplyNativeInitial(packet)&&applied==1);put(block,0xB8,s32(2));
 put(world,0x278,s32(4));put(world,0x298,u64(1));put(world,0x2A8,addr(block2));
 put(block2,8,addr(mapdata2));put(mapdata2,8,u32(0x18010000));put(block2,0xB8,s32(3));put(block2,0xC0,addr(entries));
 assert(!BbscWorldApplyNativeInitial(make(true))&&applied==1); // atomic preflight
 put(world,0x278,s32(3));
 auto& p=bbsc_world_presence_local;p.world={11,99};p.phase=World::Phase::Playing;p.map=0x18000000;p.visit=1;p.sequence=1;
 bbsc_world_presence_book.Bind(p.world,11);auto other=p;assert(bbsc_world_presence_book.Hear(22,p.world,other,now));
 auto scope=World::ScopeOf(p);bbsc_independent_owners.Bind(p.world);
 World::Control lease;lease.scope=scope;lease.owner=22;lease.epoch=7;assert(bbsc_independent_owners.Take(11,lease,now));
 assert(!BbscWorldNativeInitialReady(scope,22,7)&&sent.size()==1);auto request=sent.back().control;
 assert(request.kind==World::ControlKind::NativeInitialRequest&&request.owner==11);
 assert(!BbscWorldNativeInitialReady(scope,22,7)&&sent.size()==1);
 auto reply=request;reply.kind=World::ControlKind::NativeInitialReady;reply.owner=22;
 u64 hash=World::NativeInitialFingerprint(packet);std::vector<u8> digest(8);std::memcpy(digest.data(),&hash,8);
 BbscWorldNativeInitialControl({33,reply,digest});assert(bbsc_world_initial.fingerprints.empty());
 auto stale=reply;stale.sequence++;BbscWorldNativeInitialControl({22,stale,digest});assert(bbsc_world_initial.fingerprints.empty());
 stale=reply;stale.epoch++;BbscWorldNativeInitialControl({22,stale,digest});assert(bbsc_world_initial.fingerprints.empty());
 BbscWorldNativeInitialControl({22,reply,digest});assert(bbsc_world_initial.fingerprints.contains(hash));
 received.push_back(bad);received.push_back(packet);
 assert(BbscWorldNativeInitialReady(scope,22,7)&&applied==2);
 assert(BbscWorldNativeInitialReady(scope,22,7)&&applied==2); // once per load
 ++bbsc_world_native_load;assert(!BbscWorldNativeInitialReady(scope,22,7));
 BbscWorldNativeInitialControl({22,reply,digest});assert(bbsc_world_initial.fingerprints.empty()); // old visit
 // A pre-event arrival still advertises its previous map while Loading.
 p.phase=World::Phase::Loading;p.map=0x15000000;
 reply.sequence=bbsc_world_initial.request;BbscWorldNativeInitialControl({22,reply,digest});
 received.push_back(packet);assert(BbscWorldNativeInitialReady(scope,22,7)&&applied==3);
 assert(BbscWorldNativeInitialReady(scope,0,0)); // first unoccupied map keeps native admission
 p.phase=World::Phase::Playing;p.map=scope.map;
 ++bbsc_world_native_load;
 here=false;assert(!BbscWorldNativeInitialReady(scope,22,7));here=true;
 assert(BbscWorldNativeInitialReady(scope,11,7)); // owner never resets itself
 // Owner builds native11 only for a resident requester in its current scope.
 self=22;bbsc_world_presence_book.Bind(p.world,22);assert(bbsc_world_presence_book.Hear(11,p.world,other,now));
 scene=false;BbscWorldNativeInitialControl({11,request,{}});assert(!native_sends);
 scene=true;send_ok=false;const auto before=sent.size();BbscWorldNativeInitialControl({11,request,{}});assert(native_sends==1&&sent.size()==before);
 send_ok=true;BbscWorldNativeInitialControl({11,request,{}});assert(native_sends==2&&sent.back().control.kind==World::ControlKind::NativeInitialReady);
 assert(sent.back().payload==digest&&!bbsc_world_initial_sending);
 request.scope.map=0x19000000;BbscWorldNativeInitialControl({11,request,{}});assert(native_sends==2);
 request.scope=scope;other.phase=World::Phase::Loading;other.map=0x15000000;++other.sequence;
 assert(bbsc_world_presence_book.Hear(11,p.world,other,now));
 BbscWorldNativeInitialControl({11,request,{}});assert(native_sends==3); // explicit target, not last committed map
 other.phase=World::Phase::Playing;++other.sequence;assert(bbsc_world_presence_book.Hear(11,p.world,other,now));
 BbscWorldNativeInitialControl({11,request,{}});assert(native_sends==3); // unrelated playing map denied
}
'''

def original_contract(path):
    data=Path(path).read_bytes();ph=struct.unpack_from('<Q',data,32)[0]
    size,count=struct.unpack_from('<HH',data,54)
    segments=[struct.unpack_from('<II6Q',data,ph+i*size) for i in range(count)]
    def read(a,n):
        for t,_,o,v,_,s,_,_ in segments:
            if t==1 and v<=a and a+n<=v+s:return data[o+a-v:o+a-v+n]
        raise AssertionError(hex(a))
    def call(a,target):
        assert read(a,1)==b'\xe8' and a+5+struct.unpack('<i',read(a+1,4))[0]==target
    call(0x178C7EF,0x1786360) # native summon sends the full initial world state
    call(0x1786709,0x190E750) # CHR records use the actual historical-death bitmap
    assert read(0x178669A,10)==bytes.fromhex('48 b8 20 52 48 43 00 17 09 15')
    assert read(0x1786746,5)==bytes.fromhex('ba 11 00 00 00')
    assert read(0x190E7FE,7)==bytes.fromhex('83 b8 f8 00 00 00 00') # HP<=0 serialized
    assert read(0x190E876,9)==bytes.fromhex('0f b6 14 0e 09 c2 88 14 0e')
    call(0x191BF6B,0x190E8B0) # native CHR loader calls this exact handler/ABI
    assert read(0x190E972,10)==bytes.fromhex('48 b9 08 00 00 00 02 00 00 00')
    assert read(0x190E97C,7)==bytes.fromhex('48 89 88 b4 01 00 00')
    call(0x190E983,0x18C49F0) # historical removal, not proxy Kill018BF9A0
    print('PASS original 1.09 native summon/channel11 CHR serializer, dead bits and historical handler ABI')

def main():
    code=SOURCE
    for actual,mock in [('reinterpret_cast<Apply>(image_base+0x0190E8B0)','MockApply'),
                        ('reinterpret_cast<Send>(image_base+0x01786360)','MockSend'),
                        ('reinterpret_cast<Receive>(image_base+0x01789200)','MockReceive')]:
        assert code.count(actual)==1
        code=code.replace(actual,mock)
    compiler=shutil.which('clang++') or 'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-native-chr-') as tmp:
        cpp=Path(tmp)/'initial.cpp';exe=Path(tmp)/'initial.exe'
        cpp.write_text(PREFIX+code+MAIN,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],env=env,check=True)
    print('PASS production native CHR admission: packet bounds, atomic block preflight, owner/epoch/load fences, once-only apply, native send failure')
    if os.environ.get('BBSC_TEST_EBOOT'):original_contract(os.environ['BBSC_TEST_EBOOT'])

if __name__=='__main__':main()
