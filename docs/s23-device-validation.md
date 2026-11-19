# S23+ validation — local development work

Device: SM-S916B, Snapdragon8Gen2/Adreno740,8GB, Android16/API36. Native screenshots were captured and viewed
at2340x1080 landscape and1080x2340 portrait. This is native Android validation; no browser can execute this app.
The user's decrypted game files passed every1.4.3 integrity pin. No ROM/key download or integrity bypass was used.

## Refresh and timing

The upstream1.0.1 app in the initial cave settled near10 rendered FPS with framework effective render rate20Hz;
one tap restored120Hz. The patched app retained120Hz without taps in cave/title and a601s island/descent trial
(all120 framework samples). These are Android framework observations, not external scanout measurements.
Samsung Standard selected60Hz despite the max app vote; original Adaptive mode was restored and selected120Hz.
No app code writes global display settings. Thermal/battery policy can still limit actual hardware performance.

The selected30fps cap initially became about60 on a120Hz panel. Converting guest60Hz intervals into physical
display slots fixes that separate error: the device logs29.9fps/33.37ms while the framework remains120Hz.
This does not turn a30fps game into120fps.40/unlimited/frame-generation have separate policies.

## Memory and actual scene coverage

| Trial | Result and limit |
| --- | --- |
| Normal retention, Sky Island load | Foreground LOW_MEMORY at about193s app elapsed; no app SIGSEGV/device-lost evidence. |
| Initial lower-retention profile | Staging374→104MiB; still foreground LOW_MEMORY during descent. Workloads differ, so this is a retention counter comparison, not total-RAM savings. |
| Demand shader/prewarm only added | Still foreground LOW_MEMORY during descent; insufficient. |
| Compact descriptor pools plus bounded retention/demand defaults | One601s sky-ledged/descent/respawn session survived. Some falling views14–18fps; ledge28–30fps. |
| Latest profile, unedited advanced public progress on Hyrule surface | Ground scene loaded near Link's house/Arkadia in Akkala. Walked, climbed, panned camera and opened ability wheel/map/Hero's Path. Extended capture result recorded below after completion. |

Enable **Graphics → Performance → Low memory mode** and relaunch the game. The developer override is
`TOTK_LOW_MEMORY=1` in the game's `totk.env`. The mode bounds retained
staging/recorder slabs, frees completely empty fence-retired image blocks, quarters descriptor-pool capacities with
a full-size wide-layout fallback, disables eager PSO prewarming and bounds shader warming to16MiB. Explicit
individual developer overrides win. Guest heap and image quality are not reduced by the profile. First-use shader
hitches remain possible; active allocations can exceed retention targets. Overlapping RSS/PSS/GPU/shared counters
must not be added as if disjoint. These trials used Light/30fps/960x540, frame generation off and shadow override256.

The original compact profile survived the sky and initial ground tests but was subsequently killed on a longer
Akkala route. The revised profile adds smaller Vulkan image blocks and a lower staging retention target.
See the routes below before drawing conclusions about memory or FPS.

