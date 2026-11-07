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

# Центральный Ярнам: разрешения NPC доставлены, но не читаются

07.11.2026. Gameplay FAILED подтверждён пользователем для установленной DLL04:31.
SOURCE FIXED / targeted checks PASS; NOT BUILT / NOT INSTALLED / gameplay OPEN.

## Живой отказ

По просьбе оставлены P2Central, P1на другой карте (Yahar).
Read-only снимок01:43UTC: P1native host3/PID20148; P2guest6/PID14612.
P2Central block5:28active, всеREMOTE/FFFF, model bound.
У host native request-list key80000002 уже содержит25заявок block5.
Оба native room roster имеют2участников. УP2 remote PlayerIns slots пусты;
уhost пока сохраняется remote PlayerIns. Поэтому приём заявки host возможен,
а приём grant guest блокируется.

live-native-transport-queues.json01:43:24UTC: network state4уобоих;
уP2 endpoint channel0x17 queue24, первый grant52bytes/count12.
Каналы0x16уобоих и0x17уhost пусты. Очередь полученных разрешений существует:
это не доказательство потери UDP или отсутствия host arbitration.

## Точная причина

Оригинальный ReceiveFromMember01789200 сначала проверяет native session,
потом классифицирует channel01789268..0178929D. Имеющийся allowlist
0x80000000004067B не содержит bits15/16 (channel0x16/0x17 минус7).
Оба канала попадают в поиск sender среди live PlayerIns world+30/+38.
Нет PlayerIns ->01789369 return0 БЕЗ чтения endpoint queue.
ReceiveFromHost017893E0 после проверки роли/hostidentity вызывает этот же
ReceiveFromMember. Оттого channel17backlog остаётся при наличии native endpoint.
Ранее исправленные018F092C/018ED1B6/018ED470 находятся ПОСЛЕ этой границы;
fixture подменял ReceiveMember/ReceiveHost и не мог поймать ранний отказ.

## Правка

В native-NPC installer добавлен byte-verified rewrite10bytes01789274:
тот же movabsRCX, native mask OR только bits15/16 ->0x80000000005867B.
Исходные native session/role/hostidentity/endpoint lookup/queue consumption,
packet size и room-key admission/retention остаются. Для всех остальных
каналов actor policy прежняя. Send path не менялся: live network state4,
реально полученная queue доказывает прохождение его gates в этом сценарии.
Новых hooks/циклов/опросов/ticks/таймеров/retry/пакетов/NPCwalks нет.
Переписан существующий operand classification; дополнительные C++ callbacks
на пакет не добавлены. Штатный actor lookup на этих двух каналах пропущен,
ценой перехода в/из verified rewrite. Startup-only marker о transport admission.
Дополнительное периодическое или per-packet логирование не понадобилось.

## Проверки

Расширен test_native_npc_member_authority.py: теперь выполняет ORIGINAL
ReceiveFromMember и ReceiveFromHost, а не их заглушки. Низкая доставка в очередь
и native session/identity services остаются границамиfixture. Full intake/list/
prune/merge/grant/guest apply/EnemyIns local update/XYZ sender безremoteactor PASS.
24старых queued grants + последний grant новой карты полностью прочитаны,
последнее слово1 иLOCAL brain/XYZ sender подтверждены тем жеnativeпутём.
Exhaustive channels0..44: доnative queue доходят прежние каналы плюс ТОЛЬКО16/17.
Неизвестный endpoint иnative offline отклоняются. Tests с актёром и без него,
legacy alias, native identity/room fencing иempty release сохранены.
Negative controls transport(request),transport-grant,request,retain,grant
воспроизводят соответствующие assertions. Installer7verifiedspans failclosed,
native/legacy/default2000ticks безновойNPCработы PASS. MOD syntax exit0.

Логи двух профилей собраны вpc, exit0/2files/warnings0, live snapshots.
Исходники толькоmods-src/BBSC, HEAD46a4ac2/pin6e7d32f сохранены.
DLL не собиралась/не устанавливалась в этом ходе. Живые игры не завершались,
память/сейвы/settings не менялись. Игровой результат после установки OPEN.

## 07.11.2026, 04:52 МСК — NPC transport: BUILT / INSTALLED / P1+P2 STARTED; gameplay OPEN

DLL build exit0/8warnings, input metadata unchanged, related chats ready.
Delta5files/deploy exit0; backup
D:/Games/Bloodborne/coop-dev/backups/npc-transport-chalice-uncap-20261107-20261107-045036.
P1 run045100/PID24468, P2 run045142/PID37116: оба live,35/35hooks и новый
NPC native transport admission ready. Новая маска каналов загружена;
работа ИИ Central безhost/после возврата/рядом ещё требует игрового подтверждения.
По запросу восстановлены личные наборы Player1/2 изchalice-tests-20261104-143129,
fullsavedata+matchingBBSCjournals; более поздние journals отложены с прежними
сейвами. Backup текущего состояния:
D:/Games/Bloodborne/coop-dev/saves/before-npc-transport-chalice-20261107-044927.
«Деревня» и исходные снимки сохранены. fps_mode=uncap/frame_cap=0 обоим;
бессмертие вINI сохранено. Процессы не завершались,HEAD/pinне менялись.
Evidence parent out/coop-dev/runs/npc-transport-chalice-uncap-20261107/run.md.
