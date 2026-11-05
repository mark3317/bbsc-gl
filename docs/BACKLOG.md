## 05.11.2026 — late arrivals and native presence/travel corrections

User run19:09-19:29 failed: absent host model/name remained, host could not see
arriving guest, guest lamp return failed, host repeatedly returned to Dream
about7s after Yharnam arrival (also solo19:24:02->19:24:09). No crash; old MODEL
visible messages were not proof of a rendered mesh. Both games later closed.

Source changes:
- Native018C6390 presence switch replaces the insufficient render-byte hide;
  pair disable/enable and reconcile every remote actor even without an insert
  task. Retain native binding and bounded reconstruction. Render log now says
  repair requested, not visibly confirmed. The previous blanket avoidance of
  the native switch was too broad; its native cleanup needs paired enable.
- Observe completed load generation and curtain in presence before map ownership
  or rendering. Game tick may miss the entire load; the old map/visit must not
  authorize actors or capture Yharnam enemies into Dream's snapshot. World capture
  additionally requires agreement with the native current map and no load.
- Native c1_11 has an executor flag-range gate before SetFlag. A scoped visitor
  lamp request may pass that native gate to the local travel interceptor. Both
  host and guest use independent native stage requests. Consume invalid travel
  contexts locally, never broadcast them into another player's native event.
  Intercept before personal journal hooks; one-shot travel flags are excluded
  from quest journaling/replay and cleared through native SetFlag before a trip.
  This removes competing old event requests; the precise earlier solo loop cause
  was not conclusively observed and must be rechecked in game.
- Enemy messages assemble atomically with separate sequence/epoch fences; retain
  streamed-out kills. A follower seeds newly streamed actors once per visit and
  owner epoch only after complete flags/enemies. Use native HP/warp and native
  ForceCharacterDeath018BF9A0 with native2004[4]'s no-reward bit21 for historical
  dead actors; never just leave a live-looking inert actor at HP0. Existing map
  owner remains selected while present; native HP/hit routing stays in charge.

Targeted production fixtures PASS (travel range/host+guest commands, missed-load
presence, all-actor hide and reunion, multipart enemy reorder/incomplete/stale
state, native no-reward death and one-time baseline, altar and authority). MOD
syntax PASS; original ELF validates17 hook spans/7 calls; trampoline PASS.
Code/build/deploy/game results are separate: new gameplay confirmation OPEN.

## 05.11.2026 — Dream lamps, command ownership and per-peer model lifecycle

Build/deploy/start result: source f8e7bf6 DLL build and isolated-stage delta
both exit0. Backup independent-player-lifecycle-20261105-190858. Two profiles
started19:08:58 MSK; native processes16252/12892, fresh run_20261105_190922.log
(P2) and run_20261105_190926.log (P1). Both report enemy/travel hooks ready and
local relay connected. Startup succeeds; actual co-op interaction/model/flicker
confirmation remains OPEN. No computer-use, save edits, or game termination.
Evidence: parent out/coop-dev/runs/independent-player-lifecycle-20261105.

18:39 check: no-follow remains confirmed, but guest headstone list is empty,
altar does not respond, host prompt flickers and guest model is missing after
host reunion. Read-only flags show guest normal lamps unset while host lamps
are set; occupied altar record already agrees. Runtime respawn guard also
repeatedly reverses the guest's independent lamp selection.

Normal lamps now enter the existing shared kind1 progress journal; the host
catalog supplies only their live Dream bits, without copying personal services
or chalice lamp namespace. Ordinary received map snapshots also contribute to
the existing shared progress/reward path. Commands resolve the actual native
executor's talk record, with load-generation fencing, instead of the last
unrelated evaluated device. Independent mode retains native selected respawn
point and full native auxiliary word; prejoin home backup remains unchanged.

Every remote peer has an identity/visit-bound render lifecycle. Removed native
SetDisabled on players: it unlinks attachments, so toggling it cannot restore
a model. Use native member setter and bounded native insertion task transition;
wait for native activation/model readiness before restoring visibility. Native
physics reset/idle are retained only for a confirmed alive peer's stale death
visual. Legacy overlapping self/remote repair is skipped in independent mode.
No HP/type writes or custom mesh creation. Minimal draw/fade/death-bit repair
remains where no safe player-oriented native wrapper has been established.
The event revive wrapper013CBAD0 handles local-player global state or script
IDs below10000; it is not a safe generic replacement for remote PlayerIns.

Targeted production fixtures PASS: player lifecycle (four peers, load/address
reuse, apart/reunion, death, bounded retries), altar/shared progress, command
context, respawn guard, member binding, presence bridge and authority callbacks.
Full MOD syntax PASS. Build/deploy/start and gameplay are separate pending steps.
User preference: favor native game functions over duplicate manual handlers.

## 05.11.2026 — independent travel: native integration, development branch

18:25 run: host travel no longer moves guest (user confirmed), both exits0,
no Warp crash recurrence. Remaining guest Dream refusal traced to device actor
!=PlayerIns. Fixa904d93 admits audited devices, blocks remote player copies,
isolates Dream phase and owner flag echoes, makes object corrections owner-only.
Targeted tests/build/delta PASS; P1/P2 restarted18:39 MSK with hooks ready.
Guest travel and host headstone prompt flicker still require game confirmation.

Second game check: activation CONFIRMED18:15:12, guest lamps FAILED and both
profiles crashed. Fixd6bd1f6 corrects real ESD evaluator/result register context
and16-byte native Warp argument alignment. Targeted production fixtures/syntax
PASS, DLL build/delta exit0, isolated stage updated18:24. No automatic launch;
recheck guest lamps and authority takeover after owner load/return. See HANDOFF.

First user game check FAILED (legacy follow/closed lamps). Native room was
incorrectly read from self endpoint fields (zero). Fixf398e01 reads actual full
64-bit Matching2 room; targeted regression PASS, build/delta exit0, P1/P2
restarted18:14 with explicit enemy/travel hook readiness. Recheck activation
and personal travel; overall feature remains OPEN. Details in HANDOFF/fixes.

Source73d84d3 implements native per-map ownership, scoped state transfer, local
lamp loads and host altar travel. Targeted native/model fixtures PASS; final
DLL build/delta exit0, isolated P1/P2 startup18:01 MSK and local relay connection
confirmed. Player-to-player admission/full game scenarios OPEN; user tests
manually, no computer-use. See
[implementation](fixes/2026-11-05-independent-world-travel.md).

### Historical first gate

User authorized implementation on `codex/independent-world-travel` and a two-profile
PC launch. World/place presence bridge and pure owner/routing/guest-altar rules
are implemented and targeted fixtures PASS. DLL build/delta exit0; isolated staging Player1/2 startup confirmed16:59 MSK
(PID25140/11776,34/34 hooks each); connection unconfirmed. Main install unchanged.
Live capability is metadata ONLY:
free travel, native AI handover and the host altar UI are NOT implemented yet.
Host-world guests must see host chalices; own world keeps personal altars.
[Implementation and remaining work](fixes/2026-11-05-independent-world-travel.md).
Do not declare the overall feature complete or reopen lamps from this first gate.

## 05.11.2026 — подтверждение пользователя для BBGL 1.2.0

Пользователь сообщил: основная сюжетная игра полностью проверена на прохождение
в кооперативе, переход в NG+ работает. В релизе подчеркнуть рабочее совместное
прохождение чаш и возвращённую штатную случайную генерацию корневых подземелий.
Это актуализирует прежние общие формулировки о неподтверждённом сюжетном финале.
Подтверждение не закрывает автоматически все дополнительные обряды, редкие
сценарии наград/переподключения, повторную выдачу предметов в NG+ и все составы группы.

## 05.11.2026 — актуальные незакрытые сценарии наград

Архитектура, ограничения и история: [REWARDS.md](REWARDS.md).
DLL с исправлениями установлена на ПК; два native-профиля стартовали06:24:17 МСК.
Целевые fixtures и сборка PASS, игровые сценарии остаются открыты:

- повторный вход после «Следа когтя» Гилберта/других одноразовых предметов,
  отсутствие предмета после личного подбора и дома; корректный новый подбор в NG+;
- смерть гостя одновременно с врагом/охотником, полный wipe и невзятое тело;
- native «Осмотреть» ритуальную кровь и сохранение личных NPC-условий;
- недостающие уникальные награды base/DLC и чаш при загрузке к хосту,
  уже перенесённая победа, хранение предмета в сундуке, повторный вход;
- пересечение catch-up с живым boss event, отказ native выдачи, независимые ритуалы.

Не возвращать опрос наград раз в секунду, рассылку инвентаря хоста или
дополнительную death-recovery очередь скриптовых/боссовых наград. Бессмертие
мешает сценарию смерти; без просьбы настройки не менять. Личные стадии Джуры
не уравнивать с хостом: более ранняя причина его состояния не доказана.
Старые пункты ниже — история этапов; текущий статус сверять со сводкой.

## 05.11.2026 — repeated Clawmark/global native receipts installed on PC

P2 picked lot29010 at05:53:26 and05:56:35 across rejoin. Ledger already records
its actual delivery; receipt50001300 belongs to area0 and was outside map receipt
capture/replay. General fix restores personal global receipt bits before native
roll from confirmed own lot history; immediate rune receipt flush, minimal own
snapshot bits, load/producer hooks, no inventory grant or periodic scan. Original
107 global lots/86 flags audited (47 NPC-linked);63 NPC map-receipt lots already
in map scope. Targeted production/native fixtures PASS. DLL build/deploy exit0, delta5, backup global-loot-receipts-20261105-20261105-062348. P1/P2 start requested06:23 MSK. Gameplay remains OPEN.
[Evidence](fixes/2026-11-05-global-loot-receipts.md).

## 05.11.2026 — reward check on host load, event-driven (INSTALLED PC, gameplay OPEN)

Missing unique base/DLC rewards now check after guest inventory readiness, without
waiting for home. 17 native unique chalice award lots are eligible from original
host earned-receipt facts in the existing progress packet. These facts are never
copied into client receipt flags or dungeon progress; local native award writes
its own actual receipt. Both peers need the updated DLL for the extra facts.
Receipt/history/carried+stored checks retained; first catch-up and live boss event
share the runtime accounted ticket. No timed reward scan: work signals come from
inventory readiness, newly added boss completion/host facts and pending-file load.
Identical packets/ordinary map flags do not trigger reward checks. A failed give
keeps pending eligibility and waits for the next load/new progress event.
Targeted 55-lot native trampoline, original cup PARAM data, guest/home/slot guards,
packet deduplication, event work scheduling and actual ledger persistence PASS.
Final DLL build/deploy exit0, delta5, backup host-load-rewards-20261105-20261105-054206.
P1/P2 start requested05:42 MSK; startup confirmation in the parent run record.
[Details](fixes/2026-11-05-host-load-unique-rewards.md).

## 05.11.2026 — native receipts and unique boss catch-up (INSTALLED PC, gameplay OPEN)

Corrected actual 2003[4] permission1 versus [36] permission0; reviewed guest awards
now use native permission0. Native scripted completion is no longer rolled back;
confirmed map pickup receipts enter own snapshot immediately, including same-tick
boss-award/TakeItem. Shared progress preserved; 15 unique boss rewards/base+DLC
catch up through native Award, including already-merged victories and stale
missing-chalice receipts. Actual give history/storage prevent duplicates; old
untracked consumables/random gems excluded by latest user scope. Seven pure m29
reward events use original selection/award with per-character/ritual/layer/lot
receipts; independent own dungeon progress preserved. Targeted production/native
fixtures PASS. Final DLL build/deploy exit0, delta5, backup
native-reward-receipts-20261105-20261105-050421. P1/P2 requested start05:04 MSK;
process/startup confirmation in the parent run record.
[Details](fixes/2026-11-05-native-reward-receipts.md).

## 05.11.2026 — native script/boss delivery INSTALLED PC; gameplay OPEN

38 лотов: native award вместо ручного BossGoods/add/броска, без нового death
recovery и без K3 inventory block/fallback этих лотов. Сохранены личные условия
и необходимая одноразовая обработка boss type-wait. Целевые fixtures PASS;
игровая выдача/полная сумка/смерть/два независимых гостя ещё не подтверждены.
Лаунчер/мод/порт с одобренным курсором собраны и установлены, оба exit0,
copied5186; P1/P2 старт04:00 МСК с сохранённым бессмертием.
[Подробности](fixes/2026-11-05-native-scripted-boss-rewards.md).

## 05.11.2026 — native enemy loot INSTALLED PC; gameplay OPEN

Удалена ручная очередь добычи врагов. Native death worker разрешает выдачу
подбираемого тела при смерти гостя и сохраняет полный результат native броска.
Сохранён оригинальный once-per-life latch; native fixtures повторной смерти/
нового врага и guards PASS. DLL build/deploy exit0, два профиля запущены
03:25 МСК с запрошенным бессмертием. Проверить реальные личные тела охотников,
обоих гостей, одновременную смерть (без бессмертия), полный wipe/карту/неподобранное.
[Подробности](fixes/2026-11-05-native-enemy-loot.md). Историческая запись ниже
описывает удалённую реализацию, не текущую очередь.

## 05.11.2026 — OPEN: надёжность добычи при смерти гостя / native loot study (история)

Production queue теряет награду при dead/loading/left-host/invalid-global;
простого переноса проверки недостаточно из-за одноразового work signal.
Риск двойных native пуль/флаконов при nameId0: guard ошибочно использует имя
как признак источника. Проверки воспроизводят ошибки; код DLL не исправлялся.
Штатный подбор уже разрешён; native award arg0 проходит permission branch,
но native producer/filter трупной добычи ещё не прослежен полностью.
До перехода требуется один производитель личного лота, дедуп конкретной смерти,
проверка одновременной смерти/загрузки, двух гостей, nameId0, смешанных лотов,
NPC prerequisites/скрытых сундуков, полной сумки и повторного входа.
См. [исследование](fixes/2026-11-05-native-guest-loot-study.md).

## 05.11.2026 — личные ключевые предметы установлены на ПК

DLL собрана и установлена в02:26 МСК, оба exit=0; Player 1/2 стартовали с новой
сборкой и отдельными профилями. Проверить в игре: вход не выдаёт предметы хоста,
свой подбор/награда/покупка работают, уже полученное восстанавливается после
загрузок; отдельно значок Пылающего молота. Реальные сейвы не менялись.
Прогон: родительский out/coop-dev/runs/personal-keys-20261105/run.md.

## 05.11.2026 — личное получение22 ключей/значков/инструментов

Обмен инвентарём хоста полностью удалён из исходников по новой просьбе пользователя.
У всех22 есть самостоятельный источник; EndIfClient награды значка Пылающего молота
исправлен. Проверки данных, производственной выдачи и сохранения квитанций PASS.
Сборка/установка и реальный игровой контроль всех22 открыты. Текущая установка
ещё использует предыдущую разовую выдачу при входе. [Аудит](fixes/2026-11-05-personal-key-items.md).

## 05.11.2026 — проверить отсутствие подсказок о колоколах у лестницы

Исходники кооп-overlay убирают MSB Message 1121/1122; целевые проверки PASS.
После установки проверить у всех участников отсутствие двух подсказок при
сохранении остальных посланников и зеркала. Установка отложена при работающих
играх; игровой результат открыт. [Разбор](fixes/2026-11-05-dream-bell-hints.md).

## 05.11.2026 — разовая выдача ключей установлена на ПК

Сборка/установка exit=0, 01:54 МСК; Player 1/2 действительно стартовали
с отдельными профилями. Проверка выдачи при входе, новых наград босса/подборов
без периодического обмена и повторного подключения остаётся открытой.
Подсказки двух колоколов также включены в дельту. Прогон в родительском
out/coop-dev/runs/join-only-keys-20261105/run.md.

## 05.11.2026 — разовая выдача ключей при подключении

Исходники изменены: начальный снимок ключей/значков/инструментов передаётся по
запросу входящего гостя, без периодического обновления от хоста. Проверить после
будущей сборки/установки: поздний вход получает недостающее; новый подбор хостом
не выдаётся автоматически уже подключённым гостям; совместная победа и личный
подбор дают награду своими путями; второй гость и повторная загрузка не обновляют
первому набор. Новый вход разрешает новый снимок. Fixtures PASS, gameplay OPEN.
См. fixes/2026-11-05-join-only-shared-keys.md.

## 05.11.2026 — П3 корректно вернулся после краша хоста П1

Прогон 00:52–01:00 МСК: пользователь подтвердил краш П1 (первоначальное П2
исправлено). П3 обнаружил потерю по нативному таймауту, прошёл state 6 -> 7 -> 0,
ограниченный drain 2 s и send-home; в 01:00:44 вернулся в личный Сон, один,
без автопоиска Small Bell. Около 33 s от исчезновения П1 до полного возврата.
Причина краша не установлена: у П1 нет Fault/stack, runner exit=0.
Повторное подключение после последнего возврата и сохранность реальных сейвов
не проверялись. Код/сборка/деплой не менялись. Логи и разбор в родительском
out/coop-dev/runs/host-crash-review-20261105-0101/run.md.

## 05.11.2026 — исправление отключения П3 установлено на ПК

DLL с защитой Blank/drain и готовой изоляцией личных ламп чаши собрана и
установлена в общую установку ПК (build/deploy exit=0, дельта 5 файлов).
Исходные входы сборки не изменились; связанные чаты завершены. Бэкап:
D:/Games/Bloodborne/coop-dev/backups/p3-blank-fix-20261105-20261105-005157.
Три существующих Player CMD запущены 00:52 МСК с отдельными профилями.
Игровое подтверждение исключения П2 → переход П1 в Сон при оставшемся П3
открыто. Настройки, сейвы и игровые данные не менялись. Подробности:
родительский out/coop-dev/runs/p3-blank-deploy-20261105/run.md.

## 05.11.2026 — Blank выбранного гостя закрывает сессию при загрузке хоста

После исключения П2 оставшийся П3 отключён при переходе П1 в Сон: старый Blank
разрешает Stop по временному отсутствию персонажей (reload phase 4, reinsert true).
В исходниках выбранное исключение отделено от закрытия комнаты, добавлены guards
сетевого состава/reinsert/reload; целевые проверки PASS. Полный syntax check OOM.
После сборки/установки проверить исключение П2 и переход П1 в Сон при оставшемся
П3, а также настоящее закрытие пустой комнаты. [Подтверждение](fixes/2026-11-05-p3-disconnect-after-selected-kick.md).

## 05.11.2026 — проверить первый вход в чашу за одну загрузку

П2 принимает П3, затем П1 из чаши с тем же номером карты. П1 должен за первую
загрузку получить ритуал П2 и появиться в его мире. Отдельно проверить повторный
вход и последующий переход П2 в другую чашу. [Разбор](fixes/2026-11-05-chalice-single-load.md).

## 05.11.2026 — проверить видимость между гостями на установленной DLL

П2 в чаше, сначала входит П3, затем П1. Проверить видимость в обе стороны до и
после перехода через лампу, повторного входа и возрождения одного гостя при другом
погибшем. [Состояние проверки](fixes/2026-11-05-remote-model-visibility.md).

## 05.11.2026 — проверить второго гостя в чаше после исправления точки появления

Профиль 2 принимает профиль 3, затем профиль 1 на той же карте. Проверить появление
профиля 1 рядом с хостом и сохранение обоих кооператоров в мире. [Подробности](fixes/2026-11-05-same-map-host-placement.md).

## 04.11.2026 — аудит соединений, доработка и установка на ПК

Разбор этапов, воспроизведённые гонки и матрица проверок — [отчёт](fixes/2026-11-04-connection-system-audit.md).
113 различных проверок Party прошли в ходе аудита; завершающий набор — 52/52.
DLL и пакет собраны с exit 0, на этот ПК установлена дельта из 10 файлов,
резервная копия — Bloodborne/coop-dev/backups/connection-audit-20261104-234844.
Режим — три отдельных профиля Player, результаты запуска в родительском
out/coop-dev/runs/connection-audit-20261104/run.md. Соединение в игре открыто.

## 04.11.2026 — individual Player shortcuts: Beckoning after Player 3 exit

23:15:43 MSK Player 3 exited (GPU out of device memory, runner exit 23).
Static group revision 335 still owned by Player 2, room/pending/joined empty.
Restart recovery set release intent and requested unanimous release. Its
coordinator (revision 335 modulo 3) was the absent Player 3. Player 2's three
acquire requests were denied; native item effect could not start.
Standalone Player shortcuts now use the existing dynamic Party on the three
profile-specific loopback endpoints. Coordinated --all retains static consensus.
Targeted regression: pre-fix acquire timed out after peer 3 exit; post-fix
Player 2 acquired, Player 1 saw the host and joined its room. Script installed
on this PC (copy exit 0), backup player-bell-20261104-232637. In-game icon OPEN.

## 04.11.2026 — latest launcher + approved setup hint INSTALLED PC23:14MSK

Launcher rebuilt with approved short Russian setup hint: pick up Notebook from
messengers in Hunter's Dream; items for shared play are granted automatically.
English equivalent included. Latest local launcher/DLL/Party changes packaged;
DLL build23:05 and port18:22 reused after source metadata check. Fast package
exit0, full PC deployment exit0 copied5186. Backups under Bloodborne/coop-dev/
backups/latest-launcher-approved-20261104-20261104-231340. Three existing Player
CMD entries started23:14:32 with separate profiles. Gameplay remains OPEN.
No source pin/commit/push, process stop, save/settings or original game edits.
Parent out/coop-dev/runs/latest-launcher-20261104-2305/run.md.

## 04.11.2026 — retained-host rejoin relay recovery INSTALLED PC23:01MSK

New admissions reset only the target outgoing stream/sequence/error fence.
Old queued work and late failures cannot poison the new stream; other guests
and host ownership remain intact. Placement enqueue reports acceptance and
retries pending delivery every500ms within existing90s expiry; native ACK required.
Before-fix production rejoin regression FAIL, targeted transport/placement/native
NP/idle-host checks PASS. Repeated HTTP/native relay JoinRoom tested without
host release/acquire, with fresh manual responder actions and prior peer failure.
Two-file Party delta prepared+deployed exit0, no DLL/port rebuild needed.
Backup D:/Games/Bloodborne/coop-dev/backups/rejoin-host-held-20261104-20261104-230130.
Three existing local Player CMD entrypoints started23:01:42; gameplay OPEN.
No settings/save edits, process stop, commit/pin/push or VPS update.
See fixes/2026-11-04-rejoin-held-host-relay.md; parent run
out/coop-dev/runs/rejoin-host-held-20261104-2302/run.md.

## 04.11.2026 — repeated PC guest join failure OBSERVED 22:47/22:49MSK

Closed PC/laptop logs22:30–22:50 reviewed. PC guest attempts22:47:08 and
22:49:06 enter native4, return0 after8s; Party rejects JoinRoom102 with
Native join placement not acknowledged. Laptop sees rooms/pending, no joined.
Earlier PC state6 at22:46:33; reverse laptop state6 at22:50:18 succeeds.
Failure localized to native JoinRoom/placement acknowledgment; root cause OPEN.
PC runner exit0 after user quit. Active PC run log appeared0bytes until close,
then1.60GB; do not infer missing runtime events from empty active runner log.
No product/build/deploy, save/settings changes, process stop, commit/pin/push.
Evidence parent out/coop-dev/runs/connection-check-20261104-2254/run.md.

## 04.11.2026 — active idle-host authority + quiet HTTP reset INSTALLED PC/laptop22:27MSK

Supersedes OPEN findings below. Drained room/pending/joined search with active
Beckoning and no explicit cancel keeps Party ownership in native0/2/5. Dynamic
staged admission blocks this exception. Other players remain blocked; same host
can accept a new guest without ringing again. Explicit silence/expiry still
releases; native recovery of stale occupied rooms unchanged.
HTTP.handle now closes expected reset/abort/broken-pipe sockets quietly; failed
response I/O closes keep-alive. Unexpected handler errors remain visible.
Both regression cases fail before fix;13 role/HTTP +4 targeted native recovery/load
checks PASS after fix. Python compile/Party delta package exit0. Runtime compat.py
only, installed PC/laptop exit0,1file each; no DLL/port/launcher rebuild needed.
Backups Bloodborne/coop-dev/backups/idle-host-http-20261104-20261104-222706(PC),
222738(laptop); initial laptop backup also retained before successful retry.
No launch/process stop, saves/settings edit, commit/pin/push or VPS change.
Gameplay OPEN. Parent out/coop-dev/runs/idle-host-http-20261104/run.md.

## 04.11.2026 — six join/leave cases reviewed; idle-host mismatch OPEN

PC/laptop22:04–22:11, DLL22:00:29:6 successful guest joins (5 laptop,1 PC),
Small Bell consumed at all joins and6 home returns without automatic re-ring.
Menu exits, Blank, kick, host exit and role exchange observed. Final journals both
fully drained. Latest return-bell fix gameplay confirmed for this run.
Found functional mismatch: native empty-host0 with Beckoning still active can
retire Party ownership after3s. PC22:07:04/22:09:55 host=true followed by
host_stopped retirement; isolated real DynamicEngine+Compatibility reproduction
confirms native bell=true with owner=None/host presence=None. New-host overlap
therefore remains possible. Two Party owners/actual simultaneous presses NOT
observed; absence of authority overlap does not prove effect overlap impossible.
Also17 local HTTP ConnectionResetError10054 tracebacks (4PC,13laptop), outside
existing do_POST OSError handler. Requests/gameplay continue; diagnostic flaw.
No product edit/build/deploy, saves/settings write, process stop or commit/pin/push.
Detailed review: parent out/coop-dev/runs/connection-matrix-20261104-2212/run.md.

## 04.11.2026 — guest return must not re-ring Small Bell INSTALLED PC/laptop22:01MSK

Latest laptop run_20261104_214815: guest state6 at21:52:19, Blank return0 at
21:52:42, world-load host check explicitly reactivated Small Bell21:52:55.
Successful guest entry now consumes9005 without Stop/Blank/PartyCancel. Cleanup
waits through loading/death; return removes any restored residual effect once.
After visiting a host, return/later personal loads cannot auto-ring. Availability
still checks existing hosts; new manual rings and deliberate collision-yield work.
JoinRoom withdraws sign; consumed/late create callbacks cannot republish until
settled responder-off return followed by a new responder-on observation.
Nine real RPC/Compatibility role cases + production native role fixture PASS.
DLL build exit0; unchanged inputs;6-file DLL+Party delta PC/laptop exit0. Backups
Bloodborne/coop-dev/backups/return-bell-20261104-20261104-220119(PC),220136(laptop).
No launch requested/performed, process stop, saves/settings edit, commit/pin/push
or VPS change. Gameplay OPEN. See fixes/2026-11-04-bell-role-switch.md and parent
out/coop-dev/runs/return-bell-20261104/run.md.

## 04.11.2026 — Small Bell -> Beckoning reverse switch INSTALLED PC/laptop21:47MSK

Latest laptop21:36:40 grant was revoked4ms later by the OLD responder sample;
native host effect then remained without Party ownership. Fixed direction fence:
responder release requires Beckoning witnessed in the exact new scope. Acquire
withdraws old sign, advertises reserved host intent immediately; late creates
cannot republish. Explicit cancellation drains even before first host sample.
Native handler erases9005 before granted Beckoning apply, retrying erase failure.
Eight targeted RPC/bridge cases + production deferred-item fixture PASS. DLL build
exit0;7-file DLL+Party delta PC/laptop exit0; unchanged source inputs and no other
active related work. Backups Bloodborne/coop-dev/backups/
responder-to-host-20261104-20261104-214701(PC),214720(laptop).
Both normal launchers started/responding, PC35076/session2, laptop5356/session1;
temporary interactive launch task removed. No game launch/process stop or real
save/settings edit, commit/pin/push, VPS change. Reverse-switch gameplay OPEN.
See fixes/2026-11-04-bell-role-switch.md and parent
out/coop-dev/runs/responder-to-host-20261104/run.md.

## 04.11.2026 — timestamped run logs installed PC+laptop21:25MSK; endgame restored

