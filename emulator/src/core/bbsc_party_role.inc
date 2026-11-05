// SPDX-License-Identifier: GPL-2.0-or-later
#ifdef BBSC_MOD
// Discovery runs in Party's worker. Native item/effect operations stay here on
// the game thread, with the same load, life and room fences as manual bell use.
void TickBbscPartyRole() {
    static u32 generation = ~u32{0};
    static bool check_load = true, yielding = false;
    static bool visited_host = false, clear_return_search = false;
    static s64 ready_since = 0, retry_at = 0;
    const u32 current = bbsc_load_generation.load();
    const s32 state = GetSessionState();
    if (state == 6) {
        visited_host = true;
        clear_return_search = true;
        check_load = false;
    }
    if (generation != current) {
        // Returning home, guest respawn and later personal travel must never
        // restart an already consumed Small Bell search. A deliberate collision
        // yield below can still arm its own responder action.
        generation = current; check_load = !visited_host; ready_since = 0; retry_at = 0;
    }
    const unsigned hint = BbscMod::PartyHostHint();
    if (hint != 2) yielding = false;
    const u64 global = GetGlobalState(), player = GetLocalPlayerCharacter();
    const s64 now = SteadyNowMs();
    if (BbscQuitInProgress() || BbscReturningToTitle() || !player ||
        !ReadablePointer(global, 0x1598) || ReadValue<u8>(global, 8) != 0 ||
        (state != 6 && ReadValue<u8>(global, 0x1592) == 0) || BbscCurtainActive() ||
        bbsc_world_load_pending.load() || bbsc_reload_finish_pending.load() ||
        GetCharacterHp(player) <= 0) {
        ready_since = 0;
        return;
    }
    if (state == 6) {
        // Admission has completed, so this search is consumed. Do not call
        // PartyCancel/Blank or Stop: membership and seamless follow stay intact.
        if (BbscLocalEffectNode(9005) && BbscEraseLocalEffect(9005))
            BBSC_TIMELINE("JOIN", "Small Resonant Bell search consumed after successful guest join");
        return;
    }
    if (state != 0 || GetBbscSessionMemberCount(global) != 1 || BbscInAnotherWorld()) {
        ready_since = 0;
        return;
    }
    if (clear_return_search) {
        if (BbscLocalEffectNode(9005) && !BbscEraseLocalEffect(9005)) return;
        clear_return_search = false;
        check_load = false;
        BBSC_TIMELINE("JOIN", "returned from host: responder search stays off until a new bell action");
    }
    if (hint == 2) {
        if (yielding) return;
        if (BbscLocalEffectNode(9000) && !BbscEraseLocalEffect(9000)) return;
        BbscMod::PartyCancel();
        yielding = true; check_load = true; ready_since = now; retry_at = now + 500;
        BBSC_TIMELINE("JOIN", "simultaneous empty host search: yielding to the selected network host");
        return;
    }
    if (!check_load || now < retry_at) return;
    if (!ready_since) ready_since = now;
    if (BbscLocalEffectNode(9000) || BbscLocalEffectNode(9005) ||
        BbscLocalEffectNode(9025) || BbscLocalEffectNode(7511)) {
        check_load = false;
        return;
    }
    // Allow discovery to finish after loading; never wait or call HTTP here.
    if (hint != 1) {
        if (now-ready_since >= 3'000) check_load = false;
        return;
    }
    if (bbsc_pending_party_item.ticket || BbscSmallBellSessionBlocked()) return;
    const u64 carried = BbscCarriedInventory();
    if (!carried || !BbscInventoryHas(carried, 0x40000000u | SmallResonantBellGoodsId)) return;
    using Apply = bool PS4_SYSV_ABI (*)(u64, s32, s32);
    const bool applied = reinterpret_cast<Apply>(image_base + UseItemNativeApplyOffset)(
        player, SmallResonantBellGoodsId, BellUseArgument);
    retry_at = now + 1'000;
    if (applied) {
        check_load = false;
        BBSC_TIMELINE("JOIN", "world-load host check: existing network host found; native responder bell started");
    }
}
#endif
