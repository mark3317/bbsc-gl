#pragma once
#include <cstdint>
namespace BbscMod {
bool PartyEnabled();
bool PartyAcquire(); // actual item execution only; blocks at most eight seconds, fails closed
bool PartyCanBeckon(); // cached availability; never grants a role
void PartyObserve(std::int32_t state, bool loading, bool bell);
void PartyMaintain(); // existing mod maintenance worker, not the frame thread
}
