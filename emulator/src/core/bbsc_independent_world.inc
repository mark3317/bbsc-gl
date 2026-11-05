// SPDX-License-Identifier: GPL-2.0-or-later
// Included inside bloodborne_re.cpp's implementation namespace. Native offsets
// and ownership approach: CLS_AMG / Yharnam Together, GPL-2.0-or-later. Adapted
// to BBSC's native direct P2P transport; no replacement transport or server.
#ifdef BBSC_MOD
std::atomic<bool> bbsc_independent_hooks{false}, bbsc_independent_active{false};
std::atomic<bool> bbsc_independent_travel_hooks{false};
std::atomic<u32> bbsc_independent_role{0}, bbsc_independent_owner{0};
World::OwnerBook bbsc_independent_owners; // protected by presence mutex
std::map<World::Scope,World::OwnerLease> bbsc_independent_elected;
u64 bbsc_independent_epoch = 0;
World::WorldId bbsc_independent_bound{};
struct BbscWorldIncoming {u32 sender;World::Control control;std::vector<u8> payload;};
std::mutex bbsc_independent_incoming_mutex;
std::deque<BbscWorldIncoming> bbsc_independent_incoming;
thread_local u8 bbsc_independent_send_depth = 0;
u8 bbsc_independent_send_skip = 0;

bool BbscIndependentActive() {return bbsc_independent_active.load(std::memory_order_acquire);}
bool BbscIndependentTravelAllowed() {
    return BbscIndependentActive() && bbsc_independent_travel_hooks.load() &&
           !BbscQuitInProgress() && !BbscReturningToTitle();
}
u32 BbscIndependentCapabilities() {
    return World::PresenceCapability |
        (bbsc_independent_hooks.load() ? World::OwnerCapability : 0) |
        (bbsc_independent_hooks.load() && bbsc_independent_travel_hooks.load() ?
         World::IndependentTravelCapability : 0);
}

// The complete native identity lives at [member_id], not in the lock wrapper.
BbscMod::RegisterIdentity BbscWorldIdentity(u64 member_id) {
    BbscMod::RegisterIdentity out;
    if (!IsValidMemberId(member_id)) return out;
    const u64 identity = ReadValue<u64>(member_id,0);
    if (!ReadablePointer(identity,0x5A) || ReadValue<u64>(identity,0)!=image_base+0x052C5C00) return out;
    out.room=ReadValue<u32>(identity,0x30);
    out.member=ReadValue<u16>(identity,0x34);
    std::memcpy(out.name,reinterpret_cast<const void*>(identity+0x36),16);
    return out;
}
u32 BbscWorldPeer(u64 member_id) {
    return BbscMod::FindSessionRegisterPeer(BbscWorldIdentity(member_id));
}
u64 BbscWorldNativeMember(u32 peer) {
    if (!peer) return 0;
    const u64 manager=ReadValue<u64>(image_base+MatchingStatePointerOffset,0);
    if (!ReadablePointer(manager,0x108)) return 0;
    const u64 first=ReadValue<u64>(manager,0xF8),end=ReadValue<u64>(manager,0x100);
    if (end<first || end-first>8*0x20 || !ReadablePointer(first,end-first)) return 0;
    for(u64 at=first;at<end;at+=0x20) if(BbscWorldPeer(at)==peer) return at;
    return 0;
}
bool BbscWorldPeerHere(u32 peer) {
    if (!BbscIndependentActive()) return true;
    std::scoped_lock lock{bbsc_world_presence_mutex};
    const auto* m=bbsc_world_presence_book.Find(peer,SteadyNowMs());
    return m && World::SamePlace(bbsc_world_presence_local,m->presence);
}
bool BbscWorldActorHere(u64 chr) {
    return !BbscIndependentActive() || BbscWorldPeerHere(BbscWorldPeer(chr+0x3D8));
}
bool BbscWorldSendHere(u32 peer) {
    std::scoped_lock lock{bbsc_world_presence_mutex};
    if(!peer || !bbsc_world_presence_book.Known(peer)) return true; // native first-sync bootstrap
    const auto* m=bbsc_world_presence_book.Find(peer,SteadyNowMs());
    return m && World::SamePlace(bbsc_world_presence_local,m->presence);
}
u32 BbscWorldLivingHere() {
    std::scoped_lock lock{bbsc_world_presence_mutex};
    return bbsc_world_presence_book.LivingHere(bbsc_world_presence_local,SteadyNowMs());
}
u32 BbscWorldParticipantsHere() {
    std::scoped_lock lock{bbsc_world_presence_mutex};u32 count=0;
    for(const auto& [peer,m]:bbsc_world_presence_book.Members())
        count+=World::PresenceBook::Fresh(m,SteadyNowMs()) && World::SamePlace(bbsc_world_presence_local,m.presence);
    return count;
}
bool BbscWorldTaskHere(u64 task) {
    if (!BbscIndependentActive()) return true;
    const s32 mode=ReadValue<s32>(task,0xE8);
    const u32 peer=mode==2 && GetSessionState()==6 ? GetBbscRelayHost() : BbscWorldPeer(task+0xC8);
    return peer && BbscWorldPeerHere(peer);
}

