# Native block responsibility — 06.11.2026

User requested distributed block responsibility, native synchronization, shared
progress and protection from repeated enemies/rewards, then build/install/start
Player1 and Player2. This supersedes the former prohibition on retaining native
enemy history ONLY for the bounded, opaque native CHR block records described here.

Implementation:

- Native0190E750 serializes each loaded CHR block. A native-room-host metadata
  coordinator assigns one responsible participant per native block, preferring
  a participant whose own draw groups activate it; the incumbent remains stable
  while active. This is independent of the existing map flag/progress owner.
- Ordinary adjacent maps use the same canonical native block key, preventing
  two owners when players stand on opposite sides of a map border. Dungeon keys
  retain the complete world/channel/layout/ritual identity. New capability8 gates
  this protocol; legacy members retain the previous negotiated behavior.
- Metadata coordination runs on presence/offer reception too, without native
  memory calls: the room host can be loading another map or playing a movie.
- Handover revokes the incumbent, clears its awake NPC ownership words, and
  waits for its final native record/ack before granting the successor. An explicit
  native departure/unload also fences that authority; no heartbeat timeout elects
  a second simulator. World/visit/sequence/epoch and record size/count are checked.
- Only the responsible participant's native death bits enter shared history.
  Bits merge additively during a live map incarnation; unloading a streamed block
  does not clear them. Complete map departure/reload resets ordinary native lives;
  permanent boss/story state still comes from the existing flag/progress system.
- Native0190E8B0 applies history once per block/epoch/load, through the original
  historical-removal path, without Kill/AwardItemLot or reward replay. The table
  retains no HP, position, AI, inventory or actor pointers across clients. Its
  opaque native records travel with lease metadata on the existing control path.
- Native ownership, damage routing and native HP send/receive select the block's
  owner, including when a map follower owns a block or a map owner follows one.
  Outgoing native producer buffers stay unchanged; foreign/stale-source HP entries
  become native invalid-handle entries. Reliable native sequencing stays native.
- Established ordinary/chalice event admission uses certified native block records,
  rather than waiting for a distant map owner's full CHR footprint or player actor
  FirstSync. Shared flags remain mandatory. Joining admission and Hunter's Dream
  keep their existing native/host/catalog checks. Newly streamed, unadmitted blocks
  cannot get NPC authority; malformed inventory is not treated as an empty world.
- Added bounded per-load logs for block lease, admission and wait reasons.

Validation performed before build:

- Production coordinator + full block runtime on allocated fixture memory:
  disjoint footprints, border overlap, owner/follower native callbacks, revoke/
  final acknowledgement, deaths, unload/reload, stale/foreign packets, malformed
  inventory/counts, scope/ritual isolation, native HP filtering/retargeting and
  host-loading coordination PASS. Native serialize/apply calls alone are mocked.
- Production bootstrap PASS: block admission replaces map-wide NPC wait while
  preserving the shared flag gate and existing Dream/joining/travel boundaries.
- Native legacy initial-state/streaming, authority callbacks and trampoline PASS.
- Shared progress policy and original-data shared boss rewards/receipts PASS.
- Original 1.09 read-only serializer/handler ABI and new hook span checks PASS.

Gameplay remains OPEN. Required two-player check: Church of the Good Chalice /
Old Yharnam entrance separation, door/lamp operation, independent travel, kills
followed by reunion and role reversal; also ordinary map borders and separate
rituals. Passing fixtures does not establish live engine behavior or performance.
No real save/settings/game assets are modified by the tests. Build, installation
and launch evidence is recorded separately in the parent run directory.

Build/install: DLL build exit0; delta prepare/deploy exit0, five files installed
at01:48 MSK with the backup above. Player1/2 launch requested01:48:35. Gameplay
still OPEN; startup observation is in the parent run record.
