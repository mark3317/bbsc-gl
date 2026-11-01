## 2026-11-02 — повторная выдача shared keys, прогон 02:30–02:37 МСК

Логи обеих машин: bloodborne_pc/out/coop-dev/runs/keys-20261102-0231.
На клиенте семь shared keys повторно показаны в 02:33:51, 02:34:39,
02:36:31. В 02:35:42 те же предметы восстановлены K2-trip без окон.
Причина: shared-key tick мог опередить ledger reconciliation текущей загрузки;
постоянная принадлежность проверялась по временному phantom inventory.
Дополнительно FinishBbscTripAtHome удалял receipts через 60 секунд дома/при join.

В исходниках обоих checkout: shared keys ждут BbscGuestLoadItemsReady;
receipt из сериализуемого per-user/per-slot trip journal означает полученный
предмет, восстановление без popup/новой записи Given. Shared-key receipts
сохраняются при FinishBbscTripAtHome; запись Key гарантированно попадает в journal.
Формат файла не изменён. Старые уже удалённые receipts восстановить задним числом
невозможно: при наличии предметов join снова фиксирует их в журнале.
Проверки test_shared_keys.py и test_load_readiness.py PASS (clang++).
Код не собран и не установлен, игровой результат pending. Живые сейвы,
настройки и metadata не менялись. Запуск игры не выполнялся.

