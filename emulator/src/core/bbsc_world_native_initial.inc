// SPDX-License-Identifier: GPL-2.0-or-later
// Native summon CHR initial state. Only request/packet correlation metadata is
// retained; all NPC bits are built by01786360 and consumed directly by0190E8B0.
struct BbscNativeInitialAdmission {
    World::Scope scope{};u64 load=~u64{0},epoch=0,request=0;
    u32 owner=0;bool ready=false;s64 sent=0;
    std::set<u64> fingerprints;
};
BbscNativeInitialAdmission bbsc_world_initial;
u64 bbsc_world_initial_sequence=0;

// Native mode: one transaction per destination load. These are only temporary
// native packet bytes, never an enemy cache or a simulation/watchdog loop.
struct BbscNativeInitialOnce {
    World::Scope scope{};u64 load=~u64{0},request=0,epoch=0;
    u32 owner=0,received=0;u16 parts=0;bool consumed=false;
    std::array<std::vector<u8>,13> packets;
};
BbscNativeInitialOnce bbsc_world_initial_once;

void BbscWorldNativeInitialOnce(const World::Scope& scope) {
    auto& once=bbsc_world_initial_once;
    const u64 load=bbsc_world_native_load.load();
    if(once.scope==scope && once.load==load)return;
    once={};once.scope=scope;once.load=load;
    // A coordinated wipe starts a new native encounter. A peer's previous
    // visit is not a resident world from which to import historical deaths.
    if(!World::Valid(scope) || !BbscIndependentActive() || BbscIsBossWipeLoad(scope))return;
    {std::scoped_lock lock{bbsc_world_presence_mutex};
        const auto* lease=bbsc_independent_owners.Find(scope);
        if(!lease || !lease->owner || lease->owner==BbscMod::RegisterOwnId())return;
        const auto* resident=bbsc_world_presence_book.Resident(lease->owner);
        if(!resident || resident->presence.phase!=World::Phase::Playing ||
           World::ScopeOf(resident->presence)!=scope)return;
        once.owner=lease->owner;once.epoch=lease->epoch;
    }
    once.request=++bbsc_world_initial_sequence;
    World::Control c;c.kind=World::ControlKind::NativeInitialRequest;c.scope=scope;
    c.owner=BbscMod::RegisterOwnId();c.epoch=once.epoch;c.sequence=once.request;
    BbscWorldSend(c); // once; no timer, retry, task scan or event barrier
    BBSC_TIMELINE("WORLD","one-shot native state requested owner={:08x} map={:#x} load={} request={}",
        once.owner,scope.map,load,once.request);
}

bool BbscWorldApplyNativeInitial(std::span<const u8> bytes) {
    const auto records=World::NativeInitialCharacters(bytes);if(!records)return false;
    const u64 world=ReadValue<u64>(image_base+CandidateLocalStatePointerOffset,0);
    if(!ReadablePointer(world,0x280))return false;
    const s32 count=ReadValue<s32>(world,0x278);if(count<2 || count>64)return false;
    // This is the exact block list used by native01786360. Preflight every
    // LOCAL block before the native historical-death handler removes any actor.
    // The resident can have additional streamed blocks. Native0191BDD0 skips
    // records without a local block (0191BF1A -> 0191BF70); their presence must
    // not hold all visitor events, including AI initialization, behind a wait
    // for identical streaming footprints. Still require coverage/counts for
    // every local block, so a partial packet cannot admit unsynchronized NPCs.
    std::vector<std::pair<u64,std::span<const u8>>> apply;
    std::set<u32> matched;
    for(s32 i=0;i<count-2;++i){
        const size_t at=0x290+static_cast<size_t>(i)*0x18;
        if(!ReadablePointer(world+at-0x10,0x18))return false;
        if(!ReadValue<u64>(world,at-0x10))continue;
        const u64 block=ReadValue<u64>(world,at);
        if(!ReadablePointer(block,0xC8))return false;
        const s32 actors=ReadValue<s32>(block,0xB8);if(!actors)continue;
        const u64 map=ReadValue<u64>(block,8);if(!ReadablePointer(map,12))return false;
        const u32 id=ReadValue<u32>(map,8);
        auto found=std::ranges::find_if(*records,[&](auto record){return World::NativeInitialWord(record,0)==id;});
        if(found==records->end() || actors<0 || actors>1024 ||
           World::NativeInitialWord(*found,8)!=static_cast<u32>(actors) || !matched.insert(id).second)return false;
        const u64 entries=ReadValue<u64>(block,0xC0);
        if(!ReadablePointer(entries,static_cast<size_t>(actors)*0x38))return false;
        apply.emplace_back(block,*found);
    }
    if(apply.empty() && !records->empty())return false;
    using Apply=void PS4_SYSV_ABI (*)(u64,const u8*,const u8*);
    for(const auto& [block,record]:apply)
        reinterpret_cast<Apply>(image_base+0x0190E8B0)(block,record.data(),record.data());
    return true;
}

