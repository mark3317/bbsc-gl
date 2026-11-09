// SPDX-License-Identifier: GPL-2.0-or-later
// Included at the native item gate, after the lifecycle helpers are defined.
#ifdef BBSC_MOD
struct BbscPendingPartyItem {
    std::uint64_t ticket = 0;
    u64 player = 0, global = 0;
    u32 map = 0, generation = 0;
    s32 argument = 0, state = 0;
    std::chrono::steady_clock::time_point started{};
};
BbscPendingPartyItem bbsc_pending_party_item;
std::mutex bbsc_party_item_mutex;
thread_local bool bbsc_party_item_replaying = false;

bool BbscPartyItemContext(const BbscPendingPartyItem& item) {
    return !BbscReturningToTitle() && !BbscQuitInProgress() &&
           item.player == GetLocalPlayerCharacter() && item.global == GetGlobalState() &&
           item.map == GetCurrentPackedMap() && item.state == GetSessionState() &&
           item.generation == bbsc_load_generation.load() && !bbsc_reload_finish_pending.load() &&
           ReadablePointer(item.global, 0x10) && ReadValue<u8>(item.global, 8) == 0 &&
           GetCharacterHp(item.player) > 0;
}

bool GateBbscPartyItem(const GuestRegisterSnapshot& registers) {
    using Mailbox = BbscMod::PartyAcquireMailbox;
    auto& item = bbsc_pending_party_item;
    if (bbsc_party_item_replaying) {
        return registers.rdi == item.player && BbscPartyItemContext(item) &&
               BbscMod::PartyAcquireResult(item.ticket) == Mailbox::Granted;
    }
    std::unique_lock lock{bbsc_party_item_mutex, std::try_to_lock};
    if (!lock) return false;
    // Repeated native callbacks / repeated button presses share the same request.
    if (item.ticket) return false;
    item = {0, registers.rdi, GetGlobalState(), GetCurrentPackedMap(), bbsc_load_generation.load(),
            static_cast<s32>(registers.rdx), GetSessionState(), std::chrono::steady_clock::now()};
    if ((item.state != 0 && item.state != 3) || !BbscPartyItemContext(item)) {
        item = {};
        return false;
    }
    item.ticket = BbscMod::PartyRequestAcquire();
    return false; // no effects or resource consumption before unanimous confirmation
}

void TickBbscPartyItem() {
    using Mailbox = BbscMod::PartyAcquireMailbox;
    if (bbsc_party_item_replaying) return;
    std::unique_lock lock{bbsc_party_item_mutex, std::try_to_lock};
    if (!lock) return;
    auto& item = bbsc_pending_party_item;
    if (!item.ticket) return;
    const auto result = BbscMod::PartyAcquireResult(item.ticket);
    if (!BbscPartyItemContext(item) ||
        std::chrono::steady_clock::now() - item.started > std::chrono::seconds(12) ||
        result == Mailbox::Denied || result == Mailbox::Stale) {
        BbscMod::PartyCancel();
        item = {};
        return;
    }
    if (result != Mailbox::Granted) return;
    // The durable host reservation already withdrew our published sign and
    // blocks other hosts. Stop the native Small Bell before applying Beckoning;
    // an old responder observation must not undo the newly granted role.
    if (BbscLocalEffectNode(9005) != 0) {
        if (!BbscEraseLocalEffect(9005)) return;
        BBSC_TIMELINE("JOIN", "Small Resonant Bell stopped before switching to Beckoning host search");
    }
    // The verified NativeApply entry is also used by seamless responder resume.
    // Keep the permission only on this call stack so its nested GoodsExecutor
    // hook cannot issue a second request or consume the action a second time.
    using Apply = bool PS4_SYSV_ABI (*)(u64, s32, s32);
    bbsc_party_item_replaying = true;
    const bool applied = reinterpret_cast<Apply>(image_base + UseItemNativeApplyOffset)(
        item.player, 200, item.argument);
    bbsc_party_item_replaying = false;
    BbscMod::PartyFinishAcquire(item.ticket);
    item = {};
    if (applied) BbscMod::PartyBellRang();
    else BbscMod::PartyCancel();
}
#endif
