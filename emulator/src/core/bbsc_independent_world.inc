// SPDX-License-Identifier: GPL-2.0-or-later
// Included inside bloodborne_re.cpp's implementation namespace. Native offsets
// and ownership approach: CLS_AMG / Yharnam Together, GPL-2.0-or-later. Adapted
// to BBSC's native direct P2P transport; no replacement transport or server.
#ifdef BBSC_MOD
std::atomic<bool> bbsc_independent_hooks{false}, bbsc_independent_active{false};
std::atomic<bool> bbsc_independent_travel_hooks{false};
std::atomic<bool> bbsc_world_native_warp_hook{false};
std::atomic<u32> bbsc_independent_role{0}, bbsc_independent_owner{0};
World::OwnerBook bbsc_independent_owners; // protected by presence mutex
bool BbscIndependentActive();
// ORIGINAL01914C70 indexes records by native block ID (+28, stride160),
// publishes the keyed actor list at +850+ID*8, and separately INSERTS into
// the SORTED +280 list. A native ID is NOT its position in that compact list.
u64 BbscWorldNpcBlock(u64 world,u32 block) {
    if(block>=32 || !ReadablePointer(world,0xA48))return 0;
    const s32 count=ReadValue<s32>(world,0x20);
    if(count<0 || count>64 || block>=static_cast<u32>(count))return 0;
    const u64 base=ReadValue<u64>(world,0x28),record=base+static_cast<u64>(block)*0x160;
    if(!ReadablePointer(record,0xC8) ||
       ReadValue<u64>(world,0x850+block*8)!=record+0xB8)return 0;
    return record;
}
std::map<World::Scope,World::OwnerLease> bbsc_independent_elected;
u64 bbsc_independent_epoch = 0;
World::WorldId bbsc_independent_bound{};
struct BbscWorldIncoming {u32 sender;World::Control control;std::vector<u8> payload;};
void BbscWorldReceiveLampCheckpoint(const BbscWorldIncoming& message);
std::mutex bbsc_independent_incoming_mutex;
std::deque<BbscWorldIncoming> bbsc_independent_incoming;
thread_local u8 bbsc_independent_send_depth = 0;
u8 bbsc_independent_send_skip = 0;
bool BbscWorldSceneReady();
bool BbscWorldBlocksActive();
bool BbscWorldBlockSimulation();
bool BbscWorldAdmitBlocks(const World::Scope& scope);
void TickBbscWorldBlocks();
void BbscWorldCoordinateBlocks();
void BbscWorldReceiveBlock(const BbscWorldIncoming& message);
bool BbscCombatTraceEnabled();
void TraceBbscCombatActor(std::string_view stage,u64 actor,s32 requested_hp,bool begin);
void TraceBbscCombatPacket(std::string_view stage,u32 channel,u32 peer,std::span<const u8> record,bool admitted);
u32 BbscWorldBlockRole(u64 chr);
bool BbscWorldBlockOwnsAny();
u64 BbscWorldBlockHpMember();
bool BbscWorldBlockPacketSend(GuestRegisterSnapshot* regs);
bool BbscWorldNativeInitialReady(const World::Scope& scope,u32 owner,u64 epoch);
void BbscWorldNativeInitialControl(const BbscWorldIncoming& message);
void BbscWorldNativeInitialOnce(const World::Scope& scope);
thread_local std::vector<u8>* bbsc_world_initial_capture=nullptr;
thread_local u32 bbsc_world_initial_sending=0;
thread_local u64 bbsc_world_initial_fingerprint=0;

