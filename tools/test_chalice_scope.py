"""Exercise production dungeon reads, snapshot assembly and scope switches without a game.

The memory fixture verifies recovered native loader input and borrowed-context lifecycle.
Actual resource loading and session continuity still require the documented two-PC test.
"""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "emulator/src/core/bloodborne_re.cpp").read_text(encoding="utf-8")


def function(signature, source=SOURCE):
    start = source.index(signature + " {")
    opening = source.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end] + "\n"


prefix = r'''
#include <algorithm>
#include <atomic>
#include <bit>
#include <charconv>
#include <cmath>
#include <array>
#include <cassert>
#include <cstring>
#include <map>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>
#define FMT_HEADER_ONLY
#include "fmt/format.h"
#include "core/bbsc_chalice.h"
#include "core/bbsc_follow.h"
#include "core/libraries/np/np_signaling/np_signaling_bbsc.h"
using namespace Core::Bloodborne;
#undef PS4_SYSV_ABI
#define PS4_SYSV_ABI
void NotifyBbscHostDeathReload() {}
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define LOG_ERROR(...)
#define BBSC_TIMELINE(...)
using Packet=Libraries::Np::NpSignaling::SignalingBbscWorldFlags;
u64 image_base=0x100000;
std::unordered_map<u64,u64> memory;
std::array<bool,7> selected{};
std::vector<u8> form(140, 17);
std::map<u64,std::array<s32,18>> arrays;
template<class T> T ReadValue(u64 p,size_t off) {
    if constexpr (std::is_same_v<T,std::array<s32,18>>) return arrays[p+off];
    else return static_cast<T>(memory[p+off]);
}
template<class T> bool WriteValue(u64 p,size_t off,const T& value) {
    if constexpr (std::is_same_v<T,std::array<s32,18>>) arrays[p+off]=value;
    else memory[p+off]=value;
    return true;
}
namespace MemoryProt { constexpr int CpuWrite=1; }
bool memory_writable=true;
bool HasMemoryAccess(u64 p,size_t,int) { return memory_writable && p>=0x10000; }
s32 session=3;
s32 GetSessionState() { return session; }
u64 GetGlobalState() { return 0x90000; }
struct GuestRegisterSnapshot {
    u64 r13{},rcx{},rdx{},r8{},r15{},rbp{},rbx{},rsi{},rax{};
};
struct SummonPlacementDescriptor { u32 packed_region; float x,y,z,heading; s32 area; };
std::optional<SummonPlacementDescriptor> bbsc_connect_first_placement,seamless_received_host_placement;
auto& initial_claim=bbsc_connect_first_placement;
bool seamless_received_host_placement_consumed=false;
std::mutex seamless_placement_mutex;
std::atomic<u32> bbsc_tick_map{},bbsc_connect_first_map{};
std::atomic<s64> bbsc_connect_first_since_ms{};
bool BbscConnectFirstEnabled(){return true;}
constexpr s64 BbscConnectFirstTimeoutMs=90000;
bool bbsc_join_teleport_done=false, bbsc_chalice_transition_owned=false;
constexpr u64 StageTransitionOffset=0x013cde30;
s32 player_type=1, hp=594;
s32 GetLocalPlayerType() { return player_type; }
u64 GetLocalPlayerCharacter() { return 0x80000; }
s32 GetCharacterHp(u64) { return hp; }
template<class... Args> bool InstallGuestCodeHook(Args&&...) { return true; }
bool ReadablePointer(u64 p,size_t) { return p >= 0x10000; }
bool BbscEventFlag(u32 f) { return f>=9020 && f<=9026 && selected[f-9020]; }
s64 now=1000;
s64 SteadyNowMs() { return now; }
constexpr s64 BbscFollowStaleMs=15000;
bool BbscWarpTogetherEnabled() { return true; }
bool quitting=false; bool BbscQuitInProgress(){return quitting;}
bool BbscMapResident(u32){return false;}
u32 relay_host=9; u32 GetBbscRelayHost(){return relay_host;}
bool IsSprjLuaEventManReady(){return true;}
int departures=0; void OnBbscPeerLeft(u32,bool){++departures;}
int native_loads=0; void SummonedReload(){++native_loads;}
bool enabled=true;
bool BbscWorldSyncEnabled() { return enabled; }
u32 current=0x1d000000;
u32 GetCurrentPackedMap() { return current; }
bool IsUsablePackedMap(u32 m) { return m && m!=0xffffffff; }
constexpr size_t BbscWorldGroupBytes=125, BbscWorldChunkGroups=8;
constexpr size_t BbscWorldGroupCount=40, BbscDreamGroupCount=57;
bool compact_world=false; bool BbscCompactWorldSnapshots(){return compact_world;}
constexpr size_t BbscWorldChunkCount=5, BbscDreamChunkCount=8, BbscSnapshotMaxGroups=57;
constexpr s64 BbscWorldFlagsFreshMs=6000;
std::vector<std::vector<u8>> sent;
namespace Libraries::Np::NpSignaling::Helpers {
u32 SendBbscWorldFlagsToPeers(const void* p,u32 size) {
    sent.emplace_back(static_cast<const u8*>(p),static_cast<const u8*>(p)+size); return 1;
}
}
std::array<u8,125> group{};
u64 BbscFlagGroupStorage(u32) { return reinterpret_cast<u64>(group.data()); }
u32 key_of(u32,size_t n) { return static_cast<u32>(12900+n); }
'''

