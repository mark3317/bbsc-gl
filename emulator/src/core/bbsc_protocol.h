// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace Core::Bloodborne::Protocol {
// KeyItems (0x29) and KeyItemsRequest (0x2E) are retired; IDs stay reserved.
inline constexpr std::uint8_t Follow = 0x20, Matching = 0x21, WorldFlags = 0x22,
    Life = 0x23, Scale = 0x24, Pvp = 0x25, Progress = 0x26, HostBoss = 0x27,
    Cutscene = 0x28, KeyItems = 0x29, SessionLeave = 0x2A,
    Register = 0x2B, RegisterKill = 0x2C, ChaliceMount = 0x2D, KeyItemsRequest = 0x2E,
    Placement = 0x30, AimedPlacement = 0x31, WorldPresence = 0x32, WorldControl = 0x33, Envelope = 0x40,
    PeerLeft = 0x7E, Peers = 0x7F;
inline constexpr std::size_t LifeLegacySize = 14, LifeVisibleSize = 15,
    LifeVisitSize = LifeVisibleSize + 2 * sizeof(std::uint64_t);
inline constexpr std::array Types{Follow, Matching, WorldFlags, Life, Scale, Pvp,
    Progress, HostBoss, Cutscene, KeyItems, SessionLeave, Register, RegisterKill,
    ChaliceMount, KeyItemsRequest, Placement, AimedPlacement, WorldPresence, WorldControl, Envelope, PeerLeft, Peers};
static_assert([] {
    for (unsigned i = 0; i < Types.size(); ++i)
        for (unsigned j = i + 1; j < Types.size(); ++j)
            if (Types[i] == Types[j]) return false;
    return true;
}(), "BBSC packet IDs must be unique across all dispatchers");
}
