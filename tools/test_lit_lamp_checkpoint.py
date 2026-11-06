"""Production checkpoint + original native lamp activation, allocated memory only."""
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a = source.index('void RememberBbscLitLampCheckpoint(u64 instance) {')
b = source.index('\nvoid PS4_SYSV_ABI BbscEventBank2003Hook', a)
production = source[a:b]
assert 'if (bbsc_event_run.ours && LampTravel::IsLampActivationEvent(bbsc_event_run.event))\n        RememberBbscLitLampCheckpoint(instance);' in source
if os.environ.get('BBSC_TEST_CHECKPOINT_OLD'):
    production = production.replace('void RememberBbscLitLampCheckpoint(u64 instance) {',
                                    'void RememberBbscLitLampCheckpoint(u64 instance) { return;')

code = r'''
#define NOMINMAX
#include <windows.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <cstring>
#include <limits>
#include "core/bbsc_world_lamp_points.h"
#include "core/bbsc_lamp_travel_data.h"
using namespace Core::Bloodborne;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define BBSC_TIMELINE(...)
#define ABI __attribute__((sysv_abi))
bool allowed=true,writable=true; s32 role=6,hp=594;s64 event=7100;
u32 map=0x1b000000;constexpr u32 BbscDreamStateMap=0x15000000;
u64 image=0;
std::array<u8,0x1800> global{};
bool BbscIndependentTravelAllowed(){return allowed;}
int shared_lit=0; s32 shared_point=0;
void QueueBbscSharedLampCheckpoint(s32 point){++shared_lit;shared_point=point;}
bool ReadablePointer(u64 p,size_t){return p>=0x10000;}
enum class MemoryProt{CpuWrite};
bool HasMemoryAccess(u64,size_t,MemoryProt){return writable;}
s32 GetSessionState(){return role;} u32 GetCurrentPackedMap(){return map;}
u64 GetGlobalState(){return (u64)global.data();}
u64 GetLocalPlayerCharacter(){return 0x10000;}s32 GetCharacterHp(u64){return hp;}
s64 BbscEventIdOf(u64){return event;}
namespace Chalice {bool IsMap(u32 m){return (m>>24)==29;}}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t o,T v){memcpy((void*)(p+o),&v,sizeof(v));}
int lit=0;
void ABI NativeLight(s32 entity,u64,s32 value){assert(entity>0&&value==1);++lit;}
std::array<s32,4> point_data{};
void ABI NativePoint(u64 desc,s32 point){point_data[1]=point;point_data[2]=101163;WriteValue<u64>(desc,0x38,(u64)point_data.data());}
void Link(u64 off,void* target){u8* p=(u8*)(image+off);p[0]=0x48;p[1]=0xb8;memcpy(p+2,&target,8);p[10]=0xff;p[11]=0xe0;}
'''+production

native = ''
if os.environ.get('BBSC_TEST_EBOOT'):
    # This is the original function called by EMEVD2003[52], including all
    # three gates that skip its checkpoint write. Only lookup/lighting are mocks.
    with open(os.environ['BBSC_TEST_EBOOT'], 'rb') as f:
        f.seek(0x131e4a0+0x4000)
        blob = f.read(0x109)
    assert blob[:8] == bytes.fromhex('554889e541574156')
    native = 'const unsigned char native[]={'+','.join(map(str,blob))+'};memcpy((void*)(image+0x131e4a0),native,sizeof(native));\n'
    # RIP-relative data targets independently decoded from the native bytes.
    def rip(at, length, displacement):
        return 0x131e4a0+at+length+struct.unpack_from('<i',blob,at+displacement)[0]
    cookie = rip(0x14,7,3)
    stateptr = rip(0x22,7,3)
    manager = rip(0x30,7,3)
    assert stateptr == rip(0x75,7,3)
    native += f'WriteValue<u64>(image,{cookie},(u64)cookie.data());WriteValue<u64>(image,{stateptr},GetGlobalState());WriteValue<u64>(image,{manager},(u64)manager.data());\n'

