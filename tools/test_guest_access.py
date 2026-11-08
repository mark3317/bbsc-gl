"""Execute actual local-player/dialogue gates and validate the original f47 ABI.

Allocated memory only. Optional argument: original analysis ELF (read only).
"""
from pathlib import Path
import os, struct, subprocess, sys, tempfile
import test_world_travel_native as travel

root = travel.ROOT
source = (root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')

def function(signature):
    a=source.index(signature+' {');b=source.index('{',a)+1;depth=1
    while depth:
        depth+=(source[b]=='{')-(source[b]=='}');b+=1
    return source[a:b]+'\n'

# A join must never start another address-space-wide workshop search.
for removed in ('StartBbscToolScan', 'TickBbscDreamTools', 'FindInMemory',
                'BbscGiveHostWorkshopTools', 'bbsc_dream_type_conditions'):
    assert removed not in source, removed

prefix=travel.PREFIX+r'''
using s8=int8_t;
#define BBSC_PERF_SCOPE(...)
#define LOG_INFO(...)
bool BbscResearchEnabled(){return false;}
void NoteBbscBossRewardEvent(s64){}
s64 BbscRunningEventId(u64){return native_event;}
u8 bbsc_guest_role_skip=0;
u8 bbsc_dream_type_skip=0;
std::vector<s64> bbsc_dream_type_logged;
'''
production=travel.SOURCE[travel.SOURCE.index('s32 bbsc_world_travel_point='):
                         travel.SOURCE.index('void InstallBbscWorldTravel() {')]
production+=function('void PS4_SYSV_ABI BbscDreamTalkHook(u64 /*tag*/, const GuestRegisterSnapshot* registers)')
production+=function('void PS4_SYSV_ABI BbscGuestRoleGateHook(u64, const GuestRegisterSnapshot* registers)')
production+=function('void PS4_SYSV_ABI BbscDreamTypeCheckHook(u64 /*tag*/, const GuestRegisterSnapshot* registers)')
main=r'''
int main(){
 assert(!GuestAccess::EventAllowed(13204820)); // never execute both jump scripts as guest
 assert(GuestAccess::EventAllowed(13204832)&&GuestAccess::EventAllowed(13204833));
 assert(!GuestAccess::EventAllowed(12424810)&&GuestAccess::EventAllowed(12424811));
 assert(!GuestAccess::EventAllowed(13304870)&&GuestAccess::EventAllowed(13304871));
 std::array<u8,0x48> record{};std::array<u8,0x30> condition{};
 const u64 c=(u64)condition.data();
 Set(record,0x10,c);Set(record,0x18,u64{0x60000});
 Set(condition,0,image_base+TalkConditionVtableOffset);Set(condition,0x18,u64{0x40000});
 GuestRegisterSnapshot r;r.rcx=(u64)record.data();
 state=6;allowed=true;current_map=BbscHuntersDreamMap;
 for(u32 talk:{999999u,210699u,210692u,240000u,290001u,210305u}){
   Set(condition,0x10,talk);Set(condition,0x25,u8{1});BbscDreamTalkHook(0,&r);assert(condition[0x25]==0);
 }
 native_flags.insert(1028);Set(condition,0x10,u32{210305});
 Set(condition,0x25,u8{1});BbscDreamTalkHook(0,&r);assert(condition[0x25]==1);
 native_flags.clear();Set(condition,0x10,u32{210306});
 Set(condition,0x25,u8{1});BbscDreamTalkHook(0,&r);assert(condition[0x25]==1);
 // An empty/unknown host altar cannot create or replace its cup via f19.
 Set(condition,0x10,u32{210050});Set(condition,0x25,u8{1});
 bbsc_world_catalog_ready=false;BbscDreamTalkHook(0,&r);assert(condition[0x25]==1);
 bbsc_world_catalog_ready=true;bbsc_world_altars[0].entry.occupied=true;
 BbscDreamTalkHook(0,&r);assert(condition[0x25]==0);
 Set(condition,0x10,u32{999999});Set(condition,0x18,u64{0x30000});
 Set(condition,0x25,u8{1});BbscDreamTalkHook(0,&r);assert(condition[0x25]==1);
 Set(condition,0x18,u64{0x40000});state=3;BbscDreamTalkHook(0,&r);assert(condition[0x25]==1);
 // No pointer permission cache: event identity is checked on every invocation.
 std::array<u8,0xc0> instance{};r.rdi=c;r.rdx=(u64)instance.data();
 for(s64 event:std::array<s64,15>{-1,0,999999,3503,12100000,12100002,12100180,12104800,12104850,13204832,13204820,12424810,12424811,13304870,13304871})
 for(s32 role:{0,3,6})for(s32 entity:{10000,3200110})for(s8 type:{0,1,2}){
   state=role;native_event=event;Set(condition,0x28,entity);Set(condition,0x2c,type);
   condition[0x10]=0;bbsc_dream_type_skip=0;BbscDreamTypeCheckHook(0,&r);
   assert(bool(bbsc_dream_type_skip)==(role==6&&entity==10000&&type==0&&GuestAccess::EventAllowed(event)));
 }
 // End/JumpIfHost and End/JumpIfClient use their ORIGINAL native branch.
 // Only this exact bank1003 caller/context may receive a local host answer.
 std::array<u64,1> stack{};r.rsp=(u64)stack.data();r.r14=(u64)instance.data();r.rdi=c;
 Set(condition,0,image_base+0x0532D270);
 for(s64 event:std::array<s64,10>{-1,999999,9421,12501803,3503,12100000,12424810,12424811,13304870,13304871})
 for(s32 role:{3,6})for(u8 wanted:{0,1,2,3,4})for(bool bank:{false,true}){
   native_event=event;state=role;Set(condition,0x28,wanted);
   stack[0]=image_base+(bank?0x17bf643:0x1800000);r.rax=123;bbsc_guest_role_skip=0;condition[0x10]=0xa6;
   BbscGuestRoleGateHook(0,&r);
   const bool changed=role==6&&bank&&wanted<2&&GuestAccess::EventAllowed(event);
   assert(bool(bbsc_guest_role_skip)==changed);
   assert(r.rax==(changed?u64(wanted==0):123));
   assert(condition[0x10]==(changed?u8(0xa6|(wanted==0)):0xa6));
 }
}
'''
compiler=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
env=dict(os.environ,PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH',''))
with tempfile.TemporaryDirectory(prefix='bbsc-guest-access-') as tmp:
    cpp=Path(tmp)/'access.cpp';exe=Path(tmp)/'access.exe'
    cpp.write_text(prefix+production+main,encoding='utf-8')
    subprocess.run([compiler,'-std=c++20','-I',str(root/'emulator/src'),str(cpp),'-o',str(exe)],env=env,check=True)
    subprocess.run([str(exe)],env=env,check=True)
print('PASS production guest default-allow gates, explicit deny list, native host/NPC/remote actors retained, no full-memory scanner')

if len(sys.argv)>1:
    data=Path(sys.argv[1]).read_bytes()
    ph=struct.unpack_from('<Q',data,32)[0];size,count=struct.unpack_from('<HH',data,54)
    segments=[struct.unpack_from('<II6Q',data,ph+i*size) for i in range(count)]
    def read(address,length):
        for kind,_,offset,virtual,_,span,_,_ in segments:
            if kind==1 and virtual<=address and address+length<=virtual+span:
                return data[offset+address-virtual:offset+address-virtual+length]
        raise AssertionError(hex(address))
    # Real dispatcher: R15=evaluator, R14=argument reader, count==6, five
    # integer variants at exactly the slots read by the production result hook.
    assert read(0x203ad74,6)==bytes.fromhex('49 89 d6 49 89 f7')
    assert read(0x203c35d,8)==bytes.fromhex('45 31 ff 83 f8 06 0f 85')
    for address,offset,index in [(0x203c36c,-0x1e0,1),(0x203cf5d,-0x1f0,2),
                                  (0x203e4ef,-0x200,3),(0x203e96b,-0x210,4),(0x203e9f6,-0x220,5)]:
        assert read(address,12)==b'\x48\x8d\xbd'+struct.pack('<i',offset)+b'\xba'+struct.pack('<i',index)
    assert read(0x203eecf,9)==bytes.fromhex('41 c7 44 24 08 02 00 00 00')
    assert read(0x17b21a0,6)==bytes.fromhex('55 48 89 e5 41 57')
    # Bank1003 keeps its instance in R14, constructs the native predicate vtable
    # and uses its return value. The callback never writes a native instruction.
    assert read(0x17bede1,3)==bytes.fromhex('49 89 f6')
    assert read(0x17bf62c,7)==bytes.fromhex('4c 8d 3d 3d dc b6 03')
    assert read(0x17bf63e,5)==b'\xe8'+struct.pack('<i',0x17b21a0-0x17bf643)
    assert read(0x17b240d,11)==bytes.fromhex('8a 4b 10 80 e1 fe 08 c1 88 4b 10')
    print('PASS original1.09 workshop f47 count, evaluator ABI, all five variant stack locations, result boundary')
