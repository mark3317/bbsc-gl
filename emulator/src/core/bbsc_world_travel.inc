// SPDX-License-Identifier: GPL-2.0-or-later
#ifdef BBSC_MOD
s32 bbsc_world_travel_point=0,bbsc_world_travel_layer=0;
u32 bbsc_world_travel_flag=0;
s32 bbsc_world_travel_altar_pending=-1;
s64 bbsc_world_travel_since=0,bbsc_world_travel_request_sent=0;
bool bbsc_world_travel_inflight=false,bbsc_world_travel_saw_load=false;
bool bbsc_world_travel_native_armed=false;
u32 bbsc_world_travel_load=0;
World::WorldId bbsc_world_travel_world{};
std::atomic<u32> bbsc_world_travel_talk{0};
std::atomic<s64> bbsc_world_travel_talk_seen{0};
alignas(16) std::array<u8,0x100> bbsc_world_live_talker{};
alignas(16) std::array<u64,8> bbsc_world_live_talk{};
alignas(16) std::array<u8,0x88> bbsc_world_bonfire_phase{};
alignas(16) std::array<u8,0xC0> bbsc_world_lamp_command{};
thread_local s32 bbsc_world_esd_function=-1;
thread_local u64 bbsc_world_esd_actor=0;
thread_local u32 bbsc_world_esd_talk=0;
struct BbscWorldTalkRecord {u64 condition=0;u32 generation=0;};
std::map<u64,BbscWorldTalkRecord> bbsc_world_talk_records;
thread_local u32 bbsc_world_command_talk=0;
thread_local u64 bbsc_world_command_actor=0;
thread_local s64 bbsc_world_command_seen=0;

void NoteBbscWorldTalkRecord(u64 condition,u64 executor) {
    if(!executor || !ReadablePointer(condition,0x30) ||
       ReadValue<u64>(condition,0)!=image_base+TalkConditionVtableOffset)return;
    const u32 generation=bbsc_load_generation.load();
    static u32 bound=0;if(bound!=generation){bound=generation;bbsc_world_talk_records.clear();}
    if(bbsc_world_talk_records.size()<512 || bbsc_world_talk_records.contains(executor))
        bbsc_world_talk_records[executor]={condition,generation};
}

bool BbscWorldTravelActorAllowed() {
    // A lamp/headstone/altar has its OWN native actor; it is not PlayerIns.
    // Only a resident remote PLAYER copy must not issue our local journey.
    return bbsc_world_esd_actor && !BbscRegisterRemotePlayer(bbsc_world_esd_actor);
}

