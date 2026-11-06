"""Regression: native unqueued return after a cross-map summon must keep its map.
Executes production callbacks and the original 1.09 loader CMP/map-read opcodes.
Allocated fixture memory only; no game process or saves.
"""
import os
from pathlib import Path
import test_world_travel_native as travel

REGRESSION=r"""
 // A fresh cross-map join has host placement m24_01 and summon phase3.
 // Native WarpNextStage_Bonfire(2102950) selects Dream in global+0C.
 bbsc_world_travel_inflight=false;bbsc_world_travel_point=0;
 bbsc_world_travel_native_armed=false;bbsc_world_requested_scope.reset();
 bbsc_world_requested_mount.reset();bbsc_world_altar_visiting=-1;
 current_map=0x18010000;state=6;allowed=true;hp=594;
 std::array<u8,0x88> rules{};Set(rules,0x84,s32{3});
 Set(global,0x0c,u32{0x15000000});Set(global,0x14c4,u32{0x18010000});
 const auto original_global=global;const auto original_rules=rules;
 // Original0192997A CMP/JNE; original map loads01929987/8E and01929A8A/91.
 // Relocate only RIP pointer operands and JNE displacement into allocated code.
 const u8 loader[]={0x48,0x89,0xf8, // rax = SysV argument (rules)
   0x83,0xb8,0x84,0,0,0,3,0x0f,0x85,14,0,0,0,
   0x48,0x8b,0x05,0,0,0,0,0x8b,0x80,0xc4,0x14,0,0,0xc3,
   0x48,0x8b,0x05,0,0,0,0,0x8b,0x40,0x0c,0xc3};
 auto* code=reinterpret_cast<u8*>(image_base+0x1000);
 std::memcpy(code,loader,sizeof(loader));
 const u64 global_pointer=image_base+0x1100;
 WriteValue<u64>(global_pointer,0,GetGlobalState());
 WriteValue<s32>(reinterpret_cast<u64>(code),19,static_cast<s32>(global_pointer-(reinterpret_cast<u64>(code)+23)));
 WriteValue<s32>(reinterpret_cast<u64>(code),33,static_cast<s32>(global_pointer-(reinterpret_cast<u64>(code)+37)));
 using Pick=u32 PS4_SYSV_ABI (*)(u64);
 auto pick=reinterpret_cast<Pick>(code);
 assert(pick(reinterpret_cast<u64>(rules.data()))==0x18010000); // native bug mechanism
 GuestRegisterSnapshot phase;phase.rax=reinterpret_cast<u64>(rules.data());
 BbscWorldBonfirePhase(0,&phase);assert(pick(phase.rax)==0x18010000); // no local trip: preserve summon
 r.rdi=2102950;r.rsi=12345;const auto before_arms=arms;
 BbscWorldNativeWarpBegin(&r);
 phase.rax=reinterpret_cast<u64>(rules.data());BbscWorldBonfirePhase(0,&phase);
 assert(pick(phase.rax)==0x15000000); // REGRESSION: old production callback fails here
 assert(bbsc_world_travel_inflight&&bbsc_world_travel_point==2102950);
 assert(bbsc_world_requested_scope->map==0x15000000);
 assert(bbsc_world_requested_scope->world==bbsc_world_presence_local.world);
 assert(global==original_global&&rules==original_rules); // no stale-bank or native phase writes
 BbscWorldNativeWarpBegin(&r);assert(arms==before_arms+1);
 ++bbsc_load_generation;current_map=0x15000000;TickBbscWorldTravel();
 assert(!bbsc_world_travel_inflight&&bbsc_world_travel_point==0);
 phase.rax=reinterpret_cast<u64>(rules.data());BbscWorldBonfirePhase(0,&phase);
 assert(pick(phase.rax)==0x18010000); // guard expires with completed journey
 // Subsequent native return, even if old queued scope names another map.
 current_map=0x18010000;r.rdi=2102950;BbscWorldNativeWarpBegin(&r);
 assert(bbsc_world_requested_scope->map==0x15000000);
 ++bbsc_load_generation;current_map=0x15000000;TickBbscWorldTravel();
 // Unknown requests and calls outside co-op do not acquire a local trip.
 r.rdi=-1;BbscWorldNativeWarpBegin(&r);assert(!bbsc_world_travel_inflight);
 for(auto role:{0,4,7}){state=role;r.rdi=2102950;BbscWorldNativeWarpBegin(&r);assert(!bbsc_world_travel_inflight);}
 state=6;allowed=false;BbscWorldNativeWarpBegin(&r);assert(!bbsc_world_travel_inflight);allowed=true;
 // Both roles use the same native destination; initial join remains untouched.
 state=3;current_map=0x18010000;BbscWorldNativeWarpBegin(&r);
 phase.rax=reinterpret_cast<u64>(rules.data());BbscWorldBonfirePhase(0,&phase);assert(pick(phase.rax)==0x15000000);
 ++bbsc_load_generation;current_map=0x15000000;TickBbscWorldTravel();
"""

def check_original_loader(path):
    import struct
    data=Path(path).read_bytes();ph=struct.unpack_from('<Q',data,32)[0]
    size,count=struct.unpack_from('<HH',data,54)
    segments=[struct.unpack_from('<II6Q',data,ph+i*size) for i in range(count)]
    def read(a,n):
        s=next(s for s in segments if s[0]==1 and s[3]<=a<a+n<=s[3]+s[5])
        return data[s[2]+a-s[3]:s[2]+a-s[3]+n]
    assert read(0x192997a,7)==bytes.fromhex('83 b8 84 00 00 00 03')
    assert read(0x1929981,2)==bytes.fromhex('0f 85')
    assert 0x1929987+struct.unpack('<i',read(0x1929983,4))[0]==0x1929a8a
    assert read(0x192998e,6)==bytes.fromhex('8b 80 c4 14 00 00')
    assert read(0x1929a91,3)==bytes.fromhex('8b 40 0c')
    assert read(0x13cdfab,3)==bytes.fromhex('89 41 0c')
    assert read(0x13cdffb,7)==bytes.fromhex('48 89 88 3c 15 00 00')
    print('PASS original1.09: bonfire destination write, summon-phase branch and BOTH native map reads')

if __name__=='__main__':
    if os.environ.get('BBSC_TEST_EBOOT'):check_original_loader(os.environ['BBSC_TEST_EBOOT'])
    travel.MAIN=travel.MAIN.replace(' VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);',REGRESSION+'\n VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);')
    travel.main()
    print('PASS unqueued Dream return after cross-map join: old host map rejected; native destination retained; scoped lifecycle and negative paths')
