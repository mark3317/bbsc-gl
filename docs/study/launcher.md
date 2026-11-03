# Область 5 — лаунчер (LA)

Репо `bloodborne_pc`, ветка `mark/coop-relay`. Лаунчер — **Python + QML** (`launcher/`, ~9.8k строк py + `qml/`), не C++/Qt.
Ссылки: `coop:` = `launcher/bbport_coop.py` (774), `be:` = `launcher/bbport_launcher_backend.py` (1734).
Не читались: `bbport_launcher_win.py` (2772, старый UI?), QML-страницы, мастер `bbport_pkg_setup.py`, i18n.

## 1. Файлы
| Файл | Роль |
|---|---|
| `bbport_coop.py` | весь кооп: пакеты BBSC, override нашей сборки, Tailscale/IP, файрвол, хостинг серверов, invite, аккаунты shadNet, env запуска, бэкап сейвов |
| `bbport_launcher_backend.py` | QML-бэкенд: настройки (`settings.json`, `bbport.ini`), слоты `coopSetup`/`coopInstallZip`/старт коопа (`be:1416-1520`) |
| `bbport_launcher_qml.py`, `qml/*.qml` | UI: Main, HomePage, SettingsWorkspace, SetupWizard, Rail… |
| `bbport_pkg_setup.py`, `bbport_readiness.py`, `bbport_vulkan.py`, `bbport_steam.py` | мастер установки игры, проверки готовности, GPU, Steam |
| `packaging/windows/build-coop-package.sh` | пакет для друзей: bb-probe (с BBSC relay) + лаунчер + `coop-server.json` (сервер по умолчанию, `COOP_INVITE`) + `coop/bbsc/` (наша сборка из `mods-src/BBSC/build/mod`) → `dist/bbport-coop-windows.zip` |

