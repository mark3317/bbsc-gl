# 07.11.2026 — ранний штатный допуск ИИ боевых NPC

Статус: SOURCE / targeted checks PASS. Build/install/start фиксируются отдельно ниже; gameplay OPEN.

## Причина и изменение

В оригинальном EnemyIns virtual+128 (018E6540), вызываемом существующим
проходом019176D8, выбирается локальный контроллер [chr+3B8] либо сетевой
[chr+3C0]. Обычный допуск018E659A..018E65DE читает signed native ownership
word. Его grant приходит через native channel17 от хоста; request — channel16.
Это отдельный этап от completion018BD488: модель может уже быть активирована,
а её native контроллер всё ещё выбран сетевым. Предыдущий тест completion
этого этапа не выполнял; прошлый игровой прогон подтверждённо FAILED.

Теперь замена исходного условия018E655E читает опубликованный байт роли
карты соответствующего native блока:1=local owner,2=remote owner,0=original.
Оригинальные binding [chr+60], publication [model+80] и update контроллера
остаются штатными. При известной lease выбор не зависит от старого grant,
поэтому его перезапись при возвращении хоста не меняет выбранного контроллера.
Native forced-local и special fallback сохранены. Dream не получает override:
персональная Doll и прежняя штатная логика продолжают использовать свой путь.

Публикация — в том же BbscWorldPublishOwner, что передача карты (через уже
существующий однократный обход; каждый блок читается максимум один раз),
при реальном изменении lease и в событии создания native sync table018ECCD4.
Последнее требуется для блоков, которых ещё не было при commit карты.
Map берётся из native block metadata+8, scope через World::BlockScope с
world/room/ritual. Для player tables, loading, неизвестной lease — fallback.
При новом visit/утрате роли метаданные сбрасываются.

## Оптимизация и границы

Нового tick, таймера, опроса, сканирования акторов, очереди, пакета или
периодического C++ callback нет. Старые ownership/wake hooks остаются OFF.
В существующей native развилке — прямое чтение одного байта из32-byte массива;
когда owner известен, прежний pointer chase по grant table не выполняется.
Нет C++ snapshot/lock/логирования/вызова кода мода на каждом native решении.
Изменение lease публикует максимум32 cached metadata entries однократно,
без чтения игры с relay thread. Постоянные heartbeat не повторяют публикацию.
Новый observer018ECCD4 работает только при создании native таблицы.
Generic InstallGuestCodeRewrite генерирует код при установке, не в runtime.

## Доказательства

- test_native_ai_admission.py выполняет ORIGINAL018E6540..018E66EC:
  вход, прежнюю no-grant ветку, binding local/remote controller, публикацию
  в model и вызов update. Production rewrite меняет guest no-grant -> local
  owner; возврат/stale grant не отбирает контроллер; смена owner -> remote.
- Native table publication выполнен с исходным store через production Windows
  trampoline: R13/R14/R15 проверены, исходная запись таблицы сохранена.
- Отдельные block roles, unknown fallback, Dream, loading, native forced/special,
  signature mismatch — PASS. Negative control без rewrite FAIL как ожидается.
- Fixture200k calls: original~6.0ns / cached owner~4.8ns. Это изолированная
  стоимость выбора, не замер FPS в игре; C++ runtime callbacks отсутствуют.
- test_map_ai_handover: actual native0191AAE0, transfer/retention/new visit,
  2000 idle commits без actor work PASS.
- test_native_npc_sync_mode: installer spans/mismatch, native/default/custom,
  2000 ticks без новых NPC-проходов, bootstrap/lamp dependencies PASS.
- Прежний test_native_npc_activation_ai и MOD syntax PASS.

Игровая проверка ещё нужна: П1 в Сон, П2 к новым врагам, затем возврат П1;
проверить не только движение, но и атаки/попадания. Другие native потребители
ownership words и HP/сетевой транспорт этой правкой не заменялись.
Новые события WORLD: NPC AI native admission block/map/owner/epoch/role/load;
NPC AI native table created; START early native admission ready.

