"""Production resident-completion policy plus exact native drain and selection gate."""
from pathlib import Path
import os
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
s = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a = s.index('void CompleteBbscResidentSummons(')
b = s.index('\n}', a)+2
policy = s[a:b]
NATIVE = "554889e5415741564155415453504989fe488d051834cc03488b004c8b60084d85e47407413974241074524c8b601031c96666666666662e0f1f8400000000004d85e4740741397424107431ffc14981c4a006000083f9047ce6488b402031c94c8b24c84d85e474074139742410740d48ffc183f9287ce8e920010000498b8424c0050000488b004885c074038b400c498b86c00100004c8b384939c70f84fa00000031c94c8d2da459cc03498b9424880600004c89fb660f1f8400000000004c8b7b1049395758750e498b7760493bb424900600007418488b1b4839c375e0e99e00000066662e0f1f840000000000490fbe4f08c5f857c04883f921770b48c1e107c4c17a10440d20c4c17a1186100200004d85ff74234c89ffe800398000488b084889c74c89feff517048c7431000000000498b86c00100004c8b3b4839c37430488b43084c8938488b03488b4b0848894808498bbed0010000488b074889deff507049ff8ec8010000498b9ec0010000b1014889d84939df0f852bffffffeb0484c974164c89f74883c4085b415c415d415e415f5de943f9ffff4883c4085b415c415d415e415f5dc3"
GATE = "488b8d10f9ffff4883b9c8010000007574c5fa108110020000c5f057c9c5f82ec17762"
fixture = r'''
#include <windows.h>
#include <array>
#include <vector>
#include <cassert>
#include <cstring>
#include <cstdint>
#include <cstdio>
#include "core/cpu_patches.h"
using u8=uint8_t;using u32=uint32_t;using s32=int32_t;using u64=uint64_t;
#define LOG_INFO(...)
u64 image_base=0,status,session,global,world,local,player,data,task,entries,head,node,req,allocator,vtable,task2;
constexpr u64 CandidateLocalStatePointerOffset=0x0553E878,MemberIdEqualsOffset=0x00CA1C70;
bool enabled=true,quit=false,title=false,valid_member=true;int hp=100,type=1,role=7,slot_type=1,free_calls=0,updates=0;
template<class T>T ReadValue(u64 p,size_t n){T v;memcpy(&v,(void*)(p+n),sizeof(v));return v;}
template<class T>void put(u64 p,size_t n,T v){memcpy((void*)(p+n),&v,sizeof(v));}
bool ReadablePointer(u64 p,size_t n){return p>=image_base&&n<=0x5600000&&p-image_base<=0x5600000-n;}
bool BbscHuntersEnabled(){return enabled;}bool BbscQuitInProgress(){return quit;}bool BbscReturningToTitle(){return title;}
u64 GetMatchingState(){return session;}u64 GetGlobalState(){return global;}u64 GetLocalPlayerCharacter(){return local;}
int GetCharacterHp(u64){return hp;}int GetCharacterType(u64){return type;}
bool IsValidMemberId(u64){return valid_member;}
std::vector<u64> GetMultiPlayerInsTasks(){return {task};}
struct Slot{int type,role;};Slot GetMemberSlotInfo(u64){return {slot_type,role};}
bool PS4_SYSV_ABI equals(u64 a,u64 b){return ReadValue<u64>(a,0)==ReadValue<u64>(b,0);}
u64 PS4_SYSV_ABI get_data(u64){return data;}
u64 PS4_SYSV_ABI get_allocator(u64){return allocator;}
void PS4_SYSV_ABI free_native(u64,u64 p){assert(p==req||p==node);++free_calls;}
void PS4_SYSV_ABI update_native(u64 p){assert(p==status);++updates;}
POLICY
void copy(u64 p,std::vector<u8> v){memcpy((void*)p,v.data(),v.size());}
void jump(u64 p,u64 target){std::vector<u8> b={0x48,0xb8};for(int i=0;i<8;++i)b.push_back(target>>(i*8));b.insert(b.end(),{0xff,0xe0});copy(p,b);}
void rel(std::vector<u8>& b,u64 addr,u64 to){b.push_back(0xe8);s32 d=s32(to-(addr+b.size()+4));for(int i=0;i<4;++i)b.push_back(u32(d)>>(8*i));}
int main(){
 image_base=(u64)VirtualAlloc(nullptr,0x5600000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);assert(image_base);
 status=image_base+0x10000;session=image_base+0x11000;global=image_base+0x12000;world=image_base+0x14000;
 local=image_base+0x15000;player=image_base+0x16000;data=image_base+0x17000;task=image_base+0x18000;entries=image_base+0x19000;
 head=image_base+0x1a000;node=image_base+0x1b000;req=image_base+0x1c000;allocator=image_base+0x1d000;vtable=image_base+0x1e000;
 copy(image_base+0x1877d00,{NATIVE});copy(image_base+0x18731a8,{GATE});
 jump(image_base+MemberIdEqualsOffset,(u64)equals);jump(image_base+0x207b720,(u64)get_allocator);jump(image_base+0x18777e0,(u64)update_native);
 // The original queue/cooldown gate reads SosStatus from its frame, not the candidate manager in RAX.
 copy(image_base+0x18731cb,{0xb8,1,0,0,0,0xc3});copy(image_base+0x187322d,{0x31,0xc0,0xc3});
 u64 entry=image_base+0x1000;std::vector<u8> bridge={0x55,0x48,0x81,0xec,0,7,0,0,0x48,0x8d,0xac,0x24,0xf0,6,0,0,
  0x48,0x89,0xbd,0x10,0xf9,0xff,0xff};
 rel(bridge,entry,image_base+0x18731a8);bridge.insert(bridge.end(),{0x48,0x81,0xc4,0,7,0,0,0x5d,0xc3});copy(entry,bridge);
 using Gate=u32 PS4_SYSV_ABI(*)(u64);auto ready=(Gate)entry;
 put(image_base+CandidateLocalStatePointerOffset,0,world);put(world,0x30,s32{1});put(world,0x38,entries);put(entries,0,player);
 jump(image_base+0x4000,(u64)get_data);put(player,0,vtable);put(vtable,0x1c8,image_base+0x4000);put(player,0x3d8,u64{42});put(task,0xc8,u64{42});
 put(allocator,0,vtable);put(vtable,0x70,(u64)free_native);put(status,0x1d0,allocator);
 // Exact native lookup: remote PlayerGameData slot, by its game id at +10.
 u64 slots=image_base+0x20000;put(image_base+0x553b130,0,slots);put(slots,0x10,data);put(slots,0x20,image_base+0x24000);
 put(data,0x10,s32{10001});put(data,0x5c0,image_base+0x25000);
 put(data,0x688,u64{123456});put(data,0x690,u64{987654});
 auto reset=[&]{
  enabled=true;quit=title=false;hp=100;type=slot_type=1;role=7;valid_member=true;free_calls=updates=0;
  put(session,0x124,s32{3});put(global,8,u8{0});put(global,0x1592,u8{1});
  put(task,0xe8,s32{1});put(task,0x50,s32{6});put(task,0x54,s32{6});put(task,0xed,u8{12});
  put(player,0x3d8,u64{42});put(status,0x1c0,head);put(status,0x1c8,u64{1});put(status,0x210,0.0f);
  put(head,0,node);put(head,8,node);put(node,0,head);put(node,8,head);put(node,0x10,req);
  put(req,8,u8{7});put(req,0x58,u64{123456});put(req,0x60,u64{987654});
  put(image_base+0x553d750+7*0x80,0x20,0.25f);
 };
 reset();assert(ready(status)==0); // already created guest still holds the original native selection gate
 CompleteBbscResidentSummons(status);
 assert(ReadValue<u64>(status,0x1c8)==0&&ReadValue<u64>(head,0)==head&&ReadValue<u64>(head,8)==head);
 assert(free_calls==2&&updates==1); // original native destructors/unlink/counter/update, exactly once
 assert(ReadValue<float>(status,0x210)==0.25f&&ready(status)==0); // original post-completion backoff retained
 put(status,0x210,0.0f);assert(ready(status)==1);CompleteBbscResidentSummons(status);assert(free_calls==2&&updates==1);
 // Incomplete insertion, departing member, wrong role/member/account/character never complete.
 for(int scenario=0;scenario<20;++scenario){
  reset();switch(scenario){
   case 0:enabled=false;break;case 1:quit=true;break;case 2:title=true;break;
   case 3:put(session,0x124,s32{6});break;case 4:put(global,8,u8{1});break;
   case 5:put(global,0x1592,u8{0});break;case 6:hp=0;break;
   case 7:put(task,0x50,s32{3});break;case 8:put(task,0x54,s32{8});break;
   case 9:put(task,0xed,u8{14});break;case 10:put(task,0xe8,s32{0});break;
   case 11:type=2;break;case 12:slot_type=2;break;case 13:role=8;break;
   case 14:valid_member=false;break;case 15:put(player,0x3d8,u64{99});break;
   case 16:put(req,0x58,u64{111});break;case 17:put(req,0x60,u64{111});break;
   case 18:put(req,8,u8{8});break;case 19:put(status,0x1c8,u64{5});break;
  }
  CompleteBbscResidentSummons(status);assert(free_calls==0&&updates==0&&ready(status)==0);
 }
 for(int coop_role:{7,21,22,23,24}){
  reset();role=coop_role;put(req,8,u8(coop_role));put(image_base+0x553d750+coop_role*0x80,0x20,0.25f);
  CompleteBbscResidentSummons(status);assert(free_calls==2&&updates==1&&ReadValue<u64>(status,0x1c8)==0);
 }
 reset();u64 other_node=image_base+0x26000,other_req=image_base+0x27000;
 put(node,0,other_node);put(other_node,0,head);put(other_node,8,node);put(other_node,0x10,other_req);put(head,8,other_node);
 put(other_req,8,u8{7});put(other_req,0x58,u64{999});put(other_req,0x60,u64{888});put(status,0x1c8,u64{2});
 CompleteBbscResidentSummons(status);
 assert(free_calls==2&&updates==1&&ReadValue<u64>(status,0x1c8)==1);
 assert(ReadValue<u64>(head,0)==other_node&&ReadValue<u64>(other_node,8)==head&&ReadValue<u64>(other_node,0x10)==other_req);
 put(status,0x210,0.0f);assert(ready(status)==0); // another unfinished request still blocks admission
 // A native signature mismatch cannot call a different function.
 reset();put(image_base+0x1877d00,0,u8{0x90});CompleteBbscResidentSummons(status);assert(free_calls==0);
 puts("PASS: production policy + exact native identity-bound completion/unlink/free/backoff and queue/ready gate; five roles, unrelated pending retained, 21 rejection cases");
}
'''.replace('POLICY',policy).replace('NATIVE',','.join(hex(b) for b in bytes.fromhex(NATIVE))).replace('GATE',','.join(hex(b) for b in bytes.fromhex(GATE)))
with tempfile.TemporaryDirectory(prefix='bbsc-resident-summon-') as tmp:
    cpp,exe=Path(tmp)/'test.cpp',Path(tmp)/'test.exe'
    cpp.write_text(fixture,encoding='utf-8')
    subprocess.run([os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe'),'-std=c++20','-O0','-DNOMINMAX','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=10,env={**os.environ,'PATH':'C:/msys64/clang64/bin;'+os.environ.get('PATH','')})
