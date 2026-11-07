// SPDX-License-Identifier: GPL-2.0-or-later
// Native block authority. Control messages contain only native CHR records and
// ownership metadata; live HP/AI/animation/position remain on native channels.
std::atomic<bool> bbsc_world_blocks_active{false};
World::BlockCoordinator bbsc_world_block_coordinator;
std::mutex bbsc_world_block_mutex;
World::WorldId bbsc_world_block_world{};
struct BbscBlockLocal {u64 address=0,load=0,applied_epoch=~u64{0};bool active=false;std::vector<u8> native;bool quiesced=false;};
struct BbscBlockView {World::BlockLease lease;u64 sequence=0,load=~u64{0};};
std::map<std::pair<World::Scope,u32>,BbscBlockView> bbsc_world_block_views;
struct BbscBlockPublication {u64 epoch=0;u32 owner=0;s64 sent=0;std::vector<u8> bytes;};
std::map<std::pair<std::pair<World::Scope,u32>,u32>,BbscBlockPublication> bbsc_world_block_published;
std::map<u32,BbscBlockLocal> bbsc_world_block_local;
std::map<u32,u32> bbsc_world_block_handles;
std::map<u32,u32> bbsc_world_block_players;
std::map<u32,BbscBlockLocal> bbsc_world_block_withdrawn;
std::atomic<u64> bbsc_world_block_sequence{0};
thread_local u32 bbsc_world_block_hp_source=0;
World::Scope bbsc_world_block_scope{};
bool bbsc_world_block_inventory_ready=false;
u64 bbsc_world_block_inventory_load=~u64{0};
// Guarded by block_mutex. A certificate describes metadata, never memory
// access. Capture and accepted leases invalidate it before changing inputs.
u64 bbsc_world_block_admission_revision=0;
u64 bbsc_world_block_admitted_revision=~u64{0};
bool BbscWorldBlocksActive(){return bbsc_world_blocks_active.load();}
bool BbscWorldBlockSimulation(){return BbscWorldBlocksActive() && GetCurrentPackedMap()!=0x15000000;}
void BbscWorldBlockWait(const World::Scope& scope,u32 block,u32 reason) {
    static World::WorldId world{};static u64 load=~u64{0};static std::set<std::pair<u32,u32>> logged;
    const u64 current=bbsc_world_native_load.load();
    if(world!=scope.world || load!=current){world=scope.world;load=current;logged.clear();}
    if(logged.emplace(block,reason).second)
        BBSC_TIMELINE("WORLD","native block waiting map={:#x} block={:#x} reason={} load={} (1=inventory 2=lease 3=count)",
            scope.map,block,reason,current);
}

