"""Production host altar view -> Dream delta -> home restore, allocated memory only.

No real saves, journals or game processes are read or written.
"""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

import test_world_altars_native as altars

ROOT = altars.ROOT
SOURCE = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')


def function(signature, source=SOURCE):
    start = source.index(signature + ' {')
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


def code():
    prefix = altars.PREFIX.replace(
        'void KeepBbscOwnWorldGroup(u32 key,const u8* p){if(!own_kept.contains(key))std::memcpy(own_kept[key].data(),p,125);}',
        '')
    prefix += r'''
#include <bit>
#include <filesystem>
#include <optional>
#include <string_view>
constexpr size_t BbscWorldGroupBytes=125;
auto& bbsc_own_world=own_kept;bool bbsc_own_world_dirty=false;
std::optional<int> bbsc_own_world_slot;
std::filesystem::path BbscOwnWorldPath(int){assert(false);return {};}
bool BbscHomeForOwnWorld(){return session!=4&&session!=6;}
constexpr u32 BbscOwnTimeKey=0xFFFF9800,BbscTimeGroupKey=9;
constexpr size_t BbscTimeByte=100;constexpr u8 BbscTimeMask=0xE0;
template<class T>void WriteValue(u64 p,size_t o,T v){std::memcpy(reinterpret_cast<void*>(p+o),&v,sizeof(v));}
'''
    keys = SOURCE[SOURCE.index('constexpr std::array<u32, 57> BbscDreamStateKeys{'):SOURCE.index('constexpr size_t BbscDreamChunkCount')]
    dream = SOURCE[SOURCE.index('struct BbscDreamOwnState {'):SOURCE.index('// The Dream\'s shops')]
    shops = SOURCE[SOURCE.index('constexpr u32 BbscDreamSoldGroup'):SOURCE.index('// Puts the guest\'s own shop flags')]
    section = altars.SOURCE[altars.SOURCE.index('struct BbscWorldAltar {'):altars.SOURCE.index('struct BbscWorldState {')]
    return prefix + keys + dream + shops + ''.join(function(s) for s in (
        'bool BbscIsMapFlagGroup(u32 key)',
        'void KeepBbscOwnWorldGroup(u32 key, const u8* live)',
        'size_t KeepBbscOwnDreamShopFlags(size_t index, u8* live)',
        'void NoteBbscOwnDreamRestored(u32 key, const u8* live)',
        'void RestoreBbscOwnDreamState(std::string_view why)',
        'size_t RestoreBbscOwnWorld(std::string_view why)',
    )) + section + r'''
int main(){
 image_base=1; // restoration requires an initialized module; no native calls here
 for(int slot=0;slot<7;++slot)for(int change=0;change<3;++change){
  groups.clear();own_kept.clear();bbsc_dream_own={};session=6;bbsc_world_catalog_ready=true;
  for(int s=0;s<7;++s)for(int j=0;j<6;++j)groups[94000+s*100+j]={};
  const u32 key=94005+slot*100;
  groups[key][62]=0x80; // 94x05500: personal model present
  groups[key][12]=0x80; // 94x05100: personal cup kind
  groups[94000+slot*100][0]=29; // personal ritual remains functional
  groups[7][0]=0;groups[70009][0]=3;groups[12100][0]=0xA5;
  const auto personal=groups;
  for(size_t i=0;i<BbscDreamGroupCount;++i){
   const u32 k=BbscDreamStateKeys[i];if(!groups.contains(k))continue;
   KeepBbscOwnWorldGroup(k,groups[k].data());
   bbsc_dream_own.held|=u64{1}<<i;bbsc_dream_own.own[i]=groups[k];
   bbsc_dream_own.written[i]=groups[k]; // initial host view matches personal cup
  }
  for(int s=0;s<7;++s)for(int j=0;j<6;++j)
   std::memcpy(bbsc_world_altars[s].entry.record.data()+j*125,groups[94000+s*100+j].data(),125);
  auto& record=bbsc_world_altars[slot].entry.record;
  if(change==0)record.fill(0); // host removes same-slot ritual
  if(change==1){record[625+62]=0x10;record[625+12]=0x08;} // replaces cup kind/model
  assert(BbscWorldApplyAltars(BbscDreamStateMap));
  if(change==2)groups[key][62]=0; // native event changed the borrowed view
  groups[7][0]=0x40; // unrelated personal Dream edit must survive
  groups[70009][0]=4; // purchase count must survive
  groups[12100][0]=0;KeepBbscOwnWorldGroup(12100,personal.at(12100).data());
  session=0;assert(RestoreBbscOwnWorld("fixture home")>0);
  for(int s=0;s<7;++s)for(int j=0;j<6;++j){const u32 k=94000+s*100+j;assert(groups[k]==personal.at(k));}
  assert(groups[key][62]==0x80&&groups[key][12]==0x80);
  assert(groups[94000+slot*100][0]==29);
  assert(groups[7][0]==0x40&&groups[70009][0]==4&&groups[12100][0]==0xA5);
 }
 // The local travel/selector group is not an altar record.
 own_kept[9]={};std::array<u8,125> changed{};changed[0]=0x42;
 NoteBbscOwnDreamRestored(9,changed.data());assert(own_kept[9]==changed);
}
'''


def run(negative=False):
    text = code()
    if negative:
        text = text.replace('BbscIsMapFlagGroup(key) || (key >= 94000 && key < 94700)', 'BbscIsMapFlagGroup(key)')
    compiler = os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-altar-model-') as tmp:
        cpp=Path(tmp)/'model.cpp';exe=Path(tmp)/'model.exe';cpp.write_text(text,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        result=subprocess.run([str(exe)],env=env,capture_output=True)
        assert (result.returncode!=0) if negative else (result.returncode==0), result.stderr.decode(errors='replace')
    print('PASS old policy rejected' if negative else 'PASS seven personal altar models/kinds/records restored after host removal/replacement/native changes; Dream edits/purchases retained')


def assets():
    if not os.environ.get('BBSC_TEST_GAME'):
        return
    import sys
    sys.path.insert(0,str(ROOT/'tools/gamedata'))
    from emevd import Emevd
    events=dict(Emevd(Path(os.environ['BBSC_TEST_GAME'])/'event/m21_00_00_00.emevd.dcx').events)
    for slot in range(7):
        instructions=events[12105010+slot]
        assert (2005,3,struct.pack('<II',2101200+slot*10,1)) in instructions
        assert any(bank==3 and iid==0 and struct.unpack_from('<I',args,4)[0]==94005500+slot*100000 for bank,iid,args in instructions)
    print('PASS original 1.09 seven altar model events consume personal ritual display flags')


if __name__=='__main__':
    run();run(negative=True);assets()