void BbscWorldSend(World::Control control,std::span<const u8> payload={}) {
    const auto bytes=World::Encode(control,payload);
    if (!bytes.empty()) Libraries::Np::NpSignaling::Helpers::SendBbscWorldFlagsToPeers(bytes.data(),bytes.size());
}

// Metadata only: safe to run on the relay receive thread even while the host's
// game thread is loading another map. There is no independent timeout election.
void BbscWorldCoordinate() {
    std::vector<World::Control> send;
    {
        std::scoped_lock lock{bbsc_world_presence_mutex};
        const auto local=bbsc_world_presence_local;
        const u32 self=BbscMod::RegisterOwnId();
        if (!World::Valid(local) || local.world.host!=self || !(local.capabilities&World::OwnerCapability)) return;
        if(local.world!=bbsc_independent_bound) {
            bbsc_independent_bound=local.world;
            bbsc_independent_elected.clear();bbsc_independent_owners.Bind(local.world);
        }
        static s64 last_sent=0;bool changed=false;
        auto members=bbsc_world_presence_book.Members();
        members[self]={local,SteadyNowMs(),0};
        for(const auto& [peer,m]:members) {
            if (!(m.presence.capabilities&World::OwnerCapability) ||
                m.presence.phase!=World::Phase::Playing || !World::Valid(World::ScopeOf(m.presence))) continue;
            const auto scope=World::ScopeOf(m.presence);
            auto& previous=bbsc_independent_elected[scope];
            const u32 owner=World::ChooseOwner(m.presence,members,previous.owner,SteadyNowMs());
            if(!previous.epoch || previous.owner!=owner) {previous={owner,++bbsc_independent_epoch,SteadyNowMs()};changed=true;}
            World::Control c;c.kind=World::ControlKind::Owner;c.scope=scope;c.owner=owner;c.epoch=previous.epoch;
            if(std::ranges::none_of(send,[&](const auto& p){return p.scope==scope;})) {
                bbsc_independent_owners.Take(self,c,SteadyNowMs());send.push_back(c);
            }
        }
        const s64 now=SteadyNowMs();
        if(!changed && now-last_sent<1000)send.clear();else last_sent=now;
    }
    for(const auto& c:send) BbscWorldSend(c);
}

void ProcessBbscWorldControl(u32 sender,const World::Control& c,std::span<const u8> payload) {
    if(c.kind==World::ControlKind::Owner) {
        std::scoped_lock lock{bbsc_world_presence_mutex};
        if(c.scope.world!=bbsc_world_presence_local.world) return;
        bbsc_independent_owners.Bind(c.scope.world);
        bbsc_independent_owners.Take(sender,c,SteadyNowMs());
        return;
    }
    std::scoped_lock lock{bbsc_independent_incoming_mutex};
    if(bbsc_independent_incoming.size()<128)
        bbsc_independent_incoming.push_back({sender,c,{payload.begin(),payload.end()}});
}

