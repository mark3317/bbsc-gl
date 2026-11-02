# Combined latest:60FPS comparison — 02.11.2026

## Provenance / thermal exclusion

Both machines collected,3 files each, warnings=0 and ChangedDuringCopy=false. Previous capped run perf-idle60-20261102 retained. New DLL built05:09:41, matches combined62b3200 (guard snapshots + neighboring quit/bell/presentation changes). Both game logs online. No settings/saves/code/build/install changes during collection/analysis.

User asks to ignore throttling. New laptop telemetry shows a sharp break near05:22:17 (37,4FPS) /05:22:22 (12,6FPS), then sustained12–13FPS. Conservatively exclude all windows ending after05:22:10 and all later profiling from conclusions. Baseline excludes04:55:00 onward as before. These are visible timing breaks, not a temperature/frequency measurement: sensor data was not collected. Primary comparison is far earlier, in the first paired session05:13–05:16.

Roles match the immediately previous run: PC guest, laptop host. Baseline paired selection04:50:45–04:52:00 (~70s); new early pair05:13:45–05:14:55 (~65s), after both characters joined05:13:35.951/37.852. New larger selection05:13:45–05:16:30 ends before session shutdown05:16:37/38. All selections use complete5-second windows. Different route/camera/fights and multiple combined changes limit causal interpretation. New pre-pair gameplay is too short/overlaps startup to replace the main paired comparison with a robust alone baseline.

## Same-role early pair comparison

| Metric | PC guest: previous→new | Laptop host: previous→new |
|---|---|---|
| Mean FPS |59.36→58.45|52.45→51.03|
| FPS window range |58.98–60.00→57.02–60.01|41.26–59.60→44.64–59.80|
| Frames>50ms/min |5.99→7.37|16.25→30.39|
| Raw >50ms count / duration |7/70.13s→8/65.13s|19/70.17s→33/65.15s|
| Frames>100ms |0→0|4→2|
| Worst frame |99.94→99.82ms|149.99→117.54ms|
| Window p99 range |18–34→18–51ms|19–67→18–68ms|

Thus fewer extreme laptop outliers in this short sample, but more50–100ms frames. Laptop >50ms rate +87%, PC +23%; mean FPS −2.7%/−1.5%. These are observations, not proof of a source regression due to differing scenes. There is no evidence of an overall stutter improvement from this combined update.

## Entire first paired session, still before thermal tail

New extended sample160s: PC56.76FPS /26.94 >50ms frames/min /worst184.28ms; laptop48.99FPS /23.19 >50ms/min /worst117.54ms. PC has a pronounced burst around05:14:58–05:15:23 with48–54FPS and many50–84ms frames; it was retained, not discarded as throttle. Laptop is then around47–48FPS, long before the later sharp thermal break. No full FPS average including later low thermal frames is used. Detailed counts in segment-metrics.json.

## Table checks / module profiling

Pre-tail maxima (whole pre-tail run, not equal-duration stress tests):
- Laptop scaling table owners15.337→20.866ms; TickBbscScaling15.340→20.869ms.
- PC owners13.236→16.474ms; parent13.237→16.476ms.
- No >50ms scaling call in the published pre-tail records. The prior hundreds-ms scaling workload has not returned; the residual long table check remains.

For indicative sustained-profile costs, use10–11-second reports with>=200 game ticks, excluding long pauses between profiler calls: baseline04:50:40–04:54:55 (19 reports/device), new05:13:40–05:16:30 (14/device). For a slot outside top10, no zero value was invented; means use reports where the slot is present. Different activity and sample coverage limit precision:

| Cost | PC previous→new | Laptop previous→new |
|---|---|---|
| Table owners |110.05→147.74us/game frame (18→14 reports)|197.22→229.37us/game frame (17→13 reports)|
| TickBbscScaling |111.81→149.42us/frame|201.12→223.48us/frame|
| NPC event lookup |300.35→431.61us/frame|576.20→323.57us/frame|
| NPC pass parent |548.04→782.39us/frame|1210.08→1086.79us/frame|
| Bell final result |212.74→275.34us/frame|855.62→1177.64us/frame|

Owner overhead did not measurably fall in these runtime profiles despite fewer duplicate guard calls in fixtures. Some laptop NPC work is lower, but it does not establish whole-game improvement. Nested costs overlap parents and are not added together. A59.5-second baseline profiler gap and27–28-second new gaps show that perf game-frame normalization differs across menu/inactive periods; these long reports are excluded from sustained-profile means, not from actual frame-stall counts.

Active-table preparation remains fast: PC2ms /laptop5ms, with1 live copy and5359 enemy/375 boss rows. Multi-minute table scanning has not returned.

## Remaining holds / next investigation

Before thermal cutoff laptop IsValidSos.Update max43.909ms, table owner max20.866ms. PC contains synchronous progress backup86.125ms and Warp.RespawnPoint.Resolve97.276ms elsewhere in the pre-tail run. A PC4367ms frame at05:17:58 is in the quit/transition interval, outside the gameplay comparisons; it must not be advertised as ordinary gameplay or considered fixed. Neither counts nor wall-time scopes identify a specific mutex owner or separate CPU preemption, memory protection waits, disk and GPU waiting.

Conclusion: previous large-scan fix is retained, but this combined update has not reduced remaining ordinary stutters or long owner checks in the measured run. Do not claim a performance gain. Next evidence needed: sub-timing/counts within guard/query operations tied to individual slow frames, with cap/roles/route held constant. No new build or installation is implied by this log review.
