// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <span>

namespace Core::Bloodborne::BossRetry {

struct Arena {
    std::uint32_t map, defeated, first, last;
    std::array<std::int32_t, 3> names;
    std::uint32_t extra = 0;
};

// CUSA03173 1.09 boss gauges, victory guards and bounds of the attempt flags.
inline constexpr Arena StoryArenas[] = {
    {0x15000000, 12101800, 12104800, 12104802, {804000}},                  // Gehrman
    {0x15000000, 12101850, 12104850, 12104852, {540000}},                  // Moon Presence
    {0x16000000, 12201800, 12204800, 12204881, {210000}},                  // Witches
    {0x17000000, 12301700, 12304700, 12304702, {508000}},                  // Paarl
    {0x17000000, 12301800, 12304800, 12304808, {209000, 209010}},          // Blood-starved Beast
    {0x18000000, 12401800, 12404223, 12404802, {502000}},                  // Amelia
    {0x18010000, 12411700, 12414700, 12414702, {500000}, 12415400},        // Cleric Beast
    {0x18010000, 12411800, 12414800, 12414807, {271000, 272000}},          // Gascoigne
    {0x18020000, 12421700, 12424700, 12424790, {257000, 257010}},          // Ebrietas
    {0x18020000, 12421800, 12424800, 12424802, {251000, 251010}},          // Celestial Emissary
    {0x19000000, 12501800, 12504800, 12504802, {232000}},                  // Logarius
    {0x1A000000, 12601800, 12604800, 12604815, {551000, 551010}},          // Wet Nurse
    {0x1A000000, 12601850, 12604850, 12604986, {899000}},                  // Micolash
    {0x1B000000, 12701800, 12704800, 12704802, {212010, 212020, 212030}},  // Shadows
    {0x1C000000, 12801800, 12804800, 12804808, {507000}},                  // One Reborn
    {0x20000000, 13201800, 13204800, 13204812, {510000, 510010}},          // Rom
    {0x21000000, 13301800, 13304800, 13304808, {512000, 512010}},          // Amygdala
    {0x22000000, 9471,     13404802, 13404825, {451000, 451005}},          // Ludwig
    {0x22000000, 13401850, 13404852, 13404859, {450000}},                  // Laurence
    {0x23000000, 13501800, 13504802, 13504809, {452000}},                  // Maria
    {0x23000000, 13501850, 13504852, 13504878, {403000}},                  // Living Failures
    {0x24000000, 13601800, 13604802, 13604820, {453000, 454000}},          // Orphan
};

struct ChaliceInit {
    std::uint32_t event, words, victory_arg;
    std::array<std::uint32_t, 3> attempt_args; // one-based positions, zero if unused
    bool slot_completion;
    std::uint32_t name_arg = 0; // one-based position for alternate arena selection
};

// Only native boss attempt arguments. Fog unlocks, first encounter and reward
// arguments in the same constructors can be permanent and are kept.
inline constexpr ChaliceInit ChaliceInits[] = {
    {12904029, 6, 5, {3, 4, 5}, false},
    {12904030, 7, 6, {4, 5, 6}, false},
    {12904039, 8, 7, {3, 4}, false},
    {12904040, 6, 5, {2, 3}, false},
    {12904776, 8, 5, {5}, true, 4},
    {12904863, 7, 5, {5}, true, 7},
    {12904877, 8, 5, {5}, true},
    {12904881, 7, 5, {5}, true, 4},
    {12904890, 8, 5, {5}, true, 4},
    {12904891, 8, 5, {5}, true, 4},
    {12906789, 8, 5, {8}, false},         // side arena host fog
    {12906790, 6, 2, {5, 6}, true},      // side arena guest fog
    {12906791, 5, 2, {4, 5}, true, 2},   // side arena setup
    {12906795, 7, 2, {4, 5}, true, 2},   // Watchers setup
    {12906796, 8, 5, {8}, false},         // two-sided host fog
    {12906800, 6, 3, {6}, false},         // single-sided host fog
    {12906802, 6, 2, {5, 6}, true},      // guest fog
    {12906806, 5, 2, {4, 5}, true, 2},   // single boss setup
    {12906810, 7, 4, {6, 7}, true},      // boss music
    {12906825, 8, 7, {7}, true, 5},      // optional second gauge in a layer encounter
    {12906978, 7, 4, {1, 7}, true},      // alternate boss music
};

constexpr std::uint32_t FirstLayerVictory = 12901800;
constexpr std::uint32_t LayerCount = 4;
constexpr std::array<std::uint32_t, 10> ChaliceVictories{
    12901800, 12901801, 12901802, 12901803, 12901804, 12901805, 12901806,
    12900580, 12900680, 12900780,
};

constexpr bool ChaliceAttemptArgument(std::uint32_t flag) {
    return flag >= 12905500 && flag < 12906000;
}

struct ChaliceAttempt {
    std::uint32_t victory = 0;
    std::uint32_t name = 0;
    std::array<std::uint32_t, 4> flags{};
};

constexpr ChaliceAttempt ReadChaliceInit(std::span<const std::uint32_t> words) {
    if (words.size() < 2) return {};
    const auto init = std::ranges::lower_bound(ChaliceInits, words[1], {}, &ChaliceInit::event);
    if (init == std::ranges::end(ChaliceInits) || words[1] != init->event ||
        words.size() != init->words + 2 || (init->slot_completion && words[0] > 7)) return {};
    const auto args = words.subspan(2);
    const auto victory = args[init->victory_arg];
    if (std::ranges::find(ChaliceVictories, victory) == ChaliceVictories.end()) return {};
    const auto name = init->name_arg ? args[init->name_arg - 1] : 0;
    ChaliceAttempt attempt{victory, init->event == 12904877 ? 304001u : name};
    std::size_t count = 0;
    for (const auto position : init->attempt_args) {
        if (position && ChaliceAttemptArgument(args[position - 1])) {
            attempt.flags[count++] = args[position - 1];
        }
    }
    if (init->slot_completion) attempt.flags[count] = init->event + words[0];
    return attempt;
}

} // namespace Core::Bloodborne::BossRetry
