"""Original lift scripts and production flags/event policies; fixture memory only.

Usage: python tools/test_elevator_native_sync.py <dvdroot_ps4>
"""
from pathlib import Path
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
STATE=(ROOT/'emulator/src/core/bbsc_world_state.inc').read_text(encoding='utf-8')

def function(sig,source=SOURCE):
    a=source.index(sig+' {');b=source.index('{',a)+1;depth=1
    while depth:
        depth+=(source[b]=='{')-(source[b]=='}');b+=1
    return source[a:b]+'\n'

# (packed map, permanent flag, unlock event). This is test evidence only;
# runtime uses the original scripts and existing full-map flag snapshots.
UNLOCKS=[(0x16000000,12200121,12200121),(0x18010000,12410330,12410330),
         (0x1B000000,12700137,12700137),(0x1B000000,12700147,12700147),
         (0x1C000000,12800612,12800607),(0x21000000,13300111,13300111),
         (0x23000000,13501108,13501105),(0x23000000,13501118,13501115),
         (0x23000000,13501128,13501125),(0x24000000,13601108,13601105)]

def original(game):
    sys.path.insert(0,str(ROOT/'tools/gamedata'))
    from emevd import Emevd
    implicit={12200121,12700137,12700147,13300111}
    for packed,flag,event in UNLOCKS:
        name=f'm{packed>>24:02d}_{packed>>16&255:02d}_00_00'
        evd=dict(Emevd(game/'event'/(name+'.emevd.dcx')).events)
        ins=evd[event]
        assert any(b==3 and i==2 for b,i,a in ins) # region condition
        assert sum(b==2005 and i==6 for b,i,a in ins)>=2 # lever activation
        assert not any(b==2000 and i==2 and a[:4]==bytes(4) for b,i,a in ins) # NoNetSync
        if flag in implicit:
            assert ins[0]==(1003,2,bytes.fromhex('0001020000000000'))
        elif flag in (12410330,12800612):
            assert any(b==2000 and i==0 and struct.unpack_from('<II',a,4)==(event,flag)
                       for b,i,a in evd[0] if len(a)>=12)
            assert any(b==2003 and i==2 and a==struct.pack('<II',0,1) for b,i,a in ins)
        else:
            assert any(b==2003 and i==2 and a==struct.pack('<II',flag,1) for b,i,a in ins)
    print('PASS original 1.09: 10 permanent unlock flags, region/lever paths, implicit completion, parameter substitutions, no NoNetSync')

PREFIX=r'''
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <map>
#include <mutex>
#include "core/bbsc_world_control.h"
#include "core/bbsc_quest_event_rules.h"
#include "core/bbsc_lamp_travel_data.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
namespace QuestRules=Core::Bloodborne::QuestRules;
namespace Bbsc=Core::Bbsc;
constexpr size_t BbscWorldGroupBytes=125,BbscWorldGroupCount=40;
constexpr std::array<u32,4> BbscWorldFlagKinds{1,6,7,5};
constexpr u32 BbscDreamStateMap=0x15000000;
bool independent=true,own_npc=true;int session=6;
bool BbscIndependentTravelAllowed(){return independent;}
bool BbscOwnNpcQuestsEnabled(){return own_npc;}
int GetSessionState(){return session;}
std::mutex bbsc_world_presence_mutex;World::Presence bbsc_world_presence_local;
std::map<u32,std::array<u8,125>> groups,own;
u64 BbscFlagGroupStorage(u32 k){return reinterpret_cast<u64>(groups[k].data());}
s32 BbscWorldHostAltarSlot(const World::Scope&){return -1;}
u64 BbscWorldNativeAltarGroup(s32,u32,u32){return 0;}
void KeepBbscOwnWorldGroup(u32 k,const u8* p){if(!own.contains(k))std::memcpy(own[k].data(),p,125);}
void KeepBbscGuestTalkBits(u32,const u8*,u8*){}
void KeepBbscNpcOwnBits(u32,const u8*,u8*){}
'''

