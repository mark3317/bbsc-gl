"""Production travel starts native animation while destination data is late."""
import test_world_travel_native as travel

travel.MAIN=r'''
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 Link(0x13cfcc0,reinterpret_cast<void*>(&NativeFlag));
 WriteValue<u64>(image_base+WorldFlagManPointerOffset,0,GetGlobalState());
 bbsc_world_presence_local.world={11,99};bbsc_world_catalog_ready=true;
 std::array<u8,128> context{};Set(context,0,image_base+TalkConditionVtableOffset);
 GuestRegisterSnapshot r;r.r14=0x50000;
 auto command=[&](u32 talk,s32 id){Set(context,0x10,talk);Set(context,0x18,u64{0x40000});
  NoteBbscWorldTalkRecord(reinterpret_cast<u64>(context.data()),r.r14);r.rax=id;BbscWorldAltarCommand(0,&r);};
 std::array<u8,0xc0> instance{};std::array<u8,0x20> instruction{};
 Set(instance,0xb0,reinterpret_cast<u64>(instruction.data()));r.rbx=reinterpret_cast<u64>(instance.data());
 for(int role:{3,6})for(int route=0;route<4;++route){
  state=role;snapshot_ready=false;chalice_ready=false;now+=1000;
  bbsc_world_travel_point=0;bbsc_world_travel_inflight=false;bbsc_world_travel_native_armed=false;
  bbsc_world_requested_mount.reset();bbsc_world_requested_scope.reset();
  u32 flag;
  if(route==0){current_map=0x17000000;command(230000,11);flag=72300100;native_event=7200;}
  if(route==1){current_map=0x1d000000;command(290111,11);flag=72900101;native_event=12907020;}
  if(route==2){current_map=0x15000000;command(210000,11);flag=LampTravel::Returns[0].flag;native_event=12107000;}
  if(route==3){
   current_map=0x15000000;auto& altar=bbsc_world_altars[0];altar.entry.occupied=true;altar.entry.ritual=36;
   altar.mount.key={55,66,88,0};altar.mount.revision=36;
   command(210050,79);const int before=sent;
   assert(!QueueBbscWorldTravel(72100420,1));
   assert(sent==before+1&&!bbsc_world_requested_scope&&!bbsc_world_travel_point);
   // Preparation started with the FIRST native altar command, before its animation.
   flag=72100300;native_event=12107200;
  }
  assert(QueueBbscWorldTravel(flag,1));
  const int count=sets,before=sent;TickBbscWorldTravel();
  assert(sets==count+1&&released==flag&&sent>before&&bbsc_world_travel_inflight);
  // Missing destination data and mount readiness NEVER block animation or native wait.
  for(const auto [bank,op]:{std::pair{2004,14},std::pair{1001,0}}){
   Set(instruction,0,s32{bank});Set(instruction,4,s32{op});const auto unchanged=instruction;
   BbscWorldTravelDispatch(0,&r);assert(!bbsc_world_travel_dispatch_skip&&instruction==unchanged);
  }
  Set(instruction,0,s32{2003});Set(instruction,4,s32{49});const auto unchanged=instruction;
  BbscWorldTravelDispatch(0,&r);assert(bbsc_world_travel_dispatch_skip&&instruction==unchanged);
  snapshot_ready=true;BbscWorldTravelDispatch(0,&r);
  assert(bool(bbsc_world_travel_dispatch_skip)==(route==3)); // cup still needs native descriptor
  if(route==3){
   const auto trip=bbsc_world_travel_since;now+=91000;TickBbscWorldTravel();
   assert(bbsc_world_travel_inflight&&sets==count+1&&bbsc_world_travel_since==trip);
  }
  chalice_ready=true;BbscWorldTravelDispatch(0,&r);assert(!bbsc_world_travel_dispatch_skip);
  const s64 event=native_event;native_event=12300000;snapshot_ready=false;
  BbscWorldTravelDispatch(0,&r);assert(!bbsc_world_travel_dispatch_skip);native_event=event;
  snapshot_ready=true;r.rdi=bbsc_world_travel_point;BbscWorldNativeWarpBegin(&r);
  ++bbsc_load_generation;current_map=bbsc_world_requested_scope->map;TickBbscWorldTravel();
  assert(!bbsc_world_travel_inflight&&state==role&&sets==count+1);
 }
 VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
'''

if __name__=='__main__':
    travel.main()
    print('PASS both roles: ordinary/dungeon return, headstone and cup entry; prepare with animation; only native warp waits; no timeout bypass or replay')
