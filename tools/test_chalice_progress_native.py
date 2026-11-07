"""Production cup seeding / owner receive / native host storage, allocated memory.

Runs the original 1.09 group mapper and its tables. No live save or process access.
"""
from pathlib import Path
import os, struct, subprocess, tempfile
import test_world_altars_native as altars

ROOT = altars.ROOT
SOURCE = (ROOT/'emulator/src/core/bbsc_world_state.inc').read_text(encoding='utf-8')
LAMPS = (ROOT/'emulator/src/core/bbsc_world_lamps.inc').read_text(encoding='utf-8')

def function(source, signature):
    a=source.index(signature+' {');p=source.index('{',a)+1;depth=1
    while depth:
        depth+=(source[p]=='{')-(source[p]=='}');p+=1
    return source[a:p]+'\n'

def original():
    data=Path(os.environ['BBSC_TEST_EBOOT']).read_bytes()
    ph=struct.unpack_from('<Q',data,32)[0];size,n=struct.unpack_from('<HH',data,54)
    segments=[struct.unpack_from('<II6Q',data,ph+i*size) for i in range(n)]
    def read(a,n):
        s=next(s for s in segments if s[0]==1 and s[3]<=a and a+n<=s[3]+s[5])
        return data[s[2]+a-s[3]:s[2]+a-s[3]+n]
    result=''
    for a,n in ((0x13BC710,0x16B),(0x4730C10,20),(0x47314D0,136)):
        result+='{const u8 raw[]={'+','.join(map(str,read(a,n)))+'};std::memcpy((void*)(image_base+'+hex(a)+'),raw,sizeof(raw));}\n'
    return result

PREFIX=r'''
#include <deque>
u32 self=11;namespace BbscMod{u32 RegisterOwnId(){return self;}}
World::OwnerBook bbsc_independent_owners;World::PresenceBook bbsc_world_presence_book;
std::mutex bbsc_independent_incoming_mutex;
std::deque<BbscWorldIncoming> bbsc_independent_incoming;
std::vector<BbscWorldIncoming> packets;
void BbscWorldSend(const World::Control& c,std::span<const u8> p){++sends;packets.push_back({self,c,{p.begin(),p.end()}});}
bool BbscWorldSceneReady(){return true;}bool BbscCurtainActive(){return false;}
std::atomic<u64> bbsc_world_load_pending{0};std::atomic<bool> bbsc_reload_finish_pending{false};
std::atomic<u32> bbsc_independent_role{0},bbsc_load_generation{1};
u32 BbscLampPointMap(s32){return 0x18000000;}
void BbscWorldReceiveBlock(const BbscWorldIncoming&){}
void BbscWorldReceiveLampCheckpoint(const BbscWorldIncoming&){}
void BbscWorldNativeInitialControl(const BbscWorldIncoming&){}
u64 addr(auto& a){return reinterpret_cast<u64>(a.data());}
void put(auto& a,size_t off,auto v){std::memcpy(a.data()+off,&v,sizeof(v));}
'''

