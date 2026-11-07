// SPDX-License-Identifier: GPL-2.0-or-later
#ifdef BBSC_MOD
s32 bbsc_world_travel_point=0,bbsc_world_travel_layer=0;
u32 bbsc_world_travel_flag=0;
s32 bbsc_world_travel_altar_pending=-1;
s64 bbsc_world_travel_since=0,bbsc_world_travel_request_sent=0;
bool bbsc_world_travel_inflight=false,bbsc_world_travel_saw_load=false;
bool bbsc_world_travel_native_armed=false;
u32 bbsc_world_travel_departure_load=0,bbsc_world_travel_altar_load=0;
World::WorldId bbsc_world_travel_departure_world{},bbsc_world_travel_altar_world{};
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
thread_local u64 bbsc_world_workshop_frame=0;
struct BbscWorldTalkRecord {u64 condition=0;u32 generation=0;};
std::map<u64,BbscWorldTalkRecord> bbsc_world_talk_records;
thread_local u32 bbsc_world_command_talk=0;
thread_local u64 bbsc_world_command_actor=0;
thread_local s64 bbsc_world_command_seen=0;
// Authorization for the asynchronous native79 callbacks, separate from the
// last ESD command (other devices keep evaluating while this menu is open).
struct BbscGuestAltarMenu {
    World::WorldId world{};u32 load=0;s32 slot=-1;u64 ritual=0;
};
BbscGuestAltarMenu bbsc_world_guest_altar_menu;
u8 bbsc_world_altar_remove_skip=0;
const struct BbscAltarMenuState {std::array<u8,0x364> padding{};s32 state=4;} bbsc_world_altar_menu_state;
static_assert(offsetof(BbscAltarMenuState,state)==0x364);

bool BbscWorldGuestAltarMenuContext() {
    const auto& menu=bbsc_world_guest_altar_menu;
    if(GetSessionState()!=6 || !BbscIndependentTravelAllowed() || GetCurrentPackedMap()!=0x15000000 ||
       menu.slot<0 || menu.slot>=7 || menu.load!=bbsc_load_generation.load())return false;
    {std::scoped_lock lock{bbsc_world_presence_mutex};if(menu.world!=bbsc_world_presence_local.world)return false;}
    return true;
}
bool BbscWorldGuestAltarMenuActive() {
    if(!BbscWorldGuestAltarMenuContext() || !bbsc_world_catalog_ready.load())return false;
    const auto& menu=bbsc_world_guest_altar_menu;const auto& entry=bbsc_world_altars[menu.slot].entry;
    return entry.occupied && entry.ritual==menu.ritual;
}

// Native promises retain a raw ritual-helper pointer. Give them a separately
// constructed native helper, not the visitor's personal helper or a memcpy of
// its owning pointers. Seven stable addresses live until process exit, including
// across map loads; native async callbacks may outlive the ESD command.
struct BbscGuestAltarView {
    alignas(16) std::array<u8,0x270> helper{};
    World::WorldId world{};u32 load=0;
    World::AltarRecord record{};
    bool constructed=false,ready=false;
};
std::array<BbscGuestAltarView,7> bbsc_world_altar_views;
bool bbsc_world_altar_view_refreshing=false;

u64 BbscWorldGuestAltarHelper(s32 slot) {
    if(!BbscWorldGuestAltarMenuActive() || slot!=bbsc_world_guest_altar_menu.slot ||
       bbsc_world_altar_view_refreshing)return 0;
    auto& view=bbsc_world_altar_views[slot];
    const auto& menu=bbsc_world_guest_altar_menu;
    const auto& altar=bbsc_world_altars[slot];
    if(!view.ready || view.world!=menu.world || view.load!=menu.load || view.record!=altar.entry.record){
        // Atomically install all host backing groups BEFORE the game's own
        // decoder reads channel/parts/glyph/ritual metadata from this slot.
        if(!BbscWorldApplyAltars(GetCurrentPackedMap()))return 0;
        bbsc_world_altar_view_refreshing=true;
        using Construct=void PS4_SYSV_ABI (*)(void*,const s32*);
        using Update=void PS4_SYSV_ABI (*)(void*,const void*);
        if(!view.constructed){
            reinterpret_cast<Construct>(image_base+0x01AA3110)(view.helper.data(),&slot);
            view.constructed=true;
        }
        const std::array<u8,16> frame{}; // native delta at +8; no timer advance
        reinterpret_cast<Update>(image_base+0x01AA6860)(view.helper.data(),frame.data());
        bbsc_world_altar_view_refreshing=false;
        view.world=menu.world;view.load=menu.load;view.record=altar.entry.record;view.ready=true;
        BBSC_TIMELINE("TRAVEL","guest native altar host helper slot={} host_channel={:#x} decoded_channel={:#x}",
            slot,altar.mount.key.channel,ReadValue<u64>(reinterpret_cast<u64>(view.helper.data()),0xD8));
    }
    return reinterpret_cast<u64>(view.helper.data());
}