u32 BbscWorldBlockOwner(u32 handle) {
#ifdef BBSC_PERF_NESTED
    BBSC_PERF_NESTED("measure block owner lookup");
#endif
    std::unique_lock lock{bbsc_world_block_mutex,std::defer_lock};
    {
#ifdef BBSC_PERF_NESTED
        BBSC_PERF_NESTED("measure block owner mutex wait");
#endif
        lock.lock();
    }
    if(!bbsc_world_block_inventory_ready || bbsc_world_block_inventory_load!=bbsc_world_native_load.load())return 0;
    if(const auto player=bbsc_world_block_players.find(handle);player!=bbsc_world_block_players.end())return player->second;
    const auto id=bbsc_world_block_handles.find(handle);if(id==bbsc_world_block_handles.end())return 0;
    const auto local=bbsc_world_block_local.find(id->second);
    const auto view=bbsc_world_block_views.find({World::BlockScope(bbsc_world_block_scope,id->second),id->second});
    if(local==bbsc_world_block_local.end() || view==bbsc_world_block_views.end() ||
       local->second.load!=bbsc_world_native_load.load() ||
       local->second.applied_epoch!=view->second.lease.epoch)return 0;
    return view->second.lease.owner;
}
u32 BbscWorldBlockRole(u64 chr) {
    if(!ReadablePointer(chr,0x94))return 0;
    const auto owner=BbscWorldBlockOwner(ReadValue<u32>(chr,0x90));
    return owner?(owner==BbscMod::RegisterOwnId()?1:2):0;
}
bool BbscWorldBlockOwnsAny() {
    std::scoped_lock lock{bbsc_world_block_mutex};
    if(!bbsc_world_block_inventory_ready || bbsc_world_block_inventory_load!=bbsc_world_native_load.load())return false;
    for(const auto& [id,local]:bbsc_world_block_local){
        const auto view=bbsc_world_block_views.find({World::BlockScope(bbsc_world_block_scope,id),id});
        if(view!=bbsc_world_block_views.end() && view->second.lease.owner==BbscMod::RegisterOwnId() &&
           local.load==bbsc_world_native_load.load() && local.applied_epoch==view->second.lease.epoch)return true;
    }
    return false;
}
u64 BbscWorldBlockHpMember() {
    std::set<u32> providers;
    {std::scoped_lock lock{bbsc_world_block_mutex};
        for(const auto& [id,local]:bbsc_world_block_local){
            const auto view=bbsc_world_block_views.find({World::BlockScope(bbsc_world_block_scope,id),id});
            if(view!=bbsc_world_block_views.end() && view->second.lease.owner &&
               view->second.lease.owner!=BbscMod::RegisterOwnId())providers.insert(view->second.lease.owner);
        }}
    // Native guest HP receive has a single-source ABI. Poll each responsible
    // native member, retaining the native receiver and its reliable queues.
    static thread_local u32 previous=0;
    auto it=providers.upper_bound(previous);if(it==providers.end())it=providers.begin();
    bbsc_world_block_hp_source=it==providers.end()?0:*it;
    if(it==providers.end())return 0;previous=*it;return BbscWorldNativeMember(*it);
}

