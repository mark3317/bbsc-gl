"""Production local abduction gates/predicates and read-only original EMEVD audit."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')

def function(signature):
    start = source.index(signature+' {')
    end = source.index('{', start)+1
    depth = 1
    while depth:
        depth += (source[end] == '{')-(source[end] == '}')
        end += 1
    return source[start:end]+'\n'

code = r'''
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <set>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
bool allowed=true,writable=true; s64 event=9421;
std::set<u32> flags;
std::array<u8,0x1600> global{};
bool BbscIndependentTravelAllowed(){return allowed;}
bool BbscEventFlag(u32 f){return flags.contains(f);}
u64 GetGlobalState(){return (u64)global.data();}
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
enum class MemoryProt{CpuWrite};
bool HasMemoryAccess(u64,size_t,MemoryProt){return writable;}
template<class T>T ReadValue(u64 p,size_t off){T v;memcpy(&v,(void*)(p+off),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t off,T v){memcpy((void*)(p+off),&v,sizeof(v));}
s64 BbscEventIdOf(u64){return event;}
'''
for sig in ['bool IsBbscKidnapEvent(s64 event)', 'bool IsBbscKidnapFlag(u32 flag)',
            'bool BbscKidnapDeathPending()', 'bool BbscKidnapRespawnReady()',
            'void EnableBbscKidnapEvent(u64 instance)']:
    code += function(sig)
negative = os.environ.get('BBSC_TEST_SNATCHER_OLD') == '1'
if negative:
    code = code.replace('void EnableBbscKidnapEvent(u64 instance) {',
                        'void EnableBbscKidnapEvent(u64 instance) { return;')
code += r'''
int main(){
 assert(!BbscKidnapDeathPending()); flags={9420};assert(BbscKidnapDeathPending());
 assert(!BbscKidnapRespawnReady());flags={9421};assert(BbscKidnapDeathPending());
 WriteValue<u32>(GetGlobalState(),0x1528,2412950);assert(!BbscKidnapRespawnReady());
 WriteValue<u32>(GetGlobalState(),0x1528,2802959);assert(BbscKidnapRespawnReady());
 flags.insert(9423);assert(!BbscKidnapDeathPending());
 flags={9420};allowed=false;assert(!BbscKidnapDeathPending());allowed=true;
 for(s64 e:{9421,9422,12400780,12700500})assert(IsBbscKidnapEvent(e));
 assert(!IsBbscKidnapEvent(9400)&&!IsBbscKidnapFlag(9424));
 for(s64 e:{9421,9422,12400780,12700500,9400}){
  event=e;
  alignas(8) std::array<u8,0xC0> instance{};
  alignas(8) std::array<u8,0x100> file{},ref{},ins{};
  u64 p=(u64)instance.data(),f=(u64)file.data(),r=(u64)ref.data(),i=(u64)ins.data();
  WriteValue<u64>(p,0xA8,r);WriteValue<u64>(r,8,f);WriteValue<u64>(p,0xB0,i);
  WriteValue<u64>(f,0x78,0x90);WriteValue<u64>(i,0x10,0);
  WriteValue<s32>(i,0,1003);WriteValue<s32>(i,4,6);WriteValue<u64>(i,8,4);
  WriteValue<u32>(f,0x90,256);WriteValue<u8>(p,0x78,1);
  allowed=false;EnableBbscKidnapEvent(p);assert(ReadValue<u8>(p,0x78)==1);
  allowed=true;writable=false;EnableBbscKidnapEvent(p);assert(ReadValue<s32>(i,0)==1003);
  writable=true;EnableBbscKidnapEvent(p);
  assert(ReadValue<u8>(p,0x78)==(e==9400?1:0));
  assert(ReadValue<s32>(i,0)==((e==9421||e==9422)?1001:1003));
  assert(ReadValue<u64>(i,8)==4); // next instruction/extent preserved
 }
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-snatcher-') as tmp:
    cpp, exe = Path(tmp)/'test.cpp', Path(tmp)/'test.exe'
    cpp.write_text(code, encoding='utf-8')
    compiler = os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    result = subprocess.run([str(exe)],env=env)
    if negative:
        assert result.returncode != 0, 'Old host-only gates passed the guest regression'
        print('PASS negative control: original host-only gates FAIL local abduction regression')
        raise SystemExit(0)
    result.check_returncode()

if os.environ.get('BBSC_TEST_GAME'):
    import struct
    sys.path.insert(0,str(ROOT/'tools/gamedata'))
    from emevd import Emevd
    game=Path(os.environ['BBSC_TEST_GAME'])
    common=dict(Emevd(game/'event/common.emevd.dcx').events)
    assert common[9421]==[(1003,2,bytes.fromhex('00010000cf240000')),
        (1003,6,bytes.fromhex('00010000')),(3,0,bytes.fromhex('00010000cc240000')),
        (2003,23,struct.pack('<I',2802959)),(2003,2,bytes.fromhex('cc24000000000000'))]
    assert common[9422][1]==(1003,6,bytes.fromhex('00010000'))
    assert common[9422][6]==(2002,3,struct.pack('<III',28000010,8,10000))
    assert common[9422][9]==(2003,2,struct.pack('<II',9423,1))
    for name,event in [('m24_00_00_00',12400780),('m27_00_00_00',12700500)]:
        ins=dict(Emevd(game/f'event/{name}.emevd.dcx').events)[event]
        assert ins[0]==(4,3,struct.pack('<III',2,10000,0))
        assert ins[-1]==(2003,2,struct.pack('<II',9420,1))
        assert any(b==4 and i==1 for b,i,a in ins) # native last attacker check
        assert any(b==4 and i==2 for b,i,a in ins) # native lethal HP check
    print('PASS original1.09 lethal-hit detectors, prison selector, one-time cinematic/receipt')
print('PASS production abduction: local gates, native respawn readiness, one-time/personal conditions')
