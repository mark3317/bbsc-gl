// SPDX-License-Identifier: GPL-2.0-or-later
#ifdef BBSC_MOD
s32 bbsc_world_travel_point=0,bbsc_world_travel_layer=0;
s32 bbsc_world_travel_altar_pending=-1;
s64 bbsc_world_travel_since=0,bbsc_world_travel_request_sent=0;
bool bbsc_world_travel_inflight=false,bbsc_world_travel_saw_load=false;
u32 bbsc_world_travel_load=0;
World::WorldId bbsc_world_travel_world{};
std::atomic<u32> bbsc_world_travel_talk{0};
std::atomic<s64> bbsc_world_travel_talk_seen{0};
alignas(16) std::array<u8,0x100> bbsc_world_live_talker{};
alignas(16) std::array<u64,8> bbsc_world_live_talk{};
alignas(16) std::array<u8,0x88> bbsc_world_bonfire_phase{};
thread_local s32 bbsc_world_esd_function=-1;
thread_local u64 bbsc_world_esd_actor=0;
thread_local u32 bbsc_world_esd_talk=0;

bool BbscWorldTravelActorAllowed() {
    // A lamp/headstone/altar has its OWN native actor; it is not PlayerIns.
    // Only a resident remote PLAYER copy must not issue our local journey.
    return bbsc_world_esd_actor && !BbscRegisterRemotePlayer(bbsc_world_esd_actor);
}

bool BbscWorldTravelInFlight(){return bbsc_world_travel_inflight;}
bool BbscWorldTalkAllowed(u32 talk) {
    if(!BbscIndependentTravelAllowed() || GetSessionState()!=6 || !BbscOwnOpeningDone())return false;
    bool allow=std::ranges::find(LampTravel::Talks,talk)!=LampTravel::Talks.end();
    if(talk>=210050 && talk<=210110 && (talk-210050)%10==0){
        const size_t slot=(talk-210050)/10;
        allow=bbsc_world_catalog_ready.load() && bbsc_world_altars[slot].entry.occupied;
    }
    if(talk/10000==29 && talk%1000<100) allow=true; // native dungeon lamps
    if(allow){bbsc_world_travel_talk=talk;bbsc_world_travel_talk_seen=SteadyNowMs();}
    return allow;
}
void PS4_SYSV_ABI BbscWorldLampMultiplayer(u64,const GuestRegisterSnapshot* regs) {
    if(!regs)return;
    const bool host=GetSessionState()==3 && GetLocalPlayerType()==0 &&
        Core::Bbsc::SwitchEnabled("SHADPS4_BBSC_LAMP");
    const bool guest=BbscWorldTravelActorAllowed() && BbscWorldTalkAllowed(bbsc_world_esd_talk);
    if(guest){static std::atomic<bool> logged{false};if(!logged.exchange(true))
        BBSC_TIMELINE("TRAVEL","guest lamp gate admitted talk={} actor={}",bbsc_world_esd_talk,
            bbsc_world_esd_actor==GetLocalPlayerCharacter()?"player":"device");}
    if(host || guest){auto* r=const_cast<GuestRegisterSnapshot*>(regs);r->rax&=~u64{0xFF};r->rcx&=~u64{0xFF};}
}
void PS4_SYSV_ABI BbscWorldLampTalker(u64,const GuestRegisterSnapshot* regs) {
    // The dispatcher saved its evaluator (RSI) in R15 and its result (RDI)
    // in R12. Use the entry snapshot: the switch also reuses R15 as scratch.
    if(!regs || !BbscWorldTravelActorAllowed())return;
    if(BbscWorldTalkAllowed(bbsc_world_esd_talk))
        const_cast<GuestRegisterSnapshot*>(regs)->r15=reinterpret_cast<u64>(bbsc_world_live_talk.data());
}
void PS4_SYSV_ABI BbscWorldEsdFunction(u64,const GuestRegisterSnapshot* regs){
    bbsc_world_esd_function=regs?static_cast<s32>(regs->rax):-1;
    const u64 evaluator=regs?regs->r15:0;
    const bool valid=ReadablePointer(evaluator,0x30) && ReadValue<u64>(evaluator,0)==image_base+TalkConditionVtableOffset;
    bbsc_world_esd_actor=valid?ReadValue<u64>(evaluator,0x18):0;
    bbsc_world_esd_talk=valid?ReadValue<u32>(evaluator,0x10):0;
}
void PS4_SYSV_ABI BbscWorldEsdResult(u64,const GuestRegisterSnapshot* regs){
    if(!regs || (bbsc_world_esd_function!=26 && bbsc_world_esd_function!=47) || !BbscIndependentTravelAllowed())return;
    const u32 talk=bbsc_world_esd_talk;
    // The altar's sole f47 is the missing Ritual Blood Workshop Tool check.
    // A visitor uses the occupied host altar, without receiving a personal item.
    if(bbsc_world_esd_function==47 && !(talk>=210050 && talk<=210110 && (talk-210050)%10==0))return;
    if(BbscWorldTravelActorAllowed() && BbscWorldTalkAllowed(talk))
        const_cast<GuestRegisterSnapshot*>(regs)->rax&=~u64{0xFF};
}
void PS4_SYSV_ABI BbscWorldAltarCommand(u64,const GuestRegisterSnapshot* regs){
    if(!regs || GetSessionState()!=6 || !BbscIndependentTravelAllowed() ||
       !BbscWorldTravelActorAllowed())return;
    const u32 talk=bbsc_world_travel_talk.load();
    if(talk<210050 || talk>210110 || (talk-210050)%10 ||
       SteadyNowMs()-bbsc_world_travel_talk_seen.load()>1000 || !BbscWorldTalkAllowed(talk))return;
    // c1_78 opens the special chalice menu. Reuse c1_41, the original headstone
    // list, with the ten native layer entries already added by this ESD. It has
    // no ritual creation/removal/inventory actions. c1_79 (empty-altar ritual UI)
    // is never available to visitors. The host keeps both original commands.
    auto* r=const_cast<GuestRegisterSnapshot*>(regs);
    if(r->rax==78)r->rax=41;
    else if(r->rax==79)r->rax=88; // outside the native dispatcher range: no-op
}
void PS4_SYSV_ABI BbscWorldBonfirePhase(u64,const GuestRegisterSnapshot* regs){
    if(regs && bbsc_world_travel_inflight && GetSessionState()==6 &&
       bbsc_world_travel_point>=2902950 && bbsc_world_travel_point<2902960)
        const_cast<GuestRegisterSnapshot*>(regs)->rax=reinterpret_cast<u64>(bbsc_world_bonfire_phase.data());
}

