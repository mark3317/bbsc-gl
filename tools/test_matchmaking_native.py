from pathlib import Path
import subprocess, os
root=Path(__file__).resolve().parents[1]
s=(root/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(name):
 a=s.index(name);a=s.rfind('\n',0,a)+1;begin=s.index('{',a);depth=1;i=begin+1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
fixture=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
#include <string_view>
#include <iostream>
#include <array>
#include <algorithm>
#include <cmath>
#include <limits>
using u64=uint64_t;using u32=uint32_t;using s32=int32_t;using s64=int64_t;
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
enum class MemoryProt { CpuWrite };
std::vector<unsigned char> image(0x0556e800),manager(0x20),info(0x9c0),network(0xc58),broker(0x194);
u64 image_base=(u64)image.data(); constexpr u64 SummonManagerRootPointerOffset=0x0553B120;
constexpr u64 RoleMetadataTableOffset=0x0553D750,RoleMetadataStride=0x80,SummonBuildRoleTableOffset=0x0556E560;
bool ReadablePointer(u64 p,size_t n){for(auto* v:{&image,&manager,&info,&network,&broker})if(p>=(u64)v->data()&&p+n<=(u64)v->data()+v->size())return true;return false;}
bool HasMemoryAccess(u64 p,size_t n,MemoryProt){return ReadablePointer(p,n);}
template<class T>T ReadValue(u64 p,size_t off){T v{};if(ReadablePointer(p+off,sizeof(v)))std::memcpy(&v,(void*)(p+off),sizeof(v));return v;}
template<class T>bool WriteValue(u64 p,size_t off,T v){if(!ReadablePointer(p+off,sizeof(v)))return false;std::memcpy((void*)(p+off),&v,sizeof(v));return true;}
s32 state=0;bool foreign=false,effect=false,erase_ok=true;s64 now=1000;int notices=0,erases=0;
s32 GetSessionState(){return state;}bool BbscInAnotherWorld(){return foreign;}u64 BbscLocalEffectNode(int id){assert(id==9000);return effect;}
s64 SteadyNowMs(){return now;}bool BbscEraseLocalEffect(int id){assert(id==9000);++erases;if(erase_ok)effect=false;return erase_ok;}
const char16_t* BbscL(const char16_t* text,const char16_t*){return text;}
void BbscAnnounce(const char16_t*,std::string_view what){assert(what=="host search ended");++notices;}
'''
fixture+=function('bool ConfigureBbscSummonPolling()')+'\n'+function('void TickBbscHostSearchLimit()')
fixture+=r'''
int main(){
 assert(!ConfigureBbscSummonPolling());
 WriteValue<u64>(image_base,0x05540288,(u64)manager.data());WriteValue<u64>((u64)manager.data(),0x18,(u64)info.data());
 WriteValue<u64>(image_base,SummonManagerRootPointerOffset,(u64)network.data());WriteValue<u64>((u64)network.data(),0xc50,(u64)broker.data());
 WriteValue<u32>((u64)info.data(),0x89c,30);WriteValue<u32>((u64)info.data(),0x8a0,35);WriteValue<u32>((u64)info.data(),0x8a4,60);
 WriteValue<float>((u64)broker.data(),0x190,30);
 WriteValue<u32>((u64)info.data(),0x8c8,60);
 for(u32 role=0;role<34;++role){
  auto meta=image_base+RoleMetadataTableOffset+role*RoleMetadataStride;
  auto backoff=image_base+SummonBuildRoleTableOffset+role*12;
  WriteValue<float>(meta,0x18,60);
  WriteValue<unsigned char>(backoff,0,3);
  WriteValue<float>(backoff,4,55);
  WriteValue<float>(backoff,8,900);
 }
 assert(ConfigureBbscSummonPolling());
 for(auto off:{0x89c,0x8a4})assert(ReadValue<u32>((u64)info.data(),off)==2);
 assert(ReadValue<u32>((u64)info.data(),0x8a0)==1);
 assert(ReadValue<float>((u64)broker.data(),0x190)==2);
 assert(ReadValue<u32>((u64)info.data(),0x8c8)==2);
 for(u32 role=0;role<34;++role){
  bool coop=role==7||(role>=21&&role<=24);
  auto meta=image_base+RoleMetadataTableOffset+role*RoleMetadataStride;
  auto backoff=image_base+SummonBuildRoleTableOffset+role*12;
  assert(ReadValue<float>(meta,0x18)==(coop?2:60));
  assert(ReadValue<float>(backoff,4)==(coop?2:55));
  assert(ReadValue<unsigned char>(backoff,0)==3&&ReadValue<float>(backoff,8)==900);
 }
 // Do not continually restart a countdown or increase a disabled/expired one.
 auto retry=image_base+SummonBuildRoleTableOffset+7*12;
 for(float remaining:{1.f,0.f,-0.1f}){
  WriteValue<float>(retry,4,remaining);assert(ConfigureBbscSummonPolling());
  assert(ReadValue<float>(retry,4)==remaining);
 }
 WriteValue<float>(retry,4,std::numeric_limits<float>::quiet_NaN());
 assert(ConfigureBbscSummonPolling()&&std::isnan(ReadValue<float>(retry,4)));
 WriteValue<u32>((u64)info.data(),0x89c,0xffffffff);assert(!ConfigureBbscSummonPolling());
 effect=true;TickBbscHostSearchLimit();now+=299999;TickBbscHostSearchLimit();assert(effect&&notices==0);
 ++now;erase_ok=false;TickBbscHostSearchLimit();assert(effect&&notices==0);
 erase_ok=true;state=3;TickBbscHostSearchLimit();assert(!effect&&notices==1&&state==3);
 TickBbscHostSearchLimit();assert(notices==1);
 effect=true;TickBbscHostSearchLimit();now+=10000;effect=false;TickBbscHostSearchLimit();
 effect=true;TickBbscHostSearchLimit();now+=299999;TickBbscHostSearchLimit();assert(effect&&notices==1);
 ++now;TickBbscHostSearchLimit();assert(!effect&&notices==2);
 state=6;effect=true;TickBbscHostSearchLimit();now+=400000;TickBbscHostSearchLimit();assert(effect&&notices==2);
 state=0;foreign=true;TickBbscHostSearchLimit();assert(effect&&notices==2);
 std::cout<<"PASS: native polling and co-op retry guard/cache/countdowns, other roles and observation windows preserved, no countdown reset, invalid pointers/settings, 300s bell boundary, erase retry, party preserved\n";
}
'''
build=root/'build';cpp=build/'test_matchmaking_native.cpp';exe=build/'test_matchmaking_native.exe';cpp.write_text(fixture,encoding='utf-8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe','-std=c++20',str(cpp),'-o',str(exe)],check=True)
env=dict(os.environ);env['PATH']='C:/msys64/clang64/bin;'+env.get('PATH','')
subprocess.run([str(exe)],check=True,env=env)