Supersedes source-only log-name status below. Launcher/Party fast package build
exit0; current21:06 DLL and18:22 port reused. Frozen launcher --script smoke in
isolated profile created run_20261104_212434.log through both real log openers;
no last_run file. Final source metadata unchanged; related chats complete.
PC/laptop deploy exit0,5145 files each, backups under Bloodborne/coop-dev/backups/
run-log-names-20261104-212449(PC),212546(laptop). New runs use timestamped names;
legacy logs retained. User explicitly requested endgame rollback again: both
configured user_dirs restored exit0; savedata+metadata backups under saves/
before-gehrman-rollback-20261104-212353(PC),212416(laptop). No real game launch,
process stop, settings/game-data edits, commit/pin/push. New actual gameplay run
not performed. Parent record out/coop-dev/runs/run-log-names-20261104/run.md.

## 04.11.2026 — bell roles / host check: USER GAMEPLAY CONFIRMED

User reports the completed PC+laptop run works correctly ("прогнал все работает ок").
Closes the reported empty-host role latch and requested network-host check /
simultaneous-bell behavior for that run. Broader progression/NG+ is not implied.
No further product/build/deploy or live-save/settings changes in this update.

## 04.11.2026 — bell role switch + world-load host check INSTALLED PC/laptop21:07MSK

Supersedes the investigation below. Both peers initially rang Beckoning (user
clarification). Fresh native responder evidence now releases only an EMPTY
acquired search. Dynamic presence advertises active hosts; world-load host check
uses the native Small Bell, and availability/acquire reject another known host.
Simultaneous empty searches choose one host; loser cancels, waits for durable
release then searches as responder. Occupied worlds never yield; yielding fences
new room/claim admission before native cancellation. Legacy local-three unchanged.
Six RPC/bridge role cases, five production WinHTTP cases,14 dynamic tests and
native role/tick/deferred-item fixtures PASS. DLL build exit0;7-file DLL+Party
delta deployed PC/laptop exit0. Backups Bloodborne/coop-dev/backups/
bell-roles-20261104-20261104-210659(PC),210719(laptop). Build inputs unchanged.
No game launch or process stop; gameplay OPEN. No saves/settings writes,
commit/pin/push or VPS change. Launcher log-name changes remain source-only.
See fixes/2026-11-04-bell-role-switch.md and parent
out/coop-dev/runs/bell-roles-20261104-2108/run.md.

## 04.11.2026 — latest join failure: LOG INVESTIGATION / OPEN

PC twin and laptop test20:46 run, both DLL20:17:07: laptop acquired Beckoning
home gen2/rev9, then switched to native responder20:47:26 and published its sign.
Party ownership was never released; installed presence gate masks that sign.
PC search reports no_sign; no claim/JoinRoom. PC Blank release/reacquire works.
Exact laptop item/menu action unrecorded; callback failure itself not established.
Evidence parent out/coop-dev/runs/join-failure-20261104-2051 (live snapshots).
No product edit/build/deploy, saves/settings write, process stop, commit/pin/push.
See fixes/2026-11-04-bell-role-switch.md; workaround/gameplay not confirmed.

## 04.11.2026 — timestamped run logs: SOURCE UPDATED / NOT BUILT OR DEPLOYED

BBGL reader and direct Party runner create run_YYYYMMDD_HHMMSS.log using local
launch time. Exclusive creation adds _2/_3 on same-second collisions; existing
runs and legacy last_run files are retained. Launcher remains the sole log owner
when piping game output. coopdev status/collect and the build-deploy skill's
collector support both naming schemes. UI diagnostic hints and logging docs updated.
Timestamp/collision, real runner ownership, Windows reader lifetime/restart/error,
profile/latest-log and real collector on isolated fixture checks PASS. No build,
deploy/game launch, real saves/settings changes, commit/pin/push.

## 04.11.2026 — shared finale + first audience installed PC/laptop20:18MSK

Supersedes source-only status below. Full fast package exit0; later first-audience
addition rebuilt only DLL exit0, final inputs unchanged. Both devices received
same seven-file DLL+Party delta, deployment exit0 (7 files each). Backups under
Bloodborne/coop-dev/backups/gehrman-finale-20261104-201808(PC),201820(laptop).
Fallen host/guest finale, local first entrance and burst delivery code tests PASS;
gameplay OPEN. Requested endgame restore complete, previous saves+metadata backed
up under saves/before-gehrman-rollback-20261104-200959(PC),201001(laptop). Actual PC
user_dir is LocalAppData/Bloodborne Game Launcher/twin; older D:/.../twin unchanged.
No launch/process stop, settings/game-data write, commit/pin/push or VPS change.
See fixes/2026-11-04-shared-gehrman-finale.md and parent run gehrman-finale-20261104.

## 04.11.2026 — shared finale / fallen host+guest / first audience: SOURCE FIXED

Latest guest host-relay ingress stopped19:48:43, before death19:51:07 and host
ending21000020 at19:51:29. Guest respawned19:51:34 but received no movie. Full
Party peer error was not preserved: exact live overflow remains unproven.
Fixed reproducible healthy-burst queue fencing; bounded backpressure preserves
later cutscenes. Fallen host terminal events wait for native death recovery;
guest retains ending until actor/curtain ready. First Gehrman audience locally
opens guest barrier without setting fight flags, only host can talk; normal fog
returns after intro/on retry. Native/runtime/transport targeted tests and syntax
PASS; gameplay OPEN. Requested endgame restore complete PC+laptop, both exit0,
with pre-rollback backups200959/201001 under each Bloodborne/coop-dev/saves.
See fixes/2026-11-04-shared-gehrman-finale.md and parent run gehrman-finale-20261104.

## 04.11.2026 — Mergo/follow DLL installed PC + laptop19:45MSK

Supersedes source-only status below for Mergo Dream phase and explicit host-load
follow. Related chats completed/read; source inputs unchanged across DLL build.
Build, delta preparation and both five-file deployments exit0. Parent4483863 /
BBSC HEAD+gitlink0ddb1d4 plus recorded working changes. Backups under each
Bloodborne/coop-dev/backups/mergo-finale-20261104-194437(PC),194509(laptop).
Both normal launchers started; no game launch, process stop, save/settings edit,
commit/pin/push. Endgame snapshots preserved. Gameplay validation OPEN.
Record: parent out/coop-dev/runs/mergo-launch-20261104/run.md.

## 04.11.2026 — Mergo Dream finale phase: SOURCE FIXED / NOT BUILT OR DEPLOYED

Own-Dream mode skipped global burning-workshop/finale phase, despite existing
shared battle/ending support. Per explicit user request, host sends Dream snapshots
in own mode too; guest borrows only9462 and1028..1030 before construction and during
Dream ticks, retaining personal services and own-world journal. Native EMEVD and
production selective-writer/follow fixtures PASS; MSVC-target syntax exit0.
Gameplay OPEN; both peers need new DLL. Requested endgame snapshots completed
exit0 at PC D:/Games/Bloodborne/coop-dev/saves/endgame-mergo-20261104 and laptop
C:/Games/Bloodborne/coop-dev/saves/endgame-mergo-20261104 (complete savedata + BBSC
progress metadata). No restore/live-save edits, build/deploy, process stop or pin.
See fixes/2026-11-04-mergo-dream-phase.md for log evidence and scope.

## 04.11.2026 — explicit host-load follow: SOURCE FIXED / NOT BUILT OR DEPLOYED

Supersedes the log-only follow investigation below. Host repeats completed native
load generation/map/arrival transform in follow kind1 (58bytes ordinary,82bytes
chalice); bundled relay, emulator relay and signaling share strict decoding.
Explicit arrival bypasses2500ms border debounce and is sent on completion without
waiting for500ms broadcast cadence. Guest checks remain250ms. Legacy hosts retain
silence inference/debounce. Actual walking retains the previous load's arrival map.
The5000ms guest post-load guard is retained by explicit user instruction; completed
load generation and pending native construction now protect suspended loading ticks.
World flags/dungeon identity/life checks remain. Production sender/receiver/tick,
ordinary/chalice and legacy/malformed wire tests, relay role/session dispatch and
follow-arrival fixtures PASS. MSVC-target syntax of main TU, bundled relay and
emulator relay exit0. No DLL build/deploy or gameplay validation, game process
control, saves/settings/game-data writes, pin/commit/push. Both peers need updated
DLL for new follow metadata. See fixes/2026-11-04-follow-delay.md.

## 04.11.2026 — follow delay: LOG INVESTIGATION / OPEN

Latest transition evidence18:24–18:37 (before18:53 deployment); newer short
starts contain no follow events. Dream: host ready18:36:00.996, guest request
18:36:03.761, arrival18:36:18.378: ~2.8s pre-follow plus14.617s guest load.
Code waits for host load completion,2500ms stable mismatch; guest post-load
5000ms protection and optional4000ms flags wait are conditional. Two earlier
transitions first report walked/no reload, then follow~7–8s after host ready.
Arrival-by-load is inferred from>1500ms receive silence; exact failing packet
sequence unrecorded. See fixes/2026-11-04-follow-delay.md and parent
out/coop-dev/runs/follow-delay-20261104. No product edits/build/deploy/gameplay
validation of latest DLL, saves/settings writes, process stop, commit/pin/push.

## 04.11.2026 — Lecture Building host exits: SOURCE FIXED / NOT DEPLOYED

Latest main twin run18:24 onward records BOTH exits: guest native load completes
18:31:09 /18:32:16 with destination3302959 /2602959 while still in m32_00;
host completes18:31:11 /18:32:18, then guest follows and loads a second time.
Earlier button-only guard did not stop host ObjAct/event replication. Before
native event update,13200310/13200311 now disable instance network sync; guest4/6
pause the whole event, host/solo retain original local execution. Event-pass hook
installed once independently of Dream/personal-NPC options. Actual original EMEVD,
production lookup/pass, native button rejection/trampoline, follow-arrival and
shared gift-pass fixtures PASS; full MSVC-target TU syntax exit0. No DLL build or
deploy/gameplay; Bloodborne.exe still running, no process stopped. No save/settings
or game-data writes, commit/pin/push. Evidence parent out/coop-dev/runs/
lecture-doors-20261104; fixes/2026-11-04-lecture-door-authority.md.

## 04.11.2026 — top line during fade, parent SOURCE FIXED / gameplay OPEN

Fullscreen native solid fade now has a 2-physical-pixel Vulkan viewport margin.
Resolution/Y-direction and exclusion fixtures PASS; port installed PC18:24MSK,
copy exit0 with backup. Live reproduction and visual confirmation OPEN. BBSC/pin unchanged. See parent
docs/fixes/2026-11-04-fade-edge.md for scope (clip-disabled path unchanged).

## 04.11.2026 — latest PvP/join/NPC/prompt fixes installed PC + laptop17:53MSK

Supersedes SOURCE ONLY installation status for new repeated-join placement,
new-world relay/PvP stream reset and early personal NPC reward authority.
Related chats completed/read before build, including latest prompt-icon/mod
precedence fix. Parent4483863 / BBSC HEAD/gitlink0ddb1d4 plus recorded working
changes. DLL build exit0; full fast launcher/Party/package build exit0 with
BB_FAST_DEPLOY=1 SKIP_BUILD=1. Port16:30:58 reused after its source16:30:22;
source size/mtime snapshot unchanged. No new relevant active work at final barrier.
PC and laptop copy exit0,5148files each. Backups:
D:/Games/Bloodborne/coop-dev/backups/latest-pvp-join-20261104-175131 and
C:/Games/Bloodborne/coop-dev/backups/latest-pvp-join-20261104-175227.
Both normal launchers opened and responding: PC11992, laptop15776/session1.
User asked launcher launch only; no game started. Saves/settings/mods retained;
no stopped processes, commit/pin/push or game-data writes. No running legacy VPS
component or wire-format change in this scope; no VPS update required.
Build/deploy/launcher start confirmed; PvP/rewards/placement/prompt gameplay OPEN.
Record: parent out/coop-dev/runs/latest-pvp-join-20261104-1749/run.md.

## 04.11.2026 — host-only PvP / missing Blood Dregs, SOURCE FIXED / gameplay OPEN

Shared with the new repeat-join placement fix: DynamicEngine.apply now resets
outgoing relay stream/sequence when local world generation advances. Without it,
a new receiver receipt expects seq1 but host continues its old count. Negative
production-engine reproduction confirms guest PvP request still reaches host
while host confirmation stalls; restoring reset unblocks it. Three worlds with
persistent native TCP pass guest requests, host on/off state and kill claim/ACK
in both directions. Production dispatcher role/session checks, lethal finisher
callbacks and real award/replay/retry service PASS. Award fixture updated to use
the actual protocol header after its initial missing-include compile failure.
Last twin/test PC run shows host toggles17:31–17:33 and accepted guest request;
complete PC rotation preserved. Laptop raw prefix is partial; later completed
filter excluded PvP, so exact live stream counters/each missing reward remain
unproven. No product build/deploy/gameplay in this task; use the shared placement
DLL + Party changes together. No save/settings/game-data writes or process stop,
commit/pin/push. See fixes/2026-11-04-pvp-session-stream.md and parent
out/coop-dev/runs/pvp-20261104. Existing missing items are not auto-compensated.

## 04.11.2026 — NEW repeat-join placement regression, SOURCE FIXED / NOT DEPLOYED

Fresh twin/test PC+laptop run16:59/17:03MSK, separate from the older11:35
placement issue. Guest enters state6 at17:17:46 and17:26:55 but has no aimed
placement/host lock/join teleport;17:26 host is in Woods while guest loads
Cathedral Ward. Party NP JoinRoom precedes HTTP admission delivery and consumes
pending before placement flush; captured events have native joins without
admission_delivered. Deterministic production bridge fixture reproduces this.
NP JoinRoom now keeps its reservation until DLL acknowledges placement through
independent /party/tick (sign/create may never run); bounded8s, scoped owner,
generation/ticket/room checks. Native aimed handler accepts joining4 before
handoff, rejects established3/6. Dynamic receiver drops foreign/stale aimed frames.
Also reproduced outgoing relay seq carry across new local acquire generations:
receiver's new world receipt expectsseq1 but sender continues previous sequence,
stalling follow/PvP/world state too. DynamicEngine.apply now resets the stream
when generation advances, retaining native TCP. This is a protocol source defect;
exact live stream watermarks were not recorded, so do not assert each packet loss.
Targeted placement(3), fresh-world relay, existing relay/window/dedup and real
HTTP/NP host rotation PASS; production native handler/ack expiry/population JSON
PASS; actual MSVC-target syntax check of both changed native TUs exit0.
No DLL build/deploy/gameplay confirmation yet; related PvP chat active at barrier.
Logs/evidence: parent out/coop-dev/runs/join-new-20261104 and
fixes/2026-11-04-new-join-teleport.md. HEAD/gitlink0ddb1d4, other local edits retained.
No real save/settings/game-data writes, pin/commit/push or process termination.
DLL + party/compat.py + party/dynamic.py must be delivered together.

## 04.11.2026 — early NPC rewards: network authority and badge sharing, SOURCE FIXED

User reports early Crow Hunter Badge, Clawmark and potentially other items.
Personal death workers (including12410761 and Eileen12410803/12410804) were
already guest-enabled but excluded from local network execution. Host action
replay could bypass the guest's guarded death predicate; the existing talk-only
provenance policy deliberately did not cover death workers. Extractor now also
localizes existing pure personal workers and accepts native CLEAR of a single
known NPC quest family (including unused bits), never broad SET/unknown effects.
50 events vs16 before; original native conditions retained. Shared-key sender
and receiver now exclude NPC badges4111/4112/4116 (Crow/Powder Keg/Wheel), with
stable25-bit layout and rejection of old hosts' bits. Native reward paths retained.
Production localization fixture covers every personal worker before first condition
and later steps; production key tick covers sender, legacy receiver and reload;
quest prerequisite/native predicate/trampoline and original-data generators PASS.
Full BBSC_MOD translation-unit syntax PASS. No DLL build/deploy/gameplay, commit,
pin/push or real save/settings/game-data writes. Game running at check; no process
stopped. Existing wrong inventory/progress is not rolled back. Runtime origin of
the user's particular awards remains unrecorded; gameplay confirmation OPEN.
See fixes/2026-11-04-personal-reward-authority.md.

## 04.11.2026 — Alfred absent near Forbidden Woods entrance, INVESTIGATION / OPEN

User reports Alfred absent for host and guest after Amelia; skull activated.
Whether Cathedral Ward was reloaded after skull activation is not yet established.
Read-only original installed CUSA03173 EMEVD: m24_00 event12400590 checks
1340 +9801 at initialization, clears1340..1359 and sets1344. Its label4
shows entity2400763 (MSB position -112.756,-2.215,196.657), while label0
shows2400760 at62.508,-26.806,51.644. Branches end without waiting for a
new9801 value, so walking back without a map reload does not reevaluate this
placement. Original t240333 ESD confirms1340 quest branch. This is a possible
native load-timing explanation, NOT proof of live flag values or a mod defect.
Next: confirm full area reload after skull, then compare actual quest/story
flags if still absent. Do not force1344 or bypass death/hostility/quest states.
HEAD/gitlink0ddb1d4 with pre-existing working changes. No product edits,
build/deploy/gameplay confirmation, save/settings/game-data writes, commit/pin/push.

## 04.11.2026 — same-bell repeat join twin/test, INVESTIGATION / OPEN

User confirms: guest joined first Beckoning, left, could not rejoin while that same
bell still rang; host rang again and guest joined. Supersedes earlier localization
between invitation and signaling. Current16:24MSK PC /16:26 laptop run, main profiles.
Both logs now available: laptop retrieved read-only via strict SSH over Tailscale.
Client resumes sign create16:38:13, every~2s, bare52-byte responses. Host continues
search but receives only73-byte empty-list responses until16:40:27; then919-byte
candidate response and successful invitation. First admission16:29:42 returned211
bytes to client and signaling established16:29:43. Later absence of a new signaling
activation is NOT proof of failed rejoin (existing channel can be reused).
Failure localized to Party candidate availability/filtering during old bell, before
host invitation. Exact owner/finalized/pending/joined/sign gate remains unproven:
detailed Party diagnostics disabled. Do not call this a network failure or claim a
code fix. User confirms rejoin after new bell; log-only world arrival not asserted.
Evidence: parent out/coop-dev/runs/repeat-join-20261104/run.md, current-pc and
laptop-after; previous dialogue investigation laptop snapshots also inspected.
No product code/build/deploy/test, real save/settings/game-data writes, commit/pin/push.

## 04.11.2026 — latest PC/laptop dialogue persistence investigation, OPEN

Read-only collection over strict SSH to laptop Tailscale address, latest live
16:24/16:26 onward MSK run. Logs and copied mod journal in parent
out/coop-dev/runs/dialog-progress-20261104-1640 (initial and later snapshots).
Later live logs ChangedDuringCopy=true; detailed BBSC diagnostics disabled.
Laptop slot sd1/0 journal archive updated16:35:57, v2/39 flag entries;
pending archive updated16:35:40. Current source retires talk journal only after
matching final table/revision and native own-world save confirmation. This is
evidence that reconciliation completed for recorded entries, NOT proof every
conversation flag was captured or survived later activity. Old sd1/1 pending
and journal12:11:57 are a different character, not this run's failed transfer.
Journal includes72400300=1/72400310=1; no72410500..503 or72410382 entries.
Original read-only ESD identifies first pair in t240312/t240504,72410501 in
t241319,72410382 in t241316. Which NPC/step user observed is pending clarification;
no proven Tailscale transport or backup failure for this run. No code/build/deploy,
settings/save/game-data/live-journal mutations, commit/pin/push. HEAD/gitlink0ddb1d4
plus existing working changes. Logs alone cannot assign the exact defect.

## 04.11.2026 — death status reset and latest DLL fixes installed PC

15:19MSK DLL build/5-file delta preparation/PC copy exit0. Includes status cleanup,
search-expiry Dream session fix, original kit gift suppression and item descriptions.
Backup: D:/Games/Bloodborne/coop-dev/backups/death-status-20261104-151917.
No game launch, save/settings/game-data changes, commit/pin/push. Gameplay OPEN.
See HANDOFF and parent out/coop-dev/runs/death-status-deploy-20261104-1518/run.md.

## 04.11.2026 — co-op item descriptions revised, SOURCE ONLY

Russian item descriptions use «хозяин мира» instead of «хост». Removed Insight-cost
wording from short/full bell descriptions; Sinister Bell now describes enabling or
disabling PvP in the current session. English text/generators and compiled message
tables updated together. Generated Russian table/token test and eight English item
entries consistency PASS; diff check PASS. No build/deploy/game visual confirmation.

## 04.11.2026 — исходный подарок Зовущего колокола/Бланка скрыт, SOURCE FIXED

12101024 завершён до показа посланников и действия; все локальные роли.
Набор через Блокнот и остальные подарки сохранены. Целевые C++ проверки,
read-only EMEVD/лоты и полный синтаксис PASS. Сборки/установки/игрового
подтверждения нет. См. [отчёт](fixes/2026-11-04-native-kit-gift.md).

## 04.11.2026 — chalice → Dream after search expiry, SOURCE FIXED / gameplay OPEN

Passive search expiry no longer arms Blank cleanup or cancels established Party.
Explicit item/effect/menu cancellation retained. Production expiry→Dream native
regression, matchmaking, menu quit, follow/chalice and syntax checks PASS.
No build/deploy; in-game confirmation pending. Investigation below is historical.

Player2 host's300s search expiry at14:58:36 arms Blank cleanup; Dream arrival
14:59:22 briefly has self-only actor population and forces native Stop despite
3room members. Both guests return home; all3processes remain alive. Distinct
from previous Party retirement guard. Separate passive search expiry from explicit
cancel and protect load/session scope. At investigation: no product changes/build/deploy.
See fixes/2026-11-04-chalice-dream-search-end.md.

## 04.11.2026 — poison/death status reset, SOURCE FIXED / gameplay OPEN

Same-actor revive now removes native death-expiring saved/timed effects and calls
native five-gauge resistance reset, clears pending triggers/fractions. Preserves
original death-persistent categories3/6 and indefinite equipment/session effects;
unavailable cleanup uses real-load fallback. Production/native-code fixture,
rearm/boss-lamp/accounting/hotpaths and full syntax PASS. No build/deploy/restart.
See fixes/2026-11-04-poison-after-death.md. Gameplay still requires confirmation.

## 04.11.2026 — poison retained after death, initial investigation

User reports retained poison. Latest Player1 guest death14:55:22MSK uses native
death handlers, revived at host lamp without reload14:55:27, detectors rearmed.
Poison state is not logged; original status/buildup cleanup vs retained actor
revive needs tracing. Prior registration fixture is not status-effect coverage.
No product changes/build/deploy. See fixes/2026-11-04-poison-after-death.md.

## 04.11.2026 — Player3 repeat join inspected; latest attempt succeeds

14:39 three-profile run, same b4d7 Party group. Host Player2 received Player3
candidate at14:50:16 but no pending/native claim through room end14:53:06;
Player3 kept refreshing sign. Block localized before claim, exact gate OPEN.
New generation32 admitted Player3 at14:53:37; chalice load/teleport finished
14:53:49; native hunters3 at14:54:11. No manual recovery/code/build/deploy.
Live snapshots changed during collection. See fixes/2026-11-04-player3-connect.md;
parent out/coop-dev/runs/player3-connect-20261104-1455. Repeat-join stability OPEN.

## 04.11.2026 — latest fixes installed PC; three profiles launched14:39MSK

Supersedes earlier SOURCE ONLY installation status for root chalice Party API,
scripted pickups, boss-lamp revival, Small Bell session block, host Dream retirement
and item notification OK registration. Latest launcher home/VPN UI and mod sharing
included. Related chats read/completed in this checkout before build. Parent1987812,
BBSC HEAD/gitlink0ddb1d4 plus recorded working changes. DLL build exit0; full fast
launcher/package build exit0 (BB_FAST_DEPLOY=1 SKIP_BUILD=1); current native cursor
port reused. Source input size/mtime unchanged during build. PC copy exit0,5145files.
Backup: D:/Games/Bloodborne/coop-dev/backups/root-chalice-latest-20261104-143816.
User then requested launch: existing Player1/2/3 CMD scripts started three distinct
profiles; fresh game logs on all3, responding native PIDs6396/14548/15328. All3
windows are preparing shaders at startup snapshot. Start is not proof of connection
or chalice behavior. Existing profile diagnostic/one-hit settings retained; no manual
save/settings/journal/game-data changes, process termination, commit/pin/push.
Laptop not updated/launched; no VPS component/protocol change required. Gameplay OPEN.
Record: parent out/coop-dev/runs/root-chalice-latest-20261104-143534/run.md.

## 04.11.2026 — Player3 late restart after crash, INVESTIGATED / OPEN

Last13:40 three-profile run: Player3 GPU DeviceLost14:13:27MSK, exit23;
matching current nvlddmkm153 / WER141. Restart14:15 uses static Party group9166,
while original host remains in b4d7: sufficient control/admission blocker.
Same profile script/config argument; current config still b4d7. Origin of new
group NOT established; do not assume config rotation or stale membership.
Player2 also GPU-crashes14:17:31; host retires14:18:13. Four game logs incl.
rotation + three event streams captured in parent out/coop-dev/runs/
player3-rejoin-20261104. Two live copies changed during collection.
No product code/build/deploy/restart, real save/settings/live-journal changes,
commit/pin/push. See fixes/2026-11-04-player3-crash-rejoin.md. Recovery OPEN.

## 04.11.2026 — item notification OK registration, SOURCE ONLY

User clarifies client boss/key notification stays about10s without OK.
Native queue skips action11/param4400 on a character control bit. Popup-only
read substitution for living/loaded state6 + exact pending queue removes that
blocker, preserving original prompt/input/cleanup and all character flags.
Production callback + actual Windows trampoline/branch fixture PASS; native ELF
inspection and full C++ syntax PASS. Notebook producer fixture has unrelated
unchanged-from-HEAD five-item expectation FAIL. Last live bit was not captured:
additional native gates/gameplay timing remain OPEN. No build/deploy/restart,
commit/pin/push or real save/settings/game writes.
See fixes/2026-11-04-item-popup-confirm.md.

## 04.11.2026 — root chalices with Party, SOURCE ONLY / gameplay OPEN

Native channel HTTP API and persistent profile catalogue implemented; original uploaded
FormData is retained, fixed story descriptions remain separate.13 targeted Party tests,
native root mount/direct-summon/follow fixture and relay dispatch PASS; temporary bundle
import PASS. No build/install/gameplay or real save/settings changes. Next: original
root ritual in game, follow from Dream, late join inside, layers/wipe/return and rites.
Details: fixes/2026-11-04-root-chalice-feasibility.md.

Historical investigation before implementation:

Investigation: current Compatibility has no channel handlers; six relevant paths
return UnknownResponse. Existing host borrowed-loader bridge is a viable basis for
follow/direct joins, not proof of root/rites completeness. Trace original ritual
FormData flow, restore persistent channel API in Party, verify mount completeness,
ritual/layer identity and targeted gameplay. No implementation/build/deploy.
Details: fixes/2026-11-04-root-chalice-feasibility.md.

## 04.11.2026 — host Dream travel retirement regression, SOURCE ONLY

Latest three-PC run logs copied to parent out/coop-dev/runs/host-dream-20261104.
At13:58:02MSK LocalPlayer1 emits host_empty generation27/revision262; all three
replicas clear owner/room, although its preceding roster still contains Player3.
Native gameplay markers absent; the exact teleport phase is not recorded. Live
log copies changed during collection; not a final stopped-run capture.
Reproduced premature terminal certificate from a transient self-only/no-bell
observation in an isolated three-process fixture using the previous decision.
Automatic retirement now requires3s continuous fresh terminal evidence; load,
death, population restoration and stale/gapped frames reset confirmation. Native
loading includes pending construction/reload-finish and the mod curtain.
No build/deploy/gameplay, commit/pin/push, save/settings or game-file changes.
See fixes/2026-11-04-host-dream-retirement.md. Gameplay confirmation OPEN.

## 04.11.2026 — Ritual Blood and scripted personal pickups, SOURCE ONLY

Original m23 event12300130 blocks guests before its glint/action. Reviewed11
native pickups (10 new fixes plus existing Crown); host-type permission, exact
EndIfClient memory patch, local event sync and personal completion/checkpoint
flags. Native local completion writes use the existing trip journal; Eye Pendant
receipt9470 requires actual matching delivery. Original availability retained.
All16 action-award definitions surveyed. Gold Ardeo12700902 and Laurence
skull13501141 remain OPEN: separate NPC/world side effects, not auto-enabled.
Production pickup/three-person masks/localization, original-data survey, Crown,
personal journal, quest prerequisite/native fixtures and shared policy PASS;
full BBSC_MOD syntax and diff check PASS. No DLL build/deploy/gameplay,
commit/pin/push or real save/settings/game writes. Gameplay OPEN.
Details: fixes/2026-11-04-scripted-pickups.md.