bool BbscIndependentActive() {return bbsc_independent_active.load(std::memory_order_acquire);}
bool BbscIndependentTravelAllowed() {
    return BbscIndependentActive() && bbsc_independent_travel_hooks.load() &&
           !BbscQuitInProgress() && !BbscReturningToTitle();
}
u32 BbscIndependentCapabilities() {
    if(SessionTest::NativeNpcSync())
        return World::PresenceCapability | SessionTest::Capability |
            (bbsc_independent_travel_hooks.load()?World::OwnerCapability|World::IndependentTravelCapability:0);
    return World::PresenceCapability |
        (bbsc_independent_hooks.load() ? World::OwnerCapability|World::BlockCapability : 0) |
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

// Native NPC request lists used PlayerIns handles as opaque participant keys.
// Independent maps have no remote PlayerIns. Bind an opaque, non-reused key to
// the complete current room identity instead; never retain an actor/roster ptr.
struct BbscNpcMemberBinding {u32 peer=0;BbscMod::RegisterIdentity identity{};};
std::mutex bbsc_npc_member_mutex;
std::map<u32,BbscNpcMemberBinding> bbsc_npc_members;
std::map<u32,u32> bbsc_npc_peer_keys;
World::WorldId bbsc_npc_member_world{};
u32 bbsc_npc_member_sequence=0; // process lifetime; never reuse a departed key

World::WorldId BbscWorldNpcRoom() {
    std::scoped_lock lock{bbsc_world_presence_mutex};
    return bbsc_world_presence_local.world;
}
bool BbscWorldNpcHost() {
    const u64 manager=ReadValue<u64>(image_base+MatchingStatePointerOffset,0);
    return ReadablePointer(manager,0x128) && ReadValue<u32>(manager,0x124)==3;
}
void BbscWorldNpcForgetPeer(u32 peer,bool host) {
    std::scoped_lock lock{bbsc_npc_member_mutex};
    if(host){bbsc_npc_members.clear();bbsc_npc_peer_keys.clear();bbsc_npc_member_world={};return;}
    const auto key=bbsc_npc_peer_keys.find(peer);
    if(key!=bbsc_npc_peer_keys.end()){
        bbsc_npc_members.erase(key->second);bbsc_npc_peer_keys.erase(key);
    }
}
bool BbscWorldNpcRoomKeyMode() {
    if(BbscIndependentActive())return true;
    const auto world=BbscWorldNpcRoom();
    std::scoped_lock lock{bbsc_npc_member_mutex};
    // Once this room accepted a room-key request, keep using that key space
    // through temporary loading/negotiation. Do not create a PlayerIns alias.
    return World::Valid(world) && world==bbsc_npc_member_world;
}
u32 PS4_SYSV_ABI BbscWorldNpcRequestMember(u64 member,u32 bytes) {
    if(!BbscWorldNpcRoomKeyMode())return 1; // original join before room-key admission
    if(!BbscWorldNpcHost() || bytes<4 || bytes>0x1000 || (bytes&3) ||
       !ReadablePointer(image_base+0x05570090,bytes))return 0;
    const u32 count=ReadValue<u32>(image_base+0x05570090,0);
    if(count!=(bytes-4)/4)return 0; // native list assignment must not overread
    const u32 peer=BbscWorldPeer(member);
    const auto world=BbscWorldNpcRoom();
    if(!peer || peer==BbscMod::RegisterOwnId() || !World::Valid(world) ||
       world.host!=BbscMod::RegisterOwnId() || BbscWorldNativeMember(peer)!=member)return 0;
    const auto identity=BbscWorldIdentity(member);
    u32 key=0;
    {
        std::scoped_lock lock{bbsc_npc_member_mutex};
        if(bbsc_npc_member_world!=world){
            bbsc_npc_members.clear();bbsc_npc_peer_keys.clear();bbsc_npc_member_world=world;
        }
        const auto previous=bbsc_npc_peer_keys.find(peer);
        if(previous!=bbsc_npc_peer_keys.end()){
            auto& binding=bbsc_npc_members.at(previous->second);
            if(!std::memcmp(&binding.identity,&identity,sizeof(identity)))return previous->second;
            bbsc_npc_members.erase(previous->second);bbsc_npc_peer_keys.erase(previous);
        }
        if(bbsc_npc_members.size()>=8 || bbsc_npc_member_sequence>=0x7FFFFFFE)return 0;
        key=0x80000000u|++bbsc_npc_member_sequence;
        bbsc_npc_members.emplace(key,BbscNpcMemberBinding{peer,identity});
        bbsc_npc_peer_keys.emplace(peer,key);
    }
    BBSC_TIMELINE("WORLD","NPC native request member admitted peer={:08x} key={:#x} room={:016x} actor_required=false",
        peer,key,world.room);
    return key;
}
u64 PS4_SYSV_ABI BbscWorldNpcGrantMember(u32 key) {
    if(!(key&0x80000000u) || key==0xFFFFFFFFu || !BbscWorldNpcHost())return 0;
    const auto world=BbscWorldNpcRoom();
    BbscNpcMemberBinding binding;
    {
        std::scoped_lock lock{bbsc_npc_member_mutex};
        const auto found=bbsc_npc_members.find(key);
        if(!World::Valid(world) || world.host!=BbscMod::RegisterOwnId() ||
           world!=bbsc_npc_member_world || found==bbsc_npc_members.end())return 0;
        binding=found->second;
    }
    const u64 member=BbscWorldNativeMember(binding.peer);
    const auto identity=member?BbscWorldIdentity(member):BbscMod::RegisterIdentity{};
    if(!member || std::memcmp(&binding.identity,&identity,sizeof(identity))){
        std::scoped_lock lock{bbsc_npc_member_mutex};
        const auto previous=bbsc_npc_peer_keys.find(binding.peer);
        if(previous!=bbsc_npc_peer_keys.end() && previous->second==key){
            bbsc_npc_members.erase(key);bbsc_npc_peer_keys.erase(previous);
        }
        return 0;
    }
    return member;
}
u64 PS4_SYSV_ABI BbscWorldNpcRetainMember(u32 key) {
    if(key&0x80000000u)return BbscWorldNpcGrantMember(key);
    if(!BbscWorldNpcRoomKeyMode())return 1; // original native join lookup
    // Once active, remote requests use room keys exclusively. Drop an old
    // PlayerIns-keyed alias from the join fallback so one peer cannot receive
    // two separate grant packets, each resetting its complete ownership table.
    const u64 world=ReadValue<u64>(image_base+CandidateLocalStatePointerOffset,0);
    const u64 self=ReadablePointer(world,0x68)?ReadValue<u64>(world,0x60):0;
    return ReadablePointer(self,0xC) && ReadValue<u32>(self,8)==key?1:0;
}
bool BbscWorldPeerHere(u32 peer) {
    if (!BbscIndependentActive()) return true;
    std::scoped_lock lock{bbsc_world_presence_mutex};
    const auto* m=bbsc_world_presence_book.Resident(peer);
    return m && World::SamePlace(bbsc_world_presence_local,m->presence);
}
bool BbscLectureExitRecipient(u64 member) {
    const s32 state=GetSessionState();
    if(state!=3 && state!=6)return false;
    // Both areas use m32_00. Their playable geometry is separated along Z
    // in the original MapStudio data. Both Lecture floors are north of 480.
    const auto here=ReadCharacterTransform(GetLocalPlayerCharacter());
    return here && here->position[2]>=480.0f && BbscWorldPeerHere(BbscWorldPeer(member));
}
bool BbscWorldActorHere(u64 chr) {
    return !BbscIndependentActive() || BbscWorldPeerHere(BbscWorldPeer(chr+0x3D8));
}
bool BbscWorldSendHere(u32 peer) {
    std::scoped_lock lock{bbsc_world_presence_mutex};
    if(!peer || !bbsc_world_presence_book.Known(peer)) return true; // native first-sync bootstrap
    const auto* m=bbsc_world_presence_book.Resident(peer);
    return m && World::SamePlace(bbsc_world_presence_local,m->presence);
}
bool BbscWorldPlayerSendHere(u32 peer) {
    std::scoped_lock lock{bbsc_world_presence_mutex};
    const auto* member=bbsc_world_presence_book.Resident(peer);
    return member && World::SamePlayerSpace(bbsc_world_presence_local,member->presence);
}
u32 BbscWorldLivingHere() {
    std::scoped_lock lock{bbsc_life_mutex, bbsc_world_presence_mutex};
    return bbsc_world_presence_book.LivingHere(bbsc_world_presence_local, [](u32 peer, s64 present_at) {
        // A room member can report death before its map presence arrives.
        // Use the explicit newer report without treating silence as a death.
        const auto life = bbsc_peer_life.find(peer);
        return life != bbsc_peer_life.end() && life->second.dead &&
               life->second.received_ms >= present_at;
    });
}
u32 BbscWorldParticipantsHere() {
    std::scoped_lock lock{bbsc_world_presence_mutex};u32 count=0;
    for(const auto& [peer,m]:bbsc_world_presence_book.Members())
        count+=World::SamePlace(bbsc_world_presence_local,m.presence);
    return count;
}
bool BbscWorldTaskHere(u64 task) {
    if (!BbscIndependentActive()) return true;
    const s32 mode=ReadValue<s32>(task,0xE8);
    const u32 peer=mode==2 && GetSessionState()==6 ? GetBbscRelayHost() : BbscWorldPeer(task+0xC8);
    std::scoped_lock lock{bbsc_world_presence_mutex};
    const auto* member=bbsc_world_presence_book.Resident(peer);
    return peer && member && World::SamePlayerSpace(bbsc_world_presence_local,member->presence);
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
            const bool lease_changed=!previous.epoch || previous.owner!=owner;
            if(lease_changed) {previous={owner,++bbsc_independent_epoch,SteadyNowMs()};changed=true;}
            World::Control c;c.kind=World::ControlKind::Owner;c.scope=scope;c.owner=owner;c.epoch=previous.epoch;
            if(std::ranges::none_of(send,[&](const auto& p){return p.scope==scope;})) {
                bbsc_independent_owners.Take(self,c,SteadyNowMs());
                send.push_back(c);
            }
        }
        const s64 now=SteadyNowMs();
        if(!changed && now-last_sent<1000)send.clear();else last_sent=now;
    }
    for(const auto& c:send) BbscWorldSend(c);
    BbscWorldCoordinateBlocks();
}

void ProcessBbscWorldControl(u32 sender,const World::Control& c,std::span<const u8> payload) {
    if(c.kind==World::ControlKind::BlockOffer || c.kind==World::ControlKind::BlockLease){
        BbscWorldReceiveBlock({sender,c,{payload.begin(),payload.end()}});return;
    }
    if(c.kind==World::ControlKind::Owner) {
        std::scoped_lock lock{bbsc_world_presence_mutex};
        if(c.scope.world!=bbsc_world_presence_local.world) return;
        bbsc_independent_owners.Bind(c.scope.world);
        bbsc_independent_owners.Take(sender,c,SteadyNowMs());
        return;
    }
    std::scoped_lock lock{bbsc_independent_incoming_mutex};
    if (BbscNativeFinaleCommitted()) return;
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
    // A load-only snapshot borrows the original serializer. Its temporary
    // packet goes through the existing world-control delivery, so reception
    // wakes the game-thread handler without polling a second native queue.
    if(SessionTest::NativeNpcSync()){
        if(channel==0x11 && bbsc_world_initial_capture && r->r8<=0x6400 &&
           ReadablePointer(r->rcx,static_cast<size_t>(r->r8))){
            const auto* bytes=reinterpret_cast<const u8*>(r->rcx);
            bbsc_world_initial_capture->assign(bytes,bytes+r->r8);
            r->rax=1;bbsc_independent_send_skip=1;
        }
        return; // native combat, ownership and all ordinary packets unchanged
    }
    // Native channel34 is one handle plus three 8-word draw/display/backread
    // group sets (018BE2CA..018BE404). Only our own PlayerIns record may cross
    // a player border here; NPC records retain the exact-place policy below.
    if(channel==0x34 && r->r8==100 && ReadablePointer(r->rcx,100)){
        const u64 player=GetLocalPlayerCharacter();
        if(ReadablePointer(player,0x94) && ReadValue<u32>(r->rcx,0)==ReadValue<u32>(player,0x90) &&
           BbscWorldPlayerSendHere(BbscWorldPeer(r->rsi)))return;
    }
    if(BbscWorldBlockSimulation() && BbscWorldBlockPacketSend(r))return;
    if(channel==0x11 && bbsc_world_initial_sending && BbscWorldPeer(r->rsi)==bbsc_world_initial_sending &&
       r->r8<=0x6400 && ReadablePointer(r->rcx,static_cast<size_t>(r->r8)))
        bbsc_world_initial_fingerprint=World::NativeInitialFingerprint(
            {reinterpret_cast<const u8*>(r->rcx),static_cast<size_t>(r->r8)});
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
        // Native host object corrections must not override the map owner after
        // the host leaves/returns. Otherwise two copies keep resetting objects.
        if(channel==0x04 || channel==0x05 || channel==0x29 || channel==0x36 || channel==0x2F)
            drop=drop || role!=1;
    }
    if(drop){r->rax=0;bbsc_independent_send_skip=1;}
}