bool BbscWorldBlockPacketSend(GuestRegisterSnapshot* r) {
    const u32 channel=static_cast<u32>(r->rdx);
    if(channel!=4 && channel!=5 && channel!=0x15 && channel!=0x3D && channel!=0x41)return false;
    // Original queues: movement4 (8*12), HP5 (10*8), hit15 (12),
    // animation/state3D (64*100), status41 (64*24). Keep opaque payloads
    // intact; filter only their leading handles, BEFORE native sequencing.
    const size_t stride=channel==5?8:channel==0x3D?100:channel==0x41?24:12;
    const size_t limit=channel==5?80:channel==0x15?12:channel==0x3D?6400:channel==0x41?1536:96;
    if(!r->r8 || r->r8>limit || r->r8%stride || !ReadablePointer(r->rcx,r->r8)){
        r->rax=0;bbsc_independent_send_skip=1;return true;
    }
    const u32 recipient=BbscWorldPeer(r->rsi);
    const bool same_place=BbscWorldSendHere(recipient);
    const bool player_border=!same_place && BbscWorldPlayerSendHere(recipient);
    if(channel!=0x15 && !same_place && !player_border){r->rax=0;bbsc_independent_send_skip=1;return true;}
    static thread_local std::array<u8,6400> filtered;
    std::memcpy(filtered.data(),reinterpret_cast<const void*>(r->rcx),r->r8);
    bool any=false;
    for(size_t at=0;at<r->r8;at+=stride){
        const u32 handle=World::NativeInitialWord({filtered.data(),static_cast<size_t>(r->r8)},at);
        const u32 owner=BbscWorldBlockOwner(handle);
        if(channel==0x15){
            if(!owner || owner==BbscMod::RegisterOwnId())break;
            if(const u64 target=BbscWorldNativeMember(owner);target && BbscWorldSendHere(owner)){r->rsi=target;any=true;}break;
        }
        if(BbscCombatTraceEnabled())TraceBbscCombatPacket("send-intent",channel,BbscWorldPeer(r->rsi),
            {filtered.data()+at,stride},owner==BbscMod::RegisterOwnId());
        bool local_player=false;
        if(player_border){
            std::scoped_lock lock{bbsc_world_block_mutex};
            const auto player=bbsc_world_block_players.find(handle);
            local_player=player!=bbsc_world_block_players.end() && player->second==BbscMod::RegisterOwnId();
        }
        if(owner==BbscMod::RegisterOwnId() && (!player_border || local_player))any=true;
        else {
            // Status41 asserts on -1, then skips all other negative handles.
            const u32 invalid=channel==0x41?0xfffffffeu:0xffffffffu;
            std::memcpy(filtered.data()+at,&invalid,4);
        }
    }
    if(channel==0x15 && BbscCombatTraceEnabled())TraceBbscCombatPacket("send-intent",channel,BbscWorldPeer(r->rsi),
        {reinterpret_cast<const u8*>(r->rcx),static_cast<size_t>(r->r8)},any);
    if(any)r->rcx=reinterpret_cast<u64>(filtered.data());
    else{r->rax=0;bbsc_independent_send_skip=1;}
    return true;
}
void BbscWorldBlockStateReceived(const GuestRegisterSnapshot* regs,u32 channel) {
    if(!regs || !BbscWorldBlockSimulation() || static_cast<s32>(regs->rax)<=0)return;
    const size_t stride=channel==0x3D?100:24,limit=channel==0x3D?6400:1536;
    const u64 buffer=channel==0x3D?regs->r15:regs->rbx;
    if(regs->rax>limit || regs->rax%stride || !HasMemoryAccess(buffer,regs->rax,MemoryProt::CpuWrite))return;
    // Native state receivers poll explicit members. A proxy or a retired owner
    // must not overwrite the CURRENT owner's state, regardless of map role.
    const u32 source=BbscWorldPeer(channel==0x3D?regs->r14:regs->r12);
    for(size_t at=0;at<regs->rax;at+=stride){
        const u32 handle=ReadValue<u32>(buffer,at);
        const bool admitted=source && BbscWorldBlockOwner(handle)==source;
        TraceBbscCombatPacket("receive-admit",channel,source,
            {reinterpret_cast<const u8*>(buffer+at),stride},admitted);
        if(!admitted)
            WriteValue<u32>(buffer,at,channel==0x41?0xfffffffeu:0xffffffffu);
    }
}
void PS4_SYSV_ABI BbscWorldBlockAnimationReceived(u64,const GuestRegisterSnapshot* regs) {
    BbscWorldBlockStateReceived(regs,0x3D);
}
void PS4_SYSV_ABI BbscWorldBlockStatusReceived(u64,const GuestRegisterSnapshot* regs) {
    BbscWorldBlockStateReceived(regs,0x41);
}
void PS4_SYSV_ABI BbscWorldBlockHpReceived(u64,const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscWorldBlockSimulation() || static_cast<s32>(regs->rax)<=0 || regs->rax>0x50 ||
       regs->rax%8 || !HasMemoryAccess(regs->r15,regs->rax,MemoryProt::CpuWrite))return;
    for(size_t at=0;at<regs->rax;at+=8){
        const u32 handle=ReadValue<u32>(regs->r15,at);
        const bool admitted=bbsc_world_block_hp_source && BbscWorldBlockOwner(handle)==bbsc_world_block_hp_source;
        TraceBbscCombatPacket("receive-admit",5,bbsc_world_block_hp_source,
            {reinterpret_cast<const u8*>(regs->r15+at),8},admitted);
        if(!admitted)
            WriteValue<u32>(regs->r15,at,0xffffffffu);
    }
}

