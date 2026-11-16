"""Exercise character switching during early load with temporary progress journals."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from test_menu_quit import ROOT, SOURCE, function


PREFIX = r"""
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <mutex>
#include <optional>
#include <string>
#include <utility>
#include <vector>
#define FMT_HEADER_ONLY
#include <fmt/format.h>
#define BBSC_MOD
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
using u8 = uint8_t;
using u32 = uint32_t;
using u64 = uint64_t;
using s32 = int32_t;
using s64 = int64_t;

std::array<u8, 0x1600> global{};
bool returning_to_title = false;
u64 image_base = 1;
constexpr u64 EventFlagManPointerOffset = 2;
u64 GetGlobalState() { return reinterpret_cast<u64>(global.data()); }
s32 GetSessionState() { return 0; }
s64 SteadyNowMs() { return 12345; }
bool ReadablePointer(u64 pointer, size_t size) {
    return pointer == GetGlobalState() && size <= global.size();
}
template<class T> T ReadValue(u64 pointer, size_t offset) {
    if (pointer == image_base + EventFlagManPointerOffset && offset == 0) return 1;
    assert(ReadablePointer(pointer, offset + sizeof(T)));
    T value{};
    std::memcpy(&value, global.data() + offset, sizeof(value));
    return value;
}
bool BbscReturningToTitle() { return returning_to_title; }
bool BbscSharedProgressEnabled() { return true; }
void RequestBbscRewardCheck() {}
struct { u64 held = 0; } bbsc_dream_own;

constexpr size_t BbscWorldGroupBytes = 125;
constexpr u32 BbscProgressFileMagic = 0x50534242;
std::mutex bbsc_progress_mutex;
bool bbsc_progress_accept_packets = false;
std::vector<u32> bbsc_progress_host_flags;
std::map<u32, std::array<u8, BbscWorldGroupBytes>> bbsc_progress_groups;
bool bbsc_progress_was_guest = false;
s64 bbsc_progress_left_ms = 0, bbsc_progress_home_ms = 0;
bool bbsc_progress_backed_up = false, bbsc_progress_merged_at_load = false;
namespace Chalice { bool TouchesLampUnlock(u32) { return false; } }
namespace Common::FS {
enum class PathType { CapturesDir };
std::filesystem::path GetUserPath(PathType) { return "captures"; }
}
"""

STUBS = r"""
std::optional<BbscSaveSlot> bbsc_progress_slot, bbsc_own_world_slot;
std::map<u32, std::array<u8, BbscWorldGroupBytes>> bbsc_own_world;
bool bbsc_own_world_dirty = false;
std::mutex bbsc_own_world_save_mutex;
bool write_ok = true;
u32 applied = 0;
bool WriteBbscTripJournal(const BbscSaveSlot&) { return write_ok; }
bool LoadBbscTripJournal(const BbscSaveSlot&) { return false; }
void DropBbscTripJournalMemory() {}
void WriteBbscOwnWorldFile() { if (write_ok) bbsc_own_world_dirty = false; }
void RestoreBbscOwnWorldAtLoad() {}
std::pair<s64, size_t> MergeBbscSharedProgress(const char*) {
    applied = bbsc_progress_host_flags.empty() ? 0 : bbsc_progress_host_flags[0];
    return {applied != 0, 0};
}
void ApplyBbscTalkJournal(const char*, bool) {}
"""

SCENARIO = r"""
void SelectCharacter(s32 slot) {
    std::memcpy(global.data() + BbscNativeCharacterSlotOffset, &slot, sizeof(slot));
    global[0x1592] = 1;
}

int main() {
    SelectCharacter(2);
    const auto first = BbscActiveSaveSlot();
    assert(first && first->slot == 2 && first->user == "sd1");
    assert(BindBbscGuestProgress());
    bbsc_progress_host_flags = {123};
    bbsc_progress_accept_packets = true;

    returning_to_title = true;
    assert(WriteBbscPendingProgress()); // menu confirmation flushes the guest's data
    ApplyBbscSharedProgressAtLoad();
    assert(applied == 0 && bbsc_progress_slot->slot == 2);

    returning_to_title = false;
    SelectCharacter(-1);
    ApplyBbscSharedProgressAtLoad();
    assert(!BbscActiveSaveSlot() && applied == 0 && bbsc_progress_slot->slot == 2);

    SelectCharacter(0); // the previous file was written last, but this is the loaded slot
    write_ok = false;
    bbsc_own_world_slot = first;
    bbsc_own_world[9] = {};
    bbsc_own_world_dirty = true;
    bbsc_dream_own.held = 1;
    assert(!AlignBbscOwnWorldSlot() && bbsc_own_world_slot->slot == 2);
    ApplyBbscSharedProgressAtLoad();
    assert(applied == 0 && bbsc_progress_slot->slot == 2);
    assert(!bbsc_progress_accept_packets);
    assert(std::filesystem::exists(BbscPendingProgressPath(*first)));

    write_ok = true;
    ApplyBbscSharedProgressAtLoad();
    assert(applied == 0 && !bbsc_progress_slot && bbsc_progress_host_flags.empty());
    assert(!bbsc_own_world_slot && bbsc_own_world.empty() && !bbsc_dream_own.held);
    assert(!std::filesystem::exists(BbscPendingProgressPath(*BbscActiveSaveSlot())));

    SelectCharacter(2);
    ApplyBbscSharedProgressAtLoad();
    assert(applied == 123 && bbsc_progress_slot->slot == 2 && bbsc_progress_merged_at_load);
}
"""


def run():
    source = PREFIX + SOURCE[SOURCE.index("struct BbscSaveSlot {"):
                             SOURCE.index("// ---- Own world journal")] + STUBS
    signatures = (
        "bool AlignBbscOwnWorldSlot()",
        "std::filesystem::path BbscPendingProgressPath(const BbscSaveSlot& slot)",
        "bool WriteBbscPendingProgress()",
        "bool LoadBbscPendingProgress(const BbscSaveSlot& slot)",
        "bool ParkBbscProgress()",
        "bool AlignBbscProgressSlot(const BbscSaveSlot& active)",
        "bool BindBbscGuestProgress()",
        "void ApplyBbscSharedProgressAtLoad()",
    )
    source += "\n".join(function(signature) for signature in signatures) + SCENARIO
    compiler = os.environ.get("CXX") or shutil.which("clang++") or "C:/msys64/clang64/bin/clang++.exe"
    with tempfile.TemporaryDirectory(prefix="bbsc-character-progress-") as directory:
        root = Path(directory)
        cpp = root / "test.cpp"
        executable = root / "test.exe"
        cpp.write_text(source, encoding="utf-8")
        subprocess.run([compiler, "-std=c++20", "-I", str(ROOT / "emulator/externals/fmt/include"),
                        str(cpp), "-o", str(executable)], check=True)
        env = {**os.environ, "BB_USER_DIR": str(root)}
        env["PATH"] = str(Path(compiler).parent) + os.pathsep + env.get("PATH", "")
        subprocess.run([str(executable)], cwd=root, env=env, check=True)
    print("PASS: title exit, different slot, write failure, and original slot recovery")


if __name__ == "__main__":
    run()
