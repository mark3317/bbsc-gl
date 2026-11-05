// SPDX-License-Identifier: GPL-2.0-or-later
#ifdef BBSC_MOD
// Native altar records contain the decoded layout too. 01928680 reads it via
// these same read-only getters before 01928987 commits the loader. This avoids
// requiring the host to enter a dungeon merely to make its descriptor available.
struct BbscWorldAltar {
    World::AltarEntry entry;
    Chalice::Mount mount{};
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
u64 bbsc_world_shared_lamps=0;

u32 BbscWorldLampFlag(s32 point) {
    const u32 layer=static_cast<u32>(point)%10000-2950;
    return 10'000'000+static_cast<u32>(point/10000)*10000+7810+layer*20;
}
u64 BbscWorldReadLamps() {
    u64 bits=0;
    for(size_t i=0;i<LampTravel::Returns.size();++i)
        if(BbscEventFlag(BbscWorldLampFlag(LampTravel::Returns[i].point)))bits|=u64{1}<<i;
    return bits;
}
void BbscWorldApplyLamps() {
    if(!BbscIndependentActive() || GetSessionState()!=6 || !bbsc_world_catalog_ready.load())return;
    // Same kind1 shared progress as doors/bosses. Only lamp bits are exposed in
    // Dream; personal services/items and chalice ritual namespaces stay separate.
    for(size_t i=0;i<LampTravel::Returns.size();++i){
        const u32 flag=BbscWorldLampFlag(LampTravel::Returns[i].point),key=flag/1000;
        const u64 p=BbscFlagGroupStorage(key);if(!p)continue;
        auto* bytes=reinterpret_cast<u8*>(p);KeepBbscOwnWorldGroup(key,bytes);
        const size_t byte=flag%1000/8;const u8 mask=0x80u>>(flag%8);
        if(bbsc_world_shared_lamps&(u64{1}<<i)){
            bytes[byte]|=mask;
            if(BbscSharedProgressEnabled()) {std::scoped_lock lock{bbsc_progress_mutex};bbsc_progress_groups[key][byte]|=mask;}
        }else bytes[byte]&=~mask;
    }
}

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
    return BbscIndependentActive() && GetSessionState()==6 &&
           flag>=94'000'000 && Chalice::TouchesAltar(flag,width);
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
    // Progress itself is carried in the full record. The native menu decides
    // the unlocked layer list; all requests are checked against that record.
    out.entry.lamps.fill(true);
    out.mount.revision=1;
    return Chalice::ValidMount(out.mount);
}

#pragma pack(push,1)
struct BbscWorldAltarWire {
    u8 slot=0,occupied=0,current=0xFF,lamps=0;
    u64 revision=0,ritual=0;
    u64 shared_lamps=0;
    World::AltarRecord record{};
    Chalice::Mount mount{};
};
struct BbscWorldFlagPart {
    u8 first=0,count=0;std::uint16_t reserved=0;
    u64 present=0;
    std::array<std::array<u8,125>,8> groups{};
};
struct BbscWorldEnemy {
    u32 handle=0;s32 hp=0,max=0;float x=0,y=0,z=0,heading=0;
    u8 fighting=0;std::array<u8,3> padding{};
};
struct BbscWorldAltarProgress {
    u8 slot=0;std::array<u8,7> reserved{};u64 ritual=0;
    std::array<u8,125> mask{},bits{};
};
#pragma pack(pop)
std::array<BbscWorldAltarProgress,7> bbsc_world_altar_progress;

