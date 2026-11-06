"""Run production work notifications and scaling code in a concurrent C++ fixture.

No game launch: checks lost wakeups, cutscene backlog/deduplication, unchanged-frame
scaling cost, host heartbeat/expiry, changed settings and guest-count transitions.
"""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "emulator/src/core/bloodborne_re.cpp").read_text(encoding="utf-8")


def function(signature):
    start = SOURCE.index(signature + " {")
    opening = SOURCE.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (SOURCE[end] == "{") - (SOURCE[end] == "}")
        end += 1
    return SOURCE[start:end] + "\n"


prefix = r"""
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <deque>
#include <iostream>
#include <mutex>
#include <optional>
#include <thread>
#include <unordered_map>
#include <vector>
using u8=uint8_t; using u16=uint16_t; using u32=uint32_t; using u64=uint64_t;
using s16=int16_t; using s32=int32_t; using s64=int64_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...) ((void)0)
#define BBSC_TIMELINE(...) ((void)0)
#define BBSC_PERF_NESTED(...) ((void)0)
struct CountingMutex {
    std::mutex mutex; int locks=0;
    void lock() { mutex.lock(); ++locks; }
    void unlock() { mutex.unlock(); }
};
u64 image_base=1;
std::atomic<u32> bbsc_load_generation{1};
s64 now=100;
s32 session=6, extra=1;
size_t writes=0;
s64 SteadyNowMs() { return now; }
s32 GetSessionState() { return session; }
u32 GetCurrentPackedMap() { return 24; }
bool BbscScalingEnabled() { return true; }
s32 GetBbscGuestCount() { return extra; }
s32 GetBbscScalingGuests() { return extra; }
template<class T> bool WriteValue(u64, size_t, T) { ++writes; return true; }
enum class MemoryProt { CpuWrite };
bool HasMemoryAccess(u64,size_t,MemoryProt){return true;}
u64 bbsc_scale_npc_table=0x1000,bbsc_scale_effect_table=0x2000;
u16 bbsc_scale_npc_count=1;
u64 bbsc_scale_armor_begin=0,bbsc_scale_armor_end=0;
u64 BbscGameParamTable(std::string_view type){return type=="NPC_PARAM_ST"?bbsc_scale_npc_table:bbsc_scale_effect_table;}
template<class T>T ReadValue(u64,size_t){return T{1};}
void StartBbscScaling(){}
enum class BbscScaleState { Idle, Ready };
BbscScaleState bbsc_scale_state=BbscScaleState::Ready;
std::array<unsigned char,528> enemy_row{}, boss_row{};
std::vector<u64> bbsc_scale_rows_enemy{reinterpret_cast<u64>(enemy_row.data())}, bbsc_scale_rows_boss{reinterpret_cast<u64>(boss_row.data())};
struct BbscScaledNpc { u64 row; s16 armor; bool boss; };
std::vector<BbscScaledNpc> bbsc_scaled_npcs{{3,100,false}};
constexpr s64 BbscScaleFreshMs=15000;
"""

work = SOURCE[SOURCE.index("enum class BbscWork"):SOURCE.index("// ---- BBSC perf")]
scaling = SOURCE[SOURCE.index("struct BbscScaleNumbers"):SOURCE.index("const BbscScaleNumbers& BbscOwnScaleNumbers()")]
scaling = scaling.replace("std::mutex bbsc_scale_host_mutex;", "CountingMutex bbsc_scale_host_mutex;")
scaling += r"""
const BbscScaleNumbers& BbscOwnScaleNumbers() {
    static const BbscScaleNumbers own{{40,100,15,15,20}};
    return own;
}
"""
scaling += function("void TickBbscScaling()")
scaling += function("void OnBbscScalePacket(const std::uint16_t (&percent)[5])")

packet_start = SOURCE.index("struct BbscCutscenePacket")
packet = SOURCE[packet_start:SOURCE.index("\n};", packet_start) + 3]
cutscenes = "constexpr u8 BbscCutsceneType=0x28;\n#pragma pack(push, 1)\n" + packet + "\n#pragma pack(pop)\n"
cutscenes += r"""
std::mutex bbsc_cutscene_mutex;
std::deque<BbscCutscenePacket> bbsc_cutscene_queue;
std::unordered_map<s32,u32> bbsc_cutscene_seen;
bool bbsc_cutscene_replaying=false;
size_t replays=0;
void Replay(u64,u32,u32,u64,u32,u32,u64,u64,u64) { ++replays; }
const std::array<u64,1> BbscCutsceneRequestOffsets{reinterpret_cast<u64>(&Replay)-1};
bool BbscCutscenesEnabled() { return true; }
bool QueueBbscRomNativeTransition(s32) { return false; }
"""
cutscenes += function("void OnBbscCutscenePacket(const void* data, std::size_t size)")
cutscenes += function("void TickBbscCutsceneReplay()")

