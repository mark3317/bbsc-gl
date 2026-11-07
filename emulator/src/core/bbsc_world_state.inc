// SPDX-License-Identifier: GPL-2.0-or-later
#ifdef BBSC_MOD
// Native altar records contain the decoded layout too. 01928680 reads it via
// these same read-only getters before 01928987 commits the loader. This avoids
// requiring the host to enter a dungeon merely to make its descriptor available.
struct BbscWorldAltar {
    World::AltarEntry entry;
    Chalice::Mount mount{};
    u64 native_lamps=0; // exact lit/menu flags from this slot's native backing group
};
std::array<BbscWorldAltar,7> bbsc_world_altars;
World::GuestAltars bbsc_world_guest_altars;
std::array<BbscWorldAltar,7> bbsc_world_altars_assembling;
u64 bbsc_world_altar_revision=0,bbsc_world_altar_receiving=0;
u8 bbsc_world_altar_parts=0;
s32 bbsc_world_altar_current=-1,bbsc_world_altar_visiting=-1;
World::WorldId bbsc_world_altar_world{};
std::optional<Chalice::Mount> bbsc_world_requested_mount;
std::optional<World::Scope> bbsc_world_requested_scope;
std::atomic<bool> bbsc_world_catalog_ready{false};
std::atomic<bool> bbsc_world_altars_dirty{true};

std::vector<u8> BbscWorldLayoutProof(const Chalice::Mount& m) {
    std::vector<u8> bytes(88);
    std::memcpy(bytes.data(),m.parts.data(),72);
    std::memcpy(bytes.data()+72,&m.layout_map,4);
    std::memcpy(bytes.data()+76,&m.dungeon_type,4);
    std::memcpy(bytes.data()+80,&m.feature,4);
    std::memcpy(bytes.data()+84,&m.stage_map,4);
    return bytes;
}
Chalice::Key BbscIndependentDungeonKey(const Chalice::Key& key) {
    // Called under the presence mutex: the independent scope uses the complete
    // decoded layout proof. The legacy FormData key/path remains unchanged.
    for(const auto& a:bbsc_world_altars)
        if(a.entry.occupied && a.mount.key.channel==key.channel) return a.mount.key;
    return key;
}
u64 BbscIndependentRitual(const Chalice::Key& key) {
    s32 slot=GetSessionState()==3?bbsc_world_altar_current:bbsc_world_altar_visiting;
    if(slot<0) slot=bbsc_world_altar_current;
    if(slot>=0 && slot<7 && bbsc_world_altars[slot].entry.occupied &&
       bbsc_world_altars[slot].mount.key.channel==key.channel) return bbsc_world_altars[slot].entry.ritual;
    return 0;
}
bool BbscWorldMountFor(u32 map,Chalice::Mount& out) {
    if(!BbscIndependentActive() || !Chalice::IsMap(map) || !bbsc_world_requested_mount) return false;
    out=*bbsc_world_requested_mount;
    out.map=map; // actual loaded part may differ from the virtual stage root
    return Chalice::ValidMount(out);
}
bool BbscWorldProtectAltar(u32 flag,u32 width) {
    if (flag < 94'000'000 || flag >= 94'700'000 || !width || width > 32) return false;
    const s32 session=GetSessionState();
    return BbscIndependentActive() && (session==4 || session==6) &&
           flag>=94'000'000 && Chalice::TouchesAltar(flag,width);
}

// Original013B89B0 binds the selected cup's virtual m29 groups to backing
// storage indexed by013BC710(kind,40+slot,0,group). Use that same mapping
// without selecting another altar or depending on which map the host loaded.
u64 BbscWorldNativeAltarGroup(s32 slot,u32 kind,u32 group) {
    if(slot<0 || slot>=7 || (kind!=1 && kind!=6 && kind!=7) || group>=10)return 0;
    const u64 man=ReadValue<u64>(image_base+WorldFlagManPointerOffset,0);
    if(!ReadablePointer(man,0x40) || ReadValue<u32>(man,0x20)!=125)return 0;
    using Index=s32 PS4_SYSV_ABI (*)(s32,s32,s32,s32);
    const s32 index=reinterpret_cast<Index>(image_base+0x013BC710)(kind,40+slot,0,group);
    if(index<0 || static_cast<u32>(index)>=ReadValue<u32>(man,0x24))return 0;
    const u64 backing=ReadValue<u64>(man,0x28);
    if(!ReadablePointer(backing,125))return 0;
    const u64 storage=backing+static_cast<u64>(index)*125;
    return ReadablePointer(storage,125)?storage:0;
}
s32 BbscWorldHostAltarSlot(const World::Scope& scope) {
    if(GetSessionState()!=3 || !Chalice::IsMap(scope.map) || scope.world!=bbsc_world_altar_world)return -1;
    for(s32 slot=0;slot<7;++slot){const auto& a=bbsc_world_altars[slot];
        if(a.entry.occupied && a.entry.ritual==scope.ritual && a.mount.key==scope.dungeon)return slot;}
    return -1;
}
bool BbscWorldReadAltarLamps(s32 slot,u64& bits) {
    const u64 storage=BbscWorldNativeAltarGroup(slot,1,7);if(!storage)return false;
    bits=0;
    for(size_t i=0;i<10;++i)for(size_t form=0;form<2;++form){
        const u32 offset=800+static_cast<u32>(i)*20+static_cast<u32>(form)*10;
        if(ReadValue<u8>(storage,offset/8)&(0x80u>>(offset%8)))bits|=u64{1}<<(i*2+form);
    }
    return true;
}

