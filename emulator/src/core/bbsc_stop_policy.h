// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>

namespace Core::Bloodborne {
// Only the native STOP member-drain phase may take its existing timeout branch.
// Do not expire summon tasks, network requests or fabricate session completion.
constexpr bool BbscStopDrainExpired(std::uint32_t kind, std::uint64_t phase,
                                   std::int64_t elapsed_ms) {
    return kind == 0xC && phase == 0x00C9B960 && elapsed_ms >= 2000;
}
}
