"""Local lamp ignition events and original-data contract; no live writes."""
from pathlib import Path
import struct
import sys
import test_world_travel_native as travel

travel.MAIN = r'''
int main(){
 // Exercise the real dispatcher callback and ESD setter interception in the
 // same load. A different lamp, a host or solo play must keep its native path.
 std::array<u8,0x30> evaluator{};
 Set(evaluator,0,image_base+TalkConditionVtableOffset);
 Set(evaluator,0x18,u64{0x40000});
 std::array<u64,1> action_stack{image_base+0x0203F111};
 GuestRegisterSnapshot r;
 auto prompt=[&](u32 talk,u32 function=56){
  Set(evaluator,0x10,talk);r.r15=(u64)evaluator.data();r.rax=function;
  BbscWorldEsdFunction(0,&r);
  r.rsp=(u64)action_stack.data();r.rcx=0;
  BbscWorldTravelActionHook(0,&r);assert(!bbsc_world_travel_action_skip);
  return r.rcx;
 };
 for(const auto [talk,required]:LampTravel::LampAvailabilityFlags){
  state=6;bbsc_world_command_talk=talk;
  const auto command=LampTravel::DreamReturnFlag(talk)+100;
  assert(LampTravel::IsLampActivationCommand(command));
  assert(prompt(talk)==1 && QueueBbscWorldTravel(command,1));
  assert(prompt(talk,52)==0 && prompt(talk,15)==0);
  assert(!QueueBbscWorldTravel(command,0));
  native_flags.insert(required);
  assert(prompt(talk)==0 && !QueueBbscWorldTravel(command,1));
  native_flags.erase(required);
  assert(prompt(talk)==1);
  allowed=false;assert(prompt(talk)==0 && !QueueBbscWorldTravel(command,1));allowed=true;
  for(int role:{0,3}){
   state=role;assert(prompt(talk)==0 && !QueueBbscWorldTravel(command,1));
  }
 }
 state=6;
 for(u32 talk:{241001,290110,290113,210000,210050,241090})assert(prompt(talk)==0);
 bbsc_world_command_talk=241001;assert(!QueueBbscWorldTravel(72410202,1));
 ++action_stack[0];assert(prompt(241002)==0);--action_stack[0];
 Set(evaluator,0,u64{0});assert(prompt(241002)==0);

 std::array<u8,0xc0> instance{};std::array<u8,0x20> instruction{};
 Set(instance,0xb0,(u64)instruction.data());
 Set(instruction,0,s32{2004});Set(instruction,4,s32{14});
 for(int role:{3,6})for(s64 event:{7100,12907010}){
  state=role;native_event=event;++bbsc_world_native_load;
  instance[0x78]=1;const auto original=instruction;
  EnableBbscNativeTravelEvent((u64)instance.data());
  assert(instance[0x78]==0 && instruction==original);
  // A native restart can re-enable synchronization: localize again.
  instance[0x78]=1;EnableBbscNativeTravelEvent((u64)instance.data());assert(!instance[0x78]);
  assert(!LampTravel::IsNativeTravelEvent(event)); // never enters warp preparation
 }
 native_event=7000;++bbsc_world_native_load;instance[0x78]=1;
 EnableBbscNativeTravelEvent((u64)instance.data());assert(instance[0x78]==1);
 allowed=false;native_event=7100;++bbsc_world_native_load;
 EnableBbscNativeTravelEvent((u64)instance.data());assert(instance[0x78]==1);
}
'''

if __name__=='__main__':
 travel.main()
 if len(sys.argv)>1:
  sys.path.insert(0,str(travel.ROOT/'tools/gamedata'))
  from emevd import Emevd
  game=Path(sys.argv[1]);calls=[];availability={}
  for name,event in [('common.emevd.dcx',7100),('m29.emevd.dcx',12907010)]:
   ins=dict(Emevd(game/'event'/name).events)[event]
   assert ins[1]==(3,0,struct.pack('<II',256,0))
   assert ins[2]==(2004,14,struct.pack('<IIII',10000,0,101170,0))
   assert not any(b==2003 and o==49 for b,o,a in ins)
  for f in (game/'event').glob('*.emevd.dcx'):
   for eid,ins in Emevd(f).events:
    for b,o,a in ins:
     if b==2000 and o==0 and len(a)>=16:
      slot,event,flag,obj=struct.unpack_from('<IIII',a)
      if event in (7100,12907010):
       assert flag==70000200+(obj//10000)*10000+obj%100-50
       calls.append((event,flag))
      if event in (7000,12907000):
       _,_,_,entity,required,_=struct.unpack('<6I',a)
       talk=(entity//10000)*1000+entity%100-50+(110 if event==12907000 else 0)
       assert talk not in availability
       availability[talk]=required
  assert sum(e==12907010 for e,f in calls)==9
  assert sum(e==7100 for e,f in calls)==44, len(calls)
  import re
  header=(travel.ROOT/'emulator/src/core/bbsc_lamp_travel_data.h').read_text(encoding='utf-8')
  rules=header.split('LampAvailabilityFlags{{',1)[1].split('}};',1)[0]
  recorded=[tuple(map(int,row)) for row in re.findall(r'\{(\d+), (\d+)\}',rules)]
  assert len(availability)==53 and recorded==sorted((t,f) for t,f in availability.items() if f!=999)
  print('PASS guest prompt conditions match original 7000/12907000 availability flags')
  print('PASS original activation101170 targets local10000; all53 native request parameters, no warp')
 print('PASS guest prompts and writes before/after victory; ordinary/chalice native ignition and restart')
