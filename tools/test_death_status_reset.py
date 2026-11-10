"""Execute retained-death status cleanup; isolated memory, no game process/saves."""
from pathlib import Path
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')


def function(signature):
    a = source.index(signature+' {')
    b = source.index('{', a)+1
    depth = 1
    while depth:
        depth += (source[b] == '{')-(source[b] == '}')
        b += 1
    return source[a:b]


policy = function('bool BbscEffectEndsAtDeath(u8 category, float duration)')
reset = function('bool BbscResetDeathStatuses(u64 player)')
respawn = function('bool BbscRespawnInPlace(std::string_view why)')
assert respawn.index('if (!target.has_value())') < respawn.index('BbscResetDeathStatuses(player)')
assert respawn.index('BbscResetDeathStatuses(player)') < respawn.index('reinterpret_cast<Warp>')
assert respawn.index('BbscResetDeathStatuses(player)') < respawn.index('reinterpret_cast<SetHp>')
warp = respawn.index('reinterpret_cast<Warp>(warp)(player, position.data(), rotation.data(), 1)')
physics = respawn.index('reinterpret_cast<PhysicsReset>(image_base + 0x018BCF30)(player, 1)')
assert warp < physics < respawn.index('reinterpret_cast<Reset>(reset)(player)')
assert respawn.count('reinterpret_cast<PhysicsReset>') == 1
assert 'return false;' in respawn[respawn.index('if (!BbscResetDeathStatuses(player))'):][:210]
# Intercept only the native erase boundary. The actual native resistance reset
# executes from the read-only original ELF when available, including its real
# SysV virtual calls. No saved-data serializer is invoked by this fixture.
reset = reset.replace('reinterpret_cast<Erase>(erase)', '(&NativeErase)')
fixture = r'''
#define NOMINMAX
#include <windows.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;
#define PS4_SYSV_ABI __attribute__((sysv_abi))
#define LOG_INFO(...)
namespace MemoryProt {constexpr int CpuWrite=1;}
using Block=std::array<u8,0x600>;
Block actor{},mods{},effects{},resist{},vtable{};
std::array<Block,20> nodes{},rows{};
u64 image_base,player=(u64)actor.data(),global;
Block globalData{};
bool quit=false,title=false,writable=true;
int hp=0,erases=0,capCalls=0;
std::array<s32,5> caps{150,170,190,210,230};
std::vector<std::pair<u64,size_t>> ranges;
bool ReadablePointer(u64 p,size_t n){
 for(auto [a,s]:ranges)if(p>=a&&p-a<=s&&n<=s-(p-a))return true;
 return false;
}
bool HasMemoryAccess(u64 p,size_t n,int){return writable&&ReadablePointer(p,n);}
template<class T>T ReadValue(u64 p,size_t o){T v;std::memcpy(&v,(void*)(p+o),sizeof(v));return v;}
template<class T>void WriteValue(u64 p,size_t o,T v){std::memcpy((void*)(p+o),&v,sizeof(v));}
u64 GetLocalPlayerCharacter(){return player;}int GetCharacterHp(u64){return hp;}
u64 GetGlobalState(){return global;}
bool BbscQuitInProgress(){return quit;}bool BbscReturningToTitle(){return title;}
s32 PS4_SYSV_ABI NativeCap(u64 chr,u32 index){
 assert(chr==player&&index<5);++capCalls;return caps[index];
}
void PS4_SYSV_ABI FallbackReset(u64 module,u64 init){
 assert(module==(u64)resist.data()&&init==player);
 for(u32 i=0;i<5;++i){auto c=NativeCap(player,i);
  WriteValue<s32>(module,0x24+i*4,c);WriteValue<s32>(module,0x10+i*4,std::max(c,0));}
}
u64 PS4_SYSV_ABI NativeErase(u64 manager,u64 node,s32 immediate){
 assert(manager==(u64)effects.data()&&immediate==1);++erases;
 const u64 next=ReadValue<u64>(node,0x58);
 u64 link=manager+8;
 while(ReadValue<u64>(link,0)!=node){link=ReadValue<u64>(link,0)+0x58;assert(ReadablePointer(link,8));}
 WriteValue<u64>(link,0,next);
 // Poison freed storage so an incorrect traversal cannot follow stale links.
 std::memset((void*)node,0xdd,0x60);
 return next;
}
'''
fixture += policy+'\n'+reset+r'''
void setup(){
 for(auto* b:{&actor,&mods,&effects,&resist,&vtable,&globalData})b->fill(0);
 for(auto& b:nodes)b.fill(0);for(auto& b:rows)b.fill(0);
 player=(u64)actor.data();global=(u64)globalData.data();
 hp=0;quit=title=false;writable=true;erases=capCalls=0;
 ranges.clear();
 for(auto* b:{&actor,&mods,&effects,&resist,&vtable,&globalData})ranges.emplace_back((u64)b->data(),b->size());
 for(auto& b:nodes)ranges.emplace_back((u64)b.data(),b.size());
 for(auto& b:rows)ranges.emplace_back((u64)b.data(),b.size());
 ranges.emplace_back(image_base,0x1a5c500);
 WriteValue<u64>(player,0x3b0,(u64)mods.data());
 WriteValue<u64>(player,0x1c8,(u64)effects.data());
 WriteValue<u64>(player,0,(u64)vtable.data());
 WriteValue<u64>((u64)vtable.data(),0x1e0,(u64)&NativeCap);
 WriteValue<u64>((u64)mods.data(),0x28,(u64)resist.data());
 WriteValue<u64>((u64)effects.data(),0x18,player);
 WriteValue<u64>((u64)resist.data(),8,player);
 for(u32 i=0;i<5;++i){WriteValue<s32>((u64)resist.data(),0x10+i*4,2+i);
  WriteValue<s32>((u64)resist.data(),0x24+i*4,caps[i]);
  WriteValue<float>((u64)resist.data(),0x38+i*4,0.8f);}
 WriteValue<u32>((u64)resist.data(),0x4c,15);resist[0x50]=1;
}
void node(int i,u8 category,float duration){
 auto p=(u64)nodes[i].data(),r=(u64)rows[i].data();
 WriteValue<u64>(p,0x48,r);WriteValue<u8>(r,0x141,category);WriteValue<float>(r,8,duration);
 if(i)WriteValue<u64>((u64)nodes[i-1].data(),0x58,p);
 else WriteValue<u64>((u64)effects.data(),8,p);
}
int main(){
 for(unsigned c=0;c<256;++c)for(float d:{-1.0f,0.0f,30.0f,NAN}){
  const bool expected=c<10 ? (c!=3&&c!=6) : (c==255&&d>=0);
  assert(BbscEffectEndsAtDeath(c,d)==expected);
 }
 image_base=(u64)VirtualAlloc(nullptr,0x1a5c500,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);
 assert(image_base);
 NATIVE_CODE_SETUP
 FlushInstructionCache(GetCurrentProcess(),(void*)image_base,0x1a5c500);
 for(int role:{0,1})for(int life=0;life<3;++life){
  setup();WriteValue<s32>(player,0x78,role);
  for(int c=0;c<10;++c)node(c,c,30);
  node(10,255,60);node(11,255,-1);node(12,17,30);node(13,255,NAN);
  auto permanent=nodes[11],unknown=nodes[12],saved3=nodes[3],saved6=nodes[6];
  // Includes poison/frenzy/rapid-poison saved categories 0/1/2, every other
  // native death-discarded category, and ordinary unsaved temporary buffs.
  assert(BbscResetDeathStatuses(player));assert(erases==9&&capCalls==5);
  for(u32 i=0;i<5;++i){assert(ReadValue<s32>((u64)resist.data(),0x10+i*4)==caps[i]);
   assert(ReadValue<float>((u64)resist.data(),0x38+i*4)==0);}
  assert(ReadValue<u32>((u64)resist.data(),0x4c)==0&&resist[0x50]==0);
  // Persistent categories survive, as do indefinite equipment/session effects.
  WriteValue<u64>((u64)saved3.data(),0x58,(u64)nodes[6].data());
  WriteValue<u64>((u64)saved6.data(),0x58,(u64)nodes[11].data());
  assert(nodes[11]==permanent&&nodes[12]==unknown&&nodes[6]==saved6&&nodes[3]==saved3);
  assert(ReadValue<u64>((u64)effects.data(),8)==(u64)nodes[3].data());
  assert(ReadValue<u64>((u64)nodes[3].data(),0x58)==(u64)nodes[6].data());
  assert(ReadValue<u64>((u64)nodes[6].data(),0x58)==(u64)nodes[11].data());
  hp=100;assert(!BbscResetDeathStatuses(player)&&erases==9); // not a periodic cure
 }
 for(int mode=0;mode<14;++mode){
  setup();node(0,0,60);
  if(mode==0)hp=100;if(mode==1)quit=true;if(mode==2)title=true;
  if(mode==3)globalData[8]=1;if(mode==4)writable=false;
  if(mode==5)WriteValue<u64>(player,0x3b0,0);
  if(mode==6)WriteValue<u64>(player,0x1c8,0);
  if(mode==7)WriteValue<u64>((u64)resist.data(),8,player+1);
  if(mode==8)WriteValue<u64>((u64)effects.data(),0x18,player+1);
  if(mode==9)WriteValue<u64>((u64)nodes[0].data(),0x58,(u64)nodes[0].data());
  if(mode==10)WriteValue<u64>((u64)nodes[0].data(),0x48,1);
  if(mode==11)WriteValue<u64>((u64)nodes[0].data(),0x58,1);
  if(mode==12)*(u8*)(image_base+0x17e1d90)^=1;
  if(mode==13)*(u8*)(image_base+0x1a5c380)^=1;
  auto before=resist;
  assert(!BbscResetDeathStatuses(player)&&erases==0&&capCalls==0&&resist==before);
  if(mode==12)*(u8*)(image_base+0x17e1d90)^=1;
  if(mode==13)*(u8*)(image_base+0x1a5c380)^=1;
 }
 setup();assert(!BbscResetDeathStatuses(player+1));
 // No effects still needs to clear a partly filled gauge and pending trigger.
 setup();caps={0,-1,100,0,75};assert(BbscResetDeathStatuses(player));
 assert(erases==0&&capCalls==5);
 for(u32 i=0;i<5;++i)assert(ReadValue<s32>((u64)resist.data(),0x10+i*4)==std::max(caps[i],0));
 VirtualFree((void*)image_base,0,MEM_RELEASE);
}
'''
elf = ROOT.parents[1]/'out/register-study.elf'
if elf.exists():
    binary = elf.read_bytes()

    def span(address, size):
        return binary[address+0x4000:address+0x4000+size]

    # Independent original rules: death's finite unsaved filter; serializer's
    # HP gate and two category masks; the revive vtable reset only clears flags.
    assert span(0x18C4C81, 7).hex() == '80b941010000ff'
    assert span(0x18BCC20, 6).hex() == '8b89f8000000'
    assert span(0x18BCC26, 6).hex() == '41b9b7030000'
    assert span(0x18BCC2C, 6).hex() == '41b848000000'
    assert span(0x18BD0E0, 14).hex() == '488b475866c780140100000000c3'
    # Verify that production signatures match the game before running its code.
    for name, address in [('EraseSignature', 0x17E1D90), ('ResistSignature', 0x1A5C380)]:
        body = reset[reset.index(name+'{'):].split('};', 1)[0]
        signature = bytes(int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{2})', body))
        assert span(address, len(signature)) == signature, name
    native = span(0x1A5C380, 0x99)
    setup = 'const u8 code[]={'+','.join(str(b) for b in native)+'};\n'
    setup += 'std::memcpy((void*)(image_base+0x1a5c380),code,sizeof(code));\n'
