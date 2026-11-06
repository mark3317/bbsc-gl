"""Production player lifecycle and original renderer across native map borders.

Uses allocated fixture memory. Optional BBSC_TEST_MAPSTUDIO verifies the border
table against read-only original 1.09 ConnectCollision records.
"""
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import test_world_player_lifecycle as life
import test_world_player_render_admission as render

ROOT = life.ROOT

MAIN = life.MAIN[:life.MAIN.index(' // A valid DrawModule')].replace(
    'local.map=0x15000000', 'local.map=0x18000000').replace(
    'peer=bbsc_world_presence_local;', 'peer=bbsc_world_presence_local;peer.map=0x1B000000;') + r'''
 const u64 activation=reinterpret_cast<u64>(control.data());
 // Opposite sides of Cathedral/Forest: keep and attach the native actor.
 assert(!World::SamePlace(bbsc_world_presence_local,peer));
 assert(BbscWorldTaskHere(reinterpret_cast<u64>(task.data())));
 TickBbscWorldPlayers();assert(binds==1&&attachments==1&&inserts==0);
 assert(ReadValue<u8>(activation,0x20)==0);
 // Existing hidden actor is enabled in either direction, for either role.
 WriteValue(activation,0x20,u8{1});now++;Hear();TickBbscWorldPlayers();
 assert(ReadValue<u8>(activation,0x20)==0&&inserts==0);
 for(int i=0;i<4;++i){now++;Hear();TickBbscWorldPlayers();}
 assert(inserts==0&&attachments==1); // no per-frame recreation
 // A border walk advances visit WITHOUT a native load: retain model and name.
 ++peer.visit;peer.map=0x18000000;now++;Hear();TickBbscWorldPlayers();
 assert(inserts==0&&removals==0&&remote==reinterpret_cast<u64>(actor1.data()));
 // Repeated crossings in both directions must keep the SAME admitted actor.
 for(int i=0;i<8;++i){
  ++peer.visit;peer.map=i%2?0x18000000:0x1B000000;
  const u32 next=i%2?0x1B000000:0x18000000;
  if(bbsc_world_presence_local.map!=next){++bbsc_world_presence_local.visit;bbsc_world_presence_local.map=next;}
  now++;Hear();TickBbscWorldPlayers();assert(inserts==0&&removals==0&&ReadValue<u8>(activation,0x20)==0);
 }
 // An actual local load, even into an adjacent map, still recreates once.
 const int bound_before=binds;
 ++bbsc_world_native_load;++bbsc_world_presence_local.visit;
 bbsc_world_presence_local.map=0x18000000;now++;Hear();TickBbscWorldPlayers();
 assert(inserts==1&&removals==1&&remote==0);
 remote=reinterpret_cast<u64>(actor2.data());Actor(remote);now++;Hear();TickBbscWorldPlayers();
 assert(binds==bound_before+1&&inserts==1);
 // Unrelated places and loading still hide; no cross-Dream phantom.
 peer.map=0x15000000;now++;Hear();TickBbscWorldPlayers();
 assert(ReadValue<u8>(activation,0x20)==1);
 assert(!BbscWorldTaskHere(reinterpret_cast<u64>(task.data())));
 peer.map=0x1B000000;peer.phase=World::Phase::Loading;
 now++;Hear();TickBbscWorldPlayers();assert(ReadValue<u8>(activation,0x20)==1);
 // Policy is symmetric for every original border, never an NPC permission.
 for(const auto& pair:World::PlayerMapBorders){
  auto a=bbsc_world_presence_local,b=a;a.map=pair[0];b.map=pair[1];
  assert(World::SamePlayerSpace(a,b)&&World::SamePlayerSpace(b,a));
  assert(!World::SamePlace(a,b)&&!World::Routes(0x31,a,b));
  ++b.world.room;assert(!World::SamePlayerSpace(a,b));--b.world.room;
  b.phase=World::Phase::Loading;assert(!World::SamePlayerSpace(a,b));
 }
 auto a=bbsc_world_presence_local,b=a;
 a.map=0x17000000;b.map=0x1B000000;assert(!World::SamePlayerSpace(a,b)); // not transitive
 a.map=0x1D000000;b=a;assert(!World::SamePlayerSpace(a,b)); // missing ritual
 b=bbsc_world_presence_local;a=b;a.map=0x15000000;assert(!World::SamePlayerSpace(a,b));
 VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
'''


