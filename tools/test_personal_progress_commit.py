"""Targeted production-function fixtures. Run explicitly before the next build.
No game process or player save is used. Requires a C++20 compiler.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import re
ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT/'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
def function(signature):
    start=SOURCE.index(signature+' {'); opening=SOURCE.index('{',start); depth=1; end=opening+1
    while depth:
        depth+=(SOURCE[end]=='{')-(SOURCE[end]=='}'); end+=1
    return SOURCE[start:end]
prefix=r"""
#include <map>
#include <mutex>
#include <atomic>
#include <optional>
#include <string>
#include <string_view>
#include <algorithm>
#include <cstdint>
#include <cassert>
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s32=int32_t;using s64=int64_t;
#define PS4_SYSV_ABI
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
struct BbscSaveSlot{std::string user;int slot;};
std::optional<BbscSaveSlot> bbsc_progress_slot=BbscSaveSlot{"test",0},active=bbsc_progress_slot;
std::optional<BbscSaveSlot> BbscActiveSaveSlot(){return active;}
u64 image_base=1,EventFlagManPointerOffset=2; bool managers=true,guest=false,quit=false,disk_ok=true,accept=true;
bool bbsc_progress_was_guest=true,bbsc_in_talk_step=false,bbsc_quit_save_hooks_ready=true,bbsc_ledger_home_ready=true;
u32 bbsc_talk_step_id=0,bbsc_ledger_home_generation=1;
constexpr u64 BbscTalkSetFlagReturnOffset=10,BbscEventBank2003Begin=20,BbscEventBank2003End=30;
std::atomic<u32> bbsc_load_generation{1};std::atomic<bool> bbsc_talk_save_watch{false};std::atomic<s32> bbsc_talk_save_result{-1};
std::mutex bbsc_talk_journal_mutex;std::map<u32,u8> bbsc_talk_journal,live,disk,saved;
bool bbsc_talk_journal_applying=false;u64 bbsc_talk_journal_revision=0,bbsc_talk_saved_revision=0;
u32 bbsc_talk_save_generation=0;s64 bbsc_talk_save_started_ms=0,bbsc_talk_save_retry_ms=0,now=10000;
s32 save_state=0;int grants=0;constexpr u32 gift=72410310,dialogue=72410501;
u64 GetGlobalState(){return 0x10000;}bool ReadablePointer(u64,size_t){return true;}
template<class T>T ReadValue(u64 p,size_t off){if(p==image_base+0x0553B0D8||p==image_base+EventFlagManPointerOffset)return managers?1:0;if(off==0x1592)return 1;if(off==0x1554)return save_state;return 0;}
bool BbscGuestInHostWorld(){return guest;}bool BbscQuitInProgress(){return quit;}s64 SteadyNowMs(){return now;}
bool BbscEventFlag(u32 flag){return live[flag]!=0;}
bool WriteBbscTripJournal(const BbscSaveSlot&){if(!disk_ok)return false;disk=bbsc_talk_journal;return true;}
u64 setflag(u64,u32 f,u8 v){if(f==gift&&v&&!live[f])++grants;live[f]=v;return 0;}
u8 native_save(s32 slot,s32 flag,s32 erase){assert(slot==-1&&flag==0&&erase==0);if(!accept)return 0;saved=live;save_state=1;return 1;}
"""
pickup_rules = re.search(r'struct BbscScriptedPickup \{.*?\};', SOURCE, re.S).group()+'\n'
pickup_rules += re.search(r'constexpr std::array<BbscScriptedPickup, \d+> BbscScriptedPickups\{\{.*?\}\};', SOURCE, re.S).group()+'\n'
prefix = '#include <array>\n'+prefix+pickup_rules+function('bool IsBbscScriptedPickupFlag(u32 flag)')+'\n'
functions='\n'.join(function(s) for s in [
 'void NoteBbscTalkFlag(u32 flag, u8 value, u64 caller_offset, bool talk_event)',
 'bool ApplyBbscTalkJournal(std::string_view when, bool finish)'])
functions=functions.replace('reinterpret_cast<SetEventFlag>(image_base + 0x0132E5A0)','static_cast<SetEventFlag>(&setflag)')
functions=functions.replace('reinterpret_cast<Save>(image_base + BbscNativeSaveRequestOffset)','static_cast<Save>(&native_save)')
main=r"""
void reset(){bbsc_talk_journal.clear();live.clear();disk.clear();saved.clear();guest=false;quit=false;managers=true;disk_ok=true;accept=true;grants=0;
 bbsc_talk_journal_applying=false;bbsc_talk_journal_revision=1;bbsc_talk_save_watch=false;bbsc_talk_save_result=-1;bbsc_talk_save_retry_ms=0;
 save_state=0;now=10000;bbsc_load_generation=1;bbsc_ledger_home_generation=1;bbsc_ledger_home_ready=true;active=bbsc_progress_slot;}