bool BbscWorldReadAltar(s32 slot,BbscWorldAltar& out) {
    if(slot<0 || slot>=7 || !ReadablePointer(ReadValue<u64>(image_base+WorldFlagManPointerOffset,0),0x40)) return false;
    const u32 first=94000000+slot*100000;
    for(size_t i=0;i<6;++i){const u64 storage=BbscFlagGroupStorage(first/1000+i);
        if(!storage) return false; // unknown is not an empty altar
        std::memcpy(out.entry.record.data()+i*125,reinterpret_cast<const void*>(storage),125);
    }
    out.entry.occupied=out.entry.record[0]==29;
    if(!out.entry.occupied) return true;
    // Read-only native getters: channel, layout, 18 stage parts and dungeon type.
    // Buffers match or exceed the native stack outputs; no selected-altar flag is changed.
    using Get=void* PS4_SYSV_ABI (*)(void*,const s32*);
    std::array<u8,256> channel{},layout{},type{};
    reinterpret_cast<Get>(image_base+0x01AB2A40)(channel.data(),&slot);
    reinterpret_cast<Get>(image_base+0x01AB1DB0)(layout.data(),&slot);
    out.mount.parts.fill(-1);
    reinterpret_cast<Get>(image_base+0x01AB3070)(out.mount.parts.data(),&slot);
    reinterpret_cast<Get>(image_base+0x01AB31C0)(type.data(),&slot);
    std::memcpy(&out.mount.key.channel,channel.data(),8);
    std::memcpy(&out.mount.layout_map,layout.data(),4);
    std::memcpy(&out.mount.dungeon_type,type.data(),4);
    out.mount.stage_map=0x1D000000;
    out.mount.map=out.mount.layout_map;
    out.mount.feature=out.entry.record[131]&3; // native getter: flags +1024, low two bits
    out.entry.form=BbscWorldLayoutProof(out.mount);
    out.mount.key.form_size=out.entry.form.size();out.mount.key.form_version=0;
    out.mount.key.form_hash=Chalice::HashForm(out.entry.form);
    out.entry.dungeon=out.mount.key;
    if(!BbscWorldReadAltarLamps(slot,out.native_lamps))return false;
    // Ritual metadata and native lamp progress travel together. The native
    // menu and transition use the original per-layer unlock conditions.
    out.entry.lamps.fill(true);
    out.mount.revision=1;
    return Chalice::ValidMount(out.mount);
}

#pragma pack(push,1)
struct BbscWorldAltarWire {
    u8 slot=0,occupied=0,current=0xFF,lamps=0;
    u64 revision=0,ritual=0;
    u64 native_lamps=0; // twenty exact native lamp flags, same wire size
    World::AltarRecord record{};
    Chalice::Mount mount{};
};
struct BbscWorldFlagPart {
    u8 first=0,count=0;std::uint16_t reserved=0;
    u64 present=0;
    std::array<std::array<u8,125>,8> groups{};
};
struct BbscWorldAltarProgress {
    u8 slot=0;std::array<u8,7> reserved{};u64 ritual=0;
    std::array<u8,125> mask{},bits{};
};
#pragma pack(pop)
std::array<BbscWorldAltarProgress,7> bbsc_world_altar_progress;
void QueueBbscWorldLampWrite(u32 flag,u32 width,u32 value);

void QueueBbscWorldAltarWrite(u32 flag,u32 width,u32 value) {
    QueueBbscWorldLampWrite(flag,width,value);
    if (!width || width > 32) return;
    // Includes selected-altar9020..26 and mounted ritual lamp flags12907800..
    // as well as94xxxxxx records. Unrelated writes need no live role lookup.
    if (!Chalice::TouchesAltar(flag,width) && !Chalice::TouchesLampUnlock(flag,width)) return;
    if(GetSessionState()==3)
        bbsc_world_altars_dirty=true;
    if(!BbscIndependentActive() || GetSessionState()!=6 || !width || width>32 ||
       flag<94'000'000 || flag>=94'700'000)return;
    const u32 slot=(flag-94'000'000)/100'000,offset=(flag-94'000'000)%100'000;
    if(slot>=7 || offset<5000 || offset+width>6000 || !bbsc_world_altars[slot].entry.occupied)return;
    auto& p=bbsc_world_altar_progress[slot];
    if(p.ritual!=bbsc_world_altars[slot].entry.ritual){p={};p.slot=slot;p.ritual=bbsc_world_altars[slot].entry.ritual;}
    for(u32 i=0;i<width;++i){const u32 bit=offset-5000+i;const u8 mask=0x80u>>(bit%8);
        p.mask[bit/8]|=mask;
        if(value&(u32{1}<<(width-i-1)))p.bits[bit/8]|=mask;else p.bits[bit/8]&=~mask;
    }
}
// Install the complete host view at native admission or a catalog update, never
// on a timer. Check every backing group before exposing any of the seven slots.
bool BbscWorldApplyAltars(u32 map) {
    const s32 session=GetSessionState();
    if(!BbscIndependentActive() || (session!=4 && session!=6) || map!=BbscDreamStateMap)return true;
    if(!bbsc_world_catalog_ready.load())return false;
    std::array<u64,42> storage{};
    for(size_t i=0;i<7;++i)for(size_t j=0;j<6;++j){
        storage[i*6+j]=BbscFlagGroupStorage(94000+i*100+j);
        if(!storage[i*6+j])return false;
    }
    for(size_t i=0;i<7;++i)for(size_t j=0;j<6;++j){
        const u32 key=94000+i*100+j;auto* live=reinterpret_cast<u8*>(storage[i*6+j]);
        KeepBbscOwnWorldGroup(key,live);
        std::memcpy(live,bbsc_world_altars[i].entry.record.data()+j*125,125);
    }
    return true;
}

