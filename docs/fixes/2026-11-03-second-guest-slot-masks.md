# Second guest remains unclaimed: 17:16 local-three run — 03.11.2026

## Captured behavior

Logs: parent `out/coop-dev/runs/second-guest-20261103-1716-review`.
Nine stable mod/game files, warnings0, plus three read-only copied party journals.
All three players successfully host and individual guests enter. No three-player
world was observed. Blank/end-search role release now works in this run.

P2 hosts at17:19:17; P3 joins at17:19:38. P1 signs are returned from17:19:35,
but no P1 claim occurs while P3 remains. P3 leaves at17:21:23; cooldown clears
at17:21:25.842; P1 is claimed at17:21:26.312 and joins at17:21:27.029.
P3 signs are again returned at17:22:06 while P1 remains, with no claim until
P1 leaves at17:22:39; P3 claim follows at17:22:41.5. The same exclusion repeats
with P3 hosting and P1 present while P2 waits. This places the observed block
before broker claim/native JoinRoom, rather than a failed second UDP join.

## Definite native defect and correction

Existing FIVE_HUNTERS edits relax only the first slot-dependent co-op mask,
0xFFF7FF7F, in the search and direct selection functions. Each function then
applies another slot-dependent AND0xFF1FFFFF. Bits21..23 remain excluded when
both vanilla co-op slot states are nonzero, despite the expanded member cap.

Added signature-checked Hunters wide edits at01873086 and018793B9, replacing
that second mask with0xFFFFFFFF. Both emulator and DLL use the shared patch
table. PvP masks, native ready gates, pending-state handling, role cooldown,
queued-request checks and live/member capacity are unchanged.

The historical logs do NOT capture slot states, the selected role bit or the
native ready mask. Therefore this is a reproduced selector defect, not proof
that it alone caused every live exclusion above. A change-only observer at the
existing selection hook now records both co-op/PvP slot states, slot-derived
mask, ready mask and native queued count while candidates are present. It
observes before the cooldown hook and does not modify any native state.

## Validation and status

`tools/test_coop_selection_masks.py`: PASS. Executes exact original native mask
blocks in executable scratch memory, with an ABI/frame bridge. Uses actual
production wide-edit entries and verifies expected bytes before patching.
Both paths,256 slot combinations each, baseline and previous partial patch
reproduce dropped bits; full correction preserves all co-op bits and every
non-co-op bit. This fixture does not simulate native slot population or world entry.

`tools/test_second_guest_cooldown.py` and `tools/test_matchmaking_native.py`: PASS.
Changed full game translation unit, BBSC_MOD syntax check: PASS.
Source corrected; no new product build/deployment/launch in this review.
Live second-guest confirmation remains pending. No saves/settings/journals
were edited; game binary was read only for disassembly. Unrelated changes kept.

Delivery update: DLL build0/native incremental0, six-file deployment0 with backup second-guest-masks-20261103-174410. Three-profile coordinator32512 launched17:44:10MSK; gameplay validation still pending. See parent out/coop-dev/runs/second-guest-masks-20261103.
