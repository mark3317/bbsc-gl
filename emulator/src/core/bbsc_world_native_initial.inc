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
    if(!BbscIndependentActive() || c.parts!=1 || c.part || !c.sequence)return;
    World::Presence local,peer;World::OwnerLease lease;bool known=false;
    {std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;
        if(const auto* p=bbsc_independent_owners.Find(c.scope))lease=*p;
        if(const auto* p=bbsc_world_presence_book.Resident(message.sender)){peer=p->presence;known=true;}}
    if(!known || peer.world!=local.world || !lease.owner || lease.epoch!=c.epoch)return;
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
    const u64 member=BbscWorldNativeMember(message.sender);if(!member)return;
    // Native serializer ignores RDI, takes the recipient member in RSI, frees
    // its temporary buffer and returns whether the native reliable send worked.
    using Send=bool PS4_SYSV_ABI (*)(u64,u64);
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
