# BBSC-GL 1.5.10

Опубликован / Published: 11.11.2026, 02:08 МСК (10 November, 23:08 UTC).
Публикация проверена повторно / Publication rechecked: 13.11.2026.
[GitHub Release](https://github.com/mark3317/bbsc-gl/releases/tag/v1.5.10).

## Русский

Для **BBGL 1.5.10**. При подтверждении Бланка молчания закрепляется контекст штатного предмета, чтобы предыдущий расходник не задавал действие. После местного возрождения штатный OnEvent_4019 восстанавливает коллизию и гравитацию, затем обновляется физическое представление. Новых цикличных проверок и сетевых сообщений нет.

Распакуйте ZIP в папку с `Bloodborne.exe` при закрытых игре и лаунчере. Обновите всех участников. Для первой установки используйте [полный BBGL 1.5.10](https://github.com/mark3317/bbgl/releases/download/v1.5.10/bbgl-1.5.10-windows-x64.zip).

Стенды с оригинальным кодом прошли. Восстановление коллизии подтверждено в игре для хоста после падения; визуальная проверка Бланка у обоих участников остаётся открытой. Прежний случай исчерпания сетевого пула остаётся открытым. Отдельный необязательный Pig Invasion входит в полный ZIP BBGL, выключен по умолчанию и не входит в этот ZIP кооп-мода.

## English

For **BBGL 1.5.10**. Confirming a Silencing Blank binds its native item context so a previous consumable cannot supply the action. After an in-place respawn, native OnEvent_4019 restores collision and gravity before the physics proxy is synchronized. No new polling or network messages.

Close the game and launcher, then extract into the folder containing `Bloodborne.exe`. Update every player. For a first installation, use the [full BBGL 1.5.10 package](https://github.com/mark3317/bbgl/releases/download/v1.5.10/bbgl-1.5.10-windows-x64.zip).

Original-code fixtures passed. Collision restoration was confirmed in a host gameplay retest after falling; visual Silencing Blank verification for both players remains pending. The earlier network-pool exhaustion case remains open. Optional Pig Invasion is in the full BBGL ZIP, disabled by default, and is not included in this co-op mod ZIP.
