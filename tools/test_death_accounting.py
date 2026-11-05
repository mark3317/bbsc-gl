"""Execute production death accounting twice against isolated native/memory boundaries."""
from pathlib import Path
import os, subprocess, tempfile
source=(Path(__file__).resolve().parents[1]/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
 a=source.index(signature+' {'); b=source.index('{',a)+1; depth=1
 while depth:
  depth+=(source[b]=='{')-(source[b]=='}'); b+=1
 return source[a:b]
code=r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_map>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
namespace fmt {template<class...T>std::string format(const char*,T...){return {};}}
u64 image_base=0x100000, global=0x200000, slots=0x300000, record=0x400000,local=0x500000;
constexpr u64 PlayerSlotManagerPointerOffset=0x10,SprjEventManPointerOffset=0x20,PlayerEchoesOffset=0x94;
s32 bbsc_echoes_at_death=-1;bool enabled=true,drop_works=true,storage_ready=true;
int drops=0,adds=0;std::unordered_map<u64,u64> mem;
std::unordered_map<u32,s32> carried,storage;
bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64 p,size_t off){return static_cast<T>(mem[p+off]);}
template<class T>void WriteValue(u64 p,size_t off,T value){mem[p+off]=value;}
bool BbscDeathPenaltyEnabled(){return enabled;}u64 GetGlobalState(){return global;}
u64 GetLocalPlayerCharacter(){return 0x600000;}u64 GetPlayerSlotData(){return local;}
s32 GetBloodEchoes(){return static_cast<s32>(mem[local+PlayerEchoesOffset]);}
s32 GetLocalPlayerType(){return 1;}
u64 BbscCarriedInventory(){return 1;}u64 BbscStorageInventory(){return storage_ready?2:0;}
s32 BbscInventoryCount(u64 inv,u32 item){return (inv==1?carried:storage)[item&0xfffffff];}
s32 BbscInventorySlot(u64,u32 item){return static_cast<s32>(item&0xfffffff);}
void NativeDrop(u64,u64,u8){++drops;assert(mem[global+0x1592]==1);
 if(drop_works && mem[global+0x1770]){mem[record+0x38]=GetBloodEchoes();mem[slots+0x28]=1;mem[local+PlayerEchoesOffset]=0;}}
s32 NativeFits(u64,const u32* item,s32 requested){return std::min(requested,20-carried[*item&0xfffffff]);}
s32 NativeAdd(u64,const u32* key,s32 count){++adds;carried[*key&0xfffffff]+=count;return 0;}
s32 NativeChange(u64,u32 slot,s32 delta,s32* over){*over=0;return storage[slot]+=delta;}
void NativeFree(u64,u32,s32){}
'''
penalty=function('bool BbscApplyDeathPenalty(std::string_view why)').replace('image_base + DropBloodstainOffset','reinterpret_cast<u64>(&NativeDrop)')
restock=function('void BbscRestockFromStorage(std::string_view why)')
for address,name in [('0x014D9A80','NativeFits'),('0x014DA0A0','NativeAdd'),('0x014D94A0','NativeChange'),('0x014DAB20','NativeFree')]:
 restock=restock.replace('image_base + '+address,'reinterpret_cast<u64>(&'+name+')')
code+=penalty+'\n'+restock+r'''
int main(){
 mem[image_base+PlayerSlotManagerPointerOffset]=slots;mem[slots+0x30]=record;
 mem[image_base+SprjEventManPointerOffset]=0x700000;mem[0x700080]=0x800000;
 mem[global+0x1770]=1;storage={{1000,40},{900,30}};
 for(int death=0;death<2;++death){
  int before_drops=drops;mem[local+PlayerEchoesOffset]=1234+death;
  bbsc_echoes_at_death=GetBloodEchoes();carried={{1000,3},{900,7}};
  auto vials=storage[1000],bullets=storage[900];
  assert(BbscApplyDeathPenalty("repeat fixture"));
  assert(GetBloodEchoes()==0 && mem[record+0x38]==1234+death && mem[global+0x1592]==0);
  assert(!BbscApplyDeathPenalty("already handled") && drops==before_drops+1);
  BbscRestockFromStorage("repeat fixture");
  assert(carried[1000]==20 && carried[900]==20);
  assert(storage[1000]==vials-17 && storage[900]==bullets-13);
 }
 // Native drop can refuse: never report a successful penalty when all echoes remain.
 mem[local+PlayerEchoesOffset]=555;bbsc_echoes_at_death=555;drop_works=false;
 assert(!BbscApplyDeathPenalty("native refused") && GetBloodEchoes()==555);
 drop_works=true;mem[global+0x1770]=0;bbsc_echoes_at_death=555;
 assert(!BbscApplyDeathPenalty("native gate disabled") && GetBloodEchoes()==555);
 // Empty/missing storage never manufactures consumables or removes unrelated items.
 carried={{1000,3},{900,7}};storage={{1000,0},{900,0}};int before_adds=adds;
 BbscRestockFromStorage("empty");assert(adds==before_adds && carried[1000]==3 && carried[900]==7);
 storage_ready=false;BbscRestockFromStorage("unavailable");assert(adds==before_adds);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-death-accounting-') as directory:
 p=Path(directory);cpp=p/'test.cpp';exe=p/'test.exe';cpp.write_text(code,encoding='utf-8')
 compiler=os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe')
 subprocess.run([compiler,'-std=c++20',str(cpp),'-o',str(exe)],check=True)
 env=dict(os.environ);env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
 subprocess.run([str(exe)],env=env,check=True,timeout=5)
print('PASS: two death penalties and native inventory transfers, refusal, no duplicate charge, empty storage')
