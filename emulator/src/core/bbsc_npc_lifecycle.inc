// SPDX-License-Identifier: GPL-2.0-or-later
// Read-only diagnostics for actors addressed by personal native events.
// Re-resolve entity IDs at every sample: never retain/dereference an actor
// pointer across a load, streaming eviction or native actor recreation.
std::recursive_mutex bbsc_npc_lifecycle_mutex;
struct BbscNpcLifecycleState {
    u64 actor=0,control=0;
    s32 handle=-1,current=-1,requested=-1;
    u8 backread_off=0,backread_on=0,disabled=0;
    bool operator==(const BbscNpcLifecycleState&) const = default;
};
struct BbscNpcLifecycleWatch {
    s64 event=0;
    s32 opcode=0;
    u8 operand=0;
    bool sampled=false;
    BbscNpcLifecycleState previous;
};
std::map<u32,BbscNpcLifecycleWatch> bbsc_npc_lifecycle_watches;
u32 bbsc_npc_lifecycle_generation=~u32{0},bbsc_npc_lifecycle_map=0;
s32 bbsc_npc_lifecycle_session=-1;
size_t bbsc_npc_lifecycle_lines=0;
s64 bbsc_npc_lifecycle_next=0;
thread_local bool bbsc_npc_lifecycle_wake_sample=false;
thread_local u32 bbsc_npc_lifecycle_wake_generation=0,bbsc_npc_lifecycle_wake_map=0;
thread_local s32 bbsc_npc_lifecycle_wake_session=-1;
bool BbscNpcLifecycleContext() {
    const u32 generation=bbsc_load_generation.load(),map=GetCurrentPackedMap();
    const s32 session=GetSessionState();
    const bool enabled=BbscTimelineEnabled() && (session==3 || session==4 || session==6);
    if(!enabled || generation!=bbsc_npc_lifecycle_generation || map!=bbsc_npc_lifecycle_map ||
       session!=bbsc_npc_lifecycle_session){
        bbsc_npc_lifecycle_watches.clear();bbsc_npc_lifecycle_lines=0;
        bbsc_npc_lifecycle_next=0;bbsc_npc_lifecycle_wake_sample=false;
        bbsc_npc_lifecycle_generation=generation;bbsc_npc_lifecycle_map=map;
        bbsc_npc_lifecycle_session=session;
    }
    return enabled;
}
void WatchBbscNpcLifecycle(u32 entity,s64 event,s32 opcode,u8 operand) {
    std::scoped_lock lock{bbsc_npc_lifecycle_mutex};
    if(!BbscNpcLifecycleContext() || !IsBbscPersonalMapEvent(event))return;
    if(!bbsc_npc_lifecycle_watches.contains(entity) && bbsc_npc_lifecycle_watches.size()>=64)return;
    auto& watch=bbsc_npc_lifecycle_watches[entity];
    watch.event=event;watch.opcode=opcode;watch.operand=operand;
}
void ObserveBbscNpcLifecycle(std::string_view boundary,u32 block=0) {
#ifdef BBSC_PERF_NESTED
    BBSC_PERF_NESTED("measure NPC lifecycle");
#endif
    std::scoped_lock lock{bbsc_npc_lifecycle_mutex};
    if(!BbscNpcLifecycleContext() || bbsc_npc_lifecycle_lines>=512)return;
    using Find=u64 PS4_SYSV_ABI (*)(u32,u64,u64);
    for(auto& [entity,watch]:bbsc_npc_lifecycle_watches){
        BbscNpcLifecycleState state;
        const u64 actor=reinterpret_cast<Find>(image_base+0x013C97A0)(entity,0,0);
        if(ReadablePointer(actor,0x94)){
            state.actor=actor;state.handle=ReadValue<s32>(actor,0x90);
            state.backread_off=ReadValue<u8>(actor,0x28);state.backread_on=ReadValue<u8>(actor,0x29);
            state.control=ReadValue<u64>(actor,0x18);
            if(ReadablePointer(state.control,0x21)){
                state.current=ReadValue<s32>(state.control,0x10);
                state.requested=ReadValue<s32>(state.control,0x14);
                state.disabled=ReadValue<u8>(state.control,0x20);
            }
        }
        if(watch.sampled && state==watch.previous)continue;
        watch.sampled=true;watch.previous=state;++bbsc_npc_lifecycle_lines;
        BBSC_TIMELINE("QUEST","native NPC lifecycle boundary={} entity={} event={} opcode={} operand={} actor={:#x} handle={} control={:#x} backread_off={} backread_on={} current={} requested={} disabled={} block={:#x} map={:#x} load={}",
            boundary,entity,watch.event,watch.opcode,watch.operand,state.actor,state.handle,state.control,
            state.backread_off,state.backread_on,state.current,state.requested,state.disabled,block,
            bbsc_npc_lifecycle_map,bbsc_npc_lifecycle_generation);
        if(bbsc_npc_lifecycle_lines>=512)break;
    }
}
void BeginBbscNpcLifecycleWake() {
    std::scoped_lock lock{bbsc_npc_lifecycle_mutex};
    if(!BbscNpcLifecycleContext())return;
    const s64 now=SteadyNowMs();
    bbsc_npc_lifecycle_wake_sample=!bbsc_npc_lifecycle_watches.empty() &&
        bbsc_npc_lifecycle_lines<512 && now>=bbsc_npc_lifecycle_next;
    if(!bbsc_npc_lifecycle_wake_sample)return;
    bbsc_npc_lifecycle_wake_generation=bbsc_npc_lifecycle_generation;
    bbsc_npc_lifecycle_wake_map=bbsc_npc_lifecycle_map;
    bbsc_npc_lifecycle_wake_session=bbsc_npc_lifecycle_session;
    bbsc_npc_lifecycle_next=now+250;
    ObserveBbscNpcLifecycle("wake-before");
}
void EndBbscNpcLifecycleWake() {
    std::scoped_lock lock{bbsc_npc_lifecycle_mutex};
    if(std::exchange(bbsc_npc_lifecycle_wake_sample,false) &&
       bbsc_npc_lifecycle_wake_generation==bbsc_load_generation.load() &&
       bbsc_npc_lifecycle_wake_map==GetCurrentPackedMap() &&
       bbsc_npc_lifecycle_wake_session==GetSessionState())ObserveBbscNpcLifecycle("wake-after");
}
