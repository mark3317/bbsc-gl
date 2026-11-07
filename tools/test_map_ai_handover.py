"""Map-state lease changes must never overwrite per-NPC native AI grants.

Fixture memory only; optionally executes original1.09 ownership predicate.
"""
from pathlib import Path
import os
import struct
import subprocess
import tempfile
import test_independent_native as native

ROOT = Path(__file__).resolve().parents[1]
PREFIX = r'''
#include <windows.h>
#include <atomic>
#include <cassert>
#include <cstdio>
#include <set>
#include <mutex>
#include "core/bbsc_native_ai_admission.h"
#include "core/bbsc_world_control.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define BBSC_TIMELINE(...)
#define LOG_WARNING(...)
struct GuestRegisterSnapshot{u64 rdi=0;};
enum class MemoryProt{CpuWrite};
bool active=true;int reads=0,writes=0,visits=0;
std::mutex bbsc_world_presence_mutex;
std::array<std::atomic<u8>,32> bbsc_native_ai_roles{};
std::array<World::Scope,32> bbsc_native_ai_scopes{};
void BbscWorldCacheAiBlock(u64,u32){} // full publication/native decision tested separately
std::atomic<u32> bbsc_independent_owner{0},bbsc_independent_role{0};
std::array<u8,0xB00> world{};
std::array<u8,0x170> image{};
u64 image_base=(u64)image.data();constexpr u64 CandidateLocalStatePointerOffset=8;
std::array<u8,0x110> sync{};std::array<u8,0x40> table{};
std::array<u16,6> words{};
std::array<u8,0x160> block{};
std::array<std::array<u8,0x38>,6> entries{};
std::array<std::array<u8,0x400>,6> actors{};
std::array<std::array<u8,0x100>,6> controls{};
std::array<u8,0x38> players{};
u64 addr(auto& a){return (u64)a.data();}
template<class T>T ReadValue(u64 p,size_t off){++reads;T v;memcpy(&v,(void*)(p+off),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t off,T v){++writes;memcpy((void*)(p+off),&v,sizeof(v));}
bool ReadablePointer(u64 p,size_t){return p>0x10000;}
bool HasMemoryAccess(u64 p,size_t n,MemoryProt){return ReadablePointer(p,n);}
bool BbscIndependentActive(){return active;}
bool BbscWorldSceneReady(){return true;}
bool BbscWorldBlockSimulation(){return false;}
u32 BbscWorldBlockRole(u64){assert(false);return 0;}
u64 GetLocalPlayerCharacter(){return addr(actors[0]);}
u64 BbscWorldDoll(u64){return 0;}
// Count production traversal entry without replacing its real actor table walk.
void CountVisit(){++visits;}
'''
MAIN = r'''
int main(){
 WriteValue(image_base,CandidateLocalStatePointerOffset,addr(world));
 WriteValue(addr(world),0xA40,addr(sync));WriteValue(addr(sync),8,u32(1));
 WriteValue(addr(sync),0x10,addr(table));WriteValue(addr(table),0x10,u32(words.size()));
 WriteValue(addr(table),0x18,addr(words));words.fill(0xffff);words[2]=1;
 auto snapshot=words;int r=reads,w=writes;
 for(auto owner:{11u,22u,33u,0u})for(auto role:{0u,1u,2u}){
  BbscWorldPublishOwner(owner,role,true);
  for(int i=0;i<2000;++i)BbscWorldPublishOwner(owner,role,false);
  assert(words==snapshot&&visits==0&&reads==r&&writes==w);
 }
 NATIVE_CHECK
 words[2]=0xffff;BbscWorldPublishOwner(22,1,true);
 NATIVE_FOLLOWER_CHECK
 assert(visits==0&&reads==r&&writes==w);
 puts("PASS production map commits: all owners/roles/loading/return/new visit, zero NPC scans/reads/writes, native grant unchanged");
}
'''

# Count entry to the existing production walker, retaining its real traversal.
source = native.NATIVE
start = source.index('template<class Visit>')
end = source.index('std::set<u64> BbscWorldPlayers', start)
production = source[start:end].replace('if(!ReadablePointer(world,0x30)) return;',
                                      'CountVisit();if(!ReadablePointer(world,0x30)) return;')
production += ''.join(native.function(sig) for sig in [
    'std::set<u64> BbscWorldPlayers(u64 world)',
    'u64 BbscWorldOwnershipWord(u64 world,u64 chr)',
    'void PS4_SYSV_ABI BbscWorldOwnership(u64,const GuestRegisterSnapshot* regs)',
    'void BbscWorldPublishOwner(u32 owner,u32 role,bool new_visit)'])
if os.environ.get('BBSC_MAP_AI_NEGATIVE') == '1':
    # Reintroduce map-commit grant revocation and require the fixture to detect it.
    production = production.replace('const u32 previous_owner=',
        'WriteValue<u16>((u64)words.data(),4,u16{0xffff});const u32 previous_owner=')

main = MAIN
if os.environ.get('BBSC_TEST_EBOOT'):
    data = Path(os.environ['BBSC_TEST_EBOOT']).read_bytes()
    ph = struct.unpack_from('<Q', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 54)
    for i in range(count):
        typ, _, off, va, _, fs, _, _ = struct.unpack_from('<II6Q', data, ph+i*size)
        if typ == 1 and va <= 0x191aae0 and 0x191ab32 <= va+fs:
            code = data[off+0x191aae0-va:off+0x191ab32-va]
            break
    else:
        raise AssertionError('Original ownership predicate not found')
    assert code[:7] == bytes.fromhex('48 8b 87 40 0a 00 00')
    setup = ('auto* executable=VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);'
             'assert(executable);const u8 code[]={'+','.join(map(str, code))+'};'
             'memcpy(executable,code,sizeof(code));'
             'using Owns=bool PS4_SYSV_ABI (*)(u64,s32);auto owns=(Owns)executable;')
    main = main.replace('int main(){', 'int main(){'+setup)
    main = main.replace('NATIVE_CHECK', 'assert(owns(addr(world),2));')
    main = main.replace('NATIVE_FOLLOWER_CHECK', 'assert(!owns(addr(world),2));')
else:
    main = main.replace('NATIVE_CHECK', '').replace('NATIVE_FOLLOWER_CHECK', '')

with tempfile.TemporaryDirectory(prefix='bbsc-map-ai-') as tmp:
    cpp, exe = Path(tmp)/'fixture.cpp', Path(tmp)/'fixture.exe'
    cpp.write_text(PREFIX+production+main, encoding='utf8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    env = dict(os.environ, PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH', ''),
               BBSC_NATIVE_NPC_SYNC_TEST='1')
    subprocess.run([compiler, '-std=c++20', '-Wall', '-Wextra', '-Werror', '-I',
                    str(ROOT/'emulator/src'), str(cpp), '-o', str(exe)], check=True, env=env)
    result=subprocess.run([str(exe)], env=env, timeout=15)
    if os.environ.get("BBSC_MAP_AI_NEGATIVE")=="1":
        assert result.returncode!=0,"Map commit grant overwrite was not detected"
        print("PASS negative control: map commit must not revoke discoverer grant")
    else:result.check_returncode()
    if os.environ.get('BBSC_TEST_EBOOT'):
        print('PASS original 1.09 native authority predicate: map commit preserves per-NPC grants')