An attempt that changed only a sky save's position produced a white transition; it is rejected as ground proof.
The successful surface fixture instead uses unedited public advanced progress from the
[save-editor author's example](https://lohtam.github.io/totk-modified/zelda-totk/), wrapped for normal import with
options/caption from the public[nxnative#70 reproduction](https://github.com/seedds/nxnative/issues/70).
Caption previews are not authoritative location data. The normal import backs up the test app's save set first.
No saves, game data or console keys are included in the APK or public artifact directory.

## Other exercised behavior

API36 predictive Back opens the existing app menu and pauses game/audio. A visible-menu service binding fixes
Android demoting the paused game to cached importance400: observed binding flags0xc1 and unchanged game PID.
Importing saves while the game is alive is blocked; Close flushes cache and exits with EXIT_SELF/status0.
Repeated target36 signed development updates through10011 preserved saves and required no installer/fingerprint
interaction. Signing state remains private and persistent outside disposable build caches.

The ability wheel displayed its blurred world backdrop. Hero's Path discarded primitive8 (QUAD_STRIP).
The initial non-indexed candidate was insufficient: hardware revealed indexed strips. A CPU conversion attempt
failed a pending-writer guard fixture because ordinary rendering does not retain the complete writer ledger.
That attempt was replaced by GPU conversion, preserving queue order without a CPU readback wait.
The253-check live Vulkan fixture covers8/16/32-bit indices, restart markers, incomplete groups, first/base offsets,
instances, CPU inline updates and actual GPU-produced indices. It passes with direct, recorder and one-primary/lag
settings after the earlier indexed regression failed36 comparisons. Final actual trail acceptance follows separately.
Generated-frame indexed-quad UI replay is conservatively refused until its extended ownership path is qualified;
ordinary game rendering still executes. Malformed/oversized ranges and unsupported indirect base-instance use fail closed.
Build10013 actually displays the test-session green trail on S23+, inspected at the original map zoom and enlarged
in-game zoom. The public progress fixture initially had no matching historical footprint; acceptance covers the
walking history generated in these tests. Original missing-trail and corrected screenshots are retained.
The final10014 build also loaded the surface and displayed the updated trail; its180s smoke retained the main
process in all36 samples.10013 survived a separate360s/72-sample trial including a successful nearby shrine warp.
These bounded checks do not reproduce or resolve every Depths/shrine transition reported in#49.

Host validation for the current changes includes 307 Android cases (301 passed, 6 optional skips), 25 Vulkan
Python cases (22 passed, 3 optional skips), 356 native presentation checks, 246 descriptor checks and 253 quad
pixel/queue checks per tested mode.
The Android build compiles/links native code and Java/DEX, bundles licenses, verifies signing and audits APK contents.
See the[full issue checklist](upstream-issue-audit.md) for all49 individual reports and their remaining requirements.

## Extended ground capture

Build10011 completed720.839s with the same main PID15060 in all144 samples and no main-process exit.
This session includes startup/load, roughly10min on the ground, walking/climbing/camera pans and in-game menus;
it is not720s of continuous movement. Logged300-frame windows in the inspected ground segment ranged25.8–30.0fps.
The ability wheel showed the world backdrop; Hero's Path still lacked its trail before the new strip patch.
The framework reported120.00001Hz in all144 samples, with minimum system MemAvailable635.75MiB (not a process
memory budget). The process was closed deliberately after capture ended.

Viewed native settings:1080p selection,4:3 camera selector, rumble help/gain row and Mods import choices.
Returned resolution/aspect to960x540/16:9 before the next game launch. This confirms menu rendering, not1080p
performance, nondefault camera fidelity, tactile Odin rumble or actual third-party mod behavior.

## Sustained streaming in Akkala

The first 10014 route used 19 supervised sprint/recovery segments across grass, slopes and water, ending at
4318, 2202, 0000 near the Spiral Peninsula. It lasted 314 seconds including screenshot gaps. The separate
433-second capture included load and menu time. All 87 samples had the same game PID and 120 Hz render rate.
The game was paused intentionally to change Codex models.

After resuming, the same process warped to the Sinat'aq shrine at 3842, 2300, 0048. It ran and jogged
across fields onto the road toward Lake Octo, reaching at least 4048, 2584, 0075 in the last gameplay image.
Ten 15-second sprint and 7-second recovery commands were issued with visual steering and breaks between
segments. The game left the foreground during the final segment. Android recorded PID 27894 as
`LOW_MEMORY` at foreground importance 100. Android's event buffer recorded an LMKD kill for the same PID.
The 477-second capture had 95 live samples, all at 120 Hz, followed by the exit. The native log had reached
about 1,255 seconds since game startup, including the previous route and pause.

The final complete 300-frame window averaged 7.8 FPS with a 687 ms maximum frame and zero new pipelines.
Near the exit, individual frames reached 892 ms. System memory pressure rose substantially: the ten-second
full PSI average increased from 2.4% at capture start to about 26% near the end. System KGSL shared usage
remained near 1.2 GiB. The final complete image report showed 511 MiB used inside 640 MiB of Vulkan blocks.
The measurements show memory pressure and slack in the image allocator. They do not establish a leak or show
that every slow frame has the same cause. The last live sample reported 12 GiB of swap capacity and about
7.9 GiB still free. RAM Plus was not adjusted. The upstream reporter also saw the closure with RAM Plus off
and at 8 GB.

Build 10017 changes the low-memory profile to 32 MiB image blocks and an 8 MiB staging retention target.
The retirement rules and dedicated threshold are unchanged. Vulkan accounting fixtures checked both block sizes,
including allocation failures and repeated reuse of metadata. This build was installed over the earlier signed
app and loaded the Sinat'aq autosave. The menu's low-memory setting enabled the revised profile without a
game-folder override. Stretch to fill was inspected in the Screen tab, title, load screen
and actual surface gameplay on the 2340 × 1080 display. The camera view at the shrine matched 16:9 and the
picture filled the width, with the intended horizontal stretching.

The revised profile completed ten sprint/recovery segments plus climbing. It started at Sinat'aq,
warped to Ioq'ui, entered and exited the shrine, then passed the East Akkala Stable and reached
4293, 2594, 0093 on the surface. The retained transient chunks in the late route were 64 MiB, compared
with 120 MiB late in the first compact-profile run. Those figures describe one allocator category in
two different routes. The revised run still reached about 1.21 GiB of system KGSL usage.

Teleporting to Iu'iqoi lightroot after the long run ended in another foreground `LOW_MEMORY` exit.
The capture lasted 831.407 seconds. All 166 live samples had PID 6226 at 120 Hz. The 167th sample
observed the exit. The time and PID match the LMKD event. The revised mode reduces retained buffers
but still exceeds the device's practical memory budget in this sequence.

During that transition, used image-block bytes rose from 371.176 to 572.363 MiB between samples. Allocated
blocks grew from 640 to 704 MiB, while dedicated image allocations remained at 79 MiB. The final log sample
had 479.535 MiB in use across those 704 MiB of blocks. The rest was free spans inside Vulkan allocations.
With 32 MiB blocks, reclaimable bytes depend on whether all the images in a block can be retired safely.
The logs do not classify those contributors by storage ownership, age or fence, so they cannot estimate how
many blocks could actually have been freed before the exit.

Hitches have multiple signatures. In build 10014's 12.5 FPS window at frame 26700, Vulkan reported
34.0 ms of GPU work per frame. Command walking took 49.947 ms of wall time and 20.640 ms on CPU.
These scopes overlap. A later 7.8 FPS window had zero new pipelines. In build 10017 the surface
route had a 13.5 FPS window with a 900 ms maximum frame, including two synchronous pipeline compiles
that took 776.5 ms in aggregate. Loading the lightroot after the long run triggered a separate
1.17-second peak alongside many first-use pipelines. The refresh rate stayed at 120 Hz in the sampled
intervals. Thermal status 2 was observed and its independent effect was not isolated.

A fresh 10017 process loaded an Ioq'ui autosave and reached the same Iu'iqoi lightroot with the low-memory
profile still enabled. The startup log reported a matching 45,578 KiB graphics pipeline cache. Link sprinted
22 seconds across the Depths (from 4346, 2877, −0508 to 4338, 2763, −0587), then warped back to Ioq'ui
and resumed surface gameplay. The main PID 21641 survived all 48 samples across 240.629 seconds, at 120 Hz
throughout. Android killed the separate cached `:setup` process during the trial. The game exited with
`EXIT_SELF`/status 0 after the normal Close command. Android rebound the idle menu control service in a new
PID afterward, without starting gameplay. The fresh process, different preceding route and
warm pipeline cache make this a route comparison rather than an isolated memory-policy A/B.

Testing used manual brightness 26/255. The phone was returned to Adaptive brightness, with the saved
brightness value reapplied before Android resumed controlling the level. USB stay-awake stayed at its
original value and Samsung Motion smoothness stayed on Adaptive after the 60 Hz check. The dev app's
aspect setting was returned to 16:9.

## Optimization trials after the source comparison

All arms use the bundled Turnip driver, game 1.4.3, handheld Light at 960 × 540, 30 FPS cap, 16:9,
frame generation off and the low-memory profile. The route arms start from a copy of the 17:26 Ioq'ui
autosave and the same 47,951 KiB opaque driver cache. Benchmark copies live in private app storage.
Each route uses seven timed sprint/recovery segments across Akkala and the Iu'iqoi fast travel. Steering,
weather, combat, CPU clock, title-screen time and background pressure are not deterministic.

- **10017 reference.** Seven surface segments ended at 4214, 2024, 0040. The process reached Iu'iqoi and
  sprinted in the Depths. It survived 660.148 seconds across 132 samples and was then closed normally.
  The same run had 16 synchronous capture builds totaling 1,719 ms, with an observed maximum of 269 ms.
- **10018 denser-block placement, 32 MiB.** An allocator fixture reproduced a case where first-fit
  held two blocks and denser placement freed one 32 MiB block when its remaining images retired.
  On the S23+, the surface route ended within 35 map units of the reference and reached Iu'iqoi.
  The committed image-block peak grew after the transition. Android ended PID 753 with foreground
  `LOW_MEMORY`/importance 100 during the return to the surface, 611.699 seconds into capture.
  The final log window held 430.699 MiB of image bytes inside 768 MiB of blocks, plus 79 MiB of
  dedicated images. The experiment also logged seven sparsely used blocks and zero empty ones.
  At that sample there were no unreferenced shared images reported for early eviction.
  Densest-first placement remains a reversible experiment rather than a general memory fix.
- **Rootless scheduling trace.** A 22-second Perfetto trace on the 10018 Depths sprint recorded
  9.747 seconds on CPU, 2.241 seconds runnable, 9.850 seconds sleeping and 0.049 seconds in
  uninterruptible state for the main command-walker TID. Each recorder worker was runnable for
  about 4.5 seconds, compared with about 3.6 seconds running. CPU availability and wake timing
  are therefore worth checking. The sleep spans alone do not identify a lock, fence or causality.
- **Selective graphics warm-up.** The reference's eight most expensive successful capture keys
  were selected by full key and their observed costs (117–269 ms). The 6,400-byte portable list
  contains shader identifiers and render state. Build 10020 loaded all eight exact variants and
  prepared them on one worker at startup, with no missing or failed keys. Creation took 1,087 ms
  in aggregate and completed 1,801 ms after prewarm started. Turnip reported application-cache
  hits even for the slow builds. The route took a different line past East Akkala Stable, with
  a fence detour, and reached Iu'iqoi after an 836.556-second capture with the same PID in all
  168 samples. No selected key was requested in this replay. The list remains an opt-in experiment.
  A wake-batching test was also attempted, but only the reference marker was acknowledged by the
  shared storage control file. That test provides no comparison or basis for changing scheduling defaults.
- **10021 smaller blocks and submission deadlines.** The low-memory mode selects 16 MiB with
  first-fit placement. GPU-written images keep the existing 600-submission reuse window, and
  reclamation still waits for the retirement fence. The full shared-cache traversal runs at the
  next possible expiry. The allocator tests cover exact 16 MiB allocation and separate larger
  allocations. A live Vulkan fixture reuses the original image just before expiry and checks
  the new deadline in direct and recorder modes, with eight passing checks in each.
  The route passed East Akkala Stable and reached Iu'iqoi. Link moved from 4346, 2877, −0508
  to 4337, 2760, −0586 during a 22-second sprint and recovery. Settled blocks reserved 640 MiB
  in the Depths, compared with 704 MiB in the denser-placement trial. The game requested the
  return to Ioq'ui. Android killed the main process with `LOW_MEMORY` at foreground
  importance 100 during the transition, after 775.896 seconds of capture. All 155 live
  samples had the same process and a framework render rate of 120 Hz.
  In the last complete window, image use jumped from 494.535 to 755.621 MiB and block
  commitments from 640 to 784 MiB. There were 51.617 MiB of retired images and
  1.199 MiB of idle shared images; these are lifetime categories within the image accounting.
  This peak does not support shipping 16 MiB blocks by default. First-fit 32 MiB remains
  the low-memory default, and 16 MiB remains selectable in `totk.env`.
  By that window the game had skipped 20,843 of 21,037 shared-image traversals (99.1%).
  The traversal reduction is measured; its effect on FPS has not been isolated.

The benchmark environment was restored after the test. The phone returned to Adaptive brightness
and retained the existing USB stay-awake setting.

## Follow-up on the return-warp peak

Between the last two complete 10021 reports, live texture objects went from 1,451 to 2,738.
The reported total for guest pools rose from 1,134 to 1,199 MiB. Texture uploads increased
from 19.2 to 225.3 MiB per 300-frame window, and write-back staging went from zero to
21.7 MiB. These measurements cover different accounting categories and should not be added
to Android's RSS or GPU figures. The later window contained a 423 ms frame. Its 33 pipeline
creations took 6.5 ms in aggregate. The next comparison should isolate the texture and pool
overlap during the transition, including the 51.6 MiB of images already awaiting retirement.
The image usage increase was 261.1 MiB. Growth in the shared active, shared idle and retired
categories accounts for about 76.7 MiB. About 184.4 MiB of the increase therefore remains
outside those categories in the adjacent snapshots. Dedicated allocations held at 79 MiB.
This directs the next measurement to active nonshared textures and their auxiliary images.

The 10021 trial emitted 5,866 per-tile write-back messages. The post-beta candidate makes
those messages opt-in via `TOTK_VK_WB_TILE_TRACE=1`, while retaining aggregate counters and
the write-back rules. The live Vulkan write-back fixture passed all 131 checks in each
setting. The default emitted no per-tile messages and the opt-in emitted 106.

## Public beta smoke test

The published APK `1.1.0-beta.1` from `c686e4c` installed as `com.gtomasel.totk`.
On the S23+ it selected the existing prepared data, imported a public advanced save,
finished its initial data verification and loaded the Rasitaqi'u area of Akkala.
Three sprint and recovery segments moved across grass and a path to the rocky slope at
4374, 1527, 0169. Surface windows at frames 4800–6600 measured 26.6–30.0 FPS.
Adaptive held 120 Hz in all 32 samples from the moving phase through the final map and menu.
The game PID survived the 358.227-second capture, then closed normally with `EXIT_SELF`/status 0.
The separate cached setup process was reclaimed earlier. This route did not repeat the aged
Depths round trip.

The owner took the phone after this test and asked to continue without ADB.
Device testing resumed when the owner brought the phone back.

## Return-warp validation after the optimization goal

Build 10051 installed over 10022 as `com.gtomasel.totk.dev` through ADB.
The 8 GB S23+ used its bundled Turnip driver, the matching initial pipeline
cache, the archived 17:26 Ioq'ui autosave in a private test profile, and the
same Light 960 × 540 / 30 FPS gameplay configuration. Firmware reported
120 Hz in Adaptive mode. The phone ran at manual brightness 26/255 while
plugged in, and all gameplay input used the controller path.

The experimental arm used the current 32 MiB first-fit image block default.
The 10021 reference used 16 MiB first-fit blocks. Build 10051 also enabled
the following startup options alongside Low memory mode.

```ini
TOTK_VK_STAGING_RETAIN_MB=4
TOTK_VK_STAGING_EARLY_TRIM=1
TOTK_VK_DESC_TRIM_IDLE=1
TOTK_VK_PARTIAL_TEX_UPLOAD=1
TOTK_VK_IMAGE_RECLAIM_BEFORE_GROW=1
TOTK_VK_REC_DISCARD_FREE=1
```

The same seven surface sprint/recovery segments crossed Akkala. Variable
steering and collisions took the candidate to the coast at 4588, 2449, −0001,
compared with 4130, 2015, 0064 in 10021. For 27 complete surface windows
starting after the first input segment began, the results were as follows.

| S23+ surface measurements | 10021 | 10051 |
| --- | ---: | ---: |
| Median of 300-frame FPS windows | 27.3 | 29.9 |
| Lowest 300-frame FPS window | 21.6 | 20.7 |
| Frames longer than 50 ms | 636 | 491 |
| Longest frame | 431.9 ms | 327.4 ms |
| Median retained descriptor pools | 40 | 24 |
| Settled Vulkan slot staging | 64 MiB | 32 MiB |

These are comparable route measurements across two builds and several
memory options. The path and background load varied. Frame 6300 in
10051 still reported a 177.2 ms frame with zero new pipelines. The
renderer recorded 198 descriptor pools destroyed, about 94.8 MiB of
upload-only staging returned over the run so far, and over 13.9 MiB
of upload staging avoided through partial updates. Those counters are
cumulative events, while the table's staging and pool figures are
snapshot capacity.

Iu'iqoi loaded in the same process. The 22-second controller sprint
and recovery reached 4338, 2759, −0586 from 4346, 2877, −0508. The
10021 Depths endpoint was 4337, 2760, −0586.

The return warp was requested after 266 seconds in the Depths portion,
compared with 261 seconds in the reference. Build 10051 loaded Ioq'ui
and rendered playable surface gameplay in the original PID. Android
subsequently killed it at foreground importance 100 with `LOW_MEMORY`,
about 72 seconds after confirming the return and 846.8 seconds after
capture started. All 169 live samples reported 120 Hz. The earlier
10021 arm had died while loading the return, after 775.9 seconds of
capture. Peak sampled process PSS was 3.42 GiB in 10051 and 3.68 GiB
in 10021.

At the sampled return high, image allocations held 768 MiB in blocks
plus 79 MiB dedicated in 10051. The 10021 snapshot held 784 MiB in
blocks plus 79 MiB dedicated. The 10051 block commitment stayed
at 768 MiB through the last report, even after occupied spans fell
from 722.5 to 456.5 MiB. It reported 311.5 MiB of free spans across
those blocks, four sparsely occupied blocks and no empty ones.
Staging settled at 32 MiB. The last two playable windows fell to 17.0
and 9.5 FPS. The former included a 568.6 ms frame with zero new
pipelines, and the latter measured 45.8 ms per frame off CPU in the
command walker. The #55 closure remains reproducible after the warp.
[Android low-memory killer](https://source.android.com/docs/core/perf/lmkd)

Build 10052 installed as an in-place update. Its separate test started
from the archived 17:25 Iu'iqoi save, with the same memory options,
ownership and allocation-peak logging, and the optional single-primary
recorder enabled. Link ran the same 22-second Depths segment from a
fresh process, went to Ioq'ui and completed two more surface sprint
segments. The replay reached 4336, 2759, −0586 before its return.
All 83 live display samples were at 60 Hz. Changing the system
setting to Adaptive during this session left the display at 60 Hz.

The run peaked at 847.1 MiB of committed image memory during the
return and reached 62,758 coalesced texture copy regions by frame
10,200. The sampler recorded 3.41 GiB peak PSS. Android killed the
foreground process during the third surface sprint, 421.0 seconds
into capture, after a window averaging 6.6 FPS. This fresh start and
single-primary configuration give a separate test of the renderer.
The aged comparison above provides the closer match to the 10021
route.

Reopening 10052 with Adaptive selected and the normal renderer
defaults produced a 120 Hz display mode. The process loaded the
Ioq'ui autosave, crossed terrain in two controller sprint/recovery
segments, and held 120 Hz in all ten samples over the 51-second
controller test. The 30 FPS cap remained in effect. The game exited
with `EXIT_SELF` and status 0 through the menu's Close action.

ADB updates preserved the development package and game data. After
testing, the original `totk.env` was restored byte for byte, Samsung
Motion smoothness returned to Adaptive, adaptive brightness resumed,
and USB stay-awake matched the original setting. Rendered screenshots
were inspected on the 2340 × 1080 device in loading, the Depths,
the return to Akkala and subsequent movement.

## Sustained gameplay optimization

The new comparison uses the same archived Ioq'ui autosave and starting
pipeline cache, Adaptive 120 Hz, Light 960 × 540 at a 30 FPS cap,
and brightness 26/255. The previous experimental memory options stay
enabled. The single-primary option is off in both arms. The feature
under test is the use of separate 8 MiB blocks for small textures.

The 10052 control ran all seven surface segments, took both warp
legs with 261 seconds between requests, and completed two additional
surface sprint segments. Android killed the foreground process
during the third after 896.2 seconds of capture. All 178 live
display samples were 120 Hz. Peak process PSS was 3.42 GiB and
peak image commitment after the return was 815.1 MiB. The pressurized
tail still held 736 MiB of image blocks with only about 441 MiB occupied.
The 300-frame windows fell through 21.7 and 15.3 FPS with zero new
pipelines, then ended at 5.6 FPS with 72.5 ms/frame of command-walker
time off CPU and a 678 ms frame.

An independent rootless sampler saw a median of 464 major faults per
second from the game during the measured portion of surface traversal.
After the return, the median rose to 14,871 per second over ten
intervals. The system reported more than two million swap-in pages in
the same 51-second sample, and the command-walker threads contributed
about 257,000 of the game's 743,000 major faults there. This establishes
substantial page activity during the slowdown. System swap counters
include other processes, and a major fault does not identify the
backing source or the cause of a specific frame.
[Linux pressure stall information](https://docs.kernel.org/accounting/psi.html)

Build 10053 used the same archive and movement inputs with the small
blocks experiment. The two runs took different paths around obstacles
on the surface. The control ended that leg at 4235, 2779, 0126 and
the experiment ended it at 4161, 2041, 0045. Both used the same
lightroot and shrine and waited about 261 seconds between warp requests.
The experimental arm retained 120 Hz in all 172 live samples. Its
first 16 complete surface windows had a median of 27.0 FPS and a
worst frame of 155.7 ms. The control had 29.5 FPS and 296.9 ms over
the corresponding number of windows.

| Return measurement | 10052 control | 10053 small blocks |
| --- | ---: | ---: |
| Peak image commitment | 815.1 MiB | 871.1 MiB |
| Peak sampled PSS for entire capture | 3.42 GiB | 3.31 GiB |
| Time from return request to foreground LMKD | 115.7 s | 31.7 s |
| Confirmed playable surface after warp | Yes | — |

The smaller blocks raised peak image commitment by 56 MiB in this
comparison. The experiment died before the post-warp running segments.
Its last two reports showed live private texture mirror bytes rising
from 356 to 514 MiB. The earlier closure limited its peak PSS sample
to a different portion of gameplay. This result did not qualify the
allocation policy for the active build. Its implementation was removed
from the working source, the experimental APK and inputs were retained
locally, and the phone was returned to 10052 with the original settings
and game-folder environment.

### Private texture age and native heap release

10054 and 10057 used the archived 17:26 Ioq'ui save, the same initial
pipeline cache, the same seven timed surface segments and 22 seconds
of Depths movement. Both used the bundled driver and Light at
960 × 540, capped at 30 FPS with frame generation off. The S23+
stayed on Adaptive refresh with brightness set to 26/255.
10054 added counters only. 10057 also requested Bionic's minimum
release interval for previously freed native allocations, with
`mallopt` reporting success.

The 10054 control ended its surface leg at 4178, 2014, 0047,
loaded the Iu'iqoi lightroot and completed its running segment.
The game slowed to 8.6 FPS in its final complete window.
Android reported PID 14046 as `LOW_MEMORY` at foreground
importance 100, about 129 seconds after the request to enter
the Depths and before the return warp. All 110 live display
samples were at 120 Hz.

The 48 image age reports cover 88–136 MiB of private mirrors
with no lookup in at least 600 submissions in the 28 surface
movement windows. None of the 48 samples showed an entire
block occupied exclusively by that group. Some dedicated
images fell into the old bucket while the map was open and
became current again in gameplay.
[Texture age measurements and scope](transition-memory-research.md#texture-lookup-age-and-host-allocator)

10057 ended the surface leg at 4221, 2052, 0035, entered the
same lightroot and survived the comparable early Depths interval.
It requested the warp back to Ioq'ui 339 seconds after the first
request. The return was visually confirmed. The process died during
the first post-return run, about 78 seconds after requesting
the return. Android reported foreground `LOW_MEMORY` at
importance 100 for PID 17236. All 164 live samples were at
120 Hz. The last full window reached 24.4 FPS with zero
pipeline builds. A later individual frame reached 429.5 ms,
also with zero builds.

| Matched portion | 10054 control | 10057 short malloc decay |
| --- | ---: | ---: |
| First 20 complete surface windows, median FPS | 28.0 | 28.6 |
| Surface, median game major faults per second | 3,643 | 2,059 |
| Early Depths, median game major faults per second | 7,899 | 2,540 |
| Early Depths, median Android-reported native heap swap PSS | 352.9 MiB | 314.0 MiB |
| Early Depths, median Android-reported total PSS | 3,125.5 MiB | 3,082.9 MiB |
| Peak image commitment, full capture | 783.1 MiB | 783.1 MiB |

The surface memory and fault intervals cover 10–260 seconds
after movement began. The matched Depths intervals cover 40–125
seconds after the warp request. These are single sequential
trials with different steering outcomes and system pressure.
A separate earlier 10052 control also made the return and
survived about 116 seconds after requesting it. The new trial
does not establish a reliable improvement at the return, and
the short-decay override stays off by default. Build 10052 and
the saved phone settings were restored.

### Sparse copying into GPU pools

Build 10059 compared two modes using the same file-backed guest
reservation, starting save and pipeline cache. The control copied
from mapped addresses. The alternative read from the backing file
where the original mapping was still present. Both rendered the
same area around Ioq'ui and moved toward the nearby trees and
buildings. The candidate's fixed-time sprint started while the
load screen was still up, so the accepted movement times differed.
Both exited through the save-aware close path.

| S23+ observation | Mapped copy | Sparse copy |
| --- | ---: | ---: |
| Allocated guest backing sampled at the title | 859.4 MiB | 740.1 MiB |
| Allocated guest backing at renderer frame 2700 | 1,550.5 MiB | 1,547.3 MiB |
| Single process PSS sample after the run | 2,774.5 MiB | 2,916.8 MiB |

The alternative copied 1.10 GiB cumulatively through the new path.
The initial backing reduction nearly vanished during surface play.
The short run does not establish a frame-rate improvement or
justify enabling the mode by default. Both modes remain local
experiments. The phone is back on build 10052 with the saved
brightness, USB stay-awake and refresh settings.
[Shared-memory mechanism and fixture](transition-memory-research.md#displaced-guest-memory-backing)

Build 10060 scanned the original backing at frame 2699 during
another surface run. The addresses of active DMA-backed pools
intersected 1,176.8 MiB of the reservation. Their old file
offsets still held 232.1 MiB of allocated backing. This is
occupied file backing and may include swapped pages. The scan
neither freed it nor established which portions still served a
live alias. The surface was visible after the scan and Android
reported 120 Hz. The app then exited through its save-aware
close path.

### Reclaiming old DMA-pool backing

Build 10062 enabled the experimental `discard` mode on the S23+.
The early Akkala scan at frame 2699 found zero occupied bytes at
original backing offsets covered by 1,174.8 MiB of active DMA
mappings. The earlier 10060 diagnostic run found 232.1 MiB
occupied at that point. The test fixture preserved a live alias
and passed on the Linux host and on the S23+ kernel.

The 10062 experiment finished seven surface movement segments
and reached Iu'iqoi. After about 265 seconds in the Depths route
it requested the return warp and reached playable Akkala. It
completed one post-return running segment. Android recorded a
foreground `LOW_MEMORY` exit at importance 100 during the second,
101.9 seconds after requesting the return. All 155 live display
samples reported 120 Hz.

On 2026-11-18, a fresh 10062 control began from the same save and
cache with discard disabled. It completed all seven outward
surface segments, reached the same lightroot, waited 267 seconds
between the two warp requests and returned to Akkala. It completed
all three post-return running segments and still ran 174 seconds
after requesting the return, when the session ended through the
save-aware close path. All 176 live display samples reported 120 Hz.
At 4156, 2502, 0086 the rendered map displayed the green Hero's Path
trail after pressing X.

| S23+ observation | 10062 control | 10062 discard |
| --- | ---: | ---: |
| First 20 complete outward surface windows, median FPS | 30.0 | 30.0 |
| Peak sampled guest file backing | 1,637.3 MiB | 1,341.8 MiB |
| Peak sampled process PSS | 3,696.7 MiB | 3,765.8 MiB |
| System memory PSI full avg10, median 40–100 seconds after return request | 2.06% | 20.31% |
| Post-return running segments completed | 3 | 1 |
| End of run | Save-aware exit | Foreground LMKD during segment 2 |

These sequential trials shared the save, cache, route destinations
and segment schedule. Steering and world conditions led to different
positions and the trials ran at different times. Exact frame numbers
also land in different loading or play phases. The backing
reclamation works, but a smaller backing file did not establish less
process memory pressure or a longer usable session. Discard stays
an opt-in experiment. The trial that died showed more time stalled
on memory despite more than 8 GiB of reported free swap in the
matched return interval. The pressure readings describe the system
during the run and do not attribute the stalls to a single allocator.
[Android lmkd and pressure stalls](https://source.android.com/docs/core/perf/lmkd)

### Upstream write-back and explicit 60 Hz

Signed development build 10063 includes the reconciled upstream
write-back, mapping lifetime and pause-report changes. With the
experimental alias and discard options both enabled, it loaded the
Akkala autosave and completed two controller-only, 22-second
surface running segments. Android reported 60 Hz in all 26 samples
while testing `TOTK_FRAME_RATE_HINT_HZ=60`. The overlay showed
30.0 FPS and 33.4 ms at the shrine. Opening the Back menu paused at
a guest frame boundary and logged 5,300 alias landing records.
The app exited through the save-aware close path.

This short trial establishes that the two experimental paths and
the explicit refresh request worked together on the sampled route.
It does not qualify aliasing for the longer Akkala–Depths return
or compare battery consumption. [Upstream review](beta-feedback-upstream.md)

### Full return route with upstream write-back enabled

Signed build 10066 added the overlay's Android battery temperature
fallback and retained the same shader translator as 10062 and 10063.
The route used the same advanced save, Light preset and controller
inputs with `TOTK_WB_ALIAS=1`, the guest
backing in measurement mode and the ordinary Adaptive display
policy. The game read the default 120 Hz request. The Android
framework reported 120 Hz across both captures, 176 live samples.

The candidate ran seven outward surface segments, loaded Iu'iqoi,
ran in the Depths, and requested the return 284.8 seconds after the
outward warp. It arrived at Ioq'ui and finished all three planned
post-return running segments. The green Hero's Path was visible
in the 2340 × 1080 landscape map after the third. A save-aware
close began 204.1 seconds after requesting the return. Android
recorded `EXIT_SELF`, status 0, for the same gameplay process.
The log recorded 14,048 GPU write-back landings through the alias.

| S23+ observation | 10066, alias enabled |
| --- | ---: |
| First 20 complete outward surface windows, median FPS | 29.75 |
| Seven complete windows during the post-return movement, median FPS | 26.9 |
| Lowest of those return windows | 24.6 FPS |
| Longest frame during those return windows | 108.15 ms |
| Peak sampled process PSS | 3,763.3 MiB |
| Peak sampled guest file backing | 1,689.4 MiB |
| System memory PSI full avg10, median 40–100 seconds after requesting the return | 1.68% |

The outward route's 1.85-second hitch at frame 6104 spent 1,697.9 ms
on synchronous graphics pipeline creation, 79.4 ms on shader seed
reads and 0.3 ms on GPU waits during recording. The nearby 20
successful capture-build traces took 75.4–99.8 ms individually
and all targeted the same 480 × 268 capture submission.
Each reported app-cache hits in the driver's creation feedback,
which describes work avoided during the call. A cache-only probe
had returned compile-required for these graphics keys. A small list
of the 20 captured keys matched the shader manifest and is ready
for an explicit warm-up comparison. Thirteen are in the ordinary
APK warm-up list, which this low-memory profile disables. The
remaining seven are absent from that list.
[Vulkan pipeline creation feedback](https://docs.vulkan.org/spec/latest/chapters/pipelines.html)

On the return, frame 23943 took 108 ms, including 26.7 ms of
recording, zero graphics or compute pipeline creation and 1.7 ms
of guest sync waits. The older 10062 control also survived its
scheduled close. A second 10066 run with aliasing disabled is needed
to attribute any stability or performance difference.

The initially copied Vulkan cache was at the unsuffixed override
path. The Android backend used the `.intfold-v1` namespace, so
this launch began with a cold persisted graphics cache. The first
run wrote the namespaced cache and full GPU key collection on
close. The subsequent alias comparison must also start cold.

The battery level fell to 17% on the USB connection. The session
ended after the route and build 10052, the original developer
options, adaptive brightness, USB stay-awake and refresh settings
were restored.

### Host preparation while the phone charges

Build 10067 adds the opt-in `TOTK_PSO_RECREATE_CAPTURES=1`. When
prewarm is enabled and the supplied list contains at most 32 keys,
it recreates the process-local Vulkan handles for completed capture
keys on the existing background worker. It retains the binary list
format and the cache-bound resume bitmap. The option is off by
default.

The desktop Vulkan fixture collected a real capture key and a normal
screen key. The cold run built both. The default restart restored two
completion bits and built zero handles in the background. The opt-in
restart restored both bits and built exactly one handle, for the
capture. The portable-key suite also tested disabled and oversized
lists, unfinished keys, screen keys and failed recreation. The full
host suite passed 682 tests with 92 skips. The signed
APK contains the same shader translator as 10066. The cold-cache
alias control uses 10066 with its original prewarm settings. A
separate comparison will test the 20 Akkala keys. The restart
option can be compared once this warm-up trial has produced a
valid persisted cache and resume marker.

The independent hitch investigation will enable `TOTK_FRAME_TIMELINE=1`
for a traced run. Its report includes guest wake, recorder wall and
off-CPU intervals, submit and present stages and GPU timestamp
coverage. The local analysis preserves timeline IDs separately from
the renderer's counter. Several intervals overlap, and the trace's
dominant field describes growth relative to the preceding frame.
Scheduling and compositor events in a system trace can provide
additional timing evidence if the hitch recurs.
[Android FrameTimeline trace source](https://perfetto.dev/docs/data-sources/frametimeline)

During this host phase, the owner was charging the locked S23+.
The phone was next used when the owner made it available.

### Same-build cold-cache alias comparison

After the owner made the S23+ available, a second APK 10066 trial
used `TOTK_WB_ALIAS=0`, the archived Ioq'ui save, the same Turnip
and Light profile and the same controller inputs. Both trials
started with a cold persisted graphics cache and 73 learned
compute keys. Apart from the isolated profile paths, the alias
switch was the sole configuration change.

The control ran all seven outward segments, reached Iu'iqoi and
returned to Ioq'ui after a 298.0-second Depths interval. It finished
all three post-return running segments. The game exited through
its save-aware close path 204.1 seconds after the return request,
matching the prior alias-on observation time. Android recorded
`EXIT_SELF`, status 0, and 120 Hz in all 179 live samples. The
rendered map displayed the green Hero's Path again.

| S23+ observation | 10066 alias off | 10066 alias on |
| --- | ---: | ---: |
| First 20 complete surface windows, median FPS | 29.9 | 29.75 |
| Seven full post-return movement windows, median FPS | 25.2 | 26.9 |
| Longest frame in those return windows | 173.66 ms | 108.15 ms |
| Peak sampled process PSS | 3,719.4 MiB | 3,763.3 MiB |
| System memory PSI full avg10, median 40–100 seconds after return request | 8.46% | 1.68% |
| Return segments before scheduled close | 3 | 3 |

The two runs were sequential and had different starting temperature,
terrain positions and Depths dwell times. The alias-on run had better
observed return timings, while both reached the scheduled close.
These trials do not demonstrate a repeatable FPS or crash-rate
improvement. The experimental alias remains off by default.

The control reproduced all 20 known graphics pipeline identities
in the surface burst with 1,708.5 ms of accumulated synchronous
creation across the matched keys. Its longest frame during the
outward movement was 1,755 ms. The precise timing row attributed
1,625.2 ms of that frame to graphics pipeline creation. Matching
these exact identities makes them suitable for the isolated
precaching run.

### Selective pipeline warm-up on the S23+

A separate 10066 run kept alias off and replayed the first four
surface segments from the same archived save. The initial
persisted graphics cache was cold. With the small list
explicitly enabled, the device created all 20 capture pipelines
on the background worker before the save loaded. The batch took
4,556.5 ms of wall time including pauses, with 2,120.5 ms in
build work. All 36 display samples reported 120 Hz.

Over the first 13 complete movement windows, the median and
worst observed frame were 29.9 FPS and 1,755 ms in the control,
versus 29.6 FPS and 417 ms in the prewarm run. The new run
logged no first demand or synchronous creation for the 20 exact
keys. The same capture event therefore remains unverified
in the prewarm arm and the observed maximum cannot be
attributed to the optimization yet.

The 10069 restart reused the exact list and the validated cache
and resume bitmap from that run. With recreation enabled, it
logged 20 of 20 resumed and 20 queued for recreation. All 20
rebuilt on the background worker before playing, with 7.6 ms
of build work in 2.012 seconds of wall time. This confirms the
optional restart path on Android with the bundled Turnip driver.

### Descriptor batching on the S23+

Two short APK 10069 runs used the same archived save, controller
inputs and byte-identical copies of the 25,952 KiB driver cache.
Turnip accepted both copies. The graphics profile, recorder options
and load-to-motion timing were matched. The only environment
change apart from profile paths was `TOTK_VK_DESC_BATCH`.

| Six complete surface windows | Batching off | Batching on |
| --- | ---: | ---: |
| Median allocation calls per frame | 3,856.43 | 3,556.07 |
| Median allocated sets per frame | 3,856.43 | 3,770.49 |
| Median retained pools | 25.5 | 24.5 |
| Median FPS | 29.6 | 28.95 |
| Longest measured frame | 84.08 ms | 66.19 ms |
| Live display samples at 120 Hz | 24 | 24 |

Both rendered the surface and finished the two sprint segments.
The recorder used fewer calls than allocated sets with batching
enabled, confirming it was exercised on Android. The total call
difference also includes variation in descriptor workload. The
short run showed no clear FPS gain. Batching stays opt-in.

The owner requested a pause immediately after these runs. The
game had already exited through the save-aware close path. The
previous 10052 APK, developer options, adaptive brightness and
USB stay-awake settings were restored. Sustained gameplay
qualification and issue #55 remain open.

### Extended 10069 route with the bundled driver

The signed build ran on the S23+ with bundled Turnip, Light at 960 × 540,
30 FPS, Adaptive refresh and brightness 22. It loaded a fresh copy of the
advanced Ioq'ui save and a matching pipeline cache. The optional capture
worker recreated all 20 selected pipelines before play, with 1.5 ms of
build work. Alias write-back, descriptor batching and guest-backing discard
stayed disabled.

The same process completed seven outward running segments, reached the
Iu'iqoi lightroot and moved in the Depths. It requested the return to
Ioq'ui 305.4 seconds after the first warp request, then finished all three
post-return segments. The map rendered the green Hero's Path. Three
additional running segments reached an Akkala chasm and descended into
the Depths without a fast-travel load. The game drew the Anuronte oscuro
encounter, accepted movement to get away and teleported to Lookout
Landing. Two more running segments followed in the settlement.

| Phase | Complete 300-frame windows | Median FPS | Lowest window | Longest frame |
| --- | ---: | ---: | ---: | ---: |
| Outward surface | 29 | 30.0 | 28.5 FPS | 265.57 ms |
| Depths sprint | 2 | 29.25 | 28.9 FPS | 134.71 ms |
| Three return sprints | 6 | 23.3 | 20.0 FPS | 173.07 ms |
| Additional surface and chasm descent | 9 | 29.9 | 25.0 FPS | 289.40 ms |
| Lookout Landing travel and load | 3 | 28.3 | 19.7 FPS | 1,067.76 ms |
| Lookout Landing movement | 2 | 13.05 | 11.6 FPS | 508.66 ms |

Android recorded 233 live samples, all from the same process at 120 Hz.
Peak sampled process PSS was 3,545 MiB and the system's minimum sampled
`MemAvailable` was 625 MiB. After 19 minutes 26 seconds of capture, the
app flushed the cache and Android recorded `EXIT_SELF`, status 0. Battery
temperature rose from 26.3 °C before launch to about 39 °C near the end.
These measurements establish a longer successful route. The return
sprints and Lookout Landing still need work to hold 30 FPS.

The 1.07 s travel hitch included 517.2 ms in graphics pipeline creation
and 145.3 ms in shader seed reads. In the settlement, one 509 ms frame
spent 401.6 ms in graphics pipeline creation. The worst measured return
movement frame spent zero time building graphics or compute pipelines.
Those bottlenecks need different comparisons. The original running inputs
can drift as frame timing and scene conditions change.

### Lookout Landing cache comparison

Three separate 10069 processes loaded copies of the same Lookout Landing
autosave from the extended route. Each used the bundled driver, Light,
30 FPS, brightness 22 and Adaptive refresh. They started at 35.1–35.2 °C
and repeated two timed movement segments. The initial view matched and
the screenshots showed nearby endpoints with some position and in-game
time differences.

The control used the pre-route 17,286 KiB pipeline cache. The previously
visited arm used the 30,316 KiB cache from the extended run. The selective
trial used a byte-identical control cache and precompiled eight capture
keys selected from the control trace by measured synchronous build time.
Each loaded cache matched its driver and context. All three runs
finished with a save-aware close and 120 Hz in all live samples.

| First four complete gameplay windows | Control | Cache from prior visit | Eight-capture prewarm |
| --- | ---: | ---: | ---: |
| Median FPS | 29.55 | 29.80 | 27.55 |
| Median window p99 frame time | 48.80 ms | 44.43 ms | 58.17 ms |
| Longest frame | 225.88 ms | 130.58 ms | 461.65 ms |
| Frames over 50 ms | 12 | 9 | 55 |
| Logged pipeline build time | 352.2 ms | 83.5 ms | 653.5 ms |

All eight prewarm builds completed at the title and took 792.6 ms of
build work. Seven were later requested with a ready handle. Other
graphics pipelines still took 398.7 ms in the 462 ms frame. Keep this
short list out of the default profile. The complete cache from the
prior visit gave the best result in this short comparison. Each result
comes from one run.

The fresh control recorded 71,240 major process faults and 1.47 seconds
of system full memory stalls over 12 sampled intervals. The earlier
settlement movement in the extended process recorded 517,931 major
process faults and 9.90 seconds of full memory stalls across the same
number of intervals. The longer run also reached the settlement hotter
and with different cached terrain and lighting. The next endurance
comparison should use the same initial route, the cache from the prior
visit, and similar thermal conditions to check whether memory stalls
persist once the biggest pipeline builds are reduced.

Host regression checks passed for route reporting (7), pipeline keys
(14) and image memory (1). At the end of device testing, the prior APK
(10052), game environment, adaptive brightness and USB stay-awake
settings were restored. Story progression through the ending and
repeatability of the #55 mitigation remain open.

## Direct checkpoints and first endurance run

This campaign used copies of advanced saves for scenario coverage. It verified
reloading a fresh-profile prologue and a manual save on the Great Sky Island.
Separate checkpoints covered Akkala, Lookout Landing, a sky-to-Depths dive,
surface return, and shrine abilities. A short vehicle run verified steering
and camera movement. The route also exercised a save and reload, rain, smoke,
Recall, Fuse, Ascend, Ultrahand, the camera and Hero's Path.

The 10069 and 10074 pilots each covered Akkala, Iu'iqoi in the Depths, a return
to Akkala and an aged Lookout Landing visit in one process. Sampled PSS peaks
on the return were 3,777 and 3,614 MiB, respectively. A hotter 10074 repeat
returned to the same point and reached 3,750 MiB. In the pilot city footage
10074 was faster, but several phases still dropped below 30 FPS. The builds
also differed in shader translator bytes and start temperature.

| Trial | Observed result |
| --- | --- |
| Projection cap at 12, 8 and 5 km | The 5 km cap saved 32 MiB of committed Vulkan images in the short field runs. The control and 5 km arm both opened the same 548 far-texture paths. Process memory did not consistently fall. |
| Smaller mip chains for moss and sky islands | Both overlays were loaded. Neither gave a repeatable reduction in process memory or system pressure. |
| Half-distance grass and half-radius decorative island actors | The grass change was visible and left Vulkan image commitment unchanged in the matched scene. The actor-radius change left the selected model, pack and texture requests present. |
| Reduced preload lists at one Depths entrance | Removing four far models from the resource list and four corresponding far actors from the actor list suppressed two model opens in the surface test. The return from the Depths skipped one of three model opens seen in its control. The pressure and PSS samples did not establish a benefit. |
| Shadow atlas fixed at 256 | In a short field comparison it used 96 MiB less Vulkan image commitment than original shadows. Peak PSS was 3,148 vs 3,184 MiB and minimum system memory available was 756 vs 836 MiB, so the pilot alone does not establish better survival. |

The 10074 endurance run with original shadows ended after 29 min 3 s. Android
recorded `LOW_MEMORY` for the foreground game process during movement after
returning from the Depths. The return reached 3,818 MiB sampled PSS and
975.14 MiB of Vulkan image commitment. The following field segment recorded
30.06 s of full memory stalls and 1,143,853 major process faults over 28 sampled
intervals. The captured frame intervals in that segment averaged 8.67 FPS.

The fixed-shadow repeat used the same initial save and shader history. It
reached Lookout Landing and closed normally at the operator's request after
9 min 40 s. It did not reach the critical return segment. Neither the 90–120 min
endurance requirement nor sustained 30 FPS has been verified. None of the
experimental resource mods was selected for release. The four regional temple
and castle checkpoints are prepared for direct loading and await device checks.
