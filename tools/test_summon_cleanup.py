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
#include <map>
#include "bbsc_network_attempt.h"
BbscMod::NetworkAttemptTrace network_attempt_trace;
#include <string_view>
using s64=int64_t; using u64=uint64_t; using u32=uint32_t; using s32=int32_t;
using DWORD=unsigned long;
#define LOG_INFO(...)
#define LOG_WARNING(...)
#define BBSC_TIMELINE(...)
#define PS4_SYSV_ABI
std::atomic<bool> joined_claim_cleanup_due{false};
std::atomic<bool> stale_cleared{false},was_in_session{false},placement_aimed{false};
std::atomic<s64> claim_delivered_ms{0},own_user_id{0},placement_received_ms{0};
std::atomic<u32> placement_sender{0};
std::mutex aimed_placement_mutex;
std::string aimed_placement_ack,ack_header;
std::mutex summon_lifecycle_mutex;
u64 summon_lifecycle_generation=0;
bool summon_cleanup_in_flight=false;
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
int original_add_header(int,const char* name,const char* value,int){
 assert(std::string(name)=="X-BBSC-Aimed-Placement");ack_header=value;return 0;
}
bool RewriteAreaId(std::string&){return false;}
namespace Core::Bloodborne {
bool pending=false;
void NoteBbscHostRangOurSign(u32){}
std::string applied;
bool SetSeamlessHostPlacementHeader(std::string_view value){applied=value;return true;}
void ClearSeamlessHostPlacementHeader(){}
void SetBbscNativeSignClaimPending(bool v){pending=v;}
}
std::mutex state_mutex;
std::map<int,std::string> request_urls;
bool IsSummon(const std::string& u){return u.find("/summon_messenger/")!=std::string::npos;}
bool IsSummonCreate(const std::string& u){return u.find("/summon_messenger/create")!=std::string::npos;}
bool IsPublicServer(const std::string& u){return u.find("public")!=std::string::npos;}
void FinishNativeSignRequest(int){}
int original_read_data(int,void* out,u64 size){
 const std::string reply=R"({"MessageId":"SummonDataCreateResponse","UserId":1})";
 assert(size>=reply.size());std::memcpy(out,reply.data(),reply.size());return reply.size();
}
'''
for signature in ('std::string JsonString(', 'std::string JsonNumber(',
                  'bool ClearStaleRecord(', 'void WatchSessionForStaleClaims()',
                  'int SendCleanSummonCreate(', 'void MaintainSummonLifecycle()',
                  'int PS4_SYSV_ABI ReadData(', 'void OnAimedHostPlacement(',
                  'std::string AimedPlacementAcknowledgment('):
    fixture += function(signature) + '\n'
fixture += r'''
const std::string url="http://private:31315/summon_messenger/create?user_id=2545";
const std::string body=R"({"SessionId":"same-session","UserId":2545})";
void tick(){MaintainSummonLifecycle();}
int attempt(){return SendCleanSummonCreate(1,url,body.data(),body.size());}
int create(){int rc=attempt();if(rc){tick();rc=attempt();}return rc;}
int main(){
 // Initial cleanup, then normal refresh without deleting an active invitation.
 assert(create()==0&&deletes==1&&creates==1&&broker_record);
 assert(create()==0&&deletes==1&&creates==2);
 // Only a native-accepted, live aimed placement may acknowledge readiness.
 const std::string placement="1,18010000,0,0,0,0,241040";
 OnAimedHostPlacement(999,placement,111);assert(!placement_aimed);
 state=3;OnAimedHostPlacement(2545,placement,111);assert(!placement_aimed);
 state=6;OnAimedHostPlacement(2545,placement,111);assert(!placement_aimed);state=0;
 assert(create()==0&&ack_header.empty());
 OnAimedHostPlacement(2545,placement,111);
 assert(AimedPlacementAcknowledgment()==placement);
 // Direct JoinRoom may already be joining before the placement arrives.
 state=4;OnAimedHostPlacement(2545,placement,111);
 assert(AimedPlacementAcknowledgment()==placement);state=0;
 assert(placement_aimed&&aimed_placement_ack==placement);
 const std::string repeat=placement+"|Host-3-125";
 OnAimedHostPlacement(2545,repeat,111);
 assert(Core::Bloodborne::applied==placement && AimedPlacementAcknowledgment()==repeat);
 OnAimedHostPlacement(2545,placement+"|invalid ticket",111);
 assert(AimedPlacementAcknowledgment()==repeat);
 assert(create()==0&&ack_header==aimed_placement_ack);
 ack_header.clear();now+=90001;
 assert(AimedPlacementAcknowledgment().empty()); // expires even without sign/create
 assert(create()==0&&ack_header.empty()&&!placement_aimed);
 state=4;tick();assert(deletes==1&&broker_record);
 state=6;tick();assert(deletes==2&&!broker_record);
 tick();assert(deletes==2); // joined member no longer searchable
 // A pre-join create can complete late; ReadData arms another consume only
 // after its response, preventing publication/ack reordering from retaining it.
 broker_record=true;joined_claim_cleanup_due=true;stale_cleared=false;
 ++summon_lifecycle_generation;now+=2000;tick();
 assert(!broker_record&&!joined_claim_cleanup_due);int baseline=deletes;
 state=7;tick();assert(deletes==baseline);
 // Regression: departure with no HTTP traffic / next bell. A host can no
 // longer discover the previous invitation during the minutes spent in menu.
 state=0;tick();assert(deletes==baseline+1&&!broker_record);
 tick();assert(deletes==baseline+1);
 assert(create()==0&&deletes==baseline+1&&broker_record);
 // Fast rejoin before maintenance gets to run still deletes before create.
 state=6;tick();state=0;operations.clear();
 assert(create()==0);assert((operations==std::vector<char>{'D','C'}));
 // Failed cleanup remains armed, backs off, and does not publish over a claim.
 status=503;state=6;tick();state=0;tick();int failed=deletes;
 assert(!stale_cleared&&broker_record);tick();assert(deletes==failed);
 now+=2000;tick();assert(deletes==failed+1);
 int sent=creates;assert(create()!=0&&creates==sent&&!stale_cleared);
 status=200;now+=2000;tick();assert(stale_cleared&&!broker_record);
 assert(create()==0&&broker_record);
 // A delivered claim is allowed its entire join window; no cleanup during
 // a real slow join, even after the timeout. An abandoned idle claim is removed.
 claim_delivered_ms=now;now+=20001;state=4;tick();assert(claim_delivered_ms==0);
 int joining_deletes=deletes;stale_cleared=false;tick();assert(deletes==joining_deletes);
 state=6;tick();state=0;tick();create();
 claim_delivered_ms=now;now+=20000;tick();assert(broker_record);
 ++now;tick();assert(!broker_record&&claim_delivered_ms==0);
 // Re-delivery must not extend the first delivery's deadline. In the failed
 // three-player run a duplicate moved the nominal 20s cleanup to 32s.
 create();request_urls[1]=url;char reply[256];
 ReadData(1,reply,sizeof(reply));const s64 first_delivery=now;
 now+=12000;ReadData(1,reply,sizeof(reply));
 assert(claim_delivered_ms==first_delivery);
 now=first_delivery+20001;tick();assert(!broker_record&&!Core::Bloodborne::pending);
 // Public replies and a late reply to an established join cannot arm a new
 // idle-join deadline or block native sign refresh after the session ends.
 request_urls[2]="http://public/summon_messenger/create";
 ReadData(2,reply,sizeof(reply));assert(claim_delivered_ms==0);
 state=6;ReadData(1,reply,sizeof(reply));
 assert(claim_delivered_ms==0&&!Core::Bloodborne::pending&&joined_claim_cleanup_due);
 tick();state=0;tick();create();
 // Invalid identity must not mark cleanup successful.
 stale_cleared=false;assert(!ClearStaleRecord(url,"{}")&&!stale_cleared);
 // The native create callback returns immediately while a delete is blocked.
 // It may only retry publication after the worker completes that delete.
 stale_cleared=true;was_in_session=true;state=0;
 std::promise<void> entered,release;
 auto released=release.get_future();
 during_delete=[&]{entered.set_value();released.wait();};
 operations.clear();
 auto maintenance=std::async(std::launch::async,[]{tick();});
 entered.get_future().wait();
 auto posting=std::async(std::launch::async,[]{return attempt();});
 assert(posting.wait_for(std::chrono::seconds(1))==std::future_status::ready);
 assert(posting.get()!=0);
 {std::unique_lock unlocked(summon_lifecycle_mutex,std::try_to_lock);assert(unlocked);}
 release.set_value();maintenance.get();assert(attempt()==0);
 during_delete={};tick();assert((operations==std::vector<char>{'D','C'})&&broker_record);
 // A late response during unlocked delete dirties a new generation. The old
 // successful deletion must not mark that generation clean.
 stale_cleared=false;state=6;
 during_delete=[&]{char data[256];ReadData(1,data,sizeof(data));};
 tick();assert(!stale_cleared&&joined_claim_cleanup_due);
 during_delete={};tick();assert(stale_cleared&&!joined_claim_cleanup_due);
 // Even another short lifecycle section never makes the native wrapper wait.
 {std::scoped_lock lock{summon_lifecycle_mutex};
  auto busy=std::async(std::launch::async,[]{return attempt();});
  assert(busy.wait_for(std::chrono::seconds(1))==std::future_status::ready&&busy.get()!=0);}
 std::cout<<"PASS: async cleanup, retry ordering, slow join, failure backoff, nonblocking create, stale completion fence\n";
}
'''
build = root / 'build'
build.mkdir(exist_ok=True)
cpp, exe = build / 'test_summon_cleanup.cpp', build / 'test_summon_cleanup.exe'
cpp.write_text(fixture, encoding='utf-8')
subprocess.run(['C:/msys64/clang64/bin/clang++.exe', '-std=c++20', '-I', str(root/'emulator/mod'), str(cpp), '-o', str(exe)], check=True)
env = dict(os.environ)
env['PATH'] = 'C:/msys64/clang64/bin;' + env.get('PATH', '')
subprocess.run([str(exe)], check=True, env=env)