void BbscWorldNativeInitialControl(const BbscWorldIncoming& message) {
    const auto& c=message.control;
    const bool once_only=SessionTest::NativeNpcSync();
    if(!BbscIndependentActive() || !c.sequence || (!once_only && (c.parts!=1 || c.part)))return;
    World::Presence local,peer;World::OwnerLease lease;bool known=false;
    {std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;
        if(const auto* p=bbsc_independent_owners.Find(c.scope))lease=*p;
        if(const auto* p=bbsc_world_presence_book.Resident(message.sender)){peer=p->presence;known=true;}}
    if(!known || peer.world!=local.world || !lease.owner || lease.epoch!=c.epoch)return;
    if(once_only && c.kind==World::ControlKind::NativeInitialReady){
        auto& once=bbsc_world_initial_once;
        if(once.consumed || !once.request || once.load!=bbsc_world_native_load.load() ||
           once.scope!=c.scope || once.epoch!=c.epoch || once.owner!=message.sender ||
           c.owner!=lease.owner || message.sender!=lease.owner || once.request!=c.sequence ||
           peer.phase!=World::Phase::Playing || World::ScopeOf(peer)!=c.scope ||
           World::ScopeForMap(World::ScopeOf(local),GetCurrentPackedMap(),bbsc_world_requested_scope)!=c.scope ||
           !c.parts || c.parts>once.packets.size() || c.part>=c.parts ||
           message.payload.empty() || message.payload.size()>2048 ||
           (c.part+1<c.parts && message.payload.size()!=2048) ||
           (once.parts && once.parts!=c.parts))return;
        once.parts=c.parts;
        if(once.received&(1u<<c.part))return;
        once.packets[c.part]=message.payload;once.received|=1u<<c.part;
        if(once.received!=((1u<<once.parts)-1))return;
        std::vector<u8> packet;
        for(unsigned i=0;i<once.parts;++i)packet.insert(packet.end(),once.packets[i].begin(),once.packets[i].end());
        once.consumed=true;
        const bool applied=BbscWorldApplyNativeInitial(packet);
        for(auto& part:once.packets)part.clear();
        BBSC_TIMELINE("WORLD","one-shot native state result applied={} owner={:08x} map={:#x} load={} request={}",
            applied,once.owner,c.scope.map,once.load,once.request);
        return;
    }
    if(c.kind==World::ControlKind::NativeInitialReady){
        auto& admission=bbsc_world_initial;
        if(peer.phase!=World::Phase::Playing || World::ScopeOf(peer)!=c.scope ||
           message.sender!=lease.owner || c.owner!=lease.owner || message.payload.size()!=sizeof(u64) ||
           admission.scope!=c.scope || admission.owner!=lease.owner || admission.epoch!=c.epoch ||
           admission.load!=bbsc_world_native_load.load() || admission.request!=c.sequence)return;
        u64 fingerprint;std::memcpy(&fingerprint,message.payload.data(),sizeof(fingerprint));
        if(admission.fingerprints.size()<8)admission.fingerprints.insert(fingerprint);
        return;
    }
    // The explicit scope request admits a loading member whose last committed
    // presence is still the previous map. It never grants simulation authority.
    if(local.phase!=World::Phase::Playing || World::ScopeOf(local)!=c.scope ||
       (peer.phase!=World::Phase::Loading && !World::SamePlace(local,peer)) ||
       lease.owner!=BbscMod::RegisterOwnId() || c.owner!=message.sender || !message.payload.empty() ||
       !BbscWorldSceneReady())return;
    if(c.kind!=World::ControlKind::NativeInitialRequest || c.parts!=1 || c.part)return;
    const u64 member=BbscWorldNativeMember(message.sender);if(!member)return;
    // Native serializer ignores RDI, takes the recipient member in RSI, frees
    // its temporary buffer and returns whether the native reliable send worked.
    using Send=bool PS4_SYSV_ABI (*)(u64,u64);
    if(once_only){
        // Existing control fragmentation carries the ORIGINAL serializer's
        // bytes. A ready notification on another transport cannot guarantee
        // its native queue is populated yet; carrying the bytes here removes
        // that race without a receive poll or resend.
        static std::map<u32,std::tuple<World::WorldId,u64,u64>> served;
        const auto key=std::make_tuple(local.world,peer.visit,c.sequence);
        if(const auto it=served.find(message.sender);it!=served.end() &&
           std::get<0>(it->second)==local.world && std::get<1>(it->second)==peer.visit &&
           std::get<2>(it->second)>=c.sequence)return;
        served[message.sender]=key;
        std::vector<u8> packet;bbsc_world_initial_capture=&packet;
        const bool sent=reinterpret_cast<Send>(image_base+0x01786360)(0,member);
        bbsc_world_initial_capture=nullptr;
        if(!sent || packet.empty() || packet.size()>0x6400)return;
        auto reply=c;reply.kind=World::ControlKind::NativeInitialReady;reply.owner=lease.owner;
        reply.parts=static_cast<u16>((packet.size()+2047)/2048);
        for(reply.part=0;reply.part<reply.parts;++reply.part){
            const size_t at=reply.part*2048;
            BbscWorldSend(reply,{packet.data()+at,std::min<size_t>(2048,packet.size()-at)});
        }
        return;
    }
    bbsc_world_initial_sending=message.sender;bbsc_world_initial_fingerprint=0;
    const bool sent=reinterpret_cast<Send>(image_base+0x01786360)(0,member);
    bbsc_world_initial_sending=0;
    if(!sent || !bbsc_world_initial_fingerprint)return;
    auto reply=c;reply.kind=World::ControlKind::NativeInitialReady;reply.owner=lease.owner;
    BbscWorldSend(reply,{reinterpret_cast<const u8*>(&bbsc_world_initial_fingerprint),sizeof(u64)});
}

