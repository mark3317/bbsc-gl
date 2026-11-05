"""Execute remaining manual guest-key component paths; native rewards have a separate fixture.

Original parameters are read-only. Inventories, flags, game calls and receipts
are isolated memory; this is not a gameplay or real-save test.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/gamedata'))
import bbfiles
import param
from personal_keys import SOURCES

source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')


def function(signature):
    start = source.index(signature + ' {')
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


bbfiles.GAME = os.environ['BB_GAME']
_, _, data, rows = param.load('ItemLotParam')
prefix = r'''
#include <windows.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <map>
#include <random>
#include <set>
#include <string>
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;using s32=int32_t;using u64=uint64_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
namespace fmt {template<class... T>std::string format(const char*,T...){return {};}}
u64 image_base;constexpr size_t ItemLotRowSize=0x94;
enum class BbscLedgerSource {Award,Drop,Boss};
std::map<s32,std::array<u8,0x94>> lots;
std::map<u32,int> inventory,receipts;std::set<u32> flags;
int popup=0,lot_receipts=0;bool fail_add=false;
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof(v));return v;}
bool ReadablePointer(u64 p,size_t){return p!=0;}int SteadyNowMs(){return 1234;}
u64 BbscGameParamTable(const char*){return 1;}
u64 BbscParamRow(u64,u32 id,size_t){return lots.contains(id)?(u64)lots.at(id).data():0;}
bool BbscNpcReceiptAllowed(u32){return true;}bool BbscEventFlag(u32 f){return flags.contains(f);}
bool BbscGoodsIsGuestDrop(u32){return false;}bool BbscGuestInHostWorld(){return true;}
s32 AddBbscCarriedGoods(u32 id,s32 count){if(fail_add)return -1;inventory[id]+=count;return 0;}
void NoteBbscLedgerGiven(BbscLedgerSource,s32,u32,u32 code,s32 count){receipts[code]+=count;}
void NoteBbscLedgerLot(s32,u32){++lot_receipts;}
void ShowBbscItemPopup(u32,u32,s32,const char*){++popup;}
bool GiveBbscPickedLotEntry(u64,s32,u32,BbscLedgerSource){return false;}
void NoteBbscLedgerOwed(BbscLedgerSource,s32,u32,u32,s32,const char*){assert(false);}
const char16_t* BbscL(const char16_t* en,const char16_t*){return en;}
void BbscAnnounce(const char16_t*,const char*){}
u64 PS4_SYSV_ABI SetFlag(u64,u32 flag,u8 value){assert(value==1);flags.insert(flag);return 0;}
// Native boss path's inventory-fit/add calls are represented by isolated stubs.
u64 BbscCarriedInventory(){return 0x1000;}
bool BbscInventoryHas(u64,u32 code){return inventory[code&0xfffffff]>0;}
s32 PS4_SYSV_ABI Fits(u64,u32*,s32){return fail_add?0:1;}
s32 PS4_SYSV_ABI Add(u64,u32* code,s32 count){inventory[*code&0xfffffff]+=count;return 0;}
'''
code = prefix + function('void GiveBbscGuestDrop(s32 lot, u32 name)')
code += r'''
void stub(size_t offset,u64 target){
 u8 op[12]={0x48,0xb8};memcpy(op+2,&target,8);op[10]=0xff;op[11]=0xe0;
 memcpy((void*)(image_base+offset),op,12);
}
void reset(){inventory.clear();receipts.clear();flags.clear();popup=lot_receipts=0;fail_add=false;}
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x1500000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);
 assert(image_base);stub(0x0132e5a0,(u64)SetFlag);
 stub(0x014d9c10,(u64)Fits);stub(0x014da0a0,(u64)Add);
'''
import re
native_lots = set(map(int, re.findall(r"\b\d+\b", re.search(r"BbscNativeScriptedLots\{(.*?)\};", source, re.S)[1])))
for first, repeat in re.findall(r"\{\d+, \d+, (\d+), (\d+)\}", re.search(r"BbscBossRewards\{\{(.*?)\}\};", source, re.S)[1]):
    native_lots.update((int(first), int(repeat)))
checked = 0
for goods, (route, lot, _, _) in SOURCES.items():
    if lot in native_lots:
        continue  # covered through the actual native hook/tickets in test_native_reward_delivery
    checked += 1
    raw = data[rows[lot]:rows[lot] + 0x94]
    code += f'lots[{lot}]={{{",".join(map(str,raw))}}};\n'
    code += f'''
 reset();GiveBbscGuestDrop({lot},0);
 assert(inventory[{goods}]==1&&receipts[0x40000000u|{goods}]==1&&popup==1);
 reset();fail_add=true;GiveBbscGuestDrop({lot},0);
 assert(inventory[{goods}]==0&&receipts.empty()&&popup==0&&flags.empty());
'''
code += '\n}\n'
compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
with tempfile.TemporaryDirectory(prefix='bbsc-personal-key-delivery-') as folder:
    cpp, exe = Path(folder) / 'fixture.cpp', Path(folder) / 'fixture.exe'
    cpp.write_text(code, encoding='utf-8')
    subprocess.run([compiler, '-std=c++20', '-DNOMINMAX', str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(exe)], check=True, env=env, timeout=10)
print(f'PASS: {checked} remaining original key-lot manual helpers; failed add gives no receipt; native rewards tested separately')
