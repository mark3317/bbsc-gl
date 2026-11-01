// SPDX-License-Identifier: GPL-2.0-or-later
// Session-local provider for the original Vileblood Register (goods 130).
#include <windows.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <cstring>
#include <cstdlib>
#include <map>
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
struct Packet { char magic[4]={'S','H','A','D'}; u8 type=0x2B, version=1;
    char name[17]{}; s32 level=0; };
#pragma pack(pop)
static_assert(sizeof(Packet)==27);
struct Entry { Packet packet; u64 seen; };
std::mutex mutex;
std::map<u32,Entry> members;
Packet local;
u32 current_session=0;
bool local_loaded=false;
std::atomic<bool> ready{false};
std::atomic<u64> used_at{0};
std::atomic<s64> selected_board{-1};
u64 last_tick=0;

bool Ours(u32 board) {
    const u64 used=used_at.load();
    if (!ready || !used || GetTickCount64()-used>600'000) return false;
    s64 expected=-1;
    selected_board.compare_exchange_strong(expected,board);
    return selected_board.load()==board;
}
void PS4_SYSV_ABI BookUse(u64, const Core::GuestRegisterSnapshot*) {
    // Goods opmeMenuType 8 selects 0x018F72F2, then queues this Ranking factory.
    // Arm before 0x01BBC224 constructs the view and makes its first ranking request.
    selected_board=-1;
    used_at=GetTickCount64();
    LOG_INFO(Mod,"Session register: book used; ranking provider armed");
}
std::vector<Rank> Snapshot() {
    const u32 session=RegisterSessionKey();
    std::vector<Rank> out;
    const auto add=[&](const Packet& p) {
        Rank row{};
        std::memcpy(row.id.name,p.name,16);
        row.score=p.level;
        out.push_back(row);
    };
    std::scoped_lock lock{mutex};
    if (local_loaded) add(local);
    if (session && session==current_session) {
        const u64 now=GetTickCount64();
        for (const auto& [id,e]:members) if(now-e.seen<=5'000) add(e.packet);
    }
    std::sort(out.begin(),out.end(),[](const Rank& a,const Rank& b) {
        return a.score!=b.score ? a.score>b.score : std::memcmp(a.id.name,b.id.name,16)<0;
    });
    for(size_t i=0;i<out.size();++i) out[i].rank=out[i].serial=out[i].highest=static_cast<u32>(i+1);
    return out;
}
using RangeFn=s32 PS4_SYSV_ABI (*)(s32,u32,u32,Rank*,u64,void*,u64,void*,u64,u64,u64*,u32*,void*);
using ByIdFn=s32 PS4_SYSV_ABI (*)(s32,u32,const IdPc*,u64,PlayerRank*,u64,void*,u64,void*,u64,u64,u64*,u32*,void*);
using BoardFn=s32 PS4_SYSV_ABI (*)(s32,u32,Board*,void*);
RangeFn original_range=nullptr;
ByIdFn original_by_id=nullptr;
BoardFn original_board=nullptr;
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
    LOG_INFO(Mod,"Session register: board {} range {} rows {} total {}",board,first,count,all.size());
    return static_cast<s32>(count);
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
    return found;
}
s32 PS4_SYSV_ABI BoardInfo(s32 req,u32 board,Board* out,void* option) {
    if(!Ours(board)) return original_board(req,board,out,option);
    if(!out || option) return Invalid;
    *out={6,0,0,0,0};
    return 0;
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
void TickSessionRegister(s32 level,bool loaded) {
    const u64 now=GetTickCount64();
    if(now-last_tick<1'000) return;
    last_tick=now;
    const u32 session=RegisterSessionKey();
    Packet packet;
    const char* name=std::getenv("BB_SHADNET_NPID");
    if(!name || !*name) name=std::getenv("BB_USER_NAME");
    if(name) std::memcpy(packet.name,name,std::min<size_t>(std::strlen(name),16));
    packet.level=level;
    loaded=loaded && level>=1 && level<=544 && packet.name[0];
    {
        std::scoped_lock lock{mutex};
        if(session!=current_session || !session) members.clear();
        current_session=session; local=packet; local_loaded=loaded;
    }
    if(loaded && session) SendRegisterPacket(&packet,sizeof(packet));
}
void ReceiveSessionRegister(u32 sender,u32 session,const void* data,u32 size) {
    if(size!=sizeof(Packet) || !sender || !session || session!=RegisterSessionKey()) return;
    Packet packet; std::memcpy(&packet,data,sizeof(packet));
    if(std::memcmp(packet.magic,"SHAD",4) || packet.type!=0x2B || packet.version!=1 ||
       !packet.name[0] || packet.name[16] || packet.level<1 || packet.level>544) return;
    std::scoped_lock lock{mutex};
    if(session!=current_session || (members.size()>=5 && !members.contains(sender))) return;
    members[sender]={packet,GetTickCount64()};
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
    ready=a && b && c;
    LOG_INFO(Mod,"Session register installed: range={} by-id={} board={}",a,b,c);
}
}
