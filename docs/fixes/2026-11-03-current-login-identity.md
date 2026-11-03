# Current-login identity mismatch blocks second guest — 2026-11-03

Stopped22:43 run collected in parent out/coop-dev/runs/admission-exchange-2243-review/pc:9files,0warnings,stable copies. P1 hosts from22:46:06. P2 actor arrives22:46:23 but completion repeatedly logs resident user4215 vs request520383427; both role7 and character0x8000000000000000 match. Queue1/ready0/coop2/2 persists until P2 leaves22:46:57.395. P3 then arrives22:47:13: resident1704 vs request830650577, otherwise same. Leaving22:47:36.312 releases queue; P2 repeats. This establishes the user identity mismatch, not role mismatch. No simultaneous3 actors.

Native login01E87DF8 writes the authenticated user to local PlayerGameData+688. Native refresh01C43DE0 reads current ServerInfo[05540288]+60 but skips refresh when PlayerGameData+688 is already nonnegative. Loading a character with a positive legacy backend ID therefore leaves a stale replicated account, while HTTP summon uses the current login.

RefreshBbscLocalOnlineIdentity runs on the game thread after load-state observation and before party/bell/admission work. It copies only a positive current ServerInfo user to the owned local slot[0553B130]+8's+688 when different. It checks pointers/writeability and disabled/quit/title fences; no remote slots, character IDs, queues or acceptance flags are changed. It rechecks after replacement of the local character slot rather than caching the user ID alone. No direct save-file modifications. The prior native completion identity guards stay intact.

Targeted test tools/test_resident_summon_completion.py PASS: reproduce4215 vs520383427 with exact native completion, first remains blocked, refresh local identity then simulate its replication and exact native drain succeeds. Character ID/remote slot untouched by refresh; invalid current IDs, read-only data and quit are rejected; replacement local slot refreshes. Existing incomplete/departing/foreign-identity checks pass.

DLL-only build/deploy/startup recorded in parent out/coop-dev/runs/login-identity-20261103/run.md. No protocol/VPS changes. Live second-guest confirmation still pending.