struct BbscWorldState {
    u64 epoch=0,sequence=0,present=0;
    u32 parts=0;
    std::array<std::array<u8,125>,30> groups{};
    bool flags_ready=false;
};
std::map<World::Scope,BbscWorldState> bbsc_independent_states; // game thread only
u64 bbsc_world_state_sequence=0;
World::WorldId bbsc_world_states_world{};

void BbscWorldRememberProgress(const World::Scope& scope,const BbscWorldState& state) {
    if(!state.flags_ready || !BbscSharedProgressEnabled() || GetSessionState()!=6 ||
       GetLocalPlayerType()!=1 || scope.map==BbscDreamStateMap || Chalice::IsMap(scope.map))return;
    bool rewards=false;
    {std::scoped_lock lock{bbsc_progress_mutex};
        for(size_t i=0;i<10;++i)if(state.present&(u64{1}<<i)){
            const u32 key=BbscWorldGroupKey(scope.map,i);auto& merged=bbsc_progress_groups[key];
            for(size_t j=0;j<125;++j){
                rewards|=BbscBossCompletionBitsAdded(key,j,state.groups[i][j]&~merged[j]);
                merged[j]|=state.groups[i][j];
            }
        }
    }
    if(rewards)RequestBbscRewardCheck();
}

void BbscWorldApplyFlags(const World::Scope& scope,const BbscWorldState& state) {
    if(!state.flags_ready) return;
    if(scope.map==BbscDreamStateMap)return; // dedicated host Dream phase, never guest map state
    const bool guest=GetSessionState()==6;
    const bool dungeon=Chalice::IsMap(scope.map);
    const bool host_cup=GetSessionState()==3 && dungeon;
    const s32 slot=host_cup?BbscWorldHostAltarSlot(scope):-1;
    if(host_cup && slot<0)return;
    for(size_t i=0;i<30;++i) {
        if(!(state.present&(u64{1}<<i))) continue;
        const u32 key=BbscWorldGroupKey(scope.map,i);
        const u64 storage=host_cup?BbscWorldNativeAltarGroup(slot,key/10000,key%10):BbscFlagGroupStorage(key);
        if(!storage) continue;
        auto* live=reinterpret_cast<u8*>(storage);
        std::array<u8,125> before;std::memcpy(before.data(),live,125);
        if(guest) KeepBbscOwnWorldGroup(key,live);
        // Independent m29 state is already keyed by dungeon AND ritual. Its
        // lamps must replace the previous mounted cup's runtime flags too.
        if(dungeon)std::memcpy(live,state.groups[i].data(),125);
        else if (const auto flags = World::LiftFlags(key); !flags.empty()) {
            // A running lift is owned by its native event. Replaying a
            // flag from a snapshot would change its conditions without moving it.
            auto incoming = state.groups[i];
            for (const auto& lift : flags) {
                const u8 mask = lift.position | lift.temporary;
                auto& value = incoming[lift.offset];
                value = (value & ~mask) | (before[lift.offset] & mask);
            }
            Chalice::CopyHostFlagGroup(key,live,incoming);
        } else {
            Chalice::CopyHostFlagGroup(key,live,state.groups[i]);
        }
        // This is the SAME host cup's backing bank. An older owner snapshot
        // must not revoke an already recorded lamp discovery/menu unlock.
        if(host_cup && key==12907 && before!=state.groups[i])
            for(const u32 unlock:Chalice::LampUnlockFlags)for(const u32 flag:{unlock-10,unlock})
                live[flag%1000/8]|=before[flag%1000/8]&(0x80u>>(flag%8));
        // Keep permanent progress even if a resident peer's snapshot is older.
        if(i<10 && !dungeon)
            BbscMergeSharedProgressGroup(key,live,before.data());
        if (key == 12401 || key == 13201) {
            // 12401803 / 13201803 mark each player's native movie complete.
            // An owner's snapshot can arrive while the local Remo is playing.
            constexpr size_t byte = 803 / 8;
            constexpr u8 mask = 0x80 >> (803 % 8);
            live[byte] = (live[byte] & ~mask) | (before[byte] & mask);
        }
        KeepBbscGuestTalkBits(key,before.data(),live);
        KeepBbscNpcOwnBits(key,before.data(),live);
#ifdef BBSC_MOD
        NoteBbscNativeWorldFlagApply(scope.map,key,before.data(),live,before.size());
#endif
    }
}
BbscWorldState BbscWorldCaptureFlags(const World::Scope& scope) {
    BbscWorldState state;state.flags_ready=true;
    const bool dungeon=Chalice::IsMap(scope.map);
    const bool host_cup=dungeon && GetSessionState()==3;
    const s32 slot=host_cup?BbscWorldHostAltarSlot(scope):-1;
    if(dungeon){
        World::Scope current;
        {std::scoped_lock lock{bbsc_world_presence_mutex};current=World::ScopeOf(bbsc_world_presence_local);}
        // A visitor's own/previous cup must never become the initial world.
        // The host can read its actual saved cup even while staying in Dream.
        if(host_cup?slot<0:current!=scope){state.flags_ready=false;return state;}
    }
    for(size_t i=0;i<30;++i){
        const u32 key=BbscWorldGroupKey(scope.map,i);
        const u64 p=host_cup?BbscWorldNativeAltarGroup(slot,key/10000,key%10):BbscFlagGroupStorage(key);
        if(!p){if(dungeon){state.flags_ready=false;return state;}continue;}
        state.present|=u64{1}<<i;std::memcpy(state.groups[i].data(),reinterpret_cast<const void*>(p),125);
    }
    return state;
}
bool BbscWorldFlagsReady(const World::Scope& scope) {
    const auto it=bbsc_independent_states.find(scope);
    if(it==bbsc_independent_states.end() || !it->second.flags_ready)return false;
    const bool ritual_seed=it->second.epoch==0 && Chalice::IsMap(scope.map) && std::ranges::any_of(bbsc_world_altars,[&](const auto& a){
        return a.entry.occupied && a.entry.ritual==scope.ritual && a.mount.key==scope.dungeon;});
    if(it->second.epoch==0 && Chalice::IsMap(scope.map) && !ritual_seed)return false;
    // An epoch0 empty seed previously admitted a guest's personal first layer.
    // m29 events need the complete progress bank, not merely a known ritual.
    if(Chalice::IsMap(scope.map)?(it->second.present&0x3FF)!=0x3FF:!(it->second.present&1))return false;
    std::scoped_lock lock{bbsc_world_presence_mutex};
    const auto* owner=bbsc_independent_owners.Find(scope);
    return !owner || it->second.epoch==owner->epoch ||
        (owner->owner==BbscMod::RegisterOwnId() && it->second.epoch<owner->epoch);
}