bool BbscWorldTravelInFlight(){return bbsc_world_travel_inflight;}
bool BbscWorldTalkAllowed(u32 talk);
bool BbscWorldTravelFlag(u32 flag) {
    return (flag>=70000200 && flag<70000210) ||
        (flag>=72100420 && flag<72100427) || (flag>=72100300 && flag<72100310) ||
        std::ranges::any_of(LampTravel::Returns,[&](const auto& p){return p.flag==flag;});
}
void PS4_SYSV_ABI BbscWorldLampCommandRange(u64,const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscIndependentTravelAllowed() || GetSessionState()!=6 ||
       !BbscWorldTravelFlag(static_cast<u32>(regs->r15)) || !bbsc_world_command_actor ||
       BbscRegisterRemotePlayer(bbsc_world_command_actor) || !BbscWorldTalkAllowed(bbsc_world_command_talk))return;
    // c1_11 checks its executor's allowed flag range BEFORE SetFlag. A visitor's
    // map-local executor must be allowed to reach our local travel interceptor.
    const_cast<GuestRegisterSnapshot*>(regs)->rax=reinterpret_cast<u64>(bbsc_world_lamp_command.data());
}
bool BbscWorldTalkAllowed(u32 talk) {
    if(!BbscIndependentTravelAllowed() || !BbscWorldSceneReady() || GetSessionState()!=6 || !BbscOwnOpeningDone())return false;
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
    bbsc_world_command_talk=0;bbsc_world_command_actor=0;bbsc_world_command_seen=0;
    if(!regs)return;
    const auto it=bbsc_world_talk_records.find(regs->r14);
    if(it!=bbsc_world_talk_records.end() && it->second.generation==bbsc_load_generation.load()) {
        const u64 p=it->second.condition;
        if(ReadablePointer(p,0x30) && ReadValue<u64>(p,0)==image_base+TalkConditionVtableOffset){
            bbsc_world_command_talk=ReadValue<u32>(p,0x10);bbsc_world_command_actor=ReadValue<u64>(p,0x18);
            bbsc_world_command_seen=SteadyNowMs();
        }
    }
    if(!regs || GetSessionState()!=6 || !BbscIndependentTravelAllowed() ||
       !bbsc_world_command_actor || BbscRegisterRemotePlayer(bbsc_world_command_actor))return;
    const u32 talk=bbsc_world_command_talk;
    if(talk<210050 || talk>210110 || (talk-210050)%10)return;
    auto* r=const_cast<GuestRegisterSnapshot*>(regs);
    if(r->rax!=78 && r->rax!=79)return;
    // Original t210050 uses78; all six ordinary altars use79 EVEN WHEN
    // occupied. Both scripts already build the layer choices with c1_19.
    // Native headstone41 opens those choices without ritual-edit actions.
    r->rax=BbscWorldTalkAllowed(talk)?41:88;
    BBSC_TIMELINE("TRAVEL","guest altar menu talk={} slot={} command={} occupied={}",
        talk,(talk-210050)/10,r->rax,bbsc_world_catalog_ready.load() && bbsc_world_altars[(talk-210050)/10].entry.occupied);
}
void PS4_SYSV_ABI BbscWorldBonfirePhase(u64,const GuestRegisterSnapshot* regs){
    if(regs && bbsc_world_travel_inflight &&
       bbsc_world_travel_point>0)
        const_cast<GuestRegisterSnapshot*>(regs)->rax=reinterpret_cast<u64>(bbsc_world_bonfire_phase.data());
}

bool QueueBbscWorldTravel(u32 flag,u8 value) {
    if(!value || !BbscIndependentTravelAllowed() || !BbscWorldTravelFlag(flag))return false;
    if(!BbscWorldSceneReady())return true;
    if(GetSessionState()!=3 && GetSessionState()!=6)return false;
    if(!bbsc_world_command_actor || BbscRegisterRemotePlayer(bbsc_world_command_actor))return true;
    const u32 talk=bbsc_world_command_talk;
    const bool device=std::ranges::find(LampTravel::Talks,talk)!=LampTravel::Talks.end() ||
        (talk>=210050 && talk<=210110 && (talk-210050)%10==0) || (talk/10000==29 && talk%1000<100);
    if(SteadyNowMs()-bbsc_world_command_seen>1000 || !device ||
       (GetSessionState()==6 && !BbscWorldTalkAllowed(talk)))return true;
    s32 point=0,slot=-1;
    if(flag>=70000200 && flag<70000210)point=2102950;
    for(const auto& destination:LampTravel::Returns)if(destination.flag==flag){point=destination.point;break;}
    // Native helper first sets the selected altar, waits for it to clear, THEN
    // sets the chosen layer. Do not start a load from the first half-command.
    if(flag>=72100420 && flag<72100427){
        const size_t chosen=flag-72100420;
        if((GetSessionState()==6 && !bbsc_world_catalog_ready.load()) || !bbsc_world_altars[chosen].entry.occupied)
            return GetSessionState()==6;
        bbsc_world_travel_altar_pending=chosen;
        bbsc_world_altar_visiting=chosen;bbsc_world_requested_mount=bbsc_world_altars[chosen].mount;
        // Native12107100 prepares the selected altar, plays its animation and
        // clears this flag. Only then does the ESD offer the layer request.
        return false;
    }
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
        if((GetSessionState()==6 && !bbsc_world_catalog_ready.load()) || !bbsc_world_altars[slot].entry.occupied ||
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
        bbsc_world_requested_mount.reset();bbsc_world_altar_visiting=-1;
    }
    bbsc_world_requested_scope=scope;
    bbsc_world_travel_world=scope.world;bbsc_world_travel_point=point;bbsc_world_travel_flag=flag;
    bbsc_world_travel_native_armed=false;
    bbsc_world_travel_since=SteadyNowMs();bbsc_world_travel_request_sent=0;
    BBSC_TIMELINE("TRAVEL","independent lamp request point={} map={:#x} ritual={}",point,scope.map,scope.ritual);
    return true;
}

