// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include "core/bbsc_world_control.h"
#include "core/bbsc_world_native_initial.h"

namespace Core::Bloodborne::World {
inline constexpr u32 BlockCapability=8;
inline Scope BlockScope(Scope scope,u32 block) {
    // Adjacent ordinary maps can be streamed by players standing on opposite
    // sides of a border. Their SAME native block must have exactly ONE lease.
    if(!Chalice::IsMap(scope.map) && ValidMap(block))scope.map=block;
    return scope;
}
// Opaque records from native0190E750, consumed by native0190E8B0. No HP,
// transforms, AI state, reward rolls or actor pointers are put in this table.
inline bool ValidNativeBlock(std::span<const u8> record) {
    if(record.size()<13 || record.size()>140)return false;
    const auto count=NativeInitialWord(record,8);
    return NativeInitialWord(record,0)!=0xffffffffu && count && count<=1024 &&
        record.size()==12+(count+7)/8 && NativeInitialWord(record,4)==record.size();
}
inline bool MergeNativeDeaths(std::vector<u8>& into,std::span<const u8> record) {
    if(!ValidNativeBlock(record))return false;
    if(into.empty()){into.assign(record.begin(),record.end());return true;}
    if(into.size()!=record.size() || std::memcmp(into.data(),record.data(),12))return false;
    for(size_t i=12;i<into.size();++i)into[i]|=record[i];
    return true;
}
struct BlockLease {
    u32 owner=0,retiring=0,target=0;
    u64 epoch=0;
    std::vector<u8> native;
};
struct BlockOffer {u64 visit=0,sequence=0,epoch=0;bool active=false,retired=false;std::vector<u8> native;bool loaded=true;Scope origin{};};
struct BlockState {BlockLease lease;std::map<u32,BlockOffer> offers;bool empty=false;};
// Only the native room host runs this coordinator. An owner is revoked and
// acknowledges its FINAL native record before a successor is admitted.
class BlockCoordinator {
public:
    void Bind(WorldId world){if(world_!=world){world_=world;blocks_.clear();last_.clear();}}
    bool Offer(const Scope& scope,u32 peer,const BlockOffer& offer) {
        if(scope.world!=world_ || !Valid(scope) || !peer || !offer.visit || !offer.sequence ||
           !ValidNativeBlock(offer.native))return false;
        const u32 id=NativeInitialWord(offer.native,0);
        auto key=std::pair{BlockScope(scope,id),id};
        if(!blocks_.contains(key) && blocks_.size()>=2048)return false;
        auto& fence=last_[{key.first,peer}];
        // Sequence is process-wide, so one report contains multiple different
        // blocks; fence each block separately rather than dropping its siblings.
        auto& last=fence[id];
        if(offer.sequence<=last.first || offer.visit<last.second)return false;
        auto& state=blocks_[key];auto& old=state.offers[peer];
        if(!state.lease.native.empty() && (state.lease.native.size()!=offer.native.size() ||
           std::memcmp(state.lease.native.data(),offer.native.data(),12)))return false;
        // The first report after vacancy starts from the freshly loaded native
        // world, never from the previous visit's historical death bits.
        if(state.empty)state.lease.native=offer.native;
        last={offer.sequence,offer.visit};old=offer;state.empty=false;
        if(state.lease.owner==peer && state.lease.epoch==offer.epoch)
            MergeNativeDeaths(state.lease.native,offer.native);
        if(state.lease.retiring==peer && state.lease.epoch==offer.epoch && (offer.retired || !offer.loaded)){
            MergeNativeDeaths(state.lease.native,offer.native);
            state.lease.retiring=0;
        }
        return true;
    }
    template<class Occupied> void ResetUnoccupied(Occupied occupied) {
        for(auto& [key,state]:blocks_)if(!state.empty && !occupied(key.first) &&
            std::ranges::none_of(state.offers,[&](const auto& offer){
                return Valid(offer.second.origin) && occupied(offer.second.origin);})){
            state.empty=true;state.offers.clear();
            // A complete native map departure/reload starts a new ordinary
            // enemy life. Streaming a block out while anyone remains in the
            // scope does NOT reset it. Persistent boss flags stay in world sync.
            state.lease.owner=state.lease.retiring=state.lease.target=0;
            ++state.lease.epoch;
            // Keep the native header so the vacancy fence can be broadcast even
            // with no offers. Owner zero prevents applying this reset record.
            if(ValidNativeBlock(state.lease.native))
                std::fill(state.lease.native.begin()+12,state.lease.native.end(),0);
        }
    }
    // Presence/connection removal, never a heartbeat timeout. An explicit load
    // or native departure invalidates the old offer; cached native deaths remain.
    template<class Resident> void Elect(Resident resident) {
        for(auto& [key,state]:blocks_){auto& lease=state.lease;
            for(auto it=state.offers.begin();it!=state.offers.end();)
                if(!it->second.loaded || !resident(it->first,Valid(it->second.origin)?it->second.origin:key.first,it->second.visit))it=state.offers.erase(it);else ++it;
            u32 best=0;
            for(const auto& [peer,offer]:state.offers){
                if(!best || (offer.active && !state.offers.at(best).active))best=peer;
            }
            if(lease.owner && state.offers.contains(lease.owner) &&
               (!best || state.offers.at(lease.owner).active || !state.offers.at(best).active))best=lease.owner;
            if(lease.retiring){
                if(state.offers.contains(lease.retiring))continue;
                lease.retiring=0; // an explicit departure is an authority fence
            }
            if(lease.owner==best)continue;
            if(lease.owner && state.offers.contains(lease.owner)){
                lease.retiring=lease.owner;lease.target=best;lease.owner=0;++lease.epoch;
            }else{
                lease.owner=best;lease.target=0;++lease.epoch;
                if(best && lease.native.empty())lease.native=state.offers.at(best).native;
            }
        }
    }
    const auto& Blocks()const{return blocks_;}
private:
    WorldId world_{};
    std::map<std::pair<Scope,u32>,BlockState> blocks_;
    std::map<std::pair<Scope,u32>,std::map<u32,std::pair<u64,u64>>> last_;
};
#pragma pack(push,1)
// Offers: visit/origin_map identify the reporting player's map visit.
// Leases: origin_map is the acknowledged peer ID, visit is its offer's visit;
// both are zero for the vacancy broadcast. Wire size stays unchanged.
struct BlockWire {u64 visit=0;u32 block=0,retiring=0;u8 active=0,retired=0,loaded=1,reserved=0;u32 origin_map=0;};
#pragma pack(pop)
inline std::vector<u8> EncodeBlock(BlockWire wire,std::span<const u8> native) {
    if(!ValidNativeBlock(native) || NativeInitialWord(native,0)!=wire.block)return {};
    std::vector<u8> out(sizeof(wire)+native.size());
    std::memcpy(out.data(),&wire,sizeof(wire));std::memcpy(out.data()+sizeof(wire),native.data(),native.size());return out;
}
inline std::optional<BlockWire> DecodeBlock(std::span<const u8> payload) {
    if(payload.size()<sizeof(BlockWire))return {};
    BlockWire wire;std::memcpy(&wire,payload.data(),sizeof(wire));
    const auto record=payload.subspan(sizeof(wire));
    if(wire.reserved || wire.active>1 || wire.retired>1 || wire.loaded>1 || !ValidNativeBlock(record) ||
       NativeInitialWord(record,0)!=wire.block)return {};
    return wire;
}
} // namespace Core::Bloodborne::World
