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
    bool flags_ready=false;
};
std::map<World::Scope,BbscWorldState> bbsc_independent_states; // game thread only
u64 bbsc_world_state_sequence=0;
World::WorldId bbsc_world_states_world{};

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
bool BbscWorldHasSnapshot(u32 map) {
    if(!BbscIndependentActive()) return false;
    World::Scope scope;
    {std::scoped_lock lock{bbsc_world_presence_mutex};scope=World::ScopeOf(bbsc_world_presence_local);}
    if(bbsc_world_requested_scope && bbsc_world_requested_scope->map==map) scope=*bbsc_world_requested_scope;
    scope.map=map;
    const auto it=bbsc_independent_states.find(scope);
    return it!=bbsc_independent_states.end() && it->second.flags_ready;
}
void ApplyBbscIndependentAtLoad(u32 map) {
    if(!BbscIndependentActive()) return;
    World::Scope scope;
    {std::scoped_lock lock{bbsc_world_presence_mutex};scope=World::ScopeOf(bbsc_world_presence_local);}
    if(bbsc_world_requested_scope) scope=*bbsc_world_requested_scope;
    scope.map=map;
    if(auto it=bbsc_independent_states.find(scope);it!=bbsc_independent_states.end()) BbscWorldApplyFlags(scope,it->second);
    if(map==BbscDreamStateMap && GetSessionState()==6)ApplyBbscHostDreamState("independent arrival");
    if(Chalice::IsMap(map)) CompleteBbscChaliceLoad(map);
    ApplyBbscHostTime("independent world arrival");
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
void BbscWorldTakeEnemy(u64 chr,const BbscWorldEnemy& e,bool position) {
    const u64 modules=ReadValue<u64>(chr,0x3B0);
    const u64 stats=ReadablePointer(modules,0x28)?ReadValue<u64>(modules,0x20):0;
    if(!ReadablePointer(stats,0x100)) return;
    const s32 maximum=ReadValue<s32>(stats,0xFC);if(maximum<=0) return;
    const s32 hp=static_cast<s32>(static_cast<std::int64_t>(e.hp)*maximum/e.max);
    using SetHp=void PS4_SYSV_ABI (*)(u64,s32);
    reinterpret_cast<SetHp>(image_base+0x018BCD40)(chr,hp);
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
        if(e.fighting && GetCharacterHp(GetLocalPlayerCharacter())>0) {
            const u64 ai=ReadValue<u64>(chr,0x3B8),a=ReadablePointer(ai,0xB8)?ReadValue<u64>(ai,0xB0):0;
            const u64 target=ReadablePointer(a,0x568)?ReadValue<u64>(a,0x560):0;
            if(ReadablePointer(target,0x20)) {
                using Add=bool PS4_SYSV_ABI (*)(u64,u32,u64,u32,u64);
                reinterpret_cast<Add>(image_base+0x012B2960)(target+0x10,0,GetLocalPlayerCharacter(),0,ReadValue<u64>(target,8));
            }
        }
    }
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
        bbsc_world_altar_current=p.current==0xFF?-1:p.current;}
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
        if(c.kind==World::ControlKind::Request && host){
            if(Chalice::IsMap(c.scope.map)) {
                const bool known=std::ranges::any_of(bbsc_world_altars,[&](const auto& a){return a.entry.occupied &&
                    a.entry.ritual==c.scope.ritual && a.mount.key==c.scope.dungeon;});if(!known)continue;
            }
            auto it=bbsc_independent_states.find(c.scope);
            if(it==bbsc_independent_states.end())it=bbsc_independent_states.emplace(c.scope,BbscWorldCaptureFlags(c.scope)).first;
            const u64 seq=++bbsc_world_state_sequence;
            BbscWorldPublishFlags(c.scope,it->second,self,it->second.epoch,seq);
            BbscWorldPublishEnemies(c.scope,it->second,self,it->second.epoch,seq);continue;
        }
        if(c.kind!=World::ControlKind::Flags && c.kind!=World::ControlKind::Enemies)continue;
        const bool from_host=message.sender==local.world.host;
        World::OwnerLease owner;
        {std::scoped_lock lock{bbsc_world_presence_mutex};const auto* lease=bbsc_independent_owners.Find(c.scope);if(lease)owner=*lease;}
        if(!from_host && (!host || !owner.owner || owner.owner!=message.sender || owner.epoch!=c.epoch))continue;
        auto& state=bbsc_independent_states[c.scope];
        if(c.epoch<state.epoch || (c.epoch==state.epoch && c.sequence<state.sequence))continue;
        if(c.kind==World::ControlKind::Flags && message.payload.size()==sizeof(BbscWorldFlagPart)){
            BbscWorldFlagPart p;std::memcpy(&p,message.payload.data(),sizeof(p));
            if(c.parts!=4 || p.first!=c.part*8 || p.count!=std::min<unsigned>(8,30-p.first) || p.reserved || p.present>>30)continue;
            if(c.epoch!=state.epoch || c.sequence!=state.sequence){state.parts=0;state.flags_ready=false;}
            state.epoch=c.epoch;state.sequence=c.sequence;state.present=p.present;
            for(size_t j=0;j<p.count;++j)state.groups[p.first+j]=p.groups[j];
            state.parts|=1u<<c.part;state.flags_ready=state.parts==15;
        } else if(c.kind==World::ControlKind::Enemies && message.payload.size()%sizeof(BbscWorldEnemy)==0){
            for(size_t i=0;i<message.payload.size();i+=sizeof(BbscWorldEnemy)){
                BbscWorldEnemy e;std::memcpy(&e,message.payload.data()+i,sizeof(e));
                if(BbscWorldEnemyValid(e))state.enemies[e.handle]=e;
            }
        }else continue;
        if(host && !from_host){World::Control forwarded=c;BbscWorldSend(forwarded,message.payload);}
        if(BbscIndependentActive() && World::ShouldApplyFlags(c,World::ScopeOf(local),self,owner.owner,host,state.flags_ready))
            BbscWorldApplyFlags(c.scope,state);
    }
    if(!BbscIndependentActive() || local.phase!=World::Phase::Playing || !World::Valid(World::ScopeOf(local)))return;
    const auto scope=World::ScopeOf(local);const u32 role=bbsc_independent_role.load();
    World::OwnerLease lease;{std::scoped_lock lock{bbsc_world_presence_mutex};if(const auto* p=bbsc_independent_owners.Find(scope);p)lease=*p;}
    static World::Scope previous_scope;static u64 previous_epoch=0;
    const bool changed=previous_scope!=scope || previous_epoch!=lease.epoch;
    auto& saved=bbsc_independent_states[scope];
    const u64 world=ReadValue<u64>(image_base+CandidateLocalStatePointerOffset,0);
    const auto players=BbscWorldPlayers(world);const u64 doll=BbscWorldDoll(world);
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
    BbscWorldCharacters(world,[&](u64 chr){if(players.contains(chr)||chr==doll||next.enemies.size()>=1024)return;
        const auto at=ReadCharacterTransform(chr);const s32 hp=GetCharacterHp(chr);
        const u64 modules=ReadValue<u64>(chr,0x3B0),stats=ReadablePointer(modules,0x28)?ReadValue<u64>(modules,0x20):0;
        if(!at || !ReadablePointer(stats,0x100) || hp<0)return;
        BbscWorldEnemy e;e.handle=ReadValue<u32>(chr,0x90);e.hp=hp;e.max=ReadValue<s32>(stats,0xFC);
        e.x=at->position[0];e.y=at->position[1];e.z=at->position[2];e.heading=at->rotation[1];
        const u64 ai=ReadValue<u64>(chr,0x3B8),a=ReadablePointer(ai,0xB8)?ReadValue<u64>(ai,0xB0):0;
        const u64 target=ReadablePointer(a,0x568)?ReadValue<u64>(a,0x560):0;
        e.fighting=ReadablePointer(target,0x20)&&ReadValue<u64>(target,0x18)!=0;
        if(BbscWorldEnemyValid(e))next.enemies[e.handle]=e;
    });
    saved=std::move(next);
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
        for(u8 i=0;i<7;++i){BbscWorldAltarWire p;p.slot=i;p.occupied=next[i].entry.occupied;p.current=current<0?0xFF:current;
            p.revision=bbsc_world_altar_revision;p.ritual=next[i].entry.ritual;p.record=next[i].entry.record;p.mount=next[i].mount;
            for(size_t j=0;j<4;++j)if(next[i].entry.lamps[j])p.lamps|=1u<<j;
            World::Control c;c.kind=World::ControlKind::Altar;c.scope={local.world,0x15000000,{},0};c.part=i;c.parts=7;
            BbscWorldSend(c,{reinterpret_cast<const u8*>(&p),sizeof(p)});
        }
    }else if(GetSessionState()==6 && BbscIndependentActive() && GetCurrentPackedMap()==0x15000000 && bbsc_world_catalog_ready.load()) {
        for(size_t i=0;i<7;++i)for(size_t j=0;j<6;++j){const u32 key=94000+i*100+j;
            const u64 p=BbscFlagGroupStorage(key);if(!p)continue;
            KeepBbscOwnWorldGroup(key,reinterpret_cast<const u8*>(p));
            std::memcpy(reinterpret_cast<void*>(p),bbsc_world_altars[i].entry.record.data()+j*125,125);
        }
    }
}
#endif