void QueueBbscWorldAltarWrite(u32 flag,u32 width,u32 value) {
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
struct BbscWorldState {
    u64 epoch=0,sequence=0,present=0;
    u32 parts=0;
    std::array<std::array<u8,125>,30> groups{};
    std::map<u32,BbscWorldEnemy> enemies;
    std::map<u32,BbscWorldEnemy> incoming_enemies;
    u64 enemy_epoch=0,enemy_sequence=0;
    u32 enemy_parts=0,enemy_part_count=0;
    bool enemies_ready=false;
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
    for(size_t i=0;i<30;++i) {
        if(!(state.present&(u64{1}<<i))) continue;
        const u32 key=BbscWorldGroupKey(scope.map,i);const u64 storage=BbscFlagGroupStorage(key);
        if(!storage) continue;
        auto* live=reinterpret_cast<u8*>(storage);
        std::array<u8,125> before;std::memcpy(before.data(),live,125);
        if(guest) KeepBbscOwnWorldGroup(key,live);
        Chalice::CopyHostFlagGroup(key,live,state.groups[i]);
        KeepBbscGuestTalkBits(key,before.data(),live);
        KeepBbscNpcOwnBits(key,before.data(),live);
    }
}
BbscWorldState BbscWorldCaptureFlags(const World::Scope& scope) {
    BbscWorldState state;
    state.flags_ready=true;
    if(Chalice::IsMap(scope.map)) {
        World::Scope current;
        {std::scoped_lock lock{bbsc_world_presence_mutex};current=World::ScopeOf(bbsc_world_presence_local);}
        // m29's live flags belong to one mounted ritual only. An unvisited cup
        // initializes from its own complete altar record, not another cup's flags.
        if(current.dungeon!=scope.dungeon || current.ritual!=scope.ritual) return state;
    }
    for(size_t i=0;i<30;++i) if(const u64 p=BbscFlagGroupStorage(BbscWorldGroupKey(scope.map,i));p){
        state.present|=u64{1}<<i;std::memcpy(state.groups[i].data(),reinterpret_cast<const void*>(p),125);}
    return state;
}
bool BbscWorldFlagsReady(const World::Scope& scope) {
    const auto it=bbsc_independent_states.find(scope);
    if(it==bbsc_independent_states.end() || !it->second.flags_ready)return false;
    const bool ritual_seed=it->second.epoch==0 && Chalice::IsMap(scope.map) && std::ranges::any_of(bbsc_world_altars,[&](const auto& a){
        return a.entry.occupied && a.entry.ritual==scope.ritual && a.mount.key==scope.dungeon;});
    if(!(it->second.present&1) && !ritual_seed)return false;
    std::scoped_lock lock{bbsc_world_presence_mutex};
    const auto* owner=bbsc_independent_owners.Find(scope);
    return !owner || it->second.epoch==owner->epoch ||
        (owner->owner==BbscMod::RegisterOwnId() && it->second.epoch<owner->epoch);
}
void BbscWorldEnsureSeed(const World::Scope& scope) {
    if(BbscMod::RegisterOwnId()!=scope.world.host || BbscWorldFlagsReady(scope))return;
    {std::scoped_lock lock{bbsc_world_presence_mutex};
        if(const auto* owner=bbsc_independent_owners.Find(scope);owner && owner->owner!=scope.world.host)return;}
    // An unvisited location starts with the session world's existing story.
    // A location already owned by another player is NEVER recaptured here.
    auto seed=BbscWorldCaptureFlags(scope);seed.sequence=++bbsc_world_state_sequence;
    bbsc_independent_states[scope]=std::move(seed);
}
bool BbscWorldHasSnapshot(u32 map) {
    if(!BbscIndependentActive()) return false;
    World::Scope scope;
    {std::scoped_lock lock{bbsc_world_presence_mutex};scope=World::ScopeOf(bbsc_world_presence_local);}
    if(bbsc_world_requested_scope && (bbsc_world_requested_scope->map==map ||
       (Chalice::IsMap(bbsc_world_requested_scope->map) && Chalice::IsMap(map)))) scope=*bbsc_world_requested_scope;
    scope.map=Chalice::IsMap(map)?0x1D000000:map;
    return BbscWorldFlagsReady(scope);
}
void ApplyBbscIndependentAtLoad(u32 map) {
    if(!BbscIndependentActive()) return;
    World::Scope scope;
    {std::scoped_lock lock{bbsc_world_presence_mutex};scope=World::ScopeOf(bbsc_world_presence_local);}
    if(bbsc_world_requested_scope) scope=*bbsc_world_requested_scope;
    scope.map=Chalice::IsMap(map)?0x1D000000:map;
    if(auto it=bbsc_independent_states.find(scope);it!=bbsc_independent_states.end()) BbscWorldApplyFlags(scope,it->second);
    if(map==BbscDreamStateMap && GetSessionState()==6)ApplyBbscHostDreamState("independent arrival");
    if(Chalice::IsMap(map)) CompleteBbscChaliceLoad(map);
    ApplyBbscHostTime("independent world arrival");
}

World::Scope bbsc_world_bootstrap_scope{};
u64 bbsc_world_bootstrap_load=~u64{0};
bool BbscWorldSceneReady() {
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
    if(!BbscIndependentTravelAllowed() || !ReadablePointer(instance,0xC0))return false;
    World::Scope scope;
    {std::scoped_lock lock{bbsc_world_presence_mutex};scope=World::ScopeOf(bbsc_world_presence_local);}
    const u32 raw=GetCurrentPackedMap();if(!World::ValidMap(raw))return true;
    scope.map=Chalice::IsMap(raw)?0x1D000000:raw;
    if(!Chalice::IsMap(raw)){scope.dungeon={};scope.ritual=0;}
    if(Chalice::IsMap(raw) && bbsc_world_requested_scope && bbsc_world_requested_scope->world==scope.world)
        scope=*bbsc_world_requested_scope;
    const u64 load=bbsc_world_native_load.load();
    if(bbsc_world_bootstrap_load==load && bbsc_world_bootstrap_scope==scope)return false;
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
    u32 owner=0;u64 epoch=0;
    {std::scoped_lock lock{bbsc_world_presence_mutex};if(const auto* lease=bbsc_independent_owners.Find(scope)){owner=lease->owner;epoch=lease->epoch;}}
    if(scope.map!=BbscDreamStateMap && owner && owner!=BbscMod::RegisterOwnId() &&
       (it==bbsc_independent_states.end() || !it->second.enemies_ready || it->second.enemy_epoch!=epoch))return true;
    if(!BbscWorldNativePeerReady(owner))return true;
    if(it!=bbsc_independent_states.end())BbscWorldApplyFlags(scope,it->second);
    if(scope.map==BbscDreamStateMap && GetSessionState()==6)ApplyBbscHostDreamState("before native events");
    {std::scoped_lock lock{bbsc_world_presence_mutex};
        bbsc_world_bootstrap_scope=scope;bbsc_world_bootstrap_load=load;}
    BBSC_TIMELINE("WORLD","native world ready before events map={:#x} load={} flag_groups={:#x}",scope.map,load,
        it==bbsc_independent_states.end()?0:it->second.present);
    return false;
}

void BbscWorldPublishFlags(const World::Scope& scope,const BbscWorldState& state,u32 owner,u64 epoch,u64 seq) {
    for(u8 part=0;part<4;++part){
        BbscWorldFlagPart p;p.first=part*8;p.count=std::min<u8>(8,30-p.first);p.present=state.present;
        for(size_t j=0;j<p.count;++j) p.groups[j]=state.groups[p.first+j];
        World::Control c;c.kind=World::ControlKind::Flags;c.scope=scope;c.owner=owner;c.epoch=epoch;c.sequence=seq;c.parts=4;c.part=part;
        BbscWorldSend(c,{reinterpret_cast<const u8*>(&p),sizeof(p)});
    }
}
void BbscWorldPublishEnemies(const World::Scope& scope,const BbscWorldState& state,u32 owner,u64 epoch,u64 seq) {
    std::vector<BbscWorldEnemy> entries;
    for(const auto& [id,e]:state.enemies){entries.push_back(e);if(entries.size()==1024)break;}
    const size_t parts=std::max<size_t>(1,(entries.size()+47)/48);
    for(size_t i=0;i<parts;++i){const size_t first=i*48,n=std::min<size_t>(48,entries.size()-first);
        World::Control c;c.kind=World::ControlKind::Enemies;c.scope=scope;c.owner=owner;c.epoch=epoch;c.sequence=seq;c.parts=parts;c.part=i;
        if(n)BbscWorldSend(c,{reinterpret_cast<const u8*>(entries.data()+first),n*sizeof(BbscWorldEnemy)});
        else BbscWorldSend(c);
    }
}
bool BbscWorldEnemyValid(const BbscWorldEnemy& e) {
    return e.max>0 && e.max<100'000'000 && e.hp>=0 && e.hp<=e.max &&
        e.fighting<=1 && e.padding==std::array<u8,3>{} &&
        std::isfinite(e.x)&&std::isfinite(e.y)&&std::isfinite(e.z)&&std::isfinite(e.heading);
}
bool BbscWorldReceiveEnemies(BbscWorldState& state,const World::Control& c,std::span<const u8> bytes) {
    if(!c.parts || c.parts>22 || c.part>=c.parts || bytes.size()%sizeof(BbscWorldEnemy) ||
       bytes.size()>48*sizeof(BbscWorldEnemy) || c.epoch<state.enemy_epoch ||
       (c.epoch==state.enemy_epoch && c.sequence<state.enemy_sequence))return false;
    std::vector<BbscWorldEnemy> entries;
    for(size_t i=0;i<bytes.size();i+=sizeof(BbscWorldEnemy)){
        BbscWorldEnemy e;std::memcpy(&e,bytes.data()+i,sizeof(e));
        if(!BbscWorldEnemyValid(e))return false;
        entries.push_back(e);
    }
    if(c.epoch!=state.enemy_epoch || c.sequence!=state.enemy_sequence){
        state.incoming_enemies.clear();state.enemy_parts=0;state.enemy_part_count=c.parts;state.enemies_ready=false;
        state.enemy_epoch=c.epoch;state.enemy_sequence=c.sequence;
    }
    if(state.enemy_part_count!=c.parts || (state.enemy_parts&(1u<<c.part)))return false;
    for(const auto& e:entries)state.incoming_enemies[e.handle]=e;
    state.enemy_parts|=1u<<c.part;
    if(state.enemy_parts!=((1u<<c.parts)-1))return false;
    state.enemies=std::move(state.incoming_enemies);state.enemies_ready=true;
    return true;
}
void BbscWorldTakeEnemy(u64 chr,const BbscWorldEnemy& e,bool position) {
    const u64 modules=ReadValue<u64>(chr,0x3B0);
    const u64 stats=ReadablePointer(modules,0x28)?ReadValue<u64>(modules,0x20):0;
    if(!ReadablePointer(stats,0x100)) return;
    const s32 maximum=ReadValue<s32>(stats,0xFC);if(maximum<=0) return;
    const s32 hp=static_cast<s32>(static_cast<std::int64_t>(e.hp)*maximum/e.max);
    using SetHp=void PS4_SYSV_ABI (*)(u64,s32);
    reinterpret_cast<SetHp>(image_base+0x018BCD40)(chr,hp);
    if(hp==0 && !(ReadValue<u8>(chr,0x1E3)&0x25)) {
        // Same no-reward ForceCharacterDeath path as native2004[4] at017BA95A:
        // bit21 suppresses a historical kill's reward, then the game's kill
        // starts its death transition. HP=0 alone leaves a frozen live model.
        if(HasMemoryAccess(chr+0x1E1,4,MemoryProt::CpuWrite)){
            WriteValue<u32>(chr,0x1E1,ReadValue<u32>(chr,0x1E1)|0x200000);
            using Kill=void PS4_SYSV_ABI (*)(u64);
            reinterpret_cast<Kill>(image_base+0x018BF9A0)(chr);
        }
    }
    if(position && hp>0) {
        const u64 vtable=ReadValue<u64>(chr,0),warp=ReadablePointer(vtable,0x600)?ReadValue<u64>(vtable,0x5F8):0;
        if(IsEbootCodeAddress(warp)){
            // Native Warp -> 018CD600 -> 01517200 uses VMOVAPS on BOTH
            // arguments. std::array<float,4> alone guarantees only4-byte alignment.
            alignas(16) std::array<float,4> at{e.x,e.y,e.z,1};
            alignas(16) std::array<float,4> rotation{0,e.heading,0,0};
            using Warp=void PS4_SYSV_ABI (*)(u64,float*,float*,u32);
            reinterpret_cast<Warp>(warp)(chr,at.data(),rotation.data(),1);
        }

    }
}
size_t BbscWorldSeedEnemies(u64 world,const BbscWorldState& state,const std::set<u64>& players,u64 doll,std::map<u32,u64>& seeded) {
    if(!state.flags_ready || !state.enemies_ready)return 0;
    size_t count=0;
    BbscWorldCharacters(world,[&](u64 chr){
        if(players.contains(chr)||chr==doll)return;
        const u32 id=ReadValue<u32>(chr,0x90);const auto it=state.enemies.find(id);
        const u64 activation=ReadValue<u64>(chr,0x18);
        if(it==state.enemies.end() || seeded[id]==chr || !ReadablePointer(activation,0x18) ||
           ReadValue<s32>(activation,0x10)!=4 || ReadValue<s32>(activation,0x14)!=4)return;
        BbscWorldTakeEnemy(chr,it->second,false);seeded[id]=chr;++count;
    });
    return count;
}

void BbscWorldReceiveAltar(const BbscWorldIncoming& message) {
    if(message.payload.size()!=sizeof(BbscWorldAltarWire)) return;
    BbscWorldAltarWire p;std::memcpy(&p,message.payload.data(),sizeof(p));
    const auto& c=message.control;
    World::WorldId world;
    {std::scoped_lock lock{bbsc_world_presence_mutex};world=bbsc_world_presence_local.world;}
    if(message.sender!=world.host || c.scope.world!=world || p.slot>=7 || p.current!=0xFF && p.current>=7 ||
       p.occupied>1 || !p.ritual || c.parts!=7 || c.part!=p.slot || !p.revision) return;
    BbscWorldAltar a;a.entry.occupied=p.occupied;a.entry.ritual=p.ritual;a.entry.record=p.record;
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
        bbsc_world_altar_current=p.current==0xFF?-1:p.current;bbsc_world_shared_lamps=p.shared_lamps;}
    if(!bbsc_world_catalog_ready.exchange(true)) {
        const auto occupied=std::ranges::count_if(bbsc_world_altars,[](const auto& a){return a.entry.occupied;});
        BBSC_TIMELINE("TRAVEL","host altar catalog ready occupied={}",occupied);
    }
}