## 04.11.2026 — post-boss revive at that boss lamp, SOURCE ONLY

Dead host/guests now select the defeated encounter's lamp before the old lamp or
partner, even if the new lamp is unlit.19 own-lamp bosses plus phase variants;
map/load/kill guards, unknown/chalice fallback. Targeted production fixtures and
full C++ syntax PASS. No build/deploy; gameplay OPEN.
See fixes/2026-11-04-boss-lamp-respawn.md.

## 04.11.2026 — Small Resonant Bell session lock, SOURCE ONLY

Host/joining/guest/invader native states3/4/6/7 deny Small Bell availability and
both execution entries (205/legacy4121). Own world retains existing availability;
other bells/Blank unaffected. Three targeted production fixtures PASS.
No build/deploy; gameplay OPEN. See fixes/2026-11-04-small-bell-session.md.

## 04.11.2026 — current fixes built/installed; three PC profiles launched13:40MSK

Supersedes SOURCE ONLY deployment status below for native world retirement,
repeat-death native handlers, guest aura and recipient crash isolation. Related
chats read and complete, including launcher mod sharing and VPN settings.
DLL build exit0; fast package build exit0. New VPN work began during first build;
waited for completion and rebuilt only launcher/package, retaining unchanged DLL.
Source size/mtime unchanged during final rebuild. Native port reused; no VPS
component/protocol update needed. Parent HEAD1987812, BBSC HEAD/gitlink0ddb1d4
plus recorded local changes; no commit/pin/push.

PC deploy exit0, copied5147; backup:
D:/Games/Bloodborne/coop-dev/backups/native-retirement-20261104-133925.
Existing Player1/2/3 CMD scripts started distinct profiles/ports3658/3659/3660;
three native windows present/responding (PID32276/31192/27620), fresh13:40 logs.
Existing60FPS/no-DLSS settings retained. Party-only process diagnostics enabled
for this test; parent environment restored. No manual save/settings/live-journal
edits, game-data changes or process termination. Laptop not updated/launched.
Gameplay recovery, native death reset and guest appearance remain OPEN.
Record: parent out/coop-dev/runs/native-retirement-deploy-20261104-1328/run.md.

## 04.11.2026 — automatic native world retirement, SOURCE ONLY

Host ownership retires when native membership is self-only and Beckoning off,
or on confirmed loss of hosting role. Ready/alive/fresh native evidence required.
Guest host-crash recovery requires native teardown plus lost host control link.
Static durable terminal certificates supersede stuck consensus and fence old
messages; dynamic exact-reservation detach rejects late reattachment. New static
acquire still requires its fixed roster. Targeted processes/native fixtures and
full changed C++ syntax PASS. Legacy menu wrapper has duplicate-stub FAIL; current
menu fixture PASS. No build/deploy/restart, real save/settings/live-journal edits,
commit/pin/push. Gameplay OPEN. See fixes/2026-11-04-native-world-retirement.md.

## 04.11.2026 — Player1 Beckoning blocked after peer crash, investigated

Read-only three-profile log/journal snapshot: finalized revision253 retains
owner LocalPlayer3, closing room and joined crashed LocalPlayer2. LocalPlayer1
already left joined/pending/members. Installed static Party availability still
requires owner None/self, so Player1 bell remains denied after its own leave.
This is a group ownership/drain limitation, not stale Player1 membership.
No recovery, code/build/deploy, process/save/settings/live-journal changes.
Gameplay recovery OPEN. See fixes/2026-11-04-player1-beckoning-blocked.md.

## 04.11.2026 — guest appearance, SOURCE ONLY

Persistent blue summon loop removed via SpEffectVfx272 (211 -> -1); home bell
and summon-transition effects preserved. Production targeted fixture PASS.
No DLL build/deploy; host/client visual confirmation OPEN.
See fixes/2026-11-04-guest-aura.md.

## 04.11.2026 — native repeated death source fix; gameplay OPEN

Latest guest repeat still lacks text and retains status effects. User requires
original handler for every death. Replace synthetic text/HP handoff with native
death-detector rearm after retained revive; native dispatcher owns each death.
Original native guest wait already raises YOU DIED. Targeted production/ELF checks
and full BBSC_MOD syntax PASS; no build/deploy/restart or real save/settings edits.
Need gameplay confirmation of native text/status cleanup on successive deaths.
See fixes/2026-11-04-native-repeat-death.md; prior text-only workaround superseded.

## 04.11.2026 — guest crash cascades to healthy guest: source correction, OPEN gameplay

Three-profile run: host3; Player2 GPU reset12:50:52/exit23; Player1 sent home.
Reproduced global relay failure after dead recipient's144 queued frames.
Static/dynamic per-peer backlog/expiry/socket-queue failures now fence only that
stream; healthy recipients keep their ordered relay and native socket.
Four targeted regressions + four direct dependencies PASS, old source FAIL.
No build/deploy while Player1/3 run. Exact in-game relay/native-DEAD branch is
unproven with release diagnostics off. See fixes/2026-11-04-guest-crash-isolation.md.

## 04.11.2026 — progress/repeat-death DLL installed PC + laptop

DLL build and five-file delta deployment exit0 on both devices. Supersedes the
source-only installation statuses below; three PC profiles launched at12:29MSK
using existing local-party entrypoint. No manual save/settings/journal changes.
Gameplay confirmation still OPEN; native accounting cause remains unproven.
See HANDOFF and parent out/coop-dev/runs/pending-progress-deploy-20261104-1228/run.md.

## 04.11.2026 — repeat death effect corrected, SOURCE ONLY; accounting still OPEN

Supersedes the earlier read-only investigation status below. User clarifies two
non-boss deaths; second had only quick fade, no YOU DIED/echo loss/restock.
Repeat lifecycle no longer treats rejected text as accepted or starts respawn on
the same tick: bounded text retry + 3s accepted effect window, 15s fallback retained.
Native boolean text arg masked like SoloPlayDeath. Actual native no-op drop now
returns false/logs warning; unavailable/failed restock also logs warning.
Repeat, death-hotpaths and new production accounting fixtures PASS, including two
consecutive penalty/restock cycles and native refusal. Live accounting cause is
UNPROVEN; warnings are diagnostics, not a fix for gate=0/unavailable storage.
No build/deploy/gameplay, commit/pin/push or real save/settings changes.
Details: fixes/2026-11-04-repeat-client-death.md.

## 04.11.2026 — pending shared progress: source fix, gameplay OPEN

Pre-merge backup ignored BB_USER_DIR although slot detection uses it. Corrected
live-root selection; old-source failure reproduced with artificial files, corrected
production backup+boss/lamp merge PASS. Personal commit/shared-policy and full
BBSC_MOD syntax checks PASS. No build/deploy or real save/journal edits. Need game
confirmation that returned guest completes native home-save and retires pending.
See fixes/2026-11-04-pending-progress-backup.md; latest release logs do not record
the exact runtime branch. This does not close the separate repeat-death issue.

## 04.11.2026 — repeat client death, latest 12:01–12:12 run investigated

User reports second client death was not handled. Fresh PC D:/Games/Bloodborne/twin
and laptop C:/Games/Bloodborne/test logs collected (one each, warnings=0).
Signaling established 12:03:38, both processes exit0. Gameplay death/HP/spectate
markers absent with diagnostics off; exact cause UNPROVEN, bug OPEN.
Production lifecycle fixture test_repeat_death PASS, but stubs death entry/HP and
cannot confirm the full game cycle. No code/build/deploy/settings/save changes.
Details: fixes/2026-11-04-repeat-client-death.md. Next evidence requires diagnostic
first + second death on both devices; do not treat fixture success as game success.

## 04.11.2026 — initial placement fix built and installed PC + laptop

Supersedes SOURCE ONLY for the join-placement ordering fix below. Related chats
read and finished; personal lamp travel cancelled by user and archived/reverted
before build. BBSC HEAD/gitlink0ddb1d4, parent1987812 plus recorded local changes.
DLL build exit0; input size/mtime unchanged during build. Six-file DLL + Party
compat delta prepared and installed on both devices, copying exit0 on each.
Existing current launcher/UI, FPS, cursor and Diamond Sword already installed on
both devices by the earlier common deployment; native port/launcher reused.
Backups:
- PC: D:/Games/Bloodborne/coop-dev/backups/join-placement-20261104-115959
- Laptop: C:/Games/Bloodborne/coop-dev/backups/join-placement-20261104-120028
No game launch, repeat suites, file audit, commit/pin/push, real save/settings or
game-data edits. Laptop script used process-only ExecutionPolicy Bypass after
its default script restriction; no persistent policy changed. Gameplay OPEN.
Run: parent out/coop-dev/runs/join-fix-deploy-20261104/run.md.

## 04.11.2026 — initial late-join placement ordering, SOURCE ONLY

Aimed host placement was emitted before dynamic admission and lost outside the
world roster. Deferred target-specific delivery + native placement acknowledgment
implemented;2 real HTTP/relay cases,2 dynamic dependencies and native HTTP fixture
PASS. Needs common bridge/DLL build and deployment on both participants after
related guest-lamp work; initial arrival in game still OPEN. No save/settings edits.
See fixes/2026-11-04-join-placement-order.md.

## 04.11.2026 — late joining built and installed PC + laptop

Supersedes SOURCE ONLY deployment status below. All related chats completed before
build (late joining, sword integration, cursor, FPS, Player1 menu, cleanup).
Launcher package.sh BB_FAST_DEPLOY=1/SKIP_BUILD=1 exit0; current native cursor port
and BBSC DLL reused. Frozen launcher smoke loaded dynamic-worlds-v1, discovery2
and acquired an isolated temporary world successfully. Source input metadata
unchanged during build. Build contents/run status: parent
out/coop-dev/runs/late-join-pc-laptop-20261104-112427/run.md.
Parent HEAD1987812, BBSC HEAD/gitlink0ddb1d4, with recorded local source changes;
no commit, pin update or push performed by this build/deploy task.

PC deploy exit0, copied5143; laptop deploy exit0, copied5146 (metadata selection,
no file/hash audit). Backups:
- D:/Games/Bloodborne/coop-dev/backups/late-join-20261104-112904
- C:/Games/Bloodborne/coop-dev/backups/late-join-20261104-112932

Updated Diamond Sword already installed on PC by its authoring chat; copied its
current asset package to laptop mods/Diamond Sword. Laptop existing mods_enabled
and default new-mod selection enable it without editing settings/mod profiles.
Both launchers opened in interactive sessions (PC2 / laptop1), visible/responding
confirmed. Laptop direct task attempt did not confirm a window; recovered with
an interactive hidden helper, confirmed visible UI, removed our one-shot tasks.
Fresh automatic discovery on both devices lists twin and test. This confirms
launcher presence, not native room join/world arrival or any gameplay fix.
No game launched by this task. Real settings/saves/journals unchanged.
Late-join gameplay and native menu-exit confirmation remain OPEN.

## 04.11.2026 — late joining implemented, SOURCE ONLY

Regular launcher co-op now uses per-player durable home sessions and live peer
lookup (discovery BBGL-P2P-2). A player may start alone; a host can reserve a guest
whose launcher/game starts later, without rebuilding a roster or restarting either
game. Discovery feeds a live directory, never a voting list. Bells keep their roles.
DynamicEngine uses one durable writer/authority per hosted world. Admission first
persists a provisional guest binding, then commits on the host; only a confirmed
host snapshot exposes a native admission. Competing hosts/guest acquire serialize
at the guest. Separate unbound players may host independent worlds. Explicit
native leave/cancel is still required; partitions never promote or release guests.
Guest identity/login and NP/HTTP/relay sockets survive attaching/detaching. Native
room IDs are random63-bit, fencing callbacks across independent hosts. Relay keeps
16 outstanding frames/peer, ordered buffering, bounded queues and durable receipts.
Legacy static/local-three invitations retain their unanimous Engine path.

Checks:14 new real-socket/crash/race/native integration tests PASS;8 launcher
connection tests and3 explicit-firewall tests PASS;4 targeted legacy NP/RPC tests
PASS. All data/profiles temporary; no game launched, no product build, installation,
settings/save changes, pin update or push. Gameplay remains UNCONFIRMED.
All participants need the new runtime/discovery version for a later game test.
Details: docs/fixes/2026-11-04-late-join.md (BBSC tree).

## 04.11.2026 — Player 1 menu fix installed on this PC

BBSC d893098 built successfully (exit0); six-file delta installed (copy exit0)
into D:/Games/Bloodborne/Bloodborne Game Launcher, including coop/party/compat.py.
Backup: D:/Games/Bloodborne/coop-dev/backups/player1-menu-fix-20261104-095340.
No game launch, real saves/settings/journals unchanged. Gameplay confirmation
remains OPEN; do not equate native fixture PASS with title arrival in game.
Source diagnosis and checks follow below.

## 04.11.2026 — Player 1 menu exit corrected; build pending

Latest Player 1 run09:43-09:45MSK, native PID9008 exit0, diagnostics off.
Read-only Party journal retains ownerLocalPlayer3 and joinedLocalPlayer1 at rev239.
Title unload incorrectly required unanimous shared leave, blocking an isolated
player with stale membership. Current title ticket now permits LOCAL unload only
after fresh native idle/not-loading observation and explicit cancel. Ownership,
room/journal, consensus and Beckoning gates remain unchanged; no forced release.
Native StageFlow01940DBB..01940E14 requires System MenuMan+250 to set task+150;
request2 alone omits it. Restore +250 after CloseMenus, after save and Stop,
without replaying save latches or invoking StageTransition. Earlier claim that
+250 itself was necessarily a world reload was incomplete and is superseded.
Production quit, actual native branch on fake memory, offline-peer RPC and real
WinHTTP tests PASS. No real saves/settings/journals changed. Gameplay pending.
Details: fixes/2026-11-04-player1-menu-exit.md.

## 04.11.2026 — installed on this PC; gameplay still pending

Supersedes the source-only build/deploy status in older entries below.
BBSC 7b464e0 and BBGL ec0ec22: cleanup/localization committed, DLL and launcher
package built and installed on this PC; build/copy exit=0. No push, no game launch.
Install: D:/Games/Bloodborne/Bloodborne Game Launcher.
Backup: D:/Games/Bloodborne/coop-dev/backups/localization-cleanup-20261104-031341.
Fast package: BB_FAST_DEPLOY=1 SKIP_BUILD=1; native port reused.
Quest/name/claim changes are included, but second guest admission, host menu exit
and live localization bounds remain unconfirmed. Do not close these by build alone.
Local Party WinError 5 replacing status JSON remains OPEN; exact cause unknown.
Menu test still expects obsolete ROW_RESTART; separate from localization success.
Details: [parent handoff](../../../docs/P2P-HANDOFF.md) and
[localization review](../../../docs/fixes/2026-11-04-localization-review.md).

## 04.11.2026 — architecture/test cleanup, no product build

Reviewed main entrypoints/build dependencies and catalogued229 test/support files.
Removed unreachable launcher helpers, orphan QML and obsolete experiment launcher
setup; adapted network/UI/version tests to Party. Legacy save/profile contracts
retained with explicit skips. Targeted checks:48 PASS,1 FAIL,1 skipped.
Local-three lifetime fixture hit WinError5 replacing exit-status JSON; worker
failed and coordinator timed out. Retained as OPEN, exact file-lock cause unknown.
No game/save/settings/deploy/pin changes; second guest and host exit still OPEN.
See [audit](../../../docs/fixes/2026-11-04-full-project-audit.md) and parent docs/TEST-CATALOG.md.

## 04.11.2026 — quest reward prerequisites corrected; gameplay pending

Shared NPC death could advance a guest's separate personal quest before its
actor was eligible. Original native predicate accepts fake dead actor in1240;
production guard/trampoline now rejects it and retains1246/1245/native outcomes.
Generated ordered/parameter-resolved gates cover28 NPC actors and24 receipt/source
links; death worker, automatic drop, force treasure, native visibility and award
paths guarded. Missing personal phase flags completed. White ribbon/chest hide
regressions, native gate/trampoline and full BBSC_MOD syntax PASS; generators
check against original data. No product build/deploy/gameplay or save rollback.
Old run's exact chronology remains unrecorded (diagnostics off); replicated-state
mismatch is reproduced in isolated native fixture, not claimed as a live retest.
See fixes/2026-11-04-quest-reward-prerequisites.md; it supersedes the earlier
source-only audit as implementation status. Host menu-exit issue remains OPEN.

## 04.11.2026 — Clawmark source audit; guest-only origin still possible

User clarifies host had also been guest: both observations do not prove a host
award path. Correct window source: entity2410781/NPC109100 -> lot29010,
GemGen100502/flag50001300.12410761 guest-enabled death event sets1245;
12410760 force-drops the NPC treasure in1245 branch. Own-NPC protection covers
1240..1245 but omits transformed phase1246 (confirmed coverage gap). Guest
native death delivery has no separate quest-phase check; native caller is trusted.
White-ribbon old blanket-enable bug is already absent; adding12410760 to local
allowlist is not established as sufficient. Data/source assertions PASS, no
runtime cause proven and no production changes/build/deploy/save changes.
See fixes/2026-11-04-early-rune-host-exit-review.md (latest section supersedes
prior role inference and name-only NPC candidates).

## 04.11.2026 — early rune / host exit report reviewed, OPEN

Main PC00:30–00:56 co-op log has diagnostics off; preceding rotated file is
startup WinError32. Separate D:/Games/Bloodborne/twin run ends00:58. No item gate
or clinic coordinates captured. Older local23:23/23:43 Player2 traces show title
requests followed by own-world character construction, already WITHOUT extra
StageTransition; cannot prove Continue vs automatic load. User reports automatic
clinic spawn, so exit remains OPEN. User confirms early Clawmark visible to BOTH host and guest; actual lot/source unrecorded;
current guest item pass already preserves native disabled availability.
Read-only review; no save/settings/code/build/deploy changes. See
fixes/2026-11-04-early-rune-host-exit-review.md; parent run
out/coop-dev/runs/early-rune-host-exit-review-20261104.

## 04.11.2026 — chosen player names restored at native Party boundary

Latest laptop log00:42–43 shows technical P94a/P3f66 handles; PC coop_name=twin,
user confirms ID displayed in game. Launcher config dropped discovery name.
Now config preserves name; native login/room/lookup/signaling/user-info/events/
STUN use chosen name, translated to stable IDs internally. Account/game UserId,
journals/group remain stable. Duplicate/invalid names rejected before startup;
legacy nameless configs retain ID handles. Source only; no deployment/gameplay.
Named two-process native contract + legacy contract,6 discovery and7 local/start
checks PASS. Evidence: parent out/coop-dev/runs/player-name-review-20261104/review.md.
Preserve prior bounded claim recheck in compat.py when packaging.

## 04.11.2026 — bounded claim confirmation recheck in source

Compatibility.command now waits on the SAME claim sequence once more after its
first8s confirmation timeout, before returning HTTP409/native retry cooldown.
No second Engine.request, no replay of consuming POST, no retry of ValueError or
other operations; total confirmation budget16s. Does not fix underlying missing
confirmation or accelerate cases where confirmation remains absent beyond16s.
Actual two-process HTTP test blocks peer until9s: request succeeds, revision+1,
one pending guest. Two limit/rejection tests PASS. Gameplay/deploy pending;
installed/running PC+laptop unchanged. Files: party/compat.py, party/test_rpc.py.

## 04.11.2026 — slow connection review, running PC + laptop

Laptop first summon request00:35:15.372 -> HTTP409 at00:35:23.388 (8.016s).
Retry00:36:04.268 ->200 in0.540s; native ESTABLISHED in0.949s afterward.
Main observed delay is failed admission +48.896s request retry gap;8s matches
Party confirmation deadline, but exact409 reason/absent confirmation unproven.
PC revision6 snapshot has guest joined/pending empty; world arrival not established.
PC release diagnostics absent; laptop HTTP trace available, Party events absent.
Read-only snapshots while games active; no settings/save/code/deploy changes.
Evidence: parent out/coop-dev/runs/slow-connect-review-20261104-003746/review.md.

## 04.11.2026 — log ownership WinError32 hotfix installed on both devices

Both new launcher runs failed before native startup: the launcher owns last_run.log,
while Party tried a second rotation. run.py/party/run_log.py now inherit the launcher
pipe (single writer) and preserve standalone rotation. stdout/stderr/exit footer
share the pipe; failed logging setup closes Party. Regression with real locked
Windows log and actual subprocess/runner launch statements PASS; direct rotation
and no-secret checks PASS. Two-file delta copied with launchers stopped, backups
in each coop-dev/backups/log-owner-fix-20261104-002858 (PC) / -002917 (laptop).
Launchers reopened PID2548/PID13700, visible/responding; gameplay retry pending.
No settings/save/native/protocol changes. Full ZIP not regenerated; staging updated.
Evidence: parent out/coop-dev/runs/log-owner-fix-20261104-002858.

## 04.11.2026 — current package installed PC + laptop; Tailscale launchers open

Full BB_FAST_DEPLOY package build exit0; changed source inputs stable during build.
Includes release logging defaults, sequential admission rollback and latest notices.
PC copy5145 / laptop copy5152 exit0; backups under each device coop-dev/backups/
tailscale-release-20261104-20261104-001814 (PC) and -002212 (laptop).
Main profiles keep original saves: PC twin; laptop C:/Games/Bloodborne/test.
Selected Tailscale (PC100.126.220.38 / laptop100.86.230.51), opposite peer hint,
coop mode and diagnostics off; settings backed up in each existing profile.
Both launcher windows confirmed Responding=True in interactive session1:
PC PID10808; laptop PID14880 at00:23:16MSK. Laptop one-shot task exit0, removed.
No game started; gameplay connection not claimed. No VPS component required for
embedded Party/Tailscale. Run record: parent out/coop-dev/runs/tailscale-release-20261104-001336.

## 04.11.2026 — release logging is opt-in for diagnostics

GPU/network default Error; BBSC DLL filters before fmt (default Error). DLL,
GPU/network and optional timeline share native stderr/last_run.log, without
separate automatic text files. BB_DIAGNOSTICS=1 (launcher diagnostic_logs toggle)
enables verbose logs, timeline, packet samples/attempt tracing and PERF/PACING;
individual switches remain available. Party event JSONL and search diagnostics
are also opt-in. Functional exchange reply and StopRequest hooks remain active.
No save/protocol changes. Targeted GPU/DLL/native UDP/relay/policy/party tests PASS;
DLL build exit0, changed GPU source objects compiled. No deployment/gameplay run.
See ../../../docs/LOGGING.md (parent repo); detailed limits there.

## 03.11.2026 — user-requested sequential admission restored in source

Removed overlap readiness override and candidate consumption/retry experiment.
Native sequencing restored; preserved current-login identity, exact resident
completion, role cooldown guard and confirmed Blank release/notice changes.
Cooldown + resident-completion native regressions PASS. Experimental source/tests
archived outside active tree. Source only: installed DLL still23:41:30.
See fixes/2026-11-03-restore-sequential-admission.md.

## 03.11.2026 — 23:43 run FAIL: second guest still receives no claim

Latest DLL23:41:30 present in all3. P2host/P1guest/P3waiting, then
P3host/P1guest/P2waiting. Second sign reaches each host; no second admission,
no three-actor world. First request drains in both rounds; overlap hook runs.
No new native-rejection retry diagnostic; exact blocking path remains unknown.
Candidate transaction fixture PASS is not gameplay success. All3 native exit0;
launchers remain. Stable9-file review: parent out/coop-dev/runs/candidate-2343-review.
See fixes/2026-11-03-candidate-run-2343.md. Analysis only, no deployment.

## 03.11.2026 — candidate transaction DLL installed; three launching23:42

DLL build exit0;992 source inputs unchanged. Five-file delta copy0; backup
D:/Games/Bloodborne/coop-dev/backups/candidate-transaction-20261103-20261103-234222.
Coordinator960 launched23:42:29MSK. Three targeted native fixtures PASS;
actual simultaneous guest admission still needs gameplay confirmation.
See fixes/2026-11-03-candidate-transaction.md. No protocol/VPS/save changes.

## 03.11.2026 — candidate consumption transaction; build pending

Second candidate can be consumed before prepared data exists or native builder
accepts it. Matched hook now defers state1 until successful native return, before
QueueInsert. Null preparation/mode0 refusal retain eligibility; native blacklist
and mode1 destruction remain final. Keeps original capacities/guards and existing
overlap readiness;250ms bounded retries. Native scan->control-refusal->return
fixture reproduces baseline permanent loss and patched once-only queueing.
Overlap/cooldown direct regressions PASS. See fixes/2026-11-03-candidate-transaction.md.
Previous run's exact refusing predicate was not logged; this is a proven native
failure mode, gameplay confirmation remains pending. No protocol/VPS/save edits.
Parent out/coop-dev/runs/candidate-transaction-20261103.

## 03.11.2026 — 23:23 run: second sign unclaimed; silence rotation confirmed

P1host/P2guest/P3 waiting; then P3host/P1guest/P2 waiting. In both rounds,
second sign reaches host but no claim is created, even after first native request
completes (queue0/readyffffffff). Overlap hook executes; simultaneous3 not fixed.
P1 confirmed silence23:25:39.396 releases owner23:25:40.267; P3 stop notice
23:25:40.668, new host23:25:51.940. All3 exit0; stable logs collected.
See fixes/2026-11-03-second-sign-run-2323.md. Review only, no build/deploy.

## 03.11.2026 — confirmed Blank silence installed; three-profile launch23:23

Fixed missed native confirmed menu action302110: exact store01BC6BE7 now latches
silence to game tick, erases9000 and cancels ownership after existing native drain.
Old23:05 evidence: room gone23:07:17, owner retained until title23:09:03.
Added explicit finalized-release notice; exact Russian strings approved by user,
no ellipsis. See fixes/2026-11-03-confirmed-bell-silence.md.
Targeted native/trampoline/banner/WinHTTP/three-process tests PASS. Build exit0;
1017 inputs unchanged. Six-file delta (DLL + local compat.py), backup
D:/Games/Bloodborne/coop-dev/backups/blank-silence-20261103-20261103-232257.
Coordinator27320 launched23:23:08MSK; gameplay confirmation pending.
No VPS/shared protocol/save changes. Parent out/coop-dev/runs/blank-silence-20261103.

## 03.11.2026 — overlapping-admission DLL installed; three started23:05

Build23:03:22 exit0;912 inputs unchanged. Five-file delta copy0; backup
D:/Games/Bloodborne/coop-dev/backups/overlapping-admission-20261103-20261103-230426.
Coordinator29160 started23:04:32MSK. Fresh logs23:05:00–01 confirm new DLL
for P1native10332, P2native26776, P3native31624. Gameplay overlap pending.
Three native regression fixtures PASS. Command submission remains serialized
while owned; guest insertion/loading no longer by itself blocks next candidate.
See fixes/2026-11-03-overlapping-admissions.md; parent run
out/coop-dev/runs/overlapping-admission-20261103. No protocol/VPS/save changes.

## 03.11.2026 — overlapping admission selection implemented; gameplay pending

User requests independent simultaneous guest connection/loading. Existing scan
hook now restores only eligible cooperator readiness while prior insertion is
unfinished, once native dispatcher/result and broker command are idle. Keeps
per-guest request IDs/reservations, identity-bound completion and original
builder total/role caps; no queue resets or fabricated accept/arrival. Checks
capacity before candidate consumption; original role delay mask remains.
Native command buffer is still serialized; guest loading need not be.
Exact-native scan/trampoline regression plus cooldown and completion PASS.
See fixes/2026-11-03-overlapping-admissions.md. Parent run
out/coop-dev/runs/overlapping-admission-20261103; DLL build in progress.
Prior22:52 success confirms sequential admissions only, not this new overlap.

## 03.11.2026 — 22:52 run PASS: second guest joins while first stays

