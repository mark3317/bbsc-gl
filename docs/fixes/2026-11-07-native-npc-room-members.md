## 07.11.2026 — NPC AI и движение: USER CONFIRMED / CLOSED

Пользователь после проверки сообщил: «ок, все работает правильно».
Закрыты проверенные сценарии: выдача штатного ИИ новым NPC у клиента без
хоста на карте, сохранение работы при возвращении хоста и синхронизация
передвижения общих NPC при нахождении игроков рядом. Основание полного
игрового результата — подтверждение пользователя; read-only снимки ранее
подтвердили cross-map grants/пустые очереди и согласованное движение рядом.
Native transport admission01789274 и room-member boundaries работают вместе;
новых циклов/опросов/таймеров/пакетов нет. Ранние FAILED/OPEN по этим сценариям
ниже исторические. Иные несвязанные задачи этим подтверждением не закрываются.
Evidence parent out/coop-dev/runs/npc-transport-chalice-uncap-20261107/retest-analysis.md
и out/coop-dev/runs/npc-nearby-motion-20261107/analysis.md.
В этом ходе код/DLL/сейвы/settings не менялись, процессы не завершались.

# Native NPC grants без загруженного PlayerIns

SOURCE FIXED / targeted checks PASS / NOT BUILT / NOT INSTALLED / gameplay OPEN.

## Доказанный отказ

Run033657/033751: П1/host на другой карте, П2/guest в Central Yharnam.
У П228active REMOTE/FFFF; три проверенных живых NPC HP343/150/70,death0.
В native room2members, но у host только local PlayerIns slot0 и собственная
NPC request-list. Предыдущий fixture начинался с готовых списков и не исполнял
actor-dependent admission/recipient lookup.

В оригинале1.09 найдены ТРИ зависимые границы:

- 018F092C..09BE после успешного ReceiveFromMember(channel16) ищет sender
  через live PlayerIns world+30/+38 и actor+3D8; отсутствующий actor теряет заявку.
- 018ED1B6..01FA перед merge удаляет request-list, если её player handle не
  разрешается в live actor. Одного исправления intake недостаточно.
- 018ED470..0524 перед SendToMember(channel17) снова требует live PlayerIns.

## Исправление

Три byte-verified native condition rewrites в прежних обработчиках. Каналы16/17,
формат/частота/receive/send, native allocation/list assignment/pruning/merge,
NPC grant words и ранний EnemyIns остаются оригинальными.

Внутренний request-list participant key теперь может быть непрозрачным tagged
ID, привязанным к полному текущему RegisterIdentity и full WorldId. Он НЕ входит
в пакет и НЕ является новым сетевым протоколом. Свой player handle сохраняет исходную native проверку и быстрый путь без
C++ callback. Старые положительные remote keys удаляются после включения
room-key mode: иначе один гость может получить две части grant в разных
пакетах, каждый из которых сбрасывает полную таблицу ownership words.

`BbscWorldNpcRequestMember` проверяет native host role3, текущую комнату/хоста,
согласованный peer, актуальную native membership и точный размер count/payload
(4..4096байт). Невалидные/чужие/self заявки не создают binding. До первого включения room-key mode сохранён прежний native join fallback.
После принятия первого room-key запроса режим сохраняется в той же комнате
через временный Loading/negotiation, чтобы не создавать PlayerIns-keyed alias. Допуск не зависит
от карты/видимости/указателя персонажа.

`BbscWorldNpcRetainMember` отбрасывает legacy remote alias, а
`BbscWorldNpcGrantMember` для сетевых keys повторно проверяет
комнату, native host, действующего участника и полный identity. Сохранённых
actor или roster pointers нет. Для отправки реальная текущая native identity
подаётся в исходный SendToMember; его транспортные проверки не обходятся.
Original018ED399 делает add3D8 кR14, поэтому emitter подготавливает R14=entry-3D8;
это арифметика исходного адресного выражения, не создание фиктивного PlayerIns.

Existing OnBbscPeerLeft удаляет только metadata binding. Ключи монотонны за
жизнь процесса, не переиспользуются при rejoin/смене комнаты и fail closed при
исчерпании диапазона. Identity replacement, исчезнувшая native membership и
переход в другую комнату отклоняют старый ключ. При обнаружении потерянного
участника в существующей границе binding также освобождается. Native prune
удаляет старую request-list обычным путём, когда выполняется его прежний проход.

Однократный timeline при новом binding:
`NPC native request member admitted ... actor_required=false`.
Повторные пакеты/обычная выдача не добавляют heartbeat logging.

## Объём и стоимость

Новых ticks/таймеров/опросов/retry/очередей/пакетов/обходов NPC/сканов памяти нет.
Существующий actor-dependent lookup заменён существующим ограниченным поиском
native membership (`BbscWorldNativeMember`, максимум8 участников). Две небольшие
map-таблицы содержат максимум8bindings, обновляются на фактических заявках и
событиях ухода/смены identity/комнаты. Actor pointers не затрагиваются на receive
thread; OnPeerLeft меняет только metadata под отдельным mutex.

