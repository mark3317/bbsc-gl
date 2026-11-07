// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "core/bbsc_world_presence.h"

namespace Core::Bloodborne::World {
enum class PlayerVisualPhase {Loading,Apart,WaitingActor,WaitingModel,Dead,Resident};
struct PlayerVisualInput {
    u64 local_visit=0,peer_visit=0,actor=0,model=0;
    u64 local_load=0;
    u32 local_map=0,peer_map=0;
    bool loading=true,here=false,alive=false,actor_alive=false,actor_ready=false,task_ready=false;
    bool disabled=false,actor_dead=false;
    bool admitted_load=false; // native creation completed without a model watchdog
};
struct PlayerVisualAction {
    PlayerVisualPhase phase=PlayerVisualPhase::Loading;
    bool hide=false,enable=false,rebind=false,insert=false,kept_border=false;
};
// One lifecycle per native peer. Actor/model addresses are observations, never
// retained pointers to write after a load. Each input revalidates identity.
class PlayerVisualLife {
public:
    PlayerVisualAction Observe(PlayerVisualInput in,s64 now) {
        PlayerVisualAction out;
        const bool journey=in.local_visit!=last_.local_visit || in.peer_visit!=last_.peer_visit || in.here!=last_.here;
        // PlaceTracker advances visit on a border WALK as well as on a load.
        // Preserve an already admitted actor when only adjacent map IDs change;
        // removing it drops both mesh and name and restarts native FirstSync.
        const bool border=journey && in.here && last_.here && in.alive && last_.alive &&
            in.actor && (in.actor==last_.actor || in.admitted_load) && in.actor_ready && in.task_ready &&
            in.local_load==last_.local_load &&
            (in.local_visit==last_.local_visit || PlayerMapBorder(in.local_map,last_.local_map)) &&
            (in.peer_visit==last_.peer_visit || PlayerMapBorder(in.peer_map,last_.peer_map));
        out.kept_border=border;
        // StageFlow can allocate a NEW PlayerIns from the retained remote slot
        // while its member task is still at CreateWait. Neither that address nor
        // a draw graph proves FirstSync ran for this meeting. Admit once per
        // journey, including a missing or newly allocated actor, then leave the
        // actor produced by that admission alone on subsequent observations.
        if(last_.local_visit && journey && in.here && !border)
            refresh_=true;
        // A kept death does not advance either visit. Rebinding the same
        // PlayerIns cannot undo native death teardown (including AI presence).
        // Use the original removal/FirstSync creation once per reported revival.
        const bool revived=last_.local_visit && !journey && in.here &&
                           !last_.alive && in.alive;
        if(revived)refresh_=true;
        const bool changed=journey || in.actor!=last_.actor || in.model!=last_.model ||
                           in.alive!=last_.alive || in.actor_alive!=last_.actor_alive ||
                           in.actor_ready!=last_.actor_ready || in.actor_dead!=last_.actor_dead;
        if(changed){since_=now;bound_=false;}
        if(journey || revived){retries_=0;last_insert_=0;}
        last_=in;
        if(in.loading){out.phase=PlayerVisualPhase::Loading;return out;}
        if(!in.here){out.phase=PlayerVisualPhase::Apart;out.hide=in.actor && !in.disabled;return out;}
        out.enable=in.actor && in.disabled;
        if(!in.task_ready){out.phase=PlayerVisualPhase::WaitingActor;return out;}
        if(refresh_){
            refresh_=false;out.insert=true;last_insert_=now;++retries_;
            out.phase=PlayerVisualPhase::WaitingActor;return out;
        }
        // A short death can fall between presence packets. Native dead flags
        // plus restored HP independently identify a stale remote corpse. Give
        // native reception time to settle and retain the existing retry bound.
        if(in.alive && in.actor_alive && in.actor_dead){
            out.phase=PlayerVisualPhase::Dead;
            if(now-since_>=1000 && retries_<2 && (!last_insert_ || now-last_insert_>=4000)){
                out.insert=true;last_insert_=now;++retries_;
            }
            return out;
        }
        if(!in.actor || !in.model || !in.actor_ready){
            out.phase=in.actor?PlayerVisualPhase::WaitingModel:PlayerVisualPhase::WaitingActor;
            // Native creation owns model loading. A persistent missing actor or
            // render graph is retried, with a bound, never every frame.
            if(now-since_>=2500 && retries_<2 && (!last_insert_ || now-last_insert_>=4000)){
                out.insert=true;last_insert_=now;++retries_;
            }
            return out;
        }
        if(!bound_){out.rebind=true;bound_=true;}
        if(!in.alive || !in.actor_alive){out.phase=PlayerVisualPhase::Dead;return out;}
        out.phase=PlayerVisualPhase::Resident;
        // Native character creation owns render/death/opacity. A non-null draw
        // state is not proof of a visible mesh; its +0C byte is not a visibility API.
        return out;
    }
private:
    PlayerVisualInput last_{};
    s64 since_=0,last_insert_=0;
    unsigned retries_=0;
    bool bound_=false;
    bool refresh_=false;
};
} // namespace Core::Bloodborne::World
