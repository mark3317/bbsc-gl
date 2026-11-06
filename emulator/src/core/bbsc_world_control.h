// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <tuple>
#include <vector>
#include "core/bbsc_world_presence.h"

namespace Core::Bloodborne::World {
inline constexpr u32 OwnerCapability = 4;
#pragma pack(push,1)
struct Scope {
    WorldId world{};
    u32 map = 0;
    Chalice::Key dungeon{};
    u64 ritual = 0;
    bool operator==(const Scope&) const = default;
    bool operator<(const Scope& b) const {
        return std::tie(world.host,world.room,map,dungeon.channel,dungeon.form_hash,
                        dungeon.form_size,dungeon.form_version,ritual) <
               std::tie(b.world.host,b.world.room,b.map,b.dungeon.channel,b.dungeon.form_hash,
                        b.dungeon.form_size,b.dungeon.form_version,b.ritual);
    }
};
#pragma pack(pop)
inline Scope ScopeOf(const Presence& p) {
    // Layout IDs (m29_XX_YY) identify geometry, not a different event namespace.
    // All mounted dungeons use m29_00 flags; key+ritual distinguish their worlds.
    return {p.world,Chalice::IsMap(p.map)?0x1D000000u:p.map,p.dungeon,p.ritual};
}
// Destination intent never changes the namespace of CURRENT-map events.
// Use its ritual only when it names the map being queried, in the same world.
inline Scope ScopeForMap(const Scope& local,u32 map,const std::optional<Scope>& requested) {
    const u32 target=Chalice::IsMap(map)?0x1D000000u:map;
    Scope scope=local;
    if(requested && requested->world==local.world &&
       (Chalice::IsMap(requested->map)?0x1D000000u:requested->map)==target)
        scope=*requested;
    scope.map=target;
    if(!Chalice::IsMap(target)){scope.dungeon={};scope.ritual=0;}
    return scope;
}
inline bool Valid(const Scope& s) {
    if (!Valid(s.world) || !ValidMap(s.map)) return false;
    return Chalice::IsMap(s.map) ? Chalice::Valid(s.dungeon) && s.ritual != 0 :
                                 s.dungeon == Chalice::Key{} && s.ritual == 0;
}
// Wire value3 (Enemies) is reserved for old builds; no enemy payload is produced or applied.
enum class ControlKind : u8 { Owner=1, Flags=2, Enemies=3, Request=4, Altar=5, AltarRequest=6, AltarProgress=7,
    NativeInitialRequest=8, NativeInitialReady=9, Lamps=10, BlockOffer=11, BlockLease=12, LampCheckpoint=13 };
#pragma pack(push,1)
struct Control {
    char magic[4]={'S','H','A','D'};
    u8 type=Protocol::WorldControl;
    u8 version=2;
    ControlKind kind=ControlKind::Owner;
    u8 reserved=0;
    Scope scope{};
    u32 owner=0;
    u64 epoch=0;
    u64 sequence=0;
    std::uint16_t part=0,parts=1,size=0,padding=0;
};
#pragma pack(pop)
static_assert(sizeof(Control)==84);
inline bool Valid(const Control& c) {
    return !std::memcmp(c.magic,"SHAD",4) && c.type==Protocol::WorldControl &&
        c.version==2 && !c.reserved && !c.padding && Valid(c.scope) &&
        c.kind>=ControlKind::Owner && c.kind<=ControlKind::LampCheckpoint &&
        c.parts>0 && c.parts<=32 && c.part<c.parts && c.size<=2048 &&
        (c.kind!=ControlKind::Owner || (c.parts==1 && c.part==0 && c.size==0 && c.epoch!=0));
}
inline std::vector<u8> Encode(Control c,std::span<const u8> payload={}) {
    if(payload.size()>2048) return {};
    c.size=static_cast<std::uint16_t>(payload.size());
    if(!Valid(c)) return {};
    std::vector<u8> bytes(sizeof(c)+payload.size());
    std::memcpy(bytes.data(),&c,sizeof(c));
    if(!payload.empty()) std::memcpy(bytes.data()+sizeof(c),payload.data(),payload.size());
    return bytes;
}
inline std::optional<Control> DecodeControl(std::span<const u8> bytes) {
    if(bytes.size()<sizeof(Control)) return {};
    Control c;std::memcpy(&c,bytes.data(),sizeof(c));
    return Valid(c)&&bytes.size()==sizeof(c)+c.size ? std::optional{c}:std::nullopt;
}
// A current owner must not reapply its own delayed coordinator echo. Dream
// phase/services use their existing host-only protocol, not a map owner's view.
inline bool ShouldApplyFlags(const Control& c,const Scope& local,u32 self,u32 owner,
                             bool host,bool complete) {
    if(!self || c.scope.world!=local.world || c.kind!=ControlKind::Flags || !complete || c.scope.map==0x15000000)return false;
    if(c.scope==local)return owner!=self;
    return host && !Chalice::IsMap(c.scope.map);
}
struct OwnerLease {u32 owner=0;u64 epoch=0;s64 received=0;};
class OwnerBook {
public:
    void Bind(WorldId world){if(world_!=world){world_=world;leases_.clear();}}
    bool Take(u32 sender,const Control& c,s64 now){
        if(sender!=world_.host || c.scope.world!=world_ || !Valid(c) || c.kind!=ControlKind::Owner) return false;
        auto it=leases_.find(c.scope);
        if(it!=leases_.end() && (c.epoch<it->second.epoch ||
            (c.epoch==it->second.epoch && c.owner!=it->second.owner))) return false;
        leases_[c.scope]={c.owner,c.epoch,now};return true;
    }
    const OwnerLease* Find(const Scope& s) const {
        const auto it=leases_.find(s);return it==leases_.end()?nullptr:&it->second;
    }
    void Clear(){Bind({});}
private:
    WorldId world_{};
    std::map<Scope,OwnerLease> leases_;
};
} // namespace Core::Bloodborne::World
