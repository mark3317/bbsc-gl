"""Production access checks and map snapshots: permissions, bounds, reload and lookup count."""
from pathlib import Path
import os, subprocess, tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
# Frozen pre-optimization reference, independent of the checkout's future HEAD.
BASELINE=r'''
u32 GetCurrentPackedMap() {
    const u64 map_list =
        image_base != 0 ? ReadValue<u64>(image_base + CurrentMapListPointerOffset, 0) : 0;
    if (map_list < 0x10000 || !HasMemoryAccess(map_list, 0x24, MemoryProt::CpuRead)) {
        return 0;
    }

    const s32 index = ReadValue<s32>(map_list, 0x20);
    const u64 map_array = ReadValue<u64>(map_list, 0x10);
    if (index < 0 || map_array < 0x10000 ||
        !HasMemoryAccess(map_array, 0x28, MemoryProt::CpuRead)) {
        return 0;
    }

    const s32 count = ReadValue<s32>(map_array, 0x18);
    const u64 entries = ReadValue<u64>(map_array, 0x20);
    if (index >= count || entries < 0x10000) {
        return 0;
    }

    constexpr u64 MapEntryStride = 0xA0;
    const u64 entry_offset = static_cast<u64>(index) * MapEntryStride;
    if (entry_offset > std::numeric_limits<u64>::max() - entries) {
        return 0;
    }
    const u64 entry = entries + entry_offset;
    if (entry > std::numeric_limits<u64>::max() - sizeof(u64)) {
        return 0;
    }
    return ReadValue<u32>(entry, sizeof(u64));
}
'''

def function(text,signature):
    start=text.index(signature+' {');end=text.index('{',start)+1;depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]
PREFIX=r'''
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>
#include <vector>
using u64=std::uint64_t;using u32=std::uint32_t;using s32=std::int32_t;
enum class MemoryProt:u32{CpuRead=1,CpuWrite=2,CpuExec=4};
struct Region{u64 start,end;u32 prot;bool committed=true;};
std::vector<Region> regions;int maps=0,queries=0;
struct Manager{
 bool IsValidMapping(u64 p,size_t n){++maps;for(auto& r:regions)if(r.committed&&p>=r.start&&p+n<=r.end&&r.prot)return true;return false;}
 s32 QueryProtection(u64 p,void** a,void** b,u32* prot){++queries;
  for(auto& r:regions)if(r.committed&&p>=r.start&&p<r.end){*a=(void*)r.start;*b=(void*)r.end;*prot=r.prot;return 0;}return -1;}
} manager;
bool available=true;
struct Memory{static Manager* Instance(){return available?&manager:nullptr;}};
u64 image_base=0;constexpr u64 CurrentMapListPointerOffset=0x80;
template<class T>void put(u64 p,size_t off,T v){std::memcpy((void*)(p+off),&v,sizeof(v));}
'''
MAIN=r'''
int main(){
 std::array<unsigned char,0x200> image{},list{},array{};std::array<unsigned char,0x300> entries{};
 const u64 root=(u64)image.data(),l=(u64)list.data(),a=(u64)array.data(),e=(u64)entries.data();
 for(auto [p,n]:{std::pair{root,image.size()},std::pair{l,list.size()},std::pair{a,array.size()},std::pair{e,entries.size()}})
  regions.push_back({p,p+n,3});
 assert(HasMemoryAccess(l,0x24,MemoryProt::CpuRead));
 maps=queries=0;assert(HasMemoryAccess(l,4,MemoryProt::CpuWrite));assert(queries==1);
#ifdef BBSC_MOD
 assert(maps==0); // a single protection+span lookup supplies the mod contract
#else
 assert(maps==1); // preserve the emulator's separate mapping contract
#endif
 assert(!HasMemoryAccess(l,0,MemoryProt::CpuRead));
 assert(!HasMemoryAccess(~u64{0}-1,4,MemoryProt::CpuRead));
 assert(!HasMemoryAccess(l+list.size()-1,4,MemoryProt::CpuRead));
 regions[1].prot=1;assert(HasMemoryAccess(l,4,MemoryProt::CpuRead));assert(!HasMemoryAccess(l,4,MemoryProt::CpuWrite));
 regions[1].prot=0;assert(!HasMemoryAccess(l,4,MemoryProt::CpuRead)); // NOACCESS or GUARD
 regions[1].prot=3;regions[1].committed=false;assert(!HasMemoryAccess(l,4,MemoryProt::CpuRead));regions[1].committed=true;
 available=false;assert(!HasMemoryAccess(l,4,MemoryProt::CpuRead));available=true;
 image_base=root;put(root,0x80,l);put(l,0x10,a);put(a,0x20,e);
 for(int i=0;i<4;++i)put<u32>(e+i*0xa0,8,0x17000000+i);
 for(s32 count=-1;count<5;++count)for(s32 index=-1;index<5;++index){
  put(l,0x20,index);put(a,0x18,count);
  queries=0;auto before=OriginalGetCurrentPackedMap();int old=queries;
  queries=0;assert(GetCurrentPackedMap()==before);assert(queries<=old);
 }
 put<s32>(l,0x20,0);put<s32>(a,0x18,1);
 queries=0;assert(OriginalGetCurrentPackedMap()==0x17000000);assert(queries==8);
 queries=0;assert(GetCurrentPackedMap()==0x17000000);assert(queries==4);
 put<u32>(e,8,0x19000000);assert(GetCurrentPackedMap()==0x19000000); // same address, new map
 put<u64>(a,0x20,~u64{0}-4);assert(GetCurrentPackedMap()==0); // overflow before entry read
 put<u64>(a,0x20,0);assert(GetCurrentPackedMap()==0);
 image_base=0;assert(GetCurrentPackedMap()==0);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-memory-hotpath-') as tmp:
    cpp=Path(tmp)/'test.cpp'
    cpp.write_text(PREFIX+function(SOURCE,'bool HasMemoryAccess(u64 address, size_t size, MemoryProt required)')+
        '\ntemplate<class T>\n'+function(SOURCE,'T ReadValue(u64 address, size_t offset)')+'\n'+
        function(BASELINE,'u32 GetCurrentPackedMap()').replace('GetCurrentPackedMap','OriginalGetCurrentPackedMap')+'\n'+
        function(SOURCE,'u32 GetCurrentPackedMap()')+'\n'+MAIN)
    env=dict(os.environ,PATH='C:/msys64/clang64/bin;'+os.environ.get('PATH',''))
    for defines in [[],['-DBBSC_MOD']]:
        exe=Path(tmp)/('mod.exe' if defines else 'native.exe')
        subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20',*defines,str(cpp),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],env=env,check=True,timeout=10)
print('PASS: access bounds/permissions, emulator/mod contracts, map reload/overflow, 8 to 4 live map lookups')
