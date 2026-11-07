// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <array>
#include <cstdint>
#ifdef BBSC_NATIVE_AI_EMITTER
#include <xbyak/xbyak.h>
#endif
namespace Xbyak { class CodeGenerator; }

namespace Core::Bloodborne::NativeAi {
// Native request construction, after its existing active/requested/special
// character gates. Retain an eligible native holder until it releases the NPC.
inline constexpr std::array<unsigned char,10> Request{
    0x48,0x89,0xDF,0x89,0xD3,0xE8,0xF4,0x66,0xFB,0xFF};
inline constexpr std::array<unsigned char,7> EmptySelf{0x85,0xF6,0x7E,0x08,0x48,0x89,0xC7};
inline constexpr std::array<unsigned char,6> EmptyPeer{0x0F,0x8E,0x29,0xFF,0xFF,0xFF};
inline constexpr std::array<unsigned char,7> RequestMember{0x48,0x8D,0x05,0x45,0xDF,0xC4,0x03};
inline constexpr std::array<unsigned char,5> RetainMember{0x83,0xFB,0xFF,0x74,0x45};
inline constexpr std::array<unsigned char,7> GrantMember{0x48,0x8D,0x05,0x01,0x14,0xC5,0x03};
// ReceiveFromMember's native channel classification, BEFORE queue consumption.
// NPC requests/grants must not require a remote PlayerIns on the receiver's map.
inline constexpr std::array<unsigned char,10> ReceiveChannels{
    0x48,0xB9,0x7B,0x06,0x04,0x00,0x00,0x00,0x00,0x08};
void EmitReceiveChannels(Xbyak::CodeGenerator& out,uint64_t image,uint64_t);
void EmitRequest(Xbyak::CodeGenerator& out,uint64_t image,uint64_t roles);
void EmitEmptySelf(Xbyak::CodeGenerator& out,uint64_t image,uint64_t);
void EmitEmptyPeer(Xbyak::CodeGenerator& out,uint64_t image,uint64_t);
void EmitRequestMember(Xbyak::CodeGenerator& out,uint64_t image,uint64_t resolve);
void EmitRetainMember(Xbyak::CodeGenerator& out,uint64_t image,uint64_t resolve);
void EmitGrantMember(Xbyak::CodeGenerator& out,uint64_t image,uint64_t resolve);
#ifdef BBSC_NATIVE_AI_EMITTER
void EmitReceiveChannels(Xbyak::CodeGenerator& out,uint64_t image,uint64_t) {
    using namespace Xbyak::util;
    // Extend the original actor-independent allowlist by exactly channels16/17.
    // Native session/endpoint/identity lookup and queue receive still follow.
    out.mov(rcx,uint64_t{0x80000000004067B}|(uint64_t{1}<<(0x16-7))|(uint64_t{1}<<(0x17-7)));
    out.jmp(reinterpret_cast<void*>(image+0x0178927E),Xbyak::CodeGenerator::T_NEAR);
}
void EmitRequestMember(Xbyak::CodeGenerator& out,uint64_t image,uint64_t resolve) {
    using namespace Xbyak::util;
    Xbyak::Label original;
    // The original ReceiveFromMember just returned a positive packet length.
    // No caller-saved register is live here; RBP owns the sender/sync slots.
    out.mov(esi,eax);out.mov(rdi,qword[rbp-0x30]);out.mov(rax,resolve);out.call(rax);
    out.cmp(eax,1);out.je(original);
    out.test(eax,eax);out.jz(reinterpret_cast<void*>(image+0x018F0900));
    out.mov(esi,eax);
    out.jmp(reinterpret_cast<void*>(image+0x018F09BE),Xbyak::CodeGenerator::T_NEAR);
    out.L(original);out.mov(rax,image+0x0553E878);
    out.jmp(reinterpret_cast<void*>(image+0x018F0933),Xbyak::CodeGenerator::T_NEAR);
}
void EmitRetainMember(Xbyak::CodeGenerator& out,uint64_t image,uint64_t resolve) {
    using namespace Xbyak::util;
    Xbyak::Label lookup;
    out.cmp(ebx,-1);out.je(reinterpret_cast<void*>(image+0x018ED200));
    // Keep the local player's original O(1) path without a C++ callback.
    out.test(ebx,ebx);out.js(lookup);
    out.mov(rcx,qword[rax+0x60]);out.test(rcx,rcx);out.jz(lookup);
    out.cmp(ebx,dword[rcx+8]);out.je(reinterpret_cast<void*>(image+0x018ED1BB));
    out.L(lookup);
    // Result1 retains the original lookup for self / native join fallback;
    // a real member pointer retains a room key; zero prunes stale/alias keys.
    out.sub(rsp,16);out.mov(qword[rsp],r8);out.mov(qword[rsp+8],rax);
    out.mov(edi,ebx);out.mov(rax,resolve);out.call(rax);
    out.mov(rdx,rax);out.mov(r8,qword[rsp]);out.mov(rax,qword[rsp+8]);out.add(rsp,16);
    out.test(rdx,rdx);out.jz(reinterpret_cast<void*>(image+0x018ED200));
    out.cmp(rdx,1);out.je(reinterpret_cast<void*>(image+0x018ED1BB));
    out.jmp(reinterpret_cast<void*>(image+0x018ED166),Xbyak::CodeGenerator::T_NEAR);
}
void EmitGrantMember(Xbyak::CodeGenerator& out,uint64_t image,uint64_t resolve) {
    using namespace Xbyak::util;
    Xbyak::Label original;
    out.test(ebx,ebx);out.jns(original);
    out.sub(rsp,16);out.mov(qword[rsp],r8);
    out.mov(edi,ebx);out.mov(rax,resolve);out.call(rax);
    out.mov(r8,qword[rsp]);out.add(rsp,16);
    out.test(rax,rax);out.jz(reinterpret_cast<void*>(image+0x018ED67F));
    // Native018ED399 adds3D8 to R14 before SendToMember. Supply its actual
    // roster identity through that same final add; no fake PlayerIns exists.
    out.lea(r14,ptr[rax-0x3D8]);
    out.jmp(reinterpret_cast<void*>(image+0x018ED52A),Xbyak::CodeGenerator::T_NEAR);
    out.L(original);out.mov(rax,image+0x0553E878);
    out.jmp(reinterpret_cast<void*>(image+0x018ED477),Xbyak::CodeGenerator::T_NEAR);
}
void EmitRequest(Xbyak::CodeGenerator& out,uint64_t image,uint64_t) {
    using namespace Xbyak::util;
    Xbyak::Label done,not_max;
    // Keep native eligibility, including proxy/death and priority-zero exits.
    // Save the actor across the original call without changing ABI alignment.
    out.mov(rdi,rbx);out.mov(ebx,edx);
    out.sub(rsp,16);out.mov(qword[rsp],rdi);
    out.call(reinterpret_cast<void*>(image+0x018CD180));
    out.mov(rcx,qword[rsp]);out.add(rsp,16);
    out.test(eax,eax);out.jz(done,Xbyak::CodeGenerator::T_NEAR);
    // Original priorities occupy 0..7FFF. Reserve their top value for the
    // current holder, leaving ties between simultaneous first requests native.
    out.cmp(eax,0x7FFF);out.jne(not_max);out.dec(eax);out.L(not_max);
    out.mov(esi,dword[rcx+0x90]);out.test(esi,esi);out.js(done,Xbyak::CodeGenerator::T_NEAR);
    out.mov(rdx,image+0x0553E878);out.mov(rdx,qword[rdx]);out.test(rdx,rdx);out.jz(done,Xbyak::CodeGenerator::T_NEAR);
    out.mov(rdx,qword[rdx+0xA40]);out.test(rdx,rdx);out.jz(done,Xbyak::CodeGenerator::T_NEAR);
    out.mov(ecx,esi);out.shr(ecx,11);out.and_(ecx,31);
    out.cmp(ecx,dword[rdx+8]);out.jae(done,Xbyak::CodeGenerator::T_NEAR);
    out.mov(rdx,qword[rdx+rcx*8+0x10]);out.test(rdx,rdx);out.jz(done,Xbyak::CodeGenerator::T_NEAR);
    out.and_(esi,0x7FF);out.cmp(esi,dword[rdx+0x10]);out.jae(done,Xbyak::CodeGenerator::T_NEAR);
    out.mov(rdx,qword[rdx+0x18]);out.cmp(word[rdx+rsi*2],0);out.js(done,Xbyak::CodeGenerator::T_NEAR);
    out.mov(eax,0x7FFF);
    out.L(done);
    out.jmp(reinterpret_cast<void*>(image+0x01916A8C),Xbyak::CodeGenerator::T_NEAR);
}
// A valid zero-length request replaces the previous list too. The native
// list assignment already supports zero. Negative lengths still fail closed.
void EmitEmptySelf(Xbyak::CodeGenerator& out,uint64_t image,uint64_t) {
    using namespace Xbyak::util;
    out.test(esi,esi);out.js(reinterpret_cast<void*>(image+0x018F088C));
    out.mov(rdi,rax);
    out.jmp(reinterpret_cast<void*>(image+0x018F0887),Xbyak::CodeGenerator::T_NEAR);
}
void EmitEmptyPeer(Xbyak::CodeGenerator& out,uint64_t image,uint64_t) {
    out.js(reinterpret_cast<void*>(image+0x018F0900));
    out.jmp(reinterpret_cast<void*>(image+0x018F09D7),Xbyak::CodeGenerator::T_NEAR);
}

#endif
} // namespace Core::Bloodborne::NativeAi