// Seed the destination before its EMEVDs start. The native initializer uses
// the saved position and performs the object/lever setup itself.
void BbscWorldSeedLiftFlags(u32 map) {
    const u32 base = BbscWorldGroupKey(map, 0);
    if (!base) return;
    const BbscWorldState* snapshot = nullptr;
    bool snapshot_checked = false;
    const bool guest = GetSessionState() == 6;
    for (size_t i = 0; i < 10; ++i) {
        const u32 key = base + static_cast<u32>(i);
        const auto flags = World::LiftFlags(key);
        if (flags.empty()) continue;
        const auto storage = BbscFlagGroupStorage(key);
        if (!storage) continue;
        auto* live = reinterpret_cast<u8*>(storage);
        if (guest) KeepBbscOwnWorldGroup(key, live);
        if (!snapshot_checked) {
            snapshot_checked = true;
            World::Scope scope;
            u32 owner = 0;
            {
                std::scoped_lock lock{bbsc_world_presence_mutex};
                scope = World::ScopeForMap(World::ScopeOf(bbsc_world_presence_local),
                                           map & 0xFFFF0000, bbsc_world_requested_scope);
                if (const auto* lease = bbsc_independent_owners.Find(scope)) owner = lease->owner;
            }
            if (owner && owner != BbscMod::RegisterOwnId() && BbscWorldFlagsReady(scope))
                snapshot = &bbsc_independent_states.at(scope);
        }
        for (const auto& lift : flags) {
            auto& value = live[lift.offset];
            value &= ~lift.temporary; // a new load has no local movement in flight
            if (lift.position && snapshot && (snapshot->present & (u64{1} << i)))
                value = (value & ~lift.position) | (snapshot->groups[i][lift.offset] & lift.position);
        }
    }
}
void BbscWorldEnsureSeed(const World::Scope& scope) {
    if(BbscMod::RegisterOwnId()!=scope.world.host || BbscWorldFlagsReady(scope))return;
    u64 epoch=0;
    {std::scoped_lock lock{bbsc_world_presence_mutex};
        if(const auto* owner=bbsc_independent_owners.Find(scope)){
            epoch=owner->epoch;
            // Leases survive departure. Only a player STILL in this scope can
            // supply its state; never wait on a lease for a different map.
            if(owner->owner!=scope.world.host){
                const auto* resident=bbsc_world_presence_book.Resident(owner->owner);
                if(Chalice::IsMap(scope.map) || (resident &&
                   resident->presence.phase!=World::Phase::Leaving &&
                   World::ScopeOf(resident->presence)==scope))return;
            }
        }}
    // Keep any completed state above. With no resident provider, seed missing
    // flags from the host's world, preserving the lease fence. No NPC state or
    // simulation ownership is invented here.
    auto seed=BbscWorldCaptureFlags(scope);seed.sequence=++bbsc_world_state_sequence;
    seed.epoch=Chalice::IsMap(scope.map)?0:epoch;
    const auto previous=bbsc_independent_states.find(scope);
    if(previous==bbsc_independent_states.end() || previous->second.epoch!=seed.epoch || previous->second.present!=seed.present)
        BBSC_TIMELINE("TRAVEL","destination flags seeded map={:#x} epoch={} present={:#x}",scope.map,epoch,seed.present);
    bbsc_independent_states[scope]=std::move(seed);
}
bool BbscWorldHasSnapshot(u32 map) {
    if(!BbscIndependentActive()) return false;
    World::Scope scope;
    {std::scoped_lock lock{bbsc_world_presence_mutex};scope=World::ScopeOf(bbsc_world_presence_local);}
    scope=World::ScopeForMap(scope,map,bbsc_world_requested_scope);
    return BbscWorldFlagsReady(scope);
}
void ApplyBbscIndependentAtLoad(u32 map) {
    if(!BbscIndependentActive()) return;
    World::Scope scope;
    {std::scoped_lock lock{bbsc_world_presence_mutex};scope=World::ScopeOf(bbsc_world_presence_local);}
    scope=World::ScopeForMap(scope,map,bbsc_world_requested_scope);
    if(auto it=bbsc_independent_states.find(scope);it!=bbsc_independent_states.end()) BbscWorldApplyFlags(scope,it->second);
    if(map==BbscDreamStateMap && GetSessionState()==6){
        // Older saves can have the native Mergo clear without its common 50
        // phase flag. Apply that single native SetEventFlag before m21 starts.
        if (!BbscNativeFinaleCommitted() && BbscEventFlag(12601800) && !BbscEventFlag(9462))
            SetBbscLedgerFlag(9462, 1);
        ApplyBbscHostDreamState("independent arrival");
        BbscWorldApplyAltars(map);
    }
    if(Chalice::IsMap(map)) CompleteBbscChaliceLoad(map);
    ApplyBbscHostTime("independent world arrival", map);
}

