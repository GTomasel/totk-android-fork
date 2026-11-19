# Controller-only gameplay refresh rate

## Requirements and evidence

| Requirement | Status | Evidence |
| --- | --- | --- |
| Clone GTomasel/totk-android-fork using the personal account and gabitomasel@gmail.com | Complete | SSH authenticated as GTomasel; repository-local user.email and personal SSH key configured. |
| Read upstream reports about needing to touch the screen | Complete | Issues [40](https://github.com/AurelioB/totk-android/issues/40), [30](https://github.com/AurelioB/totk-android/issues/30), and [22](https://github.com/AurelioB/totk-android/issues/22). |
| Keep a persistent gameplay refresh request without touch input | Sky and surface verified on S23+ | Window/AHB hints default enabled/max. All 120 samples over 601s on the sky ledge/descent/respawn and all 144 samples over 721s on the surface retained 120 Hz. Some demanding views still render at 14–18 FPS. |
| Support 120 Hz and 60 Hz/user-selected refresh limits | Samsung Standard/Adaptive checked | Native/JVM fixtures cover explicit/fractional/invalid/migrating rates. With the app requesting max, Samsung Standard selected60Hz (mode3); restoring original Adaptive selected120Hz (mode1). Explicit60 override on hardware remains. |
| Preserve game FPS/timing, display migration and background lifecycle | Host checks and bounded device checks pass | Pause/resume clears/restores preference; failed queries clear stale votes. Later device testing found and fixed an independent guest-to-panel cap conversion bug. Menu pauses game/audio; visible-menu service binding preserves process importance. Lock/external-display checks remain. |
| Verify no-touch gameplay on Samsung hardware | Original reproduced; patched S23+ trials pass | S23+ SM-S916B/API36 original 10 FPS with effective 20 Hz untouched. A tap restored 120 Hz. Patched 120 Hz persisted through island and surface trials. Thermal limits and other device models remain separate checks. |

## Investigation limits

The existing host regression command is
`python3 -m unittest discover -s tests -p test_android_frame_rate_hint.py -v`.
It exercises production request policy with fake Android/JNI objects. JDK21 is now available and both fixtures run.
The connected S23+ reproduced the reported physical slowdown separately: the original app settled at about10
rendered frames/s with effective framework render rate20Hz; a single touch restored120Hz and accelerated output.
The modified app maintained120Hz without touch in the initial cave and title. These dumps describe Android's
framework mode/rate, not an external physical scanout measurement.

Ranked hypotheses: (1) ordinary gameplay makes no persistent refresh request after Samsung's touch boost expires;
(2) the activity and actual rendering child need consistent votes; (3) a separate vendor power policy throttles
controller-only gameplay even with valid votes. The first two have testable app-side seams. The third requires
device telemetry and remains a separate possible limit under heat or load.

## Implementation and controls

`android_perf.c` now defaults to `TOTK_FRAME_RATE_HINT=1` and `TOTK_FRAME_RATE_HINT_HZ=max`.
The existing display validation and native window/AHB-child requests stay in place, including fractional rates,
seamless SurfaceControl transitions and revalidation after window/display lifecycle changes.
`TotkActivity.selectFrameRateHint` also remembers the validated value and applies it as the foreground window's
`preferredRefreshRate`. A changed preference updates the window once, not on every game frame or touch event.
The production pause/resume callbacks release/restore that window preference.

These are requests through public Android APIs, not a hard lock against the operating system. The highest
advertised rate is a capability, not proof that the user currently permits it. Android applies the user's
refresh limit and battery/thermal policies. This avoids using the currently observed idle rate as the target
and avoids writing global settings, spoofing touches or impersonating another game.

Developer overrides in the game's existing `totk.env`:

```ini
# Optional: request 60 Hz explicitly instead of the default max.
TOTK_FRAME_RATE_HINT_HZ=60
```

`TOTK_FRAME_RATE_HINT_HZ=0` (or an explicitly empty value) restores content-rate hints without a window preference.
`TOTK_FRAME_RATE_HINT=0` disables the requests. Invalid/unavailable explicit rates fall back to content-rate hints.
The game's FPS selection remains separate from the display-refresh request.

## Local verification

- The native default-policy regression failed before the fix at `totk_perf_rate_request() == UINT32_MAX`.
- The final native and JVM refresh tests pass (2 tests, no skips). They cover default/max persistence, both native
  hint targets, 60/120/fractional requests, invalid rates, JNI failures, display migration, stale preference cleanup,
  production Java pause/resume callbacks and avoiding redundant window writes.
- All production Java sources compile and pass D8 with JDK 21, Android API 35 and build-tools 35.0.0:
  `python3 games/totk/android/apk/build_dex.py --out .scratch/refresh-rate/classes.dex --android-sdk ~/Android/Sdk`.
  The subsequent issue-audit work also built/linked all native libraries and a source translator, then signed,
  audited and installed the dedicated API36 development APK. See `docs/android-test-builds.md`.
- Android test discovery ran 292 cases: 274 passed, 6 optional cases skipped, and 12 initially errored because this
  fresh clone lacked `cryptography`. After installing the pinned `games/totk/requirements.txt` in `.scratch/venv`,
  both affected modules passed in full (16 APK tests and 7 launcher tests). All 12 errors are resolved.
- Four additional ADPF tests pass. `git diff --check` passes.
- Current Android discovery:307 cases,301 passed and6 optional skips. Vulkan host discovery:25 cases,22 passed
  and3 optional skips. A later callback-clock rounding refinement has its own passing producer regression.
- Build tools/Python dependencies are isolated in Git-ignored `.scratch/`; SDK packages use `~/Android/Sdk`.
  The later device tests use the user's verified game dump and a private developer signing key outside caches.

Device testing exposed a related high-refresh cap bug: guest interval2 was treated as two120Hz refreshes,
so the menu's30fps choice could render at60. The producer now converts guest60Hz intervals into physical slots;
the shared acquire/present paths use the converted count. Its red/green regression covers30/60/20fps guest
intervals,60/120Hz panels and small callback-calibration drift. Device10008 logs29.9fps and33.37ms present-fence
cadence while Android remains at120Hz.40/unlimited/interpolation keep their separate policies.

Commands use `.scratch/toolchain/jdk-21.0.13+9/bin` on PATH, and `.scratch/venv/bin/python` for the installed Python
dependencies. Logs and the compiled DEX are in `.scratch/refresh-rate/`.

## Remaining device acceptance

Actual native Android screenshots were captured and viewed at2340x1080 landscape and1080x2340 portrait: setup,
graphics menu, cave/cinematic/title, save import and sky ledge/descent. Browser inspection cannot execute this
native Android activity. Ordinary, first low-memory and demand-only profiles were killed by foreground LMKD
while streaming/descending the island. Compact descriptor pools plus bounded retention survived one601s run;
this does not prove full memory stability. Refresh votes do not resolve the independent memory shortage.
Samsung Standard60Hz and restoration to Adaptive120Hz were checked with the latest build. The original global
setting was restored; app code writes no global refresh setting.

Build 10052 recorded 60 Hz in all 83 live samples of a controller-driven
Depths and surface trial with Standard selected at launch. Switching to
Adaptive during that session left the active mode at 60 Hz. After reopening
under Adaptive, ten samples across 51 seconds of controller-only surface
play all reported 120 Hz. Build 10051 also held 120 Hz across all 169 live
samples in the aged Akkala round trip. See the
[device report](s23-device-validation.md#return-warp-validation-after-the-optimization-goal).

On a Samsung device, use the same save, scene and graphics settings for the original and patched builds:

1. With Adaptive/high refresh selected, record actual display refresh and delivered game frames for at least
   30 seconds of controller-only play, including the original 5–10 second idle window. Compare touching and
   untouched intervals. The patched build should retain the permitted high refresh without taps.
2. Select Standard/60 Hz in system settings and repeat. Verify the actual rate respects 60 Hz; do not mistake
   an app log requesting 120 Hz for evidence that Android selected it. Also exercise an explicit 60 Hz override.
3. Exercise both 30 and 60 FPS game caps, cutscenes, screen lock/unlock, Home/return, settings/return and any
   external-display migration. Inspect rendered gameplay and controls and confirm the game clock remains correct.
4. Check battery-saver/thermal-limited behavior separately. System limits take precedence; a refresh request is
   not proof that a separate Samsung GPU/CPU power policy has been resolved.

Reference: Android's [frame-rate guidance](https://developer.android.com/media/optimize/performance/frame-rate)
and [preferredRefreshRate API](https://developer.android.com/reference/android/view/WindowManager.LayoutParams#preferredRefreshRate).