MAIN=r'''
void flag(u8* p,u32 off,bool value=true){const u8 mask=0x80u>>(off%8);if(value)p[off/8]|=mask;else p[off/8]&=~mask;}
bool has(const u8* p,u32 off){return p[off/8]&(0x80u>>(off%8));}
int main(){
 image_base=(u64)VirtualAlloc(nullptr,128*1024*1024,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(image_base);
 ORIGINAL
 put(manager,0x20,u32(125));put(manager,0x24,u32(1200));put(manager,0x28,addr(lamp_backing));
 const World::WorldId world{11,99};bbsc_world_altar_world=world;
 World::Presence local;local.world=world;local.phase=World::Phase::Loading;
 local.map=BbscDreamStateMap;local.visit=1;local.sequence=1;bbsc_world_presence_local=local;
 session=3;map=BbscDreamStateMap;bbsc_world_states_world=world;
 bbsc_world_presence_book.Bind(world,11);bbsc_independent_owners.Bind(world);
 for(int slot=0;slot<7;++slot){auto& a=bbsc_world_altars[slot];a.entry.occupied=true;
  a.entry.ritual=100+slot;a.mount.key={u64(1000+slot),66,88,0};}
 auto scope=[&](int slot){const auto& a=bbsc_world_altars[slot];return World::Scope{world,0x1D000000,a.mount.key,a.entry.ritual};};
 auto live=[](int slot,u32 group){return (u8*)BbscWorldNativeAltarGroup(slot,1,group);};
 // Distinct physical groups for every slot/bank. Selected virtual m29 has
 // unrelated data; first guest admission must use the host's saved cup.
 for(int slot=0;slot<7;++slot){
  std::set<u64> addresses;
  for(u32 kind:{1u,6u,7u})for(u32 group=0;group<10;++group)
   assert(addresses.insert(BbscWorldNativeAltarGroup(slot,kind,group)).second);
  flag(live(slot,0),93);flag(live(slot,1),800); // progress receipt + layer1 boss
  flag(live(slot,7),840);flag(live(slot,7),850); // boss lamp remains unlocked
  groups[12900].fill(0);groups[12901].fill(0);groups[12907].fill(0);
  const auto seed=BbscWorldCaptureFlags(scope(slot));
  assert(seed.flags_ready&&seed.present==0x3FFFFFFF);
  assert(has(seed.groups[0].data(),93)&&has(seed.groups[1].data(),800));
  assert(has(seed.groups[7].data(),850));
 }
 const auto cup=scope(1);bbsc_independent_states[cup]={};
 bbsc_independent_states[cup].flags_ready=true; // old epoch0 empty admission
 assert(!BbscWorldFlagsReady(cup));bbsc_independent_states.clear();
 // Actual Request -> seed -> four existing Flags packets. Host stays in Dream.
 World::Control request;request.kind=World::ControlKind::Request;request.scope=cup;
 bbsc_independent_incoming.push_back({22,request,{}});TickBbscWorldSnapshots();
 assert(packets.size()==4&&BbscWorldFlagsReady(cup));const auto initial=packets;packets.clear();
 // First guest loads the native host progress, not personal zero progress.
 session=6;self=22;bbsc_independent_states.clear();
 for(size_t i=0;i<30;++i)groups[BbscWorldGroupKey(cup.map,i)]={};
 for(const auto& packet:initial)bbsc_independent_incoming.push_back(packet);
 TickBbscWorldSnapshots();assert(BbscWorldFlagsReady(cup));
 BbscWorldApplyFlags(cup,bbsc_independent_states[cup]);
 assert(has((const u8*)BbscFlagGroupStorage(12900),93));
 assert(has((const u8*)BbscFlagGroupStorage(12901),800));
 // A guest opens another passage. No per-flag custom message is introduced.
 auto guest=local;guest.map=cup.map;guest.dungeon=cup.dungeon;guest.ritual=cup.ritual;
 guest.phase=World::Phase::Playing;guest.sequence=2;bbsc_world_presence_local=guest;
 map=cup.map;flag((u8*)BbscFlagGroupStorage(12900),94);
 auto progressed=BbscWorldCaptureFlags(cup);progressed.epoch=2;progressed.sequence=20;
 assert(progressed.flags_ready);
 // A partially rebuilt native alias table cannot publish a half-empty cup.
 bbsc_independent_role=1;const auto missing=groups[12901];groups.erase(12901);
 TickBbscWorldSnapshots();assert(packets.empty());groups[12901]=missing;bbsc_independent_role=0;
 BbscWorldPublishFlags(cup,progressed,22,2,20);assert(packets.size()==4);auto updates=packets;packets.clear();
 // The real owner receiver persists actions directly to the host's native
 // backing slot while its selected virtual cup points elsewhere.
 session=3;self=11;map=BbscDreamStateMap;bbsc_world_presence_local=local;
 assert(bbsc_world_presence_book.Hear(22,world,guest,now));
 World::Control lease;lease.scope=cup;lease.owner=22;lease.epoch=2;
 assert(bbsc_independent_owners.Take(11,lease,now));
 const auto untouched=lamp_backing;groups[12900].fill(0xA5);const auto alias=groups[12900];
 // Simulate an older owner sending an unfiltered private bit and unused bytes.
 BbscWorldFlagPart older{};
 std::memcpy(&older,updates.front().payload.data(),sizeof(older));
 flag(older.groups[0].data(),999);
 std::memcpy(updates.front().payload.data(),&older,sizeof(older));
 std::memcpy(&older,updates.back().payload.data(),sizeof(older));
 older.groups.back().fill(0xFF);
 std::memcpy(updates.back().payload.data(),&older,sizeof(older));
 for(const auto& update:updates)bbsc_independent_incoming.push_back(update);
 TickBbscWorldSnapshots();assert(has((const u8*)live(1,0),94));
 assert(packets.size()==4);
 std::memcpy(&older,packets.front().payload.data(),sizeof(older));
 assert(has(older.groups[0].data(),94)&&!has(older.groups[0].data(),999));
 std::memcpy(&older,packets.back().payload.data(),sizeof(older));
 assert(older.groups.back()==(std::array<u8,125>{}));
 assert(has((const u8*)live(1,1),800)&&groups[12900]==alias);
 for(int slot=0;slot<7;++slot)if(slot!=1)for(u32 kind:{1u,6u,7u})for(u32 group=0;group<10;++group){
  const u64 ptr=BbscWorldNativeAltarGroup(slot,kind,group);const auto off=ptr-addr(lamp_backing);
  assert(!std::memcmp((void*)ptr,untouched.data()+off,125));
 }
 const auto accepted=lamp_backing;
 for(auto bad:updates){bad.sender=33;bbsc_independent_incoming.push_back(bad);}
 TickBbscWorldSnapshots();assert(lamp_backing==accepted);
 for(auto bad:updates){bad.control.epoch=1;bbsc_independent_incoming.push_back(bad);}
 TickBbscWorldSnapshots();assert(lamp_backing==accepted);
 // Non-owner player lights the layer1 lamp: actual host menu data changes
 // immediately even off-map. No cache lookup is required by the native menu.
 u64 lamp=2;BbscWorldIncoming lighting{22,{},{}};lighting.control.scope=cup;
 lighting.payload.resize(8);std::memcpy(lighting.payload.data(),&lamp,8);
 BbscWorldReceiveLamps(lighting);u64 native_lamps=0;
 assert(BbscWorldReadAltarLamps(1,native_lamps)&&(native_lamps&0xC)==0xC);
 assert(bbsc_world_altars_dirty.load());
 // A complete older owner snapshot cannot revoke the separate confirmed lamp.
 BbscWorldApplyFlags(cup,progressed);
 assert(BbscWorldReadAltarLamps(1,native_lamps)&&(native_lamps&0xC)==0xC);
 // Re-entry/session-cache loss reads the persisted cup, preserving layer1
 // boss/progress and the lamps of both floors. Replaced rituals are rejected.
 bbsc_independent_states.clear();auto reentry=BbscWorldCaptureFlags(cup);
 assert(reentry.flags_ready&&has(reentry.groups[0].data(),94)&&has(reentry.groups[1].data(),800));
 assert(has(reentry.groups[7].data(),830)&&has(reentry.groups[7].data(),850));
 auto stale=cup;++bbsc_world_altars[1].entry.ritual;
 assert(!BbscWorldCaptureFlags(stale).flags_ready);
 const auto before=lamp_backing;BbscWorldApplyFlags(stale,progressed);assert(lamp_backing==before);
 VirtualFree((void*)image_base,0,MEM_RELEASE);
}
'''

