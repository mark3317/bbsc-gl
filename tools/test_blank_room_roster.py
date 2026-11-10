"""Run the production Blank hooks with the original Yes and item dispatch code."""
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ELF = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parents[1] / 'out/exit-study.elf'
production = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
trace = production[production.index('void PS4_SYSV_ABI TraceEntry('):]
assert 'if (site.offset == 0x0178D9C0) {\n        ClearBbscHomeTypeOverrideBeforeSummonFinish();' in trace
data = ELF.read_bytes()
ph = struct.unpack_from('<Q', data, 32)[0]
stride, count = struct.unpack_from('<HH', data, 54)
segments = [struct.unpack_from('<II6Q', data, ph + i * stride) for i in range(count)]


def copy_original(address, size):
    segment = next(p for p in segments if p[0] == 1 and p[3] <= address
                   and address + size <= p[3] + p[5])
    offset = segment[2] + address - segment[3]
    values = ','.join(map(str, data[offset:offset + size]))
    return f'    {{ const u8 code[] = {{{values}}}; memcpy(image + {address}, code, sizeof(code)); }}\n'


source = r'''
#include <windows.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>
#include "core/cpu_patches.h"
using Core::GuestRegisterSnapshot;
using Core::InstallGuestCodeHook;
namespace BbscMod {
struct RegisterIdentity {char name[17]{};};
bool PartyEnabled(){return true;}
u64 EbootAddress();
void LogPlain(const char*){}
}
#define LOG_ERROR(...) assert(false)
#define BBSC_TIMELINE(...)
constexpr u64 MatchingStatePointerOffset=0x5540290, CandidateLocalStatePointerOffset=0x553E878;
constexpr u64 PlayerSlotManagerPointerOffset=0x553B130;
constexpr u64 MemberIdEqualsOffset=0xCA1C70;
u64 image_base=0, room=100, resident=0;
s64 bbsc_persistence_restore_at_ms=0;
u64 BbscMod::EbootAddress(){return image_base;}
s32 role=3;
bool quitting=false, returning_to_title=false;
bool bbsc_host_selected_blank=false, ready=true;
std::array<std::array<u8,0x20>,3> members{};
std::array<std::array<u8,0x20>,4> roster{};
u64 last_kick=0;
int constructs=0, destroys=0, resident_kicks=0, room_kicks=0;
const char16_t* BbscL(const char16_t* en,const char16_t*){return en;}
void BbscAnnounce(const char16_t*,std::string_view){}
s32 GetSessionState(){return role;}
u64 ReadBbscWorldRoom(){return room;}
bool BbscIndependentActive(){return true;}
bool BbscQuitInProgress(){return quitting;}
bool BbscReturningToTitle(){return returning_to_title;}
enum class MemoryProt {CpuWrite};
bool ReadablePointer(u64 addr,size_t){return addr>=0x10000;}
bool HasMemoryAccess(u64 addr,size_t,MemoryProt){return addr>=0x10000;}
bool IsValidMemberId(u64 addr){return addr>=0x10000;}
template <class T> T ReadValue(u64 addr,size_t offset){
    T value;memcpy(&value,reinterpret_cast<void*>(addr+offset),sizeof(value));return value;
}
template <class T> bool WriteValue(u64 addr,size_t offset,T value){
    memcpy(reinterpret_cast<void*>(addr+offset),&value,sizeof(value));
    return true;
}
u64 GetGlobalState(){return ReadValue<u64>(image_base+0x5556678,0);}
template <class T> u64 Addr(T& object){return reinterpret_cast<u64>(object.data());}
struct MemberSlotInfo{s32 index,type;};
MemberSlotInfo GetMemberSlotInfoByMember(u64 member){
    const u64 identity=ReadValue<u64>(member,0);
    if(!identity)return {-1,-1};
    return {ReadValue<s32>(identity,20),ReadValue<s32>(identity,24)};
}
BbscMod::RegisterIdentity BbscWorldIdentity(u64 member){
    BbscMod::RegisterIdentity out;
    memcpy(out.name,reinterpret_cast<void*>(ReadValue<u64>(member,0)),sizeof(out.name));
    return out;
}
u64 FindBbscRemotePlayerByMember(u64,u64 member){
    return ReadValue<u64>(member,0)==Addr(members[0])?resident:0;
}
bool PS4_SYSV_ABI Equals(u64 first,u64 second){
    return ReadValue<u64>(first,0)==ReadValue<u64>(second,0);
}
void PS4_SYSV_ABI Construct(u64 addr){++constructs;WriteValue(addr,0,u64{0});}
void PS4_SYSV_ABI Destroy(u64 addr){++destroys;assert(ReadValue<u64>(addr,0));}
void PS4_SYSV_ABI Assign(u64 first,u64 second){WriteValue(first,0,ReadValue<u64>(second,0));}
void PS4_SYSV_ABI ConstructText(u64 out,u64 source){
    assert(source==image_base+0x49D85F0);
    memset(reinterpret_cast<void*>(out),0,0x38);
}
void PS4_SYSV_ABI AssignText(u64 out,const char16_t* text,size_t size){
    memcpy(reinterpret_cast<void*>(out),text,size*sizeof(char16_t));
}
bool PS4_SYSV_ABI NativeReady(u64){return ready;}
bool PS4_SYSV_ABI NativeKick(u64,u64 member){++room_kicks;last_kick=member;return true;}
void PS4_SYSV_ABI NativeActorKick(u64,u64 actor){assert(actor==resident);++resident_kicks;}
void Jump(u64 addr,u64 target){
    u8 bytes[]{0x48,0xB8,0,0,0,0,0,0,0,0,0xFF,0xE0};
    memcpy(bytes+2,&target,sizeof(target));
    memcpy(reinterpret_cast<void*>(addr),bytes,sizeof(bytes));
}
'''
start = production.index('void ClearBbscHomeTypeOverrideBeforeSummonFinish() {')
source += production[start:production.index('\n}', start) + 2] + '\n'
source += (ROOT / 'emulator/src/core/bbsc_blank_roster.inc').read_text(encoding='utf-8')
source += r'''
void PS4_SYSV_ABI ReloadFinish(u64,const GuestRegisterSnapshot*) {
    ClearBbscHomeTypeOverrideBeforeSummonFinish();
}
int main(){
    auto* image=static_cast<u8*>(VirtualAlloc(nullptr,0x5600000,MEM_RESERVE|MEM_COMMIT,
                                              PAGE_EXECUTE_READWRITE));
    assert(image);image_base=reinterpret_cast<u64>(image);
'''
for address, size in [(0x016E6FB0, 0x168), (0x016E7150, 6), (0x01BC4F90, 0x77),
                      (0x015BE2A0, 6), (0x018FF760, 0x2A),
                      (0x01332B60, 0x17), (0x015C9850, 0xE3), (0x0178D9C0, 0xCA),
                      (0x01939470, 0x72), (0x01BC3D10, 0x12),
                      (0x01BC69C0, 0x12), (0x01BC6AD0, 0x12),
                      (0x018F74DF, 0x13)]:
    source += copy_original(address, size)