void EnableBbscNativeTravelEvent(u64 instance) {
    if(!BbscIndependentTravelAllowed() || !ReadablePointer(instance,0xC0))return;
    static u64 generation=~u64{0};
    static std::map<u64,std::pair<u64,s64>> events;
    const u64 load=bbsc_world_native_load.load();
    if(generation!=load){generation=load;events.clear();}
    const u64 ref=ReadValue<u64>(instance,0xA8);
    auto it=events.find(instance);
    if(it==events.end() || it->second.first!=ref)
        it=events.insert_or_assign(instance,std::pair{ref,BbscEventIdOf(instance)}).first;
    const s64 event=it->second.second;
    if(event!=7200 && event!=12107000 && event!=12107100 && event!=12107200)return;
    // Original events remain native, but their local trip must not execute in
    // another room member's game. This is native SetNetworkSyncState(false).
    WriteValue<u8>(instance,0x78,0);
    const u64 instruction=ReadValue<u64>(instance,0xB0);
    if(!ReadablePointer(instruction,0x20) || ReadValue<s32>(instruction,0)!=1003 ||
       ReadValue<s32>(instruction,4)!=6 || ReadValue<u64>(instruction,8)!=4)return;
    const u64 file=ReadablePointer(ref,0x10)?ReadValue<u64>(ref,8):0;
    if(!ReadablePointer(file,0x80))return;
    const u64 args=file+ReadValue<u64>(file,0x78)+ReadValue<u64>(instruction,0x10);
    if(!ReadablePointer(args,4) || ReadValue<u32>(args,0)!=256)return;
    // Verified first EndIfClient has no parameter substitutions in these EVDs.
    // A native WaitFrames(0) lets this visitor run its own original travel.
    if(!HasMemoryAccess(instruction,8,MemoryProt::CpuWrite) || !HasMemoryAccess(args,4,MemoryProt::CpuWrite))return;
    WriteValue<u32>(args,0,0);WriteValue<s32>(instruction,0,1001);WriteValue<s32>(instruction,4,1);
    BBSC_TIMELINE("TRAVEL","native local travel event enabled event={}",event);
}