alignas(16) std::array<u8,0x130> bbsc_world_host_state{},bbsc_world_guest_state{};
thread_local u64 bbsc_world_hp_original=0;
thread_local u64 bbsc_world_hp_receive_frame=0;
u8 bbsc_world_hp_receive_skip=0;
u64 BbscWorldStateStandIn(s32 role) {
    return reinterpret_cast<u64>((role==3?bbsc_world_host_state:bbsc_world_guest_state).data());
}
void PS4_SYSV_ABI BbscWorldHpRound(u64,const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscIndependentActive() || !bbsc_independent_role.load()) return;
    auto* r=const_cast<GuestRegisterSnapshot*>(regs);
    const u64 zero=u64{1}<<6;
    if(BbscWorldBlockSimulation()?BbscWorldBlockOwnsAny():bbsc_independent_role.load()==1) r->rflags|=zero;else r->rflags&=~zero;
}
void PS4_SYSV_ABI BbscWorldHpState(u64,const GuestRegisterSnapshot* regs) {
    bbsc_world_hp_original=0;
    bbsc_world_hp_receive_frame=0;
    if(!regs || !BbscIndependentActive() || !bbsc_independent_role.load()) return;
    auto* r=const_cast<GuestRegisterSnapshot*>(regs);
    const bool blocks=BbscWorldBlockSimulation();
    const bool producer=blocks?BbscWorldBlockOwnsAny():bbsc_independent_role.load()==1;
    // Native role3 drains DIRTY HP (bit20), role6 only receives. Forcing every
    // block participant to role6 suppressed the dirty producer, leaving only
    // the slow ten-entry/every-fourth-frame sweep above. An owner must produce
    // AND receive: at the verified common tail, enter the original role6 body
    // once after its role3 body, using the same native sync object/stack.
    if(blocks && producer)bbsc_world_hp_receive_frame=r->rbp;
    bbsc_world_hp_original=r->rdi;r->rdi=BbscWorldStateStandIn(producer?3:6);
}
void PS4_SYSV_ABI BbscWorldHpRestore(u64,const GuestRegisterSnapshot* regs) {
    if(regs && bbsc_world_hp_original) {
        const_cast<GuestRegisterSnapshot*>(regs)->rdi=bbsc_world_hp_original;bbsc_world_hp_original=0;
    }
}
void PS4_SYSV_ABI BbscWorldHpReceiveAfterSend(u64,const GuestRegisterSnapshot* regs) {
    bbsc_world_hp_receive_skip=0;
    if(!regs || !bbsc_world_hp_receive_frame || regs->rbp!=bbsc_world_hp_receive_frame)return;
    bbsc_world_hp_receive_frame=0; // native receive returns to this SAME tail
    if(!BbscIndependentActive() || !BbscWorldBlockSimulation() ||
       !ReadablePointer(regs->rax,8))return;
    // At018EF94F RAX is the original manager global from LEA018EF948.
    // The continuation018EF6C6 uses RDI immediately, so preserve the displaced
    // load even when the trampoline skips it. R12 is the native sync object.
    const u64 manager=ReadValue<u64>(regs->rax,0);
    if(!ReadablePointer(manager,0x128))return;
    const_cast<GuestRegisterSnapshot*>(regs)->rdi=manager;
    bbsc_world_hp_receive_skip=1;
}
void PS4_SYSV_ABI BbscWorldHpSource(u64,const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscIndependentActive() || regs->r12!=5) return;
    if(!BbscWorldBlockSimulation() && bbsc_independent_role.load()!=2)return;
    const u64 entry=BbscWorldBlockSimulation()?BbscWorldBlockHpMember():BbscWorldNativeMember(bbsc_independent_owner.load());
    if(entry) const_cast<GuestRegisterSnapshot*>(regs)->rbx=entry-0xD0;
}
u8 bbsc_world_hp_apply_enter=0,bbsc_world_hp_apply_skip=0;
void PS4_SYSV_ABI BbscWorldHpApplyBegin(u64,const GuestRegisterSnapshot* regs) {
    // The original NPC HP application loop is guest6/outside-own-world only.
    // A native room host may ALSO follow another participant's block. Enter
    // the SAME loop; its per-target admission below preserves local owners.
    bbsc_world_hp_apply_enter=regs && BbscIndependentActive() &&
        BbscWorldBlockSimulation() && BbscWorldSceneReady();
}
void PS4_SYSV_ABI BbscWorldHpApplyTarget(u64,const GuestRegisterSnapshot* regs) {
    bbsc_world_hp_apply_skip=0;
    if(!regs || !BbscIndependentActive() || !BbscWorldBlockSimulation())return;
    // Native pending HP bit10 was consumed just above01916ED5. Do not apply a
    // queued packet after this actor became local/unadmitted during handover.
    bbsc_world_hp_apply_skip=regs->r15==GetLocalPlayerCharacter() || BbscWorldBlockRole(regs->r15)!=2;
}
void PS4_SYSV_ABI BbscWorldHpApplyLethal(u64,const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscIndependentActive() || !BbscWorldBlockSimulation() ||
       static_cast<s32>(regs->rax)!=0 || static_cast<s32>(regs->rsi)!=0)return;
    const u64 chr=regs->r15;
    if(chr==GetLocalPlayerCharacter() || !ReadablePointer(chr,0x3B8) || BbscWorldBlockRole(chr)!=2 ||
       (ReadValue<u8>(chr,0x1E3)&0x27)!=0)return; // requested/in-progress/completed/historical death
    const u64 control=ReadValue<u64>(chr,0x18);
    if(!ReadablePointer(control,0x38) || ReadValue<s32>(control,0x10)!=4 || ReadValue<s32>(control,0x14)!=4)return;
    const u64 proxy=ReadValue<u64>(control,0x30);
    if(ReadablePointer(proxy,0x19) && (ReadValue<u8>(proxy,0x18)&1))return;
    // ORIGINAL01916EEF captures old HP into EAX, then01916EF5 stores it solely
    // for the later positive->zero lethal-edge check. A guest's predicted hit
    // may have already set HP0 before the accepted OWNER HP0 arrives. Preserve
    // that authoritative edge via the native branch's old-HP scratch value.
    // Do not write actor HP/death or call Kill here: original setter, revive/
    // proxy checks and the original single death call remain in control.
    const_cast<GuestRegisterSnapshot*>(regs)->rax=1;
    TraceBbscCombatActor("confirmed-lethal-edge",chr,0,true);
}
void PS4_SYSV_ABI BbscWorldHitState(u64,const GuestRegisterSnapshot* regs) {
    if(regs && BbscIndependentActive() && BbscWorldBlockSimulation()){
        // ORIGINAL1.09: RBX is the attacker (RSI at01A29E57); R12 is the
        // target's damage module (RDI at01A29E5A). The native hit packet at
        // 01A29FED obtains its TARGET from [R12+8]. Choosing the attacker's
        // owner suppresses channel15 for a local player hitting a remote NPC.
        const u64 target=ReadablePointer(regs->r12,0x10)?ReadValue<u64>(regs->r12,8):0;
        TraceBbscCombatActor("hit-selection",target,0,true);
        const_cast<GuestRegisterSnapshot*>(regs)->rax=BbscWorldStateStandIn(BbscWorldBlockRole(target)==1?3:6);return;
    }
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
#ifdef BBSC_PERF_NESTED
    BBSC_PERF_NESTED("measure NPC ownership");
#endif
    if(!regs || !BbscIndependentActive()) return;
    const bool scene_ready=BbscWorldSceneReady();
    const bool owning=bbsc_independent_role.load()==1 && scene_ready;
    const bool blocks=BbscWorldBlockSimulation();
    const u64 world=regs->rdi;if(!ReadablePointer(world,0xA48)) return;
    const auto players=BbscWorldPlayers(world);const u64 doll=BbscWorldDoll(world);
    BbscWorldCharacters(world,[&](u64 chr){
        if(players.contains(chr)) return;
        const u64 word=BbscWorldOwnershipWord(world,chr);if(!word) return;
        const u64 control=ReadValue<u64>(chr,0x18);if(!ReadablePointer(control,0x2C)) return;
        // Current4 can outlive a native backread-off/unload request. Reasserting
        // local ownership from that stale state keeps disabled NPC variants in
        // the owner's simulation set; followers already write FFFF. Native
        // event visibility and the requested activation state win over leases.
        // Clear stale ownership even after current has reached0: otherwise the
        // previous tick's local word survives the old !awake early return.
        if(ReadValue<u8>(chr,0x28) || (ReadValue<u8>(control,0x20)&1) ||
           ReadValue<s32>(control,0x14)!=4){
            if(ReadValue<u16>(word,0)!=0xFFFF)WriteValue<u16>(word,0,0xFFFF);return;
        }
        const bool responsible=chr==doll || (blocks?scene_ready && BbscWorldBlockRole(chr)==1:owning);
        const u16 desired=responsible?u16{1}:u16{0xFFFF};
        if(ReadValue<u16>(word,0)!=desired)WriteValue<u16>(word,0,desired);
    });
}

