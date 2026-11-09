# BBSC-GL 1.5.0

This package contains the same DLL, helper launcher and Party runtime as [BBGL 1.5.0](https://github.com/mark3317/bbgl/releases/tag/v1.5.0).

- After a boss wipe, the group waits for the last player’s death sequence before reloading. Normal loading clears Amelia’s temporary attempt state. Active boss fog follows the game’s role and collision checks, and the spectator view uses the game’s resource selection.
- Guests can join an open Chalice Dungeon room after the boss is defeated. Fallback respawn lamps stay in the current layer.
- Guests retain their own lamps for returning home. If a shared checkpoint is on another map, the native selector can choose a lit local lamp.
- The Silencing Blank can list eligible guests on other maps. Guests keep the correct multiplayer role through the end of a summon, and a confirmed departure can fall back to the native leave handler.
- Personal Insight receipts for Amelia and Rom and local flags for elevators, gates and other map conditions are protected from incoming world state.
- Party carries confirmed Beckoning Bell uses through the existing presence exchange. Local test profiles retain their Party identities across restarts and can recover eligible stale peer keys.

For a first install, use the full [BBGL 1.5.0 Windows ZIP](https://github.com/mark3317/bbgl/releases/tag/v1.5.0). To install the standalone mod ZIP over BBGL 1.5.0, close the game and launcher and extract it into the folder containing **Bloodborne.exe**. Keep your profile and saves. All players should use the matching BBGL and BBSC-GL versions on the same LAN or VPN.

Development builds were tested in game for the Amelia team wipe and spectator view, returning to personal lamps, leaving with the Silencing Blank and summoning into a cleared Chalice Dungeon. The final ZIP needs a live co-op run. Rom’s cross-map respawn case and the visual display of repeated bell notices still need confirmation.

## Русский

В архиве те же DLL, вспомогательный запуск и Party, что в [BBGL 1.5.0](https://github.com/mark3317/bbgl/releases/tag/v1.5.0).

- После общей гибели у босса группа ждёт завершения штатного шага смерти последнего игрока. Штатная загрузка очищает временные флаги попытки Амелии. У активного тумана действуют штатные проверки роли и коллизия. Режим наблюдения использует штатный выбор ресурсов окружения.
- В открытую комнату подземелья чаш можно призвать гостя после победы над боссом. Резервная лампа возрождения выбирается в текущем слое.
- Гость сохраняет личную лампу для возвращения домой. Если общая точка относится к другой карте, штатный выбор может найти местную зажжённую лампу.
- Бланк молчания может показать доступных гостей на других картах. Роль гостя сохраняется при завершении призыва. Для подтверждённого выхода предусмотрен резерв через штатный обработчик.
- Личные отметки озарения Амелии и Ром, а также местные флаги лифтов, ворот и других условий карты защищены от входящего снимка мира.
- Party передаёт подтверждённые звонки Зовущего колокола через существующий обмен данными о присутствии. Локальные тестовые профили сохраняют свои ключи Party при перезапуске и могут обновить устаревшие ключи свободных участников.

Для первой установки скачайте полный [Windows ZIP BBGL 1.5.0](https://github.com/mark3317/bbgl/releases/tag/v1.5.0). Чтобы установить отдельный ZIP мода поверх BBGL 1.5.0, закройте игру и лаунчер и распакуйте архив в папку с **Bloodborne.exe**. Сохраните профиль и сейвы. Всем игрокам нужны совпадающие версии BBGL и BBSC-GL и общая локальная сеть или VPN.

На промежуточных сборках в игре проверены общая гибель на Амелии и наблюдение, возвращение к личным лампам, выход через Бланк и призыв в зачищенную чашу. Игровой прогон итогового ZIP открыт. Ещё предстоит подтвердить возрождение после общей гибели на Ром при точке с другой карты и показ уведомлений о повторном звоне.
