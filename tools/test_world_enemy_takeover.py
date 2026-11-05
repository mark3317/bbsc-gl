"""Execute production enemy takeover with native ABI/alignment assertions.

Native01517200 uses VMOVAPS. Both arguments of the virtual Warp need16-byte
alignment, including the rotation array that previously faulted on both peers.
All memory here is allocated fixture memory; no live processes or saves.
"""
from pathlib import Path
import os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'emulator/src/core/bbsc_world_state.inc').read_text(encoding='utf-8')
def function(signature):
    start=SOURCE.index(signature+' {');p=SOURCE.index('{',start)+1;depth=1
    while depth:depth+=(SOURCE[p]=='{')-(SOURCE[p]=='}');p+=1
    return SOURCE[start:p]+'\n'
PREFIX=r'''
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <array>
#include <cassert>
#include <cmath>
#include <cstring>
#include <cstdint>
#include <map>
#include <set>
#include <vector>
#include "core/bbsc_world_control.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
struct BbscWorldEnemy {u32 handle=0;s32 hp=0,max=0;float x=0,y=0,z=0,heading=0;u8 fighting=0;std::array<u8,3> padding{};};
u64 image_base=0;int kills=0;int hp_calls=0,warps=0; s32 latest_hp=-1;
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
enum class MemoryProt{CpuWrite};bool HasMemoryAccess(u64 p,size_t,MemoryProt){return p>=0x10000;}
template<class T>void WriteValue(u64 p,size_t off,T v){std::memcpy(reinterpret_cast<void*>(p+off),&v,sizeof(v));}
void PS4_SYSV_ABI NativeKill(u64 chr){u32 bits;std::memcpy(&bits,reinterpret_cast<void*>(chr+0x1e1),4);assert(bits&0x200000);++kills;}
template<class T>T ReadValue(u64 p,size_t off){T out;std::memcpy(&out,reinterpret_cast<void*>(p+off),sizeof(T));return out;}
template<class T,size_t N>void Put(std::array<u8,N>& bytes,size_t offset,T v){std::memcpy(bytes.data()+offset,&v,sizeof(T));}
void PS4_SYSV_ABI NativeHp(u64,s32 hp){++hp_calls;latest_hp=hp;}
void PS4_SYSV_ABI NativeWarp(u64,float* at,float* rotation,u32 flags){
 assert((reinterpret_cast<u64>(at)&15)==0);assert((reinterpret_cast<u64>(rotation)&15)==0);
 // Same aligned loads as the native target, rather than a scalar fixture.
 __asm__ volatile("vmovaps (%0), %%xmm0\n\tvmovaps (%1), %%xmm1" : : "r"(at),"r"(rotation) : "xmm0","xmm1");
 assert(at[0]==1&&at[1]==2&&at[2]==3&&at[3]==1);
 assert(rotation[0]==0&&rotation[1]==0.5f&&rotation[2]==0&&rotation[3]==0&&flags==1);++warps;
}
bool IsEbootCodeAddress(u64 p){return p==reinterpret_cast<u64>(&NativeWarp);}
u64 GetLocalPlayerCharacter(){return 0;}
s32 GetCharacterHp(u64){return 0;}
std::vector<u64> actors;
template<class Visit>void BbscWorldCharacters(u64,Visit visit){for(u64 chr:actors)visit(chr);}
void Link(u64 offset,void* target){auto* p=reinterpret_cast<u8*>(image_base+offset);p[0]=0x48;p[1]=0xb8;const u64 address=reinterpret_cast<u64>(target);std::memcpy(p+2,&address,8);p[10]=0xff;p[11]=0xe0;}
'''
MAIN=r'''
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x2000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 Link(0x018BF9A0,reinterpret_cast<void*>(&NativeKill));
 Link(0x018BCD40,reinterpret_cast<void*>(&NativeHp));
 std::array<u8,0x400> chr{};std::array<u8,0x100> modules{},stats{};std::array<u8,0x600> vtable{};
 Put(chr,0,reinterpret_cast<u64>(vtable.data()));Put(chr,0x3b0,reinterpret_cast<u64>(modules.data()));
 Put(modules,0x20,reinterpret_cast<u64>(stats.data()));Put(stats,0xfc,s32{200});Put(vtable,0x5f8,reinterpret_cast<u64>(&NativeWarp));
 BbscWorldEnemy e;e.hp=25;e.max=100;e.x=1;e.y=2;e.z=3;e.heading=0.5f;
 for(int i=0;i<16;++i)BbscWorldTakeEnemy(reinterpret_cast<u64>(chr.data()),e,true);
 assert(hp_calls==16&&warps==16&&latest_hp==50);
 BbscWorldTakeEnemy(reinterpret_cast<u64>(chr.data()),e,false);assert(hp_calls==17&&warps==16);
 e.hp=0;BbscWorldTakeEnemy(reinterpret_cast<u64>(chr.data()),e,true);assert(latest_hp==0&&warps==16&&kills==1);
 BbscWorldState state;World::Control c;c.parts=2;c.part=1;c.epoch=7;c.sequence=4;e.handle=22;
 auto packet=std::span<const u8>{reinterpret_cast<const u8*>(&e),sizeof(e)};
 assert(!BbscWorldReceiveEnemies(state,c,packet)&&!state.enemies_ready);
 c.part=0;assert(BbscWorldReceiveEnemies(state,c,packet)&&state.enemies_ready&&state.enemies.size()==1);
 c.sequence=3;assert(!BbscWorldReceiveEnemies(state,c,packet)&&state.enemy_sequence==4);
 c.sequence=5;c.part=0;assert(!BbscWorldReceiveEnemies(state,c,packet)&&!state.enemies_ready);
 c.part=1;e.max=0;assert(!BbscWorldReceiveEnemies(state,c,packet)&&!state.enemies_ready);
 e.max=100;assert(BbscWorldReceiveEnemies(state,c,packet)&&state.enemies_ready);
 Put(chr,0x1e1,u32{0});std::array<u8,0x30> activation{};Put(activation,0x10,s32{4});Put(activation,0x14,s32{4});
 Put(chr,0x18,reinterpret_cast<u64>(activation.data()));Put(chr,0x90,u32{22});actors={reinterpret_cast<u64>(chr.data())};
 std::map<u32,u64> seeded;state.flags_ready=false;assert(BbscWorldSeedEnemies(1,state,{},0,seeded)==0);
 state.flags_ready=true;assert(BbscWorldSeedEnemies(1,state,{actors[0]},0,seeded)==0);
 assert(BbscWorldSeedEnemies(1,state,{},actors[0],seeded)==0);
 assert(BbscWorldSeedEnemies(1,state,{},0,seeded)==1&&kills==2);
 assert(BbscWorldSeedEnemies(1,state,{},0,seeded)==0&&kills==2);
 VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
'''
def main():
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-world-enemy-') as tmp:
        cpp=Path(tmp)/'enemy.cpp';exe=Path(tmp)/'enemy.exe'
        cpp.write_text(PREFIX+function('struct BbscWorldState')+';\n'+function('bool BbscWorldEnemyValid(const BbscWorldEnemy& e)')+function('bool BbscWorldReceiveEnemies(BbscWorldState& state,const World::Control& c,std::span<const u8> bytes)')+function('void BbscWorldTakeEnemy(u64 chr,const BbscWorldEnemy& e,bool position)')+function('size_t BbscWorldSeedEnemies(u64 world,const BbscWorldState& state,const std::set<u64>& players,u64 doll,std::map<u32,u64>& seeded)')+MAIN,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-O2','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS production enemy takeover: native SysV call, aligned VMOVAPS on position AND rotation, scaled HP, dead/no-warp paths')
if __name__=='__main__':main()
