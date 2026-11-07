// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <cstdint>
#include <span>

namespace Core::Bloodborne::World {
struct LiftFlagByte {
    std::uint16_t offset;
    std::uint8_t position;
    std::uint8_t temporary;

    // All listed bits in an entry occupy the same byte of a 1000-flag group.
    static constexpr LiftFlagByte Position(unsigned position, unsigned temporary = 0) {
        return {static_cast<std::uint16_t>(position / 8), Bit(position),
                temporary ? Bit(temporary) : std::uint8_t{0}};
    }
    static constexpr LiftFlagByte Temporary(unsigned temporary) {
        return {static_cast<std::uint16_t>(temporary / 8), 0, Bit(temporary)};
    }

private:
    static constexpr std::uint8_t Bit(unsigned flag) {
        return static_cast<std::uint8_t>(0x80u >> (flag % 8));
    }
};

// Original 1.09 EMEVD positions and temporary movement/lever interlocks.
// Permanent unlocks stay in the ordinary additive progress path.
inline std::span<const LiftFlagByte> LiftFlags(std::uint32_t group) {
    using F = LiftFlagByte;
    static constexpr F hemwick[]{F::Position(125, 126)};
    static constexpr F yharnam[]{F::Position(350, 351)};
    static constexpr F yharnam_busy[]{F::Temporary(350)};
    static constexpr F upper_ward[]{F::Position(154, 155)};
    static constexpr F woods[]{F::Position(134, 135), F::Position(144, 145)};
    static constexpr F yahargul[]{F::Position(610, 611)};
    static constexpr F yahargul_busy[]{F::Temporary(700)};
    static constexpr F mensis[]{F::Position(115, 116)};
    static constexpr F hall[]{F::Position(106), F::Position(116), F::Position(126)};
    static constexpr F hall_busy[]{F::Temporary(100), F::Temporary(110), F::Temporary(120)};
    static constexpr F hamlet[]{F::Position(106)};
    static constexpr F hamlet_busy[]{F::Temporary(100)};
    switch (group) {
    case 12200: return hemwick;
    case 12410: return yharnam;
    case 12415: return yharnam_busy;
    case 12420: return upper_ward;
    case 12700: return woods;
    case 12800: return yahargul;
    case 12804: return yahargul_busy;
    case 13300: return mensis;
    case 13501: return hall;
    case 13504: return hall_busy;
    case 13601: return hamlet;
    case 13604: return hamlet_busy;
    default: return {};
    }
}
} // namespace Core::Bloodborne::World