// A native activation COMPLETION, not the per-frame wake/update entry. RBX is
// the one ChrIns whose native setup succeeded; the displaced instruction then
// commits controller.current=4. Reused for first streaming and reactivation.
void PS4_SYSV_ABI BbscWorldNpcActivated(u64,const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscIndependentActive())return;
    const u64 chr=regs->rbx,world=ReadValue<u64>(image_base+CandidateLocalStatePointerOffset,0);
    if(!ReadablePointer(chr,0x94) || !ReadablePointer(world,0xA48))return;
    const u64 control=ReadValue<u64>(chr,0x18);
    if(!ReadablePointer(control,0x21) || control!=regs->rax ||
       ReadValue<s32>(control,0x14)!=4 || ReadValue<u8>(chr,0x28) ||
       (ReadValue<u8>(control,0x20)&1))return;
    const s32 handle=ReadValue<s32>(chr,0x90);
    if(handle<0)return;
    const u32 block=(static_cast<u32>(handle)>>11)&31,slot=handle&0x7FF;
    const u64 data=BbscWorldNpcBlock(world,block);
    if(!data)return; // native player lists have no NPC block record
    const auto skipped=[&](std::string_view reason){
        BBSC_TIMELINE("WORLD","NPC AI activation skipped reason={} actor={:#x} handle={:#x} block={} load={}",
            reason,chr,handle,block,bbsc_world_native_load.load());
    };
    const u64 sync=ReadValue<u64>(world,0xA40);
    if(!ReadablePointer(sync,0x110) || block>=ReadValue<u32>(sync,8)){skipped("sync-table");return;}
    const u64 table=ReadValue<u64>(sync,0x10+block*8);
    if(!ReadablePointer(table,0x20) || slot>=ReadValue<u32>(table,0x10)){skipped("sync-slot");return;}
    const u64 list=data+0xB8;
    if(!ReadablePointer(list,0x10) || ReadValue<u64>(table,8)!=list ||
       slot>=ReadValue<u32>(list,0)){skipped("actor-list");return;}
    const u64 entries=ReadValue<u64>(list,8);
    if(!ReadablePointer(entries+slot*0x38,8) || ReadValue<u64>(entries,slot*0x38)!=chr){skipped("actor-binding");return;}
    const u64 map_info=ReadValue<u64>(data,8);
    if(!ReadablePointer(map_info,0xC)){skipped("map-info");return;}
    const u32 map=ReadValue<u32>(map_info,8); // original0190E750's CHR record map
    if(!World::ValidMap(map)){skipped("map-id");return;}
    u32 owner=0;
    World::Scope scope{};
    u64 epoch=0,visit=0;
    u32 local_map=0;
    const char* rejected=nullptr;
    {
        std::scoped_lock lock{bbsc_world_presence_mutex};
        const auto& local=bbsc_world_presence_local;
        if(local.phase!=World::Phase::Playing)rejected="loading"; // load commit covers earlier activations
        else{
            scope=World::BlockScope(World::ScopeOf(local),map);
            const auto* lease=bbsc_independent_owners.Find(scope);
            if(!lease || !lease->owner)rejected="no-owner";
            else{
                owner=lease->owner;
                if(BbscTimelineEnabled()){epoch=lease->epoch;visit=local.visit;local_map=local.map;}
            }
        }
    }
    if(rejected){skipped(rejected);return;}
    const u64 word=BbscWorldOwnershipWord(world,chr);if(!word){skipped("ownership-word");return;}
    const bool personal_doll=map==0x15000000 && chr==BbscWorldDoll(world);
    const u16 before=ReadValue<u16>(word,0);
    // Native grants are per NPC, including a discoverer outside the map owner's
    // streaming range. Do not create/revoke grants at activation completion.
    const bool native=SessionTest::NativeNpcSync();
    const u16 desired=native?before:(personal_doll || owner==BbscMod::RegisterOwnId()?u16{1}:u16{0xFFFF});
    if(before!=desired)WriteValue<u16>(word,0,desired);
    // One record at the existing native completion, including an unchanged
    // assignment. No actor cache, return-time scan, timer or additional hook.
    if(BbscTimelineEnabled()){
        const u16 after=ReadValue<u16>(word,0);
        BBSC_TIMELINE("WORLD","NPC AI activation actor={:#x} handle={:#x} npc_map={:#x} local_map={:#x} scope_map={:#x} world={:08x}/{:016x} ritual={} owner={:08x} epoch={} local_owner={} personal_doll={} before={:#x} desired={:#x} after={:#x} applied={} visit={} load={} native_mode={} native_local={}",
            chr,handle,map,local_map,scope.map,scope.world.host,scope.world.room,scope.ritual,owner,epoch,
            owner==BbscMod::RegisterOwnId(),personal_doll,before,desired,after,after==desired,visit,bbsc_world_native_load.load(),native,after<0x8000);
    }
}

// Map state/checkpoint ownership is independent of per-NPC native grants.
void BbscWorldPublishOwner(u32 owner,u32 role,bool new_visit) {
    const u32 previous_owner=bbsc_independent_owner.exchange(owner);
    const u32 previous_role=bbsc_independent_role.exchange(role);
    if(!SessionTest::NativeNpcSync() || !role ||
       (previous_owner==owner && previous_role==role && !new_visit))return;
    BBSC_TIMELINE("WORLD","map state authority committed owner={:08x} role={} previous={:08x}/{} new_visit={}",
        owner,role,previous_owner,previous_role,new_visit);
}

