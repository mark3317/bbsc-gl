"""Execute load-only native state transfer; no live game, settings or saves."""
from pathlib import Path
import os, subprocess, tempfile
import test_world_native_initial as fixture
import test_independent_native as native

ROOT=Path(__file__).resolve().parents[1]
code=fixture.SOURCE
for actual,mock in [('reinterpret_cast<Apply>(image_base+0x0190E8B0)','MockApply'),
                    ('reinterpret_cast<Send>(image_base+0x01786360)','MockSend'),
                    ('reinterpret_cast<Receive>(image_base+0x01789200)','MockReceive')]:
    code=code.replace(actual,mock)
helpers=fixture.MAIN[:fixture.MAIN.index('int main(){')]
main=r'''
int main(){
 auto& local=bbsc_world_presence_local;
 local.world={11,99};local.map=current_map;local.phase=World::Phase::Playing;local.visit=1;local.sequence=1;
 auto resident=local;resident.visit=7;
 std::map<u32,World::Member> roster{{11,{local,10000,9000}},{22,{resident,10000,9001}}};
 assert(World::ChooseOwner(local,roster,11,10000)==11);
 roster[11].presence.phase=World::Phase::Loading;
 assert(World::ChooseOwner(resident,roster,11,10000)==22);
 roster[11].presence=local;
 assert(World::ChooseOwner(local,roster,22,10000)==22); // host returns, resident stays
 bbsc_world_presence_book.Bind(local.world,11);
 assert(bbsc_world_presence_book.Hear(22,local.world,resident,now));
 auto scope=World::ScopeOf(local);bbsc_independent_owners.Bind(local.world);
 World::Control lease;lease.scope=scope;lease.owner=22;lease.epoch=7;
 assert(bbsc_independent_owners.Take(11,lease,now));
 BbscWorldNativeInitialOnce(scope);assert(sent.size()==1);
 auto request=sent.back().control;
 // Neither elapsed time nor repeated load callbacks cause a resend.
 for(int i=0;i<2000;++i){now+=10000;BbscWorldNativeInitialOnce(scope);}
 assert(sent.size()==1&&received.empty()&&native_sends==0);
 put(world,0x278,s32(3));put(world,0x280,u64(1));put(world,0x290,addr(block));
 put(block,8,addr(mapdata));put(mapdata,8,current_map);put(block,0xB8,s32(2));put(block,0xC0,addr(entries));
 packet=make();
 // Use a valid large native packet so existing control framing is exercised.
 packet.insert(packet.begin()+4,2200,0);u32 section=2200;std::memcpy(packet.data(),&section,4);
 assert(World::NativeInitialCharacters(packet));
 self=22;local=resident;bbsc_world_presence_book.Bind(local.world,22);
 auto visitor=roster[11].presence;visitor.phase=World::Phase::Loading;visitor.map=0x15000000;
 assert(bbsc_world_presence_book.Hear(11,local.world,visitor,now));
 sent.clear();BbscWorldNativeInitialControl({11,request,{}});
 assert(native_sends==1&&sent.size()==2&&!bbsc_world_initial_capture);
 BbscWorldNativeInitialControl({11,request,{}});assert(native_sends==1&&sent.size()==2);
 auto replies=sent;
 for(const auto& reply:replies){auto wire=World::Encode(reply.control,reply.payload);assert(World::DecodeControl(wire));}
 self=11;local=visitor;current_map=scope.map;bbsc_world_presence_book.Bind(local.world,11);
 assert(bbsc_world_presence_book.Hear(22,local.world,resident,now));
 auto stale=replies[0];++stale.control.sequence;BbscWorldNativeInitialControl({22,stale.control,stale.payload});
 assert(!bbsc_world_initial_once.received&&!applied);
 // Out-of-order/duplicate frames are events, not a receive polling loop.
 BbscWorldNativeInitialControl({22,replies[1].control,replies[1].payload});assert(!applied);
 BbscWorldNativeInitialControl({22,replies[1].control,replies[1].payload});assert(!applied);
 BbscWorldNativeInitialControl({22,replies[0].control,replies[0].payload});assert(applied==1);
 BbscWorldNativeInitialControl({22,replies[0].control,replies[0].payload});assert(applied==1);
 for(int i=0;i<2000;++i)BbscWorldNativeInitialOnce(scope);
 assert(applied==1&&received.empty()&&native_sends==1);
 ++bbsc_world_native_load;sent.clear();wipe_scope=scope;
 BbscWorldNativeInitialOnce(scope);assert(sent.empty()); // no previous-attempt deaths on a wipe
 for(const auto& reply:replies)BbscWorldNativeInitialControl({22,reply.control,reply.payload});
 assert(applied==1&&!bbsc_world_initial_once.received); // old load cannot satisfy new load
 wipe_scope.reset();++bbsc_world_native_load;BbscWorldNativeInitialOnce(scope);assert(sent.size()==1);
 // Another guest follows exactly the same load path as the native room host.
 self=33;++bbsc_world_native_load;sent.clear();BbscWorldNativeInitialOnce(scope);
 assert(sent.size()==1&&sent.back().control.owner==33);
 // Failed native preflight is consumed once too; no repair loop or event hold.
 auto reply=sent.back().control;reply.kind=World::ControlKind::NativeInitialReady;reply.owner=22;
 put(block,0xB8,s32(3));auto small=make();
 BbscWorldNativeInitialControl({22,reply,small});assert(bbsc_world_initial_once.consumed&&applied==1);
 put(block,0xB8,s32(2));BbscWorldNativeInitialControl({22,reply,small});assert(applied==1);
 puts("PASS one-shot resident transfer: host departure/return, guest arrival, native bytes, fragments, stale/duplicate/load fences, no polls/retries");
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-native-once-') as tmp:
    cpp=Path(tmp)/'once.cpp';exe=Path(tmp)/'once.exe'
    cpp.write_text(fixture.PREFIX+code+helpers+main,encoding='utf8')
    compiler='C:/msys64/clang64/bin/clang++.exe'
    env=dict(os.environ,PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH',''),BBSC_NATIVE_NPC_SYNC_TEST='1')
    subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True,env=env)
    subprocess.run([str(exe)],check=True,env=env)

    # Execute the actual packet capture. All unrelated packets must be untouched.
    callbacks=native.PREFIX+native.function('void PS4_SYSV_ABI BbscWorldPacketSend(u64,const GuestRegisterSnapshot* regs)')
    cpp.write_text(callbacks+r'''
int main(){active=true;std::vector<u8> packet(3000,42),captured;GuestRegisterSnapshot r;
 r.rdx=0x11;r.r8=packet.size();r.rcx=reinterpret_cast<u64>(packet.data());r.rax=99;
 BbscWorldPacketSend(0,&r);assert(r.rax==99&&!bbsc_independent_send_skip);
 bbsc_world_initial_capture=&captured;BbscWorldPacketSend(0,&r);
 assert(captured==packet&&r.rax==1&&bbsc_independent_send_skip);
 for(u32 ch:{4u,5u,0x15u,0x16u,0x17u,0x2fu,0x34u,0x43u}){
  bbsc_independent_send_skip=0;r.rdx=ch;r.rax=99;
  BbscWorldPacketSend(0,&r);assert(r.rax==99&&!bbsc_independent_send_skip);
 }
 puts("PASS production capture: only explicit native initial serialization; native combat/ownership packets unchanged");
}
''',encoding='utf8')
    subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True,env=env)
    subprocess.run([str(exe)],check=True,env=env)
