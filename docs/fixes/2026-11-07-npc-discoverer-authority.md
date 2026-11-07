# ИИ по штатному обнаружению NPC

BUILT / PC INSTALLED / targeted checks PASS / gameplay OPEN.
Пользователь уточнил общее правило: NPC получает ИИ у обнаружившего его игрока;
вблизи двух игроков должна работать штатная симуляция, новые циклы/опросы запрещены.
Это заменяет прежнее принудительное правило «весь ИИ у владельца карты».

## Четыре живых NPC

В сохранённом live-request-life-details.json run native-npc-authority-20261107:

| Native handle | HP | chr+E4 | flags1e1 bit8 | request1EC |
|---|---:|---:|---:|---:|
|203e|145|30|0|0|
|203f|145|30|0|0|
|206f|705|30|0|0|
|2076|999|30|0|0|

Original debug strings4982C1C/4983584 называют +E4 уровнем обновления персонажа
и уровнем сокращённой обработки. ORIGINAL01915FFA..01916021 сравнивает
расстояние с native config+2C, выбирает5 либо30 и сохраняет pinned flag bit1.
ORIGINAL01916A55..74: уровни-1..4 проходят к запросу, остальные требуют bit8
либо положительный event priority+1EC. Поэтому эти четверо штатно не подавали
заявки. HP>0 и activation4/4 не означают полноценный AI-update. Снимать этот
LOD gate и будить дальних/сценарных NPC принудительно неправильно.

Баг мода: отдельный map cache всё равно выбирал LOCAL controller, тогда как
оригинальные grant и position sender оставались выключены. Эта пара правил
противоречила оригинальной симуляции.

## Повтор при удалении П1 от П2

Distance-repro-pc собран до03:19:39. П2=host9fe0730d, П1=guest4ec03841.
С03:17:49 Cathedral принадлежит П2 epoch5. У П1 новые NPC активируются
remote/FFFF по старому map-only правилу. Однократный read-only distance snapshot:
201b/2028/205d/206e у П1 current/requested4,LOD0,controllerREMOTE/FFFF;
те же handles у П2 current/requested0,LOD-1,controllerLOCAL/FFFF.
Владелец карты выгрузил NPC, а обнаружившему их игроку мод запрещал заявку.
Это конкретный путь к подтверждённому пользователем исчезновению ИИ.
Сценарий нельзя исправить одним допуском state30 или увеличением радиуса.

## Итоговая реализация

1. Ранний EnemyIns018E6540, binding/model publication/update оставлены полностью
   оригинальными. LOCAL/REMOTE выбирается по тому же signed native grant,
   который используют position/commands/hits. Отдельный map-role rewrite удалён.
2. Native request01916A82 больше не запрещён follower карты. Оригинальные
   special/readiness/LOD/priority-zero условия сохранены. При положительном
   запросе держатель текущего grant получает priority7FFF, новый заявитель
   сохраняет original priority с верхней границей7FFE. Диапазон оригинального
   протокола0..7FFF сохранён. Так уже выбранный NPC не перехватывается игроком,
   подошедшим позже. При native нулевом приоритете держатель также не запрашивает
   NPC: смерть/proxy/выгрузка не обходятся.
3. Original native host merge/grant channels16/17 выбирают одного участника.
   «Первый обнаруживший» означает первого получившего native grant. Если обе
   активации попали в одно окно заявок, исходный арбитр разрешает конкуренцию;
   новой глобальной хронологии обнаружений/пакетов нет.
4. Исправление пустых self/peer lists018F0880/018F09D1 сохранено: native
   assignment очищает старые заявки при count0. Это даёт передачу после ухода
   держателя из зоны обработки. Отрицательные counts отклоняются.
5. Map owner commit теперь меняет только метаданные состояния мира. Он не
   обходит NPC и не записывает grants. Activation hook наблюдает штатный word,
   не назначает/не отзывает ИИ. Диагностика показывает native_mode/native_local;
   owner/epoch в ней относятся к состоянию карты, а не к держателю NPC.
6. Удалены старый32-byte map AI cache, его event publisher, table-creation hook
   и map-owner→NPC проход. Legacy opt-in pipeline не активирован.

Новых циклов/опросов/ticks/таймеров/обходов/пакетов/очередей/C++ per-frame
callbacks нет. Один O(1) grant lookup в уже существующей развилке native
заявки; native zero priority выходит до lookup. Сохранена ABI alignment
при replay original priority call. Дополнительный lookup заменяет неправильный
map fence, а controller/table/map-commit overrides удалены. Реальный FPS новой
версии не измерен; fixture timing не считать игровым результатом.

## Проверки

