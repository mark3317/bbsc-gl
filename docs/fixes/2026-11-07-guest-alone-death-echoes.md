# Потеря отголосков гостем при смерти без напарника на карте

Статус: LOG CONFIRMED / CLOSED для проверенного guest-alone сценария.
07.11 П2run051950: Central05:40:10 смерть с4860;05:40:14 native drop
4860->0/stain4860 до reload;05:40:17 alive. П1на другой картеOldYharnam.
Повторного списания до выхода05:40:50 нет. Пользователь: «вроде все корректно».
Подбор пятна отдельно не проверялся. Evidence parent
out/coop-dev/runs/p2-central-echoes-confirmed-20261107/analysis.md.
Ниже — исходные детали исправления и целевых проверок; прежний source-only
статус заменён результатом игрового прогона. При анализе реальные сейвы/settings
и код/DLL не менялись.

## Причина и исправление

П2 run033751: Central Yharnam, PartyGhostDeath04:02:22.557, type1/own0,
85345 отголосков; reload04:02:26.174 с причиной no living partner at the
death step; alive04:02:29.327. П1 был в Yahar'gul. Диагностика и копии логов:
parent out/coop-dev/runs/p2-central-echoes-20261107/analysis.md.

BeginBbscCoopDeath в independent mode без живого напарника на карте выбирает
перезагрузку вместо оживления на месте. В этой ветке не было вызова
BbscApplyDeathPenalty, а оригинальный PartyGhostDeath_2 у co-op type1
не создаёт пятно крови и не списывает отголоски.

Теперь существующая ветка bbsc_request_death_reload в TickBbscSpectate
вызывает BbscApplyDeathPenalty для independent guest session6, исключая
invader, после завершения native death body и RestoreBbscOwnWorldSnapshot,
но до RequestBbscDeathReload. Поэтому старые actor/map ещё доступны для drop,
включая возможную ветку shared-lamp reload внутри RequestBbscDeathReload.

Это существующая обёртка над штатным DropBloodstain013D2910: она переносит
отголоски в пятно крови, временно выбирает локальное место смерти гостя,
возвращает own-world flag, потребляет snapshot смерти и защищает от повторного
списания. Новых записей счётчика или отдельного создания пятна в правке нет.
Ожидания, анимации и native cleanup сохраняются.

Похищение обработано выше отдельной native веткой и не затрагивается.
Host/solo/invader/legacy routing не меняются. Флаг запроса сбрасывается перед
обработкой, поэтому следующие обычные кадры не повторяют penalty.

## Стоимость

Новых hooks/ticks/таймеров/опросов/очередей/пакетов/обходов нет.
В простое новая ветка не выполняется; на уже запрошенную смерть добавлены
проверки режима/роли и один существующий native drop для гостя. Количество NPC
и удалённых игроков не добавляет работы. Живые FPS этой ревизии не измерялись.

## Проверки

- tools/test_independent_death_destination.py: извлечённые production Begin+Tick,
  вызов penalty до reload, один вызов за смерть и повторная смерть, host/solo/
  invader/legacy exclusions; прежние spectate/load/abduction сценарии PASS.
- BBSC_TEST_GUEST_RELOAD_NO_PENALTY=1 удаляет только новый вызов из production
  Tick: ожидаемый assert на порядке penalty/reload, negative control PASS.
- tools/test_death_accounting.py: production penalty и native boundary fixture,
  перенос в stain/обнуление, две смерти, отсутствие двойного списания,
  native refusal/gate, восстановление guest own-world flag PASS.
- tools/test_snatcher_abduction.py: production gates/readiness/personal rules PASS.

HEAD подмодуля46a4ac2, parent pin6e7d32f сохранены; ранее существовавшие
изменения обоих деревьев не включались в коммит. Коммит не создавался.
