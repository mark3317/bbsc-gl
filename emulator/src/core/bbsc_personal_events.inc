// SPDX-License-Identifier: GPL-2.0-or-later
// Included by bloodborne_re.cpp. Event identity/transport isolation only;
// appearance, quest conditions and actor commands remain native.
bool BbscPersonalEventIsolation() {
    const s32 state=GetSessionState();
    // Each category checks its own switch below. Rom's native local safety
    // event must remain local even when optional NPC/travel features are off.
    return state==3 || state==4 || state==6;
}
bool BbscIsolatedNativeEvent(s64 event) {
    // Host and guest jump scripts both target their own local player10000.
    // Foreign progress must not release another player's region wait.
    if(event==13204820 || event==13204821 || event==13204832 || event==13204833)return true;
    // These are the same native local journeys localized at event update.
    // m29 uses12907020 for lamp return (separate from common7200).
    // Both channel31 schemas ignore that setting at receive; timed sending
    // also ignores it. Foreign continuations must not steer a local journey.
    if(BbscIndependentTravelAllowed() &&
       (LampTravel::IsNativeTravelEvent(event) || event==13201803 || event==12401803 || LampTravel::IsLampActivationEvent(event) ||
        IsBbscKidnapEvent(event) || Bbsc::DreamFinale::EventEnding(event)))return true;
    // Keep native actor synchronization in both modes. A remote EMEVD cursor
    // must not bypass this player's conditions in any reviewed quest controller.
    return BbscOwnNpcQuestsEnabled() &&
           (std::ranges::binary_search(QuestRules::LocalEvents, event) || IsBbscPersonalMapEvent(event));
}
bool BbscPersonalEventMessage(std::span<const u8> bytes,u32& event,u16& kind) {
    if(bytes.size()<0x18)return false;
    u16 root;u32 size;
    std::memcpy(&root,bytes.data(),2);std::memcpy(&kind,bytes.data()+2,2);
    std::memcpy(&size,bytes.data()+4,4);std::memcpy(&event,bytes.data()+8,4);
    // Native012EE540: condition progress (1,8); Native012EE660: timed
    // continuation (2,12). The latter does NOT check event+78 at all.
    return root==0 && ((kind==1 && size==8 && bytes.size()==0x18) ||
        (kind==2 && size==12 && bytes.size()==0x1C)) && BbscIsolatedNativeEvent(event);
}
void NoteBbscPersonalEventTransport(std::string_view direction,u32 event,u16 kind) {
    if(!BbscTimelineEnabled())return;
    static u32 generation=~u32{0};static std::set<std::tuple<u32,u16,bool>> logged;
    const u32 current=bbsc_load_generation.load();
    if(generation!=current){generation=current;logged.clear();}
    const bool incoming=direction=="receive";
    if(logged.size()<256 && logged.emplace(event,kind,incoming).second)
        BBSC_TIMELINE(LampTravel::IsNativeTravelEvent(event)?"TRAVEL":"QUEST",
            "local native event {} isolated event={} kind={} load={}",direction,event,kind,current);
}
u8 bbsc_personal_event_send_skip=0,bbsc_personal_event_receive_skip=0;
void PS4_SYSV_ABI BbscPersonalEventSendHook(u64 kind,const GuestRegisterSnapshot* r) {
    if(!r || !BbscPersonalEventIsolation() || !ReadablePointer(r->rdi,0x30))return;
    const u32 event=ReadValue<u32>(r->rdi,0x28);
    if(!BbscIsolatedNativeEvent(event))return;
    // Native emitters return void. Only the remote copy is suppressed;
    // local timing, instruction advance and all commands run. At this boundary
    // an internal native restart cannot undo event localization mid-update.
    bbsc_personal_event_send_skip=1;
    NoteBbscPersonalEventTransport("send",event,static_cast<u16>(kind));
}
void PS4_SYSV_ABI BbscPersonalEventReceiveHook(u64,const GuestRegisterSnapshot* r) {
    if(!r)return;
    using Receive=s32 PS4_SYSV_ABI (*)(u64,u64,u32,u8*,u32);
    auto receive=reinterpret_cast<Receive>(image_base+0x01789200);
    s32 size=0;
    for(unsigned i=0;i<8;++i){
        size=receive(r->rdi,r->rsi,static_cast<u32>(r->rdx),reinterpret_cast<u8*>(r->rcx),static_cast<u32>(r->r8));
        if(size<=0 || size>static_cast<s32>(r->r8) || !BbscPersonalEventIsolation() ||
           r->rdx!=0x31 || !ReadablePointer(r->rcx,static_cast<size_t>(size)))break;
        u32 event=0;u16 kind=0;
        if(!BbscPersonalEventMessage({reinterpret_cast<const u8*>(r->rcx),static_cast<size_t>(size)},event,kind))break;
        // Already consumed/ACKed by native reliable transport. Do not let
        // another player's PC/conditions enter a personal local event.
        NoteBbscPersonalEventTransport("receive",event,kind);size=0;
    }
    const_cast<GuestRegisterSnapshot*>(r)->rax=static_cast<u64>(static_cast<s64>(size));
    // Callsite hook: the callback has executed the ORIGINAL Receive itself.
    // The relative CALL must never be copied/executed in the trampoline.
    bbsc_personal_event_receive_skip=1;
}

