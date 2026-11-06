// SPDX-License-Identifier: GPL-2.0-or-later
// Additive lamp discoveries use the existing session control channel. Unlike
// map snapshots they are independent of NPC ownership and the receiver's map.
std::map<World::Scope,u64> bbsc_world_lamps,bbsc_world_lamp_pending;
World::WorldId bbsc_world_lamp_world{};
s32 bbsc_world_lamp_menu=-1;
u32 bbsc_world_lamp_menu_load=0;

u32 BbscWorldLampFlag(size_t index,bool dungeon) {
    if(dungeon)return 12907810+static_cast<u32>(index)*20;
    const u32 point=LampTravel::Returns[index].point;
    return 10000000+(point/10000)*10000+7810+(point%10000-2950)*20;
}
size_t BbscWorldLampCount(bool dungeon) {return dungeon?10:LampTravel::Returns.size();}
u64 BbscWorldLampMask(const World::Scope& scope) {
    u64 mask=0;const bool dungeon=Chalice::IsMap(scope.map);
    for(size_t i=0;i<BbscWorldLampCount(dungeon);++i)
        if(dungeon || BbscLampPointMap(LampTravel::Returns[i].point)==scope.map)mask|=u64{1}<<i;
    return mask;
}
bool BbscWorldLampScopeKnown(const World::Scope& scope) {
    return !Chalice::IsMap(scope.map) || std::ranges::any_of(bbsc_world_altars,[&](const auto& a){
        return a.entry.occupied && a.entry.ritual==scope.ritual && a.mount.key==scope.dungeon;});
}
void BbscWorldLampBind(const World::WorldId& world) {
    if(bbsc_world_lamp_world==world)return;
    bbsc_world_lamp_world=world;bbsc_world_lamps.clear();bbsc_world_lamp_pending.clear();
    bbsc_world_lamp_menu=-1;
}
void QueueBbscWorldLampWrite(u32 flag,u32 width,u32 value) {
    if(!BbscIndependentActive() || (GetSessionState()!=3 && GetSessionState()!=6) || !width || width>32)return;
    if(flag/10000000!=1 || flag%10000>7990 || flag%10000+width<=7800)return;
    World::Scope scope;{std::scoped_lock lock{bbsc_world_presence_mutex};scope=World::ScopeOf(bbsc_world_presence_local);}
    if(!World::Valid(scope) || !BbscWorldSceneReady() || !BbscWorldLampScopeKnown(scope) ||
       (Chalice::IsMap(GetCurrentPackedMap())?0x1D000000u:GetCurrentPackedMap())!=scope.map)return;
    BbscWorldLampBind(scope.world);
    const bool dungeon=Chalice::IsMap(scope.map);const u64 allowed=BbscWorldLampMask(scope);
    for(size_t i=0;i<BbscWorldLampCount(dungeon);++i){
        for(u32 delta:{0u,10u}){const u32 f=BbscWorldLampFlag(i,dungeon)-delta;
        if((allowed&(u64{1}<<i)) && f>=flag && f-flag<width && (value&(u32{1}<<(width-1-(f-flag))))){
            if(dungeon && GetSessionState()==6)if(const u64 p=BbscFlagGroupStorage(f/1000))
                KeepBbscOwnWorldGroup(f/1000,reinterpret_cast<const u8*>(p));
            bbsc_world_lamp_pending[scope]|=u64{1}<<i;
            // Preserve already unlocked destinations when this is the first
            // discovery packet for the mounted ritual. The pre-event barrier
            // has installed that ritual's runtime state before interaction.
            if(dungeon)for(size_t j=0;j<10;++j)
                if(BbscEventFlag(BbscWorldLampFlag(j,true)) || BbscEventFlag(BbscWorldLampFlag(j,true)-10))
                    bbsc_world_lamp_pending[scope]|=u64{1}<<j;
        }}
    }
}
void BbscWorldRememberLampSnapshot(const World::Scope& scope,const BbscWorldState& state) {
    if(!state.flags_ready || !BbscIndependentActive() || !BbscWorldLampScopeKnown(scope))return;
    BbscWorldLampBind(scope.world);
    const bool dungeon=Chalice::IsMap(scope.map);u64 bits=0;
    for(size_t i=0;i<BbscWorldLampCount(dungeon);++i){
        for(u32 delta:{0u,10u}){const u32 flag=BbscWorldLampFlag(i,dungeon)-delta;
        for(size_t j=0;j<10;++j)if((state.present&(u64{1}<<j)) && BbscWorldGroupKey(scope.map,j)==flag/1000 &&
            (state.groups[j][flag%1000/8]&(0x80u>>(flag%8))))bits|=u64{1}<<i;
        }
    }
    bits&=BbscWorldLampMask(scope);
    if(bits)bbsc_world_lamp_pending[scope]|=bits;
}
void BbscWorldReceiveLamps(const BbscWorldIncoming& message) {
    const auto& c=message.control;
    if(!BbscIndependentActive() || message.payload.size()!=sizeof(u64) || c.parts!=1 || c.part ||
       !BbscWorldLampScopeKnown(c.scope))return;
    World::Presence local;
    {std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;
        if(message.sender!=local.world.host && !bbsc_world_presence_book.Resident(message.sender))return;}
    if(c.scope.world!=local.world)return;
    const bool host=BbscMod::RegisterOwnId()==local.world.host;
    if(!host && message.sender!=local.world.host)return;
    u64 bits=0;std::memcpy(&bits,message.payload.data(),sizeof(bits));
    if(!bits || (bits&~BbscWorldLampMask(c.scope)))return;
    BbscWorldLampBind(local.world);
    bbsc_world_lamps[c.scope]|=bits;
    if(message.sender==local.world.host)bbsc_world_lamp_pending[c.scope]&=~bits;
}
// Save the personal group BEFORE projecting another ritual's flags. These bits
// remain excluded from shared-progress home merge (including after a crash).
void BbscWorldApplyLampBits(const World::Scope& scope,u64 bits,bool replace) {
    const bool dungeon=Chalice::IsMap(scope.map);
    const u64 allowed=BbscWorldLampMask(scope);
    for(size_t i=0;i<BbscWorldLampCount(dungeon);++i){
        const u64 bit=u64{1}<<i;if(!(allowed&bit) || (!replace && !(bits&bit)))continue;
        for(u32 delta:{0u,10u}){const u32 flag=BbscWorldLampFlag(i,dungeon)-delta;const u64 storage=BbscFlagGroupStorage(flag/1000);
        if(!storage)continue;
        auto* live=reinterpret_cast<u8*>(storage);
        if(GetSessionState()==6)KeepBbscOwnWorldGroup(flag/1000,live);
        const u8 mask=0x80u>>(flag%8);auto& byte=live[flag%1000/8];
        if(bits&bit)byte|=mask;else byte&=~mask;
        if(!dungeon && (bits&bit) && GetSessionState()==6 && BbscSharedProgressEnabled()){
            std::scoped_lock lock{bbsc_progress_mutex};bbsc_progress_groups[flag/1000][flag%1000/8]|=mask;
        }}
    }
}
u64 BbscWorldAltarLampBits(s32 slot) {
    if(slot<0 || slot>=7 || !bbsc_world_altars[slot].entry.occupied)return 0;
    World::WorldId world;
    {std::scoped_lock lock{bbsc_world_presence_mutex};world=bbsc_world_presence_local.world;}
    if(world!=bbsc_world_lamp_world)return 0;
    const auto& a=bbsc_world_altars[slot];
    const World::Scope scope{world,0x1D000000,a.mount.key,a.entry.ritual};
    const auto it=bbsc_world_lamps.find(scope);
    return it==bbsc_world_lamps.end()?0:it->second&BbscWorldLampMask(scope);
}
bool BbscWorldAltarLampUnlocked(s32 slot,s32 layer) {
    if(slot<0 || slot>=7 || !bbsc_world_altars[slot].entry.occupied || layer<0 || layer>=10)return false;
    // The Hall is the native unconditional entry. Never authorize a guest's
    // other destinations from personal/previous-cup runtime flags.
    return layer==0 || (BbscWorldAltarLampBits(slot)&(u64{1}<<layer));
}
void BbscWorldSelectLampMenu(s32 slot) {
    if(!BbscIndependentActive() || (GetSessionState()!=3 && GetSessionState()!=6) ||
       slot<0 || slot>=7 || !bbsc_world_altars[slot].entry.occupied)return;
    bbsc_world_lamp_menu=slot;bbsc_world_lamp_menu_load=bbsc_load_generation.load();
    const auto& a=bbsc_world_altars[slot];
    World::Scope scope{bbsc_world_lamp_world,0x1D000000,a.mount.key,a.entry.ritual};
    // Until this ritual has confirmed discoveries, guests see ONLY the Hall.
    // Missing/zero state must replace personal flags, not inherit their lamps.
    if(GetSessionState()==6)BbscWorldApplyLampBits(scope,BbscWorldAltarLampBits(slot),true);
    else if(const auto it=bbsc_world_lamps.find(scope);it!=bbsc_world_lamps.end())
        BbscWorldApplyLampBits(scope,it->second,true);
}
void TickBbscWorldLamps() {
    World::Presence local;{std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;}
    BbscWorldLampBind(local.world);
    if(!BbscIndependentActive() || (GetSessionState()!=3 && GetSessionState()!=6) || !World::Valid(local.world))return;
    const u64 global=GetGlobalState();if(!ReadablePointer(global,0x10) || ReadValue<u8>(global,8))return;
    static s64 sent=0;const s64 now=SteadyNowMs();if(now-sent<500)return;sent=now;
    const u32 self=BbscMod::RegisterOwnId();const bool host=self==local.world.host;
    // Seed existing world lamps ONLY from the host. Guest personal discoveries
    // are never offered as host progress merely by joining a session.
    static World::WorldId seeded_world{};static u32 seeded_load=~u32{0};
    if(host && (seeded_world!=local.world || seeded_load!=bbsc_load_generation.load())){
        seeded_world=local.world;seeded_load=bbsc_load_generation.load();
        for(size_t i=0;i<LampTravel::Returns.size();++i)if(BbscEventFlag(BbscWorldLampFlag(i,false)) || BbscEventFlag(BbscWorldLampFlag(i,false)-10)){
            World::Scope scope{local.world,BbscLampPointMap(LampTravel::Returns[i].point),{},0};
            bbsc_world_lamps[scope]|=u64{1}<<i;
        }
    }
    for(const auto& [scope,bits]:bbsc_world_lamp_pending)if(host)bbsc_world_lamps[scope]|=bits;
    // Every receiver gets headstone entries even while in another map/Dream.
    for(const auto& [scope,bits]:bbsc_world_lamps)if(!Chalice::IsMap(scope.map))BbscWorldApplyLampBits(scope,bits,false);
    if(Chalice::IsMap(local.map) && BbscWorldSceneReady()){
        const auto scope=World::ScopeOf(local);
        if(const auto it=bbsc_world_lamps.find(scope);it!=bbsc_world_lamps.end())BbscWorldApplyLampBits(scope,it->second,false);
    }else if(local.map==BbscDreamStateMap && bbsc_world_lamp_menu_load==bbsc_load_generation.load())
        BbscWorldSelectLampMenu(bbsc_world_lamp_menu);
    // Repeat canonical state/pending discoveries: packet loss and late join do
    // not require touching a lamp a second time. Old ritual generations expire.
    auto& outgoing=host?bbsc_world_lamps:bbsc_world_lamp_pending;
    std::erase_if(outgoing,[](const auto& item){return !BbscWorldLampScopeKnown(item.first);});
    for(const auto& [scope,bits]:outgoing)if(bits){
        World::Control c;c.kind=World::ControlKind::Lamps;c.scope=scope;c.owner=self;
        BbscWorldSend(c,{reinterpret_cast<const u8*>(&bits),sizeof(bits)});
    }
}
