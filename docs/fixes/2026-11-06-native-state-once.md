# Однократное состояние карты от оставшегося участника

06.11.2026. User scope: только state transfer при loading; без polling/retry.

Логи parent out/coop-dev/runs/map-owner-native-20261106/pc содержат текущий
run224634 обоих профилей. P1 host возвращается в Central Yharnam в22:49:43,
22:51:35 и22:58:19; P2 остаётся на карте в первых двух интервалах.
Startup обоих явно сообщает native path с history/packet hooks OFF.
Логи не содержат NPC death bitmap и сами по себе не доказывают всех убитых;
видимое обнуление сообщено пользователем. Код подтверждает отключённый initial path.

ChooseOwner уже удерживает resident после возвращения хоста. Выбор и фактическое
NPC владение не менялись. Guard pre-event native branch вызывает load-scoped
однократный запрос без ожидания/остановки событий. Scope включает world/map/
ritual; request и load отвергают старые ответы. Если resident отсутствует,
запрос не отправляется и не повторяется до новой загрузки.

Provider в существующей game-thread обработке входящих controls вызывает
original01786360 для реального native member. Existing send ENTRY захватывает
только этот явный snapshot, не отправляя второй native11 и не затрагивая обычные
пакеты. Existing controls8/9+parts переносят максимум0x6400байт исходного native
пакета. Complete response один раз вызывает existing local block preflight и
original0190E8B0, который выполняет historical death/removal. Никаких HP/Kill
writes, новых NPC очередей/тикеров/таймеров/каналов, повторов и ownership scans.

Нужна небольшая адаптация доставки: ready descriptor и native11 находятся в
разных транспортных очередях, так что один receive по descriptor не гарантирует
наличия пакета. Передача bytes в existing control fragments позволяет обработку
по поступлению события без receive polling. Это временный буфер на loading,
а не постоянное состояние врагов.

PASS: test_world_native_initial_once.py (production request/control/capture,
2000 повторных loading callbacks без resend, host leave/return, guest33,
fragments out-of-order/duplicates, old request/load, preflight fail consumed once);
test_native_npc_sync_mode.py, test_world_presence.py,
test_world_native_bootstrap.py (mode0), test_world_native_initial_streaming.py,
test_independent_native.py; original out/exit-study.elf serializer/handler/site ABI.
No real save/game asset/settings edits. Источник подмодуль, HEAD/pin6e7d32f.

Build/deploy/gameplay statuses: parent run.md. Игровой критерий: P2 остаётся
в Ярнаме с убитыми врагами, P1 уходит в Сон и возвращается; старые смерти
сохраняются. Повторить со сменой прибывающего. В полном отсутствии игроков
однократная передача resident не выполняется; штатные правила сброса сохраняются.

## Игровое подтверждение — 07.11.2026

Пользователь: «готово, посмотри по логам. все работает».
Сценарий сохранения состояния карты при возвращении подтверждён пользователем.
Логи collected parent confirmed-pc-20261107:8files,warnings0,2ChangedDuringCopy;
учтены четыре запуска обоих профилей после установки, включая run001041.
В последнем run guest00:13:09.484 applied=true от resident7fd55db9;
returning host00:14:22.399 applied=true от resident96f74711.
Host loads3/5/7: ровно3requests/3results; guest load3:1request/1result.
Owner96f74711 удерживается после возвращения хоста; новых запросов внутри
одной загрузки в записанном интервале нет.

Ограничение доказательств: host00:15:01.693 и00:18:11.418 applied=false;
ранний run231528 также23:17:52.789 applied=false. Это отказ existing native
initial validation/application, а не успех. Конкретный early return не записан,
поэтому нельзя объявлять каждый native снимок применённым или объяснять весь
видимый результат одной этой правкой. Пользователь подтвердил нормальное
поведение и при текущем one-shot подходе; дополнительных механизмов не вводили.
User-visible сценарий CLOSED; техническое наблюдение о rejected initial остаётся.
Код/бинарники/сейвы/settings в этом сборе не менялись. Другие чаты после этой
правки обновили сборку (текущий HEAD e7005ff); эти изменения не выполнялись здесь.
