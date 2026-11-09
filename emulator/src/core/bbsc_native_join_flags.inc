// SPDX-License-Identifier: GPL-2.0-or-later
// Included by bloodborne_re.cpp. The native join path applies whole flag groups.
struct BbscNativeJoinFlagGroup {
    u32 slot;
    u32 key;
    std::array<u8, BbscWorldGroupBytes> shared_mask;
};

const std::vector<BbscNativeJoinFlagGroup>& BbscNativeJoinFlagGroups() {
    static const auto groups = [] {
        std::vector<BbscNativeJoinFlagGroup> result;
        using NativeSlot = u32 PS4_SYSV_ABI (*)(u32, u32, u32, u32);
        const auto native_slot = reinterpret_cast<NativeSlot>(image_base + 0x013BC710);
        const auto add = [&](u32 kind, u32 area, u32 block, u32 group) {
            const u32 key = kind * 10000 + area * 100 + block * 10 + group;
            BbscNativeJoinFlagGroup entry{0, key, {}};
            entry.shared_mask.fill(0xFF);
            MaskBbscSharedFlagGroup(key, entry.shared_mask.data());
            // Share the initial position, but keep the receiving event's own
            // movement/lever interlocks during the native FirstSync.
            if (area != 29) {
                for (const auto& lift : World::LiftFlags(key))
                    entry.shared_mask[lift.offset] &= ~lift.temporary;
            }
            if (std::ranges::all_of(entry.shared_mask, [](u8 mask) { return mask == 0xFF; })) return;
            entry.slot = native_slot(kind, area, block, group);
            if (entry.slot != ~u32{0}) result.push_back(entry);
        };
        for (const u32 group : {0u, 1u, 5u, 9u}) add(0, 0, 0, group);
        // The native INFE writer uses this table of ordinary map area/block pairs.
        constexpr u64 MapTable = 0x047314D0;
        constexpr u32 MapCount = 17;
        for (u32 i = 0; i < MapCount; ++i) {
            const u32 area = ReadValue<u32>(image_base + MapTable, i * 8);
            const u32 block = ReadValue<u32>(image_base + MapTable, i * 8 + 4);
            for (const u32 group : {0u, 1u, 4u, 5u, 6u, 7u}) add(1, area, block, group);
            for (const u32 group : {0u, 1u}) add(6, area, block, group);
        }
        return result;
    }();
    return groups;
}

constexpr size_t BbscNativeJoinSnapshotBytes = 0xA4 + 12 * BbscWorldGroupBytes;

void FilterBbscNativeJoinFlags(std::span<u8> snapshot, bool outgoing) {
    constexpr u32 HeaderBytes = 0x14;
    constexpr u32 DescriptorBytes = 12;
    constexpr u32 GroupCount = 12;
    constexpr u32 DataOffset = HeaderBytes + GroupCount * DescriptorBytes;
    static_assert(BbscNativeJoinSnapshotBytes == DataOffset + GroupCount * BbscWorldGroupBytes);
    if (snapshot.size() != BbscNativeJoinSnapshotBytes) return;
    const auto word = [snapshot](size_t offset) {
        u32 value;
        std::memcpy(&value, snapshot.data() + offset, sizeof(value));
        return value;
    };
    if (word(0) != 0x45464E49 || (word(4) & 0xFFFF) != 1 || word(8) != GroupCount ||
        word(12) != HeaderBytes || word(16) != DataOffset) return;
    for (u32 i = 0; i < GroupCount; ++i) {
        const u32 descriptor = HeaderBytes + i * DescriptorBytes;
        if (word(descriptor + 4) != i * BbscWorldGroupBytes ||
            word(descriptor + 8) != BbscWorldGroupBytes) return;
    }
    const auto& groups = BbscNativeJoinFlagGroups();
    for (u32 i = 0; i < GroupCount; ++i) {
        const u32 slot = word(HeaderBytes + i * DescriptorBytes);
        const auto group = std::ranges::find(groups, slot, &BbscNativeJoinFlagGroup::slot);
        if (group == groups.end()) continue;
        const auto storage = outgoing ? 0 : BbscFlagGroupStorage(group->key);
        if (!outgoing && (!storage || !ReadablePointer(storage, BbscWorldGroupBytes))) continue;
        const auto* own = reinterpret_cast<const u8*>(storage);
        auto* data = snapshot.data() + DataOffset + i * BbscWorldGroupBytes;
        for (size_t byte = 0; byte < BbscWorldGroupBytes; ++byte) {
            const u8 mask = group->shared_mask[byte];
            data[byte] = (data[byte] & mask) | (own ? own[byte] & ~mask : 0);
        }
    }
}