main = r"""
int main() {
    assert(TakeBbscWork()==0);
    QueueBbscWork(BbscWork::BossReward); QueueBbscWork(BbscWork::GuestDrop);
    auto mask=TakeBbscWork();
    assert(HasBbscWork(mask,BbscWork::BossReward));
    assert(HasBbscWork(mask,BbscWork::GuestDrop));
    assert(!HasBbscWork(mask,BbscWork::Cutscene));
    assert(TakeBbscWork()==0);
    // Four concurrent producers; publication before/after a drain must not lose work.
    std::mutex mutex; std::vector<int> queue;
    std::atomic<int> done{0}; std::vector<std::thread> producers;
    constexpr int count=25000;
    for (int producer=0; producer<4; ++producer) producers.emplace_back([&,producer] {
        for (int i=0;i<count;++i) {
            std::scoped_lock lock{mutex}; queue.push_back(producer*count+i);
            QueueBbscWork(BbscWork::GuestDrop);
        }
        ++done;
    });
    std::vector<int> delivered; size_t idle=0;
    while (done.load()!=4 || bbsc_pending_work.load()!=0) {
        if (HasBbscWork(TakeBbscWork(),BbscWork::GuestDrop)) {
            std::scoped_lock lock{mutex};
            delivered.insert(delivered.end(),queue.begin(),queue.end()); queue.clear();
        } else { ++idle; std::this_thread::yield(); }
    }
    for (auto& producer:producers) producer.join();
    assert(queue.empty()); assert(delivered.size()==4*count);
    std::sort(delivered.begin(),delivered.end());
    for (int i=0;i<4*count;++i) assert(delivered[i]==i);
    std::cout << "100000 queued actions, four producers: no loss/duplicates\n";

    BbscCutscenePacket packet{}; packet.map=24;
    for (u32 i=1;i<=3;++i) {
        packet.sequence=i; packet.cutscene=static_cast<s32>(i);
        OnBbscCutscenePacket(&packet,sizeof(packet));
        OnBbscCutscenePacket(&packet,sizeof(packet)); // duplicate relay/P2P
    }
    assert(bbsc_cutscene_queue.size()==3);
    for (int i=0;i<3;++i) {
        assert(HasBbscWork(TakeBbscWork(),BbscWork::Cutscene));
        TickBbscCutsceneReplay(); assert(replays==static_cast<size_t>(i+1));
    }
    assert(TakeBbscWork()==0 && bbsc_cutscene_queue.empty());
    std::cout << "cutscenes: deduplicated, one replay/frame, backlog rearmed\n";

    TickBbscScaling(); assert(writes==1);
    float hp; std::memcpy(&hp,enemy_row.data()+16,4); assert(hp>1.39f && hp<1.41f);
    const auto initial=writes;
    for (int i=0;i<10000;++i) TickBbscScaling();
    assert(writes==initial && bbsc_scale_host_mutex.locks==0);
    const u16 host[5]{80,200,30,30,40};
    OnBbscScalePacket(host);
    TickBbscScaling(); assert(writes==initial+1);
    assert(bbsc_scale_written->numbers.percent[0]==80);
    const auto applied=writes; const int locks=bbsc_scale_host_mutex.locks;
    for (int i=0;i<10000;++i) TickBbscScaling();
    assert(writes==applied && bbsc_scale_host_mutex.locks==locks);
    now=14000; OnBbscScalePacket(host); TickBbscScaling();
    assert(writes==applied); // heartbeat refreshes expiry without rewriting rows
    now=15100; TickBbscScaling(); assert(writes==applied);
    now=29000; TickBbscScaling(); assert(writes==applied+1);
    assert(bbsc_scale_written->numbers.percent[0]==40); // exact expiry
    now=30000; OnBbscScalePacket(host); TickBbscScaling();
    extra=2; TickBbscScaling(); assert(bbsc_scale_written->guests==2);
    session=0; extra=0; TickBbscScaling();
    assert(bbsc_scale_written->guests==0 && bbsc_scale_written->numbers.percent[0]==40);
    session=6; extra=1; TickBbscScaling();
    assert(bbsc_scale_written->numbers.percent[0]==80);
    const u16 changed[5]{90,210,35,31,41};
    OnBbscScalePacket(changed); TickBbscScaling();
    assert(bbsc_scale_written->numbers.percent[0]==90);
    bbsc_scaled_npcs.assign(1000, {3,100,false});
    extra=3; const auto batch_before=writes;
    TickBbscScaling(); assert(!bbsc_scale_written && writes-batch_before==8);
    extra=0; session=0; // interrupted update must restart even if returning to older key
    TickBbscScaling(); assert(!bbsc_scale_written);
    for(int i=0;i<200;++i) TickBbscScaling();
    assert(bbsc_scale_written && bbsc_scale_written->guests==0);
    auto complete=writes; TickBbscScaling(); assert(writes==complete);
    std::cout << "scaling: idle cache, packets, heartbeat, expiry, guests, solo/rejoin PASS\n";
}
"""

# Diagnostic handlers must exit before clocks/memory scans even if invoked elsewhere.
for name in ("GateWatch", "ItemSurvey", "StateDiff"):
    body = function("void TickBbsc" + name + "()")
    assert body.splitlines()[1].strip() == "if (!BbscResearchEnabled()) return;"
exit_handler = function("void TickBbscSessionExit(bool peer_work)")
assert "if (peer_work) QueueBbscWork(BbscWork::PeerLeft)" in exit_handler
for queue, kind in (("bbsc_boss_reward_queue.push_back(event);", "BossReward"),
                    ("bbsc_peer_left_pending[player] = host;", "PeerLeft")):
    assert SOURCE.split(queue, 1)[1].lstrip().startswith("QueueBbscWork(BbscWork::" + kind + ");")

with tempfile.TemporaryDirectory(prefix="bbsc-work-test-") as tmp:
    cpp, exe = Path(tmp) / "test.cpp", Path(tmp) / "test.exe"
    cpp.write_text(prefix + work + scaling + cutscenes + main, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "g++"), "-std=c++20", "-O2", "-pthread", str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=30)
print("diagnostic gating and departure retry integration: PASS")
