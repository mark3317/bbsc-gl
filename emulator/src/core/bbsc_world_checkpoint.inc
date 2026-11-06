// SPDX-License-Identifier: GPL-2.0-or-later
// Death uses the original point-load entry, without a lamp departure animation.
// Prepare exactly the selected world/ritual, then let the existing native loader
// and FirstSync/bootstrap barriers rebuild the local character and collision.
bool BeginBbscSharedLampLoad(const World::Scope& scope,s32 point) {
    const u64 global=GetGlobalState();
    if(!ReadablePointer(global,0x1530) || ReadValue<u8>(global,8) ||
       !HasMemoryAccess(global+0x1528,8,MemoryProt::CpuWrite))return false;
    if(Chalice::IsMap(scope.map)){
        const auto altar=std::ranges::find_if(bbsc_world_altars,[&](const auto& a){
            return a.entry.occupied && a.entry.ritual==scope.ritual && a.mount.key==scope.dungeon;});
        if(altar==bbsc_world_altars.end())return false;
        bbsc_world_altar_visiting=static_cast<s32>(altar-bbsc_world_altars.begin());
        bbsc_world_requested_mount=altar->mount;
    }else bbsc_world_requested_mount.reset();
    bbsc_world_requested_scope=scope;
    BbscWorldEnsureSeed(scope);
    if(!BbscWorldHasSnapshot(scope.map)){
        World::Control request;request.kind=World::ControlKind::Request;request.scope=scope;
        request.owner=BbscMod::RegisterOwnId();request.sequence=++bbsc_world_state_sequence;
        // Reuse the destination request throttle while this dead player waits.
        if(SteadyNowMs()-bbsc_world_travel_request_sent>=500){
            BbscWorldSend(request);bbsc_world_travel_request_sent=SteadyNowMs();}
        return false;
    }
    if(Chalice::IsMap(scope.map) && !PrepareBbscChaliceLoad(scope.map))return false;
    const s32 aux=scope.map==BbscDreamStateMap?101200:101163;
    WriteValue<s64>(global,0x1528,(static_cast<s64>(aux)<<32)|static_cast<u32>(point));
    bbsc_world_travel_world=scope.world;bbsc_world_travel_point=point;bbsc_world_travel_flag=0;
    bbsc_world_travel_inflight=true;bbsc_world_travel_saw_load=false;bbsc_world_travel_native_armed=false;
    bbsc_world_travel_load=bbsc_load_generation.load();bbsc_world_travel_since=SteadyNowMs();
    if(!Chalice::IsMap(scope.map))bbsc_world_altar_visiting=-1;
    NotifyBbscHostDeathReload();ClearBbscBossContext("before shared lamp death load");
    using PointLoad=void PS4_SYSV_ABI (*)(s32);
    reinterpret_cast<PointLoad>(image_base+0x013CDF30)(point);
    BBSC_TIMELINE("RESPAWN","shared lamp native death load point={} map={:#x} ritual={}",point,scope.map,scope.ritual);
    return true;
}

// Game-thread state. The host orders actual lamp activations, independently of
// additive unlock masks, NPC ownership, travel and personal checkpoint writes.
struct BbscSharedLamp {
    World::Scope scope{};
    s32 point=0;
    u32 actor=0;
    u64 sequence=0,revision=0;
    s64 lit_ms=0; // UTC activation time, preserved through retries and host ordering
};
World::WorldId bbsc_checkpoint_world{};
BbscSharedLamp bbsc_checkpoint{},bbsc_checkpoint_offer{},bbsc_checkpoint_reload{};
std::map<u32,u64> bbsc_checkpoint_seen;
std::map<u32,BbscSharedLamp> bbsc_checkpoint_accepted;
u64 bbsc_checkpoint_sequence=0;
s64 bbsc_checkpoint_sent=0,bbsc_checkpoint_reload_since=0;
u32 bbsc_checkpoint_reload_load=0;
bool bbsc_checkpoint_fallback=false;
s64 bbsc_native_lamp_selected_ms=0;
s64 BbscLampSelectionTimeMs() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}
void BindBbscSharedLamp(const World::WorldId& world);
void NoteBbscNativeLampSelection() {
    // Existing native point-load boundary, alive journeys only. Death reloads
    // must not make their own destination newer than the shared ignition.
    if (GetCharacterHp(GetLocalPlayerCharacter())<=0) return;
    World::WorldId world;
    {std::scoped_lock lock{bbsc_world_presence_mutex};world=bbsc_world_presence_local.world;}
    BindBbscSharedLamp(world);
    bbsc_native_lamp_selected_ms=BbscLampSelectionTimeMs();
}