#include "core/bbsc_npc_lifecycle.inc"

// Diagnostics observe native event instructions and the immediate result of
// character state commands. No quest stage predicate participates in gameplay.
struct BbscPersonalEventObservation {u64 instruction=0;};
std::map<u64,BbscPersonalEventObservation> bbsc_personal_event_observations;
struct BbscPersonalActorObservation {u64 actor=0;u32 entity=0; s64 event=0;s32 opcode=0;};
BbscPersonalActorObservation bbsc_personal_actor_pending;
void FlushBbscPersonalActorObservation() {
    const auto pending=std::exchange(bbsc_personal_actor_pending,{});
    if(!pending.actor || !BbscTimelineEnabled() || !ReadablePointer(pending.actor,0x30))return;
    const u64 activation=ReadValue<u64>(pending.actor,0x18);
    BBSC_TIMELINE("QUEST","native personal actor result event={} opcode={} entity={} actor={:#x} backread_off={} backread_on={} current={} requested={} disabled={}",
        pending.event,pending.opcode,pending.entity,pending.actor,
        ReadValue<u8>(pending.actor,0x28),ReadValue<u8>(pending.actor,0x29),
        ReadablePointer(activation,0x21)?ReadValue<s32>(activation,0x10):-1,
        ReadablePointer(activation,0x21)?ReadValue<s32>(activation,0x14):-1,
        ReadablePointer(activation,0x21)?ReadValue<u8>(activation,0x20):0);
}
void ObserveBbscPersonalEvent(u64 instance,s64 event) {
    if(!BbscTimelineEnabled() || !IsBbscLocalQuestEvent(event))return;
    static u32 generation=~u32{0};const u32 current=bbsc_load_generation.load();
    if(generation!=current){generation=current;bbsc_personal_event_observations.clear();}
    if(bbsc_personal_event_observations.size()>=4096)return;
    const u64 instruction=ReadValue<u64>(instance,0xB0);
    auto& previous=bbsc_personal_event_observations[instance];
    if(previous.instruction==instruction || !ReadablePointer(instruction,0x18))return;
    previous.instruction=instruction;
    const s32 bank=ReadValue<s32>(instruction,0),opcode=ReadValue<s32>(instruction,4);
    u64 args=ReadValue<u64>(instance,0xB8);
    if(!args){
        const u64 ref=ReadValue<u64>(instance,0xA8),file=ReadablePointer(ref,0x10)?ReadValue<u64>(ref,8):0;
        if(ReadablePointer(file,0x80))args=file+ReadValue<u64>(file,0x78)+ReadValue<u64>(instruction,0x10);
    }
    const u64 length=ReadValue<u64>(instruction,8);
    const u32 first=length>=4 && ReadablePointer(args,4)?ReadValue<u32>(args,0):0;
    const u32 second=length>=8 && ReadablePointer(args,8)?ReadValue<u32>(args,4):0;
    // Observe the ORIGINAL branch operand, never use its value to authorize
    // a command. -1 marks commands that are not flag predicates.
    const s32 observed=(bank==3 && opcode==0 || bank==1003 && opcode==101) && length>=8?
        static_cast<s32>(BbscEventFlag(second)):-1;
    BBSC_TIMELINE("QUEST","native personal event step event={} bank={} opcode={} first={} second={} observed_flag={} net={} load={}",
        event,bank,opcode,first,second,observed,ReadValue<u8>(instance,0x78),current);
}
void NoteBbscNativeWorldFlagApply(u32 map,u32 key,const u8* before,const u8* after,size_t size) {
    if(!BbscTimelineEnabled())return;
    size_t changed=0;u32 first=0,last=0;
    for(size_t byte=0;byte<size;++byte){
        const u8 delta=before[byte]^after[byte];
        for(unsigned bit=0;bit<8;++bit)if(delta&(0x80u>>bit)){
            const u32 flag=key*1000+static_cast<u32>(byte*8+bit);
            if(!changed)first=flag;last=flag;++changed;
        }
    }
    if(changed)BBSC_TIMELINE("WORLD","native snapshot flags applied map={:#x} group={} changed={} first={} last={} load={}",
        map,key,changed,first,last,bbsc_load_generation.load());
}
void ObserveBbscNativeWorldCommand(u64 instance,s32 bank) {
    if(!BbscTimelineEnabled() || !ReadablePointer(instance,0xC0))return;
    FlushBbscPersonalActorObservation();
    const u64 instruction=ReadValue<u64>(instance,0xB0);
    if(!ReadablePointer(instruction,0x18) || ReadValue<s32>(instruction,0)!=bank)return;
    const s32 opcode=ReadValue<s32>(instruction,4);
    if(bank==2004 && opcode!=5 && opcode!=29)return;
    static u32 generation=~u32{0};static std::set<std::pair<u64,u64>> logged;
    const u32 current=bbsc_load_generation.load();
    if(generation!=current){generation=current;logged.clear();}
    if(logged.size()>=512 || !logged.emplace(instance,instruction).second)return;
    u64 args=ReadValue<u64>(instance,0xB8);
    if(!args){
        const u64 ref=ReadValue<u64>(instance,0xA8),file=ReadablePointer(ref,0x10)?ReadValue<u64>(ref,8):0;
        if(ReadablePointer(file,0x80))args=file+ReadValue<u64>(file,0x78)+ReadValue<u64>(instruction,0x10);
    }
    const u64 length=ReadValue<u64>(instruction,8);
    if(length<4 || !ReadablePointer(args,static_cast<size_t>(std::min<u64>(length,12))))return;
    const u32 first=ReadValue<u32>(args,0),second=length>=8?ReadValue<u32>(args,4):0;
    const s64 event=BbscEventIdOf(instance);
    BBSC_TIMELINE("WORLD","native state command event={} bank={} opcode={} first={} second={} map={:#x} load={}",
        event,bank,opcode,first,second,GetCurrentPackedMap(),current);
    if(bank==2004){
        using Find=u64 PS4_SYSV_ABI (*)(u32,u64,u64);
        const u64 actor=reinterpret_cast<Find>(image_base+0x013C97A0)(first,0,0);
        bbsc_personal_actor_pending={actor,first,event,opcode};
        if(length>=5)WatchBbscNpcLifecycle(first,event,opcode,ReadValue<u8>(args,4));
    }
}
