// SPDX-License-Identifier: GPL-2.0-or-later
// Included after native travel, presence and the event iterator are available.
namespace Finale = Bbsc::DreamFinale;
#ifdef BBSC_MOD
using FinalePhase = Finale::Phase;

struct BbscNativeFinaleState {
    World::WorldId world{};
    Finale::Signal signal{};
    u32 load = 0;
    u8 recall = 0;
    u8 selected = 0;
    bool dialogue = false;
    bool returning = false;
    bool delegated = false;
    bool cycle_prepared = false;
    bool released = false;
    bool retired = false;
    bool stopping = false;
};
BbscNativeFinaleState bbsc_native_finale;
// The existing progress and flag receivers can run on the signaling thread.
std::atomic<bool> bbsc_native_finale_committed{false};
void ConsumeBbscFinaleDialog();

Finale::Signal BbscFinalePresence(World::WorldId world) {
    return world == bbsc_native_finale.world ? bbsc_native_finale.signal : Finale::Signal{};
}

bool BbscNativeFinaleActive() {
    const auto& finale = bbsc_native_finale;
    return finale.dialogue || BbscNativeFinalePlaying();
}

bool BbscNativeFinalePlaying() {
    const auto& finale = bbsc_native_finale;
    return finale.selected || finale.signal.ending;
}

bool BbscNativeFinaleCommitted() {
    return bbsc_native_finale_committed.load(std::memory_order_acquire);
}

bool BbscNativeFinaleWantsPresence() {
    return bbsc_native_finale.recall && !BbscNativeFinaleCommitted();
}

// The native room supplies the roster even when members have no PlayerIns
// on this map. A presence observation alone cannot add a participant.
bool BbscFinalePeers(World::WorldId world, Finale::Signal expected) {
    const s32 count = GetBbscSessionMemberCount(GetGlobalState());
    if (count < 2 || count > 5) return false;
    std::array<u32, 4> peers{};
    size_t size = 0;
    for (const auto task : GetMultiPlayerInsTasks()) {
        if (ReadValue<s32>(task, 0xE8) != 1 || (ReadValue<u8>(task, 0xED) & 2)) continue;
        const u32 peer = BbscWorldPeer(task + 0xC8);
        if (!peer) return false;
        if (std::find(peers.begin(), peers.begin() + size, peer) != peers.begin() + size) continue;
        if (size == peers.size()) return false;
        peers[size++] = peer;
    }
    if (size != static_cast<size_t>(count - 1)) return false;
    std::scoped_lock lock{bbsc_world_presence_mutex};
    if (bbsc_world_presence_local.world != world) return false;
    for (size_t i = 0; i < size; ++i) {
        const auto* member = bbsc_world_presence_book.Resident(peers[i]);
        if (!member || !(member->presence.capabilities & World::NativeFinaleCapability)) return false;
        const auto& p = member->presence;
        if (expected.phase == FinalePhase::None) continue;
        if (p.finale != expected) return false;
        if (expected.phase == FinalePhase::Ready &&
            (p.phase != World::Phase::Playing || p.map != Finale::Map || !p.alive)) return false;
    }
    return true;
}

