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

## Bomber Crew window investigation

The pinned upstream app already has a bounded restore path in
`Winios.m`'s `winios_census_note_frame`: while the Dock start's window census
is enabled, a visible top-level window whose first show has `WS_MINIMIZE`
receives one posted `SC_RESTORE` and a foreground request. A window shown
normally before being minimized is left alone. The production census harness
in `check-dock-start-screen.py` covers both cases, including the parked
`-32000,-32000` coordinates, and passed in the full host suite.

That path is not general geometry normalization: zero-sized windows are not
shown in the census, and a non-minimized off-screen rect is not corrected by
this restore rule. The diagnostic Bomber Crew run must establish the window
style/geometry sequence and whether `[born-minimized]` reports a successful
post. The reported symptom alone does not prove which path failed or that
the existing restore covers this game. No Bomber Crew fix or device pass is
claimed by this source audit.

## Verification still required

Clean runner builds also exposed several reproducibility defects, documented
with exact runs in [BUILDING.md](BUILDING.md): an unsupported optional native
telemetry field, omitted FEX inline headers, missing generated DXMT AIR
headers, and an rpmalloc diagnostic referenced when the native allocator is
disabled. The native runtime, corrected header artifact and DXMT archive
now build. The latest FEX allocator guard compiled in native iOS and both
guest source builds; both guest artifacts retain the rpmalloc diagnostic,
and all 59 host checks passed. Native app linking is still pending. These
are build corrections, with no game pass inferred from them.

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
