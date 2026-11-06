"""Execute production native authority callbacks and validate original 1.09 hook spans.

No live process/save is read. An optional cached, original eboot ELF supplies
instruction bytes for the exact native hook sites and read-only altar getters.
"""
from pathlib import Path
import os,re,shutil,struct,subprocess,tempfile

ROOT=Path(__file__).resolve().parents[1]
NATIVE=(ROOT/'emulator/src/core/bbsc_independent_world.inc').read_text(encoding='utf-8')
def function(signature):
    start=NATIVE.index(signature+' {');p=NATIVE.index('{',start)+1;depth=1
    while depth:
        depth+=(NATIVE[p]=='{')-(NATIVE[p]=='}');p+=1
    return NATIVE[start:p]+'\n'

PREFIX=r'''
#include <atomic>
#include <cassert>
#include <set>
#include <mutex>
#include <string_view>
#include "core/bbsc_world_control.h"
#include "core/bbsc_world_native_initial.h"
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
using namespace Core::Bloodborne;
#define PS4_SYSV_ABI
void TraceBbscCombatActor(std::string_view,uint64_t,int32_t,bool){}
struct GuestRegisterSnapshot {u64 rax{},rbx{},rcx{},rdx{},rsi{},rdi{},rbp{},rsp{},r8{},r9{},r10{},r11{},r12{},r13{},r14{},r15{},rflags{};};
bool active=false,here=true;
bool BbscWorldBlocksActive(){return false;}
bool BbscWorldBlockSimulation(){return false;}
bool BbscWorldBlockPacketSend(GuestRegisterSnapshot*){return false;}
bool BbscWorldBlockOwnsAny(){return false;}
u64 BbscWorldBlockHpMember(){return 0;}
u32 BbscWorldBlockRole(u64){return 0;}
std::atomic<bool> bbsc_independent_hooks{true},bbsc_independent_travel_hooks{true};
std::mutex bbsc_world_presence_mutex;
World::PresenceBook bbsc_world_presence_book;
World::Presence bbsc_world_presence_local;
int session=3,remote_mode=1,member_count=2;
u64 GetGlobalState(){return 1;}
int GetBbscSessionMemberCount(u64){return member_count;}
int GetSessionState(){return session;}
u32 GetBbscRelayHost(){return 22;}
std::vector<u64> GetMultiPlayerInsTasks(){return {1000,2000};}
template<class T>T ReadValue(u64 task,size_t offset){return offset==0xE8?T(task==1000?(session==6?0:3):remote_mode):T(0);}
s64 SteadyNowMs(){return 10000;}
bool BbscIndependentActive(){return active;}
thread_local u8 bbsc_independent_send_depth=0;
thread_local u32 bbsc_world_initial_sending=0;
thread_local u64 bbsc_world_initial_fingerprint=0;
bool ReadablePointer(u64 p,size_t){return p!=0;}
u8 bbsc_independent_send_skip=0;
std::atomic<u32> bbsc_independent_role{0},bbsc_independent_owner{0};
u32 BbscWorldPeer(u64 member){return member==100?11:member==200||member==2200?22:0;}
bool BbscWorldPeerHere(u32){return here;}
bool BbscWorldSendHere(u32){return here;}
bool BbscWorldPlayerSendHere(u32){return here;}
u64 GetLocalPlayerCharacter(){return 0;}
u64 BbscWorldNativeMember(u32 peer){return peer==22?200:0;}
alignas(16) std::array<u8,0x130> bbsc_world_host_state{},bbsc_world_guest_state{};
thread_local u64 bbsc_world_hp_original=0;
thread_local u64 bbsc_world_hp_receive_frame=0;
'''
MAIN=r'''
int main(){
    bbsc_world_presence_local.world={11,99};bbsc_world_presence_local.phase=World::Phase::Playing;
    bbsc_world_presence_local.map=0x18000000;bbsc_world_presence_local.visit=1;bbsc_world_presence_local.sequence=1;
    bbsc_world_presence_local.capabilities=World::PresenceCapability|World::IndependentTravelCapability;
    auto remote=bbsc_world_presence_local;bbsc_world_presence_book.Bind({11,99},11);
    assert(bbsc_world_presence_book.Hear(22,{11,99},remote,10000));
    assert(BbscWorldAllMembersReady()); // host: mode3 self, mode1 remote guest
    session=6;remote_mode=2;assert(BbscWorldAllMembersReady()); // guest: mode0 self, mode2 remote host
    member_count=3;assert(!BbscWorldAllMembersReady());member_count=2;
    GuestRegisterSnapshot r;r.rsi=100;r.rdx=0x27;r.rax=77;
    BbscWorldPacketSend(0,&r);assert(r.rax==77&&!bbsc_independent_send_skip);
    active=true;BbscWorldPacketSend(0,&r);assert(r.rax==0&&bbsc_independent_send_skip);
    const std::array<u8,4> initial{1,2,3,4};
    r.rdx=0x11;r.rsi=200;r.rcx=reinterpret_cast<u64>(initial.data());r.r8=initial.size();
    bbsc_world_initial_sending=22;bbsc_independent_send_skip=0;BbscWorldPacketSend(0,&r);
    assert(bbsc_world_initial_fingerprint==World::NativeInitialFingerprint(initial)&&!bbsc_independent_send_skip);
    bbsc_world_initial_fingerprint=0;r.rsi=100;BbscWorldPacketSend(0,&r);assert(!bbsc_world_initial_fingerprint);
    bbsc_world_initial_sending=0;
    for(u32 ch:{7u,0x10u,0x11u,0x19u,0x42u}){
        bbsc_independent_send_skip=0;r.rdx=ch;here=false;BbscWorldPacketSend(0,&r);
        assert(!bbsc_independent_send_skip); // joining is never blocked by a map filter
    }
    for(u32 ch:{4u,5u,6u,0x14u,0x31u,0x3Eu,0x2Fu}){
        bbsc_independent_send_skip=0;r.rdx=ch;here=false;bbsc_independent_role=1;
        BbscWorldPacketSend(0,&r);assert(bbsc_independent_send_skip);
        bbsc_independent_send_skip=0;here=true;BbscWorldPacketSend(0,&r);
        assert(!bbsc_independent_send_skip);
    }
    here=true;bbsc_independent_role=2;bbsc_independent_owner=22;
    r.rdx=0x15;r.rsi=100;bbsc_independent_send_skip=0;BbscWorldPacketSend(0,&r);
    assert(r.rsi==200&&!bbsc_independent_send_skip); // the map owner, not the session host
    bbsc_independent_role=1;r.rsi=100;bbsc_independent_send_skip=0;BbscWorldPacketSend(0,&r);
    assert(bbsc_independent_send_skip); // own hit already applied
    bbsc_independent_send_skip=0;r.rdx=0x04;bbsc_independent_role=2;BbscWorldPacketSend(0,&r);
    assert(bbsc_independent_send_skip); // followers don't send another HP/position authority
    r.rdx=0x2F;bbsc_independent_send_skip=0;BbscWorldPacketSend(0,&r);
    assert(bbsc_independent_send_skip); // a returning native host cannot reset the map owner's objects
    bbsc_independent_role=1;bbsc_independent_send_skip=0;BbscWorldPacketSend(0,&r);
    assert(!bbsc_independent_send_skip);bbsc_independent_role=2;
    for(u32 ch:{0x16u,0x17u,0x2Cu}){r.rdx=ch;bbsc_independent_send_skip=0;BbscWorldPacketSend(0,&r);assert(bbsc_independent_send_skip);}
    const s32 host=3,guest=6;std::memcpy(bbsc_world_host_state.data()+0x124,&host,4);
    std::memcpy(bbsc_world_guest_state.data()+0x124,&guest,4);
    r.rflags=0x123;bbsc_independent_role=1;BbscWorldHpRound(0,&r);assert(r.rflags&(u64{1}<<6));
    bbsc_independent_role=2;BbscWorldHpRound(0,&r);assert(!(r.rflags&(u64{1}<<6)));
    assert((r.rflags&~(u64{1}<<6))==(0x123u&~(u64{1}<<6)));
    r.rdi=123456;BbscWorldHpState(0,&r);assert(r.rdi==BbscWorldStateStandIn(6));
    BbscWorldHpRestore(0,&r);assert(r.rdi==123456);BbscWorldHpRestore(0,&r);assert(r.rdi==123456);
    r.rbx=999;r.r12=5;BbscWorldHpSource(0,&r);assert(r.rbx==u64{200}-0xD0);
    r.rbx=999;r.r12=6;BbscWorldHpSource(0,&r);assert(r.rbx==999);
    r.rax=1234;BbscWorldHitState(0,&r);assert(r.rax==BbscWorldStateStandIn(6));
    active=false;r.rax=1234;BbscWorldHitState(0,&r);assert(r.rax==1234);

    World::Control c;c.scope={{11,99},0x18000000,{},0};c.owner=22;c.epoch=7;
    const auto bytes=World::Encode(c);assert(bytes.size()==sizeof(c));assert(World::DecodeControl(bytes));
    auto truncated=bytes;truncated.pop_back();assert(!World::DecodeControl(truncated));
    auto bad=c;bad.padding=1;assert(World::Encode(bad).empty());
    World::OwnerBook owners;owners.Bind({11,99});assert(!owners.Take(22,c,10));assert(owners.Take(11,c,10));
    bad=c;bad.owner=33;assert(!owners.Take(11,bad,11));
    bad=c;bad.epoch=6;assert(!owners.Take(11,bad,12));
    bad=c;bad.epoch=8;bad.owner=33;assert(owners.Take(11,bad,13));
    owners.Bind({11,100});assert(!owners.Find(c.scope));assert(!owners.Take(11,c,14));
    c.kind=World::ControlKind::Flags;const auto current=c.scope;
    assert(World::ShouldApplyFlags(c,current,11,22,false,true)); // follower applies complete owner flags
    assert(!World::ShouldApplyFlags(c,current,22,22,false,true)); // owner ignores its returned echo
    assert(!World::ShouldApplyFlags(c,current,11,22,false,false)); // incomplete snapshot
    c.kind=World::ControlKind::Enemies;assert(!World::ShouldApplyFlags(c,current,11,22,false,true));
    c.kind=World::ControlKind::Flags;c.scope.map=0x15000000;
    assert(!World::ShouldApplyFlags(c,current,11,22,true,true)); // host also keeps dedicated Dream authority
    c.scope.map=0x19000000;assert(World::ShouldApplyFlags(c,current,11,22,true,true));
    assert(!World::ShouldApplyFlags(c,current,11,22,false,true)); // off-map guest
    c.scope.world.room++;assert(!World::ShouldApplyFlags(c,current,11,22,true,true));
}
'''

