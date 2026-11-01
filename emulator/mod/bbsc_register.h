#pragma once
#include "common/types.h"
namespace BbscMod {
void InstallSessionRegister();
void TickSessionRegister(s32 level, bool loaded);
void ReceiveSessionRegister(u32 sender, u32 session, const void* data, u32 size);
void ForgetSessionRegister(u32 sender);
u32 RegisterSessionKey();
u32 SendRegisterPacket(const void* data, u32 size);
}