void BbscWorldReceiveBlock(const BbscWorldIncoming& message) {
    const auto& c=message.control;const auto decoded=World::DecodeBlock(message.payload);
    if(!BbscWorldBlocksActive() || !decoded || c.parts!=1 || c.part || !c.sequence)return;
    World::Presence local,peer;bool known=false;
    {std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;
        if(message.sender==BbscMod::RegisterOwnId()){peer=local;known=true;}
        else if(const auto* member=bbsc_world_presence_book.Resident(message.sender)){peer=member->presence;known=true;}}
    if(c.scope.world!=local.world || !known || !(peer.capabilities&World::BlockCapability))return;
    const auto record=std::span<const u8>{message.payload}.subspan(sizeof(World::BlockWire));
    std::unique_lock lock{bbsc_world_block_mutex};
    if(c.kind==World::ControlKind::BlockOffer){
        if(local.world.host!=BbscMod::RegisterOwnId() || peer.phase!=World::Phase::Playing ||
           World::BlockScope(World::ScopeOf(peer),decoded->block)!=c.scope || decoded->origin_map!=peer.map ||
           decoded->visit!=peer.visit || c.owner!=message.sender || decoded->retiring)return;
        bbsc_world_block_coordinator.Offer(c.scope,message.sender,
            {decoded->visit,c.sequence,c.epoch,decoded->active!=0,decoded->retired!=0,{record.begin(),record.end()},decoded->loaded!=0,World::ScopeOf(peer)});
        lock.unlock();BbscWorldCoordinateBlocks();
    }else if(c.kind==World::ControlKind::BlockLease){
        // Lease visit/origin_map acknowledge the reporting peer's current visit.
        // An in-flight lease from before departure must not admit a new load.
        if(message.sender!=local.world.host || decoded->active || decoded->retired ||
           bool(decoded->visit)!=bool(decoded->origin_map) || !decoded->loaded || !c.epoch || (c.owner && decoded->retiring) ||
           c.scope!=World::BlockScope(c.scope,decoded->block))return;
        auto key=std::pair{c.scope,decoded->block};
        if(!bbsc_world_block_views.contains(key) && bbsc_world_block_views.size()>=2048)return;
        auto& view=bbsc_world_block_views[key];
        if(c.epoch<view.lease.epoch || c.sequence<=view.sequence ||
           (c.epoch==view.lease.epoch && (c.owner!=view.lease.owner || decoded->retiring!=view.lease.retiring)))return;
        ++bbsc_world_block_admission_revision;
        const bool changed=c.epoch!=view.lease.epoch;
        view.sequence=c.sequence;
        if(!c.owner)view.load=~u64{0};
        else if(decoded->origin_map==BbscMod::RegisterOwnId() && decoded->visit==local.visit &&
                local.phase==World::Phase::Playing)
            view.load=bbsc_world_native_load.load();
        view.lease={c.owner,decoded->retiring,0,c.epoch,{record.begin(),record.end()}};
        if(changed)BBSC_TIMELINE("WORLD","native block lease map={:#x} block={:#x} owner={:08x} retiring={:08x} epoch={}",
            c.scope.map,decoded->block,c.owner,decoded->retiring,c.epoch);
    }
}

