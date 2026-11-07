"""Production dungeon-lamp return routing; allocated memory and read-only assets."""
import os
from pathlib import Path
import sys
import struct
import test_world_travel_native as travel

travel.MAIN=r'''
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 Link(0x13cfcc0,reinterpret_cast<void*>(&NativeFlag));
 WriteValue<u64>(image_base+WorldFlagManPointerOffset,0,GetGlobalState());
 bbsc_world_presence_local.world={11,99};
 std::memset(bbsc_world_lamp_command.data()+0xA0,0xFF,8); // production installation
 // ORIGINAL_RANGE_SETUP
 std::array<u8,128> context{};Set(context,0,image_base+TalkConditionVtableOffset);
 GuestRegisterSnapshot r;r.r14=0x50000;
 auto command=[&](u32 talk,u64 actor){Set(context,0x10,talk);Set(context,0x18,actor);
  NoteBbscWorldTalkRecord(reinterpret_cast<u64>(context.data()),r.r14);r.rax=11;BbscWorldAltarCommand(0,&r);};
 for(s32 role:{0,6,3})for(u32 lamp=0;lamp<10;++lamp){
  state=role;current_map=0x1D000000;bbsc_world_travel_point=0;bbsc_world_travel_inflight=false;
  bbsc_world_requested_mount=Chalice::Mount{};bbsc_world_altar_visiting=2;
  command(290110+lamp,0x40000);const u32 flag=72900100+lamp;
  const u32 availability=LampTravel::AvailabilityFlag(290110+lamp);
  if(availability)native_flags.insert(availability); // the original lamp is available
  r.r15=flag;r.rax=123;BbscWorldLampCommandRange(0,&r);
  if(role==6)assert(r.rax==reinterpret_cast<u64>(bbsc_world_lamp_command.data()));
  for(u32 request:{flag,flag+100}){
   assert(BbscWorldTravelFlag(request)); // neither request is personal quest progress
   r.r15=request;r.rax=123;BbscWorldLampCommandRange(0,&r);
   if(role==6)assert(r.rax==reinterpret_cast<u64>(bbsc_world_lamp_command.data()));
   else assert(r.rax==123); // native solo/host range unchanged
   // ORIGINAL_RANGE_CHECK
   assert(!QueueBbscWorldTravel(request,1)); // native SetFlag runs immediately
  }
  if(availability)native_flags.erase(availability);
  assert(!bbsc_world_travel_point&&!bbsc_world_travel_inflight);
  assert(bbsc_world_requested_mount&&bbsc_world_altar_visiting==2);
  snapshot_ready=false;const int count=sets,before=sent;TickBbscWorldTravel();
  assert(sets==count&&sent==before); // no synthetic request or destination wait
  std::array<u8,0xc0> instance{};std::array<u8,0x20> instruction{};
  Set(instance,0xb0,(u64)instruction.data());Set(instruction,0,s32{2003});Set(instruction,4,s32{49});
  r.rbx=(u64)instance.data();native_event=12907020;BbscWorldTravelDispatch(0,&r);
  assert(!bbsc_world_travel_dispatch_skip); // original stage request cannot wait on snapshots
  if(role==0)continue;
  r.rdi=2102954+lamp%7;BbscWorldNativeWarpBegin(&r);
  assert(bbsc_world_travel_point==s32(r.rdi)&&bbsc_world_travel_native_armed);
  assert(bbsc_world_requested_scope->map==0x15000000&&bbsc_world_requested_scope->ritual==0);
  assert(!bbsc_world_requested_mount&&bbsc_world_altar_visiting==-1);
  ++bbsc_load_generation;current_map=0x15000000;TickBbscWorldTravel();
  assert(!bbsc_world_travel_inflight&&!bbsc_world_travel_point&&state==role);
 }
 state=6;current_map=0x1D000000;command(290110,0x40000);
 assert(!QueueBbscWorldTravel(72900100,0)&&!QueueBbscWorldTravel(72900200,1)); // activation is not return
 assert(!QueueBbscWorldTravel(72900101,1)&&!bbsc_world_travel_point); // original ESD validates context
 command(290600,0x40000);assert(!QueueBbscWorldTravel(72900100,1)&&!bbsc_world_travel_point);
 command(290110,0x30000);assert(!QueueBbscWorldTravel(72900100,1)&&!bbsc_world_travel_point);
 command(290110,0x40000);current_map=0x18010000;
 assert(!QueueBbscWorldTravel(72900100,1)&&!bbsc_world_travel_point);
 current_map=0x1D000000;allowed=false;assert(!QueueBbscWorldTravel(72900100,1));allowed=true;
 state=0;assert(!QueueBbscWorldTravel(72900100,1));
 VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
'''