def check_original_sites(elf):
    data=elf.read_bytes();phoff=struct.unpack_from('<Q',data,32)[0]
    size,count=struct.unpack_from('<HH',data,54);segments=[]
    for i in range(count):
        typ,flags,off,va,pa,fs,ms,align=struct.unpack_from('<II6Q',data,phoff+i*size)
        if typ==1:segments.append((va,off,fs))
    def original(address,n):
        for va,off,fs in segments:
            if va<=address and address+n<=va+fs:return data[off+address-va:off+address-va+n]
        raise AssertionError(f'Address outside ELF segments: {address:x}')
    total=0
    for path in ['bbsc_independent_world.inc','bbsc_world_travel.inc']:
        source=(ROOT/'emulator/src/core'/path).read_text(encoding='utf-8')
        for addr,values in re.findall(r'Site\{(0x[0-9A-Fa-f]+),\{([^}]+)\}',source):
            expected=bytes(int(v.strip(),0) for v in values.split(','))
            assert original(int(addr,16),len(expected))==expected,f'Native hook mismatch {addr}'
            total+=1
    assert original(0x018EF6C6,16)==bytes.fromhex('4d 8d bc 24 28 07 00 00 4d 8d ac 24 2c 07 00 00')
    prologue=bytes.fromhex('55 48 89 e5 41 57')
    for address in [0x1AB2A40,0x1AB1DB0,0x1AB3070,0x1AB31C0,0x18C6390,0x19186E0,0x18F4A50,0x15BC080,0x12B2960,
                    0x1786360,0x1789200,0x190E8B0]:
        assert original(address,len(prologue))==prologue,f'Native callable mismatch {address:x}'
    assert original(0x013CDF30,6)==bytes.fromhex('55 48 89 e5 41 57')
    # Native per-character cleanup used by CSMultiPlayerIns.Delete: world in RDI,
    # the matched remote PlayerIns (NOT its member id) in RSI.
    assert original(0x01E50C51,3)==bytes.fromhex('4c 89 f6')
    remove_call=0x01E50C54
    assert original(remove_call,1)==b'\xe8'
    assert remove_call+5+struct.unpack('<i',original(remove_call+1,4))[0]==0x019186E0
    # Native per-handle arrival cleanup precedes character removal. FirstSync
    # registers new arrival state by handle and rejects an existing entry.
    assert original(0x01E50C15,4)==bytes.fromhex('41 8b 76 08')
    clear_call=0x01E50C19
    assert original(clear_call,1)==b'\xe8'
    assert clear_call+5+struct.unpack('<i',original(clear_call+1,4))[0]==0x015BC080
    assert original(0x015BC5FA,4)==bytes.fromhex('48 83 c0 14')
    assert original(0x015BC603,3)==bytes.fromhex('44 39 e2')
    # Player native virtual+B0 attaches parts to the current global scene;
    # these are the exact offsets observed by BbscWorldPlayerMesh.
    assert original(0x018F4ABA,7)==bytes.fromhex('4c 8b b8 c8 5f 00 00')
    assert original(0x018F4ACA,7)==bytes.fromhex('48 8b 8b d0 04 00 00')
    assert original(0x018F4ADA,4)==bytes.fromhex('4c 89 79 10')
    assert original(0x018F4AFD,4)==bytes.fromhex('4c 8b 68 18')
    assert original(0x018F4B01,4)==bytes.fromhex('49 8b 45 70')
    assert original(0x018F4B21,4)==bytes.fromhex('49 8b 7d 18')
    # Validate the real EMEVD2003[49] dispatch and its EDI argument ABI.
    table=0x017C2C38
    case=table+struct.unpack('<i',original(table+48*4,4))[0]
    assert case==0x017C1CCC
    assert original(0x017C1CEE,2)==bytes.fromhex('8b 39')
    call=0x017C1CF0
    assert original(call,1)==b'\xe8'
    assert call+5+struct.unpack('<i',original(call+1,4))[0]==0x013CDF30
    assert original(0x02040E1B,3)==bytes.fromhex('83 f8 01') #41 requires one arg
    assert original(0x02040E1E,2)==bytes.fromhex('0f 85')
    source=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
    assert 'if(site.offset==0x013CDF30)BbscWorldNativeWarpBegin(registers);' in source
    assert 'if(site.offset==0x013CDF30)bbsc_world_native_warp_hook=true;' in source
    print(f'PASS original 1.09 ELF: {total} native hook spans + 7 callable prologues')

