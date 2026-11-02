from pathlib import Path
import subprocess, os
root = Path(__file__).resolve().parents[1]
s = (root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
def section(a,b): return s[s.index(a):s.index(b,s.index(a))]
fixture = r'''#include <cstdint>
#include <cstring>
#include <cassert>
#include <array>
using u8=uint8_t; using u16=uint16_t; using u32=uint32_t; using u64=uint64_t; using s32=int32_t;
#define PS4_SYSV_ABI
struct GuestRegisterSnapshot {u64 rbp,rcx;};
struct BbscShopLineupRow {u8 bytes[32];};
u64 image_base=0x100000, ShopListGetReturnOffset=0x200;
bool ReadablePointer(u64 p,size_t){return p!=0;}
template<class T>T ReadValue(u64 p,size_t o){T v;memcpy(&v,(void*)(p+o),sizeof v);return v;}
template<class T>void put(void* p,size_t o,T v){memcpy((u8*)p+o,&v,sizeof v);}
''' + section('constexpr bool BbscIsKitGoods(', 'void PS4_SYSV_ABI BbscShopListHook') + section('bool BbscIsNativeKitLot(', 'void PS4_SYSV_ABI BbscGuestAwardHook') + r'''
int main(){
 std::array<u8,148> row{};
 assert(!BbscIsNativeKitLot(0)); assert(!BbscIsNativeKitLot((u64)row.data()));
 for(u32 id:{200,205,225,111}){
  row.fill(0); put(row.data(),0,(s32)id);put(row.data(),0x20,4u);put(row.data(),0x40,(u16)100);
  assert(BbscIsNativeKitLot((u64)row.data()));
  put(row.data(),4,(s32)120);put(row.data(),0x24,4u);put(row.data(),0x42,(u16)100);
  assert(!BbscIsNativeKitLot((u64)row.data())); // mixed Notebook reward preserved
  put(row.data(),0x42,(u16)0); assert(BbscIsNativeKitLot((u64)row.data()));
  put(row.data(),0x20,0u);assert(!BbscIsNativeKitLot((u64)row.data()));
 }
 u64 frame[2]={0,image_base+ShopListGetReturnOffset};
 std::array<u8,32> shop{};
 for(u32 id:{200,205,225,111,120,130}){
  put(shop.data(),0,id);put(shop.data(),0x17,(u8)3);
  GuestRegisterSnapshot r{(u64)frame,(u64)shop.data()};
  BbscShopLineupResultHook(0,&r);assert((r.rcx==0)==BbscIsKitGoods(id));
  put(shop.data(),0x17,(u8)0);r.rcx=(u64)shop.data();
  BbscShopLineupResultHook(0,&r);assert(r.rcx==(u64)shop.data());
 }
 frame[1]++;put(shop.data(),0,200u);put(shop.data(),0x17,(u8)3);
 GuestRegisterSnapshot r{(u64)frame,(u64)shop.data()};BbscShopLineupResultHook(0,&r);assert(r.rcx==(u64)shop.data());
 BbscShopLineupResultHook(0,nullptr);
}
'''
build=root/'build';build.mkdir(exist_ok=True)
cpp=build/'test_native_kit_sources.cpp';exe=cpp.with_suffix('.exe');cpp.write_text(fixture,encoding='utf8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20',str(cpp),'-o',str(exe)],check=True)
env=dict(os.environ);env['PATH']='C:/msys64/clang64/bin;'+env.get('PATH','')
subprocess.run([str(exe)],env=env,check=True)
print('PASS: native kit lots and shop filtering; mixed/unrelated/category/caller cases preserved')
