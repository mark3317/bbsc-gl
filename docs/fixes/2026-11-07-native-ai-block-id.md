# 07.11.2026 — native block ID против sorted position

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


## 07.11.2026 — native NPC block-ID fix: BUILT / PC INSTALLED / P1+P2 STARTED

DLL build exit0/8 прежних warnings, inputs unchanged0. Five-file delta и
PC deploy exit0; backup D:/Games/Bloodborne/coop-dev/backups/native-ai-block-id-
20261107-20261107-024235. Игры были закрыты до установки. П1/П2 запрошены
02:42:40МСК; оба native startup02:43:06, run_20261107_024305.log,35 of35
selected и early native admission ready. Startup signature/fault errors нет.
Связанные чаты прочитаны/повторно проверены: активных доработок нет; общий
dirty source tree сохранён, pin не менялся. Целевые проверки прошлой доработки
не повторялись ради деплоя. Gameplay OPEN: host в Dream, client у новых
боевых NPC, затем host обратно; роли определять по runtime, не Player номеру.
Details fixes/2026-11-07-native-ai-block-id.md; parent run native-ai-block-id-20261107.


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
