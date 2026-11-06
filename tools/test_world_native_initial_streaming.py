"""Late arrivals must not wait for the resident's extra streamed map blocks.

Reuse the native admission fixture, including its real request/reply/load fences,
with a resident packet containing a block the visitor has not loaded. No live
process, game assets or saves are changed.
"""
import test_world_native_initial as fixture


def main():
    # Run the existing production admission lifecycle against an OWNER SUPERSET,
    # rather than the identical streaming footprints in the original fixture.
    fixture.MAIN = fixture.MAIN.replace(
        'packet=make();assert(World::NativeInitialCharacters(packet)->size()==1);',
        'packet=make(true);assert(World::NativeInitialCharacters(packet)->size()==2);',
    )
    marker = 'assert(BbscWorldApplyNativeInitial(packet)&&applied==1);'
    assert fixture.MAIN.count(marker) == 1
    fixture.MAIN = fixture.MAIN.replace(marker, marker + r'''
 // Provider extras must not conceal missing LOCAL blocks or count mismatches.
 put(world,0x278,s32(4));put(world,0x298,u64(1));put(world,0x2A8,addr(block2));
 put(block2,8,addr(mapdata2));put(mapdata2,8,u32(0x19000000));
 put(block2,0xB8,s32(2));put(block2,0xC0,addr(entries));
 assert(!BbscWorldApplyNativeInitial(packet)&&applied==1);
 // No overlap is not a successful bootstrap; never silently discard the NPCs.
 put(world,0x278,s32(3));put(mapdata,8,u32(0x19000000));
 assert(!BbscWorldApplyNativeInitial(packet)&&applied==1);
 put(mapdata,8,u32(0x18000000));
 put(world,0x278,s32(2));
 assert(!BbscWorldApplyNativeInitial(packet)&&applied==1);
 put(world,0x278,s32(3));
''')
    fixture.main()
    print('PASS resident extra streaming blocks: immediate native admission, '
          'local coverage/count preflight, no-overlap rejection, once-only apply')


if __name__ == '__main__':
    main()
