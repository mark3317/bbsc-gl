// Generated from original CUSA03173 1.09 by quest_reward_rules.py.
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
namespace Core::Bloodborne::QuestRules {
struct NpcRewardState { std::uint32_t entity, flag; bool allowed; };
inline constexpr std::array<NpcRewardState, 217> NpcRewardStates{{
    // Native state dispatcher 12400500, entity 2400730.
    {2400730, 1181, true},
    {2400730, 1184, true},
    {2400730, 1185, true},
    {2400730, 1186, true},
    {2400730, 1188, true},
    {2400730, 1191, true},
    {2400730, 1189, false},
    {2400730, 1183, true},
    {2400730, 1189, false},
    {2400730, 1187, false},
    // Native state dispatcher 12400500, entity 2400732.
    {2400732, 1181, false},
    {2400732, 1184, false},
    {2400732, 1185, false},
    {2400732, 1186, false},
    {2400732, 1188, false},
    {2400732, 1191, false},
    {2400732, 1189, true},
    {2400732, 1183, false},
    {2400732, 1189, true},
    {2400732, 1187, false},
    // Native state dispatcher 12400520, entity 2400750.
    {2400750, 1220, false},
    {2400750, 1224, true},
    {2400750, 1225, false},
    {2400750, 1226, false},
    {2400750, 1228, false},
    {2400750, 1229, false},
    {2400750, 1235, false},
    {2400750, 1222, true},
    {2400750, 1230, true},
    {2400750, 1231, true},
    // Native state dispatcher 12400610, entity 2400755.
    {2400755, 1205, true},
    {2400755, 1206, true},
    {2400755, 1207, true},
    {2400755, 1210, true},
    // Native state dispatcher 12400590, entity 2400760.
    {2400760, 1340, true},
    {2400760, 1341, true},
    {2400760, 1342, true},
    {2400760, 1343, false},
    {2400760, 1344, false},
    {2400760, 1345, false},
    {2400760, 1346, false},
    {2400760, 1347, false},
    // Native state dispatcher 12400590, entity 2400762.
    {2400762, 1340, false},
    {2400762, 1341, false},
    {2400762, 1342, false},
    {2400762, 1343, true},
    {2400762, 1344, false},
    {2400762, 1345, false},
    {2400762, 1346, false},
    {2400762, 1347, false},
    // Native state dispatcher 12400590, entity 2400763.
    {2400763, 1340, false},
    {2400763, 1341, false},
    {2400763, 1342, false},
    {2400763, 1343, false},
    {2400763, 1344, true},
    {2400763, 1345, true},
    {2400763, 1346, true},
    {2400763, 1347, true},
    // Native state dispatcher 12400560, entity 2400765.
    {2400765, 1161, true},
    {2400765, 1164, true},
    {2400765, 1165, true},
    {2400765, 1166, true},
    {2400765, 1167, true},
    // Native state dispatcher 12400900, entity 2400770.
    {2400770, 1304, true},
    {2400770, 1305, true},
    {2400770, 1306, false},
    {2400770, 1307, false},
    {2400770, 1308, false},
    {2400770, 1312, true},
    {2400770, 1317, false},
    {2400770, 1303, true},
    // Native state dispatcher 12400900, entity 2400775.
    {2400775, 1304, false},
    {2400775, 1305, false},
    {2400775, 1306, false},
    {2400775, 1307, false},
    {2400775, 1308, true},
    {2400775, 1312, false},
    {2400775, 1317, true},
    {2400775, 1303, false},
    // Native state dispatcher 12400650, entity 2400900.
    {2400900, 1373, false},
    {2400900, 1374, false},
    {2400900, 1375, false},
    {2400900, 1372, false},
    {2400900, 1371, false},
    {2400900, 1370, false},
    {2400900, 1369, true},
    {2400900, 1368, true},
    {2400900, 1365, false},
    {2400900, 1366, false},
    {2400900, 1367, false},
    {2400900, 1362, true},
    {2400900, 1363, true},
    {2400900, 1364, true},
    {2400900, 1360, false},
    {2400900, 1361, false},
    // Native state dispatcher 12400655, entity 2400901.
    {2400901, 1370, true},
    {2400901, 1371, true},
    // Native state dispatcher 12400650, entity 2400902.
    {2400902, 1373, false},
    {2400902, 1374, false},
    {2400902, 1375, false},
    {2400902, 1372, true},
    {2400902, 1371, false},
    {2400902, 1370, false},
    {2400902, 1369, true},
    {2400902, 1368, true},
    {2400902, 1365, false},
    {2400902, 1366, false},
    {2400902, 1367, false},
    {2400902, 1362, false},
    {2400902, 1363, false},
    {2400902, 1364, false},
    {2400902, 1360, false},
    {2400902, 1361, false},
    // Native state dispatcher 12400650, entity 2400903.
    {2400903, 1373, false},
    {2400903, 1374, false},
    {2400903, 1375, false},
    {2400903, 1372, false},
    {2400903, 1371, true},
    {2400903, 1370, true},
    {2400903, 1369, true},
    {2400903, 1368, true},
    {2400903, 1365, false},
    {2400903, 1366, false},
    {2400903, 1367, false},
    {2400903, 1362, false},
    {2400903, 1363, false},
    {2400903, 1364, false},
    {2400903, 1360, false},
    {2400903, 1361, false},
    // Native state dispatcher 12410830, entity 2410770.
    {2410770, 1228, true},
    {2410770, 1229, true},
    {2410770, 1235, true},
    {2410770, 1236, true},
    // Native state dispatcher 12410830, entity 2410771.
    {2410771, 1228, true},
    {2410771, 1229, true},
    {2410771, 1235, true},
    {2410771, 1236, true},
    // Native state dispatcher 12410760, entity 2410781.
    {2410781, 1240, false},
    {2410781, 1241, false},
    {2410781, 1242, false},
    {2410781, 1243, false},
    {2410781, 1244, false},
    {2410781, 1246, true},
    {2410781, 1245, true},
    // Native state dispatcher 12410800, entity 2410900.
    {2410900, 1370, false},
    {2410900, 1371, false},
    {2410900, 1372, false},
    {2410900, 1373, false},
    {2410900, 1374, false},
    {2410900, 1375, false},
    {2410900, 1369, true},
    {2410900, 1368, true},
    {2410900, 1367, true},
    {2410900, 1366, true},
    {2410900, 1365, true},
    {2410900, 1364, false},
    {2410900, 1362, false},
    {2410900, 1363, false},
    {2410900, 1360, true},
    {2410900, 1361, true},
    // Native state dispatcher 12410809, entity 2410901.
    {2410901, 1363, true},
    {2410901, 1364, true},
    {2410901, 1365, true},
    {2410901, 1366, true},
    {2410901, 1367, true},
    {2410901, 1368, true},
    {2410901, 1369, true},
    // Native state dispatcher 12500050, entity 2500790.
    {2500790, 1348, true},
    {2500790, 1349, true},
    {2500790, 1350, true},
    {2500790, 1351, true},
    // Native state dispatcher 12700700, entity 2700755.
    {2700755, 1200, true},
    {2700755, 1201, true},
    {2700755, 1202, true},
    {2700755, 1203, true},
    {2700755, 1208, true},
    {2700755, 1209, true},
    // Native state dispatcher 12700901, entity 2700912.
    {2700912, 1800, true},
    {2700912, 1801, true},
    {2700912, 1805, true},
    {2700912, 1790, true},
    {2700912, 1791, false},
    // Native state dispatcher 12800911, entity 2800670.
    {2800670, 1300, true},
    {2800670, 1301, true},
    {2800670, 1311, true},
    {2800670, 1310, false},
    {2800670, 1315, true},
    {2800670, 1313, true},
    {2800670, 1314, true},
    // Native state dispatcher 12800911, entity 2800671.
    {2800671, 1300, false},
    {2800671, 1301, false},
    {2800671, 1311, false},
    {2800671, 1310, true},
    {2800671, 1315, false},
    {2800671, 1313, false},
    {2800671, 1314, false},
    // Native state dispatcher 13400950, entity 3400902.
    {3400902, 1720, true},
    {3400902, 1725, true},
    {3400902, 1710, true},
    {3400902, 1721, false},
    {3400902, 1726, false},
    {3400902, 1711, false},
    // Native state dispatcher 13400950, entity 3400903.
    {3400903, 1720, false},
    {3400903, 1725, false},
    {3400903, 1710, false},
    {3400903, 1721, true},
    {3400903, 1726, true},
    {3400903, 1711, true},
    // Native state dispatcher 13500950, entity 3500900.
    {3500900, 1722, true},
    {3500900, 1727, true},
    {3500900, 1712, true},
    // Native state dispatcher 13500960, entity 3500910.
    {3500910, 1760, true},
    {3500910, 1761, true},
    {3500910, 1762, false},
    {3500910, 1750, true},
    {3500910, 1751, false},
    {3500910, 1752, false},
}};
inline bool NpcRewardKnown(std::uint32_t entity) {
    auto state = std::lower_bound(NpcRewardStates.begin(), NpcRewardStates.end(), entity,
        [](const NpcRewardState& row, std::uint32_t value) { return row.entity < value; });
    return state != NpcRewardStates.end() && state->entity == entity;
}
template<class Flag> bool NpcRewardAllowed(std::uint32_t entity, Flag flag) {
    auto state = std::lower_bound(NpcRewardStates.begin(), NpcRewardStates.end(), entity,
        [](const NpcRewardState& row, std::uint32_t value) { return row.entity < value; });
    if (state == NpcRewardStates.end() || state->entity != entity) return true;
    for (; state != NpcRewardStates.end() && state->entity == entity; ++state)
        if (flag(state->flag)) return state->allowed;
    return false; // native inactive/default branch
}
struct NpcRewardReceipt { std::uint32_t flag, entity; };
inline constexpr std::array<NpcRewardReceipt, 24> NpcRewardReceipts{{
    {50000900, 2400765},
    {50001000, 2400730},
    {50001000, 2400732},
    {50001100, 2400755},
    {50001100, 2700755},
    {50001200, 2400750},
    {50001200, 2410770},
    {50001205, 2410771},
    {50001300, 2410781},
    {50001610, 2400770},
    {50001610, 2400775},
    {50001610, 2800670},
    {50001610, 2800671},
    {50001800, 2400760},
    {50001800, 2400763},
    {50001820, 2400762},
    {50001820, 2500790},
    {50001900, 2400900},
    {50001900, 2400902},
    {50001900, 2400903},
    {50001900, 2410900},
    {50002250, 3500910},
    {50003400, 2410901},
    {50003500, 2400901},
}};
inline bool NpcRewardReceiptKnown(std::uint32_t receipt) {
    return std::any_of(NpcRewardReceipts.begin(), NpcRewardReceipts.end(),
        [receipt](const NpcRewardReceipt& row) { return row.flag == receipt; });
}
template<class Flag> bool NpcRewardReceiptAllowed(std::uint32_t receipt, Flag flag) {
    bool known = false;
    for (const auto& source : NpcRewardReceipts) {
        if (source.flag != receipt) continue;
        known = true;
        if (NpcRewardAllowed(source.entity, flag)) return true;
    }
    return !known;
}
} // namespace Core::Bloodborne::QuestRules
