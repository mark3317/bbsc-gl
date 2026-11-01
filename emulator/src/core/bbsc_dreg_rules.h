#pragma once
#include "common/types.h"
namespace Core::Bloodborne {
// One certificate per local life, even when damage/reward callbacks are replayed.
struct DregLife {
    u64 player = 0;
    u32 session = 0;
    bool alive = false;
    void Observe(u64 chr, u32 key, bool loaded, s32 hp) {
        if (!loaded || !key) { player = 0; session = 0; alive = false; return; }
        player = chr; session = key; alive = hp > 0;
    }
    bool Lethal(u64 victim, u64 killer, u32 key, s32 hp, bool pvp, bool player_killer) {
        if (!alive || !victim || victim != player || !key || key != session || hp != 0) return false;
        alive = false;
        return pvp && player_killer && killer && killer != victim;
    }
};
}