bool QueueBbscWorldTravel(u32 flag,u8 value) {
    if(!value || !BbscIndependentTravelAllowed())return false;
    if(GetSessionState()==3)return false;
    if(GetSessionState()!=6 || !BbscWorldTravelActorAllowed())return false;
    const u32 talk=bbsc_world_travel_talk.load();
    if(SteadyNowMs()-bbsc_world_travel_talk_seen.load()>1000 || !BbscWorldTalkAllowed(talk))return false;
    s32 point=0,slot=-1;
    if(flag>=70000200 && flag<70000210)point=2102950;
    for(const auto& destination:LampTravel::Returns)if(destination.flag==flag){point=destination.point;break;}
    // Native helper first sets the selected altar, waits for it to clear, THEN
    // sets the chosen layer. Do not start a load from the first half-command.
    if(flag>=72100420 && flag<72100427){bbsc_world_travel_altar_pending=flag-72100420;return true;}
    if(flag>=72100300 && flag<72100310){
        bbsc_world_travel_layer=flag-72100300;slot=bbsc_world_travel_altar_pending;
        bbsc_world_travel_altar_pending=-1;
        if(slot<0)return true;
        point=2902950+bbsc_world_travel_layer;
    }
    if(!point)return false;
    // Consume duplicates/rejected local travel commands as well. They must not
    // replicate into the host's native event script and move another player.
    if(bbsc_world_travel_point || bbsc_world_travel_inflight || GetCharacterHp(GetLocalPlayerCharacter())<=0)return true;
    World::Scope scope;
    {std::scoped_lock lock{bbsc_world_presence_mutex};scope.world=bbsc_world_presence_local.world;}
    if(slot>=0){
        if(!bbsc_world_catalog_ready.load() || !bbsc_world_altars[slot].entry.occupied ||
           bbsc_world_travel_layer<0 || bbsc_world_travel_layer>9)return true;
        // Hall is unconditional; subsequent layers use the original native
        // lamp flags, which the guest menu already reads from the host view.
        if(bbsc_world_travel_layer && !BbscEventFlag(12907810+bbsc_world_travel_layer*20))return true;
        bbsc_world_altar_visiting=slot;
        bbsc_world_requested_mount=bbsc_world_altars[slot].mount;
        scope.map=0x1D000000;scope.dungeon=bbsc_world_requested_mount->key;
        scope.ritual=bbsc_world_altars[slot].entry.ritual;
    }else{
        const auto it=std::ranges::find(LampPoints,point,&LampPoint::warp_point);
        if(it==LampPoints.end())return true;scope.map=it->packed_map;
    }
    bbsc_world_requested_scope=scope;
    bbsc_world_travel_world=scope.world;bbsc_world_travel_point=point;
    bbsc_world_travel_since=SteadyNowMs();bbsc_world_travel_request_sent=0;
    BBSC_TIMELINE("TRAVEL","independent lamp request point={} map={:#x} ritual={}",point,scope.map,scope.ritual);
    return true;
}

