"""Production dungeon-lamp return routing; allocated memory and read-only assets."""
import os
from pathlib import Path
import sys
import test_world_travel_native as travel

travel.MAIN=r'''
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 Link(0x13cfcc0,reinterpret_cast<void*>(&NativeFlag));
 WriteValue<u64>(image_base+WorldFlagManPointerOffset,0,GetGlobalState());
 bbsc_world_presence_local.world={11,99};
 std::array<u8,128> context{};Set(context,0,image_base+TalkConditionVtableOffset);
 GuestRegisterSnapshot r;r.r14=0x50000;
 auto command=[&](u32 talk,u64 actor){Set(context,0x10,talk);Set(context,0x18,actor);
  NoteBbscWorldTalkRecord(reinterpret_cast<u64>(context.data()),r.r14);r.rax=11;BbscWorldAltarCommand(0,&r);};
 for(s32 role:{6,3})for(u32 lamp=0;lamp<10;++lamp){
  state=role;current_map=0x1D000000;bbsc_world_travel_point=0;bbsc_world_travel_inflight=false;
  bbsc_world_requested_mount=Chalice::Mount{};bbsc_world_altar_visiting=2;
  command(290110+lamp,0x40000);const u32 flag=72900100+lamp;
  r.r15=flag;r.rax=123;BbscWorldLampCommandRange(0,&r);
  if(role==6)assert(r.rax==reinterpret_cast<u64>(bbsc_world_lamp_command.data()));
  assert(QueueBbscWorldTravel(flag,1));
  assert(bbsc_world_travel_point==2102950&&bbsc_world_travel_flag==flag);
  assert(bbsc_world_requested_scope->map==0x15000000&&bbsc_world_requested_scope->ritual==0);
  assert(!bbsc_world_requested_mount&&bbsc_world_altar_visiting==2); // source cup identity survives animation
  snapshot_ready=true;const int count=sets;TickBbscWorldTravel();
  assert(sets==count+1&&released==flag); // ORIGINAL request, never substitute activation/other lamp
  r.rdi=2102950;BbscWorldNativeWarpBegin(&r);assert(bbsc_world_altar_visiting==-1);
  ++bbsc_load_generation;current_map=0x15000000;TickBbscWorldTravel();
  assert(!bbsc_world_travel_inflight&&!bbsc_world_travel_point&&state==role);
 }
 state=6;current_map=0x1D000000;command(290110,0x40000);
 assert(!QueueBbscWorldTravel(72900100,0)&&!QueueBbscWorldTravel(72900200,1)); // activation is not return
 assert(QueueBbscWorldTravel(72900101,1)&&!bbsc_world_travel_point); // different lamp
 command(290600,0x40000);assert(QueueBbscWorldTravel(72900100,1)&&!bbsc_world_travel_point);
 command(290110,0x30000);assert(QueueBbscWorldTravel(72900100,1)&&!bbsc_world_travel_point);
 command(290110,0x40000);current_map=0x18010000;
 assert(QueueBbscWorldTravel(72900100,1)&&!bbsc_world_travel_point);
 current_map=0x1D000000;allowed=false;assert(!QueueBbscWorldTravel(72900100,1));allowed=true;
 state=0;assert(!QueueBbscWorldTravel(72900100,1));
 VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
'''

if __name__=='__main__':
    travel.main()
    print('PASS ten dungeon lamps, both roles, original return flag/release/arrival, cleared ritual and invalid contexts')
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
