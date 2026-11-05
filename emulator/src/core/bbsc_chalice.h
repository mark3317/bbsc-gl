// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <span>
#include "core/bbsc_protocol.h"

namespace Core::Bloodborne::Chalice {
// A map identifies a floor template, never a generated dungeon. No native pointers on wire.
struct Key {
    std::uint64_t channel = 0;
    std::uint64_t form_hash = 0;
    std::uint32_t form_size = 0;
    std::uint32_t form_version = 0;
    bool operator==(const Key&) const = default;
};
static_assert(sizeof(Key) == 24);
constexpr bool IsMap(std::uint32_t map) { return (map >> 24) == 29; }
constexpr bool IsLootGroup(std::uint32_t key) {
    return key / 10000 == 5 && (key % 10000) / 100 == 29;
}
constexpr bool Valid(const Key& key) {
    return key.channel != 0 && key.channel < (std::uint64_t{1} << 63) &&
           key.form_hash != 0 && key.form_size >= 16 && key.form_size <= 1024 &&
           key.form_version == 0;
}
inline std::uint64_t HashForm(std::span<const std::uint8_t> bytes) {
    std::uint64_t hash = 14695981039346656037ULL;
    for (auto byte : bytes) { hash ^= byte; hash *= 1099511628211ULL; }
    return hash;
}
// Expired, unscoped and another dungeon's state must never unblock a dungeon load.
constexpr bool CanUse(const Key& local, const Key& host, std::int64_t age_ms) {
    return Valid(local) && Valid(host) && local == host && age_ms >= 0 && age_ms < 6000;
}
// Decoded, pointer-free stage-loader input. It is borrowed by guests, never installed
// into their altar flags or cached ritual objects. Revision changes on each native load.
struct Mount {
    Key key{};
    std::uint64_t revision = 0;
    std::uint32_t map = 0;
    std::uint32_t layout_map = 0;
    std::array<std::int32_t, 18> parts{};
    std::int32_t dungeon_type = -1;
    std::uint32_t feature = 0;
    std::uint32_t stage_map = 0; // native virtual root; map may identify a resident part
    std::uint32_t reserved = 0;
    bool operator==(const Mount&) const = default;
};
static_assert(sizeof(Mount) == 128);
inline constexpr std::uint8_t MountPacketType = Protocol::ChaliceMount;
inline constexpr std::size_t MountPacketSize = 8 + sizeof(Mount);
inline bool ValidMount(const Mount& mount) {
    if (!Valid(mount.key) || mount.revision == 0 || !IsMap(mount.map) ||
        !IsMap(mount.layout_map) || !IsMap(mount.stage_map) || mount.reserved != 0 || mount.feature > 3 || mount.dungeon_type < -1) return false;
    bool any = false;
    for (auto part : mount.parts) {
        if (part < -1) return false;
        any |= part != -1;
    }
    return any;
}
// The nine conditional travel entries in t210060..t210120 (the Hall is unconditional).
inline constexpr std::array<std::uint32_t, 9> LampUnlockFlags{
    12907830, 12907850, 12907870, 12907890, 12907910, 12907930, 12907950, 12907970, 12907990};

constexpr bool TouchesLampUnlock(std::uint32_t first, std::uint32_t width = 1) {
    if (first > LampUnlockFlags.back() || std::uint64_t{first} + width <= LampUnlockFlags.front())
        return false;
    for (const auto flag : LampUnlockFlags) {
        if (flag >= first && flag - first < width) return true;
    }
    return false;
}

inline void CopyHostFlagGroup(std::uint32_t key, std::uint8_t* live,
                              const std::array<std::uint8_t, 125>& host) {
    if (key != LampUnlockFlags.front() / 1000) {
        std::memcpy(live, host.data(), host.size());
        return;
    }
    auto merged = host;
    for (const auto flag : LampUnlockFlags) {
        const auto byte = (flag % 1000) / 8;
        const auto mask = 0x80u >> (flag % 8);
        merged[byte] = (host[byte] & ~mask) | (live[byte] & mask);
    }
    std::memcpy(live, merged.data(), merged.size());
}

constexpr bool TouchesAltar(std::uint32_t first, std::uint32_t width = 1) {
    if (width == 0) return false;
    const std::uint64_t end = std::uint64_t{first} + width;
    return (first < 9027 && end > 9020) || (first < 94'700'000 && end > 94'000'000);
}
} // namespace Core::Bloodborne::Chalice
