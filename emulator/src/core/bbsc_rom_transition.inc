// SPDX-License-Identifier: GPL-2.0-or-later
// Resume the original story events. Their EMEVD commands own the Remo
// condition, time change, cleanup and (for Rom) the warp to Yahar'gul.
#ifdef BBSC_MOD
struct BbscRomTransition {
    bool pending=false,delegated=false;
    s32 scene=0;
    World::WorldId world{};
    u32 load=0;
};
BbscRomTransition bbsc_rom_transition;

bool BbscGroupStoryMovie(u32 map, s32 scene) {
    return (map == 0x20000000 && scene == 32000000) ||
           (map == 0x18000000 && scene == 24000030);
}

// A local movie request can precede the host's group movie packet. Keep its
// native time change through the first destination load in this same room.
struct BbscRomMovieVisit {
    World::WorldId world{};
    u32 load=0;
};
BbscRomMovieVisit bbsc_rom_movie_visit; // protected by the presence mutex
World::WorldId bbsc_amelia_movie_world{}; // protected by the presence mutex

void NoteBbscRomMovieRequest(s32 scene) {
    if (!BbscGroupStoryMovie(GetCurrentPackedMap(), scene) || !BbscIndependentTravelAllowed()) return;
    std::scoped_lock lock{bbsc_world_presence_mutex};
    const auto world=bbsc_world_presence_local.world;
    if (!World::Valid(world)) return;
    if (scene == 32000000) bbsc_rom_movie_visit={world,bbsc_load_generation.load()};
    else bbsc_amelia_movie_world = world;
}

bool BbscAmeliaKeepsNativeTime() {
    if (!BbscIndependentTravelAllowed()) return false;
    std::scoped_lock lock{bbsc_world_presence_mutex};
    return World::Valid(bbsc_amelia_movie_world) &&
           bbsc_amelia_movie_world == bbsc_world_presence_local.world;
}

bool BbscRomKeepsNativeTime(u32 map) {
    if((map!=0x20000000 && map!=0x1c000000) || !BbscIndependentTravelAllowed())return false;
    std::scoped_lock lock{bbsc_world_presence_mutex};
    const auto& visit=bbsc_rom_movie_visit;
    if(!World::Valid(visit.world) || visit.world!=bbsc_world_presence_local.world)return false;
    const u32 load=bbsc_load_generation.load();
    // During construction the generation is still the source generation.
    return load==visit.load || (map==0x1c000000 && load==visit.load+1);
}

void ValidateBbscStoryMovie() {
    auto& trip=bbsc_rom_transition;
    if(!trip.pending && !trip.delegated)return;
    World::WorldId world;
    {std::scoped_lock lock{bbsc_world_presence_mutex};world=bbsc_world_presence_local.world;}
    const s32 session = GetSessionState();
    if(!BbscIndependentTravelAllowed() || (session!=3 && session!=6) ||
       !BbscGroupStoryMovie(GetCurrentPackedMap(), trip.scene) ||
       bbsc_load_generation.load()!=trip.load || world!=trip.world ||
       (session==6 && GetBbscRelayHost()!=trip.world.host)) {
        BBSC_TIMELINE("CUTSCENE","native story request {} cancelled: source context changed or unavailable", trip.scene);
        trip={};
    }
}

bool QueueBbscRomNativeTransition(s32 scene) {
    const s32 session = GetSessionState();
    if (!BbscGroupStoryMovie(GetCurrentPackedMap(), scene) ||
        (session!=3 && session!=6) || !BbscIndependentTravelAllowed()) return false;
    ValidateBbscStoryMovie();
    std::scoped_lock lock{bbsc_world_presence_mutex};
    const auto world=bbsc_world_presence_local.world;
    if (!World::Valid(world) || (session==6 && world.host!=GetBbscRelayHost())) return false;
    if(bbsc_rom_transition.pending || bbsc_rom_transition.delegated)return true;
    bbsc_rom_transition={true,false,scene,world,bbsc_load_generation.load()};
    BBSC_TIMELINE("CUTSCENE","group scene {} delegated to the original event", scene);
    return true;
}

