# Image memory during the Akkala return warp

## What the current measurements show

In run 10021, the two last complete windows showed block span usage rising from 494.5 to 755.6 MiB and allocated blocks rising from 640 to 784 MiB. Dedicated allocations stayed at 79 MiB. Shared active, shared idle and retired counters explain about 76.7 MiB of the 261.1 MiB span delta. Their sampling boundaries differ, and some lifetime counters also include dedicated allocations. The remaining 184.4 MiB is an approximate reconciliation gap. The same windows report 205.4 MiB more texture uploads per window, 65 MiB more guest pool bytes and 21.7 MiB of write-back staging. Upload bytes describe traffic over a window. The process exited with foreground `LOW_MEMORY` during the return. Neither the old nor the new scene's share of the peak has been quantified. [S23+ validation](s23-device-validation.md#follow-up-on-the-return-warp-peak), [Run 10021](s23-device-validation.md#optimization-trials-after-the-source-comparison)

The current shared-image report counts the base allocations in `g_by_storage`. Each physical shared backing can serve several guest texture serials. Live private bases can be reached through `g_by_serial`. A dropped private image may be held by a write-back record. A shared root can own a native sibling, whose scene scratch and AA images have their own allocations. The same block allocator also handles quad index buffers, dummy images, post-processing, presentation and frame generation. A sum of private base and sibling bytes will therefore explain only the corresponding portion of the gap. [Image ownership and memory report](../games/totk/android/gfx/vk_res.c), [Draw and presentation allocations](../games/totk/android/gfx/vk_draw.c), [Post-processing allocations](../games/totk/android/gfx/vk_post.c), [Frame-generation allocations](../games/totk/android/gfx/vk_framegen.c)

## Memory sources to keep separate

