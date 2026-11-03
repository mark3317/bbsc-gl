// SPDX-License-Identifier: GPL-2.0-or-later
// Loopback bridge to the party engine embedded in BBGL's existing run.py process.
#include <windows.h>
#include <winhttp.h>
#include <atomic>
#include <cstdlib>
#include <string>
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
std::atomic<unsigned> native{1u<<8};
std::atomic<bool> can_beckon{false};
std::atomic<unsigned> cancel_sequence{0};
std::atomic<ULONGLONG> refreshed{0}, leave_refreshed{0};
std::atomic<unsigned> leave_confirmed{0};
std::atomic<bool> title_pending{false};
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
bool PartyAcquire() {
    if(!PartyEnabled()) return true;
    if(!ExclusiveNative()) return false;
    const bool granted=Call(L"/party/acquire","{}",8500)=="1";
    LOG_INFO(Mod,"Serverless party: actual Beckoning request {} before native item execution",
             granted?"unanimously granted":"denied/unconfirmed");
    return granted;
}
bool PartyCanBeckon() {
    return !PartyEnabled() || (ExclusiveNative() && can_beckon.load() && GetTickCount64()-refreshed.load()<1500);
}
void PartyCancel() { if(PartyEnabled()) { ++cancel_sequence; title_pending=false; leave_confirmed=0; } }
void PartyEndTitleWait() { title_pending=false; leave_confirmed=0; }
bool PartyTitleReady() {
    if(!PartyEnabled()) return true;
    const unsigned cancel=cancel_sequence.load();
    const bool ready=ExclusiveNative() && cancel && leave_confirmed.load()==cancel &&
                     GetTickCount64()-leave_refreshed.load()<1500;
    title_pending=!ready;
    return ready;
}
void PartyObserve(std::int32_t state,bool loading,bool bell) {
    if(PartyEnabled()) native=static_cast<unsigned>(state&255)|(loading?256u:0u)|(bell?512u:0u);
}
void PartyMaintain() {
    if(!PartyEnabled() || !ExclusiveNative()) return;
    static ULONGLONG last=0;
    const ULONGLONG now=GetTickCount64();
    if(now-last<250) return;
    last=now; const unsigned value=native.load(), cancel=cancel_sequence.load();
    const bool awaiting=title_pending.load();
    const std::string body="{\"state\":"+std::to_string(value&255)+",\"loading\":"+
        ((value&256)?"true":"false")+",\"bell\":"+((value&512)?"true":"false")+
        ",\"cancel_seq\":"+std::to_string(cancel)+",\"await_title\":"+(awaiting?"true":"false")+"}";
    const std::string result=Call(L"/party/tick",body,300);
    const size_t separator=result.find(' ');
    const std::string expected=std::to_string(cancel);
    const bool valid=separator!=std::string::npos && (result.substr(0,separator)=="0" || result.substr(0,separator)=="1") &&
                     (result.substr(separator+1)=="0" || result.substr(separator+1)==expected);
    can_beckon=valid && result[0]=='1'; refreshed=GetTickCount64();
    const bool ready=valid && awaiting && cancel && result.substr(separator+1)==expected;
    if(cancel_sequence.load()==cancel) {
        leave_confirmed=ready?cancel:0; leave_refreshed=GetTickCount64();
    }
}
}
