// SPDX-License-Identifier: GPL-2.0-or-later
// Opt-in, read-only combat timing. No diagnostic observation affects simulation.
bool BbscCombatTraceEnabled() {
    static const bool requested=EnvFlagEnabled("SHADPS4_BBSC_COMBAT_TRACE");
    return requested && BbscTimelineEnabled();
}
struct BbscCombatFence {
    World::WorldId world{};u64 visit=0,load=0;u32 map=0;s32 session=0;
    bool operator==(const BbscCombatFence&)const=default;
};
struct BbscCombatSample {
    u64 actor=0;u32 owner=0;s32 hp=-1,action=-1,current=-1,requested=-1;
    u8 death=0,proxy=0;u16 ownership=0xffff;
    bool operator==(const BbscCombatSample&)const=default;
};
struct BbscCombatWatch {s64 until=0;bool sampled=false,hp_seen=false;s32 hp_request=0;BbscCombatSample last;};
std::recursive_mutex bbsc_combat_mutex;
BbscCombatFence bbsc_combat_fence;
std::map<u32,BbscCombatWatch> bbsc_combat_watches;
size_t bbsc_combat_lines=0;
size_t bbsc_combat_packet_lines=0;
bool BbscCombatContext() {
    BbscCombatFence next;
    {std::scoped_lock lock{bbsc_world_presence_mutex};
        next.world=bbsc_world_presence_local.world;next.visit=bbsc_world_presence_local.visit;}
    next.load=bbsc_world_native_load.load();next.map=GetCurrentPackedMap();next.session=GetSessionState();
    const bool live=BbscCombatTraceEnabled() && BbscIndependentActive() &&
        (next.session==3 || next.session==6) && !bbsc_world_load_pending.load() &&
        !bbsc_reload_finish_pending.load();
    if(!live || next!=bbsc_combat_fence){
        bbsc_combat_fence=next;bbsc_combat_watches.clear();bbsc_combat_lines=0;bbsc_combat_packet_lines=0;
    }
    const s64 now=SteadyNowMs();
    for(auto it=bbsc_combat_watches.begin();it!=bbsc_combat_watches.end();)
        if(now>it->second.until)it=bbsc_combat_watches.erase(it);else ++it;
    return live && bbsc_combat_lines<512;
}
// Native handle -> CHR record -> slot. Resolve anew for EVERY observation;
// never follow a retained actor pointer after unload/recreation.
u64 BbscCombatActor(u32 handle) {
    if(static_cast<s32>(handle)<0)return 0;
    const u64 world=ReadValue<u64>(image_base+CandidateLocalStatePointerOffset,0);
    if(!ReadablePointer(world,0xA48))return 0;
    const u64 sync=ReadValue<u64>(world,0xA40);const u32 block=(handle>>11)&31,slot=handle&0x7ff;
    if(!ReadablePointer(sync,0x110) || block>=ReadValue<u32>(sync,8))return 0;
    const u64 entry=ReadValue<u64>(sync,0x10+block*8);
    if(!ReadablePointer(entry,0x18))return 0;
    const u64 record=ReadValue<u64>(entry,8);
    if(!ReadablePointer(record,0x10))return 0;
    const s32 count=ReadValue<s32>(record,0);
    if(count<0 || count>2048 || slot>=static_cast<u32>(count))return 0;
    const u64 actors=ReadValue<u64>(record,8);
    if(!ReadablePointer(actors+slot*0x38,8))return 0;
    const u64 actor=ReadValue<u64>(actors,slot*0x38);
    return ReadablePointer(actor,0x3B8) && ReadValue<u32>(actor,0x90)==handle?actor:0;
}
BbscCombatSample BbscCombatRead(u32 handle) {
    BbscCombatSample state;state.actor=BbscCombatActor(handle);state.owner=BbscWorldBlockOwner(handle);
    if(!state.actor)return state;
    state.hp=GetCharacterHp(state.actor);state.death=ReadValue<u8>(state.actor,0x1E3);
    const u64 control=ReadValue<u64>(state.actor,0x18);
    if(ReadablePointer(control,0x38)){
        state.current=ReadValue<s32>(control,0x10);state.requested=ReadValue<s32>(control,0x14);
        const u64 proxy=ReadValue<u64>(control,0x30);
        if(ReadablePointer(proxy,0x19))state.proxy=ReadValue<u8>(proxy,0x18);
    }
    const u64 modules=ReadValue<u64>(state.actor,0x3B0);
    if(ReadablePointer(modules,0x10)){
        const u64 action=ReadValue<u64>(modules,8);
        if(ReadablePointer(action,0x1B8))state.action=ReadValue<s32>(action,0x1B4);
    }
    const u64 world=ReadValue<u64>(image_base+CandidateLocalStatePointerOffset,0);
    if(const u64 word=BbscWorldOwnershipWord(world,state.actor))state.ownership=ReadValue<u16>(word,0);
    return state;
}
void BbscCombatLog(std::string_view stage,u32 handle,const BbscCombatSample& state,s32 requested_hp) {
    if(bbsc_combat_lines>=512)return;
    ++bbsc_combat_lines;
    BBSC_TIMELINE("COMBAT","native actor stage={} handle={:#x} owner={:08x} actor={:#x} hp={} requested_hp={} death={} action={} current={} requested={} proxy={} ownership={:#x} world={:08x}/{} visit={} map={:#x} load={} seq={}",
        stage,handle,state.owner,state.actor,state.hp,requested_hp,state.death,state.action,state.current,
        state.requested,state.proxy,state.ownership,bbsc_combat_fence.world.host,bbsc_combat_fence.world.room,
        bbsc_combat_fence.visit,bbsc_combat_fence.map,bbsc_combat_fence.load,bbsc_combat_lines);
}
void TraceBbscCombatActor(std::string_view stage,u64 actor,s32 requested_hp,bool begin) {
    if(!BbscCombatTraceEnabled() || !ReadablePointer(actor,0x94))return;
    std::scoped_lock lock{bbsc_combat_mutex};if(!BbscCombatContext())return;
    const u32 handle=ReadValue<u32>(actor,0x90);if(static_cast<s32>(handle)<0)return;
    const bool fresh=!bbsc_combat_watches.contains(handle);
    if(fresh){
        if(!begin)return;
        if(bbsc_combat_watches.size()>=8){
            const auto oldest=std::min_element(bbsc_combat_watches.begin(),bbsc_combat_watches.end(),
                [](const auto& a,const auto& b){return a.second.until<b.second.until;});
            bbsc_combat_watches.erase(oldest);
        }
    }
    auto& watch=bbsc_combat_watches[handle];
    if(begin && (fresh || stage!="hp-set-entry"))watch.until=SteadyNowMs()+15000;
    const auto sample=BbscCombatRead(handle);
    const bool event=stage=="hp-set-entry"?(!watch.hp_seen || watch.hp_request!=requested_hp):begin;
    if(stage=="hp-set-entry"){watch.hp_seen=true;watch.hp_request=requested_hp;}
    if(event || !watch.sampled || sample!=watch.last){
        BbscCombatLog(stage,handle,sample,requested_hp);watch.last=sample;watch.sampled=true;
    }
}
void TraceBbscCombatPacket(std::string_view stage,u32 channel,u32 peer,std::span<const u8> record,bool admitted) {
    if(!BbscCombatTraceEnabled() || record.size()<4)return;
    const u32 handle=World::NativeInitialWord(record,0);
    std::scoped_lock lock{bbsc_combat_mutex};
    if(!BbscCombatContext() || bbsc_combat_packet_lines>=128 || !bbsc_combat_watches.contains(handle))return;
    ++bbsc_combat_lines;++bbsc_combat_packet_lines;
    BBSC_TIMELINE("COMBAT","native packet stage={} channel={:#x} handle={:#x} peer={:08x} owner={:08x} admitted={} bytes={} fingerprint={:#x} world={:08x}/{} visit={} map={:#x} load={} seq={}",
        stage,channel,handle,peer,BbscWorldBlockOwner(handle),admitted,record.size(),World::NativeInitialFingerprint(record),
        bbsc_combat_fence.world.host,bbsc_combat_fence.world.room,bbsc_combat_fence.visit,
        bbsc_combat_fence.map,bbsc_combat_fence.load,bbsc_combat_lines);
}
void PS4_SYSV_ABI BbscCombatNativeHook(u64 tag,const GuestRegisterSnapshot* regs) {
    if(!regs || !BbscCombatTraceEnabled())return;
    if(tag==0){
        const s32 hp=static_cast<s32>(regs->rsi);
        TraceBbscCombatActor("hp-set-entry",regs->rdi,hp,hp<=0);
    }else if(tag==1)TraceBbscCombatActor("death-worker-entry",regs->rdi,0,false);
    else if(tag==2)TraceBbscCombatActor("native-hit-received",regs->r14,0,true);
}
void TickBbscCombatTrace() {
    if(!BbscCombatTraceEnabled())return;
    std::scoped_lock lock{bbsc_combat_mutex};if(!BbscCombatContext())return;
    for(auto& [handle,watch]:bbsc_combat_watches){
        const auto sample=BbscCombatRead(handle);
        if(!watch.sampled || sample!=watch.last){
            BbscCombatLog("tick",handle,sample,0);watch.last=sample;watch.sampled=true;
        }
    }
}
