// SPDX-License-Identifier: GPL-2.0-or-later
// The original Kickout list has two rows. A row carries an opaque selection
// token in place of a PlayerIns handle, which may disappear on independent travel.
// Confirmation must keep the native pending goods bound to its action. The
// update at 018F74DF refreshes item metadata BEFORE 018F759F refreshes +1C0.
// If +1C0 still names a quick-slot consumable, the forced use can start that
// consumable's animation. Bind only an already pending Blank; native flags,
// state transitions, goodsUseAnim=15, effects and replication remain unchanged.
void BindBbscConfirmedBlank() {
    const u64 world = ReadValue<u64>(image_base + CandidateLocalStatePointerOffset, 0);
    if (!ReadablePointer(world, 0x68)) return;
    const u64 player = ReadValue<u64>(world, 0x60);
    if (!ReadablePointer(player, 0x494) || ReadValue<s32>(player, 0x47C) != 111 ||
        ReadValue<s32>(player, 0x490) != 2) return;
    WriteValue<s32>(player, 0x1C0, 111);
    WriteValue<s32>(player, 0x478, 111);
}

void PS4_SYSV_ABI BbscBlankConfirmHook(u64, const GuestRegisterSnapshot* registers) {
    if (registers) BindBbscConfirmedBlank();
}

struct BbscBlankTarget {
    u64 member_id = 0;
    u64 member = 0;
    s32 token = -1;
    s32 slot = -1;
    std::array<char16_t, 17> name{};
};

constexpr u32 BbscBlankTokenMask = 0xC0003FFF;
constexpr u32 BbscBlankTokenBits = 0x40003FFF;
std::array<BbscBlankTarget, 2> bbsc_blank_rows;
// Keep the two native MemberId objects alive while their rows can be confirmed.
// Their addresses cannot be recycled for another admission in that interval.
std::array<std::array<u64, 4>, 2> bbsc_blank_member_refs;
u64 bbsc_blank_room = 0;
u32 bbsc_blank_serial = 0;
bool bbsc_blank_roster_ready = false;
u8 bbsc_blank_list_skip = 0, bbsc_blank_name_skip = 0, bbsc_blank_select_skip = 0;
u8 bbsc_blank_dispatch_skip = 0;

u64 ReadBbscWorldRoom();
BbscMod::RegisterIdentity BbscWorldIdentity(u64 member_id);

bool BbscBlankToken(u32 value) {
    // A native handle decodes its low 14 bits as a character slot. This slot
    // cannot resolve in a native character block even on an unpatched path.
    return (value & BbscBlankTokenMask) == BbscBlankTokenBits;
}

u64 BbscBlankHostRoom() {
    if (!bbsc_blank_roster_ready || GetSessionState() != 3 || !BbscIndependentActive() ||
        BbscQuitInProgress() || BbscReturningToTitle()) return 0;
    return ReadBbscWorldRoom();
}

std::array<BbscBlankTarget, 4> BbscBlankGuests() {
    std::array<BbscBlankTarget, 4> guests{};
    const u64 manager = ReadValue<u64>(image_base + MatchingStatePointerOffset, 0);
    if (!ReadablePointer(manager, 0x108)) return guests;
    const u64 first = ReadValue<u64>(manager, 0xF8), end = ReadValue<u64>(manager, 0x100);
    if (end <= first || end - first > 5 * 0x20 || (end - first) % 0x20 ||
        !ReadablePointer(first, end - first)) return guests;
    for (u64 member_id = first; member_id < end; member_id += 0x20) {
        const auto slot = GetMemberSlotInfoByMember(member_id);
        if (slot.index < 0 || slot.index >= static_cast<s32>(guests.size()) ||
            slot.type != 1) continue;
        const auto identity = BbscWorldIdentity(member_id);
        if (!identity.name[0]) continue;
        auto& guest = guests[slot.index];
        guest.member_id = member_id;
        guest.member = ReadValue<u64>(member_id, 0);
        guest.slot = slot.index;
        for (size_t i = 0; i < 16 && identity.name[i]; ++i)
            guest.name[i] = static_cast<unsigned char>(identity.name[i]);
    }
    return guests;
}