int main(){
 reset();guest=true;
 // Native completion writes occur outside bank2003; record only reviewed pickup flags.
 for(u32 f:{12300130u,12110300u,12501803u,12410511u,9470u}){
  NoteBbscTalkFlag(f,1,999,false);assert(disk[f]==1);
 }
 NoteBbscTalkFlag(12500810,1,999,false);assert(!disk.contains(12500810));
 reset();bbsc_talk_journal={{dialogue,1},{gift,1}};
 assert(!ApplyBbscTalkJournal("early",false));assert(grants==1);
 NoteBbscTalkFlag(gift,0,21,false);live[gift]=0;assert(disk[gift]==0);
 live[dialogue]=0; // late snapshot replacement must be repaired without rearming gift
 assert(!ApplyBbscTalkJournal("late",true));assert(live[dialogue]==1&&grants==1&&saved[gift]==0);
 save_state=0;bbsc_talk_save_result=0;assert(ApplyBbscTalkJournal("late",true));assert(bbsc_talk_journal.empty());
 reset();bbsc_talk_journal[dialogue]=1;managers=false;assert(!ApplyBbscTalkJournal("early",false));assert(!bbsc_talk_journal.empty());
 reset();bbsc_talk_journal[dialogue]=1;disk_ok=false;assert(!ApplyBbscTalkJournal("late",true));assert(!bbsc_talk_save_watch);
 reset();bbsc_talk_journal[dialogue]=1;assert(!ApplyBbscTalkJournal("late",true));
 NoteBbscTalkFlag(dialogue,0,10,false);live[dialogue]=0;save_state=0;bbsc_talk_save_result=0;
 assert(!ApplyBbscTalkJournal("late",true));assert(!bbsc_talk_journal.empty()&&saved[dialogue]==0); // new revision needs a new save
 reset();bbsc_talk_journal[dialogue]=1;assert(!ApplyBbscTalkJournal("late",true));save_state=0;bbsc_talk_save_result=9;
 assert(!ApplyBbscTalkJournal("late",true));assert(!bbsc_talk_journal.empty());
 reset();bbsc_talk_journal[dialogue]=1;bbsc_ledger_home_ready=false;assert(!ApplyBbscTalkJournal("late",true));assert(!bbsc_talk_save_watch);
 reset();bbsc_talk_journal[dialogue]=1;active=BbscSaveSlot{"other",1};assert(!ApplyBbscTalkJournal("early",false));assert(live.empty());
 reset(); // empty talk journal still waits for the own-world/item/shared-progress native save
 assert(!ApplyBbscTalkJournal("late",true));assert(bbsc_talk_save_watch);
 save_state=0;bbsc_talk_save_result=0;assert(ApplyBbscTalkJournal("late",true));
 reset();bbsc_talk_journal={{gift,0},{dialogue,1}}; // restart from durable consumed-trigger journal
 assert(!ApplyBbscTalkJournal("early",false));assert(grants==0&&live[dialogue]==1);
}
"""
with tempfile.TemporaryDirectory(prefix='bbsc-personal-progress-') as temporary:
    p=Path(temporary);cpp=p/'fixture.cpp';exe=p/'fixture.exe';cpp.write_text(prefix+functions+main,encoding='utf-8')
    subprocess.run([os.environ.get('CXX','g++'),'-std=c++20',str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=10)
print('Personal progress: late overwrite, gift consumption, save acknowledgment and context guards PASS')
