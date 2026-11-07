"""Real backup + home-merge regression on artificial files; no player saves used."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')


def function(signature):
    start = SOURCE.index(signature + ' {')
    opening = SOURCE.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (SOURCE[end] == '{') - (SOURCE[end] == '}')
        end += 1
    return SOURCE[start:end]


prefix = r'''
#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <map>
#include <mutex>
#include <string>
#include <string_view>
#include <vector>
#define FMT_HEADER_ONLY
#include <fmt/format.h>
#include "core/bbsc_lift_flags.h"
namespace World=Core::Bloodborne::World;
using u8=uint8_t;using u32=uint32_t;using u64=uint64_t;using s64=int64_t;
namespace fs=std::filesystem;
#define LOG_INFO(...)
#define BBSC_TIMELINE(...)
#define BBSC_PERF_NESTED(...)
#define PS4_SYSV_ABI
fs::path data;
namespace Common::FS {
enum class PathType { CapturesDir };
fs::path GetUserPath(PathType) { return data/"captures"; }
}
bool BackupBbscSavesUnchecked();
bool BackupBbscSaves() { return BackupBbscSavesUnchecked(); }
constexpr size_t BbscWorldGroupBytes=125;
std::mutex bbsc_progress_mutex;
std::vector<u32> bbsc_progress_host_flags;
std::map<u32,std::array<u8,125>> bbsc_progress_groups;
bool bbsc_progress_backed_up=false;
bool BbscOwnOpeningDone(){return true;}
std::map<u32,bool> flags;
bool BbscEventFlag(u32 f){return flags[f];}
u64 setflag(u64,u32 f,u8 v){flags[f]=v;return 0;}
u64 image_base=0;
std::array<u8,125> live{};
u64 BbscFlagGroupStorage(u32){return reinterpret_cast<u64>(live.data());}
bool BbscSharedMapProgressAllowed(u32){return true;}
bool IsBbscNpcQuestFlag(u32){return false;}
void env(const char* key,const fs::path& value) {
#ifdef _WIN32
    _putenv_s(key,value.string().c_str());
#else
    if(value.empty()) unsetenv(key); else setenv(key,value.string().c_str(),1);
#endif
}
void write(const fs::path& p,const char* value) {
    fs::create_directories(p.parent_path());std::ofstream(p)<<value;
}
int copies(const fs::path& root,const char* name) {
    int n=0;if(!fs::exists(root))return n;
    for(const auto& e:fs::recursive_directory_iterator(root))
        if(e.is_regular_file() && e.path().filename()==name)++n;
    return n;
}
'''
functions = '\n'.join(function(sig) for sig in (
    'bool BackupBbscSavesUnchecked()',
    'u8 BbscSharedProgressByte(u32 key, size_t byte, u8 incoming)',
    'std::pair<s64, size_t> MergeBbscSharedProgress(std::string_view when)',
))
functions = functions.replace(
    'reinterpret_cast<SetEventFlag>(image_base + 0x0132E5A0)',
    'static_cast<SetEventFlag>(&setflag)')
main = r'''
int main(int argc,char** argv) {
    assert(argc==2);fs::path root=fs::absolute(argv[1]);
    fs::create_directories(root/"cwd");fs::current_path(root/"cwd");
    env("APPDATA",root/"appdata");
    const auto user=root/"selected-user";
    const auto save=user/"savedata/1/CUSA00207/SPRJ0005/userdata0001";
    write(save,"live-character");
    write(user/"savedata/1004/CUSA00207/SPRJ0005/protected","protected");
    env("BB_USER_DIR",user);env("BBSC_SAVE_DIR",{});
    data=root/"good";
    // A received boss and a lamp/map bit must be applied only after backing up
    // the selected live character. The previous code returned {-2,0} here
    // forever: neither legacy save root exists in a normal BBGL installation.
    bbsc_progress_host_flags={2400};bbsc_progress_groups[12410][0]=0x80;
    auto result=MergeBbscSharedProgress("home");
    assert(result.first==1 && result.second==1 && flags[2400] && live[0]==0x80);
    assert(copies(data,"userdata0001")==1);
    assert(copies(data,"stale")==0 && copies(data,"unrelated")==0);
    assert(copies(data,"protected")==0);
    for(const auto& e:fs::recursive_directory_iterator(data)) {
        if(e.path().filename()=="userdata0001") {
            std::string value;std::ifstream(e.path())>>value;assert(value=="live-character");
        }
    }
    // Legacy trees and pre-launch snapshots must not stand in for this backup.
    write(root/"cwd/user/savedata/2/CUSA00207/SPRJ0005/unrelated","unrelated");
    write(root/"snapshot/stale","stale");
    env("BBSC_SAVE_DIR",root/"snapshot");data=root/"with-legacy";
    bbsc_progress_backed_up=false;flags[2400]=false;live.fill(0);
    result=MergeBbscSharedProgress("with legacy");
    assert(result.first==1 && result.second==1);
    assert(copies(data,"userdata0001")==1 && copies(data,"protected")==0);
    assert(copies(data,"stale")==0 && copies(data,"unrelated")==0);
    // A configured but unavailable live tree must never fall back to another
    // user's save or a pre-launch copy and authorize the merge.
    data=root/"missing";env("BB_USER_DIR",root/"not-present");
    bbsc_progress_backed_up=false;flags[2400]=false;live.fill(0);
    result=MergeBbscSharedProgress("missing");
    assert(result.first==-2 && !flags[2400] && live[0]==0);
    assert(bbsc_progress_host_flags.size()==1 && bbsc_progress_groups.size()==1);
    assert(!fs::exists(data));
    // A failed destination likewise retains the pending data and live state.
    data=root/"blocked";write(data,"not-a-directory");env("BB_USER_DIR",user);
    result=MergeBbscSharedProgress("blocked");
    assert(result.first==-2 && !flags[2400] && live[0]==0);
    // Existing non-BBGL launches retain their explicit save-directory path.
    data=root/"legacy";env("BB_USER_DIR",{});
    assert(BackupBbscSavesUnchecked());
    assert(copies(data,"stale")==1 && copies(data,"unrelated")==0);
}
'''
with tempfile.TemporaryDirectory(prefix='bbsc-progress-backup-') as temporary:
    p = Path(temporary)
    cpp, exe = p/'fixture.cpp', p/'fixture.exe'
    cpp.write_text(prefix + functions + main, encoding='utf-8')
    subprocess.run([os.environ.get('CXX', 'g++'), '-std=c++20',
                    '-I'+str(ROOT/'emulator/src'),
                    '-I'+str(ROOT/'emulator/externals/fmt/include'),
                    str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe), str(p/'files')], check=True, timeout=15)
print('Progress backup: live BB_USER_DIR, boss/lamp merge, protected user, missing/failed backup retention, legacy fallback PASS')