void ProcessBbscNativeFinale() {
    ConsumeBbscFinaleDialog();
    auto& finale = bbsc_native_finale;
    if (BbscQuitInProgress() || BbscReturningToTitle()) {
        finale = {};
        bbsc_native_finale_committed.store(false, std::memory_order_release);
        return;
    }
    // Native Stop can remove the room before the local new-cycle load finishes.
    if (BbscNativeFinaleCommitted()) return;
    World::Presence local;
    Finale::Signal host;
    {
        std::scoped_lock lock{bbsc_world_presence_mutex};
        local = bbsc_world_presence_local;
        if (const auto* member = bbsc_world_presence_book.Resident(local.world.host))
            host = member->presence.finale;
    }
    const s32 role = GetSessionState();
    if (!World::Valid(local.world) || role == 7) {
        finale = {};
        return;
    }
    if ((role != 3 && role != 6) || !BbscIndependentTravelAllowed()) return;
    if (finale.world != local.world) finale = {local.world};
    if (role == 3) {
        const bool alone = GetBbscSessionMemberCount(GetGlobalState()) == 1;
        if (finale.signal.phase == FinalePhase::AtEnd &&
            (alone || BbscFinalePeers(finale.world, finale.signal)))
            finale.signal.phase = FinalePhase::Release;
        return;
    }
    if (host.phase == FinalePhase::Recall && host.token != finale.recall)
        finale = {local.world, {}, 0, host.token};
    if (!finale.recall || host.token != finale.recall) return;
    if (host.phase == FinalePhase::Recall && !finale.selected &&
        local.phase == World::Phase::Playing && local.alive) {
        if (local.map == Finale::Map) {
            finale.signal = {FinalePhase::Ready, host.token, 0};
        } else if (!finale.returning && !BbscWorldTravelInFlight()) {
            finale.returning = true;
            // Same command called by native 2003[49]. The existing independent
            // warp hook adopts the Dream destination and preserves room tasks.
            using Warp = void PS4_SYSV_ABI (*)(s32);
            reinterpret_cast<Warp>(image_base + 0x013CDF30)(2102950);
            BBSC_TIMELINE("DREAM", "native Dream warp requested for the host's recall");
        }
    }
    if (finale.signal.phase == FinalePhase::Ready && local.map == Finale::Map &&
        (host.phase == FinalePhase::Play || host.phase == FinalePhase::AtEnd))
        finale.selected = host.ending;
    if (finale.selected == host.ending &&
        (host.phase == FinalePhase::Release || host.phase == FinalePhase::Committed ||
         host.phase == FinalePhase::Arrived)) finale.released = true;
}

bool BbscDelegateNativeFinale(u64 instance, const Finale::Event& event) {
    const auto* range = LookupBbscQuestRange(instance);
    if (!range || range->event != event.id || ReadValue<u64>(range->row, 0x18) != 0 ||
        ReadValue<u64>(instance, 0x88) != range->row) return false;
    const u64 root = ReadValue<u64>(instance, 0x80);
    const u64 ref = ReadValue<u64>(instance, 0xA8);
    const u64 file = ReadablePointer(ref, 0x10) ? ReadValue<u64>(ref, 8) : 0;
    const s32 current = ReadValue<s32>(instance, 0xA0);
    const u64 target = range->first + event.start * 0x20;
    if (!file || !ReadablePointer(root, 0x10) || ReadValue<u64>(root, 8) != file ||
        current < 0 || current > 2 || target >= range->end) return false;
    const bool submission = event.start == 3;
    if (ReadValue<s32>(target, 0) != (submission ? 2003 : 1001) ||
        ReadValue<s32>(target, 4) != (submission ? 2 : 0)) return false;
    using Clear = void PS4_SYSV_ABI (*)(u64);
    using Advance = u8 PS4_SYSV_ABI (*)(u64, u8*);
    if (!WriteValue<u8>(instance, 0x78, 0) ||
        !WriteValue<s32>(instance, 0xC0, event.start - current)) return false;
    reinterpret_cast<Clear>(image_base + 0x012EBFF0)(instance + 0x30);
    u8 continue_frame = 1;
    if (!reinterpret_cast<Advance>(image_base + 0x012EF2E0)(instance + 0x80, &continue_frame))
        return false;
    WriteValue<s32>(instance, 0x48, ReadValue<s32>(instance, 0xA0));
    WriteValue<s32>(instance, 0x60, 10000);
    return true;
}

bool GuardBbscNativeFinaleEvent(u64 instance, s64 event, s32 role) {
    const u8 ending = Finale::EventEnding(event);
    if (!ending) return false;
    if (role != 4 && role != 6) return false;
    auto& finale = bbsc_native_finale;
    if (role != 6 || finale.selected != ending)
        return true; // keep the guest instance alive at its original entry
    if (!finale.delegated) {
        if (!PrepareBbscSharedFinaleActor() ||
            !BbscDelegateNativeFinale(instance, Finale::Events[ending - 1])) return true;
        finale.delegated = true;
    }
    return false;
}

