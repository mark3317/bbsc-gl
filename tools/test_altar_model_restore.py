"""Production host altar view -> native save and home restore, allocated memory only.

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
#include <fstream>
#include <new>
#include <optional>
#include <string_view>
#include "core/cpu_patches.h"
using Core::GuestRegisterSnapshot;
#define LOG_ERROR(...)
u8 bbsc_altar_save_skip=0;
constexpr size_t BbscWorldGroupBytes=125;
auto& bbsc_own_world=own_kept;bool bbsc_own_world_dirty=false;
std::mutex bbsc_own_world_save_mutex;
struct Slot { int slot=1; };
std::optional<Slot> bbsc_own_world_slot;
s32 save_slot=1;
s32 BbscLoadedCharacterSlot(){return save_slot;}
bool BbscReturningToTitle(){return false;}
bool BindBbscOwnWorldSlot(){if(!bbsc_own_world_slot)bbsc_own_world_slot=Slot{save_slot};return true;}
bool AlignBbscOwnWorldSlot(){return true;}
std::filesystem::path fixture_journal;
std::filesystem::path BbscOwnWorldPath(const Slot&){return fixture_journal;}
bool BbscHomeForOwnWorld(){return session!=4&&session!=6;}
enum class MemoryProt { CpuRead };
bool HasMemoryAccess(u64,size_t,MemoryProt){return true;}
void KeepBbscLocalDreamFlags(u32,const u8*,u8*,bool){}
constexpr u32 BbscOwnTimeKey=0xFFFF9800,BbscTimeGroupKey=9;
constexpr size_t BbscTimeByte=100;constexpr u8 BbscTimeMask=0xE0;
template<class T>void WriteValue(u64 p,size_t o,T v){std::memcpy(reinterpret_cast<void*>(p+o),&v,sizeof(v));}
'''
    prefix = prefix.replace(
        'u64 BbscFlagGroupStorage(u32 key){auto it=groups.find(key);return it==groups.end()?0:reinterpret_cast<u64>(it->second.data());}',
        '''
std::array<std::array<u8,125>,43> flag_bank{};
u32 missing_key=0;
u64 BbscFlagGroupStorage(u32 key){
 if(key==missing_key)return 0;
 if(Chalice::IsAltarRecordGroup(key))
  return reinterpret_cast<u64>(flag_bank[(key-94000)/100*6+key%100].data());
 auto it=groups.find(key);return it==groups.end()?0:reinterpret_cast<u64>(it->second.data());
}
''')
    keys = SOURCE[SOURCE.index('constexpr std::array<u32, 57> BbscDreamStateKeys{'):SOURCE.index('constexpr size_t BbscDreamChunkCount')]
    dream = SOURCE[SOURCE.index('struct BbscDreamOwnState {'):SOURCE.index('// The Dream\'s shops')]
    shops = 'constexpr u32 BbscDreamSoldGroup = 70009;\n'
    shops += SOURCE[SOURCE.index('constexpr std::array<u16, 130> BbscDreamShopUnlockFlags{'):
                    SOURCE.index('void MaskBbscSharedFlagGroup(u32 key, u8* outgoing) {')]
    section = altars.SOURCE[altars.SOURCE.index('struct BbscWorldAltar {'):altars.SOURCE.index('struct BbscWorldState {')]
    return prefix + keys + dream + shops + ''.join(function(s) for s in (
        'bool BbscIsMapFlagGroup(u32 key)',
        'void KeepBbscOwnWorldGroup(u32 key, const u8* live)',
        'size_t KeepBbscOwnDreamShopFlags(size_t index, u8* live)',
        'void NoteBbscOwnDreamRestored(u32 key, const u8* live)',
        'void RestoreBbscOwnDreamState(std::string_view why)',
        'void PS4_SYSV_ABI BbscSavePersonalAltars(u64, const GuestRegisterSnapshot* registers)',
        'size_t RestoreBbscOwnWorld(std::string_view why, bool native_finale = false)',
    )) + section + r'''
int main(int argc,char** argv){
 assert(argc==2);
 fixture_journal=argv[1];
 image_base=1; // restoration requires an initialized module; no native calls here
 for(int slot=0;slot<7;++slot)for(int change=0;change<4;++change){
  groups.clear();own_kept.clear();bbsc_dream_own={};session=6;bbsc_world_catalog_ready=true;
  flag_bank={};
  if(change!=3){
   flag_bank[slot*6+5][62]=0x80; // personal model
   flag_bank[slot*6+5][12]=0x80; // personal cup kind
   flag_bank[slot*6][0]=29; // occupied personal ritual
  }
  const auto personal=flag_bank;
  groups[7][0]=0;groups[70009][0]=3;groups[12100][0]=0xA5;
  for(size_t i=0;i<BbscDreamGroupCount;++i){
   const u32 k=BbscDreamStateKeys[i];const auto storage=BbscFlagGroupStorage(k);
   if(!storage)continue;
   const auto* live=reinterpret_cast<const u8*>(storage);
   KeepBbscOwnWorldGroup(k,live);
   bbsc_dream_own.held|=u64{1}<<i;
   std::memcpy(bbsc_dream_own.own[i].data(),live,125);
   bbsc_dream_own.written[i]=bbsc_dream_own.own[i];
  }
  for(int s=0;s<7;++s)for(int j=0;j<6;++j)
   std::memcpy(bbsc_world_altars[s].entry.record.data()+j*125,flag_bank[s*6+j].data(),125);
  auto& record=bbsc_world_altars[slot].entry.record;
  if(change==0)record.fill(0); // host removes same-slot ritual
  if(change==1){record[625+62]=0x10;record[625+12]=0x08;} // replaces cup kind/model
  if(change==3){record[0]=29;record[4]=0x93;record[625+62]=0x20;} // new cup over empty altar
  assert(BbscWorldApplyAltars(BbscDreamStateMap));
  if(change==2)flag_bank[slot*6+5][62]=0;
  groups[7][0]=0x40; // unrelated personal Dream edit must survive
  groups[70009][0]=4; // purchase count must survive
  KeepBbscOwnWorldGroup(12100,groups[12100].data());groups[12100][0]=0;
  flag_bank.back().fill(0x4A); // unrelated saved group must come from live data
  const auto guest_view=flag_bank;
  auto native_source=reinterpret_cast<u64>(flag_bank.data());
  Core::GuestRegisterSnapshot other{};
  other.rsi=native_source;other.rbx=sizeof(flag_bank);
  save_slot=2;
  BbscSavePersonalAltars(0,&other);
  assert(!bbsc_altar_save_skip&&other.rsi==native_source);
  save_slot=1;
  for(s32 role:{6,7,0}){
   session=role; // autosave, leaving, and native state0 before home restore
   Core::GuestRegisterSnapshot regs{};
   regs.rsi=reinterpret_cast<u64>(flag_bank.data());regs.rbx=sizeof(flag_bank);
   BbscSavePersonalAltars(0,&regs);
   assert(!bbsc_altar_save_skip&&regs.rsi!=reinterpret_cast<u64>(flag_bank.data()));
   auto saved=personal;saved.back()=guest_view.back();
   assert(std::memcmp(reinterpret_cast<const void*>(regs.rsi),saved.data(),sizeof(saved))==0);
   assert(flag_bank==guest_view);
  }
  Core::GuestRegisterSnapshot bad{};
  bad.rsi=reinterpret_cast<u64>(flag_bank.data());bad.rbx=sizeof(flag_bank)-250;
  BbscSavePersonalAltars(0,&bad);
  assert(bbsc_altar_save_skip&&bad.rsi==reinterpret_cast<u64>(flag_bank.data()));
  bbsc_altar_save_skip=0;
  missing_key=94000+slot*100;
  assert(RestoreBbscOwnWorld("flag bank missing")==0&&!own_kept.empty());
  assert(flag_bank==guest_view);missing_key=0;
  assert(RestoreBbscOwnWorld("fixture home")>0&&own_kept.empty());
  assert(std::equal(personal.begin(),personal.end()-1,flag_bank.begin()));
  assert(groups[7][0]==0x40&&groups[70009][0]==4&&groups[12100][0]==0xA5);
  Core::GuestRegisterSnapshot home{};
  home.rsi=reinterpret_cast<u64>(flag_bank.data());home.rbx=sizeof(flag_bank);
  BbscSavePersonalAltars(0,&home);
  assert(!bbsc_altar_save_skip&&home.rsi==reinterpret_cast<u64>(flag_bank.data()));
 }
 // Exercise the actual native-finale restoration, including the file
 // a later process would otherwise see as an unfinished old-world journal.
 session=6;
 own_kept.clear();bbsc_dream_own={};bbsc_own_world_slot=Slot{1};
 flag_bank[0].fill(0x11);
 KeepBbscOwnWorldGroup(94000,flag_bank[0].data());
 groups[12100].fill(0x22);
 KeepBbscOwnWorldGroup(12100,groups[12100].data());
 groups[12100].fill(0x33);
 std::ofstream(fixture_journal) << "old world";
 missing_key=94000;
 assert(RestoreBbscOwnWorld("before native ending",true)==0 && own_kept.size()==2);
 assert(groups[12100][0]==0x33 && std::filesystem::exists(fixture_journal));
 missing_key=0;
 const auto retired=std::filesystem::path(fixture_journal).concat(".restored");
 std::filesystem::create_directory(retired);
 assert(RestoreBbscOwnWorld("before native ending",true)==0 && own_kept.size()==2);
 assert(std::filesystem::exists(fixture_journal));
 std::filesystem::remove(retired);
 assert(RestoreBbscOwnWorld("before native ending",true)==2 && own_kept.empty());
 assert(!std::filesystem::exists(fixture_journal) && std::filesystem::exists(retired));
 session=0;
 groups[12100].fill(0x44);flag_bank[0].fill(0x55);
 assert(RestoreBbscOwnWorld("new cycle arrival")==0);
 assert(groups[12100][0]==0x44 && flag_bank[0][0]==0x55);
 // The local travel/selector group is not an altar record.
 own_kept[9]={};std::array<u8,125> changed{};changed[0]=0x42;
 NoteBbscOwnDreamRestored(9,changed.data());assert(own_kept[9]==changed);
}
'''


def run(negative=False):
    text = code()
    if negative:
        text = text.replace('const_cast<GuestRegisterSnapshot*>(registers)->rsi = reinterpret_cast<u64>(save_flags.data());', '')
    compiler = os.environ.get('CXX') or shutil.which('clang++') or r'C:/msys64/clang64/bin/clang++.exe'
    with tempfile.TemporaryDirectory(prefix='bbsc-altar-model-') as tmp:
        cpp=Path(tmp)/'model.cpp';exe=Path(tmp)/'model.exe';cpp.write_text(text,encoding='utf-8')
        subprocess.run([compiler,'-std=c++20','-I',str(ROOT/'emulator/src'),str(cpp),'-o',str(exe)],check=True)
        env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env.get('PATH','')
        result=subprocess.run([str(exe),str(Path(tmp)/'own-world.bin')],env=env,capture_output=True)
        assert (result.returncode!=0) if negative else (result.returncode==0), result.stderr.decode(errors='replace')
    print('PASS unprotected save rejected' if negative else 'PASS seven personal altar records in guest saves and after home restore; live guest view and unrelated flags retained')


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
