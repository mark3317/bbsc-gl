## Актуальное состояние — 13.11.2026

Опубликован BBSC-GL 1.5.10 (`v1.5.10`, `54699ed`) в составе BBGL 1.5.10.
Рабочая `develop` объединена с релизной историей, диагностические записи
сохранены. Сборка и публикация завершены; установка на устройства отдельно
не подтверждена. Коллизия после местного возрождения подтверждена для П1.
Бланк, общая гибель на двух/трёх клиентах и полное покрытие Pig Invasion
требуют игрового контроля. Разрыв по защите NETWORK остаётся открытым.
Подробности и источники: [HANDOFF](docs/HANDOFF.md), [BACKLOG](docs/BACKLOG.md),
[выпуск 1.5.10](docs/release-1.5.10.md). Старые статусы ниже исторические.

## Цикличные обработки — только с разрешения пользователя, 06.11.2026

Любые новые цикличные обработки в моде (периодические опросы, таймеры,
ticks, фоновые проверки и повторы), в том числе внутри существующего
обработчика, добавлять только после явного разрешения пользователя
на конкретный механизм. Общая просьба исправить баг или добавить функцию
не считается таким разрешением. Обоснованная невозможность штатного решения
тоже не заменяет разрешения. До согласования описать назначение, период,
объём работы и ожидаемую стоимость; сначала искать штатный событийный путь.
Такие обработки не должны ухудшать общую оптимизацию: оценивать суммарную
нагрузку, включая простой и рост числа игроков/объектов, и проверять влияние
на производительность. При обнаружении регрессии устранить её до принятия
изменения; одно разрешение на механизм не означает согласия на ухудшение.

## Штатные обработки и оптимизация — предпочтение пользователя от 06.11.2026

При любых изменениях и новых доработках сначала искать и пробовать использовать
или корректировать штатные обработки игры/порта: существующие условия, команды
и обработчики. Предпочитать снятие конкретной блокировки сохранению её с новой
параллельной реализацией. Новые hooks/ticks, опросы, обходы памяти, очереди,
сетевые сообщения и повторы добавлять только при обоснованной невозможности
решить задачу штатным путём; объяснять ограничение и дополнительную стоимость.
Сохранять исходные ожидания, анимации, завершение событий и границы авторитета.
Перед такими работами читать и по новым результатам обновлять
[память по оптимизации](docs/OPTIMIZATION.md).

> Подтверждение пользователя 05.11.2026: основной сюжет полностью пройден и проверен в кооперативе, переход в NG+ работает. Чаши работают совместно, штатная случайная генерация корневых чаш возвращена. Прежние общие статусы финала ниже исторические; редкие сценарии наград/обрядов/составов группы учитываются отдельно.

> Предметы и награды, актуализация05.11: [docs/REWARDS.md](docs/REWARDS.md).
> Текущие native пути, личные условия/квитанции, catch-up уникальных base/DLC
> наград и чаш при загрузке, отсутствие секундного опроса,107 глобальных лотов,
> NG+ и границы проверок собраны там. Последняя DLL установлена на ПК, P1/P2
> старт06:24:17 МСК; игровое подтверждение ещё открыто.

> Обновление 04.11: BBSC 7b464e0 / BBGL ec0ec22 собраны и установлены на ПК;
> прежние source-only статусы ниже исторические. Игровое подтверждение остаётся
> открытым. Актуальные подробности — docs/HANDOFF.md; правила перевода — AGENTS.md.

> Аудит 04.11: [отчёт](../../docs/fixes/2026-11-04-full-project-audit.md). Каталог тестов — docs/TEST-CATALOG.md
> родительского проекта. Не запускать общий discover: некоторые native scripts
> выполняются при импорте; VPS/Blender/ELF — ручные. Файлы unittest без main
> запускать через unittest. Исторические save/profile skip не считать PASS.
> Отдельный экспериментальный party/launch.py и его prepare-скрипт удалены;
> текущий запуск — run.py / scripts/local_party.py.

# Актуальное состояние — 04.11.2026

Основной кооп использует локальный Party внутри run.py, private-network discovery
и native UDP; отдельный VPS/shadNet/gameserver для этого пути не нужен.
Старые серверные инструкции ниже — история, не текущая схема запуска.
Имена игроков, повтор ожидания того же claim и квестовые guards добавлены в исходники;
их игровое подтверждение ещё требуется. Второй гость и выход хоста остаются открыты.
Overlap-admission эксперимент отменён, используется последовательный native admission.
Для обычного деплоя — BB_FAST_DEPLOY=1, delta изменённых компонентов, без повторного
verify-release/хэширования. Код, сборка, установка и игровой результат различаются.
Текущее состояние см. в HANDOFF и отчёте docs/fixes/2026-11-04-project-cleanup.md
родительского репозитория; исторические пути/версии ниже не применять автоматически.

# Актуальные правила — 03.11.2026

Единственный источник мода — этот подмодуль `bloodborne_pc/mods-src/BBSC`.
Перед работой читать AGENTS.md, docs/HANDOFF.md и docs/BACKLOG.md здесь,
а также ../../AGENTS.md и ../../docs/TESTING.md родительского репозитория.
Правки и сборку мода выполнять только здесь; текущие пользовательские изменения сохранить.
Основная установка: D:/Games/Bloodborne/Bloodborne Game Launcher.
Для эксперимента serverless-party разрешены отдельные тестовые установки на ПК и ноутбуке;
лёгкие сетевые клиенты проверяем на ПК. Исторические адреса и установки ниже
проверять перед использованием. Офлайн / Кооп остаются режимами запуска.

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
| `C:\Users\markn\CLionProjects\bloodborne_pc\mods-src\BBSC` | этот репо: мод BBSC |
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
- Интеграция с портом находится в `gpu/bbnet` репозитория BBGL. Патч для BBport 1.7.2 сохранился в истории BBSC-GL на коммите `4f11faf`.
- `docs/` — ARCHITECTURE, WORLD-SYNC, NETWORK, SESSION-LIFECYCLE, KNOWN-LIMITATIONS, TESTING, CHANGELOG. Читай нужный doc перед правками в соответствующей подсистеме.
- `tools/` — читалки игровых данных (gamedata, souls, find-fog-walls и т.д.). `build/*.txt` — выгрузки флагов/событий.

## Сборка
- Мод для bbport (основной путь): `emulator\mod\build-mod-bbport.cmd` → `build\mod\bbsc.dll`, `bbsc-launch.exe`, `mod.json`.
  Лог: `build\mod-build.log`, последняя строка `exit=N`. Нужны VS 2022 C++ + clang-cl и сабмодули
  `git submodule update --init emulator/externals/fmt emulator/externals/xbyak`.
- Эмулятор shadPS4 (редко нужен): `build/build-shadp2p.cmd`.
- После сборки мода — пакет лаунчера собирается в `bloodborne_pc` (`packaging/windows/build-coop-package.sh`,
  берёт `mods-src/BBSC/build/mod` по умолчанию), см. CLAUDE.md там.

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
