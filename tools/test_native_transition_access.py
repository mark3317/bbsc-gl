"""Production gates over original EMEVD, using allocated fixture memory only."""
import os
from pathlib import Path
import sys
import test_world_travel_native as travel

sys.path.insert(0, str(travel.ROOT/'tools/gamedata'))
from emevd import Emevd

source = (travel.ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(sig):
    a=source.index(sig+' {'); b=source.index('{',a)+1; depth=1
    while depth:
        depth+=(source[b]=='{')-(source[b]=='}'); b+=1
    return source[a:b]

travel.PREFIX += r'''
#include <algorithm>
using s8=int8_t;
#define BBSC_PERF_SCOPE(...)
#define LOG_INFO(...)
void NoteBbscBossRewardEvent(s64){}
std::array<u64,8> bbsc_dream_type_conditions{};
size_t bbsc_dream_type_next=0;u8 bbsc_dream_type_skip=0;
std::array<s64,0> BbscDreamGuestEvents{},BbscGuestGiftEvents{};
std::vector<s64> bbsc_dream_type_logged;
bool IsBbscPersonalMapEvent(s64){return false;}
bool IsBbscChaliceBossRewardEvent(s64){return false;}
bool BbscResearchEnabled(){return false;}
''' + function('void PS4_SYSV_ABI BbscDreamTypeCheckHook(u64 /*tag*/, const GuestRegisterSnapshot* registers)')

game=Path(os.environ['BB_GAME'])
travel.MAIN='int main(){\n'
for name,ids in [('m32_00_00_00',[13200310,13200311]),('m28_00_00_00',[12800430,12800431]),
                 ('m24_00_00_00',[12405263]),('m22_00_00_00',[12200131])]:
    evd=Emevd(game/'event'/(name+'.emevd.dcx'))
    for eid,ins in evd.events:
        if eid not in ids: continue
        assert any(b==2003 and c==49 for b,c,a in ins)
        travel.MAIN+='{alignas(8) u8 file[]={'+','.join(str(b) for b in evd.data)+'};\n'
        travel.MAIN+='native_event='+str(eid)+';\n'+r'''
 alignas(8) std::array<u8,0xC0> instance{};
 alignas(8) std::array<u8,0x10> ref{};
 u64 p=(u64)instance.data(),f=(u64)file;
 WriteValue<u64>(p,0xA8,(u64)ref.data());WriteValue<u64>((u64)ref.data(),8,f);
 ++bbsc_world_native_load;
 const u64 rows=f+ReadValue<u64>(f,0x18);
 for(s64 k=0;k<ReadValue<s64>(f,0x10);++k){u64 row=rows+k*0x30;
  if(ReadValue<s64>(row,0)!=native_event)continue;
  for(s64 step=0;step<ReadValue<s64>(row,8);++step){
   u64 i=f+ReadValue<u64>(f,0x28)+ReadValue<u64>(row,0x10)+step*0x20;
   WriteValue<u64>(p,0xB0,i);WriteValue<u8>(p,0x78,1);
   auto bank=ReadValue<s32>(i,0),cmd=ReadValue<s32>(i,4);
   const u64 args=f+ReadValue<u64>(f,0x78)+ReadValue<u64>(i,0x10);
   bool client=bank==1003&&cmd==6&&ReadValue<u32>(args,0)==256;
   allowed=false;EnableBbscNativeTravelEvent(p);assert(ReadValue<u8>(p,0x78)==1);
   allowed=true;EnableBbscNativeTravelEvent(p);
   assert(ReadValue<u8>(p,0x78)==LampTravel::IsLectureExitEvent(native_event));
   assert(ReadValue<s32>(i,0)==bank);
   assert(ReadValue<s32>(i,4)==cmd);
   if(client)assert(ReadValue<u32>(args,0)==256);
  }
 }
 std::array<u8,0x30> condition{};u64 c=(u64)condition.data();
 WriteValue<s32>(c,0x28,10000);WriteValue<s8>(c,0x2C,0);
 GuestRegisterSnapshot r;r.rdi=c;r.rdx=p;state=6;bbsc_dream_type_skip=0;
 BbscDreamTypeCheckHook(0,&r);assert(bbsc_dream_type_skip&&ReadValue<u8>(c,0x10)==1);
}
'''
travel.MAIN+=r'''

// Original Rom fog loops: admit only the local player's type0, never host activation/NPC.
for(s64 id:{13204832,13204833,13204820,13204834})for(s32 role:{3,6})
for(u32 area:{0x20000000u,0x1d000000u})for(s32 chr:{10000,3200110})for(s8 type:{0,1}){
 std::array<u8,0xc0> inst{};std::array<u8,0x30> condition{};
 native_event=id;state=role;current_map=area;bbsc_dream_type_conditions.fill(0);
 u64 c=(u64)condition.data();WriteValue<s32>(c,0x28,chr);WriteValue<s8>(c,0x2c,type);
 GuestRegisterSnapshot r;r.rdi=c;r.rdx=(u64)inst.data();bbsc_dream_type_skip=0;
 BbscDreamTypeCheckHook(0,&r);
 assert(bool(bbsc_dream_type_skip)==(GuestAccess::EventAllowed(id)&&role==6&&chr==10000&&type==0));
}
for(s32 role:{3,6})for(auto [point,map]:{std::pair{2602959,0x1A000000u},std::pair{3302959,0x21000000u},
 std::pair{3202959,0x20000000u},std::pair{3202958,0x20000000u},std::pair{3402959,0x22000000u},std::pair{2502959,0x19000000u}}){
 state=role;bbsc_world_travel_inflight=false;bbsc_world_travel_native_armed=false;
 bbsc_world_requested_scope.reset();bbsc_world_presence_local.world={11,99};
 GuestRegisterSnapshot r;r.rdi=point;BbscWorldNativeWarpBegin(&r);
 assert(bbsc_world_travel_inflight&&bbsc_world_travel_native_armed);
 assert(bbsc_world_requested_scope&&bbsc_world_requested_scope->map==map);
 assert((bbsc_world_requested_scope->world==World::WorldId{11,99}));
}
for(s32 scene:{24000000,28000040,28001040,22000040})assert(LampTravel::IsLocalTravelCutscene(scene));
assert(!LampTravel::IsNativeTravelEvent(13201803)); // shared Rom story transition
assert(!LampTravel::IsNativeTravelEvent(3503)); // shared cycle progression
assert(!LampTravel::IsLocalTravelCutscene(21000000)); // shared finale
for(u32 flag:{13200123u,13200124u}){
 std::array<u8,125> before{},live{};u32 bit=flag%1000;u8 mask=0x80u>>(bit%8);
 live[bit/8]=mask;LampTravel::KeepTravelCommands(flag/1000,before.data(),live.data());assert(!live[bit/8]);
 before[bit/8]=mask;LampTravel::KeepTravelCommands(flag/1000,before.data(),live.data());assert(live[bit/8]==mask);
}
}
'''
for signature,needle in [('void OnBbscCutsceneRequestHook(u64 offset, const GuestRegisterSnapshot& registers)', 'LampTravel::IsLocalTravelCutscene(cutscene)'),
                         ('void OnBbscCutscenePacket(u32 sender, bool from_host, const void* data, std::size_t size)', 'LampTravel::IsLocalTravelCutscene(packet.cutscene)')]:
    assert needle in function(signature)
travel.main()
print('PASS original6 transition chains/all steps, client/type gates, local ObjActs; shared Rom/finale excluded')
