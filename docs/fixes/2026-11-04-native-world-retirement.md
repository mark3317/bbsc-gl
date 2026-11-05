# Automatic world retirement — 04.11.2026

Status: SOURCE ONLY. No product build, deployment, game launch/termination or real
save/settings/live-journal edits. Existing unrelated working changes retained;
BBSC HEAD and parent gitlink remain0ddb1d4. Gameplay remains OPEN.

User requirements: release host ownership when every client has disappeared from
its native session and Beckoning is inactive; also release when the host crashes
or the bound host profile loses its native hosting role.

Implementation and evidence are specified in party/PROTOCOL.md, section
Native-confirmed world retirement. Native observations carry role, member count,
load/alive/bell and frame freshness in one atomic64-bit snapshot. The maintenance
worker cannot refresh a stalled game frame into apparent readiness. Counts are
native session membership, never the briefly absent remote actors during reload.

An observed host retires with native members1 and bell off, or after loss of its
host role with native0/2/5. Both require a fresh ready/alive world. A guest retires
a crashed-host binding only after confirmed native teardown AND6s without a host
control heartbeat. Thus a live host's ordinary guest leave does not destroy its
other guests. Lost control alone does not release a still-live native session.
A cold guest restart still requires an observed native participation before local
host-loss retirement; this patch does not infer such proof from an old journal.

Static retirement uses durable authenticated terminal certificates, including
partial-commit supersession and stale generation/room fencing. Full roster votes
still apply to the next static acquisition; this change releases ownership, not
static roster membership. Dynamic retirement detaches/fences the exact guest
reservation or closes the host snapshot and any staged admission. No host migration.
Bundler includes the new shared retirement.py module.

Checks (isolated temporary profiles/journals; no real saves):
- Five new static real-process/native HTTP cases PASS: crashed guest + empty host,
  host role loss with residual bell, native population/load/death/freshness guards,
  host crash + native exit + restart, ordinary leave with a remaining healthy guest.
- Partial commit + crashed voter retirement and replayed prepare/commit/final PASS.
- Two dynamic real-process/native HTTP cases PASS: host-empty closure/detachment,
  host crash retirement followed by independent local acquire.
- Two dynamic scope/reservation cases PASS: old native scope cannot release the
  new world, delayed view/reserve cannot revive a retired attachment.
- Four direct Party dependencies PASS: explicit guest-ack close, partition restore,
  closed-room recreation/late leave, real HTTP/NP late-join host rotation.
- Production C++ population/JSON/freshness fixture and tick-observation gate PASS.
- Deferred native item/mailbox and current menu-exit/native title gate fixture PASS.
- Complete BBSC_MOD syntax for bloodborne_re.cpp and bbsc_party.cpp PASS (MSVC
  environment with clang /Zs /EHsc; no binaries built).
- Legacy tools/test_party_menu_barrier.py wrapper FAILS before running assertions:
  duplicate BbscMod stubs already present in test_menu_quit.py. Unchanged wrapper;
  ran current test_menu_quit.py directly, which includes the final Party gate: PASS.

No commit/pin/push. Updating the running installation is not part of this source
change. A later coordinated DLL + Party deployment and game test must validate
actual native member counts, automatic bell availability and host-crash recovery.