start = SOURCE.index("struct BbscWorldSnapshot {")
end = SOURCE.index("// Host side: one snapshot", start)
snapshots = SOURCE[start:end].replace(function("bool BbscCompactWorldSnapshots()"), "")
start = SOURCE.index("struct BbscFollowMessage {")
end = SOURCE.index("BbscFollowMessage bbsc_follow_latest{};", start) + len("BbscFollowMessage bbsc_follow_latest{};")
follow = SOURCE[start:end]

scope_prefix = r'''
std::string bbsc_loot_dungeon;
std::map<u32,int> bbsc_loot_groups, bbsc_loot_saved;
std::optional<int> bbsc_loot_slot;
bool bbsc_loot_loaded=false,bbsc_loot_dirty=false;
u32 bbsc_loot_area=0;
bool fail_write=false;
int flushes=0;
void WriteBbscGuestLootFile() { ++flushes; if (!fail_write) bbsc_loot_dirty=false; }
'''

main = r'''
int main() {
    // Snapshot from the host must neither unlock nor relock personal altar destinations.
    for (u8 original : {0x00, 0xFF}) {
        std::array<u8,125> live,host;
        live.fill(original); host.fill(static_cast<u8>(~original));
        Chalice::CopyHostFlagGroup(12907,live.data(),host);
        for (u32 bit=0;bit<1000;++bit) {
            const bool lamp=bit>=830 && bit<=990 && (bit-830)%20==0;
            const u8 expected=lamp ? original : host[bit/8];
            assert(((live[bit/8]^expected)&(0x80u>>(bit%8)))==0);
        }
        Chalice::CopyHostFlagGroup(12908,live.data(),host);assert(live==host);
    }
    for (s32 role : {0,3,4,6,7}) {
        session=role;memory[0x91592]=0;
        assert(BbscProtectChaliceAltar(12907870)==(role==4||role==6||role==7));
        assert(!BbscProtectChaliceAltar(12907871));
        memory[0x91592]=1;
        if(role==7) assert(!BbscProtectChaliceAltar(12907870));
    }
    session=3;
    // Recover the host's native ritual without depending on the altar number.
    memory[image_base+0x0553e9e8]=0x20000;
    memory[0x20000]=7; memory[0x20008]=0x30000;
    memory[0x30000+2*8]=0x40000; memory[0x40000+0x1d8]=0x50000;
    memory[0x50010]=42; memory[0x50058]=reinterpret_cast<u64>(form.data()); memory[0x50060]=140;
    selected[2]=true;
    const auto a=ReadBbscOwnChaliceKey(); assert(Chalice::Valid(a));
    selected[2]=false; selected[5]=true; memory[0x30000+5*8]=0x40000;
    assert(ReadBbscOwnChaliceKey()==a);
    selected[1]=true; assert(!Chalice::Valid(ReadBbscOwnChaliceKey())); selected[1]=false;
    memory[0x50060]=0x10000008cULL; assert(!Chalice::Valid(ReadBbscOwnChaliceKey())); memory[0x50060]=140;
    memory[0x50010]=0x8000000000000000ULL;
    assert(!Chalice::Valid(ReadBbscOwnChaliceKey())); memory[0x50010]=42;
    form[0]^=1; assert(ReadBbscOwnChaliceKey()!=a); form[0]^=1;
    auto unknown=a; unknown.form_version=1; assert(!Chalice::Valid(unknown));

    InstallBbscChaliceHooks(); bbsc_chalice_flag_hook_ready=true;
    // The real hook captures pointer-free host stage-loader input.
    GuestRegisterSnapshot host{};
    host.rbp=0xa0000; host.rbx=0xb0000; host.r13=current;
    host.rcx=42; host.rdx=0x1d050000; host.r8=123; host.r15=3;
    arrays[host.rbp-0x78].fill(-1); arrays[host.rbp-0x78][0]=9910000;
    BbscChaliceContextHook(0,&host);
    const auto mount=BbscHostChaliceMount(); assert(Chalice::ValidMount(mount));
    assert(mount.revision==1 && mount.layout_map==0x1d050000);
    SendBbscChaliceMount(); assert(sent.size()==1 && sent[0].size()==Chalice::MountPacketSize);
    auto descriptor=sent[0]; sent.clear();
    const auto before=memory;
    OnBbscChaliceMountPacket(descriptor.data(),descriptor.size());
    assert(memory==before); // receive callbacks never touch game memory
    OnBbscHostFollowPacket(current,0,0,0,0,1,-1,a);
    u64 present=0; group[0]=0x80;
    SendBbscFlagSnapshot(1,current,1,40,key_of,present);
    assert(sent.size()==5 && sent[0].size()==sizeof(Packet)+sizeof(Chalice::Key)+8);
    assert(sent[0][5]==4 && sent[0].size()+13+8+40 < 1280);
    for (int i=4;i>0;--i) OnBbscWorldFlagsPacket(sent[i].data(),sent[i].size());
    assert(!BbscChaliceLoadReady(current));
    OnBbscWorldFlagsPacket(sent[0].data(),sent[0].size());
    assert(BbscChaliceLoadReady(current));

    // Production compact sender and receiver: keep all30 gameplay groups,
    // no diagnostic kind5, and don't declare completion before the final part.
    compact_world=true; sent.clear(); ClearBbscHostWorldSnapshots();
    OnBbscChaliceMountPacket(descriptor.data(),descriptor.size());
    present=0; SendBbscFlagSnapshot(1,current,77,40,key_of,present);
    assert(sent.size()==4 && sent[0][5]==6);
    assert(present==((u64{1}<<30)-1));
    for(int i=3;i>0;--i) OnBbscWorldFlagsPacket(sent[i].data(),sent[i].size());
    assert(!BbscChaliceLoadReady(current));
    OnBbscWorldFlagsPacket(sent[0].data(),sent[0].size());
    assert(BbscChaliceLoadReady(current));
    assert(bbsc_world_blocks.at(current).groups[29][0]==0x80);
    assert(bbsc_world_blocks.at(current).groups[30][0]==0);
    const auto compact_dungeon=sent;
    sent.clear(); SendBbscFlagSnapshot(1,0x18010000,78,40,key_of,present);
    assert(sent.size()==4 && sent[0][5]==5);
    for(const auto& p:sent) OnBbscWorldFlagsPacket(p.data(),p.size());
    assert(bbsc_world_blocks.contains(0x18010000));
    assert(bbsc_world_blocks.at(0x18010000).present==((u64{1}<<30)-1));
    // A compact header cannot trick the parser into accepting a legacy shape.
    ClearBbscHostWorldSnapshots(); auto malformed=sent[0]; malformed[15]=5;
    OnBbscWorldFlagsPacket(malformed.data(),malformed.size());
    assert(bbsc_world_blocks.empty());
    OnBbscChaliceMountPacket(descriptor.data(),descriptor.size());
    for(const auto& p:compact_dungeon) OnBbscWorldFlagsPacket(p.data(),p.size());
    compact_world=false;

    // Direct summon to a host already in a dungeon: native entry has no BBSC warp prepare.
    // Even all three native map candidates can still be the guest's old/invalid map.
    session=6; current=0x18010000; selected.fill(false);
    initial_claim=SummonPlacementDescriptor{mount.map};
    // Gate the actual snapshot/phase transition before any native load starts.
    enabled=false;
    assert(GateBbscChaliceSummon() && bbsc_chalice_summon_map==mount.map);
    assert(bbsc_chalice_borrowed.armed.revision==0);
    bbsc_chalice_summon_since-=15000;TickBbscChaliceSummon();assert(departures==1 && !bbsc_chalice_summon_map);
    assert(GateBbscChaliceSummon());
    quitting=true;TickBbscChaliceSummon();assert(!bbsc_chalice_summon_map);
    quitting=false;assert(GateBbscChaliceSummon());
    ++relay_host;TickBbscChaliceSummon();assert(!bbsc_chalice_summon_map);--relay_host;
    // Early same-map claim, then relay identity becomes available; release exactly once.
    bbsc_tick_map=mount.map;bbsc_connect_first_map=0x15000000;
    assert(SetSeamlessHostPlacementHeader("1,1d000000,0,0,0,0,290100"));
    assert(bbsc_connect_first_map==0 && BbscChaliceInitialJoinMap()==mount.map);
    memory[0x91592]=1;relay_host=0;assert(GateBbscChaliceSummon());
    now+=100;TickBbscChaliceSummon();assert(!native_loads);
    enabled=true;relay_host=9;now+=100;TickBbscChaliceSummon();TickBbscChaliceSummon();
    assert(native_loads==1 && !bbsc_chalice_summon_map);
    enabled=true;assert(!GateBbscChaliceSummon());
    assert(BbscChaliceJoinNeedsFollow()); // do not teleport dungeon coords into Yharnam
    GuestRegisterSnapshot first_load{};
    first_load.r13=0xffffffff; first_load.rbx=0xe0000; first_load.rbp=0xf0000;
    memory[first_load.rbx+0x48]=0;
    BbscChaliceContextHook(0,&first_load);
    assert(first_load.r13==mount.stage_map && first_load.rcx==mount.key.channel);
    assert(bbsc_chalice_borrowed.pending && bbsc_chalice_borrowed.applied_revision==mount.revision);
    current=mount.map; CompleteBbscChaliceLoad(current);
    assert(!BbscChaliceJoinNeedsFollow());
    initial_claim.reset(); bbsc_chalice_borrowed={};
    bbsc_tick_map=0x15000000;
    assert(SetSeamlessHostPlacementHeader("1,15000000,0,0,0,0,210000"));
    assert(!BbscConnectFirstHost() && !bbsc_connect_first_map);

    // An already joined living guest suppresses the unprepared native m29 transition.
    // No teardown/global writes; host, initial summon, death, home, invader and BBSC follow pass.
    GuestRegisterSnapshot transition{};
    memory[0x9000c]=mount.map; memory[0x91592]=0; memory[0x90008]=0;
    bbsc_join_teleport_done=true;
    const auto guard_memory=memory;
    BbscChaliceTransitionHook(0,&transition);
    assert(bbsc_chalice_transition_skip==1 && transition.rax==1 && memory==guard_memory);
    auto passes=[&] {
        bbsc_chalice_transition_skip=0; transition.rax=99;
        BbscChaliceTransitionHook(0,&transition);
        assert(bbsc_chalice_transition_skip==0 && transition.rax==99);
    };
    bbsc_chalice_transition_owned=true; passes(); bbsc_chalice_transition_owned=false;
    hp=0; passes(); hp=594;
    player_type=2; passes(); player_type=1;
    memory[0x91592]=1; passes(); memory[0x91592]=0;
    memory[0x90008]=1; passes(); memory[0x90008]=0;
    memory[0x9000c]=0x15000000; passes(); memory[0x9000c]=mount.map;
    session=3; passes(); session=6;
    bbsc_join_teleport_done=false; passes();

    // Entry from Dream with no own altar: keep the same co-op role throughout.
    session=6; current=0x15000000; selected.fill(false);
    assert(!Chalice::Valid(ReadBbscOwnChaliceKey()));
    assert(BbscChaliceLoadReady(mount.map));
    assert(PrepareBbscChaliceLoad(mount.map));
    assert(ReadBbscChaliceKey()==a && BbscChaliceNeedsLoad(mount.map));
    assert(BbscProtectChaliceAltar(9020)); assert(BbscProtectChaliceAltar(94000000));
    assert(BbscProtectChaliceAltar(93999999,2));
    assert(!BbscProtectChaliceAltar(52900000)); assert(!BbscProtectChaliceAltar(12900000));
    assert(!BbscProtectChaliceAltar(94700000));
    GuestRegisterSnapshot write{}; write.rsi=94000000; write.rdx=32;
    BbscChaliceValueHook(0,&write); assert(bbsc_chalice_value_skip==1);
    CompleteBbscChaliceLoad(mount.map); assert(!BbscChaliceArrivalReady(mount.map));
    GuestRegisterSnapshot guest{};
    guest.rbp=0xc0000; guest.rbx=0xd0000; guest.r13=0xffffffff;
    memory[guest.rbx+0x48]=mount.map; arrays[guest.rbp-0x78].fill(-1);
    memory_writable=false; BbscChaliceContextHook(0,&guest);
    assert(guest.r13==0xffffffff && bbsc_chalice_borrowed.applied_revision==0);
    memory_writable=true; BbscChaliceContextHook(0,&guest);
    assert(session==6 && guest.r13==mount.stage_map && guest.rcx==42);
    assert(guest.rdx==mount.layout_map && guest.r8==123 && guest.r15==3);
    assert(arrays[guest.rbp-0x78]==mount.parts && memory[0x9000c]==mount.stage_map);
    assert(!BbscChaliceArrivalReady(mount.map));
    current=mount.map; CompleteBbscChaliceLoad(current);
    assert(BbscChaliceArrivalReady(current) && !BbscChaliceNeedsLoad(current));
    assert(!selected[5] && memory[0x50010]==42); // own altar fields not changed
    BbscWorldSnapshot stale;
    assert(BbscHostBlockSnapshot(current,stale) && BbscChaliceSnapshotMatches(stale));
    enabled=false; assert(!BbscChaliceLoadReady(current)); enabled=true;
    auto other=a; other.channel=43;
    OnBbscHostFollowPacket(current,0,0,0,0,2,-1,other);
    assert(!BbscChaliceLoadReady(current)); // an old complete snapshot cannot override follow identity
    OnBbscHostFollowPacket(current,0,0,0,0,3,-1,a);
    assert(SelectBbscLootScope(current)); const auto first=bbsc_loot_dungeon;
    assert(first.find("-chalice-")==0);
    bbsc_loot_dirty=true; bbsc_loot_groups[52900]=1;
    fail_write=true; assert(!SelectBbscLootScope(0x18000000));
    assert(bbsc_loot_dungeon==first && bbsc_loot_groups.size()==1);
    fail_write=false; assert(SelectBbscLootScope(0x18000000));
    assert(bbsc_loot_dungeon.empty() && bbsc_loot_groups.empty());
    assert(Chalice::IsLootGroup(52900) && !Chalice::IsLootGroup(52400));
    assert(!Chalice::IsLootGroup(12900));

    // A new load with the same virtual map/key requires the matching new flag generation.
    auto newer=mount; newer.revision=2; newer.parts[0]=9920000;
    std::memcpy(descriptor.data()+8,&newer,sizeof(newer));
    OnBbscChaliceMountPacket(descriptor.data(),descriptor.size());
    assert(!BbscChaliceLoadReady(current)); assert(BbscChaliceNeedsLoad(current));
    sent.clear(); bbsc_chalice_native=newer;
    selected[5]=true; session=3;
    SendBbscFlagSnapshot(1,current,2,40,key_of,present);
    session=6; selected.fill(false);
    for (const auto& packet:sent) OnBbscWorldFlagsPacket(packet.data(),packet.size());
    assert(BbscChaliceLoadReady(current));
    assert(!BbscChaliceSnapshotMatches(stale)); // readiness of a newer cache cannot validate an old copy
    assert(PrepareBbscChaliceLoad(current));
    CancelBbscChaliceLoad(); assert(bbsc_chalice_borrowed.armed.revision==1);
    assert(PrepareBbscChaliceLoad(current));
    BbscChaliceContextHook(0,&guest); CompleteBbscChaliceLoad(current);
    assert(!BbscChaliceNeedsLoad(current));
    // Ordinary walking to another resident part does not start another load.
    newer.map=0x1d010000;
    std::memcpy(descriptor.data()+8,&newer,sizeof(newer));
    OnBbscChaliceMountPacket(descriptor.data(),descriptor.size());
    OnBbscHostFollowPacket(newer.map,0,0,0,0,4,-1,a);
    assert(!BbscChaliceNeedsLoad(newer.map));
    assert(BbscChaliceArrivalReady(newer.map)); // resident walking keeps loot capture enabled
    // A delayed descriptor cannot roll the loader back to an older revision.
    std::memcpy(descriptor.data()+8,&mount,sizeof(mount));
    OnBbscChaliceMountPacket(descriptor.data(),descriptor.size());
    assert(bbsc_chalice_remote.revision==2);
    auto bad=newer; bad.feature=4;
    std::memcpy(descriptor.data()+8,&bad,sizeof(bad));
    OnBbscChaliceMountPacket(descriptor.data(),descriptor.size());
    assert(bbsc_chalice_remote.feature==3);
    bad=newer; bad.parts[0]=-2; assert(!Chalice::ValidMount(bad));
    bad=newer; bad.reserved=1; assert(!Chalice::ValidMount(bad));
    now+=6000; assert(!BbscLatestChaliceMount(newer.map,bad)); now-=6000;
    bbsc_chalice_value_hook_ready=false; assert(!BbscLatestChaliceMount(newer.map,bad));
    bbsc_chalice_value_hook_ready=true;

    // Return to Dream/own world discards the loan, without changing a ritual.
    current=0x15000000; now=1500; TickBbscChaliceBorrow();
    assert(!Chalice::ValidMount(bbsc_chalice_borrowed.armed));
    assert(!BbscProtectChaliceAltar(94000000));
    session=0; memory[0x90008]=0; memory[0x91592]=1;
    now=2000; TickBbscChaliceBorrow(); assert(session==0);

    // Strict framing rejects unscoped/malformed chunks and never mixes native revisions.
    ClearBbscHostWorldSnapshots();
    auto packet=sent[0]; packet.resize(sizeof(Packet)); packet[5]=1;
    OnBbscWorldFlagsPacket(packet.data(),packet.size()); assert(bbsc_world_blocks.empty());
    packet=sent[0]; packet[17]=0;
    OnBbscWorldFlagsPacket(packet.data(),packet.size()); assert(bbsc_world_blocks.empty());
    for (int i=0;i<4;++i) OnBbscWorldFlagsPacket(sent[i].data(),sent[i].size());
    packet=sent[4]; u64 rev=3; std::memcpy(packet.data()+sizeof(Packet)+sizeof(a),&rev,8);
    OnBbscWorldFlagsPacket(packet.data(),packet.size()); assert(bbsc_world_blocks.empty());
    for (const auto& chunk:sent) OnBbscWorldFlagsPacket(chunk.data(),chunk.size());
    assert(bbsc_world_blocks.size()==1);
    sent.clear(); present=0;
    SendBbscFlagSnapshot(1,0x18000000,3,40,key_of,present);
    assert(sent[0].size()==sizeof(Packet) && sent[0][5]==1);
    // Root-layout variants: all 18 native parts and both loader feature bits,
    // different FormData/ChannelIds but the SAME virtual map. Exercise first
    // summon and subsequent follow with the actual capture/preparation/hooks.
    bbsc_chalice_borrowed={};
    for (u32 variant=0;variant<4;++variant) {
        ClearBbscHostWorldSnapshots();
        session=3; selected.fill(false); selected[5]=true; current=mount.map;
        form[8]=static_cast<u8>(variant+1); memory[0x50010]=1000+variant;
        const auto root_key=ReadBbscOwnChaliceKey(); assert(root_key!=a);
        host.rcx=root_key.channel; host.r13=current; host.r15=variant; host.r8=3;
        host.rdx=0x1d350000;
        for(u32 part=0;part<18;++part) arrays[host.rbp-0x78][part]=9910000+variant*10000+part;
        const auto expected_parts=arrays[host.rbp-0x78];
        BbscChaliceContextHook(0,&host);
        const auto root_mount=BbscHostChaliceMount(); assert(Chalice::ValidMount(root_mount));
        sent.clear(); SendBbscChaliceMount();
        OnBbscChaliceMountPacket(sent[0].data(),sent[0].size());
        OnBbscHostFollowPacket(current,0,0,0,0,100+variant,-1,root_key);
        sent.clear(); present=0;
        SendBbscFlagSnapshot(1,current,10+variant,40,key_of,present);
        session=6; selected.fill(false);
        for(const auto& chunk:sent) OnBbscWorldFlagsPacket(chunk.data(),chunk.size());
        assert(BbscChaliceLoadReady(current));
        assert(BbscChaliceNeedsLoad(current)); // map equality never hides a new ritual
        initial_claim.reset(); bbsc_join_teleport_done=false;
        if(variant==0) {
            bbsc_tick_map=current;
            assert(SetSeamlessHostPlacementHeader("1,1d000000,0,0,0,0,290100"));
            assert(bbsc_connect_first_map==0 && BbscChaliceInitialJoinMap()==current);
            assert(!GateBbscChaliceSummon());
        } else assert(PrepareBbscChaliceLoad(current));
        guest.r13=0xffffffff; memory[guest.rbx+0x48]=current;
        arrays[guest.rbp-0x78].fill(-1);
        BbscChaliceContextHook(0,&guest);
        assert(arrays[guest.rbp-0x78]==expected_parts);
        assert(guest.rcx==root_key.channel && guest.rdx==host.rdx);
        assert(guest.r8==3 && guest.r15==variant && guest.r13==root_mount.stage_map);
        CompleteBbscChaliceLoad(current);
        assert(BbscChaliceArrivalReady(current) && !BbscChaliceNeedsLoad(current));
        assert(!BbscChaliceJoinNeedsFollow());
        assert((ReadBbscChaliceKey()==root_key && selected==std::array<bool,7>{}));
    }
    puts("chalice: direct native summon, no cross-world teleport, one transition owner, native capture/injection, seamless Dream entry, altar guards, same-map revisions, cancellation/cleanup, replay/malformed packets, ordinary maps PASS");
}
'''