void PS4_SYSV_ABI BbscWorldAltarHelper(u64 capture,const GuestRegisterSnapshot* regs) {
    if(!regs)return;
    // 01B661CF: command79 captures RCX into the promise. 01AC3EE7:
    // selected-helper accessor returns RAX (RBX still holds the selected slot).
    // 01B77227: the visible ritual panel bypasses that accessor and puts the
    // PERSONAL helper directly in RSI before 01C50250 -> 01C506C0 renders it.
    // Neither path replaces a personal altar/helper/channel pointer.
    if(regs->rbx>=7)return;
    if(const u64 helper=BbscWorldGuestAltarHelper(static_cast<s32>(regs->rbx))){
        auto* r=const_cast<GuestRegisterSnapshot*>(regs);
        if(capture==2)r->rsi=helper;
        else if(capture)r->rcx=helper;else r->rax=helper;
    }
}

void PS4_SYSV_ABI BbscWorldAltarUpdate(u64,const GuestRegisterSnapshot* regs) {
    if(!regs || bbsc_world_altar_view_refreshing || !BbscWorldGuestAltarMenuActive() ||
       !ReadablePointer(regs->rdi,0xCC))return;
    const s32 slot=ReadValue<s32>(regs->rdi,0xC8);
    if(const u64 helper=BbscWorldGuestAltarHelper(slot)) {
        // The helper owns native asynchronous metadata/cache work. A single
        // zero-delta decode when the record changes cannot advance that work.
        // Route the original native update to the same helper the menu borrows,
        // preserving its real frame/delta and every original update instruction.
        const_cast<GuestRegisterSnapshot*>(regs)->rdi=helper;
    }
}

void PS4_SYSV_ABI BbscWorldAltarMenuBranch(u64 continuation,const GuestRegisterSnapshot* regs) {
    // Project immediately before native layer rows read their lamp conditions,
    // after the selected helper has finished preparing its ritual.
    if(regs && !continuation && BbscIndependentTravelAllowed() && GetCurrentPackedMap()==BbscDreamStateMap)
        BbscWorldSelectLampMenu(static_cast<s32>(regs->r13));
    if(!regs || !BbscWorldGuestAltarMenuContext())return;
    // Native79 selects its occupied/empty screen from the PERSONAL cached
    // ritual state. Select its EXISTING layer screen without changing that cache.
    // R13 is the selected altar at01B75353. The continuation at01B74F4B must
    // not reopen the ritual/search screen after the native layer result.
    BBSC_TIMELINE("TRAVEL","guest native altar {} slot={} native_slot={} host_channel={:#x} personal_state={} current={}",
        continuation?"layer result":"layer menu",bbsc_world_guest_altar_menu.slot,
        continuation?-1:static_cast<s32>(regs->r13),
        bbsc_world_altars[bbsc_world_guest_altar_menu.slot].mount.key.channel,
        ReadablePointer(regs->rax,0x368)?ReadValue<s32>(regs->rax,0x364):-1,BbscWorldGuestAltarMenuActive());
    // Only the native CMP reads this stand-in. Both selected branches overwrite
    // RAX before using it again. Execute the original CMP/Jcc so native flags
    // and stack control flow remain intact; never modify the personal object.
    const_cast<GuestRegisterSnapshot*>(regs)->rax=reinterpret_cast<u64>(&bbsc_world_altar_menu_state);
}

