# Проверка сохранности оптимизаций после serverless — 03.11.2026

Только анализ и изолированная проверка backlog. Runtime исходники, установленная
сборка, процессы игр и сейвы не изменялись. Текущий BBSCeab2dc2/BBGL1e8f5e3.

## Метод и история

Прочитаны perf-runtime-review, perf-bounded-work, perf-after-review,
perf-cap60-review, perf-guard-snapshots, perf-combined60-review от02.11 и
death-http-perf от03.11. История содержала как исправления, так и отрицательные
замеры: нет общего доказанного FPS gain от каждой итерации. Сравнение старых
FPS с нынешними без одинаковых сцен/ролей/cap не выполнялось.

Для точного сравнения восстановлен baseline не только из git HEAD, но и из
сохранённого dirty patch: BBSC151e24c + out/serverless-baseline/bbsc.patch;
parent572e066 + parent.patch. Hunks проверены по контексту при восстановлении,
исходное рабочее дерево не менялось. Результаты — out/serverless-perf-audit.

Десять функций совпадают текстуально с baseline: FindBbscParamTables,
BbscGameParamTable, BbscParamViewFor, LocalizeBbscQuestEvent, TickBbscScaling,
MergeBbscSharedProgress, BbscInventoryHas, BbscDreamTypeCheckHook, QueryRegion,
LogLine. RegionCache128/250ms также сохранён. В родителе полностью совпали
p2p_transport.cpp/.h, p2p_relay.cpp, network/http.cpp и bbsc_connect_retry.h.

Следовательно сохранены: active repository вместо полного memory scan; индексы
NPC с проверкой lifetime; guard snapshots; region last-hit; scaling owners1Hz
для неизменившегося ключа; armor максимум128 прямых/8 fallback строк с проверкой
1ms; dirty/empty progress merge до backup; buffered logging; bounded native
HTTP connect retry. Не возвращались многоминутный поиск таблиц и многотысячный
неограниченный armor проход. Но новые вызовы вокруг старых функций требуют
самостоятельной оценки — неизменность функции не доказывает прежнюю частоту.

## Найденные ухудшения и риски

### 1. Конкретный возврат HTTP backlog5 вместо128

История death-http-perf: QuietHTTPServer.request_queue_size=128,
server/gameserver/bbsc_gameserver.py1534–1537. Новый compat.py162 создаёт обычный
http.server.ThreadingHTTPServer без этого параметра. Local Python3.14.6:
TCPServer/ThreadingHTTPServer.request_queue_size=5. В установленном пакете
используется python314.dll (проверено имя, не хэш).

Изолированная проверка production Compatibility.http, accept намеренно не
запущен,24 параллельных connect с timeout250ms: текущая очередь5 допускает5/24,
тот же ThreadingHTTPServer с queue128 —24/24. JSON результата сохранён.
Это воспроизводимая потеря burst capacity, не доказательство причины прежнего
menu/rejoin: там логи указывали на cancel latch и One outstanding command.

Рекомендация первым небольшим изменением: вернуть явный backlog128 в private
HTTP adapter. Native connect retry уже сохранён и не заменяет нормальную очередь.

### 2. Новый перекадровый расход даже в legacy launch

bloodborne_re.cpp21343–21347 вызывает PartyObserve(GetSessionState(), native
loading checks, BbscLocalEffectNode9000) на каждом game tick под BBSC_MOD.
PartyEnabled проверяется внутри PartyObserve, после вычисления аргументов.
Значит legacy тоже выполняет дополнительные чтения и поиск SpEffect, хотя их
результат не используется. Это нарушает принцип дешёвого выключенного режима.
Величина в microseconds/FPS не измерена; объявлять большой FPS ущерб нельзя.

Минимальное исправление: guard PartyEnabled на call site до вычисления полей;
для party переиспользовать свежий tick-context/измерять отдельным perf scope,
не вводить устаревающий pointer cache и не ослаблять native lifecycle наблюдение.

### 3. Relay persist/fsync и сеть под общей Engine.lock

engine.py26–32,350–363,386–432: каждый ingress relay frame записывает весь
party-journal с flush/fsync/replace. Это делается под той же lock, что request,
snapshot, publish и управляющие API. wire.connect/sendall также исполняются
внутри этой lock. Приём до256 сообщений за проход ограничен количеством, но
не временем: стоимость disk/network одного сообщения может быть большой.

Следствия по коду: игровой трафик BBSC способен задерживать role/leave API;
медленный peer тормозит остальных; UI title-gate может дольше ждать. Это worker
нагрузка, не fsync прямо в native game tick. Исключение — PartyAcquire на
настоящем использовании Зовущего синхронно ждёт HTTP до8500ms. Подтверждение
перед native execution необходимо, но блокировать весь callback этим временем
не единственный возможный дизайн (асинхронное разрешение потребует отдельного
проверенного resume/повтора действия). Это задержка действия, не каждого кадра.

