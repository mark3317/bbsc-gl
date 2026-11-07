// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "bbsc_dream_finale.h"

// Independent travel foundation. A room member is not necessarily present on a
// map. Inspired by Yharnam Together's PlaceTracker/EnemyOwners/channel table
// (CLS_AMG and contributors, GPL-2.0-or-later); adapted for BBSC's direct P2P
// transport and personal chalice worlds. No native pointers or save writes here.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <map>
#include <optional>
#include <span>
#include "core/bbsc_native_sync_test.h"
#include "core/bbsc_chalice.h"

namespace Core::Bloodborne::World {
using u8 = std::uint8_t;
using u32 = std::uint32_t;
using u64 = std::uint64_t;
using s64 = std::int64_t;
inline constexpr s64 PresenceFreshMs = 3'000;
inline constexpr s64 BorderSettleMs = 1'500;
inline constexpr u32 PresenceCapability = 1;
// Deliberately NOT advertised by this first bridge. A compatible presence packet
// alone must never open lamps, suppress follow, or authorize enemy ownership.
inline constexpr u32 IndependentTravelCapability = 2;
inline constexpr u32 NativeFinaleCapability = 1u << 16;

#pragma pack(push,1)
struct WorldId {
    u32 host = 0;
    u64 room = 0; // full native Matching2 room ID; never an endpoint/roster ID
    bool operator==(const WorldId&) const = default;
};
#pragma pack(pop)
static_assert(sizeof(WorldId)==12);
constexpr bool Valid(WorldId id) { return id.host != 0 && id.room != 0; }
constexpr bool ValidMap(u32 map) { return (map >> 24) >= 21 && (map >> 24) <= 36; }

enum class Phase : u8 { Unknown, Loading, Playing, Leaving };
#pragma pack(push, 1)
struct Presence {
    char magic[4] = {'S','H','A','D'};
    u8 type = Protocol::WorldPresence;
    u8 version = 2;
    Phase phase = Phase::Unknown;
    u8 reserved = 0;
    WorldId world{};
    u64 sequence = 0; // strictly increasing within this sender's process
    u64 visit = 0; // increments at every load, including a same-map reload
    u32 capabilities = PresenceCapability;
    u32 map = 0; // last committed map while loading, never permission to simulate
    Chalice::Key dungeon{};
    u64 ritual = 0; // world-scoped ritual incarnation; NOT a loader revision
    float x = 0, y = 0, z = 0;
    u8 alive = 0;
    Core::Bbsc::DreamFinale::Signal finale{};
};
#pragma pack(pop)
static_assert(sizeof(Presence) == 92);

inline bool Valid(const Presence& p) {
    if (std::memcmp(p.magic, "SHAD", 4) || p.type != Protocol::WorldPresence ||
        p.version != 2 || !Valid(p.world) || p.sequence == 0 || p.reserved ||
        p.phase > Phase::Leaving || p.alive > 1 ||
        !(p.capabilities & PresenceCapability) ||
        (p.finale != Core::Bbsc::DreamFinale::Signal{} &&
         !(p.capabilities & NativeFinaleCapability)) ||
        (!Core::Bbsc::DreamFinale::Valid(p.finale, true) &&
         !Core::Bbsc::DreamFinale::Valid(p.finale, false)) ||
        !std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z)) return false;
    if (p.phase == Phase::Playing && (!ValidMap(p.map) || p.visit == 0)) return false;
    if (p.map != 0 && !ValidMap(p.map)) return false;
    if (Chalice::IsMap(p.map)) {
        // Missing identity is a valid observation during native setup, but cannot
        // authorize shared simulation (SamePlace below).
        if (p.dungeon != Chalice::Key{} && !Chalice::Valid(p.dungeon)) return false;
    } else if (p.dungeon != Chalice::Key{} || p.ritual != 0) return false;
    return true;
}

inline std::optional<Presence> Decode(std::span<const u8> bytes) {
    if (bytes.size() != sizeof(Presence)) return std::nullopt;
    Presence p;
    std::memcpy(&p, bytes.data(), sizeof(p));
    return Valid(p) ? std::optional{p} : std::nullopt;
}
inline bool SamePlace(const Presence& a, const Presence& b) {
    if (!Valid(a) || !Valid(b) || a.phase != Phase::Playing || b.phase != Phase::Playing ||
        a.world != b.world) return false;
    if(!Chalice::IsMap(a.map) || !Chalice::IsMap(b.map))return a.map==b.map;
    return a.ritual != 0 && a.ritual == b.ritual &&
           Chalice::Valid(a.dungeon) && a.dungeon == b.dungeon;
}