void EnableBbscRomNativeTransition(u64 instance) {
    if (!BbscIndependentTravelAllowed() || !ReadablePointer(instance,0xC8)) return;
    const s64 event = BbscEventIdOf(instance);
    const bool rom = event == 13201803;
    if (!rom && event != 12401803) return;
    const s32 scene = rom ? 32000000 : 24000030;
    if (!BbscGroupStoryMovie(GetCurrentPackedMap(), scene)) return;
    // Host and guest execute their own local stream. The scoped movie packet
    // starts the group journey; a foreign native continuation cannot skip Remo.
    if (ReadValue<u8>(instance,0x78) != 0) WriteValue<u8>(instance,0x78,0);
    if (!bbsc_rom_transition.pending) return;
    ValidateBbscStoryMovie();
    if (!bbsc_rom_transition.pending || bbsc_rom_transition.scene != scene) return;
    const u64 ref=ReadValue<u64>(instance,0xA8);
    const u64 file=ReadablePointer(ref,0x10)?ReadValue<u64>(ref,8):0;
    if(!ReadablePointer(file,0x80))return;
    const u64 root=ReadValue<u64>(instance,0x80);
    if(!ReadablePointer(root,0x10) || ReadValue<u64>(root,8)!=file)return;
    const s64 count=ReadValue<s64>(file,0x10);
    const u64 directory=file+ReadValue<u64>(file,0x18);
    const u64 row=ReadValue<u64>(instance,0x88);
    if (count<1 || count>10000 || row<directory || row-directory>=static_cast<u64>(count)*0x30 ||
        (row-directory)%0x30 || !ReadablePointer(row,0x30) ||
        ReadValue<s64>(row,0)!=event || ReadValue<s64>(row,0x18)!=0) return;
    const s64 instructions=ReadValue<s64>(row,8);
    const u64 first=file+ReadValue<u64>(file,0x28)+ReadValue<u64>(row,0x10);
    if(instructions<5 || instructions>1000 || !ReadablePointer(first,instructions*0x20))return;
    struct Step { s32 bank, command; std::initializer_list<u32> args; };
    const std::array<Step,7> rom_tail{{
        {2003,2,{9180,1}}, {1001,1,{1}},
        {2002,7,{32000000,0,10000,3}}, {1001,1,{1}}, {2003,2,{9180,0}},
        {2003,2,{70002802,1}}, {2003,49,{2802958}},
    }};
    const std::array<Step,6> amelia_tail{{
        {2003,2,{9180,1}}, {1001,1,{1}}, {2006,1,{2403413,1}},
        {2002,6,{24000030,0,0xFFFFFFFFu,24,10000,2}}, {1001,1,{1}}, {2003,2,{9180,0}},
    }};
    const s32 start = rom ? 40 : 10;
    const std::span<const Step> tail = rom ? std::span<const Step>(rom_tail) :
                                           std::span<const Step>(amelia_tail);
    if (start + static_cast<s32>(tail.size()) > instructions) return;
    for (size_t k=0; k<tail.size(); ++k) {
        const auto& step = tail[k];
        const u64 instruction = first+(start+k)*0x20;
        const size_t size = step.args.size()*sizeof(u32);
        if (ReadValue<s32>(instruction,0)!=step.bank || ReadValue<s32>(instruction,4)!=step.command ||
            ReadValue<u64>(instruction,8)!=size) return;
        const u64 args=file+ReadValue<u64>(file,0x78)+ReadValue<u64>(instruction,0x10);
        if (!ReadablePointer(args,size) ||
            std::memcmp(reinterpret_cast<const void*>(args),step.args.begin(),size)!=0) return;
    }
    const s32 current=ReadValue<s32>(instance,0xA0);
    if(current<0 || current>=instructions)return;
    if (current > start && current <= start + static_cast<s32>(tail.size())) {
        // A simultaneous local interaction has already reached the original
        // tail. Leave its Remo condition and cleanup intact.
        bbsc_rom_transition.pending = false;
        bbsc_rom_transition.delegated = true;
        return;
    }
    if (current != start &&
        (!HasMemoryAccess(instance+0xC0,4,MemoryProt::CpuWrite) ||
         !HasMemoryAccess(instance+0x48,4,MemoryProt::CpuWrite))) return;
    // The native scheduler advances to start before the action condition is
    // satisfied. At that point releasing the wait is enough to run the tail.
    using Clear=void PS4_SYSV_ABI (*)(u64);
    reinterpret_cast<Clear>(image_base+0x012EBFF0)(instance+0x30);
    if (current != start) {
        // For other entry positions, the native iterator owns the PC and arguments.
        using Advance=u8 PS4_SYSV_ABI (*)(u64,u8*);
        WriteValue<s32>(instance,0xC0,start-current);
        u8 continue_frame=1;
        if(!reinterpret_cast<Advance>(image_base+0x012EF2E0)(instance+0x80,&continue_frame))return;
        WriteValue<s32>(instance,0x48,ReadValue<s32>(instance,0xA0));
    }
    // Native12ECEF8 binds10000 on a satisfied local condition. We replaced
    // the guest-only wait, so retain that same local executor for Remo.
    WriteValue<s32>(instance,0x60,10000);
    bbsc_rom_transition.pending=false;
    bbsc_rom_transition.delegated=true;
    BBSC_TIMELINE("CUTSCENE","original event {} resumed with its native movie and continuation", event);
}
#else
bool BbscGroupStoryMovie(u32,s32){return false;}
void NoteBbscRomMovieRequest(s32){}
bool BbscRomKeepsNativeTime(u32){return false;}
bool BbscAmeliaKeepsNativeTime(){return false;}
bool QueueBbscRomNativeTransition(s32){return false;}
void EnableBbscRomNativeTransition(u64){}
#endif