else:
    setup = '*(u8*)(image_base+0x1a5c380)=0xe9;\n'
    # No native file: retain production/guard fixture using a local native stub.
    reset = reset.replace('reinterpret_cast<ResetResistance>(reset)', '(&FallbackReset)')
    fixture = fixture.replace('reinterpret_cast<ResetResistance>(reset)', '(&FallbackReset)')
    signature_body = reset[reset.index('ResistSignature{'):].split('};', 1)[0]
    signature = bytes(int(x,16) for x in re.findall(r'0x([0-9A-Fa-f]{2})', signature_body))
    setup = 'const u8 code[]={'+','.join(str(b) for b in signature)+'};\n'
    setup += 'std::memcpy((void*)(image_base+0x1a5c380),code,sizeof(code));\n'
    print('SKIP: actual original resistance routine (out/register-study.elf absent)')
erase_body = reset[reset.index('EraseSignature{'):].split('};', 1)[0]
erase_sig = bytes(int(x,16) for x in re.findall(r'0x([0-9A-Fa-f]{2})', erase_body))
setup += 'const u8 eraseSig[]={'+','.join(str(b) for b in erase_sig)+'};\n'
setup += 'std::memcpy((void*)(image_base+0x17e1d90),eraseSig,sizeof(eraseSig));\n'
fixture = fixture.replace('NATIVE_CODE_SETUP', setup)
with tempfile.TemporaryDirectory(prefix='bbsc-death-status-') as temp:
    path = Path(temp)
    cpp, exe = path/'test.cpp', path/'test.exe'
    cpp.write_text(fixture, encoding='utf-8')
    compiler = os.environ.get('CXX', 'C:/msys64/clang64/bin/clang++.exe')
    subprocess.run([compiler, '-std=c++20', str(cpp), '-o', str(exe)], check=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(exe)], env=env, check=True, timeout=10)
print('PASS: three host/guest lives, death-category policy, native resistance reset, persistent effects, guards and malformed lists')