def main():
    signatures=['bool BbscWorldAllMembersReady()',
        'void PS4_SYSV_ABI BbscWorldPacketSend(u64,const GuestRegisterSnapshot* regs)',
        'u64 BbscWorldStateStandIn(s32 role)',
        'void PS4_SYSV_ABI BbscWorldHpRound(u64,const GuestRegisterSnapshot* regs)',
        'void PS4_SYSV_ABI BbscWorldHpState(u64,const GuestRegisterSnapshot* regs)',
        'void PS4_SYSV_ABI BbscWorldHpRestore(u64,const GuestRegisterSnapshot* regs)',
        'void PS4_SYSV_ABI BbscWorldHpSource(u64,const GuestRegisterSnapshot* regs)',
        'void PS4_SYSV_ABI BbscWorldHitState(u64,const GuestRegisterSnapshot* regs)']
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-independent-native-') as tmp:
        cpp=Path(tmp)/'native.cpp';exe=Path(tmp)/('native.exe' if os.name=='nt' else 'native')
        cpp.write_text(PREFIX+''.join(function(s) for s in signatures)+MAIN,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-Wall','-Wextra','-Werror','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production native authority callbacks, direct hit routing, HP role/source, owner epochs')
    if os.environ.get('BBSC_TEST_EBOOT'):check_original_sites(Path(os.environ['BBSC_TEST_EBOOT']))

if __name__=='__main__':main()
