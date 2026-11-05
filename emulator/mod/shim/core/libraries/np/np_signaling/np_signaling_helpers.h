// BBSC mod: BBSC's own packets go through the BBSC relay (bbsc_relay.cpp), not the emulator's
// signaling. Same functions, same meaning.
#pragma once
#include "core/bbsc_chalice.h"
#include "core/bbsc_follow.h"
#include "common/types.h"

namespace Libraries::Np::NpSignaling::Helpers {
u32 SendBbscFollowToPeers(u32 packed_map, float x, float y, float z, float heading, u32 sequence,
                          s32 lamp_point, const Core::Bloodborne::Chalice::Key& dungeon = {},
                          const Core::Bloodborne::Follow::Arrival& arrival = {});
u32 SendBbscWorldFlagsToPeers(const void* packet, u32 size);
} // namespace Libraries::Np::NpSignaling::Helpers
