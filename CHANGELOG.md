# Changelog

## Unreleased

- Guard FEX's optional rpmalloc snapshot diagnostic with the allocator build option. Native Apple builds disable rpmalloc; guest builds retain the diagnostic. Native linking and guest regression builds are being verified.
- Retain FEX's generated inline configuration headers in CI artifacts and generate DXMT's three AIR helper headers before standalone iOS compilation. The corrected FEX artifact and native DXMT compile passed; complete IPA packaging is pending.
- Add isolated source builds for Wine ARM64EC, ARM64 WOW64, Wine/DXMT i386, both FEX guest modules and DXMT graphics. Preserve Wine's tracked D3D9 renderer and rebuild its missing Bluetooth dependency. Component evidence and remaining device gates are recorded in `docs/BUILDING.md`.
- Separate Steam chunk decryption, decompression and checksum timing, and include failed-attempt stage time and retried payload bytes in completed-depot measurements. Throughput improvement remains unmeasured.
- Restrict FEX's Windows memory-region query to Windows builds while retaining native misaligned CASPAL diagnostics.
- Guard FEX's iOS guest-runtime telemetry reads in native builds to match the condition on their declarations. The clean macOS build exposed undeclared counters in `Core.cpp`; the ARM64EC guest path retains its existing instrumentation.
- Add a macOS diagnostic IPA build workflow and remove the prebuilt archive requirement from full Wine server and DXMT Unix builds. Clean runner verification is in progress.
- Add per-depot Steam chunk stage timing and a device throughput measurement protocol. No speed improvement is claimed yet.
- Add ARM64EC PE loader stage diagnostics to the pinned Wine fork to locate the Steam SDL3 invalid-image rejection in a device log. This does not yet resolve that failure.
- Preserve Steam's numbered launch entry through the native library and Madeira Dock so games without entry 0 can be submitted to Valve's client with their selected Windows entry. Host and device verification status is recorded in `docs/COMPATIBILITY_OVERHAUL.md`.
- Add a read-only PE import inspector and initial compatibility evidence and test matrix.