void BbscWorldNativeWarpBegin(const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscIndependentTravelAllowed() || !bbsc_world_travel_inflight || bbsc_world_travel_native_armed)return;
    bbsc_world_travel_native_armed=true;
    ArmBbscReinsertV8(); // native FirstSync begins with the stage request, never during its animation
    BBSC_TIMELINE("TRAVEL","native stage request point={} selected={} map={:#x}",static_cast<s32>(regs->rsi),
        bbsc_world_travel_point,bbsc_world_requested_scope?bbsc_world_requested_scope->map:0);
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
            bbsc_world_travel_flag=70000200;
            bbsc_world_requested_mount.reset();
            bbsc_world_requested_scope=World::Scope{world,0x15000000,{},0};
            bbsc_world_travel_world=world;bbsc_world_travel_since=SteadyNowMs();bbsc_world_travel_request_sent=0;
        }
    }
    if(!bbsc_world_travel_point && !bbsc_world_travel_inflight)return;
    if(!BbscIndependentTravelAllowed() || world!=bbsc_world_travel_world || (GetSessionState()!=6 && GetSessionState()!=3)){
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
    BbscWorldEnsureSeed(scope);
    if(!BbscWorldHasSnapshot(scope.map)){
        if(now-bbsc_world_travel_request_sent>=500){
            World::Control request;request.kind=World::ControlKind::Request;request.scope=scope;
            request.owner=BbscMod::RegisterOwnId();request.sequence=++bbsc_world_state_sequence;
            BbscWorldSend(request);bbsc_world_travel_request_sent=now;
        }
        return;
    }
    // Release the ORIGINAL local event. It owns the menu, animation, delay,
    // stage request and point selection; no synthesized summon/coordinate warp.
    if(Chalice::IsMap(scope.map) && !PrepareBbscChaliceLoad(scope.map))return;
    const u64 flagman=ReadValue<u64>(image_base+WorldFlagManPointerOffset,0);
    if(!flagman || !bbsc_world_travel_flag)return;
    bbsc_world_travel_inflight=true;bbsc_world_travel_saw_load=false;
    bbsc_world_travel_load=bbsc_load_generation.load();bbsc_world_travel_since=now;
    using Set=void PS4_SYSV_ABI (*)(u64,u32,u8);
    reinterpret_cast<Set>(image_base+0x013CFCC0)(flagman,bbsc_world_travel_flag,1);
    BBSC_TIMELINE("TRAVEL","native travel event released flag={} point={} map={:#x}",bbsc_world_travel_flag,bbsc_world_travel_point,scope.map);
}

void InstallBbscWorldTravel() {
    if(!bbsc_world_native_warp_hook.load()){
        LOG_ERROR(Debug,"BBSC native stage request hook unavailable; independent travel remains closed");return;
    }
    struct Site{u64 offset;std::vector<u8> bytes;GuestCodeHook hook;};
    const std::array sites{
        Site{0x0203C564,{0x08,0xC1,0x0F,0xB6,0xC1},BbscWorldLampMultiplayer},
        Site{0x0203B7FB,{0x49,0x8B,0x47,0x18,0x48,0x85,0xC0},BbscWorldLampTalker},
        Site{0x0203AD95,{0x89,0xC1,0x83,0xF8,0x3E},BbscWorldEsdFunction},
        Site{0x02040002,{0x89,0xC1,0x83,0xF8,0x57},BbscWorldAltarCommand},
        Site{0x0204232E,{0x8B,0x88,0xA0,0,0,0,0x83,0xF9,0xFF},BbscWorldLampCommandRange},
        Site{0x0203EECF,{0x41,0xC7,0x44,0x24,0x08,0x02,0,0,0},BbscWorldEsdResult},
        Site{0x0192997A,{0x83,0xB8,0x84,0,0,0,3},BbscWorldBonfirePhase}};
    for(const auto& site:sites)if(!ReadablePointer(image_base+site.offset,site.bytes.size()) ||
        std::memcmp(reinterpret_cast<const void*>(image_base+site.offset),site.bytes.data(),site.bytes.size())){
        LOG_ERROR(Debug,"BBSC independent travel: site {:#x} differs; guest lamps remain closed",site.offset);return;}
    // Preserve the host's old f52 behavior through the scoped hook rather than
    // globally patching every guest talk to pretend it is a solo game.
    bbsc_world_live_talk[3]=reinterpret_cast<u64>(bbsc_world_live_talker.data());
    std::memset(bbsc_world_lamp_command.data()+0xA0,0xFF,8);
    for(const auto& site:sites)if(!InstallGuestCodeHook(reinterpret_cast<void*>(image_base+site.offset),site.bytes,0,site.hook))return;
    bbsc_independent_travel_hooks=true;
    LOG_INFO(Debug,"BBSC independent travel: scoped lamp/talker/bonfire hooks installed");
}
#endif
