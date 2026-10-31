# Current naming (2026-10-31)

BBGL = Bloodborne Game Launcher; GitHub: mark3317/bbgl. Mod: BBSC-GL, mark3317/bbsc-gl. Release folder: `Bloodborne Game Launcher`; profile: `%LOCALAPPDATA%\bbgl`. Source checkout folder names below remain local paths. Historical test paths refer to the installation at the time.

# BBSC (форк mark3317) — заметки для Claude

Цель проекта: довести кооператив Bloodborne (BBSC в Windows-порте bbport) до релизного состояния —
полное прохождение в коопе без вылетов/десинхронов/софтлоков, у гостей максимум возможностей хоста
(NPC, квесты, предметы, ключи, катсцены, награды, чаши), бесшовная сессия: 1 сессия = 1 подключение.

Общайся по-русски. Пользователь — Android/Kotlin-разработчик, Linux/macOS знает.

## Рабочие папки (mark-pc, Windows)
| Путь | Что |
|---|---|
| `C:\Users\markn\CLionProjects\BBSC` | этот репо: мод BBSC |
| `C:\Users\markn\CLionProjects\bloodborne_pc` | форк bbport (Windows-порт + Qt/QML-лаунчер), в его пакет кладётся наша сборка BBSC |
| `D:\Games\Bloodborne\bbport-coop` | установленный лаунчер, в котором реально играем на этом ПК |
| `D:\Games\Bloodborne\game` | файлы игры CUSA03173 v1.09 (только чтение!) |

Тестовые машины: этот ПК, ноутбук `local_pc` (192.168.88.233, Windows 10, ssh `markn`),
VPS `remote_server` (77.73.67.175, Ubuntu 24, ssh `root`) — там игровой сервер/shadNet.

## Git
- Remotes: `mark` = github.com/mark3317/bbsc-gl (наш форк, push сюда), `origin` = CLSAMG22/BBSC (апстрим, только fetch).
- Рабочая ветка: `mark/bbport-fixes`. Не пушить в `origin`, не делать force-push без явной просьбы.
- Стиль коммитов: `BBSC <область>: <что сделано>` (см. `git log`).

## Структура
- `emulator/src/core/bloodborne_re.cpp` — основная игровая логика кооператива (~19k строк; ищи grep'ом, не читай целиком).
- `emulator/mod/` — мод-DLL для bbport: `bbsc_mod.cpp`, `bbsc_hooks.cpp`, `bbsc_relay.cpp`, `bbsc_channel.cpp`, `bbsc_http.cpp`, `bbsc_launch.cpp`, `mod.json` (версия).
- `server/gameserver/bbsc_gameserver.py` — игровой сервер (Python 3, без зависимостей), `bbhost_service.py`.
- `bbport/bbport-1.7.2-bbsc.patch` — патч к bbport (relay, np_signaling, np_utility).
- `docs/` — ARCHITECTURE, WORLD-SYNC, NETWORK, SESSION-LIFECYCLE, KNOWN-LIMITATIONS, TESTING, CHANGELOG. Читай нужный doc перед правками в соответствующей подсистеме.
- `tools/` — читалки игровых данных (gamedata, souls, find-fog-walls и т.д.). `build/*.txt` — выгрузки флагов/событий.

## Сборка
- Мод для bbport (основной путь): `emulator\mod\build-mod-bbport.cmd` → `build\mod\bbsc.dll`, `bbsc-launch.exe`, `mod.json`.
  Лог: `build\mod-build.log`, последняя строка `exit=N`. Нужны VS 2022 C++ + clang-cl и сабмодули
  `git submodule update --init emulator/externals/fmt emulator/externals/xbyak`.
- Эмулятор shadPS4 (редко нужен): `build/build-shadp2p.cmd`.
- После сборки мода — пакет лаунчера собирается в `bloodborne_pc` (`packaging/windows/build-coop-package.sh`,
  берёт `../BBSC/build/mod` по умолчанию), см. CLAUDE.md там.

## Цикл разработки и теста (tools/coop-dev в bloodborne_pc)
`bloodborne_pc/tools/coop-dev/coopdev.sh` (из Linux-VM Claude, по ssh) + `coopdev.ps1` (Windows-сторона):
status · commit bbsc|port · build mod|port|package · job · deploy mod|launcher pc|laptop|all · deploy server ·
save list|snap|restore pc|laptop · test begin|collect. Логи прогонов: `bloodborne_pc/out/coop-dev/runs/<id>/{pc,laptop,vps}`.
Снимки сейвов: `<D:|C:>\Games\Bloodborne\coop-dev\saves\<имя>` (SPRJ0005 + BBSC own-world/bell-pending).
На ноуте: установка `C:\Games\Bloodborne\bbport-coop`, user_dir `C:\Games\Bloodborne\test`. На ПК user_dir `D:\Games\Bloodborne\ddd`.
Логи BBSC: `%LOCALAPPDATA%\bbport-coop\BBSC-0.0.1-BBport\bbsc\logs` (+ captures), лог игры `<user_dir>\last_run*.log`.
VPS: `/opt/bbsc/{gameserver,shadnet,logs,data,backups}`, сервисы `bbsc-gameserver`, `bbsc-shadnet` (пользователь bbsc).

Если Claude запущен прямо на mark-pc (Claude Code в приложении, Git Bash/PowerShell), а не в VM: `coopdev.sh` не подходит
(он ходит по ssh в `mark_pc`) — вызывать `coopdev.ps1 -Action ...` локально для ПК, а для ноута `scp` + `ssh local_pc` (см. `docs/HANDOFF.md` §1).
Анализ: `tools/eboot-disasm.sh` (дизассемблер eboot по адресу BBSC), `tools/gamedata/item_lots.py` (предметы, лоты, флаги, руны).

**Состояние работы и что дальше — `docs/HANDOFF.md` (читать первым), баги — `docs/BACKLOG.md`.**

## Правила
- Сейвы: только копии. Оригинальные сейвы пользователя не трогать.
- Перед заменой файлов в `D:\Games\Bloodborne\bbport-coop` или на ноуте — бэкап заменяемых файлов.
- Логи для отладки: BBSC `mods/CUSA03173/bbsc/logs/` (в shadPS4) / папка лаунчера bbport; эмулятор `user/log/`.
- Любая правка синхронизации мира: думай про хоста И гостя, про переподключение и про сохранение (без софтлоков).
