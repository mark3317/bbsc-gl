#pragma once
#include <cstdint>
#include <string>
#include "bbsc_party_acquire.h"
namespace BbscMod {
std::string AimedPlacementAcknowledgment(); // accepted native placement, empty after expiry/leave
bool PartyEnabled();
std::uint64_t PartyRequestAcquire(); // enqueue only: never performs network I/O
PartyAcquireMailbox::Result PartyAcquireResult(std::uint64_t ticket);
void PartyFinishAcquire(std::uint64_t ticket);
void PartyCancel(); // explicit Blank, search cancellation or confirmed menu exit
void PartyEndTitleWait(); // cancel the pending title ticket
bool PartyTitleReady(); // current cancel acknowledged by final party membership
bool PartyCanBeckon(); // cached availability; never grants a role
std::uint64_t PartyBellGeneration(); // fresh finalized remote reservation
std::uint64_t PartyBellReleasedGeneration(); // finalized unowned generation; zero if unknown/owned
unsigned PartyHostHint(); // 1: remote host, 2: yield an empty competing search
void PartyObserve(std::int32_t state, bool loading, bool bell, std::int32_t members, bool alive, bool responder = false);
void PartyMaintain(); // existing mod maintenance worker, not the frame thread
}