def production():
    arrays='\n'.join(re.search(r'constexpr std::array<[^;]+ '+name+r'\{.*?\};',SOURCE,re.S).group()
                     for name in ('BbscNpcQuestFlags','BbscDreamShopUnlockFlags','BbscEncounterProgressFlags',
                                  'BbscGuestKnockEvents','BbscScriptedPickups'))
    code=PREFIX+'struct BbscScriptedPickup { u32 map; s64 event; bool client_gate; };\n'+arrays+'\n'
    for sig in ('bool IsBbscNpcQuestFlag(u32 flag)','bool IsBbscLocalQuestEvent(s64 event)',
                'bool IsBbscKidnapEvent(s64 event)','bool IsBbscPersonalMapEvent(s64 event)',
                'bool BbscSharedMapProgressAllowed(u32 flag)','u8 BbscSharedProgressByte(u32 key, size_t byte, u8 incoming)',
                'void BbscMergeSharedProgressGroup(u32 key, u8* live, const u8* incoming)',
                'u32 BbscWorldGroupKey(u32 packed_map, size_t index)',
                'void MaskBbscSharedFlagGroup(u32 key, u8* outgoing)'):
        code+=function(sig)
    code+=function('bool BbscIsolatedNativeEvent(s64 event)',(ROOT/'emulator/src/core/bbsc_personal_events.inc').read_text())
    code+=re.search(r'struct BbscWorldState \{.*?\n\};',STATE,re.S).group()+'\n'
    code+=re.search(r'struct BbscWorldFlagPart \{.*?\n\};',STATE,re.S).group()+'\n'
    code+=r'''
BbscWorldFlagPart first_part{};
void BbscWorldSend(const World::Control& c,std::span<const u8> body){
 if(c.part==0) std::memcpy(&first_part,body.data(),sizeof(first_part));
}
'''
    code+=function('BbscWorldState BbscWorldCaptureFlags(const World::Scope& scope)',STATE)
    code+=function('void BbscWorldPublishFlags(const World::Scope& scope,const BbscWorldState& state,u32 owner,u64 epoch,u64 seq)',STATE)
    code+=function('void BbscWorldApplyFlags(const World::Scope& scope,const BbscWorldState& state)',STATE)
    code+=r'''int main(){
 const auto scope=World::Scope{.map=0x18010000};
 auto& live=groups[12410];
 const auto set=[&](u32 flag){live[flag%1000/8]|=0x80u>>(flag%8);};
 set(12410330);set(12410809);set(12410511);
 const auto before=live;
 const auto captured=BbscWorldCaptureFlags(scope);
 assert(captured.present&1);
 BbscWorldPublishFlags(scope,captured,33,1,1);
 const auto sent=[&](u32 flag){return first_part.groups[0][flag%1000/8]&(0x80u>>(flag%8));};
 assert(sent(12410330)&&!sent(12410809)&&!sent(12410511)&&live==before);
 '''
    for packed,flag,event in UNLOCKS:
        code+=f'''{{
 const u32 flag={flag};const s64 event={event};
 assert(!IsBbscNpcQuestFlag(flag)&&!IsBbscPersonalMapEvent(event));
 for(bool setting:{{false,true}})for(int role:{{3,6}}){{own_npc=setting;session=role;assert(!BbscIsolatedNativeEvent(event));}}
 assert(BbscSharedMapProgressAllowed(flag));
 World::Presence p;p.world={{11,99}};p.map={packed};p.phase=World::Phase::Playing;p.visit=1;p.sequence=1;
 const auto scope=World::ScopeOf(p);bbsc_world_presence_local=p;
 auto peer=p;assert(World::Routes(0x31,p,peer));peer.map=0x15000000;assert(!World::Routes(0x31,p,peer));
 groups.clear();own.clear();const u32 key=flag/1000;const size_t byte=flag%1000/8;const u8 mask=0x80u>>(flag%8);
 groups[key][byte]|=mask;auto snapshot=BbscWorldCaptureFlags(scope);
 bool found=false;for(size_t i=0;i<10;++i)if(BbscWorldGroupKey(p.map,i)==key)found=(snapshot.present&(u64{{1}}<<i))&&(snapshot.groups[i][byte]&mask);
 assert(found);
 World::Control c;c.kind=World::ControlKind::Flags;c.scope=scope;
 for(int role:{{3,6}}){{session=role;groups.clear();own.clear();
  assert(World::ShouldApplyFlags(c,scope,33,22,role==3,true));
  BbscWorldApplyFlags(scope,snapshot);assert(groups[key][byte]&mask);
  if(role==6)assert(own[key][byte]==0);
  auto stale=snapshot;for(auto& g:stale.groups)g.fill(0);BbscWorldApplyFlags(scope,stale);assert(groups[key][byte]&mask);
 }}
 // Off-map guests defer projection until they enter the location; coordinator
 // receives its flags immediately. Admission is separately tested by bootstrap.
 auto away=scope;away.map=0x15000000;
 assert(!World::ShouldApplyFlags(c,away,33,22,false,true));
 assert(World::ShouldApplyFlags(c,away,11,22,true,true));
 assert(!World::ShouldApplyFlags(c,scope,22,22,false,true));
 assert(!World::ShouldApplyFlags(c,scope,33,22,false,false));
 }}\n'''
    code+='}\n'
    compiler=shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-elevator-native-') as tmp:
        cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text(code,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production: all 10 events shared, channel31 same-place policy, capture/apply host+guest, late-arrival snapshot, additive unlock/no rollback, incomplete/owner/off-map fences')

if __name__=='__main__':
    original(Path(sys.argv[1]))
    production()
