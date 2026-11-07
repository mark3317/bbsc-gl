// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "bbsc_lamp_travel_data.h"
#include "bbsc_native_sync_test.h"

namespace Core::Bloodborne::EventSteps {
enum : std::uint32_t {
    Travel=1, RomTransition=2, Kidnap=4, RomJump=8, Door=16,
    Finale=32, Personal=64, Kit=128, DreamPhase=256
};
// Immutable descriptor classification only. Role, PC, flags and readiness are
// deliberately evaluated by the original guards at every relevant step.
constexpr std::uint32_t Classify(std::int64_t event, bool personal) {
    return ((LampTravel::IsNativeTravelEvent(event) || LampTravel::IsLampActivationEvent(event)) ? Travel : 0u) |
           ((event==13201803 || event==12401803) ? RomTransition : 0u) |
           ((event==9421 || event==9422 || event==12400780 || event==12700500) ? Kidnap : 0u) |
           ((event==13204820 || event==13204821 || event==13204832 || event==13204833) ? RomJump : 0u) |
           ((event==13200310 || event==13200311) ? Door : 0u) |
           ((event==12100000 || event==12100002 || event==12100180) ? Finale : 0u) |
           (personal ? Personal : 0u) | (event==12101024 ? Kit : 0u) |
           ((event==12100100 || (event>=12100143 && event<=12100145) ||
             event==12100160) ? DreamPhase : 0u);
}
}
