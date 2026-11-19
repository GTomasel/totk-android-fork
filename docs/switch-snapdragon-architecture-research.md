# Switch to Snapdragon performance research

The 10069 measurements identify separate sources of delay on the Galaxy S23+.
First-use graphics pipeline creation accounts for hundreds of milliseconds in
some Lookout Landing frames. A long frame after returning from the Depths
created zero pipelines while the route showed elevated memory pressure. The
larger opportunity is sustained frame pacing after multiple regions, alongside
first-use pipeline cost. [S23+ route and cache measurements](s23-device-validation.md#extended-10069-route-with-the-bundled-driver).

## Hardware and translation boundaries

| Layer | Original Switch | Galaxy S23+ and this port | Performance implication |
| --- | --- | --- | --- |
| CPU and ABI | Nintendo identifies a custom Tegra. The original console teardown identifies the T210 with Cortex-A57/A53 cores and a GM20B GPU. The generic NVIDIA Tegra X1 whitepaper documents the SoC family. | Samsung's conformance filing identifies Snapdragon 8 Gen 2 for Galaxy, Armv9 and Adreno 740. Qualcomm documents Cortex-X3 technology in the platform family. | The port runs rewritten AArch64 game code directly. Profile host stubs, system services, the command recorder and driver. Clock rate or core count by itself cannot compare this mixture of work. [Nintendo](https://www.nintendo.com/us/gaming-systems/switch/tech-specs/), [board teardown](https://www.techinsights.com/blog/nintendo-switch-teardown), [NVIDIA X1 whitepaper](https://images.nvidia.com/content/pdf/tegra/Tegra-X1-whitepaper-v1.0.pdf), [Khronos filing 739](https://www.khronos.org/conformance/adopters/conformant-products#submission_739), [Qualcomm brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/images/company/news-media/media-center/press-kits/summit-2022/day-1/documents/Snapdragon_8_Gen_2_Product_Brief.pdf), [port architecture](architecture.md). |
| GPU and API | Maxwell hardware and the console's NVN API. | The port translates NVN commands into Vulkan. The setup translator generates SPIR-V, which Turnip compiles for Adreno. | A shader seed and a driver pipeline cache address different stages. Command order, visibility and guest resource lifetimes must survive across the two graphics APIs. [NVIDIA Switch announcement](https://blogs.nvidia.co.jp/blog/nintendo-switch/), [Mesa Turnip](https://docs.mesa3d.org/drivers/freedreno.html), [graphics port](../games/totk/android/VULKAN.md). |
| Shared memory | The generic Tegra X1 has an LPDDR4 interface shared by SoC clients. The board examination identifies LPDDR4 parts. | Android accounts for system memory and process memory as well as Vulkan heaps. The port shares Vulkan-visible backing with data at the guest's virtual addresses. | Virtual aliases, CPU mappings and GPU allocations can describe the same data. Track backing identity, ownership and completion before classifying bytes as reclaimable. [NVIDIA memory architecture](https://images.nvidia.com/content/pdf/tegra/Tegra-X1-whitepaper-v1.0.pdf), [board teardown](https://www.techinsights.com/blog/nintendo-switch-teardown), [Android accounting implementation](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android14-release/services/core/java/com/android/server/am/ActivityManagerService.java), [port pool mapping](../games/totk/android/VULKAN.md#memory-zero-copy-pools-without-host-pointer-import). |

Console revisions, active cores, power profiles, clocks and memory available to
a title need console-specific evidence. Qualcomm's product benchmarks and the
Samsung Vulkan certification cannot establish the features available on a
separate Turnip build or how fast it runs after heat and memory pressure build up.
Use the bundled Turnip binary as the comparison control. [Driver build pin](../games/totk/android/turnip/README.md), [S23+ driver comparison](s23-gpu-driver-research.md#s23-adb-results).

### Arm CPU, scheduling and thermal limits

The runtime already uses a render-thread ADPF performance hint by default.
Critical-thread, work-duration and GPU-span modes are opt-in. Compare thread CPU
time and runnable time for the guest main, the recorder, the submission thread
and compile workers before changing thread affinity or hints. An aggressive hint
can improve early latency while moving throttling earlier in a long session.
Record thermal headroom when supported, frequency and hardware completion
times. A battery temperature reading measures a different signal from the SoC
governor's headroom. [Android ADPF](https://developer.android.com/games/optimize/adpf), [thermal API](https://developer.android.com/games/optimize/adpf/thermal), [runtime hints](../games/totk/runtime/android_perf.c), [existing policies](../games/totk/android/APP.md#android-performance-hints-experimental-full-mode).

Perfetto offers kernel scheduler events, CPU samples, frequency and GPU
data sources. Correlate the port's frame identifier with CPU submission, GPU
completion and compositor expected/actual frames. Probe profiler support on
the exact device and driver before attributing unobserved GPU time. The 120 Hz
display policy and the game's 30 FPS cap are separate measurements.
[Perfetto CPU sampling](https://perfetto.dev/docs/quickstart/callstack-sampling), [GPU data sources](https://perfetto.dev/docs/data-sources/gpu), [FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline), [S23+ refresh measurements](s23-device-validation.md#refresh-and-timing).

Prefer fewer traversals, smaller temporary arrays and fewer bytes copied before
microarchitecture-specific changes. For a measured CPU-hot swizzle or copy,
compare portable and AArch64 Advanced SIMD implementations against exact bytes,
odd strides and small ranges. Optional instruction sets need a runtime check
on any supported ABI that may lack them. CPU fixture speedups alone cannot
predict phone speedups under thermal or memory pressure. The port has already
tested some deswizzle and hash changes, including candidates that gave no
hardware gain. [Arm Cortex-X3 TRM](https://documentation-service.arm.com/static/62bb289431ea212bb6625392), [Arm Cortex-A715 optimization guide](https://documentation-service.arm.com/static/62bc010a31ea212bb66256b4), [prior translation experiments](translation-research.md).

Keep the rewritten AArch64 code and Android ABI boundary distinct from address
space optimization. The runtime translates privileged or platform-sensitive
instructions, including the platform register, TLS and system calls, and
uses Linux virtual mappings for guest address ranges. Guest granularity, host
page size, DMA-BUF import alignment and texture block size are separate
properties. Android supports devices with 16 KiB system pages, so preserve
runtime page-size checks and ELF alignment when making release, protection
or suballocation changes. Avoid increasing the number of mapping splits
for a small gain in committed bytes. The port records an earlier freeze
and crash with many fragmented mappings. [Port architecture](architecture.md), [runtime mapping history](../games/totk/android/README.md#how-the-linux--android-differences-are-handled), [Android page-size guidance](https://developer.android.com/guide/practices/page-sizes).

### Vulkan render paths and bandwidth

Turnip can select tile-local GMEM or direct SYSMEM rendering per pass. Upstream
documents multiple autotune policies. Check that an option exists on the pinned
build before measuring it. Global GMEM forcing already performed poorly on a
separate A740 device in the project's documented benchmark. Pass-level load,
store, draw and byte counters can identify where reducing main-memory traffic
would help. [Mesa autotune](https://docs.mesa3d.org/drivers/freedreno.html#autotune), [port experiments](../games/totk/android/VULKAN.md).

The renderer already supports tracked attachment discard and optional pass
splitting. Limit load/store reductions to contents proven dead after a clear
or tracked invalidation. Account for NVN sampling, guest CPU reads, copied
regions, feedback, presentation and aliases. A split can feed the GPU sooner
while increasing tile stores and loads. Framebuffer-local dependencies can
reduce traffic where the producer and consumer meet the Vulkan rules. Track
actual stages, accesses and ranges when narrowing barriers. Keep queue
ownership and fences around external buffers and host-visible writes.
[Khronos render-pass sample](https://docs.vulkan.org/samples/latest/samples/performance/render_passes/README.html), [dynamic rendering local read](https://docs.vulkan.org/features/latest/features/proposals/VK_KHR_dynamic_rendering_local_read.html), [synchronization examples](https://docs.vulkan.org/guide/latest/synchronization_examples.html), [Khronos barrier sample](https://docs.vulkan.org/samples/latest/samples/performance/pipeline_barriers/README.html), [current draw path](../games/totk/android/gfx/vk_draw.c).

Maxwell compression and Qualcomm UBWC are GPU-side mechanisms. This port
already uses UBWC on eligible render targets and has a separate experimental
compressed Android hardware-buffer present path. Imported format modifiers,
format lists and image flags can affect eligibility. Texture swizzling,
render-target compression and compositor buffer import need separate
validation. For synchronization or format changes, cover depth/stencil, CPU
readback, aliasing, retire fences, and identical pixel output before device
trials. [NVIDIA X1 whitepaper](https://images.nvidia.com/content/pdf/tegra/Tegra-X1-whitepaper-v1.0.pdf), [Vulkan AHB import extension](https://docs.vulkan.org/refpages/latest/refpages/source/VK_ANDROID_external_memory_android_hardware_buffer.html), [UBWC and present implementation notes](../games/totk/android/VULKAN.md), [writeback fixtures](../tests/test_wb_alias.py).

Keep guest BC texture blocks intact when the selected format, tiling,
usage and view combination supports them. Vulkan exposes BC format support
through feature and per-format queries. Expanding guest textures into
uncompressed colors can increase staging and device bytes. Transcoding
to a different lossy compression format also changes the image and needs
separate quality qualification. Upgrade comparisons should include actual
copy format and region shape. A Turnip maintainer documents Adreno A2D copy
paths and format-dependent 3D fallbacks. Their later raw-copy hardware
path was observed from A750, so it cannot be assumed on this A740.
[Vulkan format feature guidance](https://docs.vulkan.org/guide/latest/formats.html), [Turnip copy implementation study](https://www.igalia.com/downloads/slides/KarmjitMahil-ImprovingBbufferImageCopiesOnTurnip.pdf), [prior upload work](transition-memory-research.md#coalesce-contiguous-texture-upload-regions).

## Priorities driven by measured routes

### Pipeline reuse and compilation

The 1.068 s Lookout Landing travel frame included 517.2 ms of graphics
pipeline creation and 145.3 ms of seed reads. In fresh starts from the same
autosave, the cache from a prior visit reduced the worst comparable frame from
225.88 to 130.58 ms and recorded pipeline-build time from 352.2 to 83.5 ms.
Selective startup compilation built eight capture keys and later hit seven
ready handles. Other pipeline cases still produced a 461.65 ms frame. Each
configuration ran once. Broadening prewarm based on one list needs evidence of
recurrence, remaining misses, startup time and memory cost.
[Fresh and aged measurements](s23-device-validation.md#lookout-landing-cache-comparison).

Replay the same long route with the prior-visit full cache and then compare
reuse under sustained thermal and memory conditions. Log the complete pipeline
identity, shader loading and preparation, Vulkan create/link duration and
compile worker queueing. Interpret cache feedback only when its valid bit is
set. A feedback hit may describe a reusable stage while the app still does
work around creating a handle. Keep cache identities tied to driver and
shader configuration. The port already supports graphics pipeline
libraries and a persistent cache. Compare link options on the exact workload
if CPU creation still dominates. Vulkan pipeline binaries can offer explicit
control where supported, but verify features on the pinned build before
planning another persistence path. [Pipeline cache guide](https://docs.vulkan.org/guide/latest/pipeline_cache.html), [feedback flags](https://docs.vulkan.org/refpages/latest/refpages/source/VkPipelineCreationFeedbackFlagBits.html), [graphics pipeline library sample](https://docs.vulkan.org/samples/latest/samples/extensions/graphics_pipeline_library/README.html), [pipeline binary sample](https://docs.vulkan.org/samples/latest/samples/extensions/pipeline_binary/README.html), [current cache saver](../games/totk/android/gfx/vk_pcache.c), [replay policy](../games/totk/android/gfx/vk_pso_runtime.inc).

The packed seed has indexed reads, a bounded warm set, shared in-flight
reads and immediate cold demand past unrelated worker work. It deliberately
uses pread to avoid SIGBUS on a truncated pack. Evaluate repeatable cold
offsets and decode costs before attempting short read-ahead. A host fixture
can count copied or read bytes and enforce bounded temporary memory while
covering truncation and concurrent requests. Whole-pack preloading could
increase pressure and compete with the same demand I/O it seeks to improve.
[Indexed seed reader](../games/totk/android/gfx/vk_seed_io.c), [shader seed design](first-launch-shaders.md).

The guest RomFS reader also uses pread, with explicit range and chunk handling
for split images. Distinguish guest asset reads, shader-pack reads, driver
cache I/O, anonymous/shmem faults and device buffer copies before optimizing
storage. A major fault can identify a costly fault path while leaving its
backing category open. A high-value follow-up is correlating phase-scoped byte
and latency counters for the two file readers with page-fault and PSI series.
Treat a sequential hint or small read-ahead window as a measured experiment
with a fixed byte budget. Reserve broad warm I/O for an observed natural
loading phase with enough headroom. [RomFS read path](../games/totk/runtime/romfs.c), [Linux PSI](https://docs.kernel.org/accounting/psi.html), [pressure evidence](s23-device-validation.md#lookout-landing-cache-comparison).

### Memory pressure and residency

The 173.07 ms return-movement frame created zero pipelines. The extended
process in the settlement recorded 517,931 major faults and 9.90 seconds of
system full memory stalls over 12 sampled intervals. The fresh control
recorded 71,240 faults and 1.47 seconds of stalls over 12 intervals. The
extended route reached the settlement warmer and with different resident
terrain and lighting. These measurements justify testing residency and
pressure separately from first-use compilation. [Device observations](s23-device-validation.md#lookout-landing-cache-comparison).

Android LMKD uses system pressure and thrashing information. Linux PSI
reports time when a subset of tasks is stalled or all non-idle tasks are
stalled. Vulkan's optional memory-budget query gives implementation-dependent
per-heap estimates. It cannot predict an Android kill or account for every
shared page. Keep deduplicated allocation totals, committed and live image
bytes, reclaimable retired bytes, guest shmem, staging, recorder, pipeline
allocations, PSS, swap activity and PSI as separate series. Record whether
each source was readable. [AOSP LMKD](https://source.android.com/docs/core/perf/lmkd), [Linux PSI](https://docs.kernel.org/accounting/psi.html), [Vulkan memory budget](https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_memory_budget.html), [port memory experiments](transition-memory-research.md).

A smaller guest backing file has not established a smaller peak workload in
this port. Prioritize allocation or upload reductions with byte-equivalence
fixtures. A later trim can target completed, proven regenerable content
under existing ownership and fence rules. Count whole allocations released,
reallocations, upload bytes and later demand latency on a second traversal.
Unoccupied spans inside live Vulkan blocks remain committed, and texture
lookup age alone does not prove that content can be discarded.
[S23+ backing experiment](s23-device-validation.md#reclaiming-old-dma-pool-backing), [image allocation and retirement](../games/totk/android/gfx/vk_res.c), [guest memory tracking](../games/totk/runtime/guest_shmem.h).

### NVN work and synchronization

The project already has descriptor allocation batching. Favor a narrowly
measured reduction in recorder work, staging copies or temporary allocation
over a descriptor-model rewrite. Test reused descriptors, overlaps, sparse
ranges, command ordering and retirement before comparing CPU and GPU work.
Independent command pools can support multithreaded recording. More
workers can also contend with compiler and streaming threads. Descriptor
indexing or descriptor buffers change update and lifetime semantics and
require a compatibility study. [Khronos command-buffer usage sample](https://docs.vulkan.org/samples/latest/samples/performance/command_buffer_usage/README.html), [descriptor indexing guide](https://docs.vulkan.org/guide/latest/extensions/VK_EXT_descriptor_indexing.html), [recorder source](../games/totk/android/gfx/vk_record.c), [prior experiments](external-runtime-performance.md#experiments-in-order).

## Acceptance sequence

| Priority | Evidence while the phone is disconnected | Evidence once device access returns |
| --- | --- | --- |
| Frame stalls related to compilation | Replay recorded logs and attribute shader, driver and recorder time. Verify cache identity and data safety with host fixtures. | Repeat the aged route with the prior-visit cache and similar initial conditions. Record fresh and aged frame times and the occurrence of exact pipeline keys. |
| Pressure-driven slowdown and exits | Prove exact output and bound temporary bytes in candidate fixtures. Validate shared allocation identity, fenced retirement and counter definitions. | Repeat the #55 route through both warps, the chasm and the settlement. Record Android exit reason, PSI, major faults, PSS, thermal state and recovery after returning. |
| CPU and GPU work | Compare identical bounded fixtures with real operation or memory counts. | Tie CPU scheduling, GPU timing where trustworthy and compositor deadlines to the same frames. Keep game FPS and the observed 60 Hz or 120 Hz display mode separate. Extend beyond the recorded route to story progression through the ending. |

A desktop fixture can prove less work and correct output for that input.
Android memory policy, the pinned Turnip build and sustained temperature
need separate device measurements. The successful 19-minute 26-second
capture improves route coverage. Full playthrough, repeatability of the #55
mitigation and sustained frame pacing remain open. [Device record](s23-device-validation.md), [requirements checklist](upstream-issue-audit.md).