void TickBbscWorldSnapshots() {
    std::deque<BbscWorldIncoming> incoming;
    {std::scoped_lock lock{bbsc_independent_incoming_mutex};incoming.swap(bbsc_independent_incoming);}
    World::Presence local;{std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;}
    if(local.world!=bbsc_world_states_world){bbsc_independent_states.clear();bbsc_world_states_world=local.world;}
    const u32 self=BbscMod::RegisterOwnId();const bool host=self && self==local.world.host;
    for(const auto& message:incoming){const auto& c=message.control;
        if(c.scope.world!=local.world)continue;
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
            BbscWorldPublishEnemies(c.scope,it->second,source,it->second.epoch,seq);continue;
        }
        if(c.kind!=World::ControlKind::Flags && c.kind!=World::ControlKind::Enemies)continue;
        const bool from_host=message.sender==local.world.host;
        World::OwnerLease owner;
        {std::scoped_lock lock{bbsc_world_presence_mutex};const auto* lease=bbsc_independent_owners.Find(c.scope);if(lease)owner=*lease;}
        if(!from_host && (!host || !owner.owner || owner.owner!=message.sender || owner.epoch!=c.epoch))continue;
        auto& state=bbsc_independent_states[c.scope];
        if(c.kind==World::ControlKind::Flags && (c.epoch<state.epoch || (c.epoch==state.epoch && c.sequence<state.sequence)))continue;
        if(c.kind==World::ControlKind::Flags && message.payload.size()==sizeof(BbscWorldFlagPart)){
            BbscWorldFlagPart p;std::memcpy(&p,message.payload.data(),sizeof(p));
            if(c.parts!=4 || p.first!=c.part*8 || p.count!=std::min<unsigned>(8,30-p.first) || p.reserved || p.present>>30)continue;
            if(c.epoch!=state.epoch || c.sequence!=state.sequence){state.parts=0;state.flags_ready=false;}
            state.epoch=c.epoch;state.sequence=c.sequence;state.present=p.present;
            for(size_t j=0;j<p.count;++j)state.groups[p.first+j]=p.groups[j];
            state.parts|=1u<<c.part;state.flags_ready=state.parts==15;
        } else if(c.kind==World::ControlKind::Enemies && message.payload.size()%sizeof(BbscWorldEnemy)==0){
            BbscWorldReceiveEnemies(state,c,message.payload);
        }else continue;
        if(host && !from_host){World::Control forwarded=c;BbscWorldSend(forwarded,message.payload);}
        if(c.kind==World::ControlKind::Flags && state.flags_ready)BbscWorldRememberProgress(c.scope,state);
        if(BbscIndependentActive() && World::ShouldApplyFlags(c,World::ScopeOf(local),self,owner.owner,host,state.flags_ready))
            BbscWorldApplyFlags(c.scope,state);
    }
    if(!BbscIndependentActive() || local.phase!=World::Phase::Playing || !World::Valid(World::ScopeOf(local)) ||
       local.map!=GetCurrentPackedMap() || BbscCurtainActive() || bbsc_world_load_pending.load() || bbsc_reload_finish_pending.load() || !BbscWorldSceneReady())return;
    const auto scope=World::ScopeOf(local);const u32 role=bbsc_independent_role.load();
    World::OwnerLease lease;{std::scoped_lock lock{bbsc_world_presence_mutex};if(const auto* p=bbsc_independent_owners.Find(scope);p)lease=*p;}
    static World::Scope previous_scope;static u64 previous_epoch=0;
    const bool changed=previous_scope!=scope || previous_epoch!=lease.epoch;
    auto& saved=bbsc_independent_states[scope];
    const u64 world=ReadValue<u64>(image_base+CandidateLocalStatePointerOffset,0);
    const auto players=BbscWorldPlayers(world);const u64 doll=BbscWorldDoll(world);
    static World::Scope seeded_scope;static u64 seeded_visit=0,seeded_epoch=0;
    static std::map<u32,u64> seeded;
    if(seeded_scope!=scope || seeded_visit!=local.visit || seeded_epoch!=lease.epoch){
        seeded.clear();seeded_scope=scope;seeded_visit=local.visit;seeded_epoch=lease.epoch;
    }
    if(role==2 && saved.enemies_ready && saved.enemy_epoch==lease.epoch){
        const size_t count=BbscWorldSeedEnemies(world,saved,players,doll,seeded);
        if(count)BBSC_TIMELINE("WORLD","native enemy baseline map={:#x} owner={:08x} epoch={} applied={}",scope.map,lease.owner,lease.epoch,count);
    }
    if(changed && role==1 && !saved.enemies.empty()) {
        BbscWorldCharacters(world,[&](u64 chr){if(players.contains(chr)||chr==doll)return;
            if(auto it=saved.enemies.find(ReadValue<u32>(chr,0x90));it!=saved.enemies.end()) BbscWorldTakeEnemy(chr,it->second,true);});
        BBSC_TIMELINE("WORLD","map authority acquired map={:#x} epoch={} retained_enemies={}",scope.map,lease.epoch,saved.enemies.size());
    }
    previous_scope=scope;previous_epoch=lease.epoch;
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
    auto next=BbscWorldCaptureFlags(scope);next.epoch=lease.epoch;next.sequence=++bbsc_world_state_sequence;
    // Streamed-out enemies (including kills) remain part of this area's world.
    next.enemies=saved.enemies;
    BbscWorldCharacters(world,[&](u64 chr){if(players.contains(chr)||chr==doll||next.enemies.size()>=1024)return;
        const auto at=ReadCharacterTransform(chr);const s32 hp=GetCharacterHp(chr);
        const u64 modules=ReadValue<u64>(chr,0x3B0),stats=ReadablePointer(modules,0x28)?ReadValue<u64>(modules,0x20):0;
        if(!at || !ReadablePointer(stats,0x100) || hp<0)return;
        BbscWorldEnemy e;e.handle=ReadValue<u32>(chr,0x90);e.hp=hp;e.max=ReadValue<s32>(stats,0xFC);
        e.x=at->position[0];e.y=at->position[1];e.z=at->position[2];e.heading=at->rotation[1];
        if(BbscWorldEnemyValid(e))next.enemies[e.handle]=e;
    });
    saved=std::move(next);
    BbscWorldRememberProgress(scope,saved);
    BbscWorldPublishFlags(scope,saved,self,lease.epoch,saved.sequence);
    BbscWorldPublishEnemies(scope,saved,self,lease.epoch,saved.sequence);
}