// At the native send ENTRY: filtering before reliable sequence assignment avoids
// gaps. Handshakes remain native. A follower's hit uses the map owner's actual
// member identity rather than changing the native session's host globally.
void PS4_SYSV_ABI BbscWorldPacketSend(u64,const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscIndependentActive() || bbsc_independent_send_depth) return;
    auto* r=const_cast<GuestRegisterSnapshot*>(regs);
    const u32 channel=static_cast<u32>(r->rdx);
    const auto policy=World::ChannelPolicy(channel);
    const u32 role=bbsc_independent_role.load(),owner=bbsc_independent_owner.load();
    bool drop=channel>=0x44;
    if(policy==World::NativePolicy::Drop || policy==World::NativePolicy::Personal) drop=true;
    if(policy==World::NativePolicy::SamePlace) {
        const u32 peer=BbscWorldPeer(r->rsi);
        drop= !BbscWorldSendHere(peer);
        if(channel==0x16 || channel==0x17) drop=true; // one owner per map, no native hand-out
        if(channel==0x15) {
            if(role==1) drop=true; // its own hit already applied
            else if(role==2) {
                const u64 target=BbscWorldNativeMember(owner);
                if(target){r->rsi=target;drop=false;}else drop=true;
            }
        }
        if(channel==0x04 || channel==0x05 || channel==0x29 || channel==0x36)
            drop=drop || role!=1;
    }
    if(drop){r->rax=0;bbsc_independent_send_skip=1;}
}

alignas(16) std::array<u8,0x130> bbsc_world_host_state{},bbsc_world_guest_state{};
thread_local u64 bbsc_world_hp_original=0;
u64 BbscWorldStateStandIn(s32 role) {
    return reinterpret_cast<u64>((role==3?bbsc_world_host_state:bbsc_world_guest_state).data());
}
void PS4_SYSV_ABI BbscWorldHpRound(u64,const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscIndependentActive() || !bbsc_independent_role.load()) return;
    auto* r=const_cast<GuestRegisterSnapshot*>(regs);
    const u64 zero=u64{1}<<6;
    if(bbsc_independent_role.load()==1) r->rflags|=zero;else r->rflags&=~zero;
}
void PS4_SYSV_ABI BbscWorldHpState(u64,const GuestRegisterSnapshot* regs) {
    bbsc_world_hp_original=0;
    if(!regs || !BbscIndependentActive() || !bbsc_independent_role.load()) return;
    auto* r=const_cast<GuestRegisterSnapshot*>(regs);
    bbsc_world_hp_original=r->rdi;r->rdi=BbscWorldStateStandIn(bbsc_independent_role.load()==1?3:6);
}
void PS4_SYSV_ABI BbscWorldHpRestore(u64,const GuestRegisterSnapshot* regs) {
    if(regs && bbsc_world_hp_original) {
        const_cast<GuestRegisterSnapshot*>(regs)->rdi=bbsc_world_hp_original;bbsc_world_hp_original=0;
    }
}
void PS4_SYSV_ABI BbscWorldHpSource(u64,const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscIndependentActive() || regs->r12!=5 || bbsc_independent_role.load()!=2) return;
    const u64 entry=BbscWorldNativeMember(bbsc_independent_owner.load());
    if(entry) const_cast<GuestRegisterSnapshot*>(regs)->rbx=entry-0xD0;
}
void PS4_SYSV_ABI BbscWorldHitState(u64,const GuestRegisterSnapshot* regs) {
    if(regs && BbscIndependentActive() && bbsc_independent_role.load()==2)
        const_cast<GuestRegisterSnapshot*>(regs)->rax=BbscWorldStateStandIn(6);
}