bool GuardBbscNativeFinaleCommand(u64 instance) {
    auto& finale = bbsc_native_finale;
    if (!ReadablePointer(instance, 0xC0)) return false;
    const s32 step = ReadValue<s32>(instance, 0xA0);
    if (step != 3 && step != 10 && step != 12 && step != 14 && step != 24 &&
        step != 35 && step != 36 && step != 43 && step != 44)
        return false;
    const auto* range = LookupBbscQuestRange(instance);
    if (!range || !(range->handlers & EventSteps::Finale)) return false;
    const u8 ending = Finale::EventEnding(range->event);
    if (!ending || GetCurrentPackedMap() != Finale::Map) return false;
    const auto& event = Finale::Events[ending - 1];
    const s32 role = GetSessionState();
    if (role == 3 && step == event.start && finale.signal.phase == FinalePhase::Recall &&
        finale.dialogue) {
        // The accepted native dialogue has already checked the whole room.
        // Its admission outlives transient presence/PlayerIns updates in the fight.
        if (!PrepareBbscSharedFinaleActor()) return true;
        finale.dialogue = false;
        finale.signal = {FinalePhase::Play, finale.recall, ending};
        BBSC_TIMELINE("DREAM", "native group ending {} started", ending);
    }
    if (role == 6 && finale.selected == ending && step == event.increment && !finale.cycle_prepared) {
        // A summoned load saves our cycle in +159C before adopting the
        // host's. Restore that input before the game's own capped increment.
        const u64 global = GetGlobalState();
        const u64 data = ReadValue<u64>(image_base + PlayerSlotManagerPointerOffset, 0);
        if (ReadablePointer(global, 0x15A0) && ReadValue<u8>(global, 0x1598)) {
            const s32 own_cycle = ReadValue<s32>(global, 0x159C);
            if (own_cycle >= 0 && own_cycle <= 7) WriteValue<s32>(data, 0x68, own_cycle);
        }
        finale.cycle_prepared = true;
    }
    if (step != event.commit || (role != 3 && role != 6) ||
        (role == 3 ? finale.signal.ending : finale.selected) != ending) return false;
    if (finale.signal.phase != FinalePhase::AtEnd && finale.signal.phase != FinalePhase::Release &&
        finale.signal.phase != FinalePhase::Committed) {
        finale.signal = {FinalePhase::AtEnd, finale.recall, ending};
        QueueBbscWork(BbscWork::Finale);
    }
    if (finale.signal.phase == FinalePhase::Committed) return false;
    if (role == 3) {
        std::scoped_lock lock{bbsc_world_presence_mutex};
        if (bbsc_world_presence_local.world != finale.world ||
            bbsc_world_presence_local.finale.phase != FinalePhase::Release) return true;
    } else if (!finale.released) return true;
    finale.load = bbsc_load_generation.load();
    finale.signal.phase = FinalePhase::Committed;
    bbsc_native_finale_committed.store(true, std::memory_order_release);
    if (role == 6) RestoreBbscOwnWorld("before native ending", true);
    BBSC_TIMELINE("DREAM", "native group ending {} released to the new cycle", ending);
    return false;
}

bool ApplyBbscNativeFinaleDescriptor(u64 descriptor) {
    if (!BbscNativeFinaleCommitted() || !ReadablePointer(descriptor, 0x90) ||
        ReadValue<u32>(descriptor, 8) != 0x18010000 ||
        ReadValue<u32>(descriptor, 0x54) != 8 || ReadValue<u32>(descriptor, 0x58) != 2)
        return false;
    // The type-8 new-cycle descriptor initially takes the live cycle, then
    // 01944C79 can replace it with a summon-era value. The native loader
    // 01937D51 commits +8C (copied to its task at +DC) as the live cycle.
    const u64 data = ReadValue<u64>(image_base + PlayerSlotManagerPointerOffset, 0);
    const s32 cycle = ReadValue<s32>(data, 0x68);
    if (cycle >= 1 && cycle <= 7) WriteValue<s32>(descriptor, 0x8C, cycle);
    return true;
}

