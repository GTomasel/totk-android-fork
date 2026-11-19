# Beta feedback and upstream review

Reviewed on 2026-11-18 against the published fork beta at `c686e4c`
and upstream main at `5f2c643`. The original and the fork differ in
their default display requests. The developer APK used for the
ongoing memory experiment is a separate build.
[Published beta](https://github.com/GTomasel/totk-android-low-ram/releases/tag/v1.1.0-beta.1),
[Upstream main](https://github.com/AurelioB/totk-android/commits/main/)

## New issue activity

| Report | Verification and follow-up |
| --- | --- |
| [#40, docked feedback](https://github.com/AurelioB/totk-android/issues/40#issuecomment-6964019519) | A tester reported stable gameplay at about 50 FPS in docked mode. There is no frame-time capture or matched original-app run. |
| [#40, Astra feedback](https://github.com/AurelioB/totk-android/issues/40#issuecomment-6972084166) | A tester played for three hours on a Snapdragon 8 Elite, 24 GB Astra at a 60 FPS cap and maximum graphics settings. They reported that wind vortices rendered correctly, docked mode fit their display, and they could open settings during play. They also reported heating and higher battery drain and asked for clearer performance metrics. The tester planned another run to check background activity. |
| [#60, Hero's Path](https://github.com/AurelioB/totk-android/issues/60) | The upstream report says the trail is invisible. The fork beta includes the indexed quad-strip fix. Earlier S23+ runs displayed a newly recorded trail at two zoom levels. Build 10062 again displayed a green trail after returning to Akkala and running through new terrain. The reporter's device, save and settings are unspecified. [Device evidence](s23-device-validation.md#reclaiming-old-dma-pool-backing) |
| [#58, TKMM import](https://github.com/AurelioB/totk-android/pull/58), [#59, LSFG import](https://github.com/AurelioB/totk-android/pull/59) | These draft PRs move the same commits from #45 and #46 to a different contributor fork. They are separate from the changes on upstream main. |
| [#56, rendering artifacts](https://github.com/AurelioB/totk-android/issues/56) | Upstream closed the issue after its original reporter confirmed that switching driver fixed their artifacts. Their opening message also mentioned an apparent 30 FPS limit. The driver follow-up confirms the visual symptom only. |
| [#20, wind effect](https://github.com/AurelioB/totk-android/issues/20) | Upstream still lists it as open. The beta player's report adds one device-level confirmation of the fork's wind result. |
| [#55, low-memory exit](https://github.com/AurelioB/totk-android/issues/55) | The S23+ still reproduces foreground LMKD. The long session on a 24 GB tablet adds useful compatibility evidence for that device. [Current S23+ memory results](s23-device-validation.md#reclaiming-old-dma-pool-backing) |

## Temperature, power and the overlay

The published beta's default Android refresh hint requests the
highest rate the current display advertises and adds a matching
foreground window preference. Android still applies the system's
display limits. A 60 FPS gameplay cap and a 60 Hz screen request
control different things. If the report's device used a higher
panel rate in the beta, that is a candidate contributor to the
energy difference. The GitHub report does not include the panel
rate, measured power or a matched run of the original.
[Fork refresh policy](samsung-refresh-rate.md),
[Android frame-rate API](https://developer.android.com/media/optimize/performance/frame-rate)

The current `full` overlay already distinguishes game and
presented FPS when frame generation is active, and shows resolution,
upscaling and synchronous compilation. The optional power and
system rows are available through `totk.env` and are off by default.
They can show battery temperature, thermal status, available RAM,
process RSS and readable power sensors. Sensor availability varies.
Battery discharge and USB input have different meanings, so the
USB-connected S23+ stability run does not measure tablet battery
drain. A matched Astra comparison needs the same save, driver,
scene resolution, render cap, brightness, cooling and charge state,
with observed panel Hz and a fixed 60 Hz arm.
[Overlay field definitions](../games/totk/android/APP.md),
[Android battery counters](https://developer.android.com/reference/android/os/BatteryManager)

The test used the following startup settings:

```ini
TOTK_FRAME_RATE_HINT_HZ=60
TOTK_OVERLAY=full
TOTK_OVERLAY_SYS=1
TOTK_OVERLAY_POWER=1
```

With these settings, build 10063 held 60 Hz across all 26 S23+
movement samples at a 30 FPS render cap. The system rows showed
thermal status, headroom, CPU frequency ratio, RAM and RSS.
The power row was empty even though the phone reported a battery
temperature through Android. This isolated a coverage gap in the
overlay's sysfs-only battery sampling.

The local 10066 build falls back to the Android battery snapshot
when sysfs is unreadable. The fallback is opt-in with the power row,
runs off the render thread, and makes at most one Android query
every five seconds while the overlay is visible. The S23+ displayed
`BAT 31.2C` at startup, matching the concurrent Android battery
service reading. The USB wattage counter was still unavailable.
The overlay presenter passed three 313-check runs, plus 258
power and CPU fixture checks. The Astra report still needs measurements
on that tablet.
[Android battery broadcast](https://developer.android.com/reference/android/content/Intent#ACTION_BATTERY_CHANGED)

## Changes reviewed on upstream main

| Upstream changes | Applicability to the fork |
| --- | --- |
| [`13b2174`](https://github.com/AurelioB/totk-android/commit/13b21744a2) | Seven new 1.4.3 shader variants. The local shader manifest includes these rows. Existing installed seed packs can remain in use. Rebuilding preparation is needed to gain the new packed coverage. |
| [`763ee8e`](https://github.com/AurelioB/totk-android/commit/763ee8e06a), [`c8cbeb3`](https://github.com/AurelioB/totk-android/commit/c8cbeb3017) | Improve the correctness of experimental private GPU write-back across pool retirement, alias chains and virtual mapping replacements. Upstream retains another CPU mapping of the same DMA buffer with `TOTK_WB_ALIAS=1`. The adaptation must preserve local view retirement, old shmem backing protection, exact texture layout and the optimized block swizzle for the ordinary path. |
| [`7fefdc2`](https://github.com/AurelioB/totk-android/commit/7fefdc2db8), [`becf0cd`](https://github.com/AurelioB/totk-android/commit/becf0cdac7) | Include the counters and atomic pause-report latch with the private write-back feature. The pause fix depends on the new diagnostics. |
| [`5f2c643`](https://github.com/AurelioB/totk-android/commit/5f2c6438e2) | Documents fewer mapping boundaries on an AYN Thor. The tested pooled frame-time tails were comparable and the option remains off by default. Treat this as correctness and mapping-pressure work. There is no established FPS, memory-kill or Astra power fix. |

The local integration passed the Linux Vulkan recorder run and
targeted suites for alias landing and retirement, pool finalization,
texture spans and image reclaim. The signed APK loaded Akkala on
the S23+ with aliasing explicitly enabled and logged a nonempty alias
report on pause. The seven shader variants were checked in the APK
manifest. Their individual in-game scenes remain unverified.
[Device qualification](s23-device-validation.md#upstream-write-back-and-explicit-60-hz)

The follow-up build 10066 kept aliasing enabled and disabled
experimental backing discard. It completed the Akkala–Iu'iqoi–
Akkala route with three running segments after the return and
closed normally. It still showed hitches and the earlier control
also completed the route, so these trials do not identify an
alias-related gain. The full host suite passed 680 tests with 92
skips. The Java and native refresh fixtures also passed separately
with the JDK and Clang available.
[Full return route](s23-device-validation.md#full-return-route-with-upstream-write-back-enabled)
