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
requires Python 3.14's `compression` package and Apple Swift modules.
These failures establish an unsuitable test environment, not passing results.
The updated workflow runs those three checks on macOS and the remaining 56
on Linux, using Python 3.14 for both. The complete combined result is pending.
