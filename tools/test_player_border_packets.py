"""Run actual native send filters: player-only records across adjacent maps."""
import os
from pathlib import Path
import subprocess
import tempfile
import test_world_blocks as blocks
import test_independent_native as native

ROOT = blocks.ROOT
MAIN = r'''
int main(){
 auto& p=bbsc_world_presence_local;p.world={11,99};p.phase=World::Phase::Playing;
 p.map=0x18000000;p.sequence=p.visit=1;p.alive=1;
 auto peer=p;peer.map=0x1B000000;bbsc_world_presence_book.Bind(p.world,11);
 assert(bbsc_world_presence_book.Hear(22,p.world,peer,now));
 bbsc_world_blocks_active=true;bbsc_world_block_inventory_ready=true;
 bbsc_world_block_inventory_load=1;bbsc_world_block_scope=World::ScopeOf(p);
 auto& l=bbsc_world_block_local[p.map];l.load=1;l.applied_epoch=1;
 auto& lease=bbsc_world_block_views[{World::BlockScope(bbsc_world_block_scope,p.map),p.map}].lease;
 lease.owner=self;lease.epoch=1;
 bbsc_world_block_handles[2001]=p.map;bbsc_world_block_players[1001]=self;
 put(player,0x90,u32(1001));
 for(u32 role:{1u,2u})for(u32 ch:{4u,5u,0x3Du,0x41u}){
  bbsc_independent_role=role;
  const size_t stride=ch==5?8:ch==0x3D?100:ch==0x41?24:12;
  std::array<u8,200> wire{};put(wire,0,u32(1001));put(wire,stride,u32(2001));
  const auto before=wire;
  GuestRegisterSnapshot r{};r.rsi=100;r.rdx=ch;r.rcx=addr(wire);r.r8=2*stride;
  bbsc_independent_send_skip=0;BbscWorldPacketSend(0,&r);
  assert(!bbsc_independent_send_skip&&ReadValue<u32>(r.rcx,0)==1001);
  assert(ReadValue<u32>(r.rcx,stride)==(ch==0x41?0xfffffffeu:0xffffffffu));
  assert(wire==before); // no mutation of the game's producer queue
  // NPC-only record is rejected even if WE own that NPC's block.
  put(wire,0,u32(2001));r.rcx=addr(wire);r.r8=stride;
  bbsc_independent_send_skip=0;BbscWorldPacketSend(0,&r);assert(bbsc_independent_send_skip);
 }
 // Original 100-byte channel34 handle + draw/display/backread groups.
 std::array<u8,100> groups{};put(groups,0,u32(1001));
 for(size_t at=4;at<groups.size();++at)groups[at]=u8(at);
 const auto before=groups;
 GuestRegisterSnapshot r{};r.rsi=100;r.rdx=0x34;r.rcx=addr(groups);r.r8=100;
 bbsc_independent_send_skip=0;BbscWorldPacketSend(0,&r);
 assert(!bbsc_independent_send_skip&&r.rcx==addr(groups)&&groups==before);
 put(groups,0,u32(2001));bbsc_independent_send_skip=0;BbscWorldPacketSend(0,&r);assert(bbsc_independent_send_skip);
 put(groups,0,u32(1001));r.r8=99;bbsc_independent_send_skip=0;BbscWorldPacketSend(0,&r);assert(bbsc_independent_send_skip);
 r.r8=100;
 for(int invalid=0;invalid<3;++invalid){
  auto changed=peer;++changed.sequence;
  if(invalid==0)changed.phase=World::Phase::Loading;
  if(invalid==1)changed.map=0x15000000;
  if(invalid==2)changed.map=0x20000000; // no transitive border admission
  ++peer.sequence;changed.sequence=peer.sequence;assert(bbsc_world_presence_book.Hear(22,p.world,changed,now));
  bbsc_independent_send_skip=0;BbscWorldPacketSend(0,&r);assert(bbsc_independent_send_skip);
 }
}
'''


def main():
    prefix = blocks.PREFIX.replace('bool BbscWorldSendHere(u32 peer){return peer==22;}', native.function('bool BbscWorldSendHere(u32 peer)')).replace(
        'bool BbscWorldPlayerSendHere(u32){return false;}', native.function('bool BbscWorldPlayerSendHere(u32 peer)'))
    prefix += r'''
thread_local u8 bbsc_independent_send_depth=0;
thread_local u32 bbsc_world_initial_sending=0;
thread_local u64 bbsc_world_initial_fingerprint=0;
std::atomic<u32> bbsc_independent_owner{0};
'''
    source = (ROOT/'emulator/src/core/bbsc_world_blocks.inc').read_text(encoding='utf-8')
    source = source.replace('reinterpret_cast<Serialize>(image_base+0x0190E750)', 'MockSerialize').replace(
        'reinterpret_cast<Apply>(image_base+0x0190E8B0)', 'MockApply')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    env = os.environ.copy();env['PATH'] = str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    with tempfile.TemporaryDirectory(prefix='bbsc-player-packets-') as tmp:
        for old in (False, True):
            cpp, exe = Path(tmp)/'packets.cpp', Path(tmp)/'packets.exe'
            current = prefix.replace('World::SamePlayerSpace(', 'World::SamePlace(') if old else prefix
            cpp.write_text(current+source+native.function('void PS4_SYSV_ABI BbscWorldPacketSend(u64,const GuestRegisterSnapshot* regs)')+MAIN, encoding='utf-8')
            subprocess.run([compiler,'-std=c++20','-O2','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)], check=True)
            result = subprocess.run([str(exe)], env=env)
            assert (result.returncode != 0) if old else (result.returncode == 0)
    print('PASS actual player send filters both roles: native groups/mixed animation/status/HP/position, NPC/loading/unrelated/malformed isolation; old exact-map send policy fails')


if __name__ == '__main__':
    main()