Два lookup на участника в выполняющемся original grant transaction (retain/send),
не на NPC; native NPC loops и их частота прежние. Fixture с64NPC подтверждает
ровно2resolve calls, как и с одним. При отсутствии remote request-list эти
callback границы не выполняются (отдельный fixture idle assertion); self
продолжает исходную проверку через несколько native инструкций. Дополнительного
idle tick нет.
Это ограниченная дополнительная стоимость исходных транзакций; реальный FPS
и работа UDP между двумя играми ещё не измерены/не подтверждены.

## Проверки

`tools/test_native_npc_member_authority.py` исполняет ORIGINAL018F0780 intake,
018F0B70 list creation и01A6C420 ctor, assignment/merge, полный host grant stage
018ECEB0..018ED68F (включая prune/recipient), затем original guest receive/apply,
EnemyIns binding/model/update и исходное формирование XYZ packet. У host нет
remote PlayerIns и нет таблицы NPC клиентского блока, у guest grant появляется
и одновременно включает LOCAL brain и position sender. Пустая заявка снимает
оба допуска. Native allocator/transport delivery — границы fixture, actual UDP
не исполняется; последующие unrelated native object channels после grant stage
не включены в этот сценарий.

Проверены malformed size/count, self/foreign sender, не-host, actor recreation,
появление/исчезновение remote actor, join legacy alias при одновременном
существовании room key, временный inactive без смены key space,64NPC payload,
полный native grant без remote actor, native one-member early exit,
disconnect/rejoin, full identity и room fencing, key exhaustion. PASS.
Три negative controls отдельно возвращают старые request/retain/grant gates;
каждый воспроизводит отказ ожидаемого assertion.

Direct dependencies: `test_native_npc_authority.py` — native readiness/LOD,
sticky discoverer, arbitration, brain и XYZ codec/sender/receiver PASS;
`test_native_npc_sync_mode.py` — все6native rewrite spans fail closed,
callback wiring, native/legacy/default и2000ticks без нового NPC tick work PASS.
MOD syntax PASS. Не запускались полные тесты или save/restore проверки.

Исходники только mods-src/BBSC. HEAD46a4ac2, parent pin6e7d32f не менялись;
чужие dirty changes сохранены. DLL этой правки не собиралась/не устанавливалась,
игры/сейвы/settings не менялись. Баг gameplay остаётся OPEN до нового прогона.

## 07.11.2026, 04:32 МСК — NPC room-member admission: BUILT / INSTALLED / P1+P2 STARTED; gameplay OPEN

Общая DLL из согласованного dirty-tree46a4ac2 собрана exit0 (8warnings),
inputs size/mtime не менялись. Delta5files/deploy exit0; backup
D:/Games/Bloodborne/coop-dev/backups/npc-room-members-village-20261107-20261107-043121.
Включены завершённые соседние правки native menu обоих ролей, corpse glow,
guest echoes, Rom personal effects и boss-before-spectate.
P1 run043145/PID20148, P2 run043223/PID14612: оба live,35/35hooks и новый
NPC native member admission ready. Это подтверждает загрузку исправления,
не выдачу ИИ в игровом сценарии. Cross-map/new NPC/host return/nearby gameplay OPEN.
По просьбе пользователя текущие сейвы обоих профилей (full savedata + BBSC journals)
сохранены как D:/Games/Bloodborne/coop-dev/saves/деревня; восстановления не было.
cheat_no_death=1 у обоих, прежние INI сохранены в snapshot. Игры не завершались.
Evidence parent out/coop-dev/runs/npc-room-members-village-20261107/run.md.


## 07.11.2026 — Central NPC: transport receive gate FOUND / SOURCE FIXED / checks PASS

Пользователь подтвердил отсутствие ИИ. Read-only04:43МСК: P2Central28active
REMOTE/FFFF, hostужеимеет25requests block5, уP2 channel17queue24/native state4,
нонетremote PlayerIns. Original ReceiveFromMember01789274 classification
на16/17требуетPlayerIns ДО queue read; ReceiveFromHost вызываеттотжепуть.
Native mask расширен ровно bits15/16 в прежней verified инструкции;
прочиеchannels/session/identity/endpoint gates прежние. Новых loops/hooks/
опросов/пакетов/callbacks нет. Startup-only marker. Previous fixture stubs
ReceiveMember/ReceiveHost скрывали gate; теперь исполняются original functions.
Full receive/intake/list/grant/guest/brain/XYZ +24queued backlog PASS;
5negative controls, installer7spans/native modes/2000ticks иMODsyntax PASS.
NOT BUILT/NOT INSTALLED/gameplay OPEN; игрыlive, не завершались.
Details fixes/2026-11-07-native-npc-transport-admission.md, parent evidence
out/coop-dev/runs/npc-central-transport-20261107. HEAD/pinсохранены.