def run(negative=None):
    prefix=altars.PREFIX.replace('#include <mutex>','#include <mutex>\n#include <set>')
    prefix=prefix.replace('void QueueBbscWorldLampWrite(u32,u32,u32){}','')
    prefix=prefix.replace('int sends=0;void BbscWorldSend(const World::Control&,std::span<const u8>){++sends;}',
                          'int sends=0;void BbscWorldSend(const World::Control&,std::span<const u8>);')
    prefix=prefix.replace('return static_cast<u32>((Chalice::IsMap(map)?12900:20000)+i);',
                          'return Chalice::IsMap(map)?std::array<u32,3>{1,6,7}[i/10]*10000+2900+i%10:20000+i;')
    prefix+='\nbool BbscNativeFinaleCommitted(){return false;}\n'
    prefix+='void MaskBbscSharedFlagGroup(u32 key,u8* flags){if(key==12900)flags[124]&=0xFE;}\n'
    code=prefix+PREFIX+SOURCE[SOURCE.index('struct BbscWorldAltar {'):SOURCE.index('void BbscWorldRememberProgress(')]
    for sig in ('void BbscWorldRememberProgress(const World::Scope& scope,const BbscWorldState& state)',
                'void BbscWorldApplyFlags(const World::Scope& scope,const BbscWorldState& state)',
                'BbscWorldState BbscWorldCaptureFlags(const World::Scope& scope)',
                'bool BbscWorldFlagsReady(const World::Scope& scope)',
                'void BbscWorldEnsureSeed(const World::Scope& scope)',
                'void BbscWorldPublishFlags(const World::Scope& scope,const BbscWorldState& state,u32 owner,u64 epoch,u64 seq)',
                'void BbscWorldReceiveAltar(const BbscWorldIncoming& message)'):
        code+=function(SOURCE,sig)
    code+=LAMPS+function(SOURCE,'void TickBbscWorldSnapshots()')+MAIN.replace('ORIGINAL',original())
    if negative=='seed':
        code=code.replace('const bool host_cup=dungeon && GetSessionState()==3;','const bool host_cup=false;')
    elif negative=='readiness':
        code=code.replace('if(Chalice::IsMap(scope.map)?(it->second.present&0x3FF)!=0x3FF:!(it->second.present&1))return false;', 'if(!(it->second.present&1) && !ritual_seed)return false;')
    elif negative=='persistence':
        code=code.replace('(host && !from_host && Chalice::IsMap(c.scope.map) && state.flags_ready)', 'false')
    elif negative=='incomplete':
        code=code.replace('if(!next.flags_ready)return;', '')
    elif negative=='lamp_rollback':
        code=code.replace('if(host_cup && key==12907 && before!=state.groups[i])', 'if(false)')
    elif negative=='lamp':
        code=code.replace('if(host && Chalice::IsMap(c.scope.map))BbscWorldApplyLampBits(c.scope,bits,false);','')
    compiler=os.environ.get('CXX') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-cup-progress-') as tmp:
        p=Path(tmp);cpp=p/'cup.cpp';exe=p/'cup.exe';cpp.write_text(code,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        result=subprocess.run([str(exe)],capture_output=True,env=env)
        assert (result.returncode!=0) if negative else result.returncode==0,result.stderr.decode(errors='replace')
    print('PASS negative control '+negative if negative else 'PASS original mapper / production request, seed, receive, host persistence, re-entry, lamp menu, seven slots and stale-ritual fences')

if __name__=='__main__':
    run()
    for variant in ('seed','readiness','persistence','incomplete','lamp','lamp_rollback'):run(variant)
