// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <vector>
#include "core/bbsc_world_presence.h"

namespace Core::Bloodborne::World {
// The host's seven ritual records are a guest VIEW. They are never a replacement
// for the guest's personal altar flags or cached native ritual objects. Full
// records are committed atomically; OR-merging record bits corrupts map IDs.
inline constexpr std::size_t AltarCount = 7, AltarRecordBytes = 750;
inline constexpr std::size_t AltarProgressAt = 625;
using AltarRecord = std::array<u8, AltarRecordBytes>;
struct AltarEntry {
    bool occupied = false;
    u64 ritual = 0; // increments when that slot is removed/replaced/recreated
    AltarRecord record{};
    Chalice::Key dungeon{};
    std::vector<u8> form;
    std::array<bool, 4> lamps{};
    bool operator==(const AltarEntry&) const = default;
};
inline bool Valid(const AltarEntry& a) {
    if (!a.occupied) return a.ritual != 0 && a.dungeon == Chalice::Key{} && a.form.empty() &&
                            a.lamps == std::array<bool, 4>{};
    return a.ritual != 0 && a.record[0] == 29 && Chalice::Valid(a.dungeon) &&
           a.form.size() == a.dungeon.form_size && Chalice::HashForm(a.form) == a.dungeon.form_hash;
}
struct AltarCatalog {
    WorldId world{};
    u64 revision = 0;
    std::array<AltarEntry, AltarCount> altars{};
};
inline bool Valid(const AltarCatalog& c) {
    return Valid(c.world) && c.revision != 0 &&
           std::all_of(c.altars.begin(), c.altars.end(), [](const auto& a) { return Valid(a); });
}
class GuestAltars {
public:
    void Bind(WorldId world) { if (world != world_) { world_ = world; catalog_.reset(); } }
    bool Take(u32 sender, AltarCatalog c) {
        if (!Valid(world_) || sender != world_.host || c.world != world_ || !Valid(c) ||
            (catalog_ && c.revision <= catalog_->revision)) return false;
        // A slot's ritual incarnation cannot go backwards, including a removed
        // altar. It fences queued lamp/menu requests against re-created rituals.
        if (catalog_) for (std::size_t i = 0; i < AltarCount; ++i) {
            const auto& before = catalog_->altars[i];
            const auto& after = c.altars[i];
            if (after.ritual < before.ritual ||
                (after.ritual == before.ritual &&
                 (after.occupied != before.occupied ||
                  !std::equal(after.record.begin(),after.record.begin()+AltarProgressAt,before.record.begin()) ||
                  after.dungeon != before.dungeon || after.form != before.form))) return false;
        }
        catalog_ = std::move(c);
        return true;
    }
    const AltarEntry* Destination(std::size_t slot, u64 ritual, std::size_t layer) const {
        if (!catalog_ || slot >= AltarCount || layer >= 4) return nullptr;
        const auto& a = catalog_->altars[slot];
        return a.occupied && a.ritual == ritual && a.lamps[layer] ? &a : nullptr;
    }
    const std::optional<AltarCatalog>& View() const { return catalog_; }
private:
    WorldId world_{};
    std::optional<AltarCatalog> catalog_;
};
} // namespace Core::Bloodborne::World
