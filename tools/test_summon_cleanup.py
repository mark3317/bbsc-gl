"""Run the production HTTP lifecycle functions against a deterministic broker.

No game process, network, or save files are used.
"""
from pathlib import Path
import os
import subprocess

root = Path(__file__).resolve().parents[1]
source = (root / 'emulator/mod/bbsc_http.cpp').read_text(encoding='utf-8')

def function(signature):
    start = source.index(signature)
    begin = source.index('{', start)
    depth, end = 1, begin + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

fixture = r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <future>
#include <functional>
#include <iostream>
#include <mutex>
#include <string>
#include <vector>
using s64=int64_t; using u64=uint64_t; using u32=uint32_t; using s32=int32_t;
using DWORD=unsigned long;
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
std::atomic<bool> stale_cleared{false},was_in_session{false},placement_aimed{false};
std::atomic<s64> claim_delivered_ms{0},own_user_id{0},placement_received_ms{0};
std::atomic<u32> placement_sender{0};
std::mutex summon_lifecycle_mutex;
std::string own_sign_url,own_sign_body;
s64 cleanup_retry_ms=0,now=1000;
constexpr s64 ClaimJoinWaitMs=20000,PlacementStaleMs=20000,AimedPlacementStaleMs=90000;
s64 NowMs(){return now;}
int state=0; s32 SessionState(){return state;}
int deletes=0,creates=0;DWORD status=200;bool broker_record=true;
std::vector<char> operations;
std::function<void()> during_delete;
DWORD Post(const std::string& url,const std::string& body){
 assert(url.find("/summon_messenger/delete")!=std::string::npos);
 assert(body.find("\"Force\":true")!=std::string::npos);
 ++deletes; operations.push_back('D');
 if(during_delete)during_delete();
 if(status>=200&&status<300)broker_record=false;
 return status;
}
int original_send(int,const void*,u64){++creates;operations.push_back('C');broker_record=true;return 0;}
int original_set_content_length(int,u64){return 0;}
bool RewriteAreaId(std::string&){return false;}
namespace Core::Bloodborne {void ClearSeamlessHostPlacementHeader(){}}
'''
for signature in ('std::string JsonString(', 'std::string JsonNumber(',
                  'bool ClearStaleRecord(', 'void WatchSessionForStaleClaims()',
                  'int SendCleanSummonCreate(', 'void MaintainSummonLifecycle()'):
    fixture += function(signature) + '\n'
fixture += r'''
const std::string url="http://private:31315/summon_messenger/create?user_id=2545";
const std::string body=R"({"SessionId":"same-session","UserId":2545})";
int create(){return SendCleanSummonCreate(1,url,body.data(),body.size());}
void tick(){MaintainSummonLifecycle();}
int main(){
 // Initial cleanup, then normal refresh without deleting an active invitation.
 assert(create()==0&&deletes==1&&creates==1&&broker_record);
 assert(create()==0&&deletes==1&&creates==2);
 state=4;tick();state=6;tick();assert(deletes==1);
 state=7;tick();assert(deletes==1);
 // Regression: departure with no HTTP traffic / next bell. A host can no
 // longer discover the previous invitation during the minutes spent in menu.
 state=0;tick();assert(deletes==2&&!broker_record);
 tick();assert(deletes==2);
 assert(create()==0&&deletes==2&&broker_record);
 // Fast rejoin before maintenance gets to run still deletes before create.
 state=6;tick();state=0;operations.clear();
 assert(create()==0);assert((operations==std::vector<char>{'D','C'}));
 // Failed cleanup remains armed, backs off, and does not publish over a claim.
 state=6;tick();state=0;status=503;tick();int failed=deletes;
 assert(!stale_cleared&&broker_record);tick();assert(deletes==failed);
 now+=2000;tick();assert(deletes==failed+1);
 int sent=creates;assert(create()!=0&&creates==sent&&!stale_cleared);
 status=200;now+=2000;tick();assert(stale_cleared&&!broker_record);
 assert(create()==0&&broker_record);
 // A delivered claim is allowed its entire join window; no cleanup during
 // a real slow join, even after the timeout. An abandoned idle claim is removed.
 claim_delivered_ms=now;now+=20001;state=4;tick();assert(claim_delivered_ms==0);
 state=6;tick();state=0;tick();create();
 claim_delivered_ms=now;now+=20000;tick();assert(broker_record);
 ++now;tick();assert(!broker_record&&claim_delivered_ms==0);
 // Invalid identity must not mark cleanup successful.
 stale_cleared=false;assert(!ClearStaleRecord(url,"{}")&&!stale_cleared);
 // A concurrent create cannot pass an in-flight departure delete, and no
 // delayed delete may subsequently remove the newly published sign.
 stale_cleared=true;was_in_session=true;state=0;
 std::promise<void> entered,release;
 auto released=release.get_future();
 during_delete=[&]{entered.set_value();released.wait();};
 operations.clear();
 auto maintenance=std::async(std::launch::async,[]{tick();});
 entered.get_future().wait();
 auto posting=std::async(std::launch::async,[]{return create();});
 assert(posting.wait_for(std::chrono::milliseconds(25))==std::future_status::timeout);
 release.set_value();maintenance.get();assert(posting.get()==0);
 during_delete={};tick();assert((operations==std::vector<char>{'D','C'})&&broker_record);
 std::cout<<"PASS: eager idle cleanup, refresh, slow join, failure retry, blocked stale create, claim timeout, concurrent rejoin\n";
}
'''
build = root / 'build'
build.mkdir(exist_ok=True)
cpp, exe = build / 'test_summon_cleanup.cpp', build / 'test_summon_cleanup.exe'
cpp.write_text(fixture, encoding='utf-8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe', '-std=c++20', str(cpp), '-o', str(exe)], check=True)
env = dict(os.environ)
env['PATH'] = 'C:/msys64/clang64/bin;' + env.get('PATH', '')
subprocess.run([str(exe)], check=True, env=env)
