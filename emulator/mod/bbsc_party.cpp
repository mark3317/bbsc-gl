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
std::atomic<unsigned> native{1u<<8};
std::atomic<bool> can_beckon{false};
std::atomic<ULONGLONG> refreshed{0};
std::string Call(const wchar_t* path, const std::string& body, int timeout) {
    const char* port_text=std::getenv("BBSC_PARTY_PORT");
    const char* token=std::getenv("BBSC_PARTY_TOKEN");
    if(!port_text || !token) return {};
    const long port=std::strtol(port_text,nullptr,10);
    if(port<1024 || port>65535) return {};
    HINTERNET session=WinHttpOpen(L"BBSC-party/1",WINHTTP_ACCESS_TYPE_NO_PROXY,
                                  WINHTTP_NO_PROXY_NAME,WINHTTP_NO_PROXY_BYPASS,0);
    if(!session) return {};
    WinHttpSetTimeouts(session,timeout,timeout,timeout,timeout);
    HINTERNET connection=WinHttpConnect(session,L"127.0.0.1",static_cast<INTERNET_PORT>(port),0);
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
                WINHTTP_HEADER_NAME_BY_INDEX,&status,&length,WINHTTP_NO_HEADER_INDEX) && status==200 &&
                WinHttpReadData(request,bytes,sizeof(bytes),&read)) out.assign(bytes,read);
        }
        WinHttpCloseHandle(request);
    }
    if(connection) WinHttpCloseHandle(connection);
    WinHttpCloseHandle(session); return out;
}
}
namespace BbscMod {
bool PartyEnabled() {
    static const bool enabled=[] { const char* text=std::getenv("BBSC_PARTY"); return text && std::string(text)=="1"; }();
    return enabled;
}
bool PartyAcquire() {
    if(!PartyEnabled()) return true;
    const bool granted=Call(L"/party/acquire","{}",8500)=="1";
    LOG_INFO(Mod,"Serverless party: actual Beckoning request {} before native item execution",
             granted?"unanimously granted":"denied/unconfirmed");
    return granted;
}
bool PartyCanBeckon() {
    return !PartyEnabled() || (can_beckon.load() && GetTickCount64()-refreshed.load()<1500);
}
void PartyObserve(std::int32_t state,bool loading,bool bell) {
    if(PartyEnabled()) native=static_cast<unsigned>(state&255)|(loading?256u:0u)|(bell?512u:0u);
}
void PartyMaintain() {
    if(!PartyEnabled()) return;
    static ULONGLONG last=0;
    const ULONGLONG now=GetTickCount64();
    if(now-last<250) return;
    last=now; const unsigned value=native.load();
    const std::string body="{\"state\":"+std::to_string(value&255)+",\"loading\":"+
        ((value&256)?"true":"false")+",\"bell\":"+((value&512)?"true":"false")+"}";
    Call(L"/party/native",body,300);
    const std::string result=Call(L"/party/can_beckon","{}",300);
    can_beckon=result=="1"; refreshed=GetTickCount64();
}
}
