"""Execute production load admission: one native restart, no idle actor polling."""
import os
from pathlib import Path
import subprocess
import tempfile
import test_world_player_lifecycle as life

prefix = life.PREFIX.replace(
    'std::vector<u64> GetMultiPlayerInsTasks(){',
    'int task_queries=0,actor_queries=0;std::vector<u64> GetMultiPlayerInsTasks(){++task_queries;'
).replace('std::set<u64> BbscWorldPlayers(u64){',
          'std::set<u64> BbscWorldPlayers(u64){++actor_queries;')
setup = life.MAIN[:life.MAIN.index(' // A valid DrawModule')].replace(
    '_putenv_s("BBSC_NATIVE_NPC_SYNC_TEST","0");', '_putenv_s("BBSC_NATIVE_NPC_SYNC_TEST","1");')
main = setup + r'''
 TickBbscWorldPlayers();assert(binds==1&&inserts==0);
 auto idle=[&](){
  const int tq=task_queries,aq=actor_queries,created=inserts;
  for(int i=0;i<2000;++i){++now;Hear();TickBbscWorldPlayers();}
  assert(task_queries==tq&&actor_queries==aq&&inserts==created);
 };
 idle();
 // Local load: a retained native task is temporarily not ready.
 ++bbsc_world_presence_local.visit;++bbsc_world_native_load;++bbsc_world_player_revision;
 loading=true;TickBbscWorldPlayers();assert(inserts==0);
 loading=false;WriteValue(reinterpret_cast<u64>(task.data()),0x50,s32{4});
 TickBbscWorldPlayers();assert(inserts==0);
 WriteValue(reinterpret_cast<u64>(task.data()),0x50,s32{6});
 TickBbscWorldPlayers();assert(inserts==1&&removals==1&&clears==1);
 remote=reinterpret_cast<u64>(actor2.data());Actor(remote);
 idle(); // native creation completes; no watchdog/recreation/model scans
 // A resident's side also admits a returning traveller exactly once.
 peer.map=0x18000000;++peer.visit;Hear();++bbsc_world_player_revision;
 TickBbscWorldPlayers();assert(inserts==1);
 peer.map=0x15000000;++peer.visit;Hear();++bbsc_world_player_revision;
 task_present=false;TickBbscWorldPlayers();assert(inserts==1);
 task_present=true;UpdateNativePlayers();TickBbscWorldPlayers();assert(inserts==2&&removals==2);
 remote=reinterpret_cast<u64>(actor1.data());Actor(remote);idle();
 // Walking over an adjacent map border is not another load/admission.
 bbsc_world_presence_local.map=peer.map=0x18000000;
 ++bbsc_world_presence_local.visit;++bbsc_world_native_load;++peer.visit;
 Hear();++bbsc_world_player_revision;TickBbscWorldPlayers();assert(inserts==3);
 remote=reinterpret_cast<u64>(actor2.data());Actor(remote);
 for(int i=0;i<8;++i){
  peer.map=i%2?0x18000000:0x1B000000;++peer.visit;
  Hear();++bbsc_world_player_revision;TickBbscWorldPlayers();assert(inserts==3&&remote);
 }
 idle();
 // A failed native admission is bounded; time alone never starts another.
 ++peer.visit;Hear();++bbsc_world_player_revision;task_present=false;
 TickBbscWorldPlayers();now+=15001;TickBbscWorldPlayers();idle();
 task_present=true;TickBbscWorldPlayers();assert(inserts==3);
 puts("PASS native load/reunion: one restart, pending native task, no repeated creation or idle actor polling, bounded admission");
}
'''

with tempfile.TemporaryDirectory(prefix='bbsc-player-load-once-') as td:
    cpp=Path(td)/'once.cpp';exe=Path(td)/'once.exe'
    cpp.write_text(prefix+life.admission_source()+life.player_functions()+main,encoding='utf-8')
    compiler=os.environ.get('CXX',r'C:/msys64/clang64/bin/clang++.exe')
    env=dict(os.environ,PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH',''))
    subprocess.run([compiler,'-std=c++20','-O2','-I',str(life.ROOT/'emulator/src'),str(cpp),'-o',str(exe)],env=env,check=True)
    subprocess.run([str(exe)],env=env,check=True)