void DepartBbscNativeFinaleAtSpawn(u64 task) {
    auto& finale = bbsc_native_finale;
    if (!BbscNativeFinaleCommitted() || finale.stopping || !ReadablePointer(task, 0xA8) ||
        ReadValue<u32>(task, 0x58) != 0x18010000 || ReadValue<u32>(task, 0xA4) != 8)
        return;
    const u64 global = GetGlobalState();
    if (!ReadablePointer(global, 0x1593) || !ReadValue<u8>(global, 0x1592)) return;
    const s32 role = GetSessionState();
    if (role != 0 && role != 3 && role != 6 && role != 7) return;
    const u64 manager = ReadValue<u64>(image_base + MatchingStatePointerOffset, 0);
    if ((role == 3 || role == 6) &&
        (!ReadablePointer(manager, 0x128) || ReadBbscWorldRoom() != finale.world.room)) return;

    finale.stopping = true;
    RetireBbscNativeFinaleCycle();
    bbsc_recover_session_cleanup = true;
    if (role == 3 || role == 6) {
        // Same Stop / stage reason / remote cleanup as native StageHelper. The
        // NG+ task already owns the load, so there is no second warp request.
        using Stop = u8 PS4_SYSV_ABI (*)(u64);
        const u8 stopped = reinterpret_cast<Stop>(image_base + MultiPlayStopRequestOffset)(manager);
        const u64 rules = ReadValue<u64>(image_base + SummonSessionRulesPointerOffset, 0);
        if (stopped && ReadablePointer(rules, 0xF4)) WriteValue<s32>(rules, 0xF0, 8);
        BBSC_TIMELINE("DREAM", "native NG+ loading: ending the old room (Stop -> {})", stopped);
    }
    CleanupBbscDepartingRemotes();
}

void FinishBbscNativeFinaleLoad() {
    auto& finale = bbsc_native_finale;
    if (!BbscNativeFinaleCommitted() || bbsc_load_generation.load() == finale.load ||
        GetSessionState() != 0 || GetCurrentPackedMap() != 0x18010000) return;
    const u64 global = GetGlobalState();
    if (!ReadablePointer(global, 0x1593) || !ReadValue<u8>(global, 0x1592)) return;
    RetireBbscNativeFinaleCycle();
    const u64 data = ReadValue<u64>(image_base + PlayerSlotManagerPointerOffset, 0);
    BBSC_TIMELINE("DREAM", "native NG+ arrival in own world cycle={}", ReadValue<s32>(data, 0x68));
    finale = {};
    bbsc_native_finale_committed.store(false, std::memory_order_release);
}

void RetireBbscNativeFinaleCycle() {
    auto& finale = bbsc_native_finale;
    if (finale.retired) return;
    finale.retired = true;
    // Retire the borrowed story snapshots before the new world can use them.
    ClearBbscHostWorldSnapshots();
    {
        std::scoped_lock lock{bbsc_progress_mutex};
        bbsc_progress_host_flags.clear();
        bbsc_progress_groups.clear();
    }
    {
        std::scoped_lock lock{bbsc_npc_own_mutex};
        bbsc_npc_own.clear();
        bbsc_action_owner.clear();
    }
    FinishBbscPendingProgress();
    if (bbsc_progress_slot) FinishBbscTripJournal(*bbsc_progress_slot);
    DropBbscTripJournalMemory();
    bbsc_host_time_bits = -1;
    bbsc_home_spot.valid = false;
    bbsc_guest_respawn_held = false;
    bbsc_independent_states.clear();
    const auto story = [](const auto& entry) { return !Chalice::IsMap(entry.first.map); };
    std::erase_if(bbsc_world_lamps, story);
    std::erase_if(bbsc_world_lamp_pending, story);
    BindBbscSharedLamp({});
}

// The original yes/no message used by the Abandoned Old Workshop's return
// prompt supplies the FMG slot. Scope the custom text to this one dialog.
constexpr u32 BbscFinaleDialogText = 10010713;
struct BbscFinaleDialog {
    u64 native = 0;
    u64 slot = 0;
    u64 previous = 0;
    u64 replacement = 0;
    World::WorldId world{};
    u32 load = 0;
};
BbscFinaleDialog bbsc_finale_dialog;
std::atomic<u64> bbsc_finale_dialog_native{0};
std::atomic<s32> bbsc_finale_dialog_result{-1};

void ClearBbscFinaleDialog() {
    bbsc_finale_dialog_native = 0;
    bbsc_finale_dialog_result = -1;
    const auto old = std::exchange(bbsc_finale_dialog, {});
    if (old.slot && ReadValue<u64>(old.slot, 0) == old.replacement)
        WriteValue<u64>(old.slot, 0, old.previous);
}