void PS4_SYSV_ABI BbscWorldAltarMenuItem(u64,const GuestRegisterSnapshot* regs) {
    bbsc_world_altar_remove_skip=0;
    if(!regs || !ReadablePointer(regs->rsp,8) || ReadValue<u64>(regs->rsp,0)!=image_base+0x01B67A7F ||
       !BbscWorldGuestAltarMenuContext())return;
    // Function ENTRY of native list::Add. Only the layer screen's native
    // "Remove Chalice" append is omitted; its caller still destroys temporaries.
    // Add returns its builder (RDI). Never RET from the caller's live frame.
    const_cast<GuestRegisterSnapshot*>(regs)->rax=regs->rdi;
    bbsc_world_altar_remove_skip=1;
    BBSC_TIMELINE("TRAVEL","guest native altar removal omitted slot={}",bbsc_world_guest_altar_menu.slot);
}

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
bool BbscWorldLampTalk(u32 talk) {
    return std::ranges::find(LampTravel::Talks,talk)!=LampTravel::Talks.end() ||
        std::ranges::find(LampTravel::DungeonTalks,talk)!=LampTravel::DungeonTalks.end();
}
bool BbscWorldTravelFlag(u32 flag) {
    return LampTravel::IsTravelCommand(flag);
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
    if(!BbscIndependentTravelAllowed() || GetSessionState()!=6)return false;
    // Every original lamp is usable by a guest, including unlit dungeon lamps.
    // Story ownership/admission determines world state, not access to this UI.
    bool allow=BbscWorldLampTalk(talk);
    if(talk>=210050 && talk<=210110 && (talk-210050)%10==0){
        const size_t slot=(talk-210050)/10;
        allow=bbsc_world_catalog_ready.load() && bbsc_world_altars[slot].entry.occupied;
    }
    if(allow){bbsc_world_travel_talk=talk;bbsc_world_travel_talk_seen=SteadyNowMs();}
    return allow;
}
void PS4_SYSV_ABI BbscWorldLampMultiplayer(u64,const GuestRegisterSnapshot* regs) {
    if(!regs)return;
    const bool host=GetSessionState()==3 && GetLocalPlayerType()==0 &&
        Core::Bbsc::SwitchEnabled("SHADPS4_BBSC_LAMP");
    const bool guest=BbscWorldTravelActorAllowed() && BbscGuestDialogueAllowed(bbsc_world_esd_talk);
    if(guest){
        static thread_local u32 generation=~u32{0};
        static thread_local std::map<u32,bool> logged;
        const u32 load=bbsc_load_generation.load();
        if(generation!=load){generation=load;logged.clear();}
        if(logged.emplace(bbsc_world_esd_talk,true).second)
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
    bbsc_world_workshop_frame=0;
    bbsc_world_esd_function=regs?static_cast<s32>(regs->rax):-1;
    const u64 evaluator=regs?regs->r15:0;
    const bool valid=ReadablePointer(evaluator,0x30) && ReadValue<u64>(evaluator,0)==image_base+TalkConditionVtableOffset;
    bbsc_world_esd_actor=valid?ReadValue<u64>(evaluator,0x18):0;
    bbsc_world_esd_talk=valid?ReadValue<u32>(evaluator,0x10):0;
    if (regs && bbsc_world_esd_function == 47 && BbscWorkshopTalk(bbsc_world_esd_talk) &&
        bbsc_world_esd_actor && !BbscRegisterRemotePlayer(bbsc_world_esd_actor) &&
        GetCurrentPackedMap() == BbscDreamStateMap && BbscGuestInHostWorld() &&
        ReadablePointer(regs->r14, 8)) {
        const u64 vtable = ReadValue<u64>(regs->r14, 0);
        const u64 count = ReadablePointer(vtable, 0x20) ? ReadValue<u64>(vtable, 0x18) : 0;
        // Native203C354 reads the same count before constructing its variants.
        // A malformed/short call must never reuse stack slots from a previous f47.
        if (IsEbootCodeAddress(count)) {
            using Count = s32 PS4_SYSV_ABI (*)(u64);
            if (reinterpret_cast<Count>(count)(regs->r14) == 6)
                bbsc_world_workshop_frame = regs->rbp;
        }
    }
}
void PS4_SYSV_ABI BbscWorldEsdResult(u64,const GuestRegisterSnapshot* regs){
    if (regs && bbsc_world_esd_function == 26 && BbscWorldTravelActorAllowed() &&
        BbscGuestDialogueAllowed(bbsc_world_esd_talk)) {
        const_cast<GuestRegisterSnapshot*>(regs)->rax &= ~u64{0xFF};
        return;
    }
    if (regs && bbsc_world_esd_function == 47 && bbsc_world_workshop_frame &&
        regs->rbp == bbsc_world_workshop_frame &&
        BbscWorkshopToolResult(bbsc_world_esd_talk, regs->rbp)) {
        const_cast<GuestRegisterSnapshot*>(regs)->rax = (regs->rax & ~u64{0xFF}) | 1;
        return;
    }
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
    if(BbscIndependentTravelAllowed() && GetCurrentPackedMap()==BbscDreamStateMap &&
       bbsc_world_command_actor && !BbscRegisterRemotePlayer(bbsc_world_command_actor) &&
       bbsc_world_command_talk>=210050 && bbsc_world_command_talk<=210110 &&
       (bbsc_world_command_talk-210050)%10==0 && (regs->rax==73 || regs->rax==78 || regs->rax==79))
        BbscWorldSelectLampMenu((bbsc_world_command_talk-210050)/10);
    if(!regs || GetSessionState()!=6 || !BbscIndependentTravelAllowed() ||
       !bbsc_world_command_actor || BbscRegisterRemotePlayer(bbsc_world_command_actor))return;
    const u32 talk=bbsc_world_command_talk;
    if(talk<210050 || talk>210110 || (talk-210050)%10)return;
    auto* r=const_cast<GuestRegisterSnapshot*>(regs);
    const bool select=r->rax==73;
    if(!select && r->rax!=78 && r->rax!=79)return;
    // Keep the zero-argument native async79 path, including its layer callbacks.
    // Guests use that same path for slot0 too; native78 is the host's short-ritual UI.
    bbsc_world_guest_altar_menu={};
    if(!BbscWorldApplyAltars(GetCurrentPackedMap()) || !BbscWorldTalkAllowed(talk)){
        if(!select)r->rax=88;
    }
    else {
        const s32 slot=(talk-210050)/10;
        World::WorldId world;{std::scoped_lock lock{bbsc_world_presence_mutex};world=bbsc_world_presence_local.world;}
        bbsc_world_guest_altar_menu={world,bbsc_load_generation.load(),slot,bbsc_world_altars[slot].entry.ritual};
        if(!select)r->rax=79;
    }
    BBSC_TIMELINE("TRAVEL","guest native altar menu talk={} slot={} command={} occupied={}",
        talk,(talk-210050)/10,r->rax,bbsc_world_catalog_ready.load() && bbsc_world_altars[(talk-210050)/10].entry.occupied);
}
void PS4_SYSV_ABI BbscWorldBonfirePhase(u64,const GuestRegisterSnapshot* regs){
    if (regs && BbscNativeFinaleCommitted()) {
        // A new-cycle load is local, just like the native bonfire destination.
        const_cast<GuestRegisterSnapshot*>(regs)->rax=reinterpret_cast<u64>(bbsc_world_bonfire_phase.data());
    } else if(regs && bbsc_world_travel_inflight && bbsc_world_travel_point>0){
        if(ReadablePointer(regs->rax,0x88) && ReadValue<s32>(regs->rax,0x84)==3){
            const u64 global=GetGlobalState();
            BBSC_TIMELINE("TRAVEL","native bonfire destination preserved point={} selected_map={:#x} summon_map={:#x} phase=3",
                bbsc_world_travel_point,ReadValue<u32>(global,0x0C),ReadValue<u32>(global,0x14C4));
        }
        const_cast<GuestRegisterSnapshot*>(regs)->rax=reinterpret_cast<u64>(bbsc_world_bonfire_phase.data());
    }
}

// The original event is the ONLY owner of the departure animation and its
// action state. A direct ForceAnimation plus skipping bank2004[14] splits that
// state machine: the animation can finish before the native condition advances,
// and skipping the whole command discards its native action/controller work.
// Keep a separate, generation-bound input gate from acceptance through loading.
bool BbscWorldTravelInteractionBlocked() {
    if (BbscNativeFinalePlaying()) return true;
    if((!bbsc_world_travel_point && !bbsc_world_travel_inflight) ||
       !BbscIndependentTravelAllowed() || (GetSessionState()!=3 && GetSessionState()!=6) ||
       GetCharacterHp(GetLocalPlayerCharacter())<=0 ||
       bbsc_world_travel_departure_load!=bbsc_load_generation.load())return false;
    std::scoped_lock lock{bbsc_world_presence_mutex};
    return bbsc_world_travel_departure_world==bbsc_world_presence_local.world;
}
u8 bbsc_world_travel_action_skip=0;
void PS4_SYSV_ABI BbscWorldTravelActionHook(u64,const GuestRegisterSnapshot* regs) {
    bbsc_world_travel_action_skip=0;
    if(!regs || !BbscWorldTravelInteractionBlocked())return;
    // Native action-button registration ENTRY: reject before it registers an
    // item/talk/door/lever action or mutates its manager. Never veto at the
    // accepted-action observer, where these side effects have already happened.
    const_cast<GuestRegisterSnapshot*>(regs)->rax=0;
    bbsc_world_travel_action_skip=1;
}

bool QueueBbscWorldTravel(u32 flag,u8 value) {
    // Lighting is a native action, never a queued journey or quest journal.
    // m29 return likewise keeps its original flag, animation, waits and native
    // 9020..9026 Dream destination. Adopt that journey at NativeWarpBegin only.
    if(LampTravel::IsLampActivationCommand(flag) || (flag>=72900100 && flag<72900110))return false;
    if(!value || !BbscIndependentTravelAllowed() || !BbscWorldTravelFlag(flag))return false;
    const auto reject=[&](const char* reason){
        BBSC_TIMELINE("TRAVEL","local travel rejected flag={} talk={} reason={}",flag,bbsc_world_command_talk,reason);
        return true;
    };
    if(GetSessionState()!=3 && GetSessionState()!=6)return false;
    if(!bbsc_world_command_actor || BbscRegisterRemotePlayer(bbsc_world_command_actor))return reject("missing-local-executor");
    const u32 talk=bbsc_world_command_talk;
    const bool device=BbscWorldLampTalk(talk) ||
        (talk>=210050 && talk<=210110 && (talk-210050)%10==0);
    if(SteadyNowMs()-bbsc_world_command_seen>1000 || !device ||
       (GetSessionState()==6 && !BbscWorldTalkAllowed(talk)))return reject("device-context");
    s32 point=0,slot=-1;
    if(flag>=70000200 && flag<70000210)point=2102950;
    if(LampTravel::IsDreamReturn(flag)){
        // Match the command to its actual local lamp and map. Residency/owner
        // location never authorizes another actor's request.
        if(LampTravel::DreamReturnFlag(talk)!=flag)return reject("lamp-return-context");
        const auto map=GetCurrentPackedMap();
        if(talk>=290110 && talk<=290119){
            if(!Chalice::IsMap(map))return reject("dungeon-return-context");
        }else if((map>>24)*10+((map>>16)&0xFF)!=talk/1000)return reject("lamp-return-map");
        point=2102950;
    }
    for(const auto& destination:LampTravel::Returns)if(destination.flag==flag){point=destination.point;break;}
    // Native helper first sets the selected altar, waits for it to clear, THEN
    // sets the chosen layer. Do not start a load from the first half-command.
    if(flag>=72100420 && flag<72100427){
        const size_t chosen=flag-72100420;
        if(GetSessionState()==6 && (!BbscWorldGuestAltarMenuActive() ||
           chosen!=static_cast<size_t>(bbsc_world_guest_altar_menu.slot)))return reject("altar-menu-changed");
        if((GetSessionState()==6 && !bbsc_world_catalog_ready.load()) || !bbsc_world_altars[chosen].entry.occupied)
            return GetSessionState()==6;
        if(bbsc_world_travel_point || bbsc_world_travel_inflight || GetCharacterHp(GetLocalPlayerCharacter())<=0)
            return reject("busy-or-dead");
        if(bbsc_world_travel_altar_pending==static_cast<s32>(chosen) &&
           bbsc_world_travel_altar_load==bbsc_load_generation.load() && BbscEventFlag(flag)){
            std::scoped_lock lock{bbsc_world_presence_mutex};
            if(bbsc_world_presence_local.world==bbsc_world_travel_altar_world)return reject("altar-already-selected");
        }
        bbsc_world_travel_altar_pending=chosen;
        bbsc_world_altar_visiting=chosen;bbsc_world_requested_mount=bbsc_world_altars[chosen].mount;
        bbsc_world_travel_native_armed=false;
        bbsc_world_travel_altar_load=bbsc_load_generation.load();
        {std::scoped_lock lock{bbsc_world_presence_mutex};
            bbsc_world_travel_altar_world=bbsc_world_presence_local.world;}
        // Begin destination data preparation with native12107100's animation,
        // not after its four-second wait/layer command. Do not change current
        // event scope or arm a warp from this first half-command.
        World::Scope prepare;
        {std::scoped_lock lock{bbsc_world_presence_mutex};prepare.world=bbsc_world_presence_local.world;}
        prepare.map=0x1D000000;prepare.dungeon=bbsc_world_altars[chosen].mount.key;
        prepare.ritual=bbsc_world_altars[chosen].entry.ritual;
        BbscWorldEnsureSeed(prepare);
        World::Control request;request.kind=World::ControlKind::Request;request.scope=prepare;
        request.owner=BbscMod::RegisterOwnId();request.sequence=++bbsc_world_state_sequence;
        BbscWorldSend(request);
        // Native12107100 prepares the selected altar, plays its animation and
        // clears this flag. Only then does the ESD offer the layer request.
        BBSC_TIMELINE("TRAVEL","native altar selected slot={} flag={} ritual={}",chosen,flag,bbsc_world_altars[chosen].entry.ritual);
        return false;
    }
    if(flag>=72100300 && flag<72100310){
        bbsc_world_travel_layer=flag-72100300;slot=bbsc_world_travel_altar_pending;
        bbsc_world_travel_altar_pending=-1;
        if(slot<0)return reject("layer-without-altar");
        if(GetSessionState()==6 && (!BbscWorldGuestAltarMenuActive() ||
           slot!=bbsc_world_guest_altar_menu.slot))return reject("altar-menu-changed");
        point=2902950+bbsc_world_travel_layer;
    }
    if(!point)return false;
    // Consume duplicates/rejected local travel commands as well. They must not
    // replicate into the host's native event script and move another player.
    if(bbsc_world_travel_point || bbsc_world_travel_inflight || GetCharacterHp(GetLocalPlayerCharacter())<=0)return reject("busy-or-dead");
    World::Scope scope;
    {std::scoped_lock lock{bbsc_world_presence_mutex};scope.world=bbsc_world_presence_local.world;}
    if(slot>=0){
        if((GetSessionState()==6 && !bbsc_world_catalog_ready.load()) || !bbsc_world_altars[slot].entry.occupied ||
           bbsc_world_travel_layer<0 || bbsc_world_travel_layer>9)return true;
        // Refresh the selected host ritual, then use the same native unlock
        // condition as the host. The Hall is unconditionally offered by native79.
        if(GetSessionState()==6){
            BbscWorldSelectLampMenu(slot);
            if(bbsc_world_travel_layer && !BbscEventFlag(12907810+bbsc_world_travel_layer*20))return reject("layer-locked");
        }else if(bbsc_world_travel_layer && !BbscEventFlag(12907810+bbsc_world_travel_layer*20))return reject("layer-locked");
        bbsc_world_altar_visiting=slot;
        bbsc_world_requested_mount=bbsc_world_altars[slot].mount;
        scope.map=0x1D000000;scope.dungeon=bbsc_world_requested_mount->key;
        scope.ritual=bbsc_world_altars[slot].entry.ritual;
    }else{
        const auto it=std::ranges::find(LampPoints,point,&LampPoint::warp_point);
        if(it==LampPoints.end())return true;scope.map=it->packed_map;
        // Destination loader intent is separate from the CURRENT cup's
        // resident identity. Keep its altar until native departure begins.
        bbsc_world_requested_mount.reset();
        if(!Chalice::IsMap(GetCurrentPackedMap()))bbsc_world_altar_visiting=-1;
    }
    bbsc_world_requested_scope=scope;
    bbsc_world_travel_world=scope.world;bbsc_world_travel_point=point;bbsc_world_travel_flag=flag;
    bbsc_world_travel_native_armed=false;
    bbsc_world_travel_since=SteadyNowMs();bbsc_world_travel_request_sent=0;
    bbsc_world_travel_departure_load=bbsc_load_generation.load();
    bbsc_world_travel_departure_world=scope.world;
    BBSC_TIMELINE("TRAVEL","local departure accepted; interactions locked flag={} native_animation_only=true",flag);
    BBSC_TIMELINE("TRAVEL","independent lamp request point={} map={:#x} ritual={}",point,scope.map,scope.ritual);
    return true;
}


void EnableBbscNativeTravelEvent(u64 instance) {
    if(!BbscIndependentTravelAllowed() || !ReadablePointer(instance,0xC0))return;
    const s64 event=BbscEventIdOf(instance);
    if(!LampTravel::IsNativeTravelEvent(event) && !LampTravel::IsLampActivationEvent(event))return;
    // Original events remain native, but their local trip must not execute in
    // another room member's game. This is native SetNetworkSyncState(false).
    if(ReadValue<u8>(instance,0x78)!=0)WriteValue<u8>(instance,0x78,0);
    const u64 instruction=ReadValue<u64>(instance,0xB0);
    if(bbsc_world_travel_inflight && !bbsc_world_travel_native_armed &&
       (event==12107000 || event==7200 || event==12907020) && ReadablePointer(instruction,0x20)){
        // This is native interpreter progress, not proof that an animation is
        // visible. Record changes only, bounded to the active local journey.
        static s64 trip=-1;
        static std::map<u64,u8> observed;
        if(trip!=bbsc_world_travel_since){trip=bbsc_world_travel_since;observed.clear();}
        const s32 bank=ReadValue<s32>(instruction,0),command=ReadValue<s32>(instruction,4);
        const u8 phase=bank==3 && command==0?1:bank==2004 && command==14?2:
                       bank==1001 && command==0?4:bank==2003 && command==49?8:0;
        if(phase && observed.size()<128 && !(observed[instance]&phase)){
            observed[instance]|=phase;
            BBSC_TIMELINE("TRAVEL","native travel observation event={} instance={:#x} command={}[{}] since_release_ms={} selected_flag={} flag_set={}",
                event,instance,bank,command,SteadyNowMs()-bbsc_world_travel_since,
                bbsc_world_travel_flag,BbscEventFlag(bbsc_world_travel_flag));
        }
    }
    // EndIfClient/JumpIfClient use the shared native role gate, with no EVD rewrite.

}

void BbscWorldNativeWarpBegin(const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscIndependentTravelAllowed() || (GetSessionState()!=3 && GetSessionState()!=6))return;
    if(bbsc_world_travel_inflight && bbsc_world_travel_native_armed)return;
    // EMEVD2003[49] calls013CDF30(point in EDI), bypassing the Lua wrapper
    // 0132E050(point in ESI). Cover original unqueued returns to Dream too.
    const bool queued=bbsc_world_travel_inflight;
    if(!queued){
        const s32 point=static_cast<s32>(regs->rdi);
        const auto it=std::ranges::find(LampPoints,point,&LampPoint::warp_point);
        if(it!=LampPoints.end() && !Chalice::IsMap(it->packed_map)){
            // Native7200 can issue the return without QueueBbscWorldTravel.
            // Adopt that already-authorized native trip BEFORE stage teardown:
            // the loader's phase3 branch otherwise replaces global+0C (Dream)
            // with the old summon map+14C4 while retaining the bonfire spawn.
            // BbscWorldBonfirePhase must cover this load just like a queued one.
            World::Scope scope;
            {std::scoped_lock lock{bbsc_world_presence_mutex};scope.world=bbsc_world_presence_local.world;}
            scope.map=it->packed_map;
            bbsc_world_requested_scope=scope;
            bbsc_world_requested_mount.reset();bbsc_world_altar_visiting=-1;
            bbsc_world_travel_world=scope.world;bbsc_world_travel_point=point;
            bbsc_world_travel_flag=0;bbsc_world_travel_altar_pending=-1;
            bbsc_world_travel_inflight=true;bbsc_world_travel_saw_load=false;
            bbsc_world_travel_load=bbsc_load_generation.load();
            bbsc_world_travel_since=SteadyNowMs();
        }
    }
    if(bbsc_world_requested_scope && !Chalice::IsMap(bbsc_world_requested_scope->map))
        bbsc_world_altar_visiting=-1;
    bbsc_world_travel_native_armed=true;
    if(bbsc_world_travel_inflight)NoteBbscNativeLampSelection();
    ArmBbscReinsertV8(); // native FirstSync begins with the stage request, never during its animation
    BBSC_TIMELINE("TRAVEL","native stage request point={} selected={} queued={} map={:#x}",static_cast<s32>(regs->rdi),
        bbsc_world_travel_point,queued,bbsc_world_requested_scope?bbsc_world_requested_scope->map:0);
}