Current-login refresh observed for all3. P3host/P2first/P1second. Host native
completion queued1->0 at22:54:42.200 and22:54:59.242. All3 clients report3
actors22:54:59; no first-guest departure required. Remain together until P1
explicit menu confirmation22:55:15.560 (~16s). P2 stays afterward, later menu
exit22:55:33; host22:55:47. All3 runners exit0, no native negotiation failures.
Final collection9files/0warnings/stable: parent
out/coop-dev/runs/login-identity-2252-review/final-pc. Initial pc superseded.
Second-guest admission is gameplay-confirmed for this local3 run; long-session,
remote-network/rejoin/host-rotation coverage not implied. See
fixes/2026-11-03-three-guests-run-2252.md. Analysis only, no code/deploy/save edits.

## 03.11.2026 — current-login identity correction installed; three started22:52

DLL build22:51:30 exit0;912 inputs unchanged. Delta copy0, backup
D:/Games/Bloodborne/coop-dev/backups/login-identity-20261103-20261103-225219.
Coordinator28972 started22:52:24MSK. Fresh mod logs22:52:54–56 confirm
P1native28944, P2native28636, P3native28852 all load new DLL. Startup only;
second-guest simultaneous residency still requires gameplay confirmation.
Prior22:43 run has0 native negotiation failures but confirmed legacy user-ID
mismatch; report fixes/2026-11-03-current-login-identity.md. Parent run
out/coop-dev/runs/login-identity-20261103. No direct save/protocol/VPS changes.

## 03.11.2026 — second guest root identified: legacy replicated user vs current login

22:43 run fails again. Exact host log: P2resident4215/request520383427;
P3resident1704/request830650577, role7 and character sentinel match. Queue1
blocks until resident leaves. Native01C43DE0 only refreshes negative user IDs;
positive legacy identity survives character loading after login. Add game-thread
local slot identity refresh from current ServerInfo+60 before party/bell work;
never modify remote slots or relax identity checks. Exact-native completion
fixture reproduces failure, then succeeds after local refresh/replication;
invalid IDs/writeability/quit/replaced-slot cases PASS. DLL build in progress.
See fixes/2026-11-03-current-login-identity.md. Gameplay remains pending.

## 03.11.2026 — admission corrections installed; three games started22:43

Final DLL build22:41:37 exit0;912 recorded inputs unchanged. Five-file delta
copied successfully; backup D:/Games/Bloodborne/coop-dev/backups/admission-exchange-20261103-20261103-224253.
Coordinator32036 started22:43:01MSK; fresh logs22:43:28 confirm P1native1132,
P2native28564, P3native31932 load new DLL and exchange hook installed=true.
Gameplay still pending: test second guest while first remains at host.
No claim that all admission failures are solved; old mismatch was ambiguous.
See fixes/2026-11-03-admission-exchange-audit.md and parent run
out/coop-dev/runs/admission-exchange-20261103. No protocol/VPS/save changes.

## 03.11.2026 — admission exchange/role audit; fresh build pending gameplay

22:20 failure traced across both endpoints: all13 host->guest and9 guest->host
native vport40 datagrams delivered by matching hashes; P3 never dispatches
initial version, P1 receives it. Add one native version/profile reply after
first valid peer version (+88/+89), native+90 duplicate fence; no forced
ready/accept or deadline change. Remove resident-vs-request role equality
absent from native1877D00; full user/character and insertion/actor guards stay.
Old logs cannot prove role rather than identity mismatch; new throttled log
separates both and captures paired identities/roles. Exact-native completion
and full exchange callback/trampoline tests PASS. Still no live3-player proof.
See fixes/2026-11-03-admission-exchange-audit.md; parent run
out/coop-dev/runs/admission-exchange-20261103. DLL-only, no protocol/VPS/saves.

## 03.11.2026 — 22:20 run FAILED second-guest admission; identity guard isolated

P1 hosts; P2 joins22:22:46 and is resident22:22:59/23:00. P3 sign remains
available but no second claim/JoinRoom before P2 menu exit22:23:44. Never3 actors.
Host completed-task/actor/slot checks pass; cleanup repeatedly stops at
`queued role or identity mismatch`22:23:01–42, queued1/ready0. Thus87a1186 is
not gameplay-confirmed; its HP correction is insufficient. Which of queued
role/user/character differs is not distinguished. Earlier P3 claim22:21:48
never became JoinRoom and expired20s later, a separate initial-admission issue.
All3 runners exit0; final-pc collection9 files/warnings0/all stable. Party
events in pc; first snapshot had3 changed records, superseded by final-pc.
Parent out/coop-dev/runs/resident-slot-completion-20261103-review/pc;
fixes/2026-11-03-second-guest-run-2220.md. No code/build/deploy/save changes.
Supersedes previous gameplay-pending status; second-guest bug remains open.

## 03.11.2026 — resident slot/HP correction installed; local three started22:20

87a1186 DLL build exit0;1040 recorded build inputs unchanged. Native inputs
unchanged since preceding delivery; related chats finished. Five-file delta
copy0 with backup D:/Games/Bloodborne/coop-dev/backups/resident-slot-completion-20261103-20261103-221929.
Coordinator31116 launched22:19:29MSK; current local-three group and profiles.
Fresh mod logs22:20:06/07 confirm P1 native31464, P2 native9340, P3 native10172,
DLL build22:18:18. No VPS/protocol/save/settings changes. Startup confirmed;
second-guest gameplay remains pending. Keep first guest present while admitting
second. See fixes/2026-11-03-resident-completion-slot-hp.md and parent run
out/coop-dev/runs/resident-slot-completion-20261103. Source/build-pending entry
below is historical; last18:08 failure still not retroactively explained.

## 03.11.2026 — resident admission completion corrected for zero remote HP

87a1186 removes remote HP as a predicate for completing an already arrived6/6
identity-matched cooperator; host/load/leave/role/member/full request identity
fences remain. Resolves native remote PlayerGameData by insertion slot0..3;
adds throttled pending-reason diagnostics. Exact-native fixture reproduces old
failure for arrived zero-HP actor, corrected PASS; loading zero-HP task and
foreign identities remain rejected. Four slots/missing table checks PASS;
full game TU syntax exit0. Exact guard from18:08 logs remains unproven.
Build/deploy/three-player confirmation pending. See
fixes/2026-11-03-resident-completion-slot-hp.md. Run record in parent
out/coop-dev/runs/resident-slot-completion-20261103. No VPS/protocol changes.

## 03.11.2026 — 18:08 run: resident completion fix NOT confirmed; second guest blocked

Reviewed all three profiles, build18:07:19, PIDs41568/15820/40872.
P3 host; P2 joins18:10:24 and is resident18:10:37. P1 sign returned by host
search and continually refreshed, but no claim/JoinRoom through exit18:12:07/08.
Host selection18:10:37: coop2/2, maskFFFFFFFF, ready0, queued1; remote task6/6,
flags0xC, role7. SosStatus.Update runs, no resident-completion success logged.
Last delivery's gameplay-pending status is superseded by this failed run;
source fixture success does not establish the completion policy's real guards.
Exact rejecting guard/native completion outcome not exposed by existing logs.
Collection: parent out/coop-dev/runs/second-guest-1808-review/pc, 9 standard
files/warnings0/stable copies plus party events and explicit last_run copies.
All runners exit0. No code/build/deploy/save/settings changes. See
fixes/2026-11-03-second-guest-run-1808.md. Bug remains open.

## 03.11.2026 — resident summon completion delivered; local-three launched18:08

Related menu-lock and notification source work completed. DLL build exit0;
2446 recorded source input size/mtime unchanged through build, related chats
idle. Six-file delta copy0, backup
D:/Games/Bloodborne/coop-dev/backups/resident-summon-completion-20261103-180809.
Includes current party/compat owner-excluded bell notice and host menu lock.
Native port/VPS/wire protocol unchanged. Coordinator41392 launched18:08:10MSK,
15:08:10UTC, three existing profiles. Fresh mod logs18:08:38/39 confirm
Player1 native41568, Player2 native15820, Player3 native40872, built18:07:19. Gameplay confirmation pending: second
guest should enter while first remains, without the180-game-second wait.
Build record: parent out/coop-dev/runs/resident-summon-completion-20261103.
Earlier source-only/ready-for-build status below is historical.

## 03.11.2026 — resident summon queue completion; ready for build

Latest17:44 run still blocks next guest despite open role mask. P2/P3/P1 finally
show3 actors at17:54:50 after a long delay with first guest still present. Added
host-only native identity-bound completion18777D00 for an already created,
arrived6/6 cooperative insertion task and matching live actor/full user+character
identity. Original destructor/unlink/count/backoff own completion; unfinished and
foreign requests remain. Corrected queue diagnostic to SosStatus[rbp-6F0], not
candidate manager. Direct queue removal/parallel-request bypass rejected: native
has one active request/result context and live+queued admission reservations.
Production policy + exact native completion and gate fixture PASS, five roles,
unrelated pending retained,21 rejection cases; full game TU syntax PASS.
Build/deploy/gameplay pending. See fixes/2026-11-03-resident-summon-request.md.

## 03.11.2026 — host menu lock retained through asynchronous title handoff

User reports System can reopen after a delay during active-host exit. Source
had an unguarded interval: TickBbscPendingQuit returned immediately after
bbsc_title_quit was populated, although OnReturnTitle only queues intent.
Host LoadWait/menu brake now remain asserted after final leave and CloseMenus
until native loading or world/menu replacement is observed. Handoff is latched
so reused singleton addresses cannot reapply the restriction at title/Continue.
Guest behavior and native save/Stop/final-leave ordering are retained.

Production menu fixture first reproduced the gap on old code, then PASS:
60s deferred title, reset by CloseMenus/native updates, host vs guest, loading,
context replacement/reuse, Continue and cancellation. Full BBSC_MOD translation
unit syntax PASS (existing getenv deprecation warnings). Source only; no product
build/deploy/game launch; live confirmation remains pending coordinated build.
See fixes/2026-11-03-host-quit-input.md. No save/settings changes.

## 03.11.2026 — host bell banner reproduced: installed pre-exclusion code

User reported the notification on the beckoner. Collection:
parent out/coop-dev/runs/bell-host-notice-review-20261103/pc (9 files,
warnings0; live files, some ChangedDuringCopy, not a final stopped-run snapshot).
P1 grant17:46:59.762 -> notice17:47:00.274 -> native host17:47:26.631.
P2 grant17:51:06.226 -> notice17:51:06.749 -> native host17:51:14.442.
All three logs identify DLL build17:43:21 and startup17:44:41/42.
Read-only inspection of installed coop/party/compat.py line370 confirms the
old condition `owner is not None`, including the owner in bell notices.
Source host exclusion was modified17:49:22; final wording17:53:52, after
this build/startup. Current source excludes `owner in (None,self.e.id)`;
this run cannot validate that revision. No additional code change needed
for this finding; source exclusion/text still await a coordinated build,
party compatibility file deployment and fresh runner/game startup.
No build/deploy/restart/save/settings changes during this investigation.

## 03.11.2026 — Beckoning notification wording and audience updated

Supersedes the notification wording/audience entry below: "В мире раздаётся звон
Зовущего колокола…" / "The chime of a beckoning bell resonates across the world...".
Only other party clients receive the notice; the world owner receives zero
notification generation. Repeat polling and owner rotation covered by the
updated three-client RPC test; production notice-tick fixture PASS.
Source only; no product build/deploy/gameplay confirmation.

## 03.11.2026 — second-guest masks built/installed; local-three launched17:44

Both related chats finished. DLL build exit0; native incremental exit0/no work;
recorded build input size/mtime unchanged. Six-file delta installed with backup
D:/Games/Bloodborne/coop-dev/backups/second-guest-masks-20261103-174410, including
party/compat bell-notice extension from the completed parallel work. No VPS or
wire-protocol changes. Coordinator32512 launched17:44:10MSK/14:44:10UTC; three
existing separate-profile runners started. Fresh mod logs17:44:41/42 confirm
Player1 native20260, Player2 native11760, Player3 native38820, built17:43:21. Gameplay remains pending: keep the
first guest in host world while admitting the second. Earlier source-only status
below is historical. Run: parent out/coop-dev/runs/second-guest-masks-20261103.

## 03.11.2026 — 17:16 second guest review: residual native co-op masks

Individual joins and Blank host release confirmed in the new run, but a waiting
second guest gets no claim until the resident guest leaves, across all host roles.
Fixed two missing FIVE_HUNTERS covenant co-op masks at01873086/018793B9; original
native executable blocks reproduce the residual exclusion and pass with actual
production patches (both paths,256 slot combinations, other role bits preserved).
Added change-only slot/ready-mask/queued-count observation; historical logs lack
these fields, so contribution to the live block is not yet proven. Capacity,
readiness and cooldown retained. Targeted mask/cooldown/matchmaking tests and
full BBSC_MOD TU syntax PASS. Source only; no new build/deploy/launch.
See docs/fixes/2026-11-03-second-guest-slot-masks.md. Three-player entry remains open.

## 03.11.2026 — Beckoning Bell notification, source only

All party clients, including the beckoner, now show "Игрок начал звонить в
колокол призыва." (English equivalent for English UI) once per finalized
world reservation generation, at the same authority transition that locks
other clients' Beckoning Bells. Opt-in third `/party/tick` response field;
old DLLs keep two fields and new DLLs accept old runners without a notice.
No notification from cached availability failures/network loss. Game-thread
banner retries while its table is unavailable; loading/title/quit are fenced;
repeat polling/reconnect within the same process does not repeat a generation.
Targeted 3-process RPC, legacy title ticket RPC, production native notice-tick
fixture, real WinHTTP/process fence and full changed game TU syntax PASS.
No product build, deployment or game launch; live banner appearance pending.

## 03.11.2026 — 17:16 performance run reviewed; targeted waits removed, FPS/stutters still open

Fresh9 stable files/warnings0: parent out/coop-dev/runs/perf-review-20261103-1716.
All3 mod logs built17:14:37;94 valid pacing windows/PID,report_async1,
tail_precise1,reports_dropped0. Actual background bell grants438/672/422ms;
no matching frame-long wait, each player subsequently hosted. Initial sign
cleanup/retry allowed real joins. Ready-queue menu~59.97–59.99FPS.
Stable gameplay still~47.6–55.2FPS, systemCPU92.5–95.9% with3 games. P2host
has100 frames>50ms in~70s at47.54FPS. P1post-load358ms is primarily late-ready;
CPU/GPU producer ownership unmeasured. Report capture/submit wall time reaches
10.559ms, not the old synchronous-print metric. No matched single-game A/B;
no percentage FPS gain claimed. Pairs rotate, no hunters3; second guest remains
open. Analysis only, no source/build/deploy/launch/save/settings edits.
See parent docs/fixes/2026-11-03-pacing-run-1716.md for metrics and boundaries.

## 03.11.2026 — 17:16 final Blank/native IDs/performance batch deployed; three native games launched

Related performance chat completed before final build. Parent d588b23 / BBSC
528fe6a plus recorded working changes. DLL build0/native incremental build0,
source input metadata stable throughout; 8-file delta copy0 on stopped PC.
Backup D:/Games/Bloodborne/coop-dev/backups/blank-native-ids-perf-final-20261103-171607.
Run parent out/coop-dev/runs/blank-host-exchange-20261103-164554;
coordinator20488 launched17:16:08MSK/14:16:08UTC via existing local-three mode.
Includes host Blank/search-end empty-room completion, canonical native member
IDs/slot mask/full callback incarnation, bounded application-exchange observer,
asynchronous authority-preserving bell/HTTP cleanup and diagnostic reporting,
transport formatting outside lock and checked current-map memory lookup reduction.
Targeted tests pass (own native Blank/menu/exchange +6 focused party cases;
performance validation recorded in frame-thread-stalls). No save/settings/journal
reset; all3 existing journals were final88/idle before launch. No VPS update:
changed runtime allocator is embedded in clients; public wire format unchanged.
Gameplay remains pending: Blank role transfer and native deferred bell, PL1
exchange/second guest, plus performance. The recorded PL1 pre-JoinRoom failure
is not declared solved by an API fixture or successful build/startup.
Startup confirmed: P1/P2/P3 native30272/13872/38964; fresh mod logs17:16:36/37
all built17:14:37, local coordinator run20261103-141608. Games left running.
Successful startup is not confirmation of JoinRoom, role transfer or FPS improvement.

## 03.11.2026 — frame-thread stall fixes implemented; gameplay pending

Party acquire now runs on the maintenance worker. Native item callbacks enqueue
without network waits; the game tick resumes one confirmed action with actor/map/
load-generation/cancel/death/title fences. Nested item entries share one grant;
late replies cannot revive cancelled generations. Stale-sign HTTP cleanup also
runs outside lifecycle mutex on the worker; native create uses nonblocking retry,
with in-flight/version fences and delete-before-create preserved. Unfinished
native joins are not cleaned. Parent transport formats diagnostic snapshots after
unlock; pacing and legacy Perf output use bounded asynchronous writers.
DLL memory checks avoid duplicate region lookup; current-map reader uses4 live
span checks instead of8, preserving bounds/permissions and no inter-call cache.
Targeted production fixtures,3 real WinHTTP bridge tests, native trampoline,
540 real UDP deliveries/current transport, async pacing/backpressure and relevant
hot-path regressions PASS. Full changed module TU MSVC/clang-cl syntax and native
driver syntax PASS. No product build/deploy/launch/settings/save/VPS change;
FPS benefit and native deferred-bell/initial-sign retry behavior await gameplay.
See [implementation and validation](fixes/2026-11-03-frame-thread-stalls.md).

## 03.11.2026 — 16:23 pacing run investigated; remaining stalls not fixed

Fresh stable 9-file collection/warnings0: parent
out/coop-dev/runs/perf-review-20261103-1623. All three PIDs tail_precise1;
ready-queue menu windows now59.73–60.02FPS vs historical57.1–57.4.
Gameplay47–55FPS, systemCPU95–98%, late-ready dominates; no matched
single-game baseline. P3 505.6ms frame aligns with474.9ms synchronous
PartyAcquire inside native item hook. P1 435.8ms frame aligns with stale
claim cleanup; HTTP/lifecycle-lock causality still unmeasured. Pacing
report overhead max18.827ms; packet batch formatting holds transport
mutex despite logging after unlock. BBSC hot-hook wall times include
preemption and nested ticks, not pure CPU or measured DLL FPS penalty.
Priorities: asynchronous authority-preserving party gate, measure/move
lifecycle I/O and diagnostic formatting, reduce observer overhead, then
matched one-vs-three CPU/GPU/worker-count comparison. Analysis only;
no product edits/build/deploy/launch or save/settings changes. See parent
docs/fixes/2026-11-03-pacing-run-1623.md for evidence and limits.

## 03.11.2026 — host Blank empty-room completion fixed in source; PL1 still open

16:23 run collected: 9 stable files/warnings0, plus three party journals.
P3 host/P2 guest; P1 receives a real claim16:26:01.963 but native exchange
phase11 expires08.586 before JoinRoom, ready=false. Recorded P1/P3 encoded UDP
sends all match intended receives; no proven UDP/capacity/identity cause.
Host Blank/search end now latches runtime item/search-effect end as well as
SpEffect7 and stops only a loaded, living, demonstrably empty native host room;
native idle/final party drain still own release. Three production fixtures PASS.
Additional bounded application-exchange callback observation for P1; **P1 is
not yet fixed**. No gameplay confirmation. See fixes/2026-11-03-pl1-blank-run.md.
Build/deploy/startup pending below until explicitly recorded.

## 03.11.2026 — all-current changes built/deployed; three local games launched

User requested waiting for current parallel fixes, then build/install/launch3.
Related chats completed before build; source input size/mtime and HEAD stable
through build. Parent d588b23 / BBSC ac5e70b plus inherited working changes.
Includes second-guest cooldown consumption fix, host title reload correction,
host quit input wait, accelerated initial guest placement and precise vblank tail.
DLL build0 + native incremental build0; explicit6-file delta copy0, no repeated
tests/file verification/full package. Backup:
D:/Games/Bloodborne/coop-dev/backups/all-current-three-20261103-20261103-162312.
Run out/coop-dev/runs/all-current-three-20261103-162200; coordinator27708,
local20261103-132331, UTC13:23:31. Three native PIDs12068/30784/26556 observed.
Existing local-three group/profiles and service-lifetime coordinator retained;
no save/settings/journal resets. Latest changes are client DLL/native pacing;
no VPS/server protocol change in this batch, laptop unchanged. Games left running.
Gameplay pending: second guest joins, host reaches title without reload and
input lock retains camera, guest teleport visibility and FPS/stutters. Build and
startup do not close these bugs. Earlier source-only statuses describe pre-build.

## 03.11.2026 — source-only second-guest cooldown consumption fix

Native018732DD marks pending.state1 BEFORE SummonBuild's enabled/positive role
cooldown guard can returnnull. Same-generation node stays consumed forever.
Production ApplyBbscSummonRoleDelayMask at signature-checked Scan01873269 defers
roles7/21/22/23/24 before consumption, preserving node/timer/counters/native
capacity/identity/readiness. Hook selected with research off; change-only mask
log. Exact native scan+builder-guard/production trampoline fixture reproduces
baseline and fixes delayed retry/renewed nodes; existing matchmaking fixture PASS.
Historical node/countdown not logged: causal fit, not proof of every live failure.
User no build: source only; only temporary regression harness compiled, no product
build/deploy/launch/save/settings/journal changes. Gameplay pending. See
 docs/fixes/2026-11-03-second-guest-cooldown.md.

## 03.11.2026 — host automatic reload: source fixed, build deferred

Removed StageTransition after OnReturnTitle: native execution confirms that
it arms an independent world reload even with title request2 already pending.
Updated production menu regression FAIL before/PASS after; native command test
PASS. Existing host input wait retained. No production build/deploy/launch.
Actual host title arrival remains pending a future authorized build and run.
See fixes/2026-11-03-host-title-world-reload.md; older OPEN entries are historical
diagnosis, not a claim that the corrected code has been tested in the game.

## 03.11.2026 — host title exit input lock implemented, gameplay pending

Code ac5e70b: confirmed host System exit holds native guest-departure SetLoadWait
and menu brake through save/Stop/final party wait, without camera filtering.
Cancel restores original restrictions in the same non-loading context; native
transition owns reset. Earlier host Blank cleanup cannot release the quit wait.
Production menu-quit fixture PASS; native movement/camera/menu behavior pending.
Separate host automatic reload issue remains OPEN. See
[host quit input](fixes/2026-11-03-host-quit-input.md).

DLL build exit=0 (three existing unused warnings); five-file delta installed
on the stopped main PC, copy exit=0. Backup:
D:/Games/Bloodborne/coop-dev/backups/host-quit-input-20261103-20261103-161436.
All three Player profiles use this installation. No game launched; gameplay
pending. Saves/settings, laptop and VPS unchanged; no push or parent pin update.

## 03.11.2026 — initial guest teleport accelerated, source only

Removed the 2s join-position settle and 250ms polling. Once the destination
world, living guest and actual host transform are ready, the native in-map
warp runs after one fade update. A zero-duration black fade covers placement;
100ms later it reveals over 150ms. No arbitrary living partner fallback.
Placement is marked complete only after the native warp; bad vtable retries.
Cover expires after 500ms if readiness is lost; native load/title, death curtain,
quit and replacement actor take fade ownership without a synthetic reveal.
Production-tick fixture and destination/map/mount/freshness fixture PASS.
No DLL/game build, deploy or game launch by user request. Visual result and
native fade timing await gameplay; do not claim animation removal confirmed.
See [implementation note](fixes/2026-11-03-join-teleport.md).

## 03.11.2026 — OPEN: host menu exit automatically reloads gameplay

User correction to16:03 review: P2 did not press Continue after host exit.
Confirm16:02:36.966 ->title request/StageTransition16:02:40.011 ->own character
creation16:02:49.548. Diagnostic wording "Continue" is not evidence of input.
Final79/Stop completed, actual title arrival failed. Inspect native title request
consumption vs direct StageTransition; fixture substitutes both native functions.
No code/build/deploy in this review. Prior Continue/title-success claims for this
host exit below are historical. Parent fixes/2026-11-03-second-guest-run-1603.md.

## 03.11.2026 — 16:03 run: signs returned, second guest never claimed; clean final79

Collected9 stable logs/warnings0 +3 party events +coordinator metadata:
parent out/coop-dev/runs/review-20261103-1603/pc. P1->P3, P1->P2, P3->P2 native
state6/two hunters confirmed. P3 native host->guest works after role termination,
not menu/Continue. At P3+P1, P2 sign returned but no claim. At P2+P1, P3 returned
but only claimed after P1 leaves and room recreated. P1 after guest menu/Continue
returned to P2+P3 but never claimed. Thus second-guest blocker narrowed to native
candidate/request path; exact predicate unknown, no proven UDP/capacity cause.
No3-player session, no crossed responder icon. P1 guest title0.673s/P2host3.045s.
Final79 unanimous owner/roomnull, joined/pendingempty, tx/acceptedabsent;
all native exits0, coordinatorparty_drainedtrue. Owner released BEFORE native
processes closed: missing-ACK early-close reproduction not exercised. No code,
build/deploy/launch/save/settings edits. See parent
 docs/fixes/2026-11-03-second-guest-run-1603.md.

## 03.11.2026 — 16:03 pacing: limiter loss observed, upstream stutters remain

New telemetry active in15:56 build;9 stable files/warnings0. Ready100% windows
57.10–57.42FPS: tail wake~0.8ms, cap_waits0. Gameplay CPU95–98% and late-ready
frames also present; no single-game matched comparison. Strict vblank tail now
uses existing precise helper in source only, no new build/deploy. Future runtime
must confirm gain and spin cost; cannot claim stutters fixed. Full evidence:
parent docs/fixes/2026-11-03-pacing-run-1603.md.

## 03.11.2026 — 15:56 user-authorized all-current build and local-three launch

After the initial no-build request, user explicitly requested launch with all
latest changes. BBSC5351ecd / parentd588b23 plus inherited working changes:
full fast build0 (DLL/native/launcher), PC copy0/5145 files, backup
local-party-lifetime-20261103-20261103-155517. Coordinator22972;
run local-party-lifetime-20261103-155615, local20261103-125615. No journal reset,
save/settings changes or VPS update. Gameplay pending. The service lifetime
fix is implemented/tested; former-host native admission remains open.

## 03.11.2026 — source-only local exit lifetime fix; former-host admission remains open

P1/P2 native exits previously immediately closed their consensus nodes before
P3 final release. Local-three coordinator now keeps early-exit services alive
until all native games exit and unanimous idle is durable; missing coordinator
or 30s unresolved drain stops services without forced ACK/release/journal reset.
Real 3-peer lifetime regression and former-host sign/admission socket fixture
PASS; timeout/profile checks PASS. Compatibility sign_search diagnostics expose
returned/excluded/missing peers without payloads/secrets. No native search bypass;
actual P1 guest recovery remains open. User said no build: source only, no build,
deploy, game launch or save/settings edits. See parent
 docs/fixes/2026-11-03-local-party-service-lifetime.md.

## 03.11.2026 — pacing measurement source ready, build explicitly deferred

Parent VideoOut instruments ready-vs-deadline and dispatch/wake/queue/prepare/
flip/swap + process/present CPU and machine busy.4 Python analysis tests PASS.
No C++ compile/build/install/runtime check; user explicitly asked not to build.
Pacing policy unchanged, FPS/stutter cause remains open. Future matched1vs3
scenario documented in parent docs/fixes/2026-11-03-pacing-instrumentation.md.

## 03.11.2026 — latest local-three performance reviewed, regression cause open

Collected27 stable files/warnings0: parent out/coop-dev/runs/perf-review-20261103-latest.
15:31:50–15:34:20 gameplay selection: P1host53.69/P2guest52.94/P3alone55.29FPS;
>50ms frames/min16.25/7.84/4.13. All3 games ran concurrently on PC, not matched
against historical single-PC+laptop/uncapped90 baseline. BBSC wall-time~5.0/4.9/3.7ms
per game tick includes native traced work/preemption. Scaling hundreds-ms not
reproduced. Prior serverless backlog/worker/HTTP optimizations already present.
Strict relative cap can accumulate wake lateness (0.877ms ->57FPS mathematically),
actual lateness not instrumented; limiter unchanged since old perf baseline.
Next: pacing/scheduler separation, IsValidSos/PartyObserve sub-timing and Python
queue/fsync telemetry. Analysis only; no runtime/build/deploy/settings/save changes.
See fixes/2026-11-03-perf-local-three-review.md; bug remains open.

## 03.11.2026 — 15:38 run: P2->P1 works; former-host P1 publishes but is never claimed

