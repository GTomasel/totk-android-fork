# Vulkan drivers for the Galaxy S23+

Keep the fork's **bundled Turnip** for regular play on the tested Galaxy S23+
(SM-S916B, Android 16). The phone uses the Adreno 740 in the Snapdragon 8 Gen
2 for Galaxy. The bundled driver already completed the Akkala–Depths–Akkala
route on this phone. Both runs sustained 120 Hz display refresh and finished
three post-return running segments, with some frame-time spikes still
present. Both Banners-Turnip alternatives have since run a shorter
Akkala test on this phone. [Samsung device specs](https://www.samsung.com/es/support/mobile-devices/galaxy-s23-ultra-vs-s23-plus-vs-s23/),
[Khronos device listing](https://www.khronos.org/conformance/adopters/conformant-products/vulkan#submission_739)
and [S23+ route evidence](s23-device-validation.md#same-build-cold-cache-alias-comparison).

## Drivers to compare

| Order | Driver | What the trial can establish |
| --- | --- | --- |
| Baseline | Bundled Mesa `27.0.0-devel (git-3e8621cc0e)` | Reproduce the current results with the fork's exact renderer, cache format and patched Turnip. |
| First alternative | Banners-Turnip v27.0.0-20261118-r2 **Standard**, Android ZIP | Compare a newer Mesa **main** snapshot against the bundled driver on the same phone. The package ships Mesa commit `0e9e1086bb86721e21693763c6bf35415d93fff5`. |
| Compatibility fallback | Banners-Turnip v27.0.0-20261118-r2 **8G2 One UI**, Android ZIP | Try this if Standard produces flicker or corruption. It enables the Adreno 740 `TP_UBWC_FLAG_HINT` on the same Mesa base to match the Samsung graphics stack on affected firmware. |
| Optional source build | Mesa 26.3.0, built for Android arm64/KGSL | Use the tagged Mesa release to investigate a regression in the development snapshots if the first comparison warrants it. Confirm the game's memory and presentation paths before measuring. |

The bundled build includes 14 patches, including the port's reusable KGSL
command-stream slabs. A community build can change compiler behavior, GPU
memory use and submission costs at once. If an alternative wins on the
phone, use the pinned build recipe to test the relevant changes while
retaining the fork's patches. [Bundled build recipe](https://github.com/AurelioB/totk-android/blob/main/games/totk/android/turnip/README.md)
and [Mesa 26.3.0 release notes](https://docs.mesa3d.org/relnotes/26.3.0.html).

Upstream compared several Turnip builds in Gerudo Desert on the AYN Thor,
which also has an Adreno 740. Its October Banners snapshot averaged 27.1
FPS at the standard clock setting and 32.7 FPS at the performance setting,
versus 25.7 and 31.7 FPS with PurpleVK T26. The test used the Thor's own GPU
clock limits and an older port build. This shows that driver choice can
change performance in this port. The size and direction of the change on
the S23+ remain to be measured. One cold run on the S23+ spent over 1.6 s
in synchronous graphics pipeline creation in a single frame. A separate
108 ms return-warp frame spent zero time creating pipelines. A driver
comparison should measure those cases separately. [Upstream Thor measurements](https://github.com/AurelioB/totk-android/blob/main/games/totk/android/VULKAN.md#what-the-ayn-thors-drivers-offer-androidvkprobe)
and [S23+ frame-time evidence](s23-device-validation.md#full-return-route-with-upstream-write-back-enabled).

The Banners maintainer labels the November build as automated and recommends
the One UI variant when Standard flickers. The hint addresses compression
metadata compatibility for scaled blits when drivers exchange a buffer.
The device test should check for artifacts even if the driver initializes
and draws the first scene. [Banners release and Android packages](https://github.com/The412Banner/Banners-Turnip/releases/tag/v27.0.0-20261118-r2)
[One UI patch](https://github.com/The412Banner/Banners-Turnip/blob/v27.0.0-20261118-r2/patches/8g2_oneui.py)
and [Mesa device feature definition](https://gitlab.freedesktop.org/mesa/mesa/-/blob/0e9e1086bb86721e21693763c6bf35415d93fff5/src/freedreno/common/freedreno_dev_info.h#L401-406).

## Capability and package checks

TotK shares the game's memory pools with the GPU. The backend requires
working host-pointer import, DMA-BUF export or DMA-BUF heap import. Record
the actual pool mode and whether the game presents directly from a shared
Android hardware buffer or takes the copy path. The Qualcomm system driver
failed the startup check on the Thor. The S23+ stock driver on its current
firmware has no result in this comparison. Vulkan conformance alone does
not establish memory-sharing support. [Vulkan backend](https://github.com/AurelioB/totk-android/blob/main/games/totk/android/gfx/nvn_vk.c)
and [upstream driver probe](https://github.com/AurelioB/totk-android/blob/main/games/totk/android/VULKAN.md#what-the-ayn-thors-drivers-offer-androidvkprobe).

The fork already accepts Android AdrenoTools ZIPs and AArch64 driver
libraries through **Game data → Graphics driver**. The imported library
runs in the game's process. Obtain package files from their publisher and
match the release's reported SHA-256. **Use the bundled driver** restores
the original choice. [Driver import guide](android-install.md#drivers).

| Package | SHA-256 of ZIP |
| --- | --- |
| `Turnip-v27.0.0-20261118-r2.zip` | `6bb93e2045e8dc03f4f00dc98a85d0f54b479e9208e2c762c2dd39d4c582a294` |
| `Turnip-v27.0.0-20261118-r2-8G2-OneUI.zip` | `b3cffccd29609d86bb01a4239b7441fa133b653e9b3a8055a0edae307b280ad9` |

The downloaded ZIPs matched those hashes. A host run of the production
importer accepted both and extracted byte-identical AArch64 libraries.
All 12 driver-import tests passed. Android also loaded both libraries
and logged their expected SHA-256 hashes in the device trial below.

Bundled library SHA-256:
`9b87afeb3d8d30c6a0ad5aab3e0703bc1500e0321e9f17a922106fa556389ec6`.

## S23+ ADB results

APK 10069 ran on SM-S916B firmware `S916BXXSAFZI1` with Android 16
and One UI property `80500`. Each arm loaded a separate copy of the
same Ioq'ui Shrine save, used Light (960×540) at 30 FPS with frame
generation off, and repeated the same two timed sprint and walk
sequences. Manual brightness was set to 22 during testing. The
three cold trials started with empty persisted Vulkan graphics
caches and the same installed shader seed and learned-key index.

All three drivers selected DMA-BUF export for pools and the
direct LINEAR Android hardware buffer path for presentation. The
framework reported 120 Hz in every live sample. Both Banners
drivers rendered Akkala, including the landscape, player and map,
and all three runs reached the requested save-aware close.

| Five complete gameplay windows, cold graphics cache | Bundled Turnip | Banners Standard | Banners 8G2 One UI |
| --- | ---: | ---: | ---: |
| Median FPS | 29.60 | 29.90 | 30.00 |
| Median window p95 frame time | 41.67 ms | 39.72 ms | 40.20 ms |
| Median window p99 frame time | 56.49 ms | 46.22 ms | 46.11 ms |
| Longest frame | 202.05 ms | 189.45 ms | 228.15 ms |
| Frames over 50 ms | 36 | 30 | 26 |
| Peak sampled process PSS | 3,005 MiB | 2,882 MiB | 2,938 MiB |
| Battery temperature, start → end | 32.0 → 34.9 °C | 31.0 → 33.9 °C | 32.9 → 35.2 °C |

The One UI trial still showed the loading screen at the start
marker and covered slightly less ground in the first sprint. Its
five complete timing windows are shown for context. Consider the
One UI build a compatibility option.

The bundled and Standard warm runs each loaded a matching pipeline cache
from their own cold run (12,693 and 12,500 KiB, respectively). Both
repeated the same timed inputs from the same save with similar battery
temperatures. Their second sprint ended at different coordinates on the
map. Terrain and streaming work may therefore differ between these runs.

| Five complete gameplay windows, warm graphics cache | Bundled Turnip | Banners Standard |
| --- | ---: | ---: |
| Median FPS | 29.90 | 29.50 |
| Median window p95 frame time | 39.58 ms | 41.95 ms |
| Median window p99 frame time | 45.77 ms | 54.82 ms |
| Longest frame | 66.91 ms | 279.34 ms |
| Frames over 50 ms | 5 | 22 |
| Peak sampled process PSS | 2,992 MiB | 3,128 MiB |
| Battery temperature, start → end | 33.3 → 35.5 °C | 33.5 → 35.8 °C |

In the warm Standard run, the renderer attributed 232.1 ms of the
279 ms frame to graphics pipeline creation. The cold comparison favored
Standard on p99, and the warm comparison favored the bundled driver.
Keep the bundled driver for regular play. These short tests leave
sustained temperature, battery consumption, the return warp and
the memory pressure from issue #55 open. After testing, the device's
prior APK (10052), game environment, adaptive brightness and USB
stay-awake configuration were restored.

## Further testing for a device profile

1. Use the same signed APK, initial save, running inputs, Light preset
   (960×540), 30 FPS cap, frame generation off and adaptive refresh for
   each trial. Fix brightness, power state and starting device temperature
   as closely as possible. Record Android and One UI versions.
2. Check the loaded driver and SHA, pool mode and presentation path. Run the
   same Akkala ground sections and the Depths round trip. Check the map,
   wind effects, menus and gameplay for flicker, corruption and visual
   changes. Restore the baseline before testing another variant.
3. Run an initial cold test with an empty effective graphics cache for
   each build. Warm each driver's own cache with the same traversal, then
   alternate bundled and candidate runs at least twice. Keep the same
   shader seed. Record the effective cache path and hit status at startup.
   Vulkan driver caches have their own compatibility identifiers.
   [Vulkan pipeline cache specification](https://docs.vulkan.org/spec/latest/chapters/pipelines.html#pipelines-cache).
4. Compare median FPS, p95 and p99 frame times, frames over 50 and 100 ms,
   pipeline creation time, peak process PSS, system memory pressure,
   Android exit reasons and thermal/clocks trends. Log the actual display
   refresh rate independently of rendered FPS. Watch for CPU or GPU clock
   throttling once the phone is warm. A 30 FPS cap can hide extra render
   headroom, so inspect frame times and CPU/GPU timings before drawing a
   conclusion.
5. If frame pacing improves, repeat a longer open-world session and
   revisit return-warps under memory pressure. A driver change remains a
   candidate for [issue #55](https://github.com/AurelioB/totk-android/issues/55)
   only if it lowers memory pressure or prevents a reproducible exit.

Keep the documented recommendation. If a driver consistently
improves frame pacing or stability and passes the visual and thermal
checks, consider offering it as an opt-in recommendation for the tested
model and firmware, with the driver version and SHA recorded. The app
already has hardware-dependent settings for performance tuning. Keep the
graphics driver selection scoped to the phone and firmware actually tested.
