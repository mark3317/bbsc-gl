#pragma once

#include <cstdint>
#include <cstring>

// OrbisPadData prefix only. Keep right-stick camera, connection bit, timestamp,
// touches and sensor data. Called only during a confirmed gameplay quit wait.
inline void FilterBbscQuitPad(std::uint8_t* data) {
    std::uint32_t buttons;
    std::memcpy(&buttons, data, sizeof(buttons));
    buttons &= 0x80000000u;
    std::memcpy(data, &buttons, sizeof(buttons));
    data[4] = data[5] = 128;
    data[8] = data[9] = 0;
}
