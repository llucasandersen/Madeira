# Changelog

## Unreleased

- Add per-depot Steam chunk stage timing and a device throughput measurement protocol. No speed improvement is claimed yet.
- Add ARM64EC PE loader stage diagnostics to the pinned Wine fork to locate the Steam SDL3 invalid-image rejection in a device log. This does not yet resolve that failure.
- Preserve Steam's numbered launch entry through the native library and Madeira Dock so games without entry 0 can be submitted to Valve's client with their selected Windows entry. Host and device verification status is recorded in `docs/COMPATIBILITY_OVERHAUL.md`.
- Add a read-only PE import inspector and initial compatibility evidence and test matrix.
