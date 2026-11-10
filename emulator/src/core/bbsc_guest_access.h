// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <cstdint>
#include <utility>

namespace Core::Bloodborne::GuestAccess {
// CUSA03173 1.09 host fog events and the first native enable instruction.
// Their separate guest events own the local action and traversal.
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

// Native guest traversal events and their current-fight predicate. Zero in
// the flag column means the dungeon instance supplies it through parameters.
struct GuestFogGate {
    std::int64_t event;
    std::uint32_t battle_flag;
    std::int32_t step = 4;
};
inline constexpr GuestFogGate GuestFogGates[] = {
    {12104811, 12104800}, {12104881, 12104850}, {12204891, 12204800},
    {12304731, 12304700}, {12304811, 12304800}, {12404841, 12404800},
    {12414731, 12414700}, {12414811, 12414800}, {12424711, 12424700, 3},
    {12424811, 12424800}, {12504811, 12504800}, {12604846, 12604800, 3},
    {12604861, 12604850}, {12704841, 12704800}, {12804881, 12804800},
    {12906790, 0}, {12906802, 0}, {13204831, 13204800}, {13304871, 13304800},
    {13404801, 13404808}, {13404851, 13404858}, {13504801, 13504808},
    {13504851, 13504858}, {13604801, 13604808},
};

constexpr const GuestFogGate* FindGuestFogGate(std::int64_t event) {
    const auto gate = std::ranges::lower_bound(GuestFogGates, event, {}, &GuestFogGate::event);
    return gate != std::ranges::end(GuestFogGates) && gate->event == event ? gate : nullptr;
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
