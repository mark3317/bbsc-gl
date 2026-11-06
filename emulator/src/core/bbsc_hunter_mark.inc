// SPDX-License-Identifier: GPL-2.0-or-later
// Original goods 1400 uses SpEffect 2101. The native effect walk calls
// 01335D60 for its +15F bit20, after item confirmation/animation/consumption.
// Intercept before that function starts the native return/load sequence.
u64 BbscLocalEffectNode(s32 id);
bool BbscEraseLocalEffect(s32 id);
std::atomic<bool> bbsc_hunter_mark_ready{false};
u8 bbsc_hunter_mark_skip = 0;

void PrepareBbscHunterMark(u64 goods) {
    if (!bbsc_hunter_mark_ready.load(std::memory_order_acquire)) return;
    const u64 row = BbscParamRow(goods, 1400, 0x6C);
    if (!ReadablePointer(row, 0x6C) || ReadValue<s32>(row, 0) != 2101 ||
        !HasMemoryAccess(row + 0x44, 1, MemoryProt::CpuWrite)) return;
    // Only white phantom and multiplayer permission; all other native use
    // restrictions, dialog, animation, isConsume and refId remain unchanged.
    WriteValue<u8>(row, 0x44, ReadValue<u8>(row, 0x44) | 0x14);
}

void PS4_SYSV_ABI BbscHunterMarkHook(u64, const GuestRegisterSnapshot* registers) {
    bbsc_hunter_mark_skip = 0;
    const s32 state = GetSessionState();
    const u64 player = GetLocalPlayerCharacter();
    if (!registers || !BbscSpectateEnabled() || (state != 3 && state != 6) ||
        BbscQuitInProgress() || BbscReturningToTitle() ||
        !player || GetCharacterHp(player) <= 0 ||
        BbscLocalEffectNode(2101) == 0 || BbscLocalEffectNode(2100) != 0) return;
    // Reuse precisely the open-world death destination/revive/restock path,
    // without the death penalty, spectate timer or death curtain.
    if (!BbscRespawnInPlace("bold hunter mark")) return;
    // This was a living return, not a death. A real death immediately after
    // using a mark must not be mistaken for the native repeat-death loop.
    bbsc_inplace_respawn_ms = 0;
    // Death cleanup can already have erased it. Otherwise retire the native
    // persistent mark effect so the next native effect walk cannot load again.
    if (BbscLocalEffectNode(2101) != 0) BbscEraseLocalEffect(2101);
    const_cast<GuestRegisterSnapshot*>(registers)->rax = 1; // original success result
    bbsc_hunter_mark_skip = 1;
    BBSC_TIMELINE("RESPAWN", "bold hunter mark: native item used; returned without load/curtain");
}

void InstallBbscHunterMarkHook() {
    static constexpr std::array<u8, 6> prologue{0x55,0x48,0x89,0xE5,0x41,0x56};
    const bool ready = InstallGuestCodeHook(reinterpret_cast<void*>(image_base + 0x01335D60),
        prologue, 0, BbscHunterMarkHook, &bbsc_hunter_mark_skip);
    bbsc_hunter_mark_ready.store(ready, std::memory_order_release);
    LOG_INFO(Debug, "BBSC bold hunter mark: native return hook {}", ready);
}