// Player presentation spans a directly connected native map border. Keep
// SamePlace strict for events, ownership, lamps and non-player packet routing.
// Pairs come from original 1.09 MSB ConnectCollision target area/block bytes;
// this is deliberately NOT a transitive world/region grouping. Dream m21_00
// and separate chalice rituals must never acquire actors from another place.
inline constexpr std::array<std::array<u32,2>,14> PlayerMapBorders{{
    {0x15010000,0x18000000}, {0x16000000,0x18000000},
    {0x17000000,0x18000000}, {0x17000000,0x1C000000},
    {0x18000000,0x18010000}, {0x18000000,0x18020000},
    {0x18000000,0x1B000000}, {0x18000000,0x1C000000},
    {0x18010000,0x1B000000}, {0x19000000,0x1C000000},
    {0x19000000,0x1E000000}, {0x1B000000,0x20000000},
    {0x22000000,0x23000000}, {0x23000000,0x24000000}
}};
inline bool PlayerMapBorder(u32 a,u32 b) {
    const std::array<u32,2> pair{std::min(a,b),std::max(a,b)};
    return std::ranges::find(PlayerMapBorders,pair)!=PlayerMapBorders.end();
}
inline bool SamePlayerSpace(const Presence& a,const Presence& b) {
    if(SamePlace(a,b))return true;
    if(!Valid(a) || !Valid(b) || a.phase!=Phase::Playing || b.phase!=Phase::Playing ||
       a.world!=b.world || Chalice::IsMap(a.map) || Chalice::IsMap(b.map))return false;
    return PlayerMapBorder(a.map,b.map);
}

// Raw map reads flicker at borders. Actual loading invalidates presence at once;
// only an ordinary border walk gets hysteresis. Zero reads never erase the last
// committed place. Once a load starts, wait for a real positioned actor to return.
class PlaceTracker {
public:
    void Observe(u32 raw_map, bool loading, bool positioned, s64 now) {
        if (loading || !positioned) {
            phase_ = Phase::Loading;
            pending_map_ = 0;
            return;
        }
        if (!ValidMap(raw_map)) return;
        if (phase_ != Phase::Playing) {
            map_ = raw_map;
            ++visit_;
            phase_ = Phase::Playing;
            pending_map_ = 0;
        } else if (raw_map == map_) {
            pending_map_ = 0;
        } else if (pending_map_ != raw_map) {
            pending_map_ = raw_map;
            pending_since_ = now;
        } else if (now >= pending_since_ && now - pending_since_ >= BorderSettleMs) {
            map_ = raw_map;
            ++visit_;
            pending_map_ = 0;
        }
    }
    // Keep the process-wide visit counter even if native session state briefly
    // disappears during a load and the same room is bound again afterwards.
    void Clear() {
        map_ = pending_map_ = 0;
        pending_since_ = 0;
        phase_ = Phase::Unknown;
    }
    u32 Map() const { return map_; }
    u64 Visit() const { return visit_; }
    Phase State() const { return phase_; }
private:
    u32 map_ = 0, pending_map_ = 0;
    u64 visit_ = 0;
    s64 pending_since_ = 0;
    Phase phase_ = Phase::Unknown;
};