void PS4_SYSV_ABI BbscGehrmanTalkAccepted(u64, const GuestRegisterSnapshot* regs) {
    // f56(6003) in t210305. Only the original successful action can open
    // the prompt. The original result writer still finishes the ESD call.
    bbsc_finale_talk_skip = 0;
    if (!bbsc_finale_hooks_ready || !regs ||
        bbsc_world_esd_function != 56 || bbsc_world_esd_talk != GehrmanTalkId ||
        !ReadablePointer(regs->rbp - 0x370, 8) || ReadValue<u64>(regs->rbp - 0x370, 0) != 6003 ||
        GetSessionState() != 3 || GetCurrentPackedMap() != Finale::Map ||
        !BbscNightIsOver() || GetBbscSessionMemberCount(GetGlobalState()) <= 1) return;
    auto& finale = bbsc_native_finale;
    World::WorldId world;
    { std::scoped_lock lock{bbsc_world_presence_mutex}; world = bbsc_world_presence_local.world; }
    if (finale.world == world && finale.signal.phase == FinalePhase::Recall &&
        BbscFinalePeers(world, {FinalePhase::Ready, finale.recall, 0})) {
        finale.dialogue = true;
        return;
    }
    const_cast<GuestRegisterSnapshot*>(regs)->r13 = 0;
    bbsc_finale_talk_skip = 1;
    if (!World::Valid(world) || !BbscIndependentTravelAllowed() || !BbscFinalePeers(world, {}))
        return;
    const u64 menu = ReadValue<u64>(image_base + 0x05562878, 0);
    const u64 dialog = ReadablePointer(menu, 0xD10) ? ReadValue<u64>(menu, 0xD08) : 0;
    using MenuState = u32 PS4_SYSV_ABI (*)();
    if (!ReadablePointer(dialog, 0x20) ||
        (reinterpret_cast<MenuState>(image_base + 0x0176B7E0)() & 8)) return;
    ClearBbscFinaleDialog();
    u64 fmg = 0;
    const u64 slot = FindBbscMessageSlot(30, BbscFinaleDialogText, &fmg);
    if (!slot) return;
    const auto text = BbscL(u"Summon all hunters to the Dream?", u"Призвать всех охотников в Сон?");
    const u64 replacement = reinterpret_cast<u64>(text) - fmg;
    const u64 previous = ReadValue<u64>(slot, 0);
    if (!WriteValue<u64>(slot, 0, replacement)) return;
    bbsc_finale_dialog = {dialog, slot, previous, replacement, world, bbsc_load_generation.load()};
    bbsc_finale_dialog_native = dialog;
    using OpenDialog = void PS4_SYSV_ABI (*)(u32, s32, s32);
    reinterpret_cast<OpenDialog>(image_base + 0x0176C470)(BbscFinaleDialogText, 0, 2);
}

void PS4_SYSV_ABI BbscFinaleDialogResult(u64, const GuestRegisterSnapshot* regs) {
    if (!regs || !regs->rcx || regs->rcx != bbsc_finale_dialog_native.load() ||
        ReadValue<u32>(regs->rcx, 0) != BbscFinaleDialogText) return;
    s32 pending = -1;
    if (bbsc_finale_dialog_result.compare_exchange_strong(pending, static_cast<s32>(regs->rdx)))
        QueueBbscWork(BbscWork::Finale);
}

void ConsumeBbscFinaleDialog() {
    const s32 result = bbsc_finale_dialog_result.exchange(-1);
    if (result == -1) return;
    const auto dialog = bbsc_finale_dialog;
    ClearBbscFinaleDialog();
    if (result != 1 || !dialog.native || GetSessionState() != 3 ||
        GetCurrentPackedMap() != Finale::Map || !BbscNightIsOver() ||
        bbsc_load_generation.load() != dialog.load || !BbscFinalePeers(dialog.world, {})) return;
    static u8 token = 0;
    if (++token == 0) ++token;
    bbsc_native_finale = {dialog.world, {FinalePhase::Recall, token, 0}, 0, token};
    BBSC_TIMELINE("DREAM", "host confirmed the group recall before Gehrman");
}
#else
bool BbscNativeFinaleActive() { return false; }
bool BbscNativeFinalePlaying() { return false; }
bool BbscNativeFinaleCommitted() { return false; }
bool ApplyBbscNativeFinaleDescriptor(u64) { return false; }
void DepartBbscNativeFinaleAtSpawn(u64) {}
void FinishBbscNativeFinaleLoad() {}
bool GuardBbscNativeFinaleEvent(u64, s64, s32) { return false; }
void ClearBbscFinaleDialog() {}
void RetireBbscNativeFinaleCycle() {}
#endif