template<class Visit> void BbscWorldCharacters(u64 world,Visit visit) {
    if(!ReadablePointer(world,0x30)) return;
    const s32 blocks=ReadValue<s32>(world,0x20);const u64 base=ReadValue<u64>(world,0x28);
    if(blocks<0 || blocks>64 || !ReadablePointer(base,static_cast<size_t>(blocks)*0x160)) return;
    for(s32 b=0;b<blocks;++b) {
        const u64 record=base+static_cast<u64>(b)*0x160;
        const s32 count=ReadValue<s32>(record,0xB8);const u64 entries=ReadValue<u64>(record,0xC0);
        if(count<0 || count>1024 || !ReadablePointer(entries,static_cast<size_t>(count)*0x38)) continue;
        for(s32 i=0;i<count;++i){const u64 chr=ReadValue<u64>(entries,static_cast<size_t>(i)*0x38);
            if(ReadablePointer(chr,0x400)) visit(chr);}
    }
}
std::set<u64> BbscWorldPlayers(u64 world) {
    std::set<u64> players{GetLocalPlayerCharacter()};
    if(!ReadablePointer(world,0x40)) return players;
    const s32 count=ReadValue<s32>(world,0x30);const u64 entries=ReadValue<u64>(world,0x38);
    if(count<0 || count>64 || !ReadablePointer(entries,static_cast<size_t>(count)*0x38)) return players;
    for(s32 i=0;i<count;++i) players.insert(ReadValue<u64>(entries,static_cast<size_t>(i)*0x38));
    return players;
}
u64 BbscWorldOwnershipWord(u64 world,u64 chr) {
    const s32 index=ReadValue<s32>(chr,0x90);if(index<0) return 0;
    const u64 sync=ReadValue<u64>(world,0xA40);
    if(!ReadablePointer(sync,0x110)) return 0;
    const u32 block=(index>>11)&31,slot=index&0x7FF;
    if(block>=ReadValue<u32>(sync,8)) return 0;
    const u64 entry=ReadValue<u64>(sync,0x10+block*8);
    if(!ReadablePointer(entry,0x20) || slot>=ReadValue<u32>(entry,0x10)) return 0;
    const u64 words=ReadValue<u64>(entry,0x18);
    return HasMemoryAccess(words+slot*2,2,MemoryProt::CpuWrite)?words+slot*2:0;
}
// Exact entity lookup from the native sorted pairs. Never identify an NPC by
// an assumed character slot, which changes across maps/loads.
u64 BbscWorldDoll(u64 world) {
    if(GetCurrentPackedMap()!=0x15000000 || !ReadablePointer(world,0x118)) return 0;
    const s32 tables=ReadValue<s32>(world,0x90),blocks=ReadValue<s32>(world,0x20);
    const u64 base=ReadValue<u64>(world,0x28);
    if(tables<0 || tables>16 || blocks<0 || blocks>64) return 0;
    for(s32 t=0;t<tables;++t){const u64 table=ReadValue<u64>(world,0x98+t*8);
        if(!ReadablePointer(table,0xF0)) continue;
        const s32 count=ReadValue<s32>(table,0xE0);const u64 pairs=ReadValue<u64>(table,0xE8);
        if(count<0 || count>4096 || !ReadablePointer(pairs,static_cast<size_t>(count)*8)) continue;
        for(s32 i=0;i<count;++i) if(ReadValue<s32>(pairs,i*8)==2100700){
            const s32 packed=ReadValue<s32>(pairs,i*8+4);
            const u32 block=(packed>>14)&63,slot=packed&0x3FFF;
            if(packed<0 || block>=static_cast<u32>(blocks)) return 0;
            const u64 record=base+block*0x160;
            if(!ReadablePointer(record,0xC8) || slot>=ReadValue<u32>(record,0xB8)) return 0;
            return ReadValue<u64>(ReadValue<u64>(record,0xC0),slot*0x38);
        }}
    return 0;
}
void PS4_SYSV_ABI BbscWorldOwnership(u64,const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscIndependentActive()) return;
    const u32 role=bbsc_independent_role.load();if(!role) return;
    const u64 world=regs->rdi;if(!ReadablePointer(world,0xA48)) return;
    const auto players=BbscWorldPlayers(world);const u64 doll=BbscWorldDoll(world);
    BbscWorldCharacters(world,[&](u64 chr){
        if(players.contains(chr)) return;
        const u64 word=BbscWorldOwnershipWord(world,chr);if(!word) return;
        const u64 control=ReadValue<u64>(chr,0x18);if(!ReadablePointer(control,0x2C)) return;
        const bool awake=ReadValue<s32>(control,0x14)==4 || ReadValue<s32>(control,0x10)==4;
        if(chr==doll) {WriteValue<u16>(word,0,1);return;}
        if(!awake) return;
        WriteValue<u16>(word,0,role==1?u16{1}:u16{0xFFFF});
    });
}

