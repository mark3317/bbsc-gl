// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <cstdint>

namespace Core::Bloodborne::World {
struct LocalMapFlagByte {
    unsigned offset = 0;
    std::uint8_t mask = 0;
};

// Local region conditions, personal receipts and object SFX initialization
// from original 1.09 EMEVDs. Both bit values belong to the local process.
constexpr LocalMapFlagByte LocalMapFlags(std::uint32_t key) {
    switch (key) {
    case 9: return {301 / 8, 0x05}; // 9301 and 9303, Amelia and Rom Insight
    case 12300: return {751 / 8, 0x01}; // 12300750, local player in either region
    case 12401: return {803 / 8, 0x10}; // Amelia's native movie
    case 12604: // Mensis bell maiden regions
    case 13404: // Hunter's Nightmare
    case 13504: // Research Hall
    case 13604: // Fishing Hamlet
        return {741 / 8, 0x05}; // 741 and 743, native enter/leave events
    case 12805: return {920 / 8, 0xF0}; // Yahar'gul object SFX, four slots
    case 13200: return {101 / 8, 0x04}; // Byrgenwerth local region
    case 13201: return {803 / 8, 0x10}; // Rom's native movie
    default: return {};
    }
}

constexpr bool IsLocalMapFlag(std::uint32_t flag) {
    const auto local = LocalMapFlags(flag / 1000);
    return local.offset == flag % 1000 / 8 && (local.mask & (0x80u >> (flag % 8)));
}
} // namespace Core::Bloodborne::World
