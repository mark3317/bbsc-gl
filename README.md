# BBSC-GL — Bloodborne Seamless Co-op Game Launcher

**English** · [Русский](README.ru.md) · [Download BBGL 1.3.2](https://github.com/mark3317/bbgl/releases/tag/v1.3.2)

BBSC-GL is a fork of [Bloodborne Seamless Co-op](https://github.com/CLSAMG22/BBSC), integrated into [BBGL](https://github.com/mark3317/bbgl). Download BBGL for matching DLL and P2P runtime versions. Latest release [**BBSC-GL 1.3.2**](https://github.com/mark3317/bbsc-gl/releases/tag/v1.3.2).

Hunters can travel independently within a party, use their own Dream and meet again on another map. The host’s Chalice lamp list and progress are synchronized with guests.

**The full main story has been tested as a co-op playthrough through the finale, including the transition to NG+. Chalice dungeons work in co-op, with native random generation restored for Root Chalices.** Guests explore the host's generated layout while retaining their own altars and individual progress; they do not need to create a matching dungeon first.

## Co-op and architecture

Original BBSC supplies persistent sessions, guest items, shared progress, scaling and up to five hunters. This fork extends it with personal NPC quests, keys and rewards, an own Hunter's Dream and independent chalice progress during group exploration.

The current launch path uses Party inside `run.py`, LAN/VPN discovery and native UDP. No separate VPS, shadNet server or invite code is required. Players can join after others have started; admission is sequential. Everyone must use the same BBGL version. Host migration is not implemented.

Enemy loot and reviewed scripted/boss rewards use native game delivery with personal conditions. Host inventory is not copied. Missing unique base-game, DLC and chalice rewards are checked after loading; personal receipts cover one-time loot and NG+. See [reward policy and open checks](docs/REWARDS.md).

Binaries live in `coop/client/bbsc`, Party in `coop/party`, and writable data defaults to `%LOCALAPPDATA%\Bloodborne Game Launcher` (`profile/coop` for mod state). `BBSC_DATA_DIR` can redirect it. Internal binary names and `BBSC_*` variables remain for compatibility. Native networking remains the game's transport, supplemented by BBSC messages.

## Status and build

The user confirmed a complete main-story co-op playthrough and a working NG+ transition on 5 November. Chalice co-op and randomly generated Root Chalices are supported. This does not establish coverage of every additional rite, reward edge case or party composition; those checks continue. T22 combat latency, T23 return and T24 wipe camera were confirmed on 1 November. See [HANDOFF](docs/HANDOFF.md) and [BACKLOG](docs/BACKLOG.md).

- DLL: `emulator\mod\build-mod-bbport.cmd` → `build/mod/`.
- Player package: [BBGL build guide](https://github.com/mark3317/bbgl/blob/develop/BUILDING.md).
- Standalone/server instructions and older changelog entries are historical.

## Credits and licence

BBSC by **CLS_AMG**, with contributions and foundations from **Wozzardman / shadp2p**, **fhody125 / No Dream For The Hunter**, **shadPS4**, **shadNet**, the Hunter's Dream team and the original BBport developers. See [original credits](https://github.com/CLSAMG22/BBSC#credits), [CREDITS.txt](CREDITS.txt), [NOTICE.md](NOTICE.md) and [SUPPORTERS.txt](SUPPORTERS.txt).

GPL-2.0-or-later; see [LICENSE](LICENSE). Third-party components retain their licences. Bloodborne is owned by FromSoftware and Sony Interactive Entertainment. This independent fork is not an official upstream BBSC release.
