# Guest appearance after summoning — 04.11.2026

User: retain the client's summon animation/effects in their own world; remove
the persistent blue summon glow in the host world.

Read-only inspection of original CUSA03173 PARAM/PARAMDEF data identifies:

- SpEffect 9006: stateInfo 272, maxHpRate 0.7.
- SpEffectVfx 272: midstSfxId 211, midstDmyId 203, init/finishSfxId -1.
- Bell/search VFX 188/189 use 301/300; transition row 270 uses 370/371/372.

The co-op game tick prepares only the active repository's SP_EFFECT_VFX_PARAM_ST
row 272, changing its looping SFX from 211 to -1. It validates the expected
loop/attachment/start/finish signature, refuses custom rows and rechecks the
repository once per second for replaced tables after loading. The change applies
on all updated peers, including the host's view of remote clients. The unrelated
home bell/search and transition rows remain native; no character type, SpEffect
9006, HP, team, session, animation or save changes. Original game files untouched.
SHADPS4_BBSC_KEEP_GUEST_AURA=1 retains the native persistent aura at process start.

Validation: tools/test_guest_appearance.py compiles/runs the production functions
against isolated rows; checks exact remaining bytes, unsupported rows, absent
repository/retry, replaced table and opt-out. PASS. Full bloodborne_re.cpp
BBSC_MOD syntax check with clang++ also PASS (exit0). Native rendering is not
exercised by this fixture: visual confirmation of disappearance and preserved
home transition remains OPEN. Source only; no DLL build, deployment or game run.