Рекомендация: выделить disk/state commit и outbound I/O из общей секции;
компактное durable принятие важных команд, RAM/resync для повторяемого состояния.
Не убирать fsync с прежним обещанием crash dedup и не ослаблять role quorum.

### 4. Stop-and-wait делает сеть чувствительной к RTT

engine.py417–432 допускает только один исходящий relay frame до ACK всех его
адресатов; повтор каждые80ms. При RTT100ms теоретический потолок не более10
кадров/с, до fsync/worker задержек. Compact WorldFlags burst:5 blocks ×4chunks
=20 кадров/с; steady2 blocks ×4=8, плюс follow2/s, life2/s, scale и прочие.
При таком RTT очередь закономерно может расти. Повтор80ms способен переслать
пакет ещё до первого ACK нормального100ms пути. Очередь128/expiry10s ограничены,
но вместо бесконечного роста будет отказ/перезапуск канала.

Это расчёт из кода, не WAN benchmark; LAN результаты не доказывают такую нагрузку.
Смена адресатов уменьшила вред idle peers, но active slow peer остаётся барьером.
Нужны bounded window/per-peer scheduling и приоритет lifecycle сообщений,
отдельные политики для snapshots и одноразовых действий. Части WorldFlags
нельзя объединять одним типом: map/snapshot/chunk/dungeon generation сохраняются.
Нативные игровые датаграммы не входят в этот reliable поток.

### 5. Дополнительный relay dispatch delay и worker starvation

compat.py416: monitor спит50ms, лишь затем пересылает ingress frame в native
socket. Это до порядка50ms ожидания при нормальном незаблокированном worker,
плюс engine polling10ms/передача. Не50ms гарантированно на каждый пакет и не
верхняя граница при нагрузке. Тот же monitor делает синхронный command.wait8s,
sendall с socket timeout10s и до drain пропускает работу при non-final state.
Таким образом ACK ingress может уже быть отправлен, а доставка native ещё ждать.
Старая native TCP queue статистика не показывает Python relay_out/in/pending.

Рекомендация: отдельный notification/event-driven relay dispatch; state-machine
maintenance не ждёт command completion в том же worker. Сохранить generation/
connection/member fences и запрет delivery из недопустимой сессии.

### 6. Loopback HTTP polling и повторные копии

bbsc_party.cpp Call создаёт/закрывает WinHTTP session/connection/request при
каждом вызове. WatchThread фактически вызывается после Sleep500ms, хотя внутри
PartyMaintain стоит250ms guard: без задержек это около2 проходов/с, не4.
До отмены2 RPC за проход, после любого cancel3 RPC за проход. Поскольку cancel
монотонный, /leave_ready продолжает опрашиваться после Бланка/успешного выхода
весь процесс, даже когда новый title-exit не ожидается. HTTP обработчик создаёт
поток на запрос. Это несколько новых RPC/threads в секунду на устройство,
не прямой syscall на каждый кадр. Не вызывать это12RPC/s фактической сборки.

compat monitor дополнительно deepcopy state каждые50ms; relay routing делает
snapshot для каждого кадра. Native counters/atomics title cache сами дешёвые;
сетевые проверки вынесены за patch_mutex и из game tick — это правильно.
Рекомендация: единый bridge status RPC/ответ с availability+leave ACK,
persistent session, title pending ticket вместо вечного cancel!=0 polling;
revision check перед deepcopy. Не принимать ACK от старого ticket и не заменять
подтверждение выхода таймаутом.

## Что уже улучшено первым этапом

Status8.3/s→0.5/s при неизменности + публикации при изменениях; compact
WorldFlags5→4 части; session-only адресация; удалена лишняя world_ready.
Это сокращает поток, но не исправляет lock/fsync/window/dispatch issues выше.
Старые research-heavy логи можно включить независимо от compact wire.

## Вывод и порядок

Основные прежние оптимизации игрового кода сохранены. Новый серверный слой
внутри клиента добавил работу и несколько путей задержек; утверждать, что
производительность в целом не ухудшилась, нельзя. Нет нового matched FPS/frame
benchmark, и старые разносценовые отчёты не дают процента падения.

Первыми: backlog128, legacy call-site guard, leave RPC только при pending title,
revision-based copies. Далее: убрать I/O из общей lock и50ms/8s relay dispatcher
coupling; bounded pipeline ACK. Затем baseline/delta/dirty writes. Сохранить
выход до menu load и invariants role/journal/WorldFlags. Измерять latency/queue/
fsync отдельно от игрового FPS. Никаких сборок/деплоя/новых игр в рамках аудита.
