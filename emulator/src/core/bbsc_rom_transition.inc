// SPDX-License-Identifier: GPL-2.0-or-later
// Resume the ORIGINAL13201803 at its native cutscene command. The game's
// EMEVD handler creates its own Remo condition and executes its own warp tail.
#ifdef BBSC_MOD
struct BbscRomTransition {
    bool pending=false,delegated=false;
    World::WorldId world{};
    u32 load=0;
    s64 requested=0;
};
BbscRomTransition bbsc_rom_transition;

void TickBbscRomTransition() {
    auto& trip=bbsc_rom_transition;
    if(!trip.pending && !trip.delegated)return;
    World::WorldId world;
    {std::scoped_lock lock{bbsc_world_presence_mutex};world=bbsc_world_presence_local.world;}
    if(!BbscIndependentTravelAllowed() || GetSessionState()!=6 ||
       GetCurrentPackedMap()!=0x20000000 || bbsc_load_generation.load()!=trip.load ||
       world!=trip.world || GetBbscRelayHost()!=trip.world.host ||
       (trip.pending && SteadyNowMs()-trip.requested>30'000)){
        BBSC_TIMELINE("TRAVEL","Rom native event request cancelled: source context changed or unavailable");
        trip={};
    }
}

bool QueueBbscRomNativeTransition(s32 scene) {
    if(scene!=32000000 || GetCurrentPackedMap()!=0x20000000 ||
       GetSessionState()!=6 || !BbscIndependentTravelAllowed())return false;
    TickBbscRomTransition();
    std::scoped_lock lock{bbsc_world_presence_mutex};
    const auto world=bbsc_world_presence_local.world;
    if(!World::Valid(world) || world.host!=GetBbscRelayHost())return false;
    if(bbsc_rom_transition.pending || bbsc_rom_transition.delegated)return true;
    bbsc_rom_transition={true,false,world,bbsc_load_generation.load(),SteadyNowMs()};
    BBSC_TIMELINE("TRAVEL","Rom group movie delegated to original event13201803");
    return true;
}

void EnableBbscRomNativeTransition(u64 instance) {
    if(!BbscIndependentTravelAllowed() || GetCurrentPackedMap()!=0x20000000 ||
       !ReadablePointer(instance,0xC8) || BbscEventIdOf(instance)!=13201803)return;
    // Host and guest execute their own local stream. The scoped movie packet
    // starts the group journey; a foreign native continuation cannot skip Remo.
    WriteValue<u8>(instance,0x78,0);
    TickBbscRomTransition();
    if(!bbsc_rom_transition.pending || GetSessionState()!=6)return;
    const u64 ref=ReadValue<u64>(instance,0xA8);
    const u64 file=ReadablePointer(ref,0x10)?ReadValue<u64>(ref,8):0;
    if(!ReadablePointer(file,0x80))return;
    const u64 root=ReadValue<u64>(instance,0x80);
    if(!ReadablePointer(root,0x10) || ReadValue<u64>(root,8)!=file)return;
    const s64 count=ReadValue<s64>(file,0x10);
    const u64 directory=file+ReadValue<u64>(file,0x18);
    if(count<1 || count>10000 || !ReadablePointer(directory,count*0x30))return;
    u64 row=0;
    for(s64 k=0;k<count;++k)
        if(ReadValue<s64>(directory+k*0x30,0)==13201803){row=directory+k*0x30;break;}
    if(!row || ReadValue<s64>(row,0x18)!=0 || ReadValue<u64>(instance,0x88)!=row)return;
    const s64 instructions=ReadValue<s64>(row,8);
    const u64 first=file+ReadValue<u64>(file,0x28)+ReadValue<u64>(row,0x10);
    if(instructions<5 || instructions>1000 || !ReadablePointer(first,instructions*0x20))return;
    s32 movie=-1;
    for(s32 k=0;k+4<instructions;++k){
        const u64 instruction=first+k*0x20;
        if(ReadValue<s32>(instruction,0)!=2002 || ReadValue<s32>(instruction,4)!=7 ||
           ReadValue<u64>(instruction,8)!=16)continue;
        const u64 args=file+ReadValue<u64>(file,0x78)+ReadValue<u64>(instruction,0x10);
        if(!ReadablePointer(args,16) || ReadValue<s32>(args,0)!=32000000)continue;
        movie=k;break;
    }
    if(movie<0)return;
    // Validate the actual original tail before delegating. No replacement
    // script, timer, flag writes or mod-issued warp; these commands run natively.
    const std::array<s32,5> banks{2002,1001,2003,2003,2003};
    const std::array<s32,5> commands{7,1,2,2,49};
    const std::array<u32,5> arg0{32000000,1,9180,70002802,2802958};
    const std::array<u64,5> sizes{16,4,8,8,4};
    for(size_t k=0;k<5;++k){
        const u64 instruction=first+(movie+k)*0x20;
        if(ReadValue<s32>(instruction,0)!=banks[k] || ReadValue<s32>(instruction,4)!=commands[k] ||
           ReadValue<u64>(instruction,8)!=sizes[k])return;
        const u64 args=file+ReadValue<u64>(file,0x78)+ReadValue<u64>(instruction,0x10);
        if(!ReadablePointer(args,sizes[k]) || ReadValue<u32>(args,0)!=arg0[k])return;
        if((k==2 || k==3) && ReadValue<u32>(args,4)!=(k==3?1u:0u))return;
    }
    const s32 current=ReadValue<s32>(instance,0xA0);
    if(current<0 || current>=instructions ||
       !HasMemoryAccess(instance+0xC0,4,MemoryProt::CpuWrite) ||
       !HasMemoryAccess(instance+0x48,4,MemoryProt::CpuWrite))return;
    // Same condition-tree cleanup and iterator advance used by12ECDC0 and
    // native control flow. Advance owns PC, argument allocation/substitution
    // and next-step state; no borrowed argument pointers or PC-only rewrite.
    using Clear=void PS4_SYSV_ABI (*)(u64);
    using Advance=u8 PS4_SYSV_ABI (*)(u64,u8*);
    reinterpret_cast<Clear>(image_base+0x012EBFF0)(instance+0x30);
    WriteValue<s32>(instance,0xC0,movie-current);
    u8 continue_frame=1;
    if(!reinterpret_cast<Advance>(image_base+0x012EF2E0)(instance+0x80,&continue_frame))return;
    WriteValue<s32>(instance,0x48,ReadValue<s32>(instance,0xA0));
    // Native12ECEF8 binds10000 on a satisfied local condition. We replaced
    // the guest-only wait, so retain that same local executor for Remo.
    WriteValue<s32>(instance,0x60,10000);
    bbsc_rom_transition.pending=false;
    bbsc_rom_transition.delegated=true;
    BBSC_TIMELINE("TRAVEL","Rom original event resumed at native movie; native wait/flags/2802958 tail retained");
}
#else
bool QueueBbscRomNativeTransition(s32){return false;}
void EnableBbscRomNativeTransition(u64){}
void TickBbscRomTransition(){}
#endif
