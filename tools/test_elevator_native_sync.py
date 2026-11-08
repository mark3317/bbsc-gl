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

# Map, movement events, position, busy, optional native lever interlock.
MOVEMENT = [
    (0x16000000, (12200122, 12200123), 12200125, 12200126, 0),
    (0x18010000, (12410322, 12410323), 12410350, 12415350, 12410351),
    (0x18020000, (12420151, 12420152), 12420154, 12420155, 0),
    (0x1B000000, (12700131, 12700132), 12700134, 12700135, 0),
    (0x1B000000, (12700141, 12700142), 12700144, 12700145, 0),
    (0x1C000000, (12800602, 12800604), 12800610, 12804700, 12800611),
    (0x21000000, (13300112, 13300113), 13300115, 13300116, 0),
    (0x23000000, (13501102, 13501103), 13501106, 13504100, 0),
    (0x23000000, (13501112, 13501113), 13501116, 13504110, 0),
    (0x23000000, (13501122, 13501123), 13501126, 13504120, 0),
    (0x24000000, (13601102, 13601103), 13601106, 13604100, 0),
]
MENSIS_MOVEMENT = [
    (0x1A000000, (12601320, 12601330), 12601250, 12605250, 0),
    (0x1A000000, (12601320, 12601330), 12601251, 12605251, 0),
    (0x1A000000, (12601320, 12601330), 12601252, 12605252, 0),
    (0x1A000000, (12601320, 12601330), 12601256, 12605256, 0),
    (0x1A000000, (12601320, 12601330), 12601254, 12605253, 0),
    (0x1A000000, (12601320, 12601330), 12601255, 12605254, 0),
]

def resolved_instructions(emevd, event, slot=0):
    events = dict(emevd.events)
    instructions = [(b, i, bytearray(args)) for b, i, args in events[event]]
    count, table = emevd.header[:2]
    records = (struct.unpack_from('<qqqqq', emevd.data, table + 0x30 * row)
               for row in range(count))
    _, _, _, params, offset = next(record for record in records if record[0] == event)
    if params:
        (args,) = [a[8:] for b, i, a in events[0]
                   if (b, i) == (2000, 0) and len(a) >= 8
                   and struct.unpack_from('<II', a) == (slot, event)]
        for row in range(params):
            ins, target, source, length, _ = struct.unpack_from(
                '<qqqii', emevd.data, emevd.header[9] + offset + 0x20 * row)
            assert target + length <= len(instructions[ins][2]) and source + length <= len(args)
            instructions[ins][2][target:target+length] = args[source:source+length]
    return instructions

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
    lifts = [(0, movement) for movement in MOVEMENT] + list(enumerate(MENSIS_MOVEMENT))
    for slot, (packed, events, position, busy, interlock) in lifts:
        name = f'm{packed>>24:02d}_{packed>>16&255:02d}_00_00'
        evd = Emevd(game/'event'/(name+'.emevd.dcx'))
        for event, value in zip(events, (1, 0)):
            ins = resolved_instructions(evd, event, slot)
            writes = [struct.unpack('<II', a) for b, i, a in ins if (b, i) == (2003, 2)]
            assert writes.index((busy, 1)) < writes.index((busy, 0))
            assert (position, value) in writes
            assert any((b, i) == (2003, 18) for b, i, _ in ins)
        if interlock:
            init = {12410351: 12410321, 12800611: 12800600}[interlock]
            assert (2003, 2, struct.pack('<II', interlock, 0)) in resolved_instructions(evd, init)
    print('PASS original 1.09: movement and temporary flags for 17 lifts, including six Mensis slots')

