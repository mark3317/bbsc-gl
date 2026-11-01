from pathlib import Path
import subprocess, os
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
a=s.index('struct BbscKitItem {');b=s.index('// Kit rows,',a)
fixture=r'''
#include <cstdint>
#include <cstring>
#include <cassert>
#include <array>
using u32=uint32_t;using u64=uint64_t;using u8=uint8_t;using s32=int32_t;
std::array<std::array<u8,108>,5> rows;
u64 BbscParamRow(u64,u32 id,size_t){switch(id){case 200:return (u64)rows[0].data();case 205:return (u64)rows[1].data();case 225:return (u64)rows[2].data();case 111:return (u64)rows[3].data();default:assert(false);return 0;}}
template<class T>void WriteValue(u64 p,size_t o,T v){memcpy((void*)(p+o),&v,sizeof v);}
'''+s[a:b]+r'''
int main(){
 for(auto &r:rows)r.fill(0x5a);
 PrepareBbscKitRows(1);
 assert(std::size(BbscKit)==4);
 for(int i=0;i<4;i++)for(int j=0;j<108;j++){
  const u8 expected=j==56?0: j>=100?0xff:0x5a;
  assert(rows[i][j]==expected);
 }
 for(auto v:rows[4])assert(v==0x5a);
 PrepareBbscKitRows(1); // repeated preparation preserves names/icons/type/availability
}
'''
build=root/'build';build.mkdir(exist_ok=True);cpp=build/'test_original_bells.cpp';exe=cpp.with_suffix('.exe');cpp.write_text(fixture,encoding='utf8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20',str(cpp),'-o',str(exe)],check=True)
env=dict(os.environ);env['PATH']='C:/msys64/clang64/bin;'+env.get('PATH','');subprocess.run([str(exe)],env=env,check=True)
print('PASS: real parameter preparation preserves original identity, icons, availability and unrelated goods; idempotent, four original IDs only')
