# Game compatibility test matrix

## October 6 test build 8 phone results and renderer correction

The latest Teardown export identifies source `273813a`. The driver reports
requested GL 1.0, actual GL 2.1, GLSL 1.20. It records one Vulkan present and
again faults on the game null read at `teardown.exe+0x5df216`. Later context
messages are suppressed by Wine's four-message debug-string rate limit.
The requested legacy context alone does not prove the game's later requests.
However, the pinned backend independently lacks transform feedback and
geometry-shader support, which Zink needs to expose higher GL versions.
It cannot meet Teardown's published OpenGL 4.5 requirement.

The automatic profile now requires adequate GL capability as well as bundled
files. Revision 4 returns Teardown to D3D12 instead of automatically selecting
this inadequate OpenGL backend. This is a renderer-selection correction;
missing D3D12 terrain/tools remain unresolved. RDR2's animated loading stall
also remains unresolved. The newest export contains no newer RDR2 run.
The subsequent RDR2 export also identifies source `273813a` and shows
the signer installed the app as `App.app`. The cleanup matched only
`Madeira.app`, so a previous OpenGL session's Vulkan links survived in
`sysx64`. RDR2 loads those DLLs despite its preserved `-dx12` argument,
then asserts in `vkDestroyQueryPool` and terminates the child. Subsequent
fixed-base image faults follow that termination. Its footprint is about
2.2 GB; this is not evidence of RAM exhaustion. The cleanup now recognizes
the actual installed bundle name and both prior distribution names, while
preserving ordinary files and unrelated application links. Regression checks
execute the production Foundation code with original, renamed and custom
bundle names, native/EC roots, dangling upgrades and D3D12 session switches.
This targets the new pre-intro failure; the earlier animated loading stall
still requires phone confirmation and remains unresolved.

No gameplay pass or final repair is claimed. See the
[OpenGL record](DESKTOP_OPENGL_IOS.md) for primary references and limitations.

## October 6 diagnostic test build 8: actual OpenGL capabilities

Verified on USB: `E:\Madeira-Teardown-Context-Test-8\Madeira-diagnostic-273813a.ipa`.
Source: `273813aa21876233b162472faae681fa4b15becf`; size: 95,952,213 bytes;
SHA-256: `01f10ce8fe57e8e9d95cfe9bce61613ff12bd245b57a68f908d69a5b8cf9d7d0`.

The new scoped `env.MESA_DEBUG = 1` phone run on test 7 reports
`GL_INVALID_ENUM in glGetIntegerv(pname=GL_NUM_EXTENSIONS)` and the same
first null read at `teardown.exe+0x5df216`. This does not establish whether
the query ran in an initial legacy context or the required game context.
No missing backend feature or causal connection to the crash is proved.

Test 8 logs the requested and actual WGL context version/profile, GLSL
version, context creation failures and missing Mesa OpenGL 3.0 gates.
Logging is enabled by `MESA_DEBUG`; it does not override versions, enable
unsupported features or change rendering behavior. Keep Automatic
compatibility and `env.MESA_DEBUG = 1`, then export the new full phone log.
Teardown terrain/tools, stability and RDR2 menu/Story progression remain
unconfirmed. This is a diagnostic build, not a final repair; the goal is open.