struct BbscWorldWakeRecord {u64 record;std::array<u32,24> before;};
thread_local std::vector<BbscWorldWakeRecord> bbsc_world_wake_records;
void BbscWorldRestoreWake() {
    for(const auto& saved:bbsc_world_wake_records)if(HasMemoryAccess(saved.record+0x18,0x80,MemoryProt::CpuWrite))
        for(size_t set=0;set<3;++set)for(size_t i=0;i<8;++i)
            WriteValue<u32>(saved.record,(set==0?0x38:set==1?0x18:0x78)+i*4,saved.before[set*8+i]);
    bbsc_world_wake_records.clear();
}
void PS4_SYSV_ABI BbscWorldWakeEnd(u64,const GuestRegisterSnapshot*){BbscWorldRestoreWake();}
void PS4_SYSV_ABI BbscWorldWakeBegin(u64,const GuestRegisterSnapshot* regs) {
    BbscWorldRestoreWake();
    if(!regs || !BbscIndependentActive() || !bbsc_independent_role.load())return;
    const u64 world=regs->rdi,local=GetLocalPlayerCharacter();
    if(!ReadablePointer(world,0x880) || !ReadablePointer(local,0x278))return;
    std::array<u32,24> others{};
    for(const auto chr:BbscWorldPlayers(world)) {
        if(!chr || chr==local || !ReadablePointer(chr,0x400) || GetCharacterHp(chr)<=0 || !BbscWorldActorHere(chr))continue;
        for(size_t set=0;set<3;++set)for(size_t i=0;i<8;++i) {
            const u32 group=ReadValue<u32>(chr,0x218+set*0x20+i*4);
            if(group!=0xFFFFFFFFu)others[set*8+i]|=group;
        }
    }
    const s32 count=ReadValue<s32>(world,0x278);if(count<0 || count>62)return;
    for(s32 block=0;block<count;++block){
        const u64 record=ReadValue<u64>(world,0x290+block*0x18);
        if(!HasMemoryAccess(record+0x18,0x80,MemoryProt::CpuWrite))continue;
        bool own=false;for(size_t i=0;i<8;++i)own|=(ReadValue<u32>(record,0x38+i*4)&ReadValue<u32>(local,0x218+i*4))!=0;
        if(!own)continue;
        BbscWorldWakeRecord saved;saved.record=record;
        for(size_t set=0;set<3;++set)for(size_t i=0;i<8;++i){const size_t offset=(set==0?0x38:set==1?0x18:0x78)+i*4;
            saved.before[set*8+i]=ReadValue<u32>(record,offset);
            WriteValue<u32>(record,offset,saved.before[set*8+i]|others[set*8+i]);
        }
        bbsc_world_wake_records.push_back(saved);
    }
}

// Names supplied by native registration must cover every current room member.
// A legacy/missing peer keeps the old native behavior and lamps closed.
bool BbscWorldAllMembersReady() {
    if(!bbsc_independent_hooks.load() || !bbsc_independent_travel_hooks.load()) return false;
    const s32 count=GetBbscSessionMemberCount(GetGlobalState());
    if(count<2 || count>5) return false;
    const auto tasks=GetMultiPlayerInsTasks();std::set<u32> peers;
    for(const auto task:tasks){
        const auto mode=ReadValue<s32>(task,0xE8);
        // Native self tasks are mode3 (host) / mode0 (guest). Remote tasks
        // are mode1 (guest) / mode2 (host); never negotiate against ourselves.
        if(mode!=1 && mode!=2) continue;
        if(ReadValue<u8>(task,0xED)&2) continue;
        const u32 peer=mode==2 && GetSessionState()==6 ? GetBbscRelayHost() : BbscWorldPeer(task+0xC8);
        if(!peer) return false;peers.insert(peer);
    }
    if(peers.size()!=static_cast<size_t>(count-1)) return false;
    const std::vector<u32> roster(peers.begin(),peers.end());
    std::scoped_lock lock{bbsc_world_presence_mutex};
    return bbsc_world_presence_book.AllSupportTravel(bbsc_world_presence_local,roster,SteadyNowMs());
}

