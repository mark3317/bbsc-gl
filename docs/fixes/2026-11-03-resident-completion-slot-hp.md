# Resident completion: arrival versus remote HP — 03.11.2026

Follow-up to the failed 18:08 local-three run. Code commit 87a1186.

The old completion policy demanded positive remote actor HP in addition to a
fully arrived 6/6 insertion task, cooperative role, actor MemberId equality and
queued account/character identity. Native summon-result completion is an
arrival transaction, not a health predicate: an already arrived guest may have
zero replicated HP or may have died before the next cleanup tick. A dead or
not-yet-updated replica must not keep the successful admission reserved.

Removed only the remote actor HP predicate. Host alive/loaded/own-world,
not-quitting, arrived/not-leaving task6/6, cooperator type and both member-id
and full queued role/user/character identity checks remain. No queue guard,
reservation, timer, or native destructor is bypassed. PlayerGameData is now
resolved by the insertion member's slot index in PlayerSlotManager+10, stride
6A0, the same remote table searched by native18777D00. Slots0..3 are bounded;
missing/foreign slot data cannot complete another request. This also removes
reliance on the actor's virtual getter as the authority for slot identity.

Added pending-reason logging at most once per five seconds per game thread.
It distinguishes host/world/task/actor/slot/identity/signature/native-retained
failure stages, without logging tokens or changing game state.

Validation: extended test_resident_summon_completion.py runs production policy
and exact native completion/unlink/free/backoff/selection gate. New arrived
zero-remote-HP case FAILS against the frozen pre-change policy, PASSES after
correction; unfinished zero-HP task still rejected. All four remote slot
indices work without the actor virtual getter; invalid index/missing table
rejected. Existing five-role, wrong account/character/member, host death,
loading, leaving, signature and unrelated pending-request cases pass. Full
BBSC_MOD translation unit syntax check exit0. Product build/deploy tracked below.

Limits: old logs did not record the rejecting guard or the remote actor HP.
Thus this is a reproduced policy defect, not proof that HP was the exact
rejecting guard in the 18:08 game. The slot path and pending-reason diagnostics
make any remaining failure inspectable. Three-player gameplay remains pending.

Delivery: DLL build0, five-file copy0; backup resident-slot-completion-20261103-20261103-221929. Three native PIDs31464/9340/10172 loaded DLL build22:18:18 at22:20:06/07MSK. Gameplay remains pending.
