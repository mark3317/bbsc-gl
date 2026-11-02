// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <array>
#include <cstdint>
namespace Core::Bbsc::DreamFinale {
constexpr std::uint32_t Map = 0x15000000;
// Native m21 EMEVD: victory, intro completion, encounter/AI and death transition.
// Phantom fog-entry flags 12104801/51 deliberately stay local.
constexpr std::array<std::uint32_t, 10> BattleFlags{
    12101800, 12101802, 12101850, 12101852,
    12104800, 12104802, 12104809, 12104850, 12104852, 12104859,
};
constexpr bool IsEnding(std::uint32_t map, std::int32_t scene) {
    return map == Map && (scene == 21000010 || scene == 21001010 ||
                         scene == 21000020 || scene == 21000030 || scene == 21001030);
}
constexpr std::uint32_t EndingNumber(std::int32_t scene) {
    if (scene == 21000010 || scene == 21001010) return 1;
    if (scene == 21000020) return 2;
    if (scene == 21000030 || scene == 21001030) return 3;
    return 0;
}
struct Playback {
    std::int32_t scene = 0;
    bool started = false;
    void Begin(std::int32_t id) { scene = id; started = false; }
    bool Observe(bool playing) {
        if (!scene) return false;
        if (playing) started = true;
        return started && !playing;
    }
};
} // namespace Core::Bbsc::DreamFinale