- test_native_npc_authority: ORIGINAL LOD5/30/pinned, request loop/conditions,
  production Windows rewrites, upper priority bounds, grant retention,
  simultaneous first requests/exactly one winner, self/peer positive/zero/negative
  assignment, original merge/grants, EnemyIns binding/update, channel4 XYZ codec
  sender/receiver. Distant follower eligible while map owner inactive; release
  and next active holder. PASS. Negative request/empty controls detect failures.
- test_native_npc_activation_ai: actual original activation transition with
  production callback; FFFF/1/77 unchanged across owner/map/reactivation,
  setup wait, stale actor, loading, personal Dream;2000stable steps zero callback.
 26reads/activation, no new actor reads diagnostic-OFF. PASS; negative restoring
  map assignment fails as expected.
- test_native_ai_admission: original unpatched EnemyIns function, controller,
  model binding/update, native grant gain/loss, independent NPC slot, forced/
  special inputs. Obsolete map metadata cannot force or suppress AI. PASS.
- test_map_ai_handover: actual map owner commit for all owner/role/visit changes
  and2000idle calls; zero actor walks/reads/writes and raw grants preserved.
  Original0191AAE0 predicate agrees with words. PASS; negative map overwrite fails.
- test_native_npc_sync_mode: production installer uses only retained render,
  serializer and read-only activation hooks plus3request rewrites; no early
  controller/table hooks. Version mismatch fails closed; native/legacy/default
  and direct lamp/bootstrap dependencies PASS. MOD syntax PASS.

Не собиралось и не устанавливалось в этом разборе. Игры продолжают использовать
прежнюю DLL; процессы/сейвы/settings не менялись. Общие файлы других чатов и pin
сохранены. Gameplay и производительность остаются OPEN.

## 07.11.2026 — NPC discoverer + pre-Rom: BUILT / PC INSTALLED / startup checking

DLL build exit0,8 inherited warnings, inputs unchanged0;5-file delta/deploy exit0.
Included ready native chalice lamp catalog from related chat. Named snapshot
before-rom-20261106-064652 restored to BOTH Player1/2 real user dirs while stopped,
full savedata/sce_sys and related progress journals; existing saves backed up first:
D:/Games/Bloodborne/coop-dev/saves/before-npc-discoverer-rom-20261107-033610.
Binary backup npc-discoverer-rom-20261107-20261107-033629. Accounts/settings retained.
P1 startup03:36:57,run033657,35/35 +discoverer authority/original AI ready;
P2 launch requested03:37:26. Gameplay/FPS OPEN; source tests not repeated for deploy.
Details parent out/coop-dev/runs/npc-discoverer-rom-20261107/run.md.


P1 native40720 startup03:36:57/run033657; P2 native19880 startup03:37:51/run033751.
Both35/35 selected, discoverer authority ready + ORIGINAL controller/position grant retained.
No matching startup allocation/fault/install errors in checked logs. P1 entered Byrgenwerth
(m32_00)03:37:46.851, consistent with named pre-Rom snapshot. Gameplay/FPS remain OPEN.

## 07.11.2026 — discoverer AI retest: cross-map FAILED / native actor gate found

Сбор npc-discoverer-rom-20261107/retest-pc exit0,2files,warnings0,обаlive,
до03:51:24. П1host0261a503, П2guest3766a551. Rom boss clear у обоих03:42:50,
guest reward logged; обаYahar03:48:24, П2Central03:50:10 при host на другой карте.
Read-only snapshot: у П2Central28active REMOTE/FFFF, model bound;3samples
HP343/150/70 death0. Это неLOD30. Native request/grant не выдаёт ИИ клиенту.

Следующий native допуск:018F0966..09AD host сопоставляет channel16 sender
через live PlayerIns, отсутствующий на чужой карте. Снимок: room2members,
5player slots,толькоselfslot0,guest request-list у host отсутствует. Кроме
intake,grant send018ED470..0524 также требует live target actor. Старый fixture
покрывал lists/merge/grants/brain/XYZ, но НЕ этот cross-map actor lookup.
Нужен roster-based native member resolve в обеих границах, без восстановления
map-only brain/нового periodic repair. UDP delivery отдельно не трассировалась.

Fault/fatal/install/1455 в собранном интервале нет. Смерть П2 перед victory и
поздний spectate — уже отдельный SOURCE FIXED сценарий boss-before-spectate,
его новая DLL не установлена. Код/сейвы/settings в этой проверке не менялись.
Details parent out/coop-dev/runs/npc-discoverer-rom-20261107/retest-analysis.md.
Discoverer правило в коде есть, cross-map gameplay FAILED/OPEN.
