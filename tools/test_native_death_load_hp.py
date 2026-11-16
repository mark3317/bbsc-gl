"""Production death-load preparation + original 1.09 constructor HP branch, isolated memory."""
from pathlib import Path
import os,struct,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(sig):
 a=source.index(sig+' {');b=source.index('{',a)+1;d=1
 while d:d+=(source[b]=='{')-(source[b]=='}');b+=1
 return source[a:b]
elf=Path(os.environ.get('BBSC_TEST_EBOOT',str(ROOT.parents[1]/'out/ngplus-member-left/eboot.elf'))).read_bytes()
def raw(a,b):return elf[a+0x4000:b+0x4000]
gate=raw(0x19395bc,0x19395d4)
assert gate[:3]==bytes.fromhex('488d1d') and gate[10:16]==bytes.fromhex('807870007448')
assert gate[-5]==0xe8 and 0x19395d4+struct.unpack('<i',gate[-4:])[0]==0x18fd460
heal=raw(0x18fd497,0x18fd4ab)
assert heal.hex()=='498b86b0030000488b40208bb0fc0000004c89f7'
clear=raw(0x193960d,0x1939614)
assert clear.hex()=='488b03c6407000'
def arr(b):return ','.join(str(x) for x in b)
code=r'''
#include <windows.h>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstring>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;
#define BBSC_TIMELINE(...)
namespace MemoryProt{constexpr int CpuWrite=1;}
std::array<u8,0x500> chr{};std::array<u8,0x100> modules{};std::array<u8,0x300> stats{};
std::array<u8,0x100> slots{};std::array<u8,0x20> world{};
u64 slotptr=(u64)slots.data(),image_base=(u64)&slotptr;constexpr u64 PlayerSlotManagerPointerOffset=0;
std::atomic<u32> bbsc_load_generation{4};s32 state=6,type=1;bool quit=false,title=false,writable=true;
u64 player=(u64)chr.data(),global=(u64)world.data();int hp_calls=0;
template<class T>T ReadValue(u64 a,size_t off){T x{};memcpy(&x,(void*)(a+off),sizeof x);return x;}
template<class T>void WriteValue(u64 a,size_t off,T x){memcpy((void*)(a+off),&x,sizeof x);}
bool ReadablePointer(u64 a,size_t){return a>0x10000;}
bool HasMemoryAccess(u64,size_t,int){return writable;}
u64 GetLocalPlayerCharacter(){return player;}u64 GetGlobalState(){return global;}
s32 GetSessionState(){return state;}s32 GetLocalCharacterType(){return type;}
s32 GetCharacterHp(u64){return ReadValue<s32>((u64)stats.data(),0xf8);}
bool IsInvaderType(s32 t){return t==2||t==12;}
bool BbscQuitInProgress(){return quit;}bool BbscReturningToTitle(){return title;}
void __attribute__((sysv_abi)) set_hp(u64 p,s32 hp){assert(p==(u64)chr.data());++hp_calls;WriteValue<s32>((u64)stats.data(),0xf8,hp);}
'''+function('void PrepareBbscNativeDeathResources()')+r'''
int main(){
 auto mem=(u8*)VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(mem);
 u8 prefix[]={0x53,0x41,0x55,0x48,0x83,0xec,0x28,0x49,0x89,0xcd};
 memcpy(mem,prefix,sizeof prefix);
 u8 gate[]={GATE};memcpy(mem+10,gate,sizeof gate);
 // Relocate native RIP-relative slot-manager pointer and the native call.
 *(int32_t*)(mem+13)=512-(10+7);mem[10+15]=24-16;
 *(int32_t*)(mem+10+20)=128-(10+24);
 *(u64*)(mem+512)=slotptr;
 u8 clear[]={CLEAR};memcpy(mem+34,clear,sizeof clear);
 u8 end[]={0x48,0x83,0xc4,0x28,0x41,0x5d,0x5b,0xc3};memcpy(mem+41,end,sizeof end);
 u8 hp_prefix[]={0x41,0x56,0x49,0x89,0xfe};memcpy(mem+128,hp_prefix,5);
 u8 heal[]={HEAL};memcpy(mem+133,heal,sizeof heal);
 size_t at=133+sizeof heal;mem[at++]=0x48;mem[at++]=0xb8;
 *(u64*)(mem+at)=(u64)&set_hp;at+=8;mem[at++]=0xff;mem[at++]=0xd0;
 mem[at++]=0x41;mem[at++]=0x5e;mem[at++]=0xc3;
 DWORD previous;assert(VirtualProtect(mem,4096,PAGE_EXECUTE_READ,&previous));
 FlushInstructionCache(GetCurrentProcess(),mem,4096);
 auto native=(void(*)(u64))mem;
 WriteValue<u64>(player,0x3b0,(u64)modules.data());WriteValue<u64>((u64)modules.data(),0x20,(u64)stats.data());
 WriteValue<s32>((u64)stats.data(),0xfc,594);
 // Negative control: old direct point-load path leaves a constructed guest at HP 0.
 native(player);assert(GetCharacterHp(player)==0&&hp_calls==0);
 for(int role:{3,6})for(int pending:{0,1}){
  state=role;slots[0x70]=pending;WriteValue<s32>((u64)stats.data(),0xf8,0);int before=hp_calls;
  PrepareBbscNativeDeathResources();assert(GetCharacterHp(player)==0&&slots[0x70]==1);
  native(player);assert(GetCharacterHp(player)==594&&hp_calls==before+1&&slots[0x70]==0);
  // No pending death => a second construction/travel must not heal new damage.
  WriteValue<s32>((u64)stats.data(),0xf8,123);PrepareBbscNativeDeathResources();native(player);
  assert(GetCharacterHp(player)==123&&hp_calls==before+1);
 }
 for(int mode=0;mode<8;++mode){
  state=6;type=1;quit=title=false;writable=true;world[8]=0;player=(u64)chr.data();
  WriteValue<s32>((u64)stats.data(),0xf8,0);slots[0x70]=0;
  if(mode==0)state=0;if(mode==1)type=2;if(mode==2)quit=true;if(mode==3)title=true;
  if(mode==4)world[8]=1;if(mode==5)writable=false;if(mode==6)player=0;
  if(mode==7)WriteValue<s32>((u64)stats.data(),0xf8,-1);
  PrepareBbscNativeDeathResources();assert(slots[0x70]==0);
 }
 VirtualFree(mem,0,MEM_RELEASE);
}
'''
code=code.replace('GATE',arr(gate)).replace('CLEAR',arr(clear)).replace('HEAL',arr(heal))
with tempfile.TemporaryDirectory(prefix='bbsc-native-death-hp-') as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text(code)
 subprocess.run([os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=5)
notify=function('void NotifyBbscDeathReload()')
assert notify.index('PrepareBbscNativeDeathResources()')<notify.index('SendBbscLifeState')
assert 'BbscRespawnInPlace' not in function('void TickBbscPostLoadRecovery()')
assert 'BbscRespawnLoopMs' not in source
print('PASS: original native constructor gate + HP=max instructions, old path HP0 negative control, host/guest, native flag consumed, no healing on travel/new damage/invasion/teardown')
