# Native own-sign refresh every 2 seconds

The 22:50–22:59 MSK run is preserved in bloodborne_pc/out/coop-dev/runs/
review-20261102-2300. See run-review-2250 for the synchronized timeline.

## Confirmed defect and native path

The DLL sets ServerInfo+89C / own-SOS manager+190 to 2 and disables the port's
blocking fast-sign worker. Nevertheless the game's create requests in this run
are 30 seconds apart. These interval writes alone do not queue a fresh own-sign
publication. Player 2 receives the first HTTP claim after its native signaling
task has already been canceled. Player 3 receives its claim ~5.3 seconds after
the first aimed placement; its first attempt also fails. Both eventually join,
with only ~6.5 seconds from guest state to map-load completion.

Static CUSA03173 1.09 control flow (BBSC/build/runtime-mode-eboot.elf):

- 014B9180 owns the sign records at [FrpgNetMan+C50]+158 (circular list,
  node+10 points to a sign record).
- Updating an existing own sign at 014B9246 writes byte sign+A0 = 1.
- 014B6312/631D checks an existing publication at sign+A8 and this dirty byte.
  With an existing publication and A0 = 0 it skips to the next record.
- 014B632A clears A0 before the usual native create submission, which calls
  01E90E30 at 014B6B8C. Its HTTP reply is processed by the game itself.
- Own-SOS lifetime +194 / entry+E8 is distinct from this dirty flag and is kept.

## Change

On the game tick, mark the existing native own-sign records dirty after two
seconds without a private-server create. No second HTTP consumer, fabricated
claim, replayed response, signaling override or forced session state is added.
The normal native request and its real broker reply perform the join.

Only an idle player in its own loaded world with a Small Resonant/Sinister
sign effect is eligible. Private-server create dispatch arms the mechanism.
Wait for EOF/destruction of every in-flight native create; pause after a
delivered claim until its existing join/expiry handling finishes. Host, joining,
joined, leaving, loading, canceled bell and public-server paths do not refresh.
Validate the whole circular list (maximum 34 records) before any dirty write;
only byte +A0 changes. Existing role counts, sign data, lifetime and retry
deadlines are preserved. State/pointer checks are limited to four per second
when no publication is possible; normal refresh is once every two seconds.

Additional signature-checked observers at C8DD60 and CD89C0 record cancellation
caller/parent and original signaling phase before task-13 cleanup. The generic
handle observer filters virtual +38 == CD89C0 to avoid unrelated cancel noise.
This is diagnostic only and does not suppress cancellation or alter its result.

## Validation and limits

- test_sign_refresh.py: baseline lacks the refresh path; production-function
  fixture passes the 1999/2000 ms boundary, subsequent cadence, overlapping HTTP
  lifetimes, claim pause/release, all native own signs, role/world/loading/bell
  guards, corrupt/cyclic lists and exact preservation of non-dirty bytes.
- test_matchmaking_native.py passes interval/role-backoff checks. Its fixture
  now supplies the localization helper required by existing production code.
- test_hook_resume.py passes the production trampoline, including the exact
  six-byte PUSH RBP / MOV RBP,RSP / PUSH R15 entry used by both new observers.

The missing native refresh is reproduced and corrected. Causality for the
first cancellation remains an inference from late claim versus close ordering;
the prior logs only observe teardown and cannot identify its initiating caller.
Do not claim all first-join failures fixed without a fresh game run. The added
origin observer will distinguish a remaining cancellation from delayed claims.

No server or protocol change; no VPS update required. No saves/settings/game
files changed. Build, deployment and live validation are recorded separately.