// This boundary is AFTER native condition/timer updates and BEFORE dispatch
// and PC advance. Holding it never freezes/replays the preceding animation.
u8 bbsc_world_travel_dispatch_skip=0;
void PS4_SYSV_ABI BbscWorldTravelDispatch(u64,const GuestRegisterSnapshot* regs) {
    bbsc_world_travel_dispatch_skip=0;
    if (regs && BbscNativeFinaleActive() && GuardBbscNativeFinaleCommand(regs->rbx)) {
        bbsc_world_travel_dispatch_skip=1;
        return;
    }
    if(!regs || !BbscIndependentTravelAllowed() || !bbsc_world_travel_inflight ||
       bbsc_world_travel_native_armed || !bbsc_world_requested_scope)return;
    const u64 instance=regs->rbx;
    if(!ReadablePointer(instance,0xC0))return;
    const u64 instruction=ReadValue<u64>(instance,0xB0);
    if(!ReadablePointer(instruction,0x20) || ReadValue<s32>(instruction,0)!=2003 ||
       ReadValue<s32>(instruction,4)!=49)return;
    const s64 event=BbscEventIdOf(instance);
    if(event!=7200 && event!=12107000 && event!=12107200 && event!=12907020)return;
    const auto scope=*bbsc_world_requested_scope;
    if(BbscWorldHasSnapshot(scope.map) &&
       (!Chalice::IsMap(scope.map) || PrepareBbscChaliceLoad(scope.map)))return;
    bbsc_world_travel_dispatch_skip=1;
    static s64 logged=-1;
    if(logged!=bbsc_world_travel_since){logged=bbsc_world_travel_since;
        BBSC_TIMELINE("TRAVEL","native warp held for destination after animation point={} map={:#x}",bbsc_world_travel_point,scope.map);}
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
    const auto wait=[&](const char* reason){
        static s64 trip=-1,last=0;static const char* previous=nullptr;
        if(trip!=bbsc_world_travel_since || previous!=reason || now-last>=5000){
            trip=bbsc_world_travel_since;previous=reason;last=now;
            BBSC_TIMELINE("TRAVEL","local travel waiting reason={} point={} waited_ms={} native_load={} world_pending={} finish_pending={}",
                reason,bbsc_world_travel_point,now-bbsc_world_travel_since,
                ReadablePointer(global,9)?ReadValue<u8>(global,8):0,
                bbsc_world_load_pending.load()!=0,bbsc_reload_finish_pending.load());
        }
    };
    if(!ReadablePointer(global,0x1598)){wait("global-unavailable");return;}
    const bool loading=ReadValue<u8>(global,8)!=0 || bbsc_world_load_pending.load() || bbsc_reload_finish_pending.load();
    // Prepare during the ORIGINAL animation and four-second native wait.
    // The dispatch boundary alone holds a late destination, never the animation.
    bool destination_ready=false;
    if(!loading && !bbsc_world_travel_native_armed && bbsc_world_requested_scope){
        const auto scope=*bbsc_world_requested_scope;
        BbscWorldEnsureSeed(scope);destination_ready=BbscWorldHasSnapshot(scope.map);
        if(!destination_ready && now-bbsc_world_travel_request_sent>=500){
            World::Control request;request.kind=World::ControlKind::Request;request.scope=scope;
            request.owner=BbscMod::RegisterOwnId();request.sequence=++bbsc_world_state_sequence;
            BbscWorldSend(request);bbsc_world_travel_request_sent=now;
        }
    }
    if(bbsc_world_travel_inflight){
        bbsc_world_travel_saw_load|=loading || bbsc_load_generation.load()!=bbsc_world_travel_load;
        if(bbsc_world_travel_saw_load && !loading && GetLocalPlayerCharacter() && GetCharacterHp(GetLocalPlayerCharacter())>0){
            bbsc_world_travel_inflight=false;bbsc_world_travel_point=0;
            ApplyBbscIndependentAtLoad(GetCurrentPackedMap());
            BBSC_TIMELINE("TRAVEL","independent arrival map={:#x}",GetCurrentPackedMap());
        }else if(now-bbsc_world_travel_since>90000 &&
                 bbsc_world_travel_native_armed){
            bbsc_world_travel_inflight=false;bbsc_world_travel_point=0;
            LOG_ERROR(Debug,"BBSC independent travel timed out; native leave remains available");
        }
        return;
    }
    if(now-bbsc_world_travel_since>30000 || GetCharacterHp(GetLocalPlayerCharacter())<=0){
        BBSC_TIMELINE("TRAVEL","local travel cancelled point={} waited_ms={} hp={}",bbsc_world_travel_point,now-bbsc_world_travel_since,GetCharacterHp(GetLocalPlayerCharacter()));
        bbsc_world_travel_point=0;return;
    }
    if(loading || !bbsc_world_requested_scope){wait(loading?"load-pending":"scope-missing");return;}
    const auto scope=*bbsc_world_requested_scope;
    // Release the ORIGINAL local event. It owns the menu, animation, delay,
    // stage request and point selection; no synthesized summon/coordinate warp.
    if(Chalice::IsMap(scope.map) && destination_ready)PrepareBbscChaliceLoad(scope.map);
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
        Site{0x01AC3EE7,{0x5B,0x41,0x5E,0x5D,0xC3},BbscWorldAltarHelper},
        Site{0x01AA6860,{0x55,0x48,0x89,0xE5,0x41,0x57},BbscWorldAltarUpdate},
        Site{0x0192997A,{0x83,0xB8,0x84,0,0,0,3},BbscWorldBonfirePhase}};
    static constexpr std::array<u8,7> MenuBranch{0x83,0xB8,0x64,0x03,0,0,4};
    static constexpr std::array<u8,7> MenuContinuation{0x83,0xB8,0x64,0x03,0,0,1};
    static constexpr std::array<u8,6> MenuItemEntry{0x55,0x48,0x89,0xE5,0x41,0x57};
    static constexpr std::array<u8,8> MenuHelperCapture{0x48,0x89,0x45,0xA0,0x48,0x89,0x4D,0xA8};
    static constexpr std::array<u8,7> MenuPanelHelper{0x4C,0x8D,0xBD,0x40,0xFC,0xFF,0xFF};
    for(const auto& [offset,bytes]:std::array{
        std::pair{u64{0x01B75353},std::span<const u8>{MenuBranch}},
        std::pair{u64{0x01B74F4B},std::span<const u8>{MenuContinuation}},
        std::pair{u64{0x01B76150},std::span<const u8>{MenuItemEntry}},
        std::pair{u64{0x01B661CF},std::span<const u8>{MenuHelperCapture}},
        std::pair{u64{0x01B77227},std::span<const u8>{MenuPanelHelper}}})
        if(!ReadablePointer(image_base+offset,bytes.size()) ||
           std::memcmp(reinterpret_cast<void*>(image_base+offset),bytes.data(),bytes.size())){
            LOG_ERROR(Debug,"BBSC guest native altar menu: site {:#x} differs; travel remains closed",offset);return;}
    for(const auto& site:sites)if(!ReadablePointer(image_base+site.offset,site.bytes.size()) ||
        std::memcmp(reinterpret_cast<const void*>(image_base+site.offset),site.bytes.data(),site.bytes.size())){
        LOG_ERROR(Debug,"BBSC independent travel: site {:#x} differs; guest lamps remain closed",site.offset);return;}
    // Preserve the host's old f52 behavior through the scoped hook rather than
    // globally patching every guest talk to pretend it is a solo game.
    bbsc_world_live_talk[3]=reinterpret_cast<u64>(bbsc_world_live_talker.data());
    std::memset(bbsc_world_lamp_command.data()+0xA0,0xFF,8);
    for(const auto& site:sites)if(!InstallGuestCodeHook(reinterpret_cast<void*>(image_base+site.offset),site.bytes,0,site.hook))return;
    if(!InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x01B661CF),MenuHelperCapture,1,
        BbscWorldAltarHelper) ||
       !InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x01B77227),MenuPanelHelper,2,
        BbscWorldAltarHelper) ||
       !InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x01B75353),MenuBranch,0,
        BbscWorldAltarMenuBranch) ||
       !InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x01B74F4B),MenuContinuation,1,
        BbscWorldAltarMenuBranch) ||
       !InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x01B76150),MenuItemEntry,0,
        BbscWorldAltarMenuItem,&bbsc_world_altar_remove_skip))return;
    static constexpr std::array<u8,6> ActionEntry{0x55,0x48,0x89,0xE5,0x41,0x57};
    if(!InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x01CD91F0),ActionEntry,0,
        BbscWorldTravelActionHook,&bbsc_world_travel_action_skip))return;
    static constexpr std::array<u8,6> Dispatch{0xC4,0xC1,0x7A,0x10,0x46,0x08};
    static constexpr std::array<u8,7> Tail{0x48,0x8B,0x05,0x2C,0x6C,0x0F,0x04};
    if(!ReadablePointer(image_base+0x012ECFAD,Tail.size()) ||
       std::memcmp(reinterpret_cast<void*>(image_base+0x012ECFAD),Tail.data(),Tail.size()) ||
       !InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x012ECF6B),Dispatch,0,
           BbscWorldTravelDispatch,&bbsc_world_travel_dispatch_skip,false,
           reinterpret_cast<void*>(image_base+0x012ECFAD)))return;
    bbsc_independent_travel_hooks=true;
    static constexpr std::array<u8,6> TalkAccepted{0x41,0xBD,0x01,0,0,0};
    static constexpr std::array<u8,9> DialogResult{0x89,0x51,0x18,0x89,0x90,0xCC,0x01,0,0};
    bbsc_finale_hooks_ready = summon_reload_state_hook_installed &&
        InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x0203F165),TalkAccepted,0,
            BbscGehrmanTalkAccepted,&bbsc_finale_talk_skip,false,
            reinterpret_cast<void*>(image_base+0x0203F16B)) &&
        InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x01C28261),DialogResult,0,BbscFinaleDialogResult);
    if (!bbsc_finale_hooks_ready) LOG_ERROR(Debug,"BBSC: native finale dialog or load descriptor unavailable");
    LOG_INFO(Debug,"BBSC independent travel: scoped lamp/talker/bonfire hooks installed");
}
#endif