void TickBbscWorldAltars() {
    World::Presence local;{std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;}
    if(bbsc_world_altar_world!=local.world){
        std::scoped_lock lock{bbsc_world_presence_mutex};bbsc_world_altar_world=local.world;
        bbsc_world_altar_revision=bbsc_world_altar_receiving=0;bbsc_world_altar_parts=0;
        bbsc_world_altars={};bbsc_world_catalog_ready=false;bbsc_world_altar_visiting=-1;
        bbsc_world_altar_progress={};
        bbsc_world_shared_lamps=0;
        bbsc_world_requested_mount.reset();bbsc_world_requested_scope.reset();bbsc_world_guest_altars.Bind(local.world);
    }
    if(!World::Valid(local.world))return;
    const u64 global=GetGlobalState();if(!ReadablePointer(global,0x10)||ReadValue<u8>(global,8))return;
    static s64 last=0;const s64 now=SteadyNowMs();if(now-last<1000)return;last=now;
    if(GetSessionState()==3){
        auto next=bbsc_world_altars;
        for(s32 i=0;i<7;++i) {
            BbscWorldAltar a;if(!BbscWorldReadAltar(i,a))return;
            const bool same=a.entry.occupied==next[i].entry.occupied &&
                std::equal(a.entry.record.begin(),a.entry.record.begin()+World::AltarProgressAt,next[i].entry.record.begin());
            u64 generation=next[i].entry.ritual>>3;
            if(!same || !generation)++generation;
            a.entry.ritual=(generation<<3)|static_cast<u64>(i+1);
            a.mount.revision=a.entry.ritual;
            next[i]=std::move(a);
        }
        s32 current=-1;for(s32 i=0;i<7;++i)if(BbscEventFlag(9020+i))current=i;
        {std::scoped_lock lock{bbsc_world_presence_mutex};bbsc_world_altars=next;bbsc_world_altar_current=current;}
        ++bbsc_world_altar_revision;bbsc_world_catalog_ready=true;
        const u64 lamps=BbscWorldReadLamps();
        for(u8 i=0;i<7;++i){BbscWorldAltarWire p;p.slot=i;p.occupied=next[i].entry.occupied;p.current=current<0?0xFF:current;
            p.revision=bbsc_world_altar_revision;p.ritual=next[i].entry.ritual;p.record=next[i].entry.record;p.mount=next[i].mount;
            p.shared_lamps=lamps;
            for(size_t j=0;j<4;++j)if(next[i].entry.lamps[j])p.lamps|=1u<<j;
            World::Control c;c.kind=World::ControlKind::Altar;c.scope={local.world,0x15000000,{},0};c.part=i;c.parts=7;
            BbscWorldSend(c,{reinterpret_cast<const u8*>(&p),sizeof(p)});
        }
    }else if(GetSessionState()==6 && BbscIndependentActive() && GetCurrentPackedMap()==0x15000000 && bbsc_world_catalog_ready.load()) {
        BbscWorldApplyLamps();
        for(size_t i=0;i<7;++i)for(size_t j=0;j<6;++j){const u32 key=94000+i*100+j;
            const u64 p=BbscFlagGroupStorage(key);if(!p)continue;
            KeepBbscOwnWorldGroup(key,reinterpret_cast<const u8*>(p));
            std::memcpy(reinterpret_cast<void*>(p),bbsc_world_altars[i].entry.record.data()+j*125,125);
        }
    }
}
#endif