// Exact block list used by native01786360. Native0190E750 supplies the record;
// the existing historical handler0190E8B0 installs it without replaying rewards.
void BbscWorldCaptureBlocks(const World::Scope& scope) {
#ifdef BBSC_PERF_NESTED
    BBSC_PERF_NESTED("measure block capture");
#endif
    {std::scoped_lock lock{bbsc_world_block_mutex};bbsc_world_block_inventory_ready=false;
        ++bbsc_world_block_admission_revision;}
    const u64 world=ReadValue<u64>(image_base+CandidateLocalStatePointerOffset,0);
    const u64 player=GetLocalPlayerCharacter();
    if(!ReadablePointer(world,0x280) || !ReadablePointer(player,0x238))return;
    const s32 count=ReadValue<s32>(world,0x278);if(count<2 || count>64)return;
    std::map<u32,BbscBlockLocal> next;std::map<u32,u32> handles,players;
    for(const auto chr:BbscWorldPlayers(world))if(ReadablePointer(chr,0x400)){
        const s32 handle=ReadValue<s32>(chr,0x90);
        if(handle>=0)players[handle]=chr==player?BbscMod::RegisterOwnId():BbscWorldPeer(chr+0x3D8);
    }
    for(s32 i=0;i<count-2;++i){const size_t at=0x290+static_cast<size_t>(i)*0x18;
        if(!ReadablePointer(world+at-0x10,0x18))return;
        if(!ReadValue<u64>(world,at-0x10))continue;
        const u64 block=ReadValue<u64>(world,at);if(!ReadablePointer(block,0xC8))return;
        const s32 actors=ReadValue<s32>(block,0xB8);if(actors<0 || actors>1024)return;
        if(!actors)continue;
        const u64 entries=ReadValue<u64>(block,0xC0);
        if(!ReadablePointer(entries,static_cast<size_t>(actors)*0x38))return;
        std::vector<u8> record(12+(actors+7)/8);
        using Serialize=s32 PS4_SYSV_ABI (*)(u64,u8*);
        if(reinterpret_cast<Serialize>(image_base+0x0190E750)(block,record.data())!=static_cast<s32>(record.size()) ||
           !World::ValidNativeBlock(record))return;
        const u32 id=World::NativeInitialWord(record,0);if(next.contains(id))return;auto& item=next[id];
        item.address=block;item.load=bbsc_world_native_load.load();item.native=std::move(record);
        bool retiring=false;
        {std::scoped_lock lock{bbsc_world_block_mutex};
            const auto view=bbsc_world_block_views.find({World::BlockScope(scope,id),id});
            retiring=view!=bbsc_world_block_views.end() && view->second.lease.retiring==BbscMod::RegisterOwnId();}
        item.quiesced=retiring;
        for(size_t n=0;n<8;++n)item.active|=(ReadValue<u32>(block,0x38+n*4)&ReadValue<u32>(player,0x218+n*4))!=0;
        for(s32 n=0;n<actors;++n){const u64 chr=ReadValue<u64>(entries,n*0x38);
            if(ReadablePointer(chr,0x94)){const s32 handle=ReadValue<s32>(chr,0x90);if(handle>=0)handles[handle]=id;
                if(retiring && !players.contains(handle)){
                    const u64 control=ReadValue<u64>(chr,0x18);
                    if(ReadablePointer(control,0x2c) && (ReadValue<s32>(control,0x14)==4 || ReadValue<s32>(control,0x10)==4)){
                        const u64 word=BbscWorldOwnershipWord(world,chr);
                        if(word)WriteValue<u16>(word,0,0xffff);else item.quiesced=false;
                    }
                }
            }}
    }
    std::scoped_lock lock{bbsc_world_block_mutex};
    if(bbsc_world_block_scope==scope)for(const auto& [id,item]:bbsc_world_block_local)
        if(!next.contains(id))bbsc_world_block_withdrawn[id]=item;
    for(const auto& [id,item]:next)bbsc_world_block_withdrawn.erase(id);
    for(auto& [id,item]:next)if(const auto old=bbsc_world_block_local.find(id);old!=bbsc_world_block_local.end() &&
        bbsc_world_block_scope==scope && old->second.load==item.load && old->second.address==item.address)
        item.applied_epoch=old->second.applied_epoch;
    bbsc_world_block_scope=scope;bbsc_world_block_local=std::move(next);bbsc_world_block_handles=std::move(handles);
    bbsc_world_block_players=std::move(players);
    bbsc_world_block_inventory_load=bbsc_world_native_load.load();bbsc_world_block_inventory_ready=true;
}

