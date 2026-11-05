#pragma once
#include "common/types.h"
namespace BbscMod {
#pragma pack(push, 1)
struct RegisterIdentity {
    char name[17]{};
    u32 room = 0;
    u16 member = 0;
};
#pragma pack(pop)
void InstallSessionRegister();
void TickSessionRegister(u32 offered, bool loaded, const RegisterIdentity& identity);
void ReceiveSessionRegister(u32 sender, u32 session, const void* data, u32 size);
void ReceiveRegisterKill(u32 sender, u32 session, const void* data, u32 size);
void QueueRegisterKill(const RegisterIdentity& killer);
void ForgetSessionRegister(u32 sender);
u32 FindSessionRegisterPeer(const RegisterIdentity& identity);
u32 RegisterSessionKey();
u32 RegisterOwnId();
u32 SendRegisterPacket(const void* data, u32 size);
}
namespace Core::Bloodborne {
bool GiveSessionBloodDreg(); // called only from the game tick, never a network worker
void InstallSessionDregHooks();
}