World::Scope bbsc_world_bootstrap_scope{};
u64 bbsc_world_bootstrap_load=~u64{0};
s32 bbsc_world_bootstrap_session=-1;
bool BbscWorldSceneReady() {
    // Travel metadata still has its own live phase/load/flags checks. Native
    // NPC FirstSync/admission is intentionally left to the original engine.
    if(SessionTest::NativeNpcSync())return true;
    std::scoped_lock lock{bbsc_world_presence_mutex};
    const auto& local=bbsc_world_presence_local;
    return bbsc_world_bootstrap_load==bbsc_world_native_load.load() &&
        bbsc_world_bootstrap_scope==World::ScopeOf(local);
}
bool BbscWorldNativePeerReady(u32 owner) {
    if(!owner || owner==BbscMod::RegisterOwnId())return true;
    for(const u64 task:GetMultiPlayerInsTasks()){
        const s32 mode=ReadValue<s32>(task,0xE8);if(mode!=1 && mode!=2)continue;
        const u32 peer=mode==2 && GetSessionState()==6?GetBbscRelayHost():BbscWorldPeer(task+0xC8);
        if(peer==owner && ReadValue<s32>(task,0x50)==6 && ReadValue<s32>(task,0x54)==6 &&
           !(ReadValue<u8>(task,0xED)&2))return true;
    }
    return false;
}
bool GuardBbscWorldBootstrap(u64 instance) {
    if (BbscNativeFinaleCommitted()) return false;
    const bool native_npc=SessionTest::NativeNpcSync();
    // Native NPC replication does not initialize a borrowed ritual's flags.
    // Keep the existing once-per-load cup admission before native m29 events:
    // their initial EndIfFlag must see this ritual, not the previous cup.
    // Ordinary maps retain the native-mode fast exit.
    if(native_npc){
        if(!BbscIndependentTravelAllowed())return false;
        const u64 load=bbsc_world_native_load.load();
        const s32 session=GetSessionState();
        // Successful admission belongs to the native load, not every event.
        // No map lookup, flag copy or NPC readiness query on subsequent steps.
        if(bbsc_world_bootstrap_load==load && bbsc_world_bootstrap_session==session)return false;
        World::Scope scope;
        {std::scoped_lock lock{bbsc_world_presence_mutex};scope=World::ScopeOf(bbsc_world_presence_local);}
        scope=World::ScopeForMap(scope,GetCurrentPackedMap(),bbsc_world_requested_scope);
        BbscWorldNativeInitialOnce(scope);
        if(!Chalice::IsMap(GetCurrentPackedMap())){
            bbsc_world_bootstrap_load=load;bbsc_world_bootstrap_session=session;
            return false;
        }
    }
    if(!BbscIndependentTravelAllowed() || !ReadablePointer(instance,0xC0))return false;
    // Local player travel does not consume NPC/world initialization. Holding
    // its animation/exit behind owner FirstSync can keep a visitor trapped
    // until the other player moves. Destination readiness is checked at the
    // native warp dispatch, while all shared world events keep this barrier.
    const s32 role=GetSessionState();
    if(role==3 || role==6){
        const s64 event=BbscEventIdOf(instance);
        if(LampTravel::IsNativeTravelEvent(event) || event==9421 || event==9422)return false;
    }
    World::Scope scope;
    {std::scoped_lock lock{bbsc_world_presence_mutex};scope=World::ScopeOf(bbsc_world_presence_local);}
    const u32 raw=GetCurrentPackedMap();if(!World::ValidMap(raw))return true;
    // A Dream request must not redirect the cup's departure event into
    // destination admission before the native warp has even run.
    scope=World::ScopeForMap(scope,raw,bbsc_world_requested_scope);
    const u64 load=bbsc_world_native_load.load();
    const s32 session=GetSessionState();
    // Joining can replace the native flag table without starting another map
    // load. State4 admission must not certify the subsequent state6 Dream view.
    if(bbsc_world_bootstrap_load==load && bbsc_world_bootstrap_scope==scope &&
       (!native_npc || bbsc_world_bootstrap_session==session) &&
       !(scope.map==BbscDreamStateMap && bbsc_world_bootstrap_session==4 && session==6))
        return !native_npc && BbscWorldBlocksActive() && scope.map!=BbscDreamStateMap && !BbscWorldAdmitBlocks(scope);
    BbscWorldEnsureSeed(scope);
    auto it=bbsc_independent_states.find(scope);
    if(scope.map!=BbscDreamStateMap && !BbscWorldFlagsReady(scope)){
        // Return without advancing the native instruction: initialization must
        // not run against this visitor's fresh personal world.
        static s64 sent=0;const s64 now=SteadyNowMs();
        if(now-sent>=500){
            World::Control c;c.kind=World::ControlKind::Request;c.scope=scope;
            c.owner=BbscMod::RegisterOwnId();c.sequence=++bbsc_world_state_sequence;BbscWorldSend(c);sent=now;
        }
        return true;
    }
    u32 owner=0;u64 owner_epoch=0;
    {std::scoped_lock lock{bbsc_world_presence_mutex};if(const auto* lease=bbsc_independent_owners.Find(scope)){owner=lease->owner;owner_epoch=lease->epoch;}}
    // Wait before installing any host Dream data. Native FirstSync can still
    // replace the backing table; no event may consume this view until it is ready.
    if(!native_npc && BbscWorldBlocksActive() && scope.map!=BbscDreamStateMap && (session==3 || session==6)){
        if(!BbscWorldAdmitBlocks(scope))return true;
    }else if(!native_npc){
        if(!BbscWorldNativePeerReady(owner))return true;
        if(!BbscWorldNativeInitialReady(scope,owner,owner_epoch))return true;
    }
    // Dream altar events must never initialize against personal ritual records.
    // Join state4 is included: those events can precede the final guest state6.
    if(scope.map==BbscDreamStateMap && (session==4 || session==6)){
        if(!BbscHostDreamStateReady() || !BbscHostWorldFlagsReady(BbscDreamStateMap) ||
           !bbsc_world_catalog_ready.load())return true;
        ApplyBbscHostDreamState("before native events");
        if(!BbscWorldApplyAltars(scope.map))return true;
    }
    // Enemy initial state belongs to the native network machinery. Never wait
    // for, publish or apply a parallel mod-maintained enemy snapshot.
    if(it!=bbsc_independent_states.end())BbscWorldApplyFlags(scope,it->second);
    {std::scoped_lock lock{bbsc_world_presence_mutex};
        bbsc_world_bootstrap_scope=scope;bbsc_world_bootstrap_load=load;bbsc_world_bootstrap_session=session;}
    BBSC_TIMELINE("WORLD","native world ready before events map={:#x} load={} flag_groups={:#x}",scope.map,load,
        it==bbsc_independent_states.end()?0:it->second.present);
    return false;
}