void BindBbscSharedLamp(const World::WorldId& world) {
    if(bbsc_checkpoint_world==world)return;
    bbsc_native_lamp_selected_ms=0;
    bbsc_checkpoint_world=world;bbsc_checkpoint={};bbsc_checkpoint_offer={};bbsc_checkpoint_reload={};
    bbsc_checkpoint_seen.clear();bbsc_checkpoint_accepted.clear();bbsc_checkpoint_sent=0;
    // Preserve proposal ordering when this process reconnects to the same room.
    // A restarted process also advances from the system's steady-clock epoch.
    bbsc_checkpoint_sequence=std::max(bbsc_checkpoint_sequence,static_cast<u64>(std::max<s64>(0,SteadyNowMs())));
}
bool ValidBbscSharedLamp(const BbscSharedLamp& lamp) {
    if(!World::Valid(lamp.scope) || lamp.scope.world!=bbsc_checkpoint_world ||
       !BbscWorldLampScopeKnown(lamp.scope))return false;
    if(Chalice::IsMap(lamp.scope.map))return lamp.point>=2902950 && lamp.point<=2902959;
    return std::ranges::any_of(LampPoints,[&](const auto& p){
        return p.warp_point==lamp.point && p.packed_map==lamp.scope.map;});
}
void SendBbscSharedLamp(const BbscSharedLamp& lamp) {
    World::Control c;c.kind=World::ControlKind::LampCheckpoint;c.scope=lamp.scope;
    c.owner=lamp.actor;c.sequence=lamp.sequence;c.epoch=lamp.revision;
    std::array<u8,sizeof(s32)+sizeof(s64)> payload{};
    std::memcpy(payload.data(),&lamp.point,sizeof(lamp.point));
    std::memcpy(payload.data()+sizeof(s32),&lamp.lit_ms,sizeof(lamp.lit_ms));
    BbscWorldSend(c,payload);
}
void AcceptBbscSharedLamp(BbscSharedLamp lamp) {
    bbsc_checkpoint_seen[lamp.actor]=lamp.sequence;
    // Arrival order is not ignition order. A delayed older act cannot win.
    if(bbsc_checkpoint.revision && lamp.lit_ms<bbsc_checkpoint.lit_ms){
        bbsc_checkpoint_accepted[lamp.actor]=bbsc_checkpoint;
        SendBbscSharedLamp(bbsc_checkpoint);return;
    }
    lamp.revision=bbsc_checkpoint.revision+1;bbsc_checkpoint=lamp;
    bbsc_checkpoint_accepted[lamp.actor]=lamp;
    SendBbscSharedLamp(lamp);
    BBSC_TIMELINE("RESPAWN","shared lamp selected point={} map={:#x} ritual={} actor={:08x} revision={}",
        lamp.point,lamp.scope.map,lamp.scope.ritual,lamp.actor,lamp.revision);
}
void QueueBbscSharedLampCheckpoint(s32 point) {
    if(!BbscIndependentTravelAllowed() || (GetSessionState()!=3 && GetSessionState()!=6))return;
    World::Presence local;{std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;}
    BindBbscSharedLamp(local.world);
    BbscSharedLamp lamp{World::ScopeOf(local),point,BbscMod::RegisterOwnId(),++bbsc_checkpoint_sequence,0};
    lamp.lit_ms=BbscLampSelectionTimeMs();
    const u32 map=GetCurrentPackedMap();
    if(!lamp.actor || lamp.scope.map!=(Chalice::IsMap(map)?0x1D000000u:map) || !ValidBbscSharedLamp(lamp))return;
    if(lamp.actor==local.world.host)AcceptBbscSharedLamp(lamp);
    else {bbsc_checkpoint_offer=lamp;SendBbscSharedLamp(lamp);}
}
void BbscWorldReceiveLampCheckpoint(const BbscWorldIncoming& message) {
    if(!BbscIndependentActive() || message.payload.size()!=sizeof(s32)+sizeof(s64) ||
       message.control.parts!=1 || message.control.part)return;
    World::Presence local;bool member=false;
    {std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;
        member=bbsc_world_presence_book.Resident(message.sender)!=nullptr;}
    BindBbscSharedLamp(local.world);
    const auto& c=message.control;
    BbscSharedLamp lamp{c.scope,0,c.owner,c.sequence,c.epoch};
    std::memcpy(&lamp.point,message.payload.data(),sizeof(lamp.point));
    std::memcpy(&lamp.lit_ms,message.payload.data()+sizeof(s32),sizeof(lamp.lit_ms));
    if(lamp.lit_ms<0 || !lamp.actor || !lamp.sequence || !ValidBbscSharedLamp(lamp))return;
    const u32 self=BbscMod::RegisterOwnId();
    if(self==local.world.host){
        // Only direct member proposals, never a peer's purported canonical echo.
        if(!member || message.sender!=lamp.actor || lamp.revision)return;
        if(lamp.sequence<=bbsc_checkpoint_seen[lamp.actor]){
            if(const auto it=bbsc_checkpoint_accepted.find(lamp.actor);it!=bbsc_checkpoint_accepted.end())
                SendBbscSharedLamp(it->second);
            return;
        }
        AcceptBbscSharedLamp(lamp);
    }else{
        if(message.sender!=local.world.host || !lamp.revision)return;
        // An older canonical record may acknowledge our retried offer even
        // after a different player's later activation became current.
        if((lamp.actor==self && lamp.sequence>=bbsc_checkpoint_offer.sequence) ||
           (bbsc_checkpoint_offer.point && lamp.lit_ms>=bbsc_checkpoint_offer.lit_ms))bbsc_checkpoint_offer={};
        if(lamp.revision<bbsc_checkpoint.revision)return;
        if(lamp.revision==bbsc_checkpoint.revision &&
           (lamp.scope!=bbsc_checkpoint.scope || lamp.point!=bbsc_checkpoint.point ||
            lamp.actor!=bbsc_checkpoint.actor || lamp.sequence!=bbsc_checkpoint.sequence ||
            lamp.lit_ms!=bbsc_checkpoint.lit_ms))return;
        bbsc_checkpoint=lamp;
    }
}
bool ReadBbscSharedLampCheckpoint(s32& point,bool& here) {
    if(!BbscIndependentActive())return false;
    World::Presence local;{std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;}
    BindBbscSharedLamp(local.world);
    if(!bbsc_checkpoint.revision || !ValidBbscSharedLamp(bbsc_checkpoint))return false;
    // Arrival at a different lamp remains authoritative until a later actual
    // ignition. Replayed/delayed canonical packets keep their activation date.
    if(bbsc_native_lamp_selected_ms && bbsc_checkpoint.lit_ms<=bbsc_native_lamp_selected_ms)return false;
    // A visitor has already lit and written its own native checkpoint before
    // the host acknowledgement arrives. Do not revive at the older canonical one.
    if(bbsc_checkpoint_offer.point && bbsc_checkpoint_offer.lit_ms>bbsc_checkpoint.lit_ms)return false;
    point=bbsc_checkpoint.point;
    // Residency is insufficient, including adjacent ordinary maps. Dungeon
    // point IDs additionally require the exact mounted ritual, not just m29.
    const u32 map=GetCurrentPackedMap();
    here=bbsc_checkpoint.scope==World::ScopeOf(local) &&
        bbsc_checkpoint.scope.map==(Chalice::IsMap(map)?0x1D000000u:map) &&
        (!Chalice::IsMap(map) || (BbscChaliceArrivalReady(map) && !BbscChaliceNeedsLoad(map)));
    return true;
}
bool RequestBbscSharedLampReload() {
    s32 point=0;bool here=false;
    if(bbsc_checkpoint_fallback || !BbscIndependentTravelAllowed() ||
       !ReadBbscSharedLampCheckpoint(point,here))return false;
    if(!bbsc_checkpoint_reload.point){
        // Freeze this death's target. A lamp lit during its load is for the
        // next death, and cannot redirect an already prepared native load.
        bbsc_checkpoint_reload=bbsc_checkpoint;bbsc_checkpoint_reload_since=SteadyNowMs();
        bbsc_checkpoint_reload_load=bbsc_load_generation.load();
    }
    return true;
}
void TickBbscSharedLampCheckpoint() {
    World::Presence local;{std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;}
    BindBbscSharedLamp(local.world);
    if(!BbscIndependentTravelAllowed() || (GetSessionState()!=3 && GetSessionState()!=6)){
        bbsc_checkpoint_reload={};return;
    }
    const s64 now=SteadyNowMs();
    // Seed a party with its host's existing checkpoint once. Joining guests'
    // personal progress and subsequent lamp travel must never reseed it.
    const u64 global=GetGlobalState();
    if(!ReadablePointer(global,0x1530) || ReadValue<u8>(global,8))return;
    if(BbscMod::RegisterOwnId()==local.world.host && !bbsc_checkpoint.revision){
        const s32 point=ReadValue<s32>(global,0x1528);
        World::Scope scope=World::ScopeOf(local);
        if(!Chalice::IsMap(BbscLampPointMap(point)))scope={local.world,BbscLampPointMap(point),{},0};
        BbscSharedLamp seed{scope,point,local.world.host,++bbsc_checkpoint_sequence,0};
        if(ValidBbscSharedLamp(seed))AcceptBbscSharedLamp(seed);
    }
    if(now-bbsc_checkpoint_sent>=500){
        bbsc_checkpoint_sent=now;
        if(BbscMod::RegisterOwnId()==local.world.host && bbsc_checkpoint.revision && ValidBbscSharedLamp(bbsc_checkpoint))
            SendBbscSharedLamp(bbsc_checkpoint);
        else if(bbsc_checkpoint_offer.point && ValidBbscSharedLamp(bbsc_checkpoint_offer))SendBbscSharedLamp(bbsc_checkpoint_offer);
    }
    if(!bbsc_checkpoint_reload.point)return;
    if(bbsc_checkpoint_reload_load!=bbsc_load_generation.load()) {bbsc_checkpoint_reload={};return;}
    const auto target=bbsc_checkpoint_reload;
    if(!ValidBbscSharedLamp(target) || now-bbsc_checkpoint_reload_since>30000){
        bbsc_checkpoint_reload={};bbsc_checkpoint_fallback=true;
        RequestBbscDeathReload("shared lamp destination unavailable");bbsc_checkpoint_fallback=false;return;
    }
    if(!BeginBbscSharedLampLoad(target.scope,target.point))return;
    bbsc_checkpoint_reload={};
}