void TickBbscWorldTravel() {
    World::WorldId world;{std::scoped_lock lock{bbsc_world_presence_mutex};world=bbsc_world_presence_local.world;}
    static World::WorldId bound{};
    if(bound!=world){bound=world;bbsc_world_travel_altar_pending=-1;}
    if(BbscIndependentTravelAllowed() && GetSessionState()==6 && bbsc_world_catalog_ready.load() &&
       bbsc_world_requested_mount && !bbsc_world_travel_inflight) {
        const s32 slot=bbsc_world_altar_visiting;
        const bool intact=slot>=0 && slot<7 && bbsc_world_altars[slot].entry.occupied &&
            bbsc_world_altars[slot].entry.ritual==bbsc_world_requested_mount->revision &&
            bbsc_world_altars[slot].mount.key==bbsc_world_requested_mount->key;
        if(!intact){
            // A removed/replaced host ritual can no longer accept progress.
            // Finish an already running load, then return its visitor to Dream.
            bbsc_world_travel_point=Chalice::IsMap(GetCurrentPackedMap())?2102950:0;
            bbsc_world_requested_mount.reset();
            bbsc_world_requested_scope=World::Scope{world,0x15000000,{},0};
            bbsc_world_travel_world=world;bbsc_world_travel_since=SteadyNowMs();bbsc_world_travel_request_sent=0;
        }
    }
    if(!bbsc_world_travel_point && !bbsc_world_travel_inflight)return;
    if(!BbscIndependentTravelAllowed() || world!=bbsc_world_travel_world || GetSessionState()!=6){
        bbsc_world_travel_point=0;bbsc_world_travel_inflight=false;return;
    }
    const s64 now=SteadyNowMs();const u64 global=GetGlobalState();
    if(!ReadablePointer(global,0x1598))return;
    const bool loading=ReadValue<u8>(global,8)!=0 || bbsc_world_load_pending.load() || bbsc_reload_finish_pending.load();
    if(bbsc_world_travel_inflight){
        bbsc_world_travel_saw_load|=loading || bbsc_load_generation.load()!=bbsc_world_travel_load;
        if(bbsc_world_travel_saw_load && !loading && GetLocalPlayerCharacter() && GetCharacterHp(GetLocalPlayerCharacter())>0){
            bbsc_world_travel_inflight=false;bbsc_world_travel_point=0;
            ApplyBbscIndependentAtLoad(GetCurrentPackedMap());
            BBSC_TIMELINE("TRAVEL","independent arrival map={:#x}",GetCurrentPackedMap());
        }else if(now-bbsc_world_travel_since>90000){
            bbsc_world_travel_inflight=false;bbsc_world_travel_point=0;
            LOG_ERROR(Debug,"BBSC independent travel timed out; native leave remains available");
        }
        return;
    }
    if(now-bbsc_world_travel_since>30000 || GetCharacterHp(GetLocalPlayerCharacter())<=0){bbsc_world_travel_point=0;return;}
    if(loading || !bbsc_world_requested_scope)return;
    const auto scope=*bbsc_world_requested_scope;
    if(!BbscWorldHasSnapshot(scope.map)){
        if(now-bbsc_world_travel_request_sent>=500){
            World::Control request;request.kind=World::ControlKind::Request;request.scope=scope;
            request.owner=BbscMod::RegisterOwnId();request.sequence=++bbsc_world_state_sequence;
            BbscWorldSend(request);bbsc_world_travel_request_sent=now;
        }
        return;
    }
    ApplyBbscIndependentAtLoad(scope.map);
    ApplyBbscGuestLootView(scope.map,"independent lamp travel");
    if(scope.map==BbscDreamStateMap)ApplyBbscHostDreamState("independent lamp travel");
    else RestoreBbscOwnDreamState("independent lamp travel");
    bbsc_world_travel_inflight=true;bbsc_world_travel_saw_load=false;
    bbsc_world_travel_load=bbsc_load_generation.load();bbsc_world_travel_since=now;
    bbsc_independent_role=0;
    ArmBbscReinsertV8();
    WriteValue<s32>(global,0x1528,bbsc_world_travel_point);
    reinterpret_cast<void PS4_SYSV_ABI (*)(s32)>(image_base+BbscQuitCloseMenusOffset)(3);
    if(Chalice::IsMap(scope.map)){
        if(!PrepareBbscChaliceLoad(scope.map)){bbsc_world_travel_inflight=false;return;}
        const u64 rules=ReadValue<u64>(image_base+SummonSessionRulesPointerOffset,0);
        if(!HasMemoryAccess(rules+0x84,4,MemoryProt::CpuWrite)){bbsc_world_travel_inflight=false;return;}
        WriteValue<s32>(rules,0x84,3);WriteValue<u8>(global,0x1520,0);
        WriteValue<u32>(global,0x14C4,scope.map);
        reinterpret_cast<void PS4_SYSV_ABI (*)(u64,s32)>(image_base+0x0132E050)(0,bbsc_world_travel_point);
    }else{
        const auto it=std::ranges::find(LampPoints,bbsc_world_travel_point,&LampPoint::warp_point);
        if(it==LampPoints.end()){bbsc_world_travel_inflight=false;return;}
        SummonPlacementDescriptor to{};to.packed_region=it->packed_map;
        to.x=it->x;to.y=it->y;to.z=it->z;to.heading=it->heading;
        if(!RequestBbscSessionWarp(global,to,"independent lamp"))bbsc_world_travel_inflight=false;
    }
}