if __name__=='__main__':
    if os.environ.get('BBSC_TEST_EBOOT'):
        data=Path(os.environ['BBSC_TEST_EBOOT']).read_bytes()
        ph=struct.unpack_from('<Q',data,32)[0];size,count=struct.unpack_from('<HH',data,54)
        segments=[struct.unpack_from('<II6Q',data,ph+i*size) for i in range(count)]
        segment=next(s for s in segments if s[0]==1 and s[3]<=0x204232e and 0x2042356<=s[3]+s[5])
        start=segment[2]+0x204232e-segment[3]
        original=data[start:start+0x28]
        assert original[:9]==bytes.fromhex('8b88a000000083f9ff')
        travel.PREFIX+='\nconst u8 original_range[]={'+','.join(map(str,original))+'};\n'
        travel.MAIN=travel.MAIN.replace('// ORIGINAL_RANGE_SETUP',r'''
 std::memcpy((void*)(image_base+0x204232e),original_range,sizeof(original_range));
 const u8 accept[]={0xb8,1,0,0,0,0xc3},reject[]={0x31,0xc0,0xc3};
 std::memcpy((void*)(image_base+0x2042356),accept,sizeof(accept));
 std::memcpy((void*)(image_base+0x20441de),reject,sizeof(reject));
 // Preserve native R15; feed native RAX=executor, R15D=request.
 const u8 entry[]={0x41,0x57,0x48,0x89,0xf8,0x41,0x89,0xf7,0xe8,0,0,0,0,0x41,0x5f,0xc3};
 std::memcpy((void*)(image_base+0x2042200),entry,sizeof(entry));
 WriteValue<s32>(image_base+0x2042200,9,0x204232e - (0x2042200+13));
 auto native_range=reinterpret_cast<s32 PS4_SYSV_ABI (*)(u64,u32)>(image_base+0x2042200);
 std::array<u8,0xc0> bounded{};
 Set(bounded,0xa0,u32{72900100});Set(bounded,0xa4,u32{72900109});
 assert(native_range((u64)bounded.data(),72900100)==1);
 assert(native_range((u64)bounded.data(),72900200)==0);
''').replace('// ORIGINAL_RANGE_CHECK',r'''
   if(role==6)assert(native_range(r.rax,request)==1); // actual native range instructions, both commands
''')
    travel.main()
    print('PASS ten dungeon lamps: solo/host/guest native requests, no queue/wait, seven original Dream destinations')
    if os.environ.get('BBSC_TEST_GAME'):
        sys.path.insert(0,str(travel.ROOT/'tools/gamedata'))
        import bbfiles,esd
        game=Path(os.environ['BBSC_TEST_GAME'])
        files=bbfiles.read_bnd4(bbfiles.read_dcx(game/'script/talk/m29_00_00_00.talkesdbnd.dcx'))
        for lamp in range(10):
            script=esd.Esd(files[f't{290110+lamp}.esd'][1])
            commands=script.all_commands()
            call=next(args for g,s,b,i,args in commands if b==6 and i==2147483646)
            assert call[-2:]==['290',str(lamp)]
            # The reader's legacy '/' notation represents the ESD multiply opcode.
            returns=[args for g,s,b,i,args in commands if b==1 and i==11 and '70000100' in str(args)]
            assert len(returns)==1 and returns[0]==['(((arg[0] / 10000) + 70000100) + (arg[1] / 1))','1']
        print('PASS original ten dungeon ESD return requests: 70000100 + 290*10000 + lamp = 72900100..109')