Collected9 stable mod/native logs +3 event logs, warnings0; parent
out/coop-dev/runs/review-20261103-responder-area/pc. DLL15:28:11. P2 publishes in
Cathedral240000 and joins P1 state6/two hunters. P1 active title exit2.662s and
Continue observed. P3 later becomes native host (room created); P2 joins state6.
P1 after Continue has normal responder icon, publishes sign15:35:17, but NO claim/
JoinRoom/state4/6. Crossed-area gate/publication improved; former-host guest entry
NOT confirmed/fixed. P3 earlier pre-room attempt toP1 phase11 ready=false times
out15:34:31; exact cause open. No3-player session or quit-during-Join exercised.
P2 guest menu/title1.110s+Continue works. Final all3 rev56 retains ownerP3 with
room=null/joined/pending empty. Last P3 title waits for release: persistent tx
prepare release seq18 ACK onlyP3; P1/P2 processes closed BEFORE P3 quit request.
No unilateral release/journal reset performed. P1 last idle title transition
also unconfirmed. Analysis only; no build/deploy/settings/save changes. See
parent docs/fixes/2026-11-03-responder-area-run-1538.md.
## 03.11.2026 — crossed responder bell area gate fixed, P1/P2 guest validation pending

User clarifies P1/P2 could not join one another after hosting; bell HUD crossed.
Prior P1->P2 success covered P3 as guest only. Native0191A750 still retained
!area_disable_flag in AL (Cathedral240000->flag2405) after goods/SosStatus allowed
the area. 0191A8C3 signed patch copiedAL; now MOV CL,1 lifts this geographical
veto while native common-player eligibility/range/null checks remain. Exact
native function fixture reproduces old rejection and fixes positive/negative
areas; guest-bell/matchmaking fixtures PASS. Runtime2405/common values absent
from old logs, so historical cause is consistent, not proven for every attempt.
Read-only change-only bell icon/area/publication diagnostics added. Bundled
c1d3cfd / parent1469079, inherited working changes retained. DLL build0 (3 old
warnings),5-file PC copy0, backup responder-area-crossed-bell-20261103-20261103-152859.
User-authorized coordinator20692, run responder-area-fix-20261103-152919.
P1<->P2 actual former-host guest gameplay pending; no claim of completed fix in
game. Journals/settings/saves/VPS/laptop unchanged. See parent
 docs/fixes/2026-11-03-responder-crossed-bell.md.
## 03.11.2026 — 15:07 host rotation run reviewed, P3 grant without native room remains open

Collected9 stable PC logs +3 party event logs, warnings0:
parent out/coop-dev/runs/review-20261103-host-rotation/pc. DLL14:56:31 present.
Old closing rev18 recovered normally. P1+P3 state6/two hunters; P1 addressed kick
returns P3 home. P1 role drains, P2 acquires and P3 joins state6/two hunters.
P2 active title exit completes in2.493s, guest returns home, Continue observed.
P3 next acquire unanimously final rev38 at15:06:26, BUT native remainsstate0:
no CreateJoinRoom/state1/state3 until menu15:06:59. Exact post-item/native-start
cause unknown; third hosting NOT confirmed. P3 menu releases owner rev39; all3
journals end idle. No native negotiation failure/slow-disconnect ERROR; failed
admission retry and quit-during-Join hook NOT exercised. No3-player gameplay.
All runner exit0; P2 last idle exit only reaches final-leave log before shutdown,
not a separately confirmed title transition. Analysis only; no runtime changes.
See parent docs/fixes/2026-11-03-host-rotation-run-1507.md.
## 03.11.2026 — host rotation retry/guest join exit fixed and installed, game pending

Prior local3 consensus DID rotate P2->P1 (rev8 release/rev9 acquire). P3 initial
native phase11 timeout had15/15 recorded UDP frames delivered; inner ready=false
cause remains unproven. Proven recovery bug: private Force delete retained pending
rev11, replayed failed claim and prevented fresh admission. Delivered-pending Force
withdrawal now requires native idle/no load and revision ticket (stale rejected).
Guest explicit cancel+idle now retires joined membership even without owner close.
Native stopped Join task8 selects ordinary deadline/failure cleanup via C9C6AB
read hook; no state/task writes or title ACK bypass. Real3-process rotation/failure/
retry/quit scenario + exact native predicate/CC51F0/trampoline + menu/leave fixtures
PASS. DLL build0,7-file fast PC copy0, backup p2p-host-rotation-20261103-20261103-145849.
User explicitly requested launch: coordinator28988, parent run
out/coop-dev/runs/host-rotation-fix-20261103-1459. All3 native games running15:00 (P1=33516,P2=36244,P3=20616), new DLL14:56:31 ready; gameplay pending. Saves/settings/
journals/VPS/laptop unchanged; inherited working changes kept, no pin/push.
See parent docs/fixes/2026-11-03-host-rotation-retry-exit.md.
## 03.11.2026 — local-three P2P run reviewed

Collected9 stable mod/native files, warnings0, plus3 stopped party event logs:
parent out/coop-dev/runs/review-20261103-local-three/pc. P2 host/P3 guest reach
state6/two hunters; both death/respawn and P2 title exit+Continue observed.
P1 becomes next owner; first P3 join remains pending ~56s until P1 cancellation.
Retry reaches protocol joined/native state4, then P3 menu exit stalls state7:
14:35:03.902 native disconnect exceeds5s, no final leave/title before log end.
All3 journals end rev18 ownerP1 members[P3] room33554436 closing=true, although
P1 native reachesstate0. Exact cause unproven. Three-player gameplay/full rejoin
not confirmed. Runner exit0 is process termination, not successful game exit.
Analysis only; no runtime/build/deploy/save/settings changes. See parent
 docs/fixes/2026-11-03-local-three-run-review.md.
## 03.11.2026 14:27 MSK — local-three mode installed and games running

User requested local P2P test with existing profiles. Parent75411e7 adds local-test button/helper; 4 targeted isolation/socket tests PASS, launcher-only freeze0, installed4 files backup local-three-20261103-20261103-142456. FPS60/windowed1280x720/Skip Intro are per-launch only; settings/saves not reset. P1/P2/P3 loopback control37610/11/12 and nativeUDP3658/59/60. Native PIDs28640/19400/36528 and all3 NP contexts observed. P1 had pre-native compatibility port-pair allocation failure; only failed helper was replaced, retry succeeded, other games retained. Allocator issue remains unclaimed. Games left running; gameplay pending. Run parent out/coop-dev/runs/local-three-20261103-142526; see parent docs/fixes/2026-11-03-local-three-p2p.md.

## 03.11.2026 — P2P promoted to develop, PC installed

User accepted P2P and requested mainline replacement. Main develop includes experiment1650f48 and new launcher3f4b56a; bundled developd8c8e08 runtime is party/ (no experimental launch.py). Server/invite/password flow removed, automatic/Tailscale/Radmin/custom picker and all-peer TCP/UDP preflight added. Native UDP and durable role protocol retained.5 socket tests/QML/frozen runtime+UI smokes PASS; native/DLL/package exit0; installed main PC with backup p2p-main-20261103-20261103-095153. No game launch/provider VPN gameplay claim. Source experimental worktrees removed after preserving inherited source patches/untracked files. Permanent test install/profile cleanup was rejected automatically; both archived out of active paths, saves intact. Laptop/VPS untouched. See parent docs/fixes/2026-11-03-p2p-mainline.md.

## 03.11.2026 — serverless-party, эксперимент подготовлен к игре

Отдельный parent worktree `bloodborne_pc-serverless-party`, ветки
`experiment/serverless-party` родителя и подмодуля. База 572e066/151e24c +
скопированные локальные правки, исходные деревья сохранены; чужие правки
не включены в коммиты эксперимента. Протокол unanimity + durable journal,
независимые процессы, embedded compatibility в существующем runner BBGL,
нативные bell gates до side effects, сохранённый direct VPN UDP.
10 сценариев процессов, adapter/WinHTTP/trampoline/menu-exit проверки PASS;
DLL и frozen launcher build exit=0. Отдельные тестовые установки ПК+ноут,
копии start-clinic-teststart, LAN invitation; основные сейвы/установки/VPS/
роутер/firewall не менялись. Игры не запускались, **игрового подтверждения нет**.
Сценарий, пути и границы: [отчёт родителя](../../../docs/experiments/serverless-party.md)
и [протокол](../experimental/party/PROTOCOL.md). ACK сетевого компонента не
означает exactly-once применение игровых эффектов после краша; VPN/NAT между
разными провайдерами и каталог чаш ещё не проверены/не перенесены.
## 2026-11-03 04:24 MSK — actual rejoin capture + TCP queue bounds installed

DLL atomic attempt serial now advances on first delivered claim/native join
transition, including cached signaling reuse; duplicate polling and unreadable
load manager do not refill. Native relay observes export before routing/on tick,
renews all known peer windows and existing VPS markers. Two-window realVPS
production UDP/export-bridge probe:240/240 at all4 logged boundaries, PASS.
TCP writer now nonblocking+absolute10s queue/frame deadline, unchanged FIFO/cap;
expired transport wakes owner cleanup/reconnect, no stale byte replay. Callbacks
and queue-full logging moved outside send lock.5s client queue/progress/Dispatch
stats + per-connection server age/in-flight/throughput diagnostics added. Historical
queue correlation to host death/distant lamp NOT proven; exact cause still open.

Lifecycle+actual writer loop+native relay harness PASS; server departure11 and
queue3 tests PASS; production DLL TCP functions viaVPS100 frames PASS. First probe
omitted TCP_NODELAY and timed out after28; retained as differing-condition result,
not the game's root cause. Native build0, fast package0, final DLL/delta0;
8-file PC deploy0 backup
D:/Games/Bloodborne/coop-dev/backups/rejoin-trace-tcp-queue-20261103-20261103-042422.
VPS backed up /opt/bbsc/backups/rejoin-queue-20261103/bbsc_gameserver.py,
updated Python server only, active. No game/user data/settings/firewall/SSH changes,
no commit/pin/push. P3 CPU automatic stop and GPU remain excluded/deferred.
Game confirmation pending; see fixes/2026-11-03-rejoin-trace-tcp-queue.md.

## 2026-11-03 03:59 review — repeat joins observed; CPU-overload stop excluded

Collected6 stable PC logs+VPS journal+persistent log, warnings0, review-20261103-0359.
Initial joins work, later full repeat joins at03:47–48 and03:50–51. No stale-TCP
false-host sequence/reconnect in this run; thus replacement branch not exercised.
Host TCP queue261530 bytes/dropping03:49:39 observed, server errors0, cause unknown.
P3 GPU device lost03:52:36+current WER141; server10s grace then guest-only PeerLeft
03:52:47, no false host stop. Actual host menu quit49s sends explicit leave toP2.
User attributes P3 automatic Stop03:48:35 to CPU overload and explicitly excludes
it: do not investigate or treat its queue/native rejection as a network blocker.
GPU issue remains deferred. Distinct native remote slots0/1, no identity guard hit.
Important diagnostic gap: only initial six NP activations open traces; native
rejoins reuse signaling and do NOT renew90s windows. Later tx0 is missing capture,
not zero loss. Next diagnostic trigger must cover real native attempts/claims.
Analysis only, no runtime edits/build/deploy/restart. See
fixes/2026-11-03-connection-run-0359.md. GNS migration remains separate experiment.

## 2026-11-03 03:30 MSK — TCP relay replacement fix built and installed

Newer(sender,session) connection supersedes old socket; stale EOF/state/explicit
leave cannot announce departure or invalidate the new connection. Transport-only
loss waits10s for existing reconnect/beacon; matching recovery cancels the decision.
Genuine explicit SessionLeave remains immediate; final newest-socket loss emits
one party-scoped PeerLeft after grace. Registry-locked decision/enqueue and pending
identity protect cancellation races; obsolete sockets cannot hide real departure.
Client and server diagnostics now identify control source, conn IDs and decisions.

Bundled production departure fixtures11 PASS; real publicVPS TCP replacement,
after-EOF recovery beyond timer, stale leave rejection, genuine final departure
and party scoping PASS. Actual persisted oldVPS log also confirms overlapping host
sockets before delayed old ETIMEDOUT. Original WSA10060 cause remains unknown;
recovery fixed, no timeouts disabled. DLL build0 (four existing warnings), fast
full package0;7-file PC deploy0 at03:30:31; backup
D:/Games/Bloodborne/coop-dev/backups/relay-replacement-20261103-20261103-033031.
VPS backed up /opt/bbsc/backups/relay-replacement-20261103/bbsc_gameserver.py,
updated Python game server only, restarted bbsc-gameserver, active. Native port
unchanged, no game launched or user data/settings/firewall/SSH changed. No commit/
pin/push. ZIP bloodborne_pc/dist/bbgl-1.1.0-windows-x64.zip. Game confirmation
PENDING: two guests enter, keep session6–7min, leave/rejoin one with other remaining.
Collect persistent VPS gameserver log as well as journals after run. See
fixes/2026-11-03-relay-replacement.md.

## 2026-11-03 03:12 run — initial joins work; TCP reconnect precedes false-host departure

Collected6 stable PC logs + VPS, warnings0, review-20261103-0312. Both guests
reach state6/full session. Host TCP relay times out WSA10060 at03:11:21, reconnects
03:11:24; server counts4 sockets at03:11:34. Both guests mark host7c04a649 left
and invoke DLL Stop03:11:43.448/450, while host remains active until its later
Stop03:11:59. Actual VPS unregister function unconditionally broadcasts0x7e for
old sender/session, without checking a replacement socket. Defect confirmed in
code; stale-old-socket departure is strongest causal inference, exact control
source/unregister not logged. TCP10060 initiating cause unknown. Independent
attempt trace renews:1111 jointly covered sends match VPS RX and peer RX;90s
windows end before final disconnect, so no per-frame conclusion at03:11:43.
No rejected-send/01789812 Stop or identity guard rejection; separate host remote
slots0/1. No rejoin exercised. Analysis only, no build/deploy/restart. See
fixes/2026-11-03-connection-run-0312.md. Next fix: replacement-aware relay departure
and explicit unregister/PeerLeft diagnostics; preserve genuine leave handling.

## 2026-11-03 03:02 MSK — renewable attempt tracing installed on PC + VPS

Every accepted signaling activation (also same connId) renews a bounded90s window;
BBR1 diagnostic06/07 marker retries notify both peers, duplicate/stale markers
cannot replenish budget. Independent signaling/vport40 SOCKET_TX(actual sendto
bytes/error)/SOCKET_RX + server RX/TX/DROP share encoded-frame FNV hashes;
pre-ACK responder traffic is retained. W/I/R/D lifetime budget renews too.
Fixture/native builds/fast package PASS; deployed4 PC files with backup and
Python relay on VPS (only gameserver restart, active). Final two-window realVPS
probe found actual loss: 240 successful OS sends ->238 VPS RX/TX ->238 peer RX;
role0 receives120/120, role1 receives118/120 (delivery test exit2). Two missing
frames are between PC OS send and VPS application receive; precise network/
stack segment not proven. All238 server-forwarded frames match client receive.
Game connection/rejoin failures remain OPEN; no game launched or user data/
settings/firewall changed. See fixes/2026-11-03-attempt-packet-trace.md for hashes,
limits, tests, backups and next game run. No commits/pin/push.

## 2026-11-03 02:47 MSK — latest run cannot reach the rejoin scenario

02:40–02:44 run collected (3 profiles,6 stable files,no warnings) plus VPS:
BBGL out/coop-dev/runs/review-20261103-0245. New DLL02:33:09 and native diagnostics
present. No guest JoinRoom/state6; initial phase11 negotiation wait expires
P2 at02:42:23.057 and P3 at02:43:42.000. No pre-defer send rejection or01789812
Stop, no new Matching2 stale-identity guard hit. Rejoin fix NOT validated here;
initial entry issue persists independently of unexercised room-member callbacks.
Encoded W/I comparison before cancellation: P1->P2 5/17 sends unmatched,
P2->P1 0/10; P1->P3 5/11, P3->P1 8/14. Outgoing physical endpoints correct,
no sample omissions or vport40 transport/codec/queue errors. This locates a gap
between encoded send and peer receipt, not its exact segment. Server UDP stats
send_errors0, but per-frame trace budget was exhausted previously (0 new trace
records), so full VPS attribution unavailable. Future bounded trace must renew
per run/attempt. Menu exits separated from later host failure. No code/build/
deploy/server restart/save/settings/firewall changes. See
fixes/2026-11-03-connection-run-0245.md. Both entry and repeat-join bugs OPEN.

## 2026-11-03 02:36 MSK — rejoin identity guards built and installed

Server active-slot allocation is unique in inspected run records and compiled
actual Room allocator (100 alternating rejoins incl generation wrap). Free slots
may move between clients; room/member pair identifies the occupant. Reproduced
emulator defect: late Check after MEMBER_LEFT resurrected absent member34 even
when slot2 already belonged to36, emitting ESTABLISHED. Admission now requires
current roster memberID+onlineID; MarkActive also validates membership. Pending
signaling and room JOIN callbacks validate room/self/peer incarnation before
game dispatch; genuine current DEAD/removal and KICKEDOUT remain supported.
Native rejected-send diagnostics add target/self room+member; regular changed
session shape adds native task IDs/slots. No guessed rebind, queue deletion,
Stop suppression, bound increase, wire change or local shortcut.

Baseline ghost resurrection reproduced; current admission/dispatch/reused-slot/
healthy-peer/DEAD/JOIN variants PASS; actual server allocator PASS; exact native
observer hook + local member binding + KICKEDOUT fixtures PASS. Native build0,
bundled DLL build0 (four existing warnings), six-file PC delta deploy0 at02:35:53.
Backup D:/Games/Bloodborne/coop-dev/backups/rejoin-identity-20261103-20261103-023553.
No running game/launcher, no game launched or saves/settings/firewall changed.
VPS unchanged (no server/protocol change). Working-tree build atop572e066 /
151e24c, existing changes preserved, no broad commit/pin/push.
Specific initiating recipient in previous run still unobserved; gameplay fix
PENDING, not closed by fixtures. See fixes/2026-11-03-rejoin-identity.md.
Next: hold one guest in session while kicking/rejoining the other, wait60s,
repeat and swap; collect all3 logs with new identity fields on completion.

## 2026-11-03 02:21 MSK — latest connection run reviewed, analysis only

02:05–02:17 three-profile run + VPS collected in BBGL out/coop-dev/runs/
review-20261103-0218 (six stable files, no warnings). P1 host; both guests enter
and repeated joins reach state6. Previous pre-room negotiation timeout does not
reproduce; PEEKLEN causal role remains unproven (first256 receives/client flags0).
Addressed host kicks at02:12:18/32 trigger guest OnBeKickOut/Stop in154/99ms;
notice calls recorded, native5s return retained. No earlier23–37s kick delay.
Separate automatic guest Stops at02:13:29(P2),02:14:31/02:15:47(P3) originate
at0x1789812 after repeated pre-defer Native send rejected at0x1789742. This is
new evidence for investigating native logical recipient/channel lifecycle after
rejoin, not proof of an ACK timeout, WAN loss or a particular stale pointer.
P3 first departure is menu-confirmed; P2 at02:14:51 uses Silencing Blank;
final menu exits distinguished. Native UDP/codec/queue error counters0 except
late unbound vport30 after teardown. VPS904RX/904TX match, but trace budget ends
at23:07:50 UTC, before later failures; client sample budgets also finite.
Physical UDP3658/3659/3660 bind without collision; current endpoint inspection
shows no competing application on those ports. No code/build/deploy or save/
settings/firewall changes. Details: fixes/2026-11-03-connection-run-0218.md.
Initial entry succeeds this run; repeat-join disconnect remains OPEN.

## 2026-11-03 02:03 MSK — connection emulator audit, contract fix and trace deployed

01:35–01:39 run: P1 host, P3 pre-room negotiation expires at01:37:56.358,
phase11, wait<0, exchange ready/accepted false; no P3 JoinRoom. Four native
sends have no matching receive sample, but old logs lack endpoint/wire data:
WAN loss versus wrong destination/adapter is UNRESOLVED. Both upstream v0.0.1
and v0.0.2 already contain emulator source. Matching2 and base activation API
are identical between tags; state handshake changes only add timeline calls.
Retain v0.0.2 NAT endpoint aliases, immediate relay and targeted claim placement;
no whole-stack rollback or speculative wire switch. See
fixes/2026-11-03-connection-emulator-audit.md for comparison and exact limits.

Reproduced original-adapter incompatibility: MSG_PEEKLEN returned copied length
(0 for null/capacity0), whereas original BBSC returns full queued datagram length.
Restored full-length query without consuming packet; normal peek/truncation kept.
Baseline production-adapter fixture reproduces failure; corrected adapter with
real guest/transport backend PASS. Real UDP/readiness fixture540 deliveries PASS;
trace/hash/header fixture and production server forward/drop/error/bound PASS.
Additional client syscall/header/endpoint and encoded W/I packet hashes match
server RX/TX/DROP hashes; bounded logs, no packet bodies/secrets retained.
No local shortcut remains, per explicit user instruction: test through server.

Python live-VPS probe120/120; two separate compiled current BBGL transports
60/60 each direction, server120 RX/120 TX same hashes. Synthetic success does
not execute native Bloodborne negotiation and does not close the gameplay bug.
Fast package build exit0; final native incremental build exit0; staging probe
refreshed, PC deploy exit0 (5219 files). Backup
D:/Games/Bloodborne/coop-dev/backups/connection-emulator-audit-20261103-20261103-020241.
VPS bbhost_service.py backed up in /opt/bbsc/backups/connection-trace-20261103,
Python compile PASS, bbsc-gameserver active; native shadNet unchanged.
No running game at deploy, no game launched, no save/settings/firewall edits.
Working-tree build atop BBGL572e066/bundled151e24c, existing changes preserved;
no broad commit/pin/push. Live entry validation PENDING.

Next: P1 host, ring P3 once; after its entry ring P2. On failure wait10s for
trace flush, then exit/report. Record actual roles/actions; no save rollback.

## 2026-11-03 01:30 MSK — targeted KICKEDOUT fix built and installed

Confirmed native mismatch: BBSC shadNet kick status FF000019 was put only
in RoomUpdate.errorCode; Bloodborne requires presence length4 at +18 and
reason at +8 (CC3E80/CC4209). Adapter now supplies the known status there,
rejects stale-room kicks, logs payload at INFO. No wire/server change.
Mod handles addressed OnBeKickOut only: releases stale 4047 before Lua,
suspends retention for that guest and shows own return reason. Host gets
selected-kick request notice via exact native entry/caller; other callers,
local actor and remaining guest are preserved. Native 5s home-return delay
retained; no waiting for bound1001 needed to initiate native kick processing.
Production payload/native-guard fixture, targeted policy + exact trampoline,
resident-guest/native-release/home-return checks PASS; whitespace checks PASS.
Full fast package build exit=0 (DLL four existing warnings); PC deploy exit=0,
5219 files. Backup D:/Games/Bloodborne/coop-dev/backups/
targeted-kick-20261103-20261103-013001. Build: out/build-targeted-kick-20261103.log.
No running games/launchers at installation; no game launched, saves/settings
untouched. VPS unchanged. Pre-existing dirty trees preserved; build atop
BBGL572e066/bundled151e24c, not clean commit-only release; no broad commit/pin.
Gameplay/visible notifications PENDING. See fixes/2026-11-03-targeted-kickedout.md.
Earlier hypothesis-only note below is historical; this native guard defect
is now reproduced and corrected. Unrelated initial 00:47:52 queue failure
is not established as addressed by this targeted fix.

## 2026-11-03 — уточнение: задержка адресного kick хостом

Пользователь уточнил действия 00:56:34 / 00:57:20. VPS подтверждает kick
P3/user3 и P2/user2 через 1.7/2.0 с; исключённые гости начинают native возврат
лишь через 23.0/37.4 с от host effect, после Stop по bound1001. Эти поздние
Stop нельзя считать самопроизвольными разрывами. Первопричина задержки после
server kick ещё не установлена: KICKEDOUT callback/native session teardown.
Отсутствие уведомления сообщено пользователем; suppressed draw длиной13
совместим со служебным silent sentinel и не доказывает скрытие leave banner.
Обычные leave ids явно разрешены. Анализ only, новых сборок/деплоя нет.
Подробная хронология и границы: fixes/2026-11-03-session-review-0100.md,
раздел «Уточнение пользователя: адресное исключение Бланком хоста».

## 2026-11-03 01:12 MSK — session review, native profile-port fix installed

00:44–00:59 three-profile run + VPS reviewed; P1 host. Both guests join;
P2 Stop 00:47:52, P3 00:56:52 / 00:59:05, P2 00:57:52 originate at
0x1789812 (native deferred-send bound >=1001). The initiating queue/recipient
failure remains unresolved. Death recovery, boss clear and transition to Dream
retain the session before later departures. 953 HTTP completions error=0;
no transport full/wrong_peer/codec rejection, not proof of loss-free delivery.
Found BBGL bridge never installed p2p_port hook: launcher ports were ignored,
all clients requested 3658 and relied on fallback. Settings hooks now installed
before native import registration. Added bounded pre-defer native send failure
observer; no retry, queue deletion or bound change. Targeted settings fixture
and exact native observer trampoline/flags/throttle fixture PASS. Full fast
package build exit=0, DLL 4 existing warnings; PC deploy exit=0, 5219 files.
Backup D:/Games/Bloodborne/coop-dev/backups/session-review-0100-20261103-20261103-011120.
No running games/launchers at install; no games launched or save/settings edits.
VPS/protocol unchanged, no server update needed. Existing dirty trees preserved;
working-tree build atop BBGL572e066 / bundled151e24c, no broad commit/pin.
Evidence: bloodborne_pc/out/coop-dev/runs/review-20261103-0100; build log
out/build-session-review-20261103-0100.log. Details/next gameplay scenario:
fixes/2026-11-03-session-review-0100.md. Gameplay PENDING; disconnects NOT closed.

## 2026-11-03 00:43 MSK — connection review and client package installed

00:25–00:30 run reviewed across all three profiles and VPS. P3 signaling/vport40
exchange succeeds, outer native negotiation cancels after ~6s without JoinRoom;
P2 subsequently joins, then native Stop at 00:29:29.011 (caller 0x1789812).
Initial cancellation and later Stop remain unresolved, not proven fixed.
Fixed stable Player-profile UDP ports through both UI and game environment;
private BBSC HTTP minimum connect deadline 3s, bounded connect-only retry retained;
transport D samples represent copied bytes. Added pre-teardown native failure
observer at 0x1481AF9 (original result/wait/exchange state), both mod trees.
Six launcher checks, HTTP production fixture, exact native hook trampoline and
540 real UDP delivery test PASS. Full fast build exit=0; PC deployment exit=0,
5219 selected files. Backup D:/Games/Bloodborne/coop-dev/backups/
connection-0030-20261103-20261103-004233. No game/launcher running, no game launch,
save/settings/firewall changes. VPS services active; no server code/protocol
change or VPS update needed. Local working-tree build atop BBGL572e066 /
bundled151e24c, pre-existing changes preserved; not a clean revision-only release.
Evidence: bloodborne_pc/out/coop-dev/runs/review-20261103-0030; details and next
focused scenario: fixes/2026-11-03-connection-0030.md. Gameplay PENDING.

## 2026-11-03 00:14 MSK — death/HTTP/performance package installed

Full fast package build exit=0; PC deploy exit=0, 5219 selected files copied.
Backup: D:/Games/Bloodborne/coop-dev/backups/death-http-perf-20261103-20261103-001347.
One accepted YOU DIED event per death across fallback/native guest producers;
private native HTTP jobs retry TCP-connect timeout at most twice, never ambiguous
sent requests; Python accept backlog 5 -> 128. Hot region cache/validated-span
reads reduce redundant memory guards without relaxing the 250ms cache lifetime.
Targeted fixtures PASS; no gameplay/FPS improvement claim yet. VPS Python server
updated with backup /opt/bbsc/backups/death-http-perf-20261103; active, backlog128,
external ss.info burst 24/24 HTTP200. Native shadNet unchanged. No running game
at installation, no games launched, no save/settings/firewall changes. Previous
23:47 source-only claim-deadline/Stop-observer corrections included in build.
Working-tree build atop BBGL572e066 / bundled151e24c, not a clean revision-only
release; unrelated source changes preserved. See fixes/2026-11-03-death-http-perf.md.

