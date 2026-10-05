# Game compatibility test matrix

Target device: iPhone18,2, iOS 26.6.2, Memory+ active, StikDebug JIT, no extended virtual address entitlement. Record the exact IPA SHA-256, device build, game build, Steam client file hashes, Madeira log and repeat count for each run. A blank result is not a pass.

| Target | Required device result | Current evidence | Status |
| --- | --- | --- | --- |
| PEAK, app 3527290 | Steam stays alive; PEAK.exe created; menu, single-player level, DX11/DXMT, audio, input, authentication and repeated launches | User reports PEAK worked and believes it is fully playable; successful log and exact installed build pending | Gameplay success reported; detailed acceptance pending |
| Teardown, app 1167630 | Automatic D3D12 selection; menu, level, ten minutes of play, close and relaunch | User reports one successful run, then an indefinite content wait; USB log confirms authenticated/entitled launch refusal 17 and repeated retries | Relaunch failure confirmed; shared-installer preparation under test |
| Ravenfield | Three consecutive match loads and scene changes below the device memory ceiling | Reported DXMT texture and JIT pool pressure; no footprint trace for this fork | Not tested on this fork |
| Bomber Crew | Visible primary window from Steam; switching, fullscreen and relaunch | Reported zero size and off-screen Unity window; no new device run | Not tested on this fork |
| Steam downloader | Median throughput at least 70% of direct same-CDN `URLSession` control when CPU is not limiting; resume and corruption checks | User reports much faster Steam downloading; no measured device/native-control comparison | Improvement reported; benchmark pending |
| Existing working games | Representative Steam, D3D9, D3D11, D3D12, 32-bit and 64-bit smoke and regression runs | Selection pending | Not tested on this fork |

Host tests and a source build are separate gates. They do not stand in for the device results above.

## Diagnostic package delivery

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
present in this failing run. Steam content logs and install manifests are
absent from the USB export, so the exact dependency refusal remains unproven.

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
