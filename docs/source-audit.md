# Source audit after Android beta 1.1.0-beta.1

The public beta is built from `c686e4c`. The review covered the 77 changed files since
`afdcd6b` and ran static checks across the Android build. The follow-up is in the local
working tree. Phone testing stopped at the owner's request.

## Coverage

| Area | Review and verification |
| --- | --- |
| Android native runtime and renderer | The NDK analyzer processed 108 C/C++ translation units from the Android build, including 54 Android, 43 runtime, and 11 integrated third-party units. It reported 69 warnings in the initial pass. The frontend analyzer crashed inside a JNI path. A single-unit retry with interprocedural analysis disabled finished with three warnings. These are tool diagnostics pending individual disposition. |
| Java setup, persistence and activity lifecycle | The APK build compiled the Java sources. Dedicated host fixtures exercise mod archives, save management, settings, the game lock, and the menu's game-process binding. The review compared the normal launch path with the recovery and import paths. |
| Python and shell tooling | All 245 tracked Python files parsed and all 18 tracked shell files passed Bash syntax checks. The local suite exercises setup tools and synthetic parsers. Development packaging now uses the same signature, launcher-art and content checks as release packaging. |
| Bundled code and native libraries | The APK build used the pinned Android translator compiled from source, the pinned Turnip binary and declared third-party libraries. The content audit and APK signature verification passed. |
| Other targets | The source inventory includes Metal, iOS and macOS. Their platform builds and rendering still require the corresponding toolchains and hardware. The 108-unit analysis covers the NDK Android build path. |

## Standards review

- The mod importer's documented recovery promise failed when the next action was to launch the
  game directly. Android now restores the previous directory while holding the native game lock,
  before resolving overlays. The menu can show the previous import while the swap is incomplete.
- Ignored ZIP directory entries bypassed the importer's expansion budget. All ZIP entry payloads now
  pass through a bounded copy or drain. Each import reuses one 64 KiB buffer.
- Developer APK packaging diverged from release checks. Both paths now share the same packaging
  implementation, with separate package identities and signing keys.
- The Vulkan varying fallback can create an output of the wrong shape for a scalar or explicitly
  decorated fragment input. The same vertex transform sequence is repeated in two shader paths.
  Both findings remain open. [Vulkan interface matching](https://docs.vulkan.org/spec/latest/chapters/interfaces.html#interfaces-iointerfaces-matching)

## Spec review

- The beta's explicit 1920 × 1080 scene control depends on a HeapDef overlay built by desktop tools.
  It could prevent startup on a clean Android installation. The follow-up restores Game default
  when a saved beta setting contains the unsupported value. Docked and 1080p display presentation
  continue to work through their existing paths. A turnkey native 1080p scene remains open.
- The interrupted mod swap could start a session without the earlier mods. A host fixture reproduces
  the two-rename interruption and verifies that the runtime's recovery restores the old content
  while leaving staged content for normal cleanup.
- Indexed quads and quad strips assume the all-ones primitive-restart index. The NVN entry point
  currently ignores the guest's enable and restart marker. Valid highest indices and custom markers
  remain to be exercised and supported.
- The non-indexed quad index buffer retains its previous allocation on capacity growth. Retiring
  that allocation requires proving the regular and frame-generation uses are complete. Its
  contribution to the S23+ low-memory exit remains to be measured.

The two reviews reported five standards and maintainability findings and four spec findings,
including the shared mod-recovery defect. The largest startup issues were mod recovery and
the unavailable HeapDef overlay. Follow-up remains open for primitive restart, buffer lifetime,
varying compatibility and the analyzer warnings.

## Performance follow-up

The follow-up makes per-tile write-back diagnostics opt-in. The live Vulkan write-back suite passed
131 checks in both settings. It emitted zero per-tile messages by default and 106 with tracing
enabled. The previous S23+ 10021 run emitted 5,866 of these messages. Mod overlays now allocate their
added-file index once per initialization. A host fixture passed 100,000 added paths through both
versions of the production function. The beta made 100,000 reallocations and one allocation.
The candidate made two allocations and preserved index order and duplicate rejection.
The importer's transfer buffer is shared within each session.

The next device comparison remains an aged Akkala → Depths → Akkala route with matching save,
driver, camera settings and starting cache. It should record the image-memory peak, overlap with
guest pools, and all foreground process exit reasons. The returned-surface crash remains open.
[Device results](s23-device-validation.md#follow-up-on-the-return-warp-peak)

## Local validation

Development build 10024 completed the Android native and Java build. Its APK passed the content
audit and v1, v2 and v3 signature verification. Its signing certificate matches the device's
previously installed development build.

The Clang and JDK host suite ran 934 tests. It passed 866, skipped 67 optional cases and had one
intermittent `test_live_ctl.py::test_missing_file_idle` failure on the workspace's FUSE filesystem.
That test passed three consecutive isolated reruns. The control-file group also passed 17
tests with one optional skip on tmpfs. Android startup recovery passed through
the production launch code. The mod import regression confirms the decompressed ZIP quota
includes ignored directory payloads. The saved 1080p setting migrates to Game default.

The public beta remains available at [v1.1.0-beta.1](https://github.com/GTomasel/totk-android-low-ram/releases/tag/v1.1.0-beta.1).
The 10024 fixes await device and gameplay confirmation.
