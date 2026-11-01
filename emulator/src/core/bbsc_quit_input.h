// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <atomic>
#include <cstdint>
#include <cstring>

namespace Core::Bbsc {
// The confirmed exit owns input until cancellation or the native title handoff.
inline std::atomic<bool> quit_input_blocked{false};
inline bool BlockQuitPadInput(int result, std::uint8_t* data) {
    if (result != 0 || !data || !quit_input_blocked.load()) return false;
    std::uint32_t buttons;
    std::memcpy(&buttons, data, sizeof(buttons));
    buttons &= 0x80000000u; // preserve the native system bit
    std::memcpy(data, &buttons, sizeof(buttons));
    data[4] = data[5] = data[6] = data[7] = 128;
    data[8] = data[9] = 0;
    return true;
}
} // namespace Core::Bbsc
