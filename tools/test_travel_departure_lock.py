"""Single native animation and pre-side-effect interaction gate; read-only ELF input."""
from pathlib import Path
import os, re, struct, subprocess, tempfile
import test_world_travel_native as travel


def main():
    elf=Path(os.environ['BBSC_TEST_EBOOT']).read_bytes()
    ph=struct.unpack_from('<Q',elf,32)[0];size,n=struct.unpack_from('<HH',elf,54)
    segments=[struct.unpack_from('<II6Q',elf,ph+i*size) for i in range(n)]
    def read(a,n):
        s=next(s for s in segments if s[0]==1 and s[3]<=a and a+n<=s[3]+s[5])
        return elf[s[2]+a-s[3]:s[2]+a-s[3]+n]
    bank=read(0x17ba6a0,0x2a00);action=read(0x1cd91f0,0x7a);tail=read(0x1cd97d6,0x25)
    assert bank[:8]==bytes.fromhex('554889e541574156')
    assert action[:6]==bytes.fromhex('554889e54157')
    source=(travel.ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
    callback=source[source.index('void PS4_SYSV_ABI BbscBellRefundHook('):source.index('\nvoid InstallBbscBellRefundHook()')]
    prefix=re.sub(r'struct GuestRegisterSnapshot\{[^\n]+\};',
        '#include "core/cpu_patches.h"\nusing Core::GuestRegisterSnapshot;\nusing Core::InstallGuestCodeHook;',travel.PREFIX)
    prefix=prefix.replace('#define NOMINMAX\n','').replace('#define WIN32_LEAN_AND_MEAN\n','')
    prefix+=r'''
#define BBSC_MOD
#define LOG_INFO(...)
bool EnvFlagEnabled(const char*){return false;}
bool BbscNpcRewardAllowed(u32){return true;}
s64 BbscRunningEventId(u64 p){return BbscEventIdOf(p);}
void ObserveBbscNativeWorldCommand(u64,s32){}
u8 bbsc_bell_refund_skip=0;
namespace BbscMod {u64 EbootAddress(){return image_base;} void LogPlain(const char*){}}
int native_animations=0,native_action_state=0;
void PS4_SYSV_ABI OriginalAnimationTask(u64,s32 actor,s32 target,s32 animation){
 assert(actor==10000&&target==0&&(animation==101160||animation==101164));
 ++native_animations;++native_action_state;
}
'''+callback
    production=travel.SOURCE[travel.SOURCE.index('s32 bbsc_world_travel_point='):travel.SOURCE.index('void InstallBbscWorldTravel() {')]
    body=r'''
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(image_base);
 Link(0x13cfcc0,(void*)&NativeFlag);
 const u8 bank[]={BANK},action[]={ACTION},tail[]={TAIL};
 memcpy((void*)(image_base+0x17ba6a0),bank,sizeof(bank));
 memcpy((void*)(image_base+0x1cd91f0),action,sizeof(action));
 memcpy((void*)(image_base+0x1cd97d6),tail,sizeof(tail));
 *(u8*)(image_base+0x1f128a0)=0xc3;
 u64 cookie=0,cookie_ptr=(u64)&cookie;memcpy((void*)(image_base+0x53e3be0),&cookie_ptr,8);
 u64 event_manager=(u64)global.data();memcpy((void*)(image_base+0x553b108),&event_manager,8);
 // Native's first instruction AFTER early rejection. Passing the input gate
 // would execute this sentinel; a rejected trip action must never reach it.
 u8 accepted[]={0xb8,1,0,0,0,0xe9,0x62,5,0,0};
 memcpy((void*)(image_base+0x1cd926a),accepted,sizeof(accepted));
 Link(0x13e0d80,(void*)&OriginalAnimationTask);
 assert(InstallGuestCodeHook((void*)(image_base+0x17ba6a0),{bank,8},0,BbscBellRefundHook,&bbsc_bell_refund_skip));
 assert(InstallGuestCodeHook((void*)(image_base+0x1cd91f0),{action,6},0,BbscWorldTravelActionHook,&bbsc_world_travel_action_skip));
 using Accept=int PS4_SYSV_ABI (*)(u64,u64,u64,u64,u64,u64);
 using Bank=bool PS4_SYSV_ABI (*)(u64,u64);
 auto accept=(Accept)(image_base+0x1cd91f0);auto execute=(Bank)(image_base+0x17ba6a0);
 std::array<u8,128> context{};Set(context,0,image_base+TalkConditionVtableOffset);Set(context,0x18,u64{0x40000});
 GuestRegisterSnapshot r{};r.r14=0x50000;
 std::array<u8,0xd0> instance{};std::array<u8,0x20> instruction{};
 std::array<u32,4> args{10000,0,101164,0};Set(instance,0x60,u32{10000});
 Set(instance,0xb0,(u64)instruction.data());Set(instance,0xb8,(u64)args.data());
 Set(instruction,0,s32{2004});Set(instruction,4,s32{14});
 bbsc_world_presence_local.world={11,99};
 auto command=[&](u32 talk){Set(context,0x10,talk);NoteBbscWorldTalkRecord((u64)context.data(),r.r14);r.rax=11;BbscWorldAltarCommand(0,&r);};
 auto buttons=[&](bool blocked){for(u32 id:{7030u,6030u,3200000u,3200001u,1000u}){
  assert(accept(0,0,id,0,0,0)==(blocked?0:1));assert(bbsc_world_travel_action_skip==0);
 }};
 for(int role:{3,6})for(int route=0;route<3;++route){
  state=role;allowed=true;hp=594;global[8]=0;bbsc_world_load_pending=0;bbsc_reload_finish_pending=false;
  bbsc_world_travel_point=0;bbsc_world_travel_inflight=false;bbsc_world_travel_altar_pending=-1;
  bbsc_world_requested_mount.reset();bbsc_world_requested_scope.reset();snapshot_ready=false;
  const u32 talk=route==0?210000:route==1?270000:290110;
  current_map=route==0?0x15000000:route==1?0x1b000000:0x1d000000;
  const u32 flag=route==0?72102700:LampTravel::DreamReturnFlag(talk);
  native_event=route==0?12107000:route==1?7200:12907020;
  args[2]=route==0?101164:101160;command(talk);buttons(false);
  const int early=animations,original=native_animations,actions=native_action_state;
  assert(QueueBbscWorldTravel(flag,1));assert(animations==early);buttons(true);
  assert(QueueBbscWorldTravel(flag,1));assert(animations==early);buttons(true);
  TickBbscWorldTravel();buttons(true);
  now+=5600;TickBbscWorldTravel();assert(animations==early);buttons(true);
  assert(execute(0,(u64)instance.data()));
  assert(native_animations==original+1&&native_action_state==actions+1);buttons(true);
  now+=4000;TickBbscWorldTravel();buttons(true);
  std::array<u8,0x20> warp{};Set(warp,0,s32{2003});Set(warp,4,s32{49});
  Set(instance,0xb0,(u64)warp.data());r.rbx=(u64)instance.data();BbscWorldTravelDispatch(0,&r);
  assert(bbsc_world_travel_dispatch_skip);buttons(true);Set(instance,0xb0,(u64)instruction.data());
  snapshot_ready=true;chalice_ready=true;r.rdi=route==0?2702950:2102950;BbscWorldNativeWarpBegin(&r);
  buttons(true);global[8]=1;TickBbscWorldTravel();buttons(true);
  global[8]=0;++bbsc_load_generation;TickBbscWorldTravel();buttons(false);
  assert(native_animations==original+1&&animations==early);
  command(talk);assert(QueueBbscWorldTravel(flag,1));buttons(true);
  hp=0;buttons(false);hp=594;++bbsc_world_presence_local.world.room;buttons(false);
  --bbsc_world_presence_local.world.room;buttons(true);allowed=false;buttons(false);allowed=true;
  state=0;buttons(false);state=role;bbsc_world_travel_point=0;bbsc_world_travel_inflight=false;buttons(false);
 }
 // Every altar has TWO commands, but only the first native event animates.
 // Layer selection/cancel remains possible in its existing menu; no world
 // interaction may reopen after the layer's actual travel is accepted.
 bbsc_world_catalog_ready=true;current_map=0x15000000;args[2]=101164;
 for(int role:{3,6})for(int slot=0;slot<7;++slot){
  state=role;native_event=12107100;bbsc_world_travel_point=0;bbsc_world_travel_inflight=false;
  bbsc_world_travel_altar_pending=-1;bbsc_world_requested_mount.reset();bbsc_world_requested_scope.reset();
  auto& altar=bbsc_world_altars[slot];altar.entry.occupied=true;altar.entry.ritual=100+slot;
  altar.mount.key={55,66,u32(88+slot),0};altar.mount.revision=altar.entry.ritual;
  Set(context,0x10,u32(210050+slot*10));NoteBbscWorldTalkRecord((u64)context.data(),r.r14);
  r.rax=79;BbscWorldAltarCommand(0,&r);const int original=native_animations,early=animations;
  assert(!QueueBbscWorldTravel(72100420+slot,1));buttons(false);
  native_flags.insert(72100420+slot);assert(QueueBbscWorldTravel(72100420+slot,1));
  assert(execute(0,(u64)instance.data()));assert(native_animations==original+1);
  native_flags.erase(72100420+slot);now+=4100;
  NoteBbscWorldTalkRecord((u64)context.data(),r.r14);r.rax=79;BbscWorldAltarCommand(0,&r);
  assert(QueueBbscWorldTravel(72100300,1));buttons(true);
  assert(animations==early&&native_animations==original+1);
  bbsc_world_travel_point=0;bbsc_world_travel_inflight=false;buttons(false);
 }
 assert(accept(0,0,7030,1,0,0)==0);
 VirtualFree((void*)image_base,0,MEM_RELEASE);
}
'''
    for key,data in [('BANK',bank),('ACTION',action),('TAIL',tail)]:body=body.replace(key,','.join(str(v) for v in data))
    compiler='C:/msys64/clang64/bin/clang++.exe'
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    with tempfile.TemporaryDirectory(prefix='bbsc-departure-lock-') as tmp:
        cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe'
        for label,changed,success in [
            ('fixed',production,True),
            ('eager-animation-negative',production.replace('    bbsc_world_travel_departure_load=bbsc_load_generation.load();',
                '    NativeAnimation(10000,101164,0,0);\n    bbsc_world_travel_departure_load=bbsc_load_generation.load();'),False),
            ('no-input-gate-negative',production.replace('if(!regs || !BbscWorldTravelInteractionBlocked())return;','if(true)return;'),False),
        ]:
            cpp.write_text(prefix+changed+body,encoding='utf-8')
            subprocess.run([compiler,'-std=c++20','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-I',str(travel.ROOT/'emulator/src'),'-I',str(travel.ROOT/'emulator/externals/xbyak'),
                str(cpp),str(travel.ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True,env=env)
            run=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=20)
            assert (run.returncode==0)==success,(label,run.returncode,run.stdout,run.stderr)
            print('PASS',label)
    print('PASS original bank2004/action ENTRY with production DLL trampolines: both roles, headstones/ordinary/chalice; single native animation and action state; input gate through delayed condition/late destination/load; cancellation fences')


if __name__=='__main__':main()
