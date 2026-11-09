// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <cstdint>
#include <utility>

namespace Core::Bloodborne::GuestAccess {
// CUSA03173 1.09 host fog events and the first native enable instruction.
// Their separate guest events own guest entry after the host starts the fight.
inline constexpr std::pair<std::int64_t, std::int32_t> BossFogRetrySteps[] = {
    {12104810, 5}, {12104880, 5}, {12204890, 10}, {12304730, 10}, {12304810, 8},
    {12404840, 8}, {12414730, 8}, {12414810, 8}, {12424710, 10}, {12424810, 8},
    {12504810, 8}, {12604845, 8}, {12604860, 10}, {12704840, 8}, {12804880, 10},
    {12906789, 10}, {12906796, 10}, {12906800, 8}, {13204830, 9}, {13304870, 14},
    {13404800, 8}, {13404850, 9}, {13504800, 8}, {13504850, 8}, {13604800, 8},
};

constexpr std::int32_t BossFogRetryEnableStep(std::int64_t event) {
    if (event < BossFogRetrySteps[0].first) return 0;
    const auto gate = std::ranges::lower_bound(BossFogRetrySteps, event, {},
                                               &std::pair<std::int64_t, std::int32_t>::first);
    return gate != std::ranges::end(BossFogRetrySteps) && gate->first == event ? gate->second : 0;
}

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
    // Keep host traversal restricted. The fog geometry's first-encounter
    // skip is handled separately at the exact native branch.
    if (BossFogRetryEnableStep(event)) return false;
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
