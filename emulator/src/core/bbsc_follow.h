// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cmath>
#include <cstring>
#include <vector>
#include "core/bbsc_chalice.h"

namespace Core::Bloodborne::Follow {
// kind 1 appends a repeated, immutable record of the host's last completed load.
// The legacy 34-byte prefix and optional dungeon key keep their original layout.
#pragma pack(push, 1)
struct Arrival {
    std::uint32_t generation = 0;
    std::uint32_t map = 0;
    float x = 0, y = 0, z = 0, heading = 0;
};
#pragma pack(pop)
static_assert(sizeof(Arrival) == 24);
inline bool Valid(const Arrival& a) {
    return a.generation != 0 && (a.map >> 24) >= 21 && (a.map >> 24) <= 36 &&
           std::isfinite(a.x) && std::isfinite(a.y) && std::isfinite(a.z) &&
           std::isfinite(a.heading);
}
// Shared by the bundled relay, emulator relay and native signaling transport.
template<class Packet>
bool Decode(const void* data, std::size_t size, Packet& packet,
            Chalice::Key& dungeon, Arrival& arrival) {
    packet = {}; dungeon = {}; arrival = {};
    if (!data || size < 0x1E) return false;
    const auto* bytes = static_cast<const std::uint8_t*>(data);
    if (std::memcmp(bytes, "SHAD", 4) != 0 || bytes[4] != Protocol::Follow || bytes[5] > 1)
        return false;
    const bool extended = bytes[5] == 1;
    if (size == 0x1E && !extended) {
        std::memcpy(&packet, data, size);
        packet.lamp_point = -1;
        return true;
    }
    const std::size_t base = sizeof(Packet);
    if (size < base) return false;
    std::memcpy(&packet, data, base);
    const bool scoped = Chalice::IsMap(packet.packed_map);
    const std::size_t tail = base + (scoped ? sizeof(dungeon) : 0);
    if (size != tail + (extended ? sizeof(arrival) : 0)) return false;
    if (scoped) std::memcpy(&dungeon, bytes + base, sizeof(dungeon));
    if (extended) {
        std::memcpy(&arrival, bytes + tail, sizeof(arrival));
        if (arrival.generation != 0 && !Valid(arrival)) return false;
    }
    return true;
}
template<class Packet>
std::vector<std::uint8_t> Encode(Packet packet, const Chalice::Key& dungeon,
                                 const Arrival& arrival) {
    packet.kind = 1;
    const bool scoped = Chalice::IsMap(packet.packed_map);
    const std::size_t tail = sizeof(packet) + (scoped ? sizeof(dungeon) : 0);
    std::vector<std::uint8_t> bytes(tail + sizeof(arrival));
    std::memcpy(bytes.data(), &packet, sizeof(packet));
    if (scoped) std::memcpy(bytes.data() + sizeof(packet), &dungeon, sizeof(dungeon));
    std::memcpy(bytes.data() + tail, &arrival, sizeof(arrival));
    return bytes;
}
} // namespace Core::Bloodborne::Follow
