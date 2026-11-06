"""Actual local travel and snapshot paths; allocated fixtures, read-only ESDs."""
import os
from pathlib import Path
import re
import sys
import test_world_travel_native as travel
import test_world_altars_native as altars


def routing():
    travel.MAIN = r'''
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 Link(0x13cfcc0,reinterpret_cast<void*>(&NativeFlag));
 WriteValue<u64>(image_base+WorldFlagManPointerOffset,0,GetGlobalState());
 bbsc_world_presence_local.world={11,99};
 std::array<u8,128> context{};Set(context,0,image_base+TalkConditionVtableOffset);
 GuestRegisterSnapshot r;r.r14=0x50000;
 auto command=[&](u32 talk,u64 actor){Set(context,0x10,talk);Set(context,0x18,actor);
  NoteBbscWorldTalkRecord(reinterpret_cast<u64>(context.data()),r.r14);r.rax=11;BbscWorldAltarCommand(0,&r);};
 for(s32 role:{6,3})for(bool owner_present:{false,true})for(u32 talk:LampTravel::Talks){
  const u32 flag=LampTravel::DreamReturnFlag(talk);if(!flag)continue;
  state=role;scene_ready=owner_present;snapshot_ready=owner_present;
  const u32 map=talk/1000;current_map=((map/10)<<24)|((map%10)<<16);
  bbsc_world_travel_point=0;bbsc_world_travel_inflight=false;
  command(talk,0x40000);
  r.r15=flag;r.rax=123;BbscWorldLampCommandRange(0,&r);
  if(role==6)assert(r.rax==reinterpret_cast<u64>(bbsc_world_lamp_command.data()));
  assert(BbscWorldTravelFlag(flag)&&QueueBbscWorldTravel(flag,1));
  assert(bbsc_world_travel_point==2102950&&bbsc_world_travel_flag==flag);
  assert(bbsc_world_requested_scope->map==0x15000000&&!bbsc_world_requested_mount);
  const int count=sets;TickBbscWorldTravel();
  assert(sets==count+1&&released==flag); // no resident owner/snapshot is needed to begin native animation
  r.rdi=2102950;BbscWorldNativeWarpBegin(&r);++bbsc_load_generation;
  current_map=0x15000000;TickBbscWorldTravel();assert(!bbsc_world_travel_inflight&&state==role);
 }
 state=6;current_map=0x17000000;command(230000,0x40000);
 assert(!QueueBbscWorldTravel(72300100,0)&&!QueueBbscWorldTravel(72300200,1)&&!QueueBbscWorldTravel(70000100,1)); // activation stays native
 assert(QueueBbscWorldTravel(72300101,1)&&!bbsc_world_travel_point); // wrong lamp
 current_map=0x18000000;assert(QueueBbscWorldTravel(72300100,1)&&!bbsc_world_travel_point);
 current_map=0x17000000;command(230000,0x30000);
 assert(QueueBbscWorldTravel(72300100,1)&&!bbsc_world_travel_point);
 command(230000,0x40000);allowed=false;assert(!QueueBbscWorldTravel(72300100,1));allowed=true;
 state=0;assert(!QueueBbscWorldTravel(72300100,1));state=6;
 for(u32 talk:LampTravel::Talks)if(talk/1000==210)assert(!LampTravel::DreamReturnFlag(talk));
 VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
'''
    travel.main()
    print('PASS46 ordinary/DLC lamps, both roles, owner absent/present, original return release/arrival and negative contexts')


