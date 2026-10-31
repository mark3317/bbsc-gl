# BBSC-GL — Bloodborne Seamless Co-op Game Launcher

**English** · [Русский](README.ru.md) · [Download BBGL](https://github.com/mark3317/bbgl/releases/latest)

BBSC-GL is mark3317's fork of [Bloodborne Seamless Co-op (BBSC)](https://github.com/CLSAMG22/BBSC), integrated into **[Bloodborne Game Launcher (BBGL)](https://github.com/mark3317/bbgl)**. Players should download BBGL: it includes the matching mod, launcher and hosting server. No separate mod download is needed.

## Why this fork exists

Original BBSC already provides persistent co-op, guest items, shared progress, scaling and up to five hunters. These are upstream features, not inventions of this fork. BBSC-GL concentrates on a complete playthrough in the Windows port: guests should interact with the world, keep personal quest rewards and return to their own world after playing with friends.

The goal is one connection for a play session, including area changes, deaths and chalices. This is a development goal, not a claim that every scenario is finished. Host migration is not implemented.

## Architecture and differences

| Area | Original BBSC baseline | BBSC-GL approach |
|---|---|---|
| Distribution | Separate Play, Server, Nucleus and BBport packages | Matching client and server built from a pinned submodule and shipped in BBGL; updates follow the BBGL release |
| Runtime | shadPS4 fork with an additional BBport mod target | BBport DLL and injector are the primary integration target; emulator sources remain the basis of the mod |
| Guest world | Upstream world synchronization and optional shared progress | Extended own-world snapshots, per-save-slot item/progress journals and restoration; personal NPC quest/reward handling and own Hunter's Dream |
| Session recovery | Upstream persistent session machinery | Additional death, reload, spectator, rejoin and chalice-follow fixes; latest key-item regrant fix retries after reload |
| Storage | Standalone emulator / mod directories | BBGL keeps binaries in the installation and writable state in `%LOCALAPPDATA%\bbgl`; `BBSC_DATA_DIR` redirects mod data, while standalone fallback remains |
| Networking | shadNet / native game networking and BBSC messages | Retains those layers and the game-server relay, with fork fixes in the port and server; this is not a replacement combat protocol |

World snapshots and journals separate the host's temporary world from the guest's own progression. Shared Progress merges eligible progress on return; chalice world flags are excluded from that merge. Server relay messages supplement the native game network rather than replacing all game traffic. See [architecture](docs/study/ARCHITECTURE-OVERVIEW.md) and [world synchronization](docs/study/bbsc-world-sync.md).

The inherited `bbsc.dll`, `bbsc-launch.exe`, `BBSC_*` environment variables and protocol identifiers remain for compatibility. The product and repository name is **BBSC-GL / bbsc-gl**.

## Current status

Experimental. Basic chalice play and the two T21 entry fixes were confirmed by the player. Chalice combat latency, uncommon death/disconnect recovery, distinct dungeon identities and three-player coverage remain open checks. T24 spectator recovery and T25 key-item retry changes have build/code checks, but do not imply completed gameplay validation. [Backlog and evidence](docs/BACKLOG.md).

## Build and source

- BBport mod: `emulator\mod\build-mod-bbport.cmd` → `build/mod/`.
- Game server: `server/gameserver/bbsc_gameserver.py`.
- Reproducible player package: [BBGL build guide](https://github.com/mark3317/bbgl/blob/main/BUILDING.md).
- Original emulator, standalone packages and upstream usage: [BBSC](https://github.com/CLSAMG22/BBSC#readme).

## Credits and licence

BBSC by **CLS_AMG**, with contributions and foundations from **Wozzardman / shadp2p**, **fhody125 / No Dream For The Hunter**, **shadPS4**, **shadNet**, the Hunter's Dream team and the original BBport developers. See [original credits](https://github.com/CLSAMG22/BBSC#credits), [CREDITS.txt](CREDITS.txt), [NOTICE.md](NOTICE.md) and [SUPPORTERS.txt](SUPPORTERS.txt).

GPL-2.0-or-later; see [LICENSE](LICENSE). Third-party components retain their licences. Bloodborne is owned by FromSoftware and Sony Interactive Entertainment. This independent fork is not an official upstream BBSC release.
