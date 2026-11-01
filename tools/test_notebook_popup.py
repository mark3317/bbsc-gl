from pathlib import Path
import subprocess,os
root=Path(__file__).resolve().parents[1];s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
a=s.index('struct BbscKitItem {');b=s.index('constexpr size_t GoodsRowSize',a)
c=s.index('void TickBbscDuelBellGive(const GuestRegisterSnapshot* pickup) {');d=s.index('// True while the local player',c)
fixture=r'''
#include <cstdint>
#include <cstring>
#include <vector>
#include <string>
#include <set>
#include <cassert>
using u64=uint64_t;using u32=uint32_t;using s32=int32_t;using u8=uint8_t;using s64=int64_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
struct GuestRegisterSnapshot{u64 rdi=55,rsi=0,r9=0;};
std::set<u32> inventories[3];std::vector<u32> popups;bool full=false,fail=false;int state=0,notice=0;u8 own=1;
u64 image_base=0;
s32 Fits(u64 inv,const u32*,s32){return inv==1&&full?0:1;}
s32 Add(u64 inv,const u32*key,s32){if(fail)return -1;inventories[inv].insert(0x40000000u|(*key&0xfffffff));return 0;}
u64 Queue(u64 q,const u32* h,u32 cat,u32 id,s32 count,u32 flags){assert(q==55&&*h==0&&cat==0x40000000&&count==1&&flags==0);popups.push_back(id);return 1;}
u64 InventoryFitsOffset=(u64)&Fits,InventoryAddOffset=(u64)&Add,BbscItemPopupQueue=(u64)&Queue;
s64 SteadyNowMs(){return 100000;}bool BbscKitParamsReady(){return true;}
u64 GetLocalPlayerCharacter(){return 10;}u64 GetGlobalState(){return 20;}bool ReadablePointer(u64,size_t){return true;}int GetCharacterHp(u64){return 100;}
template<class T>T ReadValue(u64,size_t off){return off==0x1592?own:0;}
u64 BbscCarriedInventory(){return 1;}u64 BbscStorageInventory(){return 2;}
bool BbscInventoryHas(u64 inv,u32 key){return inventories[inv].contains(key);}bool BbscInventoryRemove(u64 inv,u32 key){return inventories[inv].erase(key);}
int GetSessionState(){return state;}bool BackupBbscSaves(){return true;}
const char16_t* BbscL(const char16_t*a,const char16_t*){return a;}
void BbscAnnounce(const char16_t*,const char*){++notice;}
'''+s[a:b]+s[c:d]+r'''
void clear(){inventories[1].clear();inventories[2].clear();popups.clear();full=fail=false;own=1;state=0;}
int main(){GuestRegisterSnapshot pickup;
 clear();TickBbscDuelBellGive(&pickup);assert(popups.empty());
 inventories[2].insert(0x40000078);TickBbscDuelBellGive(&pickup);assert(popups.empty());
 inventories[1].insert(0x40000078);TickBbscDuelBellGive(&pickup);assert((popups==std::vector<u32>{200,205,225,111})&&notice==0);
 TickBbscDuelBellGive(&pickup);assert(popups.size()==4);
 clear();inventories[1].insert(0x40000078);inventories[2].insert(0x400000c8);TickBbscDuelBellGive(&pickup);assert(popups.size()==3);
 clear();inventories[1].insert(0x40000078);fail=true;TickBbscDuelBellGive(&pickup);assert(popups.empty());
 fail=false;full=true;TickBbscDuelBellGive(&pickup);assert(popups.size()==4&&inventories[2].size()==4);
 clear();inventories[1].insert(0x40000078);state=6;TickBbscDuelBellGive(&pickup);assert(popups.empty());
 state=0;own=0;TickBbscDuelBellGive(&pickup);assert(popups.empty());
}
'''
build=root/'build';cpp=build/'test_notebook_popup.cpp';exe=cpp.with_suffix('.exe');cpp.write_text(fixture,encoding='utf8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20',str(cpp),'-o',str(exe)],check=True)
env=dict(os.environ);env['PATH']='C:/msys64/clang64/bin;'+env.get('PATH','');subprocess.run([str(exe)],env=env,check=True)
print('PASS: real kit function: Notebook carried/storage gate, same-queue four popups, no duplicate/overlay, existing goods, failed add, storage fallback, guest/foreign world guards')