bool BbscWorldNativeInitialReady(const World::Scope& scope,u32 owner,u64 epoch) {
    if(!owner)return true; // no resident provider yet: preserve first-map native admission
    if(owner==BbscMod::RegisterOwnId())return true;
    {std::scoped_lock lock{bbsc_world_presence_mutex};
        const auto* provider=bbsc_world_presence_book.Resident(owner);
        // A retained lease for a now-empty map is not a resident to bootstrap
        // from. The existing coordinator will elect its next arriving owner.
        if(!provider || provider->presence.phase!=World::Phase::Playing || World::ScopeOf(provider->presence)!=scope)return true;}
    auto& admission=bbsc_world_initial;const u64 load=bbsc_world_native_load.load();
    if(admission.scope!=scope || admission.load!=load || admission.owner!=owner || admission.epoch!=epoch){
        admission={};admission.scope=scope;admission.load=load;admission.owner=owner;admission.epoch=epoch;
        admission.request=++bbsc_world_initial_sequence;
    }
    if(admission.ready)return true;
    const u64 member=BbscWorldNativeMember(owner);
    const u64 net=ReadValue<u64>(image_base+0x0553D6D0,0);
    if(!member || !ReadablePointer(net,0x88))return false;
    // Leave data in the native queue until a matching admission descriptor is
    // known. Old-load packets cannot satisfy the current request fingerprint.
    if(!admission.fingerprints.empty()){
        std::array<u8,0x6400> bytes;
        using Receive=s32 PS4_SYSV_ABI (*)(u64,u64,u32,u8*,u32);
        for(unsigned n=0;n<8;++n){
            const s32 size=reinterpret_cast<Receive>(image_base+0x01789200)(net,member,0x11,bytes.data(),bytes.size());
            if(size<=0 || size>static_cast<s32>(bytes.size()))break;
            const std::span<const u8> packet{bytes.data(),static_cast<size_t>(size)};
            if(!admission.fingerprints.contains(World::NativeInitialFingerprint(packet)))continue;
            if(!BbscWorldApplyNativeInitial(packet))break;
            admission.ready=true;
            BBSC_TIMELINE("WORLD","native CHR initial state applied owner={:08x} map={:#x} load={} request={}",owner,scope.map,load,admission.request);
            return true;
        }
    }
    const s64 now=SteadyNowMs();
    if(!admission.sent || now-admission.sent>=1000){
        World::Control c;c.kind=World::ControlKind::NativeInitialRequest;c.scope=scope;
        c.owner=BbscMod::RegisterOwnId();c.epoch=epoch;c.sequence=admission.request;
        BbscWorldSend(c);admission.sent=now;
    }
    return false;
}
