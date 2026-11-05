# Lecture Building: host-only native exit events

Source fixed; not built/deployed; gameplay confirmation OPEN.

Latest main-save run is `D:/Games/Bloodborne/twin/last_run.log`, starting
18:24 MSK on 4 November (initially empty while the running process buffered it).
Rotations `.1` and `.2` are older solo/Yahar'gul and Byrgenwerth runs, not this
reproduction. Laptop counterpart: `C:/Games/Bloodborne/test/last_run.log`.
Read-only SSH/scp collection uses the known laptop host key via Tailscale.
Raw laptop rotations and PC filtered timelines/provenance are in parent
`out/coop-dev/runs/lecture-doors-20261104`; no save contents were read.
Live file snapshots are not asserted final/atomic; laptop scp has no before/after
metadata check. Host/client clocks differ slightly; compare event order too.

## Recorded sequence

| Exit | Guest's premature native load completed | Host load completed + follow broadcast | Guest follow request | Guest second load completed |
|---|---|---|---|---|
| Frontier / 3302959 | 18:31:09.000 | 18:31:11.578 | 18:31:13.934 | 18:31:22.045 |
| Mensis / 2602959 | 18:32:16.678 | 18:32:18.753 | 18:32:21.104 | 18:32:29.737 |

At both premature completions the guest reports map `0x20000000` and
`RESPAWN-guest-changed` with the native destination point. Thus both native
door loads precede the mod's follow request and cause an extra load in this run.
Falling into the void is reported by the user; these logs do not capture its
visual appearance. Generic presence labels call m32_00 Byrgenwerth, so do not
exclude this run by looking only for the text "Lecture Building".

## Cause and change

The 2 November action-button guard only rejects a guest's own button press.
It cannot prevent the host's replicated ObjAct/event from running at the guest.
Read-only original m32_00 EMEVD confirms exactly four commands for each event:
13200310/13200311 wait on ObjAct13200124/13200123, play SFX932201 at
3202001/3202000, delay6s, call 2003[49] with2602959/3302959.

Before native event update, the two instances get network-sync byte+0x78=0,
the same field used by SetNetworkSyncState(false). Host/solo still execute
their original event locally. Joining4/guest6 skip the whole native update,
including initial condition, SFX, delay and warp, even if shared ObjAct was
already set. Loaded EMEVD bytes and flags are unchanged. Only the two event IDs
in packed map0x20000000 are affected; follow-host placement remains unchanged.

The existing event-pass trampoline at0x012ECDC0 is installed once by the
transition-door installer, independently of Dream/personal-NPC options, with
the new skip flag. Other NPC/pickup/gift pass behavior remains intact.

## Validation

- `tools/test_transition_door_authority.py` against original installed EMEVD:
  production event lookup and pass, both chains/all four stages, roles0..8,
  host network sync disabled, guest/joining paused, unrelated event/map/null,
  and single option-independent installation PASS.
- Existing `test_guest_transition_doors.py ../../out/exit-study.elf`: actual
  native button-rejection path for both doors and other roles/actions PASS.
- `test_hook_resume.py`: production trampoline function-entry skip/reset PASS.
- `test_follow_arrival.py`: existing follow/load arrival gating PASS.
- `test_native_kit_gift.py` with original game data: shared event-pass dependency PASS.
- Full production `bloodborne_re.cpp` MSVC-target `/Zs` check: exit0.

No DLL build/deploy, commit/pin/push, process termination, real save/settings or
on-disk game-data changes. Bloodborne.exe was still running at the process gate;
shared runtime files were not replaced. Parent/submodule pin remains0ddb1d4.

Gameplay criterion after installation: host uses each exit, guest stays in the
Lecture Building until the host's load finishes, then follows once and lands
normally. Guest cannot activate either exit itself.