struct BbscWorldWakeRecord {u64 record;std::array<u32,24> before;};
thread_local std::vector<BbscWorldWakeRecord> bbsc_world_wake_records;
void BbscWorldRestoreWake() {
    for(const auto& saved:bbsc_world_wake_records)if(HasMemoryAccess(saved.record+0x18,0x80,MemoryProt::CpuWrite))
        for(size_t set=0;set<3;++set)for(size_t i=0;i<8;++i)
            WriteValue<u32>(saved.record,(set==0?0x38:set==1?0x18:0x78)+i*4,saved.before[set*8+i]);
    bbsc_world_wake_records.clear();
}
void PS4_SYSV_ABI BbscWorldWakeEnd(u64,const GuestRegisterSnapshot*){
#ifdef BBSC_PERF_NESTED
    BBSC_PERF_NESTED("measure NPC wake end");
#endif
    BbscWorldRestoreWake();EndBbscNpcLifecycleWake();
}
void PS4_SYSV_ABI BbscWorldWakeBegin(u64,const GuestRegisterSnapshot* regs) {
#ifdef BBSC_PERF_NESTED
    BBSC_PERF_NESTED("measure NPC wake begin");
#endif
    BbscWorldRestoreWake();
    BeginBbscNpcLifecycleWake();
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
    if((!bbsc_independent_hooks.load() && !SessionTest::NativeNpcSync()) || !bbsc_independent_travel_hooks.load()) return false;
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

// Only explicit independent-travel recreations bypass the summon-only render
// hold. Native FirstSync clears PlayerIns+1E2 bit4 for phantom types1/2/12;
// a normal summon later releases that hold. A kept-session reunion has already
// finished StageFlow, so no summon tail releases the newly created character.
struct BbscWorldPlayerAdmission {
    World::WorldId world;
    u32 peer;
    u64 local_visit,peer_visit;
    s64 until_ms;
};
std::map<u64,BbscWorldPlayerAdmission> bbsc_world_player_admissions;
u8 bbsc_world_player_render_skip=0;
void ArmBbscWorldPlayerAdmission(u64 task,u32 peer,const World::Presence& local,u64 peer_visit) {
    bbsc_world_player_admissions[task]={local.world,peer,local.visit,peer_visit,SteadyNowMs()+15000};
}
void PS4_SYSV_ABI BbscWorldPlayerRenderAdmission(u64,const GuestRegisterSnapshot* regs) {
    bbsc_world_player_render_skip=0;
    if(!regs || !BbscIndependentActive())return;
    const auto found=bbsc_world_player_admissions.find(regs->rbx);
    if(found==bbsc_world_player_admissions.end())return;
    const auto admission=found->second;
    bbsc_world_player_admissions.erase(found); // one native creation, never a global window
    if(SteadyNowMs()>=admission.until_ms || !ReadablePointer(regs->rbx,0x100) ||
       !ReadablePointer(regs->r15,0x410) || ReadValue<s32>(regs->rbx,0x50)!=4 ||
       (ReadValue<u8>(regs->rbx,0xED)&2))return;
    const s32 mode=ReadValue<s32>(regs->rbx,0xE8);
    const u32 peer=mode==2 && GetSessionState()==6?GetBbscRelayHost():BbscWorldPeer(regs->rbx+0xC8);
    if((mode!=1 && mode!=2) || peer!=admission.peer ||
       (regs->r13!=1 && regs->r13!=2 && regs->r13!=12))return;
    {std::scoped_lock lock{bbsc_world_presence_mutex};
        const auto& local=bbsc_world_presence_local;
        const auto* member=bbsc_world_presence_book.Resident(peer);
        if(local.world!=admission.world || local.visit!=admission.local_visit || !member ||
           member->presence.visit!=admission.peer_visit || !member->presence.alive ||
           !World::SamePlayerSpace(local,member->presence))return;
    }
    // Mid-function trampoline skips ONLY the AND, resuming at01E502CB with
    // R15, native constructor flags, type/animation setup and stack untouched.
    bbsc_world_player_render_skip=1;
    BBSC_TIMELINE("MODEL","native recreation render hold bypassed peer={:08x} actor={:#x} type={} native_draw={}",
        peer,regs->r15,regs->r13,(ReadValue<u8>(regs->r15,0x1E2)&0x10)!=0);
}

// DrawModule+28 is present even before any mesh is attached. For c0000
// PlayerIns, native virtual+B0 (018F4A50) attaches assembled parts to the
// current WorldChrMan+5FC8 scene. FirstSync calls it before async parts finish.
// Check the actual scene links, not DrawModule's always-allocated state.
u64 BbscWorldPlayerMesh(u64 world,u64 chr,bool& detached) {
    detached=false;
    if(!ReadablePointer(world,0x5FD0) || !ReadablePointer(chr,0x4D8))return 0;
    const u64 modules=ReadValue<u64>(chr,0x3B0);
    const u64 model=ReadablePointer(modules,0x28)?ReadValue<u64>(modules,0x20):0;
    // Map-resource characters use another native scene selection path. Leave
    // that path alone; remote player parts use the global player scene.
    if(!ReadablePointer(model,0x30) || ReadValue<u64>(model,0x28))return 0;
    const u64 scene=ReadValue<u64>(world,0x5FC8),parts=ReadValue<u64>(chr,0x4D0);
    if(!ReadablePointer(scene,8) || !ReadablePointer(parts,0xE8))return 0;
    const u64 root=ReadValue<u64>(scene,0);if(!root)return 0;
    bool any=false,mismatch=false;
    for(size_t offset=0x28;offset<0xE8;offset+=8){
        const u64 part=ReadValue<u64>(parts,offset);if(!part)continue;
        if(!ReadablePointer(part,0x20))return 0;
        const u64 node=ReadValue<u64>(part,0x18);
        if(!ReadablePointer(node,0x78))return 0;
        any=true;
        mismatch|=ReadValue<u64>(node,0x70)!=scene || ReadValue<u64>(node,0x18)!=root;
    }
    if(!any)return 0;
    detached=mismatch || ReadValue<u64>(parts,0x10)!=scene;
    return detached?0:parts;
}

bool DetachBbscWorldPlayerMember(u64 chr) {
    const u64 child = ReadValue<u64>(chr, 0x60);
    const u64 table = ReadablePointer(child, 8) ? ReadValue<u64>(child, 0) : 0;
    if (!IsValidMemberId(chr + 0x3D8) || !ReadablePointer(table, 0xD8) ||
        !IsEbootCodeAddress(ReadValue<u64>(table, 0xD0))) {
        return false;
    }

    // Use the native empty MemberId as CSMultiPlayerIns.Delete does for a
    // retained actor. SetMemberId forwards it to the movement receiver too.
    // WorldChrMan.Remove defers destruction, so removal alone leaves the old
    // actor able to consume the new actor's endpoint queue.
    alignas(8) std::array<u8, 0x20> empty_member;
    const u64 member = reinterpret_cast<u64>(empty_member.data());
    using MemberLifetime = void PS4_SYSV_ABI (*)(u64);
    using SetMember = void PS4_SYSV_ABI (*)(u64, u64);
    reinterpret_cast<MemberLifetime>(image_base + 0x00CA1440)(member);
    reinterpret_cast<SetMember>(image_base + 0x018F27C0)(chr, member);
    reinterpret_cast<MemberLifetime>(image_base + 0x00CA1570)(member);
    return true;
}

// Native character presence is paired with native member binding/recreation.
// Reconcile all resident actors, including copies whose insert task is absent.
void TickBbscWorldPlayers() {
    static World::WorldId bound{};
    static std::map<u32,World::PlayerVisualLife> lives;
    static u64 local_bound_visit=0;
    // Native NPC mode needs a single admission per loading/reunion, not a
    // permanent actor/model watchdog. Existing presence changes wake this path;
    // ordinary heartbeats and frames do not inspect actors at all. Waiting for
    // a native task to settle is bounded to the current loading admission.
    const bool once=SessionTest::NativeNpcSync();
    using Visit=std::tuple<u64,u64,u64,bool>;
    static std::map<u32,Visit> completed;
    static u64 observed_revision=0;
    static s64 waiting_until=0;
    const u64 revision=bbsc_world_player_revision.load(std::memory_order_acquire);
    if(once && revision==observed_revision && !waiting_until)return;
    if(once && revision!=observed_revision){observed_revision=revision;waiting_until=SteadyNowMs()+15000;}
    if(once && SteadyNowMs()>=waiting_until){waiting_until=0;return;}
    World::Presence local;std::map<u32,World::Member> members;
    {std::scoped_lock lock{bbsc_world_presence_mutex};local=bbsc_world_presence_local;members=bbsc_world_presence_book.Members();}
    if(!BbscIndependentActive() || bound!=local.world){lives.clear();completed.clear();bound=local.world;local_bound_visit=0;}
    std::erase_if(bbsc_world_player_admissions,[&](const auto& entry){
        const auto& a=entry.second;const auto member=members.find(a.peer);
        return !BbscIndependentActive() || a.world!=local.world || a.local_visit!=local.visit ||
            SteadyNowMs()>=a.until_ms || member==members.end() || member->second.presence.visit!=a.peer_visit;
    });
    if(!BbscIndependentActive())return;
    const u64 global=GetGlobalState(),world=ReadValue<u64>(image_base+CandidateLocalStatePointerOffset,0);
    const bool loading=local.phase!=World::Phase::Playing || !ReadablePointer(global,0x10) ||
        ReadValue<u8>(global,8)!=0 || bbsc_world_load_pending.load() || bbsc_reload_finish_pending.load() || BbscCurtainActive();
    if(loading)return; // old character storage may already belong to another load
    const auto tasks=GetMultiPlayerInsTasks();const auto players=BbscWorldPlayers(world);
    std::set<u32> waiting;
    if(once)for(const auto& [peer,member]:members){
        const Visit visit{local.visit,member.presence.visit,bbsc_world_native_load.load(),World::SamePlayerSpace(local,member.presence)};
        const auto done=completed.find(peer);
        if(done==completed.end() || done->second!=visit)waiting.insert(peer);
    }
    for(const u64 chr:players){
        if(!chr || chr==GetLocalPlayerCharacter() || !ReadablePointer(chr,0x410))continue;
        const u32 peer=BbscWorldPeer(chr+0x3D8);if(!peer)continue;
        const auto it=members.find(peer);
        const bool here=it!=members.end() && World::SamePlayerSpace(local,it->second.presence);
        const u64 activation=ReadValue<u64>(chr,0x18);
        if(!here && ReadablePointer(activation,0x21) && !(ReadValue<u8>(activation,0x20)&1)){
            using Disable=void PS4_SYSV_ABI (*)(u64,u8);
            reinterpret_cast<Disable>(image_base+0x018C6390)(chr,1);
            BBSC_TIMELINE("MODEL","native absent peer hidden peer={:08x} actor={:#x}",peer,chr);
        }
    }
    if(local_bound_visit!=local.visit){
        if(!RepairBbscLocalMemberBinding(GetSessionState(),tasks,true))return;
        local_bound_visit=local.visit;
    }
    for(const u64 task:tasks){
        const s32 mode=ReadValue<s32>(task,0xE8);if(mode!=1 && mode!=2)continue;
        const u32 peer=mode==2 && GetSessionState()==6?GetBbscRelayHost():BbscWorldPeer(task+0xC8);
        if(!peer)continue;
        const auto it=members.find(peer);
        const bool fresh=it!=members.end(); // native residency survives movie silence
        World::PlayerVisualInput in;in.loading=false;in.local_visit=local.visit;
        in.local_map=local.map;in.local_load=bbsc_world_native_load.load();
        in.peer_visit=fresh?it->second.presence.visit:0;
        in.peer_map=fresh?it->second.presence.map:0;
        in.here=fresh && World::SamePlayerSpace(local,it->second.presence);
        in.alive=fresh && it->second.presence.alive;
        in.task_ready=ReadValue<s32>(task,0x50)==6 && ReadValue<s32>(task,0x54)==6 && !(ReadValue<u8>(task,0xED)&2);
        const Visit visit{local.visit,in.peer_visit,in.local_load,in.here};
        if(once && !waiting.contains(peer))continue;
        if(once && in.here && !in.task_ready)continue;
        const auto previous=completed.find(peer);
        in.admitted_load=once && previous!=completed.end() &&
            std::get<2>(previous->second)==in.local_load && std::get<3>(previous->second);
        if(once){completed[peer]=visit;waiting.erase(peer);}
        u64 chr=0;for(const auto candidate:BbscWorldPlayers(world))
            if(candidate && candidate!=GetLocalPlayerCharacter() && BbscWorldPeer(candidate+0x3D8)==peer){chr=candidate;break;}
        bool detached=false;
        u64 mesh=BbscWorldPlayerMesh(world,chr,detached);
        in.actor=chr;in.actor_alive=chr && GetCharacterHp(chr)>0;
        const u64 death_control=ReadablePointer(chr,0x60)?ReadValue<u64>(chr,0x58):0;
        in.actor_dead=ReadablePointer(death_control,0x116) && (ReadValue<u16>(death_control,0x114)&1);
        const u64 activation=ReadablePointer(chr,0x20)?ReadValue<u64>(chr,0x18):0;
        in.actor_ready=ReadablePointer(activation,0x18) && ReadValue<s32>(activation,0x10)==4 && ReadValue<s32>(activation,0x14)==4;
        in.disabled=ReadablePointer(activation,0x21) && (ReadValue<u8>(activation,0x20)&1);
        if(detached && in.here && in.alive && in.actor_alive && in.actor_ready && in.task_ready){
            using Attach=void PS4_SYSV_ABI (*)(u64);
            reinterpret_cast<Attach>(image_base+0x018F4A50)(chr);
            mesh=BbscWorldPlayerMesh(world,chr,detached);
            BBSC_TIMELINE("MODEL","native peer scene attachment peer={:08x} actor={:#x} attached={}",peer,chr,mesh!=0);
        }
        in.model=mesh;
        const auto action=lives[peer].Observe(in,SteadyNowMs());
        if(action.kept_border)
            BBSC_TIMELINE("MODEL","native peer kept across map border peer={:08x} actor={:#x} local_map={:#x} peer_map={:#x} local_visit={} peer_visit={} load={}",
                peer,chr,local.map,in.peer_map,local.visit,in.peer_visit,in.local_load);
        if(action.hide || action.enable){
            // Native character presence hides the model, name and collision
            // together. A render-node byte alone leaves a named phantom behind.
            using Disable=void PS4_SYSV_ABI (*)(u64,u8);
            reinterpret_cast<Disable>(image_base+0x018C6390)(chr,action.hide?1:0);
            BBSC_TIMELINE("MODEL","native peer {} peer={:08x} local_map={:#x} peer_map={:#x}",
                action.hide?"hidden":"enabled",peer,local.map,fresh?it->second.presence.map:0);
        }
        if(action.rebind && ReadablePointer(chr,0x410) && IsValidMemberId(task+0xC8)){
            const u64 child=ReadValue<u64>(chr,0x60),vt=ReadablePointer(child,8)?ReadValue<u64>(child,0):0;
            if(ReadablePointer(vt,0xD8) && IsEbootCodeAddress(ReadValue<u64>(vt,0xD0))){
                using SetMember=void PS4_SYSV_ABI (*)(u64,u64);
                reinterpret_cast<SetMember>(image_base+0x018F27C0)(chr,task+0xC8);
                bbsc_world_player_admissions.erase(task);
                BBSC_TIMELINE("MODEL","resident peer bound peer={:08x} actor={:#x} mesh={:#x} draw_admitted={} local_visit={} peer_visit={}",
                    peer,chr,mesh,(ReadValue<u8>(chr,0x1E2)&0x10)!=0,local.visit,in.peer_visit);
            }
        }
        // A settled native task can reach its first visit admission without
        // a PlayerIns. The one-shot path will not revisit WaitingActor.
        const bool missing_on_admission = once && in.here && in.alive && !chr;
        if(action.insert || missing_on_admission){
            if(HasMemoryAccess(task+0xED,1,MemoryProt::CpuWrite) &&
               ReadablePointer(world,0x68) && IsValidMemberId(task+0xC8) &&
               ReadValue<u64>(task,0xC8)){
                const u64 retiring = FindBbscRemotePlayer(world, task);
                // The relay may temporarily lack a registration for an actor
                // that still owns this native member's movement queue.
                if ((chr && chr != retiring) || (!action.insert && retiring)) continue;
                // Same per-character removal used by native CSMultiPlayerIns.Delete
                // at01E50C54. Keep the session/member task; never run bulk cleanup.
                if(retiring){
                    const u64 arrivals=ReadablePointer(global,0x1700)?ReadValue<u64>(global,0x16F8):0;
                    if(!ReadablePointer(arrivals,0x18) || !DetachBbscWorldPlayerMember(retiring))continue;
                    // Native Delete clears the per-handle arrival before freeing
                    // PlayerIns (01E50C19 -> 01E50C54). Handles are reused.
                    using ClearArrival=void PS4_SYSV_ABI (*)(u64,u32);
                    reinterpret_cast<ClearArrival>(image_base+0x015BC080)(arrivals,ReadValue<u32>(retiring,8));
                    using Remove=void PS4_SYSV_ABI (*)(u64,u64);
                    reinterpret_cast<Remove>(image_base+0x019186E0)(world,retiring);
                }
                ArmBbscWorldPlayerAdmission(task,peer,local,in.peer_visit);
                WriteValue<u8>(task,0xED,ReadValue<u8>(task,0xED)|1);MarkBbscRecreatedMember(task);
                using Set=void PS4_SYSV_ABI (*)(u64,s32);reinterpret_cast<Set>(image_base+MultiPlayerInsSetStateOffset)(task,4);
                BBSC_TIMELINE("MODEL","native peer recreation requested peer={:08x} previous_actor={:#x} local_visit={} peer_visit={}",peer,retiring,local.visit,in.peer_visit);
            }
            continue; // native removal invalidated this actor and its render graph
        }

    }
    // Native tasks may disappear briefly around StageFlow while the room member
    // survives. Keep its previous visit so a returning task cannot bypass the
    // meeting admission as if it were a brand-new session member.
    std::erase_if(lives,[&](const auto& entry){return !members.contains(entry.first);});
    std::erase_if(completed,[&](const auto& entry){return !members.contains(entry.first);});
    if(once && waiting.empty())waiting_until=0;
}

// Travel/catalog/ordered world updates follow below. All hook readiness is
// published together after every expected byte has been checked.
void TickBbscWorldTravel();
void TickBbscWorldSnapshots();
void TickBbscWorldAltars();
void InstallBbscWorldTravel();
#include "core/bbsc_world_state.inc"
#include "core/bbsc_world_native_initial.inc"
#include "core/bbsc_world_blocks.inc"
#include "core/bbsc_combat_trace.inc"
#include "core/bbsc_world_travel.inc"
#include "core/bbsc_world_checkpoint.inc"
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
    if(!active && World::Valid(current_world)) {
        const u32 count=GetBbscSessionMemberCount(GetGlobalState());
        size_t heard=0;{std::scoped_lock lock{bbsc_world_presence_mutex};heard=bbsc_world_presence_book.Members().size();}
        static std::tuple<World::WorldId,u32,size_t,bool,bool> previous{};
        const auto status=std::make_tuple(current_world,count,heard,bbsc_independent_hooks.load(),bbsc_independent_travel_hooks.load());
        if(status!=previous){previous=status;
            BBSC_TIMELINE("WORLD","independent negotiation: native_members={} presence_peers={} enemy_hooks={} travel_hooks={}",
                count,heard,bbsc_independent_hooks.load(),bbsc_independent_travel_hooks.load());}
    }
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
    bool new_visit=false;
    if(active){
        u64 visit=0;{std::scoped_lock lock{bbsc_world_presence_mutex};visit=bbsc_world_presence_local.visit;}
        new_visit=previous_visit!=visit;
        if(previous_visit && new_visit) DiscardBbscWorldScenes();
        previous_visit=visit;
    }else previous_visit=0;
    BbscWorldPublishOwner(owner,role,new_visit);
    TickBbscWorldAltars();TickBbscWorldSnapshots();
    if(!SessionTest::NativeNpcSync())TickBbscWorldBlocks();
    TickBbscWorldLamps();TickBbscWorldTravel();TickBbscSharedLampCheckpoint();
    if(active) TickBbscWorldPlayers();
    if(!SessionTest::NativeNpcSync())TickBbscCombatTrace();
}