## 2026-11-03 00:00 MSK — latest three-player run reviewed (analysis only)

23:49–23:59 MSK run, P1 host; P2/P3 initial and repeat joins succeed, both
wipe recoveries retain the session. 23:54 departures use Silencing Blank;
final exits are native-menu confirmed. Duplicate accepted death-text event
on P2 at 23:58:13.980 / 18.487: fallback crosses late native death script;
visible duplicate banner unproven. Old 23:22:26 DLL still has unavailable Stop
observer; 23:47 source fixes not exercised. HTTP timeouts and substantial logged
frame overhead remain; no native Fault or relay send errors. No code/build/deploy
or save/settings changes. See fixes/2026-11-03-run-review-0000.md; evidence in
bloodborne_pc/out/coop-dev/runs/review-20261103-0000.

## 2026-11-02 23:47 MSK — latest failed joins reviewed; partial source correction only

P1 host, P2 joins twice then leaves at 23:30:48 / 23:32:09; P3 never enters
JoinRoom. Three-profile mod/native logs + VPS journal: out/coop-dev/runs/
review-20261102-2333. Fixed reproduced stale-claim deadline extension on duplicate
HTTP delivery (20s became ~32s), plus duplicate Stop observer installation that
hid the initiating departure caller. Production lifecycle and trampoline checks
PASS; both code trees updated. No production build/deploy per user request.
Initial P3 cancellation and P2 disconnections remain UNRESOLVED, not confirmed
fixed by these changes. No save/settings/game/server changes. See
fixes/2026-11-02-run-review-2333.md for evidence and limits.

## 2026-11-02 23:23 MSK — native own-sign refresh installed on PC

Private-server own signs now queue native dirty refresh every 2s (rather than
assuming ServerInfo/cache writes trigger publication). Native HTTP replies remain
game-owned; in-flight requests / delivered claims pause refresh. Idle own-world
bell only, not loading/joining/hosting/joined/leaving; lifetime/counts unchanged.
Native cancellation origin/caller observers added (generic signaling cancellation
and CD89C0 phase before task-13 teardown). Exact initiating caller of the recorded
first failure remains unproven; late claim timing is the supported hypothesis.
Three targeted fixtures PASS; bundled DLL build exit=0 (4 existing warnings).
Five-file delta installed exit=0, backup D:/Games/Bloodborne/coop-dev/backups/
native-sign-refresh-20261102-232304. No game was running; no save/settings/game
or server changes. VPS update not required for this DLL-only change.
Commits: standalone 824a72c, bundled/pin 151e24c, BBGL 572e066; existing unrelated
working-tree changes preserved and present in local build. Gameplay PENDING.
Details: docs/fixes/2026-11-02-native-sign-refresh.md. Next focused scenario:
P1 host, P2/P3 guests, initial joins from different maps; record second bell to
loaded-world time and all three native/mod logs. Do not infer bug closure from build.

## 2026-11-02 23:17 MSK — remote departure banner fix installed locally

Native role-0 removal line incorrectly says local "returning home". Departure
hook now selects named disconnected text for remote co-op actors, preserving
local return and invader handling. Both trees + EN/RU generators updated.
Production callback through native trampoline PASS; bundled DLL build exit=0
(4 existing warnings), delta deploy exit=0, 5 files with backup. Gameplay pending.
See docs/fixes/2026-11-02-departure-banners.md.

## 2026-11-02 23:08 MSK — per-member wipe join-banner fix installed locally

Only kept-death remote insert restarts receive one-shot quiet member-arrival
records; genuine unmarked joins retain their message, including during recovery.
Removed wipe host-wide join-column override; guest local return override retained.
Production filter, binding and exact native-hook trampoline fixtures PASS.
Bundled DLL build exit=0 (4 existing warnings); delta deploy exit=0, 5 files.
Backup: D:/Games/Bloodborne/coop-dev/backups/wipe-arrival-filter-20261102-20261102-230857.
No game processes were running. No server/settings/save changes or game launch.
Both code trees synchronized; existing dirty work preserved, no broad commit.
Gameplay/UI validation pending. Details: docs/fixes/2026-11-02-wipe-arrival-filter.md.

## 2026-11-02 22:43 MSK — latest source package installed locally

Connection/address selector, independent server/game launch state and latest local
mod sources built/installed on PC (both exit=0). Backup latest-connection-selector-20261102-224246.
VPS current server source already matches, services active. Live validation pending.

## 2026-11-02 — latest full package installed on PC at 22:38 MSK

Full local working-tree package build exit=0 with BB_FAST_DEPLOY=1: bundled
BBSC DLL, native port, patched shadNet, launcher and frozen game server.
Installed into D:/Games/Bloodborne/Bloodborne Game Launcher, deploy exit=0,
5220 selected files copied. Backup: D:/Games/Bloodborne/coop-dev/backups/
latest-rules-coop-20261102-223756. No game/launcher processes were running.
Player 1/2/3 entry points retained; profiles, settings and saves unchanged.
Numeric defaults only: enemy HP 0, boss HP 50, damage 0, enemy/boss stagger 0
percent per guest; existing saved values are not migrated. Includes current
kept-wipe member-rebind changes; gameplay confirmation remains pending.
VPS already has matching LookupOnlineId patch and Python game-server source;
both services active since 18:14:58 UTC. No redundant VPS restart/update.
No file audit/verify-release or repeated gameplay tests. Build log:
bloodborne_pc/out/build-deploy.log. Pin remains 59ff490; build includes local
uncommitted changes, not a clean revision-only release.

## 2026-11-02 — kept-wipe local member rebind (built, installation pending)

Client recovery now runs native local member assignment + child forwarding once
per kept reload, even for equal parent ids, before restarting remote insert tasks.
An unready self task defers recovery; ordinary periodic checks remain idempotent.
Added native Stop caller observer; native queue limit / real disconnect policy
unchanged. Production-function fixture and actual Stop-prologue trampoline PASS;
bundled DLL build exit=0 (4 warnings), mod delta prepared. Installation initially
pending because Bloodborne.exe PID 35624 is open. No process termination, server,
save/settings changes. Unbound child in the recorded run remains a hypothesis;
gameplay confirmation required. See docs/fixes/2026-11-02-wipe-member-rebind.md.

## 2026-11-02 — local three-player run 21:56–22:15 MSK reviewed

Player 1 host, Players 2/3 guests; DLL built 21:06:13. Player 3 first native
negotiation closed at 22:08:42, delayed claim expired, signaling timed out;
successful world entry 22:10:24 (~110s after first ring). Boss wipe reload
completed for all, then Player 2 first entered leaving at 22:14:58.502, host
59.594; room 3 ended on VPS 22:15:03. Reliable backlogs 285/437/274 observed,
but hitting native 1001 limit / exact first stop cause unproven. VPS relay
reported no send errors at the event. No native Fault or Windows crash events;
all three later confirmed menu exit. Analysis only; no code/build/deploy/save
changes. Evidence: bloodborne_pc/out/coop-dev/runs/review-20261102-2217.
Details: BBSC/docs/fixes/2026-11-02-run-review-2215.md (workspace standalone tree).
## 2026-11-02 — 3+ player code review (analysis only)

Two production-function reproductions: party-wide dead count blocks repair of a
different revived remote; partial life roster hides a living native partner.
Also found host in-place revive treated as wipe reload (packet transition reproduced;
downstream warp reviewed, not executed). No production edits/build/deploy/game run.
See [3+ player review](fixes/2026-11-02-three-plus-review.md).

## 2026-11-02 — Cainhurst reveal and guest crown pickup (source only)

After host scene 25000010, guests now apply the original 12500810 world-effects
tail when local playback has ended and host completion is confirmed. Includes
geometry, collision, objects, character and SFX; late join/load also supported.
Crown event 12501803 now registers its native action-button prompt for guests;
completion is personal, preserving independent pickups. Both source trees updated.
Production fixture and all 82 EMEVD side-effect comparisons PASS; native helper
execution/gameplay remain unconfirmed. No build/install/save changes.
Details: docs/fixes/2026-11-02-cainhurst-crown.md.

## 2026-11-02 — Lecture Building guest exit doors

Both trees now reject guest ActionButtonParam 3200000/3200001 before native
acceptance/animation. Actual native rejection fixture PASS for both exits,
host/solo, other buttons and session states 0..8. Bundled DLL build exit=0.
No deployment; gameplay confirmation pending.
See docs/fixes/2026-11-02-guest-transition-doors.md.

## 2026-11-02 — prevent native guest key-bank reset (source + native fixture)

Found the native temporary key-bank switch/clear at 0x01AC5600, called by guest
actor setup at 0x01937A97. Local carried inventory now selects its persistent
key bank; NPC consumption and NG+ deletion remain native. Both trees updated.
Actual native bank-switch fixture PASS (baseline clears, fixed keeps keys across
reinitialization; consumption and unrelated inventories checked). Recovery journal
retained for legacy losses. Live gameplay confirmation pending.
Details: docs/fixes/2026-11-02-local-key-bank.md.

## 2026-11-02 — echo HUD acknowledgement corrected (source only)

Replaced the pre-update widget heartbeat / MenuMan+0x210 pending-reward
heuristic with a post-format observer at native 0x016570EC. It reads widget
+0x18C (the number passed to the primary text update). Only an active widget
with an unchanged displayed number and unchanged different balance for 3s
produces a warning. Hidden/absent widgets, loads, ongoing rewards and native
roll-up reset the timer. No currency or pending-reward memory is modified.
Both source trees updated. Extracted production C++ fixture PASS; production
mid-function trampoline fixture PASS. Native bytes inspected read-only in
installed CUSA03173 eboot: whole ADD RSP,0x88 before saved R13 is restored.
No DLL build/install or game confirmation. Prior `widget last ran never`
warnings do not prove a visible HUD failure. Which layout bypasses this native
widget, and whether its visible counter stalls, remain unconfirmed.

## 2026-11-02 — local member binding / reliable queue (source only)

Added periodic native local-member binding repair for stable living host/guest actors;
remote reinsertion no longer interrupts pending create/leave, and its missing timer
requires a continuous absence. Removed 30000-packet reliable-send limit override,
restoring native 1001 bound; bounded queue warnings now available in normal mode.
Targeted extracted production fixture PASS, including idle/idempotence and guards.
Existing pending-work fixture fails on finale stubs on HEAD too. Both trees updated.
No product build/deploy/game/save changes. Exact observed FPS/desync cause and gameplay
fix remain unconfirmed; native bound may end a broken whole session at 1001.
See docs/fixes/2026-11-02-member-binding-backlog.md.

## 2026-11-02 — LookupOnlineId compatibility fixed in source (unbuilt)

BBGL client command 41 is absent from the pinned packaged shadnet server;
its authenticated dispatcher returns Invalid=2 for unknown commands. Added
package patch 0006 with authenticated protobuf/database lookup and canonical
account identity, plus request name/packet context in client error diagnostics.
Four source/protocol checks PASS (full patch application, protobuf cross-wire,
auth/error guards, SQLite lookup). No product build/install/VPS change/game run.
This fixes a demonstrated package compatibility gap; it does not prove the cause
of the friends' recorded join failures or identify their running server binary.
A rebuilt server must later be installed on the host. Mod sources/pin unchanged.
See bloodborne_pc/docs/fixes/2026-11-02-lookup-online-id.md in workspace root.

## 2026-11-02 — incomplete join / cancellation clarified (diagnosis only)

Second guest enters room 161 with Matching2 peers active but remains state 4;
LeaveRoom follows after 30.009/30.010 s despite BBSC world packets. Native
0x8001000100000000 is hardcoded in cancellation/stop paths; task 13 logs late
cleanup, not the initial rejection reason. Bundled shadNet source lacks command
41 (LookupOnlineId), so dispatch returns Invalid; causal link to each failed
join and deployed VPS composition remain unverified. No production edits,
build/deploy/game run/save changes. See docs/fixes/2026-11-02-incomplete-join.md.

## 2026-11-02 — repeat HP death lifecycle (source + targeted fixture)

Native OnEvent_4000_Hp is consumed once per map load; kept in-place deaths do not
rearm it. Subsequent HP deaths now enter BeginBbscCoopDeath with the death text
at 500ms instead of the 3500ms repeat watchdog. Native scripts retain the 15s
safety fallback. Alive/load/session reset clears stale native-entry time, so a
rapid next death cannot inherit the previous script. Active death/release/curtain
is guarded against duplicate entry. Boss/wipe/invasion decisions stay in the
common death handler; native Lua event registration itself is not modified.
Both source trees updated. Extracted production lifecycle fixture PASS for host,
guest, rapid next death, native fallback, duplicate entry, load/HP/curtain/teardown.
Bundled DLL build completed exit=0. No deployment. Gameplay confirmation pending; no saves changed.

## 2026-11-02 — Parting Blank return ownership (source only)

Native send-home and stranded recovery share a game-thread return claim. Duplicate
native callbacks are skipped without releasing the active load locks. Stranded recovery
now waits 15 seconds after state 0 instead of 1 second, allowing the native 5-second
OnLeave_Limit to run first; it claims before native side effects and only after Lua
readiness checks. Ownership survives loading and resets on completed home arrival or
a fresh session. The existing 3-second synthetic OnLeaveMagic remains a startup safety
net; the cause of missing native item events is not established. Both source trees
updated; source control-flow checks only. No build, deploy or game confirmation.

## 2026-11-02 — remaining guest incorrectly sent home after peer Blank (source only)

The native OnLeave_Limit/send-home hook protected only own-world players. A living
state-6 guest with persistence still enabled could therefore execute a delayed
send-home caused by a peer leave. The hook now also protects a living resident
guest when no local teardown/quit is pending. Deferred leave/death lock release
accepts that resident too and rechecks the policy before releasing locks.
Local Blank (persistence suspended), host loss/state 0/7, joining, quit and dead
actors retain native recovery. Both source trees updated. Extracted production
hook/lock fixture and native-leave fixture PASS; no DLL/package build or deployment.
The reported three-player scenario still needs live confirmation.
Details: docs/fixes/2026-11-02-resident-guest-blank.md.

## 2026-11-02 — selectable host network (source only)

Connection/address selector and independent server/game launch busy state implemented.
17 targeted checks pass; source UI screenshots inspected. Build/deploy intentionally
not requested yet; real Radmin/public-IP hosting remains unverified. External
reachability checks and automatic router forwarding are not implemented.

## 2026-11-02 — black fade restored for deaths without reload (source only)

Restored native SprjFade black curtain around in-place co-op respawn: 0.6s
fade-out, revive after 0.7s, 0.5s black hold, 0.8s fade-in. Used by open-world
death and spectator respawn after boss victory; announcements wait for fade-in.
No synthetic loading menu. Real load/title/actor replacement cancels pending
revive; session end releases fade; failed revive falls back to native death load.
Watchdog ignores active curtain. Both source trees updated. Extracted production
C++ fixture PASS for host/guest timing, deferred notice, load/actor cancellation,
session end and failed revive fallback. No DLL build/install or game confirmation.

## 2026-11-02 06:46 MSK — final launcher + mod installed on both machines

User requested build/install latest local changes. Full fast package (native rebuild
included), BB_FAST_DEPLOY=1, exit=0. Bundled DLL build exit=0, 5 warnings. Includes
shared Dream ending / NG+ recovery, current polling/text edits and BBGL signaling
changes. Source base: BBGL879c0ee, bundledf2fca10 plus current working-tree edits.
PC deploy and laptop transfer/deploy all exit=0, 5219 files copied per machine.
Backups: PC D:/Games/Bloodborne/coop-dev/backups/final-launcher-mod-20261102-064527;
laptop C:/Games/Bloodborne/coop-dev/backups/final-launcher-mod-20261102-064553.
No games launched, no processes terminated, saves/settings unchanged. File audits
and verification disabled as requested. Build/install do not confirm gameplay.
Package: bloodborne_pc/dist/bbgl-1.0.0-windows-x64.zip; log out/build-deploy.log.

## 2026-11-02 — recover shared ending / NG+ without a home warp (source only)

Supersedes the previous ending-to-home implementation. Per-character append-only
.finale journal retains the complete scene request, host target cycle and phase.
Checksum/phase/scene/variant/cycle checks reject corrupt records; incomplete tails
are truncated before another append. Completed scenes resume the NG commit instead
of replaying; incomplete scenes are replayed after reload. Cycle assignment is
absolute, preventing repeated increments across crashes. Native save result 0 plus
idle save manager is required before durable phase-4 acknowledgement.
Both native send-phantom-home and stranded fallback are suppressed for an active
finale; after native Stop the local actor is adopted in place, old world/progress
journals drain, then host ending flags/target cycle and native save are requested.
No home respawn selection or home StageTransition is issued by this path.
Both trees updated. Static event/native-byte/source-order checks PASS. No product
build, installation, live save edits or game run. Whole translation-unit compilation,
actual movie replay after a crash, in-place role recovery and native NG load remain
unverified. Power-loss durability beyond stream flush is not claimed.

## 2026-11-02 — host search interval 1s (source only)

User requested only host search acceleration. ConfigureBbscSummonPolling now
writes ServerInfo+8A0 = 1s; sign/create and guard remain 2s, all other timers
unchanged. Both mod trees and existing native fixture expectation updated.
No build, fixture compilation, deployment or game launch. Gameplay pending.

## 2026-11-02 — intermittent join: signaling generation guard (source only)

BBGL ignores stale Ack/Established/Close from a previous peer connection instead
of modifying the replacement selected by online ID. Production-handler fixture
PASS; HEAD baseline fails as expected. Activation/readiness fixtures PASS;
pre-existing changes preserved. No product build/deploy or game launch.
Mod source/pin unchanged. Exact cause of recorded native rejection at 06:03:02.838
remains open; intermittent join is NOT marked closed.
Details: bloodborne_pc/docs/fixes/2026-11-02-signaling-generation.md (workspace root).

## 2026-11-02 — shared Dream finale / NG+ (source only, unbuilt)

User superseded the guest-return-only design: host chooses the ending, guests fight
and view scenes, then all enter the host next NG cycle. Added selective m21 boss
flag borrowing, serialized scene replay, native Remo start/completion observation,
departure/follow deferral while the guest ending plays, and guest ending commit after
native departure/home restoration and the old shared-progress journal drain.
Next cycle travels in the existing cutscene packet reserved byte; native AddClearCount
and the m21 terminal ending flags are applied after the local scene. Host dialogue
remains authoritative; guest terminal story events are not opened.
Both source trees changed. NO DLL/package build, install, game run or save changes.
Static game-data/native-byte checks only; full translation-unit compilation and live
three-ending/skip/host-first/NG transition validation remain pending. Crash during
the pending ending-to-home interval is not yet journaled for automatic completion.

## 2026-11-02 — original co-op item text (source only)

Updated RU/EN bell prompts, searches, menus, tutorials and original goods 200/205/225/111
summaries/descriptions (categories 20/24). Category 10 names remain native; names checked
against installed engus/rusru item.msgbnd read-only. No retired kit/duel instructions.
English generator validates menu IDs and item description IDs against game FMGs;
both generated tables contain 199 matching entries. Launcher bell instructions and
server notice use original names too. Both mod source trees updated; no build/deploy
or in-game layout confirmation in this text edit.

## 2026-11-02 05:43 MSK — latest launcher/mod installed on both machines

After user closed game/launcher, retried deployment of the already built full fast
package. PC and laptop deploy exit=0, 5219 files copied each; no rebuild or file
audit. Includes native kit duplicate suppression and current local source changes.
Backups: PC D:/Games/Bloodborne/coop-dev/backups/latest-launcher-mod-20261102-054241;
laptop C:/Games/Bloodborne/coop-dev/backups/latest-launcher-mod-20261102-054242.
Supersedes preceding deferred installation status. Settings/saves unchanged;
no game launched. Gameplay confirmation pending.

## 2026-11-02 05:42 MSK — latest launcher/mod built; installation deferred

User requested latest launcher and mod on both machines. Full fast package with
SKIP_BUILD=1 completed exit=0 (native sources unchanged); bundled DLL build exit=0,
5 compiler warnings. Includes current local source changes, native kit duplicate
suppression and prior consumable award fix. Base mod HEAD f2fca10 (working tree
changes included); standalone HEAD 5c4e124. No source commits/pin changes made.
PC deploy refused because Bloodborne launcher running. Laptop archive transfer
completed exit=0; deploy backed up selected files then refused at second stopped
check (GAME_OR_LAUNCHER_RUNNING), before copying replacement files. Neither
installation updated. Both need game/launcher closed before retry. No processes
terminated, no settings/saves changed. Package ready in dist/bbgl-1.0.0-windows-x64.zip.

## 2026-11-02 — native kit duplicates suppressed (source only)

Notebook remains the sole source of goods 200/205/225/111. Native award hook
skips lots containing only these goods and sets their get flags so gift events
finish. Mixed/unrelated lots are preserved. Shop row-result hook hides these
goods from native stock only at the list-builder call site; other categories,
price lookups and progression goods stay unchanged. Both source trees updated.
Targeted native kit lot/shop C++ fixture and original bell parameter fixture PASS.
No DLL build/deploy or gameplay confirmation. Existing duplicates are not removed.

## 2026-11-02 05:34 MSK — quit movement gate fix installed both machines

User reports movement still possible during latest menu exit. Earlier native
DisableMove implementation is NOT gameplay-confirmed. Native wrapper/address/ABI
are correct per read-only eboot; old Hold skipped global+8 loading interval while
same living character could remain active. No flag readback in old logs, so exact
reset writer/timing is not established. Added byte-verified hook before native
CMP [r12+111],0 at01513EB5; reassert native DisableMove for exact captured local
character/control through pending/title, even during loading. Normal movement,
remotes/replacements unaffected; cancellation preserves prior restriction.
Production menu fixture and actual CMP/JNE trampoline PASS. Standalone5c4e124 /
bundledf2fca10 / port879c0ee. DLL build exit=0 (3 existing unused warnings).
Five-file delta copied to stopped PC and laptop, both exit=0. Backups labelled
quit-movement-gate-20261102-053428 (PC) / -053436 (laptop). No games launched,
saves/settings unchanged. Build also includes pre-existing unstaged consumable
award fix in both trees; that work was preserved outside these commits.
Gameplay PENDING: hold movement input after confirmed System exit as host/guest;
character must stay still through title transition, then move normally on Continue.
Details docs/fixes/2026-11-02-quit-movement-gate.md.

## 2026-11-02 05:29 MSK — optimization work deferred by user

User explicitly ends optimization work for now; resume only on a new request.
Consolidated status, measured wins, unresolved stutters, versions, raw log paths,
thermal exclusions and future investigation starting point: docs/OPTIMIZATION-STATUS.md
(in standalone and bundled mod trees). Latest combined run did not prove another
FPS/stutter gain; do not mark remaining owners/Bell/NPC stalls fixed. Existing
logs retained. No code/build/deploy/settings/save changes in this wrap-up.

## 2026-11-02 — repeated Madman's Knowledge: source fix, NOT BUILT

Recorded one-time stackable goods awards are now suppressed on repeat outside
chalices, including after consumption. First/different lots and unflagged drops
remain allowed; missing unique recovery and chalice exception preserved.
Both source trees updated; production-function fixture PASS. No DLL/package build,
installation or save changes. Gameplay pending; supersedes earlier investigation-only
status. Details: docs/fixes/2026-11-02-repeated-consumable-awards.md.

## 2026-11-02 05:26 MSK — combined capped60 review: no further stutter improvement

Both collected in out/coop-dev/runs/perf-combined60-20261102,3 files each,
no warnings/changed copies. DLL built05:09:41. Thermal tail excluded from05:22:10
conservatively, before visible12–13FPS collapse; no temperature/frequency sensors.
Matched roles remain PC guest/laptop host. Early pair65s vs old70s: PC59.36->58.45FPS,
>50ms/min5.99->7.37; laptop52.45->51.03FPS,16.25->30.39 events/min. Laptop worst
149.99->117.54ms, fewer >100ms but more50–100ms frames. No general gain proven.
Extended first pair160s also retained, PC56.76FPS/26.94 events/min; laptop48.99/
23.19. PC burst05:14:58–05:15:23 not excluded as throttle. Pre-tail owners maxima
laptop15.34->20.87ms, PC13.24->16.47ms. Sustained-profile means did not improve:
owners PC110->148us/frame, laptop197->229 (different report coverage/scenes).
No hundreds-ms scaling calls; preparation PC2ms/laptop5ms, no broad scan regression.
Details docs/fixes/2026-11-02-perf-combined60-review.md + run analysis/metrics.
Do not claim snapshot optimization improved overall runtime. Next: detailed
memory guard/query timing correlated with slow frame events. No source/build/
deploy/settings/save changes during this analysis.

## 2026-11-02 05:10 MSK — combined latest rebuilt and installed on both machines

User explicitly requested build/install with all neighboring changes, superseding
prior no-build instruction. Standalone cfed133 / bundled62b3200 / port17fde5d.
Includes guarded table/NPC snapshots, research-only detailed bell diagnostics,
idle owner validation, repository scaling, book/refund policy, single-load join,
boss-reload guard on quit, and removal of custom loading/death overlays.
Bundled DLL build exit=0 (3 unused warnings). Existing targeted fixture results
retained, not rerun for deployment. No new native/launcher runtime changes, so
mod-only delta. Five files installed on both stopped machines, both copy exit=0;
no installed-file audit per fast preference. Backups:
PC D:/Games/Bloodborne/coop-dev/backups/combined-latest-20261102-051031;
laptop C:/Games/Bloodborne/coop-dev/backups/combined-latest-20261102-051039.
No game launched, settings/saves unchanged. Runtime combined behavior PENDING.
Test reference2026-11-02T02:10:39Z /05:10:39MSK is deployment completion, not run start.
Keep60FPS cap; next same-route/role sample plus join/leave, death/wipe and host
menu exit after boss. Collect both rotated logs. Earlier SOURCE ONLY status is
historical; explicit build now completed. Performance/presentation interactions
need runtime observation, no FPS gain claimed from build success.

## 2026-11-02 — guard/snapshot optimizations; this chat did not build

User requested remaining-stutter source edits, DO NOT BUILD yet. This chat changed
both source trees and ran only isolated perf_policy/runtime_perf/guest_bells C++
fixtures (PASS), no production build/package/deploy/game launch or settings/saves.
Table/NPC reads now copy fields from validated spans; live owners/type/bounds and
NPC permissions/reload guards remain. Bell normal-path predicates avoid detail
strings/map queries/mutex/timeline; detailed reasons remain research-only.
CONCURRENT AUDIT: shared HEAD changed externally to bd47d35/cceaae3 and already
contains these performance edits (verified via git show of the committed file).
External DLL build timestamp05:05:47, exit=0; another HANDOFF entry records
presentation deployment. Its assertion that perf edits were excluded conflicts
with actual commit contents. No external commit/build was undone by this chat.
Remaining local edits: fixture tests, docs and a research logging comment.
Runtime performance impact still unmeasured; do not state no DLL changed globally.
Details docs/fixes/2026-11-02-perf-guard-snapshots.md.

## 2026-11-02 05:06 MSK — legacy presentation removed from mod

Standalone bd47d35 / bundled cceaae3 / port pin 849296a. Removed custom
load cover, death curtain, native loading UI open/close helpers, dead ImGui
loading layer, per-frame ticks and load_cover switch in runtime/launcher metadata.
Uses found: host-follow warp, guest wipe load, in-place death respawn;
respawn now executes directly with existing world guards and fallback.
Native game loading remains owned by StageFlow. No custom logo/plate code remains.
Targeted home_return, load_readiness, boss_load_cleanup, stop_phases, menu_quit,
follow_arrival PASS; bundled DLL build exit=0 (two existing unused warnings).
Delta copied to stopped PC and laptop with backups remove-load-overlays; exit=0.
No settings/save changes. Gameplay confirmation pending, especially death/wipe.
Parallel standalone performance changes excluded from this commit/build.

## Installation 2026-11-02 05:01 MSK
Bundled DLL build exit=0 (two pre-existing unused warnings). Five-file delta installed on both stopped machines, copy exit=0. Backups: PC D:/Games/Bloodborne/coop-dev/backups/host-menu-boss-20261102-050137; laptop C:/Games/Bloodborne/coop-dev/backups/host-menu-boss-20261102-050146. No file audit per preference. First laptop invocation stopped before copying due to missing explicit delta file list; corrected invocation succeeded. Gameplay pending: laptop host / PC guest, quit host to title shortly after boss clear; title must remain until explicit Continue. No game launched, saves/settings untouched.

