"""Exercise production NPC ownership against the observed live unloading state.

Allocated fixture actors only. No game process, saves or settings are touched.
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'emulator/src/core/bbsc_independent_world.inc').read_text(encoding='utf-8')
signature = 'void PS4_SYSV_ABI BbscWorldOwnership(u64,const GuestRegisterSnapshot* regs)'
start = source.index(signature + ' {')
end = source.index('{', start) + 1
depth = 1
while depth:
    depth += (source[end] == '{') - (source[end] == '}')
    end += 1
production = source[start:end]
prefix = r'''
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <set>
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;
#define PS4_SYSV_ABI
struct GuestRegisterSnapshot{u64 rdi=0;};
std::array<u8,0xB00> world{};std::array<std::array<u8,0x100>,3> actors{},controls{};
std::array<u16,3> words{};bool active=true,scene=true,blocks=true;int block_role=1;
std::atomic<u32> bbsc_independent_role{1};
u64 addr(auto& a){return (u64)a.data();}
template<class T>T ReadValue(u64 p,size_t off){T value;memcpy(&value,(void*)(p+off),sizeof(value));return value;}
template<class T>void WriteValue(u64 p,size_t off,T value){memcpy((void*)(p+off),&value,sizeof(value));}
bool ReadablePointer(u64 p,size_t){return p>0x10000;}
bool BbscIndependentActive(){return active;}bool BbscWorldSceneReady(){return scene;}
bool BbscWorldBlockSimulation(){return blocks;}u32 BbscWorldBlockRole(u64){return block_role;}
std::set<u64> BbscWorldPlayers(u64){return {addr(actors[1])};}
u64 BbscWorldDoll(u64){return addr(actors[2]);}
template<class F>void BbscWorldCharacters(u64,F f){for(auto& a:actors)f(addr(a));}
u64 BbscWorldOwnershipWord(u64,u64 chr){for(size_t i=0;i<3;++i)if(chr==addr(actors[i]))return (u64)&words[i];return 0;}
'''
main = r'''
int main(){
 for(size_t i=0;i<3;++i){WriteValue(addr(actors[i]),0x18,addr(controls[i]));
  WriteValue(addr(controls[i]),0x10,s32(4));WriteValue(addr(controls[i]),0x14,s32(4));}
 GuestRegisterSnapshot r;r.rdi=addr(world);
 for(bool distributed:{false,true})for(u32 role:{1u,2u}){
  blocks=distributed;bbsc_independent_role=role;block_role=1;
  // Exact live state: personal controller set backread-off; native wake has
  // already requested unloading, yet old callback keeps writing local owner1.
  WriteValue(addr(actors[0]),0x28,u8(1));WriteValue(addr(controls[0]),0x14,s32(0));
  words={1,123,1};const auto before_actor=actors;const auto before_control=controls;
  BbscWorldOwnership(0,&r);
  assert(words[0]==0xffff);assert(words[1]==123); // no remote-player mutation
  assert(actors==before_actor&&controls==before_control); // no synthetic hide or state writes
  // Already-sleeping stale ownership must be released too.
  WriteValue(addr(controls[0]),0x10,s32(0));words[0]=1;BbscWorldOwnership(0,&r);assert(words[0]==0xffff);
  // A pending unload must win even BEFORE the backread byte is set.
  WriteValue(addr(actors[0]),0x28,u8(0));WriteValue(addr(controls[0]),0x10,s32(4));
  for(s32 requested:{0,1,2,3}){WriteValue(addr(controls[0]),0x14,requested);words[0]=1;
   BbscWorldOwnership(0,&r);assert(words[0]==0xffff);}
  WriteValue(addr(controls[0]),0x14,s32(4));WriteValue(addr(controls[0]),0x20,u8(1));
  words[0]=1;BbscWorldOwnership(0,&r);assert(words[0]==0xffff);
  // Ordinary active/pending activation remains assigned by existing policy.
  WriteValue(addr(controls[0]),0x20,u8(0));words[0]=0xffff;BbscWorldOwnership(0,&r);
  assert(words[0]==(distributed||role==1?1:0xffff));assert(words[2]==1);
  block_role=2;BbscWorldOwnership(0,&r);assert(words[0]==(!distributed&&role==1?1:0xffff));
 }
 // Hidden Dream doll also cannot override native backread-off.
 WriteValue(addr(actors[2]),0x28,u8(1));words[2]=1;BbscWorldOwnership(0,&r);assert(words[2]==0xffff);
 active=false;words[0]=99;BbscWorldOwnership(0,&r);assert(words[0]==99);
 active=true;BbscWorldOwnership(0,nullptr);assert(words[0]==99);
 puts("PASS production ownership: native backread/unload/disable beats map and block ownership; active actors, doll, players and offline preserved");
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-npc-ownership-') as tmp:
    folder = Path(tmp)
    cpp, exe = folder/'fixture.cpp', folder/'fixture.exe'
    cpp.write_text(prefix + production + main, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler, '-std=c++20', '-O0', str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], check=True, env=env, timeout=15)
