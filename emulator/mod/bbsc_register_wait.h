#pragma once
#include "common/types.h"

namespace BbscMod {
// Ranking's native cache has up to ten 0x50-byte slots. The mod's board has at
// most five real rows; empty trailing slots must not keep dialog 305003 open.
// Reader copies eight bytes safely; no native cache flags or ownership are changed.
template<class Reader>
bool RegisterWaitCanFinish(u64 owner,u32 expected,bool received,Reader read) {
    if(!owner || !received || expected>5) return false;
    u64 board=0,count=0;
    if(!read(owner+0x2858,&board) || static_cast<u32>(board)!=19 ||
       !read(owner+0x1120,&count) || count>10 || count<expected) return false;
    const u64 start=(owner+0xDF8+7)&~u64{7};
    for(u32 i=0;i<expected;++i) {
        u64 row=0;
        if(!read(start+i*0x50,&row) || (row&0xFF)==0) return false;
    }
    return true;
}
}
