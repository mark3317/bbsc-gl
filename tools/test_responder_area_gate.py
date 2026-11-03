"""Run exact native responder area eligibility: reproduce crossed bell, then patch it."""
from pathlib import Path
import os,re,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def patch(name):
    body=s.split(name+'{',1)[1].split('}',1)[0]
    return bytes(int(x,16) for x in re.findall(r'0x([0-9a-fA-F]+)',body))
# CUSA03173 1.09 0191A750..0191A8D5, including the real area->flag table lookup.
native=bytes.fromhex('554889e541574156415453488b5f604885db0f8461010000488b034889dfff90280600004c8dbb7c0200004c8da3780200004c89e184c0490f45cf448b31488d053309c203488338007521488d3dc70b0203488d15140c0203488d0d210a0203beb100000031c0e8f4ad7900488b034889dfff902806000084c04d0f45e7418b042489c1f7d90f4cc84863d14869c2ad8bdb684889c148c1e93f48c1f82c01c84863c84869c11f85eb514889c648c1ee3f48c1f82501f06bc06429c183c1ebb00183f90f0f87a20000004869f2d34d62104889f748c1ef3f48c1fe2601fe4863f64869fe676666664889fb48c1eb3f48c1ff2201df6bff0a29fe83fe02776d4869d21f85eb5148c1fa2589d7c1ef1f01d74863d74869fa6766666648c1ff2289fbc1eb1f01fb6bfb0a29fa83fa03773c89d289f689c9488d0c4948c1e104488d3d1b59e1024801cf48c1e6044801fe8b349685f67e16488d0d2b08c203488b094885c97407e836f3a7ff34014181fe40420f0018c920c1eb0231c988c85b415c415e415f5dc3')
assert native[0x173:0x179]==patch('ResponderSearchAreaRangeResult')
fixture=r'''
#include <windows.h>
#include <cassert>
#include <cstdint>
#include <cstring>
using u8=uint8_t;using u64=uint64_t;using s32=int32_t;
#define ABI __attribute__((sysv_abi))
bool flag=false, alternate=false;int seen_flag=0;
u8 ABI selected(u64){return alternate;}
u8 ABI getflag(u64,s32 id){seen_flag=id;return flag;}
void put(u64 p,u64 v){memcpy(reinterpret_cast<void*>(p),&v,8);}
void jump(u64 p,u64 dest){u8 code[]={0x48,0xb8,0,0,0,0,0,0,0,0,0xff,0xe0};memcpy(code+2,&dest,8);memcpy(reinterpret_cast<void*>(p),code,12);}
int main(){
 u64 image=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE));assert(image);
 const u8 body[]={NATIVE};auto* code=reinterpret_cast<u8*>(image+0x191A750);memcpy(code,body,sizeof(body));
 alignas(16) u8 manager[0x70]{},player[0x290]{},vtable[0x630]{};
 put(reinterpret_cast<u64>(manager)+0x60,reinterpret_cast<u64>(player));
 put(reinterpret_cast<u64>(player),reinterpret_cast<u64>(vtable));
 put(reinterpret_cast<u64>(vtable)+0x628,reinterpret_cast<u64>(&selected));
 put(image+0x553B0C8,1);put(image+0x553B0D8,1); // valid native singleton guards
 // Same native table entries as the original executable: area 210000/240000.
 *reinterpret_cast<s32*>(image+0x47301B0)=2105;
 *reinterpret_cast<s32*>(image+0x47301B0+3*48)=2405;
 jump(image+0x1399BF0,reinterpret_cast<u64>(&getflag));
 using Area=u8 ABI (*)(u64);auto area=reinterpret_cast<Area>(code);
 const u8 old_patch[]={0x7d,4,0x88,0xc1,0xeb,2};
 const u8 fixed[]={PATCH};
 for(int a:{210000,240000,-240000}){
  *reinterpret_cast<s32*>(player+0x278)=a;
  memcpy(code+0x173,old_patch,6);flag=true;seen_flag=0;
  assert(area(reinterpret_cast<u64>(manager))==0);assert(seen_flag==(a==210000?2105:2405));
  flag=false;assert(area(reinterpret_cast<u64>(manager))==1);
  memcpy(code+0x173,fixed,6);flag=true;
  assert(area(reinterpret_cast<u64>(manager))==1);
 }
 // Area source selected by the real native virtual dispatch stays intact.
 alternate=true;*reinterpret_cast<s32*>(player+0x278)=1000000;*reinterpret_cast<s32*>(player+0x27c)=240000;
 assert(area(reinterpret_cast<u64>(manager))==1);alternate=false;
 assert(area(reinterpret_cast<u64>(manager))==0); // out-of-range native bound retained
 put(reinterpret_cast<u64>(manager)+0x60,0);assert(area(reinterpret_cast<u64>(manager))==0);
}
'''.replace('NATIVE',','.join(map(str,native))).replace('PATCH',','.join(map(str,patch('ResponderSearchSignedAreaRangeResult'))))
with tempfile.TemporaryDirectory(prefix='bbsc-responder-area-') as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text('#include <initializer_list>\n'+fixture,encoding='utf-8')
 subprocess.run([os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe'),'-std=c++20','-O0',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=10)
print('Native responder area: old area-disable veto reproduced, fixed positive/negative maps, bounds/source/null guards: PASS')