void BbscWorldPublishFlags(const World::Scope& scope,const BbscWorldState& state,u32 owner,u64 epoch,u64 seq) {
    for(u8 part=0;part<4;++part){
        BbscWorldFlagPart p;p.first=part*8;p.count=std::min<u8>(8,30-p.first);p.present=state.present;
        for(size_t j=0;j<p.count;++j) {
            const size_t index=p.first+j;
            if(!(p.present&(u64{1}<<index))) continue;
            p.groups[j]=state.groups[index];
            MaskBbscSharedFlagGroup(BbscWorldGroupKey(scope.map,index),p.groups[j].data());
        }
        World::Control c;c.kind=World::ControlKind::Flags;c.scope=scope;c.owner=owner;c.epoch=epoch;c.sequence=seq;c.parts=4;c.part=part;
        BbscWorldSend(c,{reinterpret_cast<const u8*>(&p),sizeof(p)});
    }
}
void BbscWorldReceiveAltar(const BbscWorldIncoming& message) {
    if(message.payload.size()!=sizeof(BbscWorldAltarWire)) return;
    BbscWorldAltarWire p;std::memcpy(&p,message.payload.data(),sizeof(p));
    const auto& c=message.control;
    World::WorldId world;
    {std::scoped_lock lock{bbsc_world_presence_mutex};world=bbsc_world_presence_local.world;}
    if(message.sender!=world.host || c.scope.world!=world || p.slot>=7 || p.current!=0xFF && p.current>=7 ||
       p.occupied>1 || (p.native_lamps&~u64{0xFFFFF}) || !p.ritual || c.parts!=7 || c.part!=p.slot || !p.revision) return;
    BbscWorldAltar a;a.entry.occupied=p.occupied;a.entry.ritual=p.ritual;a.entry.record=p.record;a.native_lamps=p.native_lamps;
    if(p.occupied){a.mount=p.mount;a.entry.dungeon=p.mount.key;a.entry.form=BbscWorldLayoutProof(p.mount);
        for(size_t i=0;i<4;++i)a.entry.lamps[i]=(p.lamps&(1u<<i))!=0;
        if(!Chalice::ValidMount(p.mount) || !World::Valid(a.entry))return;
    }
    if(p.revision<bbsc_world_altar_receiving) return;
    if(p.revision!=bbsc_world_altar_receiving){bbsc_world_altar_receiving=p.revision;bbsc_world_altar_parts=0;}
    bbsc_world_altars_assembling[p.slot]=std::move(a);bbsc_world_altar_parts|=1u<<p.slot;
    if(bbsc_world_altar_parts!=0x7F) return;
    World::AltarCatalog catalog;catalog.world=world;catalog.revision=p.revision;
    for(size_t i=0;i<7;++i) catalog.altars[i]=bbsc_world_altars_assembling[i].entry;
    bbsc_world_guest_altars.Bind(world);
    if(!bbsc_world_guest_altars.Take(message.sender,std::move(catalog)))return;
    {std::scoped_lock lock{bbsc_world_presence_mutex};bbsc_world_altars=bbsc_world_altars_assembling;
        bbsc_world_altar_current=p.current==0xFF?-1:p.current;}
    if(!bbsc_world_catalog_ready.exchange(true)) {
        const auto occupied=std::ranges::count_if(bbsc_world_altars,[](const auto& a){return a.entry.occupied;});
        BBSC_TIMELINE("TRAVEL","host altar catalog ready occupied={}",occupied);
    }
    // Network packets are drained on the game thread. Reapply only on a complete
    // new host catalog; a loading table is installed by the native event barrier.
    const u64 global=GetGlobalState();
    if(ReadablePointer(global,0x10) && !ReadValue<u8>(global,8))
        BbscWorldApplyAltars(GetCurrentPackedMap());
}

#include "core/bbsc_world_lamps.inc"

