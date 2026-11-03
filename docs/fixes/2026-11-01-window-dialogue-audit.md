# Window dialogue lost after guest menu exit — audit 01.11.2026

Read-only investigation; game saves, mod code and installations not changed.
Laptop run: bbsc-mod-20261101-052157-17016.log.

## Evidence

05:27:45.517: guest talk sets 72410501=1. 05:28:35.101: native save
succeeds before Stop; 05:28:35.793: menu exit released after disconnect.
05:28:44.080: early home load applies 12 talk flags. At 05:28:59 the
late home phase finishes without another talk-journal application.
Second trip begins at 05:30:15. Own-world snapshot own-sd1-0.bin.restored
created then contains 72410500/501/502/503 all false. At 05:30:56, after
second exit, only 11 talk flags are restored. Last applied journal contains
72410515/516=0, no 72410501; the single .applied archive replaced the earlier
one. Logs prove the first conversation set the flag, and the later own-world
baseline lacks it, but do not capture the exact native write that removed it.

Original ESD t241319 in m24_01_00_00.talkesdbnd.dcx uses 72410500 for
first greeting and 72410501 for the next general greeting (talk 2900100).
It initializes 72410515/516 and temporary talking flag 70000140; those
initialization writes are not proof of completed dialogue. Logged talk-step
IDs do not reliably equal the binder filename; identify by flag and ESD.

## Mechanism audit

Native save-before-disconnect succeeds, but it precedes home-world restoration.
BBSC separately keeps own-world snapshots, host map snapshots, filtered shared
kind-1 progress, taken-item records/item ledger, and last-value dialogue flags.
KeepBbscGuestTalkBits protects current trip talk bits against host snapshot
application. Personal NPC cache is cleared after session end. Own-world
restoration replaces groups then consumes its snapshot. Shared Progress
collects kind-1 groups and excludes personal NPC flags, so it is not a direct
source for host dialogue flag 72410501. Dialogue flags are reapplied after
own-world restoration, separately from the native save that just succeeded.

ApplyBbscTalkJournal early phase sets bbsc_talk_journal_written=true. Late
phase skips every flag when that boolean is true, clears the map on finish,
and the caller retires the disk journal as .applied. Neither step verifies
the final flag table or persistence in a subsequent own-world native save.
The mark is even set before checking manager availability. A narrow fixture
executing the production function reproduced: early apply=1, simulated later
table replacement=0, late finish leaves 0 and destroys recovery journal.
This proves a recovery gap, not the identity of the native overwriter.

Items are a separate mechanism: 05:28:59 K2-trip-home confirms one item kind;
05:30:17 K2-lost-at-load detects 0x400010d8 (4312) lost on a new guest load
and restores it. This is automatic repair, not evidence that native inventory
persistence is completely clean. No reason to equate it with dialogue flags.

## Safe fix requirements (not implemented in this audit)

Keep the personal journal until verified final home state and native save;
distinguish persistent conversation/quest state from one-shot gift triggers.
Capture legitimate home-side changes/consumption before reconciliation so
retrying recovery cannot rearm gifts. Retry on unavailable managers rather
than marking applied/clearing before a successful write. Add a focused fixture
for late table replacement, manager unavailable, restart and gift consumption.
Do not solve by repeatedly OR-ing all flags or pinning every talk flag to 1.
The precise native replacement/save-snapshot boundary still needs a targeted
observation; existing log counts alone cannot certify all dialogue state.