## 2026-11-02 — host menu exit raced delayed boss-clear reload

Latest run collected from PC and laptop under bloodborne_pc/out/coop-dev/runs/host-menu-20261102 (3 files each, no collector warnings). Laptop was host, PC guest. Host log: boss reward 04:55:38, System Yes 04:55:51.306, BlockClear2_1 51.446, save/Stop 51.505, direct title request 51.808, unexpected world construction 04:56:14.995; second exit at 04:56:24.734. The old message claiming Continue is not evidence that the user selected Continue.

Production boss-clear hook previously returned as soon as session stopped, allowing delayed BlockClear2_3 native reload to compete with confirmed menu exit. Guard now precedes session/role checks: skip delayed leave and home callbacks while quit intent exists, for host and guest; do not arm boss recovery during quit. Normal boss behavior retained. This closes an identified code race; logs alone do not establish all native request writers.

Standalone c41723b / bundled b80d19f / port pin 554ebdd. Production boss_quit and menu_quit fixtures PASS. Build/deploy status below; gameplay confirmation pending. No saves/settings changed.

## 2026-11-02 05:01 MSK — initial join black cover removed, installed both machines

Standalone 4ab8575 / bundled e5c149b: removed StartBbscLoadCover("summon")
from JoinSession_White; native summon loading UI and follow/wipe covers unchanged.
Bundled DLL build exit=0 (two existing unused warnings); diff --check PASS.
Five-file delta copied to stopped PC and laptop, exit=0 with backups labelled
join-no-black-20261102-050055 (PC) / -050110 (laptop). No settings/save changes.
Concurrent bundled HEAD advanced to b80d19f during this work; it includes e5c149b.
Gameplay confirmation pending: client should remain visible until native loading.

## 2026-11-02 04:59 MSK — idle owners capped60 comparison, thermal tail excluded

Collected both machines in out/coop-dev/runs/perf-idle60-20261102,3 files each,
no warnings/changed copies. DLL built04:43:41 (latest23677dc includes idle plus
book/bell changes). User reports late laptop throttling; sharp FPS break around
04:55:00, excluded all later data, no temperature/frequency evidence collected.
Matched alone105s: laptop >50ms/min43.91->3.99 (~-91%), FPS54.20->52.52;
PC58.69->58.93FPS, >50ms/min2.15->2.28 (rare-event variation).
Owner profiling laptop510.07->168.25us/game frame (-67%), PC168.18->114.05(-32%).
Individual pre-tail owners calls still15.34ms laptop/13.24msPC; repeated overhead
reduced, not hard per-call latency. Scaling no hundreds-ms holds observed pre-tail.
Roles REVERSED in pair: PC guest/laptop host. New early pair70s: PC59.36FPS,
laptop52.45FPS, >50ms/min5.99/16.25. Do not compare directly against old laptop
guest43.50FPS/94.19 events/min as same-role improvement. Death/wipe and thermal
end excluded. Details docs/fixes/2026-11-02-perf-idle60-review.md and run
analysis.md/segment-metrics.json. No source/build/deploy/settings/save changes.

## 2026-11-02 04:44 MSK — book / latest bell fix installed on PC and laptop

Built bundled 23677dc (standalone cd67d80; port pin 73f2da3), build exit=0,
two existing unused-variable warnings. Includes Vileblood Register removal
from automatic kit, native unanswered-bell Insight refund suppression, and
previous idle scaling / repository / single-load join changes. Game code clean
in both trees at build; original_bells test changes remain local, already PASS.
Five-file delta deployed on both stopped machines, copy exit=0; no installed
file audit, no settings/save changes or game launch. Backups:
PC D:/Games/Bloodborne/coop-dev/backups/book-bell-latest-20261102-044425;
laptop C:/Games/Bloodborne/coop-dev/backups/book-bell-latest-20261102-044428.
Gameplay confirmation pending. Existing books are retained. On a character
without the book, kit must not add goods 130; natural acquisition stays vanilla.
Reference 2026-11-02T01:44:28Z is install completion, not game start.

## 2026-11-02 — bell Insight refund removed in code

Standalone cd67d80 / bundled 23677dc / port pin 73f2da3.
Suppress only common event 9183's 2004[8](10000,4680) refund, return success.
Removed timed currency correction and bell-pending marker handling. Boss/chalice
rewards unchanged. Production-hook fixture and original_bells PASS; bundled DLL
build exit=0 (two pre-existing unused warnings). No installation or save changes;
user requested code correction only. Runtime pending.
Details: docs/fixes/2026-11-02-bell-insight-refund.md.

## 2026-11-02 — Vileblood Register excluded from automatic kit

Latest PC mod log bbsc-mod-20261102-042704-14832.log at 04:31:02.986
explicitly records kit adding goods 130 to carried slot 78, alongside bells.
Removed 130 from BbscKit in standalone and bundled sources: no automatic grant
or kit parameter mutation; vanilla acquisition remains unchanged. Existing items
are not removed. Targeted test_original_bells production C++ fixture PASS:
exact co-op IDs 200/205/225/111, book row untouched, repeated preparation.
Source fix only; build/deploy and gameplay confirmation pending.

## 2026-11-02 04:41 MSK — idle owner validation reduced, installed both machines

Standalone0d71cad / bundled1f51244 / port pince93a3f. Unchanged complete scaling
key returns before repository owner queries;1Hz idle validation, immediate after
load generation, and mandatory current owner validation before every write batch.
No cached row writes happen during skipped idle frames. No formulas/settings change.
Production scaling_repository/pending_work fixtures PASS:10k idle calls no lookups,
999ms skips/1000ms validates, load forces immediate check, pending/role/expiry/
owner replacement/unload/fallback cases retained. Diff --check PASS.
DLL build exit=0 (2 existing unused warnings). Delta5 files installed on stopped
PC and laptop, both copy exit=0, no file audit. Backups scaling-idle-20261102-
044133 (PC D:/Games/Bloodborne/coop-dev/backups), -044139 (laptop
C:/Games/Bloodborne/coop-dev/backups). No game launch/save/settings changes.
Runtime effect PENDING same capped60 test, PC host/laptop guest,2–3min same route
plus exit/rejoin. Reference2026-11-02T01:41:39Z/04:41:39MSK is deployment completion,
not gameplay start. Compare against perf-cap60-20261102, not uncapped FPS runs.
Details docs/fixes/2026-11-02-scaling-idle-owners.md. Slow individual OS queries
can still exceed budget; no hard latency guarantee claimed.

## 2026-11-02 04:38 MSK — capped60 run: repository/scaling improvement observed

User reports much better feel, cap60 FPS kept. Collected both machines in
out/coop-dev/runs/perf-cap60-20261102,3 files each, no warnings/changed copies.
DLL built04:09:10. Active table preparation PC1ms/laptop4ms versus previous
laptop282.6s full background scan (different scope/work by design, not a main hold).
Laptop scaling max361.81->16.87ms, no published scaling calls>50ms. Remaining
max is almost entirely table owners16.866ms; owners869 calls>8ms across run.
Paired selected75s: PC57.76FPS (cap60), laptop guest43.50FPS, >50ms/min94.19
vs previous137.17; no >100ms frames in current paired selection. Previous guest
37.52FPS uncapped; cap/scene/load differences prevent pure optimization attribution.
Alone laptop54.20FPS, >50ms/min43.91. No new offline run. Full logs include
startup/other long intervals (PC8.684s, laptop950ms) outside gameplay selection;
not claimed fixed. Bell33.28ms/NPC25.32ms and other holds remain.
Details docs/fixes/2026-11-02-perf-cap60-review.md + run analysis.md/segment-metrics.json.
User qualitative improvement and targeted scaling runtime improvement supported;
all guest stutters NOT closed. Next candidate owners query cadence/memory checks.
No code/build/deploy/save/settings changes during collection/analysis.

## 2026-11-02 04:10 MSK — active-table scaling built and installed on both machines

Standalone244ae80 / bundled e3a6c6d / port pin910ddd0. Replaced process-wide table
search with active repository lookup for scaling, kit and solid NPCs; removed
second kit copy-scan worker. Parameter index/row reads validate spans once with
checked fragmented fallback. Tick validates active owners, skips unloaded params,
reprepares replacements and preserves original armor on same-owner retries.
Armor uses one current-span check per batch; direct copies inside checked span,
<=128 rows; fragmented fallback<=8 rows, time checked after every row (1ms target),
failed writes retained for retry. No hard guarantee against slow OS calls/logging.
Added nested scopes table owners/selection/effect writes/armor writes/report.
Target fixtures scaling_repository, pending_work, perf_policy, original_bells PASS.
Build exit=0 with2 pre-existing unused warnings. Native telemetry unchanged.
Mod delta installed5 files on each stopped machine, both copy exit=0. Backups:
PC D:/Games/Bloodborne/coop-dev/backups/scaling-repo-20261102-041003;
laptop C:/Games/Bloodborne/coop-dev/backups/scaling-repo-20261102-041011.
No installed file verification per preference. No game launch/settings/save changes.
Runtime FPS/stutter improvement remains PENDING. Next: same route/settings,
online alone then PC host/laptop guest2–3min; separately leave/rejoin and reverse
roles. Record timestamps, verify scaling/NPCs/bells, collect both rotations.
Test reference2026-11-02T01:10:11Z /04:10:11 MSK is install completion, not game start.
Details docs/fixes/2026-11-02-scaling-repository.md. Earlier perf-after analysis
retained as baseline; optional Dream tool event-code searches are unchanged.

## 2026-11-02 03:59 MSK — post-optimization performance collected, guest stalls persist

Both machines collected: out/coop-dev/runs/perf-after-20261102, 3 files each,
no warnings/ChangedDuringCopy. Latest DLL built 03:50:34 includes single-load join
2d68a7d in addition to perf fixes; both logs online, no new offline run.
Matched roles: PC host 85.76 ->84.59 FPS; laptop guest 39.10 ->37.52 FPS;
guest >50ms frames/min 131.66 ->137.17. No general FPS/stutter improvement proven.
Alone laptop 54.74 ->53.27 FPS, >50ms/min 67.47 ->51.20, but longer outliers remain.
SharedProgress laptop max 1314.43 ->41.48ms (old seconds not repeated; different
journal contents); real backup still 49ms laptop /90ms PC. Scaling still361.81ms,
10 calls >50ms in one report. NPC per-call weighted cost improved 5.75->3.33us;
Bell maximum still52.68ms. Overall selected mod reports6.61->5.08ms/frame,
without game FPS gain. Laptop background scaling scan completed03:57:07 after
282.6s (not main-thread hold); it ran throughout first paired segment, unlike
previous baseline, limiting causality. Roles swapped late, only10s comparable
post-load windows, no old baseline for reverse roles. Full online averages skewed
by menus/loading and must not be advertised as improvement.
Details: docs/fixes/2026-11-02-perf-after-review.md and run analysis.md/segment-metrics.json.
No code/build/deploy/save/settings changes in analysis. Next: background scan
cost, scaling subphase timing/budget overshoot, memory queries in Bell/NPC.

## 2026-11-02 03:51 MSK — single-load cross-map join installed

Standalone 21d3c73 / bundled 2d68a7d / port pin fa89ba0. Removed the explicit
post-summon RequestBbscSessionWarp("join") and obsolete WARP_JOIN switch/state.
Native connect-first placement already loads the host destination; final in-map
placement remains gated by host map identity, freshness and chalice readiness.
Wrong-world scoped-follow recovery remains enabled (may require a recovery load).
Production join destination fixture + follow arrival fixture PASS. DLL build exit=0
(two pre-existing unused warnings); 5-file delta installed on stopped PC + laptop,
copy exit=0. Backups single-join-load-20261102-035117 (PC) / -035128 (laptop)
under each machine's Games/Bloodborne/coop-dev/backups. Fast deploy, no installed
file audit. No game launch, save/settings changes. Runtime PENDING: connect from
a different map, expect one summon load and arrival beside host; check lighting
and streamed geometry because the removed reload was a historical lighting workaround.
Test reference 00:51:28 UTC / 03:51:28 MSK is installation completion, not game start.

## 2026-11-02 03:48 MSK — performance fixes built and installed on PC + laptop

Standalone 8f9e6fa, bundled 9d43fb7, port pin ba5956c. All four requested areas
changed: progress no-op preflight + skip duplicate backup/filtering (real mutations
still backup synchronously; failure retains journal); scaling armor in <=128-row
batches / 2ms cooperative checks; reload-cleared file event indexes + validated
instance cache; non-bell early return and validated-stack reads in bell policy.
Targeted production fixtures runtime_perf, guest_bells, pending_work,
shared_progress_policy, perf_policy PASS. New cache/no-op followup runtime fixture
PASS; mod build exit=0 (two pre-existing unused warnings). Native unchanged.
Delta installed 5 files each, stopped machines, both copy exit=0. No installed-file
verification per fast preference. Backups perf-bounded-20261102-034754 under
PC D:/Games/Bloodborne/coop-dev/backups and -034800 under laptop
C:/Games/Bloodborne/coop-dev/backups. Settings/saves unchanged, no game launched.
Includes previously built 2f07242 native DisableMove/no forced quit loading screen.
Runtime FPS gain/stutter removal still PENDING matched test. Scenario: offline,
online alone, PC host+laptop guest, same route/settings; separately join/leave,
NPC talks/bells, exit to title. Test reference 2026-11-02T00:48:00Z (03:48 MSK),
installation completion, not actual gameplay start. Keep prior raw benchmark logs.
Limits: real save backup I/O still synchronous; stagger armor rows transition over
multiple ticks; 2ms check is cooperative, not a hard cap on an OS call.
Details: docs/fixes/2026-11-02-perf-bounded-work.md (both mod checkouts).

## 2026-11-02 03:39 MSK — performance run collected and analyzed

Both PC/laptop collected in bloodborne_pc/out/coop-dev/runs/perf-20261102-review;
no warnings or changed-during-copy files. Deduplicated PC game sources.
Selected gameplay: PC offline 88.63 / alone online 93.85 / paired host 85.76 FPS;
laptop 68.52 / 54.74 / paired guest 39.10. Different scene/route not independently
controlled, so observed deltas are not exact causal mod cost. Laptop >50ms frames
0 / 67.47 / 131.66 per minute. All segment metrics in segment-metrics.json.
Confirmed long wall scopes: laptop SharedProgress 1314.43ms (03:33:34 backup/merge,
1324.71ms flip), Scaling 372.13/461.50/325.52ms; frequent NPC event localization
and ResponderBell processing. 2429.18ms flip not wholly explained by those scopes.
No proof of a specific mutex owner; scope wall time includes scheduling/waiting.
Report: docs/fixes/2026-11-02-perf-runtime-review.md (standalone) and run analysis.md.
No source modifications/build/deploy or save/settings changes during analysis.
Next optimization priorities: split durable file preparation from game memory commit,
bound scaling batches, index event ranges and measure query cache misses; preserve
save ordering and load safety. No measured optimization gain yet.

## 2026-11-02 03:39 MSK — quit DisableMove/no-logo delta installed on both machines

After user closed both games/launchers, prepared bundled 2f07242 delta installed
successfully on PC and laptop: 5 files each, copy exit=0. Previous refusal is
historical; installation now complete. Standalone 9f65a93 / port pin858969e.
Backups PC D:/Games/Bloodborne/coop-dev/backups/quit-disable-move-20261102-033922;
laptop C:/Games/Bloodborne/coop-dev/backups/quit-disable-move-20261102-033923.
No rebuild/repeated tests/file verification, saves/settings changes or game launch.
Runtime native movement/menu restriction, camera and no added logo screen pending.

## 2026-11-02 — quit screen removal/native DisableMove BUILT, NOT INSTALLED

Standalone 9f65a93 / bundled 2f07242 / pin 858969e. Latest run collected both
machines: bloodborne_pc/out/coop-dev/runs/quit-native-review-20261102.
Removed explicit world loading screen before title (source of added logo UI).
Replaced synthetic death markers with native Lua DisableMove on local entity10000;
menu brake retained; no pad/camera modification. Original movement restriction
restored on cancellation for same character/control object. Target fixture PASS,
bundled DLL build exit=0; staging + out/mod-delta.zip prepared, delta sent laptop.
Both installs REFUSED before mutation: GAME_OR_LAUNCHER_RUNNING. PC observed
bb-probe PID13284, Bloodborne PID28896/38588. No process stopped, no live files
replaced, no save/settings changes. Close game/launcher on both, then deploy delta.
Runtime movement/menu/camera/no-logo outcome remains PENDING.
Details: fixes/2026-11-02-quit-disable-move.md.

## 2026-11-02 03:27 MSK — diagnostic performance build installed on PC + laptop

Explicit user deployment request. Installed prepared perf-research-delta.zip,
6 files per stopped machine (native bb-probe + bundled mod + metadata), both exit=0.
Port 02bf0f4 / bundled d5a2322; no rebuild or installed-file verification.
Backups: PC D:/Games/Bloodborne/coop-dev/backups/perf-research-20261102-032649;
laptop C:/Games/Bloodborne/coop-dev/backups/perf-research-20261102-032703.
Settings/saves unchanged; no game launch. Runtime measurement pending.
Test reference: 2026-11-02T00:27:03Z (03:27:03 MSK), deployment completion,
not actual gameplay start. Planned offline / coop alone / paired route;
roles chosen by user, record actual segment times and collect both rotated logs.

## 2026-11-02 — FPS / stutter research build prepared

User requested matched offline/co-op FPS and long game-thread-hold investigation.
Standalone 666a03a, bundled d5a2322, port 02bf0f4. Native build and bundled DLL exit=0;
analysis fixture passed weighted windows/segment exclusion/missing capture.
Staging refreshed; bloodborne_pc/out/perf-research-delta.zip contains loader + mod delta.
No installation, game launch or settings/save changes. Runtime measurements PENDING.
New guest-flip telemetry default on (BB_PERF_CAPTURE=0 disables), five-second FPS,
frame histogram percentiles/counts and epoch timestamps for >50 ms frames.
BBSC reports rare >8/16/50 ms scope calls separately from top-ten cost.
Scope time is not proof of mutex hold; nested costs overlap. Timeline synchronous
flush under mutex is a candidate only. No measured improvement claimed.
Scenario and limitations: bloodborne_pc/docs/COOP-PERFORMANCE-RESEARCH.md.
Next: matched warmed route offline / coop alone / paired host+guest; record segment
times, collect both machines including rotated logs, correlate stalls with lifecycle.

## 2026-11-02 03:14 MSK — latest version WITH launcher installed on both machines

User requested new version together with launcher. Rebuilt launcher/package using
BB_FAST_DEPLOY=1 package.sh, exit=0; reused already-built current native binaries
(03:03, including d97ff1d window mouse recapture) and bundled d8741ed mod DLL.
Package includes current working-tree HomePage.qml. Port HEAD a1eecbb.
Both stopped machines: 5214 files copied, exit=0, backups saved; no file/hash/
manifest verification per fast preference. PC backup latest-with-launcher-
20261102-031338 under D:/Games/Bloodborne/coop-dev/backups; laptop -031405
under C:/Games/Bloodborne/coop-dev/backups. Settings/saves unchanged, game not
launched. Native quit restrictions runtime validation remains pending.
Build log bloodborne_pc/out/launcher-package-latest.log.

## 2026-11-02 03:11 MSK — native quit restrictions installed

User explicitly requests death-like character restriction with free camera,
not a pad input block. Pad filtering removed. Native death/leave pending,
menu brake and flag4047 held during confirmed exit; cancellation restores
prior values, real loading owns native reset. No HP/death penalty changes.
Standalone 17c3f99, bundled d8741ed, port pin a1eecbb. DLL build exit=0;
production menu_quit fixture PASS. Delta installed stopped PC/laptop: 5 files
each, copy exit=0; no file verification per preference. Backups quit-native-state-
20261102-031058 (PC D:/Games/Bloodborne/coop-dev/backups) and -031105
(laptop C:/Games/Bloodborne/coop-dev/backups). No game launch/save/settings edits.
Actual no-movement/no-menu/free-camera behavior PENDING user runtime check.
Prior pad-block success statements superseded by user's failed 03:00 run.
Review logs: bloodborne_pc/out/coop-dev/runs/quit-input-review-20261102.
Details: fixes/2026-11-02-quit-native-restrictions.md.

## 2026-11-02 02:58 MSK — quit input/loading installed on PC + laptop

Standalone 73f2847, bundled e98fbfd, port pin ae94f76. DLL build exit=0.
Confirmed Yes blocks pad buttons/sticks/triggers through save and native Stop.
At native session closure, open loading screen once before direct title request;
cancel restores input, title handoff releases pad so menu/Continue work.
Production menu_quit, quit_input, hook_resume PASS. Both stopped devices received
5 delta files, copy exit=0; file verification disabled per fast-deploy preference.
Backups PC D:/Games/Bloodborne/coop-dev/backups/quit-input-loading-20261102-025831;
laptop C:/Games/Bloodborne/coop-dev/backups/quit-input-loading-20261102-025837.
No game launch or save/settings changes. Runtime confirmation pending:
confirm Exit Game as host and guest, try movement/actions during disconnect,
expect loading immediately after session closure, then verify title/Continue input.
Logs both machines: bloodborne_pc/out/coop-dev/runs/menu-20261102-0248.
Details: fixes/2026-11-02-menu-input-loading.md.

## 2026-11-02 02:46 MSK — join world guard + shared key receipts installed

Standalone e368f45, bundled deae891, port pin 762c374. Bundled DLL build exit=0.
Production join destination/freshness/map/mount fixture and chalice scope PASS;
shared-key receipt and inventory barrier checks passed during preceding change.
Delta installed on stopped PC and laptop: 5 files each, copy exit=0,
file verification disabled per preference. Backups join-world-keys-20261102-024630
(PC D:/Games/Bloodborne/coop-dev/backups) and -024639
(laptop C:/Games/Bloodborne/coop-dev/backups).
Includes previous key fix; earlier unbuilt/uninstalled statements are historical.
No game launch, save/settings changes. Runtime validation pending:
join host already in chalice, exit/rejoin, host Dream-to-chalice follow,
then reload and check shared keys show only on first receipt.
Details: fixes/2026-11-02-chalice-join-wrong-world.md.

## 2026-11-02 — initial join cannot teleport between worlds

Evidence: keys-20261102-0231 laptop log, 02:35:38–42. Native summon
created the character in Dream (0x15000000), then join teleport moved it
from (-15.11,-5.11,-11.24) to dungeon host (39.86,31.50,-52.97).
At 02:36:16 guest died; recovery correctly refused in-place revive in the
wrong world. First follow at 02:34:36 had injected the loader and arrived
in m29; generic m29 missing optional resources also occur on host and do
not establish a loader failure.

Fix: require a fresh host follow map before using any remote transform.
World mismatch hands initial join to scoped follow without teleport.
Dungeon placement requires same map and mounted current revision/key.
Non-chalice adjacent resident blocks remain allowed within one area.
No changes to death policy, altars, saves or network protocol.
Production test_join_destination and test_chalice_scope PASS. Game validation pending.
Includes preceding shared-key receipt fix in the same pending DLL.

## 2026-11-02 — повторная выдача shared keys, прогон 02:30–02:37 МСК

Логи обеих машин: bloodborne_pc/out/coop-dev/runs/keys-20261102-0231.
На клиенте семь shared keys повторно показаны в 02:33:51, 02:34:39,
02:36:31. В 02:35:42 те же предметы восстановлены K2-trip без окон.
Причина: shared-key tick мог опередить ledger reconciliation текущей загрузки;
постоянная принадлежность проверялась по временному phantom inventory.
Дополнительно FinishBbscTripAtHome удалял receipts через 60 секунд дома/при join.

В исходниках обоих checkout: shared keys ждут BbscGuestLoadItemsReady;
receipt из сериализуемого per-user/per-slot trip journal означает полученный
предмет, восстановление без popup/новой записи Given. Shared-key receipts
сохраняются при FinishBbscTripAtHome; запись Key гарантированно попадает в journal.
Формат файла не изменён. Старые уже удалённые receipts восстановить задним числом
невозможно: при наличии предметов join снова фиксирует их в журнале.
Проверки test_shared_keys.py и test_load_readiness.py PASS (clang++).
Код не собран и не установлен, игровой результат pending. Живые сейвы,
настройки и metadata не менялись. Запуск игры не выполнялся.

## 2026-11-02 02:27 MSK — Stop/chalice routing installed on both machines

- Standalone `96db2f2`, bundled `e72801d`, port pin `3f079b9`.
- Bundled DLL build exit=0; target fixtures passed. Delta installed PC and laptop, 5 files each, both copy operations exit=0. No installed-file verification per fast-deploy preference; no game launch or save/settings changes.
- Backups: PC `D:/Games/Bloodborne/coop-dev/backups/stop-routing-20261102-022723`; laptop `C:/Games/Bloodborne/coop-dev/backups/stop-routing-20261102-022732`.
- Fixes: mount/register type collision; pre-load chalice-context gate; native Stop member drain bounded at 2 s; single cleanup owner; next-tick lock release; loading close once; no corpse fallback / wrong-world guest revive; readiness before uncovering. Details and scenario matrix: [stop-routing-fix](fixes/2026-11-02-stop-routing-fix.md).
- Runtime confirmation PENDING. 2 s bounds member drain, not the whole save/network/menu rendering. New `BBSC stop phase` records identify the remaining stages. First non-chalice claim/sign cadence (~31 s) remains OPEN; no claim that interval writes solve it. HTTP timeouts likewise not attributed to this issue.
- Deployment helper fixed to allow an explicitly enumerated mod-only delta ZIP without a full-package Bloodborne.exe; full-package guard remains for deployment without -Files.

## Прогон01:45–01:59 разобран — 02.11.2026, без правок кода

Continue/quest commit/inventory-before-fade подтверждены логами. Четыре выхода
0.58–0.80 s, два выхода guest12.95/17.05 s; поздний host quit5.66 s. Stop не закрыт.
Найдена точная коллизия0x2B: session-register перехватывает chalice-mount, затем
отвергает размер/версию. Чаши не монтируются. Guest recovery возрождает тело на
Y=-1500.17 и открывает cover, затем повторная смерть вынуждает настоящий reload.
Остаются поздние host leave locks, двойной cleanup и native loading UI после смерти.
Архив обеих машин+server: bloodborne_pc/out/coop-dev/review-20261102-0159.
[Полный разбор, времена и границы доказательств](fixes/2026-11-02-run-review-0159.md).

## Порядок кооп-событий установлен на обе машины — 02.11.2026, 01:43 МСК

Bundled1767a8d / standalone8e82daf / BBGL pinf259df9. DLL build exit0.
На остановленные ПК/ноут установлен mod delta: по5 файлов, без файловой верификации.
Бэкапы lifecycle-order-20261102-014341 (ПК D:/Games/Bloodborne/coop-dev/backups)
и lifecycle-order-20261102-014343 (ноут C:/Games/Bloodborne/coop-dev/backups).
Continue наблюдается через spawn-resolution, quit guard сбрасывается по готовности
мира; Stop сразу сопровождается native remote cleanup; accepted quit не отменяется
через30 s; home fallback не конкурирует с quit и ждёт1 s после завершения сессии.
Cover гостя ждёт inventory reconciliation текущего load generation. Ledger service
ограничен10 Hz с обходом на новую загрузку. Диагностика cleanup больше не лжёт при quit.
Целевые menu/load readiness/chalice/follow/home/trampoline/post-load fixtures PASS.
Правила смерти сохранены: boss spectate, вне boss немедленное revive. Гости следуют
за фонарём хоста, после ухода host идут домой. Код/деплой выполнены; игровой результат,
в особенности время Stop <нескольких секунд, ещё не подтверждён.
Сейвы/настройки/VPS не менялись, игра не запускалась.
[Матрица порядка и ожидаемое поведение](fixes/2026-11-02-lifecycle-ordering.md).

## Последние правки установлены на ПК и ноутбук — 02.11.2026, 01:06 МСК