void InstallBbscIndependentWorld() {
    if(SessionTest::NativeNpcSync()){
        // Independent lamp travel retains the room after StageFlow. Its player
        // recreation/render admission is still required with native NPC sync.
        // Keep the player path and one NPC activation-completion boundary;
        // never restore the per-frame ownership/wake hooks.
        static constexpr std::array<u8,8> RenderHold{0x41,0x80,0xA7,0xE2,0x01,0x00,0x00,0xEF};
        static constexpr std::array<u8,6> PlayerPrologue{0x55,0x48,0x89,0xE5,0x41,0x57};
        static constexpr std::array<u8,7> NpcActivated{0xC7,0x40,0x10,0x04,0x00,0x00,0x00};
        struct AiRewrite {u64 offset;std::span<const u8> bytes;Core::GuestCodeEmitter emit;u64 data=0;};
        const std::array authority{
            AiRewrite{0x01789274,NativeAi::ReceiveChannels,NativeAi::EmitReceiveChannels},
            AiRewrite{0x01916A82,NativeAi::Request,NativeAi::EmitRequest},
            AiRewrite{0x018F0880,NativeAi::EmptySelf,NativeAi::EmitEmptySelf},
            AiRewrite{0x018F09D1,NativeAi::EmptyPeer,NativeAi::EmitEmptyPeer},
            AiRewrite{0x018F092C,NativeAi::RequestMember,NativeAi::EmitRequestMember,reinterpret_cast<u64>(BbscWorldNpcRequestMember)},
            AiRewrite{0x018ED1B6,NativeAi::RetainMember,NativeAi::EmitRetainMember,reinterpret_cast<u64>(BbscWorldNpcRetainMember)},
            AiRewrite{0x018ED470,NativeAi::GrantMember,NativeAi::EmitGrantMember,reinterpret_cast<u64>(BbscWorldNpcGrantMember)}};
        for(const auto& site:authority)
            if(!ReadablePointer(image_base+site.offset,site.bytes.size()) ||
               std::memcmp(reinterpret_cast<void*>(image_base+site.offset),site.bytes.data(),site.bytes.size())){
                LOG_ERROR(Debug,"BBSC native NPC authority: request site {:#x} differs",site.offset);return;
            }
        if(!ReadablePointer(image_base+0x018BD488,NpcActivated.size()) ||
           std::memcmp(reinterpret_cast<void*>(image_base+0x018BD488),NpcActivated.data(),NpcActivated.size())){
            LOG_ERROR(Debug,"BBSC native NPC activation: completion site differs; travel remains inactive");return;
        }
        if(!ReadablePointer(image_base+0x01E502C3,RenderHold.size()) ||
           std::memcmp(reinterpret_cast<void*>(image_base+0x01E502C3),RenderHold.data(),RenderHold.size())){
            LOG_ERROR(Debug,"BBSC native player admission: render site differs; travel remains inactive");return;
        }
        for(u64 offset:{0x018C6390ull,0x019186E0ull,0x018F4A50ull,0x015BC080ull,
                        0x017894E0ull,0x01786360ull,0x0190E8B0ull})
            if(!ReadablePointer(image_base+offset,PlayerPrologue.size()) ||
               std::memcmp(reinterpret_cast<void*>(image_base+offset),PlayerPrologue.data(),PlayerPrologue.size())){
                LOG_ERROR(Debug,"BBSC native player admission: callable {:#x} differs; travel remains inactive",offset);return;
            }
        if(!InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x01E502C3),RenderHold,0,
            BbscWorldPlayerRenderAdmission,&bbsc_world_player_render_skip,true)){
            LOG_ERROR(Debug,"BBSC native player admission: could not install render hook; travel remains inactive");return;
        }
        if(!InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x017894E0),PlayerPrologue,0,
            BbscWorldPacketSend,&bbsc_independent_send_skip)){
            LOG_ERROR(Debug,"BBSC native initial state: could not install serializer capture; travel remains inactive");return;
        }
        if(!InstallGuestCodeHook(reinterpret_cast<void*>(image_base+0x018BD488),NpcActivated,0,
            BbscWorldNpcActivated)){
            LOG_ERROR(Debug,"BBSC native NPC activation: could not install completion hook; travel remains inactive");return;
        }
        for(const auto& site:authority)
            if(!Core::InstallGuestCodeRewrite(reinterpret_cast<void*>(image_base+site.offset),site.bytes,
                site.emit,image_base,site.data)){
                LOG_ERROR(Debug,"BBSC native NPC authority: could not install request site {:#x}",site.offset);return;
            }
        BBSC_TIMELINE("START","NPC native authority ready: active discoverer retains native grant; empty requests release it; no additional passes or channels");
        BBSC_TIMELINE("START","NPC native member admission ready: request/retain/grant use current room membership without PlayerIns");
        BBSC_TIMELINE("START","NPC native transport admission ready: request/grant channels16/17 receive without remote PlayerIns; native endpoint identity retained");
        BBSC_TIMELINE("START","NPC AI native admission retained: original controller/position grant; no map-owner override");
        BBSC_TIMELINE("START","NPC AI activation diagnostics ready: read-only native grant, map-state owner and epoch");
        // No role, HP, ownership-update or wake hooks. Map commits never
        // overwrite per-NPC grants. Both AI and movement read the original grant.
        // Only a load's explicit native
        // serializer call is captured; ordinary packet processing stays native.
        InstallBbscWorldTravel();
        LOG_WARNING(Debug,"BBSC native NPC sync: v1.2 simulation; one-shot resident state at load; AI authority per native NPC grant; activation observer is read-only; block/HP/ownership-update/wake hooks OFF; lamp travel and player reunion admission retained");
        return;
    }
    // Whole instruction spans from CUSA03173 1.09, matched before any mutation.
    struct Site {u64 offset;std::vector<u8> bytes;GuestCodeHook hook;const u8* skip;bool resume=false;u64 continuation=0;u64 tag=0;bool diagnostic=false;};
    const std::array sites{
        Site{0x017894E0,{0x55,0x48,0x89,0xE5,0x41,0x57},BbscWorldPacketSend,&bbsc_independent_send_skip},
        Site{0x01E502C3,{0x41,0x80,0xA7,0xE2,0x01,0x00,0x00,0xEF},BbscWorldPlayerRenderAdmission,&bbsc_world_player_render_skip,true},
        Site{0x018EF26C,{0x48,0x8B,0x9D,0x08,0xFF,0xFF,0xFF},BbscWorldHpRound,nullptr},
        Site{0x018EF578,{0x8B,0x87,0x24,0x01,0x00,0x00},BbscWorldHpState,nullptr},
        Site{0x018EF587,{0x80,0xBB,0x64,0x06,0x00,0x00,0x00},BbscWorldHpRestore,nullptr},
        Site{0x018EF684,{0x49,0x89,0xDC,0x48,0x85,0xFF},BbscWorldHpRestore,nullptr},
        Site{0x018EF759,{0x48,0xC1,0xE8,0x03,0x85,0xC0},BbscWorldBlockHpReceived,nullptr},
        Site{0x018EF108,{0x48,0x63,0xF0,0x48,0x89,0xF1},BbscWorldBlockAnimationReceived,nullptr},
        Site{0x018EFD12,{0x48,0x63,0xC8,0x48,0x89,0xC8},BbscWorldBlockStatusReceived,nullptr},
        Site{0x018EF94F,{0x48,0x8B,0x38,0x48,0x85,0xFF},BbscWorldHpReceiveAfterSend,&bbsc_world_hp_receive_skip,false,0x018EF6C6},
        Site{0x01789495,{0x48,0x81,0xC3,0xD0,0x00,0x00,0x00},BbscWorldHpSource,nullptr},
        Site{0x01916D91,{0x8B,0x88,0x24,0x01,0x00,0x00},BbscWorldHpApplyBegin,&bbsc_world_hp_apply_enter,false,0x01916DB4},
        Site{0x01916ED5,{0x0F,0xB7,0x30,0x81,0xFE,0x87,0xF9,0x00,0x00},BbscWorldHpApplyTarget,&bbsc_world_hp_apply_skip,false,0x01916F70},
        Site{0x01916EF5,{0x89,0x85,0xC0,0xFE,0xFF,0xFF},BbscWorldHpApplyLethal,nullptr},
        Site{0x01A2A102,{0x8B,0x88,0x24,0x01,0x00,0x00},BbscWorldHitState,nullptr},
        Site{0x018BCD40,{0x55,0x48,0x89,0xE5,0x41,0x57},BbscCombatNativeHook,nullptr,false,0,0,true},
        Site{0x018BD9D0,{0x55,0x48,0x89,0xE5,0x53,0x50},BbscCombatNativeHook,nullptr,false,0,1,true},
        Site{0x019165C1,{0x49,0x8B,0x86,0xB0,0x03,0x00,0x00},BbscCombatNativeHook,nullptr,false,0,2,true},
        Site{0x019173B0,{0x55,0x48,0x89,0xE5,0x41,0x57},BbscWorldOwnership,nullptr},
        Site{0x019192A0,{0x55,0x48,0x89,0xE5,0x41,0x57},BbscWorldWakeBegin,nullptr},
        Site{0x0191987E,{0x8A,0x5D,0x97,0x80,0xE3,0x01},BbscWorldWakeEnd,nullptr}};
    for(const auto& site:sites) if((!site.diagnostic || BbscCombatTraceEnabled()) &&
       (!ReadablePointer(image_base+site.offset,site.bytes.size()) ||
        std::memcmp(reinterpret_cast<const void*>(image_base+site.offset),site.bytes.data(),site.bytes.size()))) {
        LOG_ERROR(Debug,"BBSC independent world: native site {:#x} differs; feature remains inactive",site.offset);return;
    }
    static constexpr std::array<u8,6> GetterPrologue{0x55,0x48,0x89,0xE5,0x41,0x57};
    static constexpr std::array<u8,8> HpApplyEntry{0x41,0x8B,0x84,0x24,0x78,0x02,0x00,0x00};
    static constexpr std::array<u8,6> HpApplyNext{0x41,0xFF,0xC4,0x45,0x39,0xE0};
    static constexpr std::array<u8,9> HpLethalEdge{0x83,0xBD,0xC0,0xFE,0xFF,0xFF,0x00,0x7E,0x2F};
    static constexpr std::array<u8,5> HpNativeDeathCall{0xE8,0x40,0x8A,0xFA,0xFF};
    if(!ReadablePointer(image_base+0x01916DB4,HpApplyEntry.size()) ||
       !ReadablePointer(image_base+0x01916F70,HpApplyNext.size()) ||
       !ReadablePointer(image_base+0x01916F38,HpLethalEdge.size()) ||
       !ReadablePointer(image_base+0x01916F5B,HpNativeDeathCall.size()) ||
       std::memcmp(reinterpret_cast<void*>(image_base+0x01916DB4),HpApplyEntry.data(),HpApplyEntry.size()) ||
       std::memcmp(reinterpret_cast<void*>(image_base+0x01916F70),HpApplyNext.data(),HpApplyNext.size()) ||
       std::memcmp(reinterpret_cast<void*>(image_base+0x01916F38),HpLethalEdge.data(),HpLethalEdge.size()) ||
       std::memcmp(reinterpret_cast<void*>(image_base+0x01916F5B),HpNativeDeathCall.data(),HpNativeDeathCall.size())){
        LOG_ERROR(Debug,"BBSC independent world: native HP application continuations differ");return;
    }
    static constexpr std::array<u8,16> HpReceiveContinuation{
        0x4D,0x8D,0xBC,0x24,0x28,0x07,0x00,0x00, // lea r15,[r12+728]
        0x4D,0x8D,0xAC,0x24,0x2C,0x07,0x00,0x00}; // lea r13,[r12+72c]
    if(!ReadablePointer(image_base+0x018EF6C6,HpReceiveContinuation.size()) ||
       std::memcmp(reinterpret_cast<void*>(image_base+0x018EF6C6),HpReceiveContinuation.data(),HpReceiveContinuation.size())){
        LOG_ERROR(Debug,"BBSC independent world: native HP receive continuation differs");return;
    }
    for(u64 offset:{0x01AB2A40ull,0x01AB1DB0ull,0x01AB3070ull,0x01AB31C0ull,
                    0x018C6390ull,0x019186E0ull,0x018F4A50ull,0x015BC080ull,0x012B2960ull,
                    0x01786360ull,0x01789200ull,0x0190E8B0ull,0x0190E750ull})
        if(!ReadablePointer(image_base+offset,GetterPrologue.size()) ||
           std::memcmp(reinterpret_cast<const void*>(image_base+offset),GetterPrologue.data(),GetterPrologue.size())){
            LOG_ERROR(Debug,"BBSC independent world: native callable {:#x} differs",offset);return;
        }
    const s32 host=3,guest=6;
    std::memcpy(bbsc_world_host_state.data()+0x124,&host,4);
    std::memcpy(bbsc_world_guest_state.data()+0x124,&guest,4);
    for(const auto& site:sites) if((!site.diagnostic || BbscCombatTraceEnabled()) &&
       !InstallGuestCodeHook(reinterpret_cast<void*>(image_base+site.offset),site.bytes,site.tag,site.hook,site.skip,site.resume,
        site.continuation?reinterpret_cast<void*>(image_base+site.continuation):nullptr)) {
        LOG_ERROR(Debug,"BBSC independent world: could not install site {:#x}; feature remains inactive",site.offset);return;
    }
    bbsc_independent_hooks=true;
    InstallBbscWorldTravel();
    LOG_INFO(Debug,"BBSC independent world: native enemy authority hooks installed");
    BBSC_TIMELINE("START","independent hooks: enemies={} travel={}",bbsc_independent_hooks.load(),bbsc_independent_travel_hooks.load());
}
#else
void QueueBbscSharedLampCheckpoint(s32){}
void NoteBbscNativeLampSelection(){}
bool ReadBbscSharedLampCheckpoint(s32&,bool&){return false;}
bool RequestBbscSharedLampReload(){return false;}
bool BbscIndependentActive(){return false;}
bool BbscIndependentTravelAllowed(){return false;}
bool BbscWorldTalkAllowed(u32){return false;}
void NoteBbscWorldTalkRecord(u64,u64){}
bool QueueBbscWorldTravel(u32,u8){return false;}
bool BbscWorldTaskHere(u64){return true;}
u32 BbscWorldLivingHere(){return 0;}
u32 BbscWorldParticipantsHere(){return 0;}
bool BbscWorldPeerHere(u32){return true;}
bool BbscLectureExitRecipient(u64){return false;}
bool BbscWorldActorHere(u64){return true;}
u32 BbscIndependentCapabilities(){return World::PresenceCapability;}
u64 BbscIndependentRitual(const Chalice::Key&){return 0;}
Chalice::Key BbscIndependentDungeonKey(const Chalice::Key& key){return key;}
bool BbscWorldMountFor(u32,Chalice::Mount&){return false;}
bool BbscWorldHasSnapshot(u32){return false;}
void ApplyBbscIndependentAtLoad(u32){}
bool BbscWorldProtectAltar(u32,u32){return false;}
bool BbscWorldTravelInFlight(){return false;}
bool GuardBbscWorldBootstrap(u64){return false;}
void EnableBbscNativeTravelEvent(u64){}
void BbscWorldNativeWarpBegin(const GuestRegisterSnapshot*){}
bool BbscWorldTravelFlag(u32 flag){
    return LampTravel::IsTravelCommand(flag);
}
void QueueBbscWorldAltarWrite(u32,u32,u32){}
void TickBbscIndependentWorld(){}
void InstallBbscIndependentWorld(){}
void ProcessBbscWorldControl(u32,const World::Control&,std::span<const u8>){}
void BbscWorldCoordinate(){}
#endif