## Сборка, установка, запуск

DLL build exit0/8 прежних warnings; inputs unchanged0. Delta5files и deploy
exit0; backup D:/Games/Bloodborne/coop-dev/backups/native-ai-early-admission-
20261107-20261107-022559. П1/П2 запрошены02:26:07МСК, native startup02:26:34;
оба run_20261107_022634.log с35 of35 selected и early native admission ready.
PID П1=33572/П2=29900. В runtime логах при проверке нет signature/install/fault
ошибок. Старый v1.2 banner исторически описывает baseline; отдельный новый
START marker подтверждает раннюю owner admission rewrite. Gameplay OPEN:
П1 в Сон → П2 к новым боевым NPC → П1 обратно; проверить реакции/атаки/HP.
Details fixes/2026-11-07-native-ai-early-admission.md; parent run native-ai-admission-20261107.


## 07.11.2026 — early AI retest: client owns map / positive admission NOT OBSERVED

Свежие П1/П2 run022634 собраны до02:29:19МСК (collect exit0,2files,warnings0;
оба live ChangedDuringCopy). Роли в ЭТОМ прогоне поменялись: П2=host07764aeb,
П1=guest9ecf9853. П2 остаётся в Dream с02:27:13.043. П1 прибывает в
Cathedral Ward02:28:01.367;02:28:01.488 получает owner9ecf9853/role1.
Дальше до конца снимка роли/карта не меняются. Сценарий клиента без хоста
на карте присутствует; возвращения хоста в этом интервале нет.

П1: native table-created block4/5 во время load2 дают admission=0. Во всём
снимке положительных NPC AI native admission/role1/2 записей НЕТ. Activation
records25, все npc_map15000000/Dream; боевых activation records нет. П2:
activation/native table records нет. Новый START ready marker есть у обоих;
ошибок Fault/fatal/install в собранном интервале не найдено.

Логи подтверждают передачу КАРТЫ, но не появление реакций/атак боевых NPC.
Публикация cached early admission для боевых блоков не наблюдается. Не
утверждать, что ИИ заработал, либо что выданный owner был отобран хостом.
Следующее направление — почему реальная привязка native блока к map/scope
не публикует положительную роль при commit; fixture с готовыми metadata
не доказывает, что live layout/admission producer корректен. Gameplay OPEN.
Игровой код/установка/сейвы в этой проверке не менялись.
Evidence: parent out/coop-dev/runs/native-ai-admission-20261107/retest-pc.


## 07.11.2026 — AI producer: sparse native ID bug CONFIRMED / SOURCE FIXED

Причина предыдущего нулевого early admission найдена. Native block ID
ошибочно использовался как sorted position в world+280/+290. Original
01914C70 сначала индексирует world+28 records по ID (stride160), затем
вставляет list/ID/record в компактный сортированный список; +850+ID*8 —
прямая таблица list. Число записей sorted list не ограничивает величину ID.

Однократный read-only live snapshot П1 PID33572: NPC records17, sorted count4,
пары(position→ID/map):0→4/m24_00,1→5/m24_01,2→17/player,3→18/player;
sync count17. Direct records совпали с оригинальной регистрацией. Все32
байта установленного early cache равны0. У П2/Dream ID0 на позиции0, поэтому
ошибка была скрыта Dream-only успешными логами. Старый block>=count-2
отсекал боевые ID4/5, так как4-2=2. Это подтверждённая ошибка producer;
исходный controller-selection rewrite сам по себе этого layout не проверял.

В SOURCE общий BbscWorldNpcBlock теперь берёт record по настоящему native ID
и сверяет keyed list==record+B8 за O(1). Используется в ранней публикации
и activation callback; player IDs вне NPC record count исключены. Новых
hooks/циклов/опросов/пакетов нет; native развилка и её стоимость не менялись.