start = SOURCE.index("// Borrowed loader input is process-local.")
end = SOURCE.index("// Host side: say where we are", start)
bridge = SOURCE[start:end].replace("reinterpret_cast<void PS4_SYSV_ABI (*)()>(image_base + 0x0131E5C0)()", "SummonedReload()")
code = prefix + function("bool IsSameSummonPlacement(const SummonPlacementDescriptor& left,\n                           const SummonPlacementDescriptor& right)")
code += function("bool BbscConnectFirstPlacementFresh()")
code += function("std::optional<SummonPlacementDescriptor> BbscConnectFirstHost()")
code += function("bool SetSeamlessHostPlacementHeader(std::string_view value)")
code += function("Chalice::Key ReadBbscOwnChaliceKey()") + follow
code += "bool BbscChaliceLoadReady(u32);\nbool PrepareBbscChaliceLoad(u32);\n" + bridge + snapshots
code += function("void OnBbscChaliceMountPacket(const void* data, std::size_t size)")
code += function("void OnBbscHostFollowPacket(std::uint32_t packed_map, float x, float y, float z, float heading,\n"
                 "                            std::uint32_t sequence, std::int32_t lamp_point,\n"
                 "                            const Chalice::Key& dungeon, const Follow::Arrival& arrival)").replace("const Follow::Arrival& arrival)", "const Follow::Arrival& arrival = {})")
