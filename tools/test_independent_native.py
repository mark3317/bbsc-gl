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
#include "core/bbsc_world_control.h"
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
using namespace Core::Bloodborne;
#define PS4_SYSV_ABI
struct GuestRegisterSnapshot {u64 rax{},rbx{},rcx{},rdx{},rsi{},rdi{},rbp{},rsp{},r8{},r9{},r10{},r11{},r12{},r13{},r14{},r15{},rflags{};};
bool active=false,here=true;
bool BbscIndependentActive(){return active;}
thread_local u8 bbsc_independent_send_depth=0;
u8 bbsc_independent_send_skip=0;
std::atomic<u32> bbsc_independent_role{0},bbsc_independent_owner{0};
u32 BbscWorldPeer(u64 member){return member==100?11:member==200?22:0;}
bool BbscWorldPeerHere(u32){return here;}
bool BbscWorldSendHere(u32){return here;}
u64 BbscWorldNativeMember(u32 peer){return peer==22?200:0;}
alignas(16) std::array<u8,0x130> bbsc_world_host_state{},bbsc_world_guest_state{};
thread_local u64 bbsc_world_hp_original=0;
'''
MAIN=r'''
int main(){
    GuestRegisterSnapshot r;r.rsi=100;r.rdx=0x27;r.rax=77;
    BbscWorldPacketSend(0,&r);assert(r.rax==77&&!bbsc_independent_send_skip);
    active=true;BbscWorldPacketSend(0,&r);assert(r.rax==0&&bbsc_independent_send_skip);
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
    prologue=bytes.fromhex('55 48 89 e5 41 57')
    for address in [0x1AB2A40,0x1AB1DB0,0x1AB3070,0x1AB31C0,0x18C6390,0x18BCD40,0x12B2960]:
        assert original(address,len(prologue))==prologue,f'Native callable mismatch {address:x}'
    print(f'PASS original 1.09 ELF: {total} native hook spans + 7 callable prologues')

def main():
    signatures=['void PS4_SYSV_ABI BbscWorldPacketSend(u64,const GuestRegisterSnapshot* regs)',
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