void RefreshBbscBlankRows(u64 room) {
    const auto previous = room == bbsc_blank_room ? bbsc_blank_rows : decltype(bbsc_blank_rows){};
    const auto guests = BbscBlankGuests();
    using Lifetime = void PS4_SYSV_ABI (*)(u64);
    using Assign = void PS4_SYSV_ABI (*)(u64, u64);
    const auto destroy = reinterpret_cast<Lifetime>(image_base + 0x00CA1570);
    const auto construct = reinterpret_cast<Lifetime>(image_base + 0x00CA1440);
    const auto assign = reinterpret_cast<Assign>(image_base + 0x00CA1BA0);
    for (size_t i = 0; i < bbsc_blank_rows.size(); ++i)
        if (bbsc_blank_rows[i].member) destroy(reinterpret_cast<u64>(bbsc_blank_member_refs[i].data()));
    bbsc_blank_rows = {};
    bbsc_blank_room = room;
    size_t row = 0;
    for (auto guest : guests) {
        if (!guest.member) continue;
        const auto existing = std::ranges::find_if(previous, [&](const auto& entry) {
            return entry.member == guest.member && entry.name == guest.name;
        });
        if (existing != previous.end()) guest.token = existing->token;
        else if (bbsc_blank_serial < 0xFFFF)
            guest.token = static_cast<s32>(BbscBlankTokenBits | (++bbsc_blank_serial << 14));
        else break;
        const u64 reference = reinterpret_cast<u64>(bbsc_blank_member_refs[row].data());
        construct(reference);
        assign(reference, guest.member_id);
        bbsc_blank_rows[row++] = guest;
        if (row == bbsc_blank_rows.size()) break;
    }
}

u64 ResolveBbscBlankTarget(s32 token) {
    if (!bbsc_blank_room || BbscBlankHostRoom() != bbsc_blank_room) return 0;
    const auto row = std::ranges::find(bbsc_blank_rows, token, &BbscBlankTarget::token);
    if (row == bbsc_blank_rows.end() || !row->member) return 0;
    const auto current = BbscBlankGuests();
    const auto& guest = current[row->slot];
    return guest.member == row->member && guest.name == row->name ? guest.member_id : 0;
}

void PS4_SYSV_ABI BbscBlankListHook(u64, const GuestRegisterSnapshot* registers) {
    if (!registers || !ReadablePointer(registers->rsp, 8) ||
        ReadValue<u64>(registers->rsp, 0) != image_base + 0x01BC1ED0 ||
        !HasMemoryAccess(registers->rdi, 8, MemoryProt::CpuWrite)) return;
    const u64 room = BbscBlankHostRoom();
    if (!room) return;
    if (registers->r15 == 0) RefreshBbscBlankRows(room);
    if (bbsc_blank_room != room || !bbsc_blank_rows.front().member) return;
    WriteValue<s32>(registers->rdi, 0, bbsc_blank_rows[0].token);
    WriteValue<s32>(registers->rdi, 4, bbsc_blank_rows[1].token);
    const_cast<GuestRegisterSnapshot*>(registers)->rax = 1;
    bbsc_blank_list_skip = 1;
}

void PS4_SYSV_ABI BbscBlankNameHook(u64, const GuestRegisterSnapshot* registers) {
    if (!registers || !bbsc_blank_room || BbscBlankHostRoom() != bbsc_blank_room ||
        registers->rsi >= bbsc_blank_rows.size() || !bbsc_blank_rows.front().member) return;
    // Same string constructor and assignment as 016E7150, using the NpId
    // carried by the selected native room member.
    using Construct = void PS4_SYSV_ABI (*)(u64, u64);
    using Assign = void PS4_SYSV_ABI (*)(u64, const char16_t*, size_t);
    reinterpret_cast<Construct>(image_base + 0x027C0E00)(registers->rdi, image_base + 0x049D85F0);
    WriteValue<u8>(registers->rdi, 0x30, 1);
    const auto& name = bbsc_blank_rows[registers->rsi].name;
    reinterpret_cast<Assign>(image_base + 0x0262A720)(registers->rdi, name.data(),
                                                     std::char_traits<char16_t>::length(name.data()));
    const_cast<GuestRegisterSnapshot*>(registers)->rax = registers->rdi;
    bbsc_blank_name_skip = 1;
}

void PS4_SYSV_ABI BbscBlankSelectHook(u64, const GuestRegisterSnapshot* registers) {
    if (!registers || !ReadablePointer(registers->rdi, 12)) return;
    const s32 token = ReadValue<s32>(registers->rdi, 8);
    if (!BbscBlankToken(static_cast<u32>(token))) {
        BindBbscConfirmedBlank();
        return;
    }
    // The native Yes callback stores this token on the local actor and starts
    // the original item animation. A stale selection must never start it.
    if (!ResolveBbscBlankTarget(token)) bbsc_blank_select_skip = 1;
    else BindBbscConfirmedBlank();
}