for signature in (
    "u32 SendBbscFlagSnapshot(u8 version, u32 map, u32 snapshot, size_t count,\n"
    "                         u32 (*key_of)(u32 map, size_t index), u64& present)",
    "bool BbscHostBlockSnapshot(u32 packed_map, BbscWorldSnapshot& out)",
    "bool BbscChaliceSnapshotMatches(const BbscWorldSnapshot& host)",
    "bool BbscChaliceLoadReady(u32 map)",
    "void OnBbscWorldFlagsPacket(const void* data, std::uint32_t size)",
):
    code += function(signature)
relay = (ROOT / "emulator/mod/bbsc_relay.cpp").read_text(encoding="utf-8")
start = relay.index("struct FollowPacket {")
end = relay.index("\n};", start) + 3
code += "constexpr u8 FollowType=0x20;\n#pragma pack(push,1)\n" + relay[start:end] + "\n#pragma pack(pop)\n"
code += "u32 SendFrame(const void* p,u32 size) { return Libraries::Np::NpSignaling::Helpers::SendBbscWorldFlagsToPeers(p,size); }\n"
code += "namespace Libraries::Np::NpSignaling::Helpers {\n" + function(
    "u32 SendBbscFollowToPeers(u32 packed_map, float x, float y, float z, float heading, u32 sequence,\n"
    "                          s32 lamp_point, const Core::Bloodborne::Chalice::Key& dungeon,\n"
    "                          const Core::Bloodborne::Follow::Arrival& arrival)", relay).replace("const Core::Bloodborne::Follow::Arrival& arrival)", "const Core::Bloodborne::Follow::Arrival& arrival = {})") + "}\n"
code += scope_prefix + function("bool SelectBbscLootScope(u32 map)") + main

with tempfile.TemporaryDirectory(prefix="bbsc-chalice-") as tmp:
    cpp, exe = Path(tmp) / "test.cpp", Path(tmp) / "test.exe"
    cpp.write_text(code, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-O2",
                    "-I" + str(ROOT / "emulator/src"),
                    "-I" + str(ROOT / "emulator/externals/fmt/include"),
                    str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=30)
