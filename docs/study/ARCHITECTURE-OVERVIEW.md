# ARCHITECTURE-OVERVIEW — BBSC-GL + Bloodborne Game Launcher (BBGL)

Текущая поставка: BBGL включает закреплённые бинарные файлы BBSC-GL и сервера. Профиль: `%LOCALAPPDATA%\bbgl`; бинарные файлы не копируются в профиль. Приведённые ниже старые пути и механизм загрузки пакетов описывают исследованную раскладку 29.10, до перехода на единую поставку. Имена DLL и протокола BBSC сохранены.

Сводка по файлам областей (2026-10-29). Детали: `game-internals.md` (GI), `bbsc-world-sync.md` (WS), `bbsc-session-network.md` (SN),
`bbport-engine.md` (PE), `launcher.md` (LA), `history.md` (HI). Цель — CUSA03173 v1.09.

## 1. Компоненты
```
 Лаунчер (Python+QML, bloodborne_pc/launcher)
   ├─ хост: shadnet.exe + BBSC-GameServer.exe (Python→exe)   ← или VPS 77.73.67.175 (/opt/bbsc)
   └─ запуск: bbsc-launch.exe ──(suspended + LoadLibraryW)──▶ bb-probe.exe (порт) + bbsc.dll (мод)
                                                                 │             │
                                               patches.bin, engine hooks       ├─ bbsc_patch_tables.h (57 патчей)
                                               bbnet (shadPS4 net/np, в форке) ├─ bloodborne_re.cpp (~19k строк, 168 хуков, ~70 тиков)
                                                                               └─ bbsc_relay/channel/http (сеть мода)
```
| Компонент | Репо / путь | Роль |
|---|---|---|
| Лаунчер | `bloodborne_pc/launcher/bbport_coop.py`, `bbport_launcher_backend.py` | пакеты BBSC + override, Tailscale/файрвол, invite, аккаунты, env, бэкап сейвов |
| Порт | `bloodborne_pc/src/probe.c`, `engine_hooks.c`, `gpu/bbnet/vendor/shadps4` | загрузка ELF, свои патчи (хеш-проверка), сеть PSN-эмуляции (signaling/matching2 с правками BBSC) |
| Мод | `BBSC/emulator/mod/*.cpp` + `emulator/src/core/bloodborne_re.cpp` (`BBSC_MOD`) | поиск образа, патчи, трамплины, вся логика коопа |
| Сервер | `BBSC/server/gameserver/bbsc_gameserver.py`, `bbhost_service.py`; shadnet | вход/знаки/призыв (ss4.scej-network.jp подменяется), relay BBSC-пакетов (TCP), shadNet-аккаунты |

## 2. Запуск коопа (LA, PE)
1. Лаунчер: при необходимости ставит/обновляет BBSC → накладывает свою сборку (`coop\bbsc\`, если версия совпадает).
2. Хост поднимает shadnet + gameserver; invite = `BBCOOP-` + base64(адрес, ключ регистрации).
3. Логин/регистрация в shadNet → бэкап сейвов в `<user_dir>\coop-backups` → `host_overrides.json` → env (`BB_COOP=1`, `BBSC_RELAY`, `BBSC_SAVE_DIR`, `BB_SHADNET_*`).
4. `bbsc-launch.exe` стартует `bb-probe.exe` приостановленным, грузит `bbsc.dll`, отпускает. Порт держит код RWX (`BB_COOP=1`).
5. Мод ждёт образ, проверяет все сайты, пишет патчи, ставит хуки, подключается к relay `BBSC_RELAY`.

## 3. Сессия (SN)
- Состояния `[0x05540290]+0x124`: 3 хост, 4 входит, 6 гость/инвейдер. Знаки/призыв — ванильная механика через gameserver; BBSC-патчи
  (группы Stage/Revive/Tasks/HostDead/…) не дают игре закрыть сессию при загрузках, смертях, боссах.
- Хост каждые 0.5 с шлёт позицию/карту/лампу; гость в другой карте делает follow-загрузку (≤3 попытки, ждёт флаги ≤4 с).
- Смерть: спектатор при живом партнёре/боссе, вайп → перезагрузка у лампы хоста. Выход в меню снимает патчи на 20 с; «партнёр пропал» — 180 с.

## 4. Потоки данных хост → гость (WS)
| Поток | Частота | Применение у гостя |
|---|---|---|
| Флаги блоков карт kind 1/6/7 (+5 для сравнения), все области кроме Сна и чаш | 1 с текущий + 1–4 блока/с | при загрузке, до событий карты; свои NPC-квесты, подарки и журнал — поверх |
| Сон охотника (57 групп) | 1 с, только когда хост в Сне | при загрузке в Сон; магазины и мессенджеры — свои; восстановление при выходе |
| Боссы/прогресс + время ночи (0x26) | 5 с | время — сразу; боссы — копятся для Shared Progress |
| Ключи и жетоны (0x29) | 3 с | сразу в инвентарь |
| Катсцены (0x28), босс-бар, scale, PvP, life | по событию / 0.5 с | повтор запроса / UI / баланс |

Транспорт: мод → TCP relay gameserver (конверт `SHAD`+sender+session; сервер по умолчанию рассылает всем), фолбэк — UDP P2P-канал (порт 3658).
Клиент принимает «хостовые» пакеты только от `sender == session == свой хост`.

## 5. Свой мир гостя и диск (WS, GI)
- Пока гость: живая таблица флагов = мир хоста. Первая копия каждой перезаписанной группы + своё время → **own-world** (`<bbsc>\own-world\own-<user>-<slot>.bin`).
- Подборы гостя в мирах хостов → **guest-items** (`taken-<user>-<slot>.bin`). Прогресс хоста (boss-флаги + OR kind 1) → **shared-progress** (`pending-…bin`, раз в 10 с).
- Разговоры/talk-driven события гостя → **журнал в памяти**; предметы разговоров и home awards — в памяти.
- Дома (свой мир, жив, 4 с): бэкап сейвов (`save-backups\before-duel-bell-<ts>`) → restore own world → OR прогресса → журнал → предметы/награды.
- После краша: при следующем «дома» восстанавливаются own-world и pending progress (журнал — нет).
- Имена файлов зависят от **слота сейва** = новейший `userdataNNNN`, записанный в этом запуске (см. LA-1/GI-2).

## 6. Пути (ПК)
| Что | Где |
|---|---|
| Установка лаунчера | `D:\Games\Bloodborne\bbport-coop` (`out\eboot.elf`, `out\patches.bin`, `coop\bbsc\`) |
| user_dir / сейвы | `D:\Games\Bloodborne\ddd\savedata\<user>\CUSA00207\SPRJ0005\userdata000N`, `coop-backups\` |
| BBSC (мод, логи, журналы) | `%LOCALAPPDATA%\bbport-coop\BBSC-0.0.1-BBport\bbsc\{bbsc.dll, logs, captures, save-backups, bell-pending, own-world*, shared-progress*, guest-items*}` |
| Сервер на ПК-хосте | `%LOCALAPPDATA%\bbport-coop\bbsc-server\server\{shadnet.exe, BBSC-GameServer.exe, logs}` |
| VPS | `/opt/bbsc/{gameserver,shadnet,logs,data,backups}` |

\* на ПК не найдены (ПК в логах был хостом).