void InstallBbscWorldTravel() {
    struct Site{u64 offset;std::vector<u8> bytes;GuestCodeHook hook;};
    const std::array sites{
        Site{0x0203C564,{0x08,0xC1,0x0F,0xB6,0xC1},BbscWorldLampMultiplayer},
        Site{0x0203B7FB,{0x49,0x8B,0x47,0x18,0x48,0x85,0xC0},BbscWorldLampTalker},
        Site{0x0203AD95,{0x89,0xC1,0x83,0xF8,0x3E},BbscWorldEsdFunction},
        Site{0x02040002,{0x89,0xC1,0x83,0xF8,0x57},BbscWorldAltarCommand},
        Site{0x0203EECF,{0x41,0xC7,0x44,0x24,0x08,0x02,0,0,0},BbscWorldEsdResult},
        Site{0x0192997A,{0x83,0xB8,0x84,0,0,0,3},BbscWorldBonfirePhase}};
    for(const auto& site:sites)if(!ReadablePointer(image_base+site.offset,site.bytes.size()) ||
        std::memcmp(reinterpret_cast<const void*>(image_base+site.offset),site.bytes.data(),site.bytes.size())){
        LOG_ERROR(Debug,"BBSC independent travel: site {:#x} differs; guest lamps remain closed",site.offset);return;}
    // Preserve the host's old f52 behavior through the scoped hook rather than
    // globally patching every guest talk to pretend it is a solo game.
    bbsc_world_live_talk[3]=reinterpret_cast<u64>(bbsc_world_live_talker.data());
    for(const auto& site:sites)if(!InstallGuestCodeHook(reinterpret_cast<void*>(image_base+site.offset),site.bytes,0,site.hook))return;
    bbsc_independent_travel_hooks=true;
    LOG_INFO(Debug,"BBSC independent travel: scoped lamp/talker/bonfire hooks installed");
}
#endif
