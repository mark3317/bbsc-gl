// A successful native guest fog traversal writes only its local entered flag.
// Publish that ACT, not a snapshot bit: old packets must not start a new life.
struct BbscBossEntrance {
    s64 event = 0;
    u32 slot = 0, entered = 0, start = 0, victory = 0;
    bool operator==(const BbscBossEntrance&) const = default;
};
static_assert(sizeof(BbscBossEntrance) == 24);
struct BbscGuestStartedBoss {
    World::Scope scope{};
    u64 load = 0;
    std::vector<u32> flags;
};
BbscGuestStartedBoss bbsc_guest_started_boss;

bool BbscBossEntranceReady() {
    const s32 role = GetSessionState();
    const u64 global = GetGlobalState();
    return (role == 3 || role == 6) && !IsInvaderType(GetLocalPlayerType()) &&
           ReadablePointer(global, 0x10) && ReadValue<u8>(global, 8) == 0 &&
           !bbsc_world_load_pending.load() && !bbsc_reload_finish_pending.load() &&
           !BbscQuitInProgress() && !BbscReturningToTitle() && BbscWorldSceneReady();
}

BbscBossEntrance ResolveBbscBossEntrance(s64 event, u32 slot, u32 entered,
                                        const World::Scope& scope) {
    const auto* gate = GuestAccess::FindGuestFogGate(event);
    if (!gate || !entered || slot > 7) return {};
    if (Chalice::IsMap(scope.map)) {
        std::scoped_lock lock{bbsc_world_presence_mutex};
        const auto& cup = bbsc_chalice_boss_attempts;
        if (gate->battle_flag || !BbscChaliceBossLayoutMatchesScope(scope, cup.layout)) return {};
        const auto found = std::ranges::find_if(cup.constructors, [&](const auto& init) {
            return !init.actor && init.flags[1] == entered && init.flags[2] == event + slot;
        });
        if (found == cup.constructors.end() || !found->victory || !found->flags[0]) return {};
        return {event, slot, entered, found->flags[0], found->victory};
    }
    if (!gate->battle_flag || entered != gate->battle_flag + 1) return {};
    for (const auto& arena : BossRetry::StoryArenas) {
        if (arena.map == scope.map && gate->battle_flag >= arena.first && gate->battle_flag <= arena.last)
            return {event, slot, entered, gate->battle_flag, arena.defeated};
    }
    return {};
}

bool BbscGuestStartedFlag(u32 flag) {
    const auto& started = bbsc_guest_started_boss;
    if (!started.load || started.load != bbsc_world_native_load.load()) return false;
    std::scoped_lock lock{bbsc_world_presence_mutex};
    return started.scope == World::ScopeOf(bbsc_world_presence_local) &&
           std::ranges::find(started.flags, flag) != started.flags.end();
}

void KeepBbscGuestStartedFlags(u32 key, const u8* before, u8* live) {
    const auto& started = bbsc_guest_started_boss;
    if (!started.load || started.load != bbsc_world_native_load.load()) return;
    std::scoped_lock lock{bbsc_world_presence_mutex};
    if (started.scope != World::ScopeOf(bbsc_world_presence_local)) return;
    for (const u32 flag : started.flags) {
        if (flag / 1000 != key) continue;
        const u32 bit = flag % 1000;
        const u8 mask = 0x80u >> (bit % 8);
        live[bit / 8] = (live[bit / 8] & ~mask) | (before[bit / 8] & mask);
    }
}

bool ApplyBbscBossEntrance(const World::Scope& scope, const BbscBossEntrance& entry, bool own) {
    if (!entry.start || BbscEventFlag(entry.victory)) return false;
    const u64 manager = ReadValue<u64>(image_base + EventFlagManPointerOffset, 0);
    if (!ReadablePointer(manager, 0x40)) return false;
    auto& started = bbsc_guest_started_boss;
    const u64 load = bbsc_world_native_load.load();
    if (started.load != load || started.scope != scope) started = {scope, load, {}};
    if (std::ranges::find(started.flags, own ? entry.entered : entry.start) != started.flags.end()) return false;
    if (std::ranges::find(started.flags, entry.start) == started.flags.end()) started.flags.push_back(entry.start);
    if (own && std::ranges::find(started.flags, entry.entered) == started.flags.end()) started.flags.push_back(entry.entered);
    using SetFlag = void PS4_SYSV_ABI (*)(u64, u32, u32);
    reinterpret_cast<SetFlag>(image_base + 0x013CFCC0)(manager, entry.start, 1);
    BBSC_TIMELINE("FOG", "guest entrance starts native boss event={} flag={} ritual={} load={} local={}",
                  entry.event, entry.start, scope.ritual, load, own);
    return true;
}

