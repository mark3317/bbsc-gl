"""Production altar callbacks through the real Windows trampoline; allocated memory only."""
from pathlib import Path
import os, shutil, struct, subprocess, tempfile
import test_world_travel_native as travel

ROOT=travel.ROOT
prefix=travel.PREFIX
a=prefix.index('struct GuestRegisterSnapshot{');b=prefix.index('\n',a)
prefix=prefix[:a]+'#include "core/cpu_patches.h"\nusing Core::GuestRegisterSnapshot;'+prefix[b:]
prefix=prefix.replace('#define NOMINMAX\n','').replace('#define WIN32_LEAN_AND_MEAN\n','')
prefix+='\nnamespace BbscMod {u64 EbootAddress(){return image_base;}void LogPlain(const char*){}}\n'
source=travel.SOURCE[travel.SOURCE.index('s32 bbsc_world_travel_point='):travel.SOURCE.index('void InstallBbscWorldTravel() {')]
main=r'''
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x6000000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));assert(image_base);
 bbsc_world_presence_local.world={11,99};bbsc_world_catalog_ready=true;
 bbsc_world_altars[3].entry.occupied=true;bbsc_world_altars[3].entry.ritual=36;
 bbsc_world_guest_altar_menu={bbsc_world_presence_local.world,1,3,36};
 std::array<u8,0x368> personal{};Set(personal,0x364,s32{1});
 const auto before=personal;
 // Same native CMP bytes. Execute them AFTER the production callback, then
 // consume their flags. The trampoline must neither clobber flags nor return
 // from the middle of this synthetic native frame.
 using Branch=int PS4_SYSV_ABI (*)(void*);
 const u8 branch[]={0x48,0x89,0xf8,0x83,0xb8,0x64,0x03,0,0,4,0x0f,0x94,0xc0,0x0f,0xb6,0xc0,0xc3};
 for(int continuation=0;continuation<2;++continuation){
  auto* code=reinterpret_cast<u8*>(image_base+(continuation?0x01B74F4B:0x01B75353)-3);
  std::memcpy(code,branch,sizeof(branch));code[9]=continuation?1:4;
  auto body=reinterpret_cast<Branch>(code);assert(body(personal.data())==(continuation?1:0));
  assert(Core::InstallGuestCodeHook(code+3,{code+3,7},continuation,BbscWorldAltarMenuBranch));
  assert(body(personal.data())==(continuation?0:1));assert(personal==before);
  state=3;assert(body(personal.data())==(continuation?1:0));state=6;
  ++bbsc_load_generation;assert(body(personal.data())==(continuation?1:0));--bbsc_load_generation;
 }
 // Exact native Add ENTRY prologue and exact Remove-row caller. Native Add
 // returns the original builder; its other callers must still append normally.
 auto* add=reinterpret_cast<u8*>(image_base+0x01B76150);
 const u8 add_code[]={0x55,0x48,0x89,0xe5,0x41,0x57,0x48,0xff,0x07,0x48,0x89,0xf8,0x41,0x5f,0x5d,0xc3};
 std::memcpy(add,add_code,sizeof(add_code));
 assert(Core::InstallGuestCodeHook(add,{add,6},0,BbscWorldAltarMenuItem,&bbsc_world_altar_remove_skip));
 using Add=u64 PS4_SYSV_ABI (*)(u64*);
 for(int other=0;other<2;++other){
  auto* code=reinterpret_cast<u8*>(image_base+0x01B67A70+other*0x20);
  const u8 call[]={0x48,0x83,0xec,8,0x90,0x90,0x90,0x90,0x90,0x90,0xe8,0,0,0,0,0x48,0x83,0xc4,8,0xc3};
  std::memcpy(code,call,sizeof(call));const s32 displacement=static_cast<s32>(add-(code+15));std::memcpy(code+11,&displacement,4);
  u64 count=0;assert(reinterpret_cast<Add>(code)(&count)==reinterpret_cast<u64>(&count));
  assert(count==static_cast<u64>(other));assert(bbsc_world_altar_remove_skip==0);
  state=3;assert(reinterpret_cast<Add>(code)(&count)==reinterpret_cast<u64>(&count));assert(count==other+1);state=6;
 }
 VirtualFree(reinterpret_cast<void*>(image_base),0,MEM_RELEASE);
}
'''

def check_original(path):
    data=path.read_bytes();ph=struct.unpack_from('<Q',data,32)[0];size,n=struct.unpack_from('<HH',data,54)
    segments=[struct.unpack_from('<II6Q',data,ph+i*size) for i in range(n)]
    def read(a,n):
        s=next(s for s in segments if s[0]==1 and s[3]<=a and a+n<=s[3]+s[5])
        return data[s[2]+a-s[3]:s[2]+a-s[3]+n]
    assert read(0x1B75353,7)==bytes.fromhex('83 b8 64 03 00 00 04')
    assert read(0x1B7535A,2)==bytes.fromhex('0f 84')
    assert 0x1B75360+struct.unpack('<i',read(0x1B7535C,4))[0]==0x1B75400
    assert read(0x1B74F4B,9)==bytes.fromhex('83 b8 64 03 00 00 01 75 53')
    assert read(0x1B74FA7,3)==bytes.fromhex('48 8d 05') # selected continuation overwrites RAX
    assert read(0x1B75413,3)==bytes.fromhex('48 8d 05') # layer branch overwrites RAX
    assert read(0x1B76150,6)==bytes.fromhex('55 48 89 e5 41 57')
    assert read(0x1B7633C,3)==bytes.fromhex('4c 89 f8') # Add returns R15 = input RDI
    assert read(0x1B67A7A,1)==b'\xe8'
    assert 0x1B67A7F+struct.unpack('<i',read(0x1B67A7B,4))[0]==0x1B76150
    print('PASS original native menu branches, RAX lifetimes, Remove append callsite and builder return ABI')

def run():
    compiler=os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-altar-menu-hooks-') as tmp:
        cpp=Path(tmp)/'menu.cpp';exe=Path(tmp)/'menu.exe';cpp.write_text(prefix+source+main,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN',
            '-I',str(ROOT/'emulator/src'),'-I',str(ROOT/'emulator/externals/xbyak'),
            str(cpp),str(ROOT/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        subprocess.run([str(exe)],check=True,env=env,timeout=15)
    print('PASS real production trampoline: native layer branch/continuation, personal object untouched, native Remove-only omission, host/other rows retained')
    if os.environ.get('BBSC_TEST_EBOOT'):check_original(Path(os.environ['BBSC_TEST_EBOOT']))

if __name__=='__main__':run()
