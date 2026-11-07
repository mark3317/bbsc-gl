# 07.11.2026 — назначение ИИ при штатной активации NPC

Статус: SOURCE/tests PASS; build/deploy/startup ниже отдельно; gameplay OPEN.

## Причина и изменение

Прежний map-owner commit назначал управление только уже существующим актёрам.
Новые stream-in и повторная native активация приходят позднее; native room host
сам по себе не является владельцем карты. Попытка заменить роль MatchingState
глобально меняла бы сетевые/HP/сессионные ветви, а возврат ownership/wake hooks
добавил бы регулярный обход. Эти пути не использованы.

В native default подключена точная граница018BD488: native actor state machine
только после завершения virtual78 и штатной подготовки018B9890 пишет
controller.current=4. Новый BbscWorldNpcActivated выполняется только на этой
границе, не на входе state machine, не на каждом кадре и не в wake loop.
Он назначает ownership word конкретному NPC из authoritative OwnerBook,
не из native host роли. Оригинальная запись current=4/ожидания/завершение
сохраняются через прежнюю Windows trampoline.

Карта берётся у самого NPC: handle -> текущий sync table -> native actor list,
сопоставленный с world+280/290 -> block metadata+8. Это те же структуры, которые
связывает018EB7A0 и сериализует0190E750. Соседний streamed блок получает свою
map lease; чаши сохраняют текущую dungeon/ritual scope. Pointer/list/slot/actor
binding проверяется при каждом activation event, не кешируется между кадрами.
Резервные player tables, loading/offline, отсутствие lease, invalid/recycled
handle, native unload/backread/disable не получают нового назначения. Прежнее
личное владение куклой в Dream сохранено через существующий Doll lookup.

Для обычного NPC нет обхода актёров: ограниченные pointer reads и одно
metadata lookup под существующим mutex; запись word только при отличии.
На Dream activation дополнительно используется прежний lookup куклы.
Новых таймеров/ticks/опросов/очередей/повторов/сетевых сообщений нет.
Добавлен один hook только события successful activation (обоснование выше),
старые per-frame ownership/wake/HP hooks не возвращены. Он также ничего не
перезапускает, не меняет HP/позу/анимации/флаги смерти и не форсирует готовность.

## Проверки

- tools/test_native_npc_activation_ai.py исполняет ORIGINAL1.09 transition dispatch,
  native jump table, successful activation store и wait-tail с production
  Windows trampoline + настоящим callback: late actor после takeover,
  реактивация с новым lease, соседняя карта, player tables, native setup wait,
  recycled binding, loading/offline, private Doll PASS.
- 2000 native updates уже активного актёра: 0 новых callback/чтений/записей.
- Fixture cost (memory guards mocked): original0.015us/activation,
  fixed0.451us/activation,26 production reads/event. Это НЕ реальная оценка
  VirtualQuery/lock contention и НЕ игровой benchmark; стоимость только при
  активации, не на кадр/число активных NPC. Реальный frame cost ещё OPEN.
- Negative control убирает назначение word, original activation завершается,
  но тест late NPC ожидаемо FAIL; контроль PASS.
- test_native_npc_sync_mode: byte mismatch activation site fail-closed,
  default/native/legacy installation и2000ticks PASS.
- test_map_ai_handover (+original0191AAE0), test_npc_ownership PASS.
- Whole bloodborne_re.cpp BBSC_MOD syntax PASS до финальной Doll-exception;
  последующая полная DLL сборка служит compile check финального кода.

Native protocol/ownership packet processing оставлены; эта проверка не доказывает
весь live handover/streaming/native network order. Игровой сценарий: П2 остаётся,
П1 уходит в Dream, П2 доходит до ранее не загруженных NPC, затем П1 возвращается.
Нужно подтвердить агро/движение и повторную активацию; не закрывать по fixture.

Исходники dirty, чужие правки сохранены. В общую сборку также входит завершённая
правка death checkpoint map fence из соседнего чата. Сейвы/settings не менялись,
игровые файлы не редактировались; процессы не завершались.

## Build/deploy07.11

DLL build exit0/8 inherited warnings,0 source-input changes; delta/deploy exit0,
5files. Backup native-ai-activation-20261107-20261107-011225. P1/P2 existing CMD
launch requested01:12:26MSK. New heap investigation started in adjacent crash
chat during post-build audit; no source changes at packaging check. The installed
snapshot does not claim completion of that new investigation. Startup pending.
Startup confirmed07.11 01:12:56MSK: both P1/P2 run_20261107_011256.log,35/35 selected hooks, native activation completion banner in both; native PIDs10032/26628. Gameplay OPEN.

## 07.11 — повтор run011256: metadata retained / per-NPC AI UNVERIFIED

Сбор retest-pc/: exit0,2files,warnings0, оба ChangedDuringCopy=true. Обе startup
banner подтверждают установленный native activation completion механизм.
Интервал до01:16:25МСК; P1=game-7/60ac283d, P2=game-14/c305d7f3.

- П2 в01:14:18.450 был follower П1 в Old Yharnam0x17000000.
- П2 сам ушёл в Dream01:14:33.472–01:14:36.121, затем прибыл в Cathedral
  Ward0x18000000/visit4 в01:14:57.959 и получил role1 в01:14:58.064.
- П1 в этот момент остаётся Old Yharnam0x17000000/visit1; он начинает загрузку
  в Dream лишь01:15:43.975 и прибывает01:15:46.524.
- П1 возвращается01:16:09.231 снова в Old Yharnam0x17000000/visit3,
  owner60ac283d/role1. У П2 после01:14:58.064 нет нового AI authority commit
  или локальной загрузки. То есть его metadata owner не был отобран.
- Этот прогон НЕ содержит ухода хоста из той же metadata scope П2: игроки
  разделили карты раньше. Карты Old Yharnam и Cathedral Ward соседние.
- В01:16:19.039 у П2 native enemy loot eligible=true. Это не доказательство
  AI/агро/движения и не идентификация того, когда NPC впервые был streamed.
- Relay обоих до01:16:21: очередь0/dropped0; fault в собранных логах не найден.

Ограничение диагностики: BbscWorldNpcActivated не пишет итог по NPC и не имеет
счётчика/BBSC_PERF scope. Startup banner — свидетельство установки, НЕ фактического
вызова или записи word1. Отсутствие строк не является отсутствием вызовов.
Нельзя по этим логам подтвердить передачу ИИ поздним NPC или её сохранение
после возврата; подтверждено только сохранение map lease. Нет оснований объявлять
игровое исправление PASS/CLOSED. Новые циклы/опросы/диагностика в мод не добавлялись,
код/установка/процессы/сейвы/settings при этой проверке не менялись.