void TickBbscWorldSnapshots() {
    std::deque<BbscWorldIncoming> incoming;
    {std::scoped_lock lock{bbsc_independent_incoming_mutex};incoming.swap(bbsc_independent_incoming);}
    if (BbscNativeFinaleCommitted()) return;
    World::Presence local;{std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;}
    if(local.world!=bbsc_world_states_world){bbsc_independent_states.clear();bbsc_world_states_world=local.world;}
    const u32 self=BbscMod::RegisterOwnId();const bool host=self && self==local.world.host;
    for(const auto& message:incoming){const auto& c=message.control;
        if(c.scope.world!=local.world)continue;
        if(c.kind==World::ControlKind::BlockOffer || c.kind==World::ControlKind::BlockLease){
            BbscWorldReceiveBlock(message);continue;
        }
        if(c.kind==World::ControlKind::Lamps){BbscWorldReceiveLamps(message);continue;}
        if(c.kind==World::ControlKind::LampCheckpoint){BbscWorldReceiveLampCheckpoint(message);continue;}
        if(c.kind==World::ControlKind::NativeInitialRequest || c.kind==World::ControlKind::NativeInitialReady){
            BbscWorldNativeInitialControl(message);continue;
        }
        if(c.kind==World::ControlKind::Altar){BbscWorldReceiveAltar(message);continue;}
        if(c.kind==World::ControlKind::AltarProgress && host && BbscIndependentActive() && message.payload.size()==sizeof(BbscWorldAltarProgress)) {
            BbscWorldAltarProgress p;std::memcpy(&p,message.payload.data(),sizeof(p));
            World::OwnerLease owner;
            {std::scoped_lock lock{bbsc_world_presence_mutex};if(const auto* lease=bbsc_independent_owners.Find(c.scope);lease)owner=*lease;}
            if(p.slot>=7 || p.reserved!=std::array<u8,7>{} || !owner.owner || owner.owner!=message.sender ||
               owner.epoch!=c.epoch || p.ritual!=bbsc_world_altars[p.slot].entry.ritual ||
               c.scope.dungeon!=bbsc_world_altars[p.slot].mount.key || c.scope.ritual!=p.ritual)continue;
            const u32 key=94000+p.slot*100+5;const u64 storage=BbscFlagGroupStorage(key);if(!storage)continue;
            auto* live=reinterpret_cast<u8*>(storage);
            for(size_t i=0;i<125;++i)live[i]=(live[i]&~p.mask[i])|(p.bits[i]&p.mask[i]);
            bbsc_world_altars_dirty=true;
            continue;
        }
        if(c.kind==World::ControlKind::Request){
            World::OwnerLease provider;
            {std::scoped_lock lock{bbsc_world_presence_mutex};if(const auto* lease=bbsc_independent_owners.Find(c.scope))provider=*lease;}
            if(!host && provider.owner!=self)continue;
            if(Chalice::IsMap(c.scope.map)) {
                const bool known=std::ranges::any_of(bbsc_world_altars,[&](const auto& a){return a.entry.occupied &&
                    a.entry.ritual==c.scope.ritual && a.mount.key==c.scope.dungeon;});if(!known)continue;
            }
            BbscWorldEnsureSeed(c.scope);
            auto it=bbsc_independent_states.find(c.scope);
            if(it==bbsc_independent_states.end() || !BbscWorldFlagsReady(c.scope))continue;
            // Proxy the owner's revision unchanged. A coordinator-local number
            // would fence out subsequent legitimate native-owner updates.
            const u64 seq=it->second.sequence;
            const u32 source=provider.owner?provider.owner:self;
            BbscWorldPublishFlags(c.scope,it->second,source,it->second.epoch,seq);
            continue;
        }
        if(c.kind!=World::ControlKind::Flags)continue; // obsolete enemy-control packets are ignored
        const bool from_host=message.sender==local.world.host;
        World::OwnerLease owner;
        {std::scoped_lock lock{bbsc_world_presence_mutex};const auto* lease=bbsc_independent_owners.Find(c.scope);if(lease)owner=*lease;}
        if(!from_host && (!host || !owner.owner || owner.owner!=message.sender || owner.epoch!=c.epoch))continue;
        auto& state=bbsc_independent_states[c.scope];
        if(c.kind==World::ControlKind::Flags && (c.epoch<state.epoch || (c.epoch==state.epoch && c.sequence<state.sequence)))continue;
        if(c.kind==World::ControlKind::Flags && message.payload.size()==sizeof(BbscWorldFlagPart)){
            BbscWorldFlagPart p;std::memcpy(&p,message.payload.data(),sizeof(p));
            if(c.parts!=4 || c.part>=4 || p.first!=c.part*8 || p.count!=std::min<unsigned>(8,30-p.first) || p.reserved || p.present>>30)continue;
            if(c.epoch!=state.epoch || c.sequence!=state.sequence){state.parts=0;state.flags_ready=false;}
            state.epoch=c.epoch;state.sequence=c.sequence;state.present=p.present;
            for(size_t j=0;j<p.groups.size();++j){
                const size_t index=p.first+j;
                if(j>=p.count || !(p.present&(u64{1}<<index))){
                    p.groups[j].fill(0);
                    continue;
                }
                MaskBbscSharedFlagGroup(BbscWorldGroupKey(c.scope.map,index),p.groups[j].data());
                state.groups[index]=p.groups[j];
            }
            state.parts|=1u<<c.part;state.flags_ready=state.parts==15;
            if(host && !from_host) BbscWorldSend(c,{reinterpret_cast<const u8*>(&p),sizeof(p)});
        }else continue;
        if(c.kind==World::ControlKind::Flags && state.flags_ready){
            BbscWorldRememberProgress(c.scope,state);BbscWorldRememberLampSnapshot(c.scope,state);
        }
        if(BbscIndependentActive() &&
           (World::ShouldApplyFlags(c,World::ScopeOf(local),self,owner.owner,host,state.flags_ready) ||
            (host && !from_host && Chalice::IsMap(c.scope.map) && state.flags_ready)))
            BbscWorldApplyFlags(c.scope,state);
    }
    if(!BbscIndependentActive() || local.phase!=World::Phase::Playing || !World::Valid(World::ScopeOf(local)) ||
       local.map!=GetCurrentPackedMap() || BbscCurtainActive() || bbsc_world_load_pending.load() || bbsc_reload_finish_pending.load() || !BbscWorldSceneReady())return;
    const auto scope=World::ScopeOf(local);const u32 role=bbsc_independent_role.load();
    World::OwnerLease lease;{std::scoped_lock lock{bbsc_world_presence_mutex};if(const auto* p=bbsc_independent_owners.Find(scope);p)lease=*p;}
    auto& saved=bbsc_independent_states[scope];
    // Native NPC ownership/replication owns HP, death, transforms and handover.
    // No historical kills, actor-state cache, or manual takeover positions.
    static s64 last=0;const s64 now=SteadyNowMs();if(now-last<500)return;last=now;
    if(role!=1) return;
    if(Chalice::IsMap(scope.map))for(auto& progress:bbsc_world_altar_progress) {
        if(progress.ritual!=scope.ritual || std::ranges::none_of(progress.mask,[](u8 b){return b!=0;}))continue;
        World::Control c;c.kind=World::ControlKind::AltarProgress;c.scope=scope;c.owner=self;c.epoch=lease.epoch;
        c.sequence=++bbsc_world_state_sequence;
        BbscWorldSend(c,{reinterpret_cast<const u8*>(&progress),sizeof(progress)});
        // Repeat until a host catalog acknowledges these exact bits.
        const auto& record=bbsc_world_altars[progress.slot].entry.record;
        bool acknowledged=true;for(size_t i=0;i<125;++i)
            acknowledged&=(record[625+i]&progress.mask[i])==(progress.bits[i]&progress.mask[i]);
        if(acknowledged)progress.mask.fill(0);
    }
    auto next=BbscWorldCaptureFlags(scope);if(!next.flags_ready)return;next.epoch=lease.epoch;next.sequence=++bbsc_world_state_sequence;
    saved=std::move(next);
    BbscWorldRememberLampSnapshot(scope,saved);
    BbscWorldRememberProgress(scope,saved);
    BbscWorldPublishFlags(scope,saved,self,lease.epoch,saved.sequence);
}

