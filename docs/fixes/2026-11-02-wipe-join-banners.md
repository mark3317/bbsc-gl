# Boss-wipe join banners on guests — 2026-11-02

Diagnosis only; no production changes, build or deployment.

Evidence: bloodborne_pc/out/coop-dev/runs/review-20261102-boss-notice/pc
(all three mod/timeline logs, unchanged during collection). Game logs and server
journal for the same run are in review-20261102-2300. DLL build 22:40:21;
Player 1 host, Players 2/3 guests, map 0x18010000.

Host kept-death begins 22:58:20.702, local binding restores 22:58:28.920,
then two remote insert tasks restart at FirstSyncWait. Guests follow the host's
wipe at 22:58:29.086/.127, request full reload 22:58:31.097/.146,
restore local member binding 22:58:35.398/.409 and restart two remote tasks each.
All three actors are present on guests at 22:58:36.447/.425; guests report alive
at 22:58:38.034/.155. Host remains state 3 and guests state 6 through recovery.
Player 2 begins menu quit at 22:59:00 (native save-completed marker); this is
separate from the preceding wipe. One wipe is observed; not a repeated-wipe closure.

Code: bundled emulator/src/core/bloodborne_re.cpp, TickBbscReinsertV8 calls
ArmBbscRejoinLines(GetSessionState() == 6, ..., 15000) before restarting tasks.
TickBbscRejoinLines changes only RoleGuestLine (+0x30) for guests, whereas native
remote character creation at 0x0196BA20 uses RoleHostLine (+0x34, joinName).
The latter is a member-arrival producer even when the local machine is a guest:
a guest has both the host and the other guest to recreate. Thus the role-based
choice leaves member-arrival join banners unchanged on guests during recovery.
Logs explicitly show only guest-column override at 22:58:35.398/.409, versus
host-column override on the host at 22:58:28.920. Original +0x34 role values
include 0x18e71 (102001), localized as player joining the game.

This explains a repeated join announcement without a new session connection.
Resolved banner text and producer calls are not logged, so exact displayed names,
message ids and draw times remain inferred from code plus the user's observation.
The current banner filter only hides empty/silent/ActionEventInfo text; it does
not deduplicate real-looking joins for existing session members.

Future correction should distinguish recreation of existing members from actual
new arrivals, covering both banner producers on host and guests. A global quiet
timer or blanket suppression risks hiding a genuine join during recovery.