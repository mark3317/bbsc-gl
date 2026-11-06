// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <optional>
#include <span>
#include <vector>
#include "core/bbsc_world_presence.h"

namespace Core::Bloodborne::World {
// Views into one native channel11 packet, not retained enemy state. Native
// 01786360 builds three length-prefixed sections; only CHR is relevant here.
inline u32 NativeInitialWord(std::span<const u8> bytes, size_t at) {
    u32 value=0;std::memcpy(&value,bytes.data()+at,4);return value;
}
inline u64 NativeInitialFingerprint(std::span<const u8> bytes) {
    u64 value=14695981039346656037ull;
    for(const auto byte:bytes){value^=byte;value*=1099511628211ull;}
    return value;
}
inline std::optional<std::vector<std::span<const u8>>> NativeInitialCharacters(std::span<const u8> bytes) {
    if(bytes.size()>0x6400)return {};
    size_t at=0;std::span<const u8> chr;
    for(unsigned section=0;section<3;++section){
        if(bytes.size()-at<4)return {};
        const u32 size=NativeInitialWord(bytes,at);at+=4;
        if(size>bytes.size()-at)return {};
        if(section==2)chr=bytes.subspan(at,size);
        at+=size;
    }
    if(at!=bytes.size() || chr.size()<20 || NativeInitialWord(chr,0)!=0x43485220 ||
       NativeInitialWord(chr,4)!=0x15091700)return {};
    std::vector<std::span<const u8>> records;
    at=8;
    while(chr.size()-at>=12){
        const u32 map=NativeInitialWord(chr,at),size=NativeInitialWord(chr,at+4),count=NativeInitialWord(chr,at+8);
        if(map==0xFFFFFFFFu)return size==0 && count==0 && at+12==chr.size()?std::optional{records}:std::nullopt;
        if(!count || count>1024 || size!=12+(count+7)/8 || size>chr.size()-at || records.size()>=64)return {};
        for(const auto record:records)if(NativeInitialWord(record,0)==map)return {};
        records.push_back(chr.subspan(at,size));at+=size;
    }
    return {};
}
} // namespace Core::Bloodborne::World