// Other peers' actors stay bound to their identities. Native SetDisable controls
// off-map copies; no health or player-type edits are used to hide an actor.
void BbscWorldHideApart() {
    if(!BbscIndependentActive()) return;
    const u64 world=ReadValue<u64>(image_base+CandidateLocalStatePointerOffset,0);
    const u64 local=GetLocalPlayerCharacter();
    for(const auto chr:BbscWorldPlayers(world)) {
        if(!chr || chr==local || !ReadablePointer(chr,0x400)) continue;
        const u32 peer=BbscWorldPeer(chr+0x3D8);if(!peer) continue;
        using Set=void PS4_SYSV_ABI (*)(u64,u32);
        reinterpret_cast<Set>(image_base+0x018C6390)(chr,BbscWorldPeerHere(peer)?0:1);
    }
}

// Travel/catalog/ordered world updates follow below. All hook readiness is
// published together after every expected byte has been checked.
void TickBbscWorldTravel();
void TickBbscWorldSnapshots();
void TickBbscWorldAltars();
void InstallBbscWorldTravel();
#include "core/bbsc_world_state.inc"
#include "core/bbsc_world_travel.inc"
void TickBbscIndependentWorld() {
    BbscWorldCoordinate();
    static World::WorldId negotiated_world{};
    World::WorldId current_world;
    {std::scoped_lock lock{bbsc_world_presence_mutex};current_world=bbsc_world_presence_local.world;}
    if(!World::Valid(current_world)) negotiated_world={};
    else if(current_world!=negotiated_world && BbscWorldAllMembersReady()) negotiated_world=current_world;
    // Loading may temporarily remove native actor tasks/heartbeats. It must not
    // turn follow back on and undo an already negotiated independent journey.
    const bool active=World::Valid(current_world) && current_world==negotiated_world &&
                      !BbscQuitInProgress() && !BbscReturningToTitle();
    if(bbsc_independent_active.exchange(active)!=active) {
        LOG_INFO(Debug,"BBSC independent world: {} (all current members negotiated)",active?"active":"waiting");
        BBSC_TIMELINE("WORLD","independent world {}",active?"active":"waiting");
    }
    u32 owner=0,role=0;
    if(active) {
        std::scoped_lock lock{bbsc_world_presence_mutex};
        if(bbsc_world_presence_local.phase==World::Phase::Playing) {
            const auto* lease=bbsc_independent_owners.Find(World::ScopeOf(bbsc_world_presence_local));
            if(lease && lease->owner){owner=lease->owner;role=owner==BbscMod::RegisterOwnId()?1:2;}
        }
    }
    static u64 previous_visit=0;
    if(active){
        u64 visit=0;{std::scoped_lock lock{bbsc_world_presence_mutex};visit=bbsc_world_presence_local.visit;}
        if(previous_visit && previous_visit!=visit) DiscardBbscWorldScenes();
        previous_visit=visit;
    }else previous_visit=0;
    bbsc_independent_owner=owner;bbsc_independent_role=role;
    TickBbscWorldAltars();TickBbscWorldSnapshots();TickBbscWorldTravel();
    if(active) BbscWorldHideApart();
}

