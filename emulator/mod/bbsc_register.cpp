// SPDX-License-Identifier: GPL-2.0-or-later
// Session-local provider for the original Vileblood Register (goods 130).
#include <windows.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <cstring>
#include <cstdlib>
#include <map>
#include <set>
#include <tuple>
#include <mutex>
#include <vector>
#include "bbsc_register.h"
#include "common/logging/log.h"
#include "core/cpu_patches.h"

namespace BbscMod {
u64 EbootAddress();
bool ReadSlotSafely(u64, u64*);
bool WriteSlotSafely(u64, u64);
void GuardSlot(u64, u64, void**, const char*);
namespace {
// PS4 NP ABI; match the native 0xCCEB7E range and 0xCCD7D0 by-ID call sites.
struct NpId { char name[20]{}; u8 opt[8]{}; u8 reserved[8]{}; };
struct Rank {
    NpId id; u8 reserved[52]{}; s32 pc=0; u32 serial=0, rank=0, highest=0;
    s32 has_data=0; u32 pad=0; s64 score=0; u64 date=0;
};
struct PlayerRank { s32 has_data=0; u32 pad=0; Rank value; };
struct IdPc { NpId id; s32 pc; u32 pad; };
struct Board { u32 limit, update, sort, uploads; u64 bytes; };
static_assert(sizeof(NpId)==36 && sizeof(Rank)==128 && sizeof(PlayerRank)==136);
static_assert(sizeof(IdPc)==44 && sizeof(Board)==24);
#pragma pack(push,1)
struct Packet { char magic[4]={'S','H','A','D'}; u8 type=0x2B, version=2;
    RegisterIdentity identity; u32 offered=0; };
#pragma pack(pop)
static_assert(sizeof(Packet)==33);
struct Entry { Packet packet; u64 seen; };
std::mutex mutex;
std::map<u32,Entry> members;
Packet local;
u32 current_session=0;
bool local_loaded=false;
std::atomic<bool> ready{false};
constexpr u32 BookBoard=20; // native Vileblood Register, observed in the game
constexpr s32 NoRanking=static_cast<s32>(0x80550812u);
std::atomic<u64> range_log_ms{0};
u64 last_tick=0;
bool SameMember(const RegisterIdentity& a,const RegisterIdentity& b) {
    if(a.room && a.member && b.room && b.member) return a.room==b.room && a.member==b.member;
    return a.name[0] && b.name[0] && std::memcmp(a.name,b.name,16)==0;
}
#pragma pack(push,1)
struct KillPacket {
    char magic[4]={'S','H','A','D'};
    u8 type=0x2C,version=1,kind=0; // claim / acknowledgement after inventory add
    u32 victim=0,death=0;
    RegisterIdentity killer;
};
#pragma pack(pop)
static_assert(sizeof(KillPacket)==38);
using KillKey=std::tuple<u32,u32,u32>; // session, victim sender, victim's life sequence
struct OutgoingKill { KillPacket packet; u64 created=0,sent=0; };
std::map<u32,OutgoingKill> outgoing_kills;
std::map<KillKey,KillPacket> pending_kills;
std::map<KillKey,u64> delivered_kills;
u32 death_sequence=0;

void ServiceKills(bool loaded,u64 now) {
    std::vector<KillPacket> send;
    std::vector<std::pair<KillKey,KillPacket>> give;
    {
        std::scoped_lock lock{mutex};
        for(auto it=outgoing_kills.begin();it!=outgoing_kills.end();) {
            auto& e=it->second;
            if(now-e.created>30'000) { it=outgoing_kills.erase(it); continue; }
            if(!e.sent || now-e.sent>=1'000) { send.push_back(e.packet); e.sent=now; }
            ++it;
        }
        if(loaded) for(const auto& e:pending_kills) give.push_back(e);
    }
    for(const auto& [key,packet]:give) {
        if(!Core::Bloodborne::GiveSessionBloodDreg()) continue; // retry after loading/full inventory
        {
            std::scoped_lock lock{mutex};
            pending_kills.erase(key);
            delivered_kills[key]=now;
            if(delivered_kills.size()>512) delivered_kills.erase(delivered_kills.begin());
        }
        KillPacket ack=packet; ack.kind=1; send.push_back(ack);
        LOG_INFO(Mod,"PvP Blood Dreg: awarded for victim {} death {}",packet.victim,packet.death);
    }
    for(const auto& packet:send) SendRegisterPacket(&packet,sizeof(packet));
}

bool Ours(u32 board) { return ready && board==BookBoard; }
void PS4_SYSV_ABI BookUse(u64, const Core::GuestRegisterSnapshot*) {
    // Goods opmeMenuType 8 selects 0x018F72F2, then queues this Ranking factory.
    // Arm before 0x01BBC224 constructs the view and makes its first ranking request.
    range_log_ms=0;
    LOG_INFO(Mod,"Session register: book used; ranking provider armed");
}
std::vector<Rank> Snapshot() {
    const u32 session=RegisterSessionKey();
    std::vector<Rank> out;
    const auto add=[&](const Packet& p) {
        Rank row{};
        std::memcpy(row.id.name,p.identity.name,16);
        row.score=p.offered;
        out.push_back(row);
    };
    std::scoped_lock lock{mutex};
    if (local_loaded) add(local);
    if (session && session==current_session) {
        const u64 now=GetTickCount64();
        for (const auto& [id,e]:members) if(now-e.seen<=15'000) add(e.packet);
    }
    std::sort(out.begin(),out.end(),[](const Rank& a,const Rank& b) {
        return a.score!=b.score ? a.score>b.score : std::memcmp(a.id.name,b.id.name,16)<0;
    });
    u32 rank=1;
    for(size_t i=0;i<out.size();++i) {
        if(i && out[i].score!=out[i-1].score) rank=static_cast<u32>(i+1);
        out[i].serial=static_cast<u32>(i+1); out[i].rank=out[i].highest=rank;
    }
    return out;
}
using RangeFn=s32 PS4_SYSV_ABI (*)(s32,u32,u32,Rank*,u64,void*,u64,void*,u64,u64,u64*,u32*,void*);
using ByIdFn=s32 PS4_SYSV_ABI (*)(s32,u32,const IdPc*,u64,PlayerRank*,u64,void*,u64,void*,u64,u64,u64*,u32*,void*);
using BoardFn=s32 PS4_SYSV_ABI (*)(s32,u32,Board*,void*);
RangeFn original_range=nullptr;
ByIdFn original_by_id=nullptr;
BoardFn original_board=nullptr;
using RecordFn=s32 PS4_SYSV_ABI (*)(s32,u32,s64,const void*,const void*,u32*,const u64*,void*);
using GetDataFn=s32 PS4_SYSV_ABI (*)(s32,u32,const NpId*,u64*,u64,void*,void*);
using RecordDataFn=s32 PS4_SYSV_ABI (*)(s32,u32,s64,u64,u64,const void*,void*);
RecordFn original_record=nullptr;
GetDataFn original_get_data=nullptr;
RecordDataFn original_record_data=nullptr;
constexpr s32 Invalid=static_cast<s32>(0x80550704u);
bool Buffers(void* out,u64 size,u64 stride,void* comments,u64 cs,void* info,u64 is,u64 n,void* option) {
    if(option || !out || !n || n>100 || size!=n*stride ||
       (comments && cs!=n*64) || (info && is!=n*200)) return false;
    std::memset(out,0,size);
    if(comments) std::memset(comments,0,cs);
    if(info) std::memset(info,0,is);
    return true;
}
s32 PS4_SYSV_ABI Range(s32 req,u32 board,u32 first,Rank* rows,u64 size,void* comments,u64 cs,
                      void* info,u64 is,u64 n,u64* date,u32* total,void* option) {
    if(!Ours(board)) return original_range(req,board,first,rows,size,comments,cs,info,is,n,date,total,option);
    if(!first || !Buffers(rows,size,sizeof(Rank),comments,cs,info,is,n,option)) return Invalid;
    const auto all=Snapshot();
    if(date) *date=0;
    if(total) *total=static_cast<u32>(all.size());
    u32 count=0;
    for(u64 i=0;i<n && static_cast<u64>(first)-1+i<all.size();++i) {
        rows[i]=all[first-1+i]; ++count;
    }
    const u64 now=GetTickCount64();
    u64 last=range_log_ms.load();
    if((!last || now-last>=5'000) && range_log_ms.compare_exchange_strong(last,now)) {
        LOG_INFO(Mod,"Session register: board {} range {} rows {} total {}",board,first,count,all.size());
    }
    // The native 0xCCEC80 loop advances by the returned count, NOT totalRecord.
    // Zero means retry forever; 0x80550812 takes its explicit end-of-ranking branch.
    return count ? static_cast<s32>(count) : NoRanking;
}
s32 PS4_SYSV_ABI ById(s32 req,u32 board,const IdPc* ids,u64 ids_size,PlayerRank* rows,u64 size,
                     void* comments,u64 cs,void* info,u64 is,u64 n,u64* date,u32* total,void* option) {
    if(!Ours(board)) return original_by_id(req,board,ids,ids_size,rows,size,comments,cs,info,is,n,date,total,option);
    if(!ids || ids_size!=n*sizeof(IdPc) || !Buffers(rows,size,sizeof(PlayerRank),comments,cs,info,is,n,option)) return Invalid;
    const auto all=Snapshot();
    if(date) *date=0;
    if(total) *total=static_cast<u32>(all.size());
    s32 found=0;
    for(u64 i=0;i<n;++i) for(const auto& r:all) {
        if(std::memcmp(ids[i].id.name,r.id.name,16)==0) {
            rows[i].has_data=1; rows[i].value=r; rows[i].value.pc=ids[i].pc; ++found; break;
        }
    }
    return found ? found : NoRanking;
}
s32 PS4_SYSV_ABI BoardInfo(s32 req,u32 board,Board* out,void* option) {
    if(!Ours(board)) return original_board(req,board,out,option);
    if(!out || option) return Invalid;
    *out={5,0,0,0,0};
    return 0;
}
s32 PS4_SYSV_ABI Record(s32 req,u32 board,s64 score,const void* comment,const void* info,
                       u32* rank,const u64* date,void* option) {
    if(!Ours(board)) return original_record(req,board,score,comment,info,rank,date,option);
    if(option) return Invalid;
    // The Queen has already changed the native character counter. No remote scoreboard upload.
    if(rank) *rank=0;
    return 0;
}
s32 PS4_SYSV_ABI GetData(s32 req,u32 board,const NpId* id,u64* total,u64 size,void* out,void* option) {
    if(!Ours(board)) return original_get_data(req,board,id,total,size,out,option);
    if(total) *total=0;
    return NoRanking; // equipment/profile blob is not provided by this session register
}
s32 PS4_SYSV_ABI RecordData(s32 req,u32 board,s64 score,u64 total,u64 size,const void* data,void* option) {
    if(!Ours(board)) return original_record_data(req,board,score,total,size,data,option);
    return option ? Invalid : 0;
}
template<class Fn> bool Wrap(u64 offset,Fn fn,Fn& original,const char* name) {
    u64 value=0;
    if(!ReadSlotSafely(EbootAddress()+offset,&value) || !value ||
       (value>=EbootAddress() && value<EbootAddress()+0x056D4000)) return false;
    original=reinterpret_cast<Fn>(value);
    if(!WriteSlotSafely(EbootAddress()+offset,reinterpret_cast<u64>(fn))) return false;
    GuardSlot(offset,reinterpret_cast<u64>(fn),reinterpret_cast<void**>(&original),name);
    return true;
}
}
void TickSessionRegister(u32 offered,bool loaded,const RegisterIdentity& identity) {
    const u64 now=GetTickCount64();
    if(now-last_tick<1'000) return;
    last_tick=now;
    const u32 session=RegisterSessionKey();
    Packet packet;
    packet.identity=identity;
    if(!packet.identity.name[0]) {
        const char* name=std::getenv("BB_SHADNET_NPID");
        if(!name || !*name) name=std::getenv("BB_USER_NAME");
        if(name) std::memcpy(packet.identity.name,name,std::min<size_t>(std::strlen(name),16));
    }
    packet.offered=std::min<u32>(offered,99'999);
    // Zero offerings is a valid participant, unlike the prototype's level > 0 gate.
    loaded=loaded && packet.identity.name[0];
    {
        std::scoped_lock lock{mutex};
        if(session!=current_session || !session) {
            members.clear(); pending_kills.clear(); outgoing_kills.clear();
        }
        current_session=session; local=packet; local_loaded=loaded;
    }
    if(loaded && session) SendRegisterPacket(&packet,sizeof(packet));
    ServiceKills(loaded,now);
}
void ReceiveSessionRegister(u32 sender,u32 session,const void* data,u32 size) {
    if(size!=sizeof(Packet) || !sender || !session || session!=RegisterSessionKey()) return;
    Packet packet; std::memcpy(&packet,data,sizeof(packet));
    if(std::memcmp(packet.magic,"SHAD",4) || packet.type!=0x2B || packet.version!=2 ||
       !packet.identity.name[0] || packet.identity.name[16] || packet.offered>99'999) return;
    std::scoped_lock lock{mutex};
    if(session!=current_session || (members.size()>=4 && !members.contains(sender))) return;
    members[sender]={packet,GetTickCount64()};
}
void QueueRegisterKill(const RegisterIdentity& killer) {
    const u32 session=RegisterSessionKey();
    if(!session) return;
    std::scoped_lock lock{mutex};
    if(session!=current_session) {
        members.clear(); pending_kills.clear(); outgoing_kills.clear(); current_session=session;
    }
    if(SameMember(killer,local.identity) || outgoing_kills.size()>=32) return;
    KillPacket packet; packet.victim=RegisterOwnId(); packet.death=++death_sequence; packet.killer=killer;
    outgoing_kills.emplace(packet.death,OutgoingKill{packet,GetTickCount64(),0});
    LOG_INFO(Mod,"PvP Blood Dreg: lethal hit, victim {} death {} killer room {} member {}",
             packet.victim,packet.death,killer.room,killer.member);
}
void ReceiveRegisterKill(u32 sender,u32 session,const void* data,u32 size) {
    if(!sender || !session || session!=RegisterSessionKey() || size!=sizeof(KillPacket)) return;
    KillPacket packet; std::memcpy(&packet,data,sizeof(packet));
    if(std::memcmp(packet.magic,"SHAD",4) || packet.type!=0x2C || packet.version!=1 ||
       packet.kind>1 || !packet.death || packet.killer.name[16]) return;
    bool ack=false;
    {
        std::scoped_lock lock{mutex};
        if(session!=current_session) return;
        if(packet.kind==1) {
            const auto it=outgoing_kills.find(packet.death);
            const auto member=members.find(sender);
            if(packet.victim==RegisterOwnId() && it!=outgoing_kills.end() && member!=members.end() &&
               SameMember(member->second.packet.identity,it->second.packet.killer) &&
               SameMember(packet.killer,it->second.packet.killer)) outgoing_kills.erase(it);
            return;
        }
        if(packet.victim!=sender || !SameMember(packet.killer,local.identity)) return;
        const KillKey key{session,sender,packet.death};
        if(delivered_kills.contains(key)) ack=true;
        else if(pending_kills.size()<32) pending_kills.emplace(key,packet);
    }
    if(ack) { packet.kind=1; SendRegisterPacket(&packet,sizeof(packet)); }
}
void ForgetSessionRegister(u32 sender) { std::scoped_lock lock{mutex}; members.erase(sender); }
void InstallSessionRegister() {
    if(const char* v=std::getenv("BBSC_SESSION_REGISTER");v && *v=='0') return;
    const std::array<u8,6> bytes{0x55,0x48,0x89,0xE5,0x41,0x57};
    if(!Core::InstallGuestCodeHook(reinterpret_cast<void*>(EbootAddress()+0x01BBC1E0),bytes,0,BookUse)) {
        LOG_ERROR(Mod,"Session register: book hook unavailable"); return;
    }
    const bool a=Wrap(0x053E5258,Range,original_range,"SessionRegister.Range");
    const bool b=Wrap(0x053E5248,ById,original_by_id,"SessionRegister.ById");
    const bool c=Wrap(0x053E5278,BoardInfo,original_board,"SessionRegister.BoardInfo");
    const bool d=Wrap(0x053E5270,Record,original_record,"SessionRegister.Record");
    const bool e=Wrap(0x053E5268,GetData,original_get_data,"SessionRegister.GetData");
    const bool f=Wrap(0x053E5288,RecordData,original_record_data,"SessionRegister.RecordData");
    ready=a && b && c && d && e && f;
    Core::Bloodborne::InstallSessionDregHooks();
    LOG_INFO(Mod,"Session register installed: range={} by-id={} board={} record={} data={} upload={}",a,b,c,d,e,f);
}
}
