"""Production selector hook + exact native scan/consume and builder cooldown."""
from pathlib import Path
import os, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
a=s.index('void ApplyBbscSummonRoleDelayMask(')
b=s.index('\n}',a)+2
hook=s[a:b]
# 01873269..018732E5 (scan, role mask test, state=1, prepared load).
scan=bytes.fromhex('488b80a8010000488b084839c14c8bbd10f9ffff0f8444010000488d15c6a4cc03660f1f440000488b71104885f674378a5e1080cb0280fb02752c488b3e4885ff7424480fbe7f0831db4883ff21770848c1e7078b5c3a044185dd7517662e0f1f840000000000488b094839c175b8e9ea000000c64610014c8b7608')
# 01874740..0187476F (actual enabled/countdown/destructive-reject guard).
backoff=bytes.fromhex('450fb658224b8d045b488d0d109ecf03803c81007419c5fa10448104c5f057c9c5f82ec176094584d20f8456090000')
fixture=r'''
#include <windows.h>
#include <array>
#include <cassert>
#include <cmath>
#include <cstring>
#include <limits>
#include <vector>
#include "core/cpu_patches.h"
#include "bbsc_summon_admission.h"
using Core::GuestRegisterSnapshot;
#define LOG_INFO(...)
u64 image_base=0; bool enabled=true, readable=true;
namespace BbscMod { void LogPlain(const char*){} u64 EbootAddress(){return image_base;} }
BbscMod::SummonAdmission admission;
bool BbscMod::PartySummonSelectionBlocked(){return admission.Blocked();}
constexpr u64 RoleMetadataTableOffset=0x0553D750,RoleMetadataStride=0x80,SummonBuildRoleTableOffset=0x0556E560;
bool BbscHuntersEnabled(){return enabled;}
bool ReadablePointer(u64 p,size_t n){return readable&&p>=image_base&&p+n<=image_base+0x5600000;}
template<class T>T ReadValue(u64 p,size_t off){T v;std::memcpy(&v,reinterpret_cast<void*>(p+off),sizeof(v));return v;}
#define BBSC_MOD
HOOK
#undef BBSC_MOD
void PS4_SYSV_ABI adapter(u64,const GuestRegisterSnapshot* regs){ApplyBbscSummonRoleDelayMask(regs);}
template<class T>void put(u64 p,size_t off,T v){std::memcpy(reinterpret_cast<void*>(p+off),&v,sizeof(v));}
void bytes(u64 p,const std::vector<u8>& v){std::memcpy(reinterpret_cast<void*>(p),v.data(),v.size());}
void relcall(std::vector<u8>& v,u64 base,u64 target){v.push_back(0xe8);s32 d=static_cast<s32>(target-(base+v.size()+4));for(int i=0;i<4;++i)v.push_back(static_cast<u32>(d)>>(i*8));}
int main(){
 image_base=reinterpret_cast<u64>(VirtualAlloc(nullptr,0x5600000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE));assert(image_base);
 u64 scan=image_base+0x1873269,build=image_base+0x1874740;
 bytes(scan,{SCAN}); bytes(build,{BACKOFF});
 // Return item after the native state write; otherwise return zero at native no-match.
 bytes(image_base+0x18732e5,{0x48,0x89,0xf0,0xc3});bytes(image_base+0x18733c7,{0x31,0xc0,0xc3});
 bytes(image_base+0x187476f,{0xb8,1,0,0,0,0xc3});bytes(image_base+0x18750c5,{0x31,0xc0,0xc3});
 // ABI bridge only: preserve callee registers, establish native frame/RAX/R13, call scan.
 u64 entry=image_base+0x1000;
 std::vector<u8> bridge={0x55,0x53,0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57,
  0x48,0x81,0xec,8,7,0,0,0x48,0x8d,0xac,0x24,0xf0,6,0,0,
  0x48,0xc7,0x04,0x24,0,0,0,0,0x48,0x89,0xf8,0x49,0x89,0xf5};
 relcall(bridge,entry,scan);
 const u8 epilogue[]={0x48,0x81,0xc4,8,7,0,0,0x41,0x5f,0x41,0x5e,0x41,0x5d,0x41,0x5c,0x5b,0x5d,0xc3};
 bridge.insert(bridge.end(),std::begin(epilogue),std::end(epilogue));bytes(entry,bridge);
 // Fifth SysV argument already is R8 (prepared); leave destructive flag R10 at zero.
 u64 builder_entry=image_base+0x1100;
 std::vector<u8> builder_bridge={0x45,0x31,0xd2};relcall(builder_bridge,builder_entry,build);builder_bridge.push_back(0xc3);bytes(builder_entry,builder_bridge);
 using Scan=u64 PS4_SYSV_ABI (*)(u64,u64);auto select=reinterpret_cast<Scan>(entry);
 using Build=u64 PS4_SYSV_ABI (*)(u64,u64,u64,u64,u64);auto construct=reinterpret_cast<Build>(builder_entry);
 // Real pending list: the first guest is already consumed; next guest is waiting.
 alignas(16) u8 manager[0x1b0]{},head[0x18]{},n1[0x18]{},n2[0x18]{},first[0x28]{},second[0x28]{},c1[0x10]{},c2[0x10]{},prepared[0xa8]{};
 u64 m=(u64)manager,h=(u64)head,a=(u64)n1,b=(u64)n2,f=(u64)first,t=(u64)second;
 put(m,0x1a8,h);put(h,0,a);put(a,0,b);put(b,0,h);put(a,0x10,f);put(b,0x10,t);
 put(f,0,(u64)c1);put(f,8,(u64)prepared);put(f,0x10,u8{1});put(t,0,(u64)c2);put(t,8,(u64)prepared);
 for(u32 role:{7u,21u,22u,23u,24u})put(image_base+RoleMetadataTableOffset+role*0x80,4,u32{1}<<role);
 auto reset=[&](u32 role,float delay,u8 active=1){
  put((u64)c1,8,u8(role));put((u64)c2,8,u8(role));put((u64)prepared,0x22,u8(role));
  put(t,0x10,u8{0});auto back=image_base+SummonBuildRoleTableOffset+role*12;
  put(back,0,active);put(back,4,delay);
 };
 // Unpatched game consumes B during A's cooldown, rejects it, and never selects B again.
 reset(7,1.5f);assert(select(m,1u<<7)==t);assert(second[0x10]==1);
 assert(construct(0,0,0,0,(u64)prepared)==0);
 put(image_base+SummonBuildRoleTableOffset+7*12,4,0.0f);assert(select(m,1u<<7)==0);
 const u8 prologue[]={0x48,0x8b,0x80,0xa8,1,0,0};
 assert(Core::InstallGuestCodeHook(reinterpret_cast<void*>(scan),std::span<const u8>{prologue},0,adapter));
 for(u32 role:{7u,21u,22u,23u,24u}){
  put(image_base+SummonBuildRoleTableOffset+role*12,8,u32{0xdeadbeef});
  reset(role,1.5f);assert(select(m,1u<<role)==0&&second[0x10]==0&&first[0x10]==1);
  // Timer is not shortened, role counters/observation window are untouched.
  auto back=image_base+SummonBuildRoleTableOffset+role*12;
  assert(ReadValue<float>(back,4)==1.5f);
  assert(ReadValue<u8>(back,0)==1&&ReadValue<u32>(back,8)==0xdeadbeef);
  put(back,4,0.0f);assert(select(m,1u<<role)==t&&second[0x10]==1);
  assert(construct(0,0,0,0,(u64)prepared)==1);assert(select(m,1u<<role)==0);
  for(float delay:{-1.0f,0.0f,std::numeric_limits<float>::quiet_NaN()}){
   reset(role,delay);assert(select(m,1u<<role)==t);
  }
  reset(role,1.0f,0);assert(select(m,1u<<role)==t); // disabled guard is native eligible
  reset(role,1.0f);assert(select(m,0)==0&&second[0x10]==0); // don't expand native masks
  put(t,0x10,u8{2});assert(select(m,1u<<role)==0&&second[0x10]==2);
  put(back,4,0.0f);assert(select(m,1u<<role)==t&&second[0x10]==1); // renewed generation also waits
  put(back,0,u8{0});
 }
 // Other roles, feature-off and unreadable table keep the original behavior.
 reset(8,1.5f);put(image_base+RoleMetadataTableOffset+8*0x80,4,u32{1}<<8);assert(select(m,1u<<8)==t);
 reset(8,1.5f);put(image_base+SummonBuildRoleTableOffset+7*12,0,u8{1});
 put(image_base+SummonBuildRoleTableOffset+7*12,4,1.5f);
 assert(select(m,(1u<<7)|(1u<<8))==t); // delayed co-op doesn't block another eligible role
 reset(7,1.5f);enabled=false;assert(select(m,1u<<7)==t);enabled=true;
 reset(7,1.5f);readable=false;assert(select(m,1u<<7)==t);readable=true;
 // Cached co-op candidate survives a busy Party response, even with no native cooldown.
 admission.BeginSearch(10); admission.Read(10,"{\"MessageId\":\"legacy\"}");
 admission.BeginClaim(11); assert(!admission.Blocked()); admission.Finish(11);
 admission.BeginSearch(12); admission.Read(12,"{\"BBSCAdmission"); admission.Read(12,"Ready\":1,");
 assert(!admission.Blocked());
 admission.BeginSearch(13); admission.BeginClaim(14);
 admission.Read(13,"{\"BBSCAdmissionReady\":1,"); assert(admission.Blocked());
 admission.BeginSearch(15); admission.Finish(14);
 admission.Read(15,"{\"BBSCAdmissionReady\":1,"); assert(admission.Blocked());
 admission.BeginSearch(16); admission.Read(16,"{\"BBSCAdmissionReady\":0,");
 for(u32 role:{7u,21u,22u,23u,24u}) {
  reset(role,0.0f); assert(select(m,1u<<role)==0&&second[0x10]==0);
 }
 reset(8,0.0f); assert(select(m,(1u<<7)|(1u<<8))==t);
 admission.BeginSearch(17); admission.Finish(17);
 admission.Read(17,"{\"BBSCAdmissionReady\":1,"); assert(admission.Blocked());
 admission.BeginSearch(18); admission.Read(18,"{\"BBSCAdmissionReady\":1,");
 reset(7,0.0f); assert(select(m,1u<<7)==t&&second[0x10]==1);
 GuestRegisterSnapshot regs{};regs.r13=0;ApplyBbscSummonRoleDelayMask(nullptr);
 auto saved=image_base;image_base=0;ApplyBbscSummonRoleDelayMask(&regs);image_base=saved;
}
'''.replace('HOOK',hook).replace('SCAN',','.join(hex(b) for b in scan)).replace('BACKOFF',','.join(hex(b) for b in backoff))
# Compile only the temporary regression harness, never the DLL/port/launcher/package.
with tempfile.TemporaryDirectory(prefix='bbsc-second-guest-') as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/'test.exe';cpp.write_text(fixture,encoding='utf-8')
 subprocess.run([os.environ.get('CXX','C:/msys64/clang64/bin/clang++.exe'),'-std=c++20','-O0','-DNOMINMAX','-DWIN32_LEAN_AND_MEAN','-I',str(root/'emulator/src'),'-I',str(root/'emulator/mod'),'-I',str(root/'emulator/externals/xbyak'),str(cpp),str(root/'emulator/mod/bbsc_hooks.cpp'),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True,timeout=10,
                env={**os.environ,'PATH':'C:/msys64/clang64/bin;'+os.environ.get('PATH','')})
print('Second guest: exact native scan, cooldown, cached sign and Party reply ordering: PASS')