u8 bbsc_native_join_flag_serialize_skip = 0;
void PS4_SYSV_ABI BbscNativeJoinFlagSerializeHook(u64, const GuestRegisterSnapshot* registers) {
    using Serialize = u64 PS4_SYSV_ABI (*)(u64, u64);
    const auto serialize = reinterpret_cast<Serialize>(image_base + 0x013BE3C0);
    const_cast<GuestRegisterSnapshot*>(registers)->rax = serialize(registers->rdi, registers->rsi);
    // This particular caller sends the snapshot. The same serializer is also
    // used for local loads and saves, which must keep all of their own flags.
    if (ReadValue<u32>(registers->rdi, 0x20) == BbscWorldGroupBytes &&
        HasMemoryAccess(registers->rsi, BbscNativeJoinSnapshotBytes, MemoryProt::CpuReadWrite)) {
        FilterBbscNativeJoinFlags({reinterpret_cast<u8*>(registers->rsi), BbscNativeJoinSnapshotBytes}, true);
    }
    bbsc_native_join_flag_serialize_skip = 1;
}

u8 bbsc_native_join_flag_apply_skip = 0;
void PS4_SYSV_ABI BbscNativeJoinFlagApplyHook(u64, const GuestRegisterSnapshot* registers) {
    // This callsite is reached only after the game's host snapshot decompression.
    // Keep the serializer and other callers of the native apply routine intact.
    const u32 size = ReadValue<u32>(image_base, 0x0556388C);
    if (size == BbscNativeJoinSnapshotBytes &&
        HasMemoryAccess(registers->rsi, size, MemoryProt::CpuReadWrite)) {
        FilterBbscNativeJoinFlags({reinterpret_cast<u8*>(registers->rsi), size}, false);
    }
    using Apply = u64 PS4_SYSV_ABI (*)(u64, u64);
    const auto apply = reinterpret_cast<Apply>(image_base + 0x013BECA0);
    const_cast<GuestRegisterSnapshot*>(registers)->rax = apply(registers->rdi, registers->rsi);
    bbsc_native_join_flag_apply_skip = 1;
}

void InstallBbscNativeJoinFlags() {
    static constexpr std::array<u8, 5> ApplyCall{0xE8, 0xCD, 0x9A, 0xC3, 0xFF};
    if (!InstallGuestCodeHook(reinterpret_cast<void*>(image_base + 0x017851CE), ApplyCall, 0,
                              BbscNativeJoinFlagApplyHook, &bbsc_native_join_flag_apply_skip, true)) {
        LOG_ERROR(Debug, "BBSC personal flags: native join snapshot apply hook unavailable");
        return;
    }
    static constexpr std::array<u8, 5> SerializeCall{0xE8, 0x38, 0x82, 0xC3, 0xFF};
    if (!InstallGuestCodeHook(reinterpret_cast<void*>(image_base + 0x01786183), SerializeCall, 0,
                              BbscNativeJoinFlagSerializeHook, &bbsc_native_join_flag_serialize_skip, true)) {
        LOG_ERROR(Debug, "BBSC personal flags: native join snapshot send hook unavailable");
    }
}
