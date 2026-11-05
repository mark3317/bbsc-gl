# Independent travel — development branch, 05.11.2026

Branch (parent and BBSC): `codex/independent-world-travel`, based on BBSC `bdd59b7`.
User authorized implementation and a two-profile launch on this PC. This is an
incremental implementation, NOT a completed independent-travel feature.

## Agreed behavior

- Party membership survives individual lamp travel between regions.
- A guest remains in the host's world when visiting the Dream: the guest sees
  and travels through the host's chalices. Returning to the personal world shows
  that player's own altars. Personal chalices are never overwritten.
- A host travelling elsewhere leaves the remaining players where they are.
  Host game exit/crash still ends the native session; host migration is separate.
- Personal loot/reward rules and native root-chalice generation stay in place.

## Source comparison

Yharnam Together `c1288b523aa7b4b07c348288b56a54a9627ae727` and the source asset
attached to CLSAMG22/BBSC v1.0.0 (`SOURCE-COMMIT.txt`:
`e995c21f6131b154dbeee3e756421ca55dfce2bf`) have identical travel, join, enemy HP,
altar, and packet-route implementations in the files inspected. The tag's Git
tree (`4f11faf`) is the old follow-host architecture; use the release SOURCE asset.
Credit: CLS_AMG and the Yharnam Together contributors, GPL-2.0-or-later.

Their native session is kept across loads; remote insert tasks are reconstructed
on meeting. Their server selects an enemy owner per map and routes native game
channels. Their team altars replicate rituals to teammates, which is incompatible
with the agreed personal-altar model and must NOT be copied unchanged.

## Implemented first integration gate

- `bbsc_world_presence.h`: fixed-size/versioned presence wire format, room/world
  scope, finite-position validation, loading/playing/leaving states, monotonic
  visit/sequence fences, border hysteresis, freshness and five-player bounds.
- Deterministic coordinator-side owner selection, retaining a present owner when
  the host returns. This rule is NOT wired to native AI yet.
- Native channel-policy rules scoped by world/place, with dungeon identity AND
  ritual incarnation. They are NOT attached to native send/receive yet.
- `bbsc_world_altars.h`: whole-catalog guest view, host-only updates, monotonic
  ritual/revision fences and FormData validation. Pure model only: no live altar
  replacement, serialization, native menu wiring or persistent writes yet.
- Runtime game-tick publication through existing SHAD/P2P transport, packet ID
  `0x32`, and receive dispatch behind the existing session envelope. Readers only
  update metadata. Confirmed departures remove the corresponding observations.
- The live bridge advertises ONLY presence capability. It does NOT suppress
  follow, open guest lamps, route game packets or transfer enemy authority.

Tests execute the production header rules, actual tick/receiver functions and
actual shared relay dispatcher. They cover malformed/replayed/foreign packets,
load/border visits, room changes, capability gating, ownership selection, dungeon
isolation, atomic altar replacement and preservation of a separate personal view.
They do not demonstrate working native travel, native AI handover or live altars.

## Remaining implementation

1. Native packet boundary hooks and map-owner state/HP/hit/AI hooks adapted to
   direct P2P. Preserve reliable sequencing; never filter raw reliable datagrams.
2. Host-ordered map changes beyond the host's currently loaded map, plus safe
   state transfer when the owner leaves/loads. Test damaged enemy takeover.
3. Guest travel and native insert-task reconstruction, then capability-gated
   replacement of normal follow. Keep initial admission and explicit leave separate.
4. Full host altar catalog including per-slot ritual incarnation, native/random
   FormData and unlocked lamps. Load a chosen host dungeon while the host is
   elsewhere; never rely only on the latest currently mounted host dungeon.
5. World-scoped guest altar UI and command handling, preserving personal altar
   flags/cache/save snapshots. Removing an occupied ritual needs a defined safe path.
6. Presence-aware death, spectating, scaling, encounters, cutscenes, Dream ending
   and NG+. Preserve current personal rewards and catch-up semantics.
7. Native fixtures for real hooks, then two/three-player game confirmation of
   separate fights, reunion, owner handover, chalices and host departure.

The archived personal-Dream patch is not applied. No new gameplay switch is
exposed while the required native mechanisms are incomplete.

## Validation / deployment

First gate: `tools/test_world_presence.py`, `tools/test_world_presence_bridge.py`,
`tools/test_relay_dispatch.py`, `tools/test_session_register.py` PASS.
Build, isolated two-profile startup and gameplay statuses are recorded separately
in the parent run record; no successful fixture closes the feature.