bool BbscWorldAdmitBlocks(const World::Scope& scope) {
    if(!BbscWorldBlocksActive())return false;
    std::unique_lock lock{bbsc_world_block_mutex};
    if(bbsc_world_block_scope!=scope || !bbsc_world_block_inventory_ready ||
       bbsc_world_block_inventory_load!=bbsc_world_native_load.load()){
        BbscWorldBlockWait(scope,0,1);return false;
    }
    if(bbsc_world_block_admitted_revision==bbsc_world_block_admission_revision)return true;
    const u64 revision=bbsc_world_block_admission_revision;
    bool ready=true;
    for(auto& [id,item]:bbsc_world_block_local){
        const auto view=bbsc_world_block_views.find({World::BlockScope(scope,id),id});
        if(view==bbsc_world_block_views.end() || !view->second.lease.owner ||
           view->second.load!=bbsc_world_native_load.load() ||
           item.load!=bbsc_world_native_load.load()){BbscWorldBlockWait(scope,id,2);ready=false;continue;}
        const auto& lease=view->second.lease;
        if(item.applied_epoch==lease.epoch)continue;
        if(lease.native.size()!=item.native.size() || std::memcmp(lease.native.data(),item.native.data(),12)){
            BbscWorldBlockWait(scope,id,3);ready=false;continue;
        }
        const auto native=lease.native;const u64 epoch=lease.epoch,address=item.address;
        const u32 owner=lease.owner;
        lock.unlock();
        // A coordinator-certified native block record is its own admission.
        // Player actor FirstSync is separate: its provider may be on a different
        // adjacent map, or loading after it has handed this block over.
        using Apply=void PS4_SYSV_ABI (*)(u64,const u8*,const u8*);
        ObserveBbscNpcLifecycle("block-history-before",id);
        reinterpret_cast<Apply>(image_base+0x0190E8B0)(address,native.data(),native.data());
        ObserveBbscNpcLifecycle("block-history-after",id);
        lock.lock();item.applied_epoch=epoch;
        ready&=view->second.lease.epoch==epoch && view->second.lease.owner==owner;
        BBSC_TIMELINE("WORLD","native block admitted map={:#x} block={:#x} owner={:08x} epoch={} load={}",
            scope.map,id,owner,epoch,item.load);
    }
    // Apply releases the mutex around native code. A concurrent publication
    // must be checked on the next call, even when this pass itself succeeded.
    if(ready && revision==bbsc_world_block_admission_revision)
        bbsc_world_block_admitted_revision=revision;
    return ready;
}

void TickBbscWorldBlocks() {
#ifdef BBSC_PERF_NESTED
    BBSC_PERF_NESTED("measure block tick");
#endif
    World::Presence local;bool compatible=true;
    {std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;
        for(const auto& [peer,m]:bbsc_world_presence_book.Members())
            compatible&=(m.presence.capabilities&World::BlockCapability)!=0;}
    const bool negotiated=BbscIndependentActive() && (local.capabilities&World::BlockCapability) && compatible;
    bbsc_world_blocks_active=negotiated;
    {std::scoped_lock lock{bbsc_world_block_mutex};
        if(bbsc_world_block_world!=local.world){
            ++bbsc_world_block_admission_revision;
            bbsc_world_block_world=local.world;bbsc_world_block_local.clear();bbsc_world_block_withdrawn.clear();bbsc_world_block_handles.clear();bbsc_world_block_players.clear();
            bbsc_world_block_views.clear();bbsc_world_block_published.clear();bbsc_world_block_coordinator.Bind(local.world);
            bbsc_world_block_inventory_ready=false;
        }}
    if(!negotiated)return;
    const u32 self=BbscMod::RegisterOwnId();const bool host=self==local.world.host;
    const auto scope=World::ScopeOf(local);
    const bool playing=local.phase==World::Phase::Playing && scope.map!=0x15000000 && World::Valid(scope) &&
        !bbsc_world_load_pending.load() && !bbsc_reload_finish_pending.load() && !BbscCurtainActive() &&
        (Chalice::IsMap(GetCurrentPackedMap())?0x1d000000u:GetCurrentPackedMap())==scope.map;
    // Capture before native events too. Applying shared flags does not execute
    // NPC scripts or grant simulation authority to unadmitted blocks.
    if(playing && BbscWorldFlagsReady(scope)){
        BbscWorldCaptureBlocks(scope);
        {
#ifdef BBSC_PERF_NESTED
            BBSC_PERF_NESTED("measure block admission");
#endif
            BbscWorldAdmitBlocks(scope);
        }
    }
    std::vector<BbscWorldIncoming> outgoing;
    static s64 last=0;const s64 now=SteadyNowMs();
    if(now-last<100)return;last=now;
    if(playing && BbscWorldFlagsReady(scope)){
        std::unique_lock lock{bbsc_world_block_mutex,std::defer_lock};
        {
#ifdef BBSC_PERF_NESTED
            BBSC_PERF_NESTED("measure block publication mutex wait");
#endif
            lock.lock();
        }
        if(!bbsc_world_block_inventory_ready)return;
#ifdef BBSC_PERF_NESTED
        BBSC_PERF_NESTED("measure block publication copy encode");
#endif
        const auto report=[&](u32 id,const BbscBlockLocal& item){
            World::Control c;c.kind=World::ControlKind::BlockOffer;c.scope=World::BlockScope(scope,id);c.owner=self;c.sequence=++bbsc_world_block_sequence;
            World::BlockWire wire;wire.visit=local.visit;wire.origin_map=local.map;wire.block=id;wire.active=item.active;
            wire.loaded=bbsc_world_block_local.contains(id);if(!wire.loaded)wire.active=0;
            if(const auto view=bbsc_world_block_views.find({c.scope,id});view!=bbsc_world_block_views.end()){
                c.epoch=view->second.lease.epoch;wire.retired=view->second.lease.retiring==self && item.quiesced;
            }
            auto bytes=World::EncodeBlock(wire,item.native);outgoing.push_back({self,c,std::move(bytes)});
        };
        for(const auto& [id,item]:bbsc_world_block_local)report(id,item);
        for(const auto& [id,item]:bbsc_world_block_withdrawn)
            if(!bbsc_world_block_local.contains(id))report(id,item);
        bbsc_world_block_withdrawn.clear();
    }
    for(const auto& message:outgoing){if(host)BbscWorldReceiveBlock(message);else BbscWorldSend(message.control,message.payload);}
    if(host)BbscWorldCoordinateBlocks();
}

