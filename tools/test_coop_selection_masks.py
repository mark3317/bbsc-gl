"""Execute both native slot-mask blocks with the production Hunters patches."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
search = "83bdf4feffff000f94c083bd00ffffff00410f94c088c24408c2baffffffffbe7ffff7ff0f45f283bd0cffffff000f94c183bd18ffffff000f94c389f781e7fffefbff88ca08da0f45fe81e7fffffbff08d90f45fe4189ff4181e7ffff1fff4408c0440f45ff"
select = "83bd64ffffff000f94c083bd70ffffff00410f94c088c24408c2baffffffffbe7ffff7ff0f45f283bd7cffffff000f94c1837d88000f94c389f781e7fffefbff88ca08da0f45fe81e7fffffbff08d90f45fe89fb81e3ffff1fff4408c00f45df"
fixture = r'''
#include <windows.h>
#include <cassert>
#include <cstring>
#include <vector>
#include <cstdio>
#include "core/bbsc_patch_tables.h"
using namespace Core::Bbsc::PatchTables;
using u32=std::uint32_t;
void put(std::vector<u8>& b,int n){for(int i=0;i<4;++i)b.push_back(u32(n)>>(i*8));}
int main(){
 auto image=(u8*)VirtualAlloc(nullptr,0x1900000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(image);
 const std::vector<u8> blocks[]={{SEARCH},{SELECT}};
 const int starts[]={0x187302b,0x1879363};
 const int slots[2][4]={{-0x10c,-0x100,-0xf4,-0xe8},{-0x9c,-0x90,-0x84,-0x78}};
 using Fn=u32(*)(const int*);
 Fn funcs[2];
 for(int path=0;path<2;++path){
  // Windows ABI bridge: preserve nonvolatile registers, set native frame locals.
  std::vector<u8> b={0x55,0x53,0x41,0x57,0x48,0x81,0xec,0x40,1,0,0,
                     0x48,0x8d,0xac,0x24,0x20,1,0,0};
  for(int i=0;i<4;++i){b.insert(b.end(),{0x8b,0x41,u8(i*4),0x89,0x85});put(b,slots[path][i]);}
  auto entry=image+starts[path]-0x100;
  b.push_back(0xe9);put(b,int((image+starts[path])-(entry+b.size()+4)));
  memcpy(entry,b.data(),b.size());funcs[path]=(Fn)entry;
  memcpy(image+starts[path],blocks[path].data(),blocks[path].size());
  std::vector<u8> end=path==0?std::vector<u8>{0x44,0x89,0xf8}:std::vector<u8>{0x89,0xd8};
  const u8 tail[]={0x48,0x81,0xc4,0x40,1,0,0,0x41,0x5f,0x5b,0x5d,0xc3};
  end.insert(end.end(),std::begin(tail),std::end(tail));
  memcpy(image+starts[path]+blocks[path].size(),end.data(),end.size());
 }
 // Baseline, existing ordinary-coop edits only, then all production Hunters edits.
 u32 baseline[2][256]{},ordinary[2][256]{};
 for(int stage=0;stage<3;++stage){
  if(stage)for(const auto& edit:WideEdits){
   if(edit.group!=Group::Hunters)continue;
   bool covenant=strstr(edit.name,"Covenant")!=nullptr;
   if(covenant!=(stage==2))continue;
   assert(memcmp(image+edit.site,edit.original.data(),edit.original.size())==0);
   memcpy(image+edit.site,edit.replacement.data(),edit.replacement.size());
  }
  for(int path=0;path<2;++path)for(int combo=0;combo<256;++combo){
   int state[4];for(int i=0;i<4;++i)state[i]=(combo>>(2*i))&3;
   u32 mask=funcs[path](state);
   bool blocked=state[0]!=0&&state[1]!=0;
   if(stage==0){
    baseline[path][combo]=mask;
    assert((mask&0xe80080u)==(blocked?0u:0xe80080u));
   }else if(stage==1){
    ordinary[path][combo]=mask;
    assert((mask&0xe00000u)==(blocked?0u:0xe00000u)); // reproduces the residual defect
    assert((mask&0x80080u)==0x80080u);
   }else{
    assert((mask&0xe80080u)==0xe80080u);
    assert((mask&~0xe80080u)==(baseline[path][combo]&~0xe80080u)); // PvP and every other bit unchanged
    assert((mask^ordinary[path][combo])==(blocked?0xe00000u:0u));
   }
  }
 }
 puts("PASS: both exact native selectors, 256 slot combinations, baseline defect and production fix; non-coop masks preserved");
}
'''.replace("SEARCH", ",".join(hex(b) for b in bytes.fromhex(search))).replace("SELECT", ",".join(hex(b) for b in bytes.fromhex(select)))
with tempfile.TemporaryDirectory(prefix="bbsc-coop-masks-") as tmp:
    cpp, exe = Path(tmp)/"test.cpp", Path(tmp)/"test.exe"
    cpp.write_text(fixture, encoding="utf-8")
    subprocess.run([os.environ.get("CXX", "C:/msys64/clang64/bin/clang++.exe"), "-std=c++20", "-O0", "-DNOMINMAX", "-I", str(root/"emulator/src"), str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=10, env={**os.environ, "PATH":"C:/msys64/clang64/bin;"+os.environ.get("PATH", "")})