source += r'''
    const auto link=[&](u64 address,auto function){Jump(image_base+address,reinterpret_cast<u64>(function));};
    link(MemberIdEqualsOffset,Equals);
    link(0xCA1440,Construct);link(0xCA1570,Destroy);link(0xCA1BA0,Assign);
    link(0x27C0E00,ConstructText);link(0x262A720,AssignText);
    link(0xC8F570,NativeReady);link(0xC8EE30,NativeKick);link(0x178DBE0,NativeActorKick);
    // Native builder's exact return address, with R15=0 for the first row.
    const u8 builder[]{0x41,0x57,0x45,0x31,0xFF,0xE8,0,0,0,0,0x41,0x5F,0xC3};
    memcpy(image+0x1BC1EC6,builder,sizeof(builder));
    WriteValue(image_base+0x1BC1ECC,0,s32{0x16E6FB0-0x1BC1ED0});
    // Enter the original host effect branch with R14 = local character.
    const u8 effect_entry[]{0x41,0x56,0x49,0x89,0xFE};
    memcpy(image+0x18FF75B,effect_entry,sizeof(effect_entry));
    const u8 effect_exit[]{0x41,0x5E,0xC3};
    memcpy(image+0x18FF78A,effect_exit,sizeof(effect_exit));
    std::array<u8,0x130> manager{};
    std::array<u8,0x1700> global{};
    std::array<u8,0x68> world{};
    std::array<u8,0x560> player{};
    std::array<u8,0x474> action{};
    std::array<u8,0xB8> modules{};
    std::array<u8,0x820> animation{};
    std::array<u8,0x10> callback{};
    WriteValue(image_base+MatchingStatePointerOffset,0,Addr(manager));
    WriteValue(image_base+CandidateLocalStatePointerOffset,0,Addr(world));
    WriteValue(image_base+0x5556678,0,Addr(global));
    WriteValue(image_base+0x5562878,0,Addr(action));

    // Run the original StageFlow through its final choice of constructor type.
    // Return that value instead of running the remaining constructor and world setup.
    const u8 stage_exit[]{0x44,0x89,0xF8,0x48,0x83,0xC4,0x18,0x5B,
                         0x41,0x5C,0x41,0x5D,0x41,0x5E,0x41,0x5F,0x5D,0xC3};
    memcpy(image+0x19394E2,stage_exit,sizeof(stage_exit));
    image[0x14CCD40]=0xC3; // skip the unrelated slot appearance update
    std::array<u8,0x90> rules{}, slots{};
    std::array<u8,0x210> local_slot{};
    std::array<u32,2> restore_data{};
    const u64 stack_cookie=0;
    WriteValue(image_base+0x53E3BE0,0,reinterpret_cast<u64>(&stack_cookie));
    WriteValue(image_base+0x553D6D0,0,Addr(rules));
    WriteValue(image_base+PlayerSlotManagerPointerOffset,0,Addr(slots));
    WriteValue(image_base+0x553B188,0,Addr(restore_data));
    WriteValue(Addr(slots),8,Addr(local_slot));
    const auto set_home_type=reinterpret_cast<void PS4_SYSV_ABI (*)()>(image_base+0x1332B60);
    const auto create_type=reinterpret_cast<s32 PS4_SYSV_ABI (*)(u64)>(image_base+0x1939470);
    const auto summon=[&](s32 sign, s32 pending, s32 phase=3){
        WriteValue(Addr(rules),0x84,phase);
        WriteValue(Addr(global),0x16F0,sign);
        if (pending==0) set_home_type();
        else WriteValue(Addr(slots),0x8C,pending);
        return create_type(Addr(world));
    };
    role=6;
    assert(summon(-1,0)==0); // native home override wins over the assigned co-op type
    const std::array<u8,6> reload_prologue{0x55,0x48,0x89,0xE5,0x41,0x57};
    assert(InstallGuestCodeHook(image+0x178D9C0,reload_prologue,0,ReloadFinish));
    const s32 coop_type=summon(-1,0);
    assert(coop_type==1 && ReadValue<s32>(Addr(slots),0x8C)==-1);
    assert(summon(-1,-1)==1 && summon(-3,0)==2 && summon(-4,0)==12);
    assert(summon(-1,12)==12 && summon(-1,0,4)==0);
    for (const s32 state : {0,3,4,7}) { role=state; assert(summon(-1,0)==0); }
    role=6;
    WriteValue(Addr(global),0x1592,u8{1});assert(summon(-1,0)==0);
    WriteValue(Addr(global),0x1592,u8{0});
    quitting=true;assert(summon(-1,0)==0);quitting=false;
    returning_to_title=true;assert(summon(-1,0)==0);returning_to_title=false;
    bbsc_persistence_restore_at_ms=1;assert(summon(-1,0)==0);bbsc_persistence_restore_at_ms=0;
    role=3;
    puts("PASS native summon type: stale home override, co-op/invader types and native return guards");

    WriteValue(Addr(world),0x60,Addr(player));
    WriteValue(Addr(player),0x3B0,Addr(modules));
    WriteValue(Addr(modules),8,Addr(animation));
    WriteValue(Addr(manager),0xF8,Addr(roster));
    WriteValue(Addr(manager),0x100,Addr(roster)+sizeof(roster));
    for(s32 i=0;i<3;++i){
        memcpy(members[i].data(),i==0?"Here":i==1?"Away":"Invader",i==0?5:i==1?5:8);
        WriteValue(Addr(members[i]),20,i);
        WriteValue(Addr(members[i]),24,s32{i==2?2:coop_type});
        WriteValue(Addr(roster[i]),0,Addr(members[i]));
    }
    // Execute the original item-metadata call before its later +1C0 refresh.
    // Stop immediately after the call; its argument remains the native module.
    image[0x18F74F2]=0xC3;
    // Wrapper supplies the original update's R13 = local actor.
    const u8 metadata_entry[]{0x41,0x55,0x49,0x89,0xFD,0xE8,0,0,0,0,0x41,0x5D,0xC3};
    memcpy(image+0x2000,metadata_entry,sizeof(metadata_entry));
    WriteValue(image_base+0x2006,0,s32{0x18F74DF-0x200A});
    // A stand-in for metadata lookup records the goods seen at that exact call.
    link(0x1A50AD0,+[](u64 module) PS4_SYSV_ABI {
        WriteValue<s32>(module,0,ReadValue<s32>(ReadValue<u64>(module,8),0x1C0));
    });
    std::array<u64,2> metadata{}; metadata[1]=Addr(player);
    WriteValue(Addr(modules),0xB0,Addr(metadata));
    const auto read_metadata=reinterpret_cast<void PS4_SYSV_ABI (*)(u64)>(image+0x2000);
    const auto general_yes=reinterpret_cast<void PS4_SYSV_ABI (*)()>(image+0x1BC3D10);
    WriteValue<s32>(Addr(player),0x47C,111);WriteValue<s32>(Addr(player),0x490,2);
    WriteValue<s32>(Addr(player),0x1C0,1000);
    general_yes(); read_metadata(Addr(player));
    assert(metadata[0]==1000); // reproduces stale Blood Vial context before the fix
    InstallBbscBlankRoster();
    assert(bbsc_blank_roster_ready);
    for (s32 state : {0,3,6}) {
        role=state;
        for (u64 address : {0x1BC3D10ull,0x1BC69C0ull,0x1BC6AD0ull}) {
            for (s32 previous : {1000,1010,200}) {
                WriteValue<s32>(Addr(player),0x1C0,previous);
                WriteValue<s32>(Addr(player),0x478,previous);
                reinterpret_cast<void PS4_SYSV_ABI (*)()>(image+address)();
                read_metadata(Addr(player));
                assert(metadata[0]==111 && ReadValue<s32>(Addr(player),0x478)==111);
                assert(ReadValue<s32>(Addr(player),0x47C)==111 && ReadValue<s32>(Addr(player),0x490)==2);
            }
        }
    }
    role=3;
    WriteValue<s32>(Addr(player),0x47C,1010);
    WriteValue<s32>(Addr(player),0x1C0,1010);
    general_yes();assert(ReadValue<s32>(Addr(player),0x1C0)==1010);
    WriteValue<s32>(Addr(player),0x47C,111);
    for(s32 phase : {0,1,3,5,7}) {
        WriteValue<s32>(Addr(player),0x490,phase);general_yes();
        assert(ReadValue<s32>(Addr(player),0x1C0)==1010);
    }
    WriteValue<s32>(Addr(player),0x490,2);
    puts("PASS Blank confirmation: reproduced stale vial metadata; host/guest/solo, native Yes and silence stores, other goods and phases");
    using List=bool PS4_SYSV_ABI (*)(s32*);
    using Name=u64 PS4_SYSV_ABI (*)(u64,u32);
    using Yes=void PS4_SYSV_ABI (*)(u64);
    const auto list=reinterpret_cast<List>(image_base+0x1BC1EC6);
    const auto name=reinterpret_cast<Name>(image_base+0x16E7150);
    const auto yes=reinterpret_cast<Yes>(image_base+0x1BC4F90);
    const auto effect=reinterpret_cast<Yes>(image_base+0x18FF75B);
    s32 rows[2]{};
    assert(list(rows) && BbscBlankToken(rows[0]) && BbscBlankToken(rows[1]));
    const auto first=rows[0],away=rows[1];
    assert(list(rows) && rows[0]==first && rows[1]==away && constructs==4 && destroys==2);
    std::array<u8,0x38> text{};
    assert(name(Addr(text),1)==Addr(text) &&
           std::u16string_view(reinterpret_cast<char16_t*>(text.data()))==u"Away");
    WriteValue(Addr(callback),8,away);
    WriteValue<s32>(Addr(player),0x1C0,1000);
    yes(Addr(callback));
    read_metadata(Addr(player));assert(metadata[0]==111);
    assert(ReadValue<s32>(Addr(player),0x55C)==away && ReadValue<u8>(Addr(animation),0x818)==8);
    assert(!room_kicks && !resident_kicks);
    effect(Addr(player));
    assert(room_kicks==1 && last_kick==Addr(roster[1]) && bbsc_host_selected_blank);
    assert(ReadValue<s32>(Addr(player),0x55C)==-1);

    // A resident guest still goes through the original actor-aware operation.
    resident=0x12345;WriteValue(Addr(callback),8,first);
    yes(Addr(callback));effect(Addr(player));
    assert(room_kicks==1 && resident_kicks==1);

    // The member leaves after Yes. Another occupant of the slot cannot be kicked.
    WriteValue(Addr(callback),8,away);yes(Addr(callback));
    WriteValue(Addr(roster[1]),0,Addr(members[2]));
    effect(Addr(player));
    assert(room_kicks==1 && resident_kicks==1);
    yes(Addr(callback));assert(ReadValue<s32>(Addr(player),0x55C)==-1);
    assert(list(rows) && rows[0]==first && rows[1]==-1);

    // A new room cannot inherit a confirmation from the previous room.
    ++room;WriteValue(Addr(callback),8,first);yes(Addr(callback));
    assert(ReadValue<s32>(Addr(player),0x55C)==-1);
    assert(list(rows) && rows[0]!=first && rows[1]==-1);
    puts("PASS native Blank: list/name/Yes/effect, off-map MemberId, original resident kick, stale selection and room fences");
}
'''
compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
with tempfile.TemporaryDirectory(prefix='bbsc-blank-roster-') as tmp:
    directory = Path(tmp)
    cpp, exe = directory / 'test.cpp', directory / 'test.exe'
    cpp.write_text(source, encoding='utf-8')
    subprocess.run([compiler, '-std=c++20', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
                    '-I', str(ROOT / 'emulator/src'), '-I', str(ROOT / 'emulator/externals/xbyak'),
                    str(cpp), str(ROOT / 'emulator/mod/bbsc_hooks.cpp'), '-o', str(exe)], check=True)
    env = dict(os.environ, PATH=str(Path(compiler).parent) + os.pathsep + os.environ.get('PATH', ''))
    subprocess.run([str(exe)], env=env, check=True, timeout=15)