void NoteBbscGuestBossEntrance(u64 instance) {
    if (!BbscIndependentActive() || GetSessionState() != 6 || GetLocalPlayerType() != 1 ||
        !ReadablePointer(instance, 0xC0) || GetCharacterHp(GetLocalPlayerCharacter()) <= 0) return;
    const auto* gate = GuestAccess::FindGuestFogGate(BbscEventIdOf(instance));
    if (!gate) return;
    const u64 pc = ReadValue<u64>(instance, 0xB0);
    if (!ReadablePointer(pc, 0x20) || ReadValue<s32>(pc, 0) != 2003 ||
        ReadValue<s32>(pc, 4) != 2 || ReadValue<u64>(pc, 8) != 8) return;
    u64 args = ReadValue<u64>(instance, 0xB8);
    if (!args) {
        const u64 ref = ReadValue<u64>(instance, 0xA8);
        const u64 file = ReadablePointer(ref, 0x10) ? ReadValue<u64>(ref, 8) : 0;
        if (!ReadablePointer(file, 0x80)) return;
        args = file + ReadValue<u64>(file, 0x78) + ReadValue<u64>(pc, 0x10);
    }
    if (!ReadablePointer(args, 8) || ReadValue<u32>(args, 4) != 1) return;
    World::Presence local;
    std::vector<std::pair<u32, u64>> recipients;
    {
        std::scoped_lock lock{bbsc_world_presence_mutex};
        local = bbsc_world_presence_local;
        for (const auto& [peer, member] : bbsc_world_presence_book.Members())
            if (member.presence.phase == World::Phase::Playing &&
                World::ScopeOf(member.presence) == World::ScopeOf(local))
                recipients.emplace_back(peer, member.presence.visit);
    }
    if (local.phase != World::Phase::Playing || !BbscBossEntranceReady()) return;
    const auto scope = World::ScopeOf(local);
    const auto entry = ResolveBbscBossEntrance(gate->event, ReadValue<u16>(instance, 0x2C),
                                              ReadValue<u32>(args, 0), scope);
    if (!entry.start) {
        BBSC_TIMELINE("FOG", "guest passage completed without a boss match event={} slot={} entered={} ritual={}",
                      gate->event, ReadValue<u16>(instance, 0x2C), ReadValue<u32>(args, 0), scope.ritual);
        return;
    }
    if (!ApplyBbscBossEntrance(scope, entry, true)) return;
    // One event per resident (max four), over the existing reliable transport.
    // No retries. Sender and recipient visits fence a delayed act after a wipe.
    for (const auto& [peer, visit] : recipients) {
        World::Control c; c.kind = World::ControlKind::BossEntrance; c.scope = scope;
        c.owner = peer; c.sequence = local.visit; c.epoch = visit;
        BbscWorldSend(c, {reinterpret_cast<const u8*>(&entry), sizeof(entry)});
    }
}

void BbscWorldReceiveBossEntrance(const BbscWorldIncoming& message) {
    const auto& c = message.control;
    if (!BbscIndependentActive() || c.parts != 1 || c.part ||
        message.payload.size() != sizeof(BbscBossEntrance) || c.owner != BbscMod::RegisterOwnId() ||
        !BbscBossEntranceReady()) return;
    {
        std::scoped_lock lock{bbsc_world_presence_mutex};
        const auto& local = bbsc_world_presence_local;
        const auto* peer = bbsc_world_presence_book.Resident(message.sender);
        if (!peer || local.phase != World::Phase::Playing || local.visit != c.epoch ||
            peer->presence.phase != World::Phase::Playing || peer->presence.visit != c.sequence ||
            World::ScopeOf(local) != c.scope || World::ScopeOf(peer->presence) != c.scope) return;
    }
    BbscBossEntrance entry; std::memcpy(&entry, message.payload.data(), sizeof(entry));
    if (entry != ResolveBbscBossEntrance(entry.event, entry.slot, entry.entered, c.scope)) return;
    ApplyBbscBossEntrance(c.scope, entry, false);
}
