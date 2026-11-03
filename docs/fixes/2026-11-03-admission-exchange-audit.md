# Admission audit and corrections — 2026-11-03

## Current path

1. Local party consensus chooses one owner; finalized owner may publish the host room.
2. Guests publish native summon signs through HTTP compatibility. Host searches exclude self, pending, joined and stale members. These are lifecycle fences, not obsolete matchmaking restrictions.
3. Host selects one native candidate and sends summon/request. The party stores a ticket-bound claim. Host placement is attached before sending; the guest sees the claim on summon/create.
4. NP signaling establishes the P2P route. This is not JoinRoom. Native vport40 then establishes its own channel and exchanges version (subtype0) and profile (subtype1).
5. Accepted native exchange permits Matching2 JoinRoom. Native session state6 precedes insertion completion; neither alone proves an actor is present.
6. Insertion task mode1/state6/6/not-leaving must match a resident cooperative actor and MemberId. PlayerGameData comes from that task's remote slot.
7. SosStatus must complete the original summon request. Its queued counter contributes to occupied capacity and also suppresses further selection. Native completion1877D00 matches user+character, unlinks/frees, decrements and preserves role-specific cooldown.

The single native request context (+88/+8c/+90), identity checks, loading/leave fences and broker pending/joined exclusion remain necessary. Removing the queue or accepting simultaneous native claims would mix replies. The previous remote-HP rejection was already removed in87a1186. The extra equality of queued selection role and resident role is not in native completion and is removed now; resident cooperative-role checks remain.

## Last run: evidence and limits

Authoritative stopped-run logs: parent out/coop-dev/runs/resident-slot-completion-20261103-review/final-pc, with party events in pc.
P1 invited P3 at22:21:47.854, claim delivered22:21:48.433. P3 exchange timed out22:21:54.643 before JoinRoom; ready=false/accepted=false. Host received guest version45/7 and profile22:21:49.658; guest had no corresponding exchange callbacks.
Packet sample comparison22:21:49–54.700: P1->P3 all13 sends match13 native reads by full-packet hash/size, P3->P1 all9 match9 reads. No transport loss/truncation is evidenced; native dispatch/initialization is the boundary. This does not prove the precise internal discard branch.
The20-second claim cleanup and host native request timeout then delay the next invitation until22:22:42.536 (about55seconds after first invitation). P2 joins22:22:46.088 and arrives22:22:59/23:00. Cleanup subsequently rejects role OR identity, indistinguishable in the old diagnostic; P3 never gets a second invitation before exit. No3-player success.

## Changes

- On first valid native version reception, queue our version/profile again via original exchange flags+88/+89. The peer having sent its own version demonstrates that its exchange exists. This repairs the asymmetric one-shot exchange case without extending deadlines or manufacturing acceptance.
- Use native ready+90 as duplicate fence; preserve all other fields. Original callback validates version and sets ready/accepted. Native update1477E05..1478087 constructs and sends the queued response. At most one reply per endpoint; no echo loop.
- Remove redundant role equality from resident request completion. Both account/character must still match; retain native completion/free/cooldown and all actor/insertion/host gates.
- Split user vs character mismatch diagnostics and record both identity pairs and roles, throttled5seconds, so an unresolved identity failure is no longer conflated with role.

The role mismatch itself is not established by old logs. These corrections are tested candidates, not proof that every live failure is eliminated. Initial exchange replay addresses the observed asymmetry; exact discard source and live second-guest result still need the fresh run. Native55-second unsuccessful-request lifetime is not blindly shortened.

## Validation

- tools/test_resident_summon_completion.py PASS: production policy with exact native1877D00 and queue gate; different selection/resident roles, native cooldown, all four slots, remote zeroHP, wrong identities, incomplete/departing tasks, unrelated requests retained.
- tools/test_negotiation_failure_trace.py PASS with clang++ and g++: production hook and full native1478130 callback at original RVA; first valid version queues response, original callback sets acceptance, duplicate cannot re-arm, foreign channel/subtype/version rejected. Corrected fixture return type to EAX width (upper RAX was unspecified in its synthetic send-failure snippet).
- DLL build/deployment/startup recorded in parent out/coop-dev/runs/admission-exchange-20261103/run.md. No game/save/settings changes, no native port/protocol/VPS changes. Gameplay pending.
