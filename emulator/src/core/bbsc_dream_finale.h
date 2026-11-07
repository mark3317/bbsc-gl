// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <array>
#include <cstdint>
namespace Core::Bbsc::DreamFinale {
constexpr std::uint32_t Map = 0x15000000;
enum class Phase : std::uint8_t { None, Recall, Ready, Play, AtEnd, Release, Committed, Arrived };

struct Signal {
    Phase phase = Phase::None;
    std::uint8_t token = 0;
    std::uint8_t ending = 0;
    bool operator==(const Signal&) const = default;
};

struct Event {
    std::int64_t id;
    std::int32_t start;
    std::int32_t increment;
    std::int32_t commit;
};
// Increment is native 2003[21]. Commit is the first SetFlag(6604).
constexpr std::array<Event, 3> Events{{
    {12100180, 3, 14, 24}, {12100000, 12, 43, 44}, {12100002, 10, 35, 36},
}};
constexpr std::uint8_t EventEnding(std::int64_t event) {
    for (std::uint8_t i = 0; i < Events.size(); ++i)
        if (Events[i].id == event) return i + 1;
    return 0;
}
constexpr bool Valid(Signal signal, bool host) {
    if (signal.phase == Phase::None) return signal == Signal{};
    if (!signal.token) return false;
    switch (signal.phase) {
    case Phase::Recall: return host && signal.ending == 0;
    case Phase::Ready: return !host && signal.ending == 0;
    case Phase::Play: case Phase::Release:
        if (!host) return false;
        break;
    case Phase::AtEnd: case Phase::Committed: case Phase::Arrived: break;
    default: return false;
    }
    return signal.ending >= 1 && signal.ending <= Events.size();
}
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
