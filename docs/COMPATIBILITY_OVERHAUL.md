# Compatibility overhaul: investigation record

This is the evidence ledger for the iPhone 17 Pro Max / iOS 26.6.2 compatibility work. It records what has been verified and keeps hypotheses separate from fixes. The acceptance tests in [GAME_TEST_MATRIX.md](GAME_TEST_MATRIX.md) remain required.

## Baseline checkout and build constraints

- Source baseline: `willfaust/Madeira` `main` at `bbbf8d0e20fd8b75f433f4a8d2a8eaf8d5571120`, with its pinned Madeira FEX, Wine, DXMT and Dock forks. The fork preserves upstream history and attribution.
- A Windows host can inspect source and PE files, but cannot run Xcode or device gameplay. `docs/BUILDING.md` also lists inputs absent from a clean checkout, including an iOS LLVM build and Microsoft VC runtime files. No IPA or game acceptance result is implied by source checks.

## Steam SDL3 loader failure

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