code += r'''
int main(){
 image=(u64)VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(image);
 std::array<u8,0x130> manager{},remote{};std::array<u64,1> cookie{123};
 WriteValue<u64>(GetGlobalState(),0x16f8,(u64)remote.data());
 Link(0x1f26b40,(void*)&NativePoint);Link(0x146c5a0,(void*)&NativeLight);
''' + native + r'''
 std::array<u8,0xC0> instance{};std::array<u8,0x20> instruction{};
 std::array<u8,0x100> file{},ref{};std::array<u8,4> args{};
 const u64 p=(u64)instance.data(),i=(u64)instruction.data(),f=(u64)file.data();
 WriteValue<u64>(p,0xB0,i);WriteValue<s32>(i,0,2003);WriteValue<s32>(i,4,52);WriteValue<u64>(i,8,4);
 WriteValue<u64>(p,0xA8,(u64)ref.data());WriteValue<u64>((u64)ref.data(),8,f);
 WriteValue<u64>(f,0x78,0x90);WriteValue<u64>(i,0x10,0);
 auto checkpoint=[&](){return ReadValue<s64>(GetGlobalState(),0x1528);};
 auto old=[&](){WriteValue<s64>(GetGlobalState(),0x1528,(s64{101163}<<32)|2402950);};
 auto setentity=[&](s32 e){WriteValue<s32>((u64)args.data(),0,e);WriteValue<s32>(f,0x90,e);};
 for(s32 r:{3,6})for(bool inlined:{false,true}){
  role=r;WriteValue<s32>((u64)manager.data(),0x124,role);
  WriteValue<u8>(GetGlobalState(),0x1592,role==3);
  WriteValue<s32>((u64)remote.data(),0x98,0); // native remote-member gate
  WriteValue<u64>(p,0xB8,inlined?(u64)args.data():0);
  for(const auto& lamp:LampPoints){
   if(lamp.packed_map==BbscDreamStateMap)continue;
   map=lamp.packed_map;event=7100;setentity(lamp.warp_point-1000);old();
   const int offered=shared_lit;
   RememberBbscLitLampCheckpoint(p);
   assert(shared_lit==offered+1&&shared_point==lamp.warp_point);
   assert(checkpoint()==((s64{101163}<<32)|lamp.warp_point));
   // Relighting the same lamp is idempotent; no timer or nearest-lamp fallback.
   RememberBbscLitLampCheckpoint(p);assert((s32)checkpoint()==lamp.warp_point);
   assert(shared_lit==offered+2);
  }
  map=0x1d000000;event=12907010;
  for(s32 n=0;n<10;++n){setentity(2901950+n);old();RememberBbscLitLampCheckpoint(p);assert((s32)checkpoint()==2902950+n);}
  map=0x1b000000;event=7100;setentity(2701950);
'''
if native:
    code += r'''
  using Activate=void ABI (*)(u64,s32);
  auto activate=(Activate)(image+0x131e4a0);
  old();activate(0,2701950);assert((s32)checkpoint()==2402950); // old behavior
  RememberBbscLitLampCheckpoint(p);activate(0,2701950);
  assert((s32)checkpoint()==2702950&&lit>0); // native cannot undo fixed point
'''
code += r'''
  auto rejected=[&](){old();const int before=shared_lit;RememberBbscLitLampCheckpoint(p);assert((s32)checkpoint()==2402950&&shared_lit==before);};
  allowed=false;rejected();allowed=true;writable=false;rejected();writable=true;
  hp=0;rejected();hp=594;WriteValue<u8>(GetGlobalState(),8,1);rejected();WriteValue<u8>(GetGlobalState(),8,0);
  event=7000;rejected();event=7200;rejected();event=7100;
  map=0x18000000;rejected();map=0x1b000000;
  setentity(-1);rejected();setentity(2147483647);rejected();setentity(2701950);
  WriteValue<s32>(i,4,2);rejected();WriteValue<s32>(i,4,52);
  WriteValue<u64>(i,8,8);rejected();WriteValue<u64>(i,8,4);
 }
 // Offline/invasions/ended sessions and remote discovery never select a point.
 for(s32 r:{0,2,7}){role=r;old();RememberBbscLitLampCheckpoint(p);assert((s32)checkpoint()==2402950);}
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-lit-checkpoint-') as tmp:
    cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe'
    cpp.write_text(code,encoding='utf-8')
    compiler=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
    env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    result=subprocess.run([str(exe)],env=env)
    if os.environ.get('BBSC_TEST_CHECKPOINT_OLD'):
        assert result.returncode!=0,'Old behavior passed the regression'
        print('PASS negative control: missing checkpoint write FAILS regression')
        sys.exit(0)
    result.check_returncode()
print('PASS production lit checkpoint: both roles, all catalog lamps, ten dungeon points, inline/file arguments, unrelated events, map/loading/dead/write/session guards'+('; original native activation gates' if native else ''))

if os.environ.get('BBSC_TEST_GAME'):
    sys.path.insert(0,str(ROOT/'tools/gamedata'))
    from emevd import Emevd
    game=Path(os.environ['BBSC_TEST_GAME'])
    for name,event in [('common',7100),('m29',12907010)]:
        evd=Emevd(game/f'event/{name}.emevd.dcx')
        ins=dict(evd.events)[event]
        step=next(n for n,(bank,cmd,args) in enumerate(ins) if (bank,cmd)==(2003,52))
        assert ins[step][2]==bytes(4)
        assert ins[step-1]==(1001,1,struct.pack('<I',32))
        assert ins[step-2]==(2004,14,struct.pack('<IIII',10000,0,101170,0))
        # Native substitutions place the second event parameter (lamp entity)
        # in the single2003[52] argument, not the lighting request flag.
        d=evd.data
        for n in range(struct.unpack_from('<q',d,0x10)[0]):
            row=struct.unpack_from('<q',d,0x18)[0]+n*0x30
            if struct.unpack_from('<q',d,row)[0]!=event:continue
            count,offset=struct.unpack_from('<qq',d,row+24)
            params=[struct.unpack_from('<qqqii',d,struct.unpack_from('<q',d,0x58)[0]+offset+j*32) for j in range(count)]
            assert any(p[:4]==(step,0,4,4) for p in params),params
    print('PASS original7100/12907010: local request, activation animation101170,32frames, substituted lamp entity in2003[52]')
