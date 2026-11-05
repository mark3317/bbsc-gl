"""Run the native visibility tick against two independent observers' simulated member state."""
import os
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "emulator/src/core/bloodborne_re.cpp").read_text(encoding="utf-8")


def function(start, end):
    begin = source.index(start)
    return source[begin:source.index(end, begin)]


fixture = r"""
#include <algorithm>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <map>
#include <mutex>
#include <vector>
using u8=uint8_t; using u16=uint16_t; using u32=uint32_t; using u64=uint64_t;
using s32=int32_t; using s64=int64_t;
#define BBSC_MOD
bool BbscIndependentActive(){return false;}
#define PS4_SYSV_ABI
#define BBSC_TIMELINE(...)
#define LOG_INFO(...)
constexpr u64 image_base=0, CandidateLocalStatePointerOffset=32;
constexpr s64 BbscLifeFreshMs=3000, BbscRemoteReviveSettleMs=1000;
unsigned char memory[65536]{};
template<class T>T ReadValue(u64 ptr,size_t off){T v;std::memcpy(&v,memory+ptr+off,sizeof(v));return v;}
template<class T>void WriteValue(u64 ptr,size_t off,T v){std::memcpy(memory+ptr+off,&v,sizeof(v));}
bool ReadablePointer(u64 p,size_t n){return p>=256 && p+n<=sizeof(memory);}
constexpr u64 global=512,world=1024,entries=2048,local=3072,chr=8192,task=12288;
constexpr u64 control=16384,modules=18432,draw=20480,draw_state=22528;
std::atomic<u32> bbsc_load_generation{}, bbsc_world_load_pending{}, bbsc_reload_finish_pending{};
s64 now=10000; int session=6,hp=100,physics=0; u32 owner=3;
s64 SteadyNowMs(){return now;} int GetSessionState(){return session;}
u64 GetGlobalState(){return global;} int GetCharacterHp(u64){return hp;}
int GetCharacterType(u64){return 1;} bool BbscSpectateEnabled(){return true;}
bool BbscQuitInProgress(){return false;} bool BbscCurtainActive(){return false;}
std::vector<u64> GetMultiPlayerInsTasks(){return {task};}
bool IsValidMemberId(u64 p){return ReadValue<u32>(p,0)!=0;}
bool Equals(u64 a,u64 b){return ReadValue<u32>(a,0)==ReadValue<u32>(b,0);}
void Physics(u64,u8){++physics;} void ArmBbscDeathLockClear(){}
namespace BbscMod {u32 FindSessionRegisterPeer(u32){return owner;}}
u32 ReadBbscRegisterIdentity(u64){return 1;}
struct Life {bool dead; s64 received_ms; bool model_visible;};
std::mutex bbsc_life_mutex; std::map<u32,Life> bbsc_peer_life;
std::pair<int,int> BbscPeerLifeCounts(){int dead=0;for(auto& [id,l]:bbsc_peer_life)dead+=l.dead;return {2,dead};}
"""
tick = function("void TickBbscRemoteRevive() {", "// ---- The death penalty")
fixture += function("u64 BbscCharacterDrawState(", "// State 2 extends")
fixture += tick.replace("image_base + MemberIdEqualsOffset", "reinterpret_cast<u64>(&::Equals)").replace(
    "image_base + 0x018BCF30", "reinterpret_cast<u64>(&Physics)"
)
fixture += r"""
void advance(int ticks,bool refresh=true) {
    while(ticks--){now+=250;if(refresh)bbsc_peer_life[3].received_ms=now;TickBbscRemoteRevive();}
}
int main(){
    WriteValue<u64>(32,0,world); WriteValue<u64>(world,0x60,local);
    WriteValue<s32>(world,0x30,2); WriteValue<u64>(world,0x38,entries);
    WriteValue<u64>(entries,0,local); WriteValue<u64>(entries,0x38,chr);
    WriteValue<u64>(chr,0x58,control); WriteValue<u64>(chr,0x3B0,modules);
    WriteValue<u64>(modules,0x58,draw); WriteValue<u64>(draw,0x28,draw_state);
    WriteValue<u32>(chr,0x3d8,3); WriteValue<u32>(task,0xc8,3);
    WriteValue<s32>(task,0x50,6); WriteValue<s32>(task,0x54,6);
    bbsc_peer_life[2]={true,now,false};
    for(auto role:{6,3}){
        session=role;WriteValue<s32>(task,0xe8,role==3?1:2);
        WriteValue<u8>(draw_state,0xc,0); WriteValue<float>(chr,0x208,0);
        WriteValue<float>(chr,0x20c,0.5f);
        bbsc_peer_life[3]={false,now,true};
        advance(5);++bbsc_load_generation;advance(9);
        assert(ReadValue<u8>(draw_state,0xc)==0);advance(4);
        assert(ReadValue<u8>(draw_state,0xc)==1 && ReadValue<float>(chr,0x208)==1);
        assert(ReadValue<float>(chr,0x20c)==0.5f && physics==0);
    }
    WriteValue<s32>(task,0xe8,1);session=6; // guest observing the other guest
    WriteValue<u8>(draw_state,0xc,0); bbsc_peer_life[3].model_visible=false;advance(15);
    assert(ReadValue<u8>(draw_state,0xc)==0); // owner's fade / older sender
    bbsc_peer_life[3].model_visible=true;bbsc_peer_life[3].received_ms=now-4000;advance(15,false);
    assert(ReadValue<u8>(draw_state,0xc)==0);
    owner=0;advance(15);assert(ReadValue<u8>(draw_state,0xc)==0);owner=3;
    WriteValue<u8>(task,0xed,2); advance(15);assert(ReadValue<u8>(draw_state,0xc)==0);
    WriteValue<u8>(task,0xed,0);hp=0;advance(15);assert(ReadValue<u8>(draw_state,0xc)==0);hp=100;
    bbsc_world_load_pending=1;advance(15);assert(ReadValue<u8>(draw_state,0xc)==0);bbsc_world_load_pending=0;
    advance(11);assert(ReadValue<u8>(draw_state,0xc)==1);
    WriteValue<u16>(control,0x114,1);bbsc_peer_life[3].dead=true;advance(8);
    assert(physics==0);bbsc_peer_life[3].dead=false;advance(8);
    assert(physics==1 && ReadValue<u16>(control,0x114)==0); // unrelated dead guest still present
    session=0;WriteValue<u8>(draw_state,0xc,0);advance(15);assert(ReadValue<u8>(draw_state,0xc)==0);
}
"""
with tempfile.TemporaryDirectory(prefix="bbsc-visibility-") as directory:
    cpp = Path(directory) / "test.cpp"
    exe = cpp.with_suffix(".exe")
    cpp.write_text(fixture, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print("PASS: peer-specific visual and death repair, load, reconnect, unknown peer and leave guards")