| Measurement | What it can show |
| --- | --- |
| Renderer payload and Vulkan block commitments | Record used spans and actual emitted allocation sizes. Block commitments already contain the used spans, padding and holes. A free span reduces usage and can accommodate a later request. An empty block returned to Vulkan reduces commitments. [Backend allocator](../games/totk/android/gfx/vk_res.c) |
| Vulkan heap usage and budget | `VK_EXT_memory_budget` specifies estimated process usage and a dynamic guideline for when allocations may fail or slow down. A reviewed Turnip revision assigns its memory types to one heap, reads its tracked heap usage and derives budget from system memory. Verify the selected device's extension and driver identity before collecting it. [Khronos reference](https://docs.vulkan.org/refpages/latest/refpages/source/VkPhysicalDeviceMemoryBudgetPropertiesEXT.html), [Turnip heap implementation](https://github.com/GameNative/mesa-turnip/blob/c8bab41a1b67bdba56c45305f4e07f85c215c349/src/freedreno/vulkan/tu_device.cc#L2142-L2194) |
| Kernel and process samples | Track `MemAvailable`, RSS or PSS, swap, memory PSI and GPU bytes individually. Use `kernel + imported_mem` for the existing KGSL total when both exist. `gpumem_mapped` overlaps. Perfetto exposes `gpu_mem/gpu_mem_total` where the device provides it and an optional Vulkan allocator and bind tracer for a diagnostic run. Use interval deltas in cumulative PSI stall time for a short transition. [Sampler accounting](../tools/bench/README.md), [GPU tracing](https://perfetto.dev/docs/data-sources/gpu#gpu-memory), [Linux PSI](https://docs.kernel.org/accounting/psi.html#pressure-interface) |
| App exit records | Correlate package, PID and time with Android exit reason and system pressure. Android can report a memory kill as `REASON_SIGNALED` with `SIGKILL` on devices that lack explicit low-memory kill reporting. Treat that signal as ambiguous without supporting evidence. [ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo#REASON_LOW_MEMORY), [AOSP LMKD](https://source.android.com/docs/core/perf/lmkd) |

Adreno shares system memory with the CPU. App, driver and kernel counters can describe the same backing and belong on aligned tracks with separate scales. Use a clock marker on each trace, and preserve missing readings as unavailable. [Mesa architecture](https://docs.mesa3d.org/drivers/freedreno.html#hardware-architecture), [Sampler accounting](../tools/bench/README.md)

## Bounded experiments

1. **Close the allocation gap first.** Measure a cross-tabulation by lifetime, resource role and allocation kind. Use one backing identity for each base and each child. Count a shared root once, attribute in-flight private write-back orphans a single time, include native/scratch/AA children, and assign other allocator call sites their own roles. Report committed, occupied and free bytes per allocation class. Preserve separate gauges for upload traffic and write-back staging. At ordinary cadence, read cached counters. At the warp, collect bounded peaks and deltas every 10–30 frames alongside submissions and fences. Measure instrumentation overhead with the same flags disabled. An offline fixture can assert that two shared views, a detached writer, a retired sibling and a non-image allocation reconcile through allocate, fence completion and destroy. [Backend object and block accounting](../games/totk/android/gfx/nvn_vk.c), [Texture and write-back ownership](../games/totk/android/gfx/vk_res.c)
2. **Prove which old backing can leave before the new scene expands.** Compare a snapshot before the travel request, at the replacement peak and after the relevant fence completes. If old backing is queued for deletion and its ticket already completed, try reclaiming only signaled entries at an existing recording boundary before allocating another block. Compare bytes actually returned and reclaim time against the regular sweep. Keep host replay references, frozen descriptors and presentation uses in the retirement contract. Dolphin provides a useful example of unbinding views and deferring object cleanup to command-buffer completion. The Vulkan lifetime rule requires every submitted use through the image or its views to complete. A broad idle wait can bubble the pipeline and inflate transition latency. [Local retirement path](../games/totk/android/gfx/vk_res.c), [Dolphin texture destructor](https://github.com/dolphin-emu/dolphin/blob/5140482a6f0e59bec1fbe843163f280ed4a2f29c/Source/Core/VideoBackends/Vulkan/VKTexture.cpp#L42-L52), [Dolphin fence cleanup](https://github.com/dolphin-emu/dolphin/blob/5140482a6f0e59bec1fbe843163f280ed4a2f29c/Source/Core/VideoBackends/Vulkan/CommandBufferManager.cpp#L270-L305), [Vulkan object lifetime](https://docs.vulkan.org/refpages/latest/refpages/source/vkDestroyImage.html), [Khronos fence sample](https://docs.vulkan.org/samples/latest/samples/performance/wait_idle/README.html)
3. **Limit discretionary write-back bursts as a separate arm.** `vk_wb_record` can stage every settled record eligible at a seal. Each copy currently creates, allocates and maps its own coherent destination. Landing already has a byte and time budget. Test a launch-only cap on optional copy count per seal and live optional staging, with fair progress for an oversized eligible record. Keep the dirty stamp, pending record and source pin when an optional copy is deferred. Invalidation is a correctness dependency. Preserve its immediate staging and exact-fence path, pool lifetime validation, cancellation and native-to-base resolve. Watch `WB-only` bytes and oldest age alongside staging and allocation durations. A staging reduction can leave more source images pinned for longer. A coherent staging slab is a later experiment if allocation and map costs remain material. It would need per-range alignment and GPU fence plus CPU landing completion before reuse, including for cancelled copies and partial landings. [Settled write-back and sweep](../games/totk/android/gfx/vk_res.c), [Ordinary slot sealing](../games/totk/android/gfx/nvn_vk.c), [Copy alignment and regions](https://docs.vulkan.org/refpages/latest/refpages/source/vkCmdCopyImageToBuffer.html), [Vulkan memory coherency](https://docs.vulkan.org/spec/latest/chapters/memory.html#memory-device-hostaccess)
4. **Trial sibling reuse if the new census finds material overlap there.** Native content can be newer than the guest-sized base and require a resolve before a guest read. Prefer exact-compatible scratch whose contents are regenerated before the next read. Prove read-after-write and fence ownership across consecutive frames, old and new extents, GUI composition and frame-generation capture. An exact-object pool avoids the overlapping-allocation rules of bound Vulkan aliases. Generic deduplication by address would risk merging independent compression-format classes or mirrors with different ownership. [Sibling creation, authoritative resolve and format classes](../games/totk/android/gfx/vk_res.c), [Vulkan memory aliasing](https://docs.vulkan.org/spec/latest/chapters/resources.html#resources-memory-aliasing), [Vulkan synchronization](https://docs.vulkan.org/spec/latest/chapters/synchronization.html)

Heap budget is a pressure signal for optional work. Dolphin's image constructor combines budget-aware allocation with a caller-visible failure path. Reusing that policy here would require every gated caller to have a correctness-preserving deferral or fallback. Keep current block size and first-fit defaults for the first route comparisons. The smaller-block and packing arms already show how a more compact settled scene can still run into a larger transition peak. [Dolphin image allocation](https://github.com/dolphin-emu/dolphin/blob/5140482a6f0e59bec1fbe843163f280ed4a2f29c/Source/Core/VideoBackends/Vulkan/VKTexture.cpp#L82-L99), [S23+ allocator trials](s23-device-validation.md#optimization-trials-after-the-source-comparison)

## Acceptance on the S23+

Run the same aged Akkala → Iu'iqoi → Akkala route and movement, with isolated toggles. Match save, driver, app graphics, starting cache, brightness and starting thermal state. Mark both travel requests and first controllable frame at each arrival. Record peak block commitments and role/lifetime census, allocation and fence durations, write-back backlog and retained bytes, process and KGSL gauges, memory PSI, process exit reason, traversal time and 60/120 Hz behavior. Compare frame-time percentiles and longest freezes in each phase. Check the terrain, normals, flashes, main GUI and return to control. Compare repeated warm laps to distinguish a sustained reduction from background or route variance. A first device comparison has now measured the combined changes and reproduced the remaining memory exit after the return. Isolated toggles still need repeated laps to qualify a default change. [S23+ device results](s23-device-validation.md#return-warp-validation-after-the-optimization-goal), [Vulkan write-back fixtures](../games/totk/android/gfx/test_vkdraw.c)

## First host candidate

- `TOTK_VK_IMAGE_OWNERSHIP_TRACE=1` adds private mirror, private GPU-written, other private, private auxiliary, and shared auxiliary bytes to the periodic report. Shared bases use the existing counters. A Vulkan fixture verified live image size, alias handling and the transition out of the live report after release.
- Format-view upgrades now check shape before allocating an image or recording its initial layout transition. The host fixture forces an incompatible shape, checks that the original image and its revision survive, then exercises a successful format upgrade.
- Write-back statistics skip the search for duplicate records when the image has just one pending pin. The existing duplicate check still applies to records that may share an image.
- The image allocator now trims and merges free spans in place whenever neighboring spans permit it. A fragmented-block fixture ran 512 allocation/free cycles. The beta moved 270,336 bytes of span metadata and the candidate moved zero, with the same offsets and final coalescing. This measures bookkeeping work on the host.

Peak memory, frame timing and the #55 outcome in this candidate still need a matched phone run. [Vulkan image code](../games/totk/android/gfx/vk_res.c), [Allocator fixture](../tests/test_vk_image_memory.py)

Development APK 10026 built, passed its content audit, and verified APK signatures v1, v2 and v3.
The span fixture passed with GCC and Clang. The ownership, replacement and idle-expiry fixtures
passed 25 checks each in both direct and two-worker configurations. The live write-back budget
fixture passed 219 checks with each empty-block reclamation setting. The active goal continues
with host experiments until the owner makes the S23+ available.

## Bounded write-back experiment

Build 10027 adds opt-in admission limits on background copies per submission and on staging
bytes already in use. The limit compares against the device's required allocation size before
allocating and binding the copy buffer. A deferred record keeps its freshness stamp and source
pin, and an oversized copy can progress on empty staging. Explicit reads keep their immediate
copy and fence path. CPU writes still cancel stale pending copies. [Vulkan memory requirements](https://docs.vulkan.org/refpages/latest/refpages/source/VkMemoryRequirements.html), [Implementation](../games/totk/android/gfx/vk_res.c)

| Host Vulkan arm | Copies and live staging on the first eligible submission |
| --- | --- |
| Unlimited | 3 copies, 3.50 MiB |
| One copy attempt per submission | 1 copy, 0.75 MiB |
| 1 MiB staging admission limit | 1 copy, 0.75 MiB |
| Both limits | 1 copy, 0.75 MiB |

The four arms passed 93 checks in direct mode and 93 with two recorder workers. Each budgeted
arm started an explicit invalidate while a background allocation still occupied staging and
the requested copy remained deferred. All three GPU outputs landed byte-for-byte, including a
2 MiB oversized copy. A fourth record cancelled on a CPU overwrite kept the newer CPU value.
The count-only arm still reached 3.50 MiB at a later admission. In both byte-limited arms the
maximum at background admission was the single 2 MiB oversized copy. The fixture tracks
staging and guest data on the host. [Live Vulkan fixture](../games/totk/android/gfx/test_vkdraw.c)

The existing invalidation and partial-landing fixtures passed another 534 checks. APK 10027
built and passed signature and content verification. Both experimental limits are disabled by
default. Compare each limit independently on the S23+ and record WB-only source memory along
with staging and stalls, since deferring copies can keep images pinned longer.

## Lower write-back recording overhead

Build 10028 stores the first four records of an explicit read-back in local storage. A larger
request counts the remaining matches and allocates a single array. The previous code issued
one realloc request per matching record. The recorder still publishes the ranges before
removing their lookup rows and clears them before releasing the array. The fixture exercised
batches of 1, 4, 5 and 64 textures. They made 0, 0, 1 and 1 heap allocations respectively.
The recorded bytes matched for every texture and neighboring pending records remained
reachable and intact until their own read-backs. [Write-back implementation](../games/totk/android/gfx/vk_res.c)

The same build records up to 16 independent image regions in one Vulkan command. An array
texture with seven layers and three mips used two commands for its 21 regions. The fixture
compared all mip and layer bytes, including the smaller tail batch. Copy offset, producer
ordering and CPU landing rules stay the same. [Vulkan copy regions](https://docs.vulkan.org/refpages/latest/refpages/source/vkCmdCopyImageToBuffer.html), [Live Vulkan fixture](../games/totk/android/gfx/test_vkdraw.c)

The new batch fixtures passed 266 checks on the host RTX 3080 Ti, including both direct mode
and two recorder workers. Existing write-back, exact-range preflight, optional admission,
and partial-landing fixtures passed 982 checks. APK 10028 passed signatures and the content
audit. These measurements cover recording work and read-back correctness on the host.

## Peak measurements and allocation recovery

Build 10029 records interval highs for the combined block and standalone commitments and
for the occupied spans plus standalone allocations. It saves the block and standalone
bytes together at the commitment peak. The running occupied counter also removes the
block traversal from the ordinary memory sample when detailed fragmentation is disabled.
`TOTK_VK_IMAGE_PEAK_LOG=1` emits a line at allocation time when commitments set a new
interval high at least 16 MiB above the last line or interval start. That line can survive
a process kill before the next periodic report. Write-back separately records peak staging,
including explicit copies, even when all staging drains before sampling.
[Allocator implementation](../games/totk/android/gfx/vk_res.c)

Metadata growth now happens before accepting a suballocation. Every block reserves span
space for all its live allocations, so a release can return bytes without asking the host
heap for more memory. At most two additional slots are required by a single carve.
Block descriptors grow geometrically and their reservation precedes a new Vulkan allocation.
This can retain extra host metadata, since each unused reserved span slot is 16 bytes.
The failure fixture injected allocation errors into both new-block metadata reservations,
an existing block's span growth, and Vulkan allocation. It verified live handles and offsets
and released fragmented spans while the next host allocation was still forced to fail.
[Allocation failure fixture](../tests/test_vk_image_memory.py)

The GCC and Clang fixtures captured 49 MiB committed and a separate 32 MiB occupied peak
after both had subsided. Live Vulkan ran 940 checks, covering image ownership, replacement,
idle expiry, write-back batches, admission and the cooperative budget with both block-retention
policies. The admission test ended with zero live staging and reported 3.50 MiB peak in the
unlimited arm versus 2 MiB in the byte-limited arm, including the oversized record. The
Android APK passed signatures and the content audit. The effect on #55 and frame times
awaits the matched route on the S23+.

## Reuse after a completed retirement

The normal sweep handles retirements after a guest submission. A fence can complete
after that sweep and before the next texture needs backing. With
`TOTK_VK_IMAGE_RECLAIM_BEFORE_GROW=1`, a suballocated texture that finds no fitting span
checks at most 64 retirement records and destroys at most eight block-backed images
whose retirement ticket has already completed. It then retries the same allocation
policy. It uses the ordinary image destroy path, checks published completions without
waiting for a fence, and leaves other retirement and write-back work to its normal
schedule. The peak duration counter includes the driver's object destruction. The
opt-in remains off by default for the S23+ comparison.
[Vulkan image lifetime](https://docs.vulkan.org/refpages/latest/refpages/source/vkDestroyImage.html),
[Renderer implementation](../games/totk/android/gfx/vk_res.c)

The live Vulkan fixture fills two 32 MiB blocks with four 12 MiB textures. Both arms
leave a retired texture in use before its submission completes. The next 12 MiB
texture would reserve a third block in the control. The enabled arm reuses the completed
image's span, leaving commitment at **64 MiB instead of 96 MiB**. A separate retirement
for an unsubmitted ticket stays queued. Vulkan readbacks verify the old texture's data
before completion and the surviving and replacement textures after the reuse.
[Vulkan fixture](../games/totk/android/gfx/test_vk.c)

The A/B passed all 60 checks on the host RTX 3080 Ti in direct and two-worker modes.
The largest observed reclaim in those two enabled fixture runs was 1.965 µs. Another
992 checks passed with the experiment enabled, covering ownership, replacement, expiry,
GPU texel reads, and settled write-back. Signed development APK 10030 passed content
and signature verification. On the S23+, compare the default and enabled arms of the
same build with identical route and cache, and correlate reuse counts and peak reclaim
time with commitments, frame times and exit reasons.

## Reuse of space in staging buffers

The normal allocator fast path keeps appending to the latest buffer. When it runs out
of room, build 10031 checks the earlier buffers' remaining aligned space as well as
empty buffers before creating another Vulkan buffer and allocation. Each range remains
owned by its existing submission or snapshot fence. Reordering the allocator's buffer
records leaves the Vulkan handles, mapped addresses and offsets intact.
[Khronos memory allocation guide](https://docs.vulkan.org/guide/latest/memory_allocation.html),
[Arena allocator](../games/totk/android/gfx/nvn_vk.c)

The controlled Vulkan sequence uses four differently sized, independently aligned inputs.
The older policy reserves three 8 MiB slot buffers for the sequence. Reusing the remaining
space in the first two buffers reduces that to two and saves **8 MiB** in the fixture.
The snapshot variant goes from three 1 MiB buffers to two. Both variants verify byte
preservation through the frozen-data lookup and GPU copies. They cover alignment padding,
exact fit and moving the current allocator entry back and forth between live buffers.
[Vulkan fixture](../games/totk/android/gfx/test_vk.c)

The four host A/B runs passed 128 checks. Existing arena reuse, retention, texture and
texel checks passed in direct and two-worker modes. The external replay and prepared
frame-generation suites also passed in both modes, including slot ownership under ring
pressure. APK 10031 passed content and signature verification.

Use the build default for the first device route, and `TOTK_VK_OFF=arenatails` for a
control when the staging counters show meaningful reuse. Compare active, retained and
peak staging alongside the allocator totals and frame times. The host byte savings
describe this allocation sequence.

## Less work when releasing temporary buffers

When a slot or snapshot arena shrank, its buffer destruction scanned the whole texture
table and the general retirement queue for Vulkan buffer views. Build 10032 keeps a
list of live texel-buffer views and separate retirement records for those views. The
temporary-buffer path checks those lists. The existing arena lifetime condition still
controls when views that refer to its buffer can be destroyed. Normal view replacement
and texture finalization still defer destruction to the associated submission ticket.
Ordinary texture objects no longer carry the four view fields, saving 32 bytes per
object on the 64-bit build before allocator rounding.
[Khronos buffer-view lifetime](https://docs.vulkan.org/refpages/latest/refpages/source/vkDestroyBufferView.html),
[Renderer implementation](../games/totk/android/gfx/vk_res.c)

The live fixture creates 4,096 ordinary texture objects and four real Vulkan buffer
views over two independent buffers. Releasing one buffer examines four view records.
The old loop would visit 8,192 texture slots before checking deferred records. The fixture
checks that the matching live and deferred views are removed, the views over the other
buffer survive, and the cleared texture gets a new view that can be invalidated again.
The ordinary fence sweep then retires the remaining deferred view.
[Vulkan fixture](../games/totk/android/gfx/test_vk.c)

The release fixture and the arena, image-retirement, texel, write-back and replay-pin
regressions passed 3,522 checks in direct and two-worker modes. The 10032 development
APK passed content and signature verification. Capture the release counters along
with slot-reuse or transition stalls on the device to establish the gameplay effect.

## Keep a warm staging buffer and measure the burst

Build 10033 retains an existing 8 MiB buffer when reopening a retired slot under the
low-memory profile's 8 MiB staging cap. It trims first at this cap because at most one
buffer will fit. The earlier order compacted every buffer in a slot that held more
than four, including a buffer that could satisfy the next small request. The next
request then had to create, allocate, bind and map a replacement. The available
buffer is retained after the existing fence and recording ownership rules allow reuse.
[Arena implementation](../games/totk/android/gfx/nvn_vk.c)

Staging and snapshot totals now update when Vulkan memory is allocated or released.
The peak report uses each buffer's requested Vulkan allocation size, including the
driver's required padding. It records separate class peaks and the maximum of the
two current totals at the same instant. A larger update can be logged before a
periodic report with `TOTK_VK_ARENA_PEAK_LOG=1`. These bytes belong to the renderer's
buffer allocator, so Android residency and traffic remain separate.
[Khronos memory requirements](https://docs.vulkan.org/refpages/latest/refpages/source/VkMemoryRequirements.html)

The live fixture allocates an 8 MiB buffer and four 9 MiB buffers. At slot reuse it
reports a 44 MiB peak and 8 MiB still allocated. The next small request receives the
original buffer and the Vulkan allocation counter stays at five. A later snapshot
changes the snapshot maximum while the combined peak stays at 44 MiB. Sampling
starts the next interval at the live allocation totals.
[Vulkan fixture](../games/totk/android/gfx/test_vk.c)

The fixtures and regression suites passed 3,174 checks across direct mode and two
recorder workers, including replay pins and write-back under the 8 MiB cap. The
10033 development APK passed its content and signature checks. On the S23+, use the
arena and image measurements together during travel to separate staging growth from
texture-memory growth. Keep the two allocators' independent peaks on separate tracks.

## Route analysis before the next device run

`tools/bench/route_report.py` accepts one runtime log and the corresponding
`android_memory_capture.py` directory. It reports renderer memory by window and
keeps allocation events with submission serials when a run ends before the next
periodic sample. Optional phase bounds are supplied independently in rendered
frames and elapsed capture seconds. Windows that straddle a phase boundary remain
visible in the run and are excluded from that phase's window results. New captures
record a host UNIX-time anchor for timestamping route markers.
[Benchmark usage](../tools/bench/README.md)

The capture lane keeps framework render-rate samples, system memory and pressure,
and Android application exit records. It only attributes exits newly observed for
a recorded PID when both exit queries succeeded. System PSI deltas cover adjacent,
readable samples while the app was present. Vulkan peaks, upload traffic, Android
PSS/RSS and system pressure retain their own units and boundaries.
[Android exit records](https://developer.android.com/reference/android/app/ApplicationExitInfo),
[Linux pressure counters](https://docs.kernel.org/accounting/psi.html)

Reprocessing 10021 gives 155 live 120 Hz framework samples and a new
foreground `LOW_MEMORY` exit. The last two complete windows end at frames 20,700
and 21,000. Their p95 frame time is 40.11 and 60.70 ms, p99 is 74.43 and
159.29 ms, and maximum is 78.97 and 423.16 ms. The later window adds 261.086 MiB
of occupied image spans, about 65 MiB in the rounded guest-pool figures and
21.656 MiB of staged write-back. Texture upload traffic grows from 19.2 to 225.3 MiB
per window. The last window records 6.5 ms of pipeline construction across 33
pipelines. These are measurements around the exit; causal attribution still needs
a matched route. The same analyzer also recovered the 10018 foreground memory
exit and the absence of a new captured exit record for 10017.

## Separate images across guest pool lifetimes

Before build 10034, finalizing a physical guest pool left still-referenced shared
images discoverable by storage address. A new pool could then receive old pixels
when it registered the same address and texture layout. The old image could also
linger for the normal 600-submission reuse interval once its final reference left.

The renderer now detaches every overlapping shared image from the storage lookup
at pool finalization. Existing serials and in-flight read-backs keep their references.
When those owners leave, the image goes directly to the existing fenced retirement
queue. Detached images cannot create new write-back work for the reused address.
The route analyzer includes counts for detached images and base bytes queued for
retirement. The counters describe lifetime events. A block is returned once all its
occupants have left and the allocator's empty-block policy allows it.
[Renderer lifetime code](../games/totk/android/gfx/vk_res.c),
[Khronos image destruction](https://docs.vulkan.org/refpages/latest/refpages/source/vkDestroyImage.html)

The live Vulkan fixture runs physical pool finalization and registration at the same
guest address while two old serials still exist. GPU readbacks preserve the old
pixels, the replacement's pixels and an adjacent pool's pixels independently.
Dropping the final old serial queues 12 MiB of occupied image spans. After the
retirement fence, the test returns one 16 MiB block in the ordinary sweep.
[Vulkan pool lifetime fixture](../games/totk/android/gfx/test_vk.c)

A second fixture gates a real GPU read-back, detaches its shared image and drops its
last texture serial. The image remains alive until the staging ticket completes.
The detached serial cannot re-arm the cancelled write-back. All staging and image
spans retire without a store to the guest destination. The two fixtures and the
pool-finalize, texture and write-back regressions passed 1,194 checks on the host.
Signed APK 10034 passed content and signature verification.
[Gated write-back fixture](../games/totk/android/gfx/test_vkdraw.c)

## Resolve texel views against current pool mappings

Build 10035 validates direct texel-buffer view cache hits against the pool mapping
generation. After a remap, the same texture serial and descriptor resolve the
backing buffer and byte offset again. A still-valid view keeps its handle. A changed
or missing backing retires the old view. Views bound to frame-lag snapshots are
eligible only through that mode's existing snapshot path.

For physical pool finalization, the registry removes the old owner and restores
the guest pages while holding the pool lock. After that lock is released, the
finalizer clears live and queued views of the old Vulkan buffer before destroying
it. The HLE path already holds recording ownership and waits for submitted work
to complete. View cleanup uses the small view lists introduced in 10032.
[Pool finalization](../games/totk/android/gfx/nvn_vk.c),
[Vulkan buffer-view lifetime](https://docs.vulkan.org/refpages/latest/refpages/source/vkDestroyBufferView.html)

The Vulkan fixture remaps an alias between two resident donors at different
offsets. It verifies the changed view and preserves the handle of an unrelated
view. Finalization destroys both a cached and a queued view of the retired donor.
A query returns no direct view until the same address is registered again, when
it creates one for the replacement buffer. The live remap and pool, arena and
write-back regressions passed 1,364 checks in direct and two-worker modes.
Development APK 10035 passed content and signature verification. The effect of
the change on the Akkala transition awaits device validation.
[Vulkan fixture](../games/totk/android/gfx/test_vk.c)

## Skip write-back work until there is something to land

Build 10036 tracks how many background write-back records have staging and a
submission ticket. The landing sweep can skip the queue walk and timing updates
when this count is zero, even if many renders are waiting for their quiet period.
Copy admission still evaluates pending work before sealing the slot. Copied
records and cancelled copies retain their existing fence, freshness and landing
budget checks. Moving a staged record to an explicit read-back updates the
background count while the explicit path keeps the record's ownership.
[Write-back queue](../games/totk/android/gfx/vk_res.c)

The quick-reject address range extends when new work is recorded. Removing an
interior record leaves the current bounds valid. Shrinking or removing an endpoint
marks the bounds for recomputation. Explicit reads keep their detached ranges
visible in both the quick check and the exact preflight until landing completes.
The route analyzer reads the skipped-sweep and bounds counters at their tagged
frame.
[Route analysis](../tools/bench/route_report.py)

In the Vulkan fixture, 66 pending records remain unstaged for 64 idle submissions
and a final sweep. All 65 landing walks and all hull rebuilds are skipped. The
prior code would visit those records 12,870 times across its landing, aging
and bound scans. The next explicit read consumes 64 middle records, preserving
both neighbors and the current bounds. Each endpoint read then rebuilds the
bounds once, with byte-for-byte read-back checks. The broader live regressions
passed 11,146 checks in direct and two-worker modes. The 10036 APK passed the
content and signature checks.
[Write-back fixture](../games/totk/android/gfx/test_vkdraw.c)

## Skip quiet write-back scans at submission

Build 10037 remembers the first pending write-back deadline after a queue scan.
New GPU producer records request a fresh scan. The CPU freshness check resumes
when a write claims a watch, the dirty-page generation changes, or a tracked
range is added or removed. The recorder samples these values before scanning,
so a change during the scan also prompts another check. Due entries retain
their producer-fence and staging-budget checks. Explicit read-back continues to
check the selected texture's freshness before copying or landing.
[Recorder](../games/totk/android/gfx/vk_res.c),
[Dirty tracking](../games/totk/third_party/d2r_gfx/gfx/nvn/nvn_dirty.c)

With 66 pending textures, the host fixture skipped all 64 idle seal scans and
avoided 4,224 record visits per configuration. The full-scan control skipped
zero. Both landed the selected regions byte-for-byte and preserved unselected
neighbors. A separate fixture first reused the quiet hint, then wrote into a
watched texture before its deadline. The next seal cancelled the stale record
without staging a copy or overwriting CPU data. Direct and two-worker runs
passed 21,592 checks across the write-back and pool fixtures. The route parser
preserves the new counter at its reported frame. The APK passed content and
signature checks with the existing development certificate. The amount of
CPU work saved in gameplay depends on how often the queue and dirty state
change before the deadline. Compare `quiet_seals_skipped`, the recorder
timings and the frame-time distribution on the S23+.
[Write-back fixture](../games/totk/android/gfx/test_vkdraw.c),
[Route parser fixture](../tests/test_android_route_report.py)

## Reclaim completed dedicated images before replacement

Build 10038 extends the existing opt-in `TOTK_VK_IMAGE_RECLAIM_BEFORE_GROW=1`
experiment to textures with allocations larger than 16 MiB. Before allocating
one, the renderer checks up to 64 queued retirements and destroys at most eight
eligible dedicated images. It stops early when it has returned enough bytes
to cover the new allocation. A fence that is incomplete or still unsubmitted
leaves the image queued for the normal sweep. The check never blocks on a fence.
[Vulkan image lifetime](https://docs.vulkan.org/refpages/latest/refpages/source/vkDestroyImage.html),
[Renderer allocator](../games/totk/android/gfx/vk_res.c)

The host fixture kept a completed 24 MiB image queued and retired a second
24 MiB image on an unsubmitted ticket. The control reached 120 MiB of dedicated
allocations when creating a replacement. The enabled arm returned the completed
24 MiB to the driver before the new request and peaked at 96 MiB. The second
image stayed queued. Read-backs verified the old use before retirement, a surviving
image and the replacement. The existing block-reuse arm still came in at
64 MiB with the switch enabled and 96 MiB with it disabled. The Vulkan regressions
passed 894 checks in direct and two-worker modes. Development APK 10038 passed
content and signature verification.
[Vulkan fixture](../games/totk/android/gfx/test_vk.c)

The detailed memory report now shows dedicated retirement bytes and ready bytes
for both kinds of retirement. Ready span bytes denote reusable space within a
block. The reclaim report records dedicated attempts and bytes returned to the
driver. Use these counters with the interval allocation peak and reclaim timings
to judge whether the experiment applies to the Akkala return. The previous
10021 trace sampled 79 MiB of dedicated allocations in each of its final two
windows. It cannot establish how much temporary overlap occurred between
samples. The experiment is off by default pending the S23+ route comparison.
[Route parser fixture](../tests/test_android_route_report.py),
[Prior device measurements](s23-device-validation.md#follow-up-on-the-return-warp-peak)

## Reduce texture upload setup during streaming

Run 10021 recorded 1,605 uploads totaling 225.3 MiB and 291.3 ms of upload
caller wall time in the last complete window. That time is spread over 300
frames. Build 10039 keeps up to 16 copy regions in local storage. Small uploads
below the deswizzle threshold go directly through the serial decode. Larger
arrays still get a buffer-to-image command covering all their regions.
[10021 capture](s23-device-validation.md#follow-up-on-the-return-warp-peak),
[Renderer upload](../games/totk/android/gfx/vk_res.c)

For the first block-linear upload into a new image, the renderer keeps the
initial layout transition and the post-copy barrier. Host writes to its staging
span are visible at queue submission, so the extra barrier before that copy can
be omitted. Reuploads and direct copies from pitched guest memory retain the
entry barrier. The two changes can be switched off independently.
[Khronos synchronization examples](https://docs.vulkan.org/guide/latest/synchronization_examples.html#uploading-data-to-an-image)

With six uploads in each arm, temporary copy-region allocations fell from four
to two, and the renderer skipped the extra barrier on the two new block-linear
images. Both arms verified GPU read-back after initial upload and reupload for
every mip and layer. Khronos synchronization validation reported no errors
in this fixture. Direct and two-worker runs plus the deswizzle suite passed 30,377
checks. These results measure the eliminated operations and validate the
texture data on the host. The `[upload-prep]` counters and upload wall time
will show how often those paths run and how much time they take on the phone.
[Vulkan fixture](../games/totk/android/gfx/test_vk.c),
[Route parser fixture](../tests/test_android_route_report.py)

In a separate test that repeatedly overwrote eight already resident textures,
four matched runs per arm alternated their order. Median CPU time per upload was
52.8 µs with the control and 52.2 µs with the candidate for sparse writes,
and 40.8 µs and 40.7 µs for full writes. The variation between runs was larger
than those differences. This benchmark primarily exercises reuploads. The
streaming route remains the test of first-upload pacing. APK 10039 passed
the content, checksum and signature checks.

## Reuse texture layout calculations

The fork already implements the original driver’s compact layout for the
320 × 320 terrain textures investigated in nxnative #183. Its earlier trial
of nxnative’s faster copy loop was neutral in Thor gameplay and was reverted.
Build 10040 targets repeated metadata work around the existing copy loop.
The deswizzler used to calculate the whole texture’s layout three times per
subresource, once each for layer size, mip offset and tile dimensions. It now
uses one layout for all three. Write-back reuses the texture record’s existing
layout and keeps the same mip bounds through the guest ownership check and
copy, including when it writes several layers of one mip.
[nxnative #183](https://github.com/seedds/nxnative/issues/183),
[Prior Thor results](translation-research.md#5-results-log),
[Texture layout and copy](../games/totk/third_party/d2r_gfx/gfx/tex/nvn_deswizzle.c)

The host benchmark compared the unchanged baseline and the candidate at
`-O2`. It checked identical geometry for 59 mip levels across eight layouts
and alternated the order across nine pairs of 944,000 queries per arm.
Median CPU time fell from 164.0 to 76.8 ns per query with GCC and from
148.6 to 64.7 ns with Clang. This measures layout calculation alone. The test
suites passed 1,830,475 checks across texel bounds, the parallel uploader and
live Vulkan fixtures. Original-driver goldens independently checked the
mip and layer mapping. APK 10040 passed content and signature verification.
[Driver goldens](../games/totk/tests/texture_auto_layout/probe.c)

## Recover a texture allocation after a Vulkan memory error

Build 10041 checks the existing retirement queue when Vulkan returns a host
or device memory error for a texture allocation. It considers up to 64
entries and frees at most eight images, using a nonblocking check of each
image’s retirement ticket. If it frees anything, it tries the allocation
once more. A block request can fit in the space reclaimed and avoid the
second driver allocation altogether. The new diagnostics count memory
errors and how many of the requests recovered in the renderer.
[Vulkan allocation errors](https://docs.vulkan.org/refpages/latest/refpages/source/vkAllocateMemory.html),
[Image allocator](../games/totk/android/gfx/vk_res.c)

The host fixture injects a device-memory error on block growth and a
host-memory error on a dedicated request. Both proceed after retiring a
completed image. The block arm reuses an existing span at 64 MiB committed,
and the dedicated arm retries after releasing 24 MiB, staying at 96 MiB.
A second injected error with only future retirements returns promptly.
Vulkan read-backs verified the surviving and replacement images. Direct
and two-worker regressions passed 708 checks, and both injection fixtures
passed separately under Khronos synchronization validation.
[Fault injection and read-back](../games/totk/android/gfx/test_vk.c)

The 10021 route ended with an Android foreground `LOW_MEMORY` exit. App-side
recovery can run only when the allocation call returns an error to the app.
The next matched route can correlate the new counter, allocator peaks and
package exit reasons to tell whether that happened. APK 10041 passed content,
checksum and signature verification.
[Prior device capture](s23-device-validation.md#follow-up-on-the-return-warp-peak),
[AOSP low memory killer](https://source.android.com/docs/core/perf/lmkd)

## Release idle recorder pages before freeing an entire slab

During the last complete 10021 window, recorder packet and descriptor
mappings reached 99 MiB, up from 39 MiB before the transition. Referenced
block capacity reached 64.3 MiB. Those are allocator capacities. The
unreferenced difference can include untouched pages and alignment gaps.
In the final 25 seconds sampled before the app vanished, Android’s
`MemAvailable` moved between about 621 and 732 MiB. The experiment
uses the renderer’s own retention budget as its trigger. This avoids
selecting a system-wide threshold from one noisy route.
[Previous device capture](s23-device-validation.md#follow-up-on-the-return-warp-peak),
[Kernel memory counters](https://docs.kernel.org/filesystems/proc.html)

Build 10042 adds an opt-in `TOTK_VK_REC_DISCARD_FREE=1` arm. At the existing
retired-slot trim, it advises whole pages belonging only to blocks that have
been unused for at least eight generations of that slot. The allocator
keeps headers and boundary pages, and can reuse the same addresses. Each
trim attempts up to 16 advisories for each slab type. An already discarded
block is skipped until it has been reused and freed again. Entirely empty
slabs still use the existing unmap. Diagnostics track advised bytes, while
the device capture measures RSS independently.
[Linux `MADV_DONTNEED`](https://man7.org/linux/man-pages/man2/madvise.2.html),
[Recorder allocator](../games/totk/android/gfx/vk_record.c)

On the host, the kernel’s `mincore` reported 772 KiB before trimming.
The enabled arm fell to 520 KiB and the control stayed at 772 KiB.
The test verified the age threshold, both adjacent payloads, reuse of
the same address and normal slab unmap. The enabled and control arms
also passed under AddressSanitizer and UndefinedBehaviorSanitizer.
The live recorder stress
fixtures passed 9,734 checks with two workers and both command-buffer
modes. APK 10042 passed content, checksum and signature verification.
The experiment remains opt-in for the S23+ comparison.
[Recorder fixture](../games/totk/android/gfx/test_vkdraw.c)

## Pack the recorder descriptor inputs

Build 10043 stores the buffer, image and texel-view payloads in a union.
Each descriptor carries only one of those types. The lag guard’s buffer
range remains in separate storage so it is available with a texel view
or an ordinary buffer binding. Each Vulkan update-template entry still
specifies its descriptor type, offset and stride. The worker applies
the image layout only on image descriptors.
[Vulkan update template entries](https://docs.vulkan.org/refpages/latest/refpages/source/VkDescriptorUpdateTemplateEntry.html),
[Recorder data layout](../games/totk/android/gfx/vk_record.h)

The descriptor stride fell from 96 to 64 bytes. The Android ARM64 debug
information confirmed the 64-byte layout. A live Vulkan fixture updated
two uniform-buffer entries, an image-sampler entry and two distinct
texel-buffer entries using one template. Khronos validation reported
no errors on this fixture. The existing recorder stress route passed
9,096 checks across both command-buffer modes. That route retained 8 MiB
of descriptor slabs in both builds because the slab allocator rounds up
its reservations. The smaller records reduce bytes copied and hashed.
Their effect on resident memory and frame pacing in Akkala remains to
be measured.
[Mixed descriptor fixture](../games/totk/android/gfx/test_vk.c),
[Recorder stress route](../games/totk/android/gfx/test_vkdraw.c)

The full recorder suite passed its byte comparisons across worker
modes and pass boundaries. The lag-guard test initially failed in both
the candidate and a fresh build of the published revision `c686e4c`.
The copy registers its source and first-time destination. The fixture
now expects two first-copy rearms and one after the destination is
already protected. It retains its exact checks for matching pixels
and wait behavior. The corrected lag-guard and lag-uniform runs passed
2,134 checks with zero, two and three workers. APK 10043 passed
content, checksum and signature verification.

## Fix descriptor arrays in the direct renderer

The direct renderer used one 56-byte struct per resolved descriptor.
It passed the address of a selected member to `vkUpdateDescriptorSets`
with the whole array count. Vulkan steps through those pointers in
24-byte buffer or image entries and 8-byte texel views. A host probe
using the published struct layout found that the second element of
each of the three types read the wrong data.
[Vulkan descriptor writes](https://docs.vulkan.org/refpages/latest/refpages/source/VkWriteDescriptorSet.html)

Build 10044 collects each binding array in contiguous typed storage.
Single entries point directly into the selection scratch. The ordinary
direct update, replay with a substituted canvas and frame generation’s
owned terminal capture all use the same packing. Replay submits its
descriptor writes in one update. ARM64 debug information confirms
that the selection scratch went from 56 to 24 bytes per descriptor.
The worker path continues to use the update templates and 64-byte inputs
introduced in build 10043. The guest array selection still repeats the
first texture for reflected multi-element bindings.
[Implementation](../games/totk/android/gfx/vk_draw.c)

The live host Vulkan fixture checked two different offsets, sampled
image views and texel buffer views through both descriptor paths.
All nine checks passed with Khronos validation active and no validation
errors. The adaptive and interpolated terminal walker fixtures passed
989 and 1,010 checks, respectively, using the real native UI replay on
the host. For frame generation they substitute the host’s unavailable
Adreno motion estimation. The first recorder-suite launch missed the
fixture shader directory. With the generated fixtures loaded, all 390
runs completed with 45,306 checks and 351 byte comparisons of rendered
pixels and related counters. The APK passed content, checksum and
signature verification. The game’s frame times and the #55 memory peak
still require the matched S23+ route.
[Vulkan fixture](../games/totk/android/gfx/test_vk.c)

## Recover textures after a temporary memory shortage

The existing allocator can immediately reclaim completed work and retry
when a device allocation returns a memory error. If image realization
still failed, the texture serial remained registered without an image.
Subsequent lookups returned the fallback for that serial. The host
fixture reproduced this after the injected error stopped.
[Vulkan memory allocation](https://docs.vulkan.org/refpages/latest/refpages/source/vkAllocateMemory.html)

Build 10045 allows one delayed retry of a base texture after a host or
device memory shortage during image creation, allocation or binding.
The first later lookup at least eight submissions after the failure can
attempt it. Each submission admits up to four of these retries. A failed
binding destroys the unused image and releases its allocated span before
the retry. Guest-pool finalization cancels pending retries over that
pool. The retry uses the ordinary texture lookup and upload path.
[Vulkan image creation](https://docs.vulkan.org/refpages/latest/refpages/source/vkCreateImage.html),
[Vulkan image binding](https://docs.vulkan.org/refpages/latest/refpages/source/vkBindImageMemory.html),
[Implementation](../games/totk/android/gfx/vk_res.c)

The fixtures injected each failure in isolation and separately kept
memory pressure persistent. Each temporary failure case recovered all
five eligible textures through the texture ID cache with exact pixel
readback, including content updated while waiting. The persistent case
made five delayed attempts, and none repeated. A finalized pool and a
texture with a non-memory error remained unavailable. The eight runs in
direct and two-worker mode passed 806 checks with Khronos validation
active. Related image, pool and descriptor fixtures passed 304 checks.
The full recorder suite logged 45,306 passing checks and matched 351
combinations of pixels and counters byte for byte. APK 10045 passed the
content, checksum and signature audit.
[Vulkan fixture](../games/totk/android/gfx/test_vk.c)

The captured #55 failure was a foreground Android process kill. This
recovery runs when Vulkan returns a memory error to the live game.
During the matched S23+ route, correlate the new `[image-realization-retry]`
counter with frame time, image commitments and the system exit record.

## Reupload changed mip levels and layers

The 10021 route recorded 5,671 reuploads by the last complete window.
A single dirty-page hit previously sent every mip level and array layer
through deswizzling and staging. PCSX2 and Dolphin each update portions
of cached textures when their own memory metadata identifies a region.
This port has page stamps and NVN block-linear offsets, which are enough
to select whole mip/layer subresources without guessing which texels
changed inside a guest page.
[PCSX2 texture cache](https://github.com/PCSX2/pcsx2/blob/master/pcsx2/GS/Renderers/HW/GSTextureCache.cpp),
[Dolphin texture cache](https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/VideoCommon/TextureCacheBase.cpp),
[Vulkan copy regions](https://docs.vulkan.org/refpages/latest/refpages/source/VkBufferImageCopy.html)

Build 10046 adds the startup-only `TOTK_VK_PARTIAL_TEX_UPLOAD=1` experiment.
It stages a compact list of the affected subresources for previously
uploaded, CPU-mirrored block-linear textures. A dirty page shared by
two subresources selects both. The Vulkan producer journal rules out
pending or intervening writes to the original guest buffer, including
write-back. A first upload, unsupported layout, physical or virtual
pool, or incomplete write watch preserves full staging.
The upload still uses its normal ordering barriers for reuploads.
[Upload path](../games/totk/android/gfx/vk_res.c),
[Producer journal](../games/totk/android/gfx/nvn_vk.c)

| Test arm for one edited mip/layer | Staged bytes |
| --- | ---: |
| Full upload, or partial enabled with untracked storage | 2,064,384 |
| Partial enabled with native 4 KiB pages | 16,384 |
| Partial enabled with the port’s 64 KiB dirty units | 81,920 |
| BC3 with 64 KiB dirty units | 81,920 |

The fixtures read back each of the 18 mip/layer combinations and compared
their first texel or compressed block. A completed GPU buffer write and
a simulated write-back changed an independent subresource. Both cases
selected a full upload and passed readback. A queued overlapping GPU writer
also prevented partial eligibility. Khronos Vulkan validation was active
in all ten runs with direct rendering or two recorder workers. The ten
runs total 1,148 checks. The neighboring write-back, full upload and
lag-guard tests passed 2,045 checks with the option enabled. The full
recorder suite also passed with it enabled, logging 45,306 checks and
matching 351 combinations of pixels and counters byte for byte. APK
10046 passed the content, checksum and signature audit.
[Vulkan fixture](../games/totk/android/gfx/test_vk.c)

The experiment remains off by default. Compare identical S23+ routes with
and without it, reading `[upload-partial]` alongside upload time, staging
peaks and frame times. The route reporter emits a window delta when both
adjacent counter readings are available. The host test measures copied bytes for one known
edited subresource. The matching fraction of reuploads during the warp and
the effect on device performance still need to be measured.
[Offline route report](../tools/bench/route_report.py)

## Reduce the cost of block-linear texture conversion

The last complete 10021 transition window submitted 225.3 MiB across
1,605 texture uploads. Upload preparation took 291.3 ms across that
300-frame window. It included more than byte conversion. The run used
the default serial upload path.
[S23+ device capture](s23-device-validation.md#follow-up-on-the-return-warp-peak)

Build 10047 computes the starting block coordinates once per span and
advances them in the existing storage order. A full 64-byte row uses
four fixed-size 16-byte copies. The short right edge keeps its byte
bounds, and the loops clip bottom rows and depth padding. This applies
to the single-thread decoder, upload helpers and the inverse write-back
path. Android NDK Clang emitted 128-bit vector loads and stores for
the full-row copies in its ARM64 object.
[Tegra X1 storage model](https://github.com/ScanMountGoat/tegra_swizzle),
[Arm NEON load and store documentation](https://developer.arm.com/community/arm-community-blogs/b/operating-systems-blog/posts/arm-Neon-optimization),
[Implementation](../games/totk/third_party/d2r_gfx/gfx/tex/nvn_deswizzle.c)

| Host upload fixture | Serial before → after | One helper before → after | Three helpers before → after |
| --- | ---: | ---: | ---: |
| 2048×2048 RGBA8 with mips | 2.522 → 1.542 ms | 1.366 → 0.973 ms | 0.836 → 0.654 ms |
| 1024×1024 RGBA8 cubemap with mips | 3.876 → 2.624 ms | 2.302 → 1.805 ms | 1.727 → 1.555 ms |
| 512×512 RGBA8 | 0.100 → 0.038 ms | 0.056 → 0.022 ms | 0.033 → 0.014 ms |
| 256×256 RGBA8 | 0.024 → 0.007 ms | 0.025 → 0.007 ms | 0.025 → 0.007 ms |

These are medians of seven alternating before/after runs, with the same
four host CPUs available to both binaries. Each run timed 20 warm
conversions. The 256 KiB fixture stays serial because it is below the
helper threshold. The source change applies to both whole textures and
the partial uploads introduced in 10046.
[Host benchmark](../games/totk/android/gfx/test_upload_pool.c)

The texel-region oracle passed 1,785,960 checks across 156 formats,
including direct point-address checks for spans starting inside a block.
The upload pool passed 24,179 checks, including padded rows, packaged
3D layouts, compressed formats, and byte comparisons during live helper
reconfiguration. Both suites passed with AddressSanitizer and
UndefinedBehaviorSanitizer. Live Vulkan upload and write-back fixtures
passed another 1,654 checks in direct and two-worker modes. The full
recorder suite logged 45,306 checks and matched 351 pixel-and-counter
comparisons byte for byte. The APK passed content, checksum and
signature verification. The S23+ still needs a matched run to measure
the effect on frame times and memory pressure.
[Span oracle](../games/totk/android/gfx/test_texel_region.c)

## Reclaim a span that fits before growing a block

The final complete 10021 window had 51.6 MiB of images awaiting
retirement and 1.2 MiB of idle shared images. The capture does not show
which retirements had finished when each new image requested memory.
This led to testing the existing opt-in reclaim pass before block
growth. Its first eight ready images can leave fragmented holes that
do not fit the request, even when another completed image can free one.
[S23+ transition memory](s23-device-validation.md#follow-up-on-the-return-warp-peak)

Build 10048 looks ahead within the existing 64-record limit when
`TOTK_VK_IMAGE_RECLAIM_BEFORE_GROW=1`. It prefers one completed image
whose release would fit the request after joining adjacent holes. The
decision checks the allocation's memory type and aligned offset. When
there is no single fit, it can still reclaim up to eight compatible
completed images. The allocator retries the real allocation after
reclamation, so `single_span_fits` counts candidates and
`fits_after_reclaim` measures actual reuse. The pass checks published
completions without waiting for another GPU ticket.
[Vulkan memory requirements](https://docs.vulkan.org/refpages/latest/refpages/source/VkMemoryRequirements.html),
[Vulkan image lifetime](https://docs.vulkan.org/refpages/latest/refpages/source/vkDestroyImage.html)

The live fixture interleaves sixteen 2 MiB images in one block. In a
second block, a completed 12 MiB image borders an 8 MiB free tail.
The old reclaim pass destroyed eight small images and reserved a
third 32 MiB block to satisfy a 16 MiB request. The new pass reclaimed
only the 12 MiB image and reused its coalesced span. Block commitment
stayed at 64 MiB instead of growing to 96 MiB. GPU readbacks matched
for a surviving image, the replacement and an image still referenced
by the unsubmitted work. The pass peaked at 10.5 µs with validation
active in the host fixture. The two modes passed 58 checks, and
nearby block, dedicated, pressure and pool fixtures passed 270 checks.
The full recorder suite passed with reclamation enabled, with 45,306
checks and 351 exact pixel-and-counter comparisons. The allocator
fixture passed with GCC and Clang. APK 10048 passed content, checksum
and signature verification.
[Live Vulkan fixture](../games/totk/android/gfx/test_vk.c)

The experiment uses the existing opt-in setting. The matched device run
needs to measure how often the candidate and actual reuse counters
advance, and whether they reduce peak commitments during the #55 warp.

## Reduce retained and overlapping texture staging

The 10021 return window held 64 MiB across eight slot staging arenas.
The old minimum chunk size was 8 MiB. Asking for a 4 MiB retention cap
still yielded 64 MiB across all eight slots after the test workload's
bursts had settled. Build 10050 lets an empty slot begin with a smaller
chunk through `TOTK_VK_STAGING_RETAIN_MB`. The next allocation in the
same slot can use the usual 8 MiB floor or grow to fit the request.
The Android Low Memory preset still selects 8 MiB.
[Previous S23+ run](s23-device-validation.md#follow-up-on-the-return-warp-peak)

In the host fixture, the initial 45 MiB burst was the same at both
caps. After 16 quiet submissions the arenas held 32 MiB at 4 MiB per
slot, compared with 64 MiB at 8 MiB per slot. A separate fixture
reopened a slot after a mixed burst. It kept the original 4 MiB buffer
and released four larger allocations, from 40 MiB down to 4 MiB,
without a new allocation or map for the next quiet submission.
[Vulkan memory requirements](https://docs.vulkan.org/refpages/latest/refpages/source/VkMemoryRequirements.html),
[Staging fixtures](../games/totk/android/gfx/test_vk.c)

The independent startup option `TOTK_VK_STAGING_EARLY_TRIM=1`
releases surplus texture-upload chunks before the next staging
allocation. It needs a finite staging cap. On each grow, it can free
up to four chunks from one other slot. That slot must have completed
its GPU ticket and CPU submit work and have no replay lease. Texture
uploads now identify their scratch allocations so a buffer used by
general callers retains its ordinary slot lifetime. Both the existing
slot-reopen policy and the experiment use the same buffer and memory
destruction path.
[Vulkan buffer lifetime](https://docs.vulkan.org/refpages/latest/refpages/source/vkDestroyBuffer.html),
[Vulkan memory lifetime](https://docs.vulkan.org/refpages/latest/refpages/source/vkFreeMemory.html),
[Implementation](../games/totk/android/gfx/nvn_vk.c)

With the cap held at 8 MiB, the live GPU fixture verified that a pinned
upload stayed readable while another slot grew. Once the pin cleared, a third slot
released the completed 9 MiB upload chunk before allocating. Peak
reservation fell from 47 MiB to 38 MiB. Both GPU readbacks and a
separate 9 MiB general allocation retained their expected bytes.
The focused A/B passed Khronos validation in direct and two-worker
modes. The external replay fixture passed 996 checks per mode with
both options enabled. The recorder suite passed its 45,306 checks and
351 exact pixel-and-counter comparisons with both options enabled.
The final APK passed content, checksum and signature verification.

Measure the options separately on the S23+. Compare actual
`[arena-early-trim]` released bytes, staging peak, staging allocation
count and frame times during the same return warp. A lower warm cap can
increase allocation churn if the usual uploads exceed it.

## Trim spare Vulkan descriptor pools after bursts

The S23+ log from build 10021 kept 50 descriptor pools at the ends
of frames 20,700 and 21,000, with 42 recorder and eight primary pools.
Descriptor allocations dropped from about 1,837 to 841 per frame across
those windows. The 93 MiB log estimate is based on declared compact pool
capacity and descriptor size assumptions. Actual driver residency was
unmeasured.
[Previous S23+ run](s23-device-validation.md#follow-up-on-the-return-warp-peak)

The inspected Turnip driver sizes a pool's GPU buffer object from the
declared descriptors. Reset rewinds allocations within that buffer.
Destroy releases the buffer object and the host allocation. This
explains why pool count matters for Turnip and why reset count measures
different work.
[Turnip descriptor pool implementation](https://github.com/GameNative/mesa-turnip/blob/c8bab41a1b67bdba56c45305f4e07f85c215c349/src/freedreno/vulkan/tu_descriptor_set.cc#L737-L849)

Build 10051 adds `TOTK_VK_DESC_TRIM_IDLE=1` in `totk.env`.
With descriptor stock off, each owner skips resetting pools that saw
no allocations in the retired generation. At the end of every 32
recycled generations it keeps the highest pool count used during that
window, with a floor of one once it has allocated a pool. Memory
returns to the driver through pool destruction at the existing
retirement handoff. The pool can grow again on the next burst. A
recorder context that stops receiving work retains its pools until it
recycles again.
[Vulkan descriptor-pool reset](https://docs.vulkan.org/refpages/latest/refpages/source/vkResetDescriptorPool.html),
[Vulkan descriptor-pool destruction](https://docs.vulkan.org/refpages/latest/refpages/source/vkDestroyDescriptorPool.html)

The host A/B verified both a busy window that retained capacity and a
quiet window that could release it. With compact descriptors active, the
recorder fixture went from three pools to one and from 96 resets to 31.
The eight-slot primary fixture went from ten pools to eight and from 320
resets to 255. Both grew to the original count in the next burst.
Each arm passed 529 checks with Khronos validation active. The stock and
live-toggle tests passed with zero and two recorder workers, and the
240-frame live tests reported zero early pool operations. Replay
pinning passed 996 behavioral checks per arm and worker mode. Its test
event gates emit two synchronization VUIDs in both arms.
The recorder suite passed 45,306 checks across 390 fixtures and 351
exact pixel-and-counter comparisons with idle trim and both staging
experiments enabled. APK 10051 passed the 73-entry content audit, checksum
verification and verification with the existing development certificate.

On the S23+, compare `[descriptor-idle-trim]` pool destruction counts,
retained pools, pressure and frame times during the same Akkala return
warp. Keep descriptor stock off and check whether a second burst
rebuilds pools fast enough to preserve frame pacing.

### Batch frequent descriptor reservations

The 10066 capture at frame 24,000 reported 3,274.66 allocated sets
and 3,274.66 allocation calls per frame. The retired-pool counter
was unchanged from the preceding window. This identifies recurring
driver-call overhead to investigate independently of pool destruction.

Build 10069 adds the opt-in `TOTK_VK_DESC_BATCH=1` for recorder
contexts with stock off. It starts batching a layout after eight
individual requests in the same owner generation. The first four
tracked layouts each have a maximum of seven spare handles. Pool
resets at the existing retirement handoff clear the stash.
[Vulkan descriptor sets and pool reset](https://docs.vulkan.org/spec/latest/chapters/descriptorsets.html)

| Desktop Vulkan case | Allocation calls per frame, off → on | Allocated sets per frame, off → on |
| --- | ---: | ---: |
| Ordinary recorder without frame lag | 6.83 → 6.83 | 6.83 → 6.83 |
| Heavy synthetic recorder without frame lag, descriptor memo disabled in both arms | 165.44 → 53.83 | 165.44 → 176.89 |
| Recorder with frame lag | 82.80 → 11.04 | 82.80 → 83.24 |

The heavy no-lag case retained 16 pools in both arms. Each pair
returned byte-identical pixels and counters and passed 244 checks
per arm. Both arms emitted the same vertex-format validation errors
from the fixture. A separate real-driver test interleaved six layouts,
verified 108 distinct requested handles and reduced calls from 108
to 76 while allocating 24 spare sets in the same pool. The original
second-use threshold overallocated in the light case and was replaced
with the eighth-request warm-up before batching. No FPS improvement
has been measured on the S23+.

## Coalesce contiguous texture upload regions

Vulkan's buffer-to-image addressing already steps through multiple array
layers by the tightly packed layer size. Turnip likewise derives the
source stride from the copy extent, including compressed formats.
Build 10052 combines adjacent layers within each mip when that stride
matches the existing staging layout. A layer with alignment padding
keeps its own region, and partial uploads begin a new region after
every clean gap. Staging bytes and the transfer barriers are the same.
[Vulkan copy addressing](https://docs.vulkan.org/spec/latest/chapters/copies.html#copies-buffers-images-addressing),
[Turnip buffer-to-image source](https://github.com/GameNative/mesa-turnip/blob/c8bab41a1b67bdba56c45305f4e07f85c215c349/src/freedreno/vulkan/tu_clear_blit.cc#L2689-L2698)

A six-face cubemap with three mips now uses three regions instead of
18. An odd-sized array keeps six separate regions for its padded
base mip and uses one region each for its two tight mips. With grouping
enabled, the fixture avoided 56 regions across first uploads and
reuploads, and heap allocation of region arrays dropped from four to
zero. Vulkan readbacks verified the first and last texel of every
layer at each mip. A separate partial-upload case updated adjacent
layers zero and one plus isolated layer four, producing two regions
and preserving the other layers. Compressed and untracked-memory
cases also passed. Khronos synchronization validation ran in direct
and two-worker modes. The focused Vulkan tests passed 3,438 checks.
With the memory experiments active, the complete recorder suite passed
45,306 checks across 390 fixtures and 351 exact comparisons. The
signed APK passed its 73-entry content audit and checksum verification.

The existing `[upload-prep]` report includes `regions_joined`.
`TOTK_VK_OFF=uploadlayers` restores the previous copy plan for a
matched benchmark.

## Separate small textures from larger memory blocks

The 10051 and 10052 S23+ runs still held 768 MiB in suballocation blocks
after occupied spans had fallen below 460 MiB. Individual allocations
can keep a whole block alive. Custom pools allow smaller blocks to
place small resources together. A second pool can also waste capacity
and increase driver allocation count, so both outcomes need measurement.
[S23+ results](s23-device-validation.md#return-warp-validation-after-the-optimization-goal),
[Vulkan Memory Allocator custom pools](https://gpuopen-librariesandsdks.github.io/VulkanMemoryAllocator/html/custom_memory_pools.html#custom_memory_pools_when_not_to_use_custom_pools),
[Khronos suballocation guidance](https://docs.vulkan.org/guide/latest/memory_allocation.html#sub-allocation)

Build 10053 with `TOTK_VK_IMAGE_SMALL_BLOCKS=1` serves texture
allocations of at most 1 MiB from 8 MiB blocks. Larger textures and
other resources retain their regular blocks. Allocation and fast
reclamation match both the Vulkan memory type and block size.
All existing ownership and fence requirements apply.

An alternating allocation fixture placed three 1 MiB images among
larger textures. During the burst the control used 96 MiB and the
split policy used 104 MiB. After retiring the large textures, the
control still held 96 MiB and the split policy held 8 MiB. Both
retained the same three images and the Vulkan readbacks confirmed
their pixels after retirement. The four runs passed 72 checks
with Khronos validation, and the nearby reclamation fixture passed
another 58. The route parser records the number, committed bytes
and occupied bytes of the small blocks independently.

The S23+ comparison did not reproduce the fixture's benefit at the
return warp. Peak image commitment increased from 815.1 to 871.1 MiB
and Android killed the experimental build during the warp. In the
Depths, the separate small blocks held about 171 MiB of occupied
spans across 320 MiB of commitment. Splitting by size let small
allocations of different lifetimes keep their own blocks active.
The size-class patch was removed from the working source. The
paired route logs and fault measurements remain available locally.
[S23+ comparison](s23-device-validation.md#sustained-gameplay-optimization)

The last experimental window reported 514 MiB of private texture
mirrors. The current lifetime policy keeps their Vulkan images attached
to live texture serials. Determining which of these images remain
unused across the warp requires distinguishing ordinary texture
lookups, GPU writes and recorded references. Age alone cannot authorize
discard while a prior submission or descriptor still uses an image.

## Texture lookup age and host allocator

Build 10054 added a lookup-age census to the existing diagnostic flag.
The four age buckets plus unknown age matched the private mirror total
in all 48 S23+ reports. Of the 28 surface movement windows, 88–136 MiB
had gone at least 600 submissions without an ordinary lookup. None of
the 48 samples showed any block whose live spans were all in that age
class. Retiring those suballocations would free spans for reuse, but
would leave other live allocations in each block at those sample times.
The test estimates coverage from current allocation sizes and uses
lookup age only. Vulkan requires all submitted work referencing an
image view to finish before destruction. [Vulkan image-view lifetime](https://docs.vulkan.org/refpages/latest/refpages/source/vkDestroyImageView.html)

The map produced reports with about 79 MiB of dedicated mirrors in the
old lookup buckets. Those allocations were no longer in the buckets
once the Depths rendered. Map time can make world textures look idle
while their contents are needed shortly afterward.

A separate candidate tests a shorter release interval for pages the
native allocator has already freed. Before that change, a rootless
mapping snapshot in the Depths showed 367 MiB of swap PSS and 90 MiB of
resident PSS attributed to `libc_malloc` mappings. That includes live
allocations, so it gives no estimate of reclaimable bytes. On Bionic,
`mallopt(M_DECAY_TIME, 0)` requests the allocator's minimum release
interval. It can trade allocator work for lower retention. Compare the
same route and allocation settings with and without the override.
[Bionic allocator behavior](https://android.googlesource.com/platform/bionic/+/HEAD/docs/native_allocator.md),
[Scudo allocator options](https://llvm.googlesource.com/llvm-project/+/refs/tags/llvmorg-16.0.0/compiler-rt/lib/scudo/standalone/wrappers_c.inc)

The S23+ comparison with 10057 measured lower median major-fault rates
and lower native heap swap PSS in the early Depths. Both arms still
ended with a foreground low-memory kill, and 10057 died during
post-return movement. It remains an opt-in candidate.
[S23+ short-decay comparison](s23-device-validation.md#private-texture-age-and-native-heap-release)

### Displaced guest memory backing

On this Adreno driver, the Vulkan pool path copies guest bytes into
an exported DMA buffer and maps that buffer over the original
address. Linux implements the guest's shared anonymous reservation
as one shmem object. Replacing a range of virtual addresses can leave
the old file offsets allocated as long as other mappings hold the
original object. The first surface mapping snapshot had about
1,175 MiB of DMA-buffer address ranges inside the guest reservation.
That measures virtual mappings and does not quantify displaced
physical or swapped pages.
[Vulkan pool mapping](../games/totk/android/gfx/nvn_vk.c),
[Guest memory reservation](../games/totk/runtime/services.c),
[Android GKI shared memory](https://android.googlesource.com/kernel/common/+/refs/heads/android13-5.15/mm/shmem.c)

The host repro copied a 32 MiB region to a new backing and replaced
its original addresses. The first backing still accounted for
32 MiB plus two boundary pages. Hole punching returned the old 32 MiB
and left the new copy intact, but also zeroed any view of those old
offsets. NVN may alias physical pool pages independently of the
original address, so a reclaim implementation needs to prove which
offsets have no remaining reader.
[Linux MADV_REMOVE](https://www.man7.org/linux/man-pages/man2/madvise.2.html),
[NVN virtual aliases](../games/totk/third_party/d2r_gfx/gfx/nvn/totk_vpool.c)

A smaller first experiment is to copy from a known shmem file
offset. The sparse host fixture allocated 8 MiB of a 32 MiB source.
Mapping-based `memcpy` filled the holes in the original backing,
whereas `pread` left the backing at 8 MiB. The resulting bytes matched
in both runs. Both fixtures gave the same numbers on the S23+ with
its Android 16, 5.15 kernel. Trying a sparse copy in the game would
need an explicit backing identity and offset for the source, with
the existing copy path for any range already remapped by another
owner. Measure the number of eligible bytes and the change to the
guest backing before considering any hole punching.

Build 10059 exercised that approach on the S23+. The control and
experiment both used an explicit shmem reservation so the allocated
backing could be compared directly. The experiment used the file
source only for ranges whose 64 KiB tracking groups were still on
the original reservation. The mapped-source path handled other
ranges. The reduction went from about 119 MiB in the title sample
to about 3 MiB in early surface gameplay. This addresses new page
instantiation only. Existing pages at offsets displaced by the GPU
mapping can stay allocated.
[S23+ sparse-copy results](s23-device-validation.md#sparse-copying-into-gpu-pools)

Build 10060 enumerated disjoint active DMA-buffer pools under the
pool registry lock and queried data extents at their corresponding
file offsets in the original shmem. In early surface gameplay,
232.1 MiB of the 1,176.8 MiB of covered offsets still held data.
The scan only covers registered active DMA owners. Allocated offsets
can include swapped pages, and the scan supplies neither an RSS
estimate nor a safe reclamation total. A release path needs to
preserve source offsets ever handed to a fallback virtual alias
and leave the renderer's live DMA buffer untouched.
[S23+ displaced allocation measurement](s23-device-validation.md#sparse-copying-into-gpu-pools)

## Reclaiming the displaced backing

Build 10062's experimental `discard` mode copies into the DMA buffer,
installs the mapping and then requests hole punching on the old
file offsets. An NVN fallback clone resolves its current source
file and offsets while the pool lock still excludes replacement.
Its source groups stay protected for the lifetime of the guest
reservation. This also protects aliases made from another alias.
Linux can grow a clone beyond its starting VMA, so this mode
checks that the requested source is contiguous through the actual
file offsets before allowing that fallback. An unproven range
stops the experiment before cloning. The normal path is selected
when the option is unset.
[Linux mapping duplication](https://man7.org/linux/man-pages/man2/mremap.2.html),
[Linux hole punching](https://man7.org/linux/man-pages/man2/fallocate.2.html)

A host fixture creates an actual fallback clone and verifies the
contents of the preserved file offset, the replacement and both
neighboring pages. It also checks source coverage across two
VMAs of the same file and rejects a shared clone extension into
a different mapping. The log's successful range bytes can
include holes and repeat ranges. Use the allocated backing and
the extent scan for the measured memory difference.

## Reduce CPU memory held by shader and pipeline caches

The Lookout Landing route recorded both costly pipeline construction and
frame delays under memory pressure. The persisted cache from a prior visit
improved the short same-save test. This change keeps persistence and
reduces its overhead. [S23+ results](s23-device-validation.md#lookout-landing-cache-comparison)
and [hardware research](switch-snapdragon-architecture-research.md).

The Vulkan saver used to retain the heap buffer containing the last opaque
snapshot. The extended S23+ route wrote a 30,316 KiB cache payload. The
saver now maps private staging pages, releases their residency after each
attempt, and reuses the mapped address range. Growing the mapping does not
copy the old snapshot. The durable file is still written via complete
temporary-file replacement. An incomplete Vulkan extraction leaves the
previous generation available for the next launch.
[Linux MADV_DONTNEED](https://linuxman7.org/linux/man-pages/man2/madvise.2.html)
and [Vulkan pipeline cache contract](https://docs.vulkan.org/refpages/latest/refpages/source/vkGetPipelineCacheData.html).

The pinned Mesa implementation walks and serializes entries under the
cache lock for size-only calls as well as data extraction. The application
defers size queries during active play until the existing dirty deadline,
and snapshots use the size already measured in the same poll. Quiet saves
and explicit lifecycle flushes retain their eligibility. Tests cover
busy, quiet, timeout and shutdown paths as well as incomplete and failed
transactions. [Pinned Mesa implementation](https://gitlab.freedesktop.org/mesa/mesa/-/blob/f7c93a1352b578fbea6c249227d44df65b8f6a35/src/vulkan/runtime/vk_pipeline_cache.c#L730-780).

The shader seed inventory used to duplicate an 84-byte name in every table
slot. The index now stores a 32-bit fingerprint and compares the original
full name for any matching fingerprint. The pack format, loose overlays
and shader bytes stay the same. The fixture has 71,400 entries, two real
fingerprint collisions, a loose override on a colliding entry and a
missing-key lookup. Counted heap metadata fell from 24.574 to 15.118 MiB,
a 9.456 MiB reduction. This accounting excludes allocator overhead, mapped
file pages and warmed shader payloads.

| Host verification | Result |
| --- | --- |
| Pipeline staging after a successful 32 MiB snapshot | Linux `mincore` reported 33,558,528 resident bytes with the old heap buffer and zero with the new mapping. |
| Partially written Vulkan snapshot | The resident pages were released and the existing atomic-file fixture also verified preservation of the previous blob. |
| Vulkan cache and lifecycle suite | 1,003 checks passed, including real host Vulkan creation and a fresh-process cache reload. Caches were written on tmpfs because the concurrent rename check also failed on this workspace's FUSE volume with the original code. |
| Shader seed suite | 21,771 checks passed in the recorded run, including the large fixture, pack and loose fallback, and concurrent read and publication paths. |
| APK | Signed local development build 10072 includes both changes. Device frame timing, PSS, cache save duration and issue #55 remain to be validated with this build. |

## Release the startup shader mapping and bypass warming in constant time

The renderer copies shader names and payload offsets into the index during
startup. Payload reads go through the pinned file descriptor. Build 10074
releases the file mapping after copying the index and keeps the descriptor
open until outstanding reads have finished. On the 71,400-entry Linux
fixture, the old process had 7,296 KiB of resident pages in the pack
mapping. The new process had no pack mapping after indexing. The operating
system can still cache pages of the file. The atomic replacement, truncated
pack and restart tests protect the descriptor lifetime and the cold read
fallback.

Demand reads can bypass a queued warm entry. The old path traversed the
remaining warm queue under the I/O mutex on each bypass. The new path
changes the entry state directly, and the worker skips canceled entries
while draining. The existing test now exercises a bypass in the middle of
the queue while another read is in flight. The worker still warms the
surrounding entries and performs no duplicate reads.

A deliberate queue stress benchmark held the worker and requested 16,383
queued entries in reverse order. Across three runs per version, the
median fell from 320.885 to 23.091 ms. Both versions read exactly the same
payloads once and returned identical bytes. This ordering stresses the
old linear removal and does not predict frame times on Android. The
shader seed suite passed 21,779 checks, including mapping lifetime, queue
takeover and concurrent shutdown. Signed APK 10074 includes these changes
and the changes first built in 10072. The S23+ measurements remain open.

## Validate ordered shader pack ranges without temporary storage

Both the Android setup writer and the Python packer emit payloads in
index order. Build 10075 checks these ranges in a single pass. It only
allocates and sorts a range list when that pass cannot establish that
payloads are disjoint. This also accepts existing packs with valid
out-of-order offsets. The seed format, shader contents and loose overlay
behavior stay the same. [Android pack writer](../games/totk/android/setup/seed/pack.c)
and [Python pack writer](../games/totk/scripts/pack_shader_seed.py).

| Ordered 71,400-entry fixture | Before | Build 10075 |
| --- | ---: | ---: |
| Range-list allocation per open | 1,142,400 bytes | 0 bytes |
| Sorts per open | 1 | 0 |

Three batches of 31 repeated opens per version showed overlapping
wall-time measurements. The deterministic result is reduced startup
scratch and work. The native reader checked output bytes and exercised
ordered, reversed and overlapping records. The seed I/O suite also
passed 21,779 checks. The signed local APK is ready for later S23+
qualification.