void InstallBbscIndependentWorld() {
    // Whole instruction spans from CUSA03173 1.09, matched before any mutation.
    struct Site {u64 offset;std::vector<u8> bytes;GuestCodeHook hook;const u8* skip;};
    const std::array sites{
        Site{0x017894E0,{0x55,0x48,0x89,0xE5,0x41,0x57},BbscWorldPacketSend,&bbsc_independent_send_skip},
        Site{0x018EF26C,{0x48,0x8B,0x9D,0x08,0xFF,0xFF,0xFF},BbscWorldHpRound,nullptr},
        Site{0x018EF578,{0x8B,0x87,0x24,0x01,0x00,0x00},BbscWorldHpState,nullptr},
        Site{0x018EF587,{0x80,0xBB,0x64,0x06,0x00,0x00,0x00},BbscWorldHpRestore,nullptr},
        Site{0x018EF684,{0x49,0x89,0xDC,0x48,0x85,0xFF},BbscWorldHpRestore,nullptr},
        Site{0x01789495,{0x48,0x81,0xC3,0xD0,0x00,0x00,0x00},BbscWorldHpSource,nullptr},
        Site{0x01A2A102,{0x8B,0x88,0x24,0x01,0x00,0x00},BbscWorldHitState,nullptr},
        Site{0x019173B0,{0x55,0x48,0x89,0xE5,0x41,0x57},BbscWorldOwnership,nullptr},
        Site{0x019192A0,{0x55,0x48,0x89,0xE5,0x41,0x57},BbscWorldWakeBegin,nullptr},
        Site{0x0191987E,{0x8A,0x5D,0x97,0x80,0xE3,0x01},BbscWorldWakeEnd,nullptr}};
    for(const auto& site:sites) if(!ReadablePointer(image_base+site.offset,site.bytes.size()) ||
        std::memcmp(reinterpret_cast<const void*>(image_base+site.offset),site.bytes.data(),site.bytes.size())) {
        LOG_ERROR(Debug,"BBSC independent world: native site {:#x} differs; feature remains inactive",site.offset);return;
    }
    static constexpr std::array<u8,6> GetterPrologue{0x55,0x48,0x89,0xE5,0x41,0x57};
    for(u64 offset:{0x01AB2A40ull,0x01AB1DB0ull,0x01AB3070ull,0x01AB31C0ull,
                    0x018C6390ull,0x018BCD40ull,0x012B2960ull})
        if(!ReadablePointer(image_base+offset,GetterPrologue.size()) ||
           std::memcmp(reinterpret_cast<const void*>(image_base+offset),GetterPrologue.data(),GetterPrologue.size())){
            LOG_ERROR(Debug,"BBSC independent world: native callable {:#x} differs",offset);return;
        }
    const s32 host=3,guest=6;
    std::memcpy(bbsc_world_host_state.data()+0x124,&host,4);
    std::memcpy(bbsc_world_guest_state.data()+0x124,&guest,4);
    for(const auto& site:sites) if(!InstallGuestCodeHook(reinterpret_cast<void*>(image_base+site.offset),site.bytes,0,site.hook,site.skip)) {
        LOG_ERROR(Debug,"BBSC independent world: could not install site {:#x}; feature remains inactive",site.offset);return;
    }
    bbsc_independent_hooks=true;
    InstallBbscWorldTravel();
    LOG_INFO(Debug,"BBSC independent world: native enemy authority hooks installed");
}
#else
bool BbscIndependentActive(){return false;}
bool BbscIndependentTravelAllowed(){return false;}
bool BbscWorldTalkAllowed(u32){return false;}
bool QueueBbscWorldTravel(u32,u8){return false;}
bool BbscWorldTaskHere(u64){return true;}
u32 BbscWorldLivingHere(){return 0;}
u32 BbscWorldParticipantsHere(){return 0;}
bool BbscWorldPeerHere(u32){return true;}
bool BbscWorldActorHere(u64){return true;}
u32 BbscIndependentCapabilities(){return World::PresenceCapability;}
u64 BbscIndependentRitual(const Chalice::Key&){return 0;}
Chalice::Key BbscIndependentDungeonKey(const Chalice::Key& key){return key;}
bool BbscWorldMountFor(u32,Chalice::Mount&){return false;}
bool BbscWorldHasSnapshot(u32){return false;}
void ApplyBbscIndependentAtLoad(u32){}
bool BbscWorldProtectAltar(u32,u32){return false;}
bool BbscWorldTravelInFlight(){return false;}
void QueueBbscWorldAltarWrite(u32,u32,u32){}
void TickBbscIndependentWorld(){}
void InstallBbscIndependentWorld(){}
void ProcessBbscWorldControl(u32,const World::Control&,std::span<const u8>){}
void BbscWorldCoordinate(){}
#endif