PREFIX=r'''
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <map>
#include <mutex>
#include "core/bbsc_world_control.h"
#include "core/bbsc_lift_flags.h"
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
World::OwnerBook bbsc_independent_owners;
std::optional<World::Scope> bbsc_world_requested_scope;
struct TestAltar {
    struct { bool occupied = false; u64 ritual = 0; } entry;
    struct { Chalice::Key key; } mount;
};
std::array<TestAltar, 0> bbsc_world_altars;
namespace BbscMod { u32 RegisterOwnId() { return 11; } }
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
std::map<World::Scope, BbscWorldState> bbsc_independent_states;
void BbscWorldSend(const World::Control& c,std::span<const u8> body){
 if(c.part==0) std::memcpy(&first_part,body.data(),sizeof(first_part));
}
'''
    code+=function('BbscWorldState BbscWorldCaptureFlags(const World::Scope& scope)',STATE)
    code+=function('void BbscWorldPublishFlags(const World::Scope& scope,const BbscWorldState& state,u32 owner,u64 epoch,u64 seq)',STATE)
    code+=function('void BbscWorldApplyFlags(const World::Scope& scope,const BbscWorldState& state)',STATE)
    code+=function('bool BbscWorldFlagsReady(const World::Scope& scope)',STATE)
    code+=function('void BbscWorldSeedLiftFlags(u32 map)',STATE)
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
    code+=r'''
 const auto write = [](auto& group, u32 flag, bool set) {
    const u8 mask = 0x80u >> (flag % 8);
    auto& value = group[flag % 1000 / 8];
    value = set ? value | mask : value & ~mask;
 };
 const auto read = [](const auto& group, u32 flag) {
    return (group[flag % 1000 / 8] & (0x80u >> (flag % 8))) != 0;
 };
 '''
    for packed, _, position, busy, interlock in MOVEMENT + MENSIS_MOVEMENT:
        code+=f'''
 {{
    const u32 position = {position}, busy = {busy}, interlock = {interlock};
    const World::Scope destination{{.world = {{11,99}}, .map = {packed}}};
    bbsc_world_presence_local.world = destination.world;
    bbsc_world_presence_local.map = 0x15000000; // native spawn knows the target first
    bbsc_independent_owners.Bind({{}});
    bbsc_independent_owners.Bind(destination.world);
    World::Control owner;
    owner.kind = World::ControlKind::Owner;
    owner.scope = destination;
    owner.owner = 22;
    owner.epoch = 7;
    assert(bbsc_independent_owners.Take(11, owner, 1));
    for (int role : {{3,6}}) {{
        session = role;
        groups.clear(); own.clear();
        auto& snapshot = bbsc_independent_states[destination];
        snapshot = {{}};
        snapshot.flags_ready = true;
        snapshot.epoch = owner.epoch;
        snapshot.present = 1; // required main bank
        const auto index = [&](u32 flag) {{return flag / 1000 - BbscWorldGroupKey(destination.map, 0);}};
        const auto flag = [&](u32 id) {{return read(groups[id / 1000], id);}};
        for (bool desired : {{false,true}}) {{
            for (u32 id : {{position,busy,interlock}}) {{
                if (!id) continue;
                const bool incoming = id != position || desired;
                snapshot.present |= u64{{1}} << index(id);
                write(snapshot.groups[index(id)], id, incoming);
                write(groups[id / 1000], id, !incoming);
                const u8 mask = 0x80u >> (id % 8);
                assert(BbscSharedProgressByte(id / 1000, id % 1000 / 8, mask) == 0);
            }}
            BbscWorldApplyFlags(destination, snapshot);
            assert(flag(position) != desired && !flag(busy));
            if (interlock) assert(!flag(interlock));
            write(groups[busy / 1000], busy, true);
            if (interlock) write(groups[interlock / 1000], interlock, true);
            BbscWorldSeedLiftFlags(destination.map);
            assert(flag(position) == desired && !flag(busy));
            if (interlock) assert(!flag(interlock));
            write(groups[position / 1000], position, !desired);
            write(snapshot.groups[index(busy)], busy, false);
            write(groups[busy / 1000], busy, true);
            BbscWorldApplyFlags(destination, snapshot);
            assert(flag(position) != desired && flag(busy));
        }}
        snapshot.flags_ready = false;
        BbscWorldSeedLiftFlags(destination.map);
        assert(!flag(position) && !flag(busy));
        snapshot.flags_ready = true;
        snapshot.epoch = owner.epoch - 1;
        BbscWorldSeedLiftFlags(destination.map);
        assert(!flag(position));
        snapshot.epoch = owner.epoch;
        snapshot.present &= ~(u64{{1}} << index(position));
        BbscWorldSeedLiftFlags(destination.map);
        assert(!flag(position));
    }}
    owner.epoch++;
    owner.owner = 11;
    assert(bbsc_independent_owners.Take(11, owner, 2));
    BbscWorldSeedLiftFlags(destination.map);
    assert(!read(groups[position / 1000], position));
 }}
'''
    code+='}\n'
    compiler=shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-elevator-native-') as tmp:
        cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text(code,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production: all 10 events shared, channel31 same-place policy, capture/apply host+guest, late-arrival snapshot, additive unlock/no rollback, incomplete/owner/off-map fences')
    print('PASS production: 17 lifts, native live bits preserved, exact arrival position, no additive replay')

if __name__=='__main__':
    original(Path(sys.argv[1]))
    production()