struct Member {
    Presence presence{};
    s64 received = 0;
    s64 arrived = 0;
};
class PresenceBook {
public:
    void Bind(WorldId world, u32 self) {
        if (world_ != world || self_ != self) {
            members_.clear();
            // Sequence fences reset only on an actual room/world change. Expiry
            // or a temporary load must not let a delayed Playing packet revive
            // an old visit.
            last_.clear();
            world_ = world;
            self_ = self;
        }
    }
    bool Hear(u32 sender, WorldId envelope, const Presence& p, s64 now) {
        if (!sender || sender == self_ || !self_ || !Valid(world_) ||
            envelope != world_ || p.world != world_ || !Valid(p) ||
            !Core::Bbsc::DreamFinale::Valid(p.finale, sender == world_.host)) return false;
        // Native movies/loading can suspend game ticks for many seconds.
        // Only an observed leave/map change or native room departure removes
        // residency; heartbeat age is not a new authority election.
        if (members_.size() >= 4 && !members_.contains(sender)) return false;
        auto old = last_.find(sender);
        if (old != last_.end() && (p.sequence <= old->second.sequence ||
                                  p.visit < old->second.visit)) return false;
        const auto it = members_.find(sender);
        const s64 arrived = it != members_.end() && SamePlace(it->second.presence, p)
                                ? it->second.arrived : now;
        last_[sender] = {p.sequence, p.visit};
        members_[sender] = {p, now, arrived};
        return true;
    }
    void Forget(u32 sender) { members_.erase(sender); }
    void Clear() { Bind({}, 0); }
    const std::map<u32, Member>& Members() const { return members_; }
    bool Known(u32 sender) const { return last_.contains(sender); }
    static bool Fresh(const Member& m, s64 now) {
        return now >= m.received && now - m.received < PresenceFreshMs;
    }
    const Member* Find(u32 sender, s64 now) const {
        const auto it = members_.find(sender);
        return it != members_.end() && Fresh(it->second, now) ? &it->second : nullptr;
    }
    const Member* Resident(u32 sender) const {
        const auto it=members_.find(sender);return it==members_.end()?nullptr:&it->second;
    }
    u32 LivingHere(const Presence& local, s64 /*now*/) const {
        u32 count = 0;
        for (const auto& [id, m] : members_)
            count += m.presence.alive && SamePlace(local, m.presence);
        return count;
    }
    bool AllSupportTravel(const Presence& local, std::span<const u32> native_members,
                          s64 now) const {
        if (!Valid(local) || local.world != world_ ||
            !(local.capabilities & IndependentTravelCapability)) return false;
        for (const auto peer : native_members) {
            if (!peer || peer == self_) return false;
            const auto* member = Find(peer, now);
            if (!member || !(member->presence.capabilities & IndependentTravelCapability) ||
                (member->presence.capabilities & SessionTest::Capability) !=
                (local.capabilities & SessionTest::Capability)) return false;
        }
        return true;
    }
private:
    struct Fence { u64 sequence = 0, visit = 0; };
    WorldId world_{};
    u32 self_ = 0;
    std::map<u32, Member> members_;
    std::map<u32, Fence> last_;
};

// A coordinator decision, not a local timeout election. All recipients use the
// same authoritative roster/snapshot. Keep a present owner; prefer the host only
// when initially choosing, avoiding an enemy reset when the host returns.
inline u32 ChooseOwner(const Presence& place, const std::map<u32, Member>& members,
                       u32 previous, s64 now) {
    const auto eligible = [&](const auto& entry) {
        return entry.first && PresenceBook::Fresh(entry.second, now) &&
               SamePlace(place, entry.second.presence);
    };
    if (const auto it = members.find(previous); it != members.end() &&
        SamePlace(place,it->second.presence)) return previous;
    if (const auto it = members.find(place.world.host); it != members.end() && eligible(*it)) return it->first;
    u32 chosen = 0;
    s64 earliest = 0;
    for (const auto& entry : members) {
        if (eligible(entry) && (!chosen || entry.second.arrived < earliest)) {
            chosen = entry.first;
            earliest = entry.second.arrived;
        }
    }
    return chosen;
}

enum class NativePolicy { Session, SamePlace, Personal, Drop };
constexpr NativePolicy ChannelPolicy(u32 channel) {
    switch (channel) {
    case 0x04: case 0x05: case 0x06: case 0x0E: case 0x0F: case 0x12:
    case 0x14: case 0x15: case 0x16: case 0x17: case 0x24: case 0x25:
    case 0x29: case 0x2A: case 0x2B: case 0x2D: case 0x2E: case 0x2F: case 0x30:
    case 0x31: case 0x34: case 0x36: case 0x37: case 0x3D: case 0x3E:
    case 0x40: case 0x41: return NativePolicy::SamePlace;
    case 0x2C: return NativePolicy::Personal;
    case 0x27: return NativePolicy::Drop;
    default: return NativePolicy::Session;
    }
}
inline bool Routes(u32 channel, const Presence& sender, const Presence& target) {
    if (channel >= 0x44 || !Valid(sender) || !Valid(target) || sender.world != target.world) return false;
    switch (ChannelPolicy(channel)) {
    case NativePolicy::Session: return true;
    case NativePolicy::SamePlace: return SamePlace(sender, target);
    case NativePolicy::Personal: case NativePolicy::Drop: return false;
    }
    return false;
}
} // namespace Core::Bloodborne::World
