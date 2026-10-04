# Game compatibility test matrix

Target device: iPhone18,2, iOS 26.6.2, Memory+ active, StikDebug JIT, no extended virtual address entitlement. Record the exact IPA SHA-256, device build, game build, Steam client file hashes, Madeira log and repeat count for each run. A blank result is not a pass.

| Target | Required device result | Current evidence | Status |
| --- | --- | --- | --- |
| PEAK, app 3527290 | Steam stays alive; PEAK.exe created; menu, single-player level, DX11/DXMT, audio, input, authentication and repeated launches | Reported Steam SDL3 `0xC000007B` blocks process creation; exact loader cause unknown | Not tested on this fork |
| Teardown, app 1167630 | Automatic D3D12 selection; menu, level, ten minutes of play, close and relaunch | Reported OpenGL stub and child dispatcher failures; no new device run | Not tested on this fork |
| Ravenfield | Three consecutive match loads and scene changes below the device memory ceiling | Reported DXMT texture and JIT pool pressure; no footprint trace for this fork | Not tested on this fork |
| Bomber Crew | Visible primary window from Steam; switching, fullscreen and relaunch | Reported zero size and off-screen Unity window; no new device run | Not tested on this fork |
| Steam downloader | Median throughput at least 70% of direct same-CDN `URLSession` control when CPU is not limiting; resume and corruption checks | Source already has eight concurrent chunk tasks; no device benchmark | Not measured |
| Existing working games | Representative Steam, D3D9, D3D11, D3D12, 32-bit and 64-bit smoke and regression runs | Selection pending | Not tested on this fork |

Host tests and a source build are separate gates. They do not stand in for the device results above.

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