## 2. Пакеты BBSC
- Официальные релизы `CLSAMG22/BBSC` качаются по запросу, проверяются по опубликованному SHA-256, распаковываются с защитой от path traversal в `%LOCALAPPDATA%\bbport-coop\bbsc-client|bbsc-server` (старые имена `BBSC-0.0.1-BBport/-Server` поддерживаются, на этом ПК — ещё старое) (`coop:161-250`, `coop:87-93`).
- При обновлении сохраняются `bbsc/logs`, `save-backups`, `own-world`, `captures`… (`coop:48`).
- **Override** `coop:252-269`: файлы из `<port>\coop\bbsc\` копируются поверх официальных, только если установленная версия == `base` из `coop\bbsc.json`.
- Установка — при первом коопе (`_coop_ensure_packages`), обновление — кнопкой (`coopSetup` `be:1416-1433`), ZIP с диска — `coopInstallZip`.

## 3. Кооп-запуск
1. Хост: `Host.start` `coop:530-558` запускает `shadnet.exe` и `BBSC-GameServer.exe --shadnet <addr> --host 0.0.0.0 --advertise <addr> --summon-interval 5 --no-playlog` (без `--relay-session-routing`). Адрес — Tailscale-IP или локальный (`coop:297-367`); файрвол — правила для 100.64.0.0/10 и LocalSubnet через UAC (`coop:375-418`).
2. Invite: `BBCOOP-` + base64url(JSON `{a: адрес, k: ключ регистрации}`) (`coop:596-612`); ключ — `RegistrationSecretKey` в `shadnet.cfg` (`coop:500-516`).
3. Гость/хост: `create_account` (login → register с ключом → login) `coop:628-656`; имя 3-16 символов, пароль ≥4.
4. `backup_saves(user_dir)` → `<user_dir>\coop-backups\<ts>\savedata` перед каждой сессией (`coop:767-774`).
5. `co_op_environment` `coop:704-754`: пишет `host_overrides.json` (ss4.scej-network.jp → gameserver, summon_messenger → webapi) в `coop_dir` и `<port>\user`; убирает THD-переменные; ставит `BBSC_SAVE_DIR`, `BBSC_RELAY=<addr>:RELAY_PORT`, `BB_PROBE=bbsc-launch.exe`, `BBSC_EMULATOR`, `BB_ONLINE=1`, `BB_SHADNET_*` (включая пароль), `BB_COOP=1`.

## Кандидаты в находки
- **LA-1 (важный) `BBSC_SAVE_DIR` указывает на копию сейвов, а не на живые.** `coop:737-740`: приоритет у `active_save_dir(save_copy)` —
  папка из `coop-backups`, сделанная `shutil.copytree` (сохраняет mtime) ДО запуска. BBSC считает активным слот, записанный
  **после старта запуска** (`BBSC re:6219-6230`) — у копии таких нет; живые сейвы bbport лежат в `<user_dir>\savedata\<user>\CUSA00207\SPRJ0005`,
  а BBSC ищет только в `<cwd>\user` и `%APPDATA%\shadPS4` (`re:6206-6270`), про `BB_USER_DIR` не знает (grep пуст). При `user_dir`
  вне папки порта (на ПК `D:\Games\Bloodborne\ddd`, на ноуте `C:\Games\Bloodborne\test`) `BbscActiveSaveSlot()` может быть пуст весь запуск →
  own-world, pending progress и guest-items не пишутся на диск (только в память), т.е. краш гостем = потеря своего мира. Усиливает GI-2.
  Косвенно: на этом ПК в `bbsc\` нет папок `own-world/`, `shared-progress/`, `guest-items/` (но в просмотренных логах ПК был хостом).
  **Проверено на ноуте 2026-10-29 (ssh, только чтение) — ПОДТВЕРЖДЕНО практически:**
  - в 34 логах 26–27.10 ноут был гостем (`session state 6`), механизм в памяти работает: «own world: kept before the join load» (1–3 раза на лог),
    восстановление дома и слияние прогресса есть в большинстве логов;
  - но на диске: `own-world\` — один файл `own-sd1-1.bin.restored` от **26.10 18:50**, `shared-progress\` — один `pending-sd1-1.bin.merged` от 26.10 18:50,
    `guest-items\` — нет. Файл пишется заново при каждом сохранении журнала и переименовывается в `.restored`, так что mtime 26.10 значит:
    **во всех ~30 гостевых сессиях 27.10 журнал на диск не писался** (слот неизвестен) — краш гостем 27.10 потерял бы свой мир;
  - живые сейвы гостя обновлялись в `C:\Games\Bloodborne\test\savedata\1\CUSA00207\SPRJ0005` (userdata0001/0010 — 27.10 20:26), а BBSC
    бэкапит из копии: лог «duel bell: save backed up C:\Games\Bloodborne\test\coop-backups\20261027-202239\...\SPRJ0005 -> …save-backups\…».
  - Что было иначе 26.10 до 18:50 (имя пользователя `sd1`), не выяснял.
- **LA-2 Бэкапы растут без ограничений, в двух местах.** BBSC `save-backups\before-duel-bell-*`: на этом ПК **63 папки ≈ 1 ГБ**, на ноуте **1250 файлов ≈ 1.4 ГБ** и 48 папок `coop-backups` (подтверждает GI-3);
  лаунчер добавляет `<user_dir>\coop-backups\<ts>` на каждый запуск коопа (`coop:767-774`), очистки нет.
- **LA-3 Обновление официального BBSC молча отключает нашу сборку.** После `coopSetup` версия ≠ `base` → `apply_override` возвращает '' без
  сообщения (`coop:261-262`); игрок играет на официальном DLL без наших правок, а у партнёра может остаться наша — разные протоколы
  (старые пакеты без конверта отбрасываются `relay:268-274`).
- **LA-4 Сервер хоста без маршрутизации по сессии** (`coop:550-552`) — для одного хоста нормально, но подтверждает, что `--relay-session-routing`
  нигде не включается (SN-02).
- **LA-5 Пароль shadNet хранится в `settings.json` открытым текстом** (`be:162`, `bbport_launcher_win.py:258`) и передаётся через env
  `BB_SHADNET_PASSWORD` (`coop:749`) — виден в окружении процесса игры и в дампах. UI просит «пароль, который нигде не используется». Низкий.
- **LA-6 Ключ регистрации внутри invite-кода** (base64, `coop:596-598`): кто получил приглашение — может заводить аккаунты на сервере хоста
  бессрочно; ключ не меняется (`coop:500-516`). По дизайну, низкий.
- **LA-7 Гонка старта серверов на `sleep`**: 2 с до gameserver и 1 с до проверки (`coop:547`, `coop:554`); медленный старт shadnet → gameserver без
  shadnet. Есть повтор входа 10 с (`coop:660`), низкий.
