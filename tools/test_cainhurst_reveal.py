"""Production Cainhurst reveal/pickup fixture; optional read-only BB_GAME data audit."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import sys
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
    start=s.index(signature+' {');end=s.index('{',start)+1;depth=1
    while depth:
        depth+=(s[end]=='{')-(s[end]=='}');end+=1
    return s[start:end]
code=r'''
#include <windows.h>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <array>
#include <atomic>
#include <optional>
#include <mutex>
#include <deque>
#include <algorithm>
#include <vector>
#include <tuple>
#include <map>
#include "core/bbsc_quest_event_rules.h"
namespace QuestRules=Core::Bloodborne::QuestRules;
using u64=uint64_t;using u32=uint32_t;using s32=int32_t;using s64=int64_t;using u8=uint8_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
struct GuestRegisterSnapshot{};
u64 image_base=0, actor=1;int state=6,type=1;u32 map=0x19000000;
std::atomic<u32> bbsc_load_generation{1},bbsc_remo_started_sequence{0};
std::atomic<u64> bbsc_world_load_pending{0};std::atomic<bool> bbsc_reload_finish_pending{false};
u32 bbsc_cainhurst_scene_generation=~u32{0},bbsc_cainhurst_scene_sequence=0;
s64 bbsc_cainhurst_scene_request_ms=0,now=100;
std::optional<bool> playing=false;bool host_ready=true,live_flag=true,snapshot_ok=true,writable=true;
alignas(16) unsigned char global_data[0x20]={};
struct Packet{u32 map;int cutscene;};struct Queued{Packet packet;};
std::deque<Queued> bbsc_cutscene_queue;std::mutex bbsc_cutscene_mutex;
struct BbscWorldSnapshot{u64 present=1;std::array<std::array<u8,125>,40> groups{};} snapshot;
int GetSessionState(){return state;}int GetLocalPlayerType(){return type;}
u64 GetLocalPlayerCharacter(){return actor;}u32 GetCurrentPackedMap(){return map;}
u64 GetGlobalState(){return (u64)global_data;}s64 SteadyNowMs(){return now;}
bool ReadablePointer(u64 p,size_t){return p!=0;}enum class MemoryProt{CpuWrite};
bool HasMemoryAccess(u64,size_t,MemoryProt){return writable;}
template<class T>T ReadValue(u64 p,size_t off){T v;memcpy(&v,(void*)(p+off),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t off,T v){memcpy((void*)(p+off),&v,sizeof(v));}
s64 event_id=12501803;s64 BbscEventIdOf(u64){return event_id;}
std::optional<bool> BbscRemoPlaying(){return playing;}
bool BbscHostBlockSnapshot(u32,BbscWorldSnapshot& out){out=snapshot;return snapshot_ok;}
bool BbscHostWorldFlagsReady(u32){return host_ready;}bool BbscEventFlag(u32){return live_flag;}
std::vector<std::tuple<int,u32,u32>> calls;
void PS4_SYSV_ABI Draw(u32 id,u32 on){calls.emplace_back(2012,id,on);}
void PS4_SYSV_ABI Collision(u32 id,u32 on){calls.emplace_back(2011,id,on);}
u64 PS4_SYSV_ABI Find(u32 id,u64 a,u64 b){assert(id==2500600&&a==0&&b==0);return 42;}
void PS4_SYSV_ABI Disable(u64 chr,u32 off){assert(chr==42&&off==0);calls.emplace_back(2004,2500600,1);}
void PS4_SYSV_ABI CreateSfx(u64 unused,u32 id){assert(unused==0);calls.emplace_back(2006,id,1);}
void stub(u64 off,u64 target){unsigned char bytes[12]={0x48,0xb8};memcpy(bytes+2,&target,8);bytes[10]=0xff;bytes[11]=0xe0;memcpy((void*)(image_base+off),bytes,12);}
'''
code += 'struct BbscScriptedPickup { u32 map; s64 event; bool client_gate; };\n'
code += re.search(r'constexpr std::array<BbscScriptedPickup, \d+> BbscScriptedPickups\{\{.*?\}\};',s,re.S).group()+'\n'
code += re.search(r'constexpr std::array<[^;]+ BbscNpcQuestFlags\{.*?\};',s,re.S).group()+'\n'
code += ('bool bbsc_npc_own_active=true;std::mutex bbsc_npc_own_mutex;std::map<u32,u8> bbsc_npc_own;\n'
         'std::map<u32,std::array<u8,125>> bbsc_npc_checked_groups;\n')
for signature in ['bool IsBbscScriptedPickupFlag(u32 flag)',
                  'bool IsBbscKidnapFlag(u32 flag)',
                  'bool IsBbscNativeItemStateFlag(u32 flag)',
                  'bool IsBbscNpcQuestFlag(u32 flag)',
                  'void NoteBbscNpcOwnFlag(u32 flag, u8 value)',
                  'void KeepBbscNpcOwnBits(u32 key, const u8* before, u8* live)',
                  'void ArmBbscCainhurstReveal(s32 scene)',
                  'void ApplyBbscCainhurstReveal()',
                  'void TickBbscCainhurstReveal()']:
    code+=function(signature)+'\n'
code+=r'''
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);assert(image_base);
 stub(0x13cabd0,(u64)Draw);stub(0x13ca580,(u64)Collision);stub(0x13c97a0,(u64)Find);stub(0x18c6390,(u64)Disable);stub(0x1315fa0,(u64)CreateSfx);
 for(u64 off:{0x553b148ull,0x553b168ull,0x553b178ull})WriteValue<u64>(image_base,off,1);
 snapshot.groups[0][810/8]=0x80u>>(810%8);
 // Scene request is not completion; also wait for actual playback and host flag.
 ArmBbscCainhurstReveal(25000010);TickBbscCainhurstReveal();assert(calls.empty());
 now+=500;playing=true;++bbsc_remo_started_sequence;TickBbscCainhurstReveal();assert(calls.empty());
 playing=false;host_ready=false;TickBbscCainhurstReveal();assert(calls.empty());
 host_ready=true;live_flag=false;TickBbscCainhurstReveal();assert(calls.empty());
 live_flag=true;TickBbscCainhurstReveal();assert(calls.size()==82);
 auto count=calls.size();TickBbscCainhurstReveal();assert(calls.size()==count);
 // Rejoin/load into an already revealed host world; no movie packet is needed.
 ++bbsc_load_generation;bbsc_cutscene_queue.push_back({{map,25000010}});TickBbscCainhurstReveal();assert(calls.size()==count);
 bbsc_cutscene_queue.clear();global_data[8]=1;TickBbscCainhurstReveal();assert(calls.size()==count);
 global_data[8]=0;TickBbscCainhurstReveal();assert(calls.size()==count*2);
 // Neither own prior progress nor an incomplete/stale/closed host snapshot opens it.
 ++bbsc_load_generation;snapshot.groups[0][810/8]=0;TickBbscCainhurstReveal();assert(calls.size()==count*2);
 snapshot.groups[0][810/8]=0x80u>>(810%8);snapshot_ok=false;TickBbscCainhurstReveal();assert(calls.size()==count*2);snapshot_ok=true;
 state=3;TickBbscCainhurstReveal();state=6;type=2;TickBbscCainhurstReveal();assert(calls.size()==count*2);
 type=1;map=0x18010000;TickBbscCainhurstReveal();assert(calls.size()==count*2);
 map=0x19000000;playing.reset();TickBbscCainhurstReveal();assert(calls.size()==count*2);playing=false;
 // Host completion cannot remove our untaken crown; our completion survives host=false.
 std::array<u8,125> before{},live{};live[803/8]=0x80u>>(803%8);
 KeepBbscNpcOwnBits(12501,before.data(),live.data());assert(live[803/8]==0);
 NoteBbscNpcOwnFlag(12501803,1);live.fill(0);
 before[803/8]=0x80u>>(803%8); // actual native receipt before incoming host projection
 KeepBbscNpcOwnBits(12501,before.data(),live.data());assert(live[803/8]==(0x80u>>(803%8)));
 // Shared native End/Jump host predicate is covered for12501803 by test_guest_access.
 VirtualFree((void*)image_base,0,MEM_RELEASE);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-cainhurst-') as tmp:
    cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe';cpp.write_text(code,encoding='utf-8')
    compiler=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler,'-std=c++20','-I',str(root/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],check=True,env=env,timeout=10)
flags=s.split('BbscNpcQuestFlags{',1)[1].split('};',1)[0]
values=list(map(int,re.findall(r'\b\d+\b',flags)))
assert values==sorted(set(values)) and 12501803 in values
assert 'std::ranges::binary_search(BbscScriptedPickups, event' in s
if os.environ.get('BB_GAME'):
    sys.path.insert(0,str(root/'tools/gamedata'))
    import struct
    from emevd import Emevd
    events=dict(Emevd(Path(os.environ['BB_GAME'])/'event/m25_00_00_00.emevd.dcx').events)
    crown=events[12501803]
    assert crown[0]==(1003,6,struct.pack('<I',256))
    assert crown[6]==(2003,4,struct.pack('<I',2502000))
    reveal=events[12500810]
    assert reveal[94]==(2002,3,struct.pack('<III',25000010,0,10000))
    expected=[]
    for b,i,a in reveal[97:]:
        if b in (2012,2005):
            entity,on=struct.unpack('<II',a);expected.append((2012,entity,on))
        elif b==2011:
            entity,on=struct.unpack('<II',a);expected.append((2011,entity,on))
        elif b==2004:expected.append((2004,2500600,1))
        elif b==2006:expected.append((2006,struct.unpack('<I',a)[0],1))
        else:raise AssertionError((b,i))
    actual=[(2012,i,1) for i in list(range(2506000,2506037))+list(range(2506039,2506068))+list(range(2506070,2506074))]
    actual += [(2011,2506037,1),(2011,2506038,1),(2004,2500600,1),(2012,2501810,0)]
    actual += [(2006,i,1) for i in range(2503300,2503308)]
    assert sorted(actual)==sorted(expected) and len(actual)==82
print('PASS: production reveal lifecycle, 82 native effects, personal crown gate and negative paths')
