// SPDX-License-Identifier: GPL-2.0-or-later
// Called only at the existing native f47 result boundary. The original
// dispatcher has evaluated the five arguments into its own stack variants.
// No memory search, worker, ESD mutation, inventory grant or periodic repair.
bool BbscWorkshopTalk(u32 talk) { return talk == 210692 || talk == 210699; }

bool BbscWorkshopToolResult(u32 talk, u64 frame) {
    if (!BbscWorkshopTalk(talk) || !frame || frame < 0x220 ||
        GetCurrentPackedMap() != BbscHuntersDreamMap || !BbscGuestInHostWorld() ||
        !ReadablePointer(frame - 0x220, 0x50)) return false;
    std::array<s32, 5> args{};
    for (size_t i = 0; i < args.size(); ++i) {
        const u64 variant = frame - 0x1E0 - i * 0x10;
        if (ReadValue<u32>(variant, 8) != 2) return false; // native integer variant
        args[i] = ReadValue<s32>(variant, 0);
    }
    // Exact original f47(3, tool, 0, 1, 0); no other inventory predicate changes.
    if (args[0] != 3 || args[2] != 0 || args[3] != 1 || args[4] != 0) return false;
    const u32 item = static_cast<u32>(args[1]);
    const u32 flag = talk == 210699 && item == 4104 ? 6631 :
                     talk == 210692 && item == 4103 ? 6630 :
                     talk == 210692 && item == 4102 ? 6633 : 0;
    return flag && BbscEventFlag(flag);
}