Standalone 4873852 / bundled 80cae9b / BBGL pin 8494bbe. Полная сборка
build-coop-package.sh exit=0; Release payload and hygiene PASS.
На каждой машине заменено 9 файлов, проверено 5223, оба manifest PASS.
ZIP SHA256 C5D1577BB3D718E3D25F78C3081693A2B708C54880ED5AA65BC5ABC49CE9805D
проверен перед установкой на ноутбуке. DLL/launcher/native совпадают на обеих.
DLL 54F2683222CB6B9F6116439D439D76C4A799DACB6E09420BD36A4C40C347C965.
Native 191CF1D06C77CA9A3287200F790AE8F2D0BA2137AE21DCF70A1A0AF8CDB9A329.
Бэкапы: ПК D:/Games/Bloodborne/coop-dev/backups/joined-quit-20261102-010459;
ноут C:/Games/Bloodborne/coop-dev/backups/joined-quit-20261102-010520.
Сейвы/настройки не менялись; VPS не обновлялся. Игровое подтверждение pending.
Лог сборки: bloodborne_pc/out/joined-quit-package-build.log.
Предыдущие записи «исходники» ниже описывают этап до этого деплоя.
## Повторный призыв, блокировка хоста и позиция после меню — 02.11.2026, исходники

После JoinRoom/state6 знак гостя принудительно снимается с подбора; учтён
поздний create reply и повтор при сетевой ошибке. Starting/state4 не удаляется.
Host exit intent удерживает menu brake/load wait до native Continue, а не только
до state0. Native serializer получает исходные карту/позицию/поворот гостя,
привязанные к слоту; живой персонаж/сейвы вручную не перемещаются/не правятся.
Долгий выход: native Stop append FIFO подтверждён eboot; он ждёт текущую задачу.
Связь ~30 s с дублированным summon сильная, старого queue-head в логах нет;
добавлен его точечный лог. Не менять session state вручную и не увеличивать timeout.
Целевые lifecycle/menu/home/trampoline/bell tests и полная /Zs проверка PASS.
Bundled/standalone синхронизированы; не собирали/не устанавливали.
[Подробности и ограничения](fixes/2026-11-02-joined-claim-quit-origin.md).

## Гостям запрещены колокола призыва/подключения — 02.11.2026, исходники

По просьбе пользователя native goods-use result запрещает Зовущий (200,
effect 9000) и Малый звонкий (205, effect 9005) локальному гостю в state 4/6.
Запрет стоит перед native-yes/anywhere и работает независимо от опции anywhere,
для меню и быстрых слотов. Хост/соло, Бланк и PvP-переключение сохранены.
Целевой test_guest_bells исполняет production функцию с обоими значениями
anywhere, разными ролями, исходным native результатом и local/remote: PASS.
Bundled/standalone синхронизированы. Не собирали и не устанавливали.
Это не закрывает серверный повторный призыв уже вошедшего гостя хостом.

## Разобран прогон 00:25–00:35 — 02.11.2026, без правок

Обе машины на последней сборке; собрано с provenance, серверный journal сохранён.
Шесть комнат 109–114 успешно соединялись, шесть выходов завершились. Последний
выход ПК прерван ручным закрытием игры (уточнение пользователя), не считать зависанием.
Найдены: намеренная вторая cross-map загрузка (старый lighting workaround),
повторный призыв уже подключённого гостя из retained claim, 27.9 s native Stop
до вызова LeaveRoom и позднее повторное выставление leave locks хосту.
Связь долгого Stop с незавершённым повторным summon вероятна, точный timer/task
ещё не доказан. HTTP retry один раз сработал; общие TCP-тайм-ауты сохраняются.
Код/сборки/установки/сейвы не менялись. [Разбор](fixes/2026-11-02-run-review-0035.md).

## Выход с блокировкой управления и retry claim установлены — 02.11.2026

Bundled 6d8b109 / standalone 81524e4 / BBGL 7e8594f. Полная сборка
build-coop-package.sh exit=0, release payload/hygiene PASS. На закрытые ПК
и ноутбук установлено по 10 замен; 5223 файла проверены на каждой машине,
client/server manifests PASS. DLL, launcher и native exe совпадают со staging
и между машинами. Сейвы/настройки не менялись, VPS не обновлялся.
Бэкапы: ПК D:/Games/Bloodborne/coop-dev/backups/disconnect-stress-20261102-002324;
ноут C:/Games/Bloodborne/coop-dev/backups/disconnect-stress-20261102-002341.
DLL SHA256 AD0417E81096B4BF33105F82D65D5AAE695BD2ABE4AFE658DB07D3F89FC167A7.
Native SHA256 191CF1D06C77CA9A3287200F790AE8F2D0BA2137AE21DCF70A1A0AF8CDB9A329.
Игровой результат pending. Следующая запись «исходники» — исторический этап.
[Разбор прогона и правок](fixes/2026-11-02-disconnect-stress.md).

## Разрывы/повторный вход и блокировка выхода — 02.11.2026, исходники

Последний прогон собран с обеих машин и сервера: комнаты 105–107 успешно
соединялись после выходов и Blank; последняя 108 осталась пустой, потому что
claim POST не установил TCP-соединение и не дошёл до сервера. Это не прежняя
gонка signaling. В native HTTP добавлены максимум два безопасных повтора
только до отправки claim; причина самих TCP-тайм-аутов пока не установлена.
Перехват Yes перенесён до native save/stage flags; ожидающий выход закрывает
меню и блокирует управление, отмена сохраняет прежние значения блокировок.
Покрыты starting/leaving/failed и уход партнёра во время save. Целевые
menu/trampoline/transport fixtures и syntax check PASS. Не собирали/не ставили.
[Доказательства и границы](fixes/2026-11-02-disconnect-stress.md).

## Прогон 23:45–23:50 и исправление answerer — 01.11, установлено 23:56 МСК

Повторное подключение НЕ прошло. Архив investigate-20261101-2345 содержит
pc/laptop mod, pc-game, laptop-game-online (ротированный last_run.1.log), server.
Обнаружена регрессия предыдущей правки 0964480: новый входящий answerer штатно
начинает Inactive, а StartHandshakeInitiator стал отвергать его вместе с закрытыми.
Клиент создавал новый ID на каждом Offer, не начиная handshake; хост получил
30 s timeout 80552711. Это другой отказ, чем гонка established->pending.
BBGL 9f26442 разрешает новый Inactive, сохраняя защиту Established/dead_fired
и фильтр неактуальных queued activations. Production fixture дополнен этим
входящим сценарием и проходит. Полная сборка/упаковка exit0, release hygiene PASS.
Обе остановленные машины обновлены: по 9 замен, 5223 файла проверены,
client/server manifests PASS; native exe/DLL/launcher согласованы со staging.
Бэкапы answerer-fix-20261101-235512 (ПК), -235533 (ноут) в coop-dev/backups.
Native SHA256 B67E179AB0D2CD60000876F6A9BFF424826EFCF1D41916876A49634089108C87.
DLL SHA256 B8A57192D19682C7A0AD3EC9758DDF156F9E7AD5BECD8C18EDA43367803063CD.
Книга: native wait finished в 23:47:14.980, через 69 ms после Range rows1;
runtime-завершение ожидания подтверждено, визуальное подтверждение отсутствует.
Сейвы/настройки не менялись, VPS не менялся, игру не запускали.
Нужно игровое подтверждение подключения новой сборкой; общий баг не закрыт.
[Разбор](fixes/2026-11-01-activation-race.md).
## Книга и гонка активации — 01.11.2026, установлено 23:43 МСК

BBGL 0964480, bundled 9d992e8, standalone 63b789f. Найдены две ошибки:
- Ranking+2858 — first rank (начальное 0), а не board index 19. Старый guard
  блокировал закрытие плашки; fixture повторял ошибочное предположение.
- Отложенная signaling activation после ResolvePeer могла понизить уже
  ESTABLISHED до PENDING, не очистив established_fired. Повторный CheckAck
  не восстанавливал статус. Теперь текущее состояние проверяется повторно
  диспетчером и под mutex внутри StartHandshakeInitiator.

Новый production-code fixture детерминированно падает на прежнем сетевом коде
и проходит на исправленном; книга проверена с native initializer/predicate и
production trampoline, включая 1/2/5 rows. Provider fixture PASS.
Добавлена ограниченная диагностика четырёх native причин закрытия signaling.
Полная сборка (мод+порт+сервер), packaging/release hygiene PASS, exit=0.
На обеих остановленных машинах replaced=10, verified=5223, manifests PASS;
DLL/launcher/native exe совпадают. Бэкапы activation-race-20261101-234156 (ПК)
и activation-race-20261101-234226 (ноут) в соответствующем coop-dev/backups.
DLL SHA256 BD2430C4E850E0BAF114D0520E957847621E3160FC5BD069CCF3ED31BDDCC689.
Native SHA256 2DC04D463B8C67B43A8CC7AC1C05944F521347055A57D0FD13EDFEA37E3EDA71.
Сейвы/настройки не менялись, игру не запускали. Игровой результат pending.

Следующий пользовательский прогон: открыть/закрыть/снова открыть книгу;
подключить клиента из Сна к хосту в Кейнхерсте; выход гостя в меню и повторный
вход без перезапуска. Зафиксировать роли и время; проверить исчезновение
плашки, загрузку клиента к хосту и повторный вход. Не считать баги закрытыми
до результата пользователя. Сервер VPS не менялся.

Подробный разбор и предложение server event coordinator (НЕ реализовано):
[activation-race](fixes/2026-11-01-activation-race.md).
[Книга, исправление неверной трактовки поля](fixes/2026-11-01-register-loading-dialog.md).
Полные game-логи прочитаны: путь ПК оказался Bloodborne Game Launcher d/twin.
Уточнение к ранней диагностике: успешный архив показывает JoinRoom через 235 ms
после claim без промежуточного delivered create. HTTP polling не является
единственным путём; нельзя объявлять поздний create первопричиной отказа.
## Последние правки установлены на обе машины — 01.11.2026, 22:15 МСК

Bundled d6fb46a / standalone 2aa8c80 / BBGL pin bc56094: прямой выход в главное
меню и предшествующая правка плашки загрузки книги (8fbb19e) собраны и установлены.
Полная сборка build-coop-package.sh exit=0, release payload/hygiene PASS.
ПК: 9 замен, ноутбук: 14; на каждой машине 5223 файла сверены со staging,
client/server manifests PASS; DLL и launcher SHA256 совпадают между машинами.
DLL SHA256: F22A29CA354C2C5358F6C4EB38A9FE6051D341EBEDAC42DC5C0940DB2935B8F5.
Резервные копии: ПК D:/Games/Bloodborne/coop-dev/backups/menu-exit-20261101-221301;
ноут C:/Games/Bloodborne/coop-dev/backups/menu-exit-20261101-221339.
Игры/лаунчеры были закрыты, сейвы/настройки не менялись, игровой результат pending.
Эта запись заменяет статусы «только исходники» и «книга без деплоя» ниже.
[Разбор выхода](fixes/2026-11-01-menu-exit-extra-load.md).

## Лишняя загрузка при выходе — 01.11.2026, только исходники

Выход через System menu теперь после успешного native save и отключения вызывает
OnReturnTitle (event request 2), вместо возобновления MenuMan+250 — триггера
world-stage transition. Покрыт state 0: хост после ухода гостя раньше обходил hook.
Целевой test_menu_quit PASS; bundled/standalone синхронизированы.
Не собирали и не устанавливали; игровой результат pending.
[Разбор и границы доказательств](fixes/2026-11-01-menu-exit-extra-load.md).

## Плашка загрузки книги: исправлено и собрано, без деплоя — 01.11.2026

Пользователь подтвердил открытие книги и список участников, но долго остаётся
«Получение регистрационных данных». Bundled 8fbb19e / pin 09ea94c:
native predicate ждёт готовности реальных строк сессии, игнорируя пустой хвост.
Проверка на настоящем native predicate и production trampoline PASS,
provider fixture PASS, DLL build exit=0. По просьбе пользователя НЕ установлен;
ПК и ноутбук остаются на 91c8743. Визуальная проверка исправления pending.
[Нативная цепочка и границы проверки](fixes/2026-11-01-register-loading-dialog.md).

## Ноутбук обновлён для PvP и книги — 01.11.2026 21:27 МСК

Ноутбук найден в новой LAN: 192.168.1.166, DESKTOP-73Q9JB7; прежний SSH host key
подтверждён строго. Навык ssh-my-devices обновлён, SSH-конфиг не менялся.
Bundled 91c8743 установлен на закрытый ноутбук; SHA256 DLL совпадает с ПК:
9DB925B08B82BBC182EB0BD8E3DE52B701703E1D68C6092A14D852379C44EF76.
Client manifest и метаданные UTF-8 без BOM PASS. Бэкап ноутбука:
C:/Games/Bloodborne/coop-dev/backups/session-register-20261101-212740.
Это заменяет прежний статус «ноутбук отложен». Сейвы/настройки не менялись;
обе машины готовы к пользовательскому прогону, игровое подтверждение pending.
[Описание проверки](fixes/2026-11-01-pvp-dregs.md).

## Сгустки за добивание и книга подношений — 01.11.2026 20:01 МСК

Bundled 91c8743 / pin 6c75ad9: книга ранжирует до пяти участников своей сессии
по native числу сгустков, преподнесённых Королеве (+0xE8), включая нулевых.
PvP: 704 получает только автор смертельного попадания, с native HP до/после,
room/member identity, подтверждением доставки и подавлением повторов.
Исправлен цикл пустой страницы книги; board 20 обслуживается локально.
Целевые fixtures и DLL build PASS; установлено только на закрытый ПК,
SHA256/manifest PASS. Ноутбук отложен по просьбе пользователя, остаётся старым.
Новый сетевой игровой прогон pending; всем участникам нужна новая DLL.
[Детали и границы проверки](fixes/2026-11-01-pvp-dregs.md).

## Книга Нечистокровных: первый прототип — 01.11.2026 17:24 МСК

Bundled c11d31c / pin 4b1a44c: родной Ranking открывается из книги 130,
провайдер подаёт сетевые имена и уровни текущей группы, место по уровню.
Книга добавлена к комплекту после блокнота. Целевые fixtures и DLL build PASS;
установлено на закрытые ПК и ноутбук, DLL SHA256/manifest/UTF-8 без BOM PASS.
Карточки экипировки нет, подписи штатные; native UI требует игрового подтверждения.
[Разбор цепочки и ограничения](fixes/2026-11-01-session-register.md).

## Колокола в уведомлении блокнота — 01.11.2026 16:23 МСК

Bundled 9616dd9 / pin 5097954: при успешном получении блокнота отсутствующие
оригинальные колокола добавляются в ту же native очередь уведомлений.
C++ fixture реальной функции выдачи PASS, DLL build exit=0. Установлено на
закрытые ПК и ноут с бэкапами notebook-popup-20261101-162309 / -162320.
DLL SHA256 совпадает, полный client manifest и UTF-8 без BOM PASS.
Визуальный список/порядок строк и подбор блокнота требуют игрового подтверждения.
[Подробности](fixes/2026-11-01-notebook-popup.md).

## Ноутбук обновлён — 01.11.2026 16:05 МСК

Оригинальные кооп-предметы d659347 установлены на закрытый ноутбук.
DLL SHA256 совпадает с ПК; полный client manifest PASS. Бэкап:
C:/Games/Bloodborne/coop-dev/backups/original-bells-20261101-160501.
Игра не запускалась, сейвы и настройки не менялись. Игровую проверку выполняет пользователь.
Эта запись заменяет статус «ноутбук не обновлён» ниже.

## Оригинальные кооп-предметы — 01.11.2026

Четыре оригинальных goods, выдача после блокнота; отдельный Duel Bell убран.
Bundled d659347: целевая C++ проверка и DLL build PASS, установлен на ПК с
бэкапами, SHA256/client manifest PASS. Ноутбук не обновлён. Игровой контроль pending.
[Подробности](fixes/2026-11-01-original-coop-items.md).

# BACKLOG — актуальный план кооп-мода

Актуализирован 30.10.2026 по T6–T17, истории коммитов и сообщению пользователя:
практически все критические игровые баги исправлены. Основная следующая задача — **чаши**.
T19: пользователь подтвердил прохождение чаш в кооперативе; два остатка входа исправляются T21. Общее подтверждение пользователя
не означает отдельной проверки каждого редкого сценария.

Исходная установленная сборка: T17, `addfd08`, на ПК и ноутбуке.
T19 `c00fa6c` собран и установлен на ПК/ноут — автоматический вход, [код/проверки/границы](fixes/T19-chalice-follow.md);
порт с исправлением signaling `f4f0028`. Подробности окружения — [HANDOFF](HANDOFF.md).
Старый накопительный список сохранён в [истории](history/BACKLOG-2026-10-30-before-review.md).

Статусы: **подтверждено** — есть конкретный результат игры/логов;
**исправлено, контроль** — код и деплой есть, полной игровой проверки нет;
**исследование** — риск или гипотеза, а не доказанный текущий баг.

T20: [ускорение поиска и лимит колокола 5 мин](fixes/T20-matchmaking.md), BBSC `7967976`, порт `b325d1e`.
Установлен на ПК и ноут 30.10 в 21:31 МСК по просьбе пользователя, **без отката сейвов**; игровой контроль ожидается. Событийный брокер пока не реализован.

T21 `d194560`: два исправления входа в чашу, шесть наборов проверок PASS, build exit=0.
Установлена в 21:59, пользователь подтвердил оба исправления.
T22: новый остаток боевого урона; измерительный порт `6672649` установлен на обе машины
в 22:26, требуется короткий бой для локализации задержки. Боевой HP/AI не менялись.

## T25: ключи после загрузки гостя (31.10.2026)

По двум логам друзей (`013312-17200`, `043233-9232`) подтверждены потери
предметов при native reload. В `TickBbscSharedKeyItems` маска `last_applied`
переживала загрузку: повторная выдача ключей/жетонов/инструментов пропускалась.
Теперь маска сбрасывается по `bbsc_load_generation`; выдача ждёт готовности Lua,
отсутствия loading и 3 секунд стабилизации. Неуспешный AddItem не отмечается
успешным и повторяется не чаще раза в секунду. Сборка DLL: exit=0; diff --check
чистый. Тесты и игровой контроль не проводились; сборка не установлена.

Остатки из этих логов: скачки определения слота по mtime (0/1 и 2/3),
завершение загрузки без снимка флагов хоста, незавершённый join и проваливания
через лифт. Причины невидимости и лифта не доказаны; изменения в эти пути не внесены.

## Ближайшая работа

T24: повтор PT-2/PT-9 — после смерти хоста первым клиент загрузился живым,
но остался наблюдателем. По логам исправлен пропуск загрузки между игровыми
тиками через существующий native ReloadFinish; 18 recovery сценариев PASS,
perf policy PASS. [Разбор и игровой контроль](fixes/T24-wipe-spectator-camera.md).

| Приоритет | Задача | Что осталось / критерий завершения |
|---|---|---|
| P0, контроль | T23: возврат из чаши / сейв ноутбука | Host: после сетевого сбоя native state 7, OwnWorldStep повторяется >1 мин. Пробел снятия persistence исправлен `e8994b1`, установлен; конкретный pending task не установлен. Ноут восстановлен из своего `chalice-test-20261030`, 16 SHA256 PASS, плохая копия сохранена отдельно. Проверить игровой вход и возврат. [T23](fixes/T23-chalice-return-and-save.md). |
| P1, главный этап | CH-1: кооп в чашах | Прохождение и оба исправления входа T21 подтверждены пользователем. Новый боевой остаток: удар клиента регистрируется через 2–3 с, у хоста тоже. T22 измеряет native отправку/доставку/чтение; причина ещё не доказана. Затем layer ID, постоянный ID ритуала и расширенное покрытие. «Сейв тест чаш» сохранён на обеих машинах. |
| P0 при повторении | PT-3: GPU TDR | nvlddmkm / LiveKernelEvent 141 воспроизводился и Offline без BBSC, с DLSS/FG OFF. После чистой переустановки своей сборки первый переход в Сон успешен. Повторить маршрут Сон → обратно и выход в меню; устойчивое исправление и причина пока не доказаны. [T17](fixes/T17-event-work.md). |
| P0, контроль исправлений | PT-2/PT-9/PT-12 + T14: смерть и восстановление | T6 подтвердил базовые вайпы, затем были регрессии и исправления T9/T11/T14. Один контроль: оба порядка смерти на боссе, одновременная смерть вне босса, выход домой → лампа и колокол → повторный призыв. В T17 есть предупреждение NowLoading state=3 >30 с, видимый софтлок не сообщался. |
| P1, контроль исправлений | PT-1: ключевые после повторного призыва | T6 подтвердил базовый сценарий, T8 исправил новый вход с фантомной сумкой. T17: шесть goods восстановлены после загрузок, два вида сохранены после краша хоста/возврата. Проверить цепочку новый призыв → загрузка → домой → меню → новый призыв; инструменты мастерской, руны/самоцветы и ключи без дублей. |
| P1, покрытие | Три игрока и обрывы | Выход одного гостя при живом/мёртвом хосте: остальные продолжают; не остаются фантом/камера/неверное число живых и scaling. T8 удаляет life-запись по EOF; привязка relay sender к native member для адресной очистки копии остаётся задачей. Молчаливый обрыв сети проверить отдельно от закрытия процесса. |
| P1, покрытие | NPC и свой прогресс | Личные награды только за свой разговор, два одновременных разговора, разные квестовые стадии. PT-5 («Нечистота») и PT-14 (ранняя белая лента) решены: пользователь подтвердил 30.10. Для остальных NPC-наград остаётся покрытие. |
| P1, покрытие | Свой Сон, Shared Progress, DLC | Свой Сон выбран и реализован; проверить разные стадии Куклы/магазинов, покупки и сохранение. Shared Progress ON/OFF: квесты, ночь, боссы, лифты/рычаги после возврата и перезапуска. DLC: призыв, переходы и босс; полного покрытия нет. |
| P2, контроль | T11/T15/T16: загрузки и взаимодействия | Обычный лут/закрытый сундук, NPC после reload, отменённый/неудачный призыв с закрытием NowLoading, граница Соборный округ ↔ Ярнам без повторных follow; новая поездка хоста всё ещё вызывает follow. Код раскатан, отдельные результаты не записаны. |

## Что можно считать сделанным в проверенных сценариях

| Тема | Основание и границы |
|---|---|
| PT-5, PT-14, PT-10, инструмент рун у друзей | **Решено, подтверждено пользователем 30.10.2026:** «Нечистота», ранняя белая лента, появление в клинике и восстановление инструмента рун на сейвах друзей. Не включать в оставшийся контроль без нового сообщения о регрессии. |
| LA-1/GI-2, WS-2/WS-3: слот сейва и журналы на диске | `566cf7d`, тест 29.10: восстановление после краша. T17: восстановлены 960 групп своего мира и 18 talk-флагов. |
| PT-7/WS-5: стук в окна; PT-11: камера мышь/клавиатура/стик | Конкретное подтверждение пользователя T6. Не означает проверки всех NPC-событий. |
| PT-15: дверь после собаки; ранняя красная лента | Пользователь подтвердил после T7; [T8](fixes/T8-rejoin-quit.md). |
| Дубли обычного дропа | `d2e3ad4`, тест 29.10 №2: дубля нет. |
| Базовые предметы/вайпы у лампы | T6, `e40ede7`, пользователь + логи. Последующие расширенные пути восстановления — в контроле выше. |
| Уход хоста при краше и возврат гостя с предметами | T17: EOF, возврат домой, восстановление мира и предметов подтверждены логами. Лампа/колокол после этого отдельно не подтверждены. |
| PT-4: старая заглушка с логотипом | Устранена в тесте 29.10 №2. Позднее T11/T15 вернули штатный NowLoading для призыва — его завершение требует отдельного контроля. |
| PT-13: ?ActionEventInfo? | Фильтр исправлен в T11, раскатан; визуальное подтверждение не записано. Косметический остаток, не блокер чаш. |
| WS-1: защита своего прогресса чаш | `566cf7d`: область 29 исключена из Shared Progress. Это защита от слияния чужих чаш, а не готовая поддержка бесшовных подземелий. |
| Запуск signaling | `f4f0028`, T12: исправлен deadlock, порт установлен на обеих машинах. T13: отдельный отказ подключения из-за исчерпания UDP-портов MSI Center; перезапуск освободил порты. |
| Снижение диагностической нагрузки | T10/T17, сборки/автотесты/деплой проверены, Research OFF. T17: медиана ПК 59.7 игровых тиков/с, 1.474 мс BBSC; ускорение без сравнимой базы не измерено. |

## Важное, что нельзя потерять перед релизом

- PT-8: жест «отдёрнуть плащ» в инвентаре — вероятный след старой выдачи; проверить на чистом персонаже. Низкий приоритет.
- Исследовательские кандидаты из [FINDINGS](study/FINDINGS.md): загрузка без полного снимка флагов (SN-08/WS-6/WS-7), OR-слияние переключаемых состояний (WS-9), изоляция/доверие relay (SN-02), устаревшие ключи хоста (WS-4). Нужна актуальная перепроверка кода/конфигурации; не выдавать гипотезы за текущие игровые баги.
- Лаунчер: контроль совместимости override нашей DLL при обновлении пакета (LA-3), ограничение роста бэкапов (LA-2/GI-3), чистая установка и восстановление. Свою сборку не заменять upstream. Исходники и воспроизводимый пакет — перед публичной раздачей; push только по просьбе.
- Хост-миграция не запланирована; завершение хоста возвращает гостей в свои миры. Нужна понятная обработка недоступного сервера и его перезапуска.

## Порядок завершения

1. Короткий контроль GPU/смертей/предметов на текущей T17 на копиях сейвов; при отсутствии повторов перейти к чашам, не откладывать их ради косметики.
2. Фиксированная Птумеру от ритуала до следующего слоя; затем идентичность и изоляция двух разных подземелий, корневые чаши и возврат после обрыва.
3. Один объединённый прогон трёх игроков, личных NPC-наград, Сна/DLC и длительного прохождения; закрывать пункты по конкретным результатам.
4. Чистый релизный пакет своей сборки, совместимость версий, бэкапы/восстановление, инструкция с оставшимися ограничениями.

## Startup TXT gate removed (31.10.2026)

`f9447b4`: removed the blocking LICENSE.txt / NOTICE.txt / SUPPORTERS.txt
content check from the DLL. Missing or modified companion notices no longer
disable BBSC or show a startup error. Packaging license files are unchanged.
## Launcher profile layout (31.10.2026)

BBSC_DATA_DIR redirects mod logs, persistent journals and bbsc-launch.ini into the
launcher's AppData profile. Binaries remain in the launcher installation. Without
the variable the standalone BBSC layout remains compatible. Build and local profile
checks accompany the launcher ZIP; no deployment or gameplay test is implied.

## Native menu exit follow-up (01.11.2026)

Guest staying connected in title / delayed disconnect after Continue: Lua-only
exit hooks missed the native confirmation path. Implemented save-gated native
menu exit, with both global and per-viewport results deferred until successful
native save completion; failures cancel the exit. See
[implementation and checks](fixes/native-menu-save-exit.md). DLL build and
production-fixture/trampoline/post-load checks PASS; deployment and gameplay
confirmation are pending.

01.11 02:58 follow-up: 02:47 laptop logs showed the generic-dialog hook was
never called. Corrected to actual System Exit Game Yes callback (01C0D0C4,
MenuMan+250), traced from the port's real row opener and relocated vtable.
Targeted fixture/build passed; corrected DLL installed on both PCs. See
[updated native-menu notes](fixes/native-menu-save-exit.md). Gameplay pending.

01.11 03:03 run confirmed by user and logs: client native save succeeds before
disconnect; title released after state 0, own world and 8 quest flags restored,
taken-item record retained, no save errors or delayed kept-session cleanup.
Native menu exit is confirmed in this two-player scenario; see
[run evidence](fixes/native-menu-save-exit.md).

## 04.11.2026 — notification wording and punctuation (source only)

Russian and English single-sentence mod notices omit their final full stop.
Original bell search/discovery, arrivals and invasion wording is restored where
its meaning still applies to seamless co-op. Multi-sentence notices and search
ellipses are retained; covenant discovery warnings remain in their existing form
(the requested exclusion of «Слышен перезвон…» is preserved). Both generators
share tools/gamedata/notice_text.py; menu help and item descriptions keep their
punctuation. Verified 224 entries per language, original text correspondence,
name/boss tags and inline notice punctuation. No build, deploy or game test.
