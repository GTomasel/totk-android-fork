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
