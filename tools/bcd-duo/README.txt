Unofficial BCD 623 Duo compatibility candidate, 2026-10-30

This is based on the user's BCD.ipa, version 0.1.623, from BCD by thebcd69:
https://github.com/thebcd69/bcd-games/releases/tag/v0.1.623
BCD is based on Madeira by Will Faust and its contributors. The app's original
licence copies and notices are preserved. This is not an official BCD release.

WHAT CHANGED
The original main binary's SDK load-command declaration is changed from 26.2
to 27.1 to opt into Duo's resizable layout. Its executable code and existing
entitlement blob are preserved. A separate, SDK-27.1-built BCDDuo.dylib tracks
the current application window, updates Metal host scale and reflows BCD's
known touch windows within that scene. It keeps the existing Metal layer and
guest render resolution. It creates no external-display scene; system AirPlay
mirroring is retained. Audio route types are logged without receiver names.

This is a binary compatibility patch, NOT a full SDK 27.1 rebuild of BCD.
The original SDK/compiler Info.plist fields remain truthful. SDK declaration
changes alone do not prove native compatibility. The UIKit integration fixture
checks library loading and layout for four display spaces, but does not run BCD
games, verify physical fold transitions, JIT, AirPlay or receiver audio.

INSTALL
Use your usual sideload/signing tool to re-sign and install BCD-Duo.ipa.
Use the same signing account, App ID prefix and bundle ID as your existing BCD
to install as an update. Keep your data; do not uninstall first. The identifier
remains com.willfaust.madeora; the home-screen name marks it unofficial.
The main signature is stale after patching and must be replaced during signing.
Its original entitlement blob is retained so the signer can read it; verify
the installed app still has the memory allowance and JIT setup you normally use.

Keep your working BCD game settings. No game recopy or cache reset is needed.
Enable JIT as usual, then launch a game and verify a save/mission transition.
Fold, unfold and rotate while playing. Check picture, touch alignment, menus
and sound. Next use Control Center > Screen Mirroring; test video/audio and
disconnect/reconnect. Keep the phone active. Physical acceptance is pending.

If startup or layout fails, reinstall your original BCD.ipa as an update using
the same signing identity, then export the full log. The original IPA is kept
untouched. New diagnostic markers: [bcd-duo], [bcd-duo-display], [bcd-duo-audio].

PATCH SOURCE
BCDDuo-Patch-Source.zip contains the compatibility source and build/packaging
scripts. BCD's unmodified corresponding source release is linked above.
build.sh requires Xcode with SDK 27.1 and an available iOS 27 simulator.
Run package.py with the original IPA, successful BCDDuo.dylib build artifact
folder (including build.json and duo-fixture.json), and the output IPA path.
The packager verifies the input hash and all retained files, and rejects a
library without the matching successful UIKit fixture report.
