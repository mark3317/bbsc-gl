"""Original 1.09 mark return through the production Windows trampoline.

Fixture memory only; native respawn is a boundary stub. No game/save writes.
"""
from pathlib import Path
import os, struct, subprocess, tempfile

ROOT = Path(__file__).resolve().parents[1]
data = Path(os.environ.get('BBSC_TEST_EBOOT', ROOT.parents[1]/'out/exit-study.elf')).read_bytes()
ph = struct.unpack_from('<Q', data, 32)[0]
size, count = struct.unpack_from('<HH', data, 54)
segments = [struct.unpack_from('<II6Q', data, ph+i*size) for i in range(count)]
def read(a, n):
    s = next(s for s in segments if s[0] == 1 and s[3] <= a and a+n <= s[3]+s[5])
    return data[s[2]+a-s[3]:s[2]+a-s[3]+n]

assert read(0x1335d60, 6) == bytes.fromhex('55 48 89 e5 41 56')
# Original native effect walk dispatch, after effect flag bit20/vfunc checks.
assert read(0x18ff2ab, 5) == bytes.fromhex('e8 b0 6a a3 ff')
blob = read(0x1335d60, 0x1335e0a-0x1335d60)
prefix = r'''
#include <windows.h>
#include <array>
#include <atomic>
#include <cassert>
#include <cstring>
#include <string_view>
#include "core/cpu_patches.h"
using namespace Core;
using u8=uint8_t;using u64=uint64_t;using s32=int32_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
namespace MemoryProt {constexpr int CpuWrite=1;}
u64 image_base=0;int64_t bbsc_inplace_respawn_ms=0;
std::array<u8,0x100> goods{};
std::array<u8,0x400> player{},world{};
std::array<u8,0x200> events{};
std::array<u8,0x1800> global{};
u64 addr(auto& b){return reinterpret_cast<u64>(b.data());}
template<class T>T ReadValue(u64 p,size_t o){T v;std::memcpy(&v,reinterpret_cast<void*>(p+o),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t o,T v){std::memcpy(reinterpret_cast<void*>(p+o),&v,sizeof(v));}
bool ReadablePointer(u64 p,size_t){return p>0x10000;}
bool writable=true;
bool HasMemoryAccess(u64,size_t,int){return writable;}
u64 BbscParamRow(u64 p,int id,int){assert(id==1400);return p;}
bool enabled=true,quit=false,title=false,mark=true,normal=false,respawn_ok=true;
int session=3,hp=100,respawns=0,erases=0,native=0,fades=0;u64 local=0;
bool BbscSpectateEnabled(){return enabled;}
bool BbscQuitInProgress(){return quit;}
bool BbscReturningToTitle(){return title;}
s32 GetSessionState(){return session;}
u64 GetLocalPlayerCharacter(){return local;}
s32 GetCharacterHp(u64){return hp;}
u64 BbscLocalEffectNode(s32 id){return id==2101?mark:normal;}
bool BbscEraseLocalEffect(s32 id){assert(id==2101);mark=false;++erases;return true;}
bool BbscRespawnInPlace(std::string_view why){assert(why=="bold hunter mark");++respawns;if(respawn_ok)bbsc_inplace_respawn_ms=999;return respawn_ok;}
namespace BbscMod {u64 EbootAddress(){return image_base;}void LogPlain(const char*){}}
void PS4_SYSV_ABI native_mode(u64 p,s32 mode){assert(p==addr(player)&&mode==2);++native;}
int PS4_SYSV_ABI native_request(u64,u64 p){assert(p==addr(player));return 55;}
void PS4_SYSV_ABI native_fade(){++fades;}
void jump(u64 at,auto fn){u8 j[]={0x48,0xb8,0,0,0,0,0,0,0,0,0xff,0xe0};auto p=reinterpret_cast<u64>(fn);std::memcpy(j+2,&p,8);std::memcpy(reinterpret_cast<void*>(at),j,sizeof(j));}
'''
main = r'''
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 local=addr(player);WriteValue(addr(world),0x60,local);WriteValue(addr(events),0x60,u64{1});
 WriteValue(image_base,0x553e878,addr(world));WriteValue(image_base,0x553b0c8,u64{1});
 WriteValue(image_base,0x553b108,addr(events));WriteValue(image_base,0x5556678,addr(global));
 std::memcpy(reinterpret_cast<void*>(image_base+0x1335d60),original,sizeof(original));
 jump(image_base+0x1901010,native_mode);jump(image_base+0x13dede0,native_request);jump(image_base+0x1333ba0,native_fade);
 auto use=reinterpret_cast<bool PS4_SYSV_ABI (*)()>(image_base+0x1335d60);
 assert(use());assert(native==1&&fades==1&&ReadValue<int>(addr(global),0x1c)==55); // original load request
 InstallBbscHunterMarkHook();assert(bbsc_hunter_mark_ready);
 WriteValue(addr(goods),0,s32{2101});WriteValue(addr(goods),0x44,u8{3});
 auto expected=goods;expected[0x44]=0x17;
 PrepareBbscHunterMark(addr(goods));assert(ReadValue<u8>(addr(goods),0x44)==0x17);
 // Only the two permission bits change: native consumption/dialog/animation stay native.
 assert(goods==expected);goods[0x44]=3;
 bbsc_hunter_mark_ready=false;PrepareBbscHunterMark(addr(goods));assert(goods[0x44]==3);
 bbsc_hunter_mark_ready=true;writable=false;PrepareBbscHunterMark(addr(goods));assert(goods[0x44]==3);writable=true;
 WriteValue(addr(goods),0,s32{2100});PrepareBbscHunterMark(addr(goods));assert(goods[0x44]==3);
 for(int role:{3,6})for(int repeat=0;repeat<3;++repeat){
  session=role;mark=true;WriteValue(addr(global),0x1c,s32{0});int before=native;
  assert(use());assert(native==before&&fades==1&&ReadValue<int>(addr(global),0x1c)==0&&!mark&&bbsc_hunter_mark_skip==0&&bbsc_inplace_respawn_ms==0);
 }
 assert(respawns==6&&erases==6);
 // Real original continuation remains available for all excluded states.
 for(int reason=0;reason<10;++reason){
  session=3;enabled=true;quit=title=false;hp=100;local=addr(player);mark=true;normal=false;respawn_ok=true;
  if(reason==0)session=0;if(reason==1)session=4;if(reason==2)session=7;
  if(reason==3)enabled=false;if(reason==4)quit=true;if(reason==5)title=true;
  if(reason==6)hp=0;if(reason==7)mark=false;if(reason==8)normal=true;if(reason==9)respawn_ok=false;
  int before=native;use();assert(native==before+1&&bbsc_hunter_mark_skip==0);
 }
 VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
'''
code = prefix+'\nconst unsigned char original[]={'+','.join(map(str,blob))+'};\n'
code += (ROOT/'emulator/src/core/bbsc_hunter_mark.inc').read_text(encoding='utf-8')+main
compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
with tempfile.TemporaryDirectory(prefix='bbsc-hunter-mark-') as td:
    cpp=Path(td)/'mark.cpp'; exe=Path(td)/'mark.exe'
    cpp.write_text(code, encoding='utf-8')
    subprocess.run([compiler,'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
        '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),
        str(cpp),str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
    env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)],check=True,env=env)
print('PASS original mark load request reproduced; actual Windows hook, host/guest/repeated use, native fallback/offline/leave/dead/ordinary mark, exact goods permission bits')
