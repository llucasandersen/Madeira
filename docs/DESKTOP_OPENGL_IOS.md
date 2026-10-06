# Desktop OpenGL iOS candidate

This is development work for the user's Teardown rendering failure. It is not
yet a verified Teardown fix or an iPhone OpenGL conformance result.

## Components

Windows Mesa Zink translates desktop OpenGL to Vulkan. Wine's ARM64EC
`vulkan-1.dll` and `winevulkan.dll` bridge Vulkan calls into the native iOS
runtime. The Khronos loader dispatches to Mesa KosmicKrisp, which translates
Vulkan to Metal 4. Wine's iOS display driver supplies a retained CAMetalLayer
for the game's HWND. The same display mapping is used by DXMT.

The source inputs are pinned:

| Component | Source |
| --- | --- |
| Mesa | 26.2.4 archive, SHA256 `bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9` |
| Vulkan loader | `f703f919c30c5b67958d35d40a4297cb3823ed78` |
| Vulkan headers | `9a0f3099c8a9607a7c0f3127d8abfdc19a93e8c5` |
| Wine | Tracked submodule pin; staging rejects a different pin |

Mesa's iOS patches use the system default Metal device and the existing Metal
surface code. iOS advertises FIFO presentation; macOS retains its immediate
presentation path. No OpenGL version override or fabricated GPU feature is
used. Mesa upstream [documents KosmicKrisp](https://docs.mesa3d.org/drivers/kosmickrisp.html) as a macOS backend; this
iOS port requires its own device acceptance.

The candidate requires iOS 26 and AMD64 games. The Wine Vulkan wow64 table is
not enabled: its guest pointers still need conversion to Madeira's guest
window. Older iOS versions retain the existing renderer profile.

## Packaging and selection

Both source workflows must pass before `stage-opengl-artifacts.py` accepts
their artifacts. It checks the component source and Wine pins, copies the
native loader/ICD and the two Windows GL DLLs, and supplies a relative ICD
manifest and upstream licenses. The IPA build signs the native libraries and
records their final hashes. Package verification requires all seven runtime
files and checks those hashes.

When all components are bundled on iOS 26, Teardown's automatic profile
selects the OpenGL candidate. Its existing, validated version 2.1.0 settings
file changes only `gfxapi` to zero; `d3d12support`, audio and other choices are
preserved. The original settings backup remains. A missing or unsupported
settings file is not replaced with a guessed schema. The native OpenGL DLL
policy and prefix links apply to that session. Compatibility opt-out remains
available. RDR2 continues to use D3D12.

## Acceptance still required

An actual iPhone launch must show the backend and supported OpenGL version,
terrain and tools, stable sandbox gameplay, working audio and a second launch.
Compiler success and a Mac loader smoke check do not satisfy these gates.
The final IPA cannot be described as a confirmed fix before those checks.
