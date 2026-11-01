"""Production lethal-hook/award bodies, plus byte checks on an optional research ELF."""
from pathlib import Path
import os
import re
import subprocess

root = Path(__file__).resolve().parents[1]
source = (root / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
header = (root / 'emulator/mod/bbsc_register.h').read_text(encoding='utf8')
rules = (root / 'emulator/src/core/bbsc_dreg_rules.h').read_text(encoding='utf8')
strip = lambda s: re.sub(r'^#(?:include|pragma once).*$', '', s, flags=re.M)
a = source.index('void PS4_SYSV_ABI BbscDregLethalHook(')
b = source.index('void InstallBbscSessionDregHooks()', a)
fixture = r'''
#include <array>
#include <map>
#include <vector>
#include <cstdint>
#include <cstring>
#include <cassert>
using u64=uint64_t;using u32=uint32_t;using u16=uint16_t;using u8=uint8_t;using s32=int32_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_WARNING(...)
''' + strip(header) + strip(rules) + r'''
using Core::Bloodborne::DregLife;
struct GuestRegisterSnapshot {u64 rax=0,rcx=0,r15=0;};
std::vector<u16> credited;
namespace BbscMod {
u32 RegisterSessionKey(){return 42;}
void QueueRegisterKill(const RegisterIdentity& k){credited.push_back(k.member);}
}
DregLife bbsc_dreg_life;
bool bbsc_pvp_on=true,loading=false;
u64 image_base=0,CandidateLocalStatePointerOffset=1;
std::map<u64,u64> memory;
s32 hp=100;
u64 GetLocalPlayerCharacter(){return 100;}
u64 GetGlobalState(){return 3000;}
s32 GetCharacterHp(u64){return hp;}
bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64 p,size_t off){return static_cast<T>(memory[p+off]);}
bool BbscRegisterRemotePlayer(u64 c){return c>=200&&c<=500&&c%100==0;}
BbscMod::RegisterIdentity ReadBbscRegisterIdentity(u64 c){BbscMod::RegisterIdentity id;id.room=42;id.member=c/100;return id;}
u64 BbscCarriedInventory(){return 1;}u64 BbscStorageInventory(){return 2;}
int added=0,storage_adds=0,popups=0,ledger=0;bool carried_full=false,storage_full=false,add_fail=false;
enum class BbscLedgerSource{Award};
void NoteBbscLedgerGiven(BbscLedgerSource,s32,u32,u32 code,s32 n){assert(code==0x400002c0&&n==1);++ledger;}
void ShowBbscItemPopup(u32 type,u32 id,s32 n,const char*){assert(type==0x40000000&&id==704&&n==1);++popups;}
s32 PS4_SYSV_ABI Fits(u64 inv,const u32* code,s32 n){assert(*code==0x400002c0&&n==1);return inv==1?(carried_full?0:1):(storage_full?0:1);}
s32 PS4_SYSV_ABI Add(u64 inv,const u32* key,s32 n){assert(*key==0xb00002c0&&n==1);if(add_fail)return -1;++added;if(inv==2)++storage_adds;return 0;}
u64 InventoryFitsOffset=(u64)&Fits,InventoryAddOffset=(u64)&Add;
''' + source[a:b] + r'''
int main(){
 memory[1]=1000;memory[1000+0x30]=5;memory[1000+0x38]=2000;
 for(u64 i=0;i<5;++i){memory[2000+i*0x38]=(i+1)*100;memory[(i+1)*100+8]=10000+i;}
 GuestRegisterSnapshot hit;
 hit.rcx=100;
 for(u64 killer=200;killer<=500;killer+=100){
  bbsc_dreg_life.Observe(100,42,true,100);hp=0;hit.r15=killer;
  auto before=credited.size();BbscDregLethalHook(0,&hit);BbscDregLethalHook(0,&hit);
  assert(credited.size()==before+1&&credited.back()==killer/100);
 }
 auto before=credited.size();
 bbsc_dreg_life.Observe(100,42,true,100);bbsc_pvp_on=false;hit.r15=200;BbscDregLethalHook(0,&hit);assert(credited.size()==before);
 bbsc_pvp_on=true;bbsc_dreg_life.Observe(100,42,true,100);hit.r15=900;BbscDregLethalHook(0,&hit);assert(credited.size()==before); // NPC
 bbsc_dreg_life.Observe(100,42,true,100);hit.r15=100;BbscDregLethalHook(0,&hit);assert(credited.size()==before); // self
 bbsc_dreg_life.Observe(100,42,true,100);hp=20;hit.r15=200;BbscDregLethalHook(0,&hit);assert(credited.size()==before);
 hp=0;hit.r15=400;BbscDregLethalHook(0,&hit);assert(credited.back()==4); // finisher, not earlier attacker
 before=credited.size();
 GuestRegisterSnapshot periodic;periodic.rax=100;periodic.rcx=10002;
 bbsc_dreg_life.Observe(100,42,true,100);BbscDregLethalHook(1,&periodic);assert(credited.size()==before+1&&credited.back()==3);
 bbsc_dreg_life.Observe(100,42,true,100);periodic.rcx=0xffffffff;BbscDregLethalHook(1,&periodic);assert(credited.size()==before+1); // no guessed environmental killer
 hp=100;assert(GiveBbscSessionBloodDreg());assert(added==1&&popups==1&&ledger==1);
 carried_full=true;assert(GiveBbscSessionBloodDreg());assert(storage_adds==1);
 storage_full=true;assert(!GiveBbscSessionBloodDreg());assert(added==2);
 storage_full=false;add_fail=true;assert(!GiveBbscSessionBloodDreg());assert(added==2);
 add_fail=false;hp=0;assert(!GiveBbscSessionBloodDreg());hp=100;
 memory[3000+8]=1;assert(!GiveBbscSessionBloodDreg());
}
'''
build = root / 'build'
cpp = build / 'test_pvp_dregs.cpp'
exe = cpp.with_suffix('.exe')
cpp.write_text(fixture, encoding='utf8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe', '-std=c++20', str(cpp), '-o', str(exe)], check=True)
env = dict(os.environ)
env['PATH'] = 'C:/msys64/clang64/bin;' + env.get('PATH', '')
subprocess.run([str(exe)], env=env, check=True)

elf = root.parents[1] / 'out/register-study.elf'
if elf.exists():
    import capstone
    data = elf.read_bytes()
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    for address, expected in [(0x1A2C176, '8981dc010000'), (0x1A30011, '8988dc010000')]:
        span = data[address+0x4000:address+0x4006]
        assert span.hex() == expected
        ins = list(decoder.disasm(span, address))
        assert len(ins) == 1 and ins[0].size == 6 and 'rip' not in ins[0].op_str
    assert data[0x18FE4E7+0x4000:0x18FE4E7+0x4006].hex() == '8b81e8000000'
    assert data[0x18FE514+0x4000:0x18FE514+0x4006].hex() == '8988e8000000'
print('PASS: production lethal hooks, each of 4 possible finishers, earlier attacker excluded, PvP/NPC/self/environment/replay gates, native item grant/storage retry; native hook and offering-counter bytes')
