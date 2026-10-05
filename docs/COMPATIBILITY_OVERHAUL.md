# Compatibility overhaul: investigation record

This is the evidence ledger for the iPhone 17 Pro Max / iOS 26.6.2 compatibility work. It records what has been verified and keeps hypotheses separate from fixes. The acceptance tests in [GAME_TEST_MATRIX.md](GAME_TEST_MATRIX.md) remain required.

## Latest native and host gates: 959e37c

[Host run 37256826493](https://github.com/llucasandersen/Madeira/actions/runs/37256826493)
passed all 70 distinct checks. The downloaded Linux/macOS inventories were
checked against the current test filenames; all checks appear exactly once and
have exit code zero. The separate real Valve archive gate also passed.
The fresh native runtime job 111595602245 in
[IPA run 37256828172](https://github.com/llucasandersen/Madeira/actions/runs/37256828172)
passed, including the exact-basename helper containment change. App packaging
and device acceptance remain pending for this build. USB update 2 is preserved.

## Final dependency-resolution status in startup diagnostics

The supplied PEAK log records SDL3's architecture rejection and then the
loader's final `[dll-missing]` status `c000007b`. The earlier startup UI parser
accepted only `[pe-image]` records, so a dependency-resolution failure without
a preceding mapping rejection was invisible, and the architecture record did
not contain the final NTSTATUS. `SteamLoaderRejection` now also accepts the two
actual Wine final-resolution record formats. `LogStore` captures them before
hidden-live-log suppression, so the startup warning can display the measured
module basename, resolution stage and exact status without retaining paths.
Architecture evidence remains in the full diagnostic log; no status or machine
type is inferred. This observation does not declare an optional DLL fatal or
change the launch result.

The production Swift parser fixtures cover both final-resolution formats,
the supplied x86/AMD64 machine pair, missing dependencies, malformed/duplicate
status tokens, success-record rejection, callback line terminators and
multiline rejection. The remaining risk is that a later unrelated optional
failure replaces an earlier diagnostic, hence the UI labels it the last
observed rejection. New full host and Xcode app gates are required.

The initial parser run 37257705322 failed only its CRLF callback fixture:
Swift represents CRLF as one `Character`, so removing two characters also
removed the last status digit. Terminator removal now consumes one Character
for CRLF, LF or CR, with all three covered. The app built in run 37257707336,
but that package predates this parser correction and is not a final release.

## Child spawn failure descriptor ownership

Source review found two errors in the iOS `spawn_process` path. Both `dup`
results were unchecked, so descriptor exhaustion could start a child with an
invalid startup socket or silently lose its requested working directory.
If `pthread_create` failed, the duplicated socket and directory descriptors
were leaked. Repeated failed launches could therefore exhaust the shared Mach
process's descriptor table. This is a deterministic source defect, not a
confirmed cause of the supplied Teardown content wait.

`build/ntdll-unix/process_ios.c` now initializes owned descriptors to `-1`,
checks both duplication results and returns Wine's mapped NTSTATUS before
starting a child on failure. A single cleanup path closes only the duplicates,
releases any acquired census slot and frees startup allocations. Successful
thread creation still transfers those resources to the child. Original parent
descriptors remain owned by the caller; no running child is terminated.

`check-child-spawn-failure.py` extracts the actual production iOS spawn
function and injects argument/allocation, first/second duplication and thread
creation failures under ASan/UBSan with leak detection. Real pipe/directory
descriptors verify closure and parent preservation, including 1,000 failed
thread starts and successful ownership transfer with/without a directory.
Native compilation and all 71 host checks are required for this new change;
the earlier successful runtime predates it. Device relaunch acceptance remains
pending. The primary regression risk is returning an explicit error where
the old path incorrectly attempted startup with an invalid descriptor.

## Earlier verified app baseline: a5669ae

[Host run 37253512089](https://github.com/llucasandersen/Madeira/actions/runs/37253512089)
passed all 68 distinct repository checks. Both downloaded Linux/macOS result
inventories matched every current `check-*.py`, without omissions or duplicates,
and all exit codes were zero. This includes the actual process CPU sampler,
resume/update integrity harness, learned JIT model/native frontier, completed
upload-ring reclamation, callback owner diagnostic and numeric launch lifecycle
report fields. Earlier pending host statements below describe their original
implementation points and are superseded by this run.

[IPA run 37253514108](https://github.com/llucasandersen/Madeira/actions/runs/37253514108)
passed native Metal compilation, Xcode linking, packaging and macOS codesign
gates using verified source component artifacts. The native runtime came from
successful job 111583454146 in run 37252716282. Local ZIP CRC, app/helper identity,
runtime markers, component source pins and bundled graphics hashes passed for
`Madeira-diagnostic-a5669ae.ipa` (87,274,803 bytes), SHA-256
`c02e208064f6d41ad3014cad7146600df6d6449893f00aa9b158ff97676a8288`.
This diagnostic remains local; USB update 2 is preserved. These build results
do not establish device memory survival, renderer selection, launch timeout
behavior or the download control target. The whole goal and final release
remain unfinished.

## Optional helper containment path matching

The existing-runtime upgrade's full app/IPA build passed in run 37256203960
at `4acba7a`. The locally downloaded 87,316,034-byte package passed ZIP CRC,
identity, runtime marker and source graphics pin/hash checks, SHA-256
`e1c7e8a6ab5b195be49a091f18d4d07530cc43bc25174ab71680af5eccb993d7`.
Its host run 37256201881 passed the production publisher and all other checks
except the static Dock contract, which mistook the literal hash inventories for
program-name launch rules. The contract now excludes only the two structurally
validated SHA dictionaries, with all entries independently checked by the real
Valve archive gate. No launch-name rule is exempted. The corrected full run
subsequently passed at `5848209` in run 37256617698. Both downloaded inventories
matched all 69 distinct checks without omissions or duplicates, with all exit
codes zero. The additional real-archive step also passed: all six old/new package
sizes and hashes, all 51 legacy replacement hashes and ten critical hashes
matched verified Valve contents, and the three new archives passed the production
Swift extractor/header checks. This proves the host upgrade fixtures and package
layout, not phone installation/gameplay or the subsequent helper-matching change.

Source review found that `NtCreateUserProcess` searched every character of an
image path for a blocked helper's name. A normal executable beneath a folder
such as `hardwareupdater simulator` or `UnityCrashHandler64 Edition` therefore
returned `STATUS_ACCESS_DENIED` before its process could be created. Prefixed
filenames also matched despite not being the contained helper. This is a
deterministic source defect; no particular reported game failure is attributed
to it without a matching device path.

`ios_optional_helper_gate` now compares exact executable basenames in counted
UTF-16 input, with ASCII case folding, slash/backslash paths and drive-relative
names supported. Known Steam reporter/driver-query/survey helpers and the
existing Unity crash reporter remain refused with the same status. Crashpad
and other game children are not covered by a blanket restriction. This improves
the generic launch path without loosening Steam ownership or the loader's
machine checks. It does not make the contained helper protocols functional;
their earlier containment evidence and remaining optional-query work still
apply.

`check-optional-helper-gate.py` compiles the actual matcher with ASan/UBSan and
checks all contained basenames, case/path variants, directory/prefix/suffix
false positives, short nonterminated buffers and ordinary game children.
The fresh native runtime and all 70 host checks passed at `959e37c`, as
recorded above. App packaging and device regression gates remain required.

The current public [Portal 2 report](https://github.com/willfaust/Madeira/issues/192)
was reviewed again on October 4. It describes a game rendering while Steam
still reports SDL3 failure, with working keyboard/mouse but failed controller
input. The proposed Steam Input connection is the reporter's hypothesis, not
an established cause. This corroborates the need to treat a DLL rejection as
diagnostic evidence rather than proof of game-launch failure. The coherent
runtime repair still needs controller/device validation; no Portal 2 input fix
is inferred from build success.

The `d3d12` config gate in `ContentView.swift` controls the shader-converter
canary test, not whether the game's D3D12 DLL can create a native device. The
supplied Teardown log's native device creation already demonstrates that the
canary-disabled message alone cannot establish a disabled renderer. Importing
OPENGL32 also does not identify the active backend. Per-launch renderer
selection and gameplay results must be established with runtime evidence;
turning on the canary would not implement the requested renderer profile.

## Recoverable launch-stage deadlines

The starting screen now also retains the last explicit `[pe-image]` rejection
from the log tail while its launch hold is active, even with the live log hidden.
The diagnostic parser accepts only the loader's known section, architecture,
map, module setup and PE64 conversion formats. Input and basename lengths are
bounded; full paths are discarded. Numeric status values and architecture
machine codes are validated. Architecture records without a status show the
actual machines rather than inventing an NTSTATUS. The diagnostic appears
beside a stage timeout or host failure. It is reset per launch and does not
turn optional media DLL rejection into a fatal result. Startup temporarily
keeps the existing tail reader active while suppressing ordinary UI parsing;
the tail returns to its normal hidden-log pause after the game is revealed or
the session ends. No extra file reader or log history is retained.

The production parser's fixture tests cover all recorded stages, exact status,
architecture-without-status, path removal, unrelated records, bounded input and
malformed/duplicate fields. Capture ordering and tail activation are checked
alongside existing UI wiring. Full host/Xcode gates for this subsequent change
are pending. The latest rejection can be from an optional component; the UI
labels it as an observation, not the established cause of the stall. Exact
process identity/fatal dependency attribution still require native evidence.

The supplied required-content refusal remains retryable for hours in the host,
while the starting screen previously repeated its original message indefinitely.
`SteamLaunchProgress` in `DockStartScreen.swift` now records the current observed
stage and its start time. Starting, sign-in, authenticated/license, authorized,
configuration/content wait, submitted launch, observed program window, rendered
game, Steam-reported game exit and host result are distinguished. Request
submission is admitted by the numeric report parser. Retry counts do not reset
the stage timer. The screen warns after 60 seconds of startup, 120 seconds of
sign-in/license checking, 180 seconds of other launch waits or 600 seconds of
required-content waiting. One-time installer duration is excluded.

Warnings expose the stage and elapsed time and offer the existing desktop/log
actions; they do not cancel a download, bypass authentication or mark the
session failed. Progress clears the warning. Window observations establish a
program with a window, potentially a secondary launcher; Steam's running flag
alone is deliberately not called executable-creation evidence. A host result
is not labeled a Steam crash without evidence. Exact process creation and
module/status failure propagation still need native integration to fulfill the
entire launch-state requirement. This change is absent from the locally
verified `a5669ae` IPA and delivered USB update 2.

The existing starting-screen harness compiles the production state rules and
checks deadline boundaries, retries, recovery, invalid/backward clock values,
installer exclusion, render/exit ordering and failed request submission. The
actual report parser checks the new numeric field. New full host/Xcode gates
are required. Risk: a legitimate slow operation can trigger a warning; keeping
it recoverable preserves the session and user choice.

## Learned per-game JIT pool sizing

The supplied Ravenfield run uses an 896 MB pool while its last pool-warmer
sample reports roughly 288 MB image-head frontier and 160 MB reserved tail.
Those are conservative allocator extents, not live translated code or resident
footprint. Reducing capacity alone does not prove an equal footprint saving.
Unused executable capacity is still a constraint worth budgeting, but an
arbitrary smaller default risks exhausting the image head or causing FEX to
rotate/recompile its code too often. StikDebug prepares the executable mapping
before detaching; this implementation does not assume it can safely grow that
mapping afterward.

`AdaptiveJITRecord` in `MadeiraDock.swift` now chooses a pool from observations
for the same Steam app/build. Unknown games/builds retain the standard pool.
Two completed Dock sessions, each with at least three minutes after the first
observed present and at least 300 presents, are required before shrinking.
The highest observed head-plus-tail extent receives a 25% plus 128 MB margin,
rounds upward to 64 MB, and never selects less than 512 MB or more than the
standard capacity. For example, an observed 448 MB frontier chooses 704 MB.
An observation within 64 MB of exhaustion blocks shrinking for that build.
The record never forgets a larger previous peak. The existing explicit `pool`
configuration and compact-Dock choice retain precedence; desktop/direct starts
are unchanged. Missing/unknown Steam build IDs disable learning.

The coordinator stores bounded, private numeric app/build records and an
in-progress marker in an atomic Application Support file before requesting
the chosen pool. A failed smaller-pool launch or an interrupted process blocks
that smaller policy on the next launch, restoring the standard pool. Failure
to write the marker keeps the standard pool. Sampling runs once per second
on a background queue and does not depend on the overlay remaining visible.
The native `ios_jit_pool_usage` helper in `virtual_ios.c` snapshots the head
under its independent allocator mutex and the reserved tail atomically; it
never enters Wine's virtual critical section or needs a Wine TEB. Counts are
saturated to capacity to avoid overflow or misleading overlap totals.

`check-adaptive-jit-budget.py` compiles the actual Swift model and native C
snapshot. It checks confidence, rendering duration/frame thresholds, margins,
minimum size, peak retention, interruption fallback, malformed/overflow values,
encoding and head/tail saturation. Full host/native/app builds are pending for
this change. Physical-device cache recovery and repeated-map memory/performance
tests are still required. A completed Steam launch report does not establish
every gameplay acceptance criterion. Later maps may exceed the learned margin;
the fallback limits repeated failures but cannot prevent the first one.
This is one part of adaptive memory budgeting, not proof that Ravenfield is
fixed. The delivered update 2 predates the policy.

The overlay's headroom value was also only read when its timers started.
It now refreshes beside physical footprint on every 250 ms display tick.

Integration review then found that the report parser did not whitelist Dock's
numeric `launch-game-running` and `launch-game-ended` events. Without those,
the new coordinator could never recognize a completed observed session even
though its isolated policy test passed. Both fields are now admitted by the
existing numeric-only parser, and `check-dock-report.py` exercises that actual
report path, including nonnumeric rejection. The full 67-check run at
`bb180ec` passed, including the policy/native frontier tests, but it does not
validate this later integration correction. New full host/app gates are
required; no smaller-pool device success is inferred from the isolated tests.

## Callback dispatcher diagnostic ownership

In the supplied Teardown game log, callback thread 00ac has PEB 0x11bdf4000
and dispatcher 0xfb6155750. The same log registers that PEB with a private
ntdll at 0xfb6100000 before these callbacks. The thread is using its child's
dispatcher, yet the diagnostic labels it `SESSION THREAD, CHILD DISPATCHER
(BUG)`. Source inspection establishes the labeling error: it compares the
thread PEB against the mutable global `peb`, which child startup changes.
The preceding child-start records show that global drifting between children.
Equality with that global does not establish session-thread identity.

`signal_arm64_ios.c` now checks the selected dispatcher against the existing
ntdll registry keyed by the calling thread's own TEB PEB. Correct child
callbacks no longer produce the false session-corruption label; actual
parent/child/sibling ownership mismatches still produce an explicit warning,
with the expected dispatcher address logged. The dispatch path itself is
unchanged. This fixes diagnostic correctness and does not claim to fix an
unproven corruption path. `check-callback-owner-diagnostic.py` compiles the
production registry lookup and expected-dispatcher helper with ASan/UBSan,
reproducing the mutable-global false positive and checking real mismatches,
same-architecture children and session fallback. Host/native build and new
device evidence were pending when written. All 66 distinct host checks passed
in run 37252063633 at `9d2c6d3`, including the production owner diagnostic
ASan/UBSan check. The native runtime also compiled successfully in run
37251963677, job 111581274860, at `44dd53b`. New device evidence remains
pending. Delivered update 2 predates this correction.

## Completed upload cache reclamation under memory pressure

The supplied Ravenfield run reaches physical footprint 6141 MB; its resource
initializer upload census has a 228 MB peak. These counters do not establish
that all of that peak remained cached. Source inspection does establish that
DXMT's ring allocator keeps ordinary completed blocks for up to 300 completion
cycles regardless of actual process headroom. Its idle initializer also tested
reclamation against the previous cached completion fence before refreshing it.
Both can delay release of temporary buffers after a scene upload.

The DXMT fork adds `dxmt_memory_budget.hpp`, using existing MadeiraCtl operation
7 for measured process headroom. Queries are shared and cached for 250 ms.
Healthy headroom (at least 1536 MB), or an unavailable measurement, preserves
the ordinary lifetime policy. Below 1536 MB the upload/copy/argument rings keep
a two-block reserve; below 512 MB they keep one. `free_blocks` releases only
the completed front of the FIFO, stops at unfinished GPU work, and retains the
newest block under pressure. Freed oversized blocks repay the existing reuse
quota. There is no forced GPU synchronization, texture data loss or release of
resources still referenced by pending GPU commands. The initializer refreshes
its completion fence before idle reclamation. This changes the DXMT command
queue, resource initializer and ring allocator, preserving the generic path.

`check-dxmt-ring-pressure.py` extracts the production ring template and budget
helper, compiles them with ASan/UBSan and exercises pressure thresholds,
recovery/unavailable measurement, query cadence, unfinished fences, latest
suballocation reference lifetime, oversized reuse accounting and ordinary
expiry. Full host and graphics source builds are required before packaging;
their results are pending for this change. This Windows host has no C++
compiler. The already delivered update 2 does not include this change.

The corrected source subsequently passed all 66 host checks in run
37252063633; the downloaded inventories were matched against every check at
`9d2c6d3`, without duplicates/missing checks and with every exit code zero.
The ring-pressure ASan/UBSan probe passed. The graphics/D3D12 source build
passed run 37252061524 with DXMT `b286373`, correcting the initial logger
compile failure below. These gates do not validate the later learned-JIT
changes or physical-device memory/performance results.

The tradeoff is more buffer allocation churn when measured headroom is low;
the retained reserve limits that churn and healthy sessions retain their
previous policy. The change cannot reclaim live textures or fix Ravenfield's
entire memory problem. Adaptive JIT sizing, broader resource reclamation and
three consecutive physical-device map loads remain required. Before/after
footprint and performance measurements are pending.

The initial graphics compile in run 37251751879 rejected the new transition
log: `Logger::info` accepts one formatted string, not variadic arguments.
The call now constructs that string, and the host stub uses the actual
single-string signature so this compile defect cannot be hidden by its stub.
The failed build remains failed; corrected source/host gates must pass.

## Baseline checkout and build constraints

- Source baseline: `willfaust/Madeira` `main` at `bbbf8d0e20fd8b75f433f4a8d2a8eaf8d5571120`, with its pinned Madeira FEX, Wine, DXMT and Dock forks. The fork preserves upstream history and attribution.
- A Windows host can inspect source and PE files, but cannot run Xcode or device gameplay. `docs/BUILDING.md` also lists inputs absent from a clean checkout, including an iOS LLVM build and Microsoft VC runtime files. No IPA or game acceptance result is implied by source checks.

## Steam SDL3 loader failure

### Supplied device architecture evidence and official package comparison

The supplied October 4 PEAK logs, including the 19:10:28 session, now contain
the fork's rejection diagnostic: `SDL3.dll` has `file_machine=014c`, while the
calling process has `current_machine=8664`, `wow_teb=0`, `code=1`. The adjacent
load result is `c000007b`, followed by the SDL3 assertion. This establishes an
x86 DLL being requested by a 64-bit process in these runs, rather than a
correct AMD64 SDL3 image failing PE mapping. The loader's architecture check
correctly rejects that combination; admitting x86 machine code into the x64
process would be an invalid fix. These session logs also accompany a reported
playable PEAK run, so the rejection alone does not prove the game never starts.

All three packages currently pinned in `SteamRuntime.swift` were downloaded
from Valve's HTTPS host and verified against their exact sizes and SHA-256
pins. The January `bins_win32` package supplies an x86 root `SDL3.dll`, SHA-256
`db01ec466db9c4e19cc5fe8c878ac89bc1b6057136432554842b3cd4dca88669`, alongside
the supported AMD64 `steamclient64.dll` (hash `71b391fe...`). Neither companion
package supplies an AMD64 SDL3. The device file hash is unavailable, so package
identity is not inferred solely from the matching machine type.

Independent inspection of Valve's current `steam_client_win64` manifest,
version 1788652215, and its size/SHA-256-verified component packages found:

| Package | Archive SHA-256 | Relevant layout |
| --- | --- | --- |
| `bins_win64.zip.36f5d9202e79ab2aa3e3c5902e84bbd799d31fc0` | `93f5b6bea0267fd85dc8cc823fdab5c5fb55d7f3a1deab0598acefef0e133bce` | AMD64 SDL3, AMD64 steamclient64, x86 steamclient for 32-bit games |
| `bins_codecs_win64.zip.9edc714e8a6f8c2881ac0cfdc2af382070e42c2e` | `5a32e6966666f6246acd2c92b98f1eee52e717d9085fe901c8825df77da48ffb` | AMD64 FFmpeg libraries imported by video64 |
| `steam_win64_steamrow.zip.6f024698857e81681cf673422a8c1a4d06e2be7f` | `5dbc39918056cc8b7815daaa181eb3fa19a264b25dab33f3d1ad631b79ee3bb8` | AMD64 steam.exe |

Its SDL3 hash is `e453238b...` from the earlier local AMD64 inspection below;
its `steamclient64.dll` hash is the already supported September adapter's
`caba4826aa3501039d095aee1843a6bfb270fb43a3ab4455b2d6733223579fee`.
This provides a coherent official 64-bit runtime candidate, including media
dependencies, without a third-party DLL replacement or weakened loader checks.
The fresh-install pins now select these coherent September 64-bit packages,
including codec dependencies, using the already supported exact client adapter.
Before publication the installer checks the AMD64/PE32+ headers of steam.exe,
steamclient64, SDL3, video64 and all six imported FFmpeg DLLs. A synthetic header
test rejects x86, inconsistent optional headers, malformed offsets and truncation.
New host/Xcode gates and real-package extraction validation are pending.
The original installer refused an existing steam.exe, so changing fresh-install
pins alone would not repair the user's prefix. The new publication path checks
all destinations before writing registry or runtime files. Identical current
files are kept; absent files are created; replacement is allowed only when the
existing hash matches the overlapping file in the three verified January
packages. The 51 old-file hashes are metadata, not redistributed binaries.
Unknown files cause a conflict before publication. Every replacement is backed
up under the prefix's `.madeira-steam-runtime-backup/jan2026` directory before
any runtime change. Backups are checked on retry. Files are published atomically,
with steam.exe last; a mixture left by interruption can resume because old and
new verified bytes are both recognized. Each write rechecks quiescence, target
path and the previously inspected bytes, refusing concurrent edits.

`prepareRequiredDockContent` invokes `prepareIfNeeded` after pausing downloads
and before fetching shared content or handing sign-in to Dock. The ten critical
file hashes determine whether preparation can be skipped; a complete correct
runtime is not downloaded again. Games, saves, account folders and unrelated
files are outside the publication plan. Authentication and Valve's exact private
adapter checks are unchanged. This automatic existing-install upgrade still
requires new host/Xcode and device validation. Mixed publication is recoverable,
not a claim of a filesystem-wide atomic transaction. A newer or modified unknown
Steam install is deliberately preserved and reported as a conflict.

The production publisher's filesystem fixture covers complete preflight,
unknown-file preservation, verified backups, interruption after one replacement,
resumed publication, repeat invocation, unrelated saves/account files and a
concurrent edit before commit. CI additionally downloads all six exact old/new
Valve packages, verifies sizes and archive hashes, checks replacement and critical
metadata against their contents, and runs the real production Swift ZIP reader
and AMD64 header gate against the three current archives. The packages remain
ignored runner data; CI uploads diagnostic text, not Valve binaries.
Downloaded Valve binaries remain ignored and are not redistributed in the IPA.

The [public Portal 2 report](https://github.com/willfaust/Madeira/issues/192) records repeated `SDL3.dll` loads returning `0xC000007B`, followed by Steam's `Failed to load "SDL3.dll"` assertion and a crash reporter launch attempt. This establishes the order of failure; it does not identify which PE loader check returned the status. The same status is part of the reported PEAK failure, so this loader path is the first device regression target.

A read-only inspection of a local Valve Steam installation's `SDL3.dll` (SHA-256 `e453238bb31d593a87e7de87f1f5985fa11d2f9ed12a83fc65c9a52857a30118`, dated 2026-09-02) found an AMD64 PE32+ image (`Machine=0x8664`), 4 KiB section alignment and a relocation directory. Its direct imports are KERNEL32, USER32, GDI32, ADVAPI32, SHELL32, OLE32, OLEAUT32, IMM32, SETUPAPI, VERSION, WINMM and HID. It has no direct VC runtime import. This local file has **not** been matched by hash to the failing device copy. `0xC000007B` could still come from machine routing, image mapping or a dependency; the current evidence cannot select among them.

The same local installation's `video64.dll` imports `libavcodec-62.dll`, `libavfilter-11.dll`, `libavformat-62.dll`, `libavutil-60.dll`, `libswresample-6.dll` and `libswscale-9.dll`; all six are present beside it. Their existence on the device and successful loading there remain unverified.

Run `python tools/inspect-pe-imports.py <path-to-SDL3.dll> <path-to-video64.dll>` on the actual Steam runtime to compare hashes, PE machine types and direct imports. The tool prints only file names, hashes and PE metadata. The next loader test must log the precise rejection stage and nested dependency status before changing Wine or Madeira's mapping logic.

The forked Wine loader now emits `[pe-image]` only for invalid-image failures in its ARM64EC path. It distinguishes section creation, architecture validation, view mapping, PE64 conversion and module setup, including the file machine type where available. This is diagnostic instrumentation, **not** an SDL3 fix. The clean native runtime build in [run 37242307604](https://github.com/llucasandersen/Madeira/actions/runs/37242307604) rebuilt ARM64EC `ntdll.dll`; the downloaded binary contains the marker and has SHA-256 `83037726d9e2ed18c9ab1a600cd0a7ce9ba52c07ff9e3495cb2a3cf6b0c260e3`. App packaging and testing with the failing device runtime remain required before changing loader behavior. A component build does not prove that the device log contains these lines.

## Steam launch-option selection

[Issue 174](https://github.com/willfaust/Madeira/issues/174) reports a game whose Steam configuration has entries 1, 2 and 3 but no entry 0. Dock's pinned `launch.c` passed option 0 on every `LaunchApp` and retry; the native parser sorted entries but discarded their numeric keys. The change preserves the key through `SteamLaunchOption` and `SteamDirectStart.Choice`, fetches it before the native Steam session logs off, and passes it to Dock. Dock validates a bounded decimal key and uses it for the initial call and retries. Authentication and entitlement gates remain in place. Host tests cover numbered keys and invalid input. Device verification remains outstanding; the generic option 0 path applies when metadata is unavailable.

## Download baseline

`DepotDownloader.swift` already uses a bounded task group with eight concurrent chunks, a shared `URLSession` and offset based `pwrite` assembly. The claim that its network stage is simply serial is not supported by the current source. Throughput, stage times, CDN behavior and iOS CPU and memory load still need measurement before tuning.

## Child isolation on ntdll-copy failure

Source inspection of `wine_ios_child_main` found a definite isolation violation:
when `ios_jit_copy_module_for_child` failed, boot continued using the session's
shared ntdll image. That image contains the parent's mutable module list and
loader state. Allowing a second pseudo-process to initialize it can corrupt
the parent. This is an unsafe failure path regardless of the game requesting
the child; it has not been established as the cause of the reported Teardown
dispatcher failure.

The boot path now records `copy_child_ntdll` and uses the existing
`CHILD_BOOT_FAIL` exit on copy failure, releasing the child boot lock before
returning. Successful child copies retain their dispatcher-slot repairs and
ARM64EC file-header patch. This does not gate successful helpers or alter the
cross-architecture private-image path. The regression harness compiles the
production copy block and failure macro with an injected failed allocation;
it checks that no translation, dispatcher write or guest entry follows failure,
and that successful EC/native children retain their initialization. Host and
clean native-runtime builds are required. All 62 host checks passed in run
37247596425 at `78f21d1`; downloaded inventories matched exactly, including
the injected failure and successful EC/native paths under sanitizers. The
clean native-runtime job 111568466791 in run 37247598276 passed; its app
packaging is still running. This protects session integrity; it
does not supply missing pool capacity or prove Teardown gameplay.

## Teardown renderer investigation

The application's logged `madeira-d3d12: gate off` came from the optional M1
shader-converter canary in `ContentView.swift`. The `d3d12` setting controls
running that self-test; it does not enable a game's D3D12 renderer. The log now
says this explicitly to prevent mistaking it for renderer selection. Teardown's
[developer changelog](https://teardowngame.com/changelog/) records the D3D12
backend in version 1.5.1, but the exact installed game
build and renderer-selection interface still need verification before applying
an automatic profile. D3D12 gameplay and the reported callback mismatch remain
unverified.

An anonymous query through Valve-signed SteamCMD on October 4, 2026 returned
app-info change number `39450024` and public build `25295735`. Launch option
0 is `teardown.exe`, type `default`, with no arguments. Options 1–5 point to
`teardown64_profile_steam.exe` and are restricted to developer beta branches.
There is no public DX12 launch option in that metadata, so selecting a
different numbered Steam launch entry cannot implement renderer selection.
The isolated query's transcript is retained in
`build/ci-output/steamcmd/teardown-appinfo-current.log`; no personal Steam
account or game-content download was used. The installed device build and
settings still need matching against this public metadata.

## Bomber Crew window investigation

The pinned upstream app already has a bounded restore path in
`Winios.m`'s `winios_census_note_frame`: while the Dock start's window census
is enabled, a visible top-level window whose first show has `WS_MINIMIZE`
receives one posted `SC_RESTORE` and a foreground request. A window shown
normally before being minimized is left alone. The production census harness
in `check-dock-start-screen.py` covers both cases, including the parked
`-32000,-32000` coordinates, and passed in the full host suite.

That path is not general geometry normalization: zero-sized windows are not
marked visible in the census, and a non-minimized off-screen rect is not corrected by
this restore rule. The diagnostic Bomber Crew run must establish the window
style/geometry sequence and whether `[born-minimized]` reports a successful
post. The reported symptom alone does not prove which path failed or that
the existing restore covers this game. No Bomber Crew fix or device pass is
claimed by this source audit.

A further source audit found that only desktop-mode swapchains fed the census
Metal flag. Game-mode swapchains updated the UIKit compositor's separate set
without feeding the launch census. Also, the Metal flag setter ignored windows
not yet listed by WindowPosChanged. This could lose render-window evidence at
startup. The game-mode Wine-thread callback now snapshots current top-level
client geometry through win32u before marking Metal evidence. A zero-sized or
off-screen render window can therefore be recorded without falsely calling it
visible. Child and null HWNDs remain excluded, and UIKit dispatch follows the
Wine query so the main queue never performs this query without a Wine TEB.
The census ABI and normal compositor behavior are unchanged.

The production census harness now exercises swapchain-before-frame ordering,
zero/off-screen geometry, child/null exclusion and preservation of the Metal
flag when a later valid frame arrives. Host and native compilation of this
change are pending. This fixes missing launch evidence; geometry normalization
and the Bomber Crew device acceptance remain unfinished.

The follow-up startup normalization uses the first visible, unowned top-level
game-mode Metal render HWND per process. Child, disabled, tool, modal-framed
and owned dialog windows are excluded. An initially minimized, zero-client-
size or distant off-screen render window is queued for a single repair after
500 ms. Its owning Wine thread consumes the queue from the event pump, outside
WindowPosChanged and outside the registry mutex. It rechecks identity, styles
and geometry; a normal size established during the grace period is preserved.
Minimized windows first receive SW_RESTORE; geometry is queried again because
that call may run application code or destroy the window. Remaining invalid
geometry is normalized to the guest host bounds without activation or z-order
changes. Destroy/session reset clear the bounded registry, and subsequent
swapchain recreation does not reverse a later deliberate minimize.

The production driver-block harness covers grace timing, owner-thread routing,
one repair, later minimization, parked and zero-size windows, restoration,
destruction during restore, valid geometry during the grace period, excluded
windows, changed process identity, secondary windows, tick wrap and bounded
capacity under ASan/UBSan. These checks and the native build are pending.
This is a generic startup repair, with a regression risk that an intentionally
invalid primary render window at initial swapchain creation may be normalized.
Bomber Crew's device run and window/fullscreen/relaunch checks remain required.

## D3D11 memory headroom policy for 64-bit guests

The pinned DXMT already had an automatic large-BC-texture mip policy, but its
default was `kMadeira32BitModule`. Thus a normal 64-bit guest never reached
the measured pressure decision without an explicit setting. The existing
comment describes a scene load increasing footprint from 4.35 GB toward
6.1 GB, but no new device trace has matched that event to this fork's
Ravenfield run. Pointer width is not a useful reason to omit pressure
protection in Madeira's single iOS process.

The preserved-history DXMT fork now enables this existing policy for both
guest widths. It still uses measured headroom through MadeiraCtl op 7, not
an assumed universal process limit. Healthy, unavailable, small, single-mip,
unaligned and ineligible resources remain unchanged; explicit off settings
retain precedence. Only new eligible large BC shader-resource textures under
pressure lose one physical top mip. This can reduce image detail, does not
evict existing textures and does not implement adaptive JIT sizing or general
resource trimming. Existing logical descriptor/subresource handling remains
in the upstream allocation path.

The new host test compiles production configuration and pressure decisions
under both guest-width defaults, with sanitizer checks for pressure/recovery,
explicit off values, unavailable queries, zero/negative thresholds and size/
mip restrictions. All 63 distinct host checks passed in run 37248256151 at
Madeira `f8b0e2b`, including both guest-width memory-policy builds under
sanitizers. The downloaded Linux/macOS inventories matched every host check,
with no missing or duplicate results. The first run, 37248222424, failed on
an incorrect test fixture: halving 4097 produces the aligned dimension 2048.
The corrected fixture uses 2050, whose halved dimension 1025 is unaligned.
This was a test correction, not a production behavior change.

Graphics source run 37248224379 passed with the new DXMT pin `7e2396b`.
Its downloaded artifact passed source-pin, SHA-256 and PE metadata checks.
The diagnostic workflow now verifies and stages the four primary DXMT DLLs,
preserves Wine D3D9, and checks their hashes in the built app provenance.
IPA run 37248837994 at Madeira `c214f95` has been dispatched with that
graphics artifact; packaging is pending. The delivered USB diagnostic
retains the prior graphics binaries.
Ravenfield's repeated map-load acceptance and regressions on other games
still require device tests.

## Verification still required

### Teardown relaunch content wait, October 4 device evidence

The new user-provided USB log supersedes the earlier generic success report
for repeat-launch acceptance: online authentication and entitlement succeeded,
but Valve refused launch with error 17 and retried three times without creating
the game. The current Dock content wait permits six hours of retries. Its
message is not proof that a download is making progress. This failure occurs
before renderer selection; changing the graphics backend cannot explain it.

Valve's retrieved product metadata declares shared installer depot 228989
from owner app 228980 with `sharedinstall=1`. Madeira intentionally excludes
such depots from a game's main folder and size calculation, but did not have
a native preparation step to install them into their owner's common folder.
The later USB transfer supplies Steam's content log. It explicitly records
`required app 228980 not ready` on every relaunch attempt and adds depot 228989
as the dependency connecting that owner to this game. This confirms the exact
required-content blocker; the newly implemented preparation still requires
successful build, host and device verification.

The launch path now resolves the consumer's exact declared shared installer
depots, pauses any active native download before reusing its downloader, and
downloads/verifies each dependency into the owner's own folder before closing
the native connection and transferring the account to Dock. Owner install
records merge previously installed depots and are written only after verified
completion. Metadata bounds, required manifest checks, Steam depot keys,
manifest authorization, checksums, journals and original launch authorization
remain in effect. No Microsoft runtime binaries are added to the repository
or public IPA; dependency content is obtained by the user's Steam session.

The production Steam library harness now checks exact dependency selection,
owner-directory installation and its resulting record. Host run 37249543427
at Madeira `596560f` is pending. Native build and device repeat-launch proof
are still required. Existing game-folder/shared-content tests remain enabled.
The previous census host run 37249027374 failed only its obsolete static
call-count assertion after adding the second frame feed; the assertion now
counts both feeds, with its behavioral and sanitizer checks retained.
The first dependency host run then exposed an incomplete synthetic PICS
fixture: its consumer lacked the required `common` block and failed metadata
parsing before reaching the new install checks. The fixture is corrected in
`399ef52`; its missing-manifest test now checks the specific validation error,
and host run 37250041732 is pending. No failed run is recorded as a pass.

Run 37250041732 subsequently passed the new dependency install, exact-depot,
owner-record, missing-manifest and existing corruption/resume checks, but its
uninstall assertion still expected the entire library to become empty. The new
independent installer app should remain installed after game removal. The
assertion now verifies removal of the game/same-folder owner and preservation
of the separate installer app and folder. This corrects the fixture expectation;
it does not suppress a production uninstall failure.

The memory overlay also assumed a fixed 4096 MB ceiling. It now reads
`jit_available_memory()` (iOS `os_proc_available_memory`) at the existing sample
cadence and shows measured headroom beside physical footprint. Warning colors
use that measured value; the app no longer paints a healthy increased-memory
session red merely because footprint exceeds 4 GB. This is reporting, not
resource reclamation or a Ravenfield survival claim. The supplied run's pool
warmer reports roughly 288 MB head and 160 MB tail usage inside its 896 MB pool;
pool capacity, live translated code and jetsam-charged footprint are distinct
measurements. Adaptive pool sizing still needs implementation and validation.

The earlier supplied game log also creates a native Madeira D3D12 device,
despite importing OPENGL32 through the absent-GL stub. Importing that DLL alone
does not identify the active rendering backend. The log retains dispatcher
warnings that need owner/session identity analysis. Ravenfield's supplied run
reaches physical footprint 6141 MB, while its texture census reports requested
capacity rather than residency (Metal currentAllocatedSize is separately
1689 MB at the last census). Those numbers must not be equated; the footprint
confirms memory pressure, not its complete allocation breakdown.

The first IPA containing the source-built DXMT memory policy passed Xcode,
packaging and macOS codesign gates in run 37248837994. Local ZIP, identity,
SHA-256, runtime and graphics source-pin/hash checks passed for
`Madeira-diagnostic-c214f95.ipa`, SHA-256
`8b667c5e9fe3f84898f640a4abb83fb55abed5540859862d29f5643d81eb32ee`.
It preserves Wine D3D9. This local diagnostic predates dependency preparation
and window normalization, is not the final IPA, and was not copied over the
delivered USB diagnostic.

Clean runner builds also exposed several reproducibility defects, documented
with exact runs in [BUILDING.md](BUILDING.md): an unsupported optional native
telemetry field, omitted FEX inline headers, missing generated DXMT AIR
headers, and an rpmalloc diagnostic referenced when the native allocator is
disabled. The native runtime, corrected header artifact and DXMT archive
now build. The latest FEX allocator guard compiled in native iOS and both
guest source builds; both guest artifacts retain the rpmalloc diagnostic,
and all 59 host checks passed. Native app linking and packaging subsequently
passed in run 37244570613. The verified first diagnostic IPA is available in
[diagnostic release 1](https://github.com/llucasandersen/Madeira/releases/tag/v0.1.3-compat-diagnostic.1)
and on the requested USB stick. These are build corrections, with no game
pass inferred from them. Following delivery, the user reported PEAK working
and believed it fully playable, with much faster Steam downloads. The user
subsequently reported Teardown working flawlessly. The matrix
records this device report separately from build evidence. A successful phone
log and exact installed build remain pending; the report does not identify
the earlier SDL3 failure's root cause or establish every acceptance criterion.
Teardown's successful report likewise does not identify its renderer or explain
the earlier OpenGL/dispatcher symptoms. It is not evidence that later source
changes, which are absent from the delivered IPA, fixed those symptoms.

The clean diagnostic build exposed a source-build defect in the pinned Madeira
FEX fork: `IosFfsBypassLog` and `IosCbEntryLog` were declared under
`FEX_IOS_HOST`, while `CompileBlock` read them outside that condition. The native
iOS core build, which does not enable the Windows guest-runtime hooks, failed
with fourteen undeclared-identifier errors. The fork guards those telemetry
reads with the same condition. This does not change the guest-runtime path.
The next native compile reached the ARM64 helper and exposed an unguarded
Windows `VirtualQuery` diagnostic. That query is now restricted to Windows;
native builds retain the address and alignment report. Neither correction
changes CASPAL emulation. The native iOS FEX build passed in
[run 37234579200](https://github.com/llucasandersen/Madeira/actions/runs/37234579200),
using Madeira `980371c` and FEX `259f3ba7f`. The app build and device run are
still pending; this component build does not establish gameplay compatibility.

The loader fix needs a test against the exact failing SDL3 PE, host loader tests and a signed device run showing Steam stays alive and creates the game process. Gameplay, DXMT, input, sound, Steam authentication and repeat launch checks follow that. Teardown, Ravenfield, Bomber Crew and download acceptance checks are tracked separately in the matrix. No root cause or fix is claimed for those yet.