void PS4_SYSV_ABI BbscBlankDispatchHook(u64, const GuestRegisterSnapshot* registers) {
    if (!registers || !BbscBlankToken(static_cast<u32>(registers->rsi))) return;
    // Reject expired tokens without letting native reinterpret them as actors.
    bbsc_blank_dispatch_skip = 1;
    if (static_cast<u32>(registers->rdx) != 1) return;
    if (GetSessionState() == 3) bbsc_host_selected_blank = true;
    const u64 member = ResolveBbscBlankTarget(static_cast<s32>(registers->rsi));
    if (!member) return;

    const u64 manager = ReadValue<u64>(image_base + MatchingStatePointerOffset, 0);
    const u64 world = ReadValue<u64>(image_base + CandidateLocalStatePointerOffset, 0);
    const u64 actor = FindBbscRemotePlayerByMember(world, member);
    if (actor) {
        // Preserve the actor's original event flags when a native copy exists.
        using HandleActor = void PS4_SYSV_ABI (*)(u64, u64);
        reinterpret_cast<HandleActor>(image_base + 0x0178DBE0)(registers->rdi, actor);
    } else {
        // The native wrappers eventually pass MemberId to these same calls.
        // Only the actor-local flags have no equivalent when no actor exists.
        using Ready = bool PS4_SYSV_ABI (*)(u64);
        if (!reinterpret_cast<Ready>(image_base + 0x00C8F570)(manager + 0x18)) return;
        using Kick = bool PS4_SYSV_ABI (*)(u64, u64);
        if (!reinterpret_cast<Kick>(image_base + 0x00C8EE30)(manager + 0x18, member)) return;
    }
    BbscAnnounce(BbscL(u"Disconnecting the selected player...",
                       u"Отключение выбранного игрока..."), "host kick requested");
    BBSC_TIMELINE("LEAVE", "host requested selected room member exclusion");
}

void InstallBbscBlankRoster() {
    if (!BbscMod::PartyEnabled()) return;
    // Native Yes stores: general item confirmation and the Small/Sinister
    // silence options. Beckoning's store is hooked by InstallBbscBanners.
    static constexpr std::array<u8, 10> confirmed{0xC7,0x80,0x70,0x04,0,0,1,0,0,0};
    static constexpr std::array<u8, 10> silence{0xC7,0x80,0x74,0x04,0,0,1,0,0,0};
    if (!InstallGuestCodeHook(reinterpret_cast<void*>(image_base + 0x01BC3D17),
                              confirmed, 0, BbscBlankConfirmHook) ||
        !InstallGuestCodeHook(reinterpret_cast<void*>(image_base + 0x01BC69C7),
                              silence, 0, BbscBlankConfirmHook) ||
        !InstallGuestCodeHook(reinterpret_cast<void*>(image_base + 0x01BC6AD7),
                              silence, 0, BbscBlankConfirmHook))
        LOG_ERROR(Debug, "BBSC Blank: native confirmation binding unavailable");
    static constexpr std::array<u8, 6> entry{0x55,0x48,0x89,0xE5,0x41,0x57};
    static constexpr std::array<u8, 6> select{0x55,0x48,0x89,0xE5,0x41,0x56};
    bbsc_blank_roster_ready =
        InstallGuestCodeHook(reinterpret_cast<void*>(image_base + 0x016E6FB0), entry, 0,
                             BbscBlankListHook, &bbsc_blank_list_skip) &&
        InstallGuestCodeHook(reinterpret_cast<void*>(image_base + 0x016E7150), entry, 0,
                             BbscBlankNameHook, &bbsc_blank_name_skip) &&
        InstallGuestCodeHook(reinterpret_cast<void*>(image_base + 0x01BC4F90), select, 0,
                             BbscBlankSelectHook, &bbsc_blank_select_skip) &&
        InstallGuestCodeHook(reinterpret_cast<void*>(image_base + 0x015BE2A0), entry, 0,
                             BbscBlankDispatchHook, &bbsc_blank_dispatch_skip);
    if (!bbsc_blank_roster_ready) LOG_ERROR(Debug, "BBSC Blank: native room list hooks unavailable");
}
