// SPDX-License-Identifier: GPL-2.0-or-later
// Loopback bridge to the party engine embedded in BBGL's existing run.py process.
#include <windows.h>
#include <winhttp.h>
#include <atomic>
#include <charconv>
#include <cstdlib>
#include <string>
#include <string_view>
#include "bbsc_party.h"
#include "common/logging/log.h"
namespace {
// A crashed runner must not authorize a second native world while its old game lives.
bool ExclusiveNative() {
    static const bool unique=[] {
        const char* identity=std::getenv("BBSC_PARTY_INSTANCE");
        if(!identity || !*identity) return false;
        const std::string name="Local\\BBSC-Party-Native-"+std::string(identity);
        const HANDLE handle=CreateMutexA(nullptr,FALSE,name.c_str());
        return handle && GetLastError()!=ERROR_ALREADY_EXISTS; // retained until process exit
    }();
    return unique;
}
std::atomic<std::uint64_t> native{1u<<8};
std::atomic<bool> can_beckon{false};
std::atomic<unsigned> host_hint{0};
std::atomic<unsigned> room_members{0};
constexpr std::uint64_t CountedBellNotices=std::uint64_t{1}<<63;
std::atomic<std::uint64_t> bell_generation{0}, bell_released_generation{0};
std::atomic<std::uint64_t> local_bell_rings{0};
std::atomic<unsigned> cancel_sequence{0};
std::atomic<ULONGLONG> refreshed{0}, leave_refreshed{0};
std::atomic<unsigned> leave_confirmed{0};
std::atomic<bool> title_pending{false};
BbscMod::PartyAcquireMailbox acquire;
std::string Call(const wchar_t* path, const std::string& body, int timeout) {
    const char* port_text=std::getenv("BBSC_PARTY_PORT");
    const char* token=std::getenv("BBSC_PARTY_TOKEN");
    if(!port_text || !token) return {};
    const long port=std::strtol(port_text,nullptr,10);
    if(port<1024 || port>65535) return {};
    struct Client {
        HINTERNET session=nullptr;
        HINTERNET connection=nullptr;
        long port=0;
        ~Client(){if(connection)WinHttpCloseHandle(connection);if(session)WinHttpCloseHandle(session);}
    };
    thread_local Client client;
    if(!client.session)client.session=WinHttpOpen(L"BBSC-party/1",WINHTTP_ACCESS_TYPE_NO_PROXY,
                                                  WINHTTP_NO_PROXY_NAME,WINHTTP_NO_PROXY_BYPASS,0);
    if(!client.session)return {};
    WinHttpSetTimeouts(client.session,timeout,timeout,timeout,timeout);
    if(client.port!=port || !client.connection){
        if(client.connection)WinHttpCloseHandle(client.connection);
        client.connection=WinHttpConnect(client.session,L"127.0.0.1",static_cast<INTERNET_PORT>(port),0);
        client.port=port;
    }
    const HINTERNET connection=client.connection;
    HINTERNET request=connection?WinHttpOpenRequest(connection,L"POST",path,nullptr,
        WINHTTP_NO_REFERER,WINHTTP_DEFAULT_ACCEPT_TYPES,0):nullptr;
    std::string out;
    if(request) {
        const std::string header="X-BBSC-Party: "+std::string(token)+"\r\nContent-Type: application/json\r\n";
        const std::wstring wide(header.begin(),header.end());
        if(WinHttpSendRequest(request,wide.c_str(),static_cast<DWORD>(wide.size()),
            const_cast<char*>(body.data()),static_cast<DWORD>(body.size()),static_cast<DWORD>(body.size()),0) &&
            WinHttpReceiveResponse(request,nullptr)) {
            DWORD status=0,length=sizeof(status),read=0; char bytes[64]{};
            if(WinHttpQueryHeaders(request,WINHTTP_QUERY_STATUS_CODE|WINHTTP_QUERY_FLAG_NUMBER,
                WINHTTP_HEADER_NAME_BY_INDEX,&status,&length,WINHTTP_NO_HEADER_INDEX) && status==200) {
                for(;;) {
                    if(!WinHttpReadData(request,bytes,sizeof(bytes),&read)){out.clear();break;}
                    if(!read)break;
                    if(out.size()+read>sizeof(bytes)){out.clear();break;}
                    out.append(bytes,read);
                }
            }
        }
        WinHttpCloseHandle(request);
    }
    return out;
}
}
namespace BbscMod {
bool PartyEnabled() {
    static const bool enabled=[] { const char* text=std::getenv("BBSC_PARTY"); return text && std::string(text)=="1"; }();
    return enabled;
}
std::uint64_t PartyRequestAcquire() {
    return PartyEnabled() && ExclusiveNative() ? acquire.Request() : 0;
}
PartyAcquireMailbox::Result PartyAcquireResult(std::uint64_t ticket) {
    return acquire.Poll(ticket);
}
void PartyFinishAcquire(std::uint64_t ticket) {
    acquire.Finish(ticket);
}
bool PartyCanBeckon() {
    return !PartyEnabled() || (ExclusiveNative() && can_beckon.load() && GetTickCount64()-refreshed.load()<1500);
}
unsigned PartyHostHint() {
    return PartyEnabled() && ExclusiveNative() && GetTickCount64()-refreshed.load()<1500 ? host_hint.load() : 0;
}
unsigned PartyRoomMemberCount() {
    return PartyEnabled() && ExclusiveNative() ? room_members.load() : 0;
}
void PartyBellRang() { ++local_bell_rings; }
std::uint64_t PartyBellGeneration(bool& counted) {
    const auto value=PartyEnabled() && ExclusiveNative() && GetTickCount64()-refreshed.load()<1500
        ? bell_generation.load() : 0;
    counted=(value & CountedBellNotices)!=0;
    return value & ~CountedBellNotices;
}
std::uint64_t PartyBellReleasedGeneration() {
    return PartyEnabled() && ExclusiveNative() && GetTickCount64()-refreshed.load()<1500
        ? bell_released_generation.load() : 0;
}
void PartyCancel() { if(PartyEnabled()) { acquire.Cancel(); ++cancel_sequence; title_pending=false; leave_confirmed=0; } }
void PartyEndTitleWait() { title_pending=false; leave_confirmed=0; }
bool PartyTitleReady() {
    if(!PartyEnabled()) return true;
    const unsigned cancel=cancel_sequence.load();
    const bool ready=ExclusiveNative() && cancel && leave_confirmed.load()==cancel &&
                     GetTickCount64()-leave_refreshed.load()<1500;
    title_pending=!ready;
    return ready;
}
void PartyObserve(std::int32_t state,bool loading,bool bell,std::int32_t members,bool alive,bool responder) {
    if(PartyEnabled()) {
        // One atomic snapshot; zero encodes unknown, member count includes self.
        const unsigned population=members>=1 && members<=5 ? static_cast<unsigned>(members) : 0;
        native=(GetTickCount64()<<15)|static_cast<unsigned>(state&255)|(loading?256u:0u)|
               (bell?512u:0u)|(population<<10)|(alive?8192u:0u)|(responder?16384u:0u);
    }
}
void PartyMaintain() {
    if(!PartyEnabled() || !ExclusiveNative()) return;
    static ULONGLONG last=0;
    const ULONGLONG now=GetTickCount64();
    if(now-last<250) return;
    last=now; const auto snapshot=native.load();
    const unsigned value=static_cast<unsigned>(snapshot&0x7FFFu), cancel=cancel_sequence.load();
    const bool awaiting=title_pending.load();
    const std::string body="{\"state\":"+std::to_string(value&255)+",\"loading\":"+
        ((value&256)?"true":"false")+",\"bell\":"+((value&512)?"true":"false")+
        ",\"members\":"+std::to_string((value>>10)&7u)+",\"alive\":"+((value&8192)?"true":"false")+
        ",\"responder\":"+((value&16384)?"true":"false")+
        ",\"fresh\":"+((snapshot>>15 && now-(snapshot>>15)<1500)?"true":"false")+
        ",\"cancel_seq\":"+std::to_string(cancel)+",\"await_title\":"+(awaiting?"true":"false")+
        ",\"bell_ring_seq\":"+std::to_string(local_bell_rings.load())+
        ",\"placement_ticket\":true,\"aimed_placement\":\""+AimedPlacementAcknowledgment()+"\"}";
    const std::string result=Call(L"/party/tick",body.substr(0,body.size()-1)+",\"bell_notice\":true,\"bell_release\":true,\"host_check\":true,\"roster_count\":true}",300);
    // Accept old two-field runners, but only an explicit generation can notify.
    const size_t generation_separator=result.find(' ',result.find(' ')+1);
    const std::string status=result.substr(0,generation_separator);
    std::uint64_t generation=0, released=0; unsigned hint=0, members=0;
    bool roster_confirmed=false;
    if(generation_separator!=std::string::npos) {
        const char* first=result.data()+generation_separator+1;
        const char* end=result.data()+result.size();
        const auto parsed=std::from_chars(first,end,generation);
        if(parsed.ec!=std::errc{} || generation>=CountedBellNotices) generation=0;
        else if(parsed.ptr!=end) {
            if(*parsed.ptr==' ') {
                const auto tail=std::from_chars(parsed.ptr+1,end,released);
                if(tail.ec!=std::errc{}) { generation=0; released=0; }
                else if(tail.ptr!=end) {
                    if(*tail.ptr==' ') {
                        const auto host=std::from_chars(tail.ptr+1,end,hint);
                        const std::string_view extension(host.ptr,end);
                        const bool has_members=extension.size()==4 &&
                                               (extension.starts_with(" 1 ") || extension.starts_with(" 0 ")) &&
                                               extension.back()>='0' && extension.back()<='5';
                        if(host.ec!=std::errc{} || hint>2 ||
                           (!extension.empty() && extension!=" 1" && !has_members)) {
                            generation=0; released=0; hint=0;
                        } else if(!extension.empty()) {
                            if(extension[1]=='1') generation|=CountedBellNotices;
                            if(has_members) {
                                members=static_cast<unsigned>(extension.back()-'0');
                                roster_confirmed=true;
                            }
                        }
                    } else { generation=0; released=0; }
                }
            } else generation=0;
        }
    }
    const size_t separator=status.find(' ');
    const std::string expected=std::to_string(cancel);
    const bool valid=separator!=std::string::npos && (status.substr(0,separator)=="0" || status.substr(0,separator)=="1") &&
                     (status.substr(separator+1)=="0" || status.substr(separator+1)==expected);
    // An unavailable reply is not a roster change. An explicit zero clears
    // the previous room once Party has confirmed that we no longer belong.
    if(valid && roster_confirmed && room_members.exchange(members)!=members)
        Core::Bloodborne::OnBbscPartyRoomMemberCountChanged();
    can_beckon=valid && status[0]=='1'; host_hint=valid?hint:0; bell_generation=valid?generation:0; bell_released_generation=valid?released:0; refreshed=GetTickCount64();
    const bool ready=valid && awaiting && cancel && status.substr(separator+1)==expected;
    if(cancel_sequence.load()==cancel) {
        leave_confirmed=ready?cancel:0; leave_refreshed=GetTickCount64();
    }
    // This is the maintenance worker, never the native item/frame callback.
    // A cancelled generation is discarded even when its HTTP response arrives late.
    if (const auto ticket=acquire.Take()) {
        const auto started=GetTickCount64();
        const bool granted=Call(L"/party/acquire","{}",8500)=="1";
        const bool accepted=acquire.Complete(ticket,granted);
        LOG_INFO(Mod,"Serverless party: asynchronous Beckoning request ticket={} granted={} current={} duration_ms={}",
                 ticket,granted,accepted,GetTickCount64()-started);
    }
}
}
