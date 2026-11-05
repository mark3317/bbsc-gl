// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "core/bbsc_world_presence.h"

namespace Core::Bloodborne::World {
enum class PlayerVisualPhase {Loading,Apart,WaitingActor,WaitingModel,Dead,Resident};
struct PlayerVisualInput {
    u64 local_visit=0,peer_visit=0,actor=0,model=0;
    bool loading=true,here=false,alive=false,actor_alive=false,actor_ready=false,task_ready=false;
    bool disabled=false;
};
struct PlayerVisualAction {
    PlayerVisualPhase phase=PlayerVisualPhase::Loading;
    bool hide=false,enable=false,rebind=false,insert=false;
};
// One lifecycle per native peer. Actor/model addresses are observations, never
// retained pointers to write after a load. Each input revalidates identity.
class PlayerVisualLife {
public:
    PlayerVisualAction Observe(PlayerVisualInput in,s64 now) {
        PlayerVisualAction out;
        const bool journey=in.local_visit!=last_.local_visit || in.peer_visit!=last_.peer_visit || in.here!=last_.here;
        // StageFlow can allocate a NEW PlayerIns from the retained remote slot
        // while its member task is still at CreateWait. Neither that address nor
        // a draw graph proves FirstSync ran for this meeting. Admit once per
        // journey, including a missing or newly allocated actor, then leave the
        // actor produced by that admission alone on subsequent observations.
        if(last_.local_visit && journey && in.here)
            refresh_=true;
        const bool changed=journey || in.actor!=last_.actor || in.model!=last_.model ||
                           in.alive!=last_.alive || in.actor_alive!=last_.actor_alive || in.actor_ready!=last_.actor_ready;
        if(changed){since_=now;bound_=false;}
        if(journey){retries_=0;last_insert_=0;}
        last_=in;
        if(in.loading){out.phase=PlayerVisualPhase::Loading;return out;}
        if(!in.here){out.phase=PlayerVisualPhase::Apart;out.hide=in.actor && !in.disabled;return out;}
        out.enable=in.actor && in.disabled;
        if(!in.task_ready){out.phase=PlayerVisualPhase::WaitingActor;return out;}
        if(refresh_){
            refresh_=false;out.insert=true;last_insert_=now;++retries_;
            out.phase=PlayerVisualPhase::WaitingActor;return out;
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