// Metadata only: native room host may be in a movie/loading another map.
// Offers and presence drive this on the receive thread, like map leases.
void BbscWorldCoordinateBlocks() {
    if(!BbscWorldBlocksActive())return;
    World::Presence local;std::map<u32,World::Member> members;
    {std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;members=bbsc_world_presence_book.Members();}
    const u32 self=BbscMod::RegisterOwnId();if(!self || self!=local.world.host)return;
    members[self]={local,SteadyNowMs(),0};
    std::vector<BbscWorldIncoming> outgoing;
    {
        std::scoped_lock lock{bbsc_world_block_mutex};
        if(bbsc_world_block_world!=local.world)return;
        bbsc_world_block_coordinator.ResetUnoccupied([&](const World::Scope& target){
            return std::ranges::any_of(members,[&](const auto& m){return m.second.presence.phase==World::Phase::Playing &&
                World::ScopeOf(m.second.presence)==target;});
        });
        bbsc_world_block_coordinator.Elect([&](u32 peer,const World::Scope& target,u64 visit){
            const auto m=members.find(peer);return m!=members.end() && m->second.presence.phase==World::Phase::Playing &&
                World::ScopeOf(m->second.presence)==target && m->second.presence.visit==visit;
        });
        for(const auto& [key,state]:bbsc_world_block_coordinator.Blocks()){
            const auto& lease=state.lease;if(lease.native.empty())continue;
            // Broadcast per-reporter acknowledgements. All peers retain the
            // epoch fence, but only the acknowledged visit may apply history.
            auto recipients=state.offers;
            if(recipients.empty())recipients[0]={};
            for(const auto& [recipient,offer]:recipients){
            World::Control c;c.kind=World::ControlKind::BlockLease;c.scope=key.first;c.owner=lease.owner;
            c.epoch=lease.epoch;c.sequence=++bbsc_world_block_sequence;
            World::BlockWire wire;wire.block=key.second;wire.retiring=lease.retiring;
            wire.visit=offer.visit;wire.origin_map=recipient;
            auto bytes=World::EncodeBlock(wire,lease.native);auto& previous=bbsc_world_block_published[{key,recipient}];
            const s64 now=SteadyNowMs();
            if(previous.epoch==c.epoch && previous.owner==c.owner && previous.bytes==bytes && now-previous.sent<1000)continue;
            previous={c.epoch,c.owner,now,bytes};
            outgoing.push_back({self,c,std::move(bytes)});
            }
        }
    }
    for(const auto& message:outgoing){BbscWorldReceiveBlock(message);BbscWorldSend(message.control,message.payload);}
}