void TickBbscWorldAltars() {
    World::Presence local;{std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;}
    if(bbsc_world_altar_world!=local.world){
        std::scoped_lock lock{bbsc_world_presence_mutex};bbsc_world_altar_world=local.world;
        bbsc_world_altar_revision=bbsc_world_altar_receiving=0;bbsc_world_altar_parts=0;
        bbsc_world_altars={};bbsc_world_catalog_ready=false;bbsc_world_altar_visiting=-1;
        bbsc_world_altar_progress={};
        bbsc_world_altars_dirty=true;
        bbsc_world_requested_mount.reset();bbsc_world_requested_scope.reset();bbsc_world_guest_altars.Bind(local.world);
    }
    if(!World::Valid(local.world))return;
    const u64 global=GetGlobalState();if(!ReadablePointer(global,0x10)||ReadValue<u8>(global,8))return;
    if(GetSessionState()==3){
        static u64 last_load=~u64{0};const u64 load=bbsc_world_native_load.load();
        if(last_load!=load){last_load=load;bbsc_world_altars_dirty=true;}
        if(bbsc_world_altars_dirty.exchange(false)){
            auto next=bbsc_world_altars;
            for(s32 i=0;i<7;++i) {
                BbscWorldAltar a;if(!BbscWorldReadAltar(i,a)){bbsc_world_altars_dirty=true;return;}
                const bool same=a.entry.occupied==next[i].entry.occupied &&
                    std::equal(a.entry.record.begin(),a.entry.record.begin()+World::AltarProgressAt,next[i].entry.record.begin());
                u64 generation=next[i].entry.ritual>>3;
                if(!same || !generation)++generation;
                a.entry.ritual=(generation<<3)|static_cast<u64>(i+1);
                a.mount.revision=a.entry.ritual;
                next[i]=std::move(a);
            }
            s32 current=-1;for(s32 i=0;i<7;++i)if(BbscEventFlag(9020+i))current=i;
            bool changed=!bbsc_world_catalog_ready.load() || current!=bbsc_world_altar_current;
            for(size_t i=0;i<7;++i)changed|=next[i].entry!=bbsc_world_altars[i].entry || next[i].mount!=bbsc_world_altars[i].mount || next[i].native_lamps!=bbsc_world_altars[i].native_lamps;
            {std::scoped_lock lock{bbsc_world_presence_mutex};bbsc_world_altars=next;bbsc_world_altar_current=current;}
            if(changed)++bbsc_world_altar_revision;
            bbsc_world_catalog_ready=true;
        }
        // Retransmit the same revision for late arrivals/lost packets. Native
        // flags are read only after a write/load, and visitors apply each revision once.
        static s64 last=0;const s64 now=SteadyNowMs();
        static u64 sent_revision=0;
        if(sent_revision==bbsc_world_altar_revision && now-last<1000)return;
        if(!bbsc_world_catalog_ready.load())return;
        last=now;sent_revision=bbsc_world_altar_revision;
        for(u8 i=0;i<7;++i){const auto& altar=bbsc_world_altars[i];BbscWorldAltarWire p;p.slot=i;p.occupied=altar.entry.occupied;p.current=bbsc_world_altar_current<0?0xFF:bbsc_world_altar_current;
            p.revision=bbsc_world_altar_revision;p.ritual=altar.entry.ritual;p.record=altar.entry.record;p.mount=altar.mount;p.native_lamps=altar.native_lamps;
            for(size_t j=0;j<4;++j)if(altar.entry.lamps[j])p.lamps|=1u<<j;
            World::Control c;c.kind=World::ControlKind::Altar;c.scope={local.world,0x15000000,{},0};c.part=i;c.parts=7;
            BbscWorldSend(c,{reinterpret_cast<const u8*>(&p),sizeof(p)});
        }
    }
}
#endif