def snapshots():
    source=(travel.ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
    signature='void KeepBbscGuestTalkBits(u32 key, const u8* before, u8* live)'
    start=source.index(signature+' {');p=source.index('{',start)+1;depth=1
    while depth:
        depth+=(source[p]=='{')-(source[p]=='}');p+=1
    actual=source[start:p]
    altars.PREFIX=altars.PREFIX.replace('void KeepBbscGuestTalkBits(u32,const u8*,u8*){}',r'''
constexpr size_t BbscWorldGroupBytes=125;
constexpr std::array<u32,0> BbscGuestGiftTriggerFlags{};
std::mutex bbsc_talk_journal_mutex;std::map<u32,u8> bbsc_talk_journal;
bool BbscIndependentTravelAllowed(){return active;}
'''+actual)
    altars.PREFIX=altars.PREFIX.replace('return static_cast<u32>((Chalice::IsMap(map)?12900:20000)+i);','return (i/10==0?10000:i/10==1?60000:70000)+(map>>24)*100+((map>>16)&255)*10+i%10;')
    altars.MAIN=r'''
int main(){
 std::vector<u32> commands;
 for(u32 talk:LampTravel::Talks)if(const u32 f=LampTravel::DreamReturnFlag(talk)){commands.push_back(f);commands.push_back(f+100);}
 for(u32 talk:LampTravel::DungeonTalks){const auto f=LampTravel::DreamReturnFlag(talk);commands.push_back(f);commands.push_back(f+100);}
 for(const auto& d:LampTravel::Returns)commands.push_back(d.flag);
 for(u32 i=0;i<7;++i)commands.push_back(72100420+i);
 for(u32 i=0;i<10;++i){commands.push_back(72100300+i);commands.push_back(70000200+i);}
 for(int role:{3,6})for(bool value:{false,true})for(const u32 flag:commands){
  session=role;const u32 key=flag/1000;const u32 bit=flag%1000;const u8 mask=0x80u>>(bit%8);
  std::array<u8,125> before{},incoming{};before[bit/8]=value?mask:0;incoming.fill(value?0:255);
  auto live=incoming;KeepBbscGuestTalkBits(key,before.data(),live.data());
  assert(bool(live[bit/8]&mask)==value);
  assert(live[124]==incoming[124]); // other world bits still synchronize
 }
 // Actual independent snapshot path: source is an owner currently in Dream,
 // target is guest's Old Yharnam world. Repeat alternating owner snapshots.
 for(int role:{3,6})for(bool value:{false,true}){
  session=role;groups.clear();groups[72300]={};const u32 bit=100;const u8 mask=0x80u>>(bit%8);
  groups[72300][bit/8]=value?mask:0;
  World::Scope scope{{11,99},0x17000000,{},0};BbscWorldState s;s.flags_ready=true;s.present=u64{1}<<20;
  for(int repeat=0;repeat<6;++repeat){s.groups[20].fill(repeat%2?255:0);BbscWorldApplyFlags(scope,s);
   assert(bool(groups[72300][bit/8]&mask)==value);
  }
 }
 active=false;std::array<u8,125> before{},live{};live.fill(255);
 KeepBbscGuestTalkBits(72300,before.data(),live.data());assert(live[12]==255);
}
'''
    altars.main()
    print('PASS actual snapshot apply and local-command preservation: owner changes, both roles, both bit values, unrelated bits and disabled mode')


def assets(game):
    sys.path.insert(0,str(travel.ROOT/'tools/gamedata'))
    import bbfiles,esd
    header=(travel.ROOT/'emulator/src/core/bbsc_lamp_travel_data.h').read_text()
    ordinary=set(map(int,re.findall(r'\d+',re.search(r'51> Talks\{([^}]+)',header).group(1))))
    ordinary={t for t in ordinary if t//1000!=210}
    found=set()
    for path in sorted((game/'script/talk').glob('*.talkesdbnd.dcx')):
        if path.name.startswith('m10_'):continue
        for name,(_,raw) in bbfiles.read_bnd4(bbfiles.read_dcx(path)).items():
            if not(name.startswith('t') and name.endswith('.esd')):continue
            commands=esd.Esd(raw).all_commands()
            returns=[a for g,s,b,i,a in commands if b==1 and i==11 and '70000100' in str(a)]
            if not returns:continue
            if name=='t210692.esd':
                assert returns==[['70000100','1']] # workbench request, NOT lamp travel
                continue
            talk=int(name[1:-4]);found.add(talk)
            calls=[a for g,s,b,i,a in commands if b==6 and i==2147483646]
            assert len(calls)==1,(name,calls)
            call=calls[0];assert len(call)>=6,(path.name,name,call,returns);area,index=map(int,call[4:6])
            assert returns==[['(((arg[0] / 10000) + 70000100) + (arg[1] / 1))','1']]
            assert (area,index)==((290,talk-290110) if area==290 else (talk//1000,talk%1000))
    assert found==ordinary|set(range(290110,290120)),found^ordinary^set(range(290110,290120))
    print('PASS exhaustive original ESD survey:46 ordinary/DLC +10 dungeon return commands; activation is distinct')


if __name__=='__main__':
    routing()
    snapshots()
    if os.environ.get('BBSC_TEST_GAME'):assets(Path(os.environ['BBSC_TEST_GAME']))
