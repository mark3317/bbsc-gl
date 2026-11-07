// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>

namespace Core::Bloodborne::GuestAccess {
// Deny lists govern LOCAL interaction gates only. They never change native
// session state, network authority, remote actors or inventory requirements.
constexpr bool AltarTalk(std::uint32_t talk) {
    return talk >= 210050 && talk <= 210110 && (talk - 210050) % 10 == 0;
}
constexpr bool TalkAllowed(std::uint32_t talk, bool ending, bool occupied_altar) {
    if (talk == 210306 || (talk == 210305 && ending)) return false; // final encounter/ending choice
    // Existing host cup may be visited. Creating/replacing a host cup stays
    // behind the native host gate; the native remove action is fenced separately.
    return !AltarTalk(talk) || occupied_altar;
}
constexpr bool EventAllowed(std::int64_t event) {
    if (event <= 0) return false; // unresolved identity cannot bypass the deny list
    switch (event) {
    case 3503: // native cycle progression
    case 12100000: case 12100002: case 12100180: // ending/credits initiators
    case 12104800: case 12104850: // final encounter host activation
    case 13204820: // Rom host jump; guests use the native local 13204821
        return false;
    default:
        return true;
    }
}
} // namespace Core::Bloodborne::GuestAccess