Расширенный test_native_ai_admission выполняет ORIGINAL01914C70 registration,
живой layout17/4/5/17/18, последующую вставку меньшего ID, production table
observer, actual owner commit после Loading и ORIGINAL EnemyIns controller
selection/update. PASS. Negative control старого sorted-position lookup FAIL
на блоке4 как ожидается. Прежний activation test PASS/26reads, map handover/
2000idle commits и MOD syntax PASS. Fixture metadata поправлены по original
registration, прежнее ручное совпадение ID=position больше не доказательство.

Не собрано/не установлено в этом разборе. П1/П2 продолжают работать со старой
DLL run022634; память игр только читалась, файлов/сейвов не меняли. Gameplay
по исправленной привязке OPEN. Evidence parent run: live-block-layout.json,
block-index-analysis.md; details fixes/2026-11-07-native-ai-block-id.md.


## 07.11.2026 — NPC AI assignment PASS / shared movement FAILED

Run024305 собран до02:51:07МСК, exit0/2files/warnings0, оба live
ChangedDuringCopy. П1=guest0088f093, П2=host6fb824d7. П1 в Cathedral с
02:44:18.725, map owner0088f093/role1 с02:44:18.838, host в Dream до02:44:51
затем в Old Yharnam. У П1 есть61 combat activation в Cathedral, все desired1,
applied=true (43 beforeFFFF,18 before1). Нулевой cache producer исправлен.

В Old Yharnam вместе с02:46:20: host owner6fb824d7/role1, client role2;
47 клиентских activation до02:47:30 остаются remote/FFFF, у хоста45 local/1.
После ухода хоста в Dream02:48:53 клиент получает Old Yharnam и9 local
activation. П1 возвращается в Cathedral02:49:10, host прибывает туда
02:49:48.921: owner остаётся0088f093 epoch2, у host role2. Host получает
16 Cathedral activation remote/FFFF; client cache4 остаётсяrole1.

Пользователь подтвердил НОВЫЙ/оставшийся баг: движение NPC рассинхронизируется,
когда игроки рядом. Однократный read-only live snapshot обоих процессов:
в Cathedral11 одинаковых active NPC handles. У П1 все11 controller LOCAL и
model+80 совпадает; у П2 все11 REMOTE и model+80 совпадает. Cached roles4:
П1=1,П2=2. Выбор раннего ИИ и сохранение owner работают.

НО native signed ownership words не согласованы с этим выбором: П1 local/FFFF9,
local/1 всего2; П2 remote/1 у7,remote/FFFF4. Для7 одинаковых handles авторитет
в native таблице прямо противоположен выбранному контроллеру; ещё2 имеют
FFFF у обоих. Это не доказательство двух local brains — local/network выбор
как раз правильный. Доказано несогласование native ownership и map AI owner.

Original018EE829 проверяет signed native word перед формированием position
corrections018EE8A5..018EE8E4 (дельты XYZ), которые018EEA0C..20 отправляет на
native channel4. Receiver018EEB34..45 читает этот channel,018EEC43..92 восстанавливает
позиции. Cache override для EnemyIns не меняет этот native sender gate. При
снятых words у фактического AI owner и разрешённых words у follower это даёт
конкретный путь к описанному рассинхрону. Фактический поток пакетов/перезаписей
за весь интервал не трассировался; автор конкретной поздней записи отдельно
не установлен. Нельзя считать исправленным только по успешным activation.

В собранном интервале Fault/fatal/CHECK FAIL/install errors не найдено.
Reunion Old Yharnam: у обоих resident peer bound/draw_admitted=true; Cathedral
у обоих native recreation requested, у host render hold bypassed. Это допуск
моделей, не визуальное подтверждение отсутствия любых багов.

Статус: AI assignment/retention CONFIRMED, shared NPC movement FAILED/OPEN.
Дальше согласовать native authority для передачи позиции с map lease через
штатные assignment/receive boundaries, без нового периодического repair.
Код/установка/сейвы в этой проверке не менялись. Evidence parent run:
retest-pc, shared-npc-controller-snapshot.json, shared-movement-analysis.md.
