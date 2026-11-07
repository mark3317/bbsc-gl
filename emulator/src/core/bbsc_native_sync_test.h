// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <string_view>

namespace Core::Bloodborne::SessionTest {
// The normal path keeps v1.2 native NPC synchronization. The former independent
// NPC pipeline is an explicit process-local diagnostic opt-in (value 0).
// Never persisted in the player's settings/save.
inline bool NativeNpcSync() {
    static const bool enabled=[] {
        const char* value=std::getenv("BBSC_NATIVE_NPC_SYNC_TEST");
        return !value || std::string_view(value)!="0";
    }();
    return enabled;
}
inline constexpr std::uint32_t Capability=16;
// v1.2.0 local workers plus reviewed personal progress driven by local NPC
// conditions. The other NPC dispatchers still use native event replication.
inline constexpr std::array<std::int64_t,67> NativeLocalEvents{
    9722,9723,9781,12300700,12300701,12300702,12300704,
    12400501,12400521,12400531,12400561,12400563,12400564,12400565,
    12400611,12400622,12400624,12400630,12400650,12400651,12400652,
    12400800,12400903,12400904,12400954,12410653,12410654,12410655,12410659,12410676,12410701,
    12410702,12410703,12410713,12410734,12410736,12410738,12410744,12410745,12410748,
    12410761,12410762,12410763,12410785,12410786,12410801,12410803,12410804,12410809,12410810,12410811,
    12410812,12410813,12410814,12410831,12600029,12700701,12700720,12701000,12701001,12701002,12800901,
    12800906,13500998,13600942,13600944,13600955
};
inline bool LocalQuest(std::int64_t event) {
    return std::binary_search(NativeLocalEvents.begin(),NativeLocalEvents.end(),event);
}
}
