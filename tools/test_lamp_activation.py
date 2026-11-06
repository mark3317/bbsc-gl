"""Local lamp ignition events and original-data contract; no live writes."""
from pathlib import Path
import struct
import sys
import test_world_travel_native as travel

travel.MAIN = r'''
int main(){
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
  game=Path(sys.argv[1]);calls=[]
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
  assert sum(e==12907010 for e,f in calls)==9
  assert sum(e==7100 for e,f in calls)==44, len(calls)
  print('PASS original activation101170 targets local10000; all53 native request parameters, no warp')
 print('PASS ordinary/chalice ignition: both roles, native restart, shared lamp visibility untouched, feature off')
