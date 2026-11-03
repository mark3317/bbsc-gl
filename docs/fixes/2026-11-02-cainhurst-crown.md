# Cainhurst crown reveal and personal crown pickup — 2026-11-02

## Cause

Read-only CUSA03173 1.09 m25_00_00_00 EMEVD inspection:
- Event 12500810 hides the throne-room parts, waits for player type 0, Logarius
  defeated, the local player in region 2502806 and attire 250000 equipped.
  It plays 25000010, then executes 82 geometry/object/collision/character/SFX
  changes. The existing relay replays RequestRemo only. A guest's event remains
  behind the host/equipment gate and never runs the world-effects tail.
- Event 12501803 begins with EndIfClient and ends on its event completion flag.
  After Logarius it creates action-button proxy 2500850, waits on action 2500030,
  then awards lot 2502000 (attire 250000, flag 52502000). The client never gets
  the prompt. Copying host completion also suppresses a personal pickup.

## Change

The game-thread reveal tick mirrors precisely the 82 native effects using the
same native helpers as the original event. It requires a co-op guest in m25_00,
finished loading, a usable actor/managers, no active/pending local crown movie,
a fresh host snapshot with 12500810 set and the same live flag. A request is
not a completion: native Remo start sequence is observed; an unstarted request
gets a 3-second grace before authoritative world repair. Late joins need no
movie packet. Each load applies once. Hosts, invaders and other maps are excluded.
No guest crown/equipment requirement is imposed on the host's world reveal.

The event-step hook replaces only the verified EndIfClient instruction of
12501803 with WaitFrames(0) in loaded EMEVD memory. Original prompt, action,
award and completion remain native. This no-op is valid for host and guest;
no role-dependent patch survives a return home and game files remain untouched.
12501803 is a personal map event and protected personal flag, so host completion
cannot remove the guest's crown prompt or produce a duplicate pickup. Its pickup
remains voluntary; the existing item ledger handles guest award persistence.
NPC quests and the later queen's separate pickup event remain unchanged.

## Validation / limits

Both standalone and bundled source trees updated. tools/test_cainhurst_reveal.py
PASS: extracted production lifecycle and native-helper call fixture; all 82
side effects match the installed game's original EMEVD tail; host flag / local
movie / queue / loading / late join / stale snapshot / role / map guards; one
application per generation; personal pickup flag masks; exact gate replacement
and negative inputs. Native helper signatures inspected in read-only disassembly.
This fixture stubs helper execution; actual rendering, collision traversal,
proxy interaction and saved crown still need a live game test.
No DLL/package build, deployment, game launch, save or game-file changes.

Suggested live test: each guest picks up its own crown after Logarius, the host
wears theirs and reveals the room; after local scenes everyone walks through to
the throne room. A late guest sees the open room; already taken crowns do not
repeat after reload/rejoin, while an untaken guest crown remains available.
