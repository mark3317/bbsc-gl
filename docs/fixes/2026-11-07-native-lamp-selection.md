# 07.11.2026 — штатный выбор личной лампы после общего зажигания

Пользователь сообщил: П1 переместился в Гробницу Идон, погиб, возродился
в Центральном Ярнаме рядом с П2. Снимки обоих участников:
`out/coop-dev/runs/personal-respawn-20261107/pc` родительского проекта;
сбор exit0,2files,warnings0. П1=host, П2=guest.

## Доказательство

В host run_20261107_001041.log00:11:32.219 shared lamp2412951/revision1.
00:14:53.634 native request2412953;00:15:01.698 native checkpoint
2102950→2412953.00:15:27.678 retained revive выбирает last lamp с координатами
(-193.40,-28.65,68.50), как предыдущий revive у2412951.
Штатный checkpoint был правильным, shared resolver подменял его старой записью.

## Итоговое правило пользователя

Новое зажигание любым участником обновляет общую точку. Более позднее личное
перемещение выбирает собственную штатную лампу. Позднейшее зажигание снова
побеждает. Возрождение на арене после победы над боссом остаётся первым выбором.

На существующем native point-load boundary отмечается дата живой поездки.
Existing actual lamp activation записывает UTC-время зажигания в существующий
LampCheckpoint (payload12bytes вместо4); повторы сохраняют дату. Shared resolver
возвращает false, если личный native выбор новее. Тогда retained revive читает
штатный global+1528, а reload продолжает уже выбранный01332BC0 destination.
Host дополнительно не принимает более старое зажигание как новое из-за задержки
доставки. Изменения не добавляют ticks/hooks/опросы/таймеры/очереди/повторы.
Стоимость и условие синхронных часов записаны в OPTIMIZATION.md.

## Проверки

- test_shared_lamp_checkpoint: production host/two guests, same-map Oedon vs
  Central, later ignition, first delayed delivery/replay, out-of-order activations,
  dead point-load, existing scope/ritual/ordering/reload tests PASS.
- BBSC_TEST_LAMP_PRIORITY_OLD=1: возврат старого приоритета ожидаемо FAIL;
  negative control PASS.
- BBSC_TEST_EBOOT=parent out/exit-study.elf: original1.09 native point-load PASS.
- test_world_travel_native: production callback registers selection once PASS.
- test_boss_lamp_respawn:19original boss destinations, priority/roles/stale guards PASS.
- test_independent_death_destination: ordinary fade/boss hold/wipe/native kidnap PASS.
- test_lit_lamp_checkpoint: actual ignition for both roles/catalog/dungeons PASS.

SOURCE READY. Build/deploy/gameplay статусы дополняются отдельно.
Сейвы/settings/файлы игры не менялись; действующие процессы не завершались.
