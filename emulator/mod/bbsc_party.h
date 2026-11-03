#pragma once
#include <cstdint>
namespace BbscMod {
bool PartyEnabled();
bool PartyAcquire(); // actual item execution only; blocks at most eight seconds, fails closed
void PartyCancel(); // explicit Blank, search cancellation or confirmed menu exit
bool PartyTitleReady(); // current cancel acknowledged by final party membership
bool PartyCanBeckon(); // cached availability; never grants a role
void PartyObserve(std::int32_t state, bool loading, bool bell);
void PartyMaintain(); // existing mod maintenance worker, not the frame thread
}
