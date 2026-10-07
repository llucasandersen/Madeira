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
native loader/ICD and all four Windows GL/Vulkan DLLs, and supplies a relative ICD
manifest and upstream licenses. The IPA build signs the native libraries and
records their final hashes. Package verification requires all seven runtime
files and checks those hashes.

Test build 8's iPhone log reports a requested legacy 1.0 context, actual
OpenGL 2.1 and GLSL 1.20. Later context messages are hidden by Wine's existing
four-message OutputDebugString rate limit; absence is not evidence that no
later request occurred. Independently, the pinned KosmicKrisp source does not
advertise `VK_EXT_transform_feedback` or `geometryShader`. Mesa's
[Zink requirements](https://docs.mesa3d.org/drivers/zink.html) need the former
for GL 3.0 and the latter for GL 3.2. The backend cannot meet Teardown's
[published GL 4.5 requirement](https://teardowngame.com/faq.html).

Automatic selection now requires both bundled components and sufficient
OpenGL capability. The pinned backend's capability is 2.1, so Teardown's
revision 4 profile selects D3D12 and updates only its validated renderer
settings. Original backups, audio choices and other settings are preserved.
This corrects selection of an inadequate renderer; it does not resolve the
earlier D3D12 terrain/tools failure. The experimental OpenGL components remain
bundled for explicit development sessions. No version override or invented
feature is used. RDR2 continues to use D3D12; its loading stall is unresolved.

All four PE components (`opengl32.dll`, `libgallium_wgl.dll`, `vulkan-1.dll`
and `winevulkan.dll`) are packaged in `x86_64-opengl`, outside the default
ARM64EC DLL farm. After ordinary prefix farms are seeded, OpenGL sessions
link them into `sysx64`, including AMD64 games started by native Steam roots.
ARM64EC roots also receive the links in `system32`. Every session first clears
prior bundle-owned GL/Vulkan links, including old global Vulkan links and
dangling links after reinstall. User files and unrelated links are preserved.
This prevents RDR2's D3D12 sessions from discovering the newly bundled Vulkan
PE components through the default farm.

Test 6's phone log showed Teardown selecting OpenGL but loading the Wine
GL-absent stub through `sysx64`. The user's later report of no suitable pixel
format is consistent with that path; that particular run has no supplied log.
Test 7 corrects the links. Context creation and correct images still require
phone acceptance.

## Acceptance still required

Successful Vulkan swapchain submissions advance the front end's combined
D3D/OpenGL presentation counter. Failed submissions do not dismiss the launch
screen. This also supplies OpenGL FPS observations; it does not prove that the
submitted image contains correct game geometry or that it appeared on glass.

An actual iPhone launch must show the backend and supported OpenGL version,
terrain and tools, stable sandbox gameplay, working audio and a second launch.
Compiler success and a Mac loader smoke check do not satisfy these gates.
The final IPA cannot be described as a confirmed fix before those checks.