All 87 exact-source host checks pass without sanitizer diagnostics in
[37553880854](https://github.com/llucasandersen/Madeira/actions/runs/37553880854).
The Windows OpenGL component and iPhone Vulkan ABI bridge compile in
[37553878897](https://github.com/llucasandersen/Madeira/actions/runs/37553878897).
App packaging passes in
[37553913023](https://github.com/llucasandersen/Madeira/actions/runs/37553913023).
The six targeted Mac checks from 37546113080 have identical corresponding
app/runtime inputs. Reused native runtime 37540738924 and native OpenGL
37538235752 inputs were compared and verified; XAudio2 matches working test 5
apart from rebuild timestamps. Package provenance, all seven OpenGL runtime
hashes and all nine USB file hashes pass. RDR2 retains test 7's runtime and
profile; no new RDR2 loading repair is claimed. No bulk game copy was made.

## October 6 test build 7 phone results: acceptance failed

The supplied `E:\Madeira\fex-jit-dump.bin` is 939,524,096 bytes. Bounded reads
of its compiled blocks match the first crash instruction. The game caller at
RVA `0x887f40` loads a member at `+0x2200`, calls the getter at `0xd8910`
(`+0xe8`), then the getter at `0xa37d0` (`+0x10`). That zero return becomes the
input to the constructor at `0x5df210`, which dereferences it at `0x5df216`.
The compiled getter instructions preserve 64-bit pointers. Object types and
the cause of the missing data remain unproved; no game binary was patched.
The pool's original game-image copy is not the runtime-decrypted guest code
at these locations, so it cannot replace the compiled-block evidence.

RDR2's `ml981` profiler reads the frame's entry RIP, which can be stale while
translated code runs. Its concentrated `0x132cc623` bucket does not prove a
fixed spin loop. The exact thread sampler resolves varied current RIPs in
that worker. Requested a Teardown run with scoped `env.MESA_DEBUG = 1` to
enable the release OpenGL driver's existing error output. The user has no
game-native logs or RDR2 `system.xml` available and confirms an animated
loading spinner. No new repair is claimed from the dump alone.

The supplied `logs 5/RDR2.exe-2026-10-06_18-57-50.txt` and
`logs 5/teardown.exe-2026-10-06_19-06-42.txt` both identify IPA source
`5887d285908e0e490934439967e1db259c7fb277`. The user reports a visible,
audible RDR2 intro followed by indefinite loading, and Teardown intro audio
with a white screen followed by a crash. Neither game passes acceptance.

RDR2's log covers about 504 seconds and reaches at least 28,800 D3D12 presents,
with continued roughly 59 FPS submission near the end. GPU command-buffer
reports show zero errors. Footprint reaches about 4,958 MB; video budget trims
from 2,048 to 1,740 MB. The main thread repeatedly waits in `NtDelayExecution`
while a guest worker consumes about one CPU core. Repeated SMC/SIGBUS messages
also occur; their presence alone does not establish an unhandled fatal fault
because successful self-modifying-code recovery is logged in the same paths.
The stall's root cause is unresolved. GPU submissions do not prove menu or
Story progress or correct images on screen.

Teardown now logs all four `sysx64` GL/Vulkan links, loads Mesa
`libgallium_wgl.dll` and the native Wine Vulkan ABI bridge, and records one
successful Vulkan present. It then faults at about 36 seconds: the exact
reconstructed guest RIP is `teardown.exe+0x5df216`, reading a byte through
null `RDX` (`44 0f b6 0a`). The stale State.RIP still names Mesa code and is
not the faulting game instruction. The existing generic R10 operand diagnostic
does not prove a lost pointer high half for this instruction. Subsequent
crash-reporting/process cleanup faults must not be substituted for this first
game fault. Its origin and the white-screen cause remain unresolved.

Requested the game's own Teardown error output and RDR2's generated
`Settings/system.xml`, plus the last visible RDR2 screen. The USB was
disconnected during investigation. No new repair IPA has been built from
these observations, and test 7 must not be described as a confirmed fix.

## October 6 combined test build 7 delivery

Verified on USB: `E:\Madeira-RDR2-Teardown-Test-7\Madeira-diagnostic-5887d28.ipa`.
Source: `5887d285908e0e490934439967e1db259c7fb277`; size: 95,951,300 bytes;
SHA-256: `ebcb2f77f40a107c6d13aec5e2866d54ffbe0e45e6be4a530eff492c67625a73`.

Test 6's supplied RDR2 log (`madeira-log 14.txt`) runs for about 130 seconds
without game presents. Its footprint stalls near 2,175 MB, below the reported
6,144 MB process allowance. The new globally staged Vulkan PE DLLs load before
native faults and internal child exits; the waiting wrapper remains alive.
This run does not establish RAM exhaustion or the exact fault mechanism.
The phone reports 11,694 MB physical RAM. The 2,048 MB setting is video memory,
not the total process allowance; the Windows minimum-memory warning can remain.

Teardown's supplied log (`madeira-log.prev 15.txt`) selects OpenGL but its
AMD64 child loads the old Wine GL-absent stub through `sysx64` under a native
Steam root. The later pixel-format error is a user report without a new log.
Test 7 links all four GL/Vulkan PE components into the AMD64 child farm after
normal seeding, and also into `system32` for ARM64EC roots. Vulkan PE DLLs are
confined to the OpenGL package and linked only for OpenGL sessions. Prior
bundle-owned links are cleaned, including old global Vulkan links; user files
are preserved. This restores RDR2's prior D3D12 dependency setup. Both changes
remain candidates pending phone acceptance.

All 87 distinct checks pass at the exact IPA source in
[37546112592](https://github.com/llucasandersen/Madeira/actions/runs/37546112592),
with zero raw/effective exits and no sanitizer diagnostics. All six targeted
Mac checks pass in
[37546113080](https://github.com/llucasandersen/Madeira/actions/runs/37546113080),
including executed Foundation prefix routing, reinstall cleanup and user-file
preservation. App compilation, signing and packaging pass in
[37546112953](https://github.com/llucasandersen/Madeira/actions/runs/37546112953).
Native runtime inputs match the reused successful run 37540738924; unchanged
graphics source remains 37404589105. Native OpenGL source remains 37538235752,
Windows components 37537462947, and the updated iPhone Vulkan bridge compile
and presentation regression 37540738727. Package provenance, all seven OpenGL
runtime component hashes, and all nine USB file hashes pass. XAudio2 matches
the working test 5 component apart from rebuild timestamps.

Fully close Madeira, re-sign and install using the same account/App ID prefix,
enable JIT, and keep Automatic compatibility enabled with RDR2 video memory
on Auto. Test RDR2 through the intro into Story, then Teardown terrain, tools,
sound and repeat launch. Export source-stamped logs. Gameplay is unconfirmed
and the goal remains unfinished. Game archives remain on E: without bulk copies
to F: or game-file modifications.

## October 6 combined test build 6 delivery

The combined RDR2 memory and Teardown desktop OpenGL candidate is verified on
USB at `E:\Madeira-RDR2-Teardown-Test-6\Madeira-diagnostic-d4aa1dc.ipa`.
Source is `d4aa1dcbec439c41718ecdb125f7e60ec9ee7bc6`; size is 95,950,798 bytes;
SHA-256 is `2b20f7992229923daf6e8f995dd83454c98647d0eb2dbedacabe777c487d5d5f`.

All 86 distinct host checks pass at this source in
[37540738773](https://github.com/llucasandersen/Madeira/actions/runs/37540738773),
with zero raw/effective exits and no sanitizer diagnostics. The updated native
Vulkan bridge compiles for iPhone and its failed-present/concurrent-counter
regression passes in
[37540738727](https://github.com/llucasandersen/Madeira/actions/runs/37540738727).
Fresh runtime compilation, app build, signing and packaging pass in
[37540738924](https://github.com/llucasandersen/Madeira/actions/runs/37540738924).
The previously passed pinned graphics and OpenGL components are verified by
source comparison and staging hashes. The final IPA includes all seven OpenGL
runtime files; package/provenance checks and all nine USB file hashes pass.
XAudio2 matches the working test 5 component apart from rebuild timestamps.

RDR2's Auto video-memory setting receives a 2,048 MB budget, retaining native
pressure trimming and explicit nonzero choices. Recognized direct imports
receive the profile. Teardown's automatic profile selects the bundled OpenGL
candidate on iOS 26. Successful Vulkan submissions update launch/FPS observers;
failed submissions cannot dismiss the launch screen. This proves submission
accounting, not correct images on the phone.

Re-sign and install as an update with the existing signing account/App ID
prefix, then enable JIT. Test RDR2 through the intro into Story; test Teardown
terrain, tools, sound, stable gameplay and repeat launches. Export full logs
with the new source stamp. Both gameplay outcomes and the overall goal remain
unconfirmed. Game archives remain unchanged on E:, without bulk copies to F:.

## October 6 intro memory error and Teardown OpenGL work

The new RDR2 phone log is test build 5. It passes the previous child-runtime
startup failure, creates D3D12 and presents frames. The user reports an
out-of-memory error while loading the intro. The supplied `exit_file.dat`
confirms `ERR_GFX_D3D_DEFERRED_MEM`. The log shows a 6,144 MB process limit,
about 4,879 MB peak footprint, and an automatic video-memory budget falling
from 1,024 MB to 768 MB. No successful Story gameplay is established.

The candidate applies a 2,048 MB video-memory budget when RDR2's setting is
Auto, including a recognized direct import. Explicit nonzero settings and the
native pressure trim remain. No unprovided `system.xml` is fabricated. This
is a candidate for the observed error, not a proven root-cause conclusion.

Five targeted Mac checks pass in
[37537646486](https://github.com/llucasandersen/Madeira/actions/runs/37537646486).
The complete regression run and fresh combined IPA are still being built.

The user resumed Teardown work and requested desktop OpenGL. The source-built
Windows Zink DLLs and native Wine bridge pass in
[37537462947](https://github.com/llucasandersen/Madeira/actions/runs/37537462947).
The iOS Metal4 backend, Khronos Vulkan loader and actual Mac loader/ICD
dispatch pass in
[37538235752](https://github.com/llucasandersen/Madeira/actions/runs/37538235752).
Component staging also passes locally. The [OpenGL candidate](DESKTOP_OPENGL_IOS.md)
still requires iPhone feature and gameplay checks, including terrain, tools,
sound and repeat launch. Teardown is no longer deferred.

The final combined IPA has not yet been delivered to USB. Game archives remain
on E: and are not part of the app build. The goal remains unfinished until
physical-device acceptance.

## October 6 RDR2 test build 5 delivery

The latest phone log is still test build 3 (`madeira-log 12.txt`). It reaches
the required child image address, then fails private-ntdll startup before
graphics. Test build 5 includes the template retention correction and preserves
the requested `-dx12` argument that Launcher.exe drops when restarting RDR2.
Explicit child renderer choices and automatic compatibility opt-out remain
effective. Windows child startup information and Unix argv receive the same
command line; caller process parameters remain unchanged. Existing settings
are backed up, and missing settings are not fabricated. Game files remain
unchanged on E: with no bulk copy to F:.

All 85 distinct host checks pass in
[37482398582](https://github.com/llucasandersen/Madeira/actions/runs/37482398582)
at `d4f52fa`, with no sanitizer diagnostics. Its production runtime/app source
matches IPA source `e159c2c`; later changes isolate a test fixture, exclude
internal session state from the configuration catalog and record evidence.
Five targeted Mac checks also pass in
[37481321943](https://github.com/llucasandersen/Madeira/actions/runs/37481321943).
Fresh native runtime, app build, signing and packaging pass in
[37481013995](https://github.com/llucasandersen/Madeira/actions/runs/37481013995).
Unchanged graphics/Common-Controls source artifacts remain run 37404589105.
Audio matches the earlier working component apart from rebuild timestamps.
IPA provenance/component checks and all seven USB file hashes pass.

Diagnostic IPA: `E:\Madeira-RDR2-Test-5\Madeira-diagnostic-e159c2c.ipa`
(88,241,733 bytes), SHA-256 `3b72ba7c6c1694509a8ee9aa62ee5b65ee81875f57bc41173c30bb68905bd6ce`.
Install as an update using the same signing account/App ID prefix. Keep the
imported game folder and `env.MADEIRA_WAIT_CHILDREN = 1`, enable JIT and launch
the existing RDR2.exe with automatic compatibility. Export the complete new
log and report whether menu/story gameplay, visuals, audio, input and a second
launch work. Phone acceptance remains pending; this is not a final gameplay
pass, and the active goal remains open. Teardown stays deferred.

## October 6 RDR2 renderer handoff and test gates

The latest phone log (test build 3) fails private runtime startup before any
graphics device or presents. Test build 4 on USB retains the needed ntdll
template; its phone result remains pending. The same log shows that the
initial `-dx12` argument disappears when Launcher.exe restarts RDR2.exe.
Production source `e159c2c` preserves that requested renderer in the child
Windows command line, respecting explicit child choices and automatic
compatibility opt-out. It also releases the Wine argument parser's scratch
buffer and checks allocation failure. No game files were changed.

Five targeted Mac checks pass in run 37481321943 at `34a527f` with identical
production source: template lifetime, socket cleanup, actual Wine parser and
renderer helper, XML settings adapter and library launch environment.
Run 37481326596 passes 84 of 85 distinct host checks with no sanitizer
diagnostics; only the generated catalog check failed. Source `d4f52fa` keeps
internal session policy out of user settings; its local catalog check passes.
Full run 37482398582 is pending. Fresh native runtime compilation passes in
IPA workflow 37481013995; app packaging remains pending. Phone menu/story
gameplay, audio/input and repeat launch remain unverified.

## October 6 targeted runtime host evidence

The full host run 37472160091 later timed out during compiler downloads, before Linux tests started.
To validate the two changed runtime paths independently, macOS ARM64 run
[37477610396](https://github.com/llucasandersen/Madeira/actions/runs/37477610396) passes
the production template helper/image-reload harness and the process socket
ownership/teardown harness under ASan/UBSan/TSan. Eight image-reload modes and
both socket sanitizer runs are checked in the downloaded artifacts, without
sanitizer diagnostics. The template assertions exercise containing allocation
promotion, default/private/stale mappings and unrelated allocation ownership.
Root teardown assertions exercise one-time template retention and cleanup order.

Initial macOS attempts failed before execution on an omitted SDK path, then
Apple's unsupported leak-detection option. The workflow now selects the macOS
SDK; the harness retains address/UB/thread checks on Darwin and leak detection
on Linux. Production runtime source at `5166038` matches IPA source `df29649`;
the differences are CI, documentation and that platform sanitizer option.
The test-build-4 IPA on USB is unchanged; its README records this evidence.
This is a two-check host result, not an 84-check or phone gameplay pass. The
full gate and phone test remain pending, and the goal is not complete.

## October 6 RDR2 template correction: device test pending

Log `madeira-log 12.txt` confirms test build 3 retires the old executable and
maps generation 2 at `0x140000000`. Boot then fails at `copy_child_ntdll`:
the default ntdll template's pool allocation was reclaimed with the initial
process. Test build 4 (`df29649`) preserves only that default template's
containing allocation before initial-process cleanup. Private child copies
and the launcher's other allocations retain their existing owners.

Fresh native runtime and IPA build 37472164121 passed at `df29649`. Package
provenance, component hashes, linked preservation marker and all seven USB
copies passed. Host run 37472160091 remains in progress: Apple job passed,
Linux job still preparing its compiler/headers; no 84-check pass is claimed.
The diagnostic IPA is available for phone testing while that gate continues:
`E:\Madeira-RDR2-Test-4\Madeira-diagnostic-df29649.ipa`, 88,238,956 bytes,
SHA-256 `a54634968d4eb4151f6c064c2547ab2dfffda761e95cc21962a53fd5136279f5`. Its README explicitly records the pending gate.
The phone test request is pending. Runtime boot, graphics initialization,
menu/story gameplay and repeat launch remain unverified; the goal is active.
This is not a completed release. The imported game stays unchanged, and
Teardown remains deferred. Do not retransfer the game for this app update.

## October 5 RDR2 initial-process cleanup follow-up

Phone log `madeira-log 11.txt` confirms test build 2 (`b680d5a`) registers the
preferred image as OWNED and binds the original process PEB. The original
RDR2 process exits normally, but the initial-process branch of
`process_exit_wrapper` only reports its status and closes the server socket.
It skips the image retirement and owner reclamation performed for children.
The old image remains mapped at `0x140000000`; the relaunched image is still
at `0xe40000000`. No graphics device or presents occur after two minutes.
Loader critical-section timeout records also remain; gameplay has not started.

The initial-process branch now claims teardown once, retires its own fixed
image while its server connection is live, closes only its master descriptor,
releases owner caches/windows, reclaims owner pool allocations and publishes
image readiness. Shared NULL-owner runtime copies survive. The production
socket ownership harness checks this order with real descriptors, concurrent
duplicate initial-process exits and unrelated descriptor reuse, in addition
to its existing child ownership and generation cases under ASan/UBSan/TSan.
This follows the existing child teardown model; peer-thread quiescence and
other loader/activation defects are not established as solved by host tests.

All 84 distinct host checks pass at `f5fbc36` in
[37410965039](https://github.com/llucasandersen/Madeira/actions/runs/37410965039).
Fresh native runtime and IPA build/signing/package
[37410967290](https://github.com/llucasandersen/Madeira/actions/runs/37410967290)
pass at the same source. Graphics/Common-Controls artifacts are unchanged
from verified 37404589105. IPA provenance and component hashes, controls CHPE
metadata and ordinal 345, and all seven USB copies are verified. Rebuilt audio
matches the previous binary after excluding COFF/debug build timestamps.
Test build 3 is on
`E:\Madeira-RDR2-Test-3\Madeira-diagnostic-f5fbc36.ipa`, 88,239,804 bytes,
SHA-256 `acc7a261eaf1f786aa6e9bae47ebb10ad59062da34ed4bee460bc1768a79e55d`.

Install as an update using the same signing identity. Keep the imported game
folder, `env.MADEIRA_WAIT_CHILDREN = 1`, automatic compatibility and JIT, then
launch RDR2.exe. Phone startup, graphics initialization, menu/story gameplay,
audio/input, sustained play and repeat launch remain pending. RDR2 is not
declared playable or complete. Teardown remains deferred and unresolved.

## October 5 RDR2 launcher handoff and fixed image claim

The latest phone log (`madeira-log 10.txt`) confirms that
`env.MADEIRA_WAIT_CHILDREN = 1` keeps the launcher session alive. The original
RDR2 process exits normally and Launcher.exe starts another RDR2.exe. That
process stalls before a graphics device is created. The game is already
imported; 58GB remaining free space does not require another transfer.

The preferred image claim is recorded with host-page size `0x73c4000`, while
the mapping commit receives Windows-page size `0x73c2000`. Exact size matching
leaves the claim in CLAIMING, without an owner available for retirement. The
second image maps at `0xe40000000` instead of `0x140000000`; this executable
has no relocation directory. The native commit helper now rounds the size to
host page boundaries, with overflow rejection, before matching the interval.
The production helper test covers these exact values, 4KB/16KB hosts, wrong
intervals, rollback, overflow and owner readiness under sanitizers.

All 84 distinct host checks pass at `b680d5a` in
[37408456325](https://github.com/llucasandersen/Madeira/actions/runs/37408456325).
Fresh native runtime and app/signing/package build
[37408458321](https://github.com/llucasandersen/Madeira/actions/runs/37408458321)
passes at the same source. Unchanged graphics and Common-Controls artifacts
come from verified 37404589105 at `4916501`. IPA provenance, source/component
hashes, controls CHPE metadata and ordinal 345, and all seven USB file copies
are verified. Test build 2 is on
`E:\Madeira-RDR2-Test-2\Madeira-diagnostic-b680d5a.ipa`, 88,239,821 bytes,
SHA-256 `ba013cc3967435f023063dd080243ae035f9e55a5f905fa4eb4e75afd5fbe00c`.

Install as an update with the same signing identity, keep the imported game
folder and `env.MADEIRA_WAIT_CHILDREN = 1`, enable JIT and launch RDR2.exe.
No game archives were copied to F: or modified. This fixes the identified
claim bookkeeping defect; successful phone startup, graphics initialization,
menu/story gameplay, audio/input, sustained play and repeat launch remain
unverified. Teardown's visual issue remains deferred and unresolved.

Target device: iPhone18,2, iOS 26.6.2, Memory+ active, StikDebug JIT, no extended virtual address entitlement. Record the exact IPA SHA-256, device build, game build, Steam client file hashes, Madeira log and repeat count for each run. A blank result is not a pass.

## October 5 current priority: direct RDR2 import

The user deferred Teardown and requested RDR2. The current E: folder has
276 files totaling 128,167,940,440 bytes; no game archives were copied to F:.
The earlier pre-import log (`madeira-log 7.txt`) reported 59GB free.
The game is now imported; earlier folder and storage observations below are historical.
The current AMD64 executable has no relocations and occupies 121,378,816
bytes at 0x140000000, within the existing protected 128MiB image window.
Its standard direct imports resolve in the game folder or existing Wine farm,
except comctl32 ordinal 345: TaskDialogIndirect belongs to version 6.
Its embedded manifest explicitly requests AMD64 Common-Controls 6.0.
The new candidate builds pinned Wine comctl32_v6, stages it with authenticated
artifact hashes, and seeds the AMD64 side-by-side store every session.
The x86 assembly store remains separate. Default direct launch adds `-dx12`
and existing settings receive the backed-up DX12 API edit.
RDR2 test build 1 is verified on USB:
`E:\Madeira-RDR2-Test-1\Madeira-diagnostic-028c48b.ipa`, 88,239,176 bytes,
SHA-256 `a8ac9a4a732abf458d9d934c0c4f21567f4b9433a8c33c6a3e096d1d6c237677`.
All 84 distinct host checks pass in 37405316787 at `83ae131`; the follow-up
changes only a test fixture. Graphics and controls build 37404589105 passes
at `4916501`. The DLL has ARM64EC CHPE metadata and a real TaskDialogIndirect
export at ordinal 345. IPA build/signing 37405134953 passes at `028c48b`,
whose only difference from graphics source is the staging header check.
Source/module hashes, packaged controls, update identity and USB copy hashes
pass. The private standard import/export audit on E: has no remaining checked
export gaps when Common-Controls v6 assembly redirection is applied.
Local game DLLs were checked for presence; their activation paths were not
changed or validated. Phone follow-up confirms the v6 DLL loads; the
startup stall and next test are recorded above. No menu/story pass is established.

Candidate 9 phone follow-up: terrain and tools remain invisible; audio works.
`madeira-log 5.txt` confirms `dcde6b1` and NaN-to-zero off. Candidate 10 adds
integer volume lowering with Teardown session defaults and explicit overrides.
All 83 host checks pass in 37397386359 at `b5f91cc` (host fixture follow-up only;
identical production code). Graphics 37396683612 and fresh converter/app/
signing/package 37396758237 pass at `0a3f3c8`. Unchanged native runtime is
reused from verified 37392506691. Local/USB checks pass:
`E:\Madeira-Compatibility-Update-10\Madeira-diagnostic-0a3f3c8.ipa`,
87,614,225 bytes, SHA-256
`a3ead869ad0b6a7dd526621d7ad73861aa2e6eb1cabc4baf0c898ab9b0c3c245`.
Visible world/tools, sustained play and relaunch acceptance remain pending.
Candidate 10 fails visual acceptance on the phone. Setting
`msc-bounds-check = 0` does not restore terrain or tools. The latest gameplay
log confirms source `0a3f3c8`, bounds checking off and cache hits throughout.
The copied cache contains voxel fragment shaders with integer 3D reads and
bounds checking off. The remaining voxel data/binding failure is unresolved.
RDR2 phone startup attempts are recorded above; the complete goal remains open.
The [candidate-10 prerelease](https://github.com/llucasandersen/Madeira/releases/tag/v0.1.3-compat-diagnostic.10)
has the exact app source tag and all six public/USB asset sizes and digests match.

October 5 candidate-8 phone follow-up: the user confirms working Teardown sound,
but terrain/voxels/tools remain invisible. The new log has source `88b8218`;
compound replay works, nonzero geometry draws occur, and foreground summaries
show no GPU errors or skipped draws. Candidate 9 corrects the converter's
float-payload default and adds bounded volume-input captures. Native Metal
payload probe 37392477416 passed on the hosted paravirtual GPU; it does not test
the converter or this phone. All 82 host checks (37392477348), graphics
(37392477354) and fresh native/app/package gates (37392506691) passed at
`dcde6b1`, including strict macOS codesign. Local and USB verification passed:
`E:\Madeira-Compatibility-Update-9\Madeira-diagnostic-dcde6b1.ipa`,
87,609,479 bytes, SHA-256
`363c4cf839e5abc843cd8532d8c543a7671f9ef14f96892dbc105ae496652c4d`.
Teardown visual/sustained/relaunch acceptance and the whole goal remain open.
The [candidate-9 prerelease](https://github.com/llucasandersen/Madeira/releases/tag/v0.1.3-compat-diagnostic.9)
has the exact app source tag and all six asset sizes/digests match the USB copy.

October 5 candidate-7 follow-up: the source stamp is `8ed43f9` and the 12GB
arena is installed. The user reaches gameplay but reports invisible voxels,
terrain and tools, with no audio. The log identifies skipped compound indirect
draw signatures and missing `xaudio2_9.dll`. Candidate 8 implements their
renderer/audio paths and adds RDR2 startup/settings preparation. Corrected
graphics source build 37388280813 and native job 112024366813 passed;
all 81 final host checks passed in 37389190309 at `2eb39bc` (two fixture-only
assertion fixes after app source `88b8218`). App/package job 112028007240
passed in 37388596153, including strict macOS codesign. Local and USB package
verification passed for candidate 8 at `E:\Madeira-Compatibility-Update-8`:
`Madeira-diagnostic-88b8218.ipa`, 87,605,635 bytes, SHA-256
`18a6fb47b267e653a8289f8a4bfd87c3349c0efe25a33fdfbc3c21630c94a140`.
The actual package includes the new rendering/audio components and 12GB marker.
Physical acceptance remains pending.
The [candidate-8 prerelease](https://github.com/llucasandersen/Madeira/releases/tag/v0.1.3-compat-diagnostic.8)
has the exact app source tag; all six uploaded asset sizes and digests match USB.
RDR2 has not been run on the phone. Its complete E: folder is 128,156,672,448
bytes, while the latest phone log reports 60GB free. No large game copy was made.

October 5 candidate-6 phone follow-up: the source stamp is `7257ae1`.
D3D12 presents frames, then gameplay freezes. The 8GB FEX-only arena
`[0xb30000000,0xd30000000)` is exhausted; worker 0230 fails emulator
initialization with `c0000017`. Its creator 0194 holds a Steam lock while
waiting for the worker's startup event, blocking Steam thread 0050 and the
game's IPC reply. A new candidate first attempts a 12GB constrained arena,
retaining the explicit cap and smaller fallback reservations. All 80 host
checks and real Valve archives passed in 37379694983 at `fcf847a`; downloaded
inventories have zero raw/effective exits and no sanitizer diagnostics.
`fcf847a` changes only the fixture's stub types from runtime source `8ed43f9`.
The initial 37378789850 run failed that fixture compilation and is not accepted.
Fresh native job 111994980332 and app job 111999716612 passed in 37378793318,
including strict codesign. Local and USB package/source/identity/provenance
checks passed; the app binary contains the new reservation marker.
Candidate 7 is delivered at
`E:\Madeira-Compatibility-Update-7\Madeira-diagnostic-8ed43f9.ipa`,
87,414,539 bytes, SHA-256
`a00c15268fb1a98e1fa65eda534b35eb417269a0c71690f7d2d24e4a7fadf83d`.
The [candidate 7 prerelease](https://github.com/llucasandersen/Madeira/releases/tag/v0.1.3-compat-diagnostic.7)
has the exact runtime source tag; all five remote asset sizes and SHA-256
digests match the verified USB copies.
This is a capacity repair candidate; sustained phone gameplay and relaunch
remain required before final acceptance. No private log is committed.

Latest startup-crash candidate: `7257ae1`, with per-process late-alias
registrations. Full 79-check host workflow 37319437329 passed at `dd2f973`;
downloaded inventories and sanitizer logs are clean. `dd2f973` changes only
the fixture extraction from the runtime/app source at `7257ae1`. Initial
37318424980 failed that extraction and is not accepted as a full pass.
Fresh native job 111791000983 and app job 111796486469 passed in 37318428523,
including strict codesign. Local and USB package/source/identity/provenance
checks passed; the app binary contains the callback-retirement marker.

Candidate 6 is delivered at
`E:\Madeira-Compatibility-Update-6\Madeira-diagnostic-7257ae1.ipa`,
87,414,514 bytes, SHA-256
`a297b30dac9b6c899396548ab7d6c61baea1aa8e8472a91586a896f5f8a4cfe4`.
The [candidate 6 prerelease](https://github.com/llucasandersen/Madeira/releases/tag/v0.1.3-compat-diagnostic.6)
is for crash retesting. Candidate 5's actual phone log confirms content ready
and D3D12 device creation but startup access violations. The main-thread fault
producer remains unverified; candidate 6 now has initial rendering followed by
the separately identified arena-exhaustion freeze above.

Previous completed host validation: all 79 checks and real Valve archives passed
at `7301473` in 37279302920. Downloaded inventories match every distinct check,
with zero raw/effective exits and no sanitizer diagnostics. This includes the
actual native control transfers, cache/record preservation and refused depot
keys, alongside all earlier native/loader/window/memory/download regressions.

Previous completed app validation: workflow 37279305970 and app job 111663398759
passed at `7301473`, including strict macOS codesign verification. The package
reuses the unchanged native runtime verified at `889c6be` in 37274760178.
Local and USB ZIP/CRC/identity/runtime/graphics/source-stamp/checksum checks
passed. The IPA is 87,414,822 bytes, SHA-256
`b894ed3bce43fcb03f5cdb34dd55c6743913d8102c4d6e62349932284a69bd15`.
This adds the owned native control, read-only cache handling, immediate
background cancellation and installed-game access to candidate 4. No new
physical gameplay, throughput or complete native peer shutdown proof is inferred.

Earlier source work at `4c0d431` adds the owned-depot phone native-control
measurement and a 79th actual-source host check. Targeted 37278109635, full
host 37278126945 and app 37278129844 passed. Downloaded host inventories match
all 79 distinct checks with zero raw/effective exits and no sanitizer diagnostics;
the native control fixture observed 72 successful requests and peak concurrency
eight. No package from this source was delivered: the follow-up at `7301473`
disables retained manifest-cache publication, cancels directly on background
entry and exposes the controls for installed owned games. Full host 37279302920
and app 37279305970 passed for that source. The app reuses the unchanged
verified native runtime from 37274760178. The superseded intermediate app runs
37278775828 and 37279072888 were requested to cancel after real source changes;
cancellation is not an app-build pass. USB candidate 5 was the previous
verified delivered package; the new phone crash export and candidate 6 supersede
its pending Teardown test request.

The cache-preservation follow-up at `e0f8dda` passed all 79 checks and real Valve
archives in 37278773557. Downloaded inventories match that source with zero
raw/effective exits and no sanitizer diagnostics. The actual owned-library
ASan harness reports cache and install-record preservation and refused-key
enforcement for the new control method. This proof predates the later background
observer and installed-game menu changes, which passed their complete gates
above. Physical checks remain required.

Earlier completed host validation: all 78 checks and real Valve archives passed
at `889c6be` (37274755529). Downloaded inventories match that full test tree,
with no missing or duplicate checks. This includes native exit records,
callback delivery, exact selected-game/host generation correlation and stale
file-tail delivery, synchronized image-owner publication and scalar Mach LSE
alias atomics and native ARM paired stores, alongside the existing sanitizer
fixtures, explicit Mach FP/LR/SP scalar writeback/pre-index cases and the
runner's recovering-sanitizer integration. Every raw and
effective exit is zero, with no sanitizer diagnostics. Fresh native compilation
at `889c6be` passed in job 111649257006 of workflow 37274760178, including the
scalar register/pre-index follow-up. Its app job 111652524468 also passed;
physical device acceptance remains unverified.

Earlier completed app validation: workflow 37274760178 passed at `889c6be`,
including app job 111652524468 and strict macOS codesign verification. It uses
the fresh native runtime from the same workflow and source commit above.
Local ZIP/CRC/identity/runtime/graphics/source-stamp checks passed, SHA-256
`8600b07540c57783e61777ac63086a7a30e63706cf0e6a9209d96128ebf58670`.
The IPA is 87,374,598 bytes, includes native launch/exit correlation, image
ownership synchronization, scalar Mach LSE atomics, integer paired stores
and the explicit scalar register/pre-index follow-up,
and has no new physical
acceptance results. Automatic renderer selection, 10-minute/relaunch behavior,
repeated map loads and final delivery remain unverified.

The later Mach LSE alias change at `5d10bb3` passed its targeted ASan/UBSan and
TSan checks (37269300151), full 76-check suite and fresh native compilation.
Its app/package gates passed (37269302622). The subsequent integer paired-store
change at `343028f` passed corrected native ARM ASan/UBSan and TSan fixtures
at `17776be` (37271658156), with terminal logs checked for sanitizer errors.
The initial fixture's recovering UBSan result is not accepted. Full 77-check
suite 37271658528 passed with exact inventories and clean native ARM logs;
fresh iOS workflow 37271515195 passed. `17776be`
changes only tests/docs from the runtime/app sources built at `343028f`.
No new device result
or final USB delivery is inferred from these builds.

Earlier completed source validation: all 73 distinct checks and real Valve
archives passed at `e0835ca` (37261593279). Fresh native socket changes compiled
at `4503b36` (37261069251); complete app/package/signing gates at `e0835ca`
passed (37261594883). Local package checks passed, SHA-256
`b034dbf2409aef16360a7f51af6a2c7f764c7422eec2eb1760ab85294f73bf2e`.
The new automatic Teardown profile uses the supplied registry schema; its
74-check/app gates and physical renderer/10-minute/relaunch acceptance remain
pending. This is not a final release or a new USB delivery.

Earlier source validation: all 68 distinct host checks passed at `a5669ae`
(run 37253512089); its Xcode/IPA build passed (run 37253514108). The downloaded
package passed ZIP, identity, runtime and graphics provenance checks, SHA-256
`c02e208064f6d41ad3014cad7146600df6d6449893f00aa9b158ff97676a8288`.
This locally retained diagnostic has no new device acceptance results and
does not replace the delivered USB update 2 or constitute the final release.

At `4666116`, all 69 distinct host checks passed in run 37255530422. The
downloaded Linux/macOS inventories matched every repository check without
omissions or duplicates. This includes the actual Wine machine gate, coherent
fresh-install runtime pins, AMD64 header guard, launch-stage deadlines and
loader rejection parsing. Its IPA run 37255532583 passed Xcode/Metal/package
gates; local ZIP, identity, runtime and graphics provenance verification passed
for `Madeira-diagnostic-4666116.ipa` (87,305,193 bytes), SHA-256
`d206888d0da7b6f8915c38fe3491634bc3ab3faf5cb439677995a1f652a2174f`.
That local diagnostic predates automatic existing-runtime upgrades and the
real-archive CI gate introduced at `4acba7a`. It supplies no new device result
and has not replaced USB update 2. The later upgrade requires its own gates.

| Target | Required device result | Current evidence | Status |
| --- | --- | --- | --- |
| PEAK, app 3527290 | Steam stays alive; PEAK.exe created; menu, single-player level, DX11/DXMT, audio, input, authentication and repeated launches | User reports PEAK worked and believes it is fully playable; USB transfer now includes PEAK session logs; exact installed build and individual acceptance results pending | Gameplay success reported; detailed acceptance pending |
| Teardown, app 1167630 | Automatic D3D12 selection; visible voxels/terrain/tools, audio, level, ten minutes, close and relaunch | Candidate 8 audio works on the phone, but terrain/voxels/tools remain invisible despite active compound replay and nonzero draws | Candidate 9 preserves float texture payloads and adds bounded input captures; all 82 host and graphics/native/app/USB gates pass; visual/ten-minute/relaunch acceptance pending |
| RDR2, additional USB import requirement | Direct imported executable; actual DX12 device, menu/story gameplay, audio/input, sustained play and relaunch | Game imported; v6 controls load; child-session handoff works, then relaunched image stalls before graphics; whole 128GB folder inspected on E: with no bulk copy | Test build 3 fails private runtime boot; test build 5 diagnostic on USB retains the template and renderer request; 85 host checks pass; phone startup/gameplay remains pending |
| Ravenfield | Three consecutive match loads and scene changes below the device memory ceiling | Supplied session log reaches physical footprint 6141 MB; no three-match survival result on the updated package | Memory pressure confirmed; updated device acceptance pending |
| Bomber Crew | Visible primary window from Steam; switching, fullscreen and relaunch | Reported zero size and off-screen Unity window; no new device run | Not tested on this fork |
| Steam downloader | Median throughput at least 70% of direct same-CDN `URLSession` control when CPU is not limiting; resume and corruption checks | User reports much faster Steam downloading; no measured device/native-control comparison | Improvement reported; benchmark pending |
| Existing working games | Representative Steam, D3D9, D3D11, D3D12, 32-bit and 64-bit smoke and regression runs | Selection pending | Not tested on this fork |

Host tests and a source build are separate gates. They do not stand in for the device results above.

## Original-scope completion audit, October 5, 2026

This audit retains all eleven original requirements, plus RDR2. Candidate 8 is a tested
build for collecting missing evidence; it does not establish completion.

| Original requirement | Current authoritative evidence | Remaining gate |
| --- | --- | --- |
| 1. PEAK and Valve runtime | Coherent Valve runtime upgrade, actual PE machine/dependency fixtures, real archive checks, native/app builds and user report of earlier gameplay | Exact updated-package log; Steam survival, executable creation, single-player, audio/input, authentication, networking where supported and repeated launches |
| 2. Teardown renderer/content/children | Candidate 8 audio confirmed; indirect replay active, but geometry invisible. Candidate 9 shader policy/capture and all build gates pass | Verify visible world/tools, ten minutes and relaunch; native peer-thread resource lifetime remains under audit |
| 3. Ravenfield memory | Consumed learned JIT budgeting, measured footprint/headroom and source-built completed-resource ring trimming; host fixtures and graphics/app build | Three consecutive matches, scene changes, safe measured memory headroom and performance on the target phone |
| 4. Bomber Crew windows | Compiled owner-thread primary-window repair, startup grace and actual-source sanitizer fixtures preserving dialogs and later minimization | Real Steam start, visible game window, switching, fullscreen/windowed transitions and relaunch |
| 5. Steam downloads | Production adaptive concurrency, connection reuse/CDN selection, network/decode/write/hash/CPU/resume instrumentation, integrity fixtures and owned native-control measurement in candidate 5 | Measured same-CDN native-control comparison, roughly 70% median target when CPU is not limiting and actual device resume/update behavior |
| 6. General compatibility profiles/review | Default generic path, user opt-out and consumed Teardown profile; documented upstream report/source comparison and generic native store fixes | Device validation of consumed policy; exclusive-store reservations and unrelated reported secondary-launcher failures remain separate unresolved findings |
| 7. Steam robustness/UI | Coherent runtime dependencies, exact optional-helper gate, bounded launch stages and generation-correlated game/Steam-host creation/exit diagnostics, compiled Swift/native fixtures | Device proof that the client and optional-component/helper paths preserve launch; new logs must establish exact failure/stage attribution if a run fails |
| 8. Target iPhone/address/JIT correctness | Preserved address-map architecture; package requests JIT/Memory+ and has no extended-VA entitlement; native ARM and iOS compilation | Re-signed installation and actual iPhone18,2/iOS 26.6.2 execution, StikDebug JIT, measured memory behavior and exception delivery |
| 9. Regression/component gates | Exact 81-check Linux/Apple inventories at 2eb39bc, raw/effective exits zero, no sanitizer diagnostics; actual source renderer/native components and app/package/USB gates passed at 88b8218 | Representative previously working games, actual target-device regressions and any further changed subsystem gates |
| 10. Fork/docs/build/IPA | Preserved fork/submodule histories, licenses, clean worktree, documented clean build, verified package with no private signing identity, exact-source GitHub prerelease and checksum-verified USB copy | Final acceptance report and final release after the remaining required results; diagnostic publication is not final acceptance |
| 11. Definition of done | Source, host/component build, test package, prerelease and USB candidate gates have evidence | All game/device/benchmark results above and final release; overall completion is unproven |
| Additional RDR2 request | Direct launch/settings preparation, static dependencies and full E: folder-size inspection; no bulk copy | Sufficient phone storage, actual API/activation/startup, story gameplay, audio/input and repeat launch |

The October 5 USB crash export is stamped `7301473` on iPhone18,2/iOS 26.6.2.
It verifies JIT/Memory+, required-content completion, Valve-client game creation
and D3D12 device creation, followed by startup access violations. It is failure
evidence, not gameplay acceptance. The native-control JSON and other physical
gates remain pending. New results must be tied to the exact source/checksum.

## Historical component build verification

At Madeira `9d2c6d3`, all 66 distinct host checks passed in
[run 37252063633](https://github.com/llucasandersen/Madeira/actions/runs/37252063633).
The downloaded inventories match all checks at that commit, including the
production ring-pressure and callback-owner diagnostic sanitizer probes.
The corrected graphics source build passed
[run 37252061524](https://github.com/llucasandersen/Madeira/actions/runs/37252061524),
with DXMT `b286373`. The callback diagnostic compiled in the native runtime
job of run 37251963677. The later learned-JIT pool sizing and headroom refresh
at `bb180ec` require their new 67-check run and native/app gates; those are
pending. These changes are absent from the delivered USB update 2, and no
new game/device acceptance pass is inferred.

At Madeira `e6e9b2311b09a187e503dd69968b9f177f5de56c`, all 64 distinct host
checks passed in [run 37250480384](https://github.com/llucasandersen/Madeira/actions/runs/37250480384).
Downloaded Linux/macOS inventories match every repository `check-*.py`,
without missing or duplicate results and with every exit code zero. This
includes the corrected shared-installer install/uninstall fixture, exact
required-depot selection, missing-manifest refusal and the production window
repair sanitizer tests. Earlier failed fixture runs remain failed.

The native runtime containing the primary-window repair compiled successfully
in [run 37249781579](https://github.com/llucasandersen/Madeira/actions/runs/37249781579).
The matching latest app compiled and packaged successfully in
[run 37250535597](https://github.com/llucasandersen/Madeira/actions/runs/37250535597),
including macOS ad-hoc codesign verification. It includes the required Steam
content preparation, paused-download resume, source-built DXMT memory policy,
window repair and measured headroom overlay. Device acceptance remains pending;
adaptive JIT sizing and broader resource reclamation are still unfinished.

## Diagnostic package delivery

Test candidate 5 is copied to
`E:\Madeira-Compatibility-Update-5\Madeira-diagnostic-7301473.ipa`, with checksum,
source/graphics provenance and installation/test instructions. The USB copy
passed the package verifier with the exact source commit and checksum above.
The [candidate 5 prerelease](https://github.com/llucasandersen/Madeira/releases/tag/v0.1.3-compat-diagnostic.5)
is published at exact source commit `7301473`. All five remote asset sizes and
server SHA-256 digests match the USB files; draft=false and prerelease=true were
verified through the GitHub API. The updated Teardown log and native control
JSON were requested for this package. Private USB logs remain dated October 4;
the complete goal/final release and remaining runtime findings are not resolved
by this delivery.

Test candidate 4 is copied to
`E:\Madeira-Compatibility-Update-4\Madeira-diagnostic-889c6be.ipa`, with checksum,
source/graphics provenance and installation/test instructions. The USB copy
passed the package verifier with the exact source commit and checksum above.
This is the latest package for new phone tests; candidate 3 predates the scalar
register/writeback/pre-index follow-up. The app/helper identities and update
signing requirements are unchanged. The full goal is not complete: device
acceptance, measured download comparison and remaining native lifetime findings
still require evidence and work.
The [candidate 4 prerelease](https://github.com/llucasandersen/Madeira/releases/tag/v0.1.3-compat-diagnostic.4)
is published at exact source commit `889c6be`. Its five remote asset sizes and
server SHA-256 digests match the USB files; draft=false and prerelease=true
were checked through the GitHub API. Teardown acceptance was requested against
this specific package. The supplied logs remain dated October 4.

Test candidate 3 is copied to
`E:\Madeira-Compatibility-Update-3\Madeira-diagnostic-3e94179.ipa`, with checksum,
source/graphics provenance and installation/test instructions. The USB copy
passed the package verifier with exact source commit and checksum above. It
contains the coherent runtime repair, automatic Teardown renderer profile,
learned JIT and staging trim policies, and the subsequent native ownership,
exit correlation and store fixes missing from update 2. It retains the existing
app identity for updating with the same signing account/App ID prefix.
New phone logs have been requested for Teardown's content preparation,
ten-minute gameplay and relaunch. This is an acceptance-test candidate;
the complete goal and final release remain pending the device gates.
The [candidate 3 prerelease](https://github.com/llucasandersen/Madeira/releases/tag/v0.1.3-compat-diagnostic.3)
is published at exact source commit `3e94179`. All five uploaded asset sizes
and server SHA-256 digests match the USB IPA, checksum, provenance, graphics
metadata and README; the release is a published prerelease rather than a draft.

Update 2 packages `Madeira-diagnostic-e6e9b23.ipa` from the verified source
commit above. Local package checks and the copy at
`E:\Madeira-Compatibility-Update-2` passed ZIP CRC, bundle/helper identity,
runtime hashes, graphics source pins/hashes and SHA-256 checks. Its SHA-256 is
`d323b016a6239a34cbb6182bf288c7a8d05170eb49fbedd6b96434373215c92e`.
Version 0.1.3/build 100 and the upstream bundle identity are retained for
re-signing over an existing installation with the same account/App ID prefix.
The original USB diagnostic and supplied user logs are preserved. This package
is ready for sideloading and device tests; it does not complete the full goal.

[Diagnostic release 1](https://github.com/llucasandersen/Madeira/releases/tag/v0.1.3-compat-diagnostic.1)
contains `Madeira-diagnostic-e6f6a2c.ipa`, version 0.1.3/build 100, from
Madeira `e6f6a2c`. The package identity/checksum/runtime checks passed,
including verification of the USB copy at `E:\Madeira-Compatibility-Test`.
Its SHA-256 is
`c02c67e857a9995821b3bd14b32ee71b8e846936c947b91fb7962fe8d3fc89ee`.
The CI build passed Xcode linking and macOS codesign verification. Phone
gameplay subsequently received the user report below; the exact installed
IPA and a complete successful PEAK launch log remain to be confirmed.

## User device report, October 4, 2026 (America/Chicago)

After diagnostic delivery, the user reported that PEAK worked, then clarified:
"yes fully playable I believe also downloading speed is much faster on steam too".
This records reported playable gameplay and a perceived download improvement.
Audio, controls, single-player mode, repeat launches and networking were not
confirmed individually. No diagnostic log, installed IPA checksum or measured
throughput accompanied the report. It does not establish why the earlier SDL3
failure cleared or whether the downloader meets the native-control target.

The user subsequently reported: "teardown works flawlessly super good okay so
teardown works now". This records reported successful Teardown gameplay.
The renderer, installed IPA/game build, ten-minute run and close/relaunch were
not confirmed individually, and no successful log accompanied the report.
The earlier OpenGL and dispatcher symptoms are no longer the latest device
result; their root cause and the reason they cleared remain unverified.

The user then clarified that Teardown ran once but subsequent launches remain
at the required-content message. The supplied October 4 log shows successful
online authentication, requested-app entitlement/listing, launch refusal 17
and three retries without a game process. No successful renderer evidence is
present in this failing run. The later USB log transfer supplied Steam's
content log: it explicitly names required app 228980 as not ready, and records
the dependency from depot 228989 to Teardown. Its earlier game log records a
Madeira D3D12 device being created. This establishes the dependency behind the
relaunch refusal and earlier backend initialization, not a ten-minute/relaunch
pass. Ravenfield's supplied run reaches physical footprint `fpMB=6141`; no
three-match survival result is established.

## Host regression evidence

On Madeira `980371c`, [Linux run 37234581507](https://github.com/llucasandersen/Madeira/actions/runs/37234581507)
ran all 59 existing host checks: 56 passed and three failed on missing host
modules. `check-jit-network.py` requires Swift Darwin;
`check-steam-cloud.py` requires Swift CryptoKit; `check-steam-library.py`
requires Python 3.14's `compression` package.
These failures establish an unsuitable test environment, not passing results.
Mac run 37235072729 passed the JIT network and Steam Cloud checks, but exposed
that the Steam library harness provides Linux compression/crypto shims which
conflict with the Apple SDK. The updated workflow runs the two Apple checks
on macOS and the remaining 57 on Linux, using Python 3.14 for both. The
complete combined result passed in
[run 37235206418](https://github.com/llucasandersen/Madeira/actions/runs/37235206418)
at Madeira `2e4dd32`: 57 Linux checks and two macOS checks, all exit zero.
The downloaded result artifacts were compared to every `check-*.py` in the
repository: 59 distinct checks, with no missing or duplicate entries.
The Steam library/depot harness compiled production download code and ran its
install, interruption/resume, update, corruption, ownership, shared-depot,
uninstall and refusal phases under AddressSanitizer. This establishes host
regression coverage; it supplies no real CDN/device throughput measurement.

After the decoder stage/retry timing change, all 59 checks passed again in
[run 37236100223](https://github.com/llucasandersen/Madeira/actions/runs/37236100223)
at Madeira `c76fd42`. Both downloaded result inventories were checked against
the repository's complete host check list. The known decoder vectors use the
measured pipeline; checksum rejection, corruption recovery, interruption,
resume and update behavior remain covered by the production-code harness.

After the native diagnostic counter and compile-failure gate change, all 59
checks passed in
[run 37242309362](https://github.com/llucasandersen/Madeira/actions/runs/37242309362)
at Madeira `a793ece`. The downloaded Linux and macOS result artifacts again
matched all 59 repository checks, without duplicates or missing entries.
These host results do not validate the native iOS compile or phone gameplay.

After guarding FEX's rpmalloc snapshot diagnostic with the allocator option,
all 59 host checks passed in
[run 37244575135](https://github.com/llucasandersen/Madeira/actions/runs/37244575135)
at Madeira `e6f6a2c` / FEX `b28076559`. The downloaded Linux/macOS inventories
again matched all 59 distinct repository checks, all exit zero.