def verify_assets():
    if not (directory := os.environ.get('BBSC_TEST_MAPSTUDIO')):
        return
    import sys
    sys.path.insert(0, str(ROOT / 'tools/gamedata'))
    from msb import Msb
    borders = set()
    for path in Path(directory).glob('*_00.msb.dcx'):
        msb = Msb(path)
        area, block = map(int, path.name[1:6].split('_'))
        source = area << 24 | block << 16
        for off in msb.lists.get('PARTS_PARAM_ST', []):
            if struct.unpack_from('<i', msb.data, off + 0x14)[0] != 11:
                continue
            extra = struct.unpack_from('<q', msb.data, off + 0xB8)[0]
            area, block = msb.data[off + extra + 4:off + extra + 6]
            target = area << 24 | (0 if block == 255 else block) << 16
            borders.add(tuple(sorted((source, target))))
    header = (ROOT / 'emulator/src/core/bbsc_world_presence.h').read_text(encoding='utf-8')
    table = header[header.index('PlayerMapBorders{{'):header.index('inline bool SamePlayerSpace')]
    expected = {tuple(int(v, 16) for v in pair) for pair in re.findall(r'\{(0x[0-9A-F]+),(0x[0-9A-F]+)\}', table)}
    assert borders == expected, (borders - expected, expected - borders)
    print('PASS original 1.09 MSB: all 14 direct map borders, including Cathedral/Forest')


def main():
    verify_assets()
    compiler = os.environ.get('CXX') or life.shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    env = os.environ.copy()
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    production = life.SOURCE
    with tempfile.TemporaryDirectory(prefix='bbsc-player-border-') as tmp:
        for old in (0, 1, 2):
            life.SOURCE = production.replace('World::SamePlayerSpace(', 'World::SamePlace(') if old == 1 else production
            header = (ROOT/'emulator/src/core/bbsc_world_players.h').read_text(encoding='utf-8')
            if old == 2:
                header = header.replace('in.here && !border)', 'in.here)')
            (Path(tmp)/'core').mkdir(exist_ok=True)
            (Path(tmp)/'core/bbsc_world_players.h').write_text(header, encoding='utf-8')
            cpp, exe = Path(tmp)/'border.cpp', Path(tmp)/'border.exe'
            cpp.write_text(life.PREFIX + life.admission_source() +
                           life.function('bool BbscWorldTaskHere(u64 task)') +
                           life.function('u64 BbscWorldPlayerMesh(u64 world,u64 chr,bool& detached)') +
                           life.function('void TickBbscWorldPlayers()') + MAIN, encoding='utf-8')
            subprocess.run([compiler, '-std=c++20', '-O2', '-I', tmp, '-I', str(ROOT/'emulator/src'), str(cpp), '-o', str(exe)], check=True)
            result = subprocess.run([str(exe)], env=env)
            assert (result.returncode != 0) if old else (result.returncode == 0)
    life.SOURCE = production
    print('PASS production cross-border lifecycle; old exact-map policy fails negative control')
    # Run the complete original native renderer/FirstSync Windows trampoline
    # suite with the two peers on opposite sides of Cathedral/Forest.
    render.MAIN = render.MAIN.replace('local.map=0x15000000', 'local.map=0x18000000').replace(
        'peer=bbsc_world_presence_local;', 'peer=bbsc_world_presence_local;peer.map=0x1B000000;').replace(
        'if(invalid==4)peer.map=0x18000000;', 'if(invalid==4)peer.map=0x15000000;').replace(
        'peer.map=0x15000000;peer.alive=1;', 'peer.map=0x1B000000;peer.alive=1;')
    render.main()


if __name__ == '__main__':
    main()
